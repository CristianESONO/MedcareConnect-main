"""Complément DevisPart pour devis sans sous-devis (affichage WhatsApp, prestataire)."""

from django.test import TestCase

from cart.devis_part_backfill import ensure_devis_has_parts
from cart.models import Cart, CartItem, Devis, DevisPart
from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from users.models import User


class EnsureDevisPartsBackfillTest(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Plan backfill",
            slug="plan-backfill-tu",
        )
        self.patient = User.objects.create_user(
            username="pat_backfill",
            email="pb@example.com",
            password="x",
            user_type="patient",
        )
        self.prest = User.objects.create_user(
            username="presta_bf",
            email="pr@example.com",
            password="x",
            user_type="prestataire",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.prest,
            name="Structure BF Exact",
            address="Dakar",
            subscription_plan=self.plan,
            is_active=True,
            whatsapp_number="+221770199999",
        )
        svc = ServiceMedical.objects.create(name="Svc bf")
        self.acte = ActeMedical.objects.create(
            name="Acte BF",
            service_medical_category=svc,
            level=2,
        )
        self.pa = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte,
            price=5000,
        )
        self.cart = Cart.objects.create(patient=self.patient, status="converted")
        CartItem.objects.create(cart=self.cart, prestataire_acte=self.pa, quantity=1)

    def test_creates_parts_from_details_when_missing(self):
        devis = Devis.objects.create(
            patient=self.patient,
            cart=self.cart,
            total_brut=5000,
            total_assurance=0,
            total_patient=5000,
            status="sent",
            details=[
                {
                    "acte": "Acte BF",
                    "organisme": "Structure BF Exact",
                    "unit_price": "5000.00",
                    "quantity": 1,
                    "subtotal": "5000.00",
                    "coverage_rate": None,
                    "patient_cost": "5000.00",
                }
            ],
        )
        self.assertEqual(devis.parts.count(), 0)
        n = ensure_devis_has_parts(devis)
        self.assertEqual(n, 1)
        self.assertEqual(devis.parts.count(), 1)
        part = devis.parts.get()
        self.assertTrue(part.reference.startswith("DP-"))
        self.assertEqual(part.organisme_id, self.org.pk)

    def test_idempotent(self):
        devis = Devis.objects.create(
            patient=self.patient,
            cart=self.cart,
            total_brut=5000,
            total_assurance=0,
            total_patient=5000,
            status="sent",
            details=[
                {
                    "acte": "Acte BF",
                    "organisme": "Structure BF Exact",
                    "unit_price": "5000.00",
                    "quantity": 1,
                    "subtotal": "5000.00",
                    "coverage_rate": None,
                    "patient_cost": "5000.00",
                }
            ],
        )
        ensure_devis_has_parts(devis)
        self.assertEqual(ensure_devis_has_parts(devis), 0)
        self.assertEqual(DevisPart.objects.filter(devis=devis).count(), 1)
