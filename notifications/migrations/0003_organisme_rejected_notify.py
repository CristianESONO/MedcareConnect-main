from django.db import migrations


def seed_organisme_rejected(apps, schema_editor):
    Event = apps.get_model("notifications", "NotificationEvent")
    Channel = apps.get_model("notifications", "NotificationChannel")
    Template = apps.get_model("notifications", "NotificationTemplate")
    Rule = apps.get_model("notifications", "NotificationRule")
    ev = Event.objects.filter(code="organisme.rejected").first()
    ch = Channel.objects.filter(code="in_app").first()
    if not ev or not ch:
        return
    Template.objects.update_or_create(
        event=ev,
        channel=ch,
        defaults={
            "subject": "Fiche désactivée",
            "body": (
                "Votre fiche « {{ organisme.name }} » n'est plus publiée sur MedCare. "
                "Pour toute question, contactez l'équipe MedCare."
            ),
            "is_enabled": True,
        },
    )
    Rule.objects.update_or_create(
        event=ev,
        channel=ch,
        defaults={
            "target_roles": [],
            "notify_event_actor": True,
            "extra_emails": "",
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_notificationsettings_patient_wa_me"),
    ]

    operations = [
        migrations.RunPython(seed_organisme_rejected, migrations.RunPython.noop),
    ]
