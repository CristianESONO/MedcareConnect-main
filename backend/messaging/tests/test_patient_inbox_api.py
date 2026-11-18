from django.test import TestCase
from django.urls import resolve, reverse

from messaging.models import Conversation, Message, Notification
from users.models import User


class PatientInboxApiTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient_inbox_api",
            first_name="Awa",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.provider = User.objects.create_user(
            username="provider_inbox_api",
            first_name="Clinique",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.conversation = Conversation.objects.create(
            patient=self.patient,
            prestataire=self.provider,
            subject="Demande de consultation",
        )
        Message.objects.create(
            conversation=self.conversation,
            sender=self.provider,
            receiver=self.patient,
            content="Votre demande est bien reçue.",
            is_read=False,
        )

    def test_inbox_api_requires_patient_authentication(self):
        response = self.client.get(reverse("messaging:patient_inbox_api"))
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.provider)
        response = self.client.get(reverse("messaging:patient_inbox_api"))
        self.assertEqual(response.status_code, 403)

    def test_inbox_api_serializes_only_patient_conversations(self):
        other_patient = User.objects.create_user(
            username="other_patient_inbox_api",
            password="StrongPass!2026",
            user_type="patient",
        )
        Conversation.objects.create(
            patient=other_patient,
            prestataire=self.provider,
            subject="Conversation privée",
        )
        self.client.force_login(self.patient)

        response = self.client.get(reverse("messaging:patient_inbox_api"))

        self.assertEqual(response.status_code, 200)
        conversations = response.json()["conversations"]
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]["id"], self.conversation.pk)
        self.assertEqual(conversations[0]["organization"], "Clinique")
        self.assertEqual(conversations[0]["preview"], "Votre demande est bien reçue.")
        self.assertEqual(conversations[0]["unread_count"], 1)
        self.assertEqual(
            conversations[0]["url"],
            reverse("messaging:conversation_detail", args=[self.conversation.pk]),
        )

    def test_patient_inbox_route_serves_react_shell(self):
        self.client.force_login(self.patient)

        response = self.client.get(reverse("messaging:inbox"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            resolve(reverse("messaging:inbox")).func.__name__,
            "inbox",
        )


class PatientConversationApiTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient_thread_api",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.provider = User.objects.create_user(
            username="provider_thread_api",
            first_name="Centre Médical",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.conversation = Conversation.objects.create(
            patient=self.patient,
            prestataire=self.provider,
            subject="Conversation générale",
        )

    def test_patient_thread_api_enforces_authentication_and_ownership(self):
        url = reverse(
            "messaging:patient_conversation_api",
            args=[self.conversation.pk],
        )
        self.assertEqual(self.client.get(url).status_code, 401)

        other_patient = User.objects.create_user(
            username="other_thread_api",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.client.force_login(other_patient)
        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.force_login(self.provider)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_patient_thread_api_reads_messages_and_marks_them_read(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.provider,
            receiver=self.patient,
            content="Votre demande est reçue.",
            is_read=False,
        )
        self.client.force_login(self.patient)

        response = self.client.get(
            reverse("messaging:patient_conversation_api", args=[self.conversation.pk])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["conversation"]["organization"], "Centre Médical")
        self.assertTrue(payload["conversation"]["can_send_free_message"])
        self.assertEqual(payload["timeline"][-1]["content"], "Votre demande est reçue.")
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_patient_can_send_message_in_general_conversation(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse("messaging:patient_conversation_api", args=[self.conversation.pk]),
            {"content": "Bonjour, je souhaite un renseignement."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertTrue(
            self.conversation.messages.filter(
                sender=self.patient,
                content="Bonjour, je souhaite un renseignement.",
            ).exists()
        )

    def test_closed_conversation_rejects_patient_message(self):
        self.conversation.thread_status = Conversation.STATUS_CLOSED
        self.conversation.save(update_fields=["thread_status"])
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse("messaging:patient_conversation_api", args=[self.conversation.pk]),
            {"content": "Bonjour"},
        )

        self.assertEqual(response.status_code, 409)


class PatientNotificationsApiTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient_notifications_api",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.message_notification = Notification.objects.create(
            user=self.patient,
            notification_type="message",
            title="Nouveau message",
            content="Votre demande est reçue.",
            link="/messaging/",
        )
        self.reminder = Notification.objects.create(
            user=self.patient,
            notification_type="rdv",
            title="Rappel de rendez-vous",
            content="Votre rendez-vous approche.",
        )

    def test_api_lists_separate_patient_notifications_and_reminders(self):
        self.client.force_login(self.patient)

        inbox_response = self.client.get(
            reverse("messaging:patient_notifications_api"), {"scope": "inbox"}
        )
        reminders_response = self.client.get(
            reverse("messaging:patient_notifications_api"), {"scope": "rappels"}
        )

        self.assertEqual(inbox_response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in inbox_response.json()["notifications"]],
            [self.message_notification.pk],
        )
        self.assertEqual(reminders_response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in reminders_response.json()["notifications"]],
            [self.reminder.pk],
        )

    def test_api_marks_only_requested_patient_scope_as_read(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse("messaging:patient_notifications_api"),
            {"scope": "rappels"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.message_notification.refresh_from_db()
        self.reminder.refresh_from_db()
        self.assertFalse(self.message_notification.is_read)
        self.assertTrue(self.reminder.is_read)

    def test_api_requires_patient_authentication(self):
        url = reverse("messaging:patient_notifications_api")
        self.assertEqual(self.client.get(url).status_code, 401)

        provider = User.objects.create_user(
            username="provider_notifications_api",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(provider)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_patient_notifications_and_reminders_routes_serve_react(self):
        self.client.force_login(self.patient)

        notifications_response = self.client.get(reverse("messaging:notifications"))
        reminders_response = self.client.get(reverse("messaging:rappels"))

        self.assertEqual(notifications_response.status_code, 200)
        self.assertEqual(reminders_response.status_code, 200)

    def test_api_rejects_unknown_notification_scope(self):
        self.client.force_login(self.patient)

        response = self.client.get(
            reverse("messaging:patient_notifications_api"), {"scope": "unknown"}
        )

        self.assertEqual(response.status_code, 400)
