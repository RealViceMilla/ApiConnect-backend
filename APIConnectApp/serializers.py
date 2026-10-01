from django.forms.models import model_to_dict

from .models import (
    APISection,
    Alert,
    Campus,
    CampusCareer,
    Career,
    Course,
    CycleTemplate,
    Document,
    DocumentVersion,
    ProcessStage,
    ProductivePartner,
    Semester,
    User,
    UserCampus,
    Visit,
)


# Convierte fechas y datetimes a texto ISO para respuestas JSON.
def _date(value):
    return value.isoformat() if value else None


# Serializa la informacion publica basica de un usuario.
def user_to_dict(user: User):
    if user is None:
        return None
    roles = sorted(set(user.groups.filter(name__in=User.Role.values).values_list("name", flat=True)) | {user.rol})
    role_labels = dict(User.Role.choices)
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.get_full_name(),
        "email": user.email,
        "rol": user.rol,
        "rol_display": user.get_rol_display(),
        "roles": roles,
        "roles_display": [role_labels[role] for role in roles],
    }


# Serializa una sede institucional.
def campus_to_dict(campus: Campus):
    return {"id": campus.id, "name": campus.name, "is_active": campus.is_active}


# Serializa una carrera institucional.
def career_to_dict(career: Career):
    return {"id": career.id, "code": career.code, "name": career.name, "is_active": career.is_active}


# Serializa la relacion carrera-sede usada por las secciones API.
def campus_career_to_dict(campus_career: CampusCareer):
    return {
        "id": campus_career.id,
        "campus": campus_to_dict(campus_career.campus),
        "career": career_to_dict(campus_career.career),
        "is_active": campus_career.is_active,
    }


# Serializa una asignatura API.
def course_to_dict(course: Course):
    return {"id": course.id, "code": course.code, "name": course.name, "is_active": course.is_active}


# Serializa un periodo academico.
def semester_to_dict(semester: Semester):
    return {"id": semester.id, "year": semester.year, "period": semester.period, "is_active": semester.is_active}


# Serializa una empresa o contraparte productiva.
def partner_to_dict(partner: ProductivePartner):
    if partner is None:
        return None
    return {
        "id": partner.id,
        "name": partner.name,
        "rut": partner.rut,
        "business_area": partner.business_area,
        "contact_name": partner.contact_name,
        "contact_email": partner.contact_email,
        "contact_phone": partner.contact_phone,
        "address": partner.address,
        "requirements_match": partner.requirements_match,
        "status": partner.status,
        "proposed_by": user_to_dict(partner.proposed_by),
    }


# Serializa una seccion API y opcionalmente su detalle BPM.
def section_to_dict(section: APISection, include_children=False):
    data = {
        "id": section.id,
        "name": section.name,
        "campus_career": campus_career_to_dict(section.campus_career),
        "course": course_to_dict(section.course),
        "semester": semester_to_dict(section.semester),
        "career_director": user_to_dict(section.career_director),
        "specialist_teacher": user_to_dict(section.specialist_teacher),
        "ctp_coordinator": user_to_dict(section.ctp_coordinator),
        "productive_partner": partner_to_dict(section.productive_partner),
        "status": section.status,
        "created_at": _date(section.created_at),
        "updated_at": _date(section.updated_at),
    }
    if include_children:
        stages = list(section.stages.all())
        template_map = {template.stage_type: template for template in CycleTemplate.objects.filter(stage_type__in={stage.stage_type for stage in stages}).only("id", "stage_type", "file", "updated_at")}
        data["stages"] = [stage_to_dict(stage, include_documents=True, template_map=template_map) for stage in stages]
        data["visits"] = [visit_to_dict(visit) for visit in section.visits.all()]
        data["alerts"] = [alert_to_dict(alert) for alert in section.alerts.filter(is_active=True)]
    return data


# Serializa una etapa del proceso BPM.
def stage_to_dict(stage: ProcessStage, include_documents=False, template_map=None):
    template = template_map.get(stage.stage_type) if template_map is not None else CycleTemplate.objects.filter(stage_type=stage.stage_type).only("id", "file", "updated_at").first()
    data = {
        "id": stage.id,
        "section_id": stage.section_id,
        "stage_type": stage.stage_type,
        "stage_type_display": stage.get_stage_type_display(),
        "order": stage.order,
        "responsible_role": stage.responsible_role,
        "responsible_role_display": stage.get_responsible_role_display(),
        "responsible_user": user_to_dict(stage.responsible_user),
        "status": stage.status,
        "due_date": _date(stage.due_date),
        "completed_at": _date(stage.completed_at),
        "notes": stage.notes,
        "feedback": stage.feedback,
        "review_details": stage.review_details,
        "is_overdue": stage.is_overdue,
        "template": {
            "id": template.id,
            "file_name": template.file.name.rsplit("/", 1)[-1],
            "updated_at": _date(template.updated_at),
        } if template else None,
    }
    if include_documents:
        data["documents"] = [document_to_dict(document, include_versions=True) for document in stage.documents.all()]
    return data


# Serializa un documento logico asociado a una etapa.
def document_to_dict(document: Document, include_versions=False):
    stage = document.stage
    section = stage.section
    data = {
        "id": document.id,
        "stage_id": document.stage_id,
        "stage": {
            "id": stage.id,
            "order": stage.order,
            "stage_type": stage.stage_type,
            "stage_type_display": stage.get_stage_type_display(),
            "status": stage.status,
        },
        "section": {
            "id": section.id,
            "name": section.name,
            "status": section.status,
            "course": course_to_dict(section.course),
            "semester": semester_to_dict(section.semester),
            "campus_career": campus_career_to_dict(section.campus_career),
        },
        "title": document.title,
        "document_type": document.document_type,
        "status": document.status,
        "current_version": document.current_version,
        "delivery_due_date": _date(document.delivery_due_date),
        "review_due_date": _date(document.review_due_date),
        "uploaded_by": user_to_dict(document.uploaded_by),
        "reviewed_by": user_to_dict(document.reviewed_by),
        "approved_by": user_to_dict(document.approved_by),
        "reviewed_at": _date(document.reviewed_at),
        "approved_at": _date(document.approved_at),
        "is_historical": document.is_historical,
    }
    if include_versions:
        data["versions"] = [document_version_to_dict(version) for version in document.versions.all()]
    return data


# Serializa una version fisica de un documento.
def document_version_to_dict(version: DocumentVersion):
    file_name = version.file.name.rsplit("/", 1)[-1] if version.file else None
    return {
        "id": version.id,
        "document_id": version.document_id,
        "version_number": version.version_number,
        "file": version.file.url if version.file else None,
        "file_name": file_name,
        "notes": version.notes,
        "uploaded_by": user_to_dict(version.uploaded_by),
        "created_at": _date(version.created_at),
    }


# Serializa una visita referencial de la seccion.
def visit_to_dict(visit: Visit):
    return {
        "id": visit.id,
        "section_id": visit.section_id,
        "visit_number": visit.visit_number,
        "scheduled_date": _date(visit.scheduled_date),
        "status": visit.status,
        "notes": visit.notes,
        "place": visit.place,
        "assigned_teacher": user_to_dict(visit.assigned_teacher),
    }


# Serializa una alerta activa o historica del proceso.
def alert_to_dict(alert: Alert):
    return {
        "id": alert.id,
        "section_id": alert.section_id,
        "stage_id": alert.stage_id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "title": alert.title,
        "message": alert.message,
        "created_at": alert.created_at.isoformat(),
        "due_date": _date(alert.due_date),
        "is_active": alert.is_active,
        "email_sent": alert.email_sent,
        "resolved_at": _date(alert.resolved_at),
        "recipients": [user_to_dict(user) for user in alert.recipients.all()],
    }


# Normaliza errores de formularios para responderlos como JSON.
def validation_errors_to_dict(form):
    return {field: [str(error) for error in errors] for field, errors in form.errors.items()}


# Convierte modelos simples a diccionarios primitivos cuando no se necesita un serializer especifico.
def primitive_model_dict(instance, exclude=None):
    return model_to_dict(instance, exclude=exclude or [])




