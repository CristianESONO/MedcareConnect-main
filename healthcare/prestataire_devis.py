"""Registre devis prestataire — enrichissement lignes (RDV, fil, actions)."""
from __future__ import annotations

from django.db.models import Q, Sum
from django.utils.formats import date_format

from appointments.models import RendezVous


def _rdv_maps_for_parts(part_ids):
    """Dernier RDV actif et RDV en attente de confirmation, par sous-devis."""
    if not part_ids:
        return {}, {}
    active = {}
    pending = {}
    qs = (
        RendezVous.objects.filter(devis_part_id__in=part_ids)
        .exclude(status__in=(RendezVous.STATUS_DECLINED, RendezVous.STATUS_CANCELLED))
        .order_by("-created_at")
    )
    for rdv in qs:
        active.setdefault(rdv.devis_part_id, rdv)
        if rdv.status == RendezVous.STATUS_REQUESTED:
            pending.setdefault(rdv.devis_part_id, rdv)
    return active, pending


def _creneau_label(rdv) -> str:
    if not rdv or not rdv.start:
        return ""
    return date_format(rdv.start, r"D j M · H\hi")


def prestataire_devis_kpis(base_qs):
    """KPI bandeau (aligné démo structures)."""
    active_qs = base_qs.exclude(status="archived")
    accepted_q = Q(
        rendez_vous__status__in=(
            RendezVous.STATUS_CONFIRMED,
            RendezVous.STATUS_COMPLETED,
        )
    )
    return {
        "active": active_qs.count(),
        "new": active_qs.filter(status="sent").count(),
        "accepted": active_qs.filter(accepted_q).distinct().count(),
        "total_value": active_qs.aggregate(v=Sum("total_brut"))["v"] or 0,
    }


def prestataire_devis_filter_qs(base_qs, status_filter: str):
    """Filtre liste — sémantique démo + statuts techniques."""
    if status_filter == "active":
        return base_qs.exclude(status="archived")
    if status_filter == "all":
        return base_qs
    if status_filter == "new":
        return base_qs.filter(status="sent")
    if status_filter == "accepted":
        return base_qs.filter(
            rendez_vous__status__in=(
                RendezVous.STATUS_CONFIRMED,
                RendezVous.STATUS_COMPLETED,
            )
        ).distinct()
    return base_qs.filter(status=status_filter)


def prestataire_devis_counts(base_qs):
    accepted_q = Q(
        rendez_vous__status__in=(
            RendezVous.STATUS_CONFIRMED,
            RendezVous.STATUS_COMPLETED,
        )
    )
    active_qs = base_qs.exclude(status="archived")
    return {
        "active": active_qs.count(),
        "all": base_qs.count(),
        "new": base_qs.filter(status="sent").count(),
        "sent": base_qs.filter(status="sent").count(),
        "viewed": base_qs.filter(status="viewed").count(),
        "accepted": active_qs.filter(accepted_q).distinct().count(),
        "relanced": base_qs.filter(status="relanced").count(),
        "expired": base_qs.filter(status="expired").count(),
        "archived": base_qs.filter(status="archived").count(),
    }


def prestataire_devis_rows(parts):
    """Enrichit une page de DevisPart pour templates liste / détail."""
    from messaging.thread import conversation_for_part, thread_url

    part_ids = [p.pk for p in parts]
    active_rdv_map, pending_rdv_map = _rdv_maps_for_parts(part_ids)
    rows = []
    for part in parts:
        active_rdv = active_rdv_map.get(part.pk)
        pending_rdv = pending_rdv_map.get(part.pk)
        creneau = _creneau_label(pending_rdv or active_rdv)
        is_accepted = bool(
            active_rdv
            and active_rdv.status
            in (RendezVous.STATUS_CONFIRMED, RendezVous.STATUS_COMPLETED)
        )
        conv = conversation_for_part(part)
        show_confirm = bool(
            pending_rdv
            and not part.is_archived
            and part.status not in ("expired", "archived")
        )
        show_relance = bool(
            not part.is_archived
            and part.can_relance()
            and (
                not pending_rdv
                or part.status in ("relanced", "expired")
            )
        )
        rows.append(
            {
                "part": part,
                "devis": part.devis,
                "items": part.details or [],
                "subtotal": part.total_brut,
                "items_count": len(part.details or []),
                "active_rdv": active_rdv,
                "pending_rdv": pending_rdv,
                "creneau": creneau,
                "has_creneau": bool(pending_rdv),
                "is_accepted": is_accepted,
                "thread_url": thread_url(conv) if conv else None,
                "show_confirm": show_confirm,
                "show_relance": show_relance,
            }
        )
    return rows
