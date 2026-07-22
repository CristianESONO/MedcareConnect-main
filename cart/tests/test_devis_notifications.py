"""devis.created → journal des notifications (même logique que la vue conversion panier)."""

from decimal import Decimal

from django.test import TestCase

from cart.models import Cart, CartItem, Devis
from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from notifications.dispatcher import dispatch
from notifications.models import NotificationEvent, NotificationLog
from users.models import User


class DevisCreatedDispatchTest(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Plan test devis",
            slug="plan-test-devis-tu",
        )
        self.prest = User.objects.create_user(
            username="presta_devis_tu",
            email="pd@example.com",
            password="x",
            user_type="prestataire",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.prest,
            name="Labo Devis TU",
            address="Dakar",
            subscription_plan=self.plan,
            is_active=True,
        )
        self.svc = ServiceMedical.objects.create(name="Svc Devis TU")
        self.acte = ActeMedical.objects.create(
            name="Prise de sang TU",
            service_medical_category=self.svc,
            level=3,
        )
        self.pa = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte,
            price=5000,
        )
        self.patient = User.objects.create_user(
            username="patient_devis_tu",
            email="patd@example.com",
            password="x",
            user_type="patient",
        )
        User.objects.create_user(
            username="admin_devis_tu",
            email="ad@example.com",
            password="x",
            user_type="admin",
        )
        self.cart = Cart.objects.create(patient=self.patient, status="active")
        CartItem.objects.create(cart=self.cart, prestataire_acte=self.pa, quantity=1)

    def test_devis_created_increments_logs(self):
        devis = Devis.objects.create(
            cart=self.cart,
            patient=self.patient,
            total_brut=Decimal("5000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("5000"),
            details=[],
            status="sent",
        )
        event = NotificationEvent.objects.get(code="devis.created")
        n0 = NotificationLog.objects.filter(event=event).count()
        dispatch(
            "devis.created",
            context={
                "devis": devis,
                "devis_part": None,
                "patient": self.patient,
                "organisme": self.org,
                "link": f"/cart/devis/{devis.reference}/",
                "link_prestataire": f"/healthcare/prestataire/devis/part/DP-TEST/",
            },
            actor=self.prest,
        )
        n1 = NotificationLog.objects.filter(event=event).count()
        self.assertGreater(n1, n0)
