import json
from datetime import timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse, QueryDict
from django.utils import timezone

from appointments.models import RdvReminderSchedule, RendezVous
from cart.models import Devis
from healthcare.models import ActeMedical
from messaging.models import Conversation, Message

from .forms import RdvReminderScheduleForm


def _error(message, status):
    return JsonResponse({"error": message}, status=status)


def _admin_error(request):
    user = request.user
    if not user.is_authenticated:
        return _error("Authentification requise.", 401)
    if not user.is_active or not (user.is_superuser or user.is_admin_user):
        return _error("Accès réservé aux administrateurs.", 403)
    return None


def _method_error(allowed):
    response = _error("Méthode HTTP non autorisée.", 405)
    response["Allow"] = ", ".join(allowed)
    return response


def _page_data(page):
    return {
        "page": page.number,
        "pages": page.paginator.num_pages,
        "total": page.paginator.count,
        "has_previous": page.has_previous(),
        "has_next": page.has_next(),
    }


def _json_body(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, _error("Corps JSON invalide.", 400)
    if not isinstance(payload, dict):
        return None, _error("Le corps JSON doit être un objet.", 400)
    return payload, None


def _number(value):
    return float(value) if isinstance(value, Decimal) else value


def _user_data(user):
    if user is None:
        return None
    return {
        "id": user.pk,
        "username": user.username,
        "name": user.display_name,
        "email": user.email,
    }


def _quote_data(devis, include_parts=False):
    data = {
        "reference": devis.reference,
        "patient": _user_data(devis.patient),
        "insurance": (
            {"id": devis.insurance_id, "name": devis.insurance.name}
            if devis.insurance_id else None
        ),
        "status": devis.status,
        "status_label": devis.get_status_display(),
        "total_brut": _number(devis.total_brut),
        "total_assurance": _number(devis.total_assurance),
        "total_patient": _number(devis.total_patient),
        "details": devis.details or [],
        "notes": devis.notes or "",
        "created_at": devis.created_at.isoformat(),
        "valid_until": devis.valid_until.isoformat() if devis.valid_until else None,
        "relance_count": devis.relance_count,
        "max_relances": devis.MAX_RELANCES,
        "can_relance": devis.can_relance(),
        "is_archived": devis.is_archived,
        "archived_at": devis.archived_at.isoformat() if devis.archived_at else None,
    }
    if not include_parts:
        return data

    parts = []
    for part in devis.parts.all():
        conversation = Conversation.objects.filter(devis_part=part).first()
        rdv = RendezVous.objects.filter(devis_part=part).order_by("-created_at").first()
        parts.append({
            "id": part.pk,
            "reference": part.reference,
            "organization": {"id": part.organisme_id, "name": part.organisme.name},
            "status": part.status,
            "status_label": part.get_status_display(),
            "total_brut": _number(part.total_brut),
            "relance_count": part.relance_count,
            "can_relance": part.can_relance(),
            "is_archived": part.is_archived,
            "conversation": (
                {"id": conversation.pk, "label": conversation.dossier_label}
                if conversation else None
            ),
            "appointment": (
                {"reference": rdv.reference}
                if rdv else None
            ),
        })
    data["parts"] = parts
    return data


def _activity_kpis():
    now = timezone.now()
    since_7d = now - timedelta(days=7)
    devis = Devis.objects.exclude(status="draft")
    rdv = RendezVous.objects.all()
    conversations = Conversation.objects.all()
    return {
        "quotes_total": devis.count(),
        "quotes_pending": devis.filter(status__in=("sent", "viewed")).count(),
        "quotes_expired": devis.filter(status="expired").count(),
        "quotes_value": _number(devis.aggregate(total=Sum("total_brut"))["total"] or 0),
        "appointments_total": rdv.count(),
        "appointments_requested": rdv.filter(status=RendezVous.STATUS_REQUESTED).count(),
        "appointments_confirmed_upcoming": rdv.filter(
            status=RendezVous.STATUS_CONFIRMED, start__gte=now
        ).count(),
        "appointments_completed_7d": rdv.filter(
            status=RendezVous.STATUS_COMPLETED, updated_at__gte=since_7d
        ).count(),
        "appointments_no_show": rdv.filter(status=RendezVous.STATUS_NO_SHOW).count(),
        "conversations_total": conversations.count(),
        "conversations_active": conversations.filter(
            thread_status=Conversation.STATUS_ACTIVE
        ).count(),
        "conversations_waiting": conversations.filter(
            thread_status=Conversation.STATUS_WAITING
        ).count(),
        "conversations_quotes": conversations.filter(kind=Conversation.KIND_DEVIS).count(),
        "conversations_appointments": conversations.filter(kind=Conversation.KIND_RDV).count(),
        "messages_7d": Message.objects.filter(timestamp__gte=since_7d).count(),
    }


def _quote_organizations(devis):
    names = []
    if devis.cart_id:
        for item in devis.cart.items.select_related("prestataire_acte__organisme"):
            if item.prestataire_acte and item.prestataire_acte.organisme:
                name = item.prestataire_acte.organisme.name
                if name not in names:
                    names.append(name)
    return names


def _appointment_data(rdv, include_detail=False):
    data = {
        "reference": rdv.reference,
        "patient": _user_data(rdv.patient),
        "patient_label": rdv.patient_label,
        "patient_phone": rdv.patient_phone,
        "organization": {"id": rdv.organisme_id, "name": rdv.organisme.name},
        "devis_reference": rdv.devis.reference if rdv.devis_id else None,
        "devis_part_reference": rdv.devis_part.reference if rdv.devis_part_id else None,
        "start": rdv.start.isoformat(),
        "end": rdv.end.isoformat() if rdv.end else None,
        "source": rdv.source,
        "source_label": rdv.get_source_display(),
        "status": rdv.status,
        "status_label": rdv.get_status_display(),
        "total_brut": _number(rdv.total_brut),
        "total_patient": _number(rdv.total_patient),
        "created_at": rdv.created_at.isoformat(),
    }
    if include_detail:
        conversation = Conversation.objects.filter(rendez_vous=rdv).select_related(
            "patient", "prestataire"
        ).first()
        if not conversation and rdv.devis_part_id:
            conversation = Conversation.objects.filter(
                devis_part=rdv.devis_part
            ).select_related("patient", "prestataire").first()
        data.update({
            "confirmed_at": rdv.confirmed_at.isoformat() if rdv.confirmed_at else None,
            "patient_note": rdv.patient_note,
            "prestataire_note": rdv.prestataire_note,
            "cancel_reason": rdv.cancel_reason,
            "actes_snapshot": rdv.actes_snapshot or [],
            "prerequisites": rdv.get_prerequisites_display(),
            "conversation": (
                {"id": conversation.pk, "label": conversation.dossier_label}
                if conversation else None
            ),
        })
    return data


def _schedule_data(schedule):
    acts = list(schedule.actes.all())
    return {
        "id": schedule.pk,
        "label": schedule.label,
        "offset_value": schedule.offset_value,
        "offset_unit": schedule.offset_unit,
        "offset_unit_label": schedule.get_offset_unit_display(),
        "offset_display": schedule.offset_display,
        "tolerance_minutes": schedule.tolerance_minutes,
        "include_prerequisites": schedule.include_prerequisites,
        "is_active": schedule.is_active,
        "order": schedule.order,
        "actes": [{"id": act.pk, "name": act.name} for act in acts],
        "sent_count": schedule.sent_logs.count(),
    }


def _conversation_data(conversation, include_last=True):
    last_message = (
        conversation.messages.select_related("sender").order_by("-timestamp").first()
        if include_last else None
    )
    data = {
        "id": conversation.pk,
        "label": conversation.dossier_label,
        "subject": conversation.subject or "",
        "patient": _user_data(conversation.patient),
        "prestataire": _user_data(conversation.prestataire),
        "organization": (
            {"id": conversation.organisme.pk, "name": conversation.organisme.name}
            if conversation.organisme else None
        ),
        "kind": conversation.kind,
        "kind_label": conversation.get_kind_display(),
        "status": conversation.thread_status,
        "status_label": conversation.get_thread_status_display(),
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "message_count": conversation.messages.count(),
        "devis_part_reference": (
            conversation.devis_part.reference if conversation.devis_part_id else None
        ),
        "devis_reference": (
            conversation.devis_part.devis.reference
            if conversation.devis_part_id and conversation.devis_part.devis_id else None
        ),
        "appointment_reference": (
            conversation.rendez_vous.reference if conversation.rendez_vous_id else None
        ),
    }
    if last_message:
        data["last_message"] = {
            "content": last_message.content,
            "timestamp": last_message.timestamp.isoformat(),
        }
    else:
        data["last_message"] = None
    return data


def activity_overview_api(request):
    denied = _admin_error(request)
    if denied:
        return denied
    if request.method != "GET":
        return _method_error(["GET"])
    quotes = Devis.objects.exclude(status="draft").select_related("patient").order_by("-created_at")[:6]
    appointments = RendezVous.objects.select_related("patient", "organisme", "devis").order_by("-created_at")[:6]
    conversations = Conversation.objects.select_related(
        "patient", "prestataire", "devis_part", "rendez_vous"
    ).order_by("-updated_at")[:6]
    return JsonResponse({
        "kpis": _activity_kpis(),
        "recent_quotes": [_quote_data(item) for item in quotes],
        "recent_appointments": [_appointment_data(item) for item in appointments],
        "recent_conversations": [_conversation_data(item, include_last=False) for item in conversations],
    })


def quotes_api(request):
    denied = _admin_error(request)
    if denied:
        return denied
    if request.method != "GET":
        return _method_error(["GET"])
    status_filter = (request.GET.get("status") or "all").strip()
    valid = {"all", "sent", "viewed", "relanced", "expired", "archived"}
    if status_filter not in valid:
        status_filter = "all"
    search = (request.GET.get("q") or "").strip()
    base = Devis.objects.exclude(status="draft")
    queryset = base.select_related("patient", "insurance", "cart").annotate(
        parts_count=Count("parts", distinct=True)
    ).order_by("-created_at")
    if status_filter != "all":
        queryset = queryset.filter(status=status_filter)
    if search:
        queryset = queryset.filter(
            Q(reference__icontains=search)
            | Q(patient__username__icontains=search)
            | Q(patient__email__icontains=search)
            | Q(patient__first_name__icontains=search)
            | Q(patient__last_name__icontains=search)
        )
    page = Paginator(queryset, 25).get_page(request.GET.get("page"))
    counts = {"all": base.count()}
    for status in ("sent", "viewed", "relanced", "expired", "archived"):
        counts[status] = base.filter(status=status).count()
    return JsonResponse({
        "rows": [
            {
                **_quote_data(item),
                "organizations": _quote_organizations(item),
                "parts_count": item.parts_count,
            }
            for item in page.object_list
        ],
        "pagination": _page_data(page),
        "filters": {"status": status_filter, "q": search},
        "counts": counts,
        "kpis": {
            "total": counts["all"],
            "consulted": counts["viewed"],
            "pending": base.filter(status__in=("sent", "viewed")).count(),
            "expired": counts["expired"],
            "value": _number(base.aggregate(total=Sum("total_brut"))["total"] or 0),
        },
    })


def quote_detail_api(request, reference):
    denied = _admin_error(request)
    if denied:
        return denied
    if request.method != "GET":
        return _method_error(["GET"])
    devis = Devis.objects.select_related("patient", "insurance", "cart").prefetch_related(
        "parts__organisme"
    ).filter(reference=reference).first()
    if devis is None:
        return _error("Devis introuvable.", 404)
    return JsonResponse({"quote": _quote_data(devis, include_parts=True)})


def quote_action_api(request, reference, action):
    denied = _admin_error(request)
    if denied:
        return denied
    if request.method != "POST":
        return _method_error(["POST"])
    if action not in ("relance", "archive"):
        return _error("Action inconnue.", 404)
    devis = Devis.objects.prefetch_related("parts").filter(reference=reference).first()
    if devis is None:
        return _error("Devis introuvable.", 404)
    if action == "relance":
        parts = list(devis.parts.all())
        if parts:
            relanced = 0
            for part in parts:
                if part.can_relance():
                    part.mark_relance(by_user=request.user)
                    relanced += 1
            message = (
                f"{relanced} sous-devis relancé(s) pour le devis {devis.reference}."
                if relanced else f"Aucun sous-devis relançable pour {devis.reference}."
            )
        elif not devis.can_relance():
            message = (
                f"Devis {devis.reference} déjà archivé."
                if devis.is_archived else f"Devis {devis.reference} : relances épuisées."
            )
        else:
            devis.mark_relance(by_user=request.user)
            message = (
                f"Devis {devis.reference} relancé "
                f"({devis.relance_count}/{devis.MAX_RELANCES})."
            )
            if devis.is_archived:
                message += " Archivage automatique appliqué."
    else:
        if devis.is_archived:
            message = f"Devis {devis.reference} déjà archivé."
        else:
            with transaction.atomic():
                for part in devis.parts.all():
                    if not part.is_archived:
                        part.archive(reason="Archivé par admin")
                devis.archive(reason="Archivé par admin")
            message = f"Devis {devis.reference} et sous-devis archivés."
    devis.refresh_from_db()
    return JsonResponse({"message": message, "quote": _quote_data(devis)})


def appointments_api(request):
    denied = _admin_error(request)
    if denied:
        return denied
    if request.method != "GET":
        return _method_error(["GET"])
    status_filter = (request.GET.get("status") or "all").strip()
    valid = {
        "all", RendezVous.STATUS_REQUESTED, RendezVous.STATUS_CONFIRMED,
        RendezVous.STATUS_COMPLETED, RendezVous.STATUS_DECLINED,
        RendezVous.STATUS_CANCELLED, RendezVous.STATUS_NO_SHOW, "upcoming",
    }
    if status_filter not in valid:
        status_filter = "all"
    search = (request.GET.get("q") or "").strip()
    org_filter = (request.GET.get("org") or "").strip()
    now = timezone.now()
    queryset = RendezVous.objects.select_related(
        "patient", "organisme", "devis", "devis_part"
    ).order_by("-start")
    if status_filter == "upcoming":
        queryset = queryset.filter(status__in=RendezVous.LIVE_STATUSES, start__gte=now)
    elif status_filter != "all":
        queryset = queryset.filter(status=status_filter)
    if search:
        queryset = queryset.filter(
            Q(reference__icontains=search)
            | Q(walk_in_name__icontains=search)
            | Q(walk_in_phone__icontains=search)
            | Q(patient__username__icontains=search)
            | Q(patient__email__icontains=search)
            | Q(patient__first_name__icontains=search)
            | Q(patient__last_name__icontains=search)
            | Q(devis__reference__icontains=search)
        )
    if org_filter.isdigit():
        queryset = queryset.filter(organisme_id=int(org_filter))
    base = RendezVous.objects.all()
    counts = {
        "all": base.count(),
        "requested": base.filter(status=RendezVous.STATUS_REQUESTED).count(),
        "confirmed": base.filter(status=RendezVous.STATUS_CONFIRMED).count(),
        "upcoming": base.filter(status__in=RendezVous.LIVE_STATUSES, start__gte=now).count(),
        "completed": base.filter(status=RendezVous.STATUS_COMPLETED).count(),
        "no_show": base.filter(status=RendezVous.STATUS_NO_SHOW).count(),
        "cancelled": base.filter(status=RendezVous.STATUS_CANCELLED).count(),
        "declined": base.filter(status=RendezVous.STATUS_DECLINED).count(),
    }
    page = Paginator(queryset, 25).get_page(request.GET.get("page"))
    return JsonResponse({
        "rows": [_appointment_data(item) for item in page.object_list],
        "pagination": _page_data(page),
        "filters": {"status": status_filter, "q": search, "org": org_filter},
        "counts": counts,
        "kpis": _activity_kpis(),
    })


def appointment_detail_api(request, reference):
    denied = _admin_error(request)
    if denied:
        return denied
    if request.method != "GET":
        return _method_error(["GET"])
    rdv = RendezVous.objects.select_related(
        "patient", "organisme", "devis", "devis_part"
    ).filter(reference=reference).first()
    if rdv is None:
        return _error("Rendez-vous introuvable.", 404)
    return JsonResponse({"appointment": _appointment_data(rdv, include_detail=True)})


def reminder_schedules_api(request):
    denied = _admin_error(request)
    if denied:
        return denied
    global_schedules = RdvReminderSchedule.objects.filter(
        organisme__isnull=True
    ).prefetch_related("actes").annotate(
        sent_count=Count("sent_logs")
    ).order_by("order", "-offset_value")
    if request.method == "GET":
        return JsonResponse({
            "rows": [_schedule_data(item) for item in global_schedules],
            "act_options": [
                {
                    "id": act.pk,
                    "name": (
                        f"{act.service_medical_category.name} › {act.name}"
                        if act.service_medical_category_id else act.name
                    ),
                }
                for act in ActeMedical.objects.filter(is_active=True, level=3)
                .select_related("service_medical_category")
                .order_by("service_medical_category__order", "service_medical_category__name", "name")
            ],
        })
    if request.method != "POST":
        return _method_error(["GET", "POST"])
    payload, error = _json_body(request)
    if error:
        return error
    form = _reminder_form(payload)
    if not form.is_valid():
        return _form_error(form)
    with transaction.atomic():
        schedule = form.save(commit=False)
        schedule.organisme = None
        schedule.save()
        form.save_m2m()
    return JsonResponse({"schedule": _schedule_data(schedule)}, status=201)


def reminder_schedule_detail_api(request, pk):
    denied = _admin_error(request)
    if denied:
        return denied
    schedule = RdvReminderSchedule.objects.filter(
        pk=pk, organisme__isnull=True
    ).prefetch_related("actes").first()
    if schedule is None:
        return _error("Règle de rappel globale introuvable.", 404)
    if request.method == "GET":
        return JsonResponse({"schedule": _schedule_data(schedule)})
    if request.method == "DELETE":
        label = schedule.label
        schedule.delete()
        return JsonResponse({"message": f"Règle « {label} » supprimée."})
    if request.method not in ("PUT", "PATCH"):
        return _method_error(["GET", "PUT", "PATCH", "DELETE"])
    payload, error = _json_body(request)
    if error:
        return error
    form = _reminder_form(payload, instance=schedule)
    if not form.is_valid():
        return _form_error(form)
    updated = form.save(commit=False)
    updated.organisme = None
    updated.save()
    form.save_m2m()
    return JsonResponse({"schedule": _schedule_data(updated)})


def _reminder_form(payload, instance=None):
    data = QueryDict("", mutable=True)
    for key, value in payload.items():
        if key == "actes":
            if not isinstance(value, list):
                value = []
            data.setlist("actes", [str(item) for item in value])
        elif isinstance(value, bool):
            data[key] = "true" if value else "false"
        elif value is not None:
            data[key] = str(value)
    return RdvReminderScheduleForm(data=data, instance=instance)


def _form_error(form):
    errors = {
        field: [str(message) for message in messages]
        for field, messages in form.errors.items()
    }
    return JsonResponse({
        "error": "Vérifiez les champs du formulaire.",
        "errors": errors,
    }, status=400)


def messaging_api(request):
    denied = _admin_error(request)
    if denied:
        return denied
    if request.method != "GET":
        return _method_error(["GET"])
    kind_filter = (request.GET.get("kind") or "all").strip()
    status_filter = (request.GET.get("status") or "all").strip()
    if kind_filter not in {"all", Conversation.KIND_GENERAL, Conversation.KIND_DEVIS, Conversation.KIND_RDV}:
        kind_filter = "all"
    if status_filter not in {"all", Conversation.STATUS_ACTIVE, Conversation.STATUS_WAITING, Conversation.STATUS_CLOSED}:
        status_filter = "all"
    search = (request.GET.get("q") or "").strip()
    queryset = Conversation.objects.select_related(
        "patient", "prestataire", "devis_part__organisme",
        "devis_part__devis", "rendez_vous__organisme",
    ).annotate(msg_count=Count("messages")).order_by("-updated_at")
    if kind_filter != "all":
        queryset = queryset.filter(kind=kind_filter)
    if status_filter != "all":
        queryset = queryset.filter(thread_status=status_filter)
    if search:
        queryset = queryset.filter(
            Q(subject__icontains=search)
            | Q(patient__username__icontains=search)
            | Q(patient__email__icontains=search)
            | Q(patient__first_name__icontains=search)
            | Q(patient__last_name__icontains=search)
            | Q(prestataire__username__icontains=search)
            | Q(devis_part__reference__icontains=search)
            | Q(rendez_vous__reference__icontains=search)
        )
    base = Conversation.objects.all()
    counts = {
        "all": base.count(),
        "devis": base.filter(kind=Conversation.KIND_DEVIS).count(),
        "rdv": base.filter(kind=Conversation.KIND_RDV).count(),
        "general": base.filter(kind=Conversation.KIND_GENERAL).count(),
        "active": base.filter(thread_status=Conversation.STATUS_ACTIVE).count(),
        "waiting": base.filter(thread_status=Conversation.STATUS_WAITING).count(),
        "closed": base.filter(thread_status=Conversation.STATUS_CLOSED).count(),
    }
    page = Paginator(queryset, 25).get_page(request.GET.get("page"))
    rows = []
    for item in page.object_list:
        row = _conversation_data(item, include_last=False)
        last = item.messages.select_related("sender").order_by("-timestamp").first()
        row["last_message"] = (
            {"content": last.content, "timestamp": last.timestamp.isoformat()}
            if last else None
        )
        rows.append(row)
    kpis = _activity_kpis()
    return JsonResponse({
        "rows": rows,
        "pagination": _page_data(page),
        "filters": {"kind": kind_filter, "status": status_filter, "q": search},
        "counts": counts,
        "kpis": {
            "total": kpis["conversations_total"],
            "active": kpis["conversations_active"],
            "waiting": kpis["conversations_waiting"],
            "messages_7d": kpis["messages_7d"],
        },
    })


def messaging_detail_api(request, pk):
    denied = _admin_error(request)
    if denied:
        return denied
    if request.method != "GET":
        return _method_error(["GET"])
    conversation = Conversation.objects.select_related(
        "patient", "prestataire", "devis_part__organisme",
        "devis_part__devis", "rendez_vous__organisme",
    ).filter(pk=pk).first()
    if conversation is None:
        return _error("Conversation introuvable.", 404)
    messages = [
        {
            "id": message.pk,
            "sender": _user_data(message.sender),
            "sender_id": message.sender_id,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "message_type": message.message_type,
            "message_type_label": message.get_message_type_display(),
        }
        for message in conversation.messages.select_related("sender", "receiver").order_by("timestamp")
    ]
    return JsonResponse({
        "conversation": _conversation_data(conversation, include_last=False),
        "messages": messages,
    })
