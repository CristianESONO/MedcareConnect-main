"""
Combinaisons de centres pour un lot d'examens (prix, proximité, un seul lieu).
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Optional

from healthcare.geo import haversine_km
from healthcare.models import ActeMedical, PrestataireActe


def _org_distance_km(org, lat: Optional[float], lng: Optional[float]) -> float:
    if lat is None or lng is None:
        return 0.0
    if org.latitude is None or org.longitude is None:
        return 750.0
    return haversine_km(lat, lng, float(org.latitude), float(org.longitude))


def _pa_base_qs(acte_ids: list[int]):
    return PrestataireActe.objects.filter(
        acte_id__in=acte_ids,
        is_available=True,
        organisme__is_active=True,
    ).select_related("organisme", "acte")


def line_dict(pa: PrestataireActe) -> dict[str, Any]:
    org = pa.organisme
    return {
        "acte_id": pa.acte_id,
        "acte_name": pa.acte.name,
        "prestataire_acte_id": pa.id,
        "organisme_id": org.id,
        "organisme_name": org.name,
        "organisme_slug": org.slug,
        "price": str(pa.price),
        "latitude": str(org.latitude) if org.latitude is not None else None,
        "longitude": str(org.longitude) if org.longitude is not None else None,
    }


def _dedupe_acte_ids(acte_ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for x in acte_ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def build_single_center_plans(
    acte_ids: list[int],
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    max_plans: int = 6,
) -> list[dict[str, Any]]:
    """Centres proposant tous les actes (meilleur prix par acte au sein du centre)."""
    acte_ids = _dedupe_acte_ids(acte_ids)
    if not acte_ids:
        return []
    acte_set = set(acte_ids)
    by_org: dict[int, dict[int, list[PrestataireActe]]] = defaultdict(lambda: defaultdict(list))
    for pa in _pa_base_qs(acte_ids):
        by_org[pa.organisme_id][pa.acte_id].append(pa)

    plans: list[dict[str, Any]] = []
    for org_id, by_acte in by_org.items():
        if not acte_set.issubset(by_acte.keys()):
            continue
        lines: list[dict[str, Any]] = []
        total = Decimal("0")
        dist_sum = 0.0
        org = None
        for aid in acte_ids:
            options = by_acte[aid]
            best = min(options, key=lambda x: float(x.price))
            if org is None:
                org = best.organisme
            lines.append(line_dict(best))
            total += best.price
            dist_sum += _org_distance_km(best.organisme, lat, lng)
        avg_d = round(dist_sum / len(acte_ids), 2) if acte_ids else None
        sort_key = (float(total), avg_d if avg_d is not None else 0.0)
        plans.append(
            {
                "key": f"single_{org_id}",
                "kind": "single_center",
                "title": f"Un seul centre — {org.name}",
                "subtitle": "Tous vos examens au même endroit : un seul trajet.",
                "organisme_slug": org.slug,
                "center_count": 1,
                "total_price": str(total),
                "avg_distance_km": avg_d if lat is not None else None,
                "lines": lines,
                "missing_actes": [],
                "_sort": sort_key,
            }
        )
    plans.sort(key=lambda p: p["_sort"])
    for p in plans:
        del p["_sort"]
    return plans[:max_plans]


def build_multi_cheapest(
    acte_ids: list[int],
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> dict[str, Any]:
    """Pour chaque examen : offre la moins chère (centres différents possibles)."""
    acte_ids = _dedupe_acte_ids(acte_ids)
    lines: list[dict[str, Any]] = []
    total = Decimal("0")
    orgs: set[int] = set()
    missing_names: list[str] = []
    for aid in acte_ids:
        pa = _pa_base_qs([aid]).order_by("price").first()
        if not pa:
            try:
                missing_names.append(ActeMedical.objects.get(pk=aid).name)
            except ActeMedical.DoesNotExist:
                missing_names.append(f"#{aid}")
            continue
        lines.append(line_dict(pa))
        total += pa.price
        orgs.add(pa.organisme_id)
    avg_d = None
    if lat is not None and lines:
        s = 0.0
        for ln in lines:
            pa = PrestataireActe.objects.select_related("organisme").get(pk=ln["prestataire_acte_id"])
            s += _org_distance_km(pa.organisme, lat, lng)
        avg_d = round(s / len(lines), 2)
    return {
        "key": "multi_cheapest",
        "kind": "multi_price",
        "title": "Prix total minimum",
        "subtitle": "Chaque examen au tarif le plus bas (plusieurs centres possibles).",
        "center_count": len(orgs),
        "total_price": str(total),
        "avg_distance_km": avg_d,
        "lines": lines,
        "missing_actes": missing_names,
    }


def build_multi_nearest(
    acte_ids: list[int],
    lat: float,
    lng: float,
) -> Optional[dict[str, Any]]:
    """Pour chaque examen : centre le plus proche du point de référence."""
    acte_ids = _dedupe_acte_ids(acte_ids)
    lines: list[dict[str, Any]] = []
    total = Decimal("0")
    orgs: set[int] = set()
    missing_names: list[str] = []
    for aid in acte_ids:
        candidates = list(_pa_base_qs([aid]))
        if not candidates:
            try:
                missing_names.append(ActeMedical.objects.get(pk=aid).name)
            except ActeMedical.DoesNotExist:
                missing_names.append(f"#{aid}")
            continue
        best = min(candidates, key=lambda pa: _org_distance_km(pa.organisme, lat, lng))
        lines.append(line_dict(best))
        total += best.price
        orgs.add(best.organisme_id)
    if not lines:
        return None
    s = sum(
        _org_distance_km(
            PrestataireActe.objects.select_related("organisme").get(pk=ln["prestataire_acte_id"]).organisme,
            lat,
            lng,
        )
        for ln in lines
    )
    avg_d = round(s / len(lines), 2)
    return {
        "key": "multi_nearest",
        "kind": "multi_proximity",
        "title": "Centres les plus proches",
        "subtitle": "À chaque fois le lieu le plus proche de vous pour l'examen.",
        "center_count": len(orgs),
        "total_price": str(total),
        "avg_distance_km": avg_d,
        "lines": lines,
        "missing_actes": missing_names,
    }


def build_balanced(
    acte_ids: list[int],
    lat: float,
    lng: float,
    price_weight: float = 1.0,
    distance_weight: float = 120.0,
) -> Optional[dict[str, Any]]:
    """Compromis prix + distance (score = w_p * prix + w_d * km)."""
    acte_ids = _dedupe_acte_ids(acte_ids)
    lines: list[dict[str, Any]] = []
    total = Decimal("0")
    orgs: set[int] = set()
    missing_names: list[str] = []
    for aid in acte_ids:
        candidates = list(_pa_base_qs([aid]))
        if not candidates:
            try:
                missing_names.append(ActeMedical.objects.get(pk=aid).name)
            except ActeMedical.DoesNotExist:
                missing_names.append(f"#{aid}")
            continue

        def score(pa: PrestataireActe) -> float:
            d = _org_distance_km(pa.organisme, lat, lng)
            return price_weight * float(pa.price) + distance_weight * d

        best = min(candidates, key=score)
        lines.append(line_dict(best))
        total += best.price
        orgs.add(best.organisme_id)
    if not lines:
        return None
    s = sum(
        _org_distance_km(
            PrestataireActe.objects.select_related("organisme").get(pk=ln["prestataire_acte_id"]).organisme,
            lat,
            lng,
        )
        for ln in lines
    )
    avg_d = round(s / len(lines), 2)
    return {
        "key": "balanced",
        "kind": "balanced",
        "title": "Équilibre prix & distance",
        "subtitle": "Bon compromis entre coût total et trajets.",
        "center_count": len(orgs),
        "total_price": str(total),
        "avg_distance_km": avg_d,
        "lines": lines,
        "missing_actes": missing_names,
    }


def alternatives_for_acte(
    acte_id: int,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Offres pour un acte (tri : prix+proximité si coordonnées)."""
    candidates = list(_pa_base_qs([acte_id]))
    if lat is not None and lng is not None:

        def sort_key(pa: PrestataireActe) -> tuple[float, float]:
            d = _org_distance_km(pa.organisme, lat, lng)
            return (float(pa.price) + d * 100.0, d)

        candidates.sort(key=sort_key)
    else:
        candidates.sort(key=lambda pa: float(pa.price))
    return [line_dict(pa) for pa in candidates[:limit]]


def compose_plans(
    acte_ids: list[int],
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> dict[str, Any]:
    """Réponse agrégée pour l'API / le front."""
    acte_ids = _dedupe_acte_ids(acte_ids)
    warnings: list[str] = []
    plans: list[dict[str, Any]] = []

    singles = build_single_center_plans(acte_ids, lat, lng, max_plans=4)
    if singles:
        plans.append(singles[0])
        if len(singles) > 1:
            plans.append(singles[1])

    mc = build_multi_cheapest(acte_ids, lat, lng)
    if mc["missing_actes"]:
        warnings.append(
            "Sans offre pour : " + ", ".join(mc["missing_actes"])
        )
    plans.append(mc)

    if lat is not None and lng is not None:
        mn = build_multi_nearest(acte_ids, lat, lng)
        if mn:
            plans.append(mn)
        bal = build_balanced(acte_ids, lat, lng)
        if bal:
            plans.append(bal)

    # Dédupliquer scénarios identiques (mêmes PA) et retirer les plans sans ligne
    seen_sig: set[tuple[int, ...]] = set()
    unique: list[dict[str, Any]] = []
    for p in plans:
        lines = p.get("lines") or []
        if not lines:
            continue
        sig = tuple(sorted(ln["prestataire_acte_id"] for ln in lines))
        if sig in seen_sig:
            continue
        seen_sig.add(sig)
        unique.append(p)

    return {"plans": unique, "warnings": warnings, "acte_count": len(acte_ids)}
