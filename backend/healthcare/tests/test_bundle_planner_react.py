from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch


class BundlePlannerReactTests(TestCase):
    def test_planner_page_serves_react_shell(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            response = self.client.get(reverse("healthcare:bundle_planner"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"React")

    def test_planner_json_contains_presets_and_api_urls(self):
        response = self.client.get(
            reverse("healthcare:bundle_planner"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload["presets"], list)
        self.assertEqual(payload["initial_actes"], [])
        self.assertEqual(
            payload["urls"]["plan"],
            reverse("healthcare:api_bundle_plan"),
        )
