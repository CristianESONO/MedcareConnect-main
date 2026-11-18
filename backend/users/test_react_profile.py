from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from users.models import User


class GeneralProfileReactTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="general_profile_react",
            email="old@example.com",
            password="StrongPass!2026",
            user_type="prestataire",
            avatar="avatars/existing.png",
        )
        self.client.force_login(self.user)

    def test_general_profile_page_uses_react_and_json_api_updates_details(self):
        with patch("users.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(reverse("users:profile"))
        payload = self.client.get(reverse("users:user_profile_api"))

        self.assertEqual(page.content, b"React")
        self.assertEqual(payload.status_code, 200)
        self.assertEqual(payload.json()["email"], "old@example.com")

        saved = self.client.post(
            reverse("users:user_profile_api"),
            {
                "first_name": "Awa",
                "last_name": "Diop",
                "email": "awa@example.com",
                "phone_number": "+221770000000",
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["email"], "awa@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Awa")

    def test_patient_cannot_use_general_profile_api(self):
        patient = User.objects.create_user(
            username="patient_general_profile_react",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.client.force_login(patient)

        response = self.client.get(reverse("users:user_profile_api"))

        self.assertEqual(response.status_code, 403)
