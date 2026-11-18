"""Ordre catalogue actes — aligné référentiel démo, pas alphabétique."""

from django.test import TestCase

from healthcare.data.catalog_loader import load_pillars_from_docs
from healthcare.prestataire_catalogue import (
    _acte_sort_key,
    _type_sort_key,
    official_pilier_services,
    prestataire_leaf_actes_catalog_by_pilier,
    service_actes_catalog_rows,
    service_actes_catalog_subgroups,
)
from healthcare.models import ServiceMedical


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

    def test_service_page_subgroups_match_demo_order(self):
        svc = ServiceMedical.objects.get(name="Soins dentaires")
        rows = service_actes_catalog_rows(svc)
        names = [r["acte"].name for r in rows]
        self.assertGreaterEqual(len(names), 4)
        self.assertEqual(names[0], "Consultation dentaire standard")
        # 2e acte : libellé démo ou variante legacy
        self.assertIn(
            names[1],
            ("Consultation spécialisée", "Consultation dentaire spécialisée"),
        )
        self.assertEqual(rows[0]["category"], "Consultations dentaires")

    def test_official_pilier_services_count(self):
        load_pillars_from_docs()
        services = official_pilier_services()
        self.assertEqual(len(services), 6)

    def test_soins_specialises_page_order(self):
        svc = ServiceMedical.objects.get(name="Soins spécialisés")
        rows = service_actes_catalog_rows(svc)
        names = [r["display_name"] for r in rows]
        self.assertGreaterEqual(len(names), 5)
        self.assertEqual(names[0], "Suture plaie simple")
        self.assertEqual(names[1], "Suture plaie complexe")
        self.assertEqual(rows[0]["category"], "Médecine générale")
        if "ECG à domicile" in names:
            self.assertLess(names.index("Suture plaie simple"), names.index("ECG à domicile"))
        if "Surveillance fistule artério-veineuse" in names:
            self.assertEqual(names[-1], "Surveillance fistule artério-veineuse")

    def test_explorations_fonctionnelles_page_order(self):
        svc = ServiceMedical.objects.get(name="Explorations fonctionnelles")
        rows = service_actes_catalog_rows(svc)
        names = [r["display_name"] for r in rows]
        categories = [r["category"] for r in rows]
        self.assertGreaterEqual(len(names), 10)
        self.assertEqual(names[0], "ECG")
        self.assertEqual(names[1], "Épreuve d'effort")
        self.assertEqual(categories[0], "Cardiologie")
        self.assertNotIn("Cardiologie (explorations)", categories)
        if "EFR / Spirométrie" in names:
            self.assertLess(names.index("ECG"), names.index("EFR / Spirométrie"))
        if "Arthroscopie diagnostique" in names:
            self.assertEqual(names[-1], "Arthroscopie diagnostique")
            self.assertEqual(categories[-1], "Orthopédie")

    def test_imagerie_medicale_page_order(self):
        svc = ServiceMedical.objects.get(name="Imagerie médicale")
        rows = service_actes_catalog_rows(svc)
        names = [r["display_name"] for r in rows]
        categories = [r["category"] for r in rows]
        self.assertGreaterEqual(len(names), 10)
        self.assertEqual(names[0], "Radiographie thorax")
        self.assertEqual(categories[0], "Radiographie")
        if "Radiographie rachis lombaire" in names:
            idx_cerv = names.index("Radiographie rachis cervical")
            idx_dors = names.index("Radiographie rachis dorsal")
            idx_lomb = names.index("Radiographie rachis lombaire")
            self.assertLess(idx_cerv, idx_dors)
            self.assertLess(idx_dors, idx_lomb)
        if "Échodoppler veineux MI" in names:
            self.assertLess(
                names.index("Échographie musculo-squelettique"),
                names.index("Échodoppler veineux MI"),
            )
        if "Drainage kystique / abcès" in names:
            self.assertEqual(names[-1], "Drainage kystique / abcès")
            self.assertEqual(categories[-1], "Imagerie interventionnelle")
