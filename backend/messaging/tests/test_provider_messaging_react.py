from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from messaging.models import Conversation, Message, Notification
from users.models import User


class ProviderMessagingReactTests(TestCase):
    def setUp(self):
        self.provider = User.objects.create_user(
            username="provider_react_messages",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.patient = User.objects.create_user(
            username="patient_react_messages",
            first_name="Awa",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.conversation = Conversation.objects.create(
            patient=self.patient,
            prestataire=self.provider,
            subject="Demande de consultation",
        )

    def test_provider_inbox_route_serves_react_and_api_is_scoped(self):
        other_provider = User.objects.create_user(
            username="other_provider_react_messages",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        other_patient = User.objects.create_user(
            username="other_patient_react_messages",
            password="StrongPass!2026",
            user_type="patient",
        )
        Conversation.objects.create(
            patient=other_patient,
            prestataire=other_provider,
            subject="Autre fil",
        )
        Message.objects.create(
            conversation=self.conversation,
            sender=self.patient,
            receiver=self.provider,
            content="Bonjour",
        )
        self.client.force_login(self.provider)

        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(reverse("messaging:inbox"))
        response = self.client.get(reverse("messaging:provider_inbox_api"))

        self.assertEqual(page.content, b"React")
        self.assertEqual(response.status_code, 200)
        entries = response.json()["conversations"]
        self.assertEqual([entry["id"] for entry in entries], [self.conversation.pk])
        self.assertEqual(entries[0]["patient"], "Awa")
        self.assertEqual(entries[0]["unread_count"], 1)

    def test_provider_conversation_api_marks_read_and_sends_messages(self):
        incoming = Message.objects.create(
            conversation=self.conversation,
            sender=self.patient,
            receiver=self.provider,
            content="Pouvez-vous me confirmer le créneau ?",
        )
        self.client.force_login(self.provider)
        url = reverse(
            "messaging:provider_conversation_api",
            args=[self.conversation.pk],
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["conversation"]["patient"], "Awa")
        self.assertEqual(payload["timeline"][-1]["content"], incoming.content)
        incoming.refresh_from_db()
        self.assertTrue(incoming.is_read)

        sent = self.client.post(url, {"content": "Nous vous confirmons le rendez-vous."})
        self.assertEqual(sent.status_code, 200)
        self.assertTrue(
            self.conversation.messages.filter(
                sender=self.provider,
                content="Nous vous confirmons le rendez-vous.",
            ).exists()
        )

    def test_provider_conversation_route_serves_react(self):
        self.client.force_login(self.provider)

        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            response = self.client.get(
                reverse("messaging:conversation_detail", args=[self.conversation.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"React")

    def test_provider_cannot_read_or_message_another_provider_thread(self):
        other_provider = User.objects.create_user(
            username="another_provider_react_messages",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(other_provider)

        response = self.client.get(
            reverse(
                "messaging:provider_conversation_api",
                args=[self.conversation.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_provider_notifications_are_react_backed_and_markable(self):
        notification = Notification.objects.create(
            user=self.provider,
            notification_type="message",
            title="Nouveau message",
            content="Un patient vous a écrit.",
        )
        self.client.force_login(self.provider)

        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(reverse("messaging:notifications"))
        listing = self.client.get(reverse("messaging:provider_notifications_api"))
        marked = self.client.post(reverse("messaging:provider_notifications_api"))

        self.assertEqual(page.content, b"React")
        self.assertEqual(listing.json()["notifications"][0]["id"], notification.pk)
        self.assertEqual(marked.json()["updated"], 1)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
