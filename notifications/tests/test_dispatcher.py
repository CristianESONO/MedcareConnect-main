"""Tests du dispatcher : destinataires, rendu de templates, journalisation."""

from django.test import TestCase

from notifications.dispatcher import (
    _resolve_recipients,
    dispatch,
    render_notification_template_string,
)
from notifications.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationRule,
    NotificationSettings,
    NotificationTemplate,
)
from users.models import User


class ResolveRecipientsAdminTest(TestCase):
    """Le rôle « admin » doit inclure les superutilisateurs même si user_type ≠ admin."""

    def setUp(self):
        self.event = NotificationEvent.objects.filter(code="acte.disabled").first()
        self.channel = NotificationChannel.objects.filter(code="in_app").first()
        self.assertIsNotNone(self.event)
        self.assertIsNotNone(self.channel)
        self.rule, _ = NotificationRule.objects.get_or_create(
            event=self.event,
            channel=self.channel,
            defaults={
                "target_roles": ["admin"],
                "notify_event_actor": False,
                "is_active": True,
            },
        )
        self.rule.target_roles = ["admin"]
        self.rule.notify_event_actor = False
        self.rule.save()

    def test_superuser_with_non_admin_user_type_is_recipient(self):
        u = User.objects.create_user(
            username="ops_super",
            email="ops@example.com",
            password="x",
            user_type="patient",
            is_superuser=True,
        )
        recipients = _resolve_recipients(self.rule, actor=None)
        ids = {r["user"].pk for r in recipients if r["user"]}
        self.assertIn(u.pk, ids)

    def test_admin_user_type_is_recipient(self):
        u = User.objects.create_user(
            username="ops_admin",
            email="admin@example.com",
            password="x",
            user_type="admin",
        )
        recipients = _resolve_recipients(self.rule, actor=None)
        ids = {r["user"].pk for r in recipients if r["user"]}
        self.assertIn(u.pk, ids)

    def test_prestataire_not_in_admin_rule(self):
        User.objects.create_user(
            username="presta_only",
            email="p@example.com",
            password="x",
            user_type="prestataire",
        )
        recipients = _resolve_recipients(self.rule, actor=None)
        usernames = {r["user"].username for r in recipients if r["user"]}
        self.assertNotIn("presta_only", usernames)


class NotifyEventActorTest(TestCase):
    def setUp(self):
        self.event = NotificationEvent.objects.filter(code="organisme.approved").first()
        self.channel = NotificationChannel.objects.filter(code="in_app").first()
        self.rule, _ = NotificationRule.objects.get_or_create(
            event=self.event,
            channel=self.channel,
            defaults={
                "target_roles": [],
                "notify_event_actor": True,
                "is_active": True,
            },
        )
        self.rule.target_roles = []
        self.rule.notify_event_actor = True
        self.rule.save()

    def test_actor_included_when_flag_set(self):
        actor = User.objects.create_user(
            username="structure_user",
            email="s@example.com",
            password="x",
            user_type="prestataire",
        )
        recipients = _resolve_recipients(self.rule, actor=actor)
        self.assertTrue(any(r["user"] and r["user"].pk == actor.pk for r in recipients))


class RenderTemplateStringTest(TestCase):
    def test_replaces_variables(self):
        class O:
            name = "Clinique Test"

        out = render_notification_template_string(
            "Bonjour {{ org.name }}",
            {"org": O()},
        )
        self.assertEqual(out, "Bonjour Clinique Test")


class DispatchLoggingTest(TestCase):
    """dispatch() crée une ligne de log par destinataire in-app (canal activé)."""

    def setUp(self):
        NotificationSettings.load()
        self.event = NotificationEvent.objects.get(code="acte.disabled")
        self.channel = NotificationChannel.objects.get(code="in_app")
        self.template = NotificationTemplate.objects.get(
            event=self.event, channel=self.channel
        )
        self.template.is_enabled = True
        self.template.save()

    def test_dispatch_acte_disabled_creates_logs(self):
        User.objects.create_user(
            username="admin_log_test",
            email="alog@example.com",
            password="x",
            user_type="admin",
        )
        before = NotificationLog.objects.filter(event=self.event).count()

        class Org:
            name = "Structure X"

        class Acte:
            name = "IRM"

        dispatch(
            "acte.disabled",
            context={
                "organisme": Org(),
                "acte": Acte(),
                "link": "/test/",
            },
            actor=None,
        )
        after = NotificationLog.objects.filter(event=self.event).count()
        self.assertGreater(after, before)
