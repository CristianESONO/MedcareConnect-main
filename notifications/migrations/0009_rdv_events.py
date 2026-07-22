from django.db import migrations


EVENTS = [
    # (code, label, description, audience, order)
    ("rdv.requested", "Nouvelle demande de RDV",
     "Un patient a demandé un rendez-vous (créneau à confirmer).", "prestataire", 60),
    ("rdv.confirmed", "RDV confirmé",
     "La structure a confirmé le créneau demandé par le patient.", "patient", 61),
    ("rdv.declined", "RDV refusé",
     "La structure n'a pas pu retenir le créneau demandé.", "patient", 62),
    ("rdv.cancelled", "RDV annulé",
     "Un rendez-vous a été annulé (par le patient ou la structure).", "mixed", 63),
]


TEMPLATES = {
    "rdv.requested": {
        "in_app": (
            "Nouvelle demande de RDV — {{ rdv.reference }}",
            "{{ patient.display_name|default:patient.username }} demande un RDV le "
            "{{ rdv.start|date:'d/m/Y à H:i' }}. À confirmer dans votre agenda.",
        ),
        "email": (
            "[MedCare] Nouvelle demande de RDV — {{ rdv.reference }}",
            "Bonjour,\n\n{{ patient.display_name|default:patient.username }} demande un "
            "rendez-vous le {{ rdv.start|date:'d/m/Y à H:i' }} pour {{ organisme.name }}.\n"
            "Référence : {{ rdv.reference }}\n\n"
            "Confirmez ou refusez depuis votre espace pro (Agenda / RDV).\n",
        ),
    },
    "rdv.confirmed": {
        "in_app": (
            "RDV confirmé — {{ rdv.reference }}",
            "{{ organisme.name }} a confirmé votre rendez-vous du "
            "{{ rdv.start|date:'d/m/Y à H:i' }}.",
        ),
    },
    "rdv.declined": {
        "in_app": (
            "RDV non retenu — {{ rdv.reference }}",
            "{{ organisme.name }} n'a pas pu retenir le créneau du "
            "{{ rdv.start|date:'d/m/Y à H:i' }}. Vous pouvez proposer un autre créneau.",
        ),
    },
    "rdv.cancelled": {
        "in_app": (
            "RDV annulé — {{ rdv.reference }}",
            "Le rendez-vous du {{ rdv.start|date:'d/m/Y à H:i' }} ({{ organisme.name }}) "
            "a été annulé.",
        ),
    },
}


RULES = [
    # event_code, channel_code, target_roles, notify_event_actor, extra_emails
    ("rdv.requested", "in_app", [], True, ""),
    ("rdv.confirmed", "in_app", [], True, ""),
    ("rdv.declined", "in_app", [], True, ""),
    ("rdv.cancelled", "in_app", [], True, ""),
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
        ("notifications", "0008_google_reviews_url_setting"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
