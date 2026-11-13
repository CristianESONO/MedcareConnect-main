from django.test import TestCase, Client
from django.urls import reverse
from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, ServiceMedical, TypeOrganisme
from users.models import User


class DuplicatesSearchTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.type_clinique = TypeOrganisme.objects.create(name="Clinique", slug="clinique")
        self.service = ServiceMedical.objects.create(name="Biologie médicale", slug="biologie", is_active=True)

        # Doublons réels de la prod : VS (824) et VS (vitesse de sédimentation) (1197)
        self.acte_canonique = ActeMedical.objects.create(
            name="VS",
            service_medical_category=self.service,
            level=3,
            is_active=True,
        )
        self.acte_doublon = ActeMedical.objects.create(
            name="VS (vitesse de sédimentation)",
            service_medical_category=self.service,
            level=3,
            is_active=True,
        )

        u = User.objects.create_user("labo_test", "labo@test.sn", "pass")
        self.org = OrganismeDeSante.objects.create(
            user=u,
            name="Labo Test",
            slug="labo-test",
            type_organisme=self.type_clinique,
            is_active=True,
            is_verified=True,
            city="Dakar",
        )
        self.pa_canon = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte_canonique,
            price=3000,
            is_available=True,
        )

    def test_autocomplete_deduplicates_vs_variations(self):
        """L'autocomplétion pour 'vs' ne doit pas afficher de multiples doublons canoniques."""
        url = reverse("healthcare:api_search_autocomplete")
        resp = self.client.get(url, {"q": "vs"})
        self.assertEqual(resp.status_code, 200)
        sugs = resp.json().get("suggestions", [])
        acte_labels = [s["label"] for s in sugs if s["type"] == "acte"]
        # 'VS' doit être présent
        self.assertIn("VS", acte_labels)
        # Mais pas de doublon synonyme direct de VS dans la même liste
        self.assertNotIn("VS (vitesse de sédimentation)", acte_labels)

