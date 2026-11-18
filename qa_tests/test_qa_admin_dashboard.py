"""
Parcours dashboard administrateur — RBAC et pages de modération / pilotage.
Base de test pytest uniquement (jetable).
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_anonyme_dashboard_redirige_connexion(client):
    r = client.get(reverse("dashboard:index"), follow=False)
    assert r.status_code == 302
    assert "connexion" in (r.url or "").lower()


@pytest.mark.django_db
def test_patient_dashboard_redirige_accueil(client, patient_user):
    client.force_login(patient_user)
    r = client.get(reverse("dashboard:index"), follow=False)
    assert r.status_code == 302
    assert r.url == reverse("home")


@pytest.mark.django_db
def test_prestataire_dashboard_admin_redirige_accueil(client, prestataire_user, organisme_actif):
    client.force_login(prestataire_user)
    r = client.get(reverse("dashboard:index"), follow=False)
    assert r.status_code == 302
    assert r.url == reverse("home")


@pytest.mark.django_db
def test_superuser_dashboard_index_200(client, superuser):
    client.force_login(superuser)
    r = client.get(reverse("dashboard:index"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_superuser_organismes_list_200(client, superuser):
    client.force_login(superuser)
    r = client.get(reverse("dashboard:organismes_list"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_superuser_reviews_list_200(client, superuser):
    client.force_login(superuser)
    r = client.get(reverse("dashboard:reviews_list"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_superuser_devis_overview_200(client, superuser):
    client.force_login(superuser)
    r = client.get(reverse("dashboard:devis_overview"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_superuser_activite_rdv_200(client, superuser):
    client.force_login(superuser)
    r = client.get(reverse("dashboard:rdv_overview"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_superuser_messaging_overview_200(client, superuser):
    client.force_login(superuser)
    r = client.get(reverse("dashboard:messaging_overview"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_admin_metier_dashboard_index_200(client, admin_user):
    client.force_login(admin_user)
    r = client.get(reverse("dashboard:index"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_admin_metier_services_list_200(client, admin_user):
    client.force_login(admin_user)
    r = client.get(reverse("dashboard:services_list"))
    assert r.status_code == 200
