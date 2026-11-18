"""Accès aux vues d’administration des notifications (superadmin)."""

from django.test import Client, TestCase
from django.urls import reverse

from users.models import User


class PatientWhatsAppAdminViewTest(TestCase):
    def setUp(self):
        self.url = reverse("notifications:admin_patient_wa_messages")
        self.super = User.objects.create_user(
            username="super_tu",
            email="super@example.com",
            password="x",
            is_superuser=True,
        )

    def test_anonymous_gets_react_shell_but_admin_api_rejects_access(self):
        r = Client().get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Type"].startswith("text/html"))
        api_response = Client().get(reverse("notifications:admin_settings_api"))
        self.assertEqual(api_response.status_code, 401)

    def test_superuser_gets_react_shell(self):
        c = Client()
        self.assertTrue(c.login(username="super_tu", password="x"))
        for route_name in (
            "admin_settings",
            "admin_rules",
            "admin_templates",
            "admin_patient_wa_messages",
            "admin_logs",
        ):
            with self.subTest(route=route_name):
                response = c.get(reverse(f"notifications:{route_name}"))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response["Content-Type"].startswith("text/html"))
