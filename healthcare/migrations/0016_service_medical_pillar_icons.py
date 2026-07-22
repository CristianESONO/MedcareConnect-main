# Generated manually — icônes piliers (familles de soins)

from django.db import migrations

from healthcare.service_icons import icons_for_pillars_data


def set_pillar_icons(apps, schema_editor):
    ServiceMedical = apps.get_model("healthcare", "ServiceMedical")
    for name, icon in icons_for_pillars_data():
        ServiceMedical.objects.filter(name=name).update(icon=icon)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("healthcare", "0015_organismo_catalogue_assurances_text"),
    ]

    operations = [
        migrations.RunPython(set_pillar_icons, noop_reverse),
    ]
