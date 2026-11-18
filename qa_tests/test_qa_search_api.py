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
def test_recherche_acte_avec_resultats_affiche_les_structures(client, prestataire_acte):
    r = client.get(
        reverse("healthcare:search"),
        {"acte": prestataire_acte.acte_id},
    )
    assert r.status_code == 200
    assert prestataire_acte.organisme.name.encode() in r.content


@pytest.mark.django_db
def test_filtre_ville_dakar_exclut_les_autres_villes(
    client, prestataire_acte, subscription_plan
):
    from healthcare.models import OrganismeDeSante, PrestataireActe
    from users.models import User

    prestataire_acte.organisme.city = "Dakar"
    prestataire_acte.organisme.save(update_fields=["city"])
    autre_user = User.objects.create_user(
        username="qa_autre_ville",
        email="autre-ville@qa.test",
        password="test-pass-qa-123",
        user_type="prestataire",
    )
    autre_org = OrganismeDeSante.objects.create(
        user=autre_user,
        name="Structure QA Thiès",
        address="Thiès",
        city="Thiès",
        subscription_plan=subscription_plan,
        is_active=True,
        is_verified=True,
    )
    PrestataireActe.objects.create(
        organisme=autre_org,
        acte=prestataire_acte.acte,
        price=8000,
    )

    r = client.get(
        reverse("healthcare:search"),
        {"acte": prestataire_acte.acte_id, "city": "Dakar"},
    )
    assert r.status_code == 200
    assert prestataire_acte.organisme.name.encode() in r.content
    assert autre_org.name.encode() not in r.content


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
