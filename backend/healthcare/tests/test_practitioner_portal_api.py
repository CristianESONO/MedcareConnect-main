from django.test import TestCase
from django.urls import reverse
from django.http import HttpResponse
from unittest.mock import patch

from healthcare.models import (
    ActeMedical,
    ExamenPanel,
    OrganismeDeSante,
    PractitionerAffiliation,
    PrestationTicket,
    PrestataireActe,
    ServiceMedical,
)
from users.models import User


class PractitionerPortalApiTests(TestCase):
    def setUp(self):
        self.practitioner_user = User.objects.create_user(
            username="practitioner_portal_api",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.practitioner = OrganismeDeSante.objects.create(
            user=self.practitioner_user,
            name="Cabinet API Praticien",
            account_nature="praticien",
            is_active=True,
        )
        self.structure_user = User.objects.create_user(
            username="structure_portal_api",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.structure = OrganismeDeSante.objects.create(
            user=self.structure_user,
            name="Clinique API Structure",
            is_active=True,
        )
        self.service = ServiceMedical.objects.create(name="Actes praticien API")
        self.act = ActeMedical.objects.create(
            name="Consultation praticien API",
            service_medical_category=self.service,
            level=3,
            reference_price=10000,
        )
        self.client.force_login(self.practitioner_user)

    def test_access_api_lists_structures_and_creates_affiliation_request(self):
        response = self.client.get(
            reverse("healthcare:prestataire_acces"),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.structure.name, [row["name"] for row in response.json()["available_structures"]])

        created = self.client.post(
            reverse("healthcare:prestataire_affiliation_create"),
            {
                "structure_id": self.structure.pk,
                "role_title": "Consultant",
                "days": ["Lundi"],
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(created.status_code, 201)
        affiliation = PractitionerAffiliation.objects.get(
            praticien=self.practitioner,
            structure=self.structure,
        )
        self.assertEqual(affiliation.status, "pending")
        self.assertEqual(affiliation.days_schedule, ["Lundi"])

    def test_practitioner_agenda_json_rejects_invalid_slots_and_saves_valid_ones(self):
        affiliation = PractitionerAffiliation.objects.create(
            praticien=self.practitioner,
            structure=self.structure,
            status="approved",
        )
        url = reverse("healthcare:agenda_praticien_edit", args=[affiliation.pk])
        initial = self.client.get(url, HTTP_ACCEPT="application/json")
        self.assertEqual(initial.status_code, 200)
        self.assertIn("Lundi_07:00", [
            f"{day}_{hour}"
            for day in initial.json()["days"]
            for hour in initial.json()["hours"]
        ])

        invalid = self.client.post(
            url,
            {"slots": ["Lundi_09:00", "Mardi_25:00", "Faux_10:00"]},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(invalid.status_code, 400)

        saved = self.client.post(
            url,
            {"slots": ["Lundi_09:00"]},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(saved.status_code, 200)
        affiliation.refresh_from_db()
        self.assertEqual(affiliation.days_schedule, ["Lundi : 09:00"])

    def test_ticket_api_validates_and_creates_a_practitioner_ticket(self):
        invalid = self.client.post(
            reverse("healthcare:prestataire_ticket_create"),
            {"title": "Consultation", "price": "n/a", "mode": "cabinet"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(PrestationTicket.objects.filter(organisme=self.practitioner).count(), 0)

        created = self.client.post(
            reverse("healthcare:prestataire_ticket_create"),
            {
                "title": "Consultation à domicile",
                "description": "Séance de suivi.",
                "price": "12000",
                "mode": "domicile",
                "acte_id": self.act.pk,
                "zone": "Dakar",
                "disponibilite": "Sur rendez-vous",
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(created.status_code, 201)
        ticket = PrestationTicket.objects.get(pk=created.json()["id"])
        self.assertEqual(ticket.organisme, self.practitioner)
        self.assertEqual(ticket.acte, self.act)

        listing = self.client.get(
            reverse("healthcare:prestataire_tickets"),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["tickets"][0]["title"], ticket.title)

    def test_panels_api_lists_real_panels_and_accepts_form_posts(self):
        self.client.force_login(self.structure_user)
        provider_act = PrestataireActe.objects.create(
            organisme=self.structure,
            acte=self.act,
            price=12500,
            is_available=True,
        )
        panel = ExamenPanel.objects.create(
            organisme=self.structure,
            nom="Panel réel",
            description="Bilan de test",
        )
        panel.actes.add(provider_act)

        response = self.client.get(
            reverse("healthcare:prestataire_panels"),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["panels"][0]["nom"], panel.nom)
        self.assertEqual(payload["panels"][0]["actes"][0]["nom"], self.act.name)
        self.assertTrue(any(act["nom"] == self.act.name for act in payload["acts"]))

        created = self.client.post(
            reverse("healthcare:panel_create"),
            {"nom": "Panel React", "kind": "panel", "acte_ids": str(provider_act.pk)},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(created.status_code, 200)
        self.assertTrue(ExamenPanel.objects.filter(pk=created.json()["id"], organisme=self.structure).exists())

        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(reverse("healthcare:prestataire_panels"))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.content, b"React")

    def test_public_ticket_and_panel_urls_serve_react_and_json_data(self):
        ticket = PrestationTicket.objects.create(
            organisme=self.practitioner,
            acte=self.act,
            identifiant="consultation-public-test",
            title="Consultation publique",
            description="Consultation de suivi.",
            price=12000,
            mode="cabinet",
        )
        ticket_url = reverse("patient_ticket_view", args=[ticket.identifiant])
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(ticket_url)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.content, b"React")
        payload = self.client.get(ticket_url, HTTP_ACCEPT="application/json").json()
        self.assertEqual(payload["title"], ticket.title)
        self.assertEqual(payload["provider"]["slug"], self.practitioner.slug)

        panel = ExamenPanel.objects.create(
            organisme=self.structure,
            nom="Panel public",
            description="Examens de contrôle.",
        )
        provider_act = PrestataireActe.objects.create(
            organisme=self.structure,
            acte=self.act,
            price=12500,
            is_available=True,
        )
        panel.actes.add(provider_act)
        panel_url = reverse("patient_ticket_view", args=[panel.token])
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            panel_page = self.client.get(panel_url)
        self.assertEqual(panel_page.status_code, 200)
        self.assertEqual(panel_page.content, b"React")
        panel_payload = self.client.get(panel_url, HTTP_ACCEPT="application/json").json()
        self.assertEqual(panel_payload["kind"], "panel")
        self.assertEqual(panel_payload["acts"][0]["name"], self.act.name)
