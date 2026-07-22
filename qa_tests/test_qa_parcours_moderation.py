"""
Parcours modération : approbation / rejet structure, avis patient, publication avis.
Vérifie que les événements attendus alimentent le journal des notifications.
"""

import pytest
from django.urls import reverse

from healthcare.models import PlatformReview
from notifications.models import NotificationEvent, NotificationLog


def _count_logs(code: str) -> int:
    ev = NotificationEvent.objects.get(code=code)
    return NotificationLog.objects.filter(event=ev).count()


@pytest.mark.django_db
def test_approbation_organisme_cree_log_organisme_approved(
    client, superuser, organisme_en_attente,
):
    n0 = _count_logs("organisme.approved")
    client.force_login(superuser)
    url = reverse("dashboard:organisme_approve", args=[organisme_en_attente.pk])
    r = client.get(url, follow=False)
    assert r.status_code == 302
    organisme_en_attente.refresh_from_db()
    assert organisme_en_attente.is_active is True
    assert _count_logs("organisme.approved") == n0 + 1


@pytest.mark.django_db
def test_rejet_organisme_cree_log_organisme_rejected(
    client, superuser, organisme_actif,
):
    n0 = _count_logs("organisme.rejected")
    client.force_login(superuser)
    url = reverse("dashboard:organisme_reject", args=[organisme_actif.pk])
    r = client.get(url, follow=False)
    assert r.status_code == 302
    organisme_actif.refresh_from_db()
    assert organisme_actif.is_active is False
    assert _count_logs("organisme.rejected") == n0 + 1


@pytest.mark.django_db
def test_patient_soumet_avis_cree_log_review_posted(
    client, patient_user, prestataire_acte, admin_user,
):
    acte = prestataire_acte.acte
    n0 = _count_logs("review.posted")
    client.force_login(patient_user)
    url = reverse("healthcare:platform_review")
    r = client.post(
        url,
        data={
            "rating": "5",
            "tarifs_delais_comment": "Très bon accueil (QA).",
            "actes": str(acte.pk),
        },
        follow=False,
    )
    assert r.status_code == 302
    assert PlatformReview.objects.filter(patient=patient_user, rating=5).exists()
    assert _count_logs("review.posted") == n0 + 1


@pytest.mark.django_db
def test_admin_approuve_avis_cree_log_review_approved(
    client, superuser, patient_user, prestataire_acte,
):
    acte = prestataire_acte.acte
    review = PlatformReview.objects.create(
        patient=patient_user,
        rating=4,
        tarifs_delais_comment="En attente",
        is_approved=False,
    )
    review.actes.add(acte)
    n0 = _count_logs("review.approved")
    client.force_login(superuser)
    url = reverse("dashboard:review_approve", args=[review.pk])
    r = client.get(url, follow=False)
    assert r.status_code == 302
    review.refresh_from_db()
    assert review.is_approved is True
    assert _count_logs("review.approved") == n0 + 1
