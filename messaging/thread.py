"""Fil de discussion guidé (style WhatsApp) ancré sur un DevisPart / RendezVous."""
from __future__ import annotations

from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from .models import Conversation, Message, Notification


def thread_url(conv: Conversation) -> str:
    return reverse("messaging:conversation_detail", args=[conv.pk])


def _touch(conv: Conversation):
    conv.save(update_fields=["updated_at"])


def _append(
    conv: Conversation,
    *,
    sender,
    receiver,
    content: str,
    message_type: str = "internal",
    payload: dict | None = None,
    notify: bool = True,
    notify_title: str = "",
) -> Message:
    msg = Message.objects.create(
        conversation=conv,
        sender=sender,
        receiver=receiver,
        content=content,
        message_type=message_type,
        payload=payload or {},
    )
    _touch(conv)
    if notify and receiver:
        Notification.objects.create(
            user=receiver,
            notification_type="message",
            title=notify_title or f"Message · {conv.dossier_label}",
            content=content[:200],
            link=thread_url(conv),
        )
    return msg


def append_system(conv: Conversation, content: str, payload: dict | None = None) -> Message:
    return _append(
        conv,
        sender=conv.prestataire,
        receiver=conv.patient,
        content=content,
        message_type="system",
        payload=payload,
        notify=False,
    )


def append_status(conv: Conversation, content: str, payload: dict | None = None) -> Message:
    return _append(
        conv,
        sender=conv.prestataire,
        receiver=conv.patient,
        content=content,
        message_type="status_card",
        payload=payload,
        notify=False,
    )


def append_patient(conv: Conversation, content: str, *, notify=True, payload=None) -> Message:
    return _append(
        conv,
        sender=conv.patient,
        receiver=conv.prestataire,
        content=content,
        message_type="internal",
        payload=payload,
        notify=notify,
        notify_title=f"Patient · {conv.dossier_label}",
    )


def append_prestataire(conv: Conversation, content: str, *, notify=True, payload=None) -> Message:
    return _append(
        conv,
        sender=conv.prestataire,
        receiver=conv.patient,
        content=content,
        message_type="internal",
        payload=payload,
        notify=notify,
        notify_title=f"{conv.organisme.name if conv.organisme else 'Structure'} · {conv.dossier_label}",
    )


def _actes_lines(part) -> str:
    lines = []
    for row in part.details or []:
        qty = row.get("quantity", 1)
        acte = row.get("acte", "")
        sub = row.get("patient_cost") or row.get("subtotal") or "0"
        try:
            sub_i = int(float(sub))
        except (TypeError, ValueError):
            sub_i = sub
        suffix = f" ×{qty}" if qty and int(qty) > 1 else ""
        lines.append(f"• {acte}{suffix} — {sub_i:,} F".replace(",", " "))
    return "\n".join(lines) if lines else "• (détail non disponible)"


def ensure_devis_thread(part) -> tuple[Conversation, bool]:
    """Crée le fil lié à un sous-devis (1 fil = 1 structure)."""
    org = part.organisme
    prestataire = org.user
    patient = part.devis.patient
    conv, created = Conversation.objects.get_or_create(
        devis_part=part,
        defaults={
            "patient": patient,
            "prestataire": prestataire,
            "subject": f"{org.name} · {part.reference}",
            "kind": Conversation.KIND_DEVIS,
            "thread_status": Conversation.STATUS_ACTIVE,
        },
    )
    if not created and conv.messages.exists():
        return conv, False

    if not created:
        # Fil créé sans messages (ex. erreur partielle) — on (re)peuple.
        pass
    else:
        created = True

    append_system(
        conv,
        f"Estimation MedCare · {org.name}\nDevis parent {part.devis.reference}",
        payload={"event": "devis_opened", "part_ref": part.reference},
    )
    append_prestataire(
        conv,
        f"Bonjour 👋 Voici le récapitulatif de votre demande :\n\n{_actes_lines(part)}\n\n"
        f"Total patient : {int(part.total_patient or 0):,} F".replace(",", " ")
        + "\n\nSouhaitez-vous prendre rendez-vous ? Utilisez le bouton ci-dessous ou écrivez-nous ici.",
        notify=True,
    )
    append_patient(conv, "Je souhaite prendre rendez-vous pour ces actes.", notify=False)
    return conv, True


def link_rdv(conv: Conversation, rdv) -> Conversation:
    conv.rendez_vous = rdv
    conv.kind = Conversation.KIND_RDV
    conv.thread_status = Conversation.STATUS_WAITING
    conv.save(update_fields=["rendez_vous", "kind", "thread_status", "updated_at"])
    return conv


def _slot_label(dt) -> str:
    if not dt:
        return "—"
    loc = timezone.localtime(dt)
    return date_format(loc, "l j F · H\\hi")


def on_rdv_requested(rdv, note: str = "") -> Conversation | None:
    part = rdv.devis_part
    if not part:
        return None
    conv, _ = ensure_devis_thread(part)
    link_rdv(conv, rdv)
    label = _slot_label(rdv.start)
    append_patient(conv, f"🕐 Créneau souhaité : {label}", notify=True)
    if note:
        append_patient(conv, note.strip(), notify=False)
    append_status(
        conv,
        f"⏳ Demande envoyée — en attente de confirmation par {rdv.organisme.name}.",
        payload={"rdv_ref": rdv.reference, "status": rdv.status},
    )
    return conv


def on_rdv_rescheduled(rdv, old_start, note: str = "", *, by_patient: bool = True) -> Conversation | None:
    """Créneau modifié par le patient (depuis la messagerie)."""
    conv = conversation_for_rdv(rdv)
    if not conv:
        return on_rdv_requested(rdv, note)
    old_label = _slot_label(old_start)
    new_label = _slot_label(rdv.start)
    append_system(
        conv,
        f"Créneau modifié : {old_label} → {new_label}",
        payload={"event": "slot_changed", "rdv_ref": rdv.reference, "by": "patient"},
    )
    append_patient(conv, f"Nouveau créneau souhaité : {new_label}", notify=True)
    if note:
        append_patient(conv, note.strip(), notify=False)
    append_status(
        conv,
        "Nouvelle demande — en attente de confirmation.",
        payload={"rdv_ref": rdv.reference, "status": rdv.status, "event": "waiting"},
    )
    conv.thread_status = Conversation.STATUS_WAITING
    conv.save(update_fields=["thread_status", "updated_at"])
    return conv


def on_rdv_moved_by_prestataire(rdv, old_start, note: str = "") -> Conversation | None:
    """Créneau déplacé par la structure (agenda pro, drag & drop)."""
    from appointments.models import RendezVous

    conv = conversation_for_rdv(rdv)
    if not conv and rdv.devis_part_id:
        conv, _ = ensure_devis_thread(rdv.devis_part)
        link_rdv(conv, rdv)
    if not conv:
        return None

    old_label = _slot_label(old_start)
    new_label = _slot_label(rdv.start)
    org_name = rdv.organisme.name if rdv.organisme_id else "La structure"

    append_system(
        conv,
        f"Créneau déplacé par {org_name} : {old_label} → {new_label}",
        payload={"event": "slot_moved", "rdv_ref": rdv.reference, "by": "prestataire"},
    )

    if rdv.status == RendezVous.STATUS_CONFIRMED:
        body = f"Votre rendez-vous confirmé est maintenant prévu le {new_label}."
        status_body = f"Rendez-vous confirmé · {new_label}"
        thread_status = Conversation.STATUS_ACTIVE
        event_key = "confirmed"
    else:
        body = (
            f"{org_name} vous propose un nouveau créneau : {new_label}. "
            "Merci de confirmer si cela vous convient."
        )
        status_body = f"Nouveau créneau proposé · {new_label}"
        thread_status = Conversation.STATUS_WAITING
        event_key = "waiting"

    append_prestataire(
        conv,
        body,
        notify=True,
        payload={"rdv_ref": rdv.reference, "event": "slot_moved"},
    )
    if note:
        append_prestataire(conv, note.strip(), notify=False)

    append_status(
        conv,
        status_body,
        payload={"rdv_ref": rdv.reference, "status": rdv.status, "event": event_key},
    )
    conv.thread_status = thread_status
    conv.save(update_fields=["thread_status", "updated_at"])
    return conv


def on_rdv_event(rdv, event: str, detail: str = "") -> Conversation | None:
    """event: confirmed | declined | cancelled | completed | no_show"""
    conv = (
        Conversation.objects.filter(devis_part=rdv.devis_part_id).first()
        if rdv.devis_part_id
        else Conversation.objects.filter(rendez_vous=rdv).first()
    )
    if not conv:
        return None

    labels = {
        "confirmed": ("✅ Rendez-vous confirmé", Conversation.STATUS_ACTIVE),
        "declined": ("✕ Demande refusée", Conversation.STATUS_CLOSED),
        "cancelled": ("Annulation", Conversation.STATUS_CLOSED),
        "completed": ("✓ Rendez-vous honoré", Conversation.STATUS_CLOSED),
        "no_show": ("Patient absent", Conversation.STATUS_CLOSED),
    }
    title, ts = labels.get(event, (event, conv.thread_status))
    label = _slot_label(rdv.start)
    body = f"{title} · {label}"
    if detail:
        body += f"\n{detail}"
    append_status(conv, body, payload={"rdv_ref": rdv.reference, "status": rdv.status, "event": event})
    conv.thread_status = ts
    conv.save(update_fields=["thread_status", "updated_at"])

    if event == "confirmed":
        append_prestataire(
            conv,
            f"Votre rendez-vous est confirmé pour le {label}. À bientôt !",
            notify=True,
        )
    elif event in ("declined", "cancelled") and detail:
        append_prestataire(conv, detail, notify=True)
    return conv


def on_rdv_reminder(
    rdv,
    *,
    schedule_label: str,
    schedule_id: int,
    prerequisites: str = "",
) -> Conversation | None:
    """Poste le rappel RDV (avec consignes actes) dans le fil messagerie."""
    conv = conversation_for_rdv(rdv)
    if not conv and rdv.devis_part_id:
        conv, _ = ensure_devis_thread(rdv.devis_part)
        link_rdv(conv, rdv)
    if not conv:
        return None
    if _has_reminder_marker(conv, rdv.reference, schedule_id):
        return conv

    label = _slot_label(rdv.start)
    org_name = rdv.organisme.name if rdv.organisme_id else "la structure"
    summary = (
        f"Votre rendez-vous {rdv.reference} chez {org_name} "
        f"est prévu le {label}."
    )
    body_lines = [f"🔔 Rappel — {schedule_label}", summary]
    if prerequisites:
        body_lines.extend(["", "📋 Consignes importantes :", prerequisites])
    append_status(
        conv,
        "\n".join(body_lines),
        payload={
            "rdv_ref": rdv.reference,
            "event": "reminder",
            "schedule_id": schedule_id,
            "schedule_label": schedule_label,
            "prerequisites": prerequisites,
            "summary": summary,
        },
    )
    return conv


def conversation_for_part(part) -> Conversation | None:
    return Conversation.objects.filter(devis_part=part).select_related(
        "rendez_vous", "devis_part__organisme"
    ).first()


def conversation_for_rdv(rdv) -> Conversation | None:
    if rdv.devis_part_id:
        return conversation_for_part(rdv.devis_part)
    return Conversation.objects.filter(rendez_vous=rdv).first()


def _has_rdv_marker(conv: Conversation, rdv_ref: str, event: str | None = None) -> bool:
    qs = conv.messages.filter(payload__rdv_ref=rdv_ref)
    if event:
        return qs.filter(payload__event=event).exists()
    return qs.exists()


def _has_reminder_marker(conv: Conversation, rdv_ref: str, schedule_id: int) -> bool:
    return conv.messages.filter(
        payload__rdv_ref=rdv_ref,
        payload__event="reminder",
        payload__schedule_id=schedule_id,
    ).exists()


def sync_rdv_thread(rdv, *, notify: bool = False) -> Conversation | None:
    """Peuple ou complète le fil d'un RDV déjà en base (backfill / resync)."""
    from appointments.models import RendezVous

    part = rdv.devis_part
    if not part:
        return None

    conv, _ = ensure_devis_thread(part)
    link_rdv(conv, rdv)

    ref = rdv.reference
    label = _slot_label(rdv.start)
    note = (rdv.patient_note or "").strip()
    detail = (rdv.prestataire_note or rdv.cancel_reason or "").strip()

    slot_markers = conv.messages.filter(payload__rdv_ref=ref, content__icontains="Créneau").exists()
    if not slot_markers and rdv.status in (
        RendezVous.STATUS_REQUESTED,
        RendezVous.STATUS_CONFIRMED,
        RendezVous.STATUS_COMPLETED,
        RendezVous.STATUS_NO_SHOW,
    ):
        append_patient(conv, f"🕐 Créneau souhaité : {label}", notify=notify)
        if note:
            append_patient(conv, note, notify=False)

    status_events = {
        RendezVous.STATUS_REQUESTED: (
            "waiting",
            f"⏳ Demande envoyée — en attente de confirmation par {rdv.organisme.name}.",
            Conversation.STATUS_WAITING,
        ),
        RendezVous.STATUS_CONFIRMED: (
            "confirmed",
            f"✅ Rendez-vous confirmé · {label}",
            Conversation.STATUS_ACTIVE,
        ),
        RendezVous.STATUS_DECLINED: (
            "declined",
            f"✕ Demande refusée · {label}",
            Conversation.STATUS_CLOSED,
        ),
        RendezVous.STATUS_CANCELLED: (
            "cancelled",
            f"Annulation · {label}" + (f"\n{detail}" if detail else ""),
            Conversation.STATUS_CLOSED,
        ),
        RendezVous.STATUS_COMPLETED: (
            "completed",
            f"✓ Rendez-vous honoré · {label}",
            Conversation.STATUS_CLOSED,
        ),
        RendezVous.STATUS_NO_SHOW: (
            "no_show",
            f"Patient absent · {label}",
            Conversation.STATUS_CLOSED,
        ),
    }

    spec = status_events.get(rdv.status)
    if spec:
        event_key, body, thread_status = spec
        if not _has_rdv_marker(conv, ref, event_key):
            append_status(
                conv,
                body,
                payload={"rdv_ref": ref, "status": rdv.status, "event": event_key},
            )
        if (
            rdv.status == RendezVous.STATUS_CONFIRMED
            and not conv.messages.filter(content__icontains="confirmé pour le").exists()
        ):
            append_prestataire(
                conv,
                f"Votre rendez-vous est confirmé pour le {label}. À bientôt !",
                notify=notify,
            )
        conv.thread_status = thread_status
        conv.kind = Conversation.KIND_RDV
        conv.save(update_fields=["thread_status", "kind", "updated_at"])

    return conv


def fix_notification_links_for_conv(conv: Conversation) -> int:
    """Pointe les notifications liées au dossier vers le fil de discussion."""
    if not conv.devis_part_id:
        return 0
    part = conv.devis_part
    url = thread_url(conv)
    updated = 0
    for user_id in (conv.patient_id, conv.prestataire_id):
        updated += Notification.objects.filter(user_id=user_id).filter(
            link__icontains=part.reference
        ).update(link=url)
        if conv.rendez_vous_id:
            updated += Notification.objects.filter(user_id=user_id).filter(
                link__icontains=conv.rendez_vous.reference
            ).update(link=url)
    return updated
