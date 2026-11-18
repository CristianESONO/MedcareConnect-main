"""Tests pour vérifier que seuls les actes spécifiques (level=3) sont sélectionnables pour les panels."""

import json
from django.test import TestCase
from django.urls import reverse

from users.models import User
from healthcare.models import ActeMedical, ExamenPanel, OrganismeDeSante, ServiceMedical


class PanelActsLevelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="org_panel_level_test",
            email="org_panel@medcare.test",
            password="testpass123",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.user,
            name="Clinique Panel Level Test",
            city="Dakar",
            is_active=True,
        )
        self.service = ServiceMedical.objects.create(name="Biologie médicale", order=1)

        # Niveau 2 : Sous-service intermédiaire
        self.sous_service = ActeMedical.objects.create(
            name="Hématologie",
            service_medical_category=self.service,
            level=2,
            is_active=True,
        )

        # Niveau 3 : Vrai acte médical
        self.acte_vrai = ActeMedical.objects.create(
            name="NFS / Hémogramme",
            service_medical_category=self.service,
            parent_service=self.sous_service,
            level=3,
            is_active=True,
        )

    def test_prestataire_panels_excludes_level_2(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("healthcare:prestataire_panels"))
        self.assertEqual(response.status_code, 200)

        actes_data = json.loads(response.context["actes_json"])
        actes_noms = [a["nom"] for a in actes_data]

        # Le vrai acte (level 3) doit être présent
        self.assertIn("NFS / Hémogramme", actes_noms)
        # Le sous-service intermédiaire (level 2) NE doit PAS être présent dans les choix sélectionnables
        self.assertNotIn("Hématologie", actes_noms)

    def test_panel_create_rejects_level_2_resolution(self):
        self.client.force_login(self.user)
        # Tenter d'injecter l'ID du sous-service (level 2)
        response = self.client.post(
            reverse("healthcare:panel_create"),
            {
                "nom": "Bilan Test",
                "kind": "panel",
                "acte_ids": f"am_{self.sous_service.pk}",
                "acte_noms": "Hématologie",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        panel = ExamenPanel.objects.get(nom="Bilan Test")
        # Le sous-service ne doit pas avoir été attaché comme acte
        self.assertEqual(panel.actes.count(), 0)
