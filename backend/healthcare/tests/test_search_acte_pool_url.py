"""URL de retrait d’examens sur la recherche (lot vs pool explicite)."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse

from healthcare.views import _search_url_with_acte_pool


def test_remove_url_drops_lot_param():
    """Réinjecter lot= réimposait tous les actes du lot ; le lien « × » ne devait pas le garder."""
    rf = RequestFactory()
    req = rf.get(
        "/sante/recherche/",
        {"sort": "price_asc", "acte": ["58", "59"], "lot": "1"},
    )
    url = _search_url_with_acte_pool(req, [58])
    assert "lot=" not in url
    assert "acte=58" in url
    assert "acte=59" not in url
    assert "sort=price_asc" in url


def test_canonical_search_route_serves_react_and_legacy_path_redirects():
    client = Client()

    canonical = client.get(reverse("healthcare:search"))
    legacy = client.get("/search?acte=58", follow=False)

    assert canonical.status_code == 200
    assert b'id="root"' in b"".join(canonical.streaming_content)
    assert legacy.status_code == 301
    assert legacy["Location"] == "/sante/recherche/?acte=58"


@patch("healthcare.views._acte_ids_from_lot_params")
def test_search_redirect_strips_lot_when_explicit_subset_of_lot(mock_lot_ids):
    """GET avec actes affinés + lot= : redirection sans lot= pour ne pas réétendre le périmètre."""
    mock_lot_ids.return_value = [58, 59, 60]
    c = Client()
    resp = c.get(
        reverse("healthcare:search_api"),
        {"sort": "price_asc", "acte": ["58", "59"], "lot": "1"},
    )
    assert resp.status_code == 200
    loc = resp.json()["redirect_url"]
    assert "lot=" not in loc
    assert "acte=58" in loc or "acte%3D58" in loc.replace("%2C", ",")


@pytest.mark.django_db
def test_search_api_returns_real_search_contract():
    response = Client().get(reverse("healthcare:search_api"), {"q": "aucun-resultat-attendu"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["results_count"] == 0
    assert payload["offers"] == []
    assert {"stats", "filters", "services", "families", "filter_options", "pagination"} <= payload.keys()


@pytest.mark.django_db
def test_search_api_returns_real_search_contract_for_authenticated_patient():
    patient = get_user_model().objects.create_user(
        username="patient_search_api",
        password="StrongPass!2026",
        user_type="patient",
    )
    client = Client()
    client.force_login(patient)

    response = client.get(reverse("healthcare:search_api"))

    assert response.status_code == 200
    assert {"stats", "filters", "services", "families", "filter_options", "pagination"} <= response.json().keys()
