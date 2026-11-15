from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

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


# ─── Nouveaux Tags Unifiés (Phase 3) ─────────────────────────────────────────

@register.filter
def fcfa(value: Any, suffix: str = "FCFA") -> str:
    """Formate un montant avec séparateur d'espace pour les milliers (ex: 15 000 FCFA)."""
    if value is None or value == "":
        return ""
    try:
        from decimal import Decimal, ROUND_HALF_UP
        val = int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        formatted = f"{val:,}".replace(",", " ")
        return f"{formatted} {suffix}".strip() if suffix else formatted
    except Exception:
        return f"{value} {suffix}".strip() if suffix else str(value)


@register.filter
def insurance_summary(names: Optional[Iterable[Any]], max_count: int = 3) -> str:
    """Résume une liste d'assurances partenaires (ex: AXA · Allianz · Ascoma +2)."""
    if not names:
        return "Assurances non renseignées"
    try:
        names_list = list(names)
    except TypeError:
        return str(names)
    if not names_list:
        return "Assurances non renseignées"
    try:
        max_c = int(max_count)
    except (ValueError, TypeError):
        max_c = 3
    shown = names_list[:max_c]
    text = " · ".join(str(n) for n in shown)
    remaining = len(names_list) - max_c
    if remaining > 0:
        text += f" +{remaining}"
    return text


@register.simple_tag
def org_status_badge(org: Any, is_pioneer: Optional[bool] = None) -> str:
    """
    Génère le badge HTML standardisé pour le statut d'une structure médicale
    (En attente d'approbation / Pionnier / Vérifié).
    """
    if not org:
        return ""
    is_verified = getattr(org, "is_verified", True)
    if not is_verified:
        return mark_safe(
            '<span class="unverified-badge sipn-ico-inline" '
            'style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700" '
            'title="Cette structure est en attente d\'approbation par MedCare Connect">'
            '<i class="ti ti-clock"></i> En attente d\'approbation</span>'
        )

    pioneer = False
    if is_pioneer is not None:
        pioneer = bool(is_pioneer)
    else:
        sub = getattr(org, "subscription_plan", None)
        if sub and getattr(sub, "is_pioneer_offer", False):
            pioneer = True

    if pioneer:
        return mark_safe(
            '<span class="pioneer-badge sipn-ico-inline" '
            'style="background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700">'
            '<i class="ti ti-star"></i> Pionnier</span>'
        )
    else:
        return mark_safe(
            '<span class="verified-badge sipn-ico-inline" '
            'style="background:#e8faf3;color:#065f46;border:1px solid #a7f3d0;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700">'
            '<i class="ti ti-check"></i> Vérifié</span>'
        )


@register.simple_tag
def coverage_badge(matching_count: Any, total_actes: Any) -> str:
    """Génère le badge de taux de couverture multi-actes (ex: 2/3 actes)."""
    try:
        tot = int(total_actes)
        mat = int(matching_count)
    except (TypeError, ValueError):
        return ""
    if tot <= 1:
        return ""
    full = (mat == tot)
    badge_cls = "scard-coverage--full" if full else "scard-coverage--partial"
    plural = "s" if tot > 1 else ""
    return mark_safe(
        f'<span class="scard-coverage scard-m-coverage {badge_cls}">{mat}/{tot} acte{plural}</span>'
    )


@register.simple_tag
def delai_badge(delai_or_pa: Any) -> str:
    """Génère le badge HTML standardisé de délai indicatif."""
    if not delai_or_pa:
        return ""
    if hasattr(delai_or_pa, "get_delai_display"):
        txt = delai_or_pa.get_delai_display()
    else:
        txt = str(delai_or_pa)
    if not txt or txt.lower() in ("none", ""):
        return ""
    return mark_safe(
        f'<span class="scard-delai sipn-ico-inline"><i class="ti ti-clock"></i> {escape(txt)}</span>'
    )
