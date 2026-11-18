from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from appointments.models import RendezVous
from cart.models import Devis, DevisPart
from healthcare.models import OrganismeDeSante, SubscriptionPlan
from users.models import User


class PatientAppointmentsApiTests(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(
            name="Plan patient RDV API",
            slug="plan-patient-rdv-api",
        )
        self.provider = User.objects.create_user(
            username="provider_patient_rdv_api",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.patient = User.objects.create_user(
            username="patient_rdv_api",
            first_name="Awa",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.organization = OrganismeDeSante.objects.create(
            user=self.provider,
            name="Clinique RDV API",
            address="Dakar",
            city="Dakar",
            quartier="Mermoz",
            subscription_plan=plan,
            is_active=True,
            is_verified=True,
        )
        self.appointment = RendezVous.objects.create(
            patient=self.patient,
            organisme=self.organization,
            start=timezone.now() + timedelta(days=2),
            status=RendezVous.STATUS_REQUESTED,
            actes_snapshot=[
                {"acte": "CRP", "quantity": 2, "subtotal": "10000"}
            ],
            total_brut=Decimal("10000"),
            total_patient=Decimal("10000"),
        )

    def test_api_requires_patient_authentication(self):
        response = self.client.get(reverse("appointments:patient_appointments_api"))

        self.assertEqual(response.status_code, 401)

    def test_api_returns_only_patient_appointments_and_actions(self):
        self.client.force_login(self.patient)

        response = self.client.get(reverse("appointments:patient_appointments_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["upcoming"]), 1)
        appointment = payload["upcoming"][0]
        self.assertEqual(appointment["reference"], self.appointment.reference)
        self.assertEqual(appointment["acts"][0]["name"], "CRP")
        self.assertEqual(appointment["acts"][0]["quantity"], 2)
        self.assertTrue(appointment["can_cancel"])
        self.assertTrue(appointment["can_reschedule"])
        self.assertEqual(payload["past"], [])

    def test_patient_can_cancel_through_json_response(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse(
                "appointments:patient_cancel",
                kwargs={"ref": self.appointment.reference},
            ),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, RendezVous.STATUS_CANCELLED)

    def test_non_patient_cannot_read_patient_appointments(self):
        self.client.force_login(self.provider)

        response = self.client.get(reverse("appointments:patient_appointments_api"))

        self.assertEqual(response.status_code, 403)

    def test_booking_page_uses_react_shell_and_exposes_slots_as_json(self):
        devis = Devis.objects.create(
            patient=self.patient,
            total_brut=Decimal("10000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("10000"),
            details=[],
        )
        part = DevisPart.objects.create(
            devis=devis,
            organisme=self.organization,
            details=[{"acte": "CRP", "quantity": 1, "subtotal": "10000"}],
            total_brut=Decimal("10000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("10000"),
            status="sent",
        )
        self.client.force_login(self.patient)

        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(
                reverse("appointments:patient_book", args=[part.reference])
            )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.content, b"React")

        response = self.client.get(
            reverse("appointments:patient_book", args=[part.reference]),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["booking_data"]["part"], part.reference)
        self.assertEqual(payload["booking_data"]["org"], self.organization.name)
        self.assertEqual(payload["submit_url"], reverse("appointments:patient_book", args=[part.reference]))
