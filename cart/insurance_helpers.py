"""Assurance effective du panier patient + contexte lignes avec couverture."""

from __future__ import annotations

from users.models import PatientProfile


def get_patient_profile(user):
    if not user.is_authenticated or not getattr(user, "is_patient", False):
        return None
    return PatientProfile.objects.filter(user=user).select_related("insurance").first()


def profile_uses_insurance_in_estimates(profile) -> bool:
    if not profile:
        return True
    return bool(getattr(profile, "insurance_use_in_estimates", True))


def resolve_estimation_insurance(cart, user):
    """Assurance pour les calculs estimatifs — respecte le choix du patient."""
    profile = get_patient_profile(user)
    if profile and not profile_uses_insurance_in_estimates(profile):
        return None
    return resolve_cart_insurance(cart, user)


def sync_cart_insurance_from_profile(cart, user) -> None:
    """Préremplit selected_insurance depuis le profil si le patient n'a pas choisi sur le panier."""
    if not user.is_authenticated or not getattr(user, "is_patient", False):
        return
    if getattr(cart, "insurance_user_override", False):
        return
    profile = get_patient_profile(user)
    if not profile or not profile.insurance_id:
        return
    if cart.selected_insurance_id != profile.insurance_id:
        cart.selected_insurance = profile.insurance
        cart.save(update_fields=["selected_insurance"])


def resolve_cart_insurance(cart, user):
    """Assurance effective pour le panier (respecte le choix explicite du patient)."""
    sync_cart_insurance_from_profile(cart, user)
    return cart.selected_insurance


def build_items_with_coverage(items, insurance, patient_profile=None):
    rows = []
    for item in items:
        coverage_rate = None
        patient_cost = item.subtotal
        if insurance:
            coverage_rate = item.prestataire_acte.get_coverage_rate(
                insurance, patient_profile=patient_profile
            )
            patient_cost = item.cost_after_insurance(
                insurance, patient_profile=patient_profile
            )
        pa = item.prestataire_acte
        st_ipm = getattr(pa, "coverage_status_ipm", "to_confirm") or "to_confirm"
        st_assur = getattr(pa, "coverage_status_assurance", "to_confirm") or "to_confirm"
        pr_ipm = getattr(pa, "price_ipm", None)
        pr_assur = getattr(pa, "price_assurance", None)
        # Garde-fou G5 : prix manquant sur régime couvert -> repli sur to_confirm (comptant)
        if st_ipm == "covered" and (pr_ipm is None or pr_ipm <= 0):
            st_ipm = "to_confirm"
        if st_assur == "covered" and (pr_assur is None or pr_assur <= 0):
            st_assur = "to_confirm"
        rows.append(
            {
                "item": item,
                "coverage_rate": coverage_rate,
                "patient_cost": patient_cost,
                # Tri-tarifs : statuts et prix par régime (garde-fous spec)
                "status_ipm": st_ipm,
                "status_assurance": st_assur,
                "price_ipm": pr_ipm,
                "price_assurance": pr_assur,
            }
        )
    return rows


def coverage_totals_for_acte_qty_pairs(pairs, insurance, patient_profile=None):
    """Totaux brut / prise en charge / reste pour des paires (PrestataireActe, quantité)."""
    total_brut = 0
    total_patient = 0
    for pa, qty in pairs:
        sub = pa.price * qty
        total_brut += sub
        unit = pa.get_patient_cost(insurance, patient_profile=patient_profile)
        total_patient += unit * qty
    return {
        "total_brut": total_brut,
        "total_assurance": total_brut - total_patient,
        "total_patient": total_patient,
    }


def _best_indicative_rate_percent(acte, insurances, patient_profile=None):
    """Meilleur taux indicatif parmi plusieurs assurances (logique démo patient)."""
    from healthcare.coverage import lookup_coverage_rate_percent

    best = None
    for insurance in insurances:
        rate = lookup_coverage_rate_percent(
            insurance, acte, patient_profile=patient_profile
        )
        if rate is None:
            continue
        if best is None or rate > best:
            best = rate
    return best


def indicative_patient_cost(pa, insurances, patient_profile=None):
    """Reste à charge indicatif (barème plateforme, sans contrainte structure)."""
    from healthcare.coverage import patient_cost_from_rate

    if not insurances:
        return pa.price
    rate = _best_indicative_rate_percent(
        pa.acte, insurances, patient_profile=patient_profile
    )
    if rate is None:
        return pa.price
    return patient_cost_from_rate(pa.price, rate)


def indicative_coverage_totals_for_acte_qty_pairs(
    pairs, insurances, patient_profile=None
):
    """Estimation démo : taux par catégorie d'acte, indépendamment des prises en charge structure."""
    total_brut = 0
    total_patient = 0
    for pa, qty in pairs:
        sub = pa.price * qty
        total_brut += sub
        unit = indicative_patient_cost(pa, insurances, patient_profile)
        total_patient += unit * qty
    return {
        "total_brut": total_brut,
        "total_assurance": total_brut - total_patient,
        "total_patient": total_patient,
    }


def cart_coverage_totals(cart, insurance, patient_profile=None):
    """Totaux brut / prise en charge / reste patient pour une assurance."""
    items = list(
        cart.items.select_related(
            "prestataire_acte__acte__parent_service",
            "prestataire_acte__acte__service_medical_category",
            "prestataire_acte__organisme",
        )
    )
    total_brut = sum(i.subtotal for i in items)
    if not insurance:
        return {
            "total_brut": total_brut,
            "total_assurance": 0,
            "total_patient": total_brut,
        }
    total_patient = sum(
        i.cost_after_insurance(insurance, patient_profile=patient_profile)
        for i in items
    )
    return {
        "total_brut": total_brut,
        "total_assurance": total_brut - total_patient,
        "total_patient": total_patient,
    }
