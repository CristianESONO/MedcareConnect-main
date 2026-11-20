from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
)
from healthcare.views import RECOMMENDED_BILAN_ACTS
from users.models import User


class RecommendedBilanSearchTests(TestCase):
    def setUp(self):
        service = ServiceMedical.objects.create(name="Biologie médicale")
        user = User.objects.create_user(
            username="bilan_provider",
            email="bilan-provider@example.com",
            password="test-password",
        )
        organisme = OrganismeDeSante.objects.create(
            user=user,
            name="Laboratoire Bilan",
            address="Dakar",
            is_active=True,
        )

        self.actes_by_name = {}
        all_names = dict.fromkeys(
            name for names in RECOMMENDED_BILAN_ACTS.values() for name in names
        )
        for name in all_names:
            acte = ActeMedical.objects.create(
                name=name,
                service_medical_category=service,
                level=3,
                is_active=True,
            )
            self.actes_by_name[name] = acte
            PrestataireActe.objects.create(
                organisme=organisme,
                acte=acte,
                price=Decimal("5000.00"),
                is_available=True,
            )

        ActeMedical.objects.create(
            name="NFS (hémogramme)",
            service_medical_category=service,
            level=3,
            is_active=True,
        )

    def test_each_recommended_bilan_selects_acts_and_keeps_navigation_counts(self):
        for bilan_key, names in RECOMMENDED_BILAN_ACTS.items():
            with self.subTest(bilan=bilan_key):
                response = self.client.get(
                    reverse("healthcare:search"),
                    {"bilan": bilan_key, "q": "libellé générique sans correspondance"},
                    follow=True,
                )

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("bilan", response.wsgi_request.GET)
                self.assertNotIn("q", response.wsgi_request.GET)
                selected_ids = {
                    int(acte_id) for acte_id in response.context["current_actes"]
                }
                expected_ids = {self.actes_by_name[name].pk for name in names}
                self.assertEqual(selected_ids, expected_ids)

                results = list(response.context["page"].object_list)
                self.assertEqual({row.acte_id for row in results}, expected_ids)

                family_counts = response.context["service_dem_pills"]
                self.assertGreater(family_counts[0]["count"], 0)
                self.assertTrue(any(row["count"] > 0 for row in family_counts[1:]))
                families = response.context["acte_dem_families"]
                self.assertTrue(any(family["open"] for family in families))
                self.assertTrue(
                    any(subgroup["open"] for family in families for subgroup in family["subgroups"])
                )

    def test_act_navigation_starts_with_families_and_subfamilies_collapsed(self):
        response = self.client.get(reverse("healthcare:search"))

        self.assertEqual(response.status_code, 200)
        families = response.context["acte_dem_families"]
        self.assertTrue(families)
        self.assertTrue(all(not family["open"] for family in families))
        self.assertTrue(
            all(
                not subgroup["open"]
                for family in families
                for subgroup in family["subgroups"]
            )
        )
