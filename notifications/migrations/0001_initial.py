import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


CHANNELS = [
    ("in_app", "Notification dans l'app", "S'affiche dans la cloche / cloche utilisateur.", True, False, 10),
    ("email", "Email", "Envoi via SMTP (configurable dans Réglages notifications).", True, True, 20),
    ("whatsapp_cloud", "WhatsApp (Cloud API)", "Envoi via l'API WhatsApp Cloud officielle.", True, True, 30),
]


EVENTS = [
    # (code, label, description, audience, order)
    ("devis.created", "Nouveau devis WhatsApp", "Un patient vient de générer un devis.", "mixed", 10),
    ("subscription.requested", "Demande de changement de formule", "Une structure a demandé un changement d'abonnement.", "admin", 20),
    ("subscription.approved", "Changement de formule approuvé", "L'équipe a appliqué une nouvelle formule à une structure.", "prestataire", 21),
    ("subscription.rejected", "Demande de changement refusée", "L'équipe a refusé une demande de changement.", "prestataire", 22),
    ("organisme.created", "Nouvelle structure inscrite", "Un prestataire vient de créer sa fiche.", "admin", 30),
    ("organisme.approved", "Structure activée", "L'équipe MedCare a activé la fiche.", "prestataire", 31),
    ("organisme.rejected", "Structure refusée / désactivée", "L'équipe a désactivé la fiche.", "prestataire", 32),
    ("review.posted", "Nouvel avis patient", "Un patient a déposé un avis.", "mixed", 40),
    ("review.approved", "Avis publié", "L'équipe a approuvé un avis patient.", "prestataire", 41),
    ("acte.disabled", "Acte désactivé par une structure", "Pour suivi qualité côté équipe ops.", "admin", 50),
]


TEMPLATES = {
    # event_code: { channel_code: (subject, body) }
    "devis.created": {
        "in_app": (
            "Nouveau devis #{{ devis.reference }}",
            "Devis {{ devis.reference }} généré pour {{ patient.display_name|default:patient.username }}{% if organisme %} – concerne {{ organisme.name }}{% endif %}.",
        ),
        "email": (
            "[MedCare] Nouveau devis #{{ devis.reference }}",
            "Bonjour,\n\nUn nouveau devis vient d'être généré ({{ devis.reference }}).\n"
            "Patient : {{ patient.display_name|default:patient.username }}\n"
            "Total brut : {{ devis.total_brut }} FCFA\n\n"
            "Lien d'administration : /admin/cart/devis/{{ devis.id }}/change/\n",
        ),
        "whatsapp_cloud": (
            "",
            "Bonjour, un nouveau devis MedCare ({{ devis.reference }}) vient d'être généré pour {{ patient.display_name|default:patient.username }}. Connectez-vous à votre espace MedCare.",
        ),
    },
    "subscription.requested": {
        "in_app": (
            "Demande de changement de formule",
            "{{ organisme.name }} demande à passer en formule {{ requested_plan.name }}.",
        ),
        "email": (
            "[MedCare] Demande d'abonnement — {{ organisme.name }}",
            "Bonjour,\n\nLa structure {{ organisme.name }} demande le passage à la formule {{ requested_plan.name }}.\n"
            "Formule actuelle : {{ previous_plan.name|default:'(aucune)' }}\n"
            "Message : {{ message_from_structure|default:'(aucun)' }}\n\n"
            "À traiter dans /admin/healthcare/subscriptionchangerequest/\n",
        ),
    },
    "subscription.approved": {
        "in_app": (
            "Votre formule est validée",
            "Vous êtes désormais en formule {{ requested_plan.name }}.",
        ),
        "email": (
            "[MedCare] Votre nouvelle formule est active",
            "Bonjour,\n\nVotre demande a été approuvée. Vous êtes maintenant en formule {{ requested_plan.name }}.\n"
            "Bonne continuation,\nL'équipe MedCare\n",
        ),
    },
    "subscription.rejected": {
        "in_app": (
            "Demande d'abonnement refusée",
            "Votre demande pour {{ requested_plan.name }} n'a pas été retenue. {% if staff_note %}Note : {{ staff_note }}{% endif %}",
        ),
        "email": (
            "[MedCare] Demande d'abonnement refusée",
            "Bonjour,\n\nVotre demande pour {{ requested_plan.name }} n'a pas été retenue.\n"
            "{% if staff_note %}Note de l'équipe : {{ staff_note }}{% endif %}\n",
        ),
    },
    "organisme.created": {
        "in_app": (
            "Nouvelle structure à valider",
            "{{ organisme.name }} ({{ organisme.city }}) vient de créer sa fiche.",
        ),
        "email": (
            "[MedCare] Nouvelle structure à valider — {{ organisme.name }}",
            "Bonjour,\n\nNouvelle inscription : {{ organisme.name }} ({{ organisme.type_organisme }}, {{ organisme.city }}).\n"
            "À valider dans /admin/healthcare/organismedesante/{{ organisme.id }}/change/\n",
        ),
    },
    "organisme.approved": {
        "in_app": (
            "Votre fiche est activée",
            "Bravo, votre fiche {{ organisme.name }} est désormais visible sur MedCare.",
        ),
        "email": (
            "[MedCare] Votre fiche est en ligne",
            "Bonjour,\n\nLa fiche {{ organisme.name }} est désormais active sur MedCare.\n",
        ),
    },
    "review.posted": {
        "in_app": (
            "Nouvel avis sur {{ organisme.name }}",
            "{{ patient.display_name|default:patient.username }} a laissé un avis ({{ review.rating }}/5).",
        ),
        "email": (
            "[MedCare] Nouvel avis — {{ organisme.name }}",
            "Bonjour,\n\nNouvel avis ({{ review.rating }}/5) sur {{ organisme.name }}.\n"
            "Commentaire : {{ review.comment|default:'(aucun)' }}\n",
        ),
    },
    "review.approved": {
        "in_app": (
            "Avis publié",
            "Un avis sur {{ organisme.name }} vient d'être validé par la modération.",
        ),
    },
    "acte.disabled": {
        "in_app": (
            "Acte désactivé",
            "{{ organisme.name }} a masqué l'acte « {{ acte.name }} ».",
        ),
    },
}


# Règles initiales : minimales, in-app uniquement (les autres canaux sont créés mais sans destinataires).
RULES_INITIAL = [
    # event_code, channel_code, target_roles, notify_event_actor, extra_emails
    ("devis.created", "in_app", ["admin"], True, ""),
    ("subscription.requested", "in_app", ["admin"], False, ""),
    ("subscription.approved", "in_app", [], True, ""),
    ("subscription.rejected", "in_app", [], True, ""),
    ("organisme.created", "in_app", ["admin"], False, ""),
    ("organisme.approved", "in_app", [], True, ""),
    ("review.posted", "in_app", ["admin"], True, ""),
    ("review.approved", "in_app", [], True, ""),
    ("acte.disabled", "in_app", ["admin"], False, ""),
]


def seed_notifications(apps, schema_editor):
    Channel = apps.get_model("notifications", "NotificationChannel")
    Event = apps.get_model("notifications", "NotificationEvent")
    Template = apps.get_model("notifications", "NotificationTemplate")
    Rule = apps.get_model("notifications", "NotificationRule")
    Settings = apps.get_model("notifications", "NotificationSettings")

    Settings.objects.get_or_create(pk=1)

    chan_by_code = {}
    for code, label, desc, enabled, ext, order in CHANNELS:
        c, _ = Channel.objects.update_or_create(
            code=code,
            defaults={
                "label": label,
                "description": desc,
                "is_enabled": enabled,
                "requires_external_config": ext,
                "order": order,
            },
        )
        chan_by_code[code] = c

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

    for ev_code, chan_code, roles, notify_actor, extra in RULES_INITIAL:
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


def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email_enabled", models.BooleanField(default=False, verbose_name="Activer l'envoi d'email")),
                ("smtp_host", models.CharField(blank=True, max_length=255)),
                ("smtp_port", models.PositiveIntegerField(default=587)),
                ("smtp_user", models.CharField(blank=True, max_length=255)),
                ("smtp_password", models.CharField(blank=True, max_length=255)),
                ("smtp_use_tls", models.BooleanField(default=True)),
                ("smtp_use_ssl", models.BooleanField(default=False)),
                ("smtp_from_email", models.EmailField(blank=True, max_length=254, verbose_name="Adresse expéditeur")),
                ("smtp_from_name", models.CharField(blank=True, max_length=255, verbose_name="Nom expéditeur")),
                ("smtp_reply_to", models.EmailField(blank=True, max_length=254, verbose_name="Reply-To")),
                ("whatsapp_enabled", models.BooleanField(default=False, verbose_name="Activer WhatsApp Cloud API")),
                ("wa_phone_number_id", models.CharField(blank=True, max_length=64, verbose_name="Phone number ID")),
                ("wa_business_account_id", models.CharField(blank=True, max_length=64, verbose_name="Business account ID")),
                ("wa_access_token", models.TextField(blank=True, verbose_name="Access token (permanent)")),
                ("wa_api_version", models.CharField(default="v20.0", max_length=10)),
                ("in_app_enabled", models.BooleanField(default=True, verbose_name="Activer notifications in-app")),
                ("log_retention_days", models.PositiveIntegerField(default=90, help_text="Durée de rétention des logs en jours.")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Réglages notifications", "verbose_name_plural": "Réglages notifications"},
        ),
        migrations.CreateModel(
            name="NotificationChannel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("is_enabled", models.BooleanField(default=True)),
                ("requires_external_config", models.BooleanField(default=False, help_text="Vrai si le canal dépend d'une configuration externe (SMTP, API…).")),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"verbose_name": "Canal de notification", "verbose_name_plural": "Canaux de notification", "ordering": ["order", "label"]},
        ),
        migrations.CreateModel(
            name="NotificationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=80, unique=True, help_text="Identifiant technique stable (ex. devis.created, subscription.requested).")),
                ("label", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("audience", models.CharField(choices=[("admin", "Équipe MedCare (admins)"), ("prestataire", "Structures / prestataires"), ("patient", "Patients"), ("mixed", "Mixte")], default="admin", help_text="Public principal de l'événement (sert au regroupement).", max_length=20)),
                ("sample_context", models.JSONField(blank=True, null=True, help_text="Exemple de variables disponibles dans le template (documentation).")),
                ("is_enabled", models.BooleanField(default=True)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"verbose_name": "Événement de notification", "verbose_name_plural": "Événements de notification", "ordering": ["order", "label"]},
        ),
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(blank=True, max_length=255, help_text="Sujet (email) ou titre (in-app).")),
                ("body", models.TextField(help_text="Corps du message — supporte la syntaxe Django.")),
                ("is_enabled", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="templates", to="notifications.notificationchannel")),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="templates", to="notifications.notificationevent")),
            ],
            options={"verbose_name": "Template de notification", "verbose_name_plural": "Templates de notification", "unique_together": {("event", "channel")}},
        ),
        migrations.CreateModel(
            name="NotificationRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_roles", models.JSONField(blank=True, default=list, help_text="Liste de rôles destinataires (admin / prestataire / patient).")),
                ("extra_emails", models.TextField(blank=True, help_text="Emails séparés par des virgules ou retours à la ligne.")),
                ("notify_event_actor", models.BooleanField(default=False, help_text="Notifie aussi l'acteur lié à l'événement (l'organisme / le patient concerné, selon le contexte fourni à dispatch()).")),
                ("is_active", models.BooleanField(default=True)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rules", to="notifications.notificationchannel")),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rules", to="notifications.notificationevent")),
                ("target_users", models.ManyToManyField(blank=True, help_text="Utilisateurs explicitement abonnés à cette règle.", related_name="subscribed_rules", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Règle de notification", "verbose_name_plural": "Règles de notification", "ordering": ["event__order", "event__label", "channel__order"], "unique_together": {("event", "channel")}},
        ),
        migrations.CreateModel(
            name="UserNotificationPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_preferences", to="notifications.notificationchannel")),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_preferences", to="notifications.notificationevent")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Préférence de notification", "verbose_name_plural": "Préférences de notification", "unique_together": {("user", "event", "channel")}},
        ),
        migrations.CreateModel(
            name="NotificationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_address", models.CharField(blank=True, max_length=255, help_text="Email ou numéro WhatsApp si pas de user lié.")),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("queued", "En file"), ("sent", "Envoyée"), ("failed", "Échec"), ("skipped", "Ignorée")], db_index=True, default="queued", max_length=20)),
                ("error", models.TextField(blank=True)),
                ("context_snapshot", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("channel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="logs", to="notifications.notificationchannel")),
                ("event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="logs", to="notifications.notificationevent")),
                ("recipient_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notification_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Journal d'envoi", "verbose_name_plural": "Journaux d'envoi", "ordering": ["-created_at"]},
        ),
        migrations.RunPython(seed_notifications, reverse_seed),
    ]
