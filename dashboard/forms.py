from django import forms

from healthcare.models import (
    Assurance,
    ActeMedical,
    ServiceMedical,
    SubscriptionFeature,
    SubscriptionPlan,
    SubscriptionPlanFeature,
)
from appointments.models import RdvReminderSchedule
from healthcare.forms import ActeSelect2MultipleWidget

TW = (
    "w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-900 "
    "shadow-sm transition focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
)
TW_TA = TW + " min-h-[100px]"


class ServiceMedicalForm(forms.ModelForm):
    class Meta:
        model = ServiceMedical
        fields = ("name", "description", "icon", "image", "order", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": TW_TA, "rows": 4})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update(
                    {"class": "h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"}
                )
            else:
                field.widget.attrs.update({"class": TW})


class ActeMedicalForm(forms.ModelForm):
    class Meta:
        model = ActeMedical
        fields = (
            "name",
            "code",
            "description",
            "rdv_prerequisites",
            "service_medical_category",
            "parent_service",
            "level",
            "reference_price",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": TW_TA, "rows": 4})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update(
                    {"class": "h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"}
                )
            else:
                field.widget.attrs.update({"class": TW})

        self._refresh_parent_queryset()
        if "rdv_prerequisites" in self.fields:
            self.fields["rdv_prerequisites"].widget.attrs.update({"class": TW_TA, "rows": 5})
            self.fields["rdv_prerequisites"].help_text = (
                "Ex. : être à jeun 12 h, apporter ordonnance et carte d'assurance. "
                "Inclus dans les rappels automatiques si activé sur la règle."
            )

    def _refresh_parent_queryset(self):
        parent = self.fields["parent_service"]
        cat_id = None
        if self.data.get("service_medical_category"):
            try:
                cat_id = int(self.data.get("service_medical_category"))
            except (TypeError, ValueError):
                pass
        elif self.instance.pk and self.instance.service_medical_category_id:
            cat_id = self.instance.service_medical_category_id

        qs = ActeMedical.objects.none()
        if cat_id:
            qs = ActeMedical.objects.filter(service_medical_category_id=cat_id).order_by("level", "name")
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
        parent.queryset = qs
        parent.required = False

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent_service")
        cat = cleaned.get("service_medical_category")
        if parent and cat and parent.service_medical_category_id != cat.pk:
            self.add_error(
                "parent_service",
                "L’acte parent doit appartenir au même service médical.",
            )
        return cleaned


class AssuranceForm(forms.ModelForm):
    class Meta:
        model = Assurance
        fields = (
            "name",
            "segment",
            "description",
            "logo",
            "website",
            "contact_phone",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": TW_TA, "rows": 4})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update(
                    {"class": "h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"}
                )
            else:
                field.widget.attrs.update({"class": TW})


class SubscriptionFeatureForm(forms.ModelForm):
    class Meta:
        model = SubscriptionFeature
        fields = ("code", "label", "description", "order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": TW_TA, "rows": 4})
            else:
                field.widget.attrs.update({"class": TW})


class SubscriptionPlanForm(forms.ModelForm):
    included_features = forms.ModelMultipleChoiceField(
        queryset=SubscriptionFeature.objects.order_by("order", "label"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Modules inclus dans la formule",
        help_text=(
            "Cochez les droits affichés sur la page Abonnement (comparaison des offres). "
            "Le verrouillage technique des écrans côté prestataire n'est pas encore branché."
        ),
    )

    class Meta:
        model = SubscriptionPlan
        fields = (
            "name",
            "slug",
            "short_description",
            "long_description",
            "monthly_price_fcfa",
            "is_default",
            "is_public",
            "is_pioneer_offer",
            "trial_months",
            "order",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["slug"].help_text = (
            "Laisser vide pour générer automatiquement à partir du nom."
        )
        self.fields["short_description"].label = "Cible affichée sur la carte"
        self.fields["short_description"].help_text = (
            "Texte sous le nom de la formule (ex. « Structures mono-pilier »). "
            "Prioritaire sur le libellé BIZ-ECO par défaut du slug."
        )
        if self.instance.pk:
            self.fields["included_features"].initial = SubscriptionFeature.objects.filter(
                plan_features__plan=self.instance,
                plan_features__included=True,
            )
        for name, field in self.fields.items():
            if name == "included_features":
                continue
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": TW_TA, "rows": 4})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update(
                    {"class": "h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"}
                )
            else:
                field.widget.attrs.update({"class": TW})

    def _sync_included_features(self, plan):
        selected_ids = {f.pk for f in self.cleaned_data.get("included_features", [])}
        SubscriptionPlanFeature.objects.filter(plan=plan).exclude(
            feature_id__in=selected_ids
        ).delete()
        for feature_id in selected_ids:
            SubscriptionPlanFeature.objects.update_or_create(
                plan=plan,
                feature_id=feature_id,
                defaults={"included": True},
            )

    def save(self, commit=True):
        plan = super().save(commit=commit)
        if commit and "included_features" in self.cleaned_data:
            self._sync_included_features(plan)
        return plan


class RdvReminderScheduleForm(forms.ModelForm):
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

    @staticmethod
    def _acte_choice_label(acte: ActeMedical) -> str:
        svc = getattr(acte.service_medical_category, "name", "") or ""
        return f"{svc} › {acte.name}" if svc else acte.name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        actes_field = self.fields["actes"]
        actes_field.queryset = ActeMedical.objects.filter(
            is_active=True, level=3
        ).select_related("service_medical_category").order_by(
            "service_medical_category__order", "service_medical_category__name", "name"
        )
        actes_field.required = False
        actes_field.label_from_instance = self._acte_choice_label
        actes_field.help_text = (
            "Laisser vide pour tous les RDV. Sinon, la règle ne s'applique qu'aux RDV contenant au moins un de ces actes."
        )
        for name, field in self.fields.items():
            if name == "actes":
                continue
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update(
                    {"class": "h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"}
                )
            else:
                field.widget.attrs.update({"class": TW})
