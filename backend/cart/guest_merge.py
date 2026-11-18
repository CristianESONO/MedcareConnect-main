"""Fusion panier invité (localStorage) → panier serveur patient."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Sum

from healthcare.models import Assurance, PrestataireActe

from .models import Cart, CartItem

GUEST_CART_SESSION_KEY = "medcare_guest_cart_session_v1"
GUEST_INSURANCE_SESSION_KEY = "medcare_guest_insurance_id_v1"
GUEST_INSURANCE_OPT_OUT_KEY = "medcare_guest_insurance_opt_out_v1"


def _normalize_guest_items(raw: list) -> dict[int, int]:
    """Retourne {prestataire_acte_id: quantité totale}."""
    out: dict[int, int] = {}
    if not isinstance(raw, list):
        return out
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            pa_id = int(row.get("pa_id") if row.get("pa_id") is not None else row.get("prestataire_acte_id"))
        except (TypeError, ValueError):
            continue
        qty = row.get("qty") if row.get("qty") is not None else row.get("q", 1)
        try:
            qty = max(1, min(999, int(qty)))
        except (TypeError, ValueError):
            qty = 1
        out[pa_id] = out.get(pa_id, 0) + qty
    return out


def _normalize_session_cart(raw: object) -> dict[int, int]:
    """
    Session: dict { "prestataire_acte_id": qty }.
    Retourne {prestataire_acte_id: qty}.
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[int, int] = {}
    for k, v in raw.items():
        try:
            pa_id = int(k)
            qty = int(v)
        except (TypeError, ValueError):
            continue
        if pa_id <= 0:
            continue
        qty = max(1, min(999, qty))
        out[pa_id] = out.get(pa_id, 0) + qty
    return out


@transaction.atomic
def merge_guest_items_into_cart(
    user,
    raw_items: list,
    insurance_id=None,
    insurance_opt_out=False,
) -> tuple[int, int]:
    """
    Fusionne les lignes invité dans le panier actif du user.
    Retourne (nombre de prestataire_acte distincts fusionnés, nombre total d'articles dans le panier).
    """
    cart = Cart.get_active_cart(user)
    merged_qty = _normalize_guest_items(raw_items)
    if not merged_qty:
        return 0, cart.item_count

    pas = list(
        PrestataireActe.objects.filter(
            pk__in=list(merged_qty.keys()),
            is_available=True,
            organisme__is_active=True,
        ).select_related("acte", "organisme")
    )
    found = {pa.pk: pa for pa in pas}
    touched = 0
    for pa_id, qty in merged_qty.items():
        if pa_id not in found:
            continue
        pa = found[pa_id]
        existing = CartItem.objects.filter(cart=cart, prestataire_acte=pa).first()
        if existing:
            existing.quantity += qty
            existing.save(update_fields=["quantity"])
        else:
            if CartItem.objects.filter(
                cart=cart, prestataire_acte__acte_id=pa.acte_id
            ).exists():
                continue
            CartItem.objects.create(cart=cart, prestataire_acte=pa, quantity=qty)
        touched += 1

    if insurance_opt_out:
        cart.selected_insurance = None
        cart.insurance_user_override = True
        cart.save(update_fields=["selected_insurance", "insurance_user_override"])
    elif insurance_id is not None and str(insurance_id).strip() != "":
        if not cart.selected_insurance_id:
            try:
                ass = Assurance.objects.get(pk=int(insurance_id), is_active=True)
                cart.selected_insurance = ass
                cart.insurance_user_override = True
                cart.save(update_fields=["selected_insurance", "insurance_user_override"])
            except (ValueError, Assurance.DoesNotExist):
                pass

    total_units = CartItem.objects.filter(cart=cart).aggregate(t=Sum("quantity"))["t"] or 0
    return touched, int(total_units)


@transaction.atomic
def merge_session_cart_into_cart(request, user) -> tuple[int, int]:
    """
    Fusionne le panier visiteur stocké en session dans le panier actif du user (patient).
    Retourne (distincts fusionnés, nombre de lignes dans le panier serveur).
    """
    raw = request.session.get(GUEST_CART_SESSION_KEY)
    merged_qty = _normalize_session_cart(raw)
    if not merged_qty:
        return 0, Cart.get_active_cart(user).item_count

    raw_list = [{"pa_id": pa_id, "qty": qty} for pa_id, qty in merged_qty.items()]
    insurance_id = request.session.get(GUEST_INSURANCE_SESSION_KEY)
    guest_opt_out = request.session.get(GUEST_INSURANCE_OPT_OUT_KEY)
    touched, line_count = merge_guest_items_into_cart(
        user, raw_list, insurance_id=insurance_id, insurance_opt_out=bool(guest_opt_out),
    )

    # Nettoyage session après succès (même si touched==0, les lignes invalides auront été ignorées)
    request.session.pop(GUEST_CART_SESSION_KEY, None)
    request.session.pop(GUEST_INSURANCE_SESSION_KEY, None)
    request.session.pop(GUEST_INSURANCE_OPT_OUT_KEY, None)
    request.session.modified = True
    return touched, line_count
