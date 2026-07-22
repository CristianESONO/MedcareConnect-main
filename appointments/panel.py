"""Helpers partagés pour l'onglet « Mes RDV » du panneau compte patient."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render
from django.utils import timezone

from .models import RendezVous


def patient_rdv_context(user) -> dict:
    """Sépare les RDV du patient en « à venir » et « historique »."""
    from messaging.thread import conversation_for_rdv, thread_url

    qs = (
        RendezVous.objects.filter(patient=user)
        .select_related("organisme", "devis", "devis_part")
        .order_by("start")
    )
    now = timezone.now()
    upcoming, past = [], []
    for rdv in qs:
        conv = conversation_for_rdv(rdv)
        rdv.thread_url = thread_url(conv) if conv else None
        if rdv.status in RendezVous.LIVE_STATUSES and rdv.start and rdv.start >= now:
            upcoming.append(rdv)
        else:
            past.append(rdv)
    past.reverse()
    return {"rdv_upcoming": upcoming, "rdv_past": past}


def render_rdv_panel(request):
    """Rend le partial « Mes RDV » (injecté dans le drawer compte patient)."""
    ctx = patient_rdv_context(request.user)
    ctx["account_active"] = "rdv"
    ctx["pac_messages"] = list(messages.get_messages(request))
    return render(request, "users/patient_panel/_rdv.html", ctx)


def book_data_json(org, part) -> tuple[str, bool]:
    """Construit le payload JSON des disponibilités pour le chat de prise de RDV.

    Retourne (json_str, has_slots).
    """
    import json

    from django.utils.formats import date_format

    from . import slots as slot_engine

    days = slot_engine.availability(
        org,
        horizon_days=slot_engine.BOOKING_HORIZON_DAYS,
        max_days=slot_engine.BOOKING_HORIZON_DAYS,
        window_start=slot_engine.BOOKING_WINDOW_START,
        window_end=slot_engine.BOOKING_WINDOW_END,
    )
    soonest = next(
        (
            {"value": s["value"], "label": f"{d['weekday']} {s['label']}"}
            for d in days
            for s in d["slots"]
            if s["available"]
        ),
        None,
    )
    data = {
        "org": org.name,
        "org_city": org.city or "",
        "part": part.reference,
        "total": str(int(part.total_patient or 0)),
        "actes": [
            {
                "acte": line.get("acte", ""),
                "quantity": int(line.get("quantity") or 1),
                "price": int(float(line.get("patient_cost") or line.get("subtotal") or 0)),
            }
            for line in (part.details or [])
        ],
        "soonest": soonest,
        "days": [
            {
                "label": date_format(d["date"], "l j F"),
                "short": date_format(d["date"], "d/m/Y"),
                "slots": [
                    {"value": s["value"], "label": s["label"], "available": s["available"]}
                    for s in d["slots"]
                ],
            }
            for d in days
        ],
    }
    return json.dumps(data, ensure_ascii=False), bool(data["days"])


def snapshot_from_devis_part(part) -> tuple[list, object, object]:
    """Construit le snapshot d'actes + totaux figés depuis un DevisPart."""
    lines = []
    for line in part.details or []:
        lines.append({
            "acte_id": line.get("acte_id"),
            "acte": line.get("acte", ""),
            "quantity": line.get("quantity", 1),
            "subtotal": line.get("subtotal"),
            "patient_cost": line.get("patient_cost"),
        })
    return lines, part.total_brut, part.total_patient
