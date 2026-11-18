"""Services métier pour la construction et l'exécution des requêtes de recherche."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, List, Optional, Sequence, Set, Tuple, Union

from django.db.models import Case, F, IntegerField, Max, Min, Q, QuerySet, Value, When

from healthcare.geo import haversine_km, parse_lat_lng, parse_radius_km
from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, Region
from healthcare.management.commands.fusionner_actes_doublons import _canonical_key_for_acte


class SearchService:
    """Centralise la construction, le filtrage et le tri des requêtes de recherche de prestations de santé."""

    SORT_CHOICES = frozenset(
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
            "price_ipm_asc",
            "price_ipm_desc",
            "price_assurance_asc",
            "price_assurance_desc",
        }
    )

    VALID_DELAIS = frozenset({k for k, _ in PrestataireActe.DELAI_CHOICES if k})

    @classmethod
    def is_all_zones_ambulance(cls, organisme: Any) -> bool:
        """Détecte si une structure est une ambulance / SMUR couvrant toutes zones."""
        if not organisme:
            return False
        t_slug = (organisme.type_organisme.slug or "").lower() if getattr(organisme, "type_organisme", None) else ""
        t_name = (organisme.type_organisme.name or "").lower() if getattr(organisme, "type_organisme", None) else ""
        o_name = (getattr(organisme, "name", None) or "").lower()
        return "ambulance" in t_slug or "ambulance" in t_name or "ambulance" in o_name

    @classmethod
    def annotate_delai_sort(cls, qs: QuerySet) -> QuerySet:
        """Annotation pour trier les offres par délai indicatif (`PrestataireActe.DELAI_RANK`)."""
        whens = [When(delai=k, then=Value(v)) for k, v in PrestataireActe.DELAI_RANK.items()]
        return qs.annotate(
            _delai_sort=Case(
                *whens,
                default=Value(99),
                output_field=IntegerField(),
            )
        )

    @classmethod
    def attach_distance_km_to_offers(cls, offers: Iterable[Any], latlng: Optional[Tuple[float, float]]) -> None:
        """Attache la distance GPS en km (distance_km) aux offres pour affichage / tri."""
        if not latlng:
            return
        lat0, lng0 = latlng
        for pa in offers:
            if getattr(pa, "distance_km", None) is not None:
                continue
            org = getattr(pa, "organisme", None)
            if not org or org.latitude is None or org.longitude is None:
                pa.distance_km = None
                continue
            pa.distance_km = round(
                haversine_km(lat0, lng0, float(org.latitude), float(org.longitude)),
                1,
            )

    @classmethod
    def parse_int_list(cls, values: Iterable[Any]) -> List[int]:
        """Convertit une liste de valeurs brutes en liste d'entiers uniques sans doublon."""
        out: List[int] = []
        for x in values:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return list(dict.fromkeys(out))

    @classmethod
    def acte_ids_from_lot_params(cls, lot_ids: Sequence[int]) -> List[int]:
        """Retourne la liste des IDs d'actes appartenant aux lots spécifiés."""
        if not lot_ids:
            return []
        return list(
            ActeMedical.objects.filter(
                lot_memberships__lot_id__in=lot_ids,
            )
            .values_list("pk", flat=True)
            .distinct()
        )

    @classmethod
    def build_base_queryset(cls) -> QuerySet:
        """Queryset de base des offres de prestations actives et tarifées."""
        return PrestataireActe.objects.filter(
            is_available=True,
            organisme__is_active=True,
            price__gt=0,
        ).select_related(
            "organisme",
            "organisme__type_organisme",
            "organisme__region",
            "organisme__subscription_plan",
            "acte",
            "acte__service_medical_category",
        )

    @classmethod
    def build_search_text_filter(cls, q: str) -> Tuple[Optional[Q], List[int]]:
        """
        Construit l'expression Q de recherche textuelle avec résolution
        des synonymes médicaux et actes équivalents.
        """
        q = (q or "").strip()
        if not q:
            return None, []

        q_norm_key = _canonical_key_for_acte(q)
        equiv_acte_ids: List[int] = []
        if q_norm_key:
            for a in ActeMedical.objects.filter(is_active=True, level=3):
                if _canonical_key_for_acte(a.name) == q_norm_key:
                    equiv_acte_ids.append(a.pk)

        q_filter = (
            Q(acte__name__icontains=q)
            | Q(acte__description__icontains=q)
            | Q(acte__service_medical_category__name__icontains=q)
            | Q(organisme__name__icontains=q)
            | Q(organisme__city__icontains=q)
        )
        if equiv_acte_ids:
            q_filter |= Q(acte_id__in=equiv_acte_ids)
        if len(q) >= 2:
            q_filter |= Q(acte__code__icontains=q)

        return q_filter, equiv_acte_ids

    @classmethod
    def apply_level_price_location_filters(
        cls,
        qs: QuerySet,
        *,
        level: Optional[str] = None,
        regime_filter: str = "comptant",
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        assurance_ids: Optional[Sequence[int]] = None,
        city: str = "",
        apply_city: bool = True,
        type_ids: Optional[Sequence[Any]] = None,
        region_ids: Optional[Sequence[Any]] = None,
        delai_filter: str = "",
        domicile_filter: bool = False,
    ) -> QuerySet:
        """Applique les filtres de niveau, prix, assurance, localisation, type et délai."""
        if level in ("1", "2", "3"):
            qs = qs.filter(acte__level=int(level))

        reg = (regime_filter or "comptant").lower().strip()
        price_field = "price"
        if reg == "ipm":
            price_field = "price_ipm"
            qs = qs.filter(price_ipm__isnull=False, price_ipm__gt=0)
        elif reg == "assurance":
            price_field = "price_assurance"
            qs = qs.filter(price_assurance__isnull=False, price_assurance__gt=0)
        else:
            qs = qs.filter(price__gt=0)

        if price_min is not None:
            qs = qs.filter(**{f"{price_field}__gte": price_min})
        if price_max is not None:
            qs = qs.filter(**{f"{price_field}__lte": price_max})

        if assurance_ids:
            qs = qs.filter(
                organisme__prises_en_charge__assurance_id__in=assurance_ids,
                organisme__prises_en_charge__is_active=True,
            ).distinct()

        if apply_city and city:
            clean_city = city.strip()
            if clean_city.lower() in ("dakar (tous)", "dakar"):
                qs = qs.filter(
                    Q(organisme__city__iexact="Dakar")
                    | Q(organisme__region__slug="dakar")
                )
            else:
                qs = qs.filter(
                    Q(organisme__city__icontains=clean_city)
                    | Q(organisme__quartier__icontains=clean_city)
                    | Q(organisme__address__icontains=clean_city)
                    | Q(organisme__quartier__icontains="toutes zones")
                    | Q(organisme__address__icontains="toutes zones")
                )

        if type_ids:
            qs = qs.filter(organisme__type_organisme_id__in=type_ids)

        if region_ids:
            reg_q = Q(organisme__region_id__in=region_ids)
            dakar_pks = list(Region.objects.filter(slug__iexact="dakar").values_list("pk", flat=True))
            if any(str(rpk) in [str(x) for x in region_ids] for rpk in dakar_pks):
                reg_q |= Q(
                    organisme__region__isnull=True,
                    organisme__city__iexact="Dakar",
                ) | Q(
                    organisme__region__isnull=True,
                    organisme__address__icontains="Dakar",
                )
            qs = qs.filter(reg_q)

        if delai_filter and delai_filter in cls.VALID_DELAIS:
            target_rank = PrestataireActe.DELAI_RANK.get(delai_filter, 99)
            better_or_equal = [
                k for k in cls.VALID_DELAIS
                if PrestataireActe.DELAI_RANK.get(k, 99) <= target_rank
            ]
            qs = qs.filter(delai__in=better_or_equal)

        if domicile_filter:
            qs = qs.filter(organisme__prises_sang_domicile=True)

        return qs

    @classmethod
    def filter_and_sort_offers(
        cls,
        pa_qs: QuerySet,
        *,
        sort: str = "price_asc",
        regime_filter: str = "comptant",
        latlng: Optional[Tuple[float, float]] = None,
        proximity_on: bool = False,
        radius_km: float = 30.0,
    ) -> Tuple[Union[QuerySet, List[Any]], int]:
        """
        Ordonne les résultats selon la clé de tri ou le calcul de proximité GPS.
        Retourne un tuple (résultats, nombre_total_de_résultats).
        """
        if sort not in cls.SORT_CHOICES:
            sort = "price_asc"

        reg = (regime_filter or "comptant").lower().strip()

        # Proximité géographique GPS avec rayon
        if proximity_on and latlng:
            lat0, lng0 = latlng
            scored_geo: List[Any] = []
            unscored_geo: List[Any] = []
            for pa in pa_qs:
                org = pa.organisme
                is_global_ambulance = cls.is_all_zones_ambulance(org)

                if org.latitude is not None and org.longitude is not None:
                    d = haversine_km(lat0, lng0, float(org.latitude), float(org.longitude))
                    if d <= radius_km or is_global_ambulance:
                        pa.distance_km = round(d, 1)
                        scored_geo.append(pa)
                else:
                    pa.distance_km = None
                    unscored_geo.append(pa)

            if sort == "price_asc":
                scored_geo.sort(key=lambda x: (x.distance_km, x.price, x.acte.name))
                unscored_geo.sort(key=lambda x: (x.price, x.acte.name))
            elif sort == "price_desc":
                scored_geo.sort(key=lambda x: (x.distance_km, -x.price, x.acte.name))
                unscored_geo.sort(key=lambda x: (-x.price, x.acte.name))
            elif sort == "delai_asc":
                scored_geo.sort(
                    key=lambda x: (
                        x.distance_km,
                        getattr(x, "_delai_sort", 99),
                        x.price,
                        x.acte.name,
                    )
                )
                unscored_geo.sort(
                    key=lambda x: (
                        getattr(x, "_delai_sort", 99),
                        x.price,
                        x.acte.name,
                    )
                )
            elif sort == "delai_desc":
                scored_geo.sort(
                    key=lambda x: (
                        x.distance_km,
                        -getattr(x, "_delai_sort", 99),
                        x.price,
                        x.acte.name,
                    )
                )
                unscored_geo.sort(
                    key=lambda x: (
                        -getattr(x, "_delai_sort", 99),
                        x.price,
                        x.acte.name,
                    )
                )
            else:
                scored_geo.sort(key=lambda x: (x.distance_km, x.price))
                unscored_geo.sort(key=lambda x: x.price)

            scored = scored_geo + unscored_geo
            return scored, len(scored)

        # Tri par distance pure
        elif latlng and sort == "distance":
            lat0, lng0 = latlng
            scored_geo = []
            unscored_geo = []
            for pa in pa_qs:
                org = pa.organisme
                if org.latitude is not None and org.longitude is not None:
                    d = haversine_km(lat0, lng0, float(org.latitude), float(org.longitude))
                    pa.distance_km = round(d, 1)
                    scored_geo.append(pa)
                else:
                    pa.distance_km = None
                    unscored_geo.append(pa)
            scored_geo.sort(key=lambda x: (x.distance_km, x.price))
            unscored_geo.sort(key=lambda x: x.price)
            scored = scored_geo + unscored_geo
            return scored, len(scored)

        # Tris standard en base de données
        else:
            if sort == "price_desc":
                pa_qs = pa_qs.order_by("-price", "acte__name", "organisme__name")
            elif sort == "popular":
                pa_qs = pa_qs.order_by("-organisme__profile_views_count", "price", "acte__name")
            elif sort == "recent_pa":
                pa_qs = pa_qs.order_by("-updated_at", "acte__name")
            elif sort == "name_org":
                pa_qs = pa_qs.order_by("organisme__name", "acte__name", "price")
            elif sort in ("delai_asc", "delai_rdv_asc"):
                pa_qs = pa_qs.order_by("_delai_sort", "price", "acte__name", "organisme__name")
            elif sort == "delai_desc":
                pa_qs = pa_qs.order_by("-_delai_sort", "price", "acte__name", "organisme__name")
            elif sort == "price_ipm_asc":
                pa_qs = pa_qs.order_by(
                    F("price_ipm").asc(nulls_last=True), "price", "acte__name", "organisme__name"
                )
            elif sort == "price_ipm_desc":
                pa_qs = pa_qs.order_by(
                    F("price_ipm").desc(nulls_last=True), "acte__name", "organisme__name"
                )
            elif sort == "price_assurance_asc":
                pa_qs = pa_qs.order_by(
                    F("price_assurance").asc(nulls_last=True), "price", "acte__name", "organisme__name"
                )
            elif sort == "price_assurance_desc":
                pa_qs = pa_qs.order_by(
                    F("price_assurance").desc(nulls_last=True), "acte__name", "organisme__name"
                )
            else:
                # price_asc par défaut adapté au régime
                if reg == "ipm":
                    pa_qs = pa_qs.order_by(F("price_ipm").asc(nulls_last=True), "price", "acte__name", "organisme__name")
                elif reg == "assurance":
                    pa_qs = pa_qs.order_by(F("price_assurance").asc(nulls_last=True), "price", "acte__name", "organisme__name")
                else:
                    pa_qs = pa_qs.order_by("price", "acte__name", "organisme__name")

            return pa_qs, pa_qs.count()

    @classmethod
    def extract_zone_from_org(cls, org: Any) -> str:
        """Extrait le libellé de zone ou quartier pertinent d'un organisme."""
        q = (getattr(org, "quartier", None) or "").strip()
        if q and q.lower() not in ("none", ""):
            return q
        addr = (getattr(org, "address", None) or "").strip()
        if addr and addr.lower() not in ("none", "", "dakar"):
            return addr
        return (getattr(org, "city", None) or "").strip() or "Dakar"

    @classmethod
    def extract_top_zones(
        cls,
        scope_qs: Optional[QuerySet] = None,
        pool_from_request: bool = False,
        q: str = "",
        service_id: Optional[Any] = None,
    ) -> List[str]:
        """Extrait la liste ordonnée des zones/quartiers représentés par les résultats."""
        if pool_from_request or q or service_id:
            if scope_qs is not None:
                target_org_ids = list(scope_qs.values_list("organisme_id", flat=True).distinct())
            else:
                target_org_ids = []
            if target_org_ids:
                found_orgs = OrganismeDeSante.objects.filter(id__in=target_org_ids)
                return sorted({cls.extract_zone_from_org(o) for o in found_orgs if cls.extract_zone_from_org(o)})
            return []
        else:
            all_active_org_ids = list(
                PrestataireActe.objects.filter(is_available=True, organisme__is_active=True)
                .values_list("organisme_id", flat=True)
                .distinct()
            )
            if all_active_org_ids:
                all_found_orgs = OrganismeDeSante.objects.filter(id__in=all_active_org_ids)
                return sorted({cls.extract_zone_from_org(o) for o in all_found_orgs if cls.extract_zone_from_org(o)})
            return []

    @classmethod
    def get_global_price_stats(cls) -> dict:
        """Retourne les prix min et max globaux des actes actifs."""
        return PrestataireActe.objects.filter(
            is_available=True,
            organisme__is_active=True,
        ).aggregate(pmin=Min("price"), pmax=Max("price"))
