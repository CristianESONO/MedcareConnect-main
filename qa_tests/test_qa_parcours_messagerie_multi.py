"""
Parcours panier multi-structures → un devis par acte, messagerie fil direct.
"""

import pytest
from django.urls import reverse

from cart.models import Cart, CartItem, Devis, DevisPart


@pytest.fixture
def cart_deux_structures(db, patient_user, subscription_plan):
    from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, ServiceMedical
    from users.models import User

    prest_a = User.objects.create_user(
        username="qa_prest_a",
        email="pa@qa.test",
        password="test-pass-qa-123",
        user_type="prestataire",
    )
    prest_b = User.objects.create_user(
        username="qa_prest_b",
        email="pb@qa.test",
        password="test-pass-qa-123",
        user_type="prestataire",
    )
    org_a = OrganismeDeSante.objects.create(
        user=prest_a,
        name="QA Labo Multi",
        address="Dakar",
        subscription_plan=subscription_plan,
        is_active=True,
        is_verified=True,
    )
    org_b = OrganismeDeSante.objects.create(
        user=prest_b,
        name="QA Radio Multi",
        address="Thiès",
        subscription_plan=subscription_plan,
        is_active=True,
        is_verified=True,
    )
    svc = ServiceMedical.objects.create(name="Svc QA multi")
    acte_a = ActeMedical.objects.create(name="Acte QA A", service_medical_category=svc, level=2)
    acte_b = ActeMedical.objects.create(name="Acte QA B", service_medical_category=svc, level=2)
    pa_a = PrestataireActe.objects.create(organisme=org_a, acte=acte_a, price=5000)
    pa_b = PrestataireActe.objects.create(organisme=org_b, acte=acte_b, price=8000)
    cart = Cart.objects.create(patient=patient_user, status="active")
    CartItem.objects.create(cart=cart, prestataire_acte=pa_a, quantity=1)
    CartItem.objects.create(cart=cart, prestataire_acte=pa_b, quantity=1)
    return cart


@pytest.mark.django_db
def test_reserver_un_acte_multi_structures_ne_groupe_pas(
    client, patient_user, cart_deux_structures,
):
    client.force_login(patient_user)
    item = CartItem.objects.filter(cart=cart_deux_structures).order_by("pk").first()
    r = client.get(reverse("cart:generate_devis") + f"?item={item.pk}", follow=False)
    assert r.status_code == 302
    assert "validate=1" not in (r.url or "")
    assert "/messaging/" in (r.url or "")

    assert Devis.objects.filter(patient=patient_user).count() == 1
    devis = Devis.objects.get(patient=patient_user)
    assert DevisPart.objects.filter(devis=devis).count() == 1
    assert len(devis.details) == 1
    cart_deux_structures.refresh_from_db()
    assert cart_deux_structures.status == "active"
    assert cart_deux_structures.items.count() == 1


@pytest.mark.django_db
def test_reserver_panier_une_structure_redirige_fil_direct(
    client, patient_user, cart_avec_ligne,
):
    from cart.models import CartItem

    client.force_login(patient_user)
    item = CartItem.objects.get(cart=cart_avec_ligne)
    r = client.get(reverse("cart:generate_devis") + f"?item={item.pk}", follow=False)
    assert r.status_code == 302
    assert "validate=1" not in (r.url or "")
    assert "/messaging/" in (r.url or "")
    assert "book=1" in (r.url or "")
