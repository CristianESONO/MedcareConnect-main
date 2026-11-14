from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, ServiceMedical, TypeOrganisme
from users.models import User


class ProximitySearchTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.type_clinique = TypeOrganisme.objects.create(name="Clinique", slug="clinique")
        self.type_ambulance = TypeOrganisme.objects.create(
            name="Ambulance médicalisée — Transport & SMUR", slug="ambulance"
        )
        self.service = ServiceMedical.objects.create(name="Urgences", slug="urgences", is_active=True)
        self.acte = ActeMedical.objects.create(
            name="Consultation Urgence",
            service_medical_category=self.service,
            level=3,
            is_active=True,
        )

        # Structure 1: Proche (Dakar Plateau : 14.670, -17.430)
        u1 = User.objects.create_user("org1", "org1@test.sn", "pass")
        self.org_proche = OrganismeDeSante.objects.create(
            user=u1,
            name="Clinique Proche",
            slug="clinique-proche",
            type_organisme=self.type_clinique,
            latitude=Decimal("14.670000"),
            longitude=Decimal("-17.430000"),
            is_active=True,
            is_verified=True,
            city="Dakar",
        )
        self.pa_proche = PrestataireActe.objects.create(
            organisme=self.org_proche,
            acte=self.acte,
            price=Decimal("10000.00"),
            is_available=True,
        )

        # Structure 2: Eloignée (Thiès : 14.790, -16.920)
        u2 = User.objects.create_user("org2", "org2@test.sn", "pass")
        self.org_eloignee = OrganismeDeSante.objects.create(
            user=u2,
            name="Clinique Eloignee",
            slug="clinique-eloignee",
            type_organisme=self.type_clinique,
            latitude=Decimal("14.790000"),
            longitude=Decimal("-16.920000"),
            is_active=True,
            is_verified=True,
            city="Thiès",
        )
        self.pa_eloignee = PrestataireActe.objects.create(
            organisme=self.org_eloignee,
            acte=self.acte,
            price=Decimal("10000.00"),
            is_available=True,
        )

        # Structure 3: Sans coordonnées GPS (ex: AMBUCare ou structure sans coordonnées)
        u3 = User.objects.create_user("org3", "org3@test.sn", "pass")
        self.org_sans_gps = OrganismeDeSante.objects.create(
            user=u3,
            name="AMBUCare Dakar",
            slug="ambucare-dakar",
            type_organisme=self.type_ambulance,
            latitude=None,
            longitude=None,
            is_active=True,
            is_verified=True,
            city="Dakar",
        )
        self.pa_sans_gps = PrestataireActe.objects.create(
            organisme=self.org_sans_gps,
            acte=self.acte,
            price=Decimal("15000.00"),
            is_available=True,
        )

    def test_proximity_includes_structures_without_coords_at_end(self):
        """
        En recherche 'près de moi' (lat/lng + proximity=1),
        les structures sans coordonnées ne doivent plus être écartées mais placées en dernier
        avec distance inconnue.
        """
        url = reverse("healthcare:search")
        # Position utilisateur: Dakar (14.671, -17.431)
        resp = self.client.get(
            url,
            {
                "q": "Consultation Urgence",
                "lat": "14.671",
                "lng": "-17.431",
                "proximity": "1",
                "radius_km": "5",
                "sort": "price_asc",
            },
        )
        self.assertEqual(resp.status_code, 200)
        page = resp.context.get("page")
        items = list(page.object_list) if page else []

        # Les structures doivent inclure la proche et celle sans GPS
        self.assertIn(self.pa_proche, items)
        self.assertIn(self.pa_sans_gps, items)
        # La structure éloignée (Thiès) doit être STRICTEMENT EXCLUE du rayon de 5 km
        self.assertNotIn(self.pa_eloignee, items)
        # La proche doit arriver AVANT celle sans GPS
        idx_proche = items.index(self.pa_proche)
        idx_sans_gps = items.index(self.pa_sans_gps)
        self.assertLess(idx_proche, idx_sans_gps)
        
        item_proche = items[idx_proche]
        item_sans_gps = items[idx_sans_gps]
        self.assertIsNotNone(getattr(item_proche, "distance_km", None))
        self.assertIsNone(getattr(item_sans_gps, "distance_km", None))

    def test_proximity_filters_and_sorts_grouped_structures_blocks(self):
        """Dans mobile_results_by_org, les structures hors rayon sont exclues et triées par distance."""
        url = reverse("healthcare:search")
        resp = self.client.get(
            url,
            {
                "acte": str(self.acte.pk),
                "lat": "14.671",
                "lng": "-17.431",
                "proximity": "1",
                "radius_km": "5",
                "sort": "distance",
            },
        )
        self.assertEqual(resp.status_code, 200)
        blocks = resp.context.get("mobile_results_by_org") or []
        orgs = [b["org"] for b in blocks]
        self.assertIn(self.org_proche, orgs)
        self.assertNotIn(self.org_eloignee, orgs)
        # L'ambulance sans coordonnées est en dernier
        self.assertIn(self.org_sans_gps, orgs)
        self.assertEqual(orgs[0], self.org_proche)

