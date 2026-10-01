# Generated manually to remove the obsolete textual requirements field from APISection.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("APIConnectApp", "0016_assign_closure_stage_to_career_director"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="apisection",
            name="requirements",
        ),
    ]
