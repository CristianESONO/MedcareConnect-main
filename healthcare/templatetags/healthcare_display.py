from django import template

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
