from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import Client, SimpleTestCase, TestCase
from django.urls import resolve, reverse

from cart.models import Devis
from healthcare.models import Assurance, SearchHistory
from medcare_connect.views import react_app
from .forms import PatientProfileCompteForm
from .models import PatientProfile, User


class ReactAuthApiTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        csrf_response = self.client.get("/api/auth/csrf/")
        self.csrf_token = csrf_response.json()["csrfToken"]

    def test_patient_registration_creates_account_and_session(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "user_type": "patient",
                "account_nature": "structure",
                "first_name": "Awa",
                "last_name": "Diallo",
                "username": "awa_diallo",
                "email": "awa@example.sn",
                "phone_number": "+221770000000",
                "password1": "StrongPass!2026",
                "password2": "StrongPass!2026",
            },
            HTTP_ACCEPT="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["redirect_url"].endswith("/users/compte/panel/rdv/"))
        user = User.objects.get(username="awa_diallo")
        self.assertTrue(user.is_patient)
        self.assertTrue(PatientProfile.objects.filter(user=user).exists())
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(user.pk),
        )

    def test_registration_returns_field_errors_as_json(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "user_type": "patient",
                "account_nature": "structure",
                "username": "bad",
                "email": "not-an-email",
                "password1": "short",
                "password2": "different",
            },
            HTTP_ACCEPT="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())
        self.assertFalse(User.objects.filter(username="bad").exists())

    def test_auth_api_rejects_requests_without_csrf_token(self):
        response = Client(enforce_csrf_checks=True).post(
            "/api/auth/login/",
            {"username": "awa_diallo", "password": "password"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_login_authenticates_with_existing_django_user(self):
        user = User.objects.create_user(
            username="awa_diallo",
            email="awa@example.sn",
            password="StrongPass!2026",
            user_type="patient",
        )

        response = self.client.post(
            "/api/auth/login/",
            {
                "username": user.username,
                "password": "StrongPass!2026",
            },
            HTTP_ACCEPT="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["redirect_url"].endswith("/users/compte/panel/rdv/"))
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_login_returns_invalid_credentials_as_json(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "unknown", "password": "wrong"},
            HTTP_ACCEPT="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["username"],
            ["Nom d'utilisateur ou mot de passe incorrect."],
        )


class ReactHomeApiTests(SimpleTestCase):
    def test_public_information_pages_are_served_by_react(self):
        for path in ("/a-propos/", "/comment-ca-marche/", "/contact/", "/confiance/"):
            with self.subTest(path=path):
                self.assertIs(resolve(path).func, react_app)

    @patch("medcare_connect.views._home_vitrine_context")
    def test_home_data_serializes_vitrine_context(self, get_context):
        get_context.return_value = {
            "stats": {"providers": 2, "services": 6, "assurances": 4, "acts": 120},
            "pillars": [{
                "service": SimpleNamespace(pk=7, name="Biologie médicale", slug="biologie-medicale"),
                "act_count": 24,
                "sample_acts": "NFS, glycémie",
            }],
            "trending_actes": [{
                "acte": SimpleNamespace(pk=19, name="NFS"),
                "struct_count": 2,
                "min_price": Decimal("5000.00"),
                "category": "Biologie médicale",
                "subfamily": "Hématologie",
                "location": "Dakar",
            }],
        }

        response = self.client.get(reverse("home_vitrine_data"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stats"]["acts"], 120)
        self.assertEqual(response.json()["pillars"][0]["id"], 7)
        self.assertEqual(response.json()["trending_actes"][0]["min_price"], "5000.00")

    def test_home_data_only_allows_get_requests(self):
        response = self.client.post(reverse("home_vitrine_data"))
        self.assertEqual(response.status_code, 405)


class PatientReactOverviewApiTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient_overview",
            first_name="Awa",
            last_name="Diallo",
            email="awa-overview@example.sn",
            password="StrongPass!2026",
            user_type="patient",
        )

    def test_overview_requires_patient_authentication(self):
        response = self.client.get(reverse("users:patient_overview_api"))

        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_overview_returns_patient_counts_and_next_appointment(self):
        self.client.force_login(self.patient)

        response = self.client.get(reverse("users:patient_overview_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["first_name"], "Awa")
        self.assertEqual(
            payload["stats"],
            {
                "upcoming_appointments": 0,
                "pending_quotes": 0,
                "insurances": 0,
                "cart_items": 0,
            },
        )
        self.assertIsNone(payload["next_appointment"])

    def test_overview_rejects_non_patient_accounts(self):
        provider = User.objects.create_user(
            username="provider_overview",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(provider)

        response = self.client.get(reverse("users:patient_overview_api"))

        self.assertEqual(response.status_code, 403)

    def test_patient_react_account_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("users:patient_panel_react_rdv"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("login")))
        self.assertIn("next=", response["Location"])

    def test_patient_react_account_rejects_provider_accounts(self):
        provider = User.objects.create_user(
            username="provider_account_shell",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(provider)

        response = self.client.get(reverse("users:patient_panel_react_rdv"))

        self.assertEqual(response.status_code, 403)

    def test_patient_can_update_profile_and_location_through_api(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse("users:patient_profile_api"),
            {
                "first_name": "Awa",
                "last_name": "Ndiaye",
                "email": self.patient.email,
                "phone_number": "+221770000000",
                "date_of_birth": "",
                "address": "Dakar",
                "city": "Dakar-Plateau",
                "quartier": "Mermoz",
                "last_known_latitude": "14.716700",
                "last_known_longitude": "-17.467700",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["city"], "Dakar-Plateau")
        self.assertEqual(response.json()["last_known_latitude"], "14.716700")
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.first_name, "Awa")

    def test_password_change_keeps_patient_authenticated(self):
        self.patient.set_password("StrongPass!2026")
        self.patient.save(update_fields=["password"])
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse("users:patient_password_api"),
            {
                "old_password": "StrongPass!2026",
                "new_password1": "AnotherStrongPass!2027",
                "new_password2": "AnotherStrongPass!2027",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.check_password("AnotherStrongPass!2027"))
        self.assertEqual(
            self.client.get(reverse("users:patient_profile_api")).status_code,
            200,
        )


class PatientReactQuotesApiTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient_quotes",
            password="StrongPass!2026",
            user_type="patient",
        )

    def test_quotes_require_patient_authentication(self):
        response = self.client.get(reverse("users:patient_quotes_api"))
        self.assertEqual(response.status_code, 401)

        provider = User.objects.create_user(
            username="provider_quotes",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(provider)
        response = self.client.get(reverse("users:patient_quotes_api"))
        self.assertEqual(response.status_code, 403)

    @patch("users.patient_panel._devis_list_entries")
    def test_quotes_api_serializes_lines_actions_and_patient_scope(self, get_entries):
        self.client.force_login(self.patient)
        devis = SimpleNamespace(
            reference="DEV-12345678",
            created_at=SimpleNamespace(isoformat=lambda: "2026-02-25T10:00:00+00:00"),
        )
        get_entries.return_value = [{
            "devis": devis,
            "part": None,
            "lines": [{"acte": "CRP", "quantity": 2, "subtotal": "6000.00"}],
            "total_patient": Decimal("6000.00"),
            "closed": False,
            "actions": [{
                "url": "/messagerie/123/",
                "button_text": "Prendre un rendez-vous",
            }],
            "status_badge": {"label": "À planifier", "class": "pac-badge--wait"},
        }]

        response = self.client.get(reverse("users:patient_quotes_api"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["entries"],
            [{
                "reference": "DEV-12345678",
                "organization": "Devis",
                "created_at": "2026-02-25T10:00:00+00:00",
                "status": "À planifier",
                "status_class": "pac-badge--wait",
                "closed": False,
                "lines": [{"name": "CRP", "quantity": 2, "subtotal": "6000.00"}],
                "total_patient": "6000.00",
                "action": {
                    "url": "/messagerie/123/",
                    "label": "Prendre un rendez-vous",
                },
            }],
        )
        get_entries.assert_called_once_with(self.patient)


class PatientQuoteLegacyRedirectTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient_quote_redirect",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.devis = Devis.objects.create(
            patient=self.patient,
            total_brut=Decimal("8000"),
            total_assurance=Decimal("0"),
            total_patient=Decimal("8000"),
            details=[],
        )

    @patch("cart.devis_part_backfill.ensure_devis_has_parts")
    def test_quote_detail_legacy_url_redirects_to_react_quote_list(self, _ensure_parts):
        self.client.force_login(self.patient)

        response = self.client.get(
            reverse("users:patient_panel_devis", args=[self.devis.reference])
        )

        self.assertRedirects(
            response,
            reverse("users:patient_panel_react_devis"),
            fetch_redirect_response=False,
        )


class PatientReactInsuranceApiTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient_insurance",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.insurance = Assurance.objects.create(
            name="Assurance patient test",
            segment=Assurance.Segment.MUTUELLE,
        )

    def test_insurance_api_requires_patient_authentication(self):
        response = self.client.get(reverse("users:patient_insurance_api"))
        self.assertEqual(response.status_code, 401)

        provider = User.objects.create_user(
            username="provider_insurance",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(provider)
        response = self.client.get(reverse("users:patient_insurance_api"))
        self.assertEqual(response.status_code, 403)

    @patch("healthcare.coverage.reference_rates_for_assurance")
    def test_insurance_api_lists_options_and_reference_rates(self, get_rates):
        self.client.force_login(self.patient)
        get_rates.return_value = {"Hématologie": 70}

        response = self.client.get(
            reverse("users:patient_insurance_api"),
            {"insurance": self.insurance.pk},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["insurance_id"], self.insurance.pk)
        self.assertEqual(payload["insurance_options"][0]["name"], self.insurance.name)
        self.assertEqual(
            payload["category_rates"],
            [{
                "field": "cat_rate__hematologie",
                "label": "Hématologie",
                "value": "70",
                "reference": "70",
            }],
        )

    @patch("healthcare.coverage.reference_rates_for_assurance")
    def test_insurance_api_saves_coverage_and_direct_payment(self, get_rates):
        self.client.force_login(self.patient)
        get_rates.return_value = {"Hématologie": 70}

        response = self.client.post(
            reverse("users:patient_insurance_api"),
            {
                "has_insurance": "1",
                "insurance": str(self.insurance.pk),
                "insurance_number": "CARD-123",
                "insurance_coverage_pct": "75",
                "insurance_use_in_estimates": "on",
                "cat_rate__hematologie": "80",
            },
        )

        self.assertEqual(response.status_code, 200)
        profile = self.patient.patient_profile
        self.assertEqual(profile.insurance_id, self.insurance.pk)
        self.assertEqual(profile.insurance_number, "CARD-123")
        self.assertEqual(profile.insurance_coverage_pct, Decimal("75.00"))
        self.assertEqual(profile.insurance_coverage_by_category, {"Hématologie": 80.0})
        self.assertTrue(profile.insurance_use_in_estimates)

        response = self.client.post(
            reverse("users:patient_insurance_api"),
            {"has_insurance": "0"},
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertIsNone(profile.insurance_id)
        self.assertEqual(profile.insurance_number, "")
        self.assertIsNone(profile.insurance_coverage_pct)
        self.assertEqual(profile.insurance_coverage_by_category, {})
        self.assertFalse(response.json()["has_insurance"])

    def test_assurance_account_route_uses_react_shell(self):
        self.client.force_login(self.patient)

        response = self.client.get(reverse("users:patient_panel_react_assurance"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            resolve(reverse("users:patient_panel_react_assurance")).func.__name__,
            "patient_panel_react_home",
        )


class PatientReactSearchHistoryApiTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient_search_history",
            password="StrongPass!2026",
            user_type="patient",
        )

    def test_search_history_requires_patient_authentication(self):
        response = self.client.get(reverse("users:patient_search_history_api"))
        self.assertEqual(response.status_code, 401)

        provider = User.objects.create_user(
            username="provider_search_history",
            password="StrongPass!2026",
            user_type="prestataire",
        )
        self.client.force_login(provider)
        response = self.client.get(reverse("users:patient_search_history_api"))
        self.assertEqual(response.status_code, 403)

    def test_search_history_is_scoped_to_patient_and_encoded_for_search(self):
        self.client.force_login(self.patient)
        SearchHistory.objects.create(
            user=self.patient,
            query="CRP & NFS",
            results_count=3,
        )
        other_patient = User.objects.create_user(
            username="other_search_history",
            password="StrongPass!2026",
            user_type="patient",
        )
        SearchHistory.objects.create(
            user=other_patient,
            query="private search",
            results_count=1,
        )

        response = self.client.get(reverse("users:patient_search_history_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["query"], "CRP & NFS")
        self.assertIn("CRP+%26+NFS", payload["entries"][0]["url"])

    def test_search_history_account_route_uses_react_shell(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("users:patient_panel_react_search_history"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            resolve(reverse("users:patient_panel_react_search_history")).func.__name__,
            "patient_panel_react_home",
        )


class PatientProfileLocationFormTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="patient_location",
            password="StrongPass!2026",
            user_type="patient",
        )
        self.profile = PatientProfile.objects.create(user=user)

    def test_profile_saves_freeform_city_and_geolocation(self):
        form = PatientProfileCompteForm(
            {
                "city": "Dakar-Plateau",
                "quartier": "Mermoz",
                "last_known_latitude": "14.716700",
                "last_known_longitude": "-17.467700",
            },
            instance=self.profile,
        )

        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save()
        self.assertEqual(profile.city, "Dakar-Plateau")
        self.assertEqual(profile.quartier, "Mermoz")
        self.assertEqual(profile.last_known_latitude, Decimal("14.716700"))
        self.assertEqual(profile.last_known_longitude, Decimal("-17.467700"))

    def test_profile_requires_both_geolocation_coordinates(self):
        form = PatientProfileCompteForm(
            {"last_known_latitude": "14.7167"},
            instance=self.profile,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("last_known_latitude", form.errors)

    def test_patient_profile_page_exposes_geolocation_settings(self):
        self.client.force_login(self.profile.user)
        response = self.client.get(reverse("users:patient_profile_api"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("last_known_latitude", response.json())
        self.assertIn("last_known_longitude", response.json())
