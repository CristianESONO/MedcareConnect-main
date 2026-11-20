import json
import logging
import unicodedata
from datetime import datetime
from urllib.parse import quote, urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from decimal import Decimal, InvalidOperation

from django.db.models import Q, Min, Max, Count, F, Sum, Case, When, IntegerField, Value, Prefetch
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse

from users.patient_panel import panel_redirect

from notifications.dispatcher import render_notification_template_string
from notifications.models import NotificationSettings

from .models import (
    OrganismeDeSante,
    ServiceMedical,
    ActeMedical,
    PrestataireActe,
    Assurance,
    PriseEnChargeAssurance,
    ProfileView,
    PlatformReview,
    Favoris,
    SearchHistory,
    TypeOrganisme,
    Region,
    LotExamenPrefait,
    SubscriptionPlan,
    SubscriptionPlanFeature,
    SubscriptionChangeRequest,
    get_default_subscription_plan,
)
from .utils import assurances_grouped_for_select
from collections import OrderedDict, defaultdict
from itertools import groupby

logger = logging.getLogger(__name__)

from healthcare.services import (
    PricingService,
    SearchService,
    DashboardService,
    InsuranceManageService,
)

from .forms import (
    OrganismeForm,
    OpeningHoursForm,
    PrestataireActeForm,
    PlatformReviewForm,
    SubscriptionChangeRequestForm,
)
from .geo import haversine_km, parse_lat_lng, parse_radius_km
from .search_views import (
    ACTES_ORDER,
    RECOMMENDED_BILAN_ACTS,
    search,
    _SEARCH_SORT_CHOICES,
    _acte_ids_from_lot_params,
    _actes_order_for_service_name,
    _annotate_delai_sort,
    _attach_distance_km_to_offers,
    _build_acte_nav_indexes,
    _build_mobile_piliers_payload,
    _is_all_zones_ambulance,
    _normalize_catalog_label,
    _normalize_recommended_act_name,
    _parse_decimal_param,
    _parse_int_list,
    _recommended_bilan_acte_ids,
    _resolve_acte_for_nav,
    _search_org_card_icon,
    _search_querydict_for_links,
    _search_url_mutate,
    _search_url_with_acte_pool,
    _search_url_with_query,
)

SESSION_PARCOURS_ACTES = "parcours_acte_ids"

def _leaf_actes_grouped_by_service():
    """Actes feuilles (niveau 3) actifs, regroupés par catégorie ServiceMedical (pôles / familles)."""
    services = ServiceMedical.objects.filter(is_active=True).order_by("order", "name")
    groups = []
    for svc in services:
        actes = list(
            ActeMedical.objects.filter(
                service_medical_category=svc,
                level=3,
                is_active=True,
            ).order_by("name")
        )
        if actes:
            groups.append((svc, actes))
    return groups


def _prestataire_leaf_actes_queryset():
    """Actes feuilles sélectionnables (délègue au module catalogue)."""
    from healthcare.prestataire_catalogue import prestataire_leaf_actes_queryset

    return prestataire_leaf_actes_queryset()


def _prestataire_leaf_actes_catalog_by_pilier():
    from healthcare.prestataire_catalogue import prestataire_leaf_actes_catalog_by_pilier

    return prestataire_leaf_actes_catalog_by_pilier()

def _prestataire_leaf_actes_grouped_by_service():
    """Regroupe les actes prestataire sélectionnables par pilier (`ServiceMedical`)."""
    by_svc = {}
    for acte in _prestataire_leaf_actes_queryset():
        svc = acte.service_medical_category
        if svc is None or not svc.is_active:
            continue
        by_svc.setdefault(svc, []).append(acte)
    return [
        (svc, by_svc[svc])
        for svc in sorted(by_svc.keys(), key=lambda s: (s.order, s.name))
    ]


def _catalog_price_from_post(post, acte_id: int, fallback: Decimal) -> Decimal:
    """Prix saisi dans le formulaire catalogue (champ `price_<acte_id>`)."""
    raw = post.get(f"price_{acte_id}")
    if raw is None:
        return fallback
    s = str(raw).strip().replace(" ", "").replace(",", ".")
    if not s:
        return Decimal("0")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return fallback


def _catalog_delai_from_post(post, acte_id: int, fallback: str) -> str:
    """Délai indicatif (`delai_<acte_id>`) — valeur autorisée ou repli."""
    raw = post.get(f"delai_{acte_id}")
    if raw is None:
        return fallback
    v = str(raw).strip()
    allowed = {k for k, _ in PrestataireActe.DELAI_CHOICES}
    return v if v in allowed else fallback


@require_GET
def api_actes_budget(request):
    """
    Actes ayant au moins une offre ≤ max (FCFA), pour le mode Budget type démo.
    Respecte famille (service) et assurances si passés en query (cohérent avec la recherche).
    """
    max_p = _parse_decimal_param((request.GET.get("max") or "").strip())
    if max_p is None:
        return JsonResponse({"actes": []})
    service_id = request.GET.get("service")
    assurance_raw = [v for v in request.GET.getlist("assurance") if v]
    qs = PrestataireActe.objects.filter(
        is_available=True,
        organisme__is_active=True,
        price__gt=0,
        price__lte=max_p,
    )
    if service_id:
        qs = qs.filter(acte__service_medical_category_id=service_id)
    if assurance_raw:
        qs = qs.filter(
            organisme__prises_en_charge__assurance_id__in=assurance_raw,
            organisme__prises_en_charge__is_active=True,
        ).distinct()
    rows = (
        qs.values("acte_id")
        .annotate(min_price=Min("price"), n_struct=Count("organisme_id", distinct=True))
        .order_by("min_price")[:28]
    )
    acte_ids = [r["acte_id"] for r in rows]
    names = dict(ActeMedical.objects.filter(pk__in=acte_ids).values_list("pk", "name"))
    actes = []
    for r in rows:
        aid = r["acte_id"]
        actes.append({
            "id": aid,
            "name": names.get(aid, ""),
            "min_price": float(r["min_price"]),
            "n_struct": r["n_struct"],
        })
    return JsonResponse({"actes": actes})


def _session_parcours_acte_ids(request):
    raw = request.session.get(SESSION_PARCOURS_ACTES) or []
    if not isinstance(raw, list):
        return []
    return _parse_int_list(raw)


def _presta_acte_form_ui(qs, post_data=None, selected_acte_pk=None):
    """
    Données pour le sélecteur d'actes : un <optgroup> par couple (pilier, type niveau 2),
    libellé « Pilier — Type » ; chaque <option> n’affiche que le **nom de l’acte feuille** (niveau 3),
    pour ne pas suggérer que le type (ex. « Immunologie & Auto-immunité ») est une ligne sélectionnable.
    """
    ordered = qs.order_by(
        "service_medical_category__order",
        "service_medical_category__name",
        "parent_service_id",
        "name",
    )
    groups = []
    for cat, actes_iter in groupby(ordered, key=lambda a: a.service_medical_category):
        chunk = list(actes_iter)
        chunk.sort(key=lambda a: (a.parent_service_id or 0, a.name))
        for _parent_id, leaves_iter in groupby(chunk, key=lambda a: a.parent_service_id):
            leaves = list(leaves_iter)
            if not leaves:
                continue
            parent_obj = leaves[0].parent_service
            optgroup_label = (
                f"{cat.name} — {parent_obj.name}" if parent_obj else cat.name
            )
            opts = [(a.pk, a.name) for a in leaves]
            groups.append(
                {"service_name": optgroup_label, "service_id": cat.pk, "options": opts}
            )
    services = ServiceMedical.objects.filter(is_active=True).order_by("order", "name")
    initial_svc = ""
    if post_data and post_data.get("presta_service_filter"):
        initial_svc = str(post_data.get("presta_service_filter")).strip()
    elif selected_acte_pk:
        try:
            a = ActeMedical.objects.only("service_medical_category_id").get(pk=int(selected_acte_pk))
            initial_svc = str(a.service_medical_category_id)
        except (ActeMedical.DoesNotExist, TypeError, ValueError):
            pass
    sel_id = None
    if selected_acte_pk is not None:
        try:
            sel_id = int(selected_acte_pk)
        except (TypeError, ValueError):
            sel_id = None
    return {
        "acte_option_groups": groups,
        "medical_services": services,
        "presta_service_filter": initial_svc,
        "selected_acte_id": sel_id,
    }


def _require_prestataire(view_func):
    from functools import wraps
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_prestataire:
            messages.error(request, "Accès réservé aux prestataires.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped


def _whatsapp_me_url(digits: str, message: str) -> str:
    """Lien wa.me avec texte prérempli (UTF-8)."""
    if not digits:
        return ""
    return "https://wa.me/" + digits + "?text=" + quote(message)


def centres_list(request):
    """Redirige vers l'annuaire (URL historique /centres/)."""
    from django.shortcuts import redirect

    q = request.GET.urlencode()
    url = reverse("healthcare:annuaire")
    if q:
        url = f"{url}?{q}"
    return redirect(url)


def annuaire(request):
    from .annuaire import build_annuaire_context

    return render(request, "healthcare/annuaire.html", build_annuaire_context(request))


@require_GET
def api_search_autocomplete(request):
    """Suggestions pour la barre de recherche : actes, familles de soins, centres."""
    import unicodedata
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"suggestions": []})

    def strip_accents(s: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

    q_clean = strip_accents(q)

    suggestions = []

    services = [
        s for s in ServiceMedical.objects.filter(is_active=True).order_by("order")
        if q_clean in strip_accents(s.name)
    ][:4]
    for s in services:
        suggestions.append({
            "label": s.name,
            "type": "famille",
            "url": f"?service={s.pk}&sort=price_asc",
        })

    # Dictionnaire d'intentions / équivalences d'actes pour orienter directement vers l'acte canonique
    INTENTIONS_CANONIQUES = {
        "vs": "VS",
        "vitesse de sed": "VS",
        "cholest": "Cholestérol total",
        "glycem": "Glycémie à jeun",
        "nfs": "NFS / Hémogramme",
        "hemogram": "NFS / Hémogramme",
        "creatin": "Créatininémie",
        "uree": "Urée sanguine",
        "trigly": "Triglycérides",
        "ecg": "Électrocardiogramme (ECG)",
        "electrocardio": "Électrocardiogramme (ECG)",
        "acide uri": "Acide urique (uricémie)",
        "uricem": "Acide urique (uricémie)",
        "transam": "ALAT",
    }
    
    canonical_target = None
    for pattern, target_name in INTENTIONS_CANONIQUES.items():
        if pattern in q_clean:
            canonical_target = target_name
            break

    all_actes = list(ActeMedical.objects.filter(is_active=True).select_related("service_medical_category"))
    matched_actes = [
        a for a in all_actes
        if q_clean in strip_accents(a.name) or (a.code and q_clean in strip_accents(a.code))
    ]

    if canonical_target:
        # Si une intention canonique est détectée (ex: "VS", "cholestérol"), afficher l'acte canonique en priorité
        matched_actes.sort(
            key=lambda a: (
                0 if strip_accents(a.name) == strip_accents(canonical_target) else 1,
                -a.prestataire_actes.count(),
                a.name.lower(),
            )
        )
    else:
        matched_actes.sort(key=lambda a: (-a.prestataire_actes.count(), a.name.lower()))

    # Déduplication visuelle : ne pas renvoyer plusieurs variantes de la même intention canonique
    seen_canon_names = set()
    deduped_actes = []
    from .management.commands.fusionner_actes_doublons import _canonical_key_for_acte

    for a in matched_actes:
        c_key = _canonical_key_for_acte(a.name)
        if c_key in seen_canon_names:
            continue
        seen_canon_names.add(c_key)
        deduped_actes.append(a)

    for a in deduped_actes[:8]:
        suggestions.append({
            "id": a.pk,
            "label": a.name,
            "type": "acte",
            "detail": a.service_medical_category.name if a.service_medical_category else "",
            "url": f"?acte={a.pk}&sort=price_asc",
        })

    centres = [
        c for c in OrganismeDeSante.objects.filter(is_active=True).select_related("type_organisme").order_by("name")
        if q_clean in strip_accents(c.name)
    ][:4]
    for c in centres:
        type_label = c.type_organisme.name if c.type_organisme else ""
        suggestions.append({
            "label": c.name,
            "type": "centre",
            "detail": f"{type_label} — {c.city}" if type_label else c.city,
            "url": f"?q={c.name}&sort=price_asc",
        })

    return JsonResponse({"suggestions": suggestions})


@require_GET
def api_organisme_preview(request, slug):
    """
    Aperçu léger d'une structure pour le panneau latéral sur la recherche.
    Ne comptabilise pas de vue de profil (évite de gonfler les stats au survol / ouvertures multiples).
    """
    org = get_object_or_404(
        OrganismeDeSante.objects.select_related("type_organisme", "region"),
        slug=slug,
        is_active=True,
    )
    insurances = list(
        PriseEnChargeAssurance.objects.filter(organisme=org, is_active=True)
        .select_related("assurance")
        .order_by("assurance__name")
        .values_list("assurance__name", flat=True)[:40]
    )
    logo_url = ""
    if org.logo:
        logo_url = request.build_absolute_uri(org.logo.url)
    fiche_path = reverse("healthcare:organisme_detail", args=[org.slug])
    return JsonResponse(
        {
            "name": org.name,
            "slug": org.slug,
            "city": org.city or "",
            "quartier": org.quartier or "",
            "type_label": org.type_organisme.name if org.type_organisme else "",
            "verified": org.is_verified,
            "prises_sang_domicile": org.prises_sang_domicile,
            "insurances": insurances,
            "avg_rating": None,
            "review_count": 0,
            "logo_url": logo_url,
            "fiche_url": request.build_absolute_uri(fiche_path),
            "actes_count": PrestataireActe.objects.filter(
                organisme=org,
                is_available=True,
            ).count(),
        }
    )


@login_required
def platform_review(request):
    """Formulaire d'avis centralisé MedCare (actes par famille + tarifs & délais)."""
    if not request.user.is_patient:
        messages.error(request, "Seuls les patients peuvent déposer un avis sur MedCare.")
        return redirect("healthcare:search")

    existing = PlatformReview.objects.filter(patient=request.user).first()
    groups = _leaf_actes_grouped_by_service()

    selected_acte_ids = set()
    if request.method == "POST":
        for x in request.POST.getlist("actes"):
            try:
                selected_acte_ids.add(int(x))
            except (TypeError, ValueError):
                pass

        if existing:
            messages.warning(
                request,
                "Vous avez déjà déposé un avis sur MedCare. Une seule contribution par compte.",
            )
            return redirect("healthcare:platform_review")
        form = PlatformReviewForm(request.POST)
        if form.is_valid():
            review = PlatformReview.objects.create(
                patient=request.user,
                rating=form.cleaned_data["rating"],
                tarifs_delais_comment=(form.cleaned_data.get("tarifs_delais_comment") or "").strip(),
            )
            review.actes.set(form.cleaned_data["actes"])
            try:
                from notifications.dispatcher import dispatch as _notify

                _notify(
                    "review.posted",
                    context={
                        "review": review,
                        "organisme": None,
                        "patient": request.user,
                        "link": f"/admin/healthcare/platformreview/{review.id}/change/",
                    },
                    actor=None,
                )
            except Exception:
                pass
            messages.success(
                request,
                "Merci pour votre avis ! Il sera publié après modération. "
                "Vous pouvez aussi nous laisser un avis sur Google.",
            )
            return redirect("healthcare:platform_review_google")
    else:
        form = PlatformReviewForm()

    ctx = {
        "form": form,
        "service_acte_groups": groups,
        "existing_platform_review": existing,
        "google_url": NotificationSettings.load().resolved_google_reviews_url,
        "selected_acte_ids": selected_acte_ids,
    }
    return render(request, "healthcare/platform_review.html", ctx)


def platform_review_google(request):
    """Page dédiée lien vers Google Avis (URL : réglages notifications admin, sinon .env)."""
    ns = NotificationSettings.load()
    url = ns.resolved_google_reviews_url
    return render(
        request,
        "healthcare/platform_review_google.html",
        {"google_reviews_url": url},
    )


def _opening_hours_list(org):
    """Liste des jours + plages pour affichage fiche / aperçu (même logique que `organisme_detail`)."""
    hours_list = []
    _jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    _today_fr = _jours[datetime.now().weekday()]

    raw = org.opening_hours
    if isinstance(raw, str):
        raw = None

    default_hours = {
        "Lundi": {"open": "07:00", "close": "19:00", "closed": False},
        "Mardi": {"open": "07:00", "close": "19:00", "closed": False},
        "Mercredi": {"open": "07:00", "close": "19:00", "closed": False},
        "Jeudi": {"open": "07:00", "close": "19:00", "closed": False},
        "Vendredi": {"open": "07:00", "close": "19:00", "closed": False},
        "Samedi": {"open": "07:00", "close": "19:00", "closed": False},
        "Dimanche": {"open": "08:00", "close": "13:00", "closed": False},
    }

    source = raw if (raw and isinstance(raw, dict) and any(bool(v) for v in raw.values())) else default_hours

    for day in _jours:
        info = source.get(day, {})
        if not isinstance(info, dict):
            info = {}
        is_closed = info.get("closed", False) or (not info.get("open") and not info.get("close"))
        open_val = (info.get("open") or "").replace(":", "h") if info.get("open") else ""
        close_val = (info.get("close") or "").replace(":", "h") if info.get("close") else ""

        display_h = "Fermé"
        if not is_closed and (open_val or close_val):
            display_h = f"{open_val} – {close_val}" if (open_val and close_val) else (open_val or close_val)

        hours_list.append({
            "day": day,
            "day_label": day,
            "days": day,
            "hours": display_h,
            "is_today": day == _today_fr,
            "open": info.get("open", ""),
            "close": info.get("close", ""),
            "open_time": open_val or info.get("open", ""),
            "close_time": close_val or info.get("close", ""),
            "closed": is_closed,
            "display_hours": display_h,
        })
    return hours_list


def organisme_detail(request, slug):
    from .organisme_fiche import build_insurances_profil, fiche_context_for_org

    org = get_object_or_404(
        OrganismeDeSante.objects.select_related(
            "type_organisme", "user", "region", "subscription_plan",
        ).prefetch_related("prelevement_zones"),
        slug=slug, is_active=True,
    )

    # Praticien indépendant : rediriger vers sa fiche dédiée /sante/praticien/<slug>/
    # (évite le Http404 brut qui peut déclencher un 500 si le handler 404 plante en prod)
    if org.is_praticien:
        return redirect("healthcare:praticien_public_detail", slug=org.slug)

    org.profile_views_count = F("profile_views_count") + 1
    org.save(update_fields=["profile_views_count"])
    from .profile_tracking import resolve_profile_view_source

    view_source = resolve_profile_view_source(request)
    if request.user.is_authenticated:
        ProfileView.objects.create(
            organisme=org,
            viewer=request.user,
            source=view_source,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
    else:
        ProfileView.objects.create(
            organisme=org,
            source=view_source,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    actes = list(
        PrestataireActe.objects.filter(
            organisme=org, is_available=True,
        ).select_related(
            "acte__service_medical_category", "acte__parent_service",
        ).order_by(
            "acte__service_medical_category__order", "acte__level", "acte__name",
        )
    )

    wa_digits = (org.whatsapp_digits or "").strip()
    ns = NotificationSettings.load()
    wa_msg_general = render_notification_template_string(
        ns.patient_wa_me_message_general,
        {"org": org},
    )
    wa_general_url = _whatsapp_me_url(wa_digits, wa_msg_general) if wa_digits else ""
    for pa in actes:
        wa_acte_body = render_notification_template_string(
            ns.patient_wa_me_message_acte,
            {"org": org, "acte": pa.acte},
        )
        pa.whatsapp_url = _whatsapp_me_url(wa_digits, wa_acte_body) if wa_digits else ""

    insurances = PriseEnChargeAssurance.objects.filter(
        organisme=org, is_active=True,
    ).select_related("assurance").order_by("assurance__segment", "assurance__name")

    hours_list = _opening_hours_list(org)
    fiche_ctx = fiche_context_for_org(org, actes, hours_list, request)

    from .organisme_fiche import resolve_patient_insurance_match
    patient_insurance_match, patient_match_set = resolve_patient_insurance_match(request, insurances)
    insurances_profil = build_insurances_profil(insurances, matched_set=patient_match_set)

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favoris.objects.filter(patient=request.user, organisme=org).exists()

    org.refresh_from_db()

    context = {
        "org": org,
        "wa_general_url": wa_general_url,
        "insurances": insurances,
        "insurances_profil": insurances_profil,
        "patient_insurance_match": patient_insurance_match,
        "is_favorite": is_favorite,
        "hours_list": hours_list,
        **fiche_ctx,
    }
    return render(request, "healthcare/organisme_detail.html", context)


def organisme_profil_drawer(request, org_id):
    """Vue AJAX pour charger le contenu du drawer de profil structure"""
    from .models import Assurance

    org = get_object_or_404(OrganismeDeSante, id=org_id, is_active=True)

    actes = list(
        PrestataireActe.objects.filter(
            organisme=org, is_available=True,
        ).select_related(
            "acte__service_medical_category", "acte__parent_service",
        ).order_by(
            "acte__service_medical_category__order", "acte__level", "acte__name",
        )
    )

    insurances = PriseEnChargeAssurance.objects.filter(
        organisme=org, is_active=True,
    ).select_related("assurance").order_by("assurance__segment", "assurance__name")

    hours_list = _opening_hours_list(org)

    from .organisme_fiche import build_insurances_profil, fiche_context_for_org, resolve_patient_insurance_match
    fiche_ctx = fiche_context_for_org(org, actes, hours_list, request)

    patient_insurance_match, patient_match_set = resolve_patient_insurance_match(request, insurances)
    insurances_profil = build_insurances_profil(insurances, matched_set=patient_match_set)

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favoris.objects.filter(patient=request.user, organisme=org).exists()

    context = {
        "org": org,
        "actes": actes,
        "insurances": insurances,
        "insurances_profil": insurances_profil,
        "patient_insurance_match": patient_insurance_match,
        "is_favorite": is_favorite,
        "hours_list": hours_list,
        **fiche_ctx,
    }

    return render(request, "healthcare/partials/organisme_profil_drawer.html", context)


def service_detail(request, slug):
    service = get_object_or_404(ServiceMedical, slug=slug, is_active=True)

    from healthcare.prestataire_catalogue import (
        service_actes_catalog_rows,
        service_actes_catalog_subgroups,
    )

    acte_subgroups = service_actes_catalog_subgroups(service)
    acte_rows = service_actes_catalog_rows(service)
    category_options = [sg["label"] for sg in acte_subgroups]

    providers = OrganismeDeSante.objects.filter(
        prestataire_actes__acte__service_medical_category=service,
        is_active=True,
    ).distinct().select_related("type_organisme")[:20]

    context = {
        "service": service,
        "acte_rows": acte_rows,
        "category_options": category_options,
        "providers": providers,
    }
    return render(request, "healthcare/service_detail.html", context)


@login_required
def toggle_favorite(request, slug):
    org = get_object_or_404(OrganismeDeSante, slug=slug, is_active=True)
    fav, created = Favoris.objects.get_or_create(patient=request.user, organisme=org)
    if not created:
        fav.delete()
        messages.info(request, f"« {org.name} » retiré de vos favoris.")
    else:
        messages.success(request, f"« {org.name} » ajouté à vos favoris.")
    return redirect("healthcare:organisme_detail", slug=slug)


@login_required
def my_favorites(request):
    favs = Favoris.objects.filter(patient=request.user).select_related(
        "organisme__type_organisme"
    ).order_by("-created_at")
    ctx = {"favorites": favs}
    if request.user.is_patient:
        return redirect(panel_redirect("assurance"))
    return render(request, "healthcare/my_favorites.html", ctx)


@login_required
def my_search_history(request):
    history = SearchHistory.objects.filter(user=request.user).order_by("-searched_at")[:50]
    ctx = {"history": history}
    if request.user.is_patient:
        from users.patient_panel import panel_redirect

        return redirect(panel_redirect("recherches"))
    return render(request, "healthcare/search_history.html", ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# PRESTATAIRE SIDE — Dashboard, Profile, Services, Insurance management
# ═══════════════════════════════════════════════════════════════════════════════

def _dash_context(request, active_tab):
    """Contexte partagé par toutes les pages du dashboard prestataire."""
    from messaging.models import Message
    from cart.models import DevisPart

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    unread = Message.objects.filter(receiver=request.user, is_read=False).count()
    new_devis_count = DevisPart.objects.filter(
        organisme=org,
        status="sent",
    ).exclude(devis__status="draft").count()
    from appointments.models import RendezVous

    new_rdv_count = RendezVous.objects.filter(
        organisme=org, status=RendezVous.STATUS_REQUESTED
    ).count()
    pending_subscription_request = SubscriptionChangeRequest.objects.filter(
        organisme=org, status="pending"
    ).first()
    return {
        "org": org,
        "dash_active": active_tab,
        "unread_messages": unread,
        "new_devis_count": new_devis_count,
        "new_rdv_count": new_rdv_count,
        "pending_subscription_request": pending_subscription_request,
    }


def _prest_onboarding_context(request):
    """Prestataire sans fiche OrganismeDeSante — sidebar allégée + création."""
    from messaging.models import Message
    return {
        "org": None,
        "dash_active": "onboarding",
        "unread_messages": Message.objects.filter(receiver=request.user, is_read=False).count(),
    }


_DASH_PERIOD_DAYS = {"7j": 7, "30j": 30, "total": None}


def _dashboard_period(request, org=None):
    """Retourne (clé courante, libellé court, datetime de bord)."""
    raw = (request.GET.get("period") or "").strip()
    if not raw and org is not None:
        raw = (getattr(org, "settings_dashboard_period", None) or "30j").strip()
    if raw not in _DASH_PERIOD_DAYS:
        raw = "30j"
    days = _DASH_PERIOD_DAYS[raw]
    if days is None:
        return raw, "depuis le début", None

    return raw, f"derniers {days} jours", timezone.now() - timezone.timedelta(days=days)


def _dashboard_completion(org, actes_count, insurances_count):
    """Liste de check-points de complétion du profil prestataire."""
    if getattr(org, "is_praticien", False):
        return [
            {"key": "name", "label": "Nom complet", "ok": bool((org.name or "").strip())},
            {"key": "profession", "label": "Profession", "ok": bool((org.profession or "").strip())},
            {"key": "order", "label": "N° Ordre / Titre", "ok": bool((org.ordre_numero or "").strip())},
            {"key": "logo", "label": "Photo de profil", "ok": bool(org.logo)},
            {"key": "description", "label": "Biographie", "ok": bool((org.description or "").strip())},
            {
                "key": "contact",
                "label": "Téléphone / WhatsApp",
                "ok": bool((org.contact_phone or "").strip() or (org.whatsapp_number or "").strip()),
            },
        ]

    raw_oh = org.opening_hours
    if isinstance(raw_oh, str):
        raw_oh = None
    # Vérifie qu'au moins un jour est configuré et non fermé
    hours_ok = bool(raw_oh) and any(
        isinstance(v, dict) and not v.get("closed", True) and (v.get("open") or v.get("close"))
        for v in (raw_oh or {}).values()
    )
    if getattr(org, "is_praticien", False):
        # Pour un praticien, les disponibilités sont valides si :
        #   1. opening_hours contient au moins un jour ouvert, OU
        #   2. il existe au moins un créneau de RDV à venir (agenda praticien)
        if not hours_ok:
            try:
                from appointments.models import RendezVous
                from django.utils import timezone
                hours_ok = RendezVous.objects.filter(
                    organisme=org,
                    start__gte=timezone.now(),
                ).exists()
            except Exception:
                pass
        return [
            {"key": "profile", "label": "Identité", "ok": bool(org.name and org.city)},
            {"key": "actes", "label": "Catalogue d'actes", "ok": actes_count > 0},
            {"key": "hours", "label": "Disponibilités", "ok": hours_ok},
            {"key": "logo", "label": "Photo de profil", "ok": bool(org.logo)},
            {"key": "description", "label": "Biographie / Présentation", "ok": bool(org.description and len(org.description) > 20)},
        ]
    return [
        {"key": "profile", "label": "Identité", "ok": bool(org.name and org.city)},
        {"key": "actes", "label": "Catalogue d'actes", "ok": actes_count > 0},
        {"key": "insurances", "label": "Assurances", "ok": insurances_count > 0},
        {"key": "hours", "label": "Horaires", "ok": hours_ok},
        {"key": "logo", "label": "Logo", "ok": bool(org.logo)},
        {"key": "description", "label": "Description", "ok": bool(org.description and len(org.description) > 20)},
    ]


@_require_prestataire
def prestataire_dashboard(request):
    try:
        org = request.user.healthcare_provider_profile
    except OrganismeDeSante.DoesNotExist:
        return redirect("healthcare:organisme_create")

    period_key, period_label, since = _dashboard_period(request, org)
    visit_source_filter = (request.GET.get("visit_src") or "all").strip()

    context = DashboardService.build_context(
        org,
        period_key=period_key,
        period_label=period_label,
        since=since,
        visit_source_filter=visit_source_filter,
    )
    return render(request, "healthcare/prestataire/dashboard.html", context)

def _prestataire_resolve_devis_part_or_legacy_parent(org, reference: str):
    """Référence DP-* = sous-devis ; sinon référence parent DEV-* (legacy sans parts)."""
    from cart.models import Devis, DevisPart

    ref = (reference or "").strip()
    if ref.upper().startswith("DP-"):
        part = get_object_or_404(DevisPart, reference=ref, organisme=org)
        return part, None
    devis = get_object_or_404(
        Devis,
        reference=ref,
        cart__items__prestataire_acte__organisme=org,
    )
    part = devis.parts.filter(organisme_id=org.pk).first()
    return part, devis


def _notify_devis_relanced(org, devis, part):
    """Signale au patient que la structure a relancé son devis (cloche in-app)."""
    from notifications.dispatcher import dispatch

    link = reverse("healthcare:search") + f"?pac=devis&devis_ref={devis.reference}"
    dispatch(
        "devis.relanced",
        context={
            "devis": devis,
            "devis_part": part,
            "patient": devis.patient,
            "organisme": org,
            "link": link,
        },
        actor=devis.patient,
    )


@_require_prestataire
@require_POST
def prestataire_devis_relance(request, reference):
    """Relance sur le sous-devis (réf. DP-…) ou sur la part liée au parent DEV-* (legacy)."""
    org = get_object_or_404(OrganismeDeSante, user=request.user)
    part, devis = _prestataire_resolve_devis_part_or_legacy_parent(org, reference)
    if part:
        if not part.can_relance():
            if part.is_archived:
                messages.warning(request, f"Sous-devis {part.reference} déjà archivé — relance impossible.")
            else:
                messages.warning(request, f"Sous-devis {part.reference} : nombre maximal de relances atteint.")
        else:
            part.mark_relance(by_user=request.user)
            _notify_devis_relanced(org, part.devis, part)
            if part.is_archived:
                messages.info(
                    request,
                    f"Sous-devis {part.reference} : 2e relance — archivage automatique.",
                )
            else:
                messages.success(
                    request,
                    f"Sous-devis {part.reference} relancé ({part.relance_count}/{part.MAX_RELANCES}).",
                )
    else:
        if not devis.can_relance():
            if devis.is_archived:
                messages.warning(request, f"Devis {devis.reference} déjà archivé — relance impossible.")
            else:
                messages.warning(request, f"Devis {devis.reference} : nombre maximal de relances atteint.")
        else:
            devis.mark_relance(by_user=request.user)
            _notify_devis_relanced(org, devis, None)
            if devis.is_archived:
                messages.info(
                    request,
                    f"Devis {devis.reference} : 2e relance envoyée — archivage automatique appliqué.",
                )
            else:
                messages.success(
                    request,
                    f"Devis {devis.reference} relancé ({devis.relance_count}/{devis.MAX_RELANCES}).",
                )
    return redirect(
        reverse("healthcare:prestataire_devis_list")
        + f"?status={(request.POST.get('status') or 'active').strip()}"
    )


@_require_prestataire
@require_POST
def prestataire_devis_archiver(request, reference):
    """Archive le sous-devis ou le parent legacy sans parts."""
    org = get_object_or_404(OrganismeDeSante, user=request.user)
    part, devis = _prestataire_resolve_devis_part_or_legacy_parent(org, reference)
    if part:
        if part.is_archived:
            messages.info(request, f"Sous-devis {part.reference} déjà archivé.")
        else:
            part.archive(reason="Archivé par la structure")
            messages.success(request, f"Sous-devis {part.reference} archivé.")
    else:
        if devis.is_archived:
            messages.info(request, f"Devis {devis.reference} déjà archivé.")
        else:
            devis.archive(reason="Archivé par la structure")
            messages.success(request, f"Devis {devis.reference} archivé.")
    return redirect(
        reverse("healthcare:prestataire_devis_list")
        + f"?status={(request.POST.get('status') or 'active').strip()}"
    )


@_require_prestataire
def prestataire_devis_part_detail(request, reference):
    """Fiche d'un sous-devis pour la structure connectée (marque « consulté » si envoyé)."""
    from cart.models import DevisPart
    from healthcare.prestataire_devis import prestataire_devis_rows

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    part = get_object_or_404(
        DevisPart.objects.select_related("devis", "devis__patient", "devis__insurance", "organisme"),
        reference=reference.strip(),
        organisme=org,
    )
    if part.status == "sent":
        part.status = "viewed"
        part.save(update_fields=["status"])
    row = prestataire_devis_rows([part])[0]
    ctx = _dash_context(request, "devis")
    ctx.update(
        {
            "part": part,
            "devis": part.devis,
            "row": row,
            "status_filter": (request.GET.get("status") or "active").strip(),
        }
    )
    return render(request, "healthcare/prestataire/devis_part_detail.html", ctx)


@_require_prestataire
def prestataire_patient_dossier(request, reference):
    """Dossier patient lisible par la structure à partir d'un sous-devis WhatsApp."""
    from appointments.models import RendezVous
    from cart.models import DevisPart
    from messaging.thread import conversation_for_part, thread_url
    from users.models import PatientProfile

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    part = get_object_or_404(
        DevisPart.objects.select_related(
            "devis",
            "devis__patient",
            "devis__insurance",
            "organisme",
        ),
        reference=reference.strip(),
        organisme=org,
    )
    patient = part.devis.patient
    profile = PatientProfile.objects.filter(user=patient).select_related("insurance").first()
    if part.status == "sent":
        part.status = "viewed"
        part.save(update_fields=["status"])

    patient_parts = (
        DevisPart.objects.filter(
            organisme=org,
            devis__patient=patient,
        )
        .select_related("devis", "devis__insurance")
        .order_by("-created_at")
    )
    rendez_vous = RendezVous.objects.filter(
        organisme=org,
        patient=patient,
    ).order_by("-start")

    conversation = conversation_for_part(part)
    ctx = _dash_context(request, "devis")
    ctx.update(
        {
            "patient": patient,
            "patient_profile": profile,
            "part": part,
            "devis": part.devis,
            "patient_parts": patient_parts,
            "rendez_vous": rendez_vous,
            "conversation_url": thread_url(conversation) if conversation else None,
            "status_filter": (request.GET.get("status") or "active").strip(),
        }
    )
    return render(request, "healthcare/prestataire/patient_dossier.html", ctx)


@_require_prestataire
def prestataire_devis_list(request):
    """
    Registre des sous-devis reçus par la structure (une ligne par part / par devis parent).
    """
    from cart.models import DevisPart
    from healthcare.prestataire_devis import (
        prestataire_devis_counts,
        prestataire_devis_filter_qs,
        prestataire_devis_kpis,
        prestataire_devis_rows,
    )

    org = get_object_or_404(OrganismeDeSante, user=request.user)

    status_filter = (request.GET.get("status") or "active").strip()
    valid_status = {
        "active",
        "all",
        "new",
        "sent",
        "viewed",
        "accepted",
        "relanced",
        "expired",
        "archived",
    }
    if status_filter not in valid_status:
        status_filter = "active"

    base_qs = (
        DevisPart.objects.filter(organisme=org)
        .exclude(devis__status="draft")
        .select_related("devis", "devis__patient", "devis__insurance", "organisme")
        .order_by("-created_at")
    )

    counts = prestataire_devis_counts(base_qs)
    kpis = prestataire_devis_kpis(base_qs)
    qs = prestataire_devis_filter_qs(base_qs, status_filter)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    rows = prestataire_devis_rows(page.object_list)

    ctx = _dash_context(request, "devis")
    ctx.update(
        {
            "rows": rows,
            "page": page,
            "status_filter": status_filter,
            "counts": counts,
            "kpis": kpis,
            "devis_list_url": reverse("healthcare:prestataire_devis_list"),
        }
    )
    return render(request, "healthcare/prestataire/devis_list.html", ctx)


@_require_prestataire
def prestataire_medplaque(request):
    """Page MedPlaque NFC — stats scans NFC/QR et entonnoir de conversion."""
    from healthcare.prestataire_analytics import medplaque_stats, recent_visits

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    ctx = _dash_context(request, "medplaque")
    stats = medplaque_stats(org)
    ctx.update(
        {
            "org": org,
            "mp": stats,
            "recent_plaque_visits": [
                v for v in recent_visits(org, limit=15)
                if v["source"] in ("nfc", "qr")
            ],
        }
    )
    return render(request, "healthcare/prestataire/medplaque.html", ctx)


@_require_prestataire
def prestataire_bilan(request):
    """Bilan KPI Pionnier : blocs visibilité, engagement, valeur + upgrade M6."""
    from healthcare.prestataire_bilan import build_pioneer_bilan

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    bilan = build_pioneer_bilan(org)

    actes_count = PrestataireActe.objects.filter(organisme=org).count()
    insurances_count = PriseEnChargeAssurance.objects.filter(organisme=org).count()
    completion = _dashboard_completion(org, actes_count, insurances_count)
    completion_pct = int(round(sum(1 for c in completion if c["ok"]) * 100.0 / max(len(completion), 1)))

    ctx = _dash_context(request, "bilan")
    ctx.update(
        {
            "bilan": bilan,
            "completion_pct": completion_pct,
            "completion": completion,
        }
    )
    return render(request, "healthcare/prestataire/bilan.html", ctx)


@_require_prestataire
def prestataire_settings(request):
    """Paramètres prestataire — layout démo (compte, notifications, abonnement)."""
    from healthcare.prestataire_settings_page import (
        handle_settings_post,
        notification_toggle_rows,
        preferences_context,
    )
    from users.forms import UserProfileForm

    ctx = _dash_context(request, "settings")
    org = OrganismeDeSante.objects.select_related("subscription_plan").get(pk=ctx["org"].pk)
    user = request.user

    if request.method == "POST":
        result = handle_settings_post(request, user, org)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(result)
        if result.get("ok"):
            messages.success(request, result.get("message") or "Paramètres sauvegardés.")
        else:
            for err in result.get("errors") or ["Enregistrement impossible."]:
                messages.error(request, err)
        return redirect("healthcare:prestataire_settings")

    user_form = UserProfileForm(instance=user)
    for name in ("first_name", "last_name", "email", "phone_number"):
        if name in user_form.fields:
            user_form.fields[name].widget.attrs["class"] = "param-input"

    ctx.update(
        {
            "org": org,
            "user_form": user_form,
            "notification_toggles": notification_toggle_rows(user),
            "subscription_recent": (
                SubscriptionChangeRequest.objects.filter(organisme=org)
                .select_related("requested_plan", "previous_plan")
                .order_by("-created_at")[:5]
            ),
            **preferences_context(org),
        }
    )
    return render(request, "healthcare/prestataire/settings.html", ctx)


@_require_prestataire
def prestataire_subscription(request):
    """Grille formules masquée côté prestataire — redirection paramètres."""
    messages.info(
        request,
        "Pour toute question sur votre formule, contactez l'équipe MedCare depuis la page Contact.",
    )
    return redirect("healthcare:prestataire_settings")


@_require_prestataire
def organisme_create(request):
    if hasattr(request.user, "healthcare_provider_profile"):
        return redirect("healthcare:organisme_edit")
    if request.method == "POST":
        form = OrganismeForm(request.POST, request.FILES)
        if form.is_valid():
            org = form.save(commit=False)
            org.user = request.user
            default_plan = get_default_subscription_plan()
            if default_plan:
                org.subscription_plan = default_plan
            org.save()
            try:
                from notifications.dispatcher import dispatch as _notify
                _notify(
                    "organisme.created",
                    context={
                        "organisme": org,
                        "link": f"/admin/healthcare/organismedesante/{org.id}/change/",
                    },
                    actor=request.user,
                )
            except Exception:
                pass
            messages.success(request, "Profil de votre organisme créé ! Il sera activé après vérification.")
            return redirect("healthcare:prestataire_dashboard")
    else:
        form = OrganismeForm()
    ctx = _prest_onboarding_context(request)
    ctx["form"] = form
    return render(request, "healthcare/prestataire/organisme_create.html", ctx)


def _organisme_profile_completion(org) -> int:
    if getattr(org, "account_nature", None) == "praticien" or getattr(org, "is_praticien", False):
        steps = [
            bool((org.name or "").strip()),
            bool((org.profession or "").strip()),
            bool((org.ordre_numero or "").strip()),
            bool(org.logo),
            bool((org.description or "").strip()),
            bool((org.contact_phone or "").strip() or (org.whatsapp_number or "").strip()),
        ]
    else:
        steps = [
            bool((org.name or "").strip()),
            bool(org.logo),
            bool((org.description or "").strip()),
            org.latitude is not None and org.longitude is not None,
            bool((org.contact_phone or "").strip()),
            bool((org.whatsapp_number or "").strip()),
        ]
    return round(sum(1 for ok in steps if ok) / len(steps) * 100)


@_require_prestataire
def organisme_edit(request):
    from .organisme_fiche import profil_hours_meta

    ctx = _dash_context(request, "profile")
    org = ctx["org"]
    if request.method == "POST":
        form = OrganismeForm(request.POST, request.FILES, instance=org)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour avec succès.")
            if getattr(org, "account_nature", None) == "praticien" or getattr(org, "is_praticien", False):
                return redirect("healthcare:organisme_edit")
            return redirect("healthcare:prestataire_profil_public")
    else:
        form = OrganismeForm(instance=org)
    hours_list = _opening_hours_list(org)
    ctx.update({
        "form": form,
        "is_edit": True,
        "profile_completion": _organisme_profile_completion(org),
        "hours_list": hours_list,
        "hours_meta": profil_hours_meta(hours_list),
        "hours_meta_chunks": _profil_hours_meta_chunks(hours_list),
    })
    return render(request, "healthcare/prestataire/organisme_form.html", ctx)


@_require_prestataire
def organisme_hours(request):
    ctx = _dash_context(request, "hours")
    org = ctx["org"]
    if request.method == "POST":
        form = OpeningHoursForm(request.POST, initial_data=org.opening_hours)
        if form.is_valid():
            org.opening_hours = form.get_hours_dict()
            org.save(update_fields=["opening_hours"])
            messages.success(request, "Horaires mis à jour.")
            return redirect("healthcare:prestataire_dashboard")
    else:
        form = OpeningHoursForm(initial_data=org.opening_hours)
    ctx["form"] = form
    return render(request, "healthcare/prestataire/hours_form.html", ctx)


def _insurance_profil_filter_key(segment: str) -> str:
    """Regroupe les segments assurance pour les filtres fiche (démo structures)."""
    if segment == "privee_iard":
        return "privee"
    if segment == "digitale":
        return "digitale"
    if segment == "mutuelle":
        return "mutuelle"
    if segment == "programme":
        return "programme"
    return "public"


def _profil_hours_meta(hours_list) -> str:
    from .organisme_fiche import profil_hours_meta

    return profil_hours_meta(hours_list)


def _profil_hours_meta_chunks(hours_list) -> list[str]:
    from .organisme_fiche import profil_hours_meta_chunks

    return profil_hours_meta_chunks(hours_list)


@_require_prestataire
def prestataire_profil_public(request):
    """
    Aperçu de la fiche telle que vue par un patient (aligné démo « page profil »).
    Sans incrémenter les vues ni créer de ProfileView ; fonctionne même si la fiche n'est pas encore active.
    """
    from .insurance_icons import chip_label_for_assurance_segment

    ctx = _dash_context(request, "public_profile")
    org = OrganismeDeSante.objects.select_related(
        "type_organisme", "subscription_plan", "region"
    ).get(pk=ctx["org"].pk)
    actes = PrestataireActe.objects.filter(
        organisme=org, is_available=True,
    ).select_related("acte__service_medical_category", "acte__parent_service").order_by(
        "acte__service_medical_category__order", "acte__level", "acte__name"
    )
    services_with_actes = {}
    profil_pillars = []
    pillar_idx = 0
    for pa in actes:
        svc = pa.acte.service_medical_category
        svc_name = svc.name if svc else "Autres"
        services_with_actes.setdefault(svc_name, []).append(pa)

    for svc_name, group in services_with_actes.items():
        svc = group[0].acte.service_medical_category if group else None
        pillar_idx += 1
        profil_pillars.append(
            {
                "id": f"p{pillar_idx}",
                "name": svc_name,
                "icon": svc.display_icon if svc else mark_safe('<i class="ti ti-building-hospital"></i>'),
                "actes": group,
                "count": len(group),
            }
        )

    wa_digits = (org.whatsapp_digits or "").strip()
    ns = NotificationSettings.load()
    wa_msg_general = render_notification_template_string(
        ns.patient_wa_me_message_general,
        {"org": org},
    )
    wa_general_url = _whatsapp_me_url(wa_digits, wa_msg_general) if wa_digits else ""
    for pa in actes:
        wa_acte_body = render_notification_template_string(
            ns.patient_wa_me_message_acte,
            {"org": org, "acte": pa.acte},
        )
        pa.whatsapp_url = _whatsapp_me_url(wa_digits, wa_acte_body) if wa_digits else ""

    insurances = PriseEnChargeAssurance.objects.filter(
        organisme=org, is_active=True,
    ).select_related("assurance").order_by("assurance__segment", "assurance__name")

    insurances_profil = []
    for pec in insurances:
        seg = pec.assurance.segment
        insurances_profil.append(
            {
                "name": pec.assurance.name,
                "segment": seg,
                "filter_key": _insurance_profil_filter_key(seg),
                "chip_label": chip_label_for_assurance_segment(
                    seg, pec.assurance.get_segment_display()
                ),
            }
        )

    hours_list = _opening_hours_list(org)
    open_today = None
    for h in hours_list:
        if h.get("is_today"):
            open_today = "closed" if h.get("closed") else "open"
            break

    practical_chips = []
    if org.sans_rendez_vous:
        practical_chips.append({"label": "Sans rendez-vous", "icon": "walk"})
    if org.accepte_tiers_payant:
        practical_chips.append({"label": "Tiers payant", "icon": "card"})
    if org.access_pmr:
        practical_chips.append({"label": "Accès PMR", "icon": "accessibility"})
    if org.prises_sang_domicile:
        practical_chips.append({"label": "Prestations à domicile", "icon": "home"})

    show_pioneer_badge = bool(
        getattr(org.subscription_plan, "is_pioneer_offer", False)
    )

    public_path = reverse("healthcare:organisme_detail", kwargs={"slug": org.slug})
    public_absolute_url = request.build_absolute_uri(public_path)

    from healthcare.organisme_fiche import maps_url_for_org
    maps_url = maps_url_for_org(org)

    ctx.update({
        "services_with_actes": services_with_actes,
        "profil_pillars": profil_pillars,
        "actes_visible_count": actes.count(),
        "insurances": insurances,
        "insurances_profil": insurances_profil,
        "wa_general_url": wa_general_url,
        "maps_url": maps_url,
        "hours_list": hours_list,
        "hours_meta": _profil_hours_meta(hours_list),
        "hours_meta_chunks": _profil_hours_meta_chunks(hours_list),
        "open_today": open_today,
        "practical_chips": practical_chips,
        "show_pioneer_badge": show_pioneer_badge,
        "show_public_prices": bool(org.show_prices_on_public_profile),
        "public_absolute_url": public_absolute_url,
        "public_path": public_path,
        "is_preview": True,
    })
    return render(request, "healthcare/prestataire/profil_public.html", ctx)


@_require_prestataire
def prestataire_zones_prelevement(request):
    """Redirige vers le catalogue actes (bloc prestations à domicile inline)."""
    return redirect(reverse("healthcare:actes_list") + "#bloc-domicile")


def actes_list(request):
    from healthcare.prestataire_catalogue_views import actes_list as handler

    return handler(request)


def actes_import_excel(request):
    from healthcare.prestataire_catalogue_views import actes_import_excel as handler

    return handler(request)


def actes_template_excel(request):
    from healthcare.prestataire_catalogue_views import actes_template_excel as handler

    return handler(request)


def prestataire_acte_prerequisites(request, acte_id):
    from healthcare.prestataire_catalogue_views import prestataire_acte_prerequisites as handler

    return handler(request, acte_id)


def prestataire_acte_reminder_add(request, acte_id):
    from healthcare.prestataire_catalogue_views import prestataire_acte_reminder_add as handler

    return handler(request, acte_id)


def prestataire_acte_reminder_delete(request, acte_id, pk):
    from healthcare.prestataire_catalogue_views import prestataire_acte_reminder_delete as handler

    return handler(request, acte_id, pk)


def prestataire_rdv_reminder_list(request):
    from healthcare.prestataire_catalogue_views import prestataire_rdv_reminder_list as handler

    return handler(request)


def prestataire_rdv_reminder_create(request):
    from healthcare.prestataire_catalogue_views import prestataire_rdv_reminder_create as handler

    return handler(request)


def prestataire_rdv_reminder_edit(request, pk):
    from healthcare.prestataire_catalogue_views import prestataire_rdv_reminder_edit as handler

    return handler(request, pk)


def prestataire_rdv_reminder_delete(request, pk):
    from healthcare.prestataire_catalogue_views import prestataire_rdv_reminder_delete as handler

    return handler(request, pk)


@_require_prestataire
def acte_add(request):
    ctx = _dash_context(request, "actes")
    org = ctx["org"]
    if request.method == "POST":
        form = PrestataireActeForm(request.POST, organisme=org)
        if form.is_valid():
            pa = form.save(commit=False)
            pa.organisme = org
            if PrestataireActe.objects.filter(organisme=org, acte=pa.acte).exists():
                messages.warning(request, "Cet acte est déjà dans votre liste.")
            else:
                pa.save()
                messages.success(request, f"Acte « {pa.acte.name} » ajouté.")
            return redirect("healthcare:actes_list")
    else:
        form = PrestataireActeForm(organisme=org)
    sel = request.POST.get("acte") if request.method == "POST" else None
    ctx.update(
        {
            "form": form,
            "is_edit": False,
            **_presta_acte_form_ui(
                form.fields["acte"].queryset,
                post_data=request.POST if request.method == "POST" else None,
                selected_acte_pk=sel,
            ),
        }
    )
    return render(request, "healthcare/prestataire/acte_form.html", ctx)


@_require_prestataire
def acte_edit(request, pk):
    ctx = _dash_context(request, "actes")
    pa = get_object_or_404(PrestataireActe, pk=pk, organisme=ctx["org"])
    if request.method == "POST":
        form = PrestataireActeForm(request.POST, instance=pa, organisme=ctx["org"])
        if form.is_valid():
            was_available = pa.is_available
            form.save()
            if was_available and not pa.is_available:
                try:
                    from notifications.dispatcher import dispatch as _notify
                    _notify(
                        "acte.disabled",
                        context={
                            "organisme": ctx["org"],
                            "acte": pa.acte,
                            "link": f"/admin/healthcare/prestataireacte/{pa.pk}/change/",
                        },
                        actor=None,
                    )
                except Exception:
                    pass
            messages.success(request, "Acte mis à jour.")
            return redirect("healthcare:actes_list")
    else:
        form = PrestataireActeForm(instance=pa, organisme=ctx["org"])
    sel = request.POST.get("acte") if request.method == "POST" else pa.acte_id
    ctx.update(
        {
            "form": form,
            "is_edit": True,
            **_presta_acte_form_ui(
                form.fields["acte"].queryset,
                post_data=request.POST if request.method == "POST" else None,
                selected_acte_pk=sel,
            ),
        }
    )
    return render(request, "healthcare/prestataire/acte_form.html", ctx)


@_require_prestataire
def acte_delete(request, pk):
    org = get_object_or_404(OrganismeDeSante, user=request.user)
    pa = get_object_or_404(PrestataireActe, pk=pk, organisme=org)
    pa.delete()
    messages.success(request, "Acte supprimé.")
    return redirect("healthcare:actes_list")


@_require_prestataire
@require_POST
def acte_toggle_available(request, pk):
    """Bascule rapidement la disponibilité d'un acte depuis la liste catalogue."""
    org = get_object_or_404(OrganismeDeSante, user=request.user)
    pa = get_object_or_404(PrestataireActe, pk=pk, organisme=org)
    was_available = pa.is_available
    pa.is_available = not pa.is_available
    pa.save(update_fields=["is_available", "updated_at"])
    if was_available and not pa.is_available:
        try:
            from notifications.dispatcher import dispatch as _notify
            _notify(
                "acte.disabled",
                context={
                    "organisme": org,
                    "acte": pa.acte,
                    "link": f"/admin/healthcare/prestataireacte/{pa.pk}/change/",
                },
                actor=None,
            )
        except Exception:
            pass
    messages.success(
        request,
        f"« {pa.acte.name} » est maintenant {'visible' if pa.is_available else 'masqué'}.",
    )
    return redirect(request.POST.get("next") or "healthcare:actes_list")


@_require_prestataire
def insurances_manage(request):
    """Assurances acceptées — cases par segment (réf. catalogue) + champ libre « Tarifs & délais »."""
    ctx = _dash_context(request, "insurances")
    org = OrganismeDeSante.objects.get(pk=ctx["org"].pk)

    if not org.is_active:
        messages.warning(
            request,
            "Votre structure est en attente d'activation. La gestion des assurances sera disponible dès validation de votre compte."
        )
        return redirect("healthcare:prestataire_dashboard")

    if request.method == "POST" and request.POST.get("action") == "add_custom_assurance":
        custom_name = (request.POST.get("name") or "").strip()
        custom_segment = (request.POST.get("segment") or "").strip()
        custom_description = (request.POST.get("description") or "").strip()

        try:
            name = InsuranceManageService.add_custom_assurance(
                org, name=custom_name, segment=custom_segment, description=custom_description
            )
            messages.success(
                request,
                f"L'assurance « {name} » a été ajoutée et sélectionnée avec succès pour votre établissement."
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("healthcare:insurances_manage")

    if request.method == "POST" and request.POST.get("action") == "save_assurances":
        raw_ids = request.POST.getlist("assurance_ids")
        tarifs_delais = request.POST.get("assurances_tarifs_delais") or ""
        InsuranceManageService.save_assurances(org, raw_ids, tarifs_delais)
        messages.success(request, "Assurances acceptées et texte Tarifs & délais enregistrés.")
        return redirect("healthcare:insurances_manage")

    q = (request.GET.get("q") or "").strip()
    seg_filter = (request.GET.get("segment") or "").strip()
    ctx.update(InsuranceManageService.build_context(org, q=q, seg_filter=seg_filter))
    return render(request, "healthcare/prestataire/insurances.html", ctx)

@_require_prestataire
def insurance_delete(request, pk):
    org = get_object_or_404(OrganismeDeSante, user=request.user)
    pec = get_object_or_404(PriseEnChargeAssurance, pk=pk, organisme=org)
    pec.delete()
    messages.success(request, "Assurance retirée.")
    return redirect("healthcare:insurances_manage")


@require_POST
def api_ai_agent_chat(request):
    """Endpoint AJAX pour l'Agent IA MedCare (recherche intelligente)."""
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        data = request.POST or {}

    user_prompt = (data.get("prompt") or data.get("q") or "").strip()

    from .ai_agent import process_ai_patient_request
    response_data = process_ai_patient_request(user_prompt)

    return JsonResponse(response_data)

