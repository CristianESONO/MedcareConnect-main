"""Tests rappels H-N depuis le panneau préparation catalogue."""
from decimal import Decimal

import pytest
from django.urls import reverse

from appointments.models import RdvReminderSchedule
from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from healthcare.prestataire_prep_reminders import (
    add_hourly_reminder,
    delete_acte_reminder,
    reminders_for_acte,
)


@pytest.mark.django_db
def test_add_and_list_hourly_reminder(client, django_user_model):
    plan = SubscriptionPlan.objects.create(name="Prep", slug="prep-rem-tu")
    user = django_user_model.objects.create_user(
        username="prep_rem", password="test", email="prep@example.com", user_type="prestataire"
    )
    org = OrganismeDeSante.objects.create(
        user=user, name="Labo Test", slug="labo-test", subscription_plan=plan, is_active=True
    )
    svc = ServiceMedical.objects.create(name="Bio TU")
    acte = ActeMedical.objects.create(
        name="Bilan lipidique",
        service_medical_category=svc,
        level=3,
        is_active=True,
        reference_price=Decimal("5000"),
    )
    PrestataireActe.objects.create(
        organisme=org, acte=acte, price=Decimal("5000"), is_available=True
    )
    client.force_login(user)

    url = reverse("healthcare:prestataire_acte_reminder_add", args=[acte.pk])
    res = client.post(url, {"hours": 12}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert len(data["reminders"]) == 1
    assert data["reminders"][0]["display"] == "H-12"

    schedule, err = add_hourly_reminder(org, acte, 12)
    assert err is None
    assert schedule is not None
    assert RdvReminderSchedule.objects.filter(organisme=org, actes=acte).count() == 1

    listed = reminders_for_acte(org, acte.pk)
    assert listed[0]["hours"] == 12

    pk = listed[0]["pk"]
    del_url = reverse("healthcare:prestataire_acte_reminder_delete", args=[acte.pk, pk])
    res2 = client.post(del_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert res2.status_code == 200
    assert res2.json()["reminders"] == []
    assert delete_acte_reminder(org, acte.pk, pk) is False
