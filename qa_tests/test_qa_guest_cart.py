"""Panier invité — session sans compte."""

import pytest
from django.urls import reverse

from cart.views import GUEST_CART_SESSION_KEY


@pytest.mark.django_db
def test_invite_ajoute_au_panier_session(client, prestataire_acte):
    url = reverse("cart:cart_add", args=[prestataire_acte.pk])
    r = client.get(url, follow=False)
    assert r.status_code == 302
    raw = client.session.get(GUEST_CART_SESSION_KEY) or {}
    assert str(prestataire_acte.pk) in raw or prestataire_acte.pk in raw


@pytest.mark.django_db
def test_invite_apercu_panier_json(client, prestataire_acte):
    client.get(reverse("cart:cart_add", args=[prestataire_acte.pk]))
    r = client.get(reverse("cart:cart_snapshot"))
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("cart_count", 0) >= 1


@pytest.mark.django_db
def test_invite_merge_apres_connexion(client, patient_user, prestataire_acte):
    import json

    client.force_login(patient_user)
    r = client.post(
        reverse("cart:cart_merge_guest"),
        data=json.dumps(
            {"items": [{"prestataire_acte_id": prestataire_acte.pk, "quantity": 1}]}
        ),
        content_type="application/json",
        follow=False,
    )
    assert r.status_code == 200
    from cart.models import Cart, CartItem

    cart = Cart.get_active_cart(patient_user)
    assert CartItem.objects.filter(cart=cart, prestataire_acte=prestataire_acte).exists()
