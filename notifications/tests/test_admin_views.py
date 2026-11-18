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

    def test_anonymous_redirects_to_login(self):
        r = Client().get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("connexion", (r.url or "").lower())

    def test_superuser_gets_form(self):
        c = Client()
        self.assertTrue(c.login(username="super_tu", password="x"))
        r = c.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Enregistrer les messages")
