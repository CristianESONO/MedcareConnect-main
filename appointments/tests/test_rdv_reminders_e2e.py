"""Tests E2E — prérequis actes & rappels RDV configurables."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import RdvReminderSchedule, RendezVous, RendezVousReminderLog
from appointments.reminders import (
    due_reminders,
    prerequisites_for_rdv,
    rdv_matches_schedule,
    send_rdv_reminder,
)
from healthcare.models import ActeMedical, OrganismeDeSante, ServiceMedical, SubscriptionPlan
from notifications.models import NotificationLog
from users.models import User


class ReminderHelpersTest(TestCase):
    def setUp(self):
        self.svc = ServiceMedical.objects.create(name="Imagerie QA")
        self.acte_irm = ActeMedical.objects.create(
            name="IRM QA",
            service_medical_category=self.svc,
            level=3,
            rdv_prerequisites="À jeun 6 h, retirer bijoux métalliques.",
        )
        self.acte_radio = ActeMedical.objects.create(
            name="Radio QA",
            service_medical_category=self.svc,
            level=3,
        )
        plan = SubscriptionPlan.objects.create(name="Plan QA", slug="plan-qa-reminder")
        prest = User.objects.create_user(
            username="prest_reminder_qa",
            email="prest_r@qa.test",
            password="x",
            user_type="prestataire",
        )
        self.org = OrganismeDeSante.objects.create(
            user=prest,
            name="Centre QA Rappels",
            address="Dakar",
            subscription_plan=plan,
            is_active=True,
        )
        self.patient = User.objects.create_user(
            username="patient_reminder_qa",
            email="pat_r@qa.test",
            password="x",
            user_type="patient",
        )
        self.rdv = RendezVous.objects.create(
            patient=self.patient,
            organisme=self.org,
            start=timezone.now() + timedelta(days=1),
            status=RendezVous.STATUS_CONFIRMED,
            actes_snapshot=[
                {
                    "acte_id": self.acte_irm.pk,
                    "acte": self.acte_irm.name,
                    "quantity": 1,
                    "subtotal": "15000",
                    "patient_cost": "15000",
                },
                {
                    "acte": self.acte_radio.name,
                    "quantity": 1,
                    "subtotal": "5000",
                },
            ],
            total_brut=Decimal("20000"),
            total_patient=Decimal("20000"),
        )

    def test_prerequisites_by_acte_id_and_name_fallback(self):
        text = prerequisites_for_rdv(self.rdv)
        self.assertIn("IRM QA", text)
        self.assertIn("À jeun 6 h", text)
        self.assertNotIn("Radio QA", text)

    def test_get_prerequisites_display_on_model(self):
        self.assertEqual(self.rdv.get_prerequisites_display(), prerequisites_for_rdv(self.rdv))

    def test_rdv_matches_schedule_global_and_targeted(self):
        global_rule = RdvReminderSchedule.objects.create(
            label="Global QA",
            offset_value=1,
            offset_unit=RdvReminderSchedule.UNIT_DAYS,
        )
        targeted = RdvReminderSchedule.objects.create(
            label="IRM only",
            offset_value=3,
            offset_unit=RdvReminderSchedule.UNIT_DAYS,
        )
        targeted.actes.add(self.acte_radio)
        self.assertTrue(rdv_matches_schedule(self.rdv, global_rule))
        self.assertFalse(rdv_matches_schedule(self.rdv, targeted))

        targeted.actes.set([self.acte_irm])
        self.assertTrue(rdv_matches_schedule(self.rdv, targeted))

    def test_due_reminders_finds_rdv_in_window(self):
        schedule = RdvReminderSchedule.objects.filter(label="Veille du RDV (J-1)").first()
        self.assertIsNotNone(schedule)
        schedule.tolerance_minutes = 120
        schedule.save()
        self.rdv.start = timezone.now() + timedelta(hours=23)
        self.rdv.save(update_fields=["start"])

        pairs = due_reminders(now=timezone.now(), schedule=schedule)
        refs = {r.reference for r, _ in pairs}
        self.assertIn(self.rdv.reference, refs)

    def test_send_rdv_reminder_idempotent(self):
        schedule = RdvReminderSchedule.objects.create(
            label="Test send",
            offset_value=30,
            offset_unit=RdvReminderSchedule.UNIT_MINUTES,
            tolerance_minutes=60,
        )
        self.rdv.start = timezone.now() + timedelta(minutes=30)
        self.rdv.save(update_fields=["start"])

        before_logs = NotificationLog.objects.count()
        self.assertTrue(send_rdv_reminder(self.rdv, schedule))
        self.assertTrue(
            RendezVousReminderLog.objects.filter(
                rendez_vous=self.rdv, schedule=schedule
            ).exists()
        )
        self.assertGreaterEqual(NotificationLog.objects.count(), before_logs)

        # Second envoi bloqué par le log.
        pairs = due_reminders(now=timezone.now(), schedule=schedule)
        self.assertEqual(
            sum(1 for r, s in pairs if r.pk == self.rdv.pk and s.pk == schedule.pk),
            0,
        )

    def test_reminder_posts_to_messaging_thread_with_prerequisites(self):
        from cart.models import Devis, DevisPart
        from messaging.models import Message
        from messaging.thread import conversation_for_rdv

        details = [{
            "acte_id": self.acte_irm.pk,
            "acte": self.acte_irm.name,
            "quantity": 1,
            "patient_cost": "1700",
        }]
        devis = Devis.objects.create(
            patient=self.patient,
            total_brut=17000,
            total_patient=1700,
            details=details,
        )
        part = DevisPart.objects.create(
            devis=devis,
            organisme=self.org,
            details=details,
            total_brut=17000,
            total_patient=1700,
        )
        self.rdv.devis = devis
        self.rdv.devis_part = part
        self.rdv.save(update_fields=["devis", "devis_part"])

        schedule = RdvReminderSchedule.objects.create(
            label="Thread test",
            offset_value=1,
            offset_unit=RdvReminderSchedule.UNIT_HOURS,
            tolerance_minutes=30,
        )
        RendezVousReminderLog.objects.filter(rendez_vous=self.rdv, schedule=schedule).delete()

        self.assertTrue(send_rdv_reminder(self.rdv, schedule))

        conv = conversation_for_rdv(self.rdv)
        self.assertIsNotNone(conv)
        msg = Message.objects.filter(
            conversation=conv,
            payload__event="reminder",
            payload__schedule_id=schedule.pk,
        ).first()
        self.assertIsNotNone(msg)
        self.assertIn("À jeun", msg.payload.get("prerequisites", ""))
        self.assertIn("schedule_label", msg.payload)


class DashboardReminderCrudTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="super_reminder_crud",
            email="super_crud@qa.test",
            password="test-pass-qa-123",
            user_type="admin",
            is_superuser=True,
        )
        self.client = Client()
        self.client.force_login(self.admin)
        self.svc = ServiceMedical.objects.create(name="Labo QA CRUD")
        self.acte = ActeMedical.objects.create(
            name="NFS QA",
            service_medical_category=self.svc,
            level=3,
        )

    def test_list_reminder_schedules_200(self):
        r = self.client.get(reverse("dashboard:rdv_reminder_schedules_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Veille du RDV")

    def test_create_reminder_schedule_post(self):
        r = self.client.post(
            reverse("dashboard:rdv_reminder_schedule_create"),
            {
                "label": "2 h avant QA",
                "offset_value": 2,
                "offset_unit": RdvReminderSchedule.UNIT_HOURS,
                "tolerance_minutes": 20,
                "include_prerequisites": "on",
                "is_active": "on",
                "order": 99,
                "actes": [str(self.acte.pk)],
            },
        )
        self.assertEqual(r.status_code, 302)
        created = RdvReminderSchedule.objects.filter(label="2 h avant QA").first()
        self.assertIsNotNone(created)
        self.assertIn(self.acte, created.actes.all())

    def test_edit_acte_with_prerequisites(self):
        r = self.client.post(
            reverse("dashboard:acte_edit", kwargs={"pk": self.acte.pk}),
            {
                "name": self.acte.name,
                "code": "",
                "description": "",
                "rdv_prerequisites": "Apporter ordonnance.",
                "service_medical_category": self.svc.pk,
                "parent_service": "",
                "level": 3,
                "reference_price": "",
                "is_active": "on",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.acte.refresh_from_db()
        self.assertEqual(self.acte.rdv_prerequisites, "Apporter ordonnance.")

    def test_actes_list_shows_prerequisites_badge(self):
        self.acte.rdv_prerequisites = "Jeûne 12 h"
        self.acte.save()
        r = self.client.get(reverse("dashboard:actes_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "NFS QA")


class PatientAndAdminRdvViewsTest(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name="Plan QA Views", slug="plan-qa-views")
        prest = User.objects.create_user(
            username="prest_views_qa",
            password="x",
            user_type="prestataire",
        )
        self.org = OrganismeDeSante.objects.create(
            user=prest,
            name="Clinique QA Views",
            address="Dakar",
            subscription_plan=plan,
            is_active=True,
        )
        self.patient = User.objects.create_user(
            username="patient_views_qa",
            password="x",
            user_type="patient",
        )
        self.admin = User.objects.create_user(
            username="admin_views_qa",
            password="x",
            user_type="admin",
            is_superuser=True,
        )
        svc = ServiceMedical.objects.create(name="Svc Views")
        acte = ActeMedical.objects.create(
            name="Echo QA",
            service_medical_category=svc,
            level=3,
            rdv_prerequisites="Vessie pleine.",
        )
        self.rdv = RendezVous.objects.create(
            patient=self.patient,
            organisme=self.org,
            start=timezone.now() + timedelta(days=2),
            status=RendezVous.STATUS_CONFIRMED,
            actes_snapshot=[{"acte_id": acte.pk, "acte": acte.name, "quantity": 1}],
        )
        self.client = Client()

    def test_patient_rdv_panel_renders_prerequisites(self):
        self.client.force_login(self.patient)
        r = self.client.get(reverse("users:patient_panel_tab", kwargs={"tab": "rdv"}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Consignes avant le RDV")
        self.assertContains(r, "Vessie pleine")

    def test_admin_rdv_detail_renders_prerequisites(self):
        self.client.force_login(self.admin)
        r = self.client.get(
            reverse("dashboard:rdv_admin_detail", kwargs={"reference": self.rdv.reference})
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Prérequis / consignes patient")
        self.assertContains(r, "Vessie pleine")


class ManagementCommandTest(TestCase):
    def test_send_rdv_reminders_dry_run_exits_zero(self):
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("send_rdv_reminders", "--dry-run", stdout=out)
        self.assertIn("règle", out.getvalue().lower())
