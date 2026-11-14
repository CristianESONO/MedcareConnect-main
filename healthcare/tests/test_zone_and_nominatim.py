from decimal import Decimal
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from io import StringIO
from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, Region, ServiceMedical, TypeOrganisme
from healthcare.nominatim import search_places
from users.models import User


class ZoneAndNominatimTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.type_clinique = TypeOrganisme.objects.create(name="Clinique", slug="clinique")
        self.service = ServiceMedical.objects.create(name="Biologie", slug="biologie", is_active=True)
        self.acte = ActeMedical.objects.create(
            name="Examen Zone",
            service_medical_category=self.service,
            level=3,
            is_active=True,
        )
        self.reg_dakar, _ = Region.objects.get_or_create(name="Dakar", slug="dakar")

        # Structure 1: Plateau (with region = Dakar)
        u1 = User.objects.create_user("doc_plateau", "p@test.sn", "pass")
        self.org_plateau = OrganismeDeSante.objects.create(
            user=u1,
            name="Clinique Plateau",
            slug="clinique-plateau",
            type_organisme=self.type_clinique,
            region=self.reg_dakar,
            city="Dakar",
            quartier="Plateau",
            address="Rue Wagane Diouf, Plateau",
            latitude=14.6700,
            longitude=-17.4300,
            is_active=True,
            is_verified=True,
        )
        self.pa_plateau = PrestataireActe.objects.create(
            organisme=self.org_plateau,
            acte=self.acte,
            price=Decimal("10000.00"),
            is_available=True,
        )

        # Structure 2: Mermoz (WITHOUT region explicit)
        u2 = User.objects.create_user("doc_mermoz", "m@test.sn", "pass")
        self.org_mermoz = OrganismeDeSante.objects.create(
            user=u2,
            name="Centre Mermoz",
            slug="centre-mermoz",
            type_organisme=self.type_clinique,
            region=None,  # No explicit region
            city="Dakar",
            quartier="Mermoz",
            address="Mermoz Pyrotechnie",
            latitude=14.7100,
            longitude=-17.4700,
            is_active=True,
            is_verified=True,
        )
        self.pa_mermoz = PrestataireActe.objects.create(
            organisme=self.org_mermoz,
            acte=self.acte,
            price=Decimal("12000.00"),
            is_available=True,
        )

        # Structure 3: Ambulance covering Dakar (toutes zones)
        u3 = User.objects.create_user("doc_ambu", "a@test.sn", "pass")
        self.org_ambu = OrganismeDeSante.objects.create(
            user=u3,
            name="Ambulance Dakar Express",
            slug="ambulance-dakar-express",
            type_organisme=self.type_clinique,
            region=None,
            city="Dakar",
            quartier="Dakar (toutes zones)",
            address="Dakar",
            latitude=None,
            longitude=None,
            is_active=True,
            is_verified=True,
        )
        self.pa_ambu = PrestataireActe.objects.create(
            organisme=self.org_ambu,
            acte=self.acte,
            price=Decimal("25000.00"),
            is_available=True,
        )

    @patch("healthcare.nominatim._get_json")
    def test_nominatim_search_places_restricts_to_dakar_and_senegal(self, mock_get_json):
        mock_get_json.return_value = [
            {
                "lat": "14.6710",
                "lon": "-17.4320",
                "display_name": "Dakar-Plateau, Dakar, Sénégal",
                "type": "administrative",
            }
        ]
        results = search_places("Plateau", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["lat"], 14.6710)
        self.assertEqual(results[0]["lon"], -17.4320)

        # Verify the requested URL contains countrycodes=sn and viewbox for Dakar
        called_url = mock_get_json.call_args[0][0]
        self.assertIn("countrycodes=sn", called_url)
        self.assertIn("viewbox=-17.55%2C14.60%2C-17.10%2C14.85", called_url)
        self.assertIn("bounded=1", called_url)
        self.assertIn("accept-language=fr", called_url)

    @patch("healthcare.nominatim._get_json")
    def test_api_geocode_returns_matching_addresses(self, mock_get_json):
        mock_get_json.return_value = [
            {
                "lat": "14.7100",
                "lon": "-17.4700",
                "display_name": "Mermoz, Dakar, Sénégal",
                "type": "residential",
            }
        ]
        url = reverse("healthcare:api_geocode")
        resp = self.client.get(f"{url}?q=Mermoz")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["display_name"], "Mermoz, Dakar, Sénégal")
        self.assertEqual(data["results"][0]["lat"], 14.7100)

    def test_zone_filter_matches_only_selected_zone_and_all_zones_ambulance(self):
        """Filtering by 'Plateau' should return Plateau + all-zone ambulance, but not Mermoz."""
        url = reverse("healthcare:search")
        resp = self.client.get(url, {"q": "Examen Zone", "city": "Plateau"}, HTTP_HOST="localhost")
        self.assertEqual(resp.status_code, 200)
        page = resp.context.get("page")
        items = list(page.object_list) if page else []
        self.assertIn(self.pa_plateau, items)
        self.assertIn(self.pa_ambu, items)
        self.assertNotIn(self.pa_mermoz, items)

    def test_zone_filter_ignores_trailing_empty_city_param_and_filters_mobile_blocks(self):
        """Si le formulaire envoie city=Plateau&city= (champs multiples dans le DOM), la valeur non-vide est retenue."""
        url = reverse("healthcare:search")
        # Envoie deux valeurs pour 'city' simulant les inputs multiples du formulaire HTML
        resp = self.client.get(f"{url}?acte={self.acte.pk}&city=Plateau&city=", HTTP_HOST="localhost")
        self.assertEqual(resp.status_code, 200)
        blocks = resp.context.get("mobile_results_by_org") or []
        orgs = [b["org"] for b in blocks]
        self.assertIn(self.org_plateau, orgs)
        self.assertNotIn(self.org_mermoz, orgs)

    def test_region_filter_includes_structures_without_explicit_region_in_dakar(self):
        """Filtering by Region Dakar must keep structures in Dakar even if region_id is NULL."""
        url = reverse("healthcare:search")
        resp = self.client.get(url, {"q": "Examen Zone", "region": str(self.reg_dakar.pk)}, HTTP_HOST="localhost")
        self.assertEqual(resp.status_code, 200)
        page = resp.context.get("page")
        items = list(page.object_list) if page else []
        self.assertIn(self.pa_plateau, items)
        # Mermoz has region=None but city="Dakar", must remain findable
        self.assertIn(self.pa_mermoz, items)

    def test_management_command_verifier_adresses_structures(self):
        out = StringIO()
        call_command("verifier_adresses_structures", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("Ambulance Dakar Express", output)
        self.assertIn("Centre Mermoz", output)

