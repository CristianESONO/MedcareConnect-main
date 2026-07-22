"""Séries temporelles et stats MedPlaque pour le dashboard prestataire."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Count, Sum
from django.db.models.functions import TruncWeek
from django.urls import reverse
from django.utils import timezone

from healthcare.models import OrganismeDeSante, ProfileView
from healthcare.profile_tracking import visit_row_from_profile_view


WEEK_LABELS = [f"S{i}" for i in range(1, 9)]


def _week_starts(num_weeks: int = 8):
    """8 semaines calendaires se terminant la semaine courante (S1…S8)."""
    today = timezone.localdate()
    # Lundi de la semaine courante
    monday = today - timedelta(days=today.weekday())
    starts = []
    for i in range(num_weeks - 1, -1, -1):
        starts.append(monday - timedelta(weeks=i))
    return starts


def _bucket_counts(qs, date_field: str, week_starts: list) -> list[int]:
    """Compte par semaine (8 buckets) + total en 9e position."""
    annotated = (
        qs.annotate(_wk=TruncWeek(date_field))
        .values("_wk")
        .annotate(n=Count("id"))
    )
    by_week = {row["_wk"].date() if row["_wk"] else None: row["n"] for row in annotated}
    data = []
    for start in week_starts:
        data.append(by_week.get(start, 0))
    data.append(sum(data))
    return data


def _apply_period_mask(data: list[int | None], period_key: str) -> list[int | None]:
    """Masque les semaines hors période (null = barre grisée)."""
    if period_key == "total":
        return data
    visible = 1 if period_key == "7j" else 4
    masked = []
    for i, v in enumerate(data):
        if i == len(data) - 1:
            masked.append(v)
        elif i < len(data) - 1 - visible:
            masked.append(None)
        else:
            masked.append(v)
    return masked


def build_activity_chart(org: OrganismeDeSante, period_key: str) -> dict[str, Any]:
    from appointments.models import RendezVous
    from cart.models import CartItem, DevisPart

    week_starts = _week_starts(8)
    since = week_starts[0]

    views_qs = ProfileView.objects.filter(organisme=org, viewed_at__date__gte=since)
    devis_qs = DevisPart.objects.filter(
        organisme=org,
        status__in=["sent", "viewed", "relanced"],
    ).exclude(devis__status="draft").filter(created_at__date__gte=since)
    rdv_qs = RendezVous.objects.filter(
        organisme=org,
        status=RendezVous.STATUS_CONFIRMED,
        created_at__date__gte=since,
    )
    items_qs = CartItem.objects.filter(
        prestataire_acte__organisme=org,
        added_at__date__gte=since,
    )
    plaque_qs = ProfileView.objects.filter(
        organisme=org,
        source__in=[ProfileView.SOURCE_NFC, ProfileView.SOURCE_QR],
        viewed_at__date__gte=since,
    )

    valeur_by_week = (
        devis_qs.annotate(_wk=TruncWeek("created_at"))
        .values("_wk")
        .annotate(v=Sum("total_brut"))
    )
    valeur_map = {
        (row["_wk"].date() if row["_wk"] else None): int((row["v"] or 0) // 1000)
        for row in valeur_by_week
    }
    valeur_data = []
    for start in week_starts:
        valeur_data.append(valeur_map.get(start, 0))
    valeur_data.append(sum(valeur_data))

    raw_series = {
        "devis": _bucket_counts(devis_qs, "created_at", week_starts),
        "vues": _bucket_counts(views_qs, "viewed_at", week_starts),
        "reservations": _bucket_counts(rdv_qs, "created_at", week_starts),
        "valeur": valeur_data,
        "medplaque": _bucket_counts(plaque_qs, "viewed_at", week_starts),
    }

    series = {}
    for key, values in raw_series.items():
        series[key] = _apply_period_mask(values, period_key)

    return {
        "labels": WEEK_LABELS + ["Total"],
        "series": series,
        "meta": {
            "devis": {"label": "Devis générés", "color": "#3b82f6", "color_last": "#10b981"},
            "vues": {"label": "Vues de la fiche", "color": "#60a5fa", "color_last": "#2563eb"},
            "reservations": {"label": "Réservations confirmées", "color": "#c4b5fd", "color_last": "#7c3aed"},
            "valeur": {"label": "Valeur actes (kFCFA)", "color": "#fcd34d", "color_last": "#d97706"},
            "medplaque": {"label": "Accès MedPlaque (NFC + QR)", "color": "#d8b4fe", "color_last": "#9333ea"},
        },
        "period_sub": {
            "7j": "7 derniers jours",
            "30j": "30 derniers jours",
            "total": "cumulé depuis l'activation",
        }.get(period_key, ""),
    }


def medplaque_reference(org: OrganismeDeSante) -> str:
    year = org.created_at.year if org.created_at else timezone.now().year
    return f"CPP-{year}-{org.pk:04d}"


def medplaque_month_index(org: OrganismeDeSante) -> int:
    if not org.created_at:
        return 0
    delta = timezone.now() - org.created_at
    return min(6, max(0, delta.days // 30))


def medplaque_nfc_active(org: OrganismeDeSante) -> bool:
    """NFC hébergée 6 mois (M0→M6) si feature MedPlaque incluse ou plan Pionnier."""
    if not org.plan_allows("medplaque"):
        plan_slug = (getattr(org.subscription_plan, "slug", None) or "").lower()
        if plan_slug != "pionnier":
            return False
    return medplaque_month_index(org) <= 6


def medplaque_stats(org: OrganismeDeSante, since=None) -> dict[str, Any]:
    from cart.models import DevisPart

    views = ProfileView.objects.filter(organisme=org)
    if since:
        views = views.filter(viewed_at__gte=since)

    nfc_scans = views.filter(source=ProfileView.SOURCE_NFC).count()
    qr_scans = views.filter(source=ProfileView.SOURCE_QR).count()
    total_plaque = nfc_scans + qr_scans

    devis_from_plaque = 0
    if total_plaque:
        devis_qs = DevisPart.objects.filter(
            organisme=org,
            status__in=["sent", "viewed", "relanced"],
        ).exclude(devis__status="draft")
        if since:
            devis_qs = devis_qs.filter(created_at__gte=since)
        devis_from_plaque = devis_qs.count()

    scan_to_visit_pct = 100 if total_plaque else 0
    visit_to_devis_pct = (
        round(devis_from_plaque * 100.0 / max(total_plaque, 1))
        if total_plaque
        else 0
    )

    month_idx = medplaque_month_index(org)
    base_url = reverse("healthcare:organisme_detail", args=[org.slug])
    return {
        "reference": medplaque_reference(org),
        "nfc_scans": nfc_scans,
        "qr_scans": qr_scans,
        "total_access": total_plaque,
        "nfc_active": medplaque_nfc_active(org),
        "month_index": month_idx,
        "month_label": f"M0 → M{month_idx}",
        "scan_to_visit_pct": scan_to_visit_pct,
        "visit_to_devis_pct": visit_to_devis_pct,
        "profile_url_nfc": f"{base_url}?src=nfc&utm_source=medplaque&utm_medium=nfc",
        "profile_url_qr": f"{base_url}?src=qr&utm_source=medplaque&utm_medium=qr",
    }


def recent_visits(org: OrganismeDeSante, limit: int = 8, source: str | None = None) -> list[dict]:
    qs = ProfileView.objects.filter(organisme=org).select_related("viewer", "organisme")
    if source and source != "all":
        qs = qs.filter(source=source)
    return [visit_row_from_profile_view(v) for v in qs.order_by("-viewed_at")[:limit]]
