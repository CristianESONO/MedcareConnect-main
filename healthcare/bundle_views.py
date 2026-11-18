"""
Parcours / lot d'examens : combinaisons de centres.
"""
from __future__ import annotations

import json

from django.db.models import Q
from django.urls import reverse
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from healthcare.bundle_planner import alternatives_for_acte, compose_plans
from healthcare.geo import parse_lat_lng
from healthcare.models import ActeMedical, LotExamenPrefait


SESSION_ACTE_KEYS = "parcours_acte_ids"


@ensure_csrf_cookie
def bundle_planner(request):
    """Page principale : composer un lot, voir scénarios, personnaliser, envoyer au panier."""
    presets = (
        LotExamenPrefait.objects.filter(is_active=True)
        .prefetch_related("lot_actes__acte")
        .order_by("order", "name")
    )
    preset_payload = []
    for lot in presets:
        actes = [la.acte for la in lot.lot_actes.all()]
        preset_payload.append(
            {
                "id": lot.id,
                "name": lot.name,
                "teaser": lot.teaser,
                "icon": lot.icon or "📋",
                "description": lot.description,
                "acte_ids": [a.id for a in actes],
                "acte_labels": [a.name for a in actes],
            }
        )

    initial_ids = request.session.get(SESSION_ACTE_KEYS) or []
    if not isinstance(initial_ids, list):
        initial_ids = []

    pa_alt_tpl = reverse(
        "healthcare:api_pa_alternatives", kwargs={"acte_id": 999999999}
    ).replace("999999999", "__ACTE__")

    context = {
        "presets_json": json.dumps(preset_payload),
        "initial_acte_ids_json": json.dumps([int(x) for x in initial_ids if str(x).isdigit()]),
        "pa_alternatives_url_tpl": pa_alt_tpl,
    }
    return render(request, "healthcare/bundle_planner.html", context)


@require_POST
def api_bundle_plan(request):
    """JSON in: { acte_ids: number[], lat?, lng? } → plans + warnings."""
    try:
        body = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide"}, status=400)
    raw_ids = body.get("acte_ids") or []
    acte_ids: list[int] = []
    for x in raw_ids:
        try:
            acte_ids.append(int(x))
        except (TypeError, ValueError):
            continue
    acte_ids = [i for i in acte_ids if i > 0]
    if not acte_ids:
        return JsonResponse({"error": "Sélectionnez au moins un examen."}, status=400)
    if len(acte_ids) > 40:
        return JsonResponse({"error": "Maximum 40 examens par parcours."}, status=400)

    lat_s = body.get("lat")
    lng_s = body.get("lng")
    latlng = None
    if lat_s not in (None, "") and lng_s not in (None, ""):
        latlng = parse_lat_lng(str(lat_s), str(lng_s))

    lat, lng = latlng if latlng else (None, None)
    data = compose_plans(acte_ids, lat, lng)

    if body.get("save_selection"):
        request.session[SESSION_ACTE_KEYS] = acte_ids
        request.session.modified = True

    return JsonResponse(data)


@require_GET
def api_actes_autocomplete(request):
    """Recherche d'actes (niveau 3) pour ajouter au lot."""
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    qs = (
        ActeMedical.objects.filter(is_active=True, level=3)
        .filter(Q(name__icontains=q) | Q(code__icontains=q))
        .select_related("service_medical_category")
        .order_by("name")[:18]
    )
    results = [
        {
            "id": a.id,
            "name": a.name,
            "service": a.service_medical_category.name,
        }
        for a in qs
    ]
    return JsonResponse({"results": results})


@require_GET
def api_pa_alternatives(request, acte_id: int):
    """Offres alternatives pour changer de centre sur un examen."""
    lat_s = request.GET.get("lat")
    lng_s = request.GET.get("lng")
    latlng = parse_lat_lng(lat_s, lng_s) if lat_s and lng_s else None
    lat, lng = latlng if latlng else (None, None)
    rows = alternatives_for_acte(acte_id, lat, lng, limit=30)
    return JsonResponse({"alternatives": rows})


@require_POST
def bundle_save_session(request):
    """Mémorise les IDs d'actes dans la session (y compris visiteur non connecté)."""
    try:
        body = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide"}, status=400)
    raw_ids = body.get("acte_ids") or []
    acte_ids: list[int] = []
    for x in raw_ids:
        try:
            acte_ids.append(int(x))
        except (TypeError, ValueError):
            continue
    request.session[SESSION_ACTE_KEYS] = acte_ids[:40]
    request.session.modified = True
    return JsonResponse({"ok": True, "count": len(acte_ids)})
