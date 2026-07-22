"""Helpers admin dashboard — formules visibles et actions abonnement."""

from __future__ import annotations

from django.db.models import QuerySet

from healthcare.models import OrganismeDeSante, SubscriptionPlan

# Plan retiré de l'UI admin (migration 0021 supprime l'enregistrement en base).
EXCLUDED_ADMIN_PLAN_SLUGS = frozenset({"reseau"})


def catalog_public_plans_qs() -> QuerySet[SubscriptionPlan]:
    """Formules affichées au prestataire (grille abonnement) — hors plans de test smoke."""
    return (
        SubscriptionPlan.objects.filter(is_public=True)
        .exclude(slug__startswith="smoke")
        .exclude(name__istartswith="Smoke")
        .order_by("order", "name")
    )

PLAN_ACTION_DEACTIVATE = "__desactiver__"


def admin_assignable_plans_qs() -> QuerySet[SubscriptionPlan]:
    return (
        SubscriptionPlan.objects.exclude(slug__in=EXCLUDED_ADMIN_PLAN_SLUGS)
        .exclude(slug__startswith="smoke")
        .exclude(name__istartswith="Smoke")
        .order_by("order", "name")
    )


def is_admin_assignable_plan(plan: SubscriptionPlan) -> bool:
    slug = (plan.slug or "").lower()
    if slug in EXCLUDED_ADMIN_PLAN_SLUGS or slug.startswith("smoke"):
        return False
    return not (plan.name or "").lower().startswith("smoke")


def cleanup_smoke_subscription_plans() -> int:
    """Réaffecte les structures sur plans smoke puis supprime ces plans."""
    from healthcare.models import SubscriptionChangeRequest, SubscriptionPlanFeature, get_default_subscription_plan

    fallback = get_default_subscription_plan()
    removed = 0
    for plan in SubscriptionPlan.objects.filter(slug__startswith="smoke"):
        if fallback:
            OrganismeDeSante.objects.filter(subscription_plan_id=plan.pk).update(
                subscription_plan_id=fallback.pk
            )
        SubscriptionPlanFeature.objects.filter(plan=plan).delete()
        SubscriptionChangeRequest.objects.filter(
            requested_plan=plan
        ).update(requested_plan=fallback)
        SubscriptionChangeRequest.objects.filter(previous_plan=plan).update(
            previous_plan=fallback
        )
        plan.delete()
        removed += 1
    return removed


def migrate_off_reseau_plan() -> int:
    """Basculer les structures encore sur « Réseau » vers Pro, puis supprimer le plan."""
    reseau = SubscriptionPlan.objects.filter(slug="reseau").first()
    if not reseau:
        return 0
    fallback = SubscriptionPlan.objects.filter(slug="pro").first()
    if fallback:
        OrganismeDeSante.objects.filter(subscription_plan_id=reseau.pk).update(
            subscription_plan_id=fallback.pk
        )
    from healthcare.models import SubscriptionPlanFeature

    SubscriptionPlanFeature.objects.filter(plan=reseau).delete()
    try:
        reseau.change_requests.all().delete()
    except Exception:
        pass
    reseau.delete()
    return 1
