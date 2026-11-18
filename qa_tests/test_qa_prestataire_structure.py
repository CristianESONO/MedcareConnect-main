"""
Parcours espace prestataire (structure) — accès, pages clés du tableau de bord.
Base de test pytest uniquement (jetable).
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_anonyme_prestataire_dashboard_redirige_connexion(client):
    r = client.get(reverse("healthcare:prestataire_dashboard"), follow=False)
    assert r.status_code == 302
    assert "connexion" in (r.url or "").lower()


@pytest.mark.django_db
def test_patient_ne_peut_pas_acceder_dashboard_prestataire(client, patient_user):
    client.force_login(patient_user)
    r = client.get(reverse("healthcare:prestataire_dashboard"), follow=False)
    assert r.status_code == 302
    assert r.url == reverse("home")


@pytest.mark.django_db
def test_prestataire_dashboard_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:prestataire_dashboard"))
    assert r.status_code == 200
    assert organisme_actif.name.encode() in r.content


@pytest.mark.django_db
def test_prestataire_devis_list_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:prestataire_devis_list"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_prestataire_actes_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:actes_list"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_prestataire_bilan_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:prestataire_bilan"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_prestataire_medplaque_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:prestataire_medplaque"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_prestataire_parametres_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:prestataire_settings"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_prestataire_assurances_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("healthcare:insurances_manage"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_prestataire_messagerie_200(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("messaging:inbox"))
    assert r.status_code == 200
