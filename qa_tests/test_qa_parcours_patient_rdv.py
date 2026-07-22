"""RDV patient — réservation, annulation, report de créneau."""

import pytest
from django.urls import reverse
from django.utils import timezone

from appointments.models import RendezVous
from appointments.slots import first_available_slot


@pytest.mark.django_db
def test_patient_reserve_creneau(client, patient_user, devis_part_patient):
    org = devis_part_patient.organisme
    slot = first_available_slot(org)
    assert slot, "aucun créneau disponible en test"

    client.force_login(patient_user)
    url = reverse("appointments:patient_book", args=[devis_part_patient.reference])
    r = client.post(url, {"slot": slot, "note": "Test QA"}, follow=False)
    assert r.status_code == 200
    rdv = RendezVous.objects.filter(devis_part=devis_part_patient).first()
    assert rdv is not None
    assert rdv.status == RendezVous.STATUS_REQUESTED


@pytest.mark.django_db
def test_patient_annule_rdv(client, patient_user, devis_part_patient):
    org = devis_part_patient.organisme
    slot = first_available_slot(org)
    start = timezone.datetime.fromisoformat(slot)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.get_current_timezone())
    rdv = RendezVous.objects.create(
        patient=patient_user,
        organisme=org,
        devis=devis_part_patient.devis,
        devis_part=devis_part_patient,
        start=start,
        status=RendezVous.STATUS_CONFIRMED,
        total_brut=devis_part_patient.total_brut,
        total_patient=devis_part_patient.total_patient,
    )

    client.force_login(patient_user)
    url = reverse("appointments:patient_cancel", args=[rdv.reference])
    r = client.post(url, {"reason": "Empêchement QA"}, follow=False)
    assert r.status_code == 200
    rdv.refresh_from_db()
    assert rdv.status == RendezVous.STATUS_CANCELLED


@pytest.mark.django_db
def test_patient_reporte_rdv_demande(client, patient_user, devis_part_patient):
    org = devis_part_patient.organisme
    slot1 = first_available_slot(org)
    start = timezone.datetime.fromisoformat(slot1)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.get_current_timezone())
    rdv = RendezVous.objects.create(
        patient=patient_user,
        organisme=org,
        devis=devis_part_patient.devis,
        devis_part=devis_part_patient,
        start=start,
        status=RendezVous.STATUS_REQUESTED,
        total_brut=devis_part_patient.total_brut,
        total_patient=devis_part_patient.total_patient,
    )

    slots = []
    from appointments.slots import availability

    for day in availability(org, horizon_days=14, max_days=14):
        for s in day["slots"]:
            if s["available"] and s["value"] != slot1:
                slots.append(s["value"])
                break
        if slots:
            break
    assert slots, "besoin d'un second créneau"
    slot2 = slots[0]

    client.force_login(patient_user)
    url = reverse("appointments:patient_reschedule", args=[rdv.reference])
    r = client.post(url, {"slot": slot2}, follow=False)
    assert r.status_code in (200, 302)
    rdv.refresh_from_db()
    assert rdv.start.isoformat()[:16] == timezone.datetime.fromisoformat(slot2).isoformat()[:16]
