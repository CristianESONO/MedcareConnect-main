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
            level=1,
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

    def test_patient_with_matched_insurance_sees_red_message(self):
        """Quand le patient a configuré son assurance et qu'elle est acceptée, le message rouge apparaît."""
        self.client.force_login(self.patient_with_axa)
        url = reverse("healthcare:organisme_detail", kwargs={"slug": self.org.slug})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()

        # Le message doit être présent
        self.assertIn("Votre assurance est acceptée ici", html)
        self.assertIn("AXA Assurances", html)

        # Le message est stylé en rouge
        self.assertIn("#dc2626", html)
        self.assertIn('<div class="profil-drawer-ins-match"', html)

        # Le tag dans la liste des assurances
        self.assertIn("Acceptée pour vous", html)

    def test_patient_with_unmatched_insurance_does_not_see_message(self):
        """Quand le patient a configuré une assurance non acceptée, le message n'apparaît pas."""
        self.client.force_login(self.patient_with_sunu)
        url = reverse("healthcare:organisme_detail", kwargs={"slug": self.org.slug})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()

        self.assertNotIn("Votre assurance est acceptée ici", html)
        self.assertNotIn('<div class="profil-drawer-ins-match"', html)
        self.assertNotIn("Acceptée pour vous", html)

    def test_anonymous_visitor_does_not_see_message_by_default(self):
        """Un visiteur sans assurance configurée ne voit pas le message."""
        url = reverse("healthcare:organisme_detail", kwargs={"slug": self.org.slug})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()

        self.assertNotIn("Votre assurance est acceptée ici", html)
        self.assertNotIn('<div class="profil-drawer-ins-match"', html)

    def test_get_param_assurance_matches(self):
        """Si un visiteur arrive avec ?assurance=<id_axa>, le message est affiché."""
        url = reverse("healthcare:organisme_detail", kwargs={"slug": self.org.slug}) + f"?assurance={self.assurance_axa.pk}"
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()

        self.assertIn("Votre assurance est acceptée ici", html)
        self.assertIn('<div class="profil-drawer-ins-match"', html)
        self.assertIn("#dc2626", html)
