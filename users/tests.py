from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticatedAdminRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(
            username="admin-redirect-test",
            password="test-password",
            user_type="admin",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_auth_pages_redirect_authenticated_admin_to_dashboard(self):
        for route_name in ("login", "register"):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertRedirects(
                    response,
                    reverse("dashboard:index"),
                    fetch_redirect_response=False,
                )

    def test_landing_header_shows_admin_access_instead_of_auth_links(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Administration")
        self.assertNotContains(response, 'href="/connexion/"')
        self.assertEqual(
            response.content.count(
                b'class="mc-landing-btn mc-landing-btn-login">Administration</a>'
            ),
            1,
        )
        self.assertContains(
            response,
            'href="/dashboard/" class="mc-landing-drawer-link"',
        )
