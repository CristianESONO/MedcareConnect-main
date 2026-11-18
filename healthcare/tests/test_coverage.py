"""Tests calcul de couverture assurance."""

from decimal import Decimal

from django.test import TestCase

from healthcare.coverage import (
    assurance_rates_lookup_key,
    coverage_category_for_acte,
    lookup_coverage_rate_percent,
    patient_cost_from_rate,
)
from healthcare.models import (
    ActeMedical,
    Assurance,
    OrganismeDeSante,
    PrestataireActe,
    PriseEnChargeAssurance,
    ServiceMedical,
    SubscriptionPlan,
)
from users.models import User


class CoverageLookupTests(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(name="Plan cov", slug="plan-cov-tu")
        self.prest = User.objects.create_user(
            username="presta_cov",
            email="pc@example.com",
            password="x",
            user_type="prestataire",
        )
        self.svc = ServiceMedical.objects.create(name="Biologie médicale", order=1)
        self.type_hem = ActeMedical.objects.create(
            name="Hématologie",
            service_medical_category=self.svc,
            level=2,
        )
        self.acte = ActeMedical.objects.create(
            name="NFS / Hémogramme",
            service_medical_category=self.svc,
            parent_service=self.type_hem,
            level=3,
        )
        self.assurance = Assurance.objects.create(
            name="Couverture Maladie Universelle (CMU)",
            segment="regime_public",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.prest,
            name="Labo Test",
            address="Dakar",
            subscription_plan=self.plan,
            is_active=True,
        )
        self.pa = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte,
            price=Decimal("10000"),
            is_available=True,
        )

    def test_category_from_parent_service(self):
        self.assertEqual(coverage_category_for_acte(self.acte), "Hématologie")

    def test_assurance_alias_cmu(self):
        self.assertEqual(assurance_rates_lookup_key(self.assurance), "CMU")

    def test_rate_hematologie_cmu(self):
        rate = lookup_coverage_rate_percent(self.assurance, self.acte)
        self.assertEqual(rate, Decimal("70"))

    def test_no_rate_without_prise_en_charge(self):
        self.assertIsNone(self.pa.get_coverage_rate(self.assurance))

    def test_patient_cost_with_prise_en_charge(self):
        PriseEnChargeAssurance.objects.create(
            organisme=self.org,
            assurance=self.assurance,
            is_active=True,
        )
        self.assertEqual(self.pa.get_coverage_rate(self.assurance), Decimal("70"))
        self.assertEqual(self.pa.get_patient_cost(self.assurance), Decimal("3000"))

    def test_patient_global_rate_overrides_reference(self):
        from users.models import PatientProfile, User

        PriseEnChargeAssurance.objects.create(
            organisme=self.org,
            assurance=self.assurance,
            is_active=True,
        )
        patient = User.objects.create_user(
            username="pat_cov",
            email="pc@example.com",
            password="x",
            user_type="patient",
        )
        profile = PatientProfile.objects.create(
            user=patient,
            insurance=self.assurance,
            insurance_coverage_pct=Decimal("50"),
        )
        self.assertEqual(
            self.pa.get_coverage_rate(self.assurance, patient_profile=profile),
            Decimal("50"),
        )
        self.assertEqual(
            self.pa.get_patient_cost(self.assurance, patient_profile=profile),
            Decimal("5000"),
        )

    def test_patient_cost_from_rate_helper(self):
        self.assertEqual(
            patient_cost_from_rate(Decimal("10000"), Decimal("70")),
            Decimal("3000"),
        )
