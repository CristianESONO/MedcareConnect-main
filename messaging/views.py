from datetime import timedelta
from urllib.parse import quote

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.urls import reverse
from django.utils.formats import date_format
from django.utils import timezone

from users.patient_account_ctx import patient_account_tab

from .models import Conversation, Message, Notification
from . import thread as thread_svc
from healthcare.models import OrganismeDeSante
from cart.models import Cart


def _presta_ctx(user):
    try:
        return {
            "org": user.healthcare_provider_profile,
            "dash_active": "messages",
        }
    except Exception:
        return {"dash_active": "messages"}


def _thread_display_messages(conv: Conversation, msgs):
    """Masque les messages « seed » remplacés par l’UI dédiée (carte devis, demande initiale)."""
    if not conv.devis_part_id:
        return list(msgs)
    out = []
    for msg in msgs:
        if msg.message_type == "system":
            low = (msg.content or "").lower()
            if "estimation medcare" in low and "devis parent" in low:
                continue
            out.append(msg)
            continue
        if msg.sender_id == conv.prestataire_id and "récapitulatif" in (msg.content or "").lower():
            continue
        if msg.sender_id == conv.patient_id and "je souhaite prendre rendez-vous pour ces actes" in (msg.content or "").lower():
            continue
        out.append(msg)
    return out


def _date_separator_label(dt) -> str:
    local = timezone.localtime(dt)
    day = local.date()
    today = timezone.localdate()
    if day == today:
        return "Aujourd'hui"
    if day == today - timedelta(days=1):
        return "Hier"
    return date_format(local, "j F Y")


def _thread_sender_label(msg: Message, conv: Conversation) -> str | None:
    if msg.message_type == "status_card":
        return "MedCare"
    if msg.message_type == "system":
        return None
    if msg.sender_id == conv.prestataire_id:
        org = conv.organisme
        return org.name if org else (conv.prestataire.display_name or "Structure")
    if msg.sender_id == conv.patient_id:
        return conv.patient.display_name or "Patient"
    return "MedCare"


def _thread_timeline(conv: Conversation, msgs, *, skip_day=None):
    """Chronologie avec séparateurs de date et libellé d’expéditeur."""
    timeline = []
    last_day = None
    for msg in msgs:
        msg_day = timezone.localtime(msg.timestamp).date()
        if msg_day != last_day:
            if not (skip_day and last_day is None and msg_day == skip_day):
                timeline.append({"kind": "date", "label": _date_separator_label(msg.timestamp)})
            last_day = msg_day
        msg.thread_sender = _thread_sender_label(msg, conv)
        timeline.append({"kind": "message", "msg": msg})
    return timeline


def _live_rdv_for_conv(conv: Conversation):
    """RDV actif (demandé ou confirmé) lié au fil, via FK ou sous-devis."""
    from appointments.models import RendezVous

    rdv = conv.rendez_vous
    if rdv and rdv.status in RendezVous.LIVE_STATUSES:
        return rdv
    if conv.devis_part_id:
        return (
            RendezVous.objects.filter(
                devis_part=conv.devis_part,
                status__in=RendezVous.LIVE_STATUSES,
            )
            .order_by("-created_at")
            .first()
        )
    return None


def _thread_context(request, conv: Conversation) -> dict:
    from appointments.models import RendezVous
    from appointments import slots as slot_engine
    from appointments.panel import book_data_json

    conv = (
        Conversation.objects.select_related(
            "patient",
            "prestataire",
            "devis_part__organisme",
            "devis_part__devis",
            "rendez_vous__organisme",
        )
        .filter(pk=conv.pk)
        .first()
    )
    rdv = conv.rendez_vous
    live_rdv = _live_rdv_for_conv(conv)
    display_rdv = live_rdv or rdv
    part = conv.devis_part
    org = part.organisme if part else (display_rdv.organisme if display_rdv else None)

    status_banner = None
    thread_actions = []
    show_reschedule = show_book = False
    reschedule_ctx = book_ctx = None

    is_patient = request.user == conv.patient
    is_presta = request.user == conv.prestataire
    conv_url = reverse("messaging:conversation_detail", args=[conv.pk])

    allow_reply = conv.thread_status != Conversation.STATUS_CLOSED
    if is_patient:
        allow_reply = False

    if display_rdv and display_rdv.start:
        badge = conv.status_badge
        if live_rdv:
            mapping = {
                "requested": ("wait", "À confirmer"),
                "confirmed": ("ok", "Confirmé"),
            }
            badge = mapping.get(live_rdv.status, badge)
        when = date_format(timezone.localtime(display_rdv.start), "l j F · H\\hi")
        status_banner = {"class": badge[0], "text": f"{badge[1]} · {when}"}
    elif part:
        status_banner = {"class": "ok", "text": "Estimation disponible — prenez rendez-vous"}

    if is_patient and live_rdv:
        if live_rdv.status == RendezVous.STATUS_REQUESTED:
            if request.GET.get("reschedule"):
                show_reschedule = True
                payload, has_slots = book_data_json(org, part)
                reschedule_ctx = {
                    "org": org,
                    "part": part,
                    "has_slots": has_slots,
                    "book_data_json": payload,
                    "rdv_ref": live_rdv.reference,
                    "success_url": conv_url,
                }
            else:
                thread_actions.append({
                    "label": "Modifier le créneau",
                    "url": conv_url + "?reschedule=1",
                    "method": "GET",
                    "style": "primary",
                })
        thread_actions.append({
            "label": "Annuler le RDV",
            "url": reverse("appointments:patient_cancel", args=[live_rdv.reference]),
            "method": "POST",
            "style": "danger",
            "confirm": "Annuler ce rendez-vous ?",
            "hidden": {"reason": "Annulé via messagerie", "next": conv_url},
        })

    elif is_patient and part and not live_rdv:
        if request.GET.get("book"):
            show_book = True
            payload, has_slots = book_data_json(org, part)
            book_ctx = {
                "org": org,
                "part": part,
                "has_slots": has_slots,
                "book_data_json": payload,
                "success_url": conv_url,
            }
        # Boutons « Prendre RDV » : mc-thread-footer dans le template

    if is_presta and display_rdv:
        if display_rdv.status == RendezVous.STATUS_REQUESTED:
            thread_actions.extend([
                {
                    "label": "Confirmer",
                    "url": reverse("appointments:prestataire_rdv_action", args=[display_rdv.reference]),
                    "method": "POST",
                    "style": "ok",
                    "hidden": {"action": "confirm", "next": conv_url},
                },
                {
                    "label": "Refuser",
                    "url": reverse("appointments:prestataire_rdv_action", args=[display_rdv.reference]),
                    "method": "POST",
                    "style": "danger",
                    "confirm": "Refuser cette demande ?",
                    "hidden": {"action": "decline", "next": conv_url},
                },
            ])
        elif display_rdv.status == RendezVous.STATUS_CONFIRMED:
            thread_actions.extend([
                {
                    "label": "Honoré",
                    "url": reverse("appointments:prestataire_rdv_action", args=[display_rdv.reference]),
                    "method": "POST",
                    "style": "ok",
                    "hidden": {"action": "complete", "next": conv_url},
                },
                {
                    "label": "Absent",
                    "url": reverse("appointments:prestataire_rdv_action", args=[display_rdv.reference]),
                    "method": "POST",
                    "style": "danger",
                    "hidden": {"action": "no_show", "next": conv_url},
                },
            ])

    return {
        "thread_org": org,
        "status_banner": status_banner,
        "thread_actions": thread_actions,
        "show_reschedule": show_reschedule,
        "reschedule_ctx": reschedule_ctx,
        "show_book": show_book,
        "book_ctx": book_ctx,
        "allow_reply": allow_reply,
        "has_live_rdv": live_rdv is not None,
    }


def _group_by_day(items, datetime_attr="updated_at"):
    """
    Regroupe une liste d'objets (conversations/messages) par jour selon datetime_attr.
    """
    groups = []
    current_group = None
    for item in items:
        dt = getattr(item, datetime_attr, None)
        if not dt:
            continue
        local_dt = timezone.localtime(dt)
        day = local_dt.date()
        if not current_group or current_group["date"] != day:
            current_group = {
                "date": day,
                "label": _date_separator_label(dt),
                "items": []
            }
            groups.append(current_group)
        current_group["items"].append(item)
    return groups


@login_required
def inbox(request):
    if request.user.is_prestataire:
        conversations = Conversation.objects.filter(prestataire=request.user)
    else:
        conversations = Conversation.objects.filter(patient=request.user)

    conversations = conversations.select_related(
        "patient", "prestataire", "devis_part__organisme", "rendez_vous"
    ).order_by("-updated_at")

    ctx = {"conversations": conversations}
    if request.user.is_patient:
        devis_ref = (request.GET.get("devis") or "").strip()
        if devis_ref and request.GET.get("validate") == "1":
            from cart.models import Devis
            from users.patient_panel import devis_validate_inbox_context

            devis = (
                Devis.objects.filter(reference=devis_ref, patient=request.user)
                .prefetch_related("parts__organisme")
                .first()
            )
            if devis:
                validate_ctx = devis_validate_inbox_context(devis)
                ctx.update(validate_ctx)
                highlight_ids = validate_ctx.get("devis_validate_highlight_ids") or set()
                if highlight_ids:
                    conv_list = list(conversations)
                    conv_list.sort(
                        key=lambda c: (
                            0 if c.pk in highlight_ids else 1,
                            -c.updated_at.timestamp(),
                        )
                    )
                    ctx["conversations"] = conv_list
                    ctx["conversations_pending_validate"] = [
                        c for c in conv_list if c.pk in highlight_ids
                    ]
                    ctx["conversations_other"] = [
                        c for c in conv_list if c.pk not in highlight_ids
                    ]

    if "conversations_pending_validate" in ctx:
        ctx["grouped_pending"] = _group_by_day(ctx["conversations_pending_validate"])
    if "conversations_other" in ctx:
        ctx["grouped_other"] = _group_by_day(ctx["conversations_other"])
    ctx["grouped_conversations"] = _group_by_day(ctx["conversations"])

    if request.user.is_prestataire:
        ctx.update(_presta_ctx(request.user))
        return render(request, "messaging/inbox_prestataire.html", ctx)
    if request.user.is_patient:
        ctx.update(patient_account_tab("messages"))
        return render(request, "messaging/inbox_patient.html", ctx)
    return render(request, "messaging/inbox.html", ctx)


@login_required
def conversation_detail(request, pk):
    conv = get_object_or_404(
        Conversation.objects.select_related(
            "patient",
            "prestataire",
            "devis_part__organisme",
            "devis_part__devis",
            "rendez_vous__organisme",
        ),
        pk=pk,
    )
    if request.user != conv.patient and request.user != conv.prestataire:
        django_messages.error(request, "Accès non autorisé.")
        return redirect("messaging:inbox")

    conv_url = reverse("messaging:conversation_detail", args=[conv.pk])
    if request.user == conv.patient:
        from appointments.models import RendezVous

        live_rdv = _live_rdv_for_conv(conv)
        if request.GET.get("book") and live_rdv:
            return redirect(conv_url)
        if request.GET.get("reschedule") and (
            not live_rdv or live_rdv.status != RendezVous.STATUS_REQUESTED
        ):
            return redirect(conv_url)

    conv.messages.filter(receiver=request.user, is_read=False).update(is_read=True)

    if request.method == "POST" and (request.POST.get("content") or request.FILES.get("attachment")):
        content = (request.POST.get("content") or "").strip()
        attachment = request.FILES.get("attachment")
        if attachment:
            if request.user == conv.patient:
                thread_svc.append_patient(
                    conv,
                    content or "Pièce jointe",
                    attachment=attachment,
                )
            elif request.user == conv.prestataire:
                thread_svc.append_prestataire(
                    conv,
                    content or "Pièce jointe",
                    attachment=attachment,
                )
        elif content:
            if request.user == conv.patient:
                django_messages.warning(
                    request,
                    "Les messages libres ne sont pas disponibles — utilisez la prise de rendez-vous.",
                )
            elif request.user == conv.prestataire:
                thread_svc.append_prestataire(conv, content)
        return redirect("messaging:conversation_detail", pk=conv.pk)

    raw_msgs = conv.messages.select_related("sender").order_by("timestamp")
    msgs = _thread_display_messages(conv, raw_msgs)
    skip_day = timezone.localtime(conv.created_at).date() if conv.devis_part_id else None
    thread_timeline = _thread_timeline(conv, msgs, skip_day=skip_day)
    devis_open_date_label = _date_separator_label(conv.created_at) if conv.devis_part_id else None
    try:
        thread_ctx = _thread_context(request, conv)
    except Exception:
        thread_ctx = {
            "thread_org": conv.organisme,
            "status_banner": None,
            "thread_actions": [],
            "show_reschedule": False,
            "reschedule_ctx": None,
            "show_book": False,
            "book_ctx": None,
            "allow_reply": conv.thread_status != Conversation.STATUS_CLOSED
            and request.user != conv.patient,
            "has_live_rdv": _live_rdv_for_conv(conv) is not None,
        }
    ctx = {
        "conversation": conv,
        "msgs": msgs,
        "thread_timeline": thread_timeline,
        "devis_open_date_label": devis_open_date_label,
        "thread_org": conv.organisme,
        "thread_actions": [],
        "status_banner": None,
        "show_reschedule": False,
        "show_book": False,
        "allow_reply": True,
        "has_live_rdv": False,
        **thread_ctx,
    }
    if request.user.is_patient:
        ctx.update(patient_account_tab("messages"))
        return render(request, "messaging/conversation_patient.html", ctx)
    ctx.update(_presta_ctx(request.user))
    return render(request, "messaging/conversation.html", ctx)


@login_required
def start_conversation(request, slug):
    org = get_object_or_404(OrganismeDeSante, slug=slug, is_active=True)
    if request.user == org.user:
        django_messages.warning(request, "Vous ne pouvez pas vous envoyer un message.")
        return redirect("healthcare:organisme_detail", slug=slug)

    conv = Conversation.objects.filter(
        patient=request.user, prestataire=org.user, kind=Conversation.KIND_GENERAL
    ).first()
    if not conv:
        subject = request.GET.get("subject", f"Demande pour {org.name}")
        conv = Conversation.objects.create(
            patient=request.user,
            prestataire=org.user,
            subject=subject,
            kind=Conversation.KIND_GENERAL,
        )
    return redirect("messaging:conversation_detail", pk=conv.pk)


@login_required
def whatsapp_contact(request, slug):
    org = get_object_or_404(OrganismeDeSante, slug=slug, is_active=True)
    phone = org.whatsapp_number or org.contact_phone
    if not phone:
        django_messages.error(request, "Ce prestataire n'a pas de numéro WhatsApp configuré.")
        return redirect("healthcare:organisme_detail", slug=slug)

    number = phone.replace("+", "").replace(" ", "").replace("-", "")

    cart = Cart.objects.filter(patient=request.user, status="active").first()
    lines = [f"Bonjour {org.name},", "", "Je vous contacte via MedCare Connect."]
    if cart and cart.items.exists():
        lines.append("")
        lines.append("Actes qui m'intéressent :")
        for item in cart.items.filter(prestataire_acte__organisme=org).select_related("prestataire_acte__acte"):
            lines.append(f"- {item.prestataire_acte.acte.name} ({item.prestataire_acte.price} XOF)")
        lines.append("")
        lines.append("Merci de me confirmer la disponibilité et les tarifs.")
    else:
        lines.append("")
        lines.append("J'aimerais avoir des informations sur vos services.")

    text = quote("\n".join(lines))
    wa_url = f"https://wa.me/{number}?text={text}"

    Message.objects.create(
        sender=request.user,
        receiver=org.user,
        content=f"[WhatsApp] Contact initié vers {org.name}",
        message_type="whatsapp_request",
        whatsapp_data={"phone": number, "organisme": org.name},
    )
    Notification.objects.create(
        user=org.user,
        notification_type="whatsapp",
        title=f"Demande WhatsApp de {request.user.display_name}",
        content=f"Le patient {request.user.display_name} a initié un contact WhatsApp.",
        link=f"/healthcare/{org.slug}/",
    )

    return redirect(wa_url)


@login_required
def notifications_list(request):
    notifs = Notification.queryset_inbox(request.user).order_by("-created_at")[:50]
    ctx = {"notifications": notifs, "notif_scope": "inbox"}
    if request.user.is_patient:
        ctx.update(patient_account_tab("notifications"))
        return render(request, "messaging/notifications_patient.html", ctx)
    return render(request, "messaging/notifications.html", ctx)


@login_required
def rappels_list(request):
    if not getattr(request.user, "is_patient", False):
        return redirect("messaging:notifications")
    notifs = (
        Notification.objects.filter(user=request.user)
        .filter(notification_type__in=["rappel", "prelevement", "preparation"])
        .exclude(title__icontains="confirmé")
        .exclude(title__icontains="devis")
        .order_by("-created_at")[:50]
    )
    ctx = {
        "notifications": notifs,
        "notif_scope": "rappels",
    }
    ctx.update(patient_account_tab("rappels"))
    return render(request, "messaging/rappels_patient.html", ctx)


@login_required
def notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    if notif.link:
        return redirect(notif.link)
    if notif.is_rappel:
        return redirect("messaging:rappels")
    return redirect("messaging:notifications")


@login_required
def mark_all_read(request):
    scope = (request.POST.get("scope") or request.GET.get("scope") or "inbox").strip()
    qs = Notification.objects.filter(user=request.user, is_read=False)
    if scope == "rappels":
        qs = qs.filter(notification_type__in=Notification.RAPPEL_NOTIFICATION_TYPES)
        redirect_name = "messaging:rappels"
        msg = "Tous les rappels ont été marqués comme lus."
    else:
        qs = qs.exclude(notification_type__in=Notification.RAPPEL_NOTIFICATION_TYPES)
        redirect_name = "messaging:notifications"
        msg = "Toutes les notifications ont été marquées comme lues."
    qs.update(is_read=True)
    django_messages.success(request, msg)
    return redirect(redirect_name)
