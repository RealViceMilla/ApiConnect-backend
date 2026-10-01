from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone



MAX_DOCUMENT_SIZE_MB = 20
MAX_DOCUMENT_SIZE_BYTES = MAX_DOCUMENT_SIZE_MB * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".xls",
    ".xlsx",
}
username_with_spaces_validator = RegexValidator(
    r"^[\w.@+\- ]+\Z",
    "El nombre de usuario solo puede contener letras, números, espacios, tildes y @/./+/-/_.",
)

DOCUMENT_TYPE_EXTENSIONS = {
    "Excel": {".xls", ".xlsx"},
    "Otro": ALLOWED_DOCUMENT_EXTENSIONS,
}


def validate_document_file(file):
    name = getattr(file, "name", "")
    extension = f".{name.rsplit('.', 1)[-1].lower()}" if "." in name else ""
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError("Tipo de archivo no permitido. Usa solo Excel (.xls o .xlsx).")
    if getattr(file, "size", 0) > MAX_DOCUMENT_SIZE_BYTES:
        raise ValidationError(f"El archivo no puede superar {MAX_DOCUMENT_SIZE_MB} MB.")


# Modelo para agregar campos de timestamp a otros modelos, con created_at y updated_at automáticos
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Representa a cada usuario del sistema y define su rol dentro del proceso API.
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        DA = "DA", "Director Académico"
        DC = "DC", "Director de Carrera"
        AP = "AP", "Asesor Pedagógico"
        C_API = "C_API", "Coordinador API"
        CTP = "CTP", "Coordinador Técnico Pedagógico"
        D_VCM = "D_VCM", "Director de Vinculación con el Medio"
        DE = "DE", "Docente Especialista"


    username = models.CharField(
        "nombre de usuario",
        max_length=150,
        unique=True,
        help_text="Requerido. Permite letras, números, espacios, tildes y @/./+/-/_.",
        validators=[username_with_spaces_validator],
        error_messages={"unique": "Ya existe un usuario con ese nombre."},
    )
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=20, choices=Role.choices, default=Role.C_API)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return f"{self.get_full_name() or self.username} - {self.get_rol_display()}"


# representa una sede institucional donde se desarrollan las asignaturas API.
class Campus(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "sede"
        verbose_name_plural = "sedes"

    def __str__(self):
        return self.name


# define a qué sedes tiene acceso o en cuáles puede trabajar un usuario.
class UserCampus(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campus_access")
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="user_access")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["user", "campus"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "campus"],
                name="unique_user_campus",
            )
        ]
        verbose_name = "sede de usuario"
        verbose_name_plural = "sedes de usuarios"

    def __str__(self):
        return f"{self.user} - {self.campus}"


# una carrera institucional disponible para ser impartida en distintas sedes.
class Career(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=180)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "carrera"
        verbose_name_plural = "carreras"

    def __str__(self):
        return self.name


#relaciona una carrera con una sede específica donde se encuentra disponible.
class CampusCareer(TimeStampedModel):
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="campus_careers")
    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="campus_careers")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "carrera por sede"
        verbose_name_plural = "carreras por sede"

        constraints = [
            models.UniqueConstraint(
                fields=["campus", "career"],
                name="unique_campus_career"
            )
        ]

    def __str__(self):
        return f"{self.career} - {self.campus}"


# representa una asignatura API que participa en el modelo de Aprendizaje Integrado al Sector Productivo.
class Course(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=180)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "asignatura API"
        verbose_name_plural = "asignaturas API"

    def __str__(self):
        return f"{self.name} ({self.code})"


# representa un período académico institucional, como Otoño o Primavera de un determinado año.
class Semester(TimeStampedModel):
    class Period(models.TextChoices):
        OTONO = "Otoño", "Otoño"
        PRIMAVERA = "Primavera", "Primavera"

    year = models.PositiveIntegerField()
    period = models.CharField(max_length=20, choices=Period.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-year", "period"]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "period"],
                name="unique_semester_period_by_year",
            )
        ]
        verbose_name = "semestre"
        verbose_name_plural = "semestres"

    def __str__(self):
        return f"{self.period} {self.year}"


# representa una empresa o socio productivo que participa en proyectos asociados a las asignaturas API.
class ProductivePartner(TimeStampedModel):
    class Status(models.TextChoices):
        PROPOSED = "Propuesta", "Propuesta"
        VALIDATED = "Validada", "Validada"
        REJECTED = "Rechazada", "Rechazada"
        INACTIVE = "Inactiva", "Inactiva"

    name = models.CharField(max_length=180)
    rut = models.CharField(max_length=30, blank=True)
    business_area = models.CharField(max_length=150, blank=True)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    requirements_match = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED)
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposed_partners",
    )

    class Meta:
        ordering = ["name"]
        permissions = [
            ("propose_productive_partner", "Puede proponer empresas o contrapartes"),
        ]
        verbose_name = "socio productivo"
        verbose_name_plural = "socios productivos"

    def __str__(self):
        return self.name


# representa una sección concreta de una asignatura API
# en una sede, carrera y semestre determinados, siendo la entidad principal del sistema.
class APISection(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "Activa", "Activa"
        IN_PROGRESS = "En proceso", "En proceso"
        DELAYED = "Retrasada", "Retrasada"
        FINISHED = "Finalizada", "Finalizada"
        SUSPENDED = "Suspendida", "Suspendida"

    campus_career = models.ForeignKey(CampusCareer, on_delete=models.PROTECT, related_name="api_sections")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="api_sections")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="api_sections")
    name = models.CharField(max_length=50)

    career_director = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name="api_sections_as_career_director")
    specialist_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name="api_sections_as_specialist")
    ctp_coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name="api_sections_as_ctp_coordinator")
    productive_partner = models.ForeignKey(
        ProductivePartner, on_delete=models.SET_NULL, null=True,
        blank=True, related_name="api_sections")
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["semester", "campus_career", "course", "name"]
        permissions = [
            ("define_requirements", "Puede definir requisitos API"),
            ("select_productive_partner", "Puede seleccionar contraparte productiva"),
            ("close_api_section", "Puede cerrar una sección API"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["campus_career", "course", "semester", "name"],
                name="unique_api_section",
            )
        ]
        verbose_name = "sección API"
        verbose_name_plural = "secciones API"

    def __str__(self):
        return f"{self.campus_career} - {self.course.name} - {self.name} ({self.semester})"

    def clean(self):
        if not self.career_director_id:
            raise ValidationError("La sección debe tener un Director de Carrera asignado.")
        if self.status == self.Status.FINISHED and self.pk:
            pending_stages = self.stages.exclude(
                status__in=[ProcessStage.Status.APPROVED, ProcessStage.Status.FINISHED]
            ).exists()
            if pending_stages:
                raise ValidationError("No se puede cerrar una sección con etapas pendientes.")


#representa una etapa del flujo de trabajo de una sección API
# y permite controlar su avance, responsables y fechas límite.
class ProcessStage(TimeStampedModel):
    class StageType(models.TextChoices):
        REQUIREMENTS = "Requisitos Académicos", "Requisitos Académicos"
        COMPANY_PROPOSAL = "Objetivos VcM", "Objetivos VcM"
        PROJECT_PROPOSAL = "Identificación de Posibles Contrapartes", "Identificación de Posibles Contrapartes"
        DOCUMENT_VALIDATION = "Selección de Contraparte Definitiva", "Selección de Contraparte Definitiva"
        FOLLOW_UP = "Formulación del Proyecto", "Formulación del Proyecto"
        CTP_VALIDATION = "Validación CTP", "Validación CTP"
        VISITS = "Registro de Visitas", "Registro de Visitas"
        FINAL_DELIVERY = "Entrega del Proyecto Final", "Entrega del Proyecto Final"
        CLOSURE = "Acta de Cierre", "Acta de Cierre"

    class Status(models.TextChoices):
        PENDING = "Pendiente", "Pendiente"
        IN_PROGRESS = "En proceso", "En proceso"
        APPROVED = "Aprobada", "Aprobada"
        REJECTED = "Rechazada", "Rechazada"
        DELAYED = "Retrasada", "Retrasada"
        FINISHED = "Finalizada", "Finalizada"

    section = models.ForeignKey(APISection, on_delete=models.CASCADE, related_name="stages")
    stage_type = models.CharField(max_length=60, choices=StageType.choices)
    order = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(9)]
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    review_details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["section", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "order"],
                name="unique_stage_order_by_section",
            ),
            models.UniqueConstraint(
                fields=["section", "stage_type"],
                name="unique_stage_type_by_section",
            ),
        ]
        verbose_name = "etapa"
        verbose_name_plural = "etapas"

    def __str__(self):
        return f"{self.section} - {self.get_stage_type_display()}"

    @property
    def responsible_role(self):
        if self.order == 5:
            return User.Role.DE
        if self.order == 6:
            return User.Role.CTP
        return User.Role.DC

    @property
    def responsible_user(self):
        if self.order == 5:
            return self.section.specialist_teacher
        if self.order == 6:
            return self.section.ctp_coordinator
        return self.section.career_director

    @property
    def responsible_user_id(self):
        if self.order == 5:
            return self.section.specialist_teacher_id
        if self.order == 6:
            return self.section.ctp_coordinator_id
        return self.section.career_director_id

    def get_responsible_role_display(self):
        return dict(User.Role.choices).get(self.responsible_role, self.responsible_role)

    def clean(self):
        if self.completed_at and self.status not in {self.Status.APPROVED, self.Status.FINISHED}:
            raise ValidationError("Solo las etapas aprobadas o finalizadas pueden tener fecha de cierre.")
        if self.status in {self.Status.APPROVED, self.Status.FINISHED} and self.pk:
            missing_documents = self.documents.exclude(status=Document.Status.APPROVED).exists()
            if missing_documents:
                raise ValidationError("No se puede cerrar una etapa sin todos sus documentos aprobados.")

    @property
    def is_overdue(self):
        return bool(
            self.due_date
            and self.status not in {self.Status.APPROVED, self.Status.FINISHED}
            and self.due_date < timezone.localdate()
        )


# Plantilla oficial compartida por todas las secciones para una etapa del ciclo.
class CycleTemplate(TimeStampedModel):
    stage_type = models.CharField(max_length=60, choices=ProcessStage.StageType.choices, unique=True)
    file = models.FileField(upload_to="cycle_templates/", validators=[validate_document_file])
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_cycle_templates",
    )

    class Meta:
        ordering = ["stage_type"]
        verbose_name = "plantilla del ciclo"
        verbose_name_plural = "plantillas del ciclo"

    def __str__(self):
        return self.get_stage_type_display()

    def clean(self):
        validate_document_file(self.file)


# representa una ficha o documento asociado a una etapa del proceso, cuya aprobación permite continuar con el flujo.
class Document(TimeStampedModel):
    class DocumentType(models.TextChoices):
        EXCEL = "Excel", "Excel"
        WORD = "Word", "Word"
        PDF = "PDF", "PDF"
        ZIP = "ZIP", "ZIP"
        OTHER = "Otro", "Otro"

    class Status(models.TextChoices):
        PENDING = "Pendiente", "Pendiente"
        UPLOADED = "Subido", "Subido"
        UNDER_REVIEW = "En revisión", "En revisión"
        APPROVED = "Aprobado", "Aprobado"
        REJECTED = "Rechazado", "Rechazado"
        REPLACED = "Reemplazado", "Reemplazado"

    stage = models.ForeignKey(ProcessStage, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=180)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    current_version = models.PositiveIntegerField(default=1)
    delivery_due_date = models.DateField(null=True, blank=True)
    review_due_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name="uploaded_api_documents")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name="reviewed_api_documents")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name="approved_api_documents")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    is_historical = models.BooleanField(default=False)

    class Meta:
        ordering = ["stage", "title"]
        permissions = [
            ("review_api_document", "Puede revisar documentos API"),
            ("download_api_document", "Puede descargar documentos API"),
        ]
        verbose_name = "documento"
        verbose_name_plural = "documentos"

    def __str__(self):
        return f"{self.title} v{self.current_version}"

    def clean(self):
        if self.delivery_due_date and self.review_due_date and self.review_due_date < self.delivery_due_date:
            raise ValidationError("La fecha de revisión no puede ser anterior a la fecha de entrega.")
        if self.pk and self.stage.status in {ProcessStage.Status.APPROVED, ProcessStage.Status.FINISHED} and self.status != self.Status.APPROVED:
            raise ValidationError("No se puede modificar un documento no aprobado dentro de una etapa cerrada.")


# representa las distintas versiones históricas de un documento y almacena los archivos subidos.
class DocumentVersion(TimeStampedModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="api_documents/%Y/%m/", validators=[validate_document_file])
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_api_document_versions",
    )

    class Meta:
        ordering = ["document", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="unique_document_version_number",
            )
        ]
        verbose_name = "versión de documento"
        verbose_name_plural = "versiones de documentos"

    def __str__(self):
        return f"{self.document.title} - versión {self.version_number}"

    def clean(self):
        validate_document_file(self.file)
        name = getattr(self.file, "name", "")
        extension = f".{name.rsplit('.', 1)[-1].lower()}" if "." in name else ""
        allowed_extensions = DOCUMENT_TYPE_EXTENSIONS.get(self.document.document_type, ALLOWED_DOCUMENT_EXTENSIONS)
        if extension not in allowed_extensions:
            raise ValidationError("La extension del archivo no coincide con el tipo de documento.")
        if self.document.stage.status in {ProcessStage.Status.APPROVED, ProcessStage.Status.FINISHED}:
            raise ValidationError("No se pueden agregar versiones a una etapa cerrada.")


# representa una visita asociada a una sección API y sirve como referencia para el seguimiento y el calendario institucional.
class Visit(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "Programada", "Programada"
        COMPLETED = "Realizada", "Realizada"
        CANCELLED = "Cancelada", "Cancelada"
        RESCHEDULED = "Reprogramada", "Reprogramada"
    
    section = models.ForeignKey(APISection, on_delete=models.CASCADE, related_name="visits")
    visit_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])
    scheduled_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)
    place = models.CharField(max_length=255, blank=True)
    assigned_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_api_visits",
    )
    class Meta:
        ordering = ["section", "visit_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "visit_number"],
                name="unique_visit_number_by_section",
            )
        ]
        verbose_name = "visita"
        verbose_name_plural = "visitas"

    def __str__(self):
        return f"Visita {self.visit_number} - {self.section}"


class CalendarEvent(TimeStampedModel):
    class Category(models.TextChoices):
        MEETING = "Reunión", "Reunión"
        DEADLINE = "Hito", "Hito"
        ACTIVITY = "Actividad", "Actividad"
        REVIEW = "Revisión", "Revisión"
        OTHER = "Otro", "Otro"

    title = models.CharField(max_length=180)
    event_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.ACTIVITY)
    section = models.ForeignKey(APISection, on_delete=models.CASCADE, null=True, blank=True, related_name="calendar_events")
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_calendar_events",
    )

    class Meta:
        ordering = ["event_date", "start_time", "title"]
        verbose_name = "evento de calendario"
        verbose_name_plural = "eventos de calendario"

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("La hora de término debe ser posterior a la hora de inicio.")

    def __str__(self):
        return f"{self.title} - {self.event_date}"

# representa una notificación generada por retrasos, documentos pendientes, visitas faltantes o incumplimientos del proceso.
class Alert(TimeStampedModel):
    class AlertType(models.TextChoices):
        PENDING_DOCUMENT = "Documento pendiente", "Documento pendiente"
        OVERDUE_STAGE = "Etapa vencido", "Etapa vencido"
        MISSING_VISIT = "Visita sin registrar", "Visita sin registrar"
        MISSING_EVALUATION = "Evaluación no realizada", "Evaluación no realizada"
        STAGE_DELAY = "Retraso en etapa", "Retraso en etapa"
        PENDING_APPROVAL = "Falta de aprobación", "Falta de aprobación"

    class Severity(models.TextChoices):
        GREEN = "Verde", "Verde"
        YELLOW = "Amarillo", "Amarillo"
        RED = "Rojo", "Rojo"

    section = models.ForeignKey(APISection, on_delete=models.CASCADE, related_name="alerts")
    stage = models.ForeignKey(
        ProcessStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    alert_type = models.CharField(max_length=60, choices=AlertType.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    title = models.CharField(max_length=180)
    message = models.TextField()
    due_date = models.DateField(null=True, blank=True)
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="api_alerts",
    )
    is_active = models.BooleanField(default=True)
    email_sent = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "alerta"
        verbose_name_plural = "alertas"

    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"


class AlertRead(TimeStampedModel):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name="read_receipts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="read_api_alerts")
    read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["alert", "user"], name="unique_alert_read_by_user")]
        verbose_name = "lectura de alerta"
        verbose_name_plural = "lecturas de alertas"


class CTPValidationReview(TimeStampedModel):
    class Result(models.TextChoices):
        PENDING = "pending", "Pendiente de revisión"
        APPROVED = "approved", "Aprobado"
        REJECTED = "rejected", "Rechazado"

    section = models.ForeignKey(APISection, on_delete=models.CASCADE, related_name="ctp_reviews")
    attempt = models.PositiveSmallIntegerField()
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="submitted_ctp_reviews")
    submitted_at = models.DateTimeField(default=timezone.now)
    result = models.CharField(max_length=12, choices=Result.choices, default=Result.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_ctp_reviews")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    error_stages = models.JSONField(default=list, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-attempt"]
        constraints = [models.UniqueConstraint(fields=["section", "attempt"], name="unique_ctp_review_attempt")]
        verbose_name = "revisión CTP"
        verbose_name_plural = "revisiones CTP"


class AuditLog(TimeStampedModel):
    class Action(models.TextChoices):
        SECTION_CREATED = "section_created", "Creación de sección"
        REQUIREMENTS_UPDATED = "requirements_updated", "Actualización de requisitos"
        PARTNER_PROPOSED = "partner_proposed", "Propuesta de empresa"
        PARTNER_SELECTED = "partner_selected", "Selección de empresa"
        STAGE_CHANGED = "stage_changed", "Cambio de etapa"
        DOCUMENT_UPLOADED = "document_uploaded", "Subida de documento"
        DOCUMENT_APPROVED = "document_approved", "Aprobación de documento"
        DOCUMENT_REJECTED = "document_rejected", "Rechazo de documento"
        DOCUMENT_DOWNLOADED = "document_downloaded", "Descarga de documento"
        DOCUMENT_DELETED = "document_deleted", "Eliminación de archivo"
        SECTION_CLOSED = "section_closed", "Cierre de sección"
        ADMIN_CREATED = "admin_created", "Registro administrativo creado"
        ADMIN_UPDATED = "admin_updated", "Registro administrativo editado"
        ADMIN_TOGGLED = "admin_toggled", "Registro administrativo activado o desactivado"
        ADMIN_DELETED = "admin_deleted", "Registro administrativo eliminado"
        CALENDAR_CREATED = "calendar_created", "Evento de calendario creado"
        CALENDAR_UPDATED = "calendar_updated", "Evento de calendario editado"
        CALENDAR_DELETED = "calendar_deleted", "Evento de calendario eliminado"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="api_audit_logs",
    )
    section = models.ForeignKey(APISection, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    stage = models.ForeignKey(ProcessStage, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=40, choices=Action.choices)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self):
        return f"{self.get_action_display()} - {self.created_at:%Y-%m-%d %H:%M}"






