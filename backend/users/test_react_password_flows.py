from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from unittest.mock import patch

from users.models import User


class ReactPasswordFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="password_flow_user",
            email="password-flow@example.com",
            password="OriginalStrong!2026",
            user_type="prestataire",
        )

    def test_password_change_uses_react_shell_and_json_form_errors(self):
        self.client.force_login(self.user)
        with patch("users.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(reverse("users:change_password"))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.content, b"React")

        invalid = self.client.post(
            reverse("users:change_password"),
            {
                "old_password": "wrong",
                "new_password1": "ChangedStrong!2026",
                "new_password2": "ChangedStrong!2026",
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("old_password", invalid.json()["errors"])

        changed = self.client.post(
            reverse("users:change_password"),
            {
                "old_password": "OriginalStrong!2026",
                "new_password1": "ChangedStrong!2026",
                "new_password2": "ChangedStrong!2026",
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertTrue(changed.json()["ok"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ChangedStrong!2026"))

    def test_reset_request_is_enumeration_safe_and_confirm_updates_password(self):
        response = self.client.post(
            reverse("api_password_reset"),
            {"email": self.user.email},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Si cette adresse", response.json()["message"])
        self.assertEqual(len(mail.outbox), 1)

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse(
            "api_password_reset_confirm",
            kwargs={"uidb64": uid, "token": token},
        )
        checked = self.client.get(confirm_url, HTTP_ACCEPT="application/json")
        self.assertEqual(checked.status_code, 200)
        self.assertTrue(checked.json()["valid"])

        changed = self.client.post(
            confirm_url,
            {
                "new_password1": "ResetStrong!2026",
                "new_password2": "ResetStrong!2026",
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(changed.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ResetStrong!2026"))

    def test_reset_pages_serve_react(self):
        paths = [
            reverse("password_reset"),
            reverse("password_reset_done"),
            reverse("password_reset_complete"),
            reverse(
                "password_reset_confirm",
                kwargs={"uidb64": "MQ", "token": "token"},
            ),
        ]
        with patch("users.views.react_app", return_value=HttpResponse("React")):
            for path in paths:
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content, b"React")
