from django.test import TestCase

from healthcare.models import TypeOrganisme
from users.models import User


class ReactAdminApiTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="react_admin",
            email="admin@example.com",
            password="StrongPass!2026",
        )
        self.regular_user = User.objects.create_user(
            username="regular_react_admin",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.platform_admin = User.objects.create_user(
            username="platform_role_admin",
            password="StrongPass!2026",
            user_type="admin",
        )

    def test_admin_urls_use_react_shell(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/html"))

    def test_admin_logout_redirects_to_medcare_login(self):
        for user in (self.admin_user, self.platform_admin):
            with self.subTest(username=user.username):
                self.client.force_login(user)

                response = self.client.get("/users/deconnexion/")

                self.assertRedirects(response, "/connexion/", fetch_redirect_response=False)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_api_requires_staff_session(self):
        response = self.client.get("/admin/api/models/")
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.regular_user)
        response = self.client.get("/admin/api/models/")
        self.assertEqual(response.status_code, 403)

    def test_admin_model_list_and_form_api_support_registered_models(self):
        self.client.force_login(self.admin_user)
        models_response = self.client.get("/admin/api/models/")
        self.assertEqual(models_response.status_code, 200)
        self.assertTrue(
            any(
                item["app_label"] == "healthcare"
                and item["model_name"] == "typeorganisme"
                for item in models_response.json()["models"]
            )
        )
        for item in models_response.json()["models"]:
            with self.subTest(model=f"{item['app_label']}.{item['model_name']}"):
                response = self.client.get(
                    f"/admin/api/models/{item['app_label']}/{item['model_name']}/form/"
                )
                expected_status = 200 if item["can_add"] else 403
                self.assertEqual(response.status_code, expected_status, response.content)

        form_response = self.client.get(
            "/admin/api/models/healthcare/typeorganisme/form/"
        )
        self.assertEqual(form_response.status_code, 200)
        self.assertTrue(
            {"name", "slug"}.issubset(
                {field["name"] for field in form_response.json()["fields"]}
            )
        )

        create_response = self.client.post(
            "/admin/api/models/healthcare/typeorganisme/form/",
            {"name": "Centre React Admin", "slug": "centre-react-admin", "order": 12, "icon": "hospital"},
        )
        self.assertEqual(create_response.status_code, 200, create_response.content)
        pk = create_response.json()["pk"]
        self.assertTrue(TypeOrganisme.objects.filter(pk=pk).exists())

        update_response = self.client.post(
            f"/admin/api/models/healthcare/typeorganisme/{pk}/",
            {"name": "Centre modifié", "slug": "centre-react-admin", "order": 13, "icon": "hospital"},
        )
        self.assertEqual(update_response.status_code, 200, update_response.content)
        self.assertEqual(TypeOrganisme.objects.get(pk=pk).name, "Centre modifié")

        delete_response = self.client.post(
            f"/admin/api/models/healthcare/typeorganisme/{pk}/",
            {"action": "delete"},
        )
        self.assertEqual(delete_response.status_code, 200, delete_response.content)
        self.assertFalse(TypeOrganisme.objects.filter(pk=pk).exists())

    def test_staff_login_api_creates_admin_session(self):
        response = self.client.post(
            "/admin/api/session/",
            {"username": self.admin_user.username, "password": "StrongPass!2026"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_platform_admin_role_can_access_react_admin_without_staff_flag(self):
        self.client.force_login(self.platform_admin)
        models_response = self.client.get("/admin/api/models/")
        self.assertEqual(models_response.status_code, 200)
        self.assertTrue(models_response.json()["models"])
        form_response = self.client.get(
            "/admin/api/models/healthcare/typeorganisme/form/"
        )
        self.assertEqual(form_response.status_code, 200)
