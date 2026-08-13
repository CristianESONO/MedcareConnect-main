"""Helpers UI ambulance patient — alignés DEMO_DESKTOP_PATIENT.html."""

from __future__ import annotations


def is_ambulance_acte_name(name: str) -> bool:
    """True si le libellé d'acte relève du pilier ambulance (transport, rapatriement, couverture)."""
    low = (name or "").lower()
    if not low:
        return False
    keys = (
        "ambulance",
        "transport réanimatoire",
        "transport reanimatoire",
        "évacuation sanitaire",
        "evacuation sanitaire",
        "rapatriement",
        "couverture médicale",
        "couverture medicale",
        "assistance médicale",
        "assistance medicale",
    )
    return any(k in low for k in keys)


def ambulance_acte_flow(name: str) -> str:
    """Retourne le flux configurateur : trajet | rapatriement | evenement."""
    low = (name or "").lower()
    if any(k in low for k in ("couverture", "événement", "evenement", "assistance", "manifestation", "sportive")):
        return "evenement"
    if any(k in low for k in ("rapatriement", "évacuation", "evacuation")):
        return "rapatriement"
    return "trajet"


def ambulance_configure_label(name: str) -> str:
    flow = ambulance_acte_flow(name)
    if flow == "evenement":
        return "🩺 Configurer ma couverture"
    if flow == "rapatriement":
        return "🌍 Organiser le rapatriement"
    return "🚑 Configurer mon trajet"


def ambulance_configure_short(name: str, *, sur_devis: bool = False) -> str:
    if sur_devis:
        return "Devis personnalisé"
    return "Configurer →"


def ambulance_price_hint(name: str, *, sur_devis: bool = False) -> str:
    if sur_devis:
        return "Devis personnalisé selon la destination et le mode de transport."
    flow = ambulance_acte_flow(name)
    if flow == "evenement":
        return "Tarif selon la durée et le dispositif médical. À préciser lors de la configuration."
    if flow == "rapatriement":
        return "Tarif selon la distance et le mode de transport."
    return (
        "Tarif selon la distance parcourue (facturation au km). "
        "Le montant final dépend du trajet que vous configurez."
    )


def ambulance_sur_devis(name: str, price) -> bool:
    low = (name or "").lower()
    if "international" in low:
        return True
    try:
        return float(price or 0) <= 0
    except (TypeError, ValueError):
        return False
