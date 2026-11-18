"""
Contrôle d'accès — espace notifications admin (superadmin / admin seulement).
Scénario type testeur : patient et prestataire ne doivent pas accéder aux écrans internes.
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_anonyme_recoit_shell_react_mais_api_refuse(client):
    url = reverse("notifications:admin_settings")
    r = client.get(url, follow=False)
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/html")
    assert client.get(reverse("notifications:admin_settings_api")).status_code == 401


@pytest.mark.django_db
def test_patient_recoit_shell_react_mais_api_refuse(client, patient_user):
    client.force_login(patient_user)
    r = client.get(reverse("notifications:admin_settings"), follow=False)
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/html")
    assert client.get(reverse("notifications:admin_settings_api")).status_code == 403


@pytest.mark.django_db
def test_prestataire_recoit_shell_react_mais_api_refuse(client, prestataire_user):
    client.force_login(prestataire_user)
    r = client.get(reverse("notifications:admin_logs"), follow=False)
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/html")
    assert client.get(reverse("notifications:admin_logs_api")).status_code == 403


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
