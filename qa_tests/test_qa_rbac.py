"""
Contrôle d'accès — espace notifications admin (superadmin / admin seulement).
Scénario type testeur : patient et prestataire ne doivent pas accéder aux écrans internes.
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_anonyme_redirige_vers_login(client):
    url = reverse("notifications:admin_settings")
    r = client.get(url, follow=False)
    assert r.status_code == 302
    assert "connexion" in (r.url or "").lower()


@pytest.mark.django_db
def test_patient_redirige_vers_accueil(client, patient_user):
    client.force_login(patient_user)
    r = client.get(reverse("notifications:admin_settings"), follow=False)
    assert r.status_code == 302
    assert r.url == reverse("home")


@pytest.mark.django_db
def test_prestataire_redirige_vers_accueil(client, prestataire_user):
    client.force_login(prestataire_user)
    r = client.get(reverse("notifications:admin_logs"), follow=False)
    assert r.status_code == 302
    assert r.url == reverse("home")


@pytest.mark.django_db
def test_admin_metier_accede_aux_regles(client, admin_user):
    client.force_login(admin_user)
    r = client.get(reverse("notifications:admin_rules"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_superuser_accede_aux_logs(client, superuser):
    client.force_login(superuser)
    r = client.get(reverse("notifications:admin_logs"))
    assert r.status_code == 200
