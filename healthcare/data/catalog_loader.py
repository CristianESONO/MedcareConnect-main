"""
Charge le catalogue officiel (PDF) en base : Assurance, ServiceMedical, ActeMedical.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

from healthcare.data.catalog_assurances import ASSURANCES_FROM_DOCS
from healthcare.data.catalog_pillars import PILLARS_FROM_DOCS
from healthcare.models import ActeMedical, Assurance, ServiceMedical


def _reference_price_xof(pillar_name: str, acte_name: str) -> Decimal:
    """Prix indicatif stable (orientation) selon le pilier."""
    bands = {
        "Biologie médicale": (4000, 28000),
        "Imagerie médicale": (15000, 150000),
        "Explorations fonctionnelles": (8000, 45000),
        "Ambulance médicalisée": (15000, 120000),
        "Soins spécialisés": (5000, 45000),
        "Soins dentaires": (8000, 90000),
    }
    lo, hi = bands.get(pillar_name, (5000, 30000))
    h = int(hashlib.md5(f"{pillar_name}|{acte_name}".encode()).hexdigest()[:8], 16)
    val = lo + (h % (hi - lo + 1))
    step = 500
    return Decimal((val // step) * step)


def reset_reference_catalog() -> None:
    """
    Supprime catalogue et offres liées (PEC, prestations).
    Ne supprime pas les comptes utilisateurs ni les organismes.
    """
    from healthcare.models import (
        LotExamenPrefait,
        PriseEnChargeAssurance,
        PrestataireActe,
    )

    LotExamenPrefait.objects.all().delete()
    PrestataireActe.objects.all().delete()
    PriseEnChargeAssurance.objects.all().delete()
    ActeMedical.objects.all().delete()
    ServiceMedical.objects.all().delete()
    Assurance.objects.all().delete()


def load_assurances_from_docs() -> dict[str, Assurance]:
    """Crée ou met à jour les assurances (segment + description)."""
    out: dict[str, Assurance] = {}
    valid_segments = {c.value for c in Assurance.Segment}
    for row in ASSURANCES_FROM_DOCS:
        seg = row["segment"]
        if seg not in valid_segments:
            seg = Assurance.Segment.PRIVEE_IARD
        a, _ = Assurance.objects.update_or_create(
            name=row["name"],
            defaults={
                "segment": seg,
                "description": row.get("description") or "",
                "is_active": True,
            },
        )
        out[row["name"]] = a
    return out


def load_pillars_from_docs() -> None:
    """Crée les 6 piliers, types (niveau 2) et actes (niveau 3)."""
    for pillar in PILLARS_FROM_DOCS:
        svc, _ = ServiceMedical.objects.update_or_create(
            name=pillar["name"],
            defaults={
                "order": pillar.get("order", 0),
                "icon": pillar.get("icon") or "",
                "is_active": True,
                "description": f"Pilier Medcare — {pillar['name']}",
            },
        )
        for type_def in pillar["types"]:
            parent, _ = ActeMedical.objects.update_or_create(
                name=type_def["name"],
                service_medical_category=svc,
                parent_service=None,
                defaults={
                    "level": 2,  # Sous-service (document niveau 2)
                    "description": "",
                },
            )
            for acte_name in type_def["actes"]:
                price = _reference_price_xof(pillar["name"], acte_name)
                ActeMedical.objects.update_or_create(
                    name=acte_name.strip(),
                    service_medical_category=svc,
                    parent_service=parent,
                    defaults={
                        "level": 3,  # Acte spécifique (document niveau 3)
                        "reference_price": price,
                        "description": "",
                    },
                )


PRESET_LOTS_DATA = [
    {
        "name": "Bilan biologique court",
        "teaser": "NFS + glycémie",
        "icon": "🩸",
        "order": 1,
        "acte_names": ["NFS / Hémogramme", "Glycémie"],
    },
    {
        "name": "Bilan rénal",
        "teaser": "Urée & créatinine",
        "icon": "💧",
        "order": 2,
        "acte_names": ["Urée", "Créatinine"],
    },
    {
        "name": "Bilan hépatique express",
        "teaser": "Transaminases & bilirubine",
        "icon": "🧬",
        "order": 3,
        "acte_names": ["ASAT", "ALAT", "GGT", "Bilirubine totale"],
    },
    {
        "name": "Bilan lipides & sucre",
        "teaser": "Glycémie, cholestérol, HDL, LDL, TG",
        "icon": "❤️",
        "order": 4,
        "acte_names": [
            "Glycémie",
            "Cholestérol total",
            "HDL",
            "LDL",
            "Triglycérides",
        ],
    },
    {
        "name": "Hémostase de base",
        "teaser": "TP/INR & TCA",
        "icon": "🩹",
        "order": 5,
        "acte_names": ["TP / INR", "TCA"],
    },
    {
        "name": "Échographie pelvis & abdomen",
        "teaser": "Double échographie",
        "icon": "📡",
        "order": 6,
        "acte_names": ["Échographie pelvienne", "Échographie abdominale"],
    },
    {
        "name": "Thyroïde biologie + écho",
        "teaser": "TSH & échographie thyroïdienne",
        "icon": "🔬",
        "order": 7,
        "acte_names": ["TSH, FT4 (± FT3)", "Échographie thyroïdienne"],
    },
]


def load_preset_lots() -> None:
    """Lots prédéfinis (parcours patient) — noms d'actes = catalogue niveau 3."""
    from healthcare.models import ActeMedical, LotExamenPrefait, LotExamenPrefaitActe

    for spec in PRESET_LOTS_DATA:
        lot, _ = LotExamenPrefait.objects.update_or_create(
            name=spec["name"],
            defaults={
                "teaser": spec.get("teaser", ""),
                "description": spec.get("description", ""),
                "icon": spec.get("icon", ""),
                "order": spec.get("order", 0),
                "is_active": True,
            },
        )
        LotExamenPrefaitActe.objects.filter(lot=lot).delete()
        for i, aname in enumerate(spec["acte_names"]):
            acte = ActeMedical.objects.filter(level=3, name=aname).first()
            if acte:
                LotExamenPrefaitActe.objects.create(lot=lot, acte=acte, order=i)


def load_full_reference_catalog() -> dict[str, Assurance]:
    """Assurances + piliers / actes (sans toucher aux utilisateurs)."""
    assurances = load_assurances_from_docs()
    load_pillars_from_docs()
    load_preset_lots()
    return assurances
