"""Tests unitaires pour PricingService."""

from decimal import Decimal
from django.test import TestCase

from users.models import User
from healthcare.models import (
    ActeMedical,
    Assurance,
    OrganismeDeSante,
    PrestataireActe,
    PriseEnChargeAssurance,
    ServiceMedical,
)
from healthcare.services import PricingService


class PricingServiceTests(TestCase):
    def setUp(self):
        # Créer un User pour satisfaire le OneToOne obligatoire d'OrganismeDeSante
        self.user = User.objects.create_user(
            username="test_organisme",
            email="test@medcare.test",
            password="testpass123",
        )

        self.service = ServiceMedical.objects.create(
            name="Laboratoire Test",
            slug="laboratoire-test",
        )

        self.acte = ActeMedical.objects.create(
            name="NFS Test",
            service_medical_category=self.service,
            code="NFS_TEST_1",
        )

        self.org = OrganismeDeSante.objects.create(
            user=self.user,
            name="Clinique A Test",
        )

        self.assurance1 = Assurance.objects.create(name="AXA Test")
        self.assurance2 = Assurance.objects.create(name="Allianz Test")

        PriseEnChargeAssurance.objects.create(
            organisme=self.org,
            assurance=self.assurance1,
            is_active=True,
        )

        self.pa = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte,
            price=Decimal("10000"),
            price_ipm=Decimal("8000"),
            coverage_status_ipm="covered",
            price_assurance=Decimal("7500"),
            coverage_status_assurance="covered",
        )

    def test_pricing_comptant(self):
        res = PricingService.get_regime_info(self.pa, regime="comptant")
        self.assertEqual(res["regime"], "comptant")
        self.assertEqual(res["effective_price"], Decimal("10000"))
        self.assertEqual(res["status"], "covered")
        self.assertFalse(res["is_conventionne"])

    def test_pricing_ipm_covered(self):
        res = PricingService.get_regime_info(self.pa, regime="ipm")
        self.assertEqual(res["regime"], "ipm")
        self.assertEqual(res["price"], Decimal("8000"))
        self.assertEqual(res["effective_price"], Decimal("8000"))
        self.assertEqual(res["status"], "covered")
        self.assertTrue(res["is_conventionne"])

    def test_pricing_assurance_fallback_when_price_none(self):
        self.pa.price_assurance = None
        res = PricingService.get_regime_info(self.pa, regime="assurance")
        self.assertEqual(res["regime"], "assurance")
        self.assertIsNone(res["price"])
        self.assertEqual(res["effective_price"], Decimal("10000"))
        self.assertEqual(res["status"], "to_confirm")
        self.assertFalse(res["is_conventionne"])

    def test_attach_insurance_context_all_when_no_selection(self):
        PricingService.attach_insurance_context([self.pa], selected_insurance_ids=[])
        self.assertTrue(self.pa.dem_insurance_match)
        self.assertIn("AXA Test", self.pa.dem_insurance_names)

    def test_attach_insurance_context_filtering(self):
        # Filtrer sur assurance1 (AXA) -> match
        PricingService.attach_insurance_context([self.pa], selected_insurance_ids=[self.assurance1.pk])
        self.assertTrue(self.pa.dem_insurance_match)

        # Filtrer sur assurance2 (Allianz) -> no match
        PricingService.attach_insurance_context([self.pa], selected_insurance_ids=[self.assurance2.pk])
        self.assertFalse(self.pa.dem_insurance_match)
