from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify

from medcare_connect.upload_paths import UploadToUnique


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ("patient", "Patient"),
        ("prestataire", "Prestataire de Santé"),
        ("admin", "Administrateur"),
    )
    user_type = models.CharField(
        max_length=20, choices=USER_TYPE_CHOICES, default="patient"
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(
        upload_to=UploadToUnique("avatars"),
        max_length=255,
        blank=True,
        null=True,
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.username)
            slug = base_slug
            counter = 1
            while User.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    @property
    def is_patient(self):
        return self.user_type == "patient"

    @property
    def is_prestataire(self):
        return self.user_type == "prestataire"

    @property
    def is_admin_user(self):
        return self.user_type == "admin"

    @property
    def display_name(self):
        full = self.get_full_name()
        return full if full else self.username


class PatientProfile(models.Model):
    GENDER_CHOICES = (
        ("M", "Masculin"),
        ("F", "Féminin"),
        ("O", "Autre"),
    )
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="patient_profile"
    )
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True, null=True
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, default="Dakar")
    quartier = models.CharField(max_length=100, blank=True, null=True)
    insurance = models.ForeignKey(
        "healthcare.Assurance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients",
    )
    insurance_number = models.CharField(max_length=100, blank=True, null=True)
    insurance_coverage_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Taux global de prise en charge (0–100 %) pour les estimations panier/devis.",
    )
    insurance_coverage_by_category = models.JSONField(
        default=dict,
        blank=True,
        help_text="Taux par catégorie d'acte (niveau 2), ex. {'Hématologie': 70}.",
    )
    insurance_use_in_estimates = models.BooleanField(
        default=True,
        help_text="Si décoché, les tarifs bruts sont affichés (panier/devis) sans prise en charge estimée.",
    )
    last_known_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True,
        help_text="Dernière position connue pour la recherche à proximité (OpenStreetMap / GPS)",
    )
    last_known_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True,
    )

    class Meta:
        verbose_name = "Profil Patient"
        verbose_name_plural = "Profils Patients"

    def __str__(self):
        return f"Profil de {self.user.username}"
