from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from healthcare.models import OrganismeDeSante, PrestationTicket, SearchHistory
from users.models import User


class ProviderSearchHistoryReactTests(TestCase):
    def setUp(self):
        self.provider = User.objects.create_user(
            username="provider_search_history_react",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(self.provider)
        SearchHistory.objects.create(
            user=self.provider,
            query="radiologie",
            results_count=3,
        )

    def test_provider_history_page_uses_react_and_api_returns_own_entries(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(reverse("healthcare:search_history"))
        response = self.client.get(reverse("healthcare:search_history_api"))

        self.assertEqual(page.content, b"React")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entries"][0]["query"], "radiologie")
        self.assertIn("/sante/recherche/", response.json()["entries"][0]["url"])


class PatientMobileReactTests(TestCase):
    def test_mobile_routes_serve_react(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            for path in ("/patient-mobile/", "/demo-patient/"):
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content, b"React")

    def test_mobile_api_returns_latest_active_ticket(self):
        provider_user = User.objects.create_user(
            username="mobile_ticket_provider",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        organization = OrganismeDeSante.objects.create(
            user=provider_user,
            name="Cabinet mobile",
            address="Dakar",
            is_active=True,
        )
        ticket = PrestationTicket.objects.create(
            organisme=organization,
            identifiant="mobile-ticket-public",
            title="Séance de kinésithérapie",
            price="12000",
        )

        response = self.client.get(reverse("patient_mobile_data_api"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ticket"]["token"], ticket.identifiant)
        self.assertEqual(response.json()["ticket"]["provider"]["name"], organization.name)
