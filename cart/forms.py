from __future__ import annotations

from django import forms
from django_select2.forms import Select2Widget

from healthcare.models import Assurance


TAILWIND_SELECT = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent-400 focus:ring-2 focus:ring-accent-400/20 focus:outline-none"


class AssuranceSelect2Widget(Select2Widget):
    """Select2 non-AJAX : toutes les options dans le HTML, filtrage côté client."""

    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop("attrs", {}) or {}
        attrs.setdefault("class", TAILWIND_SELECT + " django-select2")
        attrs.setdefault("data-placeholder", "Rechercher une assurance…")
        attrs.setdefault("data-minimum-results-for-search", 0)
        attrs.setdefault("data-width", "100%")
        super().__init__(attrs=attrs, *args, **kwargs)


class GuestInsuranceSelectForm(forms.Form):
    insurance = forms.ModelChoiceField(
        queryset=Assurance.objects.filter(is_active=True).order_by("segment", "name"),
        required=False,
        empty_label="Sans assurance",
        widget=AssuranceSelect2Widget,
    )


class CartInsuranceSelectForm(forms.Form):
    insurance = forms.ModelChoiceField(
        queryset=Assurance.objects.filter(is_active=True).order_by("segment", "name"),
        required=False,
        empty_label="Sans assurance",
        widget=AssuranceSelect2Widget,
    )
