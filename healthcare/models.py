from django.db import models
from django.utils.text import slugify
from medcare_connect.upload_paths import UploadToUnique
from users.models import User


class TypeOrganisme(models.Model):
    """Catégorie d'organisme : Hôpital, Clinique, Laboratoire, Pharmacie, etc."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Type d'Organisme"
        verbose_name_plural = "Types d'Organismes"
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Region(models.Model):
    """Régions/villes du Sénégal pour la recherche géographique structurée."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Région"
        verbose_name_plural = "Régions"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Photo(models.Model):
    image = models.ImageField(
        upload_to=UploadToUnique("organism_photos"), max_length=255
    )
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.caption or "Photo"


class OrganismeDeSante(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="healthcare_provider_profile"
    )
    name = models.CharField(
        max_length=255,
        help_text="Nom affiché sur la plateforme (nom commercial / enseigne)",
    )
    raison_sociale = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Raison sociale légale si différente du nom commercial",
    )
    ninea = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Numéro d'identification nationale des entreprises et associations (NINEA), si applicable",
    )
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    type_organisme = models.ForeignKey(
        TypeOrganisme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organismes",
    )
    address = models.CharField(max_length=255)
    quartier = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, default="Dakar")
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organismes",
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_number = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="Numéro WhatsApp avec indicatif pays (ex: +221770000000)",
    )
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    opening_hours = models.JSONField(blank=True, null=True)
    logo = models.ImageField(
        upload_to=UploadToUnique("logos"),
        max_length=255,
        blank=True,
        null=True,
    )
    photos = models.ManyToManyField(Photo, blank=True)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    # Champs booléens non-null (présents en prod) — défaut False.
    sans_rendez_vous = models.BooleanField(default=False)
    accepte_tiers_payant = models.BooleanField(default=False)
    prises_sang_domicile = models.BooleanField(default=False)
    domicile_delai_intervention = models.CharField(
        max_length=40,
        blank=True,
        default="",
        verbose_name="Délai d'intervention à domicile",
        help_text="Délai indicatif pour les prestations à domicile (catalogue actes).",
    )
    domicile_plages_horaires = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Plages horaires à domicile",
        help_text="Ex. : 7h–10h Lun–Sam",
    )
    access_pmr = models.BooleanField(default=False)
    horaires_complement = models.TextField(blank=True, null=True)
    catalogue_tarifs_delais = models.TextField(
        blank=True,
        verbose_name="Tarifs & délais (catalogue actes)",
        help_text=(
            "Saisie libre côté structure : transparence tarifaire, délais d’exécution, particularités. "
            "Complète les cases « actes proposés » du parcours simplifié."
        ),
    )
    assurances_tarifs_delais = models.TextField(
        blank=True,
        verbose_name="Tarifs & délais (assurances)",
        help_text=(
            "Saisie libre : tiers payant, délais de prise en charge, documents requis, etc."
        ),
    )
    settings_dashboard_period = models.CharField(
        max_length=10,
        default="30j",
        choices=(
            ("7j", "7 jours"),
            ("30j", "30 jours"),
            ("total", "Depuis M0 (total)"),
        ),
        verbose_name="Période par défaut du dashboard",
    )
    settings_locale = models.CharField(
        max_length=5,
        default="fr",
        choices=(
            ("fr", "Français"),
            ("wo", "Wolof"),
            ("en", "English"),
        ),
        verbose_name="Langue du dashboard",
    )
    settings_currency = models.CharField(
        max_length=5,
        default="XOF",
        choices=(
            ("XOF", "FCFA (XOF)"),
            ("EUR", "EUR (€)"),
            ("USD", "USD ($)"),
        ),
        verbose_name="Devise d'affichage",
    )
    show_prices_on_public_profile = models.BooleanField(
        default=True,
        verbose_name="Afficher les tarifs sur le profil public",
    )
    dashboard_team = models.JSONField(
        default=list,
        blank=True,
        help_text="Invitations / accès dashboard (nom, email, rôle, statut).",
    )
    profile_views_count = models.PositiveIntegerField(default=0)
    subscription_plan = models.ForeignKey(
        "SubscriptionPlan",
        on_delete=models.PROTECT,
        related_name="organismes",
        verbose_name="Formule d'abonnement",
    )
    subscription_started_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="Début abonnement",
        help_text="Date d'entrée sur la formule actuelle (informatif, sert au calcul d'échéance).",
    )
    subscription_renewal_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="Échéance d'abonnement",
        help_text="Prochaine échéance (renouvellement). Une alerte J-30 est affichée à l'admin.",
    )
    subscription_auto_renew = models.BooleanField(
        default=True,
        verbose_name="Renouvellement automatique",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organisme de Santé"
        verbose_name_plural = "Organismes de Santé"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.subscription_plan_id:
            self.subscription_plan = get_default_subscription_plan()
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while OrganismeDeSante.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def whatsapp_link(self):
        if not self.whatsapp_number:
            return None
        number = self.whatsapp_number.replace("+", "").replace(" ", "")
        return f"https://wa.me/{number}"

    @property
    def whatsapp_digits(self):
        """Numéro WhatsApp pour wa.me (chiffres uniquement)."""
        if not self.whatsapp_number:
            return ""
        return "".join(c for c in self.whatsapp_number if c.isdigit())

    @property
    def tel_href(self):
        """URI tel: pour le numéro affiché (chiffres et + uniquement)."""
        if not self.contact_phone:
            return ""
        return "tel:" + "".join(c for c in self.contact_phone if c.isdigit() or c == "+")

    @property
    def accepted_insurances(self):
        return Assurance.objects.filter(
            prises_en_charge__organisme=self
        ).distinct()

    @property
    def services_offered(self):
        return ServiceMedical.objects.filter(
            acts__prestataire_actes__organisme=self
        ).distinct()

    def plan_allows(self, feature_code: str) -> bool:
        """
        Indique si la formule actuelle inclut le droit `feature_code` (réf. `SubscriptionFeature`).

        À ce jour, cette méthode n'est pas utilisée pour masquer des pages ou actions dans l'app :
        les inclusions servent surtout au **texte** sur la page Abonnement prestataire. Quand des
        modules devront être réellement restreints, il faudra appeler `plan_allows` depuis les vues
        ou un décorateur dédié.
        """
        if not getattr(self, "subscription_plan_id", None):
            return True
        return self.subscription_plan.plan_features.filter(
            included=True,
            feature__code=feature_code,
        ).exists()


class ServiceMedical(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(
        upload_to=UploadToUnique("services"),
        max_length=255,
        blank=True,
        null=True,
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Service Médical"
        verbose_name_plural = "Services Médicaux"
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def display_icon(self):
        """Emoji pilier (DB ou mapping catalogue)."""
        from healthcare.service_icons import icon_for_service_medical

        return icon_for_service_medical(self)

    @property
    def provider_count(self):
        return OrganismeDeSante.objects.filter(
            prestataire_actes__acte__service_medical_category=self,
            is_active=True,
        ).distinct().count()


class ActeMedical(models.Model):
    SERVICE_LEVEL_CHOICES = (
        (1, "Service Principal"),
        (2, "Sous-Service"),
        (3, "Acte Spécifique"),
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, blank=True)
    code = models.CharField(
        max_length=50, blank=True, null=True, unique=True,
        help_text="Code médical standardisé si applicable",
    )
    description = models.TextField(blank=True, null=True)
    parent_service = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_acts",
    )
    service_medical_category = models.ForeignKey(
        ServiceMedical, on_delete=models.CASCADE, related_name="acts"
    )
    level = models.IntegerField(choices=SERVICE_LEVEL_CHOICES, default=3)
    reference_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Prix moyen/recommandé pour orientation",
    )
    rdv_prerequisites = models.TextField(
        blank=True,
        verbose_name="Prérequis / consignes RDV",
        help_text=(
            "Instructions patient avant le rendez-vous (à jeun, ordonnance, arrêt médicaments…). "
            "Inclus dans les rappels automatiques si configurés."
        ),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Acte Médical"
        verbose_name_plural = "Actes Médicaux"
        unique_together = ("name", "parent_service", "service_medical_category")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

    @property
    def subfamily_display_icon(self):
        """Emoji sous-famille (type niveau 2) pour le catalogue prestataire."""
        from healthcare.service_icons import icon_for_subfamily_label

        return icon_for_subfamily_label(self.name)

    @property
    def full_path(self):
        """Retourne le chemin hiérarchique complet : Service > Sous-service > Acte"""
        parts = [self.name]
        current = self.parent_service
        while current:
            parts.insert(0, current.name)
            current = current.parent_service
        parts.insert(0, self.service_medical_category.name)
        return " > ".join(parts)

    @property
    def price_range(self):
        """Retourne le min/max des prix chez tous les prestataires."""
        prices = self.prestataire_actes.filter(
            is_available=True
        ).aggregate(
            min_price=models.Min("price"),
            max_price=models.Max("price"),
        )
        return prices


class PrestataireActe(models.Model):
    DELAI_CHOICES = (
        ("", "Non précisé"),
        ("immediat", "Immédiat (urgence)"),
        ("30min", "Moins de 30 min"),
        ("1h", "Moins d'1 heure"),
        ("2h", "Moins de 2 heures"),
        ("4h", "Dans la journée (≤ 4h)"),
        ("24h", "Sous 24 h"),
        ("48h", "Sous 48 h"),
        ("72h", "Sous 72 h"),
        ("7j", "Sous 7 jours"),
        ("rdv", "Sur rendez-vous"),
    )
    DELAI_RANK = {
        "immediat": 0, "30min": 1, "1h": 2, "2h": 3, "4h": 4,
        "24h": 5, "48h": 6, "72h": 7, "7j": 8, "rdv": 9, "": 99,
    }

    organisme = models.ForeignKey(
        OrganismeDeSante, on_delete=models.CASCADE, related_name="prestataire_actes"
    )
    acte = models.ForeignKey(
        ActeMedical, on_delete=models.CASCADE, related_name="prestataire_actes"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delai = models.CharField(
        max_length=16,
        choices=DELAI_CHOICES,
        blank=True,
        default="",
        db_index=True,
        help_text="Délai indicatif d'obtention du résultat ou de réalisation.",
    )
    is_available = models.BooleanField(default=True)
    notes = models.TextField(
        blank=True, null=True,
        help_text="Conditions particulières, délais, prérequis…",
    )
    rdv_prerequisites = models.TextField(
        blank=True,
        verbose_name="Consignes / prérequis RDV (structure)",
        help_text="Message personnalisé pour vos patients (rappels automatiques).",
    )
    rdv_prerequisites_active = models.BooleanField(
        default=True,
        verbose_name="Diffuser les consignes au patient",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organisme", "acte")
        verbose_name = "Prestataire-Acte"
        verbose_name_plural = "Prestataires-Actes"

    def __str__(self):
        return f"{self.organisme.name} - {self.acte.name} ({self.price} XOF)"

    @property
    def delai_rank(self) -> int:
        return self.DELAI_RANK.get(self.delai or "", 99)

    def get_coverage_rate(self, assurance, patient_profile=None):
        """Taux indicatif si la structure accepte l'assurance."""
        from healthcare.coverage import (
            lookup_coverage_rate_percent,
            organisme_accepts_insurance,
        )

        if not assurance:
            return None
        if not organisme_accepts_insurance(self.organisme_id, assurance):
            return None
        return lookup_coverage_rate_percent(
            assurance, self.acte, patient_profile=patient_profile
        )

    def get_patient_cost(self, assurance=None, patient_profile=None):
        """Reste à charge patient après taux indicatif de l'assurance."""
        from healthcare.coverage import patient_cost_from_rate

        if not assurance:
            return self.price
        rate = self.get_coverage_rate(assurance, patient_profile=patient_profile)
        if rate is None:
            return self.price
        return patient_cost_from_rate(self.price, rate)


class Assurance(models.Model):
    """Assureur ou dispositif de couverture (réf. document ASSURANCES_SENEGAL.pdf)."""

    class Segment(models.TextChoices):
        PRIVEE_IARD = "privee_iard", "Assurance privée (IARD / traditionnelle)"
        DIGITALE = "digitale", "Assurance santé digitale / plateforme"
        REGIME_PUBLIC = "regime_public", "Régime public / institutionnel"
        MUTUELLE = "mutuelle", "Mutuelle / mutualité solidaire"
        PROGRAMME = "programme", "Programme ou initiative de couverture"

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    segment = models.CharField(
        max_length=32,
        choices=Segment.choices,
        default=Segment.PRIVEE_IARD,
        db_index=True,
        help_text="Segment réglementaire / commercial (hiérarchie document officiel)",
    )
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(
        upload_to=UploadToUnique("insurance_logos"),
        max_length=255,
        blank=True,
        null=True,
    )
    website = models.URLField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["segment", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def segment_icon(self):
        from healthcare.insurance_icons import icon_for_assurance_segment

        return icon_for_assurance_segment(self.segment)

    @property
    def segment_chip_label(self):
        from healthcare.insurance_icons import chip_label_for_assurance_segment

        return chip_label_for_assurance_segment(
            self.segment, self.get_segment_display()
        )

    @property
    def provider_count(self):
        return OrganismeDeSante.objects.filter(
            prises_en_charge__assurance=self,
            is_active=True,
        ).distinct().count()


class PriseEnChargeAssurance(models.Model):
    """Lien prestataire ↔ assurance acceptée (sans taux de couverture sur la plateforme)."""

    organisme = models.ForeignKey(
        OrganismeDeSante,
        on_delete=models.CASCADE,
        related_name="prises_en_charge",
    )
    assurance = models.ForeignKey(
        Assurance, on_delete=models.CASCADE, related_name="prises_en_charge"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organisme", "assurance")
        verbose_name = "Prise en Charge Assurance"
        verbose_name_plural = "Prises en Charge Assurances"

    def __str__(self):
        return f"{self.organisme.name} — {self.assurance.name}"


class ProfileView(models.Model):
    """Suivi des consultations de profil prestataire (tableau de bord)."""

    SOURCE_ANNUAIRE = "annuaire"
    SOURCE_WHATSAPP = "whatsapp"
    SOURCE_NFC = "nfc"
    SOURCE_QR = "qr"
    SOURCE_CHOICES = [
        (SOURCE_ANNUAIRE, "Annuaire"),
        (SOURCE_WHATSAPP, "WhatsApp"),
        (SOURCE_NFC, "MedPlaque NFC"),
        (SOURCE_QR, "MedPlaque QR"),
    ]

    organisme = models.ForeignKey(
        OrganismeDeSante, on_delete=models.CASCADE, related_name="profile_views"
    )
    viewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="viewed_profiles"
    )
    source = models.CharField(
        max_length=16,
        choices=SOURCE_CHOICES,
        default=SOURCE_ANNUAIRE,
        db_index=True,
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]
        verbose_name = "Vue de Profil"
        verbose_name_plural = "Vues de Profil"

    def __str__(self):
        who = self.viewer.username if self.viewer else "Anonyme"
        return f"{who} → {self.organisme.name} ({self.viewed_at.strftime('%d/%m/%Y')})"


class PlatformReview(models.Model):
    """Avis centralisé MedCare : note globale, actes concernés (feuilles du catalogue), champ libre tarifs & délais."""

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="platform_reviews"
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    tarifs_delais_comment = models.TextField(
        blank=True,
        verbose_name="Tarifs & délais",
        help_text="Retour libre sur tarifs et délais (unique champ texte, comme la démo structures).",
    )
    actes = models.ManyToManyField(
        "ActeMedical",
        related_name="platform_reviews",
        blank=True,
        help_text="Actes médicaux concernés (niveau 3 / segmentation catalogue).",
    )
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Avis plateforme"
        verbose_name_plural = "Avis plateforme"
        constraints = [
            models.UniqueConstraint(fields=["patient"], name="unique_platform_review_per_patient"),
        ]

    def __str__(self):
        return f"{self.patient.username} — avis MedCare ({self.rating}/5)"

    @property
    def comment(self):
        """Compatibilité avec les templates d’événements historiques utilisant `review.comment`."""
        return self.tarifs_delais_comment or ""


class Favoris(models.Model):
    """Prestataires favoris d'un patient."""
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="favoris"
    )
    organisme = models.ForeignKey(
        OrganismeDeSante, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("patient", "organisme")
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"

    def __str__(self):
        return f"{self.patient.username} ★ {self.organisme.name}"


class LotExamenPrefait(models.Model):
    """
    Lot / parcours d'examens prédéfini (ex. bilan hépatique, check-up) — choix rapide patient.
    Les actes référencés sont des ActeMedical de niveau 3 (feuilles du catalogue).
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    teaser = models.CharField(
        max_length=300,
        blank=True,
        help_text="Courte phrase affichée sur la carte (ex. idéal avant intervention)",
    )
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji ou clé d'icône")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    actes = models.ManyToManyField(
        "ActeMedical",
        through="LotExamenPrefaitActe",
        related_name="lots_prefaits",
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Lot d'examens prédéfini"
        verbose_name_plural = "Lots d'examens prédéfinis"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:210]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class LotExamenPrefaitActe(models.Model):
    lot = models.ForeignKey(
        LotExamenPrefait, on_delete=models.CASCADE, related_name="lot_actes"
    )
    acte = models.ForeignKey(
        "ActeMedical", on_delete=models.CASCADE, related_name="lot_memberships"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]
        unique_together = ("lot", "acte")
        verbose_name = "Acte du lot"
        verbose_name_plural = "Actes du lot"

    def __str__(self):
        return f"{self.lot.name} → {self.acte.name}"


class SearchHistory(models.Model):
    """Historique des recherches patient."""
    SEARCH_TYPE_CHOICES = (
        ("service", "Par Service"),
        ("acte", "Par Acte"),
        ("prestataire", "Par Prestataire"),
        ("localisation", "Par Localisation"),
        ("general", "Recherche Générale"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="search_history"
    )
    query = models.CharField(max_length=500)
    search_type = models.CharField(
        max_length=20, choices=SEARCH_TYPE_CHOICES, default="general"
    )
    filters_applied = models.JSONField(blank=True, null=True)
    results_count = models.PositiveIntegerField(default=0)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-searched_at"]
        verbose_name = "Historique de Recherche"
        verbose_name_plural = "Historiques de Recherche"

    def __str__(self):
        return f"{self.user.username}: \"{self.query}\" ({self.searched_at.strftime('%d/%m/%Y')})"


# ── Abonnements structures (formules configurables, sans paiement intégré) ──


class SubscriptionFeature(models.Model):
    """Référentiel des droits / modules activables par formule (créé en admin)."""

    code = models.SlugField(
        max_length=64,
        unique=True,
        help_text="Identifiant technique stable (ex. whatsapp_devis, medplaque).",
    )
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "label"]
        verbose_name = "Fonctionnalité d'abonnement"
        verbose_name_plural = "Fonctionnalités d'abonnement"

    def __str__(self):
        return f"{self.label} ({self.code})"


class PrelevementZone(models.Model):
    """
    Zone tarifaire de prestation à domicile pour un organisme (laboratoire, clinique…).
    Une zone = un quartier/ville + un forfait de déplacement en FCFA (0 = gratuit).
    """

    organisme = models.ForeignKey(
        OrganismeDeSante,
        on_delete=models.CASCADE,
        related_name="prelevement_zones",
    )
    label = models.CharField(
        max_length=120,
        help_text="Nom court de la zone (ex : « Mermoz », « Plateau », « Banlieue »).",
    )
    forfait_fcfa = models.PositiveIntegerField(
        default=0,
        help_text="Tarif du déplacement en FCFA (0 = gratuit).",
    )
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "label"]
        unique_together = ("organisme", "label")
        verbose_name = "Zone de prestation à domicile"
        verbose_name_plural = "Zones de prestation à domicile"

    def __str__(self):
        return f"{self.organisme.name} — {self.label}"


class SubscriptionPlan(models.Model):
    """Formule d'abonnement : tarif indicatif et liste de fonctionnalités incluses."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    long_description = models.TextField(blank=True)
    monthly_price_fcfa = models.PositiveIntegerField(
        default=0,
        help_text="Montant mensuel indicatif en FCFA (0 = gratuit). Pas de prélèvement automatique.",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Attribuée aux nouvelles structures si aucune autre logique.",
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Visible sur la page « Abonnement » côté structure.",
    )
    is_pioneer_offer = models.BooleanField(
        default=False,
        help_text="Affiche un badge type « Partenaire Pionnier » dans l'UI.",
    )
    trial_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Durée d'essai en mois (affichage seulement).",
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Formule d'abonnement"
        verbose_name_plural = "Formules d'abonnement"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:135]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SubscriptionPlanFeature(models.Model):
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="plan_features",
    )
    feature = models.ForeignKey(
        SubscriptionFeature,
        on_delete=models.CASCADE,
        related_name="plan_features",
    )
    included = models.BooleanField(
        default=True,
        help_text="Si faux, la ligne sert à documenter une exclusion explicite (rare).",
    )

    class Meta:
        unique_together = ("plan", "feature")
        ordering = ["feature__order", "feature__label"]
        verbose_name = "Fonctionnalité incluse dans la formule"
        verbose_name_plural = "Fonctionnalités incluses par formule"

    def __str__(self):
        return f"{self.plan.name} → {self.feature.label}"


class SubscriptionChangeRequest(models.Model):
    """Demande de changement de formule par la structure — traitement manuel côté admin."""

    STATUS_CHOICES = (
        ("pending", "En attente"),
        ("approved", "Approuvée"),
        ("rejected", "Refusée"),
        ("cancelled", "Annulée par la structure"),
    )
    organisme = models.ForeignKey(
        OrganismeDeSante,
        on_delete=models.CASCADE,
        related_name="subscription_change_requests",
    )
    previous_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Formule au moment de la demande",
    )
    requested_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="change_requests",
        verbose_name="Formule demandée",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    message_from_structure = models.TextField(
        blank=True,
        verbose_name="Message de la structure",
    )
    staff_note = models.TextField(
        blank=True,
        verbose_name="Note interne (équipe MedCare)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_subscription_requests",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande de changement de formule"
        verbose_name_plural = "Demandes de changement de formule"

    def __str__(self):
        return f"{self.organisme.name} → {self.requested_plan.name} ({self.get_status_display()})"


def get_default_subscription_plan():
    """Formule par défaut pour une nouvelle structure."""
    p = SubscriptionPlan.objects.filter(is_default=True).first()
    if p:
        return p
    return SubscriptionPlan.objects.order_by("order", "pk").first()
