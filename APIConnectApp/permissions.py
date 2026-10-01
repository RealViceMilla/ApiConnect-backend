from django.contrib.auth.models import AnonymousUser

from .models import APISection, ProductivePartner, User


# Roles base usados para separar permisos administrativos, academicos y de revision.
ADMIN_ROLES = {User.Role.ADMIN, User.Role.DA}
SECTION_MANAGER_ROLES = {User.Role.ADMIN, User.Role.DA, User.Role.DC}
DOCUMENT_REVIEW_ROLES = {User.Role.ADMIN, User.Role.DA, User.Role.CTP}
REQUIREMENTS_ROLES = {User.Role.ADMIN, User.Role.DA, User.Role.DC}
PARTNER_PROPOSAL_ROLES = {User.Role.ADMIN, User.Role.DA, User.Role.D_VCM}


# Verifica que el usuario exista, no sea anonimo y tenga sesion activa.
def is_authenticated(user):
    return bool(user and not isinstance(user, AnonymousUser) and user.is_authenticated and user.is_active)


# Obtiene el rol institucional guardado en el modelo User.
def user_roles(user):
    if not is_authenticated(user):
        return set()
    cached = getattr(user, "_api_connect_roles_cache", None)
    if cached is not None:
        return cached
    roles = set(user.groups.filter(name__in=User.Role.values).values_list("name", flat=True))
    legacy_role = getattr(user, "rol", None)
    if legacy_role in User.Role.values:
        roles.add(legacy_role)
    user._api_connect_roles_cache = roles
    return roles


def user_role(user):
    return getattr(user, "rol", None)


# Comprueba permisos segun el rol propio de ConectaAPI.
def has_role(user, roles):
    if not is_authenticated(user):
        return False
    role_set = set(roles)
    if getattr(user, "is_superuser", False) and User.Role.ADMIN in role_set:
        return True
    return bool(user_roles(user) & role_set)


# Comprueba permisos segun grupos nativos de Django.
def has_group(user, group_names):
    return is_authenticated(user) and user.groups.filter(name__in=set(group_names)).exists()


# Permite usar rol interno o Django Groups como fuentes validas de autorizacion.
def has_role_or_group(user, roles):
    return has_role(user, roles) or has_group(user, roles)


# Controla el acceso territorial mediante UserCampus.
def can_access_campus(user, campus):
    if not is_authenticated(user) or not campus or not campus.is_active:
        return False
    if has_role_or_group(user, ADMIN_ROLES):
        return True
    assigned_campuses = user.campus_access.filter(is_active=True, campus__is_active=True)
    return not assigned_campuses.exists() or assigned_campuses.filter(campus=campus).exists()


# Controla si un usuario puede ver una seccion API concreta.
def can_access_section(user, section: APISection):
    if not is_authenticated(user) or not section:
        return False
    if (
        section.status == APISection.Status.SUSPENDED
        or not section.campus_career.is_active
        or not section.campus_career.campus.is_active
        or not section.campus_career.career.is_active
        or not section.course.is_active
        or not section.semester.is_active
        or (section.productive_partner and section.productive_partner.status == ProductivePartner.Status.INACTIVE)
    ):
        return False
    if has_role_or_group(user, ADMIN_ROLES):
        return True
    if not can_access_campus(user, section.campus_career.campus):
        return False
    return True


# Permite administrar una seccion solo a roles directivos autorizados.
def can_manage_section(user, section=None):
    if not has_role_or_group(user, SECTION_MANAGER_ROLES):
        return False
    return section is None or can_access_section(user, section)


# Permite modificar una etapa solo si no esta cerrada y el usuario corresponde.
def can_manage_stage(user, stage):
    if not can_access_section(user, stage.section):
        return False
    if has_role_or_group(user, ADMIN_ROLES):
        return True
    if stage.status in {stage.Status.APPROVED, stage.Status.FINISHED}:
        return False
    return stage.responsible_user_id == user.id


# Permite subir documentos al responsable de la etapa.
def can_upload_document(user, document):
    stage = document.stage
    if not can_access_section(user, stage.section):
        return False
    if not stage.section.career_director_id:
        return False
    if has_role_or_group(user, {User.Role.ADMIN}):
        return True
    prefetched_stages = getattr(stage.section, "_prefetched_objects_cache", {}).get("stages")
    if prefetched_stages is None:
        previous_pending = stage.section.stages.filter(order__lt=stage.order).exclude(
            status__in={stage.Status.APPROVED, stage.Status.FINISHED}
        ).exists()
    else:
        previous_pending = any(
            item.order < stage.order
            and item.status not in {stage.Status.APPROVED, stage.Status.FINISHED}
            for item in prefetched_stages
        )
    if previous_pending:
        return False
    if stage.status in {stage.Status.APPROVED, stage.Status.FINISHED}:
        return False
    return stage.responsible_user_id == user.id


def can_manage_visits(user, section):
    return can_access_section(user, section) and has_role_or_group(
        user, {User.Role.ADMIN, User.Role.DC, User.Role.D_VCM}
    )


def can_advance_stage(user, stage):
    if not can_access_section(user, stage.section):
        return False
    if has_role_or_group(user, {User.Role.ADMIN}):
        return True
    return stage.responsible_user_id == user.id


# Permite revisar documentos solo a roles revisores y con acceso a la seccion.
def can_review_document(user, document):
    if can_access_section(user, document.stage.section) and has_role_or_group(user, {User.Role.ADMIN}):
        return True
    if document.stage.status in {document.stage.Status.APPROVED, document.stage.Status.FINISHED}:
        return False
    if document.stage.order == 5:
        return can_access_section(user, document.stage.section) and has_role_or_group(user, {User.Role.DC})
    return can_access_section(user, document.stage.section) and has_role_or_group(user, DOCUMENT_REVIEW_ROLES)


# Permite al DC y roles superiores definir requisitos de la seccion.
def can_define_requirements(user, section):
    return can_access_section(user, section) and has_role_or_group(user, REQUIREMENTS_ROLES)


# Permite al DVCM y roles superiores proponer empresas.
def can_propose_partner(user, section):
    return can_access_section(user, section) and has_role_or_group(user, PARTNER_PROPOSAL_ROLES)


# Permite al DC y roles superiores seleccionar la contraparte final.
def can_select_partner(user, section):
    return can_access_section(user, section) and has_role_or_group(user, REQUIREMENTS_ROLES)


# Protege la descarga de archivos con la misma regla territorial de la seccion.
def can_download_document(user, document):
    return can_access_section(user, document.stage.section)


