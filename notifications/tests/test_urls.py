"""Résolution des URLs de l’espace admin notifications."""

from django.test import TestCase
from django.urls import NoReverseMatch, resolve, reverse


class NotificationsAdminUrlsTest(TestCase):
    def test_named_routes_resolve(self):
        names = [
            "notifications:admin_settings",
            "notifications:admin_rules",
            "notifications:admin_rule_edit",
            "notifications:admin_templates",
            "notifications:admin_patient_wa_messages",
            "notifications:admin_logs",
            "notifications:admin_log_resend",
            "notifications:my_preferences",
        ]
        for name in names:
            with self.subTest(name=name):
                if name == "notifications:admin_rule_edit":
                    url = reverse(name, args=[1, 1])
                else:
                    url = reverse(name)
                match = resolve(url)
                self.assertEqual(match.url_name, name.split(":")[1])

    def test_rule_edit_requires_integer_ids(self):
        with self.assertRaises(NoReverseMatch):
            reverse("notifications:admin_rule_edit", args=["a", "b"])
