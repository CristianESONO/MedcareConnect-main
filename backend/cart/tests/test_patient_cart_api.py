from django.test import TestCase
from django.urls import resolve, reverse
from django.http import HttpResponse
from unittest.mock import patch

from cart.models import Cart, CartItem
from healthcare.models import (
    ActeMedical,
    Assurance,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from users.models import User


class PatientCartApiTests(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(
            name="Plan patient cart API",
            slug="plan-patient-cart-api",
        )
        self.patient = User.objects.create_user(
            username="patient_cart_api",
            password="StrongPass!2026",
            user_type="patient",
        )
        provider = User.objects.create_user(
            username="provider_cart_api",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.organization = OrganismeDeSante.objects.create(
            user=provider,
            name="Structure panier API",
            address="Dakar",
            subscription_plan=plan,
            is_active=True,
            is_verified=True,
        )
        service = ServiceMedical.objects.create(name="Service panier API")
        act = ActeMedical.objects.create(
            name="Acte panier API",
            service_medical_category=service,
            level=3,
        )
        prestataire_acte = PrestataireActe.objects.create(
            organisme=self.organization,
            acte=act,
            price=5000,
        )
        self.cart = Cart.objects.create(patient=self.patient, status="active")
        self.item = CartItem.objects.create(
            cart=self.cart,
            prestataire_acte=prestataire_acte,
            quantity=2,
        )

    def test_patient_cart_api_requires_patient_authentication(self):
        response = self.client.get(reverse("cart:patient_cart_api"))
        self.assertEqual(response.status_code, 401)

        provider = User.objects.get(username="provider_cart_api")
        self.client.force_login(provider)
        response = self.client.get(reverse("cart:patient_cart_api"))
        self.assertEqual(response.status_code, 403)

    def test_patient_cart_api_returns_grouped_lines_and_totals(self):
        self.client.force_login(self.patient)

        response = self.client.get(reverse("cart:patient_cart_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["item_count"], 2)
        self.assertEqual(payload["total_brut"], "10000.00")
        self.assertEqual(len(payload["groups"]), 1)
        self.assertEqual(payload["groups"][0]["organization"], self.organization.name)
        self.assertEqual(
            payload["groups"][0]["lines"][0]["acte"],
            "Acte panier API",
        )
        self.assertEqual(payload["groups"][0]["lines"][0]["quantity"], 2)

    def test_patient_cart_actions_update_quantity_and_insurance_as_json(self):
        self.client.force_login(self.patient)

        quantity_response = self.client.post(
            reverse("cart:cart_update_quantity", args=[self.item.pk]),
            {"quantity": "3"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(quantity_response.status_code, 200)
        self.assertTrue(quantity_response.json()["ok"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 3)

        insurance = Assurance.objects.create(
            name="Assurance panier API",
            segment=Assurance.Segment.MUTUELLE,
        )
        insurance_response = self.client.post(
            reverse("cart:cart_select_insurance"),
            {"insurance": str(insurance.pk)},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(insurance_response.status_code, 200)
        self.assertTrue(insurance_response.json()["ok"])
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.selected_insurance_id, insurance.pk)

    def test_patient_cart_account_route_uses_react_shell(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("users:patient_panel_react_cart"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            resolve(reverse("users:patient_panel_react_cart")).func.__name__,
            "patient_panel_react_home",
        )

    def test_guest_cart_route_uses_react_shell(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            response = self.client.get(reverse("cart:cart_view"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"React")

    def test_guest_cart_api_returns_session_items_and_totals(self):
        session = self.client.session
        session["medcare_guest_cart_session_v1"] = {str(self.item.prestataire_acte_id): 2}
        session.save()

        response = self.client.get(reverse("cart:guest_cart_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["item_count"], 2)
        self.assertEqual(payload["total_brut"], "10000.00")
        self.assertEqual(payload["groups"][0]["organization"], self.organization.name)
        self.assertEqual(payload["groups"][0]["lines"][0]["quantity"], 2)

    def test_guest_cart_actions_accept_json_requests(self):
        session = self.client.session
        session["medcare_guest_cart_session_v1"] = {str(self.item.prestataire_acte_id): 1}
        session.save()

        quantity_response = self.client.post(
            reverse("cart:guest_cart_update_quantity", args=[self.item.prestataire_acte_id]),
            {"quantity": "3"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(quantity_response.status_code, 200)
        self.assertTrue(quantity_response.json()["ok"])

        insurance = Assurance.objects.create(
            name="Assurance visiteur",
            segment=Assurance.Segment.MUTUELLE,
        )
        insurance_response = self.client.post(
            reverse("cart:guest_cart_select_insurance"),
            {"insurance": str(insurance.pk)},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(insurance_response.status_code, 200)
        self.assertTrue(insurance_response.json()["ok"])

        guest_data = self.client.get(reverse("cart:guest_cart_api")).json()
        self.assertEqual(guest_data["groups"][0]["lines"][0]["quantity"], 3)
        self.assertEqual(guest_data["insurance_id"], insurance.pk)

    def test_cart_session_api_reports_account_roles(self):
        response = self.client.get(reverse("cart:cart_session_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": False,
                "is_patient": False,
                "is_prestataire": False,
                "is_praticien": False,
                "is_admin": False,
            },
        )

        self.client.force_login(self.patient)
        response = self.client.get(reverse("cart:cart_session_api"))
        self.assertEqual(
            response.json(),
            {
                "authenticated": True,
                "is_patient": True,
                "is_prestataire": False,
                "is_praticien": False,
                "is_admin": False,
            },
        )

        self.client.force_login(self.organization.user)
        response = self.client.get(reverse("cart:cart_session_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": True,
                "is_patient": False,
                "is_prestataire": True,
                "is_praticien": False,
                "is_admin": False,
            },
        )

        self.organization.account_nature = "praticien"
        self.organization.save(update_fields=["account_nature"])
        response = self.client.get(reverse("cart:cart_session_api"))
        self.assertTrue(response.json()["is_praticien"])

        admin = User.objects.create_user(
            username="admin_cart_api",
            password="StrongPass!2026",
            user_type="admin",
        )
        self.client.force_login(admin)
        response = self.client.get(reverse("cart:cart_session_api"))
        self.assertTrue(response.json()["is_admin"])
