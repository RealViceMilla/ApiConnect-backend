from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    APISection,
    Alert,
    AuditLog,
    CalendarEvent,
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


# Permite asignar sedes directamente desde la ficha del usuario.
class UserCampusInline(admin.TabularInline):
    model = UserCampus
    extra = 0
    autocomplete_fields = ("campus",)


# Extiende el admin de usuarios con rol institucional y sedes asociadas.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("ConectaAPI", {"fields": ("rol", "phone")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "roles_display", "is_staff", "is_active")
    list_filter = UserAdmin.list_filter + ("rol",)
    search_fields = ("username", "email", "first_name", "last_name")
    inlines = (UserCampusInline,)

    @admin.display(description="Roles")
    def roles_display(self, obj):
        roles = set(obj.groups.filter(name__in=User.Role.values).values_list("name", flat=True)) | {obj.rol}
        labels = dict(User.Role.choices)
        return ", ".join(labels[role] for role in sorted(roles))


# Administra las sedes institucionales.
@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


# Administra las carreras globales de la institucion.
@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


# Administra la relacion entre carreras y sedes.
@admin.register(CampusCareer)
class CampusCareerAdmin(admin.ModelAdmin):
    list_display = ("career", "campus", "is_active")
    list_filter = ("campus", "is_active")
    search_fields = ("career__code", "career__name", "campus__name")
    autocomplete_fields = ("campus", "career")


# Administra las asignaturas API disponibles.
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


# Administra los periodos academicos.
@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("period", "year", "is_active")
    list_filter = ("period", "year", "is_active")
    search_fields = ("period", "year")


# Administra empresas y contrapartes productivas.
@admin.register(ProductivePartner)
class ProductivePartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "rut", "business_area", "status", "contact_name", "contact_email")
    list_filter = ("status", "business_area")
    search_fields = ("name", "rut", "contact_name", "contact_email")
    autocomplete_fields = ("proposed_by",)


# Muestra las etapas BPM dentro de una seccion API.
class ProcessStageInline(admin.TabularInline):
    model = ProcessStage
    extra = 0
    fields = ("order", "stage_type", "status", "due_date")


# Muestra visitas referenciales dentro de una seccion API.
class VisitInline(admin.TabularInline):
    model = Visit
    extra = 0
    fields = ("visit_number", "scheduled_date", "place", "assigned_teacher", "status", "notes")
    autocomplete_fields = ("assigned_teacher",)


# Administra la entidad principal del flujo BPM academico.
@admin.register(APISection)
class APISectionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "course",
        "campus_career",
        "semester",
        "career_director",
        "productive_partner",
        "status",
    )
    list_filter = ("status", "semester", "campus_career__campus", "course")
    search_fields = (
        "name",
        "course__code",
        "course__name",
        "campus_career__career__name",
        "campus_career__campus__name",
        "productive_partner__name",
    )
    autocomplete_fields = ("campus_career", "course", "semester", "career_director", "specialist_teacher", "ctp_coordinator", "productive_partner")
    inlines = (ProcessStageInline, VisitInline)


# Muestra las versiones historicas dentro del documento logico.
class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    fields = ("version_number", "file", "uploaded_by", "notes", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("uploaded_by",)


# Administra las etapas del flujo de una seccion API.
@admin.register(ProcessStage)
class ProcessStageAdmin(admin.ModelAdmin):
    list_display = ("section", "order", "stage_type", "status", "due_date", "completed_at")
    list_filter = ("stage_type", "status", "due_date")
    search_fields = ("section__name", "section__course__name", "section__campus_career__career__name")
    autocomplete_fields = ("section",)


@admin.register(CycleTemplate)
class CycleTemplateAdmin(admin.ModelAdmin):
    list_display = ("stage_type", "uploaded_by", "updated_at")
    search_fields = ("stage_type", "notes")
    autocomplete_fields = ("uploaded_by",)


# Administra documentos logicos y sus versiones asociadas.
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "stage", "document_type", "status", "current_version", "delivery_due_date", "review_due_date")
    list_filter = ("document_type", "status", "is_historical", "delivery_due_date", "review_due_date")
    search_fields = ("title", "stage__section__name", "stage__section__course__name")
    autocomplete_fields = ("stage", "uploaded_by", "reviewed_by", "approved_by")
    inlines = (DocumentVersionInline,)


# Administra versiones fisicas de documentos.
@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version_number", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("document__title", "document__stage__section__name")
    autocomplete_fields = ("document", "uploaded_by")


# Administra visitas referenciales usadas por calendario y seguimiento.
@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("section", "visit_number", "scheduled_date", "place", "assigned_teacher", "status")
    list_filter = ("status", "scheduled_date")
    search_fields = ("section__name", "section__course__name", "notes")
    autocomplete_fields = ("section", "assigned_teacher")


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_date", "start_time", "category", "section", "created_by")
    list_filter = ("category", "event_date")
    search_fields = ("title", "description", "location", "section__name", "created_by__username")
    autocomplete_fields = ("section", "created_by")

# Administra alertas de vencimiento, documentos pendientes y visitas faltantes.
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "stage", "alert_type", "severity", "due_date", "is_active", "email_sent", "resolved_at")
    list_filter = ("alert_type", "severity", "is_active", "email_sent", "due_date")
    search_fields = ("title", "message", "section__name", "stage__stage_type")
    autocomplete_fields = ("section", "stage", "recipients")
    filter_horizontal = ("recipients",)


# Expone la auditoria en modo solo lectura para preservar trazabilidad.
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "section", "stage", "document", "ip_address", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "section__name", "document__title")
    autocomplete_fields = ("actor", "section", "stage", "document")
    readonly_fields = ("actor", "section", "stage", "document", "action", "metadata", "ip_address", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Administra la relacion usuario-sede que limita el acceso territorial.
@admin.register(UserCampus)
class UserCampusAdmin(admin.ModelAdmin):
    list_display = ("user", "campus", "is_active")
    list_filter = ("campus", "is_active")
    search_fields = ("user__username", "user__first_name", "user__last_name", "campus__name")
    autocomplete_fields = ("user", "campus")

