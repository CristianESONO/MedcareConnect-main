from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, ServiceMedical, TypeOrganisme
from users.models import User


class BudgetAndZeroPricesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_org = User.objects.create_user(
            username="clinique_test", email="clinique@test.sn", password="password123"
        )
        self.type_org = TypeOrganisme.objects.create(name="Clinique", slug="clinique")
        self.org = OrganismeDeSante.objects.create(
            user=self.user_org,
            name="Clinique Test Prix",
            slug="clinique-test-prix",
            type_organisme=self.type_org,
            is_active=True,
            is_verified=True,
            city="Dakar",
        )
        self.service = ServiceMedical.objects.create(name="Biologie", slug="biologie", is_active=True)
        self.acte = ActeMedical.objects.create(
            name="Glycémie Test",
            service_medical_category=self.service,
            level=3,
            is_active=True,
        )

        # Offre valide
        self.pa_valide = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.acte,
            price=Decimal("5000.00"),
            is_available=True,
        )

        # Deuxième structure pour l'offre à 0
        self.user_org_zero = User.objects.create_user(
            username="zero_org", email="zero@test.sn", password="password123"
        )
        self.org_zero = OrganismeDeSante.objects.create(
            user=self.user_org_zero,
            name="Centre Gratuit",
            slug="centre-gratuit",
            type_organisme=self.type_org,
            is_active=True,
            is_verified=True,
            city="Dakar",
        )
        # Note: on force la création directe pour tester le comportement de la recherche face aux données existantes à 0
        self.pa_zero = PrestataireActe.objects.filter(organisme=self.org_zero, acte=self.acte).first()
        if not self.pa_zero:
            self.pa_zero = PrestataireActe(
                organisme=self.org_zero,
                acte=self.acte,
                price=Decimal("0.00"),
                is_available=True,
            )
            # save sans full_clean si nécessaire pour émuler données corrompues en base
            super(PrestataireActe, self.pa_zero).save()

    def test_zero_price_not_in_search(self):
        """Une offre avec un prix à 0 ne doit jamais apparaître dans la recherche patient."""
        url = reverse("healthcare:search")
        resp = self.client.get(url, {"q": "Glycémie Test"})
        self.assertEqual(resp.status_code, 200)
        results = resp.context.get("page")
        result_pas = list(results.object_list) if results else []
        self.assertNotIn(self.pa_zero, result_pas)
        self.assertIn(self.pa_valide, result_pas)

    def test_zero_price_not_in_api_budget(self):
        """Une offre avec un prix à 0 ne doit pas être prise en compte dans l'API budget."""
        url = reverse("healthcare:api_actes_budget")
        resp = self.client.get(url, {"max": "10000"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        actes = data.get("actes", [])
        glycemie_row = next((a for a in actes if a["id"] == self.acte.id), None)
        self.assertIsNotNone(glycemie_row)
        # Le min_price doit être 5000, et non 0
        self.assertEqual(glycemie_row["min_price"], 5000.0)

    def test_zero_price_rejected_in_model_clean(self):
        """Le modèle PrestataireActe doit lever une ValidationError si price <= 0."""
        from django.core.exceptions import ValidationError
        bad_pa = PrestataireActe(
            organisme=self.org,
            acte=self.acte,
            price=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            bad_pa.full_clean()

