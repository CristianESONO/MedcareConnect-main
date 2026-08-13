from django import template

from healthcare.ambulance_ui import (
    ambulance_acte_flow,
    ambulance_configure_label,
    ambulance_configure_short,
    ambulance_price_hint,
    ambulance_sur_devis,
    is_ambulance_acte_name,
)
from healthcare.service_icons import (
    icon_for_service_medical,
    icon_for_subfamily_label,
)

register = template.Library()


@register.filter
def service_icon(service):
    """Icône pilier / famille de soins (emoji démo)."""
    return icon_for_service_medical(service)


@register.filter
def subfamily_icon(label):
    """Icône sous-famille (type niveau 2) pour pastilles catalogue."""
    return icon_for_subfamily_label(label)


@register.filter
def is_ambulance_acte(name):
    return is_ambulance_acte_name(name)


@register.filter
def ambulance_btn_label(name):
    return ambulance_configure_label(name)


@register.filter
def ambulance_hint(name):
    return ambulance_price_hint(name)


@register.filter
def ambulance_flow(name):
    return ambulance_acte_flow(name)


@register.simple_tag
def ambulance_sur_devis_for(name, price):
    return ambulance_sur_devis(name, price)


@register.simple_tag
def ambulance_configure_short_for(name, price):
    return ambulance_configure_short(name, sur_devis=ambulance_sur_devis(name, price))
