from django.shortcuts import render
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
    return render(request, "index.html", _home_vitrine_context())


def home_medcare_sn(request):
    """Reproduction structurelle de medcare.sn (charte app) — URL dédiée /medcare-sn/."""
    return render(request, "index.html", _home_vitrine_context())


def home_v2(request):
    services = ServiceMedical.objects.filter(is_active=True).order_by("order")[:8]
    stats = {
        "providers": OrganismeDeSante.objects.filter(is_active=True).count(),
        "services": ServiceMedical.objects.filter(is_active=True).count(),
    }
    return render(request, "home_v2.html", {
        "services": services,
        "stats": stats,
    })


def about(request):
    return render(request, "about.html")


def how_it_works(request):
    return render(request, "how_it_works.html")


def contact(request):
    return render(request, "contact.html")


def trust(request):
    return render(request, "trust.html")


def page_not_found(request, exception):
    return render(request, "404.html", {"path": request.path}, status=404)
