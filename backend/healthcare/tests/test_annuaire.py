"""Tests annuaire établissements."""

from django.http import HttpResponse
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from unittest.mock import patch

from healthcare.annuaire import build_annuaire_context, organisme_category_key
from healthcare.models import OrganismeDeSante, SubscriptionPlan, TypeOrganisme
from users.models import User


class AnnuaireTests(TestCase):
    def setUp(self):
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            slug="essentiel-annuaire-tu",
            defaults={
                "name": "Essentiel TU",
                "is_public": True,
                "monthly_price_fcfa": 39000,
                "order": 20,
            },
        )
        self.t_labo = TypeOrganisme.objects.create(name="Laboratoire", slug="labo-ann-tu")
        self.t_img = TypeOrganisme.objects.create(name="Centre d'imagerie", slug="img-ann-tu")
        u1 = User.objects.create_user("org1", "o1@e.com", "x", user_type="prestataire")
        u2 = User.objects.create_user("org2", "o2@e.com", "x", user_type="prestataire")
        OrganismeDeSante.objects.create(
            user=u1,
            name="Labo Test",
            slug="labo-test-ann",
            city="Dakar",
            address="Dakar",
            type_organisme=self.t_labo,
            subscription_plan=self.plan,
            is_active=True,
        )
        OrganismeDeSante.objects.create(
            user=u2,
            name="Imagerie Test",
            slug="img-test-ann",
            city="Dakar",
            address="Dakar",
            type_organisme=self.t_img,
            subscription_plan=self.plan,
            is_active=True,
        )

    def test_annuaire_page_uses_react_shell(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            response = self.client.get("/sante/annuaire/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"React")

    def test_centres_redirects_to_annuaire(self):
        response = self.client.get("/sante/centres/?q=test", follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/sante/annuaire/?q=test")

    def test_annuaire_api_filters_and_serializes_organizations(self):
        response = self.client.get(
            "/sante/api/annuaire/?type_cat=labo",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["results_count"], 1)
        self.assertEqual(payload["results"][0]["name"], "Labo Test")
        self.assertEqual(payload["results"][0]["profile_url"], "/sante/labo-test-ann/")

    def test_annuaire_filter_by_type_category(self):
        rf = RequestFactory()
        req = rf.get("/sante/annuaire/", {"type_cat": "labo"})
        SessionMiddleware(lambda request: None).process_request(req)
        ctx = build_annuaire_context(req)
        names = [row["org"].name for row in ctx["rows"]]
        self.assertIn("Labo Test", names)
        self.assertNotIn("Imagerie Test", names)


def test_organisme_category_key_labo():
    class _Type:
        name = "Laboratoire"

    class _Org:
        type_organisme = _Type()

    assert organisme_category_key(_Org()) == "labo"
