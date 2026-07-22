"""Génération devis : un devis par acte (ligne panier), pas de regroupement."""

from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem, Devis, DevisPart
from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from notifications.models import NotificationEvent, NotificationLog
from users.models import User


class DevisPerActeTest(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Plan multipart",
            slug="plan-multipart-tu",
        )
        self.patient = User.objects.create_user(
            username="pat_multipart",
            email="pm@example.com",
            password="x",
            user_type="patient",
        )
        self.prest_a = User.objects.create_user(
            username="presta_a_tu",
            email="pa@example.com",
            password="x",
            user_type="prestataire",
        )
        self.prest_b = User.objects.create_user(
            username="presta_b_tu",
            email="pb@example.com",
            password="x",
            user_type="prestataire",
        )
        self.org_a = OrganismeDeSante.objects.create(
            user=self.prest_a,
            name="Labo A Multipart",
            address="Dakar",
            subscription_plan=self.plan,
            is_active=True,
        )
        self.org_b = OrganismeDeSante.objects.create(
            user=self.prest_b,
            name="Radio B Multipart",
            address="Thiès",
            subscription_plan=self.plan,
            is_active=True,
        )
        svc = ServiceMedical.objects.create(name="Svc multipart")
        self.acte1 = ActeMedical.objects.create(
            name="Acte 1 multipart",
            service_medical_category=svc,
            level=2,
        )
        self.acte2 = ActeMedical.objects.create(
            name="Acte 2 multipart",
            service_medical_category=svc,
            level=2,
        )
        self.pa_a = PrestataireActe.objects.create(
            organisme=self.org_a,
            acte=self.acte1,
            price=4000,
        )
        self.pa_b = PrestataireActe.objects.create(
            organisme=self.org_b,
            acte=self.acte2,
            price=12000,
        )
        self.cart = Cart.objects.create(patient=self.patient, status="active")
        self.item_a = CartItem.objects.create(
            cart=self.cart, prestataire_acte=self.pa_a, quantity=1
        )
        self.item_b = CartItem.objects.create(
            cart=self.cart, prestataire_acte=self.pa_b, quantity=2
        )

    def test_generate_sans_item_redirige_chariot(self):
        self.client.force_login(self.patient)
        r = self.client.get(reverse("cart:generate_devis"), follow=False)
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("validate=1", r["Location"])
        self.assertEqual(Devis.objects.filter(patient=self.patient).count(), 0)

    def test_generate_devis_cree_un_devis_par_acte(self):
        ev = NotificationEvent.objects.get(code="devis.created")
        n0 = NotificationLog.objects.filter(event=ev).count()
        self.client.force_login(self.patient)

        r = self.client.get(
            reverse("cart:generate_devis") + f"?item={self.item_a.pk}",
            follow=False,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Devis.objects.filter(patient=self.patient).count(), 1)
        devis_a = Devis.objects.get(patient=self.patient)
        self.assertEqual(devis_a.parts.count(), 1)
        self.assertEqual(devis_a.parts.get().organisme_id, self.org_a.pk)
        self.assertEqual(len(devis_a.details), 1)
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, "active")
        self.assertEqual(self.cart.items.count(), 1)
        n1 = NotificationLog.objects.filter(event=ev).count()
        self.assertEqual(n1, n0 + 1)

        r2 = self.client.get(
            reverse("cart:generate_devis") + f"?item={self.item_b.pk}",
            follow=False,
        )
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(Devis.objects.filter(patient=self.patient).count(), 2)
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, "converted")
        self.assertEqual(self.cart.items.count(), 0)
        n2 = NotificationLog.objects.filter(event=ev).count()
        self.assertEqual(n2, n0 + 2)

    def test_redirect_un_acte_vers_fil_messagerie(self):
        self.client.force_login(self.patient)
        r = self.client.get(
            reverse("cart:generate_devis") + f"?item={self.item_a.pk}",
            follow=False,
        )
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("validate=1", r["Location"])
        self.assertIn("/messaging/", r["Location"])
        devis = Devis.objects.get(patient=self.patient)
        self.assertEqual(devis.parts.count(), 1)

    def test_generate_devis_par_structure_regroupe_plusieurs_actes(self):
        acte3 = ActeMedical.objects.create(
            name="Acte 3 même structure",
            service_medical_category=self.acte1.service_medical_category,
            level=2,
        )
        pa_a2 = PrestataireActe.objects.create(
            organisme=self.org_a,
            acte=acte3,
            price=9000,
        )
        item_a2 = CartItem.objects.create(
            cart=self.cart,
            prestataire_acte=pa_a2,
            quantity=1,
        )
        self.client.force_login(self.patient)

        r = self.client.get(
            reverse("cart:generate_devis") + f"?org={self.org_a.pk}",
            follow=False,
        )

        self.assertEqual(r.status_code, 302)
        self.assertEqual(Devis.objects.filter(patient=self.patient).count(), 1)
        devis = Devis.objects.get(patient=self.patient)
        self.assertEqual(devis.parts.count(), 1)
        part = devis.parts.get()
        self.assertEqual(part.organisme_id, self.org_a.pk)
        self.assertEqual(len(part.details), 2)
        self.assertCountEqual(
            [line["acte"] for line in part.details],
            [self.item_a.prestataire_acte.acte.name, item_a2.prestataire_acte.acte.name],
        )
        self.assertFalse(CartItem.objects.filter(pk=self.item_a.pk).exists())
        self.assertFalse(CartItem.objects.filter(pk=item_a2.pk).exists())
        self.assertTrue(CartItem.objects.filter(pk=self.item_b.pk).exists())
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, "active")
