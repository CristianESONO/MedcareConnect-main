from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, ServiceMedical, TypeOrganisme
from users.models import User
from cart.models import Cart, CartItem, Devis, DevisPart


class UnverifiedStructuresTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.type_clinique = TypeOrganisme.objects.create(name="Clinique", slug="clinique")
        self.service = ServiceMedical.objects.create(name="Consultation", slug="consultation", is_active=True)
        self.acte = ActeMedical.objects.create(
            name="Consultation Test",
            service_medical_category=self.service,
            level=3,
            is_active=True,
        )

        # Unverified structure
        self.u_unverified = User.objects.create_user("unverified_doc", "unverified@test.sn", "pass123")
        self.org_unverified = OrganismeDeSante.objects.create(
            user=self.u_unverified,
            name="Cabinet En Attente",
            slug="cabinet-en-attente",
            type_organisme=self.type_clinique,
            is_active=True,
            is_verified=False,
            city="Dakar",
        )
        self.pa_unverified = PrestataireActe.objects.create(
            organisme=self.org_unverified,
            acte=self.acte,
            price=Decimal("15000.00"),
            is_available=True,
        )

        # Verified structure
        self.u_verified = User.objects.create_user("verified_doc", "verified@test.sn", "pass123")
        self.org_verified = OrganismeDeSante.objects.create(
            user=self.u_verified,
            name="Clinique Approuvee",
            slug="clinique-approuvee",
            type_organisme=self.type_clinique,
            is_active=True,
            is_verified=True,
            city="Dakar",
        )
        self.pa_verified = PrestataireActe.objects.create(
            organisme=self.org_verified,
            acte=self.acte,
            price=Decimal("20000.00"),
            is_available=True,
        )

        # Patient user
        self.patient = User.objects.create_user("patient_test", "patient@test.sn", "pass123", user_type="patient")

    def test_search_shows_both_verified_and_unverified(self):
        """Unverified structure must not be hidden in search, it should be listed with unverified indicators."""
        response = self.client.get(reverse("healthcare:search"), {"acte": self.acte.pk}, HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 200)
        page = response.context.get("page")
        items = list(page.object_list) if page else []
        self.assertIn(self.pa_unverified, items)
        self.assertIn(self.pa_verified, items)

        # Check that unverified badge and class are rendered
        content = response.content.decode("utf-8")
        self.assertIn("En attente d'approbation", content)
        self.assertIn("scard--unverified", content)

    def test_admin_approval_action(self):
        """Admin action must approve selected unverified structures."""
        from django.contrib.admin.sites import AdminSite
        from healthcare.admin import OrganismeDeSanteAdmin

        admin_site = AdminSite()
        org_admin = OrganismeDeSanteAdmin(OrganismeDeSante, admin_site)

        self.assertFalse(self.org_unverified.is_verified)
        qs = OrganismeDeSante.objects.filter(pk=self.org_unverified.pk)
        
        # Mock request with messages support
        from django.test.client import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        req = RequestFactory().get("/")
        setattr(req, "session", "session")
        messages = FallbackStorage(req)
        setattr(req, "_messages", messages)

        org_admin.approuver_organismes(req, qs)
        self.org_unverified.refresh_from_db()
        self.assertTrue(self.org_unverified.is_verified)

    def test_cart_add_blocked_for_unverified_structure(self):
        """Cart add must be rejected with 400 for JSON and redirect for standard."""
        # JSON request
        resp_json = self.client.get(
            reverse("cart:cart_add", args=[self.pa_unverified.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_HOST="localhost",
        )
        self.assertEqual(resp_json.status_code, 400)
        self.assertIn("en cours de validation", resp_json.json().get("error", ""))

        # Standard GET
        resp_html = self.client.get(
            reverse("cart:cart_add", args=[self.pa_unverified.pk]),
            HTTP_HOST="localhost",
        )
        self.assertEqual(resp_html.status_code, 302)
        # Verify cart item was NOT created
        self.assertFalse(CartItem.objects.filter(prestataire_acte=self.pa_unverified).exists())

    def test_patient_book_blocked_for_unverified_structure(self):
        """Patient booking must be rejected if the organisme is not verified."""
        self.client.login(username="patient_test", password="pass123")
        cart = Cart.objects.create(patient=self.patient)
        devis = Devis.objects.create(
            patient=self.patient,
            cart=cart,
            reference="DEV-UNV-01",
            total_brut=Decimal("15000.00"),
            total_assurance=Decimal("0.00"),
            total_patient=Decimal("15000.00"),
            details=[],
            status="sent",
        )
        part = DevisPart.objects.create(
            devis=devis,
            organisme=self.org_unverified,
            reference="PART-UNVERIFIED-01",
            total_brut=Decimal("15000.00"),
            total_patient=Decimal("15000.00"),
            total_assurance=Decimal("0.00"),
            details=[],
            status="validated",
        )
        resp = self.client.post(
            reverse("appointments:patient_book", args=[part.reference]),
            {"slot": "asap", "note": "Urgent"},
            HTTP_HOST="localhost",
        )
        # Should redirect with error, not book
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(part.rendez_vous.exists())
