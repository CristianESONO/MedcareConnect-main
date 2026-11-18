from pathlib import Path

from django.http import FileResponse, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from healthcare.models import ServiceMedical, OrganismeDeSante, Assurance


PILLAR_ACT_SAMPLES = {
    "biologie": "NFS, Glycémie, Bilan rénal, Sérologies, Examens de labo complets",
    "imagerie": "Radiographie, Échographie, Scanner, IRM, Mammographie",
    "exploration": "ECG, Fibroscopie, ENMG, EEG, Épreuves d'effort",
    "ambulance": "Ambulances médicalisées, VSL, Couverture médicale d'événements",
    "dentaire": "Détartrage, Prothèse, Orthodontie, Implantologie, Blanchiment",
    "specialise": "Dialyse, Kinésithérapie, Psychiatrie, Soins infirmiers",
}

EXCLUDED_PILLAR_LABELS = (
    "hematologie",
    "hemostase",
    "hématologie",
    "hémostase",
    "hematologie clinique",
    "hématologie clinique",
)


def is_excluded_pillar_service(service):
    combined = " ".join(
        part for part in (
            getattr(service, "name", "") or "",
            getattr(service, "slug", "") or "",
        ) if part
    ).lower()
    return any(label in combined for label in EXCLUDED_PILLAR_LABELS)


def _pillar_sample_key(service):
    slug = (service.slug or "").lower()
    if slug.startswith("biologie"):
        return "biologie"
    if slug.startswith("imagerie"):
        return "imagerie"
    if slug.startswith("exploration"):
        return "exploration"
    if slug.startswith("ambulance"):
        return "ambulance"
    if slug.startswith("soins-dent"):
        return "dentaire"
    if slug.startswith("soins-spec"):
        return "specialise"
    return ""


def _home_vitrine_context():
    """Contexte partagé landing (/) et reproduction medcare.sn (/medcare-sn/)."""
    from django.db.models import Count, Min, Q
    from healthcare.models import ActeMedical, PrestataireActe

    pa_active = Q(
        prestataire_actes__is_available=True,
        prestataire_actes__organisme__is_active=True,
    )

    services_qs = (
        ServiceMedical.objects.filter(is_active=True)
        .annotate(act_count=Count("acts", filter=Q(acts__level=3, acts__is_active=True)))
        .order_by("order")[:12]  # On prend plus pour compenser les exclusions
    )
    pillars = []
    for service in services_qs:
        if is_excluded_pillar_service(service):
            continue
        key = _pillar_sample_key(service)
        pillars.append({
            "service": service,
            "act_count": service.act_count,
            "sample_acts": PILLAR_ACT_SAMPLES.get(key, ""),
            "sample_key": key,
        })
        if len(pillars) >= 6:  # Limiter à 6 piliers
            break
    trending_qs = (
        ActeMedical.objects.filter(level=3, is_active=True)
        .select_related("service_medical_category", "parent_service")
        .annotate(
            struct_count=Count(
                "prestataire_actes__organisme",
                filter=pa_active,
                distinct=True,
            ),
            min_price=Min("prestataire_actes__price", filter=pa_active),
            verified_struct_count=Count(
                "prestataire_actes__organisme",
                filter=pa_active & Q(prestataire_actes__organisme__is_verified=True),
                distinct=True,
            ),
        )
        .filter(struct_count__gt=0)
        .order_by("-struct_count", "-verified_struct_count", "name")[:6]
    )
    trending_actes = []
    for acte in trending_qs:
        first_pa = (
            PrestataireActe.objects.filter(
                acte=acte,
                is_available=True,
                organisme__is_active=True,
            )
            .select_related("organisme")
            .order_by("-organisme__is_verified", "-organisme__profile_views_count")
            .first()
        )
        location = ""
        if first_pa:
            org = first_pa.organisme
            parts = [p for p in (org.quartier, org.city) if p]
            location = ", ".join(parts)
        trending_actes.append({
            "acte": acte,
            "struct_count": acte.struct_count,
            "min_price": acte.min_price,
            "is_verified": acte.verified_struct_count > 0,
            "category": acte.service_medical_category.name,
            "subfamily": acte.parent_service.name if acte.parent_service else "",
            "location": location,
        })
    assurances = Assurance.objects.filter(is_active=True)[:8]
    stats = {
        "providers": OrganismeDeSante.objects.filter(is_active=True).count(),
        "services": ServiceMedical.objects.filter(is_active=True).count(),
        "assurances": Assurance.objects.filter(is_active=True).count(),
        "acts": ActeMedical.objects.count(),
    }
    return {
        "pillars": pillars,
        "trending_actes": trending_actes,
        "assurances_list": assurances,
        "stats": stats,
    }


def home(request):
    """Page d'accueil originale (avant l'offre Partenariat Pionnier)."""
    return react_app(request)


def react_app(request, status=200):
    """Serve the compiled React application for the migrated public pages."""
    app_index = Path(__file__).resolve().parent.parent / "static" / "react" / "index.html"
    if not app_index.is_file():
        return HttpResponse(
            "Le frontend React n'est pas compilé. Lancez `npm run build` dans frontend/.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    return FileResponse(
        app_index.open("rb"),
        content_type="text/html; charset=utf-8",
        status=status,
    )


@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
def home_vitrine_data(request):
    context = _home_vitrine_context()
    return JsonResponse({
        "stats": context["stats"],
        "pillars": [
            {
                "id": pillar["service"].pk,
                "name": pillar["service"].name,
                "slug": pillar["service"].slug,
                "act_count": pillar["act_count"],
                "sample_acts": pillar["sample_acts"],
            }
            for pillar in context["pillars"]
        ],
        "trending_actes": [
            {
                "id": row["acte"].pk,
                "name": row["acte"].name,
                "struct_count": row["struct_count"],
                "min_price": row["min_price"],
                "category": row["category"],
                "subfamily": row["subfamily"],
                "location": row["location"],
            }
            for row in context["trending_actes"]
        ],
    })


@require_GET
def dashboard_stats_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Connectez-vous pour consulter le tableau de bord."}, status=401)
    if not request.user.is_prestataire:
        return JsonResponse({"error": "Accès réservé aux prestataires."}, status=403)

    try:
        org = request.user.healthcare_provider_profile
    except OrganismeDeSante.DoesNotExist:
        return JsonResponse(
            {"error": "Aucun profil de structure n’est associé à ce compte."},
            status=409,
        )

    from healthcare.services.dashboard_service import DashboardService
    from healthcare.views import _dashboard_period

    period_key, period_label, since = _dashboard_period(request, org)
    context = DashboardService.build_context(
        org,
        period_key=period_key,
        period_label=period_label,
        since=since,
        visit_source_filter=(request.GET.get("visit_src") or "all").strip(),
    )
    chart = context["activity_chart"]
    labels = chart["labels"][:-1][:8]
    values = chart["series"]["devis"][:-1][:8]
    return JsonResponse({
        "org_name": org.name,
        "is_praticien": org.is_praticien,
        "is_active": org.is_active,
        "is_verified": org.is_verified,
        "org_city": org.city or "",
        "org_quartier": org.quartier or "",
        "org_description": org.description or "",
        "org_logo": org.logo.url if org.logo else None,
        "profile_url": org.get_public_url(),
        "edit_profile_url": reverse("healthcare:organisme_edit"),
        "period_key": period_key,
        "period_label": period_label,
        "views_period": context["views_period"],
        "profile_views_total": context["profile_views_total"],
        "devis_period": context["devis_period"],
        "devis_value": int(context["devis_value"]),
        "items_period": context["items_period"],
        "actes_count": context["actes_count"],
        "insurances_count": context["insurances_count"],
        "completion_pct": context["completion_pct"],
        "completion_done": context["completion_done"],
        "completion_total": context["completion_total"],
        "completion": [
            {"label": item["label"], "complete": item["ok"]}
            for item in context["completion"]
        ],
        "activity_chart": {
            "labels": chart["labels"],
            "series": chart["series"],
            "meta": chart["meta"],
            "period_sub": chart["period_sub"],
        },
        "activity": [
            {"label": label, "value": value or 0}
            for label, value in zip(labels, values)
        ],
        "top_actes": [
            {
                "name": item["prestataire_acte__acte__name"],
                "price": float(item["prestataire_acte__price"] or 0),
                "count": item["n"],
            }
            for item in context["top_actes_rows"]
        ],
        "insurance_split": context["insurance_split"],
        "insurance_split_total": context["insurance_split_total"],
        "recent_views": context["recent_views"],
        "medplaque": {
            "reference": context["medplaque"]["reference"],
            "nfc_scans": context["medplaque"]["nfc_scans"],
            "qr_scans": context["medplaque"]["qr_scans"],
            "total_access": context["medplaque"]["total_access"],
            "nfc_active": context["medplaque"]["nfc_active"],
            "month_label": context["medplaque"]["month_label"],
        },
        "accepted_insurances": [
            item.assurance.name for item in context["accepted_insurances_preview"]
        ],
        "visit_source_filter": context["visit_source_filter"],
        "rdv_requested_count": context["rdv_requested_count"],
        "rdv_upcoming_count": context["rdv_upcoming_count"],
        "pending_devis": context["pending_devis"],
        "unread_messages": context["unread_messages"],
    })


def landing(request):
    """Vitrine landing page 'Rejoindre MedCare'."""
    return react_app(request)


def home_medcare_sn(request):
    """Vitrine historique servie par l'application React."""
    return react_app(request)


def home_v2(request):
    return react_app(request)


def about(request):
    return react_app(request)


def how_it_works(request):
    return react_app(request)


def contact(request):
    return react_app(request)


def trust(request):
    return react_app(request)


def page_not_found(request, exception):
    return react_app(request, status=404)
