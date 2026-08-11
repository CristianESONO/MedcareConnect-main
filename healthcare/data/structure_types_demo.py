"""
Types de structure et piliers applicables — aligné DEMO_STRUCTURES.html (TYPE_STRUCTURE_MATRIX).

Référence démo : dossierthior/newretours/DEMO_STRUCTURES.html (~l.2938)
"""

from __future__ import annotations

# Clés piliers démo → slugs ServiceMedical (slugify du nom canonique)
PILIER_KEY_TO_SLUG: dict[str, str] = {
    "biologie": "biologie-medicale",
    "imagerie": "imagerie-medicale",
    "explorations": "explorations-fonctionnelles",
    "ambulance": "ambulance-medicalisee",
    "soins": "soins-specialises",
    "dentaire": "soins-dentaires",
}

ALL_PILIER_KEYS: tuple[str, ...] = (
    "biologie",
    "imagerie",
    "explorations",
    "ambulance",
    "soins",
    "dentaire",
)

# 8 types démo — ordre et libellés identiques à la démo
DEMO_STRUCTURE_TYPES: tuple[dict, ...] = (
    {
        "key": "labo",
        "icon": "🔬",
        "label": "Laboratoire d'analyses",
        "desc": "Pilier actif : Biologie médicale",
        "pilier_keys": ("biologie",),
    },
    {
        "key": "imagerie",
        "icon": "🩻",
        "label": "Cabinet d'imagerie",
        "desc": "Pilier actif : Imagerie médicale",
        "pilier_keys": ("imagerie",),
    },
    {
        "key": "cabinet",
        "icon": "🩺",
        "label": "Cabinet spécialisé",
        "desc": "Piliers actifs : Explorations fonctionnelles · Soins spécialisés",
        "pilier_keys": ("explorations", "soins"),
    },
    {
        "key": "dentaire",
        "icon": "🦷",
        "label": "Cabinet dentaire",
        "desc": "Pilier actif : Soins dentaires",
        "pilier_keys": ("dentaire",),
    },
    {
        "key": "ambulance",
        "icon": "🚑",
        "label": "Service d'ambulance",
        "desc": "Pilier actif : Services d'ambulance",
        "pilier_keys": ("ambulance",),
    },
    {
        "key": "clinique",
        "icon": "🏥",
        "label": "Clinique",
        "desc": "Piliers actifs : Biologie · Imagerie · Explorations · Soins spécialisés",
        "pilier_keys": ("biologie", "imagerie", "explorations", "soins"),
    },
    {
        "key": "hopital",
        "icon": "🏨",
        "label": "Hôpital",
        "desc": "Tous les piliers actifs",
        "pilier_keys": ALL_PILIER_KEYS,
    },
    {
        "key": "multi",
        "icon": "⚙️",
        "label": "Multi-activités",
        "desc": "Sélection manuelle des piliers",
        "pilier_keys": ALL_PILIER_KEYS,
    },
)

_DEMO_BY_KEY: dict[str, dict] = {row["key"]: row for row in DEMO_STRUCTURE_TYPES}

# TypeOrganisme.name (base) → clé démo
ORG_TYPE_TO_DEMO_KEY: dict[str, str] = {
    # Noms génériques (anciens)
    "Laboratoire": "labo",
    "Centre d'imagerie": "imagerie",
    "Cabinet médical": "cabinet",
    "Cabinet de kinésithérapie": "cabinet",
    "Centre de dialyse": "cabinet",
    "Cabinet santé mentale": "cabinet",
    "Praticien indépendant": "cabinet",
    "Cabinet dentaire": "dentaire",
    "Service ambulancier": "ambulance",
    "Clinique": "clinique",
    "Hôpital": "hopital",
    "Centre de santé": "multi",
    "Pharmacie": "multi",
    # Noms détaillés (base de démo actuelle)
    "Ambulance médicalisée — Transport & SMUR": "ambulance",
    "Laboratoire d'analyses médicales": "labo",
    "Laboratoire — Fertilité, Immunologie & PCR": "labo",
    "Laboratoire spécialisé — Anapath & Cytologie": "labo",
    "Laboratoire d'analyses médicales — Centre hospitalier": "labo",
    "Laboratoire hospitalier privé": "labo",
    "Imagerie — Écho · Radio · Scanner · IRM": "imagerie",
    "Centre d'imagerie médicale": "imagerie",
    "Centre d'imagerie interventionnelle": "imagerie",
    "Explorations fonctionnelles — Cardiologie & Pneumologie": "cabinet",
    "Explorations fonctionnelles — Neurologie, ORL, Ophtalmo": "cabinet",
    "Centre d'exploration fonctionnelle": "cabinet",
    "Kinésithérapie & rééducation fonctionnelle": "cabinet",
    "Centre de santé mentale": "cabinet",
    "Cabinet ou centre dentaire": "dentaire",
    "Cabinet dentaire — Soins complets & Esthétique": "dentaire",
    "Clinique E2E": "clinique",
    "Clinique privée — Soins spécialisés pluridisciplinaires": "clinique",
}


def demo_key_for_type_name(type_name: str) -> str | None:
    """Retourne la clé démo pour un nom TypeOrganisme, ou None si inconnu."""
    if not type_name:
        return None
    return ORG_TYPE_TO_DEMO_KEY.get(type_name)


def demo_structure_for_type_name(type_name: str) -> dict | None:
    key = demo_key_for_type_name(type_name)
    if key is None:
        return None
    return _DEMO_BY_KEY.get(key)


def pilier_slugs_for_demo_key(demo_key: str) -> set[str]:
    row = _DEMO_BY_KEY.get(demo_key)
    if row is None:
        return set()
    return {PILIER_KEY_TO_SLUG[k] for k in row["pilier_keys"]}
