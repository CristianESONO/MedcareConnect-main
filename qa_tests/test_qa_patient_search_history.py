"""Historique des recherches dans l'espace patient."""

import pytest
from django.urls import reverse

from healthcare.models import SearchHistory


@pytest.mark.django_db
def test_historique_patient_affiche_recherche_etat_vide_et_entrees(client, patient_user):
    SearchHistory.objects.create(
        user=patient_user,
        query="Bilan NFS QA",
        search_type="acte",
        results_count=3,
    )
    client.force_login(patient_user)

    response = client.get(
        reverse("users:patient_panel_tab", kwargs={"tab": "recherches"})
    )

    assert response.status_code == 200
    assert b"data-pac-history-search" in response.content
    assert b"data-pac-history-item" in response.content
    assert b"Bilan NFS QA" in response.content
    assert b"Aucune entr\xc3\xa9e ne correspond" in response.content
