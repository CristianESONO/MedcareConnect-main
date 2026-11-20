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
    assert b"Test QA notif" in r.content
    assert b"RDV confirm" not in r.content


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
    assert b"XYZZY_RDV_RAPPEL_ONLY" in r.content
    panel_start = r.content.find(b"pac-panel")
    assert panel_start >= 0
    panel_chunk = r.content[panel_start : panel_start + 8000]
    assert b"XYZZY_DEVIS_INBOX_ONLY" not in panel_chunk


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
def test_marquer_un_rappel_lu_le_deplace_vers_historique(client, patient_user):
    notif = Notification.objects.create(
        user=patient_user,
        title="Rappel à lire QA",
        content="Contenu du rappel",
        notification_type="rdv",
        is_read=False,
    )
    client.force_login(patient_user)

    response = client.post(
        reverse("messaging:notification_read", args=[notif.pk]),
        follow=False,
    )

    assert response.status_code == 302
    assert response.url == reverse("messaging:rappels")
    notif.refresh_from_db()
    assert notif.is_read

    active_page = client.get(reverse("messaging:rappels"))
    assert b"Rappel \xc3\xa0 lire QA" not in active_page.content

    history_page = client.get(reverse("messaging:rappels") + "?view=history")
    assert b"Rappel \xc3\xa0 lire QA" in history_page.content
    assert b'aria-label="Rappel marqu' in history_page.content
    assert b">Lu \xe2\x9c\x93</span>" in history_page.content
    assert b">Marquer comme lu</button>" not in history_page.content


@pytest.mark.django_db
def test_notifications_lues_restent_dans_historique(client, patient_user):
    notif = Notification.objects.create(
        user=patient_user,
        title="Notification archivée QA",
        content="Conservée",
        notification_type="message",
        is_read=True,
    )
    client.force_login(patient_user)

    active_page = client.get(reverse("messaging:notifications"))
    assert "Notification archivée QA".encode() not in active_page.content

    history_page = client.get(reverse("messaging:notifications") + "?view=history")
    assert "Notification archivée QA".encode() in history_page.content
    assert Notification.objects.filter(pk=notif.pk).exists()


@pytest.mark.django_db
def test_cloche_limitee_aux_cinq_notifications_non_lues(client, patient_user):
    for index in range(6):
        Notification.objects.create(
            user=patient_user,
            title=f"Notification {index}",
            notification_type="message",
            is_read=False,
        )
    client.force_login(patient_user)

    response = client.get(reverse("messaging:notifications"))

    assert response.context["recent_unread_count"] == 6
    assert len(response.context["recent_notifications"]) == 5
    assert b'class="medcare-notif-btn"' in response.content
    assert b'href="/messaging/notifications/" class="notif-foot' in response.content


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


@pytest.mark.django_db
def test_cartes_bilans_recommandes_ouvrent_les_presets_catalogue(client, patient_user):
    client.force_login(patient_user)
    response = client.get(reverse("messaging:rappels"))

    assert response.status_code == 200
    for bilan_key in ("general", "prenup", "pregnancy", "oms"):
        assert f"?bilan={bilan_key}".encode() in response.content
