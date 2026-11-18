"""Notifications messagerie patient — séparation Rappels / Notifications."""

import pytest
from django.urls import reverse

from messaging.models import Notification


@pytest.mark.django_db
def test_liste_notifications_patient_exclut_rdv(client, patient_user):
    Notification.objects.create(
        user=patient_user,
        title="Test QA notif",
        content="Message de test",
        notification_type="message",
        is_read=False,
    )
    Notification.objects.create(
        user=patient_user,
        title="RDV confirmé",
        content="Ne doit pas apparaître ici",
        notification_type="rdv",
        is_read=False,
    )
    client.force_login(patient_user)
    r = client.get(reverse("messaging:notifications"))
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/html")
    data = client.get(reverse("messaging:patient_notifications_api"), {"scope": "inbox"})
    assert data.status_code == 200
    titles = [item["title"] for item in data.json()["notifications"]]
    assert "Test QA notif" in titles
    assert not any(title.startswith("RDV confirmé") for title in titles)


@pytest.mark.django_db
def test_liste_rappels_patient_uniquement_rdv(client, patient_user):
    Notification.objects.create(
        user=patient_user,
        title="Devis reçu",
        content="XYZZY_DEVIS_INBOX_ONLY",
        notification_type="devis",
        is_read=False,
    )
    Notification.objects.create(
        user=patient_user,
        title="Rappel RDV",
        content="XYZZY_RDV_RAPPEL_ONLY",
        notification_type="rdv",
        is_read=False,
    )
    client.force_login(patient_user)
    r = client.get(reverse("messaging:rappels"))
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/html")
    data = client.get(reverse("messaging:patient_notifications_api"), {"scope": "rappels"})
    assert data.status_code == 200
    contents = [item["content"] for item in data.json()["notifications"]]
    assert "XYZZY_RDV_RAPPEL_ONLY" in contents
    assert "XYZZY_DEVIS_INBOX_ONLY" not in contents


@pytest.mark.django_db
def test_marquer_notification_lue(client, patient_user):
    notif = Notification.objects.create(
        user=patient_user,
        title="À lire QA",
        content="Contenu",
        notification_type="message",
        is_read=False,
    )
    client.force_login(patient_user)
    r = client.get(reverse("messaging:notification_read", args=[notif.pk]), follow=False)
    assert r.status_code == 302
    notif.refresh_from_db()
    assert notif.is_read


@pytest.mark.django_db
def test_tout_marquer_lu_inbox_seulement(client, patient_user):
    Notification.objects.create(
        user=patient_user,
        title="N1",
        content="x",
        notification_type="system",
        is_read=False,
    )
    Notification.objects.create(
        user=patient_user,
        title="R1",
        content="x",
        notification_type="rdv",
        is_read=False,
    )
    client.force_login(patient_user)
    r = client.post(
        reverse("messaging:mark_all_read"),
        {"scope": "inbox"},
        follow=False,
    )
    assert r.status_code == 302
    assert not Notification.objects.filter(
        user=patient_user, notification_type="system", is_read=False
    ).exists()
    assert Notification.objects.filter(
        user=patient_user, notification_type="rdv", is_read=False
    ).exists()


@pytest.mark.django_db
def test_tout_marquer_lu_rappels_seulement(client, patient_user):
    Notification.objects.create(
        user=patient_user,
        title="N1",
        content="x",
        notification_type="devis",
        is_read=False,
    )
    Notification.objects.create(
        user=patient_user,
        title="R1",
        content="x",
        notification_type="rdv",
        is_read=False,
    )
    client.force_login(patient_user)
    r = client.post(
        reverse("messaging:mark_all_read"),
        {"scope": "rappels"},
        follow=False,
    )
    assert r.status_code == 302
    assert not Notification.objects.filter(
        user=patient_user, notification_type="rdv", is_read=False
    ).exists()
    assert Notification.objects.filter(
        user=patient_user, notification_type="devis", is_read=False
    ).exists()
