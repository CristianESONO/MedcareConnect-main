"""Annuaire des établissements — liste filtrée (démo patient desktop)."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Count, Min, Prefetch, Q
from django.db.models import Case, IntegerField, When

from .models import Assurance, OrganismeDeSante, PrestataireActe, PriseEnChargeAssurance
from .utils import assurances_grouped_for_select
from .geo import haversine_km, parse_lat_lng

ANNUAIRE_CATEGORIES: list[tuple[str, str, str]] = [
    ("all", "Tous les types", "🏥"),
    ("labo", "Laboratoire", "🧬"),
    ("img", "Imagerie", "🩻"),
    ("exp", "Explorations fonctionnelles", "⚡"),
    ("dent", "Soins dentaires", "🦷"),
    ("soins", "Soins spécialisés", "💉"),
    ("amb", "Ambulance médicalisée", "🚑"),
]

CATEGORY_ICONS: dict[str, str] = {key: icon for key, _label, icon in ANNUAIRE_CATEGORIES if key != "all"}

CATEGORY_TYPE_NAMES: dict[str, list[str]] = {
    "labo": ["Laboratoire"],
    "img": ["Centre d'imagerie"],
    "dent": ["Cabinet dentaire"],
    "amb": ["Service ambulancier"],
    "exp": [
        "Cabinet médical",
        "Clinique",
        "Hôpital",
        "Centre de santé",
        "Praticien indépendant",
    ],
    "soins": [
        "Cabinet de kinésithérapie",
        "Centre de dialyse",
        "Cabinet santé mentale",
        "Pharmacie",
    ],
}

DELAI_FILTER_MAX_RANK: dict[str, int] = {
    "immediat": 0,
    "30min": 1,
    "1h": 2,
    "4h": 4,
    "24h": 5,
    "48h": 6,
    "rdv": 9,
}

ANNUAIRE_DELAI_CHOICES: list[tuple[str, str]] = [
    ("immediat", "Immédiat"),
    ("30min", "Moins de 30 min"),
    ("1h", "Moins d'1 heure"),
    ("4h", "Dans la journée"),
    ("24h", "Sous 24 h"),
    ("48h", "Sous 48 h"),
    ("rdv", "Sur rendez-vous"),
]

SORT_CHOICES: list[tuple[str, str]] = [
    ("alpha", "A → Z"),
    ("zone", "Par zone"),
    ("ins", "Couverture assurance"),
    ("rdv", "RDV le plus proche"),
    ("dist", "Distance + proche 📍"),
]


def _parse_int_list(raw_values: list[str]) -> list[int]:
    out: list[int] = []
    for val in raw_values:
        try:
            out.append(int(val))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(out))


def _delai_rank_case():
    whens = [
        When(prestataire_actes__delai=key, then=rank)
        for key, rank in PrestataireActe.DELAI_RANK.items()
        if key
    ]
    return Min(
        Case(
            *whens,
            default=99,
            output_field=IntegerField(),
            filter=Q(prestataire_actes__is_available=True),
        )
    )


def _delai_label_from_rank(rank: int | None) -> str:
    if rank is None or rank >= 99:
        return "Sur rendez-vous"
    if rank <= 0:
        return "Immédiat"
    if rank <= 1:
        return "Moins de 30 min"
    if rank <= 2:
        return "Moins de 2 h"
    if rank <= 4:
        return "Dans la journée"
    if rank <= 5:
        return "Sous 24 h"
    if rank <= 6:
        return "Sous 48 h"
    return "Sur rendez-vous"


def _hours_short(org: OrganismeDeSante) -> str:
    from .opening_hours_display import opening_hours_summary_for_org

    summary = opening_hours_summary_for_org(org, max_len=40)
    if summary:
        return summary
    return "Horaires sur demande"


def _zone_label(city: str, quartier: str | None) -> str:
    city = (city or "").strip()
    quartier = (quartier or "").strip()
    if city and quartier:
        return f"{city}, {quartier}"
    return city or quartier or "Sénégal"


def organisme_category_icon(org: OrganismeDeSante) -> str:
    name = (org.type_organisme.name if org.type_organisme else "").strip()
    for key, names in CATEGORY_TYPE_NAMES.items():
        if name in names:
            return CATEGORY_ICONS.get(key, "🏥")
    return "🏥"


def organisme_category_key(org: OrganismeDeSante) -> str:
    name = (org.type_organisme.name if org.type_organisme else "").strip()
    for key, names in CATEGORY_TYPE_NAMES.items():
        if name in names:
            return key
    return "soins"


def build_annuaire_context(request) -> dict:
    q = (request.GET.get("q") or "").strip()
    type_cat = (request.GET.get("type_cat") or "all").strip()
    zone = (request.GET.get("zone") or "").strip()
    delai_filter = (request.GET.get("delai") or "").strip()
    sort = (request.GET.get("sort") or "alpha").strip()
    if sort not in dict(SORT_CHOICES):
        sort = "alpha"

    assurance_ids = _parse_int_list(request.GET.getlist("assurance"))

    qs = (
        OrganismeDeSante.objects.filter(is_active=True)
        .select_related("type_organisme", "region", "subscription_plan")
        .annotate(
            acte_count=Count(
                "prestataire_actes",
                filter=Q(prestataire_actes__is_available=True),
                distinct=True,
            ),
            insurance_count=Count(
                "prises_en_charge",
                filter=Q(prises_en_charge__is_active=True),
                distinct=True,
            ),
            best_delai_rank=_delai_rank_case(),
        )
    )

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(city__icontains=q)
            | Q(quartier__icontains=q)
            | Q(address__icontains=q)
            | Q(type_organisme__name__icontains=q)
        )

    if type_cat and type_cat != "all":
        type_names = CATEGORY_TYPE_NAMES.get(type_cat, [])
        if type_names:
            qs = qs.filter(type_organisme__name__in=type_names)

    if zone:
        if "," in zone:
            city_part, _, quartier_part = zone.partition(",")
            qs = qs.filter(
                city__iexact=city_part.strip(),
                quartier__iexact=quartier_part.strip(),
            )
        else:
            qs = qs.filter(Q(city__iexact=zone) | Q(quartier__iexact=zone))

    if assurance_ids:
        qs = qs.filter(
            prises_en_charge__assurance_id__in=assurance_ids,
            prises_en_charge__is_active=True,
        ).distinct()

    if delai_filter == "rdv":
        qs = qs.filter(
            prestataire_actes__delai="rdv",
            prestataire_actes__is_available=True,
        ).distinct()
    elif delai_filter in DELAI_FILTER_MAX_RANK:
        max_rank = DELAI_FILTER_MAX_RANK[delai_filter]
        allowed = [
            key
            for key, rank in PrestataireActe.DELAI_RANK.items()
            if key and rank <= max_rank
        ]
        qs = qs.filter(
            prestataire_actes__delai__in=allowed,
            prestataire_actes__is_available=True,
        ).distinct()

    geo_required = False
    geo_lat = request.GET.get("geo_lat", "").strip()
    geo_lng = request.GET.get("geo_lng", "").strip()
    # Fallback vers la session si pas transmis dans l'URL
    if not geo_lat:
        geo_lat = str(request.session.get("search_lat", ""))
    if not geo_lng:
        geo_lng = str(request.session.get("search_lng", ""))
    user_coords = parse_lat_lng(geo_lat or None, geo_lng or None)

    if sort == "rdv":
        qs = qs.order_by("best_delai_rank", "name")
    elif sort == "dist":
        if user_coords:
            lat0, lng0 = user_coords
            # Calculer la distance Python sur tous les IDs du qs
            all_orgs_coords = list(
                qs.values_list("pk", "latitude", "longitude")
            )
            # Filtrer les organismes avec des coordonnées valides
            scored: list[tuple[float, int]] = []
            no_coords: list[int] = []
            for pk, lat, lng in all_orgs_coords:
                if lat is not None and lng is not None:
                    try:
                        d = haversine_km(lat0, lng0, float(lat), float(lng))
                        scored.append((d, pk))
                    except (TypeError, ValueError):
                        no_coords.append(pk)
                else:
                    no_coords.append(pk)
            scored.sort(key=lambda x: x[0])
            ordered_ids = [pk for _, pk in scored] + no_coords
            # Trier le queryset selon cet ordre via Case/When
            if ordered_ids:
                whens = [When(pk=pk, then=pos) for pos, pk in enumerate(ordered_ids)]
                qs = qs.annotate(
                    _dist_order=Case(*whens, default=len(ordered_ids), output_field=IntegerField())
                ).order_by("_dist_order")
            else:
                qs = qs.order_by("name")
        else:
            geo_required = True
            qs = qs.order_by("name")
    elif sort == "zone":
        qs = qs.order_by("city", "quartier", "name")
    elif sort == "ins":
        qs = qs.order_by("-insurance_count", "name")
    else:
        qs = qs.order_by("name")

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))

    page_orgs = list(page.object_list)
    if page_orgs:
        org_map = {
            o.pk: o
            for o in OrganismeDeSante.objects.filter(pk__in=[o.pk for o in page_orgs])
            .select_related("type_organisme", "subscription_plan")
            .prefetch_related(
                Prefetch(
                    "prises_en_charge",
                    queryset=PriseEnChargeAssurance.objects.filter(
                        is_active=True
                    ).select_related("assurance"),
                    to_attr="active_insurances",
                )
            )
            .annotate(
                acte_count=Count(
                    "prestataire_actes",
                    filter=Q(prestataire_actes__is_available=True),
                    distinct=True,
                ),
                insurance_count=Count(
                    "prises_en_charge",
                    filter=Q(prises_en_charge__is_active=True),
                    distinct=True,
                ),
                best_delai_rank=_delai_rank_case(),
            )
        }
        page.object_list = [org_map[o.pk] for o in page_orgs if o.pk in org_map]
    else:
        page.object_list = []

    rows = []
    selected_assurance_set = {str(i) for i in assurance_ids}
    for org in page.object_list:
        ins_names = [p.assurance.name for p in getattr(org, "active_insurances", [])]
        matched_ins = [
            p.assurance.name
            for p in getattr(org, "active_insurances", [])
            if str(p.assurance_id) in selected_assurance_set
        ]
        rows.append(
            {
                "org": org,
                "zone_label": _zone_label(org.city, org.quartier),
                "icon": organisme_category_icon(org),
                "acte_count": org.acte_count,
                "delai_label": _delai_label_from_rank(org.best_delai_rank),
                "hours_short": _hours_short(org),
                "insurance_count": org.insurance_count,
                "insurance_names": ins_names,
                "matched_insurances": matched_ins,
                "is_pioneer": bool(
                    org.subscription_plan
                    and getattr(org.subscription_plan, "is_pioneer_offer", False)
                ),
                "is_verified": org.is_verified,
            }
        )

    zones = []
    seen_zones: set[str] = set()
    for row in (
        OrganismeDeSante.objects.filter(is_active=True)
        .values("city", "quartier")
        .distinct()
        .order_by("city", "quartier")
    ):
        label = _zone_label(row.get("city") or "", row.get("quartier"))
        if label and label not in seen_zones:
            seen_zones.add(label)
            zones.append(label)

    qd = request.GET.copy()
    if "page" in qd:
        del qd["page"]
    query_string = qd.urlencode()

    active_filter_count = sum(
        bool(x)
        for x in (
            q,
            type_cat and type_cat != "all",
            zone,
            assurance_ids,
            delai_filter,
        )
    )

    return {
        "page": page,
        "rows": rows,
        "search_q": q,
        "current_type_cat": type_cat,
        "current_zone": zone,
        "current_delai": delai_filter,
        "current_sort": sort,
        "current_assurances": [str(i) for i in assurance_ids],
        "annuaire_categories": ANNUAIRE_CATEGORIES,
        "annuaire_delai_choices": ANNUAIRE_DELAI_CHOICES,
        "sort_choices": SORT_CHOICES,
        "zones": zones,
        "assurances_grouped": assurances_grouped_for_select(),
        "all_assurances": Assurance.objects.order_by("segment", "name"),
        "query_string": query_string,
        "active_filter_count": active_filter_count,
        "results_count": paginator.count,
        "geo_required": geo_required,
    }
