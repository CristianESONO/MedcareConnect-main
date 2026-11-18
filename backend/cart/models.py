import uuid
from django.db import models
from django.db.models import Sum
from users.models import User
from healthcare.models import Assurance, OrganismeDeSante, PrestataireActe


class Cart(models.Model):
    STATUS_CHOICES = (
        ("active", "Actif"),
        ("saved", "Sauvegardé"),
        ("converted", "Converti en devis"),
        ("expired", "Expiré"),
    )
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="carts"
    )
    name = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Nom optionnel pour identifier le panier (ex: 'Bilan complet')",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active"
    )
    selected_insurance = models.ForeignKey(
        Assurance, on_delete=models.SET_NULL, null=True, blank=True
    )
    insurance_user_override = models.BooleanField(
        default=False,
        help_text="Le patient a choisi manuellement l'assurance (ou « sans assurance ») sur le panier.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"
        ordering = ["-updated_at"]

    def __str__(self):
        label = self.name or f"Panier #{self.pk}"
        return f"{label} — {self.patient.username}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.select_related("prestataire_acte"))

    @property
    def total_after_insurance(self):
        if not self.selected_insurance:
            return self.total_price
        return sum(
            item.cost_after_insurance(self.selected_insurance)
            for item in self.items.select_related(
                "prestataire_acte__organisme", "prestataire_acte__acte"
            )
        )

    @property
    def insurance_savings(self):
        if not self.selected_insurance:
            return 0
        return self.total_price - self.total_after_insurance

    @property
    def item_count(self):
        """Total des quantités (ex. 3 lignes × 2 = 6 unités affichées sur le badge)."""
        agg = self.items.aggregate(total=Sum("quantity"))
        return int(agg["total"] or 0)

    @classmethod
    def get_active_cart(cls, user):
        """Retourne le panier actif du patient, ou en crée un nouveau."""
        cart, _ = cls.objects.get_or_create(
            patient=user, status="active",
            defaults={"name": "Mon panier"},
        )
        return cart


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    prestataire_acte = models.ForeignKey(
        PrestataireActe, on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(
        blank=True, null=True,
        help_text="Notes/demandes spécifiques du patient",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Article du panier"
        verbose_name_plural = "Articles du panier"

    def __str__(self):
        return (
            f"{self.quantity} x {self.prestataire_acte.acte.name} "
            f"chez {self.prestataire_acte.organisme.name}"
        )

    @property
    def subtotal(self):
        return self.prestataire_acte.price * self.quantity

    def cost_after_insurance(self, assurance, patient_profile=None):
        unit_cost = self.prestataire_acte.get_patient_cost(
            assurance, patient_profile=patient_profile
        )
        return unit_cost * self.quantity


class Devis(models.Model):
    """Devis estimatif généré à partir d'un panier."""
    STATUS_CHOICES = (
        ("draft", "Brouillon"),
        ("sent", "Envoyé"),
        ("viewed", "Consulté"),
        ("relanced", "Relancé"),
        ("expired", "Expiré"),
        ("archived", "Archivé"),
    )
    MAX_RELANCES = 2
    reference = models.CharField(
        max_length=20, unique=True, editable=False
    )
    cart = models.ForeignKey(
        Cart, on_delete=models.SET_NULL, null=True, blank=True, related_name="devis"
    )
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="devis"
    )
    insurance = models.ForeignKey(
        Assurance, on_delete=models.SET_NULL, null=True, blank=True
    )
    total_brut = models.DecimalField(max_digits=12, decimal_places=2)
    total_assurance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_patient = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    details = models.JSONField(
        help_text="Snapshot détaillé des items, prix et taux au moment de la génération",
    )
    notes = models.TextField(blank=True, null=True)
    relance_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Nombre de relances WhatsApp envoyées (max 2 avant archivage automatique).",
    )
    last_relanced_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    archived_reason = models.CharField(max_length=120, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = "Devis"
        verbose_name_plural = "Devis"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"DEV-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Devis {self.reference} — {self.patient.username}"

    @property
    def relances_restantes(self):
        return max(0, self.MAX_RELANCES - (self.relance_count or 0))

    @property
    def is_archived(self):
        return self.status == "archived" or self.archived_at is not None

    def can_relance(self):
        return not self.is_archived and (self.relance_count or 0) < self.MAX_RELANCES

    def mark_relance(self, by_user=None):
        from django.utils import timezone as _tz
        self.relance_count = (self.relance_count or 0) + 1
        self.last_relanced_at = _tz.now()
        if self.relance_count >= self.MAX_RELANCES:
            self.archived_at = _tz.now()
            self.archived_reason = "2 relances sans réponse"
            self.status = "archived"
        else:
            self.status = "relanced"
        self.save(update_fields=[
            "relance_count", "last_relanced_at", "status", "archived_at", "archived_reason",
        ])

    def archive(self, reason="Archivé manuellement"):
        from django.utils import timezone as _tz
        self.archived_at = _tz.now()
        self.archived_reason = reason[:120]
        self.status = "archived"
        self.save(update_fields=["archived_at", "archived_reason", "status"])


class DevisPart(models.Model):
    """
    Sous-devis par structure : cycle de vie (relance, archivage) indépendant du devis parent.
    """

    STATUS_CHOICES = Devis.STATUS_CHOICES
    MAX_RELANCES = Devis.MAX_RELANCES

    reference = models.CharField(max_length=32, unique=True, editable=False)
    devis = models.ForeignKey(
        Devis,
        on_delete=models.CASCADE,
        related_name="parts",
    )
    organisme = models.ForeignKey(
        OrganismeDeSante,
        on_delete=models.CASCADE,
        related_name="devis_parts",
    )
    details = models.JSONField(
        help_text="Snapshot des lignes (actes) pour cette structure uniquement",
    )
    total_brut = models.DecimalField(max_digits=12, decimal_places=2)
    total_assurance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_patient = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    relance_count = models.PositiveSmallIntegerField(default=0)
    last_relanced_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    archived_reason = models.CharField(max_length=120, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sous-devis (structure)"
        verbose_name_plural = "Sous-devis (structures)"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["devis", "organisme"],
                name="cart_devispart_unique_devis_organisme",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"DP-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} ({self.organisme.name}) ← {self.devis.reference}"

    @property
    def relances_restantes(self):
        return max(0, self.MAX_RELANCES - (self.relance_count or 0))

    @property
    def is_archived(self):
        return self.status == "archived" or self.archived_at is not None

    def can_relance(self):
        return not self.is_archived and (self.relance_count or 0) < self.MAX_RELANCES

    def mark_relance(self, by_user=None):
        from django.utils import timezone as _tz

        self.relance_count = (self.relance_count or 0) + 1
        self.last_relanced_at = _tz.now()
        if self.relance_count >= self.MAX_RELANCES:
            self.archived_at = _tz.now()
            self.archived_reason = "2 relances sans réponse"
            self.status = "archived"
        else:
            self.status = "relanced"
        self.save(
            update_fields=[
                "relance_count",
                "last_relanced_at",
                "status",
                "archived_at",
                "archived_reason",
            ]
        )

    def archive(self, reason="Archivé manuellement"):
        from django.utils import timezone as _tz

        self.archived_at = _tz.now()
        self.archived_reason = reason[:120]
        self.status = "archived"
        self.save(update_fields=["archived_at", "archived_reason", "status"])
