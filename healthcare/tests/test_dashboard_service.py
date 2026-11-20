"""Tests unitaires pour DashboardService."""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from users.models import User
from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ProfileView,
    ServiceMedical,
)
from cart.models import Cart, CartItem
from healthcare.services import DashboardService
from healthcare.views import _dashboard_completion, _organisme_profile_completion
from healthcare.prestataire_domicile import (
    parse_domicile_schedule,
    serialize_domicile_schedule,
)


class DashboardServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="org_dash_test",
            email="org_dash@medcare.test",
            password="testpass123",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.user,
            name="Clinique Dashboard Test",
            city="Dakar",
            is_active=True,
        )
        self.service = ServiceMedical.objects.create(name="Laboratoire")
        self.acte = ActeMedical.objects.create(
            name="Glycémie",
            service_medical_category=self.service,
        )
        self.pa = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte,
            price=Decimal("5000"),
        )

    def test_get_period_stats(self):
        ProfileView.objects.create(
            organisme=self.org,
            ip_address="127.0.0.1",
        )
        cart = Cart.objects.create(patient=self.user)
        CartItem.objects.create(
            cart=cart,
            prestataire_acte=self.pa,
            quantity=1,
        )

        stats = DashboardService.get_period_stats(self.org)
        self.assertEqual(stats["views_period"], 1)
        self.assertEqual(stats["items_period"], 1)

    def test_get_top_actes(self):
        cart = Cart.objects.create(patient=self.user)
        CartItem.objects.create(
            cart=cart,
            prestataire_acte=self.pa,
            quantity=1,
        )
        items_qs = CartItem.objects.filter(prestataire_acte__organisme=self.org)
        rows, max_n = DashboardService.get_top_actes(items_qs, limit=5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(max_n, 1)
        self.assertEqual(rows[0]["prestataire_acte__acte__name"], "Glycémie")

    def test_get_rdv_counts(self):
        counts = DashboardService.get_rdv_counts(self.org)
        self.assertIn("rdv_requested_count", counts)
        self.assertIn("rdv_upcoming_count", counts)
        self.assertEqual(counts["rdv_requested_count"], 0)

    def test_build_context_keys(self):
        ctx = DashboardService.build_context(
            self.org,
            period_key="30j",
            period_label="30 derniers jours",
        )
        self.assertEqual(ctx["org"], self.org)
        self.assertEqual(ctx["dash_active"], "home")
        self.assertEqual(ctx["period_key"], "30j")
        self.assertEqual(ctx["period_label"], "30 derniers jours")
        self.assertIn("completion_pct", ctx)
        self.assertIn("activity_chart", ctx)

    def test_practitioner_dashboard_completion_matches_profile_edit(self):
        self.org.account_nature = "praticien"
        self.org.profession = "Médecin"
        self.org.ordre_numero = "ONMS-123"
        self.org.description = "Présentation professionnelle suffisamment détaillée."
        self.org.contact_phone = "+221770000000"

        completion = _dashboard_completion(self.org, actes_count=1, insurances_count=0)
        completion_pct = round(
            sum(1 for step in completion if step["ok"]) * 100.0 / len(completion)
        )

        self.assertEqual(completion_pct, _organisme_profile_completion(self.org))

    def test_domicile_schedule_json_round_trip(self):
        schedule = {
            "lundi": {"closed": False, "open": "08:00", "close": "17:00"},
            "dimanche": {"closed": True, "open": "", "close": ""},
        }
        encoded = serialize_domicile_schedule(schedule)
        parsed = parse_domicile_schedule(encoded)
        self.assertEqual(parsed["lundi"]["open"], "08:00")
        self.assertTrue(parsed["dimanche"]["closed"])
