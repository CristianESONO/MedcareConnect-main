"""WhatsApp depuis DevisPart : un wa.me distinct par structure."""

from decimal import Decimal
from urllib.parse import parse_qs, unquote, urlparse

from django.test import TestCase

from cart.models import Cart, Devis, DevisPart
from cart.whatsapp import wa_group_from_devis_part
from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from users.models import User


class DevisPartWhatsAppTest(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(name="P WA", slug="p-wa-tu")
        self.patient = User.objects.create_user(
            username="pat_wa_tu", email="pw@e.com", password="x", user_type="patient"
        )
        self.u1 = User.objects.create_user(
            username="pr1_wa", email="p1@e.com", password="x", user_type="prestataire"
        )
        self.u2 = User.objects.create_user(
            username="pr2_wa", email="p2@e.com", password="x", user_type="prestataire"
        )
        self.org1 = OrganismeDeSante.objects.create(
            user=self.u1,
            name="Struct Alpha WA",
            address="Dakar",
            subscription_plan=self.plan,
            is_active=True,
            whatsapp_number="+221701111111",
            contact_phone="+221701111111",
        )
        self.org2 = OrganismeDeSante.objects.create(
            user=self.u2,
            name="Struct Beta WA",
            address="Thiès",
            subscription_plan=self.plan,
            is_active=True,
            whatsapp_number="+221702222222",
            contact_phone="+221702222222",
        )
        svc = ServiceMedical.objects.create(name="S WA")
        a1 = ActeMedical.objects.create(name="Acte A", service_medical_category=svc, level=1)
        a2 = ActeMedical.objects.create(name="Acte B", service_medical_category=svc, level=1)
        self.cart = Cart.objects.create(patient=self.patient, status="converted")
        self.devis = Devis.objects.create(
            cart=self.cart,
            patient=self.patient,
            total_brut=Decimal("9000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("9000"),
            details=[],
            status="viewed",
        )
        d1 = [
            {
                "acte": "Acte A",
                "organisme": self.org1.name,
                "unit_price": "4000",
                "quantity": 1,
                "subtotal": "4000",
                "coverage_rate": None,
                "patient_cost": "4000",
            }
        ]
        d2 = [
            {
                "acte": "Acte B",
                "organisme": self.org2.name,
                "unit_price": "5000",
                "quantity": 1,
                "subtotal": "5000",
                "coverage_rate": None,
                "patient_cost": "5000",
            }
        ]
        self.part1 = DevisPart.objects.create(
            devis=self.devis,
            organisme=self.org1,
            details=d1,
            total_brut=Decimal("4000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("4000"),
            status="sent",
        )
        self.part2 = DevisPart.objects.create(
            devis=self.devis,
            organisme=self.org2,
            details=d2,
            total_brut=Decimal("5000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("5000"),
            status="sent",
        )

    def test_two_distinct_wa_me_urls(self):
        g1 = wa_group_from_devis_part(self.devis, self.part1)
        g2 = wa_group_from_devis_part(self.devis, self.part2)
        self.assertTrue(g1.has_whatsapp and g2.has_whatsapp)
        self.assertIn("wa.me/221701111111", g1.wa_url)
        self.assertIn("wa.me/221702222222", g2.wa_url)
        self.assertNotEqual(g1.wa_url, g2.wa_url)
        self.assertIn(self.devis.reference, g1.wa_url)
        self.assertIn(self.part1.reference, g1.wa_url)
        q = parse_qs(urlparse(g1.wa_url).query)
        body = unquote(q.get("text", [""])[0])
        self.assertIn("au sujet du devis", body)
        self.assertIn("Montant estimé à votre charge", body)
        self.assertIn("Struct Alpha WA", body)
        self.assertIn("Acte A", body)
