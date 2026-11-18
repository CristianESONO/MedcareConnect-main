import json

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from dashboard import report_api
from healthcare.models import (
    OrganismeDeSante,
    SubscriptionFeature,
    SubscriptionPlan,
    SubscriptionPlanFeature,
)
from users.models import User


class ReactAdminReportsApiTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(
            username="reports_admin",
            password="StrongPass!2026",
            user_type="admin",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Reports Pioneer",
            slug="reports-pioneer",
            is_pioneer_offer=True,
            monthly_price_fcfa=12000,
        )
        self.feature = SubscriptionFeature.objects.create(
            code="reports_feature",
            label="Reports feature",
        )
        self.org_user = User.objects.create_user(
            username="reports_provider",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.org_user,
            name="Reports Clinic",
            slug="reports-clinic",
            city="Dakar",
            subscription_plan=self.plan,
            is_active=False,
        )

    def request(self, method, view, data=None, user=None, **kwargs):
        factory_method = getattr(self.factory, method.lower())
        if data is None:
            request = factory_method("/", **kwargs)
        else:
            request = factory_method(
                "/",
                data=json.dumps(data),
                content_type="application/json",
                **kwargs
            )
        request.user = user or self.admin
        return view(request)

    def test_api_requires_active_admin_and_returns_json_errors(self):
        denied = self.request("get", report_api.finances, user=AnonymousUser())
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(json.loads(denied.content)["error"], "Authentification requise.")

        inactive = User.objects.create_user(
            username="inactive_reports_admin",
            password="StrongPass!2026",
            user_type="admin",
            is_active=False,
        )
        denied = self.request("get", report_api.finances, user=inactive)
        self.assertEqual(denied.status_code, 403)
        self.assertIn("error", json.loads(denied.content))

    def test_assign_plan_reactivates_and_sets_first_subscription_date(self):
        assigned_plan = SubscriptionPlan.objects.create(
            name="Reports Assigned",
            slug="reports-assigned",
        )
        response = self.request(
            "post",
            lambda request: report_api.assign_plan(request, self.org.pk),
            {"plan_slug": assigned_plan.slug},
        )
        self.assertEqual(response.status_code, 200)
        self.org.refresh_from_db()
        self.assertTrue(self.org.is_active)
        self.assertIsNotNone(self.org.subscription_started_at)
        self.assertEqual(json.loads(response.content)["organization"]["plan_slug"], assigned_plan.slug)

    def test_plan_form_syncs_included_features_and_keeps_only_one_default(self):
        previous_default = SubscriptionPlan.objects.create(
            name="Previous default",
            slug="previous-default",
            is_default=True,
        )
        payload = {
            "name": "Custom plan",
            "slug": "custom-plan",
            "monthly_price_fcfa": 25000,
            "is_default": True,
            "is_public": True,
            "is_pioneer_offer": False,
            "order": 7,
            "included_features": [self.feature.pk],
        }
        created = self.request("post", report_api.create_plan, payload)
        self.assertEqual(created.status_code, 200, created.content)
        new_plan = SubscriptionPlan.objects.get(slug="custom-plan")
        previous_default.refresh_from_db()
        self.assertTrue(new_plan.is_default)
        self.assertFalse(previous_default.is_default)
        self.assertTrue(
            SubscriptionPlanFeature.objects.get(
                plan=new_plan, feature=self.feature
            ).included
        )

        payload["included_features"] = []
        payload["name"] = "Custom plan edited"
        updated = self.request(
            "patch",
            lambda request: report_api.update_plan(request, new_plan.pk),
            payload,
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertFalse(
            SubscriptionPlanFeature.objects.filter(
                plan=new_plan, feature=self.feature
            ).exists()
        )

    def test_feature_toggle_and_protected_plan_delete_report_explicit_results(self):
        toggled = self.request(
            "post",
            lambda request: report_api.toggle_feature(
                request, self.plan.pk, self.feature.pk
            ),
            {},
        )
        self.assertEqual(toggled.status_code, 200)
        self.assertTrue(json.loads(toggled.content)["included"])
        self.assertEqual(
            SubscriptionPlanFeature.objects.get(
                plan=self.plan, feature=self.feature
            ).included,
            True,
        )

        deleted = self.request(
            "delete",
            lambda request: report_api.delete_plan(request, self.plan.pk),
            {},
        )
        self.assertEqual(deleted.status_code, 409)
        self.assertIn("Impossible de supprimer", json.loads(deleted.content)["error"])

    def test_report_calculations_and_compliance_persistence(self):
        finance = json.loads(self.request("get", report_api.finances).content)
        self.assertEqual(finance["kpis"]["mrr"], 12000)
        self.assertEqual(finance["kpis"]["arr"], 144000)
        self.assertEqual(finance["months"][0], "M0")
        self.assertEqual(finance["scenarios"]["pessimiste"][0], 12000)

        checklist = {item["key"]: False for item in report_api.COMPLIANCE_CHECKLIST}
        saved = self.request(
            "put",
            report_api.compliance,
            {"checks": checklist},
        )
        self.assertEqual(saved.status_code, 200)
        refreshed = json.loads(self.request("get", report_api.compliance).content)
        self.assertEqual(refreshed["completed"], 0)
        self.assertTrue(all(not item["ok"] for item in refreshed["checklist"]))

        pioneers = json.loads(self.request("get", report_api.pioneers).content)
        self.assertEqual(pioneers["signed"], 1)
        self.assertEqual(pioneers["rows"][0]["reference"].startswith("CPP-"), True)
