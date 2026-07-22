"""APIs recherche et fiche organisme."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_api_geocode_repond(client):
    r = client.get(reverse("healthcare:api_geocode"), {"q": "Dakar"})
    assert r.status_code == 200
    assert "results" in r.json()


@pytest.mark.django_db
def test_api_actes_budget_repond(client):
    r = client.get(reverse("healthcare:api_actes_budget"), {"q": "radio"})
    assert r.status_code == 200


@pytest.mark.django_db
def test_fiche_organisme_200(client, organisme_actif):
    organisme_actif.refresh_from_db()
    assert organisme_actif.slug
    r = client.get(reverse("healthcare:organisme_detail", args=[organisme_actif.slug]))
    assert r.status_code == 200
    assert organisme_actif.name.encode() in r.content


@pytest.mark.django_db
def test_parcours_bundle_page(client):
    r = client.get(reverse("healthcare:bundle_planner"))
    assert r.status_code == 200
