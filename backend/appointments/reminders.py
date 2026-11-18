"""Envoi des rappels RDV configurables + agrégation des prérequis actes."""
from __future__ import annotations

from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone

from healthcare.models import ActeMedical

from .models import RdvReminderSchedule, RendezVous, RendezVousReminderLog


def acte_ids_from_snapshot(actes_snapshot: list | None) -> set[int]:
    ids: set[int] = set()
    for row in actes_snapshot or []:
        raw = row.get("acte_id")
        if raw is not None:
            try:
                ids.add(int(raw))
            except (TypeError, ValueError):
                pass
    return ids


def acte_names_from_snapshot(actes_snapshot: list | None) -> set[str]:
    return {
        (row.get("acte") or "").strip()
        for row in (actes_snapshot or [])
        if (row.get("acte") or "").strip()
    }


def prerequisites_for_rdv(rdv: RendezVous) -> str:
    """Consignes agrégées des actes du RDV (override structure > référentiel MedCare)."""
    from healthcare.models import PrestataireActe

    snapshot = rdv.actes_snapshot or []
    acte_ids = acte_ids_from_snapshot(snapshot)
    acte_names = acte_names_from_snapshot(snapshot)
    if not acte_ids and not acte_names:
        return ""

    by_id = {
        a.pk: a
        for a in ActeMedical.objects.filter(pk__in=acte_ids)
    }
    by_name: dict[str, ActeMedical] = {}
    if acte_names:
        for acte in ActeMedical.objects.filter(name__in=acte_names):
            by_name.setdefault(acte.name, acte)

    pa_by_acte: dict[int, PrestataireActe] = {}
    if rdv.organisme_id and acte_ids:
        for pa in PrestataireActe.objects.filter(
            organisme_id=rdv.organisme_id,
            acte_id__in=acte_ids,
        ):
            pa_by_acte[pa.acte_id] = pa

    lines: list[str] = []
    seen: set[int] = set()
    for row in snapshot:
        acte = None
        raw_id = row.get("acte_id")
        if raw_id is not None:
            try:
                acte = by_id.get(int(raw_id))
            except (TypeError, ValueError):
                pass
        if not acte:
            name = (row.get("acte") or "").strip()
            acte = by_name.get(name) if name else None
        if not acte or acte.pk in seen:
            continue
        seen.add(acte.pk)
        pa = pa_by_acte.get(acte.pk)
        text = ""
        if pa and pa.rdv_prerequisites_active:
            text = (pa.rdv_prerequisites or "").strip()
            if not text:
                text = (acte.rdv_prerequisites or "").strip()
        else:
            text = (acte.rdv_prerequisites or "").strip()
        if text:
            lines.append(f"• {acte.name} : {text}")
    return "\n".join(lines)


def rdv_matches_schedule(rdv: RendezVous, schedule: RdvReminderSchedule) -> bool:
    """True si la règle s'applique (actes ciblés ou règle globale)."""
    acte_pks = list(schedule.actes.values_list("pk", flat=True))
    if not acte_pks:
        return True
    rdv_ids = acte_ids_from_snapshot(rdv.actes_snapshot)
    if rdv_ids & set(acte_pks):
        return True
    if not rdv_ids:
        rdv_names = acte_names_from_snapshot(rdv.actes_snapshot)
        if rdv_names:
            return schedule.actes.filter(name__in=rdv_names).exists()
    return False


def due_reminders(
    *,
    now=None,
    schedule: RdvReminderSchedule | None = None,
) -> list[tuple[RendezVous, RdvReminderSchedule]]:
    """Paires (RDV, règle) à notifier maintenant."""
    now = now or timezone.now()
    schedules = RdvReminderSchedule.objects.filter(is_active=True).prefetch_related(
        Prefetch("actes", queryset=ActeMedical.objects.only("pk", "name"))
    )
    if schedule is not None:
        schedules = schedules.filter(pk=schedule.pk)

    due: list[tuple[RendezVous, RdvReminderSchedule]] = []
    for rule in schedules.order_by("order", "-offset_value"):
        tol = timezone.timedelta(minutes=max(rule.tolerance_minutes, 1))
        target = now + timezone.timedelta(minutes=rule.minutes_before)
        window_start = target - tol
        window_end = target + tol

        already_sent = RendezVousReminderLog.objects.filter(schedule=rule).values_list(
            "rendez_vous_id", flat=True
        )
        qs = (
            RendezVous.objects.select_related("organisme", "patient")
            .filter(
                status=RendezVous.STATUS_CONFIRMED,
                patient__isnull=False,
                start__gte=window_start,
                start__lte=window_end,
            )
            .exclude(pk__in=already_sent)
            .order_by("start")
        )
        for rdv in qs:
            if rule.organisme_id and rule.organisme_id != rdv.organisme_id:
                continue
            if rdv_matches_schedule(rdv, rule):
                due.append((rdv, rule))
    return due


def send_rdv_reminder(
    rdv: RendezVous,
    schedule: RdvReminderSchedule,
    *,
    dry_run: bool = False,
) -> bool:
    """Déclenche rdv.reminder et journalise l'envoi."""
    if dry_run:
        return True

    prerequisites = ""
    if schedule.include_prerequisites:
        prerequisites = prerequisites_for_rdv(rdv)

    thread_link = reverse("healthcare:search") + "?pac=rdv"
    try:
        from messaging.thread import conversation_for_rdv, on_rdv_reminder, thread_url

        conv = conversation_for_rdv(rdv)
        if conv:
            thread_link = thread_url(conv)
    except Exception:
        pass

    try:
        from notifications.dispatcher import dispatch

        dispatch(
            "rdv.reminder",
            context={
                "rdv": rdv,
                "patient": rdv.patient,
                "organisme": rdv.organisme,
                "schedule": schedule,
                "schedule_label": schedule.label,
                "prerequisites": prerequisites,
                "link": thread_link,
            },
            actor=rdv.patient,
        )
    except Exception:
        return False

    try:
        from messaging.thread import on_rdv_reminder

        on_rdv_reminder(
            rdv,
            schedule_label=schedule.label,
            schedule_id=schedule.pk,
            prerequisites=prerequisites,
        )
    except Exception:
        pass

    RendezVousReminderLog.objects.create(rendez_vous=rdv, schedule=schedule)
    # Compatibilité historique (ancien cron J-1 unique).
    if rdv.reminder_sent_at is None:
        rdv.reminder_sent_at = timezone.now()
        rdv.save(update_fields=["reminder_sent_at", "updated_at"])
    return True
