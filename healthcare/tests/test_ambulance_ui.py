from django.test import SimpleTestCase

from healthcare.ambulance_ui import (
    ambulance_acte_flow,
    ambulance_configure_label,
    ambulance_sur_devis,
    is_ambulance_acte_name,
)


class AmbulanceUiTests(SimpleTestCase):
    def test_is_ambulance_acte_name(self):
        self.assertTrue(is_ambulance_acte_name("Ambulance simple"))
        self.assertTrue(is_ambulance_acte_name("Rapatriement international"))
        self.assertFalse(is_ambulance_acte_name("IRM"))

    def test_flow_and_labels(self):
        self.assertEqual(ambulance_acte_flow("Ambulance simple"), "trajet")
        self.assertEqual(ambulance_acte_flow("Rapatriement national"), "rapatriement")
        self.assertEqual(ambulance_acte_flow("Couverture médicale sportive"), "evenement")
        self.assertEqual(ambulance_configure_label("Ambulance simple"), "🚑 Configurer mon trajet")
        self.assertEqual(ambulance_configure_label("Rapatriement national"), "🌍 Organiser le rapatriement")
        self.assertEqual(ambulance_configure_label("Couverture médicale sportive"), "🩺 Configurer ma couverture")

    def test_sur_devis(self):
        self.assertTrue(ambulance_sur_devis("Rapatriement international", 500000))
        self.assertTrue(ambulance_sur_devis("Ambulance simple", 0))
        self.assertFalse(ambulance_sur_devis("Ambulance simple", 10000))
