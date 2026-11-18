"""Admin — pages restantes (smoke GET) + modération complémentaire."""

import uuid

import pytest
from django.urls import reverse

from healthcare.models import PlatformReview


ADMIN_GET_PAGES = [
    "dashboard:users_list",
    "dashboard:organismes_list",
    "dashboard:services_list",
    "dashboard:actes_list",
    "dashboard:assurances_list",
    "dashboard:subscription_features_list",
    "dashboard:subscription_plans_list",
    "dashboard:subscriptions_overview",
    "dashboard:finances",
    "dashboard:pioneers_overview",
    "dashboard:bilans_overview",
    "dashboard:conformite",
    "dashboard:activite_overview",
    "dashboard:devis_overview",
    "dashboard:rdv_overview",
    "dashboard:messaging_overview",
    "dashboard:reviews_list",
    "dashboard:rdv_reminder_schedules_list",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", ADMIN_GET_PAGES)
def test_superuser_pages_admin_200(client, superuser, url_name):
    client.force_login(superuser)
    r = client.get(reverse(url_name))
    assert r.status_code == 200, url_name


@pytest.mark.django_db
def test_admin_organisme_detail_200(client, superuser, organisme_actif):
    client.force_login(superuser)
    r = client.get(reverse("dashboard:organisme_detail", args=[organisme_actif.pk]))
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/html")
    data = client.get(
        reverse("dashboard:admin_organization_detail_api", args=[organisme_actif.pk])
    )
    assert data.status_code == 200
    assert data.json()["organization"]["name"] == organisme_actif.name


@pytest.mark.django_db
def test_admin_supprime_avis(client, superuser, patient_user, prestataire_acte):
    review = PlatformReview.objects.create(
        patient=patient_user,
        rating=3,
        tarifs_delais_comment="À supprimer QA",
        is_approved=False,
    )
    review.actes.add(prestataire_acte.acte)
    client.force_login(superuser)
    url = reverse("dashboard:admin_review_action_api", args=[review.pk, "delete"])
    r = client.post(url)
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    assert not PlatformReview.objects.filter(pk=review.pk).exists()


@pytest.mark.django_db
def test_admin_cree_service_referentiel(client, superuser):
    client.force_login(superuser)
    name = f"Service QA {uuid.uuid4().hex[:6]}"
    r = client.post(
        "/admin/api/models/healthcare/servicemedical/form/",
        {"name": name, "order": 99, "is_active": True},
    )
    assert r.status_code == 200, r.content
    assert r.json()["ok"] is True
    from healthcare.models import ServiceMedical

    assert ServiceMedical.objects.filter(name=name).exists()
