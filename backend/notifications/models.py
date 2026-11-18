from django.db import models
from django.utils import timezone

from users.models import User


# Texte par défaut : fiche devis patient → wa.me (sous-devis / structure).
PATIENT_WA_ME_DEVIS_FORMAL_DEFAULT = (
    "Bonjour,\n\n"
    "Je vous contacte via MedCare Connect au sujet du devis {{ devis.reference }} "
    "— sous-devis {{ devis_part.reference }} — pour {{ org.name }}.\n\n"
    "Examens demandés :\n"
    "{% for line in lines %}{{ line.line_display }}\n"
    "{% endfor %}\n"
    "Montant estimé à votre charge : {{ total_display }}.\n\n"
    "Pouvez-vous confirmer la faisabilité ainsi qu'un créneau disponible ?\n\n"
    "Merci."
)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration globale (singleton via pk=1)
# ─────────────────────────────────────────────────────────────────────────────


class NotificationSettings(models.Model):
    """Réglages globaux notifs : SMTP + WhatsApp Cloud API. Singleton (pk=1)."""

    # Email / SMTP
    email_enabled = models.BooleanField(default=False, verbose_name="Activer l'envoi d'email")
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_user = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)
    smtp_from_email = models.EmailField(blank=True, verbose_name="Adresse expéditeur")
    smtp_from_name = models.CharField(max_length=255, blank=True, verbose_name="Nom expéditeur")
    smtp_reply_to = models.EmailField(blank=True, verbose_name="Reply-To")

    # WhatsApp Cloud API (Meta)
    whatsapp_enabled = models.BooleanField(default=False, verbose_name="Activer WhatsApp Cloud API")
    wa_phone_number_id = models.CharField(max_length=64, blank=True, verbose_name="Phone number ID")
    wa_business_account_id = models.CharField(max_length=64, blank=True, verbose_name="Business account ID")
    wa_access_token = models.TextField(blank=True, verbose_name="Access token (permanent)")
    wa_api_version = models.CharField(max_length=10, default="v20.0")

    # Comportement général
    in_app_enabled = models.BooleanField(default=True, verbose_name="Activer notifications in-app")
    log_retention_days = models.PositiveIntegerField(
        default=90,
        help_text="Durée de rétention des logs en jours.",
    )

    google_reviews_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="URL « Avis Google » (patients)",
        help_text=(
            "Lien public vers votre fiche Google (avis). Affiché sur /healthcare/avis/google/. "
            "Si ce champ est vide, la variable d'environnement MEDCARE_GOOGLE_REVIEWS_URL est utilisée."
        ),
    )

    # Textes préremplis wa.me (patient → structure), éditables dans /notifications/admin/templates/
    patient_wa_me_message_general = models.TextField(
        default=(
            "Bonjour, je vous contacte via MedCare Connect. "
            "Je souhaite réserver un rendez-vous pour un examen."
        ),
        verbose_name="Message WhatsApp (contact général)",
        help_text=(
            "Bouton principal sur la fiche prestataire. Utilisez {{ org.name }} pour insérer le nom de l’établissement."
        ),
    )
    patient_wa_me_message_acte = models.TextField(
        default=(
            "Bonjour, je vous contacte via MedCare Connect. "
            "Je souhaite réserver un rendez-vous pour l'examen « {{ acte.name }} » "
            "(établissement « {{ org.name }} »)."
        ),
        verbose_name="Message WhatsApp (par examen)",
        help_text=(
            "Lien WhatsApp à côté de chaque acte. Ex. {{ acte.name }} pour l’examen, {{ org.name }} pour l’établissement."
        ),
    )
    patient_wa_me_message_devis_formal = models.TextField(
        default=PATIENT_WA_ME_DEVIS_FORMAL_DEFAULT,
        verbose_name="Message WhatsApp (devis formalisé / sous-devis)",
        help_text=(
            "Fiche devis → wa.me (un message par structure). Variables Django : devis.reference, "
            "devis_part.reference, org.name, total_display ; liste lines avec line_display, acte_name, "
            "quantity, subtotal_display (voir encart d’aide sur la page d’édition)."
        ),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Réglages notifications"
        verbose_name_plural = "Réglages notifications"

    def __str__(self):
        return "Réglages notifications"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def resolved_google_reviews_url(self) -> str:
        """URL effective pour la page avis Google : base prioritaire, puis MEDCARE_GOOGLE_REVIEWS_URL."""
        u = (self.google_reviews_url or "").strip()
        if u:
            return u
        from django.conf import settings

        return (getattr(settings, "MEDCARE_GOOGLE_REVIEWS_URL", "") or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Catalogue
# ─────────────────────────────────────────────────────────────────────────────


class NotificationChannel(models.Model):
    """Canal d'envoi (email, in_app, whatsapp_cloud, sms…)."""

    code = models.SlugField(max_length=40, unique=True)
    label = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=True)
    requires_external_config = models.BooleanField(
        default=False,
        help_text="Vrai si le canal dépend d'une configuration externe (SMTP, API…).",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "label"]
        verbose_name = "Canal de notification"
        verbose_name_plural = "Canaux de notification"

    def __str__(self):
        return self.label


class NotificationEvent(models.Model):
    """Événement métier déclencheur (catalogue admin-modifiable)."""

    AUDIENCE_CHOICES = (
        ("admin", "Équipe MedCare (admins)"),
        ("prestataire", "Structures / prestataires"),
        ("patient", "Patients"),
        ("mixed", "Mixte"),
    )

    code = models.SlugField(
        max_length=80,
        unique=True,
        help_text="Identifiant technique stable (ex. devis.created, subscription.requested).",
    )
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default="admin",
        help_text="Public principal de l'événement (sert au regroupement).",
    )
    sample_context = models.JSONField(
        blank=True,
        null=True,
        help_text="Exemple de variables disponibles dans le template (documentation).",
    )
    is_enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "label"]
        verbose_name = "Événement de notification"
        verbose_name_plural = "Événements de notification"

    def __str__(self):
        return f"{self.label} ({self.code})"


class NotificationTemplate(models.Model):
    """Modèle de message pour un (event × channel). Champs dynamiques possibles (ex. {{ org.name }})."""

    event = models.ForeignKey(
        NotificationEvent,
        on_delete=models.CASCADE,
        related_name="templates",
    )
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE,
        related_name="templates",
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        help_text="Sujet (email) ou titre (in-app).",
    )
    body = models.TextField(help_text="Corps du message — peut contenir des marqueurs du type {{ org.name }}.")
    is_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("event", "channel")
        verbose_name = "Template de notification"
        verbose_name_plural = "Templates de notification"

    def __str__(self):
        return f"{self.event.label} → {self.channel.label}"


# ─────────────────────────────────────────────────────────────────────────────
# Routing : qui reçoit quoi
# ─────────────────────────────────────────────────────────────────────────────


class NotificationRule(models.Model):
    """
    Définit pour un (event × channel) la liste des destinataires.

    Sources cumulées :
      • `target_roles` : envoie à tous les users d'un rôle (admin / prestataire / patient).
      • `target_users` (M2M) : users staff explicites (équipe ops).
      • `extra_emails` : emails libres (séparés par virgule), utile pour des alertes ops.
      • Acteurs contextuels : `notify_event_actor` (l'organisme/patient concerné par l'event).
    """

    ROLE_ADMIN = "admin"
    ROLE_PRESTATAIRE = "prestataire"
    ROLE_PATIENT = "patient"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admins"),
        (ROLE_PRESTATAIRE, "Prestataires"),
        (ROLE_PATIENT, "Patients"),
    )

    event = models.ForeignKey(
        NotificationEvent,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    target_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste de rôles destinataires (admin / prestataire / patient).",
    )
    target_users = models.ManyToManyField(
        User,
        blank=True,
        related_name="subscribed_rules",
        help_text="Utilisateurs explicitement abonnés à cette règle.",
    )
    extra_emails = models.TextField(
        blank=True,
        help_text="Emails séparés par des virgules ou retours à la ligne.",
    )
    notify_event_actor = models.BooleanField(
        default=False,
        help_text=(
            "Notifie aussi l'acteur lié à l'événement (l'organisme / le patient concerné, "
            "selon le contexte fourni à dispatch())."
        ),
    )
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("event", "channel")
        ordering = ["event__order", "event__label", "channel__order"]
        verbose_name = "Règle de notification"
        verbose_name_plural = "Règles de notification"

    def __str__(self):
        return f"{self.event.label} via {self.channel.label}"

    @property
    def role_labels(self):
        labels = dict(self.ROLE_CHOICES)
        return [labels.get(r, r) for r in (self.target_roles or [])]

    def parse_extra_emails(self):
        if not self.extra_emails:
            return []
        raw = self.extra_emails.replace("\n", ",")
        return [e.strip() for e in raw.split(",") if e.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Préférences utilisateur (opt-out par event × channel)
# ─────────────────────────────────────────────────────────────────────────────


class UserNotificationPreference(models.Model):
    """Permet à un utilisateur de désactiver un canal pour un event donné."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    event = models.ForeignKey(
        NotificationEvent,
        on_delete=models.CASCADE,
        related_name="user_preferences",
    )
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE,
        related_name="user_preferences",
    )
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "event", "channel")
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notification"

    def __str__(self):
        state = "✓" if self.enabled else "✗"
        return f"{state} {self.user} / {self.event.code} / {self.channel.code}"


# ─────────────────────────────────────────────────────────────────────────────
# Journal
# ─────────────────────────────────────────────────────────────────────────────


class NotificationLog(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = (
        (STATUS_QUEUED, "En file"),
        (STATUS_SENT, "Envoyée"),
        (STATUS_FAILED, "Échec"),
        (STATUS_SKIPPED, "Ignorée"),
    )

    event = models.ForeignKey(
        NotificationEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    recipient_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
    )
    recipient_address = models.CharField(
        max_length=255,
        blank=True,
        help_text="Email ou numéro WhatsApp si pas de user lié.",
    )
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
        db_index=True,
    )
    error = models.TextField(blank=True)
    context_snapshot = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Journal d'envoi"
        verbose_name_plural = "Journaux d'envoi"

    def __str__(self):
        target = self.recipient_user or self.recipient_address or "?"
        return f"[{self.status}] {self.event} → {target}"
