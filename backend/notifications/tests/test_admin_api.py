import json
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from notifications import admin_api
from notifications.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationRule,
    NotificationSettings,
)
from users.models import User


class NotificationAdminApiTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(
            username="notification-admin",
            email="admin@example.com",
            password="secret",
            is_superuser=True,
        )
        self.user = User.objects.create_user(
            username="notification-user",
            email="user@example.com",
            password="secret",
        )
        self.event = NotificationEvent.objects.create(
            code="api.test", label="API test", audience="admin"
        )
        self.channel = NotificationChannel.objects.create(
            code="api_test", label="API test channel"
        )

    def call_api(self, view, method="get", data=None, user=None, **kwargs):
        if method == "post":
            request = self.factory.post(
                "/notifications/api/admin/",
                data=json.dumps(data or {}),
                content_type="application/json",
            )
        else:
            request = self.factory.get("/notifications/api/admin/", data=data)
        request.user = user if user is not None else self.admin
        response = view(request, **kwargs)
        response.json_data = json.loads(response.content)
        return response

    def test_api_requires_active_admin(self):
        request = self.factory.get("/notifications/api/admin/rules/")
        request.user = self.user
        response = admin_api.rules_api(request)
        self.assertEqual(response.status_code, 403)

        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        request = self.factory.get("/notifications/api/admin/rules/")
        request.user = self.user
        response = admin_api.rules_api(request)
        self.assertEqual(response.status_code, 401)

        request = self.factory.get("/notifications/api/admin/rules/")
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        response = admin_api.rules_api(request)
        self.assertEqual(response.status_code, 401)

    def test_settings_validate_and_preserve_blank_secrets(self):
        settings = NotificationSettings.load()
        settings.smtp_password = "smtp-secret"
        settings.wa_access_token = "wa-secret"
        settings.save()

        unsafe_get = self.call_api(admin_api.settings_api)
        self.assertEqual(unsafe_get.status_code, 200)
        self.assertNotIn("smtp-secret", unsafe_get.content.decode())
        self.assertNotIn("wa-secret", unsafe_get.content.decode())
        self.assertTrue(unsafe_get.json_data["settings"]["smtp_password_configured"])
        self.assertTrue(unsafe_get.json_data["settings"]["wa_access_token_configured"])

        invalid = self.call_api(admin_api.settings_api, method="post", data={
            "action": "save_smtp",
            "smtp_use_tls": True,
            "smtp_use_ssl": True,
        })
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("__all__", invalid.json_data["errors"])

        valid = self.call_api(admin_api.settings_api, method="post", data={
            "action": "save_smtp",
            "email_enabled": False,
            "smtp_host": "smtp.example.com",
            "smtp_port": 2525,
            "smtp_user": "mailer",
            "smtp_password": "",
            "smtp_use_tls": True,
            "smtp_use_ssl": False,
            "smtp_from_email": "no-reply@example.com",
            "smtp_from_name": "MedCare",
            "smtp_reply_to": "",
        })
        self.assertEqual(valid.status_code, 200)
        settings.refresh_from_db()
        self.assertEqual(settings.smtp_password, "smtp-secret")
        self.assertEqual(settings.smtp_host, "smtp.example.com")

        wa = self.call_api(admin_api.settings_api, method="post", data={
            "action": "save_wa",
            "whatsapp_enabled": False,
            "wa_phone_number_id": "phone-id",
            "wa_business_account_id": "business-id",
            "wa_access_token": "",
            "wa_api_version": "v20.0",
        })
        self.assertEqual(wa.status_code, 200)
        settings.refresh_from_db()
        self.assertEqual(settings.wa_access_token, "wa-secret")

    def test_rules_matrix_and_edit_use_existing_form(self):
        matrix = self.call_api(admin_api.rules_api)
        self.assertEqual(matrix.status_code, 200)
        self.assertTrue(any(row["event_id"] == self.event.pk for row in matrix.json_data["rules"]))

        invalid = self.call_api(
            admin_api.rule_api,
            method="post",
            data={"target_roles": ["unknown"], "is_active": True},
            event_id=self.event.pk,
            channel_id=self.channel.pk,
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("target_roles", invalid.json_data["errors"])

        saved = self.call_api(
            admin_api.rule_api,
            method="post",
            data={
                "target_roles": ["admin", "patient"],
                "target_users": [],
                "extra_emails": "ops@example.com",
                "notify_event_actor": True,
                "is_active": True,
                "note": "Ops",
            },
            event_id=self.event.pk,
            channel_id=self.channel.pk,
        )
        self.assertEqual(saved.status_code, 200)
        rule = NotificationRule.objects.get(event=self.event, channel=self.channel)
        self.assertEqual(rule.target_roles, ["admin", "patient"])
        self.assertEqual(rule.extra_emails, "ops@example.com")
        self.assertTrue(rule.notify_event_actor)

    def test_logs_filters_and_resend_dispatcher_result(self):
        log = NotificationLog.objects.create(
            event=self.event,
            channel=self.channel,
            recipient_address="recipient@example.com",
            subject="Test subject",
            status=NotificationLog.STATUS_FAILED,
            error="SMTP failed",
        )
        filtered = self.call_api(
            admin_api.logs_api,
            data={"status": "failed", "q": "recipient@example.com", "page": "1"},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual([item["id"] for item in filtered.json_data["logs"]], [log.pk])
        self.assertEqual(filtered.json_data["pagination"]["number"], 1)

        new_log = NotificationLog.objects.create(
            event=self.event,
            channel=self.channel,
            recipient_address="recipient@example.com",
            subject="Test subject",
            status=NotificationLog.STATUS_SENT,
        )
        with patch("notifications.admin_api.resend_notification_log", return_value=(new_log, "")) as resend:
            response = self.call_api(
                admin_api.log_resend_api,
                method="post",
                data={"log_id": log.pk},
            )
        resend.assert_called_once_with(log.pk)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json_data["ok"])
        self.assertEqual(response.json_data["new_log_id"], new_log.pk)
