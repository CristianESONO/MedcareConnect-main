"""Tests bilan KPI prestataire."""

from django.test import TestCase

from healthcare.models import OrganismeDeSante, ProfileView, SubscriptionPlan, TypeOrganisme
from healthcare.prestataire_bilan import build_pioneer_bilan
from users.models import User


class PioneerBilanTests(TestCase):
    def setUp(self):
        self.presta = User.objects.create_user(
            username="presta_bilan",
            email="pb@e.com",
            password="x",
            user_type="prestataire",
        )
        self.type_org = TypeOrganisme.objects.create(name="Labo", slug="labo-bilan")
        self.plan = SubscriptionPlan.objects.create(
            name="Pionnier TU",
            slug="pionnier-tu-bilan",
            is_pioneer_offer=True,
        )
        self.essentiel, _ = SubscriptionPlan.objects.get_or_create(
            slug="essentiel",
            defaults={
                "name": "Essentiel TU",
                "is_public": True,
                "monthly_price_fcfa": 39000,
                "order": 20,
            },
        )
        self.pro, _ = SubscriptionPlan.objects.get_or_create(
            slug="pro",
            defaults={
                "name": "Pro TU",
                "is_public": True,
                "monthly_price_fcfa": 69000,
                "order": 30,
            },
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.presta,
            name="Lab Bilan",
            slug="lab-bilan",
            city="Dakar",
            address="Dakar",
            type_organisme=self.type_org,
            subscription_plan=self.plan,
        )

    def test_bilan_sections_structure(self):
        ProfileView.objects.create(organisme=self.org, source=ProfileView.SOURCE_NFC)
        ProfileView.objects.create(organisme=self.org, source=ProfileView.SOURCE_ANNUAIRE)
        bilan = build_pioneer_bilan(self.org)
        self.assertEqual(len(bilan["section_a"]), 4)
        self.assertEqual(len(bilan["section_b"]), 4)
        self.assertEqual(len(bilan["section_c"]), 3)
        self.assertIn("signal", bilan["section_a"][0])
        self.assertEqual(bilan["section_a"][1]["val"], "1")

    def test_recommended_pro_when_roi_high(self):
        from cart.models import Cart, Devis, DevisPart
        from decimal import Decimal

        patient = User.objects.create_user(
            username="pat_bilan", email="p@e.com", password="x", user_type="patient"
        )
        cart = Cart.objects.create(patient=patient, status="converted")
        devis = Devis.objects.create(
            cart=cart,
            patient=patient,
            total_brut=Decimal("200000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("200000"),
            details=[],
            status="sent",
        )
        DevisPart.objects.create(
            devis=devis,
            organisme=self.org,
            reference="DP-BILAN-1",
            total_brut=Decimal("200000"),
            total_patient=Decimal("200000"),
            details=[],
            status="sent",
        )
        bilan = build_pioneer_bilan(self.org)
        self.assertGreaterEqual(bilan["roi_ratio"], 2)
        self.assertEqual(bilan["recommended_slug"], "pro")
