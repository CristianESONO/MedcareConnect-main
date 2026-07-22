"""Header / footer medcare.sn — données partagées pour les visiteurs non connectés."""

from healthcare.models import ServiceMedical

VITRINE_URL_NAMES = frozenset({
    "home",
    "landing",
    "about",
    "how_it_works",
    "contact",
    "trust",
    "page_not_found",
})


def is_vitrine_request(request):
    rm = getattr(request, "resolver_match", None)
    if not rm or rm.namespace:
        return False
    return rm.url_name in VITRINE_URL_NAMES


def is_patient_search_request(request):
    rm = getattr(request, "resolver_match", None)
    return bool(
        rm
        and rm.namespace == "healthcare"
        and rm.url_name == "search"
    )


def is_prestataire_search_request(request):
    rm = getattr(request, "resolver_match", None)
    return bool(
        request.user.is_authenticated
        and getattr(request.user, "is_prestataire", False)
        and rm
        and rm.namespace == "healthcare"
        and rm.url_name == "search"
    )


def use_visitor_chrome(request):
    """Chrome medcare.sn (header drawer + footer vitrine)."""
    if not request.user.is_authenticated:
        return True
    if getattr(request.user, "is_patient", False):
        return True
    if is_prestataire_search_request(request):
        return True
    return is_vitrine_request(request)


def get_footer_pillars():
    """Services actifs pour la colonne Services du footer visiteur."""
    return list(
        ServiceMedical.objects.filter(is_active=True).order_by("order")[:8]
    )
