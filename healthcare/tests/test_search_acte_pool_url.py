"""URL de retrait d’examens sur la recherche (lot vs pool explicite)."""

from unittest.mock import patch

from django.test import Client, RequestFactory
from django.urls import reverse

from healthcare.views import _search_url_with_acte_pool


def test_remove_url_drops_lot_param():
    """Réinjecter lot= réimposait tous les actes du lot ; le lien « × » ne devait pas le garder."""
    rf = RequestFactory()
    req = rf.get(
        "/healthcare/search/",
        {"sort": "price_asc", "acte": ["58", "59"], "lot": "1"},
    )
    url = _search_url_with_acte_pool(req, [58])
    assert "lot=" not in url
    assert "acte=58" in url
    assert "acte=59" not in url
    assert "sort=price_asc" in url


@patch("healthcare.views._acte_ids_from_lot_params")
def test_search_redirect_strips_lot_when_explicit_subset_of_lot(mock_lot_ids):
    """GET avec actes affinés + lot= : redirection sans lot= pour ne pas réétendre le périmètre."""
    mock_lot_ids.return_value = [58, 59, 60]
    c = Client()
    resp = c.get(
        reverse("healthcare:search"),
        {"sort": "price_asc", "acte": ["58", "59"], "lot": "1"},
    )
    assert resp.status_code == 302
    loc = resp["Location"]
    assert "lot=" not in loc
    assert "acte=58" in loc or "acte%3D58" in loc.replace("%2C", ",")
