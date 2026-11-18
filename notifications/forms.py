from django import forms
from django.db.models.functions import Lower

from .models import NotificationRule, NotificationSettings

TW = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-200 focus:outline-none"
TW_TEXTAREA = TW + " resize-y"

# Zone d’édition wa.me : fond blanc explicite (évite tout effet « lecture seule » visuel).
WA_ME_TEXTAREA = (
    "block w-full min-h-[12rem] rounded-xl border border-gray-300 bg-white px-4 py-3 "
    "text-sm leading-relaxed text-gray-900 shadow-sm "
    "placeholder:text-gray-400 focus:border-accent-400 focus:outline-none focus:ring-2 focus:ring-accent-200 "
    "resize-y font-sans"
)


class SmtpSettingsForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        fields = (
            "email_enabled",
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_password",
            "smtp_use_tls",
            "smtp_use_ssl",
            "smtp_from_email",
            "smtp_from_name",
            "smtp_reply_to",
        )
        widgets = {
            "smtp_host": forms.TextInput(attrs={"class": TW, "placeholder": "smtp.exemple.com"}),
            "smtp_port": forms.NumberInput(attrs={"class": TW, "placeholder": "587"}),
            "smtp_user": forms.TextInput(attrs={"class": TW, "autocomplete": "off"}),
            "smtp_password": forms.PasswordInput(
                render_value=True,
                attrs={"class": TW, "autocomplete": "new-password"},
            ),
            "smtp_from_email": forms.EmailInput(attrs={"class": TW, "placeholder": "no-reply@medcare.com"}),
            "smtp_from_name": forms.TextInput(attrs={"class": TW, "placeholder": "MedCare"}),
            "smtp_reply_to": forms.EmailInput(attrs={"class": TW, "placeholder": "support@medcare.com"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("smtp_use_ssl") and cleaned.get("smtp_use_tls"):
            raise forms.ValidationError("SSL et TLS sont mutuellement exclusifs.")
        if cleaned.get("email_enabled") and not cleaned.get("smtp_host"):
            raise forms.ValidationError("Renseignez l'hôte SMTP avant d'activer l'email.")
        if cleaned.get("email_enabled") and not cleaned.get("smtp_from_email"):
            raise forms.ValidationError("L'adresse expéditeur est requise pour activer l'email.")
        return cleaned


class WhatsAppSettingsForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        fields = (
            "whatsapp_enabled",
            "wa_phone_number_id",
            "wa_business_account_id",
            "wa_access_token",
            "wa_api_version",
        )
        widgets = {
            "wa_phone_number_id": forms.TextInput(attrs={"class": TW, "placeholder": "1234567890"}),
            "wa_business_account_id": forms.TextInput(attrs={"class": TW}),
            "wa_access_token": forms.Textarea(
                attrs={"class": TW_TEXTAREA, "rows": 3, "autocomplete": "off"}
            ),
            "wa_api_version": forms.TextInput(attrs={"class": TW, "placeholder": "v20.0"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("whatsapp_enabled"):
            if not cleaned.get("wa_phone_number_id"):
                raise forms.ValidationError("Phone number ID requis pour activer WhatsApp Cloud.")
            if not cleaned.get("wa_access_token"):
                raise forms.ValidationError("Access token requis pour activer WhatsApp Cloud.")
        return cleaned


class GeneralSettingsForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        fields = ("in_app_enabled", "log_retention_days", "google_reviews_url")
        widgets = {
            "log_retention_days": forms.NumberInput(attrs={"class": TW, "min": 1}),
            "google_reviews_url": forms.URLInput(
                attrs={
                    "class": TW,
                    "placeholder": "https://g.page/.../review ou lien avis Google",
                }
            ),
        }


class PatientWaMeTemplatesForm(forms.ModelForm):
    """Textes préremplis pour les liens wa.me (fiche organisme, côté patient)."""

    class Meta:
        model = NotificationSettings
        fields = (
            "patient_wa_me_message_general",
            "patient_wa_me_message_acte",
            "patient_wa_me_message_devis_formal",
        )
        widgets = {
            "patient_wa_me_message_general": forms.Textarea(
                attrs={
                    "class": WA_ME_TEXTAREA,
                    "rows": 6,
                    "spellcheck": "true",
                    "autocomplete": "off",
                }
            ),
            "patient_wa_me_message_acte": forms.Textarea(
                attrs={
                    "class": WA_ME_TEXTAREA,
                    "rows": 6,
                    "spellcheck": "true",
                    "autocomplete": "off",
                }
            ),
            "patient_wa_me_message_devis_formal": forms.Textarea(
                attrs={
                    "class": WA_ME_TEXTAREA,
                    "rows": 14,
                    "spellcheck": "true",
                    "autocomplete": "off",
                }
            ),
        }

    def clean_patient_wa_me_message_general(self):
        v = (self.cleaned_data.get("patient_wa_me_message_general") or "").strip()
        if not v:
            raise forms.ValidationError("Le message général ne peut pas être vide.")
        return v

    def clean_patient_wa_me_message_acte(self):
        v = (self.cleaned_data.get("patient_wa_me_message_acte") or "").strip()
        if not v:
            raise forms.ValidationError("Le message par examen ne peut pas être vide.")
        return v

    def clean_patient_wa_me_message_devis_formal(self):
        v = (self.cleaned_data.get("patient_wa_me_message_devis_formal") or "").strip()
        if not v:
            raise forms.ValidationError("Le message devis formalisé ne peut pas être vide.")
        return v


class TestEmailForm(forms.Form):
    to_email = forms.EmailField(
        label="Adresse de test",
        widget=forms.EmailInput(attrs={"class": TW, "placeholder": "vous@medcare.com"}),
    )


class TestWhatsAppForm(forms.Form):
    to_number = forms.CharField(
        label="Numéro WhatsApp (+221…)",
        widget=forms.TextInput(attrs={"class": TW, "placeholder": "+221 77 000 00 00"}),
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={"class": TW_TEXTAREA, "rows": 3}),
        initial="Test MedCare — la configuration WhatsApp Cloud est opérationnelle.",
    )


ROLE_CHOICES = (
    (NotificationRule.ROLE_ADMIN, "Admins"),
    (NotificationRule.ROLE_PRESTATAIRE, "Prestataires"),
    (NotificationRule.ROLE_PATIENT, "Patients"),
)

TOGGLE_CBX = "peer sr-only h-px w-px overflow-hidden border-0 p-0 opacity-0"


class NotificationRuleForm(forms.ModelForm):
    target_roles = forms.MultipleChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Rôles destinataires",
    )

    class Meta:
        model = NotificationRule
        fields = (
            "target_roles",
            "target_users",
            "extra_emails",
            "notify_event_actor",
            "is_active",
            "note",
        )
        widgets = {
            "extra_emails": forms.Textarea(attrs={"class": TW_TEXTAREA, "rows": 2}),
            "note": forms.TextInput(attrs={"class": TW}),
            "target_users": forms.SelectMultiple(
                attrs={
                    "class": f"{TW} min-h-[14rem] py-2 font-mono text-[13px]",
                    "size": 14,
                }
            ),
            "notify_event_actor": forms.CheckboxInput(attrs={"class": TOGGLE_CBX}),
            "is_active": forms.CheckboxInput(attrs={"class": TOGGLE_CBX}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["target_roles"].initial = self.instance.target_roles or []
        tu = self.fields["target_users"]
        tu.queryset = tu.queryset.model.objects.filter(is_active=True).order_by(Lower("username"))
        tu.label_from_instance = lambda obj: (
            f"{obj.display_name} ({obj.username})" + (f" — {obj.email}" if obj.email else "")
        )

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.target_roles = list(self.cleaned_data.get("target_roles") or [])
        if commit:
            obj.save()
            self.save_m2m()
        return obj
