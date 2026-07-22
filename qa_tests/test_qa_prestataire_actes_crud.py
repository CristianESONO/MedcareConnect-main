"""CRUD actes prestataire — ajout, édition prix, suppression."""

import pytest
from django.urls import reverse

from healthcare.models import PrestataireActe


@pytest.mark.django_db
def test_prestataire_ajoute_acte(client, prestataire_user, organisme_actif, acte_catalogue_libre):
    client.force_login(prestataire_user)
    r = client.post(
        reverse("healthcare:acte_add"),
        {
            "acte": acte_catalogue_libre.pk,
            "price": "12500",
            "delai": "24h",
            "is_available": True,
        },
        follow=False,
    )
    assert r.status_code == 302
    assert PrestataireActe.objects.filter(
        organisme=organisme_actif, acte=acte_catalogue_libre
    ).exists()


@pytest.mark.django_db
def test_prestataire_modifie_prix_acte(client, prestataire_user, prestataire_acte):
    client.force_login(prestataire_user)
    r = client.post(
        reverse("healthcare:acte_edit", args=[prestataire_acte.pk]),
        {
            "acte": prestataire_acte.acte_id,
            "price": "9900",
            "delai": prestataire_acte.delai or "",
            "is_available": True,
        },
        follow=False,
    )
    assert r.status_code == 302
    prestataire_acte.refresh_from_db()
    assert prestataire_acte.price == 9900


@pytest.mark.django_db
def test_prestataire_supprime_acte(client, prestataire_user, prestataire_acte):
    pk = prestataire_acte.pk
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:acte_delete", args=[pk]), follow=False)
    assert r.status_code == 302
    assert not PrestataireActe.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_prestataire_zones_prelevement_redirige_actes(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:prestataire_zones_prelevement"), follow=False)
    assert r.status_code == 302
    assert reverse("healthcare:actes_list") in (r.url or "")
    assert "bloc-domicile" in (r.url or "")


@pytest.mark.django_db
def test_prestataire_abonnement_page(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:prestataire_subscription"))
    assert r.status_code == 302
    assert reverse("healthcare:prestataire_settings") in (r.url or "")
