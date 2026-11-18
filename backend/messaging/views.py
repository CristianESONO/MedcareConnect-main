from datetime import timedelta
import json
from urllib.parse import quote

from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.urls import reverse
from django.utils.formats import date_format
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from django.db.models import Count, F, OuterRef, Q, Subquery

from .models import Conversation, Message, Notification
from . import thread as thread_svc
from healthcare.models import OrganismeDeSante
from cart.models import Cart


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
        org_name = org.name if org else (conv.prestataire.display_name or "Structure")
        return f"Secrétariat de {org_name}"
    if msg.sender_id == conv.patient_id:
        return conv.patient.display_name or "Patient"
    return "MedCare"


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


@login_required
def inbox(request):
    if request.user.is_patient or request.user.is_prestataire:
        from medcare_connect.views import react_app

        return react_app(request)
    if request.user.is_staff or request.user.is_superuser:
        return redirect("dashboard:messaging_overview")
    return redirect("users:profile")


@require_GET
def patient_inbox_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse(
            {"error": "Cette page est réservée aux patients."},
            status=403,
        )

    latest_message = Message.objects.filter(
        conversation_id=OuterRef("pk")
    ).order_by("-timestamp", "-pk")
    conversations = (
        Conversation.objects.filter(patient=request.user)
        .select_related(
            "patient",
            "prestataire",
            "devis_part__organisme",
            "rendez_vous__organisme",
        )
        .annotate(
            latest_message_content=Subquery(latest_message.values("content")[:1]),
            unread_count=Count(
                "messages",
                filter=Q(
                    messages__is_read=False,
                    messages__sender_id=F("prestataire_id"),
                ),
                distinct=True,
            ),
        )
        .order_by("-updated_at")[:100]
    )

    entries = []
    for conversation in conversations:
        organization = conversation.organisme
        badge_class, badge_label = conversation.status_badge
        entries.append(
            {
                "id": conversation.pk,
                "organization": (
                    f"Secrétariat de {organization.name}"
                    if organization
                    else conversation.prestataire.display_name or "Secrétariat médical"
                ),
                "initial": (
                    organization.name[0].upper()
                    if organization and organization.name
                    else (conversation.prestataire.display_name or "S")[0].upper()
                ),
                "subject": conversation.dossier_label,
                "preview": conversation.latest_message_content or "",
                "updated_at": conversation.updated_at.isoformat(),
                "status": badge_label,
                "status_class": badge_class,
                "unread_count": conversation.unread_count,
                "url": reverse("messaging:conversation_detail", args=[conversation.pk]),
            }
        )
    return JsonResponse({"conversations": entries})


@require_GET
def messaging_session_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if request.user.is_patient:
        return JsonResponse({"role": "patient"})
    if request.user.is_prestataire:
        return JsonResponse({"role": "provider"})
    return JsonResponse({"error": "Cette page est réservée aux patients et prestataires."}, status=403)


@require_GET
def provider_inbox_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_prestataire:
        return JsonResponse({"error": "Cette page est réservée aux prestataires."}, status=403)

    latest_message = Message.objects.filter(
        conversation_id=OuterRef("pk")
    ).order_by("-timestamp", "-pk")
    conversations = (
        Conversation.objects.filter(prestataire=request.user)
        .select_related("patient", "devis_part__organisme", "rendez_vous__organisme")
        .annotate(
            latest_message_content=Subquery(latest_message.values("content")[:1]),
            unread_count=Count(
                "messages",
                filter=Q(
                    messages__is_read=False,
                    messages__sender_id=F("patient_id"),
                ),
                distinct=True,
            ),
        )
        .order_by("-updated_at")[:100]
    )

    entries = []
    for conversation in conversations:
        badge_class, badge_label = conversation.status_badge
        patient_name = conversation.patient.display_name or "Patient"
        entries.append(
            {
                "id": conversation.pk,
                "patient": patient_name,
                "initial": patient_name[0].upper(),
                "subject": conversation.dossier_label,
                "preview": conversation.latest_message_content or "",
                "updated_at": conversation.updated_at.isoformat(),
                "status": badge_label,
                "status_class": badge_class,
                "unread_count": conversation.unread_count,
                "url": reverse("messaging:conversation_detail", args=[conversation.pk]),
            }
        )
    return JsonResponse({"conversations": entries})


@require_http_methods(["GET", "POST"])
def patient_conversation_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse({"error": "Cette page est réservée aux patients."}, status=403)

    conversation = (
        Conversation.objects.select_related(
            "patient",
            "prestataire",
            "devis_part__organisme",
            "rendez_vous__organisme",
        )
        .filter(pk=pk, patient=request.user)
        .first()
    )
    if not conversation:
        return JsonResponse({"error": "Conversation introuvable."}, status=404)

    if request.method == "POST":
        if conversation.thread_status == Conversation.STATUS_CLOSED:
            return JsonResponse({"error": "Cette conversation est clôturée."}, status=409)
        content = (request.POST.get("content") or "").strip()
        attachment = request.FILES.get("attachment")
        if not content and not attachment:
            return JsonResponse({"error": "Écrivez un message ou joignez un fichier."}, status=400)
        if content and not attachment and (
            conversation.kind != Conversation.KIND_GENERAL
            and conversation.devis_part_id
        ):
            return JsonResponse(
                {
                    "error": (
                        "Les messages libres ne sont pas disponibles dans ce fil. "
                        "Utilisez la prise de rendez-vous ou joignez un document."
                    )
                },
                status=400,
            )
        thread_svc.append_patient(
            conversation,
            content or "Pièce jointe",
            attachment=attachment,
        )
        return JsonResponse({"ok": True})

    conversation.messages.filter(
        receiver=request.user,
        is_read=False,
    ).update(is_read=True)
    messages = _thread_display_messages(
        conversation,
        conversation.messages.select_related("sender").order_by("timestamp", "pk"),
    )
    timeline = []
    current_day = None
    skip_day = (
        timezone.localtime(conversation.created_at).date()
        if conversation.devis_part_id
        else None
    )
    for message in messages:
        local_timestamp = timezone.localtime(message.timestamp)
        day = local_timestamp.date()
        if day != current_day:
            if not (skip_day and current_day is None and day == skip_day):
                timeline.append(
                    {
                        "kind": "date",
                        "label": _date_separator_label(message.timestamp),
                    }
                )
            current_day = day
        timeline.append(
            {
                "kind": "message",
                "id": message.pk,
                "content": message.content,
                "message_type": message.message_type,
                "payload": message.payload or {},
                "timestamp": message.timestamp.isoformat(),
                "time_label": timezone.localtime(message.timestamp).strftime("%H:%M"),
                "sender": _thread_sender_label(message, conversation),
                "from_patient": message.sender_id == conversation.patient_id,
                "attachment_url": message.attachment.url if message.attachment else None,
                "attachment_name": (
                    message.attachment.name.rsplit("/", 1)[-1]
                    if message.attachment
                    else None
                ),
            }
        )

    thread_context = _thread_context(request, conversation)

    organization = thread_context["thread_org"]
    status_banner = thread_context["status_banner"]
    part = conversation.devis_part
    devis = None
    if part:
        devis = {
            "reference": part.reference,
            "organization": organization.name if organization else "",
            "city": organization.city if organization else "",
            "quartier": organization.quartier if organization else "",
            "created_at": conversation.created_at.isoformat(),
            "total_patient": str(part.total_patient or "0"),
            "lines": [],
        }
        for line in (part.details or []):
            if not isinstance(line, dict):
                continue
            try:
                quantity = max(1, int(line.get("quantity") or 1))
            except (TypeError, ValueError):
                quantity = 1
            devis["lines"].append(
                {
                    "name": line.get("acte") or "Acte médical",
                    "quantity": quantity,
                    "price": str(line.get("patient_cost") or line.get("subtotal") or "0"),
                }
            )

    book_context = thread_context["reschedule_ctx"] or thread_context["book_ctx"]
    live_rdv = _live_rdv_for_conv(conversation)
    return JsonResponse(
        {
            "conversation": {
                "id": conversation.pk,
                "organization": (
                    organization.name
                    if organization
                    else conversation.prestataire.display_name or "Secrétariat médical"
                ),
                "city": organization.city if organization else "",
                "subject": conversation.dossier_label,
                "initial": (
                    organization.name[0].upper()
                    if organization and organization.name
                    else (conversation.prestataire.display_name or "S")[0].upper()
                ),
                "status": conversation.get_thread_status_display(),
                "status_banner": status_banner,
                "closed": conversation.thread_status == Conversation.STATUS_CLOSED,
                "can_send_free_message": (
                    conversation.thread_status != Conversation.STATUS_CLOSED
                    and (
                        conversation.kind == Conversation.KIND_GENERAL
                        or not conversation.devis_part_id
                    )
                ),
                "can_attach": conversation.thread_status != Conversation.STATUS_CLOSED,
                "has_live_rdv": live_rdv is not None,
                "can_book": bool(part and not live_rdv),
                "can_reschedule": bool(
                    live_rdv
                    and live_rdv.status == "requested"
                ),
                "can_cancel": bool(live_rdv),
                "rdv_reference": live_rdv.reference if live_rdv else None,
                "show_book": thread_context["show_book"],
                "show_reschedule": thread_context["show_reschedule"],
                "has_slots": bool(book_context and book_context["has_slots"]),
                "booking_data": (
                    json.loads(book_context["book_data_json"])
                    if book_context
                    else None
                ),
                "booking_url": (
                    reverse(
                        "appointments:patient_reschedule",
                        args=[live_rdv.reference],
                    )
                    if thread_context["show_reschedule"] and live_rdv
                    else (
                        reverse("appointments:patient_book", args=[part.reference])
                        if part
                        else None
                    )
                ),
                "cancel_url": (
                    reverse("appointments:patient_cancel", args=[live_rdv.reference])
                    if live_rdv
                    else None
                ),
                "url": reverse("messaging:conversation_detail", args=[conversation.pk]),
            },
            "devis": devis,
            "timeline": timeline,
        }
    )


@require_http_methods(["GET", "POST"])
def provider_conversation_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_prestataire:
        return JsonResponse({"error": "Cette page est réservée aux prestataires."}, status=403)

    conversation = (
        Conversation.objects.select_related(
            "patient",
            "prestataire",
            "devis_part__organisme",
            "devis_part__devis",
            "rendez_vous__organisme",
        )
        .filter(pk=pk, prestataire=request.user)
        .first()
    )
    if not conversation:
        return JsonResponse({"error": "Conversation introuvable."}, status=404)

    if request.method == "POST":
        if conversation.thread_status == Conversation.STATUS_CLOSED:
            return JsonResponse({"error": "Cette conversation est clôturée."}, status=409)
        content = (request.POST.get("content") or "").strip()
        attachment = request.FILES.get("attachment")
        if not content and not attachment:
            return JsonResponse({"error": "Écrivez un message ou joignez un fichier."}, status=400)
        thread_svc.append_prestataire(
            conversation,
            content or "Pièce jointe",
            attachment=attachment,
        )
        return JsonResponse({"ok": True})

    conversation.messages.filter(
        receiver=request.user,
        is_read=False,
    ).update(is_read=True)
    displayed_messages = _thread_display_messages(
        conversation,
        conversation.messages.select_related("sender").order_by("timestamp", "pk"),
    )
    timeline = []
    current_day = None
    for message in displayed_messages:
        local_timestamp = timezone.localtime(message.timestamp)
        day = local_timestamp.date()
        if day != current_day:
            timeline.append({"kind": "date", "label": _date_separator_label(message.timestamp)})
            current_day = day
        timeline.append(
            {
                "kind": "message",
                "id": message.pk,
                "content": message.content,
                "message_type": message.message_type,
                "payload": message.payload or {},
                "timestamp": message.timestamp.isoformat(),
                "time_label": local_timestamp.strftime("%H:%M"),
                "sender": _thread_sender_label(message, conversation),
                "from_patient": message.sender_id == conversation.patient_id,
                "attachment_url": message.attachment.url if message.attachment else None,
                "attachment_name": (
                    message.attachment.name.rsplit("/", 1)[-1]
                    if message.attachment
                    else None
                ),
            }
        )

    thread_context = _thread_context(request, conversation)
    organization = thread_context["thread_org"]
    display_name = conversation.patient.display_name or "Patient"
    part = conversation.devis_part
    devis = None
    if part:
        devis_lines = []
        for line in (part.details or []):
            if not isinstance(line, dict):
                continue
            try:
                quantity = max(1, int(line.get("quantity") or 1))
            except (TypeError, ValueError):
                quantity = 1
            devis_lines.append(
                {
                    "name": line.get("acte") or "Acte médical",
                    "quantity": quantity,
                    "price": str(
                        line.get("patient_cost") or line.get("subtotal") or "0"
                    ),
                }
            )
        devis = {
            "reference": part.reference,
            "organization": organization.name if organization else "",
            "city": organization.city if organization else "",
            "quartier": organization.quartier if organization else "",
            "created_at": conversation.created_at.isoformat(),
            "total_patient": str(part.total_patient or "0"),
            "lines": devis_lines,
        }

    return JsonResponse(
        {
            "conversation": {
                "id": conversation.pk,
                "patient": display_name,
                "patient_initial": display_name[0].upper(),
                "organization": organization.name if organization else "",
                "city": organization.city if organization else "",
                "subject": conversation.dossier_label,
                "status": conversation.get_thread_status_display(),
                "status_banner": thread_context["status_banner"],
                "closed": conversation.thread_status == Conversation.STATUS_CLOSED,
                "allow_reply": thread_context["allow_reply"],
                "actions": [
                    {
                        "label": action["label"],
                        "url": action["url"],
                        "method": action["method"],
                        "style": action.get("style", "muted"),
                        "confirm": action.get("confirm", ""),
                        "hidden": action.get("hidden", {}),
                    }
                    for action in thread_context["thread_actions"]
                ],
                "url": reverse("messaging:conversation_detail", args=[conversation.pk]),
            },
            "devis": devis,
            "timeline": timeline,
        }
    )


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

    if request.method == "GET" and (
        request.user.is_patient or request.user.is_prestataire
    ):
        from medcare_connect.views import react_app

        return react_app(request)

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
                if conv.kind == Conversation.KIND_GENERAL or not conv.devis_part_id:
                    thread_svc.append_patient(conv, content)
                else:
                    django_messages.warning(
                        request,
                        "Les messages libres ne sont pas disponibles — utilisez la prise de rendez-vous ou joignez un document.",
                    )
            elif request.user == conv.prestataire:
                thread_svc.append_prestataire(conv, content)
        return redirect("messaging:conversation_detail", pk=conv.pk)

    from medcare_connect.views import react_app

    return react_app(request)


@login_required
def start_conversation(request, slug):
    org = get_object_or_404(OrganismeDeSante, slug=slug, is_active=True,
                            user__is_active=True, user__user_type="prestataire")
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
    org = get_object_or_404(OrganismeDeSante, slug=slug, is_active=True,
                            user__is_active=True, user__user_type="prestataire")
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
        link=f"/sante/{org.slug}/",
    )

    return redirect(wa_url)


@login_required
def notifications_list(request):
    if request.user.is_patient or request.user.is_prestataire:
        from medcare_connect.views import react_app

        return react_app(request)
    if request.user.is_staff or request.user.is_superuser:
        return redirect("dashboard:activite_overview")
    return redirect("users:profile")


@login_required
def rappels_list(request):
    if not getattr(request.user, "is_patient", False):
        return redirect("messaging:notifications")
    from medcare_connect.views import react_app

    return react_app(request)


@require_http_methods(["GET", "POST"])
def patient_notifications_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse(
            {"error": "Cette page est réservée aux patients."}, status=403
        )

    scope = (request.GET.get("scope") if request.method == "GET" else request.POST.get("scope")) or "inbox"
    if scope not in {"inbox", "rappels"}:
        return JsonResponse({"error": "Type de notifications invalide."}, status=400)

    queryset = (
        Notification.queryset_rappels(request.user)
        if scope == "rappels"
        else Notification.queryset_inbox(request.user)
    )
    if scope == "rappels" and request.method == "GET":
        queryset = queryset.exclude(title__icontains="confirmé").exclude(
            title__icontains="devis"
        )

    if request.method == "POST":
        updated = queryset.filter(is_read=False).update(is_read=True)
        return JsonResponse({"ok": True, "updated": updated})

    notifications = [
        {
            "id": notification.pk,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "content": notification.content or "",
            "link": notification.link or "",
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
            "bell_cta": notification.bell_cta,
        }
        for notification in queryset.order_by("-created_at")[:50]
    ]
    return JsonResponse({"notifications": notifications})


@require_http_methods(["GET", "POST"])
def provider_notifications_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_prestataire:
        return JsonResponse({"error": "Cette page est réservée aux prestataires."}, status=403)

    queryset = Notification.queryset_inbox(request.user)
    if request.method == "POST":
        updated = queryset.filter(is_read=False).update(is_read=True)
        return JsonResponse({"ok": True, "updated": updated})

    notifications = [
        {
            "id": notification.pk,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "content": notification.content or "",
            "link": notification.link or "",
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
            "bell_cta": notification.bell_cta,
        }
        for notification in queryset.order_by("-created_at")[:50]
    ]
    return JsonResponse({"notifications": notifications})


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
