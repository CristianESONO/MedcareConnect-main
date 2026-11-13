from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, ServiceMedical, TypeOrganisme
from users.models import User


class DelaiSearchTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.type_clinique = TypeOrganisme.objects.create(name="Clinique", slug="clinique")
        self.service = ServiceMedical.objects.create(name="Biologie", slug="biologie", is_active=True)
        self.acte = ActeMedical.objects.create(
            name="Examen Delai",
            service_medical_category=self.service,
            level=3,
            is_active=True,
        )

        # Offre A : Horizon (48h, prix moins cher 8000 FCFA)
        u_horiz = User.objects.create_user("horizon", "h@test.sn", "pass")
        self.org_horizon = OrganismeDeSante.objects.create(
            user=u_horiz,
            name="Centre Horizon",
            slug="centre-horizon",
            type_organisme=self.type_clinique,
            is_active=True,
            is_verified=True,
            city="Dakar",
        )
        self.pa_horizon_48h = PrestataireActe.objects.create(
            organisme=self.org_horizon,
            acte=self.acte,
            price=Decimal("8000.00"),
            delai="48h",
            is_available=True,
        )

        # Offre B : Clemar (24h, prix plus cher 12000 FCFA)
        u_clemar = User.objects.create_user("clemar", "c@test.sn", "pass")
        self.org_clemar = OrganismeDeSante.objects.create(
            user=u_clemar,
            name="Clinique Clemar",
            slug="clinique-clemar",
            type_organisme=self.type_clinique,
            is_active=True,
            is_verified=True,
            city="Dakar",
        )
        self.pa_clemar_24h = PrestataireActe.objects.create(
            organisme=self.org_clemar,
            acte=self.acte,
            price=Decimal("12000.00"),
            delai="24h",
            is_available=True,
        )

    def test_delai_filter_24h_excludes_48h(self):
        """Avec le filtre 'sous 24 h', une offre à 48 h ne doit jamais apparaître."""
        url = reverse("healthcare:search")
        resp = self.client.get(url, {"q": "Examen Delai", "delai": "24h"})
        self.assertEqual(resp.status_code, 200)
        page = resp.context.get("page")
        items = list(page.object_list) if page else []
        self.assertIn(self.pa_clemar_24h, items)
        self.assertNotIn(self.pa_horizon_48h, items)

    def test_sort_delai_asc_places_24h_before_48h(self):
        """Sans filtre de délai, le tri 'delai_asc' doit placer 24h avant 48h (même si 48h est moins chère)."""
        url = reverse("healthcare:search")
        resp = self.client.get(url, {"q": "Examen Delai", "sort": "delai_asc"})
        self.assertEqual(resp.status_code, 200)
        page = resp.context.get("page")
        items = list(page.object_list) if page else []
        self.assertIn(self.pa_clemar_24h, items)
        self.assertIn(self.pa_horizon_48h, items)
        idx_clemar = items.index(self.pa_clemar_24h)
        idx_horizon = items.index(self.pa_horizon_48h)
        self.assertLess(idx_clemar, idx_horizon)

