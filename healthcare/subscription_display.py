"""Données d'affichage grille abonnement (BIZ-ECO-003) — hors modèle DB."""

from __future__ import annotations

from healthcare.models import SubscriptionFeature, SubscriptionPlanFeature

PLAN_TARGETS = {
    "pionnier": "Programme Partenaires Pionniers CPP-2025 · 50 slots · Dakar",
    "starter": "Structures mono-pilier",
    "essentiel": "Cabinets spécialisés multi-piliers",
    "pro": "Hôpitaux · 6 piliers complets",
}

PLAN_STRUCTURES = {
    "starter": [
        {"icon": "🔬", "name": "Laboratoire d'analyses", "chips": [("Biologie", "pc-bio")]},
        {"icon": "🖥", "name": "Centre d'imagerie", "chips": [("Imagerie", "pc-img")]},
        {"icon": "🦷", "name": "Cabinet dentaire", "chips": [("Soins dentaires", "pc-dent")]},
        {"icon": "🏃", "name": "Kiné / Rééducation", "chips": [("Soins spécialisés", "pc-soins")]},
        {"icon": "💧", "name": "Centre de dialyse", "chips": [("Soins spécialisés", "pc-soins")]},
        {"icon": "🧠", "name": "Cabinet santé mentale", "chips": [("Soins spécialisés", "pc-soins")]},
        {"icon": "🚑", "name": "Service ambulancier", "chips": [("Ambulances", "pc-amb")]},
    ],
    "essentiel": [
        {
            "icon": "🩺",
            "name": "Cabinet spécialisé",
            "chips": [
                ("Imagerie", "pc-img"),
                ("Exploration fonct.", "pc-explo"),
                ("Soins spécialisés", "pc-soins"),
            ],
        },
        {
            "icon": "🏥",
            "name": "Centre de santé",
            "chips": [
                ("Biologie", "pc-bio"),
                ("Imagerie", "pc-img"),
                ("Soins spécialisés", "pc-soins"),
            ],
        },
        {
            "icon": "🏨",
            "name": "Clinique privée",
            "chips": [
                ("Biologie", "pc-bio"),
                ("Imagerie", "pc-img"),
                ("Soins spécialisés", "pc-soins"),
            ],
        },
    ],
    "pro": [
        {
            "icon": "🏛",
            "name": "Hôpital — accès complet",
            "chips": [
                ("Biologie", "pc-bio"),
                ("Imagerie", "pc-img"),
                ("Soins spécialisés", "pc-soins"),
                ("Ambulances", "pc-amb"),
                ("Soins dentaires", "pc-dent"),
                ("Exploration fonct.", "pc-explo"),
            ],
        },
    ],
}

FEATURE_GROUPS = [
    (
        "Visibilité & profil",
        ["badge_pionnier", "listing", "profil_public", "assurances"],
    ),
    (
        "Workflow & communication",
        ["whatsapp_devis", "reservations"],
    ),
    (
        "Analytics & reporting",
        ["dashboard_basic", "dashboard_advanced", "stats_mensuelles"],
    ),
    (
        "Matériel & intégrations",
        ["medplaque", "api_partenaires", "multi_sites", "support_prioritaire"],
    ),
]


def plan_theme_slug(plan) -> str:
    slug = (plan.slug or "").lower()
    if slug in ("pionnier", "starter", "essentiel", "pro"):
        return slug
    if getattr(plan, "is_pioneer_offer", False):
        return "pionnier"
    return "starter"


def plan_target(plan) -> str:
    if getattr(plan, "short_description", None):
        return plan.short_description
    slug = (plan.slug or "").lower()
    return PLAN_TARGETS.get(slug, "")


def plan_structures(plan):
    return PLAN_STRUCTURES.get((plan.slug or "").lower(), [])


def annual_price_fcfa(monthly: int | None) -> int:
    if not monthly:
        return 0
    return int(monthly * 12 * 0.9)


def medplaque_is_addon(plan, included_codes: set[str]) -> bool:
    return (plan.slug or "").lower() == "starter" and "medplaque" not in included_codes


def build_plan_included_map(plans) -> dict[int, set[str]]:
    result: dict[int, set[str]] = {}
    for plan in plans:
        codes: set[str] = set()
        for pf in plan.plan_features.all():
            if pf.included:
                codes.add(pf.feature.code)
        result[plan.pk] = codes
    return result


def build_feature_groups(features):
    """Regroupe les features pour le tableau comparatif et le formulaire."""
    feat_by_code = {f.code: f for f in features}
    grouped = []
    used_codes: set[str] = set()
    for group_label, codes in FEATURE_GROUPS:
        rows = [feat_by_code[c] for c in codes if c in feat_by_code]
        if rows:
            grouped.append((group_label, rows))
            used_codes.update(f.code for f in rows)
    extra = [f for f in features if f.code not in used_codes]
    if extra:
        grouped.append(("Autres", extra))
    return grouped


def build_subscription_display_context(plans, features=None):
    if features is None:
        features = list(SubscriptionFeature.objects.order_by("order", "label"))
    return {
        "subscription_features_all": features,
        "subscription_feature_groups": build_feature_groups(features),
        "subscription_plan_included": build_plan_included_map(plans),
    }


def build_feature_groups_for_form():
    """Alias — mêmes groupes que la grille /dashboard/abonnements/formules/."""
    features = list(SubscriptionFeature.objects.order_by("order", "label"))
    return build_feature_groups(features)


def prefetch_plan_features_queryset():
    return SubscriptionPlanFeature.objects.select_related("feature").order_by(
        "feature__order", "feature__label"
    )
