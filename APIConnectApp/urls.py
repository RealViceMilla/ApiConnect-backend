from django.urls import path

from . import views

app_name = "api_connect"

# Rutas JSON usadas por el backend BPM de ConectaAPI.
urlpatterns = [
    path("auth/csrf/", views.csrf_token, name="csrf-token"),
    path("auth/login/", views.login_view, name="login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/me/", views.me_view, name="me"),
    path("health/", views.health_check, name="health-check"),
    path("notifications/", views.notification_list, name="notification-list"),
    path("notifications/<int:alert_id>/read/", views.notification_read, name="notification-read"),
    path("administration/options/", views.administration_options, name="administration-options"),
    path("administration/counts/", views.administration_counts, name="administration-counts"),
    path("administration/templates/", views.cycle_template_collection, name="cycle-template-collection"),
    path("administration/templates/<int:template_id>/", views.cycle_template_detail, name="cycle-template-detail"),
    path("administration/sections/import/", views.section_bulk_import, name="section-bulk-import"),
    path("administration/sections/export/", views.section_bulk_export, name="section-bulk-export"),
    path("templates/<int:template_id>/download/", views.cycle_template_download, name="cycle-template-download"),
    path("administration/<str:resource>/", views.administration_collection, name="administration-collection"),
    path("administration/<str:resource>/<int:object_id>/", views.administration_detail, name="administration-detail"),
    path("sections/", views.section_list, name="section-list"),
    path("sections/filter-options/", views.section_filter_options, name="section-filter-options"),
    path("sections/<int:section_id>/", views.section_detail, name="section-detail"),
    path("sections/<int:section_id>/cycle-download/", views.section_cycle_download, name="section-cycle-download"),
    path("sections/<int:section_id>/closure-certificate/", views.section_closure_certificate, name="section-closure-certificate"),
    path("sections/<int:section_id>/requirements/", views.section_requirements_update, name="section-requirements-update"),
    path("sections/<int:section_id>/partners/propose/", views.section_partner_propose, name="section-partner-propose"),
    path("sections/<int:section_id>/partners/select/", views.section_partner_select, name="section-partner-select"),
    path("sections/<int:section_id>/stages/", views.section_stages, name="section-stages"),
    path("sections/<int:section_id>/visits/", views.section_visits, name="section-visits"),
    path("calendar/events/", views.calendar_event_list, name="calendar-event-list"),
    path("calendar/events/<str:event_id>/", views.calendar_event_update, name="calendar-event-update"),
    path("calendar/visits/", views.calendar_visit_create, name="calendar-visit-create"),
    path("stages/<int:stage_id>/advance/", views.stage_advance, name="stage-advance"),
    path("stages/<int:stage_id>/formulation-decision/", views.stage_five_decision, name="stage-five-decision"),
    path("stages/<int:stage_id>/formulation-zip/", views.stage_formulation_zip, name="stage-formulation-zip"),
    path("stages/<int:stage_id>/validation-zip/", views.stage_validation_zip, name="stage-validation-zip"),
    path("stages/<int:stage_id>/initial-documents-excel/", views.stage_initial_documents_excel, name="stage-initial-documents-excel"),
    path("stages/<int:stage_id>/validation-decision/", views.stage_six_decision, name="stage-six-decision"),
    path("documents/", views.document_list, name="document-list"),
    path("documents/<int:document_id>/upload/", views.document_upload, name="document-upload"),
    path("documents/<int:document_id>/review/", views.document_review, name="document-review"),
    path("documents/versions/<int:version_id>/", views.document_version_delete, name="document-version-delete"),
    path("documents/versions/<int:version_id>/preview/", views.document_version_preview, name="document-version-preview"),
    path("documents/versions/<int:version_id>/download/", views.document_download, name="document-download"),
    path("alerts/", views.alert_list, name="alert-list"),
    path("alerts/generate/", views.alert_generate, name="alert-generate"),
]



