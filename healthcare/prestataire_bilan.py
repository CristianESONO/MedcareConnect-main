"""Bilan KPI Pionnier — blocs A/B/C et recommandation de passage de plan."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from healthcare.models import OrganismeDeSante, ProfileView, SubscriptionPlan
from healthcare.prestataire_analytics import medplaque_month_index, medplaque_reference


def _fmt_int(value: int | float) -> str:
    n = int(round(value))
    return f"{n:,}".replace(",", "\u202f")


def _fmt_pct(value: float) -> str:
    s = f"{value:.1f}".replace(".", ",")
    if s.endswith(",0"):
        s = s[:-2]
    return f"{s}%"


def _kpi_row(
    label: str,
    val_display: str,
    current: float,
    target: float,
    *,
    higher_is_better: bool = True,
    cible_display: str | None = None,
) -> dict[str, Any]:
    if target <= 0:
        pct = 100 if current > 0 else 0
        signal = "ok" if current > 0 else "warn"
    elif higher_is_better:
        pct = min(100, round(current / target * 100))
        if current >= target:
            signal = "ok"
        elif pct >= 60:
            signal = "warn"
        else:
            signal = "danger"
        cible = cible_display or f"≥ {_fmt_int(target)}"
    else:
        if current <= target:
            signal = "ok"
            pct = 100
        elif current <= target * 1.5:
            signal = "warn"
            pct = max(0, min(100, round(target / current * 100)))
        else:
            signal = "danger"
            pct = max(0, min(100, round(target / current * 100)))
        cible = cible_display or f"≤ {_fmt_pct(target)}"

    return {
        "label": label,
        "val": val_display,
        "cible": cible,
        "signal": signal,
        "pct": pct,
    }


def _pioneer_m6_context(org: OrganismeDeSante) -> dict[str, Any]:
    if not org.created_at:
        return {
            "days_remaining": None,
            "end_date": None,
            "progress_pct": 0,
            "label": "M0 → M6",
            "available_upgrade": False,
        }
    end = org.created_at + timezone.timedelta(days=180)
    now = timezone.now()
    days_remaining = max(0, (end.date() - now.date()).days)
    elapsed = (now - org.created_at).days
    progress_pct = min(100, round(elapsed / 180 * 100))
    return {
        "days_remaining": days_remaining,
        "end_date": end,
        "progress_pct": progress_pct,
        "label": f"M0 → M{medplaque_month_index(org)}",
        "available_upgrade": days_remaining <= 30 or medplaque_month_index(org) >= 5,
    }


def build_pioneer_bilan(org: OrganismeDeSante) -> dict[str, Any]:
    from appointments.models import RendezVous
    from cart.models import DevisPart

    views_qs = ProfileView.objects.filter(organisme=org)
    total_views = views_qs.count() or org.profile_views_count
    annuaire_views = views_qs.filter(source=ProfileView.SOURCE_ANNUAIRE).count()
    nfc_scans = views_qs.filter(source=ProfileView.SOURCE_NFC).count()

    annuaire_rate = (annuaire_views / total_views * 100) if total_views else 0.0

    devis_qs = DevisPart.objects.filter(
        organisme=org,
        status__in=["sent", "viewed", "relanced"],
    ).exclude(devis__status="draft")
    devis_total = devis_qs.count()

    rdv_qs = RendezVous.objects.filter(organisme=org)
    rdv_confirmed = rdv_qs.filter(
        status__in=[RendezVous.STATUS_CONFIRMED, RendezVous.STATUS_COMPLETED]
    ).count()
    rdv_finished = rdv_qs.filter(
        status__in=[RendezVous.STATUS_COMPLETED, RendezVous.STATUS_NO_SHOW]
    )
    rdv_no_show = rdv_finished.filter(status=RendezVous.STATUS_NO_SHOW).count()
    rdv_done_count = rdv_finished.count()
    no_show_rate = (rdv_no_show / rdv_done_count * 100) if rdv_done_count else 0.0

    devis_to_rdv_pct = (rdv_confirmed / devis_total * 100) if devis_total else 0.0

    valeur = int(devis_qs.aggregate(v=Sum("total_brut"))["v"] or 0)
    pro_plan = SubscriptionPlan.objects.filter(slug="pro", is_public=True).first()
    pro_price = pro_plan.monthly_price_fcfa if pro_plan else 69000
    roi_ratio = (valeur / pro_price) if pro_price else 0.0

    new_patients = (
        devis_qs.values("devis__patient_id")
        .distinct()
        .count()
    )

    section_a = [
        _kpi_row("Vues de la page", _fmt_int(total_views), total_views, 500),
        _kpi_row("Scans MedPlaque NFC", _fmt_int(nfc_scans), nfc_scans, 100),
        _kpi_row(
            "Taux de clic annuaire",
            _fmt_pct(annuaire_rate),
            annuaire_rate,
            8.0,
            cible_display="≥ 8%",
        ),
        _kpi_row(
            "Requêtes aboutissant à la page",
            _fmt_int(total_views),
            total_views,
            200,
        ),
    ]

    section_b = [
        _kpi_row("Devis WhatsApp générés", _fmt_int(devis_total), devis_total, 50),
        _kpi_row(
            "Réservations confirmées",
            _fmt_int(rdv_confirmed),
            rdv_confirmed,
            20,
        ),
        _kpi_row(
            "Taux conversion devis → RDV",
            _fmt_pct(devis_to_rdv_pct),
            devis_to_rdv_pct,
            30.0,
            cible_display="≥ 30%",
        ),
        _kpi_row(
            "Taux de no-show",
            _fmt_pct(no_show_rate),
            no_show_rate,
            20.0,
            higher_is_better=False,
            cible_display="≤ 20%",
        ),
    ]

    roi_display = f"× {roi_ratio:.1f}".replace(".", ",")
    section_c = [
        _kpi_row(
            "Valeur estimée actes réservés",
            f"{_fmt_int(valeur)} F",
            valeur,
            500_000,
            cible_display="≥ 500 000 F",
        ),
        _kpi_row(
            "Ratio valeur / coût Plan Pro",
            roi_display,
            roi_ratio,
            2.0,
            cible_display="≥ × 2",
        ),
        _kpi_row(
            "Nouveaux patients acquis",
            _fmt_int(new_patients),
            new_patients,
            15,
        ),
    ]

    pioneer = _pioneer_m6_context(org)
    essentiel = SubscriptionPlan.objects.filter(slug="essentiel", is_public=True).first()
    pro = pro_plan or SubscriptionPlan.objects.filter(slug="pro", is_public=True).first()

    recommended_slug = "pro" if roi_ratio >= 2 else "essentiel"

    return {
        "reference": medplaque_reference(org),
        "section_a": section_a,
        "section_b": section_b,
        "section_c": section_c,
        "pioneer": pioneer,
        "essentiel_plan": essentiel,
        "pro_plan": pro,
        "recommended_slug": recommended_slug,
        "roi_ratio": roi_ratio,
    }
