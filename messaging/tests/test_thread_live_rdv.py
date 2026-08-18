"""Tests fil messagerie — prise de RDV vs RDV déjà actif."""
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import RendezVous
from cart.models import Devis, DevisPart
from healthcare.models import ActeMedical, OrganismeDeSante, ServiceMedical, SubscriptionPlan
from messaging.models import Conversation
from users.models import User


class ThreadBookingWhenRdvLiveTest(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name="Plan msg", slug="plan-msg")
        self.prest = User.objects.create_user(
            username="prest_msg_qa", password="x", user_type="prestataire"
        )
        self.patient = User.objects.create_user(
            username="patient_msg_qa", password="x", user_type="patient"
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.prest,
            name="Clinique Msg QA",
            address="Dakar",
            subscription_plan=plan,
            is_active=True,
            opening_hours={"mon": [["08:00", "18:00"]]},
        )
        svc = ServiceMedical.objects.create(name="Labo")
        ActeMedical.objects.create(name="NFS", service_medical_category=svc, level=3)
        devis = Devis.objects.create(
            patient=self.patient,
            total_brut=1000,
            total_patient=1000,
            details=[{"acte": "NFS", "quantity": 1}],
        )
        self.part = DevisPart.objects.create(
            devis=devis,
            organisme=self.org,
            total_brut=1000,
            total_patient=1000,
            details=[{"acte": "NFS", "quantity": 1}],
        )
        self.rdv = RendezVous.objects.create(
            patient=self.patient,
            organisme=self.org,
            devis=devis,
            devis_part=self.part,
            start=timezone.now() + timedelta(days=1),
            status=RendezVous.STATUS_CONFIRMED,
        )
        self.conv = Conversation.objects.create(
            patient=self.patient,
            prestataire=self.prest,
            devis_part=self.part,
            rendez_vous=self.rdv,
            subject="Test",
            kind=Conversation.KIND_RDV,
        )
        self.client = Client()
        self.client.force_login(self.patient)

    def test_confirmed_rdv_shows_cancel_not_book_footer(self):
        url = reverse("messaging:conversation_detail", args=[self.conv.pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Annuler le RDV")
        self.assertNotContains(r, "Prendre RDV")
        self.assertNotContains(r, "Prendre un rendez-vous")

    def test_book_query_redirects_when_rdv_confirmed(self):
        url = reverse("messaging:conversation_detail", args=[self.conv.pk]) + "?book=1"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("messaging:conversation_detail", args=[self.conv.pk]))

    def test_prestataire_can_send_attachment_in_conversation(self):
        self.client.force_login(self.prest)
        url = reverse("messaging:conversation_detail", args=[self.conv.pk])
        file = SimpleUploadedFile("report.pdf", b"pdf-bytes", content_type="application/pdf")

        response = self.client.post(
            url,
            {
                "content": "Voici le rapport médical.",
                "attachment": file,
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.conv.messages.filter(
                sender=self.prest,
                content="Voici le rapport médical.",
            ).exists()
        )
        attachment_msg = self.conv.messages.filter(sender=self.prest).latest("timestamp")
        self.assertTrue(attachment_msg.attachment)
        self.assertTrue(attachment_msg.attachment.name.endswith("report.pdf") or "report" in attachment_msg.attachment.name)
