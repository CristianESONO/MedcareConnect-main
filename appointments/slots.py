"""Génération de créneaux de rendez-vous à partir des horaires d'ouverture.

Les horaires sont stockés dans `OrganismeDeSante.opening_hours` (JSON), au format :

    {"Lundi": {"open": "08:00", "close": "18:00", "closed": false}, ...}

On découpe chaque journée ouverte en créneaux de `slot_minutes`. Un créneau est
indisponible s'il est dans le passé. Plusieurs RDV peuvent partager le même créneau.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

DEFAULT_SLOT_MINUTES = 30
DEFAULT_HORIZON_DAYS = 21
DEFAULT_MAX_DAYS = 7
BOOKING_HORIZON_DAYS = 12
BOOKING_WINDOW_START = "07:30"
BOOKING_WINDOW_END = "11:00"


def _parse_hhmm(value):
    if not value:
        return None
    try:
        parts = str(value).split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, TypeError, IndexError):
        return None


def _taken_starts(organisme, day_start, day_end):
    from .models import RendezVous

    return set(
        RendezVous.objects.filter(
            organisme=organisme,
            status__in=RendezVous.OPEN_STATUSES,
            start__gte=day_start,
            start__lt=day_end,
        ).values_list("start", flat=True)
    )


def _safe_day_hours(organisme, weekday_idx: int) -> dict:
    raw = getattr(organisme, "opening_hours", None)
    if isinstance(raw, dict):
        return raw.get(JOURS[weekday_idx], {}) or {}
    if weekday_idx < 6:
        return {"open": "08:00", "close": "18:00", "closed": False}
    return {"closed": True}


def day_slots(
    organisme,
    the_date,
    slot_minutes=DEFAULT_SLOT_MINUTES,
    now=None,
    window_start=None,
    window_end=None,
):
    """Liste des créneaux pour une journée : [{value, label, available}]."""
    now = now or timezone.localtime()
    hours = _safe_day_hours(organisme, the_date.weekday())
    if not hours or hours.get("closed"):
        return []
    open_t = _parse_hhmm(hours.get("open"))
    close_t = _parse_hhmm(hours.get("close"))
    if not open_t or not close_t:
        return []
    min_t = _parse_hhmm(window_start)
    max_t = _parse_hhmm(window_end)
    if min_t and min_t > open_t:
        open_t = min_t
    if max_t and max_t < close_t:
        close_t = max_t

    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(the_date, open_t), tz)
    end_dt = timezone.make_aware(datetime.combine(the_date, close_t), tz)
    if end_dt <= start_dt:
        return []

    step = timedelta(minutes=slot_minutes)
    slots = []
    cur = start_dt
    while cur + step <= end_dt:
        slots.append({
            "value": cur.isoformat(),
            "label": cur.strftime("%Hh%M"),
            "available": cur >= now,
        })
        cur += step
    return slots


def availability(
    organisme,
    horizon_days=DEFAULT_HORIZON_DAYS,
    slot_minutes=DEFAULT_SLOT_MINUTES,
    max_days=DEFAULT_MAX_DAYS,
    window_start=None,
    window_end=None,
):
    """Jours (jusqu'à `max_days`) ayant au moins un créneau disponible."""
    now = timezone.localtime()
    out = []
    today = now.date()
    for i in range(horizon_days):
        the_date = today + timedelta(days=i)
        slots = day_slots(
            organisme,
            the_date,
            slot_minutes,
            now=now,
            window_start=window_start,
            window_end=window_end,
        )
        if any(s["available"] for s in slots):
            out.append({
                "date": the_date,
                "weekday": JOURS[the_date.weekday()],
                "slots": slots,
            })
        if len(out) >= max_days:
            break
    return out


def first_available_slot(
    organisme,
    horizon_days=BOOKING_HORIZON_DAYS,
    slot_minutes=DEFAULT_SLOT_MINUTES,
    window_start=BOOKING_WINDOW_START,
    window_end=BOOKING_WINDOW_END,
):
    """Premier créneau disponible dans la fenêtre patient."""
    for day in availability(
        organisme,
        horizon_days=horizon_days,
        slot_minutes=slot_minutes,
        max_days=horizon_days,
        window_start=window_start,
        window_end=window_end,
    ):
        for slot in day["slots"]:
            if slot["available"]:
                return slot["value"]
    return None


def has_bookable_hours(organisme) -> bool:
    """Vrai si la structure a au moins un jour ouvré exploitable (prise de RDV en ligne possible)."""
    for idx, day in enumerate(JOURS):
        h = _safe_day_hours(organisme, idx)
        if h.get("closed"):
            continue
        open_t = _parse_hhmm(h.get("open"))
        close_t = _parse_hhmm(h.get("close"))
        if open_t and close_t and close_t > open_t:
            return True
    return False


def is_slot_available(organisme, value, slot_minutes=DEFAULT_SLOT_MINUTES, exclude_rdv=None):
    """Vérifie qu'une valeur ISO correspond à un créneau dans les horaires (plusieurs RDV possibles)."""
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return False
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    loc = timezone.localtime(dt)
    hours = _safe_day_hours(organisme, loc.weekday())
    if not hours or hours.get("closed"):
        return False
    open_t = _parse_hhmm(hours.get("open"))
    close_t = _parse_hhmm(hours.get("close"))
    if not (open_t and close_t):
        return False
    if loc.time() < open_t:
        return False
    if datetime.combine(loc.date(), loc.time()) + timedelta(minutes=slot_minutes) > datetime.combine(loc.date(), close_t):
        return False
    if loc < timezone.localtime():
        return False

    return True
