from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import RendezVous
from appointments.slots import JOURS
from healthcare.models import OrganismeDeSante
from users.models import User


class ProviderAppointmentsApiTests(TestCase):
    def setUp(self):
        self.provider = User.objects.create_user(
            username="provider_appointments_api",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.patient = User.objects.create_user(
            username="patient_appointments_api",
            first_name="Awa",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.organization = OrganismeDeSante.objects.create(
            user=self.provider,
            name="Clinique RDV API",
            city="Dakar",
        )
        self.appointment = RendezVous.objects.create(
            patient=self.patient,
            organisme=self.organization,
            start=timezone.now() + timedelta(days=2),
            status=RendezVous.STATUS_REQUESTED,
            actes_snapshot=[{"acte": "CRP", "quantity": 2}],
            total_patient=Decimal("10000"),
        )

    def test_api_requires_authenticated_provider(self):
        url = reverse("appointments:prestataire_rdv_api")
        self.assertEqual(self.client.get(url).status_code, 401)

        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_api_filters_and_serializes_provider_appointments(self):
        self.client.force_login(self.provider)

        response = self.client.get(
            reverse("appointments:prestataire_rdv_api"),
            {"status": "requested", "view": "ticket"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["view_mode"], "ticket")
        self.assertEqual(payload["counts"]["requested"], 1)
        self.assertEqual(len(payload["appointments"]), 1)
        appointment = payload["appointments"][0]
        self.assertEqual(appointment["reference"], self.appointment.reference)
        self.assertEqual(appointment["patient"], "Awa")
        self.assertEqual(appointment["actes"][0]["acte"], "CRP")
        self.assertTrue(appointment["can_edit"])

    @patch("medcare_connect.views.react_app", return_value=HttpResponse("react"))
    def test_provider_appointment_list_route_serves_react(self, _react_app):
        self.client.force_login(self.provider)

        response = self.client.get(
            reverse("appointments:prestataire_rdv_list"),
            {"status": "requested"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"react")

    def test_api_does_not_expose_appointments_from_another_provider(self):
        other_provider = User.objects.create_user(
            username="other_provider_appointments_api",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        other_organization = OrganismeDeSante.objects.create(
            user=other_provider,
            name="Autre clinique",
        )
        RendezVous.objects.create(
            patient=self.patient,
            organisme=other_organization,
            start=timezone.now() + timedelta(days=3),
            status=RendezVous.STATUS_REQUESTED,
        )
        self.client.force_login(self.provider)

        response = self.client.get(reverse("appointments:prestataire_rdv_api"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["reference"] for row in response.json()["appointments"]],
            [self.appointment.reference],
        )

    def test_grid_api_requires_provider_and_returns_week_data(self):
        url = reverse("appointments:prestataire_agenda_api")
        self.assertEqual(self.client.get(url).status_code, 401)

        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.provider)
        response = self.client.get(
            url,
            {"date": timezone.localtime(self.appointment.start).date().isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["days"]), 7)
        self.assertIn(self.appointment.reference, payload["appointments"])
        self.assertEqual(len(payload["rows"][0]["cells"]), 7)

    @patch("medcare_connect.views.react_app", return_value=HttpResponse("react"))
    def test_grid_route_serves_react(self, _react_app):
        self.client.force_login(self.provider)

        response = self.client.get(reverse("appointments:prestataire_agenda"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"react")

    def test_grid_move_endpoint_reschedules_owned_appointment(self):
        self.organization.opening_hours = {
            day: {"open": "00:00", "close": "23:59", "closed": False}
            for day in JOURS
        }
        self.organization.save(update_fields=["opening_hours"])
        target_date = timezone.localdate() + timedelta(days=8)
        target = timezone.make_aware(datetime.combine(target_date, datetime.min.time().replace(hour=14)))
        self.client.force_login(self.provider)

        response = self.client.post(
            reverse(
                "appointments:prestataire_rdv_move",
                args=[self.appointment.reference],
            ),
            {"slot": target.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.appointment.refresh_from_db()
        self.assertEqual(timezone.localtime(self.appointment.start), timezone.localtime(target))

    def test_walk_in_creation_supports_json_and_rejects_invalid_slot(self):
        self.organization.opening_hours = {
            day: {"open": "00:00", "close": "23:59", "closed": False}
            for day in JOURS
        }
        self.organization.save(update_fields=["opening_hours"])
        target_date = timezone.localdate() + timedelta(days=8)
        target = timezone.make_aware(datetime.combine(target_date, datetime.min.time().replace(hour=10)))
        self.client.force_login(self.provider)

        invalid = self.client.post(
            reverse("appointments:prestataire_rdv_create"),
            {"slot": "not-a-date", "name": "Awa"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(invalid.status_code, 400)

        response = self.client.post(
            reverse("appointments:prestataire_rdv_create"),
            {
                "slot": target.isoformat(),
                "name": "Awa Diop",
                "phone": "770000000",
                "motif": "Consultation",
                "note": "Arrivée à l'accueil",
            },
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 201)
        appointment = RendezVous.objects.get(reference=response.json()["reference"])
        self.assertTrue(appointment.is_walk_in)
        self.assertEqual(appointment.walk_in_name, "Awa Diop")
