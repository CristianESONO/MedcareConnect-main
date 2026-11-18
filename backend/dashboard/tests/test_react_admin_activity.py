import json
from datetime import timedelta
from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.utils import timezone

from appointments.models import RdvReminderSchedule, RendezVous
from cart.models import Devis, DevisPart
from dashboard import activity_api
from healthcare.models import OrganismeDeSante
from messaging.models import Conversation, Message
from users.models import User


class ReactAdminActivityApiTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(
            username="activity_admin", password="StrongPass!2026", user_type="admin"
        )
        self.patient = User.objects.create_user(
            username="activity_patient", password="StrongPass!2026", user_type="patient",
            email="patient@example.test",
        )
        self.provider = User.objects.create_user(
            username="activity_provider", password="StrongPass!2026", user_type="prestataire"
        )
        self.organization = OrganismeDeSante.objects.create(
            user=self.provider, name="Clinique activité", slug="clinique-activite"
        )

    def call_api(self, view, method="get", path="/api/", user=None, data=None, **kwargs):
        if method in ("post", "put", "patch"):
            request = getattr(self.factory, method)(
                path, data=json.dumps(data or {}), content_type="application/json"
            )
        else:
            request = getattr(self.factory, method)(path)
        request.user = user or self.admin
        return view(request, **kwargs)

    def response_json(self, response):
        return json.loads(response.content)

    def make_quote(self, reference_suffix, status="sent", patient=None):
        return Devis.objects.create(
            patient=patient or self.patient,
            total_brut=Decimal("12500"),
            total_patient=Decimal("10000"),
            total_assurance=Decimal("2500"),
            status=status,
            details=[{"acte": "Bilan", "organisme": self.organization.name, "subtotal": 12500}],
        )

    def test_api_uses_active_platform_admin_authorization_and_json_errors(self):
        anonymous_request = self.factory.get("/api/")
        from django.contrib.auth.models import AnonymousUser

        anonymous_request.user = AnonymousUser()
        response = activity_api.quotes_api(anonymous_request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.response_json(response), {"error": "Authentification requise."})

        self.patient.is_active = False
        self.patient.save(update_fields=["is_active"])
        response = self.call_api(activity_api.quotes_api, user=self.patient)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.response_json(response), {"error": "Accès réservé aux administrateurs."})

        response = self.call_api(activity_api.quotes_api, method="post")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(self.response_json(response)["error"], "Méthode HTTP non autorisée.")

    def test_quote_filters_counts_pagination_and_detail_payload(self):
        sent = self.make_quote("sent")
        self.make_quote("viewed", status="viewed")
        self.make_quote("draft", status="draft")

        response = self.call_api(
            activity_api.quotes_api,
            path="/api/?status=sent&q=activity_patient&page=1",
        )
        payload = self.response_json(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["counts"]["all"], 2)
        self.assertEqual(payload["counts"]["sent"], 1)
        self.assertEqual(payload["pagination"]["total"], 1)
        self.assertEqual(payload["rows"][0]["reference"], sent.reference)
        self.assertEqual(payload["rows"][0]["patient"]["email"], self.patient.email)

        detail = self.call_api(
            activity_api.quote_detail_api, path="/api/", reference=sent.reference
        )
        self.assertEqual(self.response_json(detail)["quote"]["details"][0]["acte"], "Bilan")

    def test_quote_relance_and_archive_preserve_parent_and_part_semantics(self):
        quote = self.make_quote("parts")
        part = DevisPart.objects.create(
            devis=quote,
            organisme=self.organization,
            details=[{"acte": "Bilan"}],
            total_brut=Decimal("12500"),
            total_patient=Decimal("10000"),
            total_assurance=Decimal("2500"),
        )
        response = self.call_api(
            activity_api.quote_action_api,
            method="post",
            path="/api/",
            reference=quote.reference,
            action="relance",
        )
        self.assertEqual(response.status_code, 200)
        part.refresh_from_db()
        quote.refresh_from_db()
        self.assertEqual(part.relance_count, 1)
        self.assertEqual(part.status, "relanced")
        self.assertEqual(quote.relance_count, 0)

        response = self.call_api(
            activity_api.quote_action_api,
            method="post",
            path="/api/",
            reference=quote.reference,
            action="archive",
        )
        self.assertEqual(response.status_code, 200)
        part.refresh_from_db()
        quote.refresh_from_db()
        self.assertTrue(part.is_archived)
        self.assertTrue(quote.is_archived)
        self.assertEqual(part.archived_reason, "Archivé par admin")

    def test_reminder_crud_is_scoped_to_global_schedules(self):
        global_schedule = RdvReminderSchedule.objects.create(
            label="Global", offset_value=2, offset_unit="days", organisme=None
        )
        local_schedule = RdvReminderSchedule.objects.create(
            label="Structure", offset_value=1, organisme=self.organization
        )
        response = self.call_api(activity_api.reminder_schedules_api)
        returned_ids = {row["id"] for row in self.response_json(response)["rows"]}
        self.assertIn(global_schedule.pk, returned_ids)
        self.assertNotIn(local_schedule.pk, returned_ids)

        created = self.call_api(
            activity_api.reminder_schedules_api,
            method="post",
            data={
                "label": "Rappel global",
                "offset_value": 30,
                "offset_unit": "minutes",
                "tolerance_minutes": 20,
                "include_prerequisites": False,
                "is_active": True,
                "order": 2,
                "actes": [],
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertIsNone(RdvReminderSchedule.objects.get(pk=self.response_json(created)["schedule"]["id"]).organisme_id)

        update_local = self.call_api(
            activity_api.reminder_schedule_detail_api,
            method="put",
            data={"label": "Do not touch"},
            pk=local_schedule.pk,
        )
        self.assertEqual(update_local.status_code, 404)
        self.assertEqual(self.response_json(update_local)["error"], "Règle de rappel globale introuvable.")

        delete_global = self.call_api(
            activity_api.reminder_schedule_detail_api,
            method="delete",
            pk=global_schedule.pk,
        )
        self.assertEqual(delete_global.status_code, 200)
        self.assertFalse(RdvReminderSchedule.objects.filter(pk=global_schedule.pk).exists())
        self.assertTrue(RdvReminderSchedule.objects.filter(pk=local_schedule.pk).exists())

    def test_appointment_filters_and_messaging_detail_are_read_only(self):
        rdv = RendezVous.objects.create(
            patient=self.patient,
            organisme=self.organization,
            start=timezone.now() + timedelta(days=1),
            status=RendezVous.STATUS_CONFIRMED,
        )
        appointment_result = self.call_api(
            activity_api.appointments_api,
            path="/api/?status=upcoming&q=activity_patient",
        )
        self.assertEqual(self.response_json(appointment_result)["pagination"]["total"], 1)
        appointment_detail = self.call_api(
            activity_api.appointment_detail_api, path="/api/", reference=rdv.reference
        )
        self.assertEqual(self.response_json(appointment_detail)["appointment"]["reference"], rdv.reference)

        conversation = Conversation.objects.create(
            patient=self.patient,
            prestataire=self.provider,
            subject="Suivi du dossier",
            kind=Conversation.KIND_GENERAL,
            thread_status=Conversation.STATUS_WAITING,
        )
        message = Message.objects.create(
            conversation=conversation,
            sender=self.patient,
            receiver=self.provider,
            content="Message confidentiel de test",
            is_read=False,
        )
        list_result = self.call_api(
            activity_api.messaging_api,
            path="/api/?kind=general&status=waiting&q=activity_patient",
        )
        self.assertEqual(self.response_json(list_result)["pagination"]["total"], 1)
        detail = self.call_api(
            activity_api.messaging_detail_api, path="/api/", pk=conversation.pk
        )
        self.assertEqual(self.response_json(detail)["messages"][0]["content"], message.content)
        message.refresh_from_db()
        self.assertFalse(message.is_read)

    def test_invalid_reminder_payload_returns_json_field_errors(self):
        response = self.call_api(
            activity_api.reminder_schedules_api,
            method="post",
            data={"label": "", "offset_unit": "weeks", "actes": "not-a-list"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("errors", self.response_json(response))
        self.assertIn("label", self.response_json(response)["errors"])
