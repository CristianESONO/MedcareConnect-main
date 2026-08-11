import json
from datetime import datetime
from urllib.parse import quote, urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal, InvalidOperation

from django.db.models import Q, Min, Max, Count, F, Sum, Case, When, IntegerField, Value, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
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

from .forms import (
    OrganismeForm,
    OpeningHoursForm,
    PrestataireActeForm,
    PlatformReviewForm,
    SubscriptionChangeRequestForm,
)
from .geo import haversine_km, parse_lat_lng, parse_radius_km
from .nominatim import reverse as nominatim_reverse, search_places as nominatim_search

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


_SEARCH_SORT_CHOICES = frozenset(
    {
        "price_asc",
        "price_desc",
        "popular",
        "recent_pa",
        "name_org",
        "distance",
        "delai_asc",
        "delai_desc",
        "delai_rdv_asc",
    }
)


def _annotate_delai_sort(qs):
    """Annotation pour trier les offres par délai indicatif (`PrestataireActe.DELAI_RANK`)."""
    whens = [When(delai=k, then=Value(v)) for k, v in PrestataireActe.DELAI_RANK.items()]
    return qs.annotate(
        _delai_sort=Case(
            *whens,
            default=Value(99),
            output_field=IntegerField(),
        )
    )


def _attach_distance_km_to_offers(offers, latlng):
    """Distance GPS → structure (km) pour affichage / tri panneau « Complétez »."""
    if not latlng:
        return
    lat0, lng0 = latlng
    for pa in offers:
        if getattr(pa, "distance_km", None) is not None:
            continue
        org = pa.organisme
        if org.latitude is None or org.longitude is None:
            pa.distance_km = None
            continue
        pa.distance_km = round(
            haversine_km(lat0, lng0, float(org.latitude), float(org.longitude)),
            1,
        )


def _parse_int_list(values):
    out = []
    for x in values:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(out))


def _acte_ids_from_lot_params(lot_ids: list[int]) -> list[int]:
    if not lot_ids:
        return []
    return list(
        ActeMedical.objects.filter(
            lot_memberships__lot_id__in=lot_ids,
        )
        .values_list("pk", flat=True)
        .distinct()
    )


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
        chunk.sort(key=lambda a: (a.parent_service_id, a.name))
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


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENT SIDE — Search, Browse, Detail
# ═══════════════════════════════════════════════════════════════════════════════

def _search_querydict_for_links(request_get):
    """Paramètres GET pour préserver liens de pagination (sans page)."""
    p = request_get.copy()
    if "page" in p:
        del p["page"]
    return p.urlencode()


def _whatsapp_me_url(digits: str, message: str) -> str:
    """Lien wa.me avec texte prérempli (UTF-8)."""
    if not digits:
        return ""
    return "https://wa.me/" + digits + "?text=" + quote(message)


def _search_url_with_query(query_string: str) -> str:
    """URL /healthcare/search/ sans « ? » final si aucun paramètre."""
    base = reverse("healthcare:search")
    qs = (query_string or "").strip()
    return base + (f"?{qs}" if qs else "")


def _build_mobile_piliers_payload(acte_offer_counts: dict[int, int]) -> list[dict]:
    """Arbre actes par pilier pour la grille mobile (checkboxes, style démo)."""
    from healthcare.service_icons import icon_for_service_medical, mobile_labels_for_service


    actes = ActeMedical.objects.filter(is_active=True, level=3).select_related(
        "parent_service", "service_medical_category"
    )
    by_svc_cat, by_exact = _build_acte_nav_indexes(actes)

    piliers: list[dict] = []
    for svc in ServiceMedical.objects.filter(is_active=True).order_by("order", "name"):
        p_info = _actes_order_for_service_name(svc.name)
        if not p_info:
            continue
        cats_out: list[dict] = []
        for cat_name in p_info["categories"]:
            actes_out: list[dict] = []
            seen_pks: set[int] = set()
            for act_name in p_info["acts"].get(cat_name, []):
                a = _resolve_acte_for_nav(
                    svc.pk, cat_name, act_name, by_svc_cat, by_exact
                )
                pk = a.pk if a else None
                if pk and pk in seen_pks:
                    continue
                if pk:
                    seen_pks.add(pk)
                actes_out.append(
                    {
                        "pk": pk,
                        "name": act_name,
                        "count": int(acte_offer_counts.get(pk, 0)) if pk else 0,
                    }
                )
            if actes_out:
                # Sort actes_out to match demo order: actes from ACTES_ORDER first, then others by name
                demo_acts = p_info["acts"].get(cat_name, [])
                def sort_key(row):
                    try:
                        idx = demo_acts.index(row["name"])
                        return (0, idx)
                    except ValueError:
                        return (1, row["name"])
                actes_out.sort(key=sort_key)
                cats_out.append({"name": cat_name, "actes": actes_out})
        # Categories are already in correct order from p_info["categories"]
        from healthcare.service_icons import (
            icon_for_service_medical,
            mobile_labels_for_service,
            strip_leading_emoji,
        )

        clean_title = strip_leading_emoji(svc.name)
        short, sub = mobile_labels_for_service(clean_title)
        piliers.append(
            {
                "id": str(svc.pk),
                "icon": icon_for_service_medical(svc),
                "label": short,
                "sub": sub,
                "title": clean_title,
                "cats": cats_out,
            }
        )
    return piliers


def _search_url_with_acte_pool(request, acte_ids: list[int]) -> str:
    """
    URL recherche en conservant filtres (sauf acte/lot), puis uniquement acte=… pour chaque id.

    Ne pas réinjecter lot= : le pool affiché est union(actes GET, actes du lot) ; garder le lot
    après « retirer une pastille » ferait réapparaître les examens du lot (lien sans effet).
    """
    pairs = []
    for key in request.GET.keys():
        if key in ("acte", "lot"):
            continue
        for val in request.GET.getlist(key):
            pairs.append((key, val))
    for aid in acte_ids:
        pairs.append(("acte", str(aid)))
    return _search_url_with_query(urlencode(pairs, doseq=True))


def _search_url_mutate(request, **kw) -> str:
    """
    Reconstruit l’URL /healthcare/search/ à partir du GET courant (sans page=).
    Mots-clés : clear_service, clear_acte, service=…, acte=… (un seul id acte).
    """
    q = request.GET.copy()
    q.pop("page", None)
    if kw.get("clear_service"):
        q.pop("service", None)
    elif "service" in kw:
        v = kw["service"]
        if v is None or v == "":
            q.pop("service", None)
        else:
            q["service"] = str(v)
    if kw.get("clear_acte"):
        q.pop("acte", None)
    if kw.get("acte") is not None:
        q.setlist("acte", [str(kw["acte"])])
    return _search_url_with_query(q.urlencode())


def _parse_decimal_param(raw, default=None):
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return Decimal(str(raw).replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return default


def _search_org_card_icon(org: OrganismeDeSante) -> str:
    blob = f"{org.name} {(org.type_organisme.name if org.type_organisme else '')}".lower()
    if any(k in blob for k in ("labo", "biolog", "anapath")):
        return "🧬"
    if any(k in blob for k in ("imag", "radio", "scanner", "irm", "écho", "echo")):
        return "🩻"
    if any(k in blob for k in ("cardio", "explor", "efr", "ecg")):
        return "⚡"
    if "ambulanc" in blob:
        return "🚑"
    if "dent" in blob:
        return "🦷"
    if any(k in blob for k in ("kiné", "kine", "soin")):
        return "💉"
    return "🏥"

ACTES_ORDER = {
    "Biologie médicale": {
        "categories": [
            "Hématologie", "Hémostase / Coagulation", "Biochimie & Ionogramme",
            "Immunologie & Auto-immunité", "Sérologie & Virologie", "Bactériologie",
            "Parasitologie & Mycologie", "Endocrinologie", "Fertilité / AMP",
            "Gaz du sang & Acido-basique", "Anatomopathologie", "Cytologie",
            "Biologie moléculaire / PCR", "Toxicologie", "Marqueurs tumoraux"
        ],
        "acts": {
            "Hématologie": [
                "NFS / Hémogramme", "Réticulocytes", "VS", "Frottis sanguin",
                "Groupe ABO/Rhésus", "RAI", "Test de Coombs direct", "Test de Coombs indirect",
                "Électrophorèse de l'hémoglobine", "Vitamine B12", "Folates (B9)",
                "Fer sérique", "Ferritine", "Transferrine / CST"
            ],
            "Hémostase / Coagulation": [
                "TP / INR", "TCA", "Fibrinogène", "D-Dimères", "Temps de thrombine (TT)",
                "Activité anti-Xa", "Dosage facteur VIII", "Dosage facteur IX"
            ],
            "Biochimie & Ionogramme": [
                "Glycémie à jeun", "HbA1c", "Urée sanguine", "Créatininémie", "Natrémie",
                "Kaliémie", "Chlorémie", "Calcémie", "Phosphorémie", "Magnésémie",
                "ASAT", "ALAT", "GGT", "PAL", "Bilirubine totale", "Bilirubine conjuguée",
                "Albumine", "Protéines totales", "Électrophorèse des protéines",
                "Lipase", "Amylase", "CRP", "Procalcitonine", "Cholestérol total",
                "HDL", "LDL", "Triglycérides", "Apolipoprotéines A/B", "Lactates"
            ],
            "Immunologie & Auto-immunité": [
                "ANA / AAN", "FR (facteur rhumatoïde)", "Anti-CCP", "Complément C3",
                "Complément C4", "IgG / IgA / IgM", "Anti-dsDNA", "Anti-Sm",
                "Anti-RNP", "Anti-SSA / SSB", "Anticoagulant lupique",
                "Anticardiolipines IgG/IgM", "Anti-β2GP1", "ANCA MPO/PR3"
            ],
            "Sérologie & Virologie": [
                "VIH Ag/Ac", "Charge virale VIH", "HBsAg", "Anti-HBs", "Anti-HBc total",
                "Anti-HBc IgM", "HBeAg / Anti-HBe", "ADN VHB (charge virale HBV)",
                "Anti-VHC", "ARN VHC (charge virale HCV)", "Syphilis VDRL",
                "Syphilis TPHA", "Dengue NS1/IgM/IgG", "Chikungunya IgM/IgG",
                "Toxoplasmose IgG/IgM", "Rubéole IgG/IgM", "CMV IgG/IgM", "EBV (Epstein-Barr)"
            ],
            "Bactériologie": [
                "ECBU + antibiogramme", "Coproculture", "Hémocultures", "ECB plaies / pus",
                "Prélèvement vaginal / cervico-vaginal", "ECBE / expectorations",
                "Culture crachats", "Recherche BK / BAAR"
            ],
            "Parasitologie & Mycologie": [
                "Goutte épaisse / TDR paludisme", "Examen parasitologique des selles",
                "Filariose sanguine", "Bilharziose (urines/selles)",
                "Examen mycologique peau/ongles", "Recherche Candida"
            ],
            "Endocrinologie": [
                "TSH", "FT4", "FT3", "Anti-TPO", "Anti-Thyroglobuline", "Aldostéronémie",
                "Rénine", "Cortisol", "Prolactine", "FSH", "LH", "Estradiol",
                "Progestérone", "Testostérone", "AMH"
            ],
            "Fertilité / AMP": [
                "Spermogramme", "Spermocytogramme", "Test de migration-survie (TMS)",
                "Spermoculture + antibiogramme", "AMH (réserve ovarienne)"
            ],
            "Gaz du sang & Acido-basique": [
                "Gaz du sang artériel", "Gaz du sang capillaire", "Lactates artériels"
            ],
            "Anatomopathologie": [
                "Examen anapath. pièce opératoire", "Examen anapath. biopsie",
                "Immunohistochimie", "Immunofluorescence directe"
            ],
            "Cytologie": [
                "Cytologie liquide pleural", "Cytologie ascite", "Cytologie LCR",
                "Cytologie urinaire", "Frottis cervico-vaginal (FCV)", "Cytoponction thyroïde",
                "Cytoponction ganglion"
            ],
            "Biologie moléculaire / PCR": [
                "PCR Chlamydia / Gonocoque", "PCR HPV (génotypage)", "PCR BK",
                "GeneXpert MTB/RIF", "PCR respiratoires multiplex"
            ],
            "Toxicologie": [
                "Drogues urinaires (panel)", "Alcoolémie", "Paracétamol plasmatique",
                "Carboxyhémoglobine", "Métaux lourds"
            ],
            "Marqueurs tumoraux": [
                "PSA total", "PSA libre", "CEA", "AFP", "CA 125", "CA 19-9",
                "CA 15-3", "βHCG quantitatif"
            ]
        }
    },
    "Imagerie médicale": {
        "categories": [
            "Radiographie", "Échographie", "Échodoppler", "Scanner (TDM)", "IRM",
            "Biopsies guidées", "Ponctions guidées", "Drainages guidés"
        ],
        "acts": {
            "Radiographie": [
                "Radio thorax", "Radio abdomen (ASP)", "Radio rachis cervical",
                "Radio rachis dorsal", "Radio rachis lombaire", "Radio bassin",
                "Radio membre — genou", "Radio membre — épaule",
                "Radio membre — cheville / pied", "Radio crâne"
            ],
            "Échographie": [
                "Échographie abdominale", "Échographie pelvienne", "Échographie endovaginale",
                "Échographie obstétricale T1", "Échographie morphologique T2",
                "Échographie T3 (biométrie)", "Échographie thyroïdienne",
                "Échographie testiculaire", "Échographie parties molles", "Mammographie"
            ],
            "Échodoppler": [
                "Échodoppler veineux membres inférieurs", "Échodoppler artériel membres inférieurs",
                "Échodoppler carotidien + vertébral", "Écho-cœur (échocardiographie transthoracique)"
            ],
            "Scanner (TDM)": [
                "Scanner cérébral sans injection", "Scanner cérébral avec injection",
                "Scanner thoracique", "Scanner TAP (thoraco-abdomino-pelvien)",
                "Scanner sinus", "Angio-TDM cérébral"
            ],
            "IRM": [
                "IRM cérébrale sans injection", "IRM cérébrale avec injection",
                "IRM rachis cervical", "IRM rachis lombaire", "IRM abdomen / pelvis",
                "IRM prostate", "IRM cardiaque"
            ],
            "Biopsies guidées": [
                "Biopsie hépatique (écho-guidée)", "Biopsie mammaire (écho-guidée)",
                "Biopsie rénale (écho-guidée)", "Biopsie pulmonaire (scanner-guidée)",
                "Biopsie thyroïdienne (écho-guidée)", "Biopsie ganglionnaire",
                "Biopsie osseuse (scanner-guidée)"
            ],
            "Ponctions guidées": [
                "Ponction pleurale (écho-guidée)", "Ponction abdominale / ascite",
                "Ponction articulaire genou", "Ponction articulaire épaule / hanche",
                "Ponction mammaire diagnostique"
            ],
            "Drainages guidés": [
                "Drainage pleural (thoracique)", "Drainage abdominal / abcès",
                "Drainage biliaire", "Néphrostomie (drainage urinaire)"
            ]
        }
    },
    "Explorations fonctionnelles": {
        "categories": [
            "Cardiologie", "Pneumologie", "Gastro-entérologie", "Neurologie", "ORL",
            "Ophtalmologie", "Dermatologie", "Gynécologie", "Urologie",
            "Andrologie / Fertilité", "Hématologie clinique"
        ],
        "acts": {
            "Cardiologie": [
                "ECG standard 12 dérivations", "Épreuve d'effort (test effort cardiaque)",
                "Holter ECG 24h", "Holter tensionnel MAPA 24h", "Tilt test (table basculante)",
                "Test de marche 6 minutes"
            ],
            "Pneumologie": [
                "EFR / Spirométrie standard", "Spirométrie + bronchodilatateur",
                "Pléthysmographie corps entier", "Test de diffusion DLCO",
                "Oxymétrie nocturne", "Polygraphie ventilatoire (apnées du sommeil)"
            ],
            "Gastro-entérologie": [
                "FOGD (fibroscopie gastrique)", "Coloscopie", "Rectosigmoïdoscopie",
                "Manométrie œsophagienne", "pH-métrie œsophagienne", "Test respiratoire à l'hydrogène"
            ],
            "Neurologie": [
                "EEG standard", "EEG de sommeil", "EMG (électromyogramme)",
                "Potentiels évoqués visuels (PEV)", "Potentiels évoqués auditifs (PEA)",
                "Potentiels évoqués somesthésiques (PES)"
            ],
            "ORL": [
                "Audiométrie tonale", "Audiométrie vocale", "Impédancemétrie (tympanométrie)",
                "Tests vestibulaires VNG", "Fibroscopie ORL"
            ],
            "Ophtalmologie": [
                "Acuité visuelle + réfraction", "Fond d'œil", "OCT (tomographie optique cohérente)",
                "Champ visuel automatisé", "Pachymétrie cornéenne", "Topographie cornéenne",
                "Biométrie oculaire"
            ],
            "Dermatologie": [
                "Dermoscopie", "Cartographie des nævus", "Tests allergologiques cutanés"
            ],
            "Gynécologie": [
                "Hystérosalpingographie (HSG)", "Hystéroscopie diagnostique", "Colposcopie",
                "Monitoring ovulatoire"
            ],
            "Urologie": [
                "Débitmétrie urinaire", "Bilan urodynamique complet"
            ],
            "Andrologie / Fertilité": [
                "Spermogramme (exploration fonctionnelle)", "Spermocytogramme",
                "Test de migration-survie", "Bilan infertilité masculine"
            ],
            "Hématologie clinique": [
                "Myélogramme", "Biopsie ostéo-médullaire", "Test de fragilité osmotique"
            ]
        }
    },
    "Ambulance médicalisée": {
        "categories": [
            "Transport sanitaire", "Rapatriement", "Couverture & assistance"
        ],
        "acts": {
            "Transport sanitaire": [
                "Ambulance simple", "Ambulance médicalisée avec infirmier",
                "Ambulance médicalisée avec médecin", "Transport réanimatoire", "Évacuation sanitaire"
            ],
            "Rapatriement": [
                "Rapatriement national", "Rapatriement international"
            ],
            "Couverture & assistance": [
                "Couverture médicale sportive", "Couverture médicale de manifestation publique",
                "Assistance médicale sur site"
            ]
        }
    },
    "Soins spécialisés": {
        "categories": [
            "Médecine générale", "Cardiologie", "ORL", "Ophtalmologie", "Dermatologie",
            "Gynécologie", "Urologie", "Soins infirmiers", "Rhumatologie / Orthopédie",
            "Pédiatrie", "Kinésithérapie", "Dialyse / Néphrologie", "Psychologie",
            "Psychiatrie", "Oncologie / Radiothérapie"
        ],
        "acts": {
            "Médecine générale": [
                "Suture plaie simple", "Suture plaie complexe", "Incision & drainage abcès cutané",
                "Nébulisation thérapeutique", "Oxygénothérapie"
            ],
            "Cardiologie": [
                "ECG à domicile", "Pose / retrait Holter ECG", "Surveillance post-urgence cardiaque"
            ],
            "ORL": [
                "Lavage d'oreille", "Extraction bouchon de cérumen", "Ablation corps étranger ORL",
                "Cautérisation épistaxis", "Pose / retrait mèche nasale"
            ],
            "Ophtalmologie": [
                "Retrait corps étranger oculaire", "Lavage oculaire médical", "Laser YAG",
                "Laser rétinien", "Injection intravitréenne"
            ],
            "Dermatologie": [
                "Cryothérapie cutanée", "Exérèse lésion cutanée bénigne", "Électrocoagulation",
                "Biopsie cutanée", "Peeling médical", "Laser dermatologique"
            ],
            "Gynécologie": [
                "Pose DIU (stérilet)", "Retrait DIU", "Pose implant contraceptif",
                "Retrait implant", "Biopsie gynécologique", "Cryothérapie cervicale",
                "Aspiration endo-utérine"
            ],
            "Urologie": [
                "Sondage vésical", "Changement de sonde", "Instillation vésicale"
            ],
            "Soins infirmiers": [
                "Pansement simple", "Pansement complexe", "Perfusion IV", "Injection IM / SC",
                "Surveillance glycémique", "Soins de plaies chroniques", "Nursing médicalisé"
            ],
            "Rhumatologie / Orthopédie": [
                "Infiltration articulaire genou", "Infiltration articulaire épaule",
                "Viscosupplémentation", "Injection PRP", "Ponction articulaire évacuatrice",
                "Immobilisation orthopédique"
            ],
            "Pédiatrie": [
                "Nébulisation pédiatrique", "Lavage nasal médicalisé", "Soins plaies pédiatriques",
                "Réhydratation orale supervisée", "Perfusion pédiatrique"
            ],
            "Kinésithérapie": [
                "Rééducation post-traumatique", "Rééducation post-opératoire genou",
                "Rééducation lombalgie / cervicalgie", "Kiné respiratoire adulte",
                "Kiné respiratoire pédiatrique", "Rééducation post-AVC",
                "Rééducation périnéale post-partum", "Drainage lymphatique manuel",
                "Kinésithérapie à domicile"
            ],
            "Dialyse / Néphrologie": [
                "Hémodialyse chronique", "Hémodialyse aiguë", "Dialyse péritonéale",
                "Soins cathéter de dialyse"
            ],
            "Psychologie": [
                "Consultation de psychologie initiale", "Séance de psychologie de suivi",
                "Thérapie individuelle", "Thérapie de couple", "Thérapie familiale",
                "Téléconsultation psychologique"
            ],
            "Psychiatrie": [
                "Consultation psychiatrique initiale", "Consultation psychiatrique de suivi",
                "Évaluation psychiatrique diagnostique", "Ajustement traitement psychotrope",
                "Téléconsultation psychiatrique"
            ],
            "Oncologie / Radiothérapie": [
                "Consultation d'oncologie médicale", "Administration chimiothérapie ambulatoire",
                "Séance de radiothérapie", "Soins palliatifs ambulatoires"
            ]
        }
    },
    "Soins dentaires": {
        "categories": [
            "Consultations dentaires", "Soins conservateurs", "Endodontie",
            "Chirurgie dentaire", "Prothèses", "Implantologie", "Orthodontie",
            "Esthétique dentaire"
        ],
        "acts": {
            "Consultations dentaires": [
                "Consultation dentaire standard", "Consultation dentaire spécialisée",
                "Consultation d'urgence dentaire", "Bilan bucco-dentaire complet"
            ],
            "Soins conservateurs": [
                "Détartrage complet", "Détartrage + polissage + fluoration",
                "Traitement carie (composite)", "Obturation amalgame"
            ],
            "Endodontie": [
                "Traitement endodontique mono-radiculaire", "Traitement endodontique bi-radiculaire",
                "Traitement endodontique multi-radiculaire", "Reprise endodontique"
            ],
            "Chirurgie dentaire": [
                "Extraction simple", "Extraction chirurgicale", "Extraction dent de sagesse incluse",
                "Drainage abcès dentaire"
            ],
            "Prothèses": [
                "Couronne céramique / zirconium", "Bridge 3 éléments",
                "Prothèse amovible partielle", "Prothèse complète"
            ],
            "Implantologie": [
                "Consultation implantaire", "Pose d'implant dentaire", "Greffe osseuse",
                "Couronne sur implant"
            ],
            "Orthodontie": [
                "Appareil orthodontique fixe (arcade)", "Appareil amovible",
                "Gouttières transparentes (aligneurs)", "Contention post-orthodontie"
            ],
            "Esthétique dentaire": [
                "Blanchiment dentaire professionnel", "Facette céramique (par dent)",
                "Smile design (consultation + plan)"
            ]
        }
    }
}


def _normalize_catalog_label(name: str) -> str:
    if not name:
        return ""
    import unicodedata as _ud
    # Retirer les emojis/symboles Unicode (So, Sm, Sk, Sc, Cs, Co, Cn)
    # Ex: "🧬 Biologie medicale" -> "Biologie medicale"
    cleaned = "".join(
        c for c in name
        if _ud.category(c) not in ("So", "Sm", "Sk", "Sc", "Cs", "Co", "Cn")
    )
    return (
        cleaned.replace("’", "'")
        .replace("‘", "'")
        .replace(" ", "")
        .lower()
        .strip()
    )


def _actes_order_for_service_name(service_name: str) -> dict | None:
    sn = _normalize_catalog_label(service_name)
    for key, info in ACTES_ORDER.items():
        if _normalize_catalog_label(key) == sn:
            return info
    return None


def _acte_labels_match(canonical: str, db_name: str) -> bool:
    nc = _normalize_catalog_label(canonical)
    nd = _normalize_catalog_label(db_name)
    if nc == nd:
        return True
    if len(nc) >= 3 and (nd.startswith(nc) or nc.startswith(nd)):
        return True
    return False


def _build_acte_nav_indexes(actes_qs):
    by_svc_cat: dict[tuple[int, str], list] = defaultdict(list)
    by_exact: dict[tuple[int, str, str], ActeMedical] = {}
    for a in actes_qs:
        if a.level != 3:
            continue
        sid = a.service_medical_category_id
        if sid is None:
            continue
        cat_norm = _normalize_catalog_label(
            a.parent_service.name if a.parent_service_id else ""
        )
        by_svc_cat[(sid, cat_norm)].append(a)
        by_exact[(sid, cat_norm, _normalize_catalog_label(a.name))] = a
    return by_svc_cat, by_exact


def _resolve_acte_for_nav(
    service_id: int,
    cat_name: str,
    act_name: str,
    by_svc_cat,
    by_exact,
):
    cat_norm = _normalize_catalog_label(cat_name)
    key = (service_id, cat_norm, _normalize_catalog_label(act_name))
    if key in by_exact:
        return by_exact[key]
    for a in by_svc_cat.get((service_id, cat_norm), []):
        if _acte_labels_match(act_name, a.name):
            return a
    return None


@ensure_csrf_cookie
def search(request):
    """
    Recherche centrée sur les **prestations** (offres Prix + Acte + Lieu), façon marketplace / e-commerce.
    Les établissements restent accessibles via la page « Centres ».
    """
    q = request.GET.get("q", "").strip()
    service_id = request.GET.get("service")
    acte_ids_clean: list[int] = []
    for x in request.GET.getlist("acte"):
        try:
            acte_ids_clean.append(int(x))
        except (TypeError, ValueError):
            continue
    acte_ids_clean = list(dict.fromkeys(acte_ids_clean))
    lot_ids_clean = _parse_int_list(request.GET.getlist("lot"))
    # Sans ceci, lot= réétend le périmètre (union) : pastille retirée ou lien « Toutes »
    # pouvaient laisser lot= alors que l’utilisateur a une liste d’actes explicite affinée.
    if lot_ids_clean and acte_ids_clean:
        lot_acte_set = frozenset(_acte_ids_from_lot_params(lot_ids_clean))
        explicit_set = frozenset(acte_ids_clean)
        if lot_acte_set and (
            explicit_set <= lot_acte_set or lot_acte_set <= explicit_set
        ):
            qd = request.GET.copy()
            qd.pop("lot", None)
            new_qs = qd.urlencode()
            if request.GET.getlist("lot"):
                return redirect(_search_url_with_query(new_qs))
    acte_ids_from_lots = _acte_ids_from_lot_params(lot_ids_clean)
    # Pastilles / contexte : uniquement actes explicites dans l’URL (pas la session parcours).
    pool_for_pills = list(
        dict.fromkeys([*acte_ids_clean, *acte_ids_from_lots]),
    )
    pool_from_request = bool(acte_ids_clean or lot_ids_clean or q)
    if len(acte_ids_clean) == 1:
        acte_id = str(acte_ids_clean[0])
    elif len(pool_for_pills) == 1:
        acte_id = str(pool_for_pills[0])
    else:
        acte_id = ""
    level = request.GET.get("level")
    assurance_ids = [v for v in request.GET.getlist("assurance") if v]
    assurance_ids_int: list[int] = []
    for x in assurance_ids:
        try:
            assurance_ids_int.append(int(x))
        except (TypeError, ValueError):
            continue
    city = request.GET.get("city", "").strip()
    type_ids = [v for v in request.GET.getlist("type") if v]
    region_ids = [v for v in request.GET.getlist("region") if v]
    sort = request.GET.get("sort", "price_asc")
    if sort not in _SEARCH_SORT_CHOICES:
        sort = "price_asc"
    radius_km = parse_radius_km(request.GET.get("radius_km"), default=30.0)
    price_min = _parse_decimal_param(request.GET.get("price_min"))
    price_max = _parse_decimal_param(request.GET.get("price_max"))
    delai_filter = (request.GET.get("delai") or "").strip()
    valid_delais = {k for k, _ in PrestataireActe.DELAI_CHOICES if k}
    if delai_filter not in valid_delais:
        delai_filter = ""
    domicile_filter = request.GET.get("domicile") == "1"

    if request.GET.get("clear_geo"):
        request.session.pop("search_lat", None)
        request.session.pop("search_lng", None)

    latlng = parse_lat_lng(request.GET.get("lat"), request.GET.get("lng"))
    geo_from_get = latlng is not None and not request.GET.get("clear_geo")

    if latlng is None and not request.GET.get("clear_geo"):
        latlng = parse_lat_lng(request.session.get("search_lat"), request.session.get("search_lng"))

    if geo_from_get and latlng:
        request.session["search_lat"] = str(latlng[0])
        request.session["search_lng"] = str(latlng[1])

    proximity_on = request.GET.get("proximity") == "1" and latlng is not None

    pa_qs = PrestataireActe.objects.filter(
        is_available=True,
        organisme__is_active=True,
    ).select_related(
        "organisme",
        "organisme__type_organisme",
        "organisme__region",
        "organisme__subscription_plan",
        "acte",
        "acte__service_medical_category",
    )

    if q:
        q_filter = (
            Q(acte__name__icontains=q)
            | Q(acte__description__icontains=q)
            | Q(acte__service_medical_category__name__icontains=q)
            | Q(organisme__name__icontains=q)
            | Q(organisme__city__icontains=q)
        )
        if len(q) >= 2:
            q_filter |= Q(acte__code__icontains=q)
        pa_qs = pa_qs.filter(q_filter)

    # Pilier actif : filtre les résultats seulement en navigation (sans acte/lot explicite).
    if service_id and not acte_ids_clean and not lot_ids_clean:
        pa_qs = pa_qs.filter(acte__service_medical_category_id=service_id)

    # Même périmètre que les résultats mais **sans** filtre acte(s) : compteurs nav / pastilles.
    pa_qs_before_acte = pa_qs

    if acte_ids_clean:
        if len(acte_ids_clean) == 1:
            pa_qs = pa_qs.filter(acte_id=acte_ids_clean[0])
        else:
            # Recherche groupée : filtrer les structures proposant AU MOINS UN des actes sélectionnés (union)
            pa_qs = pa_qs.filter(acte_id__in=acte_ids_clean)

    def _apply_level_price_location_filters(qs):
        if level in ("1", "2", "3"):
            qs = qs.filter(acte__level=int(level))
        if price_min is not None:
            qs = qs.filter(price__gte=price_min)
        if price_max is not None:
            qs = qs.filter(price__lte=price_max)
        if assurance_ids_int:
            qs = qs.filter(
                organisme__prises_en_charge__assurance_id__in=assurance_ids_int,
                organisme__prises_en_charge__is_active=True,
            ).distinct()
        if city:
            qs = qs.filter(
                Q(organisme__city__icontains=city)
                | Q(organisme__quartier__icontains=city)
            )
        if type_ids:
            qs = qs.filter(organisme__type_organisme_id__in=type_ids)
        if region_ids:
            qs = qs.filter(organisme__region_id__in=region_ids)
        if delai_filter:
            better_or_equal = [
                k for k in valid_delais
                if PrestataireActe.DELAI_RANK.get(k, 99)
                <= PrestataireActe.DELAI_RANK.get(delai_filter, 99)
            ]
            qs = qs.filter(delai__in=better_or_equal)
        if domicile_filter:
            qs = qs.filter(organisme__prises_sang_domicile=True)
        return qs

    pa_qs = _apply_level_price_location_filters(pa_qs)
    pa_qs_before_acte = _apply_level_price_location_filters(pa_qs_before_acte)

    pa_qs = _annotate_delai_sort(pa_qs)
    pa_qs_before_acte = _annotate_delai_sort(pa_qs_before_acte)

    # Layout démo : sans acte/lot/service coché ni recherche texte → aucune offre (état vide par défaut).
    if not acte_ids_clean and not lot_ids_clean and not q and not service_id:
        pa_qs = pa_qs.none()

    # Compteurs sidebar « Parcourir les actes » : filtres page (assurance, zone…), pas pilier ni acte.
    pa_qs_nav = PrestataireActe.objects.filter(
        is_available=True,
        organisme__is_active=True,
    )
    if q:
        pa_qs_nav = pa_qs_nav.filter(q_filter)
    pa_qs_nav = _apply_level_price_location_filters(pa_qs_nav)

    query_string = _search_querydict_for_links(request.GET)

    per_page = 24

    if proximity_on and latlng:
        lat0, lng0 = latlng
        scored = []
        for pa in pa_qs:
            org = pa.organisme
            if org.latitude is None or org.longitude is None:
                continue
            d = haversine_km(lat0, lng0, float(org.latitude), float(org.longitude))
            if d <= radius_km:
                pa.distance_km = round(d, 1)
                scored.append(pa)
        if sort == "price_asc":
            scored.sort(key=lambda x: (x.distance_km, x.price, x.acte.name))
        elif sort == "price_desc":
            scored.sort(key=lambda x: (x.distance_km, -x.price, x.acte.name))
        elif sort == "delai_asc":
            scored.sort(
                key=lambda x: (
                    x.distance_km,
                    getattr(x, "_delai_sort", 99),
                    x.price,
                    x.acte.name,
                )
            )
        elif sort == "delai_desc":
            scored.sort(
                key=lambda x: (
                    x.distance_km,
                    -getattr(x, "_delai_sort", 99),
                    x.price,
                    x.acte.name,
                )
            )
        else:
            scored.sort(key=lambda x: (x.distance_km, x.price))
        results_count = len(scored)
        paginator = Paginator(scored, per_page)
        page = paginator.get_page(request.GET.get("page"))
    elif latlng and sort == "distance":
        lat0, lng0 = latlng
        scored = []
        for pa in pa_qs:
            org = pa.organisme
            if org.latitude is None or org.longitude is None:
                continue
            d = haversine_km(lat0, lng0, float(org.latitude), float(org.longitude))
            pa.distance_km = round(d, 1)
            scored.append(pa)
        scored.sort(key=lambda x: (x.distance_km, x.price))
        results_count = len(scored)
        paginator = Paginator(scored, per_page)
        page = paginator.get_page(request.GET.get("page"))
    else:
        if sort == "price_desc":
            pa_qs = pa_qs.order_by("-price", "acte__name", "organisme__name")
        elif sort == "popular":
            pa_qs = pa_qs.order_by("-organisme__profile_views_count", "price", "acte__name")
        elif sort == "recent_pa":
            pa_qs = pa_qs.order_by("-updated_at", "acte__name")
        elif sort == "name_org":
            pa_qs = pa_qs.order_by("organisme__name", "acte__name", "price")
        elif sort == "delai_asc":
            pa_qs = pa_qs.order_by("_delai_sort", "price", "acte__name", "organisme__name")
        elif sort == "delai_desc":
            pa_qs = pa_qs.order_by("-_delai_sort", "price", "acte__name", "organisme__name")
        elif sort == "delai_rdv_asc":
            pa_qs = pa_qs.order_by("_delai_sort", "price", "acte__name", "organisme__name")
        else:
            # price_asc par défaut (comportement « e-commerce »)
            pa_qs = pa_qs.order_by("price", "acte__name", "organisme__name")
        results_count = pa_qs.count()
        paginator = Paginator(pa_qs, per_page)
        page = paginator.get_page(request.GET.get("page"))

    if request.user.is_authenticated and (
        q
        or service_id
        or acte_ids_clean
        or assurance_ids
        or region_ids
        or type_ids
        or city
        or level
        or price_min is not None
        or price_max is not None
        or proximity_on
        or delai_filter
        or domicile_filter
    ):
        stype = "acte" if acte_ids_clean else "service" if service_id else "general"
        if proximity_on or sort == "distance":
            stype = "localisation"
        SearchHistory.objects.create(
            user=request.user,
            query=q or "Recherche prestations (filtres)",
            search_type=stype,
            filters_applied={
                "service": service_id,
                "acte": acte_ids_clean[0] if len(acte_ids_clean) == 1 else acte_ids_clean,
                "assurance": assurance_ids,
                "city": city,
                "region": region_ids,
                "type": type_ids,
                "level": level,
                "price_min": str(price_min) if price_min is not None else None,
                "price_max": str(price_max) if price_max is not None else None,
                "delai": delai_filter or None,
                "domicile": domicile_filter,
                "proximity": proximity_on,
                "radius_km": radius_km if proximity_on else None,
                "lat": latlng[0] if latlng else None,
                "lng": latlng[1] if latlng else None,
                "sort": sort,
            },
            results_count=results_count,
        )

    saved_lat = saved_lng = None
    if request.user.is_authenticated and request.user.is_patient:
        try:
            pp = request.user.patient_profile
            saved_lat = pp.last_known_latitude
            saved_lng = pp.last_known_longitude
        except Exception:
            pass

    price_stats = PrestataireActe.objects.filter(
        is_available=True, organisme__is_active=True,
    ).aggregate(pmin=Min("price"), pmax=Max("price"))

    top_cities = list(
        OrganismeDeSante.objects.filter(is_active=True)
        .exclude(city__isnull=True)
        .exclude(city__exact="")
        .values("city")
        .annotate(n=Count("id"))
        .order_by("-n", "city")
        .values_list("city", flat=True)[:30]
    )

    active_filter_count = sum(
        bool(x)
        for x in (
            service_id,
            acte_ids_clean,
            level,
            assurance_ids,
            city,
            type_ids,
            region_ids,
            price_min is not None,
            price_max is not None,
            proximity_on,
            delai_filter,
            domicile_filter,
        )
    )

    preset_payload = []
    for lot in (
        LotExamenPrefait.objects.filter(is_active=True)
        .prefetch_related("lot_actes__acte")
        .order_by("order", "name")
    ):
        actes_lot = [la.acte for la in lot.lot_actes.all()]
        preset_payload.append(
            {
                "id": lot.id,
                "name": lot.name,
                "teaser": lot.teaser or "",
                "icon": lot.icon or "📋",
                "acte_ids": [a.id for a in actes_lot],
                "acte_labels": [a.name for a in actes_lot],
            }
        )

    services_all = ServiceMedical.objects.filter(is_active=True).order_by("order")
    # Filter to only include main pillars (services that have a definition in ACTES_ORDER)
    services_for_sidebar = [s for s in services_all if _actes_order_for_service_name(s.name)]
    # Pastilles « examens » : actes du périmètre (lot/session), pas les familles de soins.
    acte_base = ActeMedical.objects.filter(is_active=True).select_related(
        "service_medical_category",
    )
    if pool_for_pills:
        actes_for_pills = acte_base.filter(pk__in=pool_for_pills).order_by(
            "service_medical_category__order",
            "name",
        )
    else:
        # Aucun lot / parcours / acte : pas de bandeau de pastilles (pas de liste globale).
        actes_for_pills = acte_base.none()

    # Ne restreindre le sélecteur « Acte » au pool que si acte/lot sont dans l’URL.
    # Sinon une session « parcours » avec d’autres examens croisait la famille choisie → liste vide.

    actes_for_browse_nav = acte_base.filter(level=3).order_by(
        "service_medical_category__order", "level", "name"
    )

    # Filtres sidebar legacy (select) : croisement pool seulement si lot/acte explicites (GET).
    if service_id:
        actes_qs = acte_base.filter(service_medical_category_id=service_id)
        if pool_for_pills and pool_from_request:
            narrowed = actes_qs.filter(pk__in=pool_for_pills)
            if narrowed.exists():
                actes_qs = narrowed
        actes_for_filter = actes_qs.order_by("level", "name")
    elif pool_for_pills:
        actes_for_filter = acte_base.filter(pk__in=pool_for_pills).order_by(
            "service_medical_category__order",
            "name",
        )
    else:
        actes_for_filter = actes_for_browse_nav

    acte_keep_query = ""
    if pool_for_pills:
        acte_keep_query = "&" + urlencode(
            [("acte", str(a)) for a in pool_for_pills], doseq=True
        )
    lot_keep_query = ""
    if lot_ids_clean:
        lot_keep_query = "&" + urlencode(
            [("lot", str(lid)) for lid in lot_ids_clean], doseq=True
        )

    acte_pills = []
    for a in actes_for_pills:
        remaining = [x for x in pool_for_pills if x != a.pk]
        acte_pills.append(
            {
                "acte": a,
                "remove_url": _search_url_with_acte_pool(request, remaining),
            }
        )

    acte_results_accordion = []
    if pool_from_request and len(pool_for_pills) > 1:
        by_acte = {}
        for pa in page.object_list:
            by_acte.setdefault(pa.acte_id, []).append(pa)
        acte_objs = {
            x.pk: x
            for x in ActeMedical.objects.filter(pk__in=pool_for_pills).select_related(
                "service_medical_category",
            )
        }
        for aid in pool_for_pills:
            items = by_acte.get(aid, [])
            if not items:
                continue
            acte_results_accordion.append(
                {
                    "acte": acte_objs.get(aid),
                    "items": items,
                }
            )

    # Toujours le layout SIPN (hero + arbre actes) — même avec lot / parcours multi-actes.
    show_dem_service_acte_nav = True
    service_dem_pills: list[dict] = []
    acte_dem_families: list[dict] = []
    dem_clear_acte_url = ""
    if show_dem_service_acte_nav:
        dem_clear_acte_url = _search_url_mutate(
            request, clear_acte=True, clear_service=True
        )
        acte_offer_counts = dict(
            pa_qs_nav.values("acte_id")
            .annotate(n=Count("pk", distinct=True))
            .values_list("acte_id", "n")
        )
        svc_offer_counts: dict[int, int] = {}
        for sid, c in (
            pa_qs_nav.exclude(acte__service_medical_category_id__isnull=True)
            .values("acte__service_medical_category_id")
            .annotate(c=Count("pk", distinct=True))
            .values_list("acte__service_medical_category_id", "c")
        ):
            if sid is not None:
                svc_offer_counts[int(sid)] = int(c)
        total_offers_nav = int(
            pa_qs_nav.aggregate(c=Count("pk", distinct=True))["c"] or 0
        )
        service_dem_pills.append(
            {
                "label": "Toutes les familles",
                "icon": "📋",
                "url": _search_url_mutate(request, clear_service=True, clear_acte=True),
                "active": not service_id,
                "count": total_offers_nav,
            }
        )
        from .service_icons import icon_for_service_medical
        import unicodedata as _ud

        def _strip_leading_emoji(text: str) -> str:
            """Retire les emojis/symboles Unicode en début de chaîne."""
            return "".join(
                c for c in text
                if _ud.category(c) not in ("So", "Sm", "Sk", "Sc", "Cs", "Co", "Cn")
            ).strip()

        for s in services_for_sidebar:
            ic = icon_for_service_medical(s)
            service_dem_pills.append(
                {
                    "label": _strip_leading_emoji(s.name),
                    "icon": ic[:12],
                    "url": _search_url_mutate(
                        request,
                        clear_acte=True,
                        service=str(s.pk),
                    )
                    + "#sidebar-desktop",
                    "active": str(s.pk) == str(service_id or ""),
                    "count": svc_offer_counts.get(int(s.pk), 0),
                    "service_id": str(s.pk),
                    "is_ambulance": "ambulance" in s.name.lower(),
                }
            )
        acte_nav_qs = actes_for_browse_nav.select_related(
            "parent_service",
            "service_medical_category",
        ).order_by(
            "service_medical_category__order",
            "service_medical_category__name",
            "parent_service__name",
            "name",
        )
        selected_set = frozenset(pool_for_pills)
        by_svc_cat, by_exact = _build_acte_nav_indexes(acte_nav_qs)

        for s in services_for_sidebar:
            p_info = _actes_order_for_service_name(s.name)
            subgroups_out: list[dict] = []
            if p_info:
                # Get all categories from database for this service
                db_categories = {}
                for a in acte_nav_qs.filter(service_medical_category_id=s.pk):
                    cat_title = a.parent_service.name if a.parent_service_id else "Autres"
                    if cat_title not in db_categories:
                        db_categories[cat_title] = []
                    db_categories[cat_title].append(a)
                
                # Process categories in demo order
                for cat_name in p_info["categories"]:
                    rows: list[dict] = []
                    seen_pks: set[int] = set()
                    # First add acts from demo order
                    for act_name in p_info["acts"].get(cat_name, []):
                        act_obj = _resolve_acte_for_nav(
                            s.pk, cat_name, act_name, by_svc_cat, by_exact
                        )
                        pk = act_obj.pk if act_obj else None
                        if pk and pk in seen_pks:
                            continue
                        if pk:
                            seen_pks.add(pk)
                        rows.append(
                            {
                                "pk": pk,
                                "name": act_name,
                                "selected": pk in selected_set if pk else False,
                                "count": int(acte_offer_counts.get(pk, 0))
                                if pk
                                else 0,
                            }
                        )
                    # Then add remaining acts from this category from database
                    cat_norm = _normalize_catalog_label(cat_name)
                    matched_acts = by_svc_cat.get((s.pk, cat_norm), [])
                    for act_obj in matched_acts:
                        if act_obj.pk in seen_pks:
                            continue
                        seen_pks.add(act_obj.pk)
                        rows.append(
                            {
                                "pk": act_obj.pk,
                                "name": act_obj.name,
                                "selected": act_obj.pk in selected_set,
                                "count": int(
                                    acte_offer_counts.get(act_obj.pk, 0)
                                ),
                            }
                        )
                    # Sort rows to match demo order
                    demo_acts = p_info["acts"].get(cat_name, [])
                    def sort_key(row):
                        try:
                            idx = demo_acts.index(row["name"])
                            return (0, idx)
                        except ValueError:
                            return (1, row["name"])
                    rows.sort(key=sort_key)
                    if rows:
                        subgroups_out.append(
                            {
                                "title": cat_name,
                                "rows": rows,
                                "count": sum(r["count"] for r in rows),
                            }
                        )
                # Add categories from database that are not in demo
                for cat_title, acts in db_categories.items():
                    cat_norm = _normalize_catalog_label(cat_title)
                    # Check if this category is already in subgroups_out
                    if any(_normalize_catalog_label(sg["title"]) == cat_norm for sg in subgroups_out):
                        continue
                    rows: list[dict] = []
                    for a in acts:
                        rows.append(
                            {
                                "pk": a.pk,
                                "name": a.name,
                                "selected": a.pk in selected_set,
                                "count": int(acte_offer_counts.get(a.pk, 0)),
                            }
                        )
                    if rows:
                        subgroups_out.append(
                            {
                                "title": cat_title,
                                "rows": rows,
                                "count": sum(r["count"] for r in rows),
                            }
                        )
            else:
                for a in acte_nav_qs.filter(service_medical_category_id=s.pk):
                    cat_title = (
                        a.parent_service.name if a.parent_service_id else "Autres"
                    )
                    sub = next(
                        (g for g in subgroups_out if g["title"] == cat_title),
                        None,
                    )
                    if sub is None:
                        sub = {"title": cat_title, "rows": [], "count": 0}
                        subgroups_out.append(sub)
                    sub["rows"].append(
                        {
                            "pk": a.pk,
                            "name": a.name,
                            "selected": a.pk in selected_set,
                            "count": int(acte_offer_counts.get(a.pk, 0)),
                        }
                    )
                for sub in subgroups_out:
                    sub["count"] = sum(r["count"] for r in sub["rows"])

            # When p_info exists, categories are already in correct order from p_info["categories"]
            # Only sort when p_info is None (fallback to database order)
            if not p_info:
                subgroups_out.sort(key=lambda sg: sg["title"])

            if not subgroups_out:
                continue

            fam_total = sum(sg["count"] for sg in subgroups_out)
            is_fam_open = bool(
                (service_id and str(s.pk) == str(service_id))
                or any(
                    r["selected"]
                    for sg in subgroups_out
                    for r in sg["rows"]
                )
            )
            acte_dem_families.append(
                {
                    "pk": s.pk,
                    "title": s.name,
                    "subgroups": subgroups_out,
                    "count": fam_total,
                    "open": is_fam_open,
                }
            )
        if acte_dem_families and not any(f["open"] for f in acte_dem_families):
            acte_dem_families[0]["open"] = True

        mobile_piliers_json = json.dumps(
            _build_mobile_piliers_payload(acte_offer_counts),
            ensure_ascii=False,
        )
    else:
        mobile_piliers_json = "[]"

    search_dem_ctx_title = ""
    search_dem_ctx_sub = ""
    if show_dem_service_acte_nav:
        search_dem_ctx_title = "Sélectionnez un acte dans le menu ←"
        search_dem_ctx_sub = (
            "Naviguez dans l'arbre à gauche ou utilisez la recherche d'acte."
        )
        if pool_from_request and len(pool_for_pills) > 1:
            search_dem_ctx_title = f"{len(pool_for_pills)} examens sélectionnés"
            search_dem_ctx_sub = (
                "Comparez les offres par examen dans la liste ci-dessous."
            )
        elif acte_id:
            try:
                aid = int(acte_id)
            except (TypeError, ValueError):
                aid = None
            if aid is not None:
                aname = ActeMedical.objects.filter(pk=aid).values_list(
                    "name", flat=True
                ).first()
                if aname:
                    search_dem_ctx_title = aname
                    search_dem_ctx_sub = (
                        "Comparez les offres par prix, délai et localisation."
                    )

    def _dem_attach_catalog_counts(rows):
        if not rows:
            return
        org_ids = list({pa.organisme_id for pa in rows})
        counts = dict(
            PrestataireActe.objects.filter(
                organisme_id__in=org_ids,
                is_available=True,
                organisme__is_active=True,
            )
            .values("organisme_id")
            .annotate(n=Count("acte_id", distinct=True))
            .values_list("organisme_id", "n")
        )
        for pa in rows:
            pa.dem_org_catalog_count = int(counts.get(pa.organisme_id, 0))
            from .opening_hours_display import opening_hours_summary_for_org

            pa.dem_horaires_short = opening_hours_summary_for_org(pa.organisme, max_len=40)

    def _dem_attach_insurance(rows):
        if not rows:
            return
        org_ids = list({pa.organisme_id for pa in rows})
        ins_names_by_org: dict[int, list[str]] = defaultdict(list)
        if org_ids:
            for oid, aname in (
                PriseEnChargeAssurance.objects.filter(
                    organisme_id__in=org_ids,
                    is_active=True,
                )
                .order_by("assurance__name")
                .values_list("organisme_id", "assurance__name")
            ):
                ins_names_by_org[int(oid)].append(aname)
        if not assurance_ids_int:
            for pa in rows:
                pa.dem_insurance_match = True
                pa.dem_insurance_names = ins_names_by_org.get(pa.organisme_id, [])
            return
        mapping = defaultdict(set)
        for oid, aid in PriseEnChargeAssurance.objects.filter(
            organisme_id__in=org_ids,
            assurance_id__in=assurance_ids_int,
            is_active=True,
        ).values_list("organisme_id", "assurance_id"):
            mapping[oid].add(aid)
        want = frozenset(assurance_ids_int)
        for pa in rows:
            pa.dem_insurance_match = bool(mapping.get(pa.organisme_id, set()) & want)
            pa.dem_insurance_names = ins_names_by_org.get(pa.organisme_id, [])

    _attach_distance_km_to_offers(page.object_list, latlng)
    _dem_attach_insurance(list(page.object_list))
    _dem_attach_catalog_counts(list(page.object_list))
    for _blk in acte_results_accordion:
        _dem_attach_insurance(_blk["items"])
        _dem_attach_catalog_counts(_blk["items"])

    mobile_results_by_org: list[dict] = []
    mobile_results_acte_total = len(pool_for_pills) if pool_from_request else 0
    if pool_from_request and page.object_list:
        acte_objs_pool = {
            x.pk: x for x in ActeMedical.objects.filter(pk__in=pool_for_pills)
        }
        by_org: dict[int, dict] = {}
        for pa in page.object_list:
            oid = pa.organisme_id
            if oid not in by_org:
                by_org[oid] = {
                    "org": pa.organisme,
                    "items": [],
                    "matching_acte_ids": set(),
                }
            by_org[oid]["items"].append(pa)
            by_org[oid]["matching_acte_ids"].add(pa.acte_id)

        org_ids = list(by_org.keys())
        ins_names_by_org: dict[int, list[str]] = {}
        if org_ids:
            for oid, aname in (
                PriseEnChargeAssurance.objects.filter(
                    organisme_id__in=org_ids,
                    is_active=True,
                )
                .order_by("assurance__name")
                .values_list("organisme_id", "assurance__name")
            ):
                ins_names_by_org.setdefault(oid, []).append(aname)

        for oid, block in by_org.items():
            org = block["org"]
            matching_count = len(block["matching_acte_ids"])
            missing_actes = [
                acte_objs_pool[aid]
                for aid in pool_for_pills
                if aid not in block["matching_acte_ids"] and aid in acte_objs_pool
            ]
            plan = getattr(org, "subscription_plan", None)
            mobile_results_by_org.append(
                {
                    "org": org,
                    "items": block["items"],
                    "matching_count": matching_count,
                    "total_actes": mobile_results_acte_total,
                    "missing_actes": missing_actes,
                    "insurance_names": ins_names_by_org.get(oid, []),
                    "is_pioneer": bool(
                        plan and getattr(plan, "is_pioneer_offer", False)
                    ),
                }
            )
        mobile_results_by_org.sort(
            key=lambda b: (-b["matching_count"], b["org"].name.lower()),
        )
        from .opening_hours_display import opening_hours_summary_for_org

        for block in mobile_results_by_org:
            block["hours_summary"] = opening_hours_summary_for_org(block["org"], max_len=56)

    dem_assurance_labels = list(
        Assurance.objects.filter(pk__in=assurance_ids_int)
        .order_by("name")
        .values_list("name", flat=True),
    )
    dem_assurance_context_json = json.dumps(
        {"ids": [str(i) for i in assurance_ids_int], "labels": dem_assurance_labels},
        ensure_ascii=False,
    )

    popular_actes_qs = (
        ActeMedical.objects.filter(level=3)
        .annotate(
            struct_count=Count(
                "prestataire_actes__organisme",
                filter=Q(
                    prestataire_actes__is_available=True,
                    prestataire_actes__organisme__is_active=True,
                ),
                distinct=True,
            ),
            offer_count=Count(
                "prestataire_actes",
                filter=Q(
                    prestataire_actes__is_available=True,
                    prestataire_actes__organisme__is_active=True,
                ),
            ),
        )
        .filter(struct_count__gt=0)
        .order_by("-struct_count", "-offer_count", "name")[:12]
    )
    search_popular_actes = [
        {"acte": acte, "struct_count": acte.struct_count} for acte in popular_actes_qs
    ]
    partner_orgs_qs = (
        OrganismeDeSante.objects.filter(
            is_active=True,
            subscription_plan__is_pioneer_offer=True,
        )
        .select_related("type_organisme", "subscription_plan")
        .annotate(
            acte_count=Count(
                "prestataire_actes",
                filter=Q(prestataire_actes__is_available=True),
                distinct=True,
            ),
        )
        .order_by("-profile_views_count", "name")[:8]
    )
    search_partner_structures = [
        {
            "org": org,
            "icon": _search_org_card_icon(org),
            "acte_count": org.acte_count,
        }
        for org in partner_orgs_qs
    ]

    context = {
        "page": page,
        "query": q,
        "results_count": results_count,
        "services": services_for_sidebar,
        "actes_for_pills": actes_for_pills,
        "acte_pills": acte_pills,
        "acte_results_accordion": acte_results_accordion,
        "selected_lot_ids_json": json.dumps(lot_ids_clean),
        "acte_keep_query": acte_keep_query,
        "lot_keep_query": lot_keep_query,
        "pool_for_pills": pool_for_pills,
        "pool_from_request": pool_from_request,
        "actes_for_filter": actes_for_filter[:500],
        "assurances_grouped": assurances_grouped_for_select(),
        "types": TypeOrganisme.objects.all(),
        "regions": Region.objects.all(),
        "current_service": service_id,
        "current_acte": acte_id,
        "current_actes": [str(i) for i in pool_for_pills],
        "presets_json": json.dumps(preset_payload),
        "current_level": level or "",
        "current_assurances": assurance_ids,
        "current_city": city,
        "current_types": type_ids,
        "current_regions": region_ids,
        "current_sort": sort,
        "price_min_val": str(price_min) if price_min is not None else "",
        "price_max_val": str(price_max) if price_max is not None else "",
        "current_lat": str(latlng[0]) if latlng else "",
        "current_lng": str(latlng[1]) if latlng else "",
        "radius_km": radius_km,
        "proximity_on": proximity_on,
        "has_coordinates": latlng is not None,
        "query_string": query_string,
        "saved_lat": saved_lat,
        "saved_lng": saved_lng,
        "global_price_min": price_stats["pmin"],
        "global_price_max": price_stats["pmax"],
        "level_choices": ActeMedical.SERVICE_LEVEL_CHOICES,
        "active_filter_count": active_filter_count,
        "top_cities": top_cities,
        "delai_choices": [c for c in PrestataireActe.DELAI_CHOICES if c[0]],
        "current_delai": delai_filter,
        "current_domicile": domicile_filter,
        "show_dem_service_acte_nav": show_dem_service_acte_nav,
        "service_dem_pills": service_dem_pills,
        "acte_dem_families": acte_dem_families,
        "mobile_piliers_json": mobile_piliers_json,
        "dem_clear_acte_url": dem_clear_acte_url,
        "search_dem_ctx_title": search_dem_ctx_title,
        "search_dem_ctx_sub": search_dem_ctx_sub,
        "dem_assurance_context_json": dem_assurance_context_json,
        "search_hero_stats": {
            "structures": OrganismeDeSante.objects.filter(is_active=True).count(),
            "piliers": ServiceMedical.objects.count(),
            "actes": ActeMedical.objects.filter(level=3).count(),
            "assurances": Assurance.objects.count(),
        },
        "search_popular_actes": search_popular_actes,
        "search_partner_structures": search_partner_structures,
        "mobile_results_by_org": mobile_results_by_org,
        "mobile_results_acte_total": mobile_results_acte_total,
        # Ambulance : IDs des services dont le nom contient "ambulance"
        "ambulance_service_ids_json": json.dumps(
            [str(s.pk) for s in services_for_sidebar if "ambulance" in s.name.lower()]
        ),
        "current_service_name": next(
            (s.name for s in services_for_sidebar if str(s.pk) == str(service_id or "")),
            "",
        ),
        "is_ambulance_service": (
            any("ambulance" in s.name.lower() for s in services_for_sidebar if str(s.pk) == str(service_id or ""))
            or any(k in (q or "").lower() for k in ["ambulance", "ambu", "smur", "rapatriement", "transport"])
        ),
    }
    if show_dem_service_acte_nav:
        from .search_mobile_context import build_search_mobile_app_context

        context.update(build_search_mobile_app_context(request))
    return render(request, "healthcare/search.html", context)


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
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"suggestions": []})

    suggestions = []

    services = ServiceMedical.objects.filter(
        is_active=True, name__icontains=q,
    ).order_by("order")[:4]
    for s in services:
        suggestions.append({
            "label": s.name,
            "type": "famille",
            "url": f"?service={s.pk}&sort=price_asc",
        })

    actes = (
        ActeMedical.objects.filter(is_active=True)
        .filter(Q(name__icontains=q) | Q(code__icontains=q))
        .select_related("service_medical_category")
        .order_by("name")[:8]
    )
    for a in actes:
        suggestions.append({
            "id": a.pk,
            "label": a.name,
            "type": "acte",
            "detail": a.service_medical_category.name,
            "url": f"?acte={a.pk}&sort=price_asc",
        })

    centres = (
        OrganismeDeSante.objects.filter(is_active=True, name__icontains=q)
        .select_related("type_organisme")
        .order_by("name")[:4]
    )
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
def api_geocode(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    return JsonResponse({"results": nominatim_search(q, limit=6)})


@require_GET
def api_reverse(request):
    latlng = parse_lat_lng(request.GET.get("lat"), request.GET.get("lon"))
    if not latlng:
        return JsonResponse({"result": None}, status=400)
    r = nominatim_reverse(latlng[0], latlng[1])
    return JsonResponse({"result": r})


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
@require_POST
def save_search_location(request):
    """Enregistre la position de recherche (session + profil patient)."""
    from users.models import PatientProfile

    latlng = parse_lat_lng(request.POST.get("lat"), request.POST.get("lng"))
    if not latlng:
        if request.POST.get("ajax") == "1":
            return JsonResponse({"ok": False, "error": "Position invalide."}, status=400)
        messages.error(request, "Position invalide.")
        return redirect("healthcare:search")
    request.session["search_lat"] = str(latlng[0])
    request.session["search_lng"] = str(latlng[1])
    if request.user.is_patient:
        prof, _ = PatientProfile.objects.get_or_create(user=request.user)
        prof.last_known_latitude = latlng[0]
        prof.last_known_longitude = latlng[1]
        prof.save(update_fields=["last_known_latitude", "last_known_longitude"])
        msg = "Votre position a été enregistrée pour les prochaines recherches."
        messages.success(request, msg)
    else:
        msg = "Position mémorisée pour cette session."
        messages.success(request, msg)
    if request.POST.get("ajax") == "1":
        return JsonResponse({"ok": True, "message": msg})
    nxt = request.POST.get("next")
    if nxt and nxt.startswith("/"):
        return redirect(nxt)
    return redirect("healthcare:search")


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

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favoris.objects.filter(patient=request.user, organisme=org).exists()

    org.refresh_from_db()

    context = {
        "org": org,
        "wa_general_url": wa_general_url,
        "insurances": insurances,
        "insurances_profil": build_insurances_profil(insurances),
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

    from .organisme_fiche import build_insurances_profil, fiche_context_for_org
    fiche_ctx = fiche_context_for_org(org, actes, hours_list, request)

    assurance_ids_int: list[int] = []
    for x in request.GET.getlist("assurance"):
        try:
            assurance_ids_int.append(int(x))
        except (TypeError, ValueError):
            continue
    patient_insurance_names = list(
        Assurance.objects.filter(pk__in=assurance_ids_int)
        .order_by("name")
        .values_list("name", flat=True),
    )
    org_insurance_names = {
        pec.assurance.name for pec in insurances
    }
    patient_match_names = [
        n for n in patient_insurance_names if n in org_insurance_names
    ]
    insurances_profil = build_insurances_profil(insurances)
    patient_match_set = set(patient_match_names)
    for row in insurances_profil:
        row["patient_match"] = row["name"] in patient_match_set

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favoris.objects.filter(patient=request.user, organisme=org).exists()

    context = {
        "org": org,
        "actes": actes,
        "insurances": insurances,
        "insurances_profil": insurances_profil,
        "patient_insurance_match": patient_match_names[0] if patient_match_names else "",
        "is_favorite": is_favorite,
        "hours_list": hours_list,
        **fiche_ctx,
    }

    return render(request, "healthcare/partials/organisme_profil_drawer.html", context)


def service_detail(request, slug):
    service = get_object_or_404(ServiceMedical, slug=slug, is_active=True)

    search_query = request.GET.get('search', '').strip()
    actes_qs = ActeMedical.objects.filter(
        service_medical_category=service, is_active=True,
    ).select_related("parent_service")

    if search_query:
        actes_qs = actes_qs.filter(name__icontains=search_query)

    actes = actes_qs.order_by("level", "name")

    providers = OrganismeDeSante.objects.filter(
        prestataire_actes__acte__service_medical_category=service,
        is_active=True,
    ).distinct().select_related("type_organisme")[:20]

    context = {"service": service, "actes": actes, "providers": providers, "search_query": search_query}
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
    raw_oh = org.opening_hours
    if isinstance(raw_oh, str):
        raw_oh = None
    hours_ok = bool(raw_oh) and any(
        bool(v) for v in (raw_oh or {}).values()
    )
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

    from cart.models import Cart, CartItem, DevisPart
    from messaging.models import Message

    actes_count = PrestataireActe.objects.filter(organisme=org).count()
    insurances_count = PriseEnChargeAssurance.objects.filter(organisme=org).count()
    from healthcare.prestataire_analytics import (
        build_activity_chart,
        medplaque_stats,
        recent_visits,
    )

    visit_source_filter = (request.GET.get("visit_src") or "all").strip()
    recent_views = recent_visits(org, limit=8, source=visit_source_filter)
    accepted_insurances = list(
        PriseEnChargeAssurance.objects.filter(organisme=org, is_active=True)
        .select_related("assurance")
        .order_by("assurance__name")[:6]
    )

    views_qs = ProfileView.objects.filter(organisme=org)
    if since:
        views_qs = views_qs.filter(viewed_at__gte=since)
    views_period = views_qs.count()

    # Items du panier qui touchent cet organisme (proxy de "demandes" en attendant
    # un vrai modèle Reservation — Sprint 5).
    items_qs = CartItem.objects.filter(prestataire_acte__organisme=org)
    if since:
        items_qs = items_qs.filter(added_at__gte=since)
    items_period = items_qs.count()

    # Sous-devis (parts) pour cette structure — statut envoyé / consulté.
    devis_part_qs = DevisPart.objects.filter(
        organisme=org,
        status__in=["sent", "viewed", "relanced"],
    ).exclude(devis__status="draft")
    if since:
        devis_part_qs = devis_part_qs.filter(created_at__gte=since)
    devis_period = devis_part_qs.count()
    devis_value = (
        devis_part_qs.aggregate(v=Sum("total_brut"))["v"] or 0
    )

    # Top 5 actes (par nombre d'apparitions dans les paniers sur la période).
    top_actes_rows = (
        items_qs.values("prestataire_acte__acte__name", "prestataire_acte__price")
        .annotate(n=Count("id"))
        .order_by("-n", "prestataire_acte__acte__name")[:5]
    )
    top_actes_max = max((r["n"] for r in top_actes_rows), default=0)

    # Répartition assurance (sur les paniers récents touchant cet organisme).
    insurance_split_rows = (
        Cart.objects.filter(
            items__prestataire_acte__organisme=org,
            **({"updated_at__gte": since} if since else {}),
        )
        .values("selected_insurance__name")
        .annotate(n=Count("id", distinct=True))
        .order_by("-n")[:5]
    )
    insurance_split = []
    insurance_total = sum(r["n"] for r in insurance_split_rows) or 0
    for row in insurance_split_rows:
        insurance_split.append(
            {
                "name": row["selected_insurance__name"] or "Sans assurance",
                "count": row["n"],
                "pct": round((row["n"] * 100.0 / insurance_total)) if insurance_total else 0,
            }
        )

    # Complétion profil
    completion = _dashboard_completion(org, actes_count, insurances_count)
    completion_done = sum(1 for c in completion if c["ok"])
    completion_pct = int(round(completion_done * 100.0 / max(len(completion), 1)))

    # Alerte : sous-devis « envoyés » non consultés par la structure (>24h).
    pending_devis = DevisPart.objects.filter(
        organisme=org,
        status="sent",
        created_at__lte=timezone.now() - timezone.timedelta(hours=24),
    ).exclude(devis__status="draft").count()
    # Badge sidebar : parts en attente de consultation par la structure
    new_devis_count = DevisPart.objects.filter(
        organisme=org,
        status="sent",
    ).exclude(devis__status="draft").count()

    # RDV : demandes à confirmer + RDV confirmés à venir
    from appointments.models import RendezVous

    rdv_requested_count = RendezVous.objects.filter(
        organisme=org, status=RendezVous.STATUS_REQUESTED
    ).count()
    rdv_upcoming_count = RendezVous.objects.filter(
        organisme=org,
        status=RendezVous.STATUS_CONFIRMED,
        start__gte=timezone.now(),
    ).count()

    unread = Message.objects.filter(receiver=request.user, is_read=False).count()
    pending_subscription_request = SubscriptionChangeRequest.objects.filter(
        organisme=org, status="pending"
    ).first()

    activity_chart = build_activity_chart(org, period_key)
    medplaque = medplaque_stats(org, since=since)

    context = {
        "org": org,
        "actes_count": actes_count,
        "insurances_count": insurances_count,
        "profile_views_total": org.profile_views_count,
        "recent_views": recent_views,
        "unread_messages": unread,
        "dash_active": "home",
        # Sprint 3
        "period_key": period_key,
        "period_label": period_label,
        "views_period": views_period,
        "devis_period": devis_period,
        "devis_value": devis_value,
        "items_period": items_period,
        "top_actes_rows": list(top_actes_rows),
        "top_actes_max": top_actes_max,
        "insurance_split": insurance_split,
        "insurance_split_total": insurance_total,
        "completion": completion,
        "completion_done": completion_done,
        "completion_total": len(completion),
        "completion_pct": completion_pct,
        "pending_devis": pending_devis,
        "new_devis_count": new_devis_count,
        "new_rdv_count": rdv_requested_count,
        "rdv_requested_count": rdv_requested_count,
        "rdv_upcoming_count": rdv_upcoming_count,
        "accepted_insurances_preview": accepted_insurances,
        "pending_subscription_request": pending_subscription_request,
        "activity_chart": activity_chart,
        "medplaque": medplaque,
        "visit_source_filter": visit_source_filter,
    }
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
            messages.success(request, "Profil mis à jour.")
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
                "icon": svc.display_icon if svc else "🏥",
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

    maps_url = ""
    if org.latitude and org.longitude:
        lat = format(org.latitude, "f").rstrip("0").rstrip(".")
        lng = format(org.longitude, "f").rstrip("0").rstrip(".")
        maps_url = (
            f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
        )
    elif org.address:
        from urllib.parse import quote

        maps_url = (
            "https://www.google.com/maps/search/?api=1&query="
            + quote(f"{org.address} {org.city}")
        )

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


@_require_prestataire
def actes_list(request):
    """
    Catalogue actes — parcours simplifié type démo : cases par pilier (segmentation),
    champ libre « Tarifs & délais », puis tableau récap (filtres) et saisie avancée.
    """
    from django.db import transaction

    ctx = _dash_context(request, "actes")
    org = OrganismeDeSante.objects.get(pk=ctx["org"].pk)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_domicile":
            from healthcare.prestataire_domicile import handle_domicile_post

            resp = handle_domicile_post(request, org)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return resp
            payload = json.loads(resp.content)
            messages.success(request, payload.get("message") or "Prestations à domicile enregistrées.")
            return redirect("healthcare:actes_list")

        if action == "save_catalogue":
            selectable = set(_prestataire_leaf_actes_queryset().values_list("pk", flat=True))
            selected: set[int] = set()
            for x in request.POST.getlist("acte_ids"):
                try:
                    selected.add(int(x))
                except (TypeError, ValueError):
                    continue
            selected &= selectable
            org.catalogue_tarifs_delais = (request.POST.get("catalogue_tarifs_delais") or "").strip()
            org.save(update_fields=["catalogue_tarifs_delais", "updated_at"])
            with transaction.atomic():
                existing = {
                    pa.acte_id: pa
                    for pa in PrestataireActe.objects.select_for_update().filter(organisme=org)
                }
                need_ids = set(existing.keys()) | selected
                acte_ref = {
                    a.pk: a
                    for a in ActeMedical.objects.filter(pk__in=need_ids)
                }
                for aid, pa in existing.items():
                    want = aid in selected
                    new_price = _catalog_price_from_post(request.POST, aid, pa.price)
                    new_delai = _catalog_delai_from_post(request.POST, aid, pa.delai)
                    pa.price = new_price
                    pa.delai = new_delai
                    pa.is_available = want
                    pa.save(
                        update_fields=["price", "delai", "is_available", "updated_at"]
                    )
                for aid in selected:
                    if aid in existing:
                        continue
                    acte = acte_ref.get(aid)
                    if acte is None:
                        acte = ActeMedical.objects.get(pk=aid)
                    ref = (
                        acte.reference_price
                        if acte.reference_price is not None
                        else Decimal("0")
                    )
                    price = _catalog_price_from_post(request.POST, aid, ref)
                    delai = _catalog_delai_from_post(request.POST, aid, "")
                    PrestataireActe.objects.create(
                        organisme=org,
                        acte=acte,
                        price=price,
                        delai=delai,
                        is_available=True,
                    )
            messages.success(request, "Votre offre d’actes et le texte Tarifs & délais ont été enregistrés.")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": True})
            return redirect("healthcare:actes_list")

    selected_acte_ids = set(
        PrestataireActe.objects.filter(
            organisme=org, is_available=True,
        ).values_list("acte_id", flat=True)
    )

    pa_lookup = {
        pa.acte_id: pa
        for pa in PrestataireActe.objects.filter(organisme=org)
    }
    from healthcare.prestataire_catalogue import (
        applicable_pilier_slugs,
        merge_catalog_blocks,
        prep_display_for_acte,
        prep_panel_payload,
        type_structure_context,
    )

    catalog_raw = _prestataire_leaf_actes_catalog_by_pilier()
    catalog_by_pilier = merge_catalog_blocks(catalog_raw, org)
    type_ctx = type_structure_context(org)
    for block in catalog_by_pilier:
        for sg in block.get("subgroups") or []:
            rows = []
            for acte in sg["actes"]:
                pa = pa_lookup.get(acte.pk)
                ref = (
                    acte.reference_price
                    if acte.reference_price is not None
                    else Decimal("0")
                )
                price_val = pa.price if pa is not None else ref
                delai_val = (pa.delai if pa is not None else "") or ""
                rows.append(
                    {
                        "acte": acte,
                        "pa": pa,
                        "price_val": price_val,
                        "delai_val": delai_val,
                        "prep": prep_display_for_acte(acte, pa),
                    }
                )
            sg["rows"] = rows

    prep_data = {}
    for block in catalog_by_pilier:
        pilier_name = block["pilier"].name
        pilier_slug = block["pilier"].slug
        for sg in block.get("subgroups") or []:
            for row in sg.get("rows") or []:
                acte = row["acte"]
                prep_data[str(acte.pk)] = prep_panel_payload(
                    acte,
                    sg["label"],
                    pilier_name,
                    row.get("pa"),
                    org=org,
                    pilier_slug=pilier_slug,
                )

    first_applicable_pilier_id = next(
        (b["pilier"].pk for b in catalog_by_pilier if b.get("applicable")),
        None,
    )
    first_applicable_pilier_slug = next(
        (b["pilier"].slug for b in catalog_by_pilier if b.get("applicable")),
        "",
    )

    from healthcare.prestataire_domicile import (
        DOMICILE_DELAI_CHOICES,
        domicile_all_actes_active,
        domicile_subgroups_from_catalog,
        domicile_zones_queryset,
        show_domicile_block,
    )

    from healthcare.forms import PrestataireActeForm
    add_form = PrestataireActeForm(organisme=org)

    applicable_slugs_raw = applicable_pilier_slugs(org)
    domicile_subgroups, domicile_all_acte_ids = domicile_subgroups_from_catalog(catalog_by_pilier)
    ctx.update(
        {
            "org": org,
            "add_form": add_form,
            **_presta_acte_form_ui(add_form.fields["acte"].queryset),
            "catalog_by_pilier": catalog_by_pilier,
            "selected_acte_ids": selected_acte_ids,
            "prestataire_delai_choices": PrestataireActe.DELAI_CHOICES,
            "total_count": PrestataireActe.objects.filter(organisme=org, is_available=True).count(),
            "first_applicable_pilier_id": first_applicable_pilier_id,
            "first_applicable_pilier_slug": first_applicable_pilier_slug,
            "show_domicile_block": show_domicile_block(org, applicable_slugs_raw),
            "domicile_zones": domicile_zones_queryset(org),
            "domicile_subgroups": domicile_subgroups,
            "domicile_all_acte_ids": domicile_all_acte_ids,
            "domicile_all_active": domicile_all_actes_active(
                domicile_all_acte_ids, set(selected_acte_ids)
            ),
            "domicile_delai_choices": DOMICILE_DELAI_CHOICES,
            "prep_data": prep_data,
            "prep_save_url_tpl": reverse(
                "healthcare:prestataire_acte_prerequisites", args=[0]
            ).replace("/0/", "/ACTE_ID/"),
            "reminder_add_url_tpl": reverse(
                "healthcare:prestataire_acte_reminder_add", args=[999]
            ).replace("999", "ACTE_ID"),
            "reminder_delete_url_tpl": reverse(
                "healthcare:prestataire_acte_reminder_delete", args=[999, 888]
            ).replace("999", "ACTE_ID").replace("888", "SCHEDULE_PK"),
            **type_ctx,
        }
    )
    return render(request, "healthcare/prestataire/actes_list.html", ctx)


@_require_prestataire
@require_POST
def prestataire_acte_prerequisites(request, acte_id):
    """Enregistre consignes / prérequis RDV pour un acte du catalogue structure."""
    from healthcare.forms import PrestataireActePrerequisitesForm

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    acte = get_object_or_404(
        ActeMedical.objects.filter(level=3, is_active=True),
        pk=acte_id,
    )
    pa = PrestataireActe.objects.filter(organisme=org, acte=acte).first()
    if pa is None:
        ref = acte.reference_price if acte.reference_price is not None else Decimal("0")
        pa = PrestataireActe.objects.create(
            organisme=org,
            acte=acte,
            price=ref,
            delai="",
            is_available=False,
        )
    form = PrestataireActePrerequisitesForm(request.POST, instance=pa)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if form.is_valid():
        obj = form.save(commit=False)
        obj.rdv_prerequisites_active = request.POST.get("rdv_prerequisites_active") == "1"
        obj.save()
        message = (obj.rdv_prerequisites or "").strip() or (acte.rdv_prerequisites or "").strip()
        configured = bool((obj.rdv_prerequisites or "").strip()) or (
            obj.rdv_prerequisites_active and bool((acte.rdv_prerequisites or "").strip())
        )
        if is_ajax:
            return JsonResponse(
                {
                    "ok": True,
                    "configured": configured and bool(message),
                    "active": obj.rdv_prerequisites_active,
                    "message": obj.rdv_prerequisites or "",
                }
            )
        messages.success(request, f"Consignes enregistrées pour « {acte.name} ».")
    else:
        if is_ajax:
            return JsonResponse({"ok": False, "error": "Données invalides."}, status=400)
        messages.error(request, "Impossible d'enregistrer les consignes.")
    next_url = request.POST.get("next") or reverse("healthcare:actes_list")
    return redirect(next_url)


@_require_prestataire
@require_POST
def prestataire_acte_reminder_add(request, acte_id):
    """Ajoute un rappel H-N pour un acte (panneau préparation catalogue)."""
    from healthcare.prestataire_prep_reminders import add_hourly_reminder, reminders_for_acte

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    acte = get_object_or_404(
        ActeMedical.objects.filter(level=3, is_active=True),
        pk=acte_id,
    )
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    try:
        hours = int(request.POST.get("hours", ""))
    except (TypeError, ValueError):
        hours = 0
    _, err = add_hourly_reminder(org, acte, hours)
    if err:
        if is_ajax:
            return JsonResponse({"ok": False, "error": err}, status=400)
        messages.error(request, err)
        return redirect(reverse("healthcare:actes_list"))
    if is_ajax:
        return JsonResponse(
            {
                "ok": True,
                "reminders": reminders_for_acte(org, acte.pk),
            }
        )
    messages.success(request, f"Rappel H-{hours} ajouté pour « {acte.name} ».")
    return redirect(reverse("healthcare:actes_list"))


@_require_prestataire
@require_POST
def prestataire_acte_reminder_delete(request, acte_id, pk):
    """Supprime un rappel lié à un acte (panneau préparation catalogue)."""
    from healthcare.prestataire_prep_reminders import delete_acte_reminder, reminders_for_acte

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    acte = get_object_or_404(
        ActeMedical.objects.filter(level=3, is_active=True),
        pk=acte_id,
    )
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not delete_acte_reminder(org, acte.pk, pk):
        if is_ajax:
            return JsonResponse({"ok": False, "error": "Rappel introuvable."}, status=404)
        messages.error(request, "Rappel introuvable.")
        return redirect(reverse("healthcare:actes_list"))
    if is_ajax:
        return JsonResponse(
            {
                "ok": True,
                "reminders": reminders_for_acte(org, acte.pk),
            }
        )
    messages.success(request, "Rappel supprimé.")
    return redirect(reverse("healthcare:actes_list"))


@_require_prestataire
def prestataire_rdv_reminder_list(request):
    from appointments.models import RdvReminderSchedule
    from django.db.models import Count

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    schedules = (
        RdvReminderSchedule.objects.filter(organisme=org)
        .prefetch_related("actes")
        .annotate(sent_count=Count("sent_logs"))
        .order_by("order", "-offset_value")
    )
    ctx = _dash_context(request, "actes")
    ctx.update({"schedules": schedules, "org": org})
    return render(request, "healthcare/prestataire/rdv_reminder_schedules_list.html", ctx)


@_require_prestataire
def prestataire_rdv_reminder_create(request):
    from appointments.models import RdvReminderSchedule
    from healthcare.forms import PrestataireRdvReminderScheduleForm

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    if request.method == "POST":
        form = PrestataireRdvReminderScheduleForm(request.POST, organisme=org)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.organisme = org
            obj.save()
            form.save_m2m()
            messages.success(request, "Règle de rappel créée.")
            return redirect("healthcare:prestataire_rdv_reminder_list")
    else:
        form = PrestataireRdvReminderScheduleForm(organisme=org)
    ctx = _dash_context(request, "actes")
    ctx.update({"form": form, "title": "Nouvelle règle de rappel RDV", "org": org})
    return render(request, "healthcare/prestataire/rdv_reminder_schedule_form.html", ctx)


@_require_prestataire
def prestataire_rdv_reminder_edit(request, pk):
    from appointments.models import RdvReminderSchedule
    from healthcare.forms import PrestataireRdvReminderScheduleForm

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    schedule = get_object_or_404(RdvReminderSchedule, pk=pk, organisme=org)
    if request.method == "POST":
        form = PrestataireRdvReminderScheduleForm(
            request.POST, instance=schedule, organisme=org
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Règle de rappel mise à jour.")
            return redirect("healthcare:prestataire_rdv_reminder_list")
    else:
        form = PrestataireRdvReminderScheduleForm(instance=schedule, organisme=org)
    ctx = _dash_context(request, "actes")
    ctx.update(
        {
            "form": form,
            "title": f"Modifier : {schedule.label}",
            "object": schedule,
            "org": org,
        }
    )
    return render(request, "healthcare/prestataire/rdv_reminder_schedule_form.html", ctx)


@_require_prestataire
@require_POST
def prestataire_rdv_reminder_delete(request, pk):
    from appointments.models import RdvReminderSchedule

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    schedule = get_object_or_404(RdvReminderSchedule, pk=pk, organisme=org)
    schedule.delete()
    messages.success(request, "Règle supprimée.")
    return redirect("healthcare:prestataire_rdv_reminder_list")


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
    from django.db import transaction

    ctx = _dash_context(request, "insurances")
    org = OrganismeDeSante.objects.get(pk=ctx["org"].pk)

    if request.method == "POST" and request.POST.get("action") == "save_assurances":
        valid = set(Assurance.objects.filter(is_active=True).values_list("pk", flat=True))
        selected: set[int] = set()
        for x in request.POST.getlist("assurance_ids"):
            try:
                selected.add(int(x))
            except (TypeError, ValueError):
                continue
        selected &= valid
        org.assurances_tarifs_delais = (request.POST.get("assurances_tarifs_delais") or "").strip()
        org.save(update_fields=["assurances_tarifs_delais", "updated_at"])
        with transaction.atomic():
            current_ids = set(
                PriseEnChargeAssurance.objects.filter(organisme=org).values_list(
                    "assurance_id", flat=True
                )
            )
            for aid in current_ids - selected:
                PriseEnChargeAssurance.objects.filter(
                    organisme=org, assurance_id=aid
                ).delete()
            for aid in selected - current_ids:
                PriseEnChargeAssurance.objects.get_or_create(
                    organisme=org,
                    assurance_id=aid,
                    defaults={"is_active": True},
                )
        messages.success(request, "Assurances acceptées et texte Tarifs & délais enregistrés.")
        return redirect("healthcare:insurances_manage")

    prises_qs = PriseEnChargeAssurance.objects.filter(organisme=org).select_related(
        "assurance"
    )
    selected_assurance_ids = set(
        PriseEnChargeAssurance.objects.filter(organisme=org).values_list(
            "assurance_id", flat=True
        )
    )

    q = (request.GET.get("q") or "").strip()
    seg_filter = (request.GET.get("segment") or "").strip()
    if q:
        prises_qs = prises_qs.filter(
            Q(assurance__name__icontains=q) | Q(assurance__description__icontains=q)
        )
    if seg_filter in dict(Assurance.Segment.choices):
        prises_qs = prises_qs.filter(assurance__segment=seg_filter)
    prises = list(prises_qs.order_by("assurance__segment", "assurance__name"))

    from .insurance_icons import (
        block_hint_for_assurance_segment,
        chip_label_for_assurance_segment,
        filter_icon_for_assurance_segment,
        filter_label_for_assurance_segment,
        icon_for_assurance_segment,
    )

    recap_seg_rows = []
    for seg, lbl in Assurance.Segment.choices:
        n = PriseEnChargeAssurance.objects.filter(
            organisme=org, assurance__segment=seg
        ).count()
        if n:
            recap_seg_rows.append(
                {
                    "segment": seg,
                    "label": lbl,
                    "chip_label": chip_label_for_assurance_segment(seg, lbl),
                    "icon": icon_for_assurance_segment(seg),
                    "n": n,
                }
            )

    by_seg = defaultdict(list)
    all_active = list(Assurance.objects.filter(is_active=True).order_by("segment", "name"))
    for a in all_active:
        by_seg[a.segment].append(a)
    seg_labels = dict(Assurance.Segment.choices)

    segment_blocks = []
    for seg, long_lbl in Assurance.Segment.choices:
        if seg not in by_seg:
            continue
        icon = icon_for_assurance_segment(seg)
        chip_lbl = chip_label_for_assurance_segment(seg, seg_labels.get(seg, seg))
        block_hint = block_hint_for_assurance_segment(seg)
        lst = by_seg[seg]
        n_sel = sum(1 for x in lst if x.pk in selected_assurance_ids)
        segment_blocks.append(
            {
                "segment": seg,
                "chip_icon": icon,
                "filter_icon": filter_icon_for_assurance_segment(seg),
                "chip_label": chip_lbl,
                "filter_label": filter_label_for_assurance_segment(seg, chip_lbl),
                "block_title": long_lbl,
                "block_hint": block_hint,
                "assurances": lst,
                "n_selected": n_sel,
                "n_total": len(lst),
            }
        )

    ctx.update(
        {
            "org": org,
            "prises": prises,
            "segment_blocks": segment_blocks,
            "insurance_catalog_total": len(all_active),
            "insurance_selected_count": len(selected_assurance_ids),
            "selected_assurance_ids": selected_assurance_ids,
            "q": q,
            "seg_filter": seg_filter,
            "recap_seg_rows": recap_seg_rows,
        }
    )
    return render(request, "healthcare/prestataire/insurances.html", ctx)


@_require_prestataire
def insurance_delete(request, pk):
    org = get_object_or_404(OrganismeDeSante, user=request.user)
    pec = get_object_or_404(PriseEnChargeAssurance, pk=pk, organisme=org)
    pec.delete()
    messages.success(request, "Assurance retirée.")
    return redirect("healthcare:insurances_manage")
