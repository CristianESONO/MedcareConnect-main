from django import forms
from django.db.models import Count, Q
from django_select2.forms import Select2MultipleWidget, Select2Widget

from appointments.models import RdvReminderSchedule

from .organisme_types import type_organisme_queryset
from .models import (
    OrganismeDeSante,
    PrestataireActe,
    PriseEnChargeAssurance,
    ActeMedical,
    SubscriptionPlan,
    SubscriptionChangeRequest,
)

TW = "w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-900 shadow-sm transition focus:border-accent-400 focus:ring-2 focus:ring-accent-400/20 focus:outline-none"
ORG_TW = (
    "w-full rounded-xl border border-gray-200 bg-gray-50/60 px-4 py-2.5 text-sm text-gray-900 "
    "shadow-sm transition placeholder:text-gray-400 "
    "focus:border-primary-400 focus:bg-white focus:ring-2 focus:ring-primary-400/20 focus:outline-none"
)


class ActeSelect2Widget(Select2Widget):
    """Select2 non-AJAX : toutes les options dans le HTML, filtrage côté client."""

    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop("attrs", {}) or {}
        attrs.setdefault("class", TW + " django-select2")
        attrs.setdefault("data-placeholder", "Rechercher un acte…")
        attrs.setdefault("data-minimum-results-for-search", 0)
        attrs.setdefault("data-width", "100%")
        super().__init__(attrs=attrs, *args, **kwargs)


class ActeSelect2MultipleWidget(Select2MultipleWidget):
    """Select2 multi — actes ciblés (admin rappels RDV, etc.)."""

    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop("attrs", {}) or {}
        attrs.setdefault("class", TW + " django-select2")
        attrs.setdefault("data-placeholder", "Rechercher des actes…")
        attrs.setdefault("data-minimum-results-for-search", 0)
        attrs.setdefault("data-width", "100%")
        attrs.setdefault("data-close-on-select", "false")
        super().__init__(attrs=attrs, *args, **kwargs)


class OrganismeForm(forms.ModelForm):
    class Meta:
        model = OrganismeDeSante
        fields = (
            "name", "raison_sociale", "ninea", "type_organisme", "profession",
            "address", "quartier", "city", "region",
            "latitude", "longitude", "contact_email", "contact_phone",
            "whatsapp_number", "description", "website", "logo",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type_organisme"].queryset = type_organisme_queryset()
        for name, f in self.fields.items():
            if isinstance(f.widget, forms.Textarea):
                f.widget.attrs.update({"class": ORG_TW, "rows": 4})
            elif name == "logo":
                f.widget = forms.ClearableFileInput(
                    attrs={"accept": "image/*", "class": "org-edit-logo-input"}
                )
            elif isinstance(f.widget, forms.ClearableFileInput):
                f.widget.attrs.update({"class": ORG_TW + " file:mr-4 file:rounded-lg file:border-0 file:bg-primary-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary-800 hover:file:bg-primary-100", "accept": "image/*"})
            else:
                f.widget.attrs.update({"class": ORG_TW})
            if name == "description":
                f.widget.attrs.setdefault("placeholder", "Présentez votre établissement en quelques lignes…")
            elif name == "name":
                f.widget.attrs.setdefault("placeholder", "Ex. Clinique du Plateau")
            elif name == "whatsapp_number":
                f.widget.attrs.setdefault("placeholder", "+221 77 000 00 00")
        inst = self.instance
        if inst and not getattr(inst, "logo", None):
            self.fields["logo"].required = True
            self.fields["logo"].label = "Logo / photo de l'établissement (obligatoire)"


class OpeningHoursForm(forms.Form):
    DAYS = [
        ("Lundi", "Lundi"), ("Mardi", "Mardi"), ("Mercredi", "Mercredi"),
        ("Jeudi", "Jeudi"), ("Vendredi", "Vendredi"),
        ("Samedi", "Samedi"), ("Dimanche", "Dimanche"),
    ]
    def __init__(self, *args, initial_data=None, **kwargs):
        super().__init__(*args, **kwargs)
        data = initial_data or {}
        for code, label in self.DAYS:
            self.fields[f"{code}_open"] = forms.CharField(
                max_length=5, required=False,
                initial=data.get(code, {}).get("open", ""),
                widget=forms.TextInput(attrs={"class": TW, "placeholder": "08:00"}),
            )
            self.fields[f"{code}_close"] = forms.CharField(
                max_length=5, required=False,
                initial=data.get(code, {}).get("close", ""),
                widget=forms.TextInput(attrs={"class": TW, "placeholder": "17:00"}),
            )
            self.fields[f"{code}_closed"] = forms.BooleanField(
                required=False,
                initial=data.get(code, {}).get("closed", False),
            )

    def get_hours_dict(self):
        result = {}
        for code, _ in self.DAYS:
            result[code] = {
                "open": self.cleaned_data.get(f"{code}_open", ""),
                "close": self.cleaned_data.get(f"{code}_close", ""),
                "closed": self.cleaned_data.get(f"{code}_closed", False),
            }
        return result


def presta_acte_choice_label(acte: ActeMedical) -> str:
    """Libellé hiérarchique complet (service › … › acte)."""
    parts = [acte.service_medical_category.name]
    ancestors = []
    p = acte.parent_service
    depth = 0
    while p is not None and depth < 8:
        ancestors.insert(0, p.name)
        p = p.parent_service
        depth += 1
    parts.extend(ancestors)
    parts.append(acte.name)
    return " › ".join(parts)


def presta_acte_short_label(acte: ActeMedical) -> str:
    """Libellé hiérarchique court (sous-niveaux › acte) ; le formulaire prestataire utilise plutôt optgroup + nom seul."""
    ancestors = []
    p = acte.parent_service
    depth = 0
    while p is not None and depth < 8:
        ancestors.insert(0, p.name)
        p = p.parent_service
        depth += 1
    if ancestors:
        return " › ".join(ancestors + [acte.name])
    return acte.name


class PrestataireActeForm(forms.ModelForm):
    class Meta:
        model = PrestataireActe
        fields = ("acte", "price", "delai", "is_available", "notes")

    def __init__(self, *args, organisme=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisme = organisme
        qs = (
            ActeMedical.objects.filter(is_active=True)
            .select_related(
                "service_medical_category",
                "parent_service",
                "parent_service__parent_service",
                "parent_service__parent_service__parent_service",
                "parent_service__parent_service__parent_service__parent_service",
            )
            .order_by(
                "service_medical_category__order",
                "service_medical_category__name",
                "level",
                "name",
            )
        )
        if organisme:
            taken = PrestataireActe.objects.filter(organisme=organisme)
            if self.instance.pk:
                taken = taken.exclude(pk=self.instance.pk)
            qs = qs.exclude(pk__in=taken.values_list("acte_id", flat=True))
        # Référentiel : niveau 3 = acte spécifique ; niveaux 1–2 ne sont jamais sélectionnables.
        # Feuilles d’arbre : pas de sous-acte actif (défense si données hors catalogue).
        qs = qs.filter(level=3).annotate(
            _presta_sub_act_count=Count(
                "sub_acts", filter=Q(sub_acts__is_active=True)
            )
        ).filter(_presta_sub_act_count=0)
        self.fields["acte"].queryset = qs
        self.fields["acte"].label = "Acte médical"
        self.fields["acte"].help_text = (
            "Recherchez puis choisissez un acte en fin de branche (sans sous-acte) dans la liste."
        )
        self.fields["acte"].label_from_instance = presta_acte_choice_label
        self.fields["acte"].widget = ActeSelect2Widget()
        # Remplacer le widget après queryset ne recopie pas choices ni required (Field ne le fait qu’à l’init).
        acte_field = self.fields["acte"]
        acte_field.widget.is_required = acte_field.required
        acte_field.widget.choices = acte_field.choices

        for name, f in self.fields.items():
            if name == "acte":
                continue
            if isinstance(f.widget, (forms.CheckboxInput,)):
                continue
            if isinstance(f.widget, forms.Textarea):
                f.widget.attrs.update({"class": TW, "rows": 2})
            else:
                f.widget.attrs.update({"class": TW})


class PriseEnChargeAssuranceSelectWidget(Select2Widget):
    """Média Select2 pour l’écran assurances prestataire ; le template rend le <select> manuellement (optgroups + matcher)."""

    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop("attrs", {}) or {}
        attrs.setdefault(
            "class",
            TW + " medcare-prise-assurance-select2",
        )
        attrs.setdefault("data-placeholder", "Rechercher une assurance…")
        attrs.setdefault("data-minimum-results-for-search", 0)
        attrs.setdefault("data-width", "100%")
        super().__init__(attrs=attrs, *args, **kwargs)


class PriseEnChargeForm(forms.ModelForm):
    """Déclaration des assurances acceptées (aucun taux de couverture en base)."""

    class Meta:
        model = PriseEnChargeAssurance
        fields = ("assurance",)
        widgets = {"assurance": PriseEnChargeAssuranceSelectWidget}


class PlatformReviewForm(forms.Form):
    """Avis MedCare centralisé : note + cases par acte (POST `actes`) + champ libre tarifs & délais."""

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    rating = forms.TypedChoiceField(
        label="Votre note",
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )
    tarifs_delais_comment = forms.CharField(
        label="Tarifs & Délais",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": TW,
                "rows": 4,
                "placeholder": "Ex. délais d’attente, transparence des tarifs, accord tiers payant…",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        raw = self.data.getlist("actes")
        ids: list[int] = []
        for x in raw:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        if not ids:
            raise forms.ValidationError(
                "Indiquez au moins un acte ou examen concerné par votre retour (cases à cocher)."
            )
        seen = set()
        uniq_ids = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                uniq_ids.append(i)
        actes = list(
            ActeMedical.objects.filter(
                pk__in=uniq_ids, level=3, is_active=True,
            )
        )
        if len(actes) != len(uniq_ids):
            raise forms.ValidationError("La sélection d’actes contient des entrées non valides.")
        cleaned["actes"] = actes
        return cleaned


class SubscriptionChangeRequestForm(forms.Form):
    """Demande de passage à une autre formule (validation manuelle par l'équipe)."""

    requested_plan = forms.ModelChoiceField(
        label="Formule souhaitée",
        queryset=SubscriptionPlan.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None,
    )
    message_from_structure = forms.CharField(
        label="Message (optionnel)",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": TW,
                "rows": 3,
                "placeholder": "Ex. : nous souhaitons activer les réservations en ligne pour septembre…",
            }
        ),
    )

    def __init__(self, *args, organisme, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisme = organisme
        from healthcare.subscription_admin import catalog_public_plans_qs

        qs = catalog_public_plans_qs()
        if organisme.subscription_plan_id:
            qs = qs.exclude(pk=organisme.subscription_plan_id)
        self.fields["requested_plan"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        if SubscriptionChangeRequest.objects.filter(
            organisme=self.organisme,
            status="pending",
        ).exists():
            raise forms.ValidationError(
                "Une demande est déjà en cours de traitement. Vous pouvez l'annuler "
                "depuis cette page avant d'en envoyer une nouvelle."
            )
        return cleaned


class PrestataireActePrerequisitesForm(forms.ModelForm):
    class Meta:
        model = PrestataireActe
        fields = ("rdv_prerequisites", "rdv_prerequisites_active")
        widgets = {
            "rdv_prerequisites": forms.Textarea(
                attrs={
                    "class": TW,
                    "rows": 6,
                    "placeholder": "Ex. : À jeun 12 h. Apportez ordonnance et pièce d'identité.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rdv_prerequisites_active"].label = "Diffuser au patient"
        self.fields["rdv_prerequisites_active"].help_text = (
            "Inclure ce message dans les rappels RDV automatiques."
        )


class PrestataireRdvReminderScheduleForm(forms.ModelForm):
    class Meta:
        model = RdvReminderSchedule
        fields = (
            "label",
            "offset_value",
            "offset_unit",
            "tolerance_minutes",
            "include_prerequisites",
            "is_active",
            "order",
            "actes",
        )
        widgets = {
            "actes": ActeSelect2MultipleWidget(),
        }

    def __init__(self, *args, organisme=None, **kwargs):
        self.organisme = organisme
        super().__init__(*args, **kwargs)
        actes_field = self.fields["actes"]
        offered = ActeMedical.objects.filter(
            prestataire_actes__organisme=organisme,
            prestataire_actes__is_available=True,
            is_active=True,
            level=3,
        ).select_related("service_medical_category").order_by(
            "service_medical_category__order",
            "service_medical_category__name",
            "name",
        )
        actes_field.queryset = offered
        actes_field.required = False
        actes_field.label_from_instance = lambda a: (
            f"{a.service_medical_category.name} › {a.name}"
            if a.service_medical_category_id
            else a.name
        )
        actes_field.help_text = (
            "Laisser vide pour tous vos RDV. Sinon, uniquement si le RDV contient un de ces actes."
        )
        for name, field in self.fields.items():
            if name == "actes":
                continue
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update(
                    {"class": "h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"}
                )
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": TW, "rows": 3})
            else:
                field.widget.attrs.update({"class": TW})
