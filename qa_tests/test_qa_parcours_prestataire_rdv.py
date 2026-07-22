"""RDV prestataire — agenda, liste, actions (confirmer, refuser, honoré)."""

import pytest
from datetime import datetime
from django.urls import reverse
from django.utils import timezone

from appointments.models import RendezVous
from appointments import slots as slot_engine
from appointments.slots import first_available_slot


def _make_requested_rdv(patient_user, devis_part_patient):
    org = devis_part_patient.organisme
    slot = first_available_slot(org)
    start = timezone.datetime.fromisoformat(slot)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.get_current_timezone())
    return RendezVous.objects.create(
        patient=patient_user,
        organisme=org,
        devis=devis_part_patient.devis,
        devis_part=devis_part_patient,
        start=start,
        status=RendezVous.STATUS_REQUESTED,
        total_brut=devis_part_patient.total_brut,
        total_patient=devis_part_patient.total_patient,
    )


@pytest.mark.django_db
def test_prestataire_agenda_200(client, prestataire_user, organisme_horaires):
    client.force_login(prestataire_user)
    r = client.get(reverse("appointments:prestataire_agenda"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_prestataire_liste_rdv_200(client, prestataire_user, organisme_horaires):
    client.force_login(prestataire_user)
    r = client.get(reverse("appointments:prestataire_rdv_list"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_prestataire_confirme_rdv(
    client, prestataire_user, patient_user, devis_part_patient,
):
    rdv = _make_requested_rdv(patient_user, devis_part_patient)
    client.force_login(prestataire_user)
    url = reverse("appointments:prestataire_rdv_action", args=[rdv.reference])
    r = client.post(
        url,
        {"action": "confirm", "next": reverse("appointments:prestataire_rdv_list")},
        follow=True,
    )
    assert r.status_code == 200
    rdv.refresh_from_db()
    assert rdv.status == RendezVous.STATUS_CONFIRMED


@pytest.mark.django_db
def test_prestataire_refuse_rdv(
    client, prestataire_user, patient_user, devis_part_patient,
):
    rdv = _make_requested_rdv(patient_user, devis_part_patient)
    client.force_login(prestataire_user)
    url = reverse("appointments:prestataire_rdv_action", args=[rdv.reference])
    r = client.post(url, {"action": "decline", "note": "Complet"}, follow=True)
    assert r.status_code == 200
    rdv.refresh_from_db()
    assert rdv.status == RendezVous.STATUS_DECLINED


@pytest.mark.django_db
def test_prestataire_modifie_rdv_depuis_liste(
    client, prestataire_user, patient_user, devis_part_patient,
):
    rdv = _make_requested_rdv(patient_user, devis_part_patient)
    org = devis_part_patient.organisme
    slots = []
    for day in slot_engine.availability(org, max_days=5):
        slots.extend(s["value"] for s in day["slots"] if s["available"])
    assert len(slots) >= 2
    new_slot = slots[1] if slots[0] == timezone.localtime(rdv.start).isoformat() else slots[0]
    # datetime-local format
    dt = datetime.fromisoformat(new_slot)
    slot_local = timezone.localtime(dt).strftime("%Y-%m-%dT%H:%M")

    client.force_login(prestataire_user)
    url = reverse("appointments:prestataire_rdv_update", args=[rdv.reference])
    r = client.post(url, {"slot": slot_local, "note": "Report"}, follow=True)
    assert r.status_code == 200
    rdv.refresh_from_db()
    assert timezone.localtime(rdv.start).strftime("%Y-%m-%dT%H:%M") == slot_local
    assert rdv.prestataire_note == "Report"


@pytest.mark.django_db
def test_prestataire_marque_honore(
    client, prestataire_user, patient_user, devis_part_patient,
):
    rdv = _make_requested_rdv(patient_user, devis_part_patient)
    rdv.confirm()
    client.force_login(prestataire_user)
    url = reverse("appointments:prestataire_rdv_action", args=[rdv.reference])
    r = client.post(url, {"action": "complete"}, follow=True)
    assert r.status_code == 200
    rdv.refresh_from_db()
    assert rdv.status == RendezVous.STATUS_COMPLETED
