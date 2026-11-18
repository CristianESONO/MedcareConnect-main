from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from users.models import User


class CatalogAssistantReactTests(TestCase):
    def setUp(self):
        self.provider = User.objects.create_user(
            username="catalog_assistant_provider",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(self.provider)

    def test_assistant_page_serves_react_shell(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            response = self.client.get(reverse("healthcare:chatbot_collecte"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"React")

    def test_assistant_json_provides_setup_and_catalog_data(self):
        response = self.client.get(
            reverse("healthcare:chatbot_collecte"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["has_organization"])
        self.assertIsInstance(payload["pillars"], list)
        self.assertIsInstance(payload["organization_types"], list)
        self.assertIsInstance(payload["reference_acts"], list)
