"""
Pages publiques et garde-fous d’accès : smoke test HTTP (sans Playwright).
Couvre une partie du check-list manuel documenté dans FONCTIONNALITES_ET_PARCOURS_TESTS.md.
"""

import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_accueil_200(client):
    assert client.get(reverse("home")).status_code == 200


@pytest.mark.django_db
def test_recherche_200(client):
    assert client.get(reverse("healthcare:search")).status_code == 200


@pytest.mark.django_db
def test_centres_redirige_vers_annuaire(client):
    r = client.get(reverse("healthcare:centres_list"), follow=False)
    assert r.status_code == 302
    assert reverse("healthcare:annuaire") in (r.url or "")


@pytest.mark.django_db
def test_annuaire_200(client):
    assert client.get(reverse("healthcare:annuaire")).status_code == 200


@pytest.mark.django_db
def test_parcours_bundle_200(client):
    assert client.get(reverse("healthcare:bundle_planner")).status_code == 200


@pytest.mark.django_db
def test_panier_public_200(client):
    assert client.get(reverse("cart:cart_view")).status_code == 200


@pytest.mark.django_db
def test_inscription_200(client):
    assert client.get(reverse("users:register")).status_code == 200


@pytest.mark.django_db
def test_connexion_200(client):
    assert client.get(reverse("users:login")).status_code == 200


@pytest.mark.django_db
def test_messagerie_inbox_redirige_si_anonyme(client):
    r = client.get(reverse("messaging:inbox"), follow=False)
    assert r.status_code == 302
    assert "connexion" in (r.url or "").lower()


@pytest.mark.django_db
def test_dashboard_redirige_si_anonyme(client):
    r = client.get(reverse("dashboard:index"), follow=False)
    assert r.status_code == 302
    assert "connexion" in (r.url or "").lower()


@pytest.mark.django_db
def test_espace_actes_prestataire_redirige_si_anonyme(client):
    r = client.get(reverse("healthcare:actes_list"), follow=False)
    assert r.status_code == 302


@pytest.mark.django_db
def test_prestataire_actes_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:actes_list"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_patient_preferences_notifications_200(client, patient_user):
    client.force_login(patient_user)
    r = client.get(reverse("notifications:my_preferences"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_api_autocomplete_recherche_200(client):
    r = client.get(reverse("healthcare:api_search_autocomplete"), data={"q": "dak"})
    assert r.status_code == 200


@pytest.mark.django_db
@override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
def test_page_404_inconnue(client):
    r = client.get("/url-inexistante-qa/", follow=False)
    assert r.status_code == 404
    assert b"Cette page n'existe pas" in r.content
