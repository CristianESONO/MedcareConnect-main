from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from healthcare.models import (
    ActeMedical,
    ExamenPanel,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
)
from users.models import User


class PanelTemplateCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="practitioner_panel_templates",
            email="practitioner-panels@medcare.test",
            password="testpass123",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.user,
            name="Cabinet Panel Templates",
            city="Dakar",
            is_active=True,
            account_nature="praticien",
        )
        self.service = ServiceMedical.objects.create(name="Biologie médicale", order=1)
        self.client.force_login(self.user)

    def create_acte(self, name, reference_price=None):
        return ActeMedical.objects.create(
            name=name,
            service_medical_category=self.service,
            level=3,
            is_active=True,
            reference_price=reference_price,
        )

    def post_template(self, nom, kind, actes):
        return self.client.post(
            reverse("healthcare:panel_create"),
            {
                "nom": nom,
                "kind": kind,
                "acte_ids": ",".join(f"am_{acte.pk}" for acte in actes),
                "acte_noms": "|||".join(acte.name for acte in actes),
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_priced_template_creates_panel_and_ticket(self):
        nfs = self.create_acte("NFS / Hémogramme", Decimal("5000"))
        vih = self.create_acte("VIH Ag/Ac", Decimal("13500"))

        panel_response = self.post_template(
            "Bilan sanguin recommandé",
            ExamenPanel.KIND_PANEL,
            [nfs, vih],
        )

        self.assertEqual(panel_response.status_code, 200)
        self.assertTrue(panel_response.json()["ok"])
        panel = ExamenPanel.objects.get(nom="Bilan sanguin recommandé")
        self.assertSetEqual(
            set(panel.actes.values_list("acte__name", flat=True)),
            {nfs.name, vih.name},
        )

        ticket_response = self.post_template(
            "Ticket VIH",
            ExamenPanel.KIND_TICKET,
            [vih],
        )

        self.assertEqual(ticket_response.status_code, 200)
        self.assertTrue(ticket_response.json()["ok"])
        ticket = ExamenPanel.objects.get(nom="Ticket VIH")
        self.assertEqual(ticket.kind, ExamenPanel.KIND_TICKET)
        self.assertEqual(ticket.actes.count(), 1)

    def test_unpriced_template_act_fails_without_partial_records(self):
        nfs = self.create_acte("NFS tarifée", Decimal("5000"))
        unpriced = self.create_acte("Acte sans tarif")

        response = self.post_template(
            "Panel incomplet",
            ExamenPanel.KIND_PANEL,
            [nfs, unpriced],
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertIn(unpriced.name, response.json()["error"])
        self.assertFalse(ExamenPanel.objects.filter(nom="Panel incomplet").exists())
        self.assertFalse(PrestataireActe.objects.filter(organisme=self.org).exists())
