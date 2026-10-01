from django.db import models
from users.models import User


class Conversation(models.Model):
    """Thread de conversation entre un patient et un prestataire."""

    KIND_GENERAL = "general"
    KIND_DEVIS = "devis"
    KIND_RDV = "rdv"
    KIND_CHOICES = [
        (KIND_GENERAL, "Général"),
        (KIND_DEVIS, "Devis"),
        (KIND_RDV, "Rendez-vous"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_WAITING = "waiting"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Actif"),
        (STATUS_WAITING, "En attente"),
        (STATUS_CLOSED, "Clos"),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations_as_patient"
    )
    prestataire = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations_as_prestataire"
    )
    subject = models.CharField(max_length=255, blank=True, null=True)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default=KIND_GENERAL)
    thread_status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    related_cart = models.ForeignKey(
        "cart.Cart",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    devis_part = models.OneToOneField(
        "cart.DevisPart",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation",
    )
    rendez_vous = models.ForeignKey(
        "appointments.RendezVous",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

    def __str__(self):
        return f"{self.patient.username} ↔ {self.prestataire.username}: {self.subject or 'Sans objet'}"

    @property
    def last_message(self):
        return self.messages.order_by("-timestamp").first()

    @property
    def unread_count_for_patient(self):
        return self.messages.filter(is_read=False, sender=self.prestataire).count()

    @property
    def unread_count_for_prestataire(self):
        return self.messages.filter(is_read=False, sender=self.patient).count()

    @property
    def organisme(self):
        if self.devis_part_id:
            try:
                return self.devis_part.organisme
            except Exception:
                pass
        if self.rendez_vous_id:
            try:
                return self.rendez_vous.organisme
            except Exception:
                pass
        return None

    @property
    def dossier_label(self):
        if self.rendez_vous_id and self.rendez_vous:
            return f"RDV {self.rendez_vous.reference}"
        if self.devis_part_id and self.devis_part:
            return f"Devis {self.devis_part.reference}"
        return self.subject or "Conversation"

    @property
    def status_badge(self):
        """Classe CSS + libellé pour l'inbox."""
        ts = self.thread_status
        if self.rendez_vous_id and self.rendez_vous:
            st = self.rendez_vous.status
            mapping = {
                "requested": ("wait", "À confirmer"),
                "confirmed": ("ok", "Confirmé"),
                "completed": ("done", "Honoré"),
                "cancelled": ("expired", "Annulé"),
                "declined": ("expired", "Refusé"),
                "no_show": ("expired", "Absent"),
            }
            return mapping.get(st, (ts, self.get_thread_status_display()))
        if ts == self.STATUS_WAITING:
            return ("wait", "En attente")
        if ts == self.STATUS_CLOSED:
            return ("expired", "Clos")
        return ("ok", "Actif")


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = (
        ("internal", "Message Interne"),
        ("whatsapp_request", "Demande WhatsApp"),
        ("system", "Message Système"),
        ("status_card", "Carte statut"),
        ("choice", "Choix guidé"),
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_messages"
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPE_CHOICES, default="internal"
    )
    payload = models.JSONField(default=dict, blank=True)
    superseded_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supersedes",
    )
    attachment = models.FileField(
        upload_to="message_attachments/", blank=True, null=True
    )
    whatsapp_data = models.JSONField(
        blank=True, null=True,
        help_text="Données du message WhatsApp (numéro, texte pré-rempli, items panier)",
    )

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return (
            f"De {self.sender.username} à {self.receiver.username} "
            f"({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
        )

    def mark_as_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    @property
    def is_from_patient(self):
        conv = self.conversation
        return conv and self.sender_id == conv.patient_id

    @property
    def bubble_class(self):
        if self.message_type in ("system", "status_card"):
            return "sys"
        if self.conversation and self.sender_id == self.conversation.patient_id:
            return "s"
        if self.conversation and self.sender_id == self.conversation.prestataire_id:
            return "r"
        return "r"


class Notification(models.Model):
    """Notifications pour les utilisateurs (contact, nouveau message, avis, etc.)."""
    TYPE_CHOICES = (
        ("message", "Nouveau Message"),
        ("whatsapp", "Demande WhatsApp"),
        ("review", "Nouvel Avis"),
        ("cart", "Modification Panier"),
        ("devis", "Devis Généré"),
        ("rdv", "Rendez-vous"),
        ("assurance", "Assurance"),
        ("prelevement", "Prestations à domicile"),
        ("profile_view", "Consultation de Profil"),
        ("system", "Notification Système"),
        ("approval", "Approbation de Compte"),
    )

    # Rappels santé / RDV — distincts des notifications « compte » (devis, messages…).
    RAPPEL_NOTIFICATION_TYPES = frozenset({"rdv"})

    # Présentation dans la cloche : classe couleur (pastille) + libellé d'action.
    # L'icône SVG est rendue par templates/partials/notif_icon.html selon le type.
    BELL_META = {
        "devis": ("ni-devis", "Voir le devis"),
        "rdv": ("ni-rdv", "Voir le RDV"),
        "message": ("ni-message", "Répondre"),
        "whatsapp": ("ni-message", "Ouvrir"),
        "review": ("ni-rappel", "Voir"),
        "cart": ("ni-devis", "Voir le panier"),
        "assurance": ("ni-assurance", "Voir"),
        "prelevement": ("ni-prelevement", "Suivre"),
        "approval": ("ni-rdv", "Voir"),
        "profile_view": ("ni-system", "Voir"),
        "system": ("ni-system", "Voir"),
    }
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    link = models.CharField(
        max_length=500, blank=True, null=True,
        help_text="URL interne vers la ressource concernée",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title}"

    def _bell_meta(self):
        return self.BELL_META.get(self.notification_type, self.BELL_META["system"])

    @property
    def bell_class(self):
        return self._bell_meta()[0]

    @property
    def bell_cta(self):
        return self._bell_meta()[1]

    @property
    def is_rappel(self) -> bool:
        return self.notification_type in self.RAPPEL_NOTIFICATION_TYPES

    @classmethod
    def queryset_rappels(cls, user):
        return cls.objects.filter(user=user, notification_type__in=cls.RAPPEL_NOTIFICATION_TYPES)

    @classmethod
    def queryset_inbox(cls, user):
        return cls.objects.filter(user=user).exclude(
            notification_type__in=cls.RAPPEL_NOTIFICATION_TYPES
        )
