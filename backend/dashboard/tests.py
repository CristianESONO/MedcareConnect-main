from decimal import Decimal
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from healthcare.models import OrganismeDeSante, PlatformReview, SubscriptionPlan
from users.models import User


class DashboardStatsApiTests(TestCase):
    def test_dashboard_stats_rejects_anonymous_and_patient_users(self):
        url = reverse("dashboard_stats_api")
        self.assertEqual(self.client.get(url).status_code, 401)

        patient = User.objects.create_user(
            username="dashboard_patient",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.client.force_login(patient)
        self.assertEqual(self.client.get(url).status_code, 403)

    @patch("healthcare.services.dashboard_service.DashboardService.build_context")
    def test_dashboard_stats_uses_current_provider_metrics(self, build_context):
        provider = User.objects.create_user(
            username="dashboard_provider",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        org = OrganismeDeSante.objects.create(
            user=provider,
            name="Clinique Dashboard",
            slug="clinique-dashboard",
        )
        build_context.return_value = {
            "views_period": 18,
            "profile_views_total": 80,
            "devis_period": 4,
            "devis_value": Decimal("12500"),
            "items_period": 9,
            "actes_count": 12,
            "insurances_count": 3,
            "completion_pct": 75,
            "completion_done": 3,
            "completion_total": 4,
            "completion": [{"label": "Catalogue d'actes", "ok": True}],
            "activity_chart": {
                "labels": ["S1", "S2", "Total"],
                "series": {"devis": [2, 2, 4]},
                "meta": {"devis": {"label": "Devis générés", "color": "#3b82f6", "color_last": "#10b981"}},
                "period_sub": "7 derniers jours",
            },
            "top_actes_rows": [
                {"prestataire_acte__acte__name": "CRP", "prestataire_acte__price": Decimal("5000"), "n": 2}
            ],
            "insurance_split": [{"name": "IPM", "count": 2, "pct": 100}],
            "insurance_split_total": 2,
            "recent_views": [],
            "medplaque": {
                "reference": "CPP-2026-0001",
                "nfc_scans": 4,
                "qr_scans": 3,
                "total_access": 7,
                "nfc_active": True,
                "month_label": "M0 → M1",
            },
            "accepted_insurances_preview": [],
            "visit_source_filter": "qr",
            "rdv_requested_count": 1,
            "rdv_upcoming_count": 5,
            "pending_devis": 2,
            "unread_messages": 3,
        }
        self.client.force_login(provider)

        response = self.client.get(
            reverse("dashboard_stats_api"),
            {"period": "7j", "visit_src": "qr"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["org_name"], org.name)
        self.assertEqual(response.json()["views_period"], 18)
        self.assertEqual(response.json()["devis_value"], 12500)
        self.assertEqual(response.json()["profile_url"], reverse(
            "healthcare:organisme_detail", kwargs={"slug": org.slug}
        ))
        self.assertEqual(response.json()["top_actes"][0]["name"], "CRP")
        self.assertEqual(response.json()["medplaque"]["total_access"], 7)
        self.assertEqual(response.json()["activity"], [
            {"label": "S1", "value": 2},
            {"label": "S2", "value": 2},
        ])
        self.assertEqual(build_context.call_args.kwargs["period_key"], "7j")
        self.assertEqual(build_context.call_args.kwargs["visit_source_filter"], "qr")

    @patch("medcare_connect.views.react_app", return_value=HttpResponse("react"))
    def test_legacy_provider_dashboard_route_serves_react(self, _react_app):
        provider = User.objects.create_user(
            username="dashboard_route_provider",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        OrganismeDeSante.objects.create(
            user=provider,
            name="Clinique Route Dashboard",
            slug="clinique-route-dashboard",
        )
        self.client.force_login(provider)

        response = self.client.get(reverse("healthcare:prestataire_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"react")


class ReactAdminDashboardApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="platform_admin",
            password="StrongPass!2026",
            user_type="admin",
        )
        self.patient = User.objects.create_user(
            username="admin_dashboard_patient",
            password="StrongPass!2026",
            user_type="patient",
        )

    def test_dashboard_admin_apis_require_platform_admin(self):
        self.assertEqual(
            self.client.get(reverse("dashboard:admin_summary_api")).status_code,
            401,
        )
        self.client.force_login(self.patient)
        self.assertEqual(
            self.client.get(reverse("dashboard:admin_summary_api")).status_code,
            403,
        )

    def test_dashboard_and_list_routes_serve_react_shell(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/html"))
        self.assertEqual(
            self.client.get(reverse("dashboard:users_list")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("dashboard:organismes_list")).status_code,
            200,
        )
        for route_name in (
            "services_list",
            "actes_list",
            "assurances_list",
            "subscription_features_list",
            "reviews_list",
            "subscription_plans_list",
            "subscriptions_overview",
            "finances",
            "pioneers_overview",
            "bilans_overview",
            "conformite",
            "devis_overview",
            "activite_overview",
            "rdv_overview",
            "rdv_reminder_schedules_list",
            "messaging_overview",
        ):
            with self.subTest(route=route_name):
                response = self.client.get(reverse(f"dashboard:{route_name}"))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response["Content-Type"].startswith("text/html"))

    def test_activity_and_report_apis_are_reachable_and_require_admin(self):
        api_routes = (
            "admin_activity_overview_api",
            "admin_activity_quotes_api",
            "admin_activity_appointments_api",
            "admin_activity_reminder_schedules_api",
            "admin_activity_messaging_api",
            "admin_reports_subscriptions_api",
            "admin_reports_finances_api",
            "admin_reports_pioneers_api",
            "admin_reports_bilans_api",
            "admin_reports_compliance_api",
        )
        for route_name in api_routes:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(f"dashboard:{route_name}"))
                self.assertEqual(response.status_code, 401)
                self.assertTrue(response["Content-Type"].startswith("application/json"))

    def test_report_plan_delete_route_accepts_react_delete_request(self):
        plan = SubscriptionPlan.objects.create(
            name="Plan à supprimer",
            slug="plan-a-supprimer",
        )
        self.client.force_login(self.admin)
        response = self.client.delete(
            reverse("dashboard:admin_reports_plan_detail_api", args=[plan.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SubscriptionPlan.objects.filter(pk=plan.pk).exists())

    def test_summary_and_filtered_lists_return_existing_admin_data(self):
        org_user = User.objects.create_user(
            username="admin_dashboard_provider",
            user_type="prestataire",
        )
        org = OrganismeDeSante.objects.create(
            user=org_user,
            name="Clinique Admin Dashboard",
            slug="clinique-admin-dashboard",
            city="Dakar",
            is_active=False,
        )
        detail_page = self.client.get(
            reverse("dashboard:organisme_detail", args=[org.pk])
        )
        self.assertEqual(detail_page.status_code, 200)
        self.assertTrue(detail_page["Content-Type"].startswith("text/html"))
        self.client.force_login(self.admin)

        summary = self.client.get(reverse("dashboard:admin_summary_api"), {"period": "30j"})
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["period"], "30j")
        self.assertEqual(summary.json()["pending_organizations"][0]["id"], org.pk)

        orgs = self.client.get(
            reverse("dashboard:admin_organizations_api"),
            {"status": "pending", "q": "Clinique Admin"},
        )
        self.assertEqual(orgs.status_code, 200)
        self.assertEqual([row["id"] for row in orgs.json()["rows"]], [org.pk])
        detail = self.client.get(
            reverse("dashboard:admin_organization_detail_api", args=[org.pk])
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["organization"]["name"], org.name)
        self.assertEqual(detail.json()["stats"]["appointments"], 0)

        users = self.client.get(
            reverse("dashboard:admin_users_api"),
            {"type": "prestataire", "q": "admin_dashboard_provider"},
        )
        self.assertEqual(users.status_code, 200)
        self.assertEqual([row["id"] for row in users.json()["rows"]], [org_user.pk])

    def test_toggle_and_organization_approval_actions(self):
        user = User.objects.create_user(
            username="toggle_dashboard_user",
            password="StrongPass!2026",
            user_type="patient",
        )
        provider = User.objects.create_user(
            username="approve_dashboard_provider",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        org = OrganismeDeSante.objects.create(
            user=provider,
            name="Clinique à approuver",
            slug="clinique-a-approuver",
            is_active=False,
        )
        self.client.force_login(self.admin)

        toggle = self.client.post(
            reverse("dashboard:admin_user_toggle_api", args=[user.pk])
        )
        self.assertEqual(toggle.status_code, 200)
        self.assertFalse(toggle.json()["is_active"])

        with patch("notifications.dispatcher.dispatch") as dispatch:
            approve = self.client.post(
                reverse(
                    "dashboard:admin_organization_action_api",
                    args=[org.pk, "approve"],
                )
            )
        self.assertEqual(approve.status_code, 200)
        self.assertTrue(approve.json()["is_active"])
        org.refresh_from_db()
        self.assertTrue(org.is_verified)
        dispatch.assert_called_once()

    def test_review_moderation_api_preserves_notification_and_delete_actions(self):
        review = PlatformReview.objects.create(
            patient=self.patient,
            rating=5,
            tarifs_delais_comment="Avis à modérer",
        )
        self.client.force_login(self.admin)
        listing = self.client.get(
            reverse("dashboard:admin_reviews_api"),
            {"status": "pending"},
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["rows"][0]["id"], review.pk)

        with patch("notifications.dispatcher.dispatch") as dispatch:
            response = self.client.post(
                reverse(
                    "dashboard:admin_review_action_api",
                    args=[review.pk, "approve"],
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_approved"])
        dispatch.assert_called_once()

        response = self.client.post(
            reverse(
                "dashboard:admin_review_action_api",
                args=[review.pk, "delete"],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PlatformReview.objects.filter(pk=review.pk).exists())
