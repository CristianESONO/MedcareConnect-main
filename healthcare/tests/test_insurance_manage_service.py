"""Tests unitaires pour InsuranceManageService."""

from django.test import TestCase

from users.models import User
from healthcare.models import Assurance, OrganismeDeSante, PriseEnChargeAssurance
from healthcare.services import InsuranceManageService


class InsuranceManageServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="org_insurance_test",
            email="org_ins@medcare.test",
            password="testpass123",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.user,
            name="Clinique Test Assurances",
            is_active=True,
        )
        self.assur_axa = Assurance.objects.create(
            name="AXA Assurances",
            slug="axa-assurances",
            segment=Assurance.Segment.PRIVEE_IARD,
            is_active=True,
        )
        self.assur_sunu = Assurance.objects.create(
            name="Sunu Sante",
            slug="sunu-sante",
            segment=Assurance.Segment.DIGITALE,
            is_active=True,
        )

    def test_add_custom_assurance_new(self):
        name = InsuranceManageService.add_custom_assurance(
            self.org,
            name="Nouvelle Mutuelle",
            segment=Assurance.Segment.MUTUELLE,
            description="Mutuelle d'entreprise",
        )
        self.assertEqual(name, "Nouvelle Mutuelle")
        self.assertTrue(Assurance.objects.filter(name="Nouvelle Mutuelle").exists())
        self.assertTrue(
            PriseEnChargeAssurance.objects.filter(
                organisme=self.org, assurance__name="Nouvelle Mutuelle", is_active=True
            ).exists()
        )

    def test_add_custom_assurance_empty_raises(self):
        with self.assertRaises(ValueError):
            InsuranceManageService.add_custom_assurance(self.org, name="   ", segment="ipm")

    def test_save_assurances(self):
        # Initialement aucune prise en charge
        raw_ids = [str(self.assur_axa.pk), str(self.assur_sunu.pk)]
        InsuranceManageService.save_assurances(
            self.org, raw_ids=raw_ids, tarifs_delais="Tiers payant à 80%"
        )

        self.org.refresh_from_db()
        self.assertEqual(self.org.assurances_tarifs_delais, "Tiers payant à 80%")
        self.assertEqual(
            PriseEnChargeAssurance.objects.filter(organisme=self.org).count(), 2
        )

        # Retirer une assurance
        raw_ids_updated = [str(self.assur_axa.pk)]
        InsuranceManageService.save_assurances(
            self.org, raw_ids=raw_ids_updated, tarifs_delais="Tiers payant à 70%"
        )
        self.assertEqual(
            PriseEnChargeAssurance.objects.filter(organisme=self.org).count(), 1
        )
        self.assertTrue(
            PriseEnChargeAssurance.objects.filter(
                organisme=self.org, assurance=self.assur_axa
            ).exists()
        )

    def test_build_context(self):
        PriseEnChargeAssurance.objects.create(
            organisme=self.org,
            assurance=self.assur_axa,
            is_active=True,
        )
        ctx = InsuranceManageService.build_context(self.org, q="AXA")
        self.assertEqual(len(ctx["prises"]), 1)
        self.assertIn(self.assur_axa.pk, ctx["selected_assurance_ids"])
        self.assertEqual(ctx["insurance_selected_count"], 1)
