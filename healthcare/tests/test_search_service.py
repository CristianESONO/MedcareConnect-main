"""Tests unitaires pour SearchService."""

from decimal import Decimal
from django.test import TestCase

from users.models import User
from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    TypeOrganisme,
)
from healthcare.services import SearchService


class SearchServiceTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="u1", email="u1@test.com", password="pwd")
        self.user2 = User.objects.create_user(username="u2", email="u2@test.com", password="pwd")
        self.user3 = User.objects.create_user(username="u3", email="u3@test.com", password="pwd")

        self.type_hopital = TypeOrganisme.objects.create(name="Hôpital", slug="hopital")
        self.type_ambulance = TypeOrganisme.objects.create(name="Service Ambulancier", slug="ambulance")

        self.service_lab = ServiceMedical.objects.create(name="Laboratoire", slug="laboratoire")
        self.service_imagerie = ServiceMedical.objects.create(name="Imagerie", slug="imagerie")

        self.acte_nfs = ActeMedical.objects.create(
            name="Numération Formule Sanguine (NFS)",
            service_medical_category=self.service_lab,
            code="NFS01",
            level=3,
        )
        self.acte_echo = ActeMedical.objects.create(
            name="Échographie Abdominale",
            service_medical_category=self.service_imagerie,
            code="ECHO01",
            level=3,
        )

        self.org1 = OrganismeDeSante.objects.create(
            user=self.user1,
            name="Clinique Dakar Plateau",
            city="Dakar",
            quartier="Plateau",
            latitude=14.6738,
            longitude=-17.4375,
            type_organisme=self.type_hopital,
            is_active=True,
        )

        self.org2 = OrganismeDeSante.objects.create(
            user=self.user2,
            name="Cabinet Almadies",
            city="Dakar",
            quartier="Almadies",
            latitude=14.7450,
            longitude=-17.5180,
            type_organisme=self.type_hopital,
            is_active=True,
        )

        self.org_amb = OrganismeDeSante.objects.create(
            user=self.user3,
            name="Ambulance Samu Express",
            city="Dakar",
            quartier="Grand Dakar",
            type_organisme=self.type_ambulance,
            is_active=True,
        )

        # Offres de prestations
        self.pa1 = PrestataireActe.objects.create(
            organisme=self.org1,
            acte=self.acte_nfs,
            price=Decimal("15000.00"),
            price_ipm=Decimal("12000.00"),
            price_assurance=Decimal("13000.00"),
            delai="24h",
            is_available=True,
        )
        self.pa2 = PrestataireActe.objects.create(
            organisme=self.org2,
            acte=self.acte_nfs,
            price=Decimal("10000.00"),
            price_ipm=Decimal("9000.00"),
            price_assurance=Decimal("9500.00"),
            delai="48h",
            is_available=True,
        )
        self.pa3 = PrestataireActe.objects.create(
            organisme=self.org1,
            acte=self.acte_echo,
            price=Decimal("35000.00"),
            delai="2h",
            is_available=True,
        )

    def test_is_all_zones_ambulance(self):
        self.assertTrue(SearchService.is_all_zones_ambulance(self.org_amb))
        self.assertFalse(SearchService.is_all_zones_ambulance(self.org1))
        self.assertFalse(SearchService.is_all_zones_ambulance(None))

    def test_parse_int_list(self):
        raw = ["10", "20", "invalid", 10, "30", None, ""]
        clean = SearchService.parse_int_list(raw)
        self.assertEqual(clean, [10, 20, 30])

    def test_annotate_delai_sort(self):
        qs = PrestataireActe.objects.filter(pk__in=[self.pa1.pk, self.pa2.pk, self.pa3.pk])
        annotated = SearchService.annotate_delai_sort(qs)
        pa3_annotated = annotated.get(pk=self.pa3.pk)
        pa1_annotated = annotated.get(pk=self.pa1.pk)
        # 2h a un rang inférieur (plus rapide) que 24h
        self.assertLess(pa3_annotated._delai_sort, pa1_annotated._delai_sort)

    def test_attach_distance_km_to_offers(self):
        latlng = (14.6700, -17.4350)
        offers = [self.pa1, self.pa2]
        SearchService.attach_distance_km_to_offers(offers, latlng)
        self.assertIsNotNone(self.pa1.distance_km)
        self.assertIsNotNone(self.pa2.distance_km)
        # Plateau est plus proche du point test que Almadies
        self.assertLess(self.pa1.distance_km, self.pa2.distance_km)

    def test_build_search_text_filter(self):
        q_filter, equiv = SearchService.build_search_text_filter("NFS")
        self.assertIsNotNone(q_filter)
        qs = PrestataireActe.objects.filter(q_filter)
        self.assertIn(self.pa1, qs)
        self.assertIn(self.pa2, qs)
        self.assertNotIn(self.pa3, qs)

    def test_apply_level_price_location_filters(self):
        qs = PrestataireActe.objects.all()
        # Filtre sur prix max 12000
        filtered = SearchService.apply_level_price_location_filters(
            qs,
            price_max=Decimal("12000.00"),
            regime_filter="comptant",
        )
        self.assertIn(self.pa2, filtered)
        self.assertNotIn(self.pa1, filtered)
        self.assertNotIn(self.pa3, filtered)

        # Filtre sur délai <= 24h
        filtered_delai = SearchService.apply_level_price_location_filters(
            qs,
            delai_filter="24h",
        )
        self.assertIn(self.pa1, filtered_delai)
        self.assertIn(self.pa3, filtered_delai)  # 2h <= 24h
        self.assertNotIn(self.pa2, filtered_delai)  # 48h > 24h

    def test_filter_and_sort_offers(self):
        qs = SearchService.annotate_delai_sort(
            PrestataireActe.objects.filter(pk__in=[self.pa1.pk, self.pa2.pk])
        )
        # Tri prix croissant
        results, count = SearchService.filter_and_sort_offers(qs, sort="price_asc")
        self.assertEqual(count, 2)
        self.assertEqual(list(results), [self.pa2, self.pa1])

        # Tri prix décroissant
        results_desc, _ = SearchService.filter_and_sort_offers(qs, sort="price_desc")
        self.assertEqual(list(results_desc), [self.pa1, self.pa2])

    def test_extract_zones(self):
        self.assertEqual(SearchService.extract_zone_from_org(self.org1), "Plateau")
        self.assertEqual(SearchService.extract_zone_from_org(self.org2), "Almadies")

        zones = SearchService.extract_top_zones(
            scope_qs=PrestataireActe.objects.filter(pk__in=[self.pa1.pk, self.pa2.pk]),
            pool_from_request=True,
        )
        self.assertIn("Almadies", zones)
        self.assertIn("Plateau", zones)
