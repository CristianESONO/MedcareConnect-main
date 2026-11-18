"""Construction de l'agenda hebdomadaire de la structure (vue calendrier).

On part des horaires d'ouverture (`OrganismeDeSante.opening_hours`) pour générer une
grille semaine × créneaux. Chaque cellule sait si elle est dans les heures d'ouverture,
si elle est occupée par un RDV (en ligne ou sur place) ou libre (donc « renseignable »).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.utils import timezone

from .slots import DEFAULT_SLOT_MINUTES, JOURS, _parse_hhmm

MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def week_monday(d: date) -> date:
    """Lundi de la semaine contenant `d`."""
    return d - timedelta(days=d.weekday())


def _fr_label(d: date, t: time) -> str:
    return f"{JOURS[d.weekday()][:3]} {d.day:02d}/{d.month:02d} · {t.strftime('%Hh%M')}"


def _fr_when(dt: datetime) -> str:
    loc = timezone.localtime(dt)
    return f"{JOURS[loc.weekday()]} {loc.day} {MOIS[loc.month - 1]} · {loc:%Hh%M}"


def build_week(org, monday: date, slot_minutes: int = DEFAULT_SLOT_MINUTES) -> dict:
    """Retourne la structure de l'agenda pour la semaine commençant à `monday`.

    {
      "days": [{date, weekday, is_today, is_open}, ...7],
      "rows": [{time, cells: [cell, ...7]}, ...],
      "rdvs": {ref: {...}},   # données pour la modale détail
    }
    """
    from .models import RendezVous

    tz = timezone.get_current_timezone()
    now = timezone.localtime()
    today = now.date()

    from .slots import _safe_day_hours

    days, day_hours = [], []
    min_open = max_close = None
    for i in range(7):
        d = monday + timedelta(days=i)
        hours = _safe_day_hours(org, d.weekday())
        open_t = close_t = None
        if hours and not hours.get("closed"):
            open_t = _parse_hhmm(hours.get("open"))
            close_t = _parse_hhmm(hours.get("close"))
            if not (open_t and close_t and close_t > open_t):
                open_t = close_t = None
        if open_t and close_t:
            min_open = open_t if min_open is None or open_t < min_open else min_open
            max_close = close_t if max_close is None or close_t > max_close else max_close
        day_hours.append((open_t, close_t))
        days.append({
            "date": d,
            "weekday": JOURS[d.weekday()],
            "is_today": d == today,
            "is_open": open_t is not None,
        })

    if min_open is None:
        min_open, max_close = time(8, 0), time(18, 0)

    # RDV de la semaine qui occupent un créneau.
    week_start = timezone.make_aware(datetime.combine(monday, time(0, 0)), tz)
    week_end = week_start + timedelta(days=7)
    rdvs = (
        RendezVous.objects.filter(
            organisme=org,
            status__in=RendezVous.OCCUPYING_STATUSES,
            start__gte=week_start,
            start__lt=week_end,
        )
        .select_related("patient", "devis")
        .order_by("start")
    )
    taken: dict[str, list] = {}
    payload = {}
    for r in rdvs:
        key = timezone.localtime(r.start).strftime("%Y-%m-%d %H:%M")
        taken.setdefault(key, []).append(r)
        payload[r.reference] = {
            "ref": r.reference,
            "name": r.patient_label,
            "phone": r.patient_phone,
            "when": _fr_when(r.start),
            "slot_iso": timezone.localtime(r.start).strftime("%Y-%m-%dT%H:%M"),
            "status": r.status,
            "status_label": r.get_status_display(),
            "source": r.source,
            "is_walk_in": r.is_walk_in,
            "motif": r.walk_in_motif,
            "devis": r.devis.reference if r.devis_id else "",
            "total": str(int(r.total_patient or 0)),
            "note": r.prestataire_note or r.patient_note,
            "actes": [l.get("acte", "") for l in (r.actes_snapshot or []) if l.get("acte")],
        }

    step = timedelta(minutes=slot_minutes)
    rows = []
    cur = datetime.combine(monday, min_open)
    end_marker = datetime.combine(monday, max_close)
    while cur < end_marker:
        t = cur.time()
        cells = []
        for i, day in enumerate(days):
            open_t, close_t = day_hours[i]
            cell = {"in_hours": False}
            if open_t and close_t and open_t <= t:
                slot_end = datetime.combine(day["date"], t) + step
                if slot_end <= datetime.combine(day["date"], close_t):
                    slot_dt = timezone.make_aware(datetime.combine(day["date"], t), tz)
                    key = slot_dt.strftime("%Y-%m-%d %H:%M")
                    rdvs_in_slot = taken.get(key, [])
                    cell = {
                        "in_hours": True,
                        "value": slot_dt.isoformat(),
                        "label": _fr_label(day["date"], t),
                        "rdvs": rdvs_in_slot,
                        "rdv_count": len(rdvs_in_slot),
                        "is_past": slot_dt < now,
                    }
            cells.append(cell)
        rows.append({"time": t.strftime("%Hh%M"), "cells": cells})
        cur += step

    return {"days": days, "rows": rows, "rdvs": payload}


def validate_walkin_slot(org, value, slot_minutes: int = DEFAULT_SLOT_MINUTES):
    """Valide un créneau saisi par la structure pour un RDV sur place.

    Retourne le datetime aware si le créneau est dans les heures d'ouverture et aligné
    (plusieurs RDV peuvent partager le même créneau).
    """
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    loc = timezone.localtime(dt)
    d, t = loc.date(), loc.time()
    hours = _safe_day_hours(org, d.weekday())
    if not hours or hours.get("closed"):
        return None
    open_t = _parse_hhmm(hours.get("open"))
    close_t = _parse_hhmm(hours.get("close"))
    if not (open_t and close_t and open_t <= t):
        return None
    if datetime.combine(d, t) + timedelta(minutes=slot_minutes) > datetime.combine(d, close_t):
        return None

    return dt
