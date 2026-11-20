"""Accès aux vues d’administration des notifications (superadmin)."""

from django.test import Client, TestCase
from django.urls import reverse

from notifications.models import NotificationChannel, NotificationEvent, NotificationSettings
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

    def test_settings_show_effective_channel_availability(self):
        settings_obj = NotificationSettings.load()
        settings_obj.in_app_enabled = True
        settings_obj.email_enabled = False
        settings_obj.smtp_host = ""
        settings_obj.smtp_from_email = ""
        settings_obj.whatsapp_enabled = False
        settings_obj.wa_phone_number_id = ""
        settings_obj.wa_access_token = ""
        settings_obj.save()

        for code, label in (
            ("in_app", "Notification dans l'app"),
            ("email", "Email"),
            ("whatsapp_cloud", "WhatsApp (Cloud API)"),
        ):
            NotificationChannel.objects.update_or_create(
                code=code,
                defaults={"label": label, "is_enabled": True},
            )

        c = Client()
        self.assertTrue(c.login(username="super_tu", password="x"))
        r = c.get(reverse("notifications:admin_settings"))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Notification dans l&#x27;app")
        self.assertContains(r, "Disponible")
        self.assertContains(r, "Indisponible")
        self.assertContains(r, "L&#x27;envoi email est désactivé")
        self.assertContains(r, "WhatsApp Cloud est désactivé")

    def test_rule_form_explains_unavailable_channel(self):
        channel = NotificationChannel.objects.update_or_create(
            code="email",
            defaults={"label": "Email", "is_enabled": True},
        )[0]
        event = NotificationEvent.objects.create(
            code="qa.email-test",
            label="Test email",
        )

        c = Client()
        self.assertTrue(c.login(username="super_tu", password="x"))
        r = c.get(
            reverse(
                "notifications:admin_rule_edit",
                args=[event.pk, channel.pk],
            )
        )

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Canal indisponible")
        self.assertContains(r, "L&#x27;envoi email est désactivé")
        self.assertContains(r, "La règle peut être préparée")
