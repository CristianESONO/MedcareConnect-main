from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from notifications.models import (
    NotificationChannel,
    NotificationEvent,
    UserNotificationPreference,
)
from users.models import User


class NotificationPreferencesReactTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notification_preferences_react",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.event = NotificationEvent.objects.create(
            code="test-message",
            label="Nouveau message",
            audience="prestataire",
        )
        self.channel = NotificationChannel.objects.create(
            code="test-email",
            label="E-mail",
        )
        self.client.force_login(self.user)

    def test_preferences_page_uses_react_and_api_returns_matrix(self):
        with patch("notifications.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(reverse("notifications:my_preferences"))
        response = self.client.get(reverse("notifications:preferences_api"))

        self.assertEqual(page.content, b"React")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["events"][0]["label"], self.event.label)
        self.assertTrue(response.json()["preferences"][0]["enabled"])

    def test_preferences_api_persists_enabled_and_disabled_channels(self):
        response = self.client.post(
            reverse("notifications:preferences_api"),
            {f"pref-{self.event.pk}-{self.channel.pk}": "on"},
        )
        self.assertEqual(response.status_code, 200)
        preference = UserNotificationPreference.objects.get(
            user=self.user,
            event=self.event,
            channel=self.channel,
        )
        self.assertTrue(preference.enabled)

        self.client.post(reverse("notifications:preferences_api"), {})
        preference.refresh_from_db()
        self.assertFalse(preference.enabled)

    def test_preferences_api_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("notifications:preferences_api"))
        self.assertEqual(response.status_code, 401)
