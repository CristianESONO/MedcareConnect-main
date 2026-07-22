"""Tests tracking profil et analytics prestataire."""

from django.test import RequestFactory, TestCase

from healthcare.models import OrganismeDeSante, ProfileView, SubscriptionPlan, TypeOrganisme
from healthcare.prestataire_analytics import build_activity_chart, medplaque_stats
from healthcare.profile_tracking import resolve_profile_view_source
from users.models import User


class ProfileTrackingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.presta = User.objects.create_user(
            username="presta_analytics",
            email="pa@e.com",
            password="x",
            user_type="prestataire",
        )
        self.type_org = TypeOrganisme.objects.create(name="Labo", slug="labo")
        self.plan = SubscriptionPlan.objects.create(name="Plan TU", slug="plan-tu-analytics")
        self.org = OrganismeDeSante.objects.create(
            user=self.presta,
            name="Test Lab",
            slug="test-lab",
            city="Dakar",
            address="Dakar",
            type_organisme=self.type_org,
            subscription_plan=self.plan,
        )

    def test_resolve_nfc_source(self):
        req = self.factory.get("/healthcare/test-lab/?src=nfc")
        self.assertEqual(resolve_profile_view_source(req), ProfileView.SOURCE_NFC)

    def test_resolve_qr_utm(self):
        req = self.factory.get("/healthcare/test-lab/?utm_source=medplaque&utm_medium=qr")
        self.assertEqual(resolve_profile_view_source(req), ProfileView.SOURCE_QR)

    def test_activity_chart_structure(self):
        ProfileView.objects.create(organisme=self.org, source=ProfileView.SOURCE_NFC)
        chart = build_activity_chart(self.org, "total")
        self.assertIn("devis", chart["series"])
        self.assertEqual(len(chart["labels"]), 9)

    def test_medplaque_stats_counts(self):
        ProfileView.objects.create(organisme=self.org, source=ProfileView.SOURCE_NFC)
        ProfileView.objects.create(organisme=self.org, source=ProfileView.SOURCE_QR)
        stats = medplaque_stats(self.org)
        self.assertEqual(stats["nfc_scans"], 1)
        self.assertEqual(stats["qr_scans"], 1)
        self.assertEqual(stats["total_access"], 2)
