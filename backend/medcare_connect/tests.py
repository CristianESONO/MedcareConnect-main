from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from . import views


class MedcareSnReactRouteTests(TestCase):
    @patch("medcare_connect.views.react_app", return_value=HttpResponse("React"))
    def test_medcare_sn_route_uses_react_app(self, react_app):
        response = self.client.get(reverse("medcare_sn"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"React")
        react_app.assert_called_once()

    @patch("medcare_connect.views.react_app", return_value=HttpResponse("React", status=404))
    def test_not_found_handler_uses_react_and_preserves_404(self, react_app):
        request = RequestFactory().get("/unknown-page/")

        response = views.page_not_found(request, Exception("Not found"))

        self.assertEqual(response.status_code, 404)
        react_app.assert_called_once_with(request, status=404)
