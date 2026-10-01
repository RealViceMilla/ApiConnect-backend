from django.db import migrations


TITLE_CORRECTIONS = {
    "Ficha de requisitos acadÃ©micos": "Ficha de requisitos académicos",
    "Ficha de selecciÃ³n de contraparte": "Ficha de selección de contraparte",
    "Ficha de formulaciÃ³n del proyecto": "Ficha de formulación del proyecto",
}


def fix_document_titles(apps, schema_editor):
    Document = apps.get_model("APIConnectApp", "Document")
    for damaged_title, corrected_title in TITLE_CORRECTIONS.items():
        Document.objects.filter(title=damaged_title).update(title=corrected_title)


def restore_document_titles(apps, schema_editor):
    Document = apps.get_model("APIConnectApp", "Document")
    for damaged_title, corrected_title in TITLE_CORRECTIONS.items():
        Document.objects.filter(title=corrected_title).update(title=damaged_title)


class Migration(migrations.Migration):
    dependencies = [
        ("APIConnectApp", "0013_alter_auditlog_action_alter_auditlog_section"),
    ]

    operations = [
        migrations.RunPython(fix_document_titles, restore_document_titles),
    ]
