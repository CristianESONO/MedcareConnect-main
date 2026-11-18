"""Types de structure et piliers — alignement DEMO_STRUCTURES.html."""

from types import SimpleNamespace
from unittest.mock import Mock

from django.test import TestCase

from healthcare.data.catalog_loader import load_pillars_from_docs
from healthcare.data.structure_types_demo import (
    DEMO_STRUCTURE_TYPES,
    pilier_slugs_for_demo_key,
)
from healthcare.models import TypeOrganisme
from healthcare.prestataire_catalogue import applicable_pilier_slugs, merge_catalog_blocks


def _org_with_type(type_row: TypeOrganisme, selected_pilier_slugs=()):
    piliers_actifs = Mock()
    piliers_actifs.exists.return_value = bool(selected_pilier_slugs)
    piliers_actifs.values_list.return_value = list(selected_pilier_slugs)
    return SimpleNamespace(
        type_organisme_id=type_row.pk,
        type_organisme=type_row,
        piliers_actifs=piliers_actifs,
    )


class StructureTypesDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_pillars_from_docs()
        cls.type_labo = TypeOrganisme.objects.create(name="Laboratoire", order=70)
        cls.type_hopital = TypeOrganisme.objects.create(name="Hôpital", order=120)
        cls.type_cabinet = TypeOrganisme.objects.create(name="Cabinet médical", order=20)

    def test_demo_has_eight_structure_types(self):
        self.assertEqual(len(DEMO_STRUCTURE_TYPES), 8)

    def test_labo_only_biologie(self):
        slugs = pilier_slugs_for_demo_key("labo")
        self.assertEqual(slugs, {"biologie-medicale"})

    def test_hopital_all_six_piliers(self):
        slugs = pilier_slugs_for_demo_key("hopital")
        self.assertEqual(len(slugs), 6)

    def test_clinique_without_ambulance_nor_dentaire(self):
        slugs = pilier_slugs_for_demo_key("clinique")
        self.assertIn("biologie-medicale", slugs)
        self.assertNotIn("ambulance-medicalisee", slugs)
        self.assertNotIn("soins-dentaires", slugs)

    def test_applicable_pilier_slugs_for_org_labo(self):
        org = _org_with_type(self.type_labo, {"biologie-medicale"})
        self.assertEqual(applicable_pilier_slugs(org), {"biologie-medicale"})

    def test_merge_catalog_marks_non_applicable_piliers(self):
        org = _org_with_type(self.type_labo, {"biologie-medicale"})
        blocks = merge_catalog_blocks([], org)
        self.assertEqual(len(blocks), 6)
        bio = next(b for b in blocks if b["pilier"].slug == "biologie-medicale")
        img = next(b for b in blocks if b["pilier"].slug == "imagerie-medicale")
        self.assertTrue(bio["applicable"])
        self.assertFalse(img["applicable"])

    def test_merge_catalog_official_pilier_order(self):
        org = _org_with_type(
            self.type_hopital,
            {
                "biologie-medicale",
                "imagerie-medicale",
                "explorations-fonctionnelles",
                "ambulance-medicalisee",
                "soins-specialises",
                "soins-dentaires",
            },
        )
        blocks = merge_catalog_blocks([], org)
        slugs = [b["pilier"].slug for b in blocks]
        self.assertEqual(
            slugs,
            [
                "biologie-medicale",
                "imagerie-medicale",
                "explorations-fonctionnelles",
                "ambulance-medicalisee",
                "soins-specialises",
                "soins-dentaires",
            ],
        )
