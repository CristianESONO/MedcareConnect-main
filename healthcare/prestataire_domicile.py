"""Prestations à domicile — inline sur le catalogue actes (aligné démo)."""

from __future__ import annotations

import json

from django.http import JsonResponse

from healthcare.models import OrganismeDeSante, PrelevementZone

DOMICILE_DELAI_CHOICES = (
    ("meme_jour", "Même jour"),
    ("sous_24h", "Sous 24h"),
    ("matin", "Matin uniquement"),
    ("sur_rdv", "Sur RDV uniquement"),
)


def show_domicile_block(org: OrganismeDeSante, applicable_slugs: set[str] | None) -> bool:
    """Afficher le bloc domicile si biologie applicable ou service déjà activé."""
    if org.prises_sang_domicile:
        return True
    if applicable_slugs is None:
        return True
    return "biologie-medicale" in applicable_slugs


def domicile_zones_queryset(org: OrganismeDeSante):
    return PrelevementZone.objects.filter(organisme=org).order_by("order", "label")


def domicile_subgroups_from_catalog(catalog_by_pilier: list) -> tuple[list[dict], list[int]]:
    """Catégories biologie pour les tags « actes à domicile » (aligné démo)."""
    for block in catalog_by_pilier:
        if block.get("pilier") and block["pilier"].slug == "biologie-medicale":
            if not block.get("applicable"):
                return [], []
            out = []
            all_ids: list[int] = []
            for sg in block.get("subgroups") or []:
                rows = sg.get("rows") or []
                acte_ids = [row["acte"].pk for row in rows if row.get("acte")]
                active_ids = [
                    row["acte"].pk
                    for row in rows
                    if row.get("acte") and row.get("pa") and row["pa"].is_available
                ]
                all_ids.extend(acte_ids)
                out.append(
                    {
                        "label": sg["label"],
                        "acte_ids": acte_ids,
                        "active_count": len(active_ids),
                        "total_count": len(acte_ids),
                        "all_active": bool(acte_ids) and len(active_ids) == len(acte_ids),
                    }
                )
            return out, all_ids
    return [], []


def domicile_all_actes_active(all_acte_ids: list[int], selected_acte_ids: set[int]) -> bool:
    if not all_acte_ids:
        return False
    return all(id_ in selected_acte_ids for id_ in all_acte_ids)


def _zones_payload(org: OrganismeDeSante) -> list[dict]:
    return [
        {
            "pk": z.pk,
            "label": z.label,
            "forfait_fcfa": z.forfait_fcfa,
            "is_active": z.is_active,
        }
        for z in domicile_zones_queryset(org)
    ]


def _save_domicile_params(org: OrganismeDeSante, request) -> None:
    delai = (request.POST.get("domicile_delai_intervention") or "").strip()
    allowed = {c[0] for c in DOMICILE_DELAI_CHOICES}
    if delai not in allowed:
        delai = ""
    plages = (request.POST.get("domicile_plages_horaires") or "").strip()[:120]
    updates = []
    if org.domicile_delai_intervention != delai:
        org.domicile_delai_intervention = delai
        updates.append("domicile_delai_intervention")
    if org.domicile_plages_horaires != plages:
        org.domicile_plages_horaires = plages
        updates.append("domicile_plages_horaires")
    if updates:
        updates.append("updated_at")
        org.save(update_fields=updates)


def _json_ok(org: OrganismeDeSante, *, message: str = "") -> JsonResponse:
    return JsonResponse(
        {
            "ok": True,
            "message": message,
            "prises_sang_domicile": org.prises_sang_domicile,
            "domicile_delai_intervention": org.domicile_delai_intervention,
            "domicile_plages_horaires": org.domicile_plages_horaires,
            "zones": _zones_payload(org),
        }
    )


def sync_domicile_zones(org: OrganismeDeSante, zones_data: list[dict]) -> None:
    existing = {z.pk: z for z in PrelevementZone.objects.filter(organisme=org)}
    seen: set[int] = set()
    order = 0
    for row in zones_data:
        label = (row.get("label") or "").strip()
        if not label:
            continue
        try:
            forfait = max(0, int(row.get("forfait_fcfa") or 0))
        except (TypeError, ValueError):
            forfait = 0
        pk = row.get("pk")
        try:
            pk_int = int(pk) if pk else None
        except (TypeError, ValueError):
            pk_int = None

        if pk_int and pk_int in existing:
            zone = existing[pk_int]
            zone.label = label
            zone.forfait_fcfa = forfait
            zone.order = order
            zone.is_active = True
            zone.save(update_fields=["label", "forfait_fcfa", "order", "is_active", "updated_at"])
            seen.add(pk_int)
        else:
            zone, _ = PrelevementZone.objects.get_or_create(
                organisme=org,
                label=label,
                defaults={"forfait_fcfa": forfait, "order": order, "is_active": True},
            )
            if zone.pk not in existing:
                zone.forfait_fcfa = forfait
                zone.order = order
                zone.save(update_fields=["forfait_fcfa", "order", "updated_at"])
            seen.add(zone.pk)
        order += 1

    for pk, zone in existing.items():
        if pk not in seen:
            zone.delete()


def handle_domicile_post(request, org: OrganismeDeSante) -> JsonResponse:
    op = (request.POST.get("domicile_op") or "save").strip()

    if op == "toggle":
        org.prises_sang_domicile = request.POST.get("prises_sang_domicile") == "1"
        org.save(update_fields=["prises_sang_domicile", "updated_at"])
        _save_domicile_params(org, request)
        msg = (
            "Prestations à domicile activées."
            if org.prises_sang_domicile
            else "Prestations à domicile désactivées."
        )
        return _json_ok(org, message=msg)

    if op == "delete_zone":
        try:
            pk = int(request.POST.get("zone_pk") or 0)
        except (TypeError, ValueError):
            pk = 0
        PrelevementZone.objects.filter(organisme=org, pk=pk).delete()
        return _json_ok(org, message="Zone supprimée.")

    raw = request.POST.get("zones_json") or "[]"
    try:
        zones_data = json.loads(raw)
        if not isinstance(zones_data, list):
            zones_data = []
    except json.JSONDecodeError:
        zones_data = []

    if request.POST.get("prises_sang_domicile") is not None:
        org.prises_sang_domicile = request.POST.get("prises_sang_domicile") == "1"
        org.save(update_fields=["prises_sang_domicile", "updated_at"])

    _save_domicile_params(org, request)
    sync_domicile_zones(org, zones_data)
    return _json_ok(org, message="Prestations à domicile enregistrées.")
