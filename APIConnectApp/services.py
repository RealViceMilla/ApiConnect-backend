from datetime import timedelta

import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import close_old_connections, transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.html import escape

from .models import APISection, Alert, AuditLog, CalendarEvent, Document, DocumentVersion, ProcessStage, ProductivePartner, User, Visit


logger = logging.getLogger(__name__)

# El SMTP no debe bloquear las peticiones web. Un unico worker evita abrir
# varios envios simultaneos contra Gmail.
_email_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="api-alert-email")


def enqueue_alert_email(alert_id, recipient_ids=None):
    """Programa el correo tras el commit y fuera del ciclo de respuesta HTTP."""
    ids = tuple(recipient_ids) if recipient_ids is not None else None

    def submit():
        future = _email_executor.submit(_send_alert_email_in_worker, alert_id, ids)
        future.add_done_callback(_log_email_task_error)

    transaction.on_commit(submit)


def _log_email_task_error(future):
    try:
        future.result()
    except Exception:
        logger.exception("Fallo inesperado en el worker de correo de alertas.")


def _send_alert_email_in_worker(alert_id, recipient_ids):
    close_old_connections()
    try:
        return send_alert_email(alert_id, recipient_ids)
    finally:
        close_old_connections()


# Define las seis etapas estandar del flujo BPM academico.
DEFAULT_STAGE_BLUEPRINT = (
    (1, ProcessStage.StageType.REQUIREMENTS),
    (2, ProcessStage.StageType.COMPANY_PROPOSAL),
    (3, ProcessStage.StageType.PROJECT_PROPOSAL),
    (4, ProcessStage.StageType.DOCUMENT_VALIDATION),
    (5, ProcessStage.StageType.FOLLOW_UP),
    (6, ProcessStage.StageType.CTP_VALIDATION),
    (7, ProcessStage.StageType.VISITS),
    (8, ProcessStage.StageType.FINAL_DELIVERY),
    (9, ProcessStage.StageType.CLOSURE),
)

# Define permisos CRUD base que se sincronizan en Django Groups.
ROLE_GROUP_PERMISSIONS = {
    User.Role.ADMIN: ["view", "add", "change", "delete"],
    User.Role.DA: ["view", "add", "change"],
    User.Role.DC: ["view", "change"],
    User.Role.AP: ["view"],
    User.Role.C_API: ["view"],
    User.Role.CTP: ["view", "change"],
    User.Role.D_VCM: ["view", "add", "change"],
    User.Role.DE: ["view", "change"],
}

# Define permisos de negocio especificos que no son CRUD generico.
ROLE_CUSTOM_PERMISSIONS = {
    User.Role.DC: [
        "define_requirements",
        "select_productive_partner",
        "close_api_section",
        "download_api_document",
    ],
    User.Role.D_VCM: ["propose_productive_partner"],
    User.Role.CTP: ["review_api_document", "download_api_document"],
    User.Role.C_API: ["download_api_document"],
}


# Crea las etapas iniciales de una seccion API respetando el orden BPM.
def create_default_stages(section: APISection, start_date=None, days_between_stages=7):
    start_date = start_date or timezone.localdate()
    created = []
    with transaction.atomic():
        for order, stage_type in DEFAULT_STAGE_BLUEPRINT:
            stage, was_created = ProcessStage.objects.get_or_create(
                section=section,
                order=order,
                defaults={
                    "stage_type": stage_type,
                    "due_date": start_date + timedelta(days=days_between_stages * order),
                },
            )
            if was_created:
                created.append(stage)
    return created


# Sincroniza los grupos de Django con los permisos esperados por cada rol.
def sync_role_groups():
    managed_models = [APISection, ProcessStage, Document, DocumentVersion, ProductivePartner, Visit, Alert]
    for role, actions in ROLE_GROUP_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        group.permissions.clear()
        for model in managed_models:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(
                content_type=content_type,
                codename__in=[f"{action}_{model._meta.model_name}" for action in actions],
            )
            group.permissions.add(*permissions)
        custom_permissions = Permission.objects.filter(codename__in=ROLE_CUSTOM_PERMISSIONS.get(role, []))
        group.permissions.add(*custom_permissions)
    return Group.objects.filter(name__in=ROLE_GROUP_PERMISSIONS.keys())


# Crea los documentos base requeridos para cada etapa del proceso.
def create_default_documents(stage: ProcessStage):
    document_titles = {
        ProcessStage.StageType.REQUIREMENTS: [("Ficha de requisitos académicos", Document.DocumentType.EXCEL)],
        ProcessStage.StageType.COMPANY_PROPOSAL: [("Ficha de objetivos VcM", Document.DocumentType.EXCEL)],
        ProcessStage.StageType.PROJECT_PROPOSAL: [("Ficha de posibles contrapartes", Document.DocumentType.EXCEL)],
        ProcessStage.StageType.DOCUMENT_VALIDATION: [("Ficha de selección de contraparte", Document.DocumentType.EXCEL)],
        ProcessStage.StageType.FOLLOW_UP: [("Ficha de formulación del proyecto", Document.DocumentType.EXCEL)],
        ProcessStage.StageType.FINAL_DELIVERY: [("Entrega del proyecto final", Document.DocumentType.EXCEL)],
        ProcessStage.StageType.CLOSURE: [("Acta de cierre", Document.DocumentType.EXCEL)],
    }
    created = []
    for title, document_type in document_titles.get(stage.stage_type, []):
        document, was_created = Document.objects.get_or_create(
            stage=stage,
            title=title,
            defaults={"document_type": document_type},
        )
        if was_created:
            created.append(document)
    return created


# Registra acciones importantes para trazabilidad y auditoría.
def log_action(action, actor=None, section=None, stage=None, document=None, metadata=None, ip_address=None):
    return AuditLog.objects.create(
        actor=actor,
        section=section,
        stage=stage,
        document=document,
        action=action,
        metadata=metadata or {},
        ip_address=ip_address,
    )

# Agrega una nueva version fisica a un documento y actualiza su estado.
def _is_admin_user(user):
    if not user:
        return False
    return bool(
        user.is_superuser
        or user.rol == User.Role.ADMIN
        or user.groups.filter(name=User.Role.ADMIN).exists()
    )


def _reopen_stage_for_admin(stage, user):
    if stage.status in {ProcessStage.Status.APPROVED, ProcessStage.Status.FINISHED} and _is_admin_user(user):
        stage.status = ProcessStage.Status.IN_PROGRESS
        stage.completed_at = None
        stage.save(update_fields=["status", "completed_at", "updated_at"])


@transaction.atomic
def add_document_version(document: Document, uploaded_file, uploaded_by=None, notes=""):
    _reopen_stage_for_admin(document.stage, uploaded_by)
    if document.stage.status in {ProcessStage.Status.APPROVED, ProcessStage.Status.FINISHED}:
        raise ValidationError("No se pueden subir documentos a una etapa cerrada.")
    document.document_type = Document.DocumentType.EXCEL
    next_version = (document.versions.aggregate(latest=Max("version_number"))["latest"] or 0) + 1
    version = DocumentVersion(
        document=document,
        version_number=next_version,
        file=uploaded_file,
        uploaded_by=uploaded_by,
        notes=notes,
    )
    version.full_clean()
    version.save()
    document.current_version = next_version
    document.status = Document.Status.UPLOADED
    document.uploaded_by = uploaded_by or document.uploaded_by
    document.reviewed_by = None
    document.reviewed_at = None
    document.approved_by = None
    document.approved_at = None
    document.full_clean()
    document.save(update_fields=["document_type", "current_version", "status", "uploaded_by", "reviewed_by", "reviewed_at", "approved_by", "approved_at", "updated_at"])
    if document.stage.status in {ProcessStage.Status.PENDING, ProcessStage.Status.REJECTED, ProcessStage.Status.DELAYED}:
        document.stage.status = ProcessStage.Status.IN_PROGRESS
        document.stage.completed_at = None
        document.stage.save(update_fields=["status", "completed_at", "updated_at"])
    log_action(
        AuditLog.Action.DOCUMENT_UPLOADED,
        actor=uploaded_by,
        section=document.stage.section,
        stage=document.stage,
        document=document,
        metadata={"version": next_version},
    )
    return version


@transaction.atomic
def delete_document_version(version: DocumentVersion, deleted_by=None, ip_address=None):
    document = version.document
    version_number = version.version_number
    file_name = version.file.name.rsplit("/", 1)[-1] if version.file else ""
    storage = version.file.storage if version.file else None
    stored_name = version.file.name if version.file else ""

    version.delete()
    latest_version = document.versions.select_related("uploaded_by").order_by("-version_number").first()
    document.current_version = latest_version.version_number if latest_version else 1
    document.status = Document.Status.UPLOADED if latest_version else Document.Status.PENDING
    document.uploaded_by = latest_version.uploaded_by if latest_version else None
    document.reviewed_by = None
    document.reviewed_at = None
    document.approved_by = None
    document.approved_at = None
    document.save(update_fields=["current_version", "status", "uploaded_by", "reviewed_by", "reviewed_at", "approved_by", "approved_at", "updated_at"])

    log_action(
        AuditLog.Action.DOCUMENT_DELETED,
        actor=deleted_by,
        section=document.stage.section,
        stage=document.stage,
        document=document,
        metadata={"version": version_number, "file_name": file_name},
        ip_address=ip_address,
    )
    if storage and stored_name:
        transaction.on_commit(lambda: storage.delete(stored_name))
    return document


def send_alert_email(alert_id, recipient_ids=None):
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return 0
    try:
        alert = Alert.objects.select_related("section__course", "stage").get(pk=alert_id)
        if not alert.is_active or alert.resolved_at:
            return 0
        recipients = alert.recipients.filter(is_active=True).exclude(email="")
        if recipient_ids is not None:
            recipients = recipients.filter(pk__in=recipient_ids)
        recipients = list(recipients)
        if not recipients:
            return 0

        stage_label = f"Etapa {alert.stage.order}: {alert.stage.get_stage_type_display()}" if alert.stage else "Proceso general"
        section_label = f"{alert.section.course.name} · {alert.section.name}"
        stage_query = f"?stage={alert.stage.order}" if alert.stage else ""
        detail_url = f"{settings.FRONTEND_BASE_URL}/#/sections/{alert.section_id}{stage_query}"
        date_label = "Fecha de la visita" if alert.alert_type == Alert.AlertType.MISSING_VISIT else "Fecha límite"
        due_date = alert.due_date.strftime("%d-%m-%Y") if alert.due_date else "Sin fecha"
        messages = []
        for recipient in recipients:
            recipient_name = recipient.get_full_name() or recipient.username
            body = (
                f"Hola {recipient_name},\n\n{alert.message}\n\n"
                f"Sección: {section_label}\nEtapa: {stage_label}\n{date_label}: {due_date}\n\n"
                f"Abrir en APIConnect: {detail_url}\n"
            )
            message = EmailMultiAlternatives(
                subject=f"[APIConnect] {alert.title}",
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient.email],
            )
            message.attach_alternative(
                f"""
                <div style="font-family:Arial,sans-serif;color:#1d1d1b;line-height:1.5;max-width:620px">
                  <h2 style="color:#c8102e">{escape(alert.title)}</h2>
                  <p>Hola {escape(recipient_name)},</p>
                  <p>{escape(alert.message)}</p>
                  <div style="background:#f4f6f8;border-left:4px solid #0e4684;padding:12px 16px;margin:18px 0">
                    <strong>Sección:</strong> {escape(section_label)}<br>
                    <strong>Etapa:</strong> {escape(stage_label)}<br>
                    <strong>{escape(date_label)}:</strong> {escape(due_date)}
                  </div>
                  <p><a href="{escape(detail_url)}" style="display:inline-block;background:#c8102e;color:#fff;text-decoration:none;padding:10px 16px;border-radius:6px;font-weight:bold">Abrir en APIConnect</a></p>
                </div>
                """,
                "text/html",
            )
            messages.append(message)

        with get_connection() as connection:
            sent_count = connection.send_messages(messages)
        if sent_count == len(messages):
            Alert.objects.filter(pk=alert.id).update(email_sent=True)
        return sent_count
    except Exception:
        logger.exception("No se pudo enviar por correo la alerta %s.", alert_id)
        return 0


# Revisa un documento y registra aprobación o rechazo.
def review_document(document: Document, reviewer, approved: bool):
    _reopen_stage_for_admin(document.stage, reviewer)
    if document.stage.status in {ProcessStage.Status.APPROVED, ProcessStage.Status.FINISHED}:
        raise ValidationError("No se puede revisar un documento de una etapa cerrada.")
    if approved and not document.versions.exists():
        raise ValidationError("No se puede aprobar un documento sin archivo versionado.")
    now = timezone.now()
    document.reviewed_by = reviewer
    document.reviewed_at = now
    if approved:
        document.status = Document.Status.APPROVED
        document.approved_by = reviewer
        document.approved_at = now
    else:
        document.status = Document.Status.REJECTED
        document.approved_by = None
        document.approved_at = None
    document.full_clean()
    document.save()
    log_action(
        AuditLog.Action.DOCUMENT_APPROVED if approved else AuditLog.Action.DOCUMENT_REJECTED,
        actor=reviewer,
        section=document.stage.section,
        stage=document.stage,
        document=document,
    )
    update_stage_status_from_documents(document.stage)
    return document


# Recalcula el estado de una etapa en funcion del estado de sus documentos.
def update_stage_status_from_documents(stage: ProcessStage):
    documents = list(stage.documents.all())
    if not documents:
        return stage
    if all(document.status == Document.Status.APPROVED for document in documents):
        stage.status = ProcessStage.Status.APPROVED
        stage.completed_at = timezone.now()
    elif any(document.status in {Document.Status.UPLOADED, Document.Status.UNDER_REVIEW} for document in documents):
        stage.status = ProcessStage.Status.IN_PROGRESS
    elif any(document.status == Document.Status.REJECTED for document in documents):
        stage.status = ProcessStage.Status.REJECTED
    stage.full_clean()
    stage.save(update_fields=["status", "completed_at", "updated_at"])
    return stage


# Avanza una etapa solo cuando todos sus documentos estan aprobados.
def advance_stage(stage: ProcessStage, actor=None, status=ProcessStage.Status.FINISHED, check_documents=True):
    if stage.status in {ProcessStage.Status.APPROVED, ProcessStage.Status.FINISHED}:
        raise ValidationError("La etapa ya está cerrada.")
    if check_documents and stage.documents.exclude(status=Document.Status.APPROVED).exists():
        raise ValidationError("No se puede avanzar la etapa sin todos sus documentos aprobados.")
    stage.status = status
    stage.completed_at = timezone.now()
    stage.full_clean()
    stage.save(update_fields=["status", "completed_at", "updated_at"])
    resolve_stage_alerts(stage, stage.completed_at)
    log_action(AuditLog.Action.STAGE_CHANGED, actor=actor, section=stage.section, stage=stage, metadata={"status": status})
    return stage


# Recalcula el estado general de la seccion segun sus etapas.
def refresh_section_status(section: APISection):
    if hasattr(section, "_prefetched_objects_cache"):
        section._prefetched_objects_cache.pop("stages", None)
    stages = list(section.stages.all())
    if not stages:
        return section
    if all(stage.status in {ProcessStage.Status.APPROVED, ProcessStage.Status.FINISHED} for stage in stages):
        section.status = APISection.Status.FINISHED
    elif any(stage.is_overdue or stage.status == ProcessStage.Status.DELAYED for stage in stages):
        section.status = APISection.Status.DELAYED
    elif any(stage.status == ProcessStage.Status.IN_PROGRESS for stage in stages):
        section.status = APISection.Status.IN_PROGRESS
    else:
        section.status = APISection.Status.ACTIVE
    section.full_clean()
    section.save(update_fields=["status", "updated_at"])
    return section


# Mantiene compatibilidad con clientes antiguos: los requisitos ya no se guardan en APISection.
def update_section_requirements(section: APISection, requirements, actor=None, ip_address=None):
    raise ValidationError("Los requisitos académicos se gestionan mediante documentos de etapa, no como dato de la sección API.")


# Registra una empresa propuesta por Vinculacion con el Medio.
def propose_partner_for_section(section: APISection, partner_data, actor=None, ip_address=None):
    if section.status == APISection.Status.FINISHED:
        raise ValidationError("No se puede proponer una empresa para una sección cerrada.")
    partner = ProductivePartner.objects.create(
        name=partner_data["name"],
        rut=partner_data.get("rut", ""),
        business_area=partner_data.get("business_area", ""),
        contact_name=partner_data.get("contact_name", ""),
        contact_email=partner_data.get("contact_email", ""),
        contact_phone=partner_data.get("contact_phone", ""),
        address=partner_data.get("address", ""),
        requirements_match=partner_data.get("requirements_match", ""),
        proposed_by=actor,
        status=ProductivePartner.Status.PROPOSED,
    )
    log_action(
        AuditLog.Action.PARTNER_PROPOSED,
        actor=actor,
        section=section,
        metadata={"partner_id": partner.id, "partner_name": partner.name},
        ip_address=ip_address,
    )
    return partner


# Selecciona la contraparte definitiva para la seccion API.
def select_partner_for_section(section: APISection, partner: ProductivePartner, actor=None, ip_address=None):
    if section.status == APISection.Status.FINISHED:
        raise ValidationError("No se puede seleccionar una empresa para una sección cerrada.")
    section.productive_partner = partner
    section.full_clean()
    section.save(update_fields=["productive_partner", "updated_at"])
    log_action(
        AuditLog.Action.PARTNER_SELECTED,
        actor=actor,
        section=section,
        metadata={"selected_partner_id": partner.id, "selected_partner_name": partner.name},
        ip_address=ip_address,
    )
    return section


# Genera alertas por etapas, documentos, visitas y eventos cercanos a vencer.
def _date_alert_state(due_date, reference_date, overdue_type=None, upcoming_type=None):
    if not due_date:
        return None
    days_until = (due_date - reference_date).days
    if days_until > 1:
        return None
    if days_until < 0:
        return Alert.Severity.RED, overdue_type or Alert.AlertType.OVERDUE_STAGE, "está vencido"
    if days_until == 0:
        return Alert.Severity.RED, upcoming_type or Alert.AlertType.STAGE_DELAY, "vence hoy"
    return Alert.Severity.YELLOW, upcoming_type or Alert.AlertType.STAGE_DELAY, "vence mañana"


def resolve_stage_alerts(stage, resolved_at=None):
    resolved_at = resolved_at or timezone.now()
    return Alert.objects.filter(stage=stage, is_active=True).update(
        is_active=False,
        resolved_at=resolved_at,
        updated_at=resolved_at,
    )
def _active_unique_users(users):
    selected = []
    seen = set()
    for user in users:
        if user and user.is_active and user.pk not in seen:
            selected.append(user)
            seen.add(user.pk)
    return selected


def _section_director_and_ctp(section):
    return _active_unique_users([
        getattr(section, "career_director", None),
        getattr(section, "ctp_coordinator", None),
    ])


def _refresh_alert(alert, severity, title, message):
    update_fields = []
    if alert.severity != severity:
        alert.severity = severity
        update_fields.append("severity")
    if alert.title != title:
        alert.title = title
        update_fields.append("title")
    if alert.message != message:
        alert.message = message
        update_fields.append("message")
    if update_fields:
        alert.email_sent = False
        update_fields.extend(["email_sent", "updated_at"])
        alert.save(update_fields=update_fields)


def _assign_recipients_and_send(alert, users, was_created):
    recipients = _active_unique_users(users)
    existing_ids = set(alert.recipients.filter(pk__in=[user.pk for user in recipients]).values_list("pk", flat=True))
    if recipients:
        alert.recipients.add(*recipients)
    # Los destinatarios nuevos disparan la senal m2m. Si todos ya estaban
    # asignados, reintentamos aqui solamente cuando el correo sigue pendiente.
    has_new_recipients = any(user.pk not in existing_ids for user in recipients)
    if recipients and not has_new_recipients and (was_created or not alert.email_sent):
        enqueue_alert_email(alert.id, [user.pk for user in recipients])


def generate_due_alerts(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    warning_date = reference_date + timedelta(days=1)
    created = []

    due_stages = ProcessStage.objects.select_related(
        "section", "section__course", "section__career_director", "section__specialist_teacher", "section__ctp_coordinator"
    ).filter(
        due_date__lte=warning_date,
        status__in=[ProcessStage.Status.PENDING, ProcessStage.Status.IN_PROGRESS, ProcessStage.Status.REJECTED],
    )
    for stage in due_stages:
        state = _date_alert_state(stage.due_date, reference_date)
        if not state:
            continue
        severity, alert_type, label = state
        title = f"Etapa pendiente: {stage.get_stage_type_display()}"
        message = f"La etapa {stage.get_stage_type_display()} {label}. Fecha límite: {stage.due_date.strftime('%d-%m-%Y')}."
        alert, was_created = Alert.objects.get_or_create(
            section=stage.section,
            stage=stage,
            alert_type=alert_type,
            due_date=stage.due_date,
            is_active=True,
            defaults={"severity": severity, "title": title, "message": message},
        )
        if was_created:
            created.append(alert)
        else:
            _refresh_alert(alert, severity, title, message)
        _assign_recipients_and_send(alert, [stage.responsible_user], was_created)

    due_documents = Document.objects.select_related(
        "stage", "stage__section", "stage__section__course", "stage__section__career_director", "stage__section__specialist_teacher", "stage__section__ctp_coordinator"
    ).filter(
        delivery_due_date__lte=warning_date,
        status__in=[Document.Status.PENDING, Document.Status.REJECTED],
    )
    for document in due_documents:
        state = _date_alert_state(
            document.delivery_due_date,
            reference_date,
            upcoming_type=Alert.AlertType.PENDING_DOCUMENT,
            overdue_type=Alert.AlertType.PENDING_DOCUMENT,
        )
        if not state:
            continue
        severity, alert_type, label = state
        title = f"Documento pendiente: {document.title}"
        message = f"El documento {document.title} {label}. Fecha límite: {document.delivery_due_date.strftime('%d-%m-%Y')}."
        alert, was_created = Alert.objects.get_or_create(
            section=document.stage.section,
            stage=document.stage,
            alert_type=alert_type,
            due_date=document.delivery_due_date,
            is_active=True,
            defaults={"severity": severity, "title": title, "message": message},
        )
        if was_created:
            created.append(alert)
        else:
            _refresh_alert(alert, severity, title, message)
        _assign_recipients_and_send(alert, [document.stage.responsible_user], was_created)

    completed_visit_dates = Visit.objects.filter(
        scheduled_date__lte=reference_date,
        status__in=[Visit.Status.COMPLETED, Visit.Status.CANCELLED],
    ).values_list("section_id", "scheduled_date", "visit_number")
    now = timezone.now()
    for section_id, scheduled_date, visit_number in completed_visit_dates:
        Alert.objects.filter(
            section_id=section_id,
            alert_type=Alert.AlertType.MISSING_VISIT,
            due_date=scheduled_date,
            title=f"Visita programada: Visita {visit_number}",
            is_active=True,
        ).update(is_active=False, resolved_at=now, updated_at=now)

    due_visits = Visit.objects.select_related(
        "section", "section__course", "section__career_director"
    ).filter(
        scheduled_date=reference_date,
    ).exclude(status__in=[Visit.Status.COMPLETED, Visit.Status.CANCELLED])
    for visit in due_visits:
        severity = Alert.Severity.RED
        alert_type = Alert.AlertType.MISSING_VISIT
        title = f"Visita programada: Visita {visit.visit_number}"
        message = f"La visita {visit.visit_number} de la sección {visit.section.name} está programada para hoy. Fecha: {visit.scheduled_date.strftime('%d-%m-%Y')}."
        alert, was_created = Alert.objects.get_or_create(
            section=visit.section,
            alert_type=alert_type,
            due_date=visit.scheduled_date,
            title=title,
            is_active=True,
            defaults={"severity": severity, "message": message},
        )
        if was_created:
            created.append(alert)
        else:
            _refresh_alert(alert, severity, title, message)
        _assign_recipients_and_send(alert, _section_director_and_ctp(visit.section), was_created)

    due_events = CalendarEvent.objects.select_related(
        "section", "section__course", "section__career_director"
    ).filter(
        section__isnull=False,
        event_date__lte=warning_date,
    )
    for event in due_events:
        state = _date_alert_state(event.event_date, reference_date)
        if not state:
            continue
        severity, alert_type, label = state
        title = f"Evento de calendario: {event.title}"
        message = f"El evento de calendario {event.title} {label}. Fecha: {event.event_date.strftime('%d-%m-%Y')}."
        alert, was_created = Alert.objects.get_or_create(
            section=event.section,
            alert_type=alert_type,
            due_date=event.event_date,
            title=title,
            is_active=True,
            defaults={"severity": severity, "message": message},
        )
        if was_created:
            created.append(alert)
        else:
            _refresh_alert(alert, severity, title, message)
        _assign_recipients_and_send(alert, _section_director_and_ctp(event.section), was_created)

    return created

# Genera alertas cuando faltan visitas referenciales de una seccion.
def create_missing_visit_alerts(section: APISection):
    existing_numbers = set(section.visits.values_list("visit_number", flat=True))
    created = []
    for visit_number in range(1, 4):
        if visit_number in existing_numbers:
            continue
        alert, was_created = Alert.objects.get_or_create(
            section=section,
            alert_type=Alert.AlertType.MISSING_VISIT,
            title=f"Visita {visit_number} sin registrar",
            is_active=True,
            defaults={
                "severity": Alert.Severity.YELLOW,
                "message": f"La visita {visit_number} aún no está registrada para la sección API.",
            },
        )
        if was_created:
            created.append(alert)
    return created










