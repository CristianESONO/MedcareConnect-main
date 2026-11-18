from django.db import migrations


def remove_reseau(apps, schema_editor):
    from healthcare.subscription_admin import migrate_off_reseau_plan

    migrate_off_reseau_plan()


class Migration(migrations.Migration):

    dependencies = [
        ("healthcare", "0020_profileview_source"),
    ]

    operations = [
        migrations.RunPython(remove_reseau, migrations.RunPython.noop),
    ]
