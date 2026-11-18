"""Connexion vue prestataire → dispatch acte.disabled."""

from django.test import Client, TestCase
from django.urls import reverse

from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from notifications.models import NotificationLog, NotificationEvent
from users.models import User


class ActeToggleNotificationTest(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Plan test TU",
            slug="plan-test-tu-acte",
        )
        self.prest_user = User.objects.create_user(
            username="presta_tu",
            email="presta_tu@example.com",
            password="secret123",
            user_type="prestataire",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.prest_user,
            name="Centre TU",
            address="Dakar",
            subscription_plan=self.plan,
            is_active=True,
        )
        self.svc = ServiceMedical.objects.create(name="Service TU Acte")
        self.acte = ActeMedical.objects.create(
            name="Acte TU Toggle",
            service_medical_category=self.svc,
            level=3,
        )
        self.pa = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte,
            price=10000,
            is_available=True,
        )
        User.objects.create_user(
            username="admin_tu_acte",
            email="admin_tu_acte@example.com",
            password="secret123",
            user_type="admin",
        )

    def test_toggle_off_creates_notification_log(self):
        event = NotificationEvent.objects.get(code="acte.disabled")
        n0 = NotificationLog.objects.filter(event=event).count()
        client = Client()
        self.assertTrue(client.login(username="presta_tu", password="secret123"))
        url = reverse("healthcare:acte_toggle_available", args=[self.pa.pk])
        response = client.post(url, {"next": reverse("healthcare:actes_list")})
        self.assertEqual(response.status_code, 302)
        self.pa.refresh_from_db()
        self.assertFalse(self.pa.is_available)
        n1 = NotificationLog.objects.filter(event=event).count()
        self.assertGreater(n1, n0)

    def test_toggle_on_does_not_log_disabled_event(self):
        self.pa.is_available = False
        self.pa.save(update_fields=["is_available"])
        event = NotificationEvent.objects.get(code="acte.disabled")
        n0 = NotificationLog.objects.filter(event=event).count()
        client = Client()
        self.assertTrue(client.login(username="presta_tu", password="secret123"))
        url = reverse("healthcare:acte_toggle_available", args=[self.pa.pk])
        client.post(url, {"next": reverse("healthcare:actes_list")})
        self.pa.refresh_from_db()
        self.assertTrue(self.pa.is_available)
        n1 = NotificationLog.objects.filter(event=event).count()
        self.assertEqual(n1, n0)
