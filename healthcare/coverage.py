"""Calcul indicatif de prise en charge assurance (par catégorie d'acte)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from healthcare.coverage_rates import COVERAGE_RATES_BY_ASSURANCE, _ASSURANCE_NAME_HINTS


def coverage_category_for_acte(acte) -> str:
    """Catégorie niveau 2 utilisée pour le barème (ex. Hématologie, Échographie)."""
    if acte.parent_service_id:
        return acte.parent_service.name
    if acte.level == 2:
        return acte.name
    if acte.service_medical_category_id:
        return acte.service_medical_category.name
    return "Autres"


def assurance_rates_lookup_key(assurance) -> str | None:
    """Associe un objet Assurance à une clé du référentiel de taux."""
    if assurance is None:
        return None
    name = (assurance.name or "").strip()
    if name in COVERAGE_RATES_BY_ASSURANCE:
        return name
    lower = name.lower()
    for hint, key in _ASSURANCE_NAME_HINTS:
        if hint in lower:
            return key
    for key in COVERAGE_RATES_BY_ASSURANCE:
        if key.lower() in lower or lower in key.lower():
            return key
    return None


def reference_rates_for_assurance(assurance) -> dict[str, int]:
    """Barème indicatif plateforme par catégorie d'acte (niveau 2)."""
    key = assurance_rates_lookup_key(assurance)
    if not key:
        return {}
    return dict(COVERAGE_RATES_BY_ASSURANCE.get(key) or {})


def patient_coverage_rate_percent(patient_profile, assurance, acte) -> Decimal | None:
    """
    Taux patient prioritaire : catégorie → global → barème plateforme.
    """
    if not assurance or not patient_profile:
        return lookup_coverage_rate_percent(assurance, acte)

    category = coverage_category_for_acte(acte)
    by_cat = patient_profile.insurance_coverage_by_category or {}

    if category in by_cat and by_cat[category] not in (None, ""):
        try:
            return Decimal(str(by_cat[category]))
        except Exception:
            pass

    if patient_profile.insurance_coverage_pct is not None:
        return patient_profile.insurance_coverage_pct

    return lookup_coverage_rate_percent(assurance, acte)


def lookup_coverage_rate_percent(assurance, acte, patient_profile=None) -> Decimal | None:
    """
    Taux indicatif 0–100 pour (assurance, acte).
    Retourne None si assurance inconnue ou catégorie sans barème.
    """
    if patient_profile is not None:
        return patient_coverage_rate_percent(patient_profile, assurance, acte)

    key = assurance_rates_lookup_key(assurance)
    if not key:
        return None
    rates = COVERAGE_RATES_BY_ASSURANCE.get(key) or {}
    category = coverage_category_for_acte(acte)
    rate = rates.get(category)
    if rate is None:
        return None
    return Decimal(str(rate))


def organisme_accepts_insurance(organisme_id: int, assurance) -> bool:
    from healthcare.models import PriseEnChargeAssurance

    if not assurance:
        return False
    return PriseEnChargeAssurance.objects.filter(
        organisme_id=organisme_id,
        assurance=assurance,
        is_active=True,
    ).exists()


def patient_cost_from_rate(unit_price, rate_percent: Decimal) -> Decimal:
    """Reste à charge patient pour un prix unitaire et un taux de couverture."""
    if not rate_percent or rate_percent <= 0:
        return unit_price
    patient_pct = (Decimal("100") - rate_percent) / Decimal("100")
    return (unit_price * patient_pct).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
