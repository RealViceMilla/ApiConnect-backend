from django.db import migrations


NEW_STAGES = {
    1: ("Requisitos Académicos", "DC", "Ficha de requisitos académicos"),
    2: ("Objetivos VcM", "DC", "Ficha de objetivos VcM"),
    3: ("Identificación de Posibles Contrapartes", "DC", "Ficha de posibles contrapartes"),
    4: ("Selección de Contraparte Definitiva", "DC", "Ficha de selección de contraparte"),
    5: ("Formulación del Proyecto", "DE", "Ficha de formulación del proyecto"),
    6: ("Cierre", "CTP", "Acta de cierre"),
}

OLD_TYPES = {
    1: "Definición de requerimientos",
    2: "Propuesta de empresa",
    3: "Propuesta de proyecto",
    4: "Validación documental",
    5: "Seguimiento y visitas",
    6: "Cierre",
}


def update_cycle(apps, schema_editor):
    ProcessStage = apps.get_model("APIConnectApp", "ProcessStage")
    CycleTemplate = apps.get_model("APIConnectApp", "CycleTemplate")
    Document = apps.get_model("APIConnectApp", "Document")

    for order, (stage_type, role, document_title) in NEW_STAGES.items():
        old_type = OLD_TYPES[order]
        ProcessStage.objects.filter(order=order).update(stage_type=stage_type, responsible_role=role)
        CycleTemplate.objects.filter(stage_type=old_type).update(stage_type=stage_type)
        Document.objects.filter(stage__order=order).update(title=document_title)


def restore_cycle(apps, schema_editor):
    ProcessStage = apps.get_model("APIConnectApp", "ProcessStage")
    CycleTemplate = apps.get_model("APIConnectApp", "CycleTemplate")
    Document = apps.get_model("APIConnectApp", "Document")
    old_roles = {1: "DC", 2: "D_VCM", 3: "DC", 4: "CTP", 5: "C_API", 6: "CTP"}
    old_titles = {
        1: "Ficha de requerimientos", 2: "Propuesta de contraparte", 3: "Propuesta de proyecto",
        4: "Validacion documental", 5: "Registro de seguimiento", 6: "Acta de cierre",
    }
    for order, (new_type, _, _) in NEW_STAGES.items():
        old_type = OLD_TYPES[order]
        ProcessStage.objects.filter(order=order).update(stage_type=old_type, responsible_role=old_roles[order])
        CycleTemplate.objects.filter(stage_type=new_type).update(stage_type=old_type)
        Document.objects.filter(stage__order=order).update(title=old_titles[order])


class Migration(migrations.Migration):
    dependencies = [("APIConnectApp", "0005_alter_cycletemplate_stage_type_and_more")]

    operations = [migrations.RunPython(update_cycle, restore_cycle)]
