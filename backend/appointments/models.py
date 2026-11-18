"""Module de prise de rendez-vous patient ↔ structure.

Un `RendezVous` est ancré sur un sous-devis (`DevisPart`, déjà découpé par structure) :
le patient choisit un créneau (généré à partir des horaires d'ouverture de la structure),
la structure confirme / refuse depuis son espace pro, puis marque le RDV honoré / absent.

Le paiement de la réservation (frais 500 FCFA) est **désactivé jusqu'à M6** — `reservation_fee`
est conservé pour l'affichage uniquement.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class RendezVous(models.Model):
    STATUS_REQUESTED = "requested"
    STATUS_CONFIRMED = "confirmed"
    STATUS_DECLINED = "declined"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_NO_SHOW = "no_show"

    STATUS_CHOICES = [
        (STATUS_REQUESTED, "Demandé"),
        (STATUS_CONFIRMED, "Confirmé"),
        (STATUS_DECLINED, "Refusé"),
        (STATUS_CANCELLED, "Annulé"),
        (STATUS_COMPLETED, "Honoré"),
        (STATUS_NO_SHOW, "Absent"),
    ]

    # Statuts qui « occupent » un créneau (donc le rendent indisponible).
    OPEN_STATUSES = (STATUS_REQUESTED, STATUS_CONFIRMED)
    # Statuts considérés comme actifs côté patient (à venir / en cours).
    LIVE_STATUSES = (STATUS_REQUESTED, STATUS_CONFIRMED)
    # Statuts qui « remplissent » un créneau dans l'agenda pro (occupé / historique).
    OCCUPYING_STATUSES = (STATUS_REQUESTED, STATUS_CONFIRMED, STATUS_COMPLETED, STATUS_NO_SHOW)

    # Origine du rendez-vous : pris en ligne par le patient ou saisi sur place par la structure.
    SOURCE_ONLINE = "online"
    SOURCE_WALK_IN = "walk_in"
    SOURCE_CHOICES = [
        (SOURCE_ONLINE, "En ligne"),
        (SOURCE_WALK_IN, "Sur place"),
    ]

    BY_PATIENT = "patient"
    BY_PRESTATAIRE = "prestataire"

    reference = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rendez_vous",
        blank=True,
        null=True,
        help_text="Patient de la plateforme. Vide pour un RDV saisi sur place.",
    )
    source = models.CharField(
        max_length=12, choices=SOURCE_CHOICES, default=SOURCE_ONLINE
    )
    # Coordonnées libres pour un RDV « sur place » (patient hors plateforme).
    walk_in_name = models.CharField("Nom (sur place)", max_length=120, blank=True)
    walk_in_phone = models.CharField("Téléphone (sur place)", max_length=40, blank=True)
    walk_in_motif = models.CharField("Motif (sur place)", max_length=200, blank=True)
    organisme = models.ForeignKey(
        "healthcare.OrganismeDeSante",
        on_delete=models.CASCADE,
        related_name="rendez_vous",
    )
    devis = models.ForeignKey(
        "cart.Devis",
        on_delete=models.SET_NULL,
        related_name="rendez_vous",
        blank=True,
        null=True,
    )
    devis_part = models.ForeignKey(
        "cart.DevisPart",
        on_delete=models.SET_NULL,
        related_name="rendez_vous",
        blank=True,
        null=True,
    )

    start = models.DateTimeField("Début du créneau")
    end = models.DateTimeField("Fin du créneau", blank=True, null=True)
    slot_minutes = models.PositiveSmallIntegerField(default=30)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_REQUESTED
    )

    # Snapshot des actes figés au moment de la prise de RDV (depuis DevisPart.details).
    actes_snapshot = models.JSONField(default=list, blank=True)
    total_brut = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_patient = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reservation_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=500,
        help_text="Frais de réservation — affichage uniquement, encaissement prévu à M6.",
    )

    patient_note = models.TextField(blank=True)
    prestataire_note = models.TextField(blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)
    cancelled_by = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    # Horodatage de l'envoi du rappel J-1 (idempotence du cron).
    reminder_sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"
        ordering = ["-start"]
        indexes = [
            models.Index(fields=["organisme", "status", "start"]),
            models.Index(fields=["patient", "status", "start"]),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"RDV-{uuid.uuid4().hex[:8].upper()}"
        if self.start and not self.end:
            self.end = self.start + timezone.timedelta(minutes=self.slot_minutes or 30)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} · {self.organisme.name} · {self.start:%d/%m %H:%M}"

    # ─── État ────────────────────────────────────────────────────────────────
    @property
    def is_walk_in(self):
        return self.source == self.SOURCE_WALK_IN

    @property
    def patient_label(self):
        """Libellé patient pour l'espace pro (en ligne ou sur place)."""
        if self.is_walk_in:
            return self.walk_in_name or "RDV sur place"
        if self.patient_id:
            return self.patient.display_name or self.patient.username
        return "—"

    @property
    def patient_phone(self):
        if self.is_walk_in:
            return self.walk_in_phone
        if self.patient_id:
            return getattr(self.patient, "phone", "") or ""
        return ""

    @property
    def is_live(self):
        return self.status in self.LIVE_STATUSES

    @property
    def is_upcoming(self):
        return self.is_live and self.start and self.start >= timezone.now()

    @property
    def is_past(self):
        return not self.is_upcoming

    @property
    def status_badge(self):
        """Classe de couleur (tailwind-ish) selon le statut, pour les templates."""
        return {
            self.STATUS_REQUESTED: "wait",
            self.STATUS_CONFIRMED: "ok",
            self.STATUS_DECLINED: "expired",
            self.STATUS_CANCELLED: "expired",
            self.STATUS_COMPLETED: "done",
            self.STATUS_NO_SHOW: "expired",
        }.get(self.status, "wait")

    # ─── Transitions ───────────────────────────────────────────────────────────
    def confirm(self, note=""):
        self.status = self.STATUS_CONFIRMED
        self.confirmed_at = timezone.now()
        if note:
            self.prestataire_note = note
        self.save(update_fields=["status", "confirmed_at", "prestataire_note", "updated_at"])

    def decline(self, note=""):
        self.status = self.STATUS_DECLINED
        if note:
            self.prestataire_note = note
        self.save(update_fields=["status", "prestataire_note", "updated_at"])

    def cancel(self, by=BY_PATIENT, reason=""):
        self.status = self.STATUS_CANCELLED
        self.cancelled_by = by
        self.cancel_reason = reason[:200]
        self.save(update_fields=["status", "cancelled_by", "cancel_reason", "updated_at"])

    def mark_completed(self, note=""):
        self.status = self.STATUS_COMPLETED
        if note:
            self.prestataire_note = note
        self.save(update_fields=["status", "prestataire_note", "updated_at"])

    def mark_no_show(self, note=""):
        self.status = self.STATUS_NO_SHOW
        if note:
            self.prestataire_note = note
        self.save(update_fields=["status", "prestataire_note", "updated_at"])

    def get_prerequisites_display(self) -> str:
        from .reminders import prerequisites_for_rdv

        return prerequisites_for_rdv(self)


class RdvReminderSchedule(models.Model):
    """Règle d'envoi de rappel RDV (plateforme ou par structure)."""

    UNIT_MINUTES = "minutes"
    UNIT_HOURS = "hours"
    UNIT_DAYS = "days"
    OFFSET_UNIT_CHOICES = [
        (UNIT_MINUTES, "Minutes avant"),
        (UNIT_HOURS, "Heures avant"),
        (UNIT_DAYS, "Jours avant"),
    ]

    label = models.CharField(
        max_length=80,
        help_text="Libellé affiché en admin (ex. « Veille du RDV », « 30 min avant »).",
    )
    offset_value = models.PositiveIntegerField(
        default=1,
        help_text="Valeur numérique (ex. 1 jour, 3 jours, 30 minutes).",
    )
    offset_unit = models.CharField(
        max_length=10,
        choices=OFFSET_UNIT_CHOICES,
        default=UNIT_DAYS,
    )
    tolerance_minutes = models.PositiveSmallIntegerField(
        default=30,
        help_text="Fenêtre cron ± minutes autour de l'heure cible d'envoi.",
    )
    include_prerequisites = models.BooleanField(
        default=True,
        verbose_name="Inclure les prérequis des actes",
        help_text="Ajoute les consignes configurées sur chaque acte du RDV.",
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    organisme = models.ForeignKey(
        "healthcare.OrganismeDeSante",
        on_delete=models.CASCADE,
        related_name="rdv_reminder_schedules",
        blank=True,
        null=True,
        help_text="Vide = règle plateforme. Renseigné = règle propre à la structure.",
    )
    actes = models.ManyToManyField(
        "healthcare.ActeMedical",
        blank=True,
        related_name="rdv_reminder_schedules",
        verbose_name="Actes concernés",
        help_text="Vide = tous les RDV confirmés. Sinon, uniquement si le RDV contient au moins un de ces actes.",
    )

    class Meta:
        verbose_name = "Règle de rappel RDV"
        verbose_name_plural = "Règles de rappel RDV"
        ordering = ["order", "-offset_value"]

    def __str__(self):
        return f"{self.label} ({self.offset_display})"

    @property
    def minutes_before(self) -> int:
        if self.offset_unit == self.UNIT_DAYS:
            return self.offset_value * 24 * 60
        if self.offset_unit == self.UNIT_HOURS:
            return self.offset_value * 60
        return self.offset_value

    @property
    def offset_display(self) -> str:
        unit_labels = {
            self.UNIT_MINUTES: "min",
            self.UNIT_HOURS: "h",
            self.UNIT_DAYS: "j",
        }
        suffix = unit_labels.get(self.offset_unit, "")
        return f"{self.offset_value} {suffix} avant"


class RendezVousReminderLog(models.Model):
    """Trace d'un rappel RDV envoyé (idempotence multi-règles)."""

    rendez_vous = models.ForeignKey(
        RendezVous,
        on_delete=models.CASCADE,
        related_name="reminder_logs",
    )
    schedule = models.ForeignKey(
        RdvReminderSchedule,
        on_delete=models.CASCADE,
        related_name="sent_logs",
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rappel RDV envoyé"
        verbose_name_plural = "Rappels RDV envoyés"
        constraints = [
            models.UniqueConstraint(
                fields=["rendez_vous", "schedule"],
                name="uniq_rdv_reminder_per_schedule",
            ),
        ]

    def __str__(self):
        return f"{self.rendez_vous.reference} · {self.schedule.label}"
