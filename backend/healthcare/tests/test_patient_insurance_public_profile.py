"""Tests affichage message 'Votre assurance est acceptée ici' sur profil public structure."""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from healthcare.models import (
    ActeMedical,
    Assurance,
    OrganismeDeSante,
    PrestataireActe,
    PriseEnChargeAssurance,
    ServiceMedical,
    SubscriptionPlan,
)
from users.models import User, PatientProfile


class PatientInsurancePublicProfileTests(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(name="Standard", slug="standard-plan")
        self.presta_user = User.objects.create_user(
            username="structure_owner",
            email="owner@example.com",
            password="pass",
            user_type="prestataire",
        )
        self.svc = ServiceMedical.objects.create(name="Consultation", order=1)
        self.acte = ActeMedical.objects.create(
            name="Consultation générale",
            service_medical_category=self.svc,
            level=3,
        )

        self.assurance_axa = Assurance.objects.create(
            name="AXA Assurances",
            segment="privee_iard",
        )
        self.assurance_sunu = Assurance.objects.create(
            name="SUNU Assurances",
            segment="privee_iard",
        )

        self.org = OrganismeDeSante.objects.create(
            user=self.presta_user,
            name="Centre Médical Horizon",
            slug="centre-medical-horizon",
            address="Route de Ouakam",
            city="Dakar",
            subscription_plan=self.plan,
            is_active=True,
        )

        self.pa = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte,
            price=Decimal("15000"),
            is_available=True,
        )

        # La structure accepte AXA Assurances
        PriseEnChargeAssurance.objects.create(
            organisme=self.org,
            assurance=self.assurance_axa,
            is_active=True,
        )

        # Patient avec AXA configurée
        self.patient_with_axa = User.objects.create_user(
            username="patient_axa",
            email="patient_axa@example.com",
            password="pass",
            user_type="patient",
        )
        self.profile_axa = PatientProfile.objects.create(
            user=self.patient_with_axa,
            insurance=self.assurance_axa,
        )

        # Patient avec SUNU configurée (non acceptée par la structure)
        self.patient_with_sunu = User.objects.create_user(
            username="patient_sunu",
            email="patient_sunu@example.com",
            password="pass",
            user_type="patient",
        )
        self.profile_sunu = PatientProfile.objects.create(
            user=self.patient_with_sunu,
            insurance=self.assurance_sunu,
        )

        self.client = Client()

    def test_patient_with_matched_insurance_receives_profile_match(self):
        self.client.force_login(self.patient_with_axa)
        url = reverse("healthcare:organisme_detail", kwargs={"slug": self.org.slug})
        resp = self.client.get(url, HTTP_ACCEPT="application/json")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["insurance_match"], "AXA Assurances")
        self.assertTrue(next(row for row in payload["insurances"] if row["name"] == "AXA Assurances")["patient_match"])

    def test_patient_with_unmatched_insurance_has_no_profile_match(self):
        self.client.force_login(self.patient_with_sunu)
        url = reverse("healthcare:organisme_detail", kwargs={"slug": self.org.slug})
        resp = self.client.get(url, HTTP_ACCEPT="application/json")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["insurance_match"], "")
        self.assertFalse(any(row["patient_match"] for row in payload["insurances"]))

    def test_anonymous_visitor_has_no_profile_match_by_default(self):
        url = reverse("healthcare:organisme_detail", kwargs={"slug": self.org.slug})
        resp = self.client.get(url, HTTP_ACCEPT="application/json")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["insurance_match"], "")

    def test_get_param_assurance_matches_on_profile_api(self):
        url = reverse("healthcare:organisme_detail", kwargs={"slug": self.org.slug}) + f"?assurance={self.assurance_axa.pk}"
        resp = self.client.get(url, HTTP_ACCEPT="application/json")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["insurance_match"], "AXA Assurances")

    def test_patient_can_manage_favorites_through_json_api(self):
        self.client.force_login(self.patient_with_axa)
        toggle_url = reverse(
            "healthcare:toggle_favorite_api",
            kwargs={"slug": self.org.slug},
        )

        added = self.client.post(toggle_url, HTTP_ACCEPT="application/json")
        self.assertEqual(added.status_code, 200)
        self.assertTrue(added.json()["is_favorite"])
        listed = self.client.get(reverse("healthcare:favorites_api"))
        self.assertEqual(listed.json()["favorites"][0]["slug"], self.org.slug)

        removed = self.client.post(toggle_url, HTTP_ACCEPT="application/json")
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(removed.json()["is_favorite"])
