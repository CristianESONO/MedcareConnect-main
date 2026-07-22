"""
Icônes et libellés courts des familles d'assurance — alignés démo structures Thior.
"""
from __future__ import annotations

SEGMENT_CATALOG: dict[str, dict[str, str]] = {
    "privee_iard": {
        "icon": "🏢",
        "filter_icon": "✅",
        "chip_label": "Privées traditionnelles",
        "filter_label": "Privées traditionnelles",
        "block_hint": "IARD et assureurs classiques.",
        "badge_color": "#0a5c8a",
    },
    "digitale": {
        "icon": "📱",
        "filter_icon": "🟢",
        "chip_label": "Digitales & plateformes",
        "filter_label": "Digitales & plateformes",
        "block_hint": "Mutuelles modernes, cartes santé, 100 % digital.",
        "badge_color": "#14b87a",
    },
    "regime_public": {
        "icon": "🏛️",
        "filter_icon": "🟠",
        "chip_label": "Régimes publics",
        "filter_label": "Régimes publics & sociaux",
        "block_hint": "CNAM, IPM, CMU, IPRES…",
        "badge_color": "#d97706",
    },
    "mutuelle": {
        "icon": "🤝",
        "filter_icon": "🤝",
        "chip_label": "Mutuelles solidaires",
        "filter_label": "Mutuelles solidaires",
        "block_hint": "Mutualité, communautaires, complémentaires.",
        "badge_color": "#7c3aed",
    },
    "programme": {
        "icon": "📋",
        "filter_icon": "📋",
        "chip_label": "Programmes & initiatives",
        "filter_label": "Programmes & initiatives",
        "block_hint": "Dispositifs ciblés, couvertures spéciales.",
        "badge_color": "#6b7280",
    },
}

DEFAULT_SEGMENT_ICON = "🛡️"


def icon_for_assurance_segment(segment: str) -> str:
    meta = SEGMENT_CATALOG.get(segment or "")
    if meta:
        return meta["icon"]
    return DEFAULT_SEGMENT_ICON


def chip_label_for_assurance_segment(segment: str, fallback: str = "") -> str:
    meta = SEGMENT_CATALOG.get(segment or "")
    if meta:
        return meta["chip_label"]
    return fallback or segment or ""


def block_hint_for_assurance_segment(segment: str) -> str:
    meta = SEGMENT_CATALOG.get(segment or "")
    if meta:
        return meta["block_hint"]
    return ""


def filter_label_for_assurance_segment(segment: str, fallback: str = "") -> str:
    meta = SEGMENT_CATALOG.get(segment or "")
    if meta:
        return meta.get("filter_label") or meta.get("chip_label", "")
    return fallback or segment or ""


def filter_icon_for_assurance_segment(segment: str) -> str:
    meta = SEGMENT_CATALOG.get(segment or "")
    if meta:
        return meta.get("filter_icon") or meta.get("icon", DEFAULT_SEGMENT_ICON)
    return DEFAULT_SEGMENT_ICON
