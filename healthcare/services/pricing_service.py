"""Services métier pour les calculs de tarification et de couverture assurance."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable, List, Optional, Set, Tuple

from healthcare.models import PriseEnChargeAssurance


class PricingService:
    """Service centralisant les règles de tarification, régimes et couverture assurance."""

    VALID_REGIMES = ("comptant", "ipm", "assurance")

    @classmethod
    def get_regime_info(cls, pa: Any, regime: Optional[str] = "comptant") -> dict:
        """
        Calcule la tarification et le statut de couverture pour un PrestataireActe selon le régime.
        Retourne un dictionnaire standardisé :
          - regime: 'comptant' | 'ipm' | 'assurance'
          - price: Decimal | None
          - status: 'covered' | 'to_confirm' | 'excluded'
          - effective_price: Decimal
          - is_conventionne: bool
        """
        reg = (regime or "comptant").lower().strip()
        if reg not in cls.VALID_REGIMES:
            reg = "comptant"

        if reg == "ipm":
            status = getattr(pa, "coverage_status_ipm", "to_confirm") or "to_confirm"
            price_ipm = getattr(pa, "price_ipm", None)
            if price_ipm is not None and price_ipm > 0:
                if status == "to_confirm":
                    status = "covered"
            elif status == "covered":
                # Garde-fou G5 : statut couvert mais prix manquant/nul -> repli sur to_confirm
                status = "to_confirm"

            effective_price = price_ipm if (price_ipm is not None and price_ipm > 0) else pa.price
            return {
                "regime": "ipm",
                "price": price_ipm,
                "status": status,
                "effective_price": effective_price,
                "is_conventionne": bool(price_ipm is not None and price_ipm > 0),
            }

        elif reg == "assurance":
            status = getattr(pa, "coverage_status_assurance", "to_confirm") or "to_confirm"
            price_assur = getattr(pa, "price_assurance", None)
            if price_assur is not None and price_assur > 0:
                if status == "to_confirm":
                    status = "covered"
            elif status == "covered":
                # Garde-fou G5 : statut couvert mais prix manquant/nul -> repli sur to_confirm
                status = "to_confirm"

            effective_price = price_assur if (price_assur is not None and price_assur > 0) else pa.price
            return {
                "regime": "assurance",
                "price": price_assur,
                "status": status,
                "effective_price": effective_price,
                "is_conventionne": bool(price_assur is not None and price_assur > 0),
            }

        else:
            return {
                "regime": "comptant",
                "price": pa.price,
                "status": "covered",
                "effective_price": pa.price,
                "is_conventionne": False,
            }

    @classmethod
    def attach_insurance_context(
        cls,
        rows: Iterable[Any],
        selected_insurance_ids: Optional[Iterable[Any]] = None,
    ) -> None:
        """
        Attache dynamiquement `dem_insurance_match` et `dem_insurance_names`
        sur chaque PrestataireActe d'une collection.
        Optimisé avec requêtes groupées sans n+1.
        """
        rows_list = list(rows)
        if not rows_list:
            return

        org_ids = {pa.organisme_id for pa in rows_list if getattr(pa, "organisme_id", None)}
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

        # Nettoyage des IDs sélectionnés
        selected_ids_int: Set[int] = set()
        if selected_insurance_ids:
            for x in selected_insurance_ids:
                try:
                    selected_ids_int.add(int(x))
                except (ValueError, TypeError):
                    pass

        if not selected_ids_int:
            for pa in rows_list:
                pa.dem_insurance_match = True
                pa.dem_insurance_names = ins_names_by_org.get(pa.organisme_id, [])
            return

        mapping: dict[int, set[int]] = defaultdict(set)
        if org_ids:
            for oid, aid in PriseEnChargeAssurance.objects.filter(
                organisme_id__in=org_ids,
                assurance_id__in=selected_ids_int,
                is_active=True,
            ).values_list("organisme_id", "assurance_id"):
                mapping[int(oid)].add(int(aid))

        want = frozenset(selected_ids_int)
        for pa in rows_list:
            pa.dem_insurance_match = bool(mapping.get(pa.organisme_id, set()) & want)
            pa.dem_insurance_names = ins_names_by_org.get(pa.organisme_id, [])

