from django.db import migrations


EVENTS = [
    # (code, label, description, audience, order)
    ("devis.relanced", "Devis relancé par la structure",
     "Une structure est revenue vers le patient au sujet de son devis (relance).",
     "patient", 64),
    ("rdv.reminder", "Rappel de RDV (J-1)",
     "Rappel automatique envoyé au patient la veille de son rendez-vous confirmé.",
     "patient", 65),
]


TEMPLATES = {
    "devis.relanced": {
        "in_app": (
            "{{ organisme.name }} a relancé votre devis — {{ devis.reference }}",
            "{{ organisme.name }} est revenue vers vous concernant votre devis "
            "{{ devis.reference }}. Consultez-le pour prendre rendez-vous.",
        ),
    },
    "rdv.reminder": {
        "in_app": (
            "Rappel — RDV demain chez {{ organisme.name }}",
            "Votre rendez-vous {{ rdv.reference }} est prévu le "
            "{{ rdv.start|date:'d/m/Y à H:i' }} chez {{ organisme.name }}.",
        ),
        # Dormant : ne part qu'une fois WhatsApp Cloud activé par l'admin.
        "whatsapp_cloud": (
            "",
            "Rappel MedCare : votre RDV chez {{ organisme.name }} est prévu le "
            "{{ rdv.start|date:'d/m/Y à H:i' }}. Réf. {{ rdv.reference }}.",
        ),
    },
}

# Templates WhatsApp ajoutés à des événements déjà seedés (rdv.confirmed).
EXTRA_TEMPLATES = {
    "rdv.confirmed": {
        "whatsapp_cloud": (
            "",
            "MedCare : {{ organisme.name }} a confirmé votre rendez-vous du "
            "{{ rdv.start|date:'d/m/Y à H:i' }}. Réf. {{ rdv.reference }}.",
        ),
    },
}


RULES = [
    # event_code, channel_code, target_roles, notify_event_actor, extra_emails, is_active
    ("devis.relanced", "in_app", [], True, "", True),
    ("rdv.reminder", "in_app", [], True, "", True),
    # Règles WhatsApp préparées mais inactives par défaut (s'activent en admin).
    ("rdv.reminder", "whatsapp_cloud", [], True, "", False),
    ("rdv.confirmed", "whatsapp_cloud", [], True, "", False),
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

    # Événements préexistants ciblés par EXTRA_TEMPLATES.
    for code in EXTRA_TEMPLATES:
        ev = Event.objects.filter(code=code).first()
        if ev:
            event_by_code[code] = ev

    all_templates = {}
    for ev_code, by_chan in TEMPLATES.items():
        all_templates.setdefault(ev_code, {}).update(by_chan)
    for ev_code, by_chan in EXTRA_TEMPLATES.items():
        all_templates.setdefault(ev_code, {}).update(by_chan)

    for ev_code, by_chan in all_templates.items():
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

    for ev_code, chan_code, roles, notify_actor, extra, active in RULES:
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
                "is_active": active,
            },
        )


def unseed(apps, schema_editor):
    Event = apps.get_model("notifications", "NotificationEvent")
    Event.objects.filter(code__in=[e[0] for e in EVENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0009_rdv_events"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
