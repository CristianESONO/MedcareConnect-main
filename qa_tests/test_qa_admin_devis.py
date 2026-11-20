"""Les devis WhatsApp ne sont pas accessibles depuis l'admin."""

from decimal import Decimal

import pytest
from django.urls import reverse

from cart.models import Cart, Devis, DevisPart
from messaging.models import Conversation, Message


@pytest.fixture
def devis_admin(db, patient_user, organisme_actif):
    cart = Cart.objects.create(patient=patient_user, status="converted")
    devis = Devis.objects.create(
        patient=patient_user,
        cart=cart,
        total_brut=Decimal("10000"),
        total_assurance=Decimal("0"),
        total_patient=Decimal("10000"),
        details=[],
        status="sent",
    )
    DevisPart.objects.create(
        devis=devis,
        organisme=organisme_actif,
        details=[{"acte": "QA", "quantity": 1}],
        total_brut=Decimal("10000"),
        total_assurance=Decimal("0"),
        total_patient=Decimal("10000"),
        status="sent",
    )
    return devis


@pytest.mark.django_db
def test_admin_cannot_access_or_change_devis(client, superuser, devis_admin):
    client.force_login(superuser)
    assert client.get(reverse("dashboard:devis_overview")).status_code == 404
    assert client.get(
        reverse("dashboard:devis_admin_detail", args=[devis_admin.reference])
    ).status_code == 404
    assert client.post(
        reverse("dashboard:devis_admin_relance", args=[devis_admin.reference])
    ).status_code == 404
    assert client.post(
        reverse("dashboard:devis_admin_archive", args=[devis_admin.reference])
    ).status_code == 404

    part = devis_admin.parts.first()
    part.refresh_from_db()
    devis_admin.refresh_from_db()
    assert part.relance_count == 0
    assert not part.is_archived
    assert not devis_admin.is_archived


@pytest.mark.django_db
def test_django_admin_hides_devis_models(client, superuser):
    superuser.is_staff = True
    superuser.save(update_fields=["is_staff"])
    client.force_login(superuser)
    assert client.get(reverse("admin:cart_devis_changelist")).status_code == 403
    assert client.get(reverse("admin:cart_devispart_changelist")).status_code == 403


@pytest.mark.django_db
def test_admin_cannot_read_devis_conversation(
    client, superuser, patient_user, organisme_actif, devis_admin
):
    part = devis_admin.parts.first()
    conversation = Conversation.objects.create(
        patient=patient_user,
        prestataire=organisme_actif.user,
        kind=Conversation.KIND_DEVIS,
        devis_part=part,
    )
    Message.objects.create(
        conversation=conversation,
        sender=patient_user,
        receiver=organisme_actif.user,
        content="Contenu confidentiel du devis QA",
    )
    client.force_login(superuser)

    overview = client.get(reverse("dashboard:messaging_overview"))
    assert overview.status_code == 200
    assert b"Contenu confidentiel du devis QA" not in overview.content
    assert devis_admin.reference.encode() not in overview.content
    assert client.get(
        reverse("dashboard:messaging_admin_detail", args=[conversation.pk])
    ).status_code == 404
