"""JSON API for the React subscription and reporting administration screens."""

import json
import logging
from datetime import timedelta

from django.contrib.admin.models import LogEntry
from django.db import transaction
from django.db.models import Count, F, ProtectedError, Sum
from django.http import JsonResponse, QueryDict
from django.utils import timezone

from cart.models import Devis
from healthcare.models import (
    OrganismeDeSante,
    PrestataireActe,
    PriseEnChargeAssurance,
    SubscriptionChangeRequest,
    SubscriptionFeature,
    SubscriptionPlan,
    SubscriptionPlanFeature,
)
from healthcare.subscription_admin import (
    PLAN_ACTION_DEACTIVATE,
    admin_assignable_plans_qs,
    is_admin_assignable_plan,
)
from .forms import SubscriptionPlanForm
from .models import ComplianceChecklistSettings

logger = logging.getLogger(__name__)

PIONEER_TARGET = 50
COMPLIANCE_CHECKLIST = [
    {
        "key": "hebergement_souverain",
        "label": "Hébergement souverain",
        "suggested": True,
        "detail": "Données hébergées sur infrastructure dédiée localisée au Sénégal (à confirmer pour la mise en prod finale).",
    },
    {
        "key": "chiffrement_tls",
        "label": "Chiffrement des données en transit (TLS)",
        "suggested": True,
        "detail": "HTTPS forcé sur tous les domaines via reverse-proxy Nginx + Let's Encrypt.",
    },
    {
        "key": "mots_de_passe_hash",
        "label": "Chiffrement des mots de passe",
        "suggested": True,
        "detail": "Hashing PBKDF2-SHA256 (configuration Django par défaut) ; aucun mot de passe stocké en clair.",
    },
    {
        "key": "logs_audit_admin",
        "label": "Logs d'audit (admin Django)",
        "suggested": True,
        "detail": "Toutes les actions effectuées dans l'admin Django (création, modification, suppression) sont historisées.",
    },
    {
        "key": "droit_oubli",
        "label": "Droit à l'oubli (suppression de compte)",
        "suggested": False,
        "detail": "À implémenter : auto-service côté patient pour demander la suppression de son compte (RGPD-like).",
    },
    {
        "key": "registre_traitements",
        "label": "Registre des traitements (loi 2008-12)",
        "suggested": False,
        "detail": "À documenter : registre listant chaque traitement de données personnelles, finalité, durée de conservation.",
    },
    {
        "key": "declaration_cdp",
        "label": "Déclaration CDP (loi 2008-12)",
        "suggested": False,
        "detail": "Démarche administrative à initier auprès de la Commission de protection des données personnelles du Sénégal.",
    },
    {
        "key": "politique_confidentialite",
        "label": "Politique de confidentialité publiée",
        "suggested": False,
        "detail": "Page publique à créer (URL `/legal/privacy/`) listant les engagements MedCare.",
    },
]


def _json_error(message, status=400, details=None):
    payload = {"ok": False, "error": message}
    if details is not None:
        payload["details"] = details
    return JsonResponse(payload, status=status)


def _admin_error(request):
    if not request.user.is_authenticated:
        return _json_error("Authentification requise.", 401)
    if not request.user.is_active or not (
        request.user.is_superuser or request.user.is_admin_user
    ):
        return _json_error("Accès réservé aux administrateurs.", 403)
    return None


def _endpoint(methods):
    """Apply active-admin authorization, JSON errors, and method validation."""
    def decorate(view):
        def wrapped(request, *args, **kwargs):
            denied = _admin_error(request)
            if denied:
                return denied
            if request.method not in methods:
                response = _json_error("Méthode non autorisée.", 405)
                response["Allow"] = ", ".join(methods)
                return response
            try:
                return view(request, *args, **kwargs)
            except Exception:
                logger.exception("Unexpected error in admin reports API (%s)", view.__name__)
                return _json_error("Une erreur interne est survenue.", 500)
        wrapped.__name__ = view.__name__
        wrapped.__doc__ = view.__doc__
        return wrapped
    return decorate


def _read_payload(request):
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, _json_error("Corps JSON invalide.")
        if not isinstance(data, dict):
            return None, _json_error("Le corps JSON doit être un objet.")
        payload = QueryDict("", mutable=True)
        for key, value in data.items():
            if isinstance(value, list):
                payload.setlist(key, [str(item) for item in value])
            elif value is None:
                payload.setlist(key, [])
            elif isinstance(value, bool):
                payload[key] = "true" if value else "false"
            else:
                payload[key] = str(value)
        return payload, None
    return request.POST, None


def _org_json(org, in_30_days=None):
    plan = org.subscription_plan
    renewal = org.subscription_renewal_at
    return {
        "id": org.pk,
        "name": org.name,
        "slug": org.slug,
        "city": org.city or "",
        "type": str(org.type_organisme) if org.type_organisme_id else "",
        "is_active": org.is_active,
        "plan_id": org.subscription_plan_id,
        "plan_name": plan.name if plan else "",
        "plan_slug": plan.slug if plan else "",
        "monthly_price_fcfa": plan.monthly_price_fcfa if plan else 0,
        "subscription_started_at": org.subscription_started_at.isoformat()
        if org.subscription_started_at else None,
        "subscription_renewal_at": renewal.isoformat() if renewal else None,
        "subscription_auto_renew": org.subscription_auto_renew,
        "profile_views_count": org.profile_views_count,
        "expires_soon": bool(renewal and in_30_days and renewal <= in_30_days),
    }


def _plan_json(plan, orgs_count=None, included_ids=None):
    return {
        "id": plan.pk,
        "name": plan.name,
        "slug": plan.slug,
        "short_description": plan.short_description,
        "long_description": plan.long_description,
        "monthly_price_fcfa": plan.monthly_price_fcfa,
        "is_default": plan.is_default,
        "is_public": plan.is_public,
        "is_pioneer_offer": plan.is_pioneer_offer,
        "trial_months": plan.trial_months,
        "order": plan.order,
        "orgs_count": orgs_count if orgs_count is not None else 0,
        "included_feature_ids": included_ids or [],
    }


@_endpoint(("GET",))
def subscriptions(request):
    today = timezone.now().date()
    in_30_days = today + timedelta(days=30)
    plans = list(
        admin_assignable_plans_qs().annotate(
            orgs_count=Count("organismes", distinct=True)
        )
    )
    features = list(SubscriptionFeature.objects.order_by("order", "label"))
    plan_filter = request.GET.get("plan") or "all"
    orgs = OrganismeDeSante.objects.select_related(
        "subscription_plan", "type_organisme"
    ).order_by("name")
    if plan_filter == "expire":
        orgs = orgs.filter(
            subscription_renewal_at__isnull=False,
            subscription_renewal_at__lte=in_30_days,
        )
    elif plan_filter == "inactif":
        orgs = orgs.filter(is_active=False)
    elif plan_filter == "pionnier":
        orgs = orgs.filter(subscription_plan__is_pioneer_offer=True)
    elif plan_filter != "all":
        orgs = orgs.filter(subscription_plan__slug=plan_filter)

    mrr = (
        admin_assignable_plans_qs()
        .annotate(n=Count("organismes"))
        .aggregate(total=Sum(F("monthly_price_fcfa") * F("n")))
        .get("total") or 0
    )
    inclusion_rows = SubscriptionPlanFeature.objects.filter(
        plan__in=plans, included=True
    ).values_list("plan_id", "feature_id")
    included_by_plan = {}
    for plan_id, feature_id in inclusion_rows:
        included_by_plan.setdefault(plan_id, []).append(feature_id)
    return JsonResponse({
        "ok": True,
        "plan_filter": plan_filter,
        "in_30_days": in_30_days.isoformat(),
        "kpis": {
            "active_organizations": OrganismeDeSante.objects.filter(is_active=True).count(),
            "expiring_soon": OrganismeDeSante.objects.filter(
                subscription_renewal_at__isnull=False,
                subscription_renewal_at__lte=in_30_days,
            ).count(),
            "pending_upgrades": SubscriptionChangeRequest.objects.filter(
                status="pending"
            ).count(),
            "mrr": mrr,
        },
        "plans": [
            _plan_json(
                plan,
                plan.orgs_count,
                included_by_plan.get(plan.pk, []),
            )
            for plan in plans
        ],
        "features": [
            {
                "id": feature.pk,
                "code": feature.code,
                "label": feature.label,
                "description": feature.description,
            }
            for feature in features
        ],
        "organizations": [_org_json(org, in_30_days) for org in orgs],
    })


@_endpoint(("POST",))
def assign_plan(request, org_id):
    payload, error = _read_payload(request)
    if error:
        return error
    try:
        org = OrganismeDeSante.objects.select_related("subscription_plan").get(pk=org_id)
    except OrganismeDeSante.DoesNotExist:
        return _json_error("Structure introuvable.", 404)
    plan_slug = (payload.get("plan_slug") or "").strip()
    if not plan_slug:
        return _json_error("Aucune formule sélectionnée.")
    if plan_slug == PLAN_ACTION_DEACTIVATE:
        if org.is_active:
            org.is_active = False
            org.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"ok": True, "organization": _org_json(org), "message": "Structure désactivée."})
    try:
        plan = SubscriptionPlan.objects.get(slug=plan_slug)
    except SubscriptionPlan.DoesNotExist:
        return _json_error("Formule introuvable.", 404)
    if not is_admin_assignable_plan(plan):
        return _json_error("Cette formule n'est plus disponible.", 400)
    update_fields = []
    if org.subscription_plan_id != plan.pk:
        org.subscription_plan = plan
        update_fields.append("subscription_plan")
        if not org.subscription_started_at:
            org.subscription_started_at = timezone.now().date()
            update_fields.append("subscription_started_at")
    if not org.is_active:
        org.is_active = True
        update_fields.append("is_active")
    if update_fields:
        org.save(update_fields=update_fields + ["updated_at"])
    return JsonResponse({
        "ok": True,
        "organization": _org_json(org),
        "message": "Formule mise à jour.",
    })


@_endpoint(("POST",))
def toggle_feature(request, plan_id, feature_id):
    try:
        plan = SubscriptionPlan.objects.get(pk=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return _json_error("Formule introuvable.", 404)
    if not is_admin_assignable_plan(plan):
        return _json_error("Cette formule n'est plus configurable.", 400)
    try:
        feature = SubscriptionFeature.objects.get(pk=feature_id)
    except SubscriptionFeature.DoesNotExist:
        return _json_error("Fonctionnalité introuvable.", 404)
    with transaction.atomic():
        relation, _ = SubscriptionPlanFeature.objects.get_or_create(
            plan=plan, feature=feature, defaults={"included": False}
        )
        relation.included = not relation.included
        relation.save(update_fields=["included"])
    return JsonResponse({"ok": True, "included": relation.included})


def _plan_form_response(request, plan=None):
    payload, error = _read_payload(request)
    if error:
        return error
    form = SubscriptionPlanForm(payload, instance=plan)
    if not form.is_valid():
        return _json_error("Veuillez corriger les champs du formulaire.", 400, form.errors.get_json_data())
    with transaction.atomic():
        saved = form.save()
        if saved.is_default:
            SubscriptionPlan.objects.exclude(pk=saved.pk).update(is_default=False)
    return JsonResponse({"ok": True, "plan": _plan_json(saved)})


@_endpoint(("POST",))
def create_plan(request):
    return _plan_form_response(request)


@_endpoint(("PATCH", "PUT", "POST", "DELETE"))
def update_plan(request, plan_id):
    if request.method == "DELETE":
        return delete_plan(request, plan_id)
    try:
        plan = SubscriptionPlan.objects.get(pk=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return _json_error("Formule introuvable.", 404)
    return _plan_form_response(request, plan)


@_endpoint(("DELETE", "POST"))
def delete_plan(request, plan_id):
    try:
        plan = SubscriptionPlan.objects.get(pk=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return _json_error("Formule introuvable.", 404)
    name = plan.name
    try:
        plan.delete()
    except ProtectedError:
        return _json_error(
            f"Impossible de supprimer « {name} » : une ou plusieurs structures utilisent encore cette formule.",
            409,
        )
    return JsonResponse({"ok": True, "message": f"Formule « {name} » supprimée."})


def _bilan_score_org(org):
    devis_total = Devis.objects.filter(
        cart__items__prestataire_acte__organisme=org,
        status__in=["sent", "viewed", "relanced"],
    ).distinct().count()
    actes_count = PrestataireActe.objects.filter(organisme=org).count()
    insurances_count = PriseEnChargeAssurance.objects.filter(organisme=org).count()
    completion = [
        bool(org.description),
        bool(org.contact_phone or org.whatsapp_number),
        bool(org.logo),
        actes_count > 0,
        insurances_count > 0,
        bool(org.latitude and org.longitude),
    ]
    completion_pct = int(round(sum(completion) * 100.0 / len(completion)))
    score = min(100, round(
        min(devis_total, 30) * 1.5
        + min(org.profile_views_count, 500) * 0.05
        + completion_pct * 0.4
    ))
    if score >= 70:
        signal, label, recommendation = "green", "Excellent", "Plan recommandé M6 : Pro"
    elif score >= 35:
        signal, label, recommendation = "amber", "Encourageant", "Plan recommandé M6 : Essentiel"
    else:
        signal, label, recommendation = "red", "À améliorer", "Plan recommandé M6 : Pionnier (offre découverte)"
    return {
        "score": score,
        "signal": signal,
        "signal_label": label,
        "recommendation": recommendation,
        "devis_total": devis_total,
        "actes_count": actes_count,
        "insurances_count": insurances_count,
        "completion_pct": completion_pct,
    }


@_endpoint(("GET",))
def finances(request):
    today = timezone.now().date()
    plans = SubscriptionPlan.objects.annotate(
        orgs_count=Count("organismes")
    ).order_by("order", "name")
    rows = []
    mrr = 0
    for plan in plans:
        subtotal = plan.monthly_price_fcfa * plan.orgs_count
        mrr += subtotal
        rows.append({
            "plan": _plan_json(plan, plan.orgs_count),
            "subtotal": subtotal,
        })
    months = list(range(13))
    scenarios = {}
    for key, rate in (("pessimiste", 0.02), ("median", 0.06), ("optimiste", 0.12)):
        current = float(mrr) if mrr else 100000.0
        series = []
        for _month in months:
            series.append(int(current))
            current *= 1 + rate
        scenarios[key] = series
    return JsonResponse({
        "ok": True,
        "today": today.isoformat(),
        "kpis": {
            "mrr": mrr,
            "arr": mrr * 12,
            "service_fees": 0,
            "estimated_conversion": "65 %",
        },
        "plan_rows": rows,
        "months": [f"M{month}" for month in months],
        "scenarios": scenarios,
    })


@_endpoint(("GET",))
def pioneers(request):
    pioneer_qs = OrganismeDeSante.objects.filter(
        subscription_plan__is_pioneer_offer=True
    ).select_related("subscription_plan", "type_organisme").order_by("-created_at")
    signed = pioneer_qs.count()
    rows = []
    for org in pioneer_qs:
        bilan = _bilan_score_org(org)
        rows.append({
            "reference": f"CPP-{org.created_at.year}-{org.pk:03d}",
            "organization": _org_json(org),
            "score": bilan["score"],
            "signal": bilan["signal"],
            "signal_label": bilan["signal_label"],
            "acts": bilan["actes_count"],
        })
    return JsonResponse({
        "ok": True,
        "target": PIONEER_TARGET,
        "signed": signed,
        "active": pioneer_qs.filter(is_active=True).count(),
        "pending": pioneer_qs.filter(is_active=False).count(),
        "onboarding": pioneer_qs.filter(profile_views_count__lt=10).count(),
        "remaining": max(0, PIONEER_TARGET - signed),
        "progress_pct": min(100, int(round(signed * 100.0 / max(PIONEER_TARGET, 1)))),
        "rows": rows,
    })


@_endpoint(("GET",))
def bilans(request):
    orgs = OrganismeDeSante.objects.filter(is_active=True).select_related(
        "subscription_plan", "type_organisme"
    ).order_by("name")
    rows = []
    counts = {"green": 0, "amber": 0, "red": 0}
    for org in orgs:
        bilan = _bilan_score_org(org)
        counts[bilan["signal"]] += 1
        rows.append({"organization": _org_json(org), **bilan})
    rows.sort(key=lambda row: row["score"], reverse=True)
    return JsonResponse({"ok": True, "rows": rows, "counts": counts, "total": len(rows)})


@_endpoint(("GET", "PUT", "POST"))
def compliance(request):
    solo = ComplianceChecklistSettings.get_solo()
    if request.method == "GET":
        stored = solo.checks if isinstance(solo.checks, dict) else {}
        checklist = []
        for item in COMPLIANCE_CHECKLIST:
            checklist.append({
                **item,
                "ok": stored.get(item["key"], bool(item["suggested"])),
            })
        logs = LogEntry.objects.select_related(
            "user", "content_type"
        ).order_by("-action_time")[:30]
        return JsonResponse({
            "ok": True,
            "checklist": checklist,
            "completed": sum(1 for item in checklist if item["ok"]),
            "total": len(checklist),
            "updated_at": solo.updated_at.isoformat() if solo.updated_at else None,
            "logs": [
                {
                    "id": entry.pk,
                    "action_time": entry.action_time.isoformat(),
                    "actor": getattr(entry.user, "display_name", "") or entry.user.username,
                    "action_flag": entry.action_flag,
                    "content_type": str(entry.content_type) if entry.content_type_id else "",
                    "object_repr": entry.object_repr[:40],
                }
                for entry in logs
            ],
        })
    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _json_error("Corps JSON invalide.")
        if not isinstance(payload, dict):
            return _json_error("Le corps JSON doit être un objet.")
    else:
        payload = request.POST
    checks = payload.get("checks")
    if checks is None:
        checks = {}
        for item in COMPLIANCE_CHECKLIST:
            raw = payload.get(item["key"], "0")
            checks[item["key"]] = raw in ("1", "true", "on", "yes")
    if not isinstance(checks, dict):
        return _json_error("Le champ checks doit être un objet.", 400)
    new_checks = {}
    for item in COMPLIANCE_CHECKLIST:
        value = checks.get(item["key"], False)
        if not isinstance(value, bool):
            return _json_error(f"Valeur invalide pour {item['key']}.", 400)
        new_checks[item["key"]] = value
    solo.checks = new_checks
    solo.save(update_fields=["checks", "updated_at"])
    return JsonResponse({
        "ok": True,
        "checks": new_checks,
        "updated_at": solo.updated_at.isoformat(),
    })
