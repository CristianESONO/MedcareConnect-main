"""Rappels RDV par acte — panneau préparation catalogue (aligné démo)."""
from __future__ import annotations

from appointments.models import RdvReminderSchedule
from healthcare.models import ActeMedical, OrganismeDeSante


def reminders_for_acte(org: OrganismeDeSante, acte_id: int) -> list[dict]:
    """Rappels horaires (H-12, H-6…) liés à un acte pour une structure."""
    qs = (
        RdvReminderSchedule.objects.filter(organisme=org, actes__pk=acte_id)
        .distinct()
        .order_by("-offset_value", "pk")
    )
    out = []
    for s in qs:
        hours = None
        display = s.label
        if s.offset_unit == RdvReminderSchedule.UNIT_HOURS:
            hours = s.offset_value
            display = f"H-{hours}"
        out.append(
            {
                "pk": s.pk,
                "label": s.label,
                "hours": hours,
                "display": display,
            }
        )
    return out


def add_hourly_reminder(org: OrganismeDeSante, acte: ActeMedical, hours: int):
    """Crée un rappel H-N pour l'acte (idempotent si déjà présent)."""
    if hours < 1 or hours > 168:
        return None, "Indiquez un nombre d'heures entre 1 et 168."

    existing = (
        RdvReminderSchedule.objects.filter(
            organisme=org,
            offset_value=hours,
            offset_unit=RdvReminderSchedule.UNIT_HOURS,
            actes=acte,
        )
        .first()
    )
    if existing:
        return existing, None

    schedule = RdvReminderSchedule.objects.create(
        organisme=org,
        label=f"H-{hours}",
        offset_value=hours,
        offset_unit=RdvReminderSchedule.UNIT_HOURS,
        tolerance_minutes=30,
        include_prerequisites=True,
        is_active=True,
        order=hours * 10,
    )
    schedule.actes.add(acte)
    return schedule, None


def delete_acte_reminder(org: OrganismeDeSante, acte_id: int, schedule_pk: int) -> bool:
    deleted, _ = RdvReminderSchedule.objects.filter(
        pk=schedule_pk,
        organisme=org,
        actes__pk=acte_id,
    ).delete()
    return deleted > 0
