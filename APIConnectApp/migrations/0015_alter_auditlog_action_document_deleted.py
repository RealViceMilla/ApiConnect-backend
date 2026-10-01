from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("APIConnectApp", "0014_fix_document_title_encoding"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("section_created", "Creación de sección"),
                    ("requirements_updated", "Actualización de requisitos"),
                    ("partner_proposed", "Propuesta de empresa"),
                    ("partner_selected", "Selección de empresa"),
                    ("stage_changed", "Cambio de etapa"),
                    ("document_uploaded", "Subida de documento"),
                    ("document_approved", "Aprobación de documento"),
                    ("document_rejected", "Rechazo de documento"),
                    ("document_downloaded", "Descarga de documento"),
                    ("document_deleted", "Eliminación de archivo"),
                    ("section_closed", "Cierre de sección"),
                    ("admin_created", "Registro administrativo creado"),
                    ("admin_updated", "Registro administrativo editado"),
                    ("admin_toggled", "Registro administrativo activado o desactivado"),
                    ("admin_deleted", "Registro administrativo eliminado"),
                    ("calendar_created", "Evento de calendario creado"),
                    ("calendar_updated", "Evento de calendario editado"),
                    ("calendar_deleted", "Evento de calendario eliminado"),
                ],
                max_length=40,
            ),
        ),
    ]
