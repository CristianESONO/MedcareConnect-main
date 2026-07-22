from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.core.files.uploadedfile import UploadedFile
from .models import User, PatientProfile
from healthcare.models import Region
from healthcare.organisme_types import TypeOrganismeSelectWidget, type_organisme_queryset


TAILWIND_INPUT = "w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-900 shadow-sm transition focus:border-accent-400 focus:ring-2 focus:ring-accent-400/20 focus:outline-none"
TAILWIND_SELECT = TAILWIND_INPUT
PAC_INPUT = "pac-profil-input"


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": TAILWIND_INPUT, "placeholder": "votre@email.com"}))
    user_type = forms.ChoiceField(
        choices=[("patient", "Patient"), ("prestataire", "Prestataire de Santé")],
        widget=forms.Select(attrs={"class": TAILWIND_SELECT, "id": "id_user_type"}),
    )
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "+221 77 000 00 00"}))

    # Champs établissement (requis si prestataire)
    organisme_name = forms.CharField(
        label="Nom commercial / enseigne",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "Ex : Clinique Les Almadies"}),
    )
    organisme_raison_sociale = forms.CharField(
        label="Raison sociale (légale)",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "Si différent du nom affiché"}),
    )
    organisme_type = forms.ModelChoiceField(
        label="Type d'établissement",
        queryset=type_organisme_queryset(),
        required=False,
        empty_label="— Choisir —",
        help_text="Indépendant, imagerie, clinique, hôpital, laboratoire, etc.",
        widget=TypeOrganismeSelectWidget(attrs={"class": TAILWIND_SELECT, "id": "id_organisme_type"}),
    )
    organisme_address = forms.CharField(
        label="Adresse du siège / établissement",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "Rue, numéro"}),
    )
    organisme_quartier = forms.CharField(
        label="Quartier",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": TAILWIND_INPUT}),
    )
    organisme_city = forms.CharField(
        label="Ville",
        max_length=100,
        required=False,
        initial="Dakar",
        widget=forms.TextInput(attrs={"class": TAILWIND_INPUT}),
    )
    organisme_region = forms.ModelChoiceField(
        label="Région",
        queryset=Region.objects.all(),
        required=False,
        empty_label="— Optionnel —",
        widget=forms.Select(attrs={"class": TAILWIND_SELECT}),
    )
    organisme_contact_phone = forms.CharField(
        label="Téléphone professionnel",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "+221 33 …"}),
    )
    organisme_contact_email = forms.EmailField(
        label="Email de l'établissement",
        required=False,
        widget=forms.EmailInput(attrs={"class": TAILWIND_INPUT, "placeholder": "contact@etablissement.sn"}),
    )
    organisme_ninea = forms.CharField(
        label="NINEA (optionnel)",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "Numéro d'identification entreprise"}),
    )
    organisme_logo = forms.ImageField(
        label="Logo / photo de l'établissement",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": TAILWIND_INPUT, "accept": "image/*"}
        ),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "user_type",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("username", "first_name", "last_name", "password1", "password2"):
            self.fields[field_name].widget.attrs.update({"class": TAILWIND_INPUT})
        self.fields["organisme_type"].queryset = type_organisme_queryset()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("user_type") == "prestataire":
            if not cleaned.get("organisme_name"):
                self.add_error("organisme_name", "Le nom commercial de l'établissement est obligatoire pour un prestataire.")
            if not cleaned.get("organisme_type"):
                self.add_error("organisme_type", "Veuillez indiquer le type d'établissement.")
            if not cleaned.get("organisme_address"):
                self.add_error("organisme_address", "L'adresse de l'établissement est obligatoire.")
            if not cleaned.get("organisme_contact_phone"):
                self.add_error("organisme_contact_phone", "Un téléphone professionnel est obligatoire.")
            if not self.files.get("organisme_logo"):
                self.add_error(
                    "organisme_logo",
                    "Le logo (photo) de l'établissement est obligatoire.",
                )
        return cleaned


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone_number", "avatar")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": TAILWIND_INPUT}),
            "last_name": forms.TextInput(attrs={"class": TAILWIND_INPUT}),
            "email": forms.EmailInput(attrs={"class": TAILWIND_INPUT}),
            "phone_number": forms.TextInput(attrs={"class": TAILWIND_INPUT}),
            "avatar": forms.ClearableFileInput(
                attrs={"class": TAILWIND_INPUT, "accept": "image/*"}
            ),
        }

    def __init__(self, *args, compte_style=False, **kwargs):
        super().__init__(*args, **kwargs)
        if compte_style:
            for name in ("first_name", "last_name", "email", "phone_number"):
                if name in self.fields:
                    self.fields[name].widget.attrs["class"] = PAC_INPUT

    def clean(self):
        cleaned = super().clean()
        user = getattr(self, "instance", None)
        if user and user.pk and user.is_prestataire:
            val = cleaned.get("avatar")
            has_existing = bool(
                getattr(user, "avatar", None) and getattr(user.avatar, "name", None)
            )
            if val is False:
                self.add_error(
                    "avatar",
                    "La photo de profil est obligatoire pour les prestataires.",
                )
            elif not isinstance(val, UploadedFile) and not has_existing:
                self.add_error(
                    "avatar",
                    "La photo de profil est obligatoire pour les prestataires.",
                )
        return cleaned


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = (
            "date_of_birth", "gender", "address", "city", "quartier",
            "insurance", "insurance_number",
            "last_known_latitude", "last_known_longitude",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"class": TAILWIND_INPUT, "type": "date"}),
            "gender": forms.Select(attrs={"class": TAILWIND_SELECT}),
            "address": forms.TextInput(attrs={"class": TAILWIND_INPUT}),
            "city": forms.TextInput(attrs={"class": TAILWIND_INPUT}),
            "quartier": forms.TextInput(attrs={"class": TAILWIND_INPUT}),
            "insurance": forms.Select(attrs={"class": TAILWIND_SELECT}),
            "insurance_number": forms.TextInput(attrs={"class": TAILWIND_INPUT}),
            "last_known_latitude": forms.NumberInput(attrs={"class": TAILWIND_INPUT, "placeholder": "14.7167", "step": "any"}),
            "last_known_longitude": forms.NumberInput(attrs={"class": TAILWIND_INPUT, "placeholder": "-17.4677", "step": "any"}),
        }


class PatientProfileCompteForm(forms.ModelForm):
    """Profil patient — onglet « Profil » Mon compte (sans assurance)."""

    class Meta:
        model = PatientProfile
        fields = ("date_of_birth", "address", "city", "quartier")
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"class": PAC_INPUT, "type": "date"}),
            "address": forms.TextInput(attrs={"class": PAC_INPUT}),
            "city": forms.TextInput(attrs={"class": PAC_INPUT, "placeholder": "Dakar"}),
            "quartier": forms.TextInput(attrs={"class": PAC_INPUT, "placeholder": "Ex. Mermoz"}),
        }


class PatientInsuranceForm(forms.ModelForm):
    """Assurance patient — onglet « Assurance » Mon compte."""

    insurance_coverage_pct = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=100,
        decimal_places=2,
        max_digits=5,
        label="Taux global de prise en charge",
        help_text="Pourcentage appliqué par défaut à vos estimations panier et devis.",
        widget=forms.NumberInput(
            attrs={
                "class": PAC_INPUT,
                "min": "0",
                "max": "100",
                "step": "0.5",
                "placeholder": "ex. 70",
                "inputmode": "decimal",
            }
        ),
    )
    insurance_use_in_estimates = forms.BooleanField(
        required=False,
        label="Inclure mon assurance dans les estimations",
        help_text="Panier, devis et bandeau de couverture sur la recherche. Décochez pour n'afficher que les tarifs bruts.",
        widget=forms.CheckboxInput(attrs={"class": "pac-ins-estimate-cb"}),
    )

    class Meta:
        model = PatientProfile
        fields = ("insurance", "insurance_number")
        widgets = {
            "insurance": forms.Select(attrs={"class": PAC_INPUT}),
            "insurance_number": forms.TextInput(
                attrs={"class": PAC_INPUT, "placeholder": "N° carte / adhérent"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from healthcare.models import Assurance
        from healthcare.coverage import reference_rates_for_assurance
        from django.utils.text import slugify

        self.fields["insurance"].queryset = Assurance.objects.filter(
            is_active=True
        ).order_by("segment", "name")
        self.fields["insurance"].empty_label = "— Choisissez votre organisme —"

        if self.instance.pk and self.instance.insurance_coverage_pct is not None:
            self.fields["insurance_coverage_pct"].initial = self.instance.insurance_coverage_pct
        if self.instance.pk:
            self.fields["insurance_use_in_estimates"].initial = self.instance.insurance_use_in_estimates

        self._category_field_map: dict[str, str] = {}
        by_cat = dict(self.instance.insurance_coverage_by_category or {})

        insurance_for_cats = self.instance.insurance
        if self.data.get("insurance"):
            try:
                insurance_for_cats = Assurance.objects.get(
                    pk=int(self.data.get("insurance")), is_active=True
                )
            except (ValueError, Assurance.DoesNotExist, TypeError):
                insurance_for_cats = self.instance.insurance

        ref = (
            reference_rates_for_assurance(insurance_for_cats)
            if insurance_for_cats
            else {}
        )
        categories = sorted(set(list(by_cat.keys()) + list(ref.keys())))
        for cat in categories:
            slug = slugify(cat) or "cat"
            field_name = f"cat_rate__{slug}"
            self._category_field_map[field_name] = cat
            initial = by_cat.get(cat)
            if initial is None and cat in ref:
                initial = ref[cat]
            self.fields[field_name] = forms.DecimalField(
                required=False,
                min_value=0,
                max_value=100,
                decimal_places=2,
                max_digits=5,
                label=cat,
                initial=initial,
                widget=forms.NumberInput(
                    attrs={
                        "class": PAC_INPUT,
                        "min": "0",
                        "max": "100",
                        "step": "0.5",
                        "placeholder": str(ref.get(cat, "")) if ref.get(cat) else "—",
                        "inputmode": "decimal",
                        "data-coverage-cat": cat,
                    }
                ),
            )

    @property
    def category_rate_fields(self):
        """Champs taux par catégorie (hors Meta.fields)."""
        return [
            (name, self[name])
            for name in self.fields
            if name.startswith("cat_rate__")
        ]

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.insurance_coverage_pct = self.cleaned_data.get("insurance_coverage_pct")
        profile.insurance_use_in_estimates = bool(
            self.cleaned_data.get("insurance_use_in_estimates")
        )

        by_cat = {}
        for field_name, cat in self._category_field_map.items():
            val = self.cleaned_data.get(field_name)
            if val is not None:
                by_cat[cat] = float(val)
        profile.insurance_coverage_by_category = by_cat

        if commit:
            profile.save()
        return profile


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, compte_style=False, **kwargs):
        super().__init__(*args, **kwargs)
        css = PAC_INPUT if compte_style else TAILWIND_INPUT
        for name, field in self.fields.items():
            field.widget.attrs.update({"class": css})
            if compte_style and name in ("new_password1", "new_password2"):
                field.widget.attrs.setdefault(
                    "placeholder", "Laisser vide pour ne pas modifier"
                )
