from decimal import Decimal
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, Devis
from users.models import User


class LegacyCartReactTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="provider_legacy_cart",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.other_user = User.objects.create_user(
            username="other_legacy_cart",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.devis = Devis.objects.create(
            patient=self.user,
            total_brut=Decimal("12000"),
            total_assurance=Decimal("2000"),
            total_patient=Decimal("10000"),
            details=[{
                "acte": "Bilan sanguin",
                "organisme": "Centre Santé",
                "quantity": 1,
                "subtotal": "12000",
                "coverage_rate": "16.67",
                "patient_cost": "10000",
            }],
        )
        Cart.objects.create(patient=self.user, status="saved")

    def test_legacy_pages_serve_react_for_non_patient_accounts(self):
        self.client.force_login(self.user)
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            for url in (
                reverse("cart:cart_view"),
                reverse("cart:devis_list"),
                reverse("cart:devis_detail", args=[self.devis.reference]),
                reverse("cart:cart_history"),
            ):
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content, b"React")

    def test_account_cart_api_serves_non_patient_account(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("cart:account_cart_api"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["item_count"], 0)

    def test_account_quote_apis_are_authenticated_and_scoped_to_owner(self):
        quotes_url = reverse("cart:account_devis_api")
        detail_url = reverse("cart:account_devis_detail_api", args=[self.devis.reference])
        self.assertEqual(self.client.get(quotes_url).status_code, 401)

        self.client.force_login(self.user)
        quotes = self.client.get(quotes_url)
        self.assertEqual(quotes.status_code, 200)
        self.assertEqual(quotes.json()["entries"][0]["reference"], self.devis.reference)

        detail = self.client.get(detail_url)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["devis"]["details"][0]["acte"], "Bilan sanguin")

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

    def test_cart_history_api_returns_only_closed_carts_for_current_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cart:cart_history_api"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["entries"]), 1)
        self.assertEqual(response.json()["entries"][0]["status_code"], "saved")
