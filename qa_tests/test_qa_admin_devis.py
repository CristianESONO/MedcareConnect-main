"""Admin — détail devis, relance, archivage."""

from decimal import Decimal

import pytest
from django.urls import reverse

from cart.models import Cart, Devis, DevisPart


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
def test_admin_devis_detail_200(client, superuser, devis_admin):
    client.force_login(superuser)
    r = client.get(reverse("dashboard:devis_admin_detail", args=[devis_admin.reference]))
    assert r.status_code == 200
    assert devis_admin.reference.encode() in r.content


@pytest.mark.django_db
def test_admin_relance_devis(client, superuser, devis_admin):
    client.force_login(superuser)
    url = reverse("dashboard:devis_admin_relance", args=[devis_admin.reference])
    r = client.post(url, follow=False)
    assert r.status_code == 302
    part = devis_admin.parts.first()
    part.refresh_from_db()
    assert part.relance_count >= 1


@pytest.mark.django_db
def test_admin_archive_devis(client, superuser, devis_admin):
    client.force_login(superuser)
    url = reverse("dashboard:devis_admin_archive", args=[devis_admin.reference])
    r = client.post(url, follow=False)
    assert r.status_code == 302
    devis_admin.refresh_from_db()
    assert devis_admin.is_archived
