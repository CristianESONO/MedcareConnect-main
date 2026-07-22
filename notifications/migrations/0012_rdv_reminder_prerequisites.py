from django.db import migrations

IN_APP_SUBJECT = (
    "Rappel — RDV chez {{ organisme.name }}"
    "{% if schedule_label %} ({{ schedule_label }}){% endif %}"
)

IN_APP_BODY = (
    "Votre rendez-vous {{ rdv.reference }} est prévu le "
    "{{ rdv.start|date:'d/m/Y à H:i' }} chez {{ organisme.name }}."
    "{% if prerequisites %}\n\n📋 Consignes importantes :\n{{ prerequisites }}"
    "{% endif %}"
)

WA_BODY = (
    "Rappel MedCare{% if schedule_label %} ({{ schedule_label }}){% endif %} : "
    "votre RDV chez {{ organisme.name }} est prévu le "
    "{{ rdv.start|date:'d/m/Y à H:i' }}. Réf. {{ rdv.reference }}."
    "{% if prerequisites %} Consignes : {{ prerequisites }}{% endif %}"
)


def update_templates(apps, schema_editor):
    Event = apps.get_model("notifications", "NotificationEvent")
    Template = apps.get_model("notifications", "NotificationTemplate")
    Channel = apps.get_model("notifications", "NotificationChannel")

    event = Event.objects.filter(code="rdv.reminder").first()
    if not event:
        return

    for chan_code, subject, body in (
        ("in_app", IN_APP_SUBJECT, IN_APP_BODY),
        ("whatsapp_cloud", "", WA_BODY),
    ):
        chan = Channel.objects.filter(code=chan_code).first()
        if not chan:
            continue
        Template.objects.update_or_create(
            event=event,
            channel=chan,
            defaults={"subject": subject, "body": body, "is_enabled": True},
        )

    Event.objects.filter(code="rdv.reminder").update(
        label="Rappel de RDV",
        description=(
            "Rappel automatique envoyé au patient avant son rendez-vous confirmé "
            "(délais configurables en admin)."
        ),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0011_rdv_rescheduled"),
        ("appointments", "0004_rdv_reminder_schedules"),
    ]

    operations = [
        migrations.RunPython(update_templates, migrations.RunPython.noop),
    ]
