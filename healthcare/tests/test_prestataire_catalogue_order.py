"""Ordre catalogue actes — aligné référentiel démo, pas alphabétique."""

from django.test import TestCase

from healthcare.data.catalog_loader import load_pillars_from_docs
from healthcare.prestataire_catalogue import (
    _acte_sort_key,
    _type_sort_key,
    prestataire_leaf_actes_catalog_by_pilier,
)


class CatalogueOrderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_pillars_from_docs()

    def test_hematologie_types_before_biochimie(self):
        hema = _type_sort_key("Biologie médicale", "Hématologie")
        bio = _type_sort_key("Biologie médicale", "Biochimie & Ionogramme")
        self.assertLess(hema[0], bio[0])

    def test_nfs_before_reticulocytes_not_alpha(self):
        nfs = _acte_sort_key("Biologie médicale", "Hématologie", "NFS / Hémogramme")
        ret = _acte_sort_key("Biologie médicale", "Hématologie", "Réticulocytes")
        self.assertLess(nfs[0], ret[0])

    def test_catalog_subgroups_follow_reference_order(self):
        blocks = prestataire_leaf_actes_catalog_by_pilier()
        bio = next(b for b in blocks if b["pilier"].name == "Biologie médicale")
        labels = [sg["label"] for sg in bio["subgroups"]]
        self.assertEqual(labels[0], "Hématologie")
        hema = bio["subgroups"][0]
        names = [a.name for a in hema["actes"]]
        self.assertEqual(names[0], "NFS / Hémogramme")
        self.assertIn("Réticulocytes", names[1:3])
