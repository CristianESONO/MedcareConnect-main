"""Affichage compact et lisible des horaires d'ouverture."""
from __future__ import annotations

JOURS_FR = [
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
]

DAY_ABBR = {
    "Lundi": "Lun",
    "Mardi": "Mar",
    "Mercredi": "Mer",
    "Jeudi": "Jeu",
    "Vendredi": "Ven",
    "Samedi": "Sam",
    "Dimanche": "Dim",
}


def hours_list_from_org(org) -> list[dict]:
    """Liste ordonnée Lundi→Dimanche pour une structure."""
    rows: list[dict] = []
    raw = org.opening_hours or {}
    if not raw:
        return rows
    for day in JOURS_FR:
        info = raw.get(day) or {}
        rows.append({"day": day, **info})
    return rows


def format_time_fr(value: str | None) -> str:
    """08:00 → 8h · 07:30 → 7h30."""
    if not value:
        return ""
    text = str(value).strip()
    if ":" not in text:
        return text
    hour_s, minute_s = text.split(":", 1)
    try:
        hour = int(hour_s)
        minute = int(minute_s)
    except (TypeError, ValueError):
        return text
    if minute == 0:
        return f"{hour}h"
    return f"{hour}h{minute:02d}"


def format_hours_range(open_time: str | None, close_time: str | None) -> str:
    start = format_time_fr(open_time)
    end = format_time_fr(close_time)
    if start and end:
        return f"{start}–{end}"
    return start or end or ""


def _day_abbr(day_name: str) -> str:
    return DAY_ABBR.get(day_name, (day_name or "")[:3])


def group_opening_hours(hours_list: list[dict]) -> list[dict]:
    """Regroupe les jours consécutifs avec les mêmes plages horaires."""
    open_days = [
        h
        for h in hours_list
        if not h.get("closed") and (h.get("open") or h.get("close"))
    ]
    if not open_days:
        return []

    groups: list[dict] = []
    current: dict | None = None
    for row in open_days:
        key = (row.get("open") or "", row.get("close") or "")
        abbr = _day_abbr(row.get("day") or "")
        if current and current["key"] == key:
            current["end"] = abbr
            current["end_day"] = row.get("day")
        else:
            if current:
                groups.append(current)
            current = {
                "start": abbr,
                "end": abbr,
                "start_day": row.get("day"),
                "end_day": row.get("day"),
                "open": row.get("open"),
                "close": row.get("close"),
                "key": key,
            }
    if current:
        groups.append(current)
    return groups


def format_day_range(start_abbr: str, end_abbr: str) -> str:
    if not start_abbr:
        return end_abbr or ""
    if not end_abbr or start_abbr == end_abbr:
        return start_abbr
    return f"{start_abbr}–{end_abbr}"


def profil_hours_meta_chunks(hours_list: list[dict], *, max_groups: int = 6) -> list[str]:
    """Segments lisibles, ex. ['Lun–Jeu 8h–18h', 'Ven 8h–17h']."""
    chunks: list[str] = []
    for group in group_opening_hours(hours_list)[:max_groups]:
        day_part = format_day_range(group["start"], group["end"])
        time_part = format_hours_range(group.get("open"), group.get("close"))
        label = f"{day_part} {time_part}".strip()
        if label:
            chunks.append(label)
    return chunks


def profil_hours_meta(hours_list: list[dict]) -> str:
    chunks = profil_hours_meta_chunks(hours_list)
    if not chunks:
        return "Horaires non renseignés"
    return " · ".join(chunks)


def opening_hours_summary_for_org(org, *, max_len: int = 72) -> str:
    """Résumé pour cartes recherche / annuaire."""
    summary = profil_hours_meta(hours_list_from_org(org))
    if summary != "Horaires non renseignés":
        return summary[:max_len]
    note = (org.horaires_complement or "").strip()
    if note:
        return note.split("\n")[0].strip()[:max_len]
    return ""
