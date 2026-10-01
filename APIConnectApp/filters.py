from .models import APISection, Alert, Document, ProcessStage, ProductivePartner, Visit
from .permissions import can_access_campus, has_role, ADMIN_ROLES


def _valid_id(value):
    return not value or str(value).isdigit()


def active_sections_queryset():
    return APISection.objects.select_related(
        "campus_career__campus",
        "campus_career__career",
        "course",
        "semester",
        "career_director",
        "specialist_teacher",
        "ctp_coordinator",
        "productive_partner",
    ).exclude(status=APISection.Status.SUSPENDED).exclude(productive_partner__status=ProductivePartner.Status.INACTIVE).filter(
        campus_career__is_active=True,
        campus_career__campus__is_active=True,
        campus_career__career__is_active=True,
        course__is_active=True,
        semester__is_active=True,
    )


# Devuelve solo las secciones visibles para el usuario segun rol y sedes asignadas.
def sections_for_user(user):
    queryset = active_sections_queryset()
    if has_role(user, ADMIN_ROLES):
        return queryset
    campus_ids = list(
        user.campus_access.filter(is_active=True, campus__is_active=True).values_list("campus_id", flat=True)
    )
    return queryset.filter(campus_career__campus_id__in=campus_ids) if campus_ids else queryset


# Aplica filtros simples enviados por query params a las secciones API.
def apply_section_filters(queryset, params):
    campus_id = params.get("campus")
    career_id = params.get("career")
    course_id = params.get("course")
    semester_id = params.get("semester")
    status = params.get("status")
    search = params.get("search")

    if not all(_valid_id(value) for value in [campus_id, career_id, course_id, semester_id]):
        return queryset.none()

    if campus_id:
        queryset = queryset.filter(campus_career__campus_id=campus_id)
    if career_id:
        queryset = queryset.filter(campus_career__career_id=career_id)
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    if semester_id:
        queryset = queryset.filter(semester_id=semester_id)
    if status:
        queryset = queryset.filter(status=status)
    if search:
        queryset = queryset.filter(name__icontains=search) | queryset.filter(course__name__icontains=search)
    return queryset


# Devuelve etapas de una seccion solo si el usuario puede acceder a su sede.
def stages_for_section(section, user):
    if not can_access_campus(user, section.campus_career.campus):
        return ProcessStage.objects.none()
    return section.stages.select_related(
        "section__career_director", "section__specialist_teacher", "section__ctp_coordinator"
    )


# Devuelve documentos disponibles para el usuario segun sus secciones visibles.
def documents_for_user(user):
    return Document.objects.select_related("stage", "stage__section", "uploaded_by", "reviewed_by", "approved_by").filter(
        stage__section__in=sections_for_user(user)
    )


# Devuelve visitas disponibles para el usuario segun sus secciones visibles.
def visits_for_user(user):
    return Visit.objects.select_related("section").filter(section__in=sections_for_user(user))


# Devuelve alertas disponibles para el usuario segun sus secciones visibles.
def alerts_for_user(user):
    return Alert.objects.select_related("section", "stage").prefetch_related("recipients").filter(section__in=sections_for_user(user))
