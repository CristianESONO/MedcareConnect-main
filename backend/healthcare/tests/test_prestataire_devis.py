"""Vue devis prestataire — KPI, filtres, actions RDV."""

from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone

from appointments.models import RendezVous
from cart.models import Cart, Devis, DevisPart
from healthcare.models import OrganismeDeSante, SubscriptionPlan
from healthcare.prestataire_devis import prestataire_devis_rows
from users.models import User


class PrestataireDevisViewTest(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(name="P Devis", slug="p-devis-tu")
        self.presta = User.objects.create_user(
            username="presta_devis",
            email="pd@e.com",
            password="x",
            user_type="prestataire",
        )
        self.patient = User.objects.create_user(
            username="pat_devis",
            email="pat@e.com",
            password="x",
            user_type="patient",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.presta,
            name="Clinique Devis TU",
            address="Dakar",
            subscription_plan=self.plan,
            is_active=True,
        )
        cart = Cart.objects.create(patient=self.patient, status="converted")
        self.devis = Devis.objects.create(
            cart=cart,
            patient=self.patient,
            total_brut=Decimal("12000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("12000"),
            details=[],
            status="sent",
        )
        self.part = DevisPart.objects.create(
            devis=self.devis,
            organisme=self.org,
            details=[{"acte": "NFS", "quantity": 1, "subtotal": "12000"}],
            total_brut=Decimal("12000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("12000"),
            status="sent",
        )
        self.client = Client(HTTP_HOST="localhost", secure=True)

    def test_list_requires_login(self):
        r = self.client.get(reverse("healthcare:prestataire_devis_list"), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("connexion", r.request["PATH_INFO"])

    def test_list_shows_kpi_and_card(self):
        self.client.force_login(self.presta)
        r = self.client.get(reverse("healthcare:prestataire_devis_api"))
        self.assertEqual(r.status_code, 200)
        payload = r.json()
        self.assertEqual(payload["kpis"]["active"], 1)
        self.assertEqual(payload["entries"][0]["reference"], self.part.reference)
        self.assertTrue(payload["entries"][0]["can_relance"])

    @patch("medcare_connect.views.react_app", return_value=HttpResponse("react"))
    def test_list_route_serves_react(self, _react_app):
        self.client.force_login(self.presta)

        response = self.client.get(reverse("healthcare:prestataire_devis_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"react")

    def test_devis_api_requires_provider_authentication(self):
        url = reverse("healthcare:prestataire_devis_api")
        self.assertEqual(self.client.get(url).status_code, 401)

        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_actes_catalogue_loads(self):
        self.client.force_login(self.presta)

        response = self.client.get("/sante/prestataire/actes/")

        self.assertEqual(response.status_code, 200)

    def test_row_enrichment_pending_rdv(self):
        start = timezone.now() + timezone.timedelta(days=2)
        RendezVous.objects.create(
            patient=self.patient,
            organisme=self.org,
            devis=self.devis,
            devis_part=self.part,
            start=start,
            status=RendezVous.STATUS_REQUESTED,
            total_brut=Decimal("12000"),
            total_patient=Decimal("12000"),
        )
        row = prestataire_devis_rows([self.part])[0]
        self.assertTrue(row["show_confirm"])
        self.assertFalse(row["show_relance"])
        self.assertTrue(row["has_creneau"])

    def test_confirm_rdv_from_list(self):
        start = timezone.now() + timezone.timedelta(days=2)
        rdv = RendezVous.objects.create(
            patient=self.patient,
            organisme=self.org,
            devis=self.devis,
            devis_part=self.part,
            start=start,
            status=RendezVous.STATUS_REQUESTED,
            total_brut=Decimal("12000"),
            total_patient=Decimal("12000"),
        )
        self.client.force_login(self.presta)
        url = reverse("appointments:prestataire_rdv_action", args=[rdv.reference])
        r = self.client.post(
            url,
            {"action": "confirm", "next": reverse("healthcare:prestataire_devis_list")},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        rdv.refresh_from_db()
        self.assertEqual(rdv.status, RendezVous.STATUS_CONFIRMED)

    def test_detail_marks_viewed(self):
        self.client.force_login(self.presta)
        url = reverse("healthcare:prestataire_devis_part_api", args=[self.part.reference])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entry"]["reference"], self.part.reference)
        self.part.refresh_from_db()
        self.assertEqual(self.part.status, "viewed")

    def test_filter_accepted(self):
        start = timezone.now() + timezone.timedelta(days=2)
        RendezVous.objects.create(
            patient=self.patient,
            organisme=self.org,
            devis=self.devis,
            devis_part=self.part,
            start=start,
            status=RendezVous.STATUS_CONFIRMED,
            total_brut=Decimal("12000"),
            total_patient=Decimal("12000"),
        )
        self.client.force_login(self.presta)
        r = self.client.get(reverse("healthcare:prestataire_devis_api"), {"status": "accepted"})
        self.assertEqual(r.status_code, 200)
        payload = r.json()
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["reference"], self.part.reference)
        self.assertTrue(payload["entries"][0]["is_accepted"])

    def test_accepted_filter_excludes_archived_parts(self):
        self.part.status = "archived"
        self.part.save(update_fields=["status"])
        RendezVous.objects.create(
            patient=self.patient,
            organisme=self.org,
            devis=self.devis,
            devis_part=self.part,
            start=timezone.now() + timezone.timedelta(days=2),
            status=RendezVous.STATUS_CONFIRMED,
            total_brut=Decimal("12000"),
            total_patient=Decimal("12000"),
        )
        self.client.force_login(self.presta)

        response = self.client.get(
            reverse("healthcare:prestataire_devis_api"), {"status": "accepted"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entries"], [])

    def test_prestataire_relance_sous_devis(self):
        self.client.force_login(self.presta)
        url = reverse("healthcare:prestataire_devis_relance", args=[self.part.reference])
        r = self.client.post(url, {"status": "active"}, follow=False)
        self.assertEqual(r.status_code, 302)
        self.part.refresh_from_db()
        self.assertEqual(self.part.relance_count, 1)

    def test_prestataire_relance_returns_json_for_react(self):
        self.client.force_login(self.presta)
        url = reverse("healthcare:prestataire_devis_relance", args=[self.part.reference])
        response = self.client.post(url, {"status": "active"}, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.part.refresh_from_db()
        self.assertEqual(self.part.relance_count, 1)

    def test_prestataire_archive_sous_devis(self):
        self.client.force_login(self.presta)
        url = reverse("healthcare:prestataire_devis_archiver", args=[self.part.reference])
        r = self.client.post(url, {"status": "active"}, follow=False)
        self.assertEqual(r.status_code, 302)
        self.part.refresh_from_db()
        self.assertTrue(self.part.is_archived)

    def test_prestataire_refuse_rdv_depuis_devis(self):
        start = timezone.now() + timezone.timedelta(days=2)
        rdv = RendezVous.objects.create(
            patient=self.patient,
            organisme=self.org,
            devis=self.devis,
            devis_part=self.part,
            start=start,
            status=RendezVous.STATUS_REQUESTED,
            total_brut=Decimal("12000"),
            total_patient=Decimal("12000"),
        )
        self.client.force_login(self.presta)
        url = reverse("appointments:prestataire_rdv_action", args=[rdv.reference])
        r = self.client.post(url, {"action": "decline", "note": "Complet"}, follow=True)
        self.assertEqual(r.status_code, 200)
        rdv.refresh_from_db()
        self.assertEqual(rdv.status, RendezVous.STATUS_DECLINED)
