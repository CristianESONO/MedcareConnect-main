# Mise à jour des textes devis.created (sous-devis + lien structure)

from django.db import migrations


def forwards(apps, schema_editor):
    NotificationEvent = apps.get_model("notifications", "NotificationEvent")
    NotificationChannel = apps.get_model("notifications", "NotificationChannel")
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    try:
        ev = NotificationEvent.objects.get(code="devis.created")
    except NotificationEvent.DoesNotExist:
        return
    ch = NotificationChannel.objects.filter(code="in_app").first()
    if not ch:
        return
    tpl = NotificationTemplate.objects.filter(event=ev, channel=ch).first()
    if not tpl:
        return
    tpl.subject = "Nouveau sous-devis #{{ devis_part.reference|default:devis.reference }}"
    tpl.body = (
        "Sous-devis {% if devis_part %}{{ devis_part.reference }}{% else %}{{ devis.reference }}{% endif %} "
        "(devis patient {{ devis.reference }}) pour {{ patient.display_name|default:patient.username }}"
        "{% if organisme %} — {{ organisme.name }}{% endif %}. "
        "Montant part structure : {% if devis_part %}{{ devis_part.total_brut }}{% else %}{{ devis.total_brut }}{% endif %} FCFA."
    )
    tpl.save(update_fields=["subject", "body"])


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_organisme_rejected_notify"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
