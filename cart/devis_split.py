"""
Regroupement des lignes de panier par organisme (devis parent / sous-devis / WhatsApp).
"""
from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
from typing import Any, Iterable

def group_cart_items_by_organisme(items: Iterable) -> "OrderedDict[int, list]":
    """
    Retourne OrderedDict[organisme_id, list[CartItem]] (ordre d'insertion stable).
    Chaque item doit avoir prestataire_acte.organisme chargé.
    """
    by_org: OrderedDict[int, list] = OrderedDict()
    for item in items:
        org = item.prestataire_acte.organisme
        oid = org.pk
        if oid not in by_org:
            by_org[oid] = []
        by_org[oid].append(item)
    return by_org


def iter_cart_item_groups_by_organisme(items: Iterable):
    """Yield (organisme, list[CartItem]) pour chaque structure."""
    by_org = group_cart_items_by_organisme(items)
    for _oid, item_list in by_org.items():
        if not item_list:
            continue
        yield item_list[0].prestataire_acte.organisme, item_list


def iter_cart_items_individually(items: Iterable):
    """Yield (organisme, list[CartItem]) — une ligne panier = un devis."""
    for item in items:
        yield item.prestataire_acte.organisme, [item]


def build_detail_lines_for_cart_items(
    item_list: list,
    selected_insurance,
    patient_profile=None,
) -> tuple[list[dict[str, Any]], Decimal, Decimal, Decimal]:
    """
    Construit le snapshot JSON + totaux (brut, assurance, patient) pour un groupe d'items.
    """
    details: list[dict[str, Any]] = []
    total_brut = Decimal("0")
    total_patient = Decimal("0")
    for item in item_list:
        pa = item.prestataire_acte
        unit_price = pa.price
        subtotal = item.subtotal
        total_brut += subtotal
        coverage_rate = None
        patient_cost = subtotal
        if selected_insurance:
            coverage_rate = pa.get_coverage_rate(
                selected_insurance, patient_profile=patient_profile
            )
            patient_cost = item.cost_after_insurance(
                selected_insurance, patient_profile=patient_profile
            )
        total_patient += patient_cost
        details.append({
            "acte_id": pa.acte_id,
            "acte": pa.acte.name,
            "organisme": pa.organisme.name,
            "unit_price": str(unit_price),
            "quantity": item.quantity,
            "subtotal": str(subtotal),
            "coverage_rate": str(coverage_rate) if coverage_rate else None,
            "patient_cost": str(patient_cost),
        })
    total_assurance = total_brut - total_patient
    return details, total_brut, total_assurance, total_patient


