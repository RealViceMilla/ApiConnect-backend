from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def expand_cycle(apps, schema_editor):
    APISection = apps.get_model("APIConnectApp", "APISection")
    ProcessStage = apps.get_model("APIConnectApp", "ProcessStage")
    Document = apps.get_model("APIConnectApp", "Document")
    CycleTemplate = apps.get_model("APIConnectApp", "CycleTemplate")

    ProcessStage.objects.filter(order=6).update(order=9, stage_type="Acta de Cierre", responsible_role="CTP")
    CycleTemplate.objects.filter(stage_type="Cierre").update(stage_type="Acta de Cierre")
    today = timezone.localdate()
    for section in APISection.objects.all():
        ProcessStage.objects.get_or_create(section=section, order=6, defaults={"stage_type": "Validación CTP", "responsible_role": "CTP", "due_date": today + timedelta(days=42)})
        ProcessStage.objects.get_or_create(section=section, order=7, defaults={"stage_type": "Registro de Visitas", "responsible_role": "DC", "due_date": today + timedelta(days=49)})
        stage8, _ = ProcessStage.objects.get_or_create(section=section, order=8, defaults={"stage_type": "Entrega del Proyecto Final", "responsible_role": "DC", "due_date": today + timedelta(days=56)})
        Document.objects.get_or_create(stage=stage8, title="Entrega del proyecto final", defaults={"document_type": "Excel"})


def contract_cycle(apps, schema_editor):
    ProcessStage = apps.get_model("APIConnectApp", "ProcessStage")
    CycleTemplate = apps.get_model("APIConnectApp", "CycleTemplate")
    ProcessStage.objects.filter(order__in=[6, 7, 8]).delete()
    ProcessStage.objects.filter(order=9).update(order=6, stage_type="Cierre", responsible_role="CTP")
    CycleTemplate.objects.filter(stage_type="Acta de Cierre").update(stage_type="Cierre")


class Migration(migrations.Migration):
    dependencies = [("APIConnectApp", "0007_processstage_feedback_processstage_review_details_and_more")]
    operations = [migrations.RunPython(expand_cycle, contract_cycle)]
