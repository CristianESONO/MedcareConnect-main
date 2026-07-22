"""Panier patient — ajout, quantité, suppression, liste devis."""

import pytest
from django.urls import reverse

from cart.models import Cart, CartItem, Devis


@pytest.mark.django_db
def test_ajout_acte_au_panier(client, patient_user, prestataire_acte):
    client.force_login(patient_user)
    url = reverse("cart:cart_add", args=[prestataire_acte.pk])
    r = client.get(url, follow=False)
    assert r.status_code == 302
    cart = Cart.get_active_cart(patient_user)
    assert CartItem.objects.filter(cart=cart, prestataire_acte=prestataire_acte).exists()


@pytest.mark.django_db
def test_mise_a_jour_quantite_panier(client, patient_user, cart_avec_ligne, prestataire_acte):
    client.force_login(patient_user)
    item = CartItem.objects.get(cart=cart_avec_ligne, prestataire_acte=prestataire_acte)
    url = reverse("cart:cart_update_quantity", args=[item.pk])
    r = client.post(url, {"quantity": 3}, follow=False)
    assert r.status_code == 302
    item.refresh_from_db()
    assert item.quantity == 3


@pytest.mark.django_db
def test_suppression_ligne_panier(client, patient_user, cart_avec_ligne, prestataire_acte):
    client.force_login(patient_user)
    item = CartItem.objects.get(cart=cart_avec_ligne, prestataire_acte=prestataire_acte)
    url = reverse("cart:cart_remove", args=[item.pk])
    r = client.get(url, follow=False)
    assert r.status_code == 302
    assert not CartItem.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_vider_panier(client, patient_user, cart_avec_ligne):
    client.force_login(patient_user)
    r = client.get(reverse("cart:cart_clear"), follow=False)
    assert r.status_code == 302
    cart_avec_ligne.refresh_from_db()
    assert cart_avec_ligne.items.count() == 0


@pytest.mark.django_db
def test_liste_devis_patient(client, patient_user, cart_avec_ligne):
    client.force_login(patient_user)
    item = CartItem.objects.get(cart=cart_avec_ligne)
    client.get(reverse("cart:generate_devis") + f"?item={item.pk}")
    r = client.get(reverse("cart:devis_list"), follow=False)
    assert r.status_code == 302
    assert "devis" in (r.url or "")
    devis = Devis.objects.get(patient=patient_user)
    r2 = client.get(reverse("users:patient_panel_tab", kwargs={"tab": "devis"}))
    assert r2.status_code == 200
    assert devis.reference.encode() in r2.content


@pytest.mark.django_db
def test_detail_devis_patient(client, patient_user, cart_avec_ligne):
    client.force_login(patient_user)
    item = CartItem.objects.get(cart=cart_avec_ligne)
    client.get(reverse("cart:generate_devis") + f"?item={item.pk}")
    devis = Devis.objects.get(patient=patient_user)
    r = client.get(reverse("cart:devis_detail", args=[devis.reference]))
    assert r.status_code == 302
    assert "/messaging/" in (r.url or "")
