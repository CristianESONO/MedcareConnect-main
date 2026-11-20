import json

from django.test import TestCase
from django.urls import reverse

from healthcare.models import Assurance, OrganismeDeSante
from users.models import User


class DashboardMapTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="dashboard_map_admin",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.admin)

    def create_org(self, username, name, **kwargs):
        user = User.objects.create_user(
            username=username,
            password="testpass123",
            user_type="prestataire",
        )
        defaults = {
            "user": user,
            "name": name,
            "city": "Dakar",
            "is_active": True,
        }
        defaults.update(kwargs)
        return OrganismeDeSante.objects.create(**defaults)

    def test_map_uses_valid_coordinates_and_correct_public_profile_url(self):
        practitioner = self.create_org(
            "map_practitioner",
            "Praticien cartographie",
            account_nature="praticien",
            latitude="14.716700",
            longitude="-17.467700",
        )
        self.create_org(
            "map_invalid_practitioner",
            "Coordonnées hors plage",
            latitude="95.000000",
            longitude="-17.467700",
        )

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        map_orgs = json.loads(response.context["map_orgs_json"])
        self.assertEqual(len(map_orgs), 1)
        self.assertEqual(map_orgs[0]["id"], practitioner.pk)
        self.assertEqual(map_orgs[0]["url"], practitioner.get_public_url())
        self.assertEqual(response.context["map_invalid_count"], 1)
        self.assertContains(response, "tile.openstreetmap.org")

    def test_active_practitioner_public_link_opens_and_inactive_link_is_disabled(self):
        practitioner = self.create_org(
            "profile_practitioner",
            "Fiche publique praticien",
            account_nature="praticien",
        )

        detail = self.client.get(
            reverse("dashboard:organisme_detail", args=(practitioner.pk,))
        )

        self.assertContains(
            detail,
            f'href="{reverse("healthcare:praticien_public_detail", kwargs={"slug": practitioner.slug})}"',
        )
        public_profile = self.client.get(practitioner.get_public_url())
        self.assertEqual(public_profile.status_code, 200)
        self.assertContains(public_profile, practitioner.name)

        inactive = self.create_org(
            "inactive_profile",
            "Fiche non publiée",
            is_active=False,
        )
        inactive_detail = self.client.get(
            reverse("dashboard:organisme_detail", args=(inactive.pk,))
        )
        self.assertContains(inactive_detail, "Fiche publique indisponible")
        self.assertNotContains(
            inactive_detail,
            f'href="{inactive.get_public_url()}"',
        )


class DashboardAssuranceSearchTests(TestCase):
    def setUp(self):
        admin = User.objects.create_user(
            username="dashboard_assurance_admin",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin)

    def test_search_matches_assurance_name_contact_and_segment_label(self):
        target = Assurance.objects.create(
            name="Sénégal Santé",
            segment=Assurance.Segment.REGIME_PUBLIC,
            description="Couverture institutionnelle",
            website="https://senegal-sante.example",
            contact_phone="781234567",
        )
        Assurance.objects.create(
            name="Mutuelle du quartier",
            segment=Assurance.Segment.MUTUELLE,
            contact_phone="779876543",
        )

        for query in ("Sénégal Santé", "institutionnelle", "781234567", "institutionnel"):
            with self.subTest(query=query):
                response = self.client.get(
                    reverse("dashboard:assurances_list"),
                    {"q": query},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(response.context["assurances"].values_list("pk", flat=True)),
                    [target.pk],
                )
                self.assertContains(response, f'value="{query}"')

    def test_search_displays_empty_state_when_nothing_matches(self):
        response = self.client.get(
            reverse("dashboard:assurances_list"),
            {"q": "introuvable"},
        )

        self.assertContains(response, "Aucune assurance ne correspond")
