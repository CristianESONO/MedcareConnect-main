from django.db import migrations


EVENTS = [
    (
        "rdv.rescheduled",
        "RDV déplacé",
        "Le créneau d'un rendez-vous a été modifié (patient ou structure).",
        "mixed",
        64,
    ),
]

TEMPLATES = {
    "rdv.rescheduled": {
        "in_app": (
            "RDV déplacé — {{ rdv.reference }}",
            "{% if organisme %}{{ organisme.name }} a déplacé votre rendez-vous au "
            "{{ rdv.start|date:'d/m/Y à H:i' }}.{% else %}"
            "{{ patient.display_name|default:patient.username }} a modifié le créneau au "
            "{{ rdv.start|date:'d/m/Y à H:i' }}.{% endif %}",
        ),
    },
}

RULES = [
    ("rdv.rescheduled", "in_app", [], True, ""),
]


def seed(apps, schema_editor):
    Channel = apps.get_model("notifications", "NotificationChannel")
    Event = apps.get_model("notifications", "NotificationEvent")
    Template = apps.get_model("notifications", "NotificationTemplate")
    Rule = apps.get_model("notifications", "NotificationRule")

    chan_by_code = {c.code: c for c in Channel.objects.all()}

    event_by_code = {}
    for code, label, desc, audience, order in EVENTS:
        e, _ = Event.objects.update_or_create(
            code=code,
            defaults={
                "label": label,
                "description": desc,
                "audience": audience,
                "is_enabled": True,
                "order": order,
            },
        )
        event_by_code[code] = e

    for ev_code, by_chan in TEMPLATES.items():
        ev = event_by_code.get(ev_code)
        if not ev:
            continue
        for chan_code, (subject, body) in by_chan.items():
            chan = chan_by_code.get(chan_code)
            if not chan:
                continue
            Template.objects.update_or_create(
                event=ev,
                channel=chan,
                defaults={"subject": subject, "body": body, "is_enabled": True},
            )

    for ev_code, chan_code, roles, notify_actor, extra in RULES:
        ev = event_by_code.get(ev_code)
        chan = chan_by_code.get(chan_code)
        if not ev or not chan:
            continue
        Rule.objects.update_or_create(
            event=ev,
            channel=chan,
            defaults={
                "target_roles": list(roles),
                "notify_event_actor": notify_actor,
                "extra_emails": extra,
                "is_active": True,
            },
        )


def unseed(apps, schema_editor):
    Event = apps.get_model("notifications", "NotificationEvent")
    Event.objects.filter(code__in=[e[0] for e in EVENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0010_relance_reminder_whatsapp"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
