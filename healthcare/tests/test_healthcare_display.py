"""Tests unitaires pour les tags et filtres de template healthcare_display."""

from decimal import Decimal
from django.test import SimpleTestCase

from healthcare.templatetags.healthcare_display import (
    coverage_badge,
    delai_badge,
    fcfa,
    insurance_summary,
    org_status_badge,
)


class DummyOrg:
    def __init__(self, is_verified=True, is_pioneer_offer=False):
        self.is_verified = is_verified
        if is_pioneer_offer:
            self.subscription_plan = DummySub(is_pioneer_offer=True)
        else:
            self.subscription_plan = None


class DummySub:
    def __init__(self, is_pioneer_offer=False):
        self.is_pioneer_offer = is_pioneer_offer


class DummyPA:
    def __init__(self, delai_display):
        self._delai_display = delai_display

    def get_delai_display(self):
        return self._delai_display


class HealthcareDisplayTagsTests(SimpleTestCase):
    def test_fcfa_filter(self):
        self.assertEqual(fcfa(15000), "15 000 FCFA")
        self.assertEqual(fcfa(Decimal("125000.5")), "125 001 FCFA")
        self.assertEqual(fcfa(1000, suffix="F"), "1 000 F")
        self.assertEqual(fcfa(None), "")
        self.assertEqual(fcfa(""), "")

    def test_insurance_summary_filter(self):
        names = ["AXA", "Allianz", "Ascoma", "Gras Savoye", "Sunu"]
        self.assertEqual(insurance_summary(names, max_count=3), "AXA · Allianz · Ascoma +2")
        self.assertEqual(insurance_summary(["AXA", "Allianz"], max_count=3), "AXA · Allianz")
        self.assertEqual(insurance_summary([]), "Assurances non renseignées")
        self.assertEqual(insurance_summary(None), "Assurances non renseignées")

    def test_org_status_badge(self):
        unverified = DummyOrg(is_verified=False)
        self.assertIn("En attente d'approbation", org_status_badge(unverified))

        pioneer = DummyOrg(is_verified=True, is_pioneer_offer=True)
        self.assertIn("Pionnier", org_status_badge(pioneer))

        verified = DummyOrg(is_verified=True, is_pioneer_offer=False)
        self.assertIn("Vérifié", org_status_badge(verified))

    def test_coverage_badge(self):
        # 1 seul acte : pas de badge
        self.assertEqual(coverage_badge(1, 1), "")
        # Multi-actes : badge partiel
        badge_partial = coverage_badge(2, 3)
        self.assertIn("2/3 actes", badge_partial)
        self.assertIn("scard-coverage--partial", badge_partial)
        # Multi-actes : badge complet
        badge_full = coverage_badge(3, 3)
        self.assertIn("3/3 actes", badge_full)
        self.assertIn("scard-coverage--full", badge_full)

    def test_delai_badge(self):
        self.assertEqual(delai_badge(None), "")
        self.assertEqual(delai_badge(""), "")
        pa = DummyPA("24 heures")
        badge = delai_badge(pa)
        self.assertIn("24 heures", badge)
        self.assertIn("ti ti-clock", badge)
