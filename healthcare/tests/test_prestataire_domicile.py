"""Prestations à domicile inline — sync zones."""

from types import SimpleNamespace

from django.test import TestCase

from healthcare.models import OrganismeDeSante, PrelevementZone, SubscriptionPlan, TypeOrganisme
from healthcare.prestataire_domicile import (
    domicile_all_actes_active,
    show_domicile_block,
    sync_domicile_zones,
)
from users.models import User


class DomicileInlineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="domi_tu",
            email="d@e.com",
            password="x",
            user_type="prestataire",
        )
        cls.type_labo = TypeOrganisme.objects.create(name="Laboratoire", order=70)
        cls.plan = SubscriptionPlan.objects.create(name="TU domi", slug="tu-domi", monthly_price_fcfa=0)

    def test_show_for_biologie_applicable(self):
        org = SimpleNamespace(prises_sang_domicile=False)
        self.assertTrue(show_domicile_block(org, {"biologie-medicale"}))

    def test_hide_for_imagerie_only(self):
        org = SimpleNamespace(prises_sang_domicile=False)
        self.assertFalse(show_domicile_block(org, {"imagerie-medicale"}))

    def test_sync_zones_create_update_delete(self):
        org = OrganismeDeSante.objects.create(
            user=self.user,
            name="Lab domi",
            slug="lab-domi",
            city="Dakar",
            address="Dakar",
            type_organisme=self.type_labo,
            subscription_plan=self.plan,
        )
        z1 = PrelevementZone.objects.create(organisme=org, label="Mermoz", forfait_fcfa=0, order=0)
        sync_domicile_zones(
            org,
            [
                {"pk": z1.pk, "label": "Mermoz", "forfait_fcfa": 2000},
                {"pk": None, "label": "Plateau", "forfait_fcfa": 1500},
            ],
        )
        self.assertEqual(PrelevementZone.objects.filter(organisme=org).count(), 2)
        z1.refresh_from_db()
        self.assertEqual(z1.forfait_fcfa, 2000)

    def test_domicile_all_actes_active(self):
        self.assertTrue(domicile_all_actes_active([1, 2, 3], {1, 2, 3}))
        self.assertFalse(domicile_all_actes_active([1, 2], {1}))
        self.assertFalse(domicile_all_actes_active([], {1}))
