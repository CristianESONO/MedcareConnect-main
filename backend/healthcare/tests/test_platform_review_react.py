from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from healthcare.models import ActeMedical, PlatformReview, ServiceMedical
from users.models import User


class PlatformReviewReactTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="platform_review_patient",
            password="StrongPass!2026",
            user_type="patient",
        )
        service = ServiceMedical.objects.create(name="Service avis")
        self.act = ActeMedical.objects.create(
            name="Examen avis",
            service_medical_category=service,
            level=3,
        )
        self.client.force_login(self.patient)

    def test_review_page_serves_react_and_json_form_data(self):
        with patch("medcare_connect.views.react_app", return_value=HttpResponse("React")):
            page = self.client.get(reverse("healthcare:platform_review"))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.content, b"React")

        payload = self.client.get(
            reverse("healthcare:platform_review"),
            HTTP_ACCEPT="application/json",
        ).json()
        self.assertFalse(payload["has_review"])
        self.assertIn(self.act.name, [
            act["name"]
            for group in payload["groups"]
            for act in group["acts"]
        ])

    def test_review_requires_an_act_and_accepts_a_valid_submission(self):
        url = reverse("healthcare:platform_review")
        invalid = self.client.post(
            url,
            {"rating": "5", "tarifs_delais_comment": "Clair"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("__all__", invalid.json()["errors"])

        response = self.client.post(
            url,
            {
                "rating": "4",
                "actes": [str(self.act.pk)],
                "tarifs_delais_comment": "Délais satisfaisants.",
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redirect_url"], reverse("healthcare:platform_review_google"))
        review = PlatformReview.objects.get(patient=self.patient)
        self.assertEqual(review.rating, 4)
        self.assertEqual(list(review.actes.all()), [self.act])
