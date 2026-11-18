from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from users.models import User


class ProviderCatalogApiTests(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Catalogue API test",
            slug="catalogue-api-test",
        )
        self.provider = User.objects.create_user(
            username="provider_catalog_api",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.patient = User.objects.create_user(
            username="patient_catalog_api",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.organization = OrganismeDeSante.objects.create(
            user=self.provider,
            name="Clinique Catalogue API",
            is_active=True,
            subscription_plan=self.plan,
        )
        self.service = ServiceMedical.objects.create(
            name="Biologie médicale",
            slug="biologie-medicale",
        )
        self.subservice = ActeMedical.objects.create(
            name="Biochimie",
            service_medical_category=self.service,
            level=2,
        )
        self.act = ActeMedical.objects.create(
            name="Dosage API",
            service_medical_category=self.service,
            parent_service=self.subservice,
            level=3,
            reference_price=5000,
            rdv_prerequisites="À jeun.",
        )
        self.provider_act = PrestataireActe.objects.create(
            organisme=self.organization,
            acte=self.act,
            price=7000,
            is_available=True,
        )
        self.other_act = ActeMedical.objects.create(
            name="Acte ajouté",
            service_medical_category=self.service,
            parent_service=self.subservice,
            level=3,
        )
        self.client.force_login(self.provider)

    def test_catalogue_api_returns_pillar_actes_and_domicile_configuration(self):
        response = self.client.get(
            reverse("healthcare:prestataire_actes_api"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["organization"], self.organization.name)
        pillar = next(item for item in payload["pillars"] if item["slug"] == "biologie-medicale")
        serialized = [
            act
            for subgroup in pillar["subgroups"]
            for act in subgroup["actes"]
            if act["id"] == self.act.pk
        ][0]
        self.assertEqual(serialized["price"], "7000.00")
        self.assertTrue(serialized["is_available"])
        self.assertEqual(serialized["preparation"]["reference"], "À jeun.")
        self.assertTrue(payload["show_domicile_block"])

    def test_catalogue_page_route_serves_react(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("react")):
            response = self.client.get(reverse("healthcare:actes_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"react")

    def test_excel_import_entry_route_serves_react_catalogue(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("react")):
            response = self.client.get(reverse("healthcare:actes_import_excel"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"react")

    def test_act_form_api_add_edit_and_validation(self):
        add_url = reverse("healthcare:acte_add")
        add_options = self.client.get(add_url, HTTP_ACCEPT="application/json")
        self.assertEqual(add_options.status_code, 200)
        self.assertIn(self.other_act.name, [item["name"] for item in add_options.json()["choices"]])

        invalid = self.client.post(
            add_url,
            {"acte": self.other_act.pk, "price": "0", "is_available": "on"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("price", invalid.json()["errors"])

        created = self.client.post(
            add_url,
            {"acte": self.other_act.pk, "price": "9000", "delai": "24h", "is_available": "on"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(created.status_code, 201)
        created_pa = PrestataireActe.objects.get(pk=created.json()["id"])
        self.assertEqual(created_pa.price, 9000)

        edit_url = reverse("healthcare:acte_edit", args=[self.provider_act.pk])
        edit_options = self.client.get(edit_url, HTTP_ACCEPT="application/json")
        self.assertEqual(edit_options.status_code, 200)
        self.assertEqual(edit_options.json()["acte"], self.act.pk)
        updated = self.client.post(
            edit_url,
            {
                "acte": self.act.pk,
                "price": "8500",
                "delai": "48h",
                "is_available": "on",
                "notes": "Sur rendez-vous",
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.provider_act.refresh_from_db()
        self.assertEqual(self.provider_act.price, 8500)

    def test_catalogue_save_and_toggle_return_json(self):
        save_response = self.client.post(
            reverse("healthcare:actes_list"),
            {
                "action": "save_catalogue",
                "catalogue_tarifs_delais": "Tarifs confirmés par téléphone.",
                f"price_{self.act.pk}": "8200",
                f"delai_{self.act.pk}": "48h",
                "acte_ids": str(self.act.pk),
            },
            HTTP_ACCEPT="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(save_response.status_code, 200)
        self.provider_act.refresh_from_db()
        self.organization.refresh_from_db()
        self.assertEqual(self.provider_act.price, 8200)
        self.assertEqual(self.provider_act.delai, "48h")
        self.assertIn("Tarifs confirmés", self.organization.catalogue_tarifs_delais)

        toggle_response = self.client.post(
            reverse("healthcare:acte_toggle_available", args=[self.provider_act.pk]),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(toggle_response.status_code, 200)
        self.assertFalse(toggle_response.json()["is_available"])
