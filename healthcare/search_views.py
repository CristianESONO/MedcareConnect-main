from collections import defaultdict
from decimal import Decimal, InvalidOperation
import json
import logging
import unicodedata
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import ensure_csrf_cookie

from healthcare.services import PricingService, SearchService

from .geo import haversine_km, parse_lat_lng, parse_radius_km
from .models import (
    ActeMedical,
    Assurance,
    LotExamenPrefait,
    OrganismeDeSante,
    PrestataireActe,
    PriseEnChargeAssurance,
    Region,
    SearchHistory,
    ServiceMedical,
    TypeOrganisme,
)
from .utils import assurances_grouped_for_select

logger = logging.getLogger(__name__)

RECOMMENDED_BILAN_ACTS = {
    "general": (
        "NFS / Hémogramme",
        "Glycémie à jeun",
        "Bilan lipidique (EAL)",
        "Créatininémie",
    ),
    "prenup": (
        "Groupe ABO/Rhésus",
        "Électrophorèse de l'hémoglobine",
        "VIH Ag/Ac",
        "HBsAg",
        "Anti-VHC",
    ),
    "pregnancy": (
        "Échographie obstétricale T1",
        "Toxoplasmose IgG/IgM",
        "Rubéole IgG/IgM",
        "Échographie morphologique T2",
        "Échographie T3 (biométrie)",
    ),
    "oms": (
        "Glycémie à jeun",
        "HbA1c",
        "ECG standard 12 dérivations",
        "VIH Ag/Ac",
        "Syphilis VDRL",
    ),
}

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
        # Tri-tarifs : tri côté serveur par tarif conventionné (spec §7)
        "price_ipm_asc",
        "price_ipm_desc",
        "price_assurance_asc",
        "price_assurance_desc",
    }
)

def _annotate_delai_sort(qs):
    """Annotation pour trier les offres par délai indicatif (`PrestataireActe.DELAI_RANK`)."""
    return SearchService.annotate_delai_sort(qs)

def _attach_distance_km_to_offers(offers, latlng):
    """Distance GPS → structure (km) pour affichage / tri panneau « Complétez »."""
    SearchService.attach_distance_km_to_offers(offers, latlng)

def _parse_int_list(values):
    return SearchService.parse_int_list(values)

def _acte_ids_from_lot_params(lot_ids: list[int]) -> list[int]:
    return SearchService.acte_ids_from_lot_params(lot_ids)

def _is_all_zones_ambulance(organisme) -> bool:
    """Détecte si une structure est une ambulance / SMUR couvrant toutes zones."""
    return SearchService.is_all_zones_ambulance(organisme)

def _search_querydict_for_links(request_get):
    """Paramètres GET pour préserver liens de pagination (sans page)."""
    p = request_get.copy()
    if "page" in p:
        del p["page"]
    return p.urlencode()

def _search_url_with_query(query_string: str) -> str:
    """URL /healthcare/search/ sans « ? » final si aucun paramètre."""
    base = reverse("healthcare:search")
    qs = (query_string or "").strip()
    return base + (f"?{qs}" if qs else "")

def _normalize_recommended_act_name(name: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", name.casefold())
        if unicodedata.category(char) != "Mn" and char.isalnum()
    )

def _recommended_bilan_acte_ids(bilan_key: str) -> tuple[list[int], list[str]]:
    expected_names = RECOMMENDED_BILAN_ACTS.get(bilan_key)
    if expected_names is None:
        return [], []

    normalized_names = {
        _normalize_recommended_act_name(name): name for name in expected_names
    }
    acts_by_name: dict[str, list[ActeMedical]] = defaultdict(list)
    for acte in ActeMedical.objects.filter(is_active=True, level=3).order_by("pk"):
        normalized_name = _normalize_recommended_act_name(acte.name)
        if normalized_name in normalized_names:
            acts_by_name[normalized_name].append(acte)

    candidate_ids = [
        acte.pk for actes in acts_by_name.values() for acte in actes
    ]
    offer_counts = dict(
        PrestataireActe.objects.filter(
            acte_id__in=candidate_ids,
            is_available=True,
            organisme__is_active=True,
            price__gt=0,
        )
        .values("acte_id")
        .annotate(total=Count("pk"))
        .values_list("acte_id", "total")
    )

    acte_ids = []
    missing_names = []
    for normalized_name, name in normalized_names.items():
        candidates = acts_by_name.get(normalized_name, [])
        if not candidates:
            missing_names.append(name)
            continue
        selected = max(
            candidates,
            key=lambda acte: (offer_counts.get(acte.pk, 0), -acte.pk),
        )
        acte_ids.append(selected.pk)
    return list(dict.fromkeys(acte_ids)), missing_names

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
        return mark_safe('<i class="ti ti-flask"></i>')
    if any(k in blob for k in ("imag", "radio", "scanner", "irm", "écho", "echo")):
        return mark_safe('<i class="ti ti-scan"></i>')
    if any(k in blob for k in ("cardio", "explor", "efr", "ecg")):
        return mark_safe('<i class="ti ti-activity"></i>')
    if "ambulanc" in blob:
        return mark_safe('<i class="ti ti-ambulance"></i>')
    if "dent" in blob:
        return mark_safe('<i class="ti ti-dental"></i>')
    if any(k in blob for k in ("kiné", "kine", "soin")):
        return mark_safe('<i class="ti ti-stethoscope"></i>')
    return mark_safe('<i class="ti ti-building-hospital"></i>')

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
    bilan_key = (request.GET.get("bilan") or "").strip()
    if bilan_key in RECOMMENDED_BILAN_ACTS:
        recommended_acte_ids, missing_bilan_names = _recommended_bilan_acte_ids(
            bilan_key
        )
        if missing_bilan_names:
            logger.warning(
                "Recommended health bundle contains acts missing from the catalogue",
                extra={
                    "bilan_key": bilan_key,
                    "act_names": missing_bilan_names,
                },
            )
            messages.warning(
                request,
                "Certains actes de ce bilan ne sont pas encore disponibles dans le catalogue.",
            )
        params = request.GET.copy()
        params.pop("bilan", None)
        params.pop("page", None)
        params.pop("q", None)
        params.setlist(
            "acte",
            [
                str(acte_id)
                for acte_id in dict.fromkeys(
                    [*acte_ids_clean, *recommended_acte_ids]
                )
            ],
        )
        return redirect(_search_url_with_query(params.urlencode()))
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
    cities = [c.strip() for c in request.GET.getlist("city") if c.strip()]
    city = cities[0] if cities else ""
    type_ids = [v for v in request.GET.getlist("type") if v]
    region_ids = [v for v in request.GET.getlist("region") if v]
    sort = request.GET.get("sort", "price_asc")
    if sort not in _SEARCH_SORT_CHOICES:
        sort = "price_asc"
    radius_km = parse_radius_km(request.GET.get("radius_km"), default=30.0)
    price_min = _parse_decimal_param(request.GET.get("price_min"))
    price_max = _parse_decimal_param(request.GET.get("price_max"))
    valid_delais = {k for k, _ in PrestataireActe.DELAI_CHOICES if k}
    delai_candidates = [d.strip() for d in request.GET.getlist("delai") if d.strip() in valid_delais]
    delai_filter = delai_candidates[0] if delai_candidates else ""
    domicile_filter = request.GET.get("domicile") == "1"

    regime_filter = (request.GET.get("regime") or "comptant").lower().strip()
    if regime_filter not in ("comptant", "ipm", "assurance"):
        regime_filter = "comptant"

    # Profil patient connecté (utilisé pour les badges d'assurance compatible et la géolocalisation)
    # NOTE: On n'injecte PAS silencieusement l'assurance ou la ville du profil dans les filtres
    # de requête actifs sans action explicite de l'utilisateur, car cela réduirait à 0 résultat
    # le catalogue complet (0 structure pour les actes non couverts par son assurance ou hors quartier).
    patient_profile = None
    if request.user.is_authenticated and getattr(request.user, "is_patient", False):
        patient_profile = getattr(request.user, "patient_profile", None)

    assurance_implicit = False

    if request.GET.get("clear_geo"):
        request.session.pop("search_lat", None)
        request.session.pop("search_lng", None)

    latlng = parse_lat_lng(request.GET.get("lat"), request.GET.get("lng"))
    geo_from_get = latlng is not None and not request.GET.get("clear_geo")

    if latlng is None and not request.GET.get("clear_geo"):
        latlng = parse_lat_lng(request.session.get("search_lat"), request.session.get("search_lng"))

    if latlng is None and not request.GET.get("clear_geo") and patient_profile:
        if patient_profile.last_known_latitude and patient_profile.last_known_longitude:
            try:
                latlng = (float(patient_profile.last_known_latitude), float(patient_profile.last_known_longitude))
            except (ValueError, TypeError):
                pass

    if geo_from_get and latlng:
        request.session["search_lat"] = str(latlng[0])
        request.session["search_lng"] = str(latlng[1])

    proximity_on = request.GET.get("proximity") == "1" and latlng is not None

    pa_qs = SearchService.build_base_queryset()

    q_filter = None
    if q:
        q_filter, equiv_acte_ids = SearchService.build_search_text_filter(q)
        if q_filter:
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

    def _apply_level_price_location_filters(qs, apply_city=True):
        return SearchService.apply_level_price_location_filters(
            qs,
            level=level,
            regime_filter=regime_filter,
            price_min=price_min,
            price_max=price_max,
            assurance_ids=assurance_ids_int,
            city=city,
            apply_city=apply_city,
            type_ids=type_ids,
            region_ids=region_ids,
            delai_filter=delai_filter,
            domicile_filter=domicile_filter,
        )

    pa_qs_before_zone = _apply_level_price_location_filters(pa_qs, apply_city=False)
    pa_qs = _apply_level_price_location_filters(pa_qs, apply_city=True)
    pa_qs_before_acte = _apply_level_price_location_filters(pa_qs_before_acte, apply_city=True)

    pa_qs = SearchService.annotate_delai_sort(pa_qs)
    pa_qs_before_acte = SearchService.annotate_delai_sort(pa_qs_before_acte)

    # Layout démo : sans acte/lot/service coché ni recherche texte → aucune offre (état vide par défaut).
    if not acte_ids_clean and not lot_ids_clean and not q and not service_id:
        pa_qs = pa_qs.none()

    # Compteurs sidebar « Parcourir les actes » : filtres page (assurance, zone…), pas pilier ni acte.
    pa_qs_nav = PrestataireActe.objects.filter(
        is_available=True,
        organisme__is_active=True,
    )
    if q and q_filter:
        pa_qs_nav = pa_qs_nav.filter(q_filter)
    pa_qs_nav = _apply_level_price_location_filters(pa_qs_nav)

    query_string = _search_querydict_for_links(request.GET)

    per_page = 24

    scored_or_qs, results_count = SearchService.filter_and_sort_offers(
        pa_qs,
        sort=sort,
        regime_filter=regime_filter,
        latlng=latlng,
        proximity_on=proximity_on,
        radius_km=radius_km,
    )
    paginator = Paginator(scored_or_qs, per_page)
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

    price_stats = SearchService.get_global_price_stats()

    top_cities = SearchService.extract_top_zones(
        scope_qs=pa_qs_before_zone,
        pool_from_request=pool_from_request,
        q=q,
        service_id=service_id,
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
                "icon": lot.icon or mark_safe('<i class="ti ti-clipboard-list"></i>'),
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
                "icon": mark_safe('<i class="ti ti-layout-grid"></i>'),
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
                    "icon": ic,
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
            for subgroup in subgroups_out:
                subgroup["open"] = any(
                    row["selected"] for row in subgroup["rows"]
                )

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
        from healthcare.services import PricingService
        PricingService.attach_insurance_context(rows, selected_insurance_ids=assurance_ids_int)

    _attach_distance_km_to_offers(page.object_list, latlng)
    _dem_attach_insurance(list(page.object_list))
    _dem_attach_catalog_counts(list(page.object_list))
    for _blk in acte_results_accordion:
        _dem_attach_insurance(_blk["items"])
        _dem_attach_catalog_counts(_blk["items"])

    mobile_results_by_org: list[dict] = []
    mobile_results_acte_total = len(pool_for_pills) if pool_for_pills else (1 if pool_from_request else 0)
    if pool_from_request and (page.object_list or results_count > 0):
        # Récupérer l'ensemble des offres des actes recherchés pour toutes les structures.
        if pool_for_pills:
            pool_offers = list(pa_qs.filter(acte_id__in=pool_for_pills))
            acte_objs_pool = {
                x.pk: x for x in ActeMedical.objects.filter(pk__in=pool_for_pills)
            }
        else:
            pool_offers = list(page.object_list)
            pool_actes = {pa.acte_id for pa in pool_offers}
            acte_objs_pool = {
                x.pk: x for x in ActeMedical.objects.filter(pk__in=pool_actes)
            }
        _attach_distance_km_to_offers(pool_offers, latlng)
        if proximity_on and latlng:
            lat0, lng0 = latlng
            filtered_pool = []
            for pa in pool_offers:
                org = pa.organisme
                is_global_ambulance = _is_all_zones_ambulance(org)
                if org.latitude is not None and org.longitude is not None:
                    d = haversine_km(lat0, lng0, float(org.latitude), float(org.longitude))
                    if d <= radius_km or is_global_ambulance:
                        pa.distance_km = round(d, 1)
                        filtered_pool.append(pa)
                else:
                    pa.distance_km = None
                    filtered_pool.append(pa)
            pool_offers = filtered_pool
        _dem_attach_insurance(pool_offers)
        _dem_attach_catalog_counts(pool_offers)
        by_org: dict[int, dict] = {}
        for pa in pool_offers:
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
            items_total = sum((pa.price or Decimal(0)) for pa in block["items"])
            plan = getattr(org, "subscription_plan", None)
            mobile_results_by_org.append(
                {
                    "org": org,
                    "items": block["items"],
                    "items_total": items_total,
                    "matching_count": matching_count,
                    "total_actes": mobile_results_acte_total,
                    "missing_actes": missing_actes,
                    "insurance_names": ins_names_by_org.get(oid, []),
                    "distance_km": min(
                        (
                            getattr(pa, "distance_km", None)
                            for pa in block["items"]
                            if getattr(pa, "distance_km", None) is not None
                        ),
                        default=None,
                    ),
                    "is_pioneer": bool(
                        plan and getattr(plan, "is_pioneer_offer", False)
                    ),
                }
            )
        def _block_sort_key(b):
            # Priorité aux structures qui couvrent le plus d'actes recherchés
            match_score = -b["matching_count"]
            if proximity_on or sort == "distance":
                min_dist = min(
                    (
                        getattr(pa, "distance_km", None)
                        for pa in b["items"]
                        if getattr(pa, "distance_km", None) is not None
                    ),
                    default=None,
                )
                return (
                    match_score,
                    0 if min_dist is not None else 1,
                    min_dist if min_dist is not None else 999999,
                    b["items_total"],
                    b["org"].name.lower(),
                )
            elif sort == "delai_asc":
                min_delai = min(
                    (getattr(pa, "_delai_sort", 99) for pa in b["items"]),
                    default=99,
                )
                return (match_score, min_delai, b["items_total"], b["org"].name.lower())
            elif sort == "delai_desc":
                min_delai = min(
                    (getattr(pa, "_delai_sort", 99) for pa in b["items"]),
                    default=99,
                )
                return (match_score, -min_delai, b["items_total"], b["org"].name.lower())
            elif sort == "price_desc":
                return (match_score, -b["items_total"], b["org"].name.lower())
            else:
                return (match_score, b["items_total"], b["org"].name.lower())

        mobile_results_by_org.sort(key=_block_sort_key)
        from .opening_hours_display import opening_hours_summary_for_org

        for block in mobile_results_by_org:
            block["hours_summary"] = opening_hours_summary_for_org(block["org"], max_len=56)

    dem_assurance_labels = list(
        Assurance.objects.filter(pk__in=assurance_ids_int)
        .order_by("name")
        .values_list("name", flat=True),
    )
    dem_assurance_context_json = json.dumps(
        {
            "ids": [str(i) for i in assurance_ids_int],
            "labels": dem_assurance_labels,
            "implicit": assurance_implicit,
        },
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
            is_verified=True,
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
        "current_regime": regime_filter,
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
        "assurance_implicit": assurance_implicit,
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
