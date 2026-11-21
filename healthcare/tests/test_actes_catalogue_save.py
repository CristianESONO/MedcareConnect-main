from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, ServiceMedical
from users.models import User


class ActesCatalogueSaveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="catalogue_save_test",
            email="catalogue_save_test@example.com",
            password="secret123",
            user_type="prestataire",
        )
        self.org = OrganismeDeSante.objects.create(
            user=self.user,
            name="Cabinet Catalogue Test",
            city="Dakar",
            is_active=True,
        )
        self.service = ServiceMedical.objects.create(name="Service Catalogue Test")
        self.parent_acte = ActeMedical.objects.create(
            name="Examen parent",
            service_medical_category=self.service,
            level=2,
        )
        self.leaf_acte = ActeMedical.objects.create(
            name="Examen élémentaire",
            service_medical_category=self.service,
            parent_service=self.parent_acte,
            level=3,
        )
        self.client.login(username="catalogue_save_test", password="secret123")

    def post_catalogue(self, **fields):
        data = {
            "action": "save_catalogue",
            "catalogue_tarifs_delais": "Nouveau texte",
        }
        data.update(fields)
        return self.client.post(
            reverse("healthcare:actes_list"),
            data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_save_disables_legacy_non_leaf_actes_and_persists_valid_selection(self):
        legacy = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.leaf_acte,
            price=Decimal("10000"),
        )
        PrestataireActe.objects.filter(pk=legacy.pk).update(
            acte_id=self.parent_acte.pk
        )

        with self.assertLogs("healthcare.views", level="WARNING") as captured:
            response = self.post_catalogue(
                acte_ids=str(self.leaf_acte.pk),
                **{f"price_{self.leaf_acte.pk}": "7500"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["warning"])
        self.assertIn("non sélectionnables", payload["message"])
        self.assertIn("Skipped non-selectable legacy catalogue acts", captured.output[0])

        saved = PrestataireActe.objects.get(
            organisme=self.org,
            acte=self.leaf_acte,
        )
        self.assertEqual(saved.price, Decimal("7500"))
        self.assertTrue(saved.is_available)
        legacy.refresh_from_db()
        self.assertEqual(legacy.acte_id, self.parent_acte.pk)
        self.assertFalse(legacy.is_available)
        self.org.refresh_from_db()
        self.assertEqual(self.org.catalogue_tarifs_delais, "Nouveau texte")

    def test_validation_failure_is_logged_and_returns_json_without_partial_save(self):
        existing = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.leaf_acte,
            price=Decimal("10000"),
        )
        self.org.catalogue_tarifs_delais = "Texte précédent"
        self.org.save(update_fields=["catalogue_tarifs_delais"])

        with self.assertLogs("healthcare.views", level="ERROR") as captured:
            response = self.post_catalogue(
                acte_ids=str(self.leaf_acte.pk),
                **{f"price_{self.leaf_acte.pk}": ""},
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("tarifs", payload["message"])
        self.assertIn("Validation error while saving practitioner catalogue", captured.output[0])

        existing.refresh_from_db()
        self.org.refresh_from_db()
        self.assertEqual(existing.price, Decimal("10000"))
        self.assertEqual(self.org.catalogue_tarifs_delais, "Texte précédent")

    def test_selected_acte_with_positive_price_is_saved(self):
        response = self.post_catalogue(
            acte_ids=str(self.leaf_acte.pk),
            **{f"price_{self.leaf_acte.pk}": "12500"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])

        saved = PrestataireActe.objects.get(
            organisme=self.org,
            acte=self.leaf_acte,
        )
        self.assertEqual(saved.price, Decimal("12500"))
        self.assertTrue(saved.is_available)

    def test_acte_prerequisites_save_ajax(self):
        response = self.client.post(
            reverse(
                "healthcare:prestataire_acte_prerequisites",
                args=[self.leaf_acte.pk],
            ),
            {
                "rdv_prerequisites": "À jeun pendant 12 heures.",
                "rdv_prerequisites_active": "1",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["configured"])

        saved = PrestataireActe.objects.get(
            organisme=self.org,
            acte=self.leaf_acte,
        )
        self.assertEqual(saved.rdv_prerequisites, "À jeun pendant 12 heures.")
        self.assertTrue(saved.rdv_prerequisites_active)

    def test_acte_prerequisites_save_with_zero_price_inactive(self):
        existing = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.leaf_acte,
            price=Decimal("500"),
            is_available=False,
        )
        PrestataireActe.objects.filter(pk=existing.pk).update(price=Decimal("0"))

        response = self.client.post(
            reverse(
                "healthcare:prestataire_acte_prerequisites",
                args=[self.leaf_acte.pk],
            ),
            {
                "rdv_prerequisites": "Apporter l'ordonnance.",
                "rdv_prerequisites_active": "1",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        existing.refresh_from_db()
        self.assertEqual(existing.rdv_prerequisites, "Apporter l'ordonnance.")
        self.assertTrue(existing.rdv_prerequisites_active)

    def test_existing_zero_price_act_can_be_priced_and_activated(self):
        existing = PrestataireActe.objects.create(
            organisme=self.org,
            acte=self.leaf_acte,
            price=Decimal("500"),
            is_available=False,
        )
        PrestataireActe.objects.filter(pk=existing.pk).update(price=Decimal("0"))

        response = self.post_catalogue(
            acte_ids=str(self.leaf_acte.pk),
            **{f"price_{self.leaf_acte.pk}": "8500"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        existing.refresh_from_db()
        self.assertEqual(existing.price, Decimal("8500"))
        self.assertTrue(existing.is_available)
