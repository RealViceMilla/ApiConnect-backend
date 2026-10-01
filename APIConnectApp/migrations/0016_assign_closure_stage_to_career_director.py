from django.db import migrations


def assign_closure_to_career_director(apps, schema_editor):
    ProcessStage = apps.get_model("APIConnectApp", "ProcessStage")
    for stage in ProcessStage.objects.filter(order=9).select_related("section"):
        stage.responsible_role = "DC"
        stage.responsible_user_id = stage.section.career_director_id
        stage.save(update_fields=["responsible_role", "responsible_user"])


def restore_closure_to_ctp(apps, schema_editor):
    ProcessStage = apps.get_model("APIConnectApp", "ProcessStage")
    ProcessStage.objects.filter(order=9).update(responsible_role="CTP", responsible_user=None)


class Migration(migrations.Migration):
    dependencies = [
        ("APIConnectApp", "0015_alter_auditlog_action_document_deleted"),
    ]

    operations = [
        migrations.RunPython(assign_closure_to_career_director, restore_closure_to_ctp),
    ]
