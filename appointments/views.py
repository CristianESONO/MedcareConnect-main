"""Vues du module rendez-vous.

Côté patient : partials AJAX injectés dans le panneau « Mon compte » (drawer).
Côté prestataire : pages pleines dans l'espace pro (agenda).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from cart.models import DevisPart
from healthcare.models import OrganismeDeSante

from . import agenda as agenda_engine
from . import slots as slot_engine
from .models import RendezVous
from .panel import render_rdv_panel, snapshot_from_devis_part


def _thread_link(rdv):
    try:
        from messaging.thread import conversation_for_rdv, thread_url
        conv = conversation_for_rdv(rdv)
        return thread_url(conv) if conv else None
    except Exception:
        return None


def _notify(event_code, **kwargs):
    """Wrapper best-effort autour du dispatcher de notifications."""
    try:
        from notifications.dispatcher import dispatch

        dispatch(event_code, **kwargs)
    except Exception:  # pragma: no cover — ne jamais casser le flux métier
        pass


def _prestataire_reschedule_rdv(rdv, org, value):
    """Déplace un RDV actif vers un créneau valide. Retourne (ok, old_start|error)."""
    if not value or not slot_engine.is_slot_available(org, value, exclude_rdv=rdv):
        return False, "Créneau invalide ou hors horaires."
    try:
        start = datetime.fromisoformat(value)
    except ValueError:
        return False, "Créneau invalide."
    if timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.get_current_timezone())

    old_start = rdv.start
    if timezone.localtime(old_start) == timezone.localtime(start):
        return True, None

    rdv.start = start
    rdv.end = start + timedelta(minutes=rdv.slot_minutes or slot_engine.DEFAULT_SLOT_MINUTES)
    rdv.save(update_fields=["start", "end", "updated_at"])

    if rdv.patient_id:
        patient_link = _thread_link(rdv) or (reverse("healthcare:search") + "?pac=rdv")
        try:
            from messaging.thread import on_rdv_moved_by_prestataire
            on_rdv_moved_by_prestataire(rdv, old_start, "")
        except Exception:
            pass
        _notify(
            "rdv.rescheduled",
            context={
                "rdv": rdv,
                "patient": rdv.patient,
                "organisme": org,
                "old_start": old_start,
                "link": patient_link,
            },
            actor=rdv.patient,
        )
    return True, old_start


def _prestataire_rdv_redirect(request, status_filter="upcoming"):
    nxt = request.POST.get("next", "")
    if nxt.startswith("/"):
        return redirect(nxt)
    sf = request.POST.get("status") or status_filter
    return redirect(reverse("appointments:prestataire_rdv_list") + f"?status={sf}")


# ─── Patient (partials du panneau) ─────────────────────────────────────────────


@login_required
def patient_book(request, part_ref):
    """Sélecteur de créneau + création de la demande de RDV pour un sous-devis."""
    if not request.user.is_patient:
        return HttpResponseForbidden()

    part = get_object_or_404(
        DevisPart.objects.select_related("organisme", "devis"),
        reference=part_ref,
        devis__patient=request.user,
    )
    org = part.organisme

    if request.method == "POST":
        value = (request.POST.get("slot") or "").strip()
        note = (request.POST.get("note") or "").strip()
        asap = value == "asap"
        if asap:
            value = slot_engine.first_available_slot(org) or ""
        if not value or not slot_engine.is_slot_available(org, value):
            messages.error(
                request,
                "Ce créneau n'est plus disponible. Merci d'en choisir un autre.",
            )
            return _render_book(request, part, org)
        try:
            start = datetime.fromisoformat(value)
        except ValueError:
            messages.error(request, "Créneau invalide.")
            return _render_book(request, part, org)

        patient_note = (
            f"Au plus vite selon disponibilité de la structure. {note}".strip()
            if asap
            else note
        )
        lines, total_brut, total_patient = snapshot_from_devis_part(part)
        rdv = RendezVous.objects.create(
            patient=request.user,
            organisme=org,
            devis=part.devis,
            devis_part=part,
            start=start,
            slot_minutes=slot_engine.DEFAULT_SLOT_MINUTES,
            status=RendezVous.STATUS_REQUESTED,
            actes_snapshot=lines,
            total_brut=total_brut or 0,
            total_patient=total_patient or 0,
            patient_note=patient_note,
        )
        _notify(
            "rdv.requested",
            context={
                "rdv": rdv,
                "patient": request.user,
                "organisme": org,
                "devis": part.devis,
                "devis_part": part,
                "link": _thread_link(rdv) or reverse("appointments:prestataire_rdv_list"),
            },
            actor=getattr(org, "user", None),
        )
        try:
            from messaging.thread import on_rdv_requested
            on_rdv_requested(rdv, patient_note)
        except Exception:
            pass
        messages.success(
            request,
            f"Demande de RDV envoyée à {org.name}. Vous serez notifié dès la confirmation.",
        )
        return render_rdv_panel(request)

    return _render_book(request, part, org)


def _render_book(request, part, org):
    from users.patient_panel import is_panel_request

    from .panel import book_data_json

    payload, has_slots = book_data_json(org, part)
    ctx = {
        "part": part,
        "devis": part.devis,
        "org": org,
        "has_slots": has_slots,
        "book_data_json": payload,
        "slot_minutes": slot_engine.DEFAULT_SLOT_MINUTES,
        "account_active": "devis",
        "account_page_title": f"Créneau — {org.name}",
        "pac_messages": list(messages.get_messages(request)),
    }
    tpl = "appointments/patient/_book.html"
    if is_panel_request(request):
        return render(request, tpl, ctx)
    ctx["panel_partial"] = tpl
    return render(request, "users/patient_compte_page.html", ctx)


@login_required
@require_POST
def patient_cancel(request, ref):
    if not request.user.is_patient:
        return HttpResponseForbidden()
    rdv = get_object_or_404(RendezVous, reference=ref, patient=request.user)
    if rdv.status in RendezVous.LIVE_STATUSES:
        rdv.cancel(by=RendezVous.BY_PATIENT, reason=request.POST.get("reason", ""))
        _notify(
            "rdv.cancelled",
            context={
                "rdv": rdv,
                "patient": request.user,
                "organisme": rdv.organisme,
                "link": _thread_link(rdv) or reverse("appointments:prestataire_rdv_list"),
            },
            actor=getattr(rdv.organisme, "user", None),
        )
        try:
            from messaging.thread import on_rdv_event
            on_rdv_event(rdv, "cancelled", rdv.cancel_reason)
        except Exception:
            pass
        messages.success(request, "Rendez-vous annulé.")
    nxt = request.POST.get("next", "")
    if nxt.startswith("/"):
        return redirect(nxt)
    return render_rdv_panel(request)


@login_required
@require_POST
def patient_reschedule(request, ref):
    """Modification du créneau tant que le RDV est en attente de confirmation."""
    if not request.user.is_patient:
        return HttpResponseForbidden()

    rdv = get_object_or_404(
        RendezVous,
        reference=ref,
        patient=request.user,
        status=RendezVous.STATUS_REQUESTED,
    )
    org = rdv.organisme
    value = (request.POST.get("slot") or "").strip()
    note = (request.POST.get("note") or "").strip()
    asap = value == "asap"
    if asap:
        value = slot_engine.first_available_slot(org) or ""
    if not value or not slot_engine.is_slot_available(org, value, exclude_rdv=rdv):
        messages.error(request, "Ce créneau n'est plus disponible.")
        nxt = request.POST.get("next", "")
        if nxt.startswith("/"):
            return redirect(nxt)
        return redirect("messaging:inbox")

    try:
        start = datetime.fromisoformat(value)
    except ValueError:
        messages.error(request, "Créneau invalide.")
        return redirect("messaging:inbox")
    if timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.get_current_timezone())

    old_start = rdv.start
    rdv.start = start
    rdv.end = start + timedelta(minutes=rdv.slot_minutes or slot_engine.DEFAULT_SLOT_MINUTES)
    if asap:
        rdv.patient_note = f"Au plus vite selon disponibilité de la structure. {note}".strip()
    elif note:
        rdv.patient_note = note
    rdv.save(update_fields=["start", "end", "patient_note", "updated_at"])

    try:
        from messaging.thread import on_rdv_rescheduled
        on_rdv_rescheduled(rdv, old_start, rdv.patient_note if asap else note)
    except Exception:
        pass

    patient_link = _thread_link(rdv) or (reverse("healthcare:search") + "?pac=rdv")
    _notify(
        "rdv.rescheduled",
        context={
            "rdv": rdv,
            "patient": request.user,
            "organisme": org,
            "old_start": old_start,
            "link": reverse("appointments:prestataire_agenda"),
        },
        actor=getattr(org, "user", None),
    )

    messages.success(request, "Créneau modifié — en attente de confirmation.")
    nxt = request.POST.get("next", "")
    if nxt.startswith("/"):
        return redirect(nxt)
    conv = None
    try:
        from messaging.thread import conversation_for_rdv, thread_url
        conv = conversation_for_rdv(rdv)
        if conv:
            return redirect(thread_url(conv))
    except Exception:
        pass
    return render_rdv_panel(request)


# ─── Prestataire (espace pro) ──────────────────────────────────────────────────


@login_required
def prestataire_agenda(request):
    """Agenda hebdomadaire (grille calendrier) de la structure."""
    try:
        org = request.user.healthcare_provider_profile
    except OrganismeDeSante.DoesNotExist:
        return redirect("healthcare:organisme_create")

    anchor = None
    raw = request.GET.get("date")
    if raw:
        try:
            anchor = date.fromisoformat(raw)
        except ValueError:
            anchor = None
    if anchor is None:
        anchor = timezone.localdate()

    monday = agenda_engine.week_monday(anchor)
    week = agenda_engine.build_week(org, monday)
    today = timezone.localdate()

    ctx = {
        "org": org,
        "dash_active": "rdv",
        "week": week,
        "rdvs_data": week["rdvs"],
        "monday": monday,
        "sunday": monday + timedelta(days=6),
        "prev_week": (monday - timedelta(days=7)).isoformat(),
        "next_week": (monday + timedelta(days=7)).isoformat(),
        "today_iso": today.isoformat(),
        "is_current_week": monday == agenda_engine.week_monday(today),
        "new_rdv_count": RendezVous.objects.filter(
            organisme=org, status=RendezVous.STATUS_REQUESTED
        ).count(),
        "action_url_tpl": reverse("appointments:prestataire_rdv_action", args=["REF"]),
        "move_url_tpl": reverse("appointments:prestataire_rdv_move", args=["REF"]),
        "update_url_tpl": reverse("appointments:prestataire_rdv_update", args=["REF"]),
        "this_url": request.get_full_path(),
    }
    return render(request, "appointments/prestataire/agenda.html", ctx)


@login_required
@require_POST
def prestataire_rdv_create(request):
    """Saisie d'un rendez-vous « sur place » dans un créneau libre de l'agenda."""
    try:
        org = request.user.healthcare_provider_profile
    except OrganismeDeSante.DoesNotExist:
        return redirect("healthcare:organisme_create")

    value = (request.POST.get("slot") or "").strip()
    name = (request.POST.get("name") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    motif = (request.POST.get("motif") or "").strip()
    note = (request.POST.get("note") or "").strip()

    back = reverse("appointments:prestataire_agenda")
    day = request.POST.get("date")
    if day:
        back += f"?date={day}"

    if not name:
        messages.error(request, "Indiquez au moins le nom du patient.")
        return redirect(back)

    dt = agenda_engine.validate_walkin_slot(org, value)
    if not dt:
        messages.error(request, "Créneau invalide ou hors horaires d'ouverture.")
        return redirect(back)

    rdv = RendezVous.objects.create(
        organisme=org,
        source=RendezVous.SOURCE_WALK_IN,
        start=dt,
        slot_minutes=slot_engine.DEFAULT_SLOT_MINUTES,
        status=RendezVous.STATUS_CONFIRMED,
        confirmed_at=timezone.now(),
        walk_in_name=name,
        walk_in_phone=phone,
        walk_in_motif=motif,
        prestataire_note=note,
    )
    messages.success(request, f"Rendez-vous sur place ajouté pour {name} ({rdv.reference}).")
    return redirect(back)


@login_required
@require_POST
def prestataire_rdv_move(request, ref):
    """Déplace un RDV actif vers un autre créneau libre (agenda drag & drop)."""
    try:
        org = request.user.healthcare_provider_profile
    except OrganismeDeSante.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Accès refusé."}, status=403)

    rdv = get_object_or_404(RendezVous, reference=ref, organisme=org)
    if rdv.status not in RendezVous.LIVE_STATUSES:
        return JsonResponse(
            {"ok": False, "error": "Seuls les RDV à venir ou à confirmer peuvent être déplacés."},
            status=400,
        )

    value = (request.POST.get("slot") or "").strip()
    ok, result = _prestataire_reschedule_rdv(rdv, org, value)
    if not ok:
        return JsonResponse({"ok": False, "error": result}, status=400)

    return JsonResponse({
        "ok": True,
        "ref": rdv.reference,
        "when": agenda_engine._fr_when(rdv.start),
        "slot": timezone.localtime(rdv.start).isoformat(),
        "label": agenda_engine._fr_label(
            timezone.localtime(rdv.start).date(),
            timezone.localtime(rdv.start).time(),
        ),
    })


@login_required
@require_POST
def prestataire_rdv_update(request, ref):
    """Modification d'un RDV depuis la liste (créneau, infos walk-in, note interne)."""
    try:
        org = request.user.healthcare_provider_profile
    except OrganismeDeSante.DoesNotExist:
        return redirect("healthcare:organisme_create")

    rdv = get_object_or_404(RendezVous, reference=ref, organisme=org)
    if rdv.status not in RendezVous.LIVE_STATUSES:
        messages.warning(request, "Ce rendez-vous ne peut plus être modifié.")
        return _prestataire_rdv_redirect(request)

    value = (request.POST.get("slot") or "").strip()
    if value:
        ok, result = _prestataire_reschedule_rdv(rdv, org, value)
        if not ok:
            messages.error(request, result)
            return _prestataire_rdv_redirect(request)

    update_fields = []
    if rdv.is_walk_in:
        name = (request.POST.get("name") or "").strip()
        if not name:
            messages.error(request, "Indiquez le nom du patient.")
            return _prestataire_rdv_redirect(request)
        rdv.walk_in_name = name
        rdv.walk_in_phone = (request.POST.get("phone") or "").strip()
        rdv.walk_in_motif = (request.POST.get("motif") or "").strip()
        update_fields.extend(["walk_in_name", "walk_in_phone", "walk_in_motif"])

    if "note" in request.POST:
        rdv.prestataire_note = (request.POST.get("note") or "").strip()
        update_fields.append("prestataire_note")

    if update_fields:
        update_fields.append("updated_at")
        rdv.save(update_fields=update_fields)

    messages.success(request, f"RDV {rdv.reference} mis à jour.")
    return _prestataire_rdv_redirect(request)


_PRESTA_FILTERS = {
    "upcoming": "À venir",
    "requested": "À confirmer",
    "confirmed": "Confirmés",
    "past": "Passés",
    "all": "Tous",
}


@login_required
def prestataire_rdv_list(request):
    try:
        org = request.user.healthcare_provider_profile
    except OrganismeDeSante.DoesNotExist:
        return redirect("healthcare:organisme_create")

    status_filter = request.GET.get("status", "upcoming")
    if status_filter not in _PRESTA_FILTERS:
        status_filter = "upcoming"

    base = RendezVous.objects.filter(organisme=org).select_related(
        "patient", "devis", "devis_part"
    )
    now = timezone.now()
    if status_filter == "upcoming":
        qs = base.filter(status__in=RendezVous.LIVE_STATUSES, start__gte=now).order_by("start")
    elif status_filter == "requested":
        qs = base.filter(status=RendezVous.STATUS_REQUESTED).order_by("start")
    elif status_filter == "confirmed":
        qs = base.filter(status=RendezVous.STATUS_CONFIRMED).order_by("start")
    elif status_filter == "past":
        qs = base.exclude(status__in=RendezVous.LIVE_STATUSES).order_by("-start")
    else:
        qs = base.order_by("-start")

    counts = {
        "upcoming": base.filter(status__in=RendezVous.LIVE_STATUSES, start__gte=now).count(),
        "requested": base.filter(status=RendezVous.STATUS_REQUESTED).count(),
        "confirmed": base.filter(status=RendezVous.STATUS_CONFIRMED).count(),
        "past": base.exclude(status__in=RendezVous.LIVE_STATUSES).count(),
        "all": base.count(),
    }
    filter_tabs = [
        {"key": k, "label": label, "count": counts.get(k, 0)}
        for k, label in _PRESTA_FILTERS.items()
    ]

    ctx = {
        "org": org,
        "dash_active": "rdv",
        "rows": qs,
        "status_filter": status_filter,
        "filter_tabs": filter_tabs,
        "new_rdv_count": counts["requested"],
    }
    return render(request, "appointments/prestataire/rdv_list.html", ctx)


@login_required
@require_POST
def prestataire_rdv_action(request, ref):
    try:
        org = request.user.healthcare_provider_profile
    except OrganismeDeSante.DoesNotExist:
        return redirect("healthcare:organisme_create")

    rdv = get_object_or_404(RendezVous, reference=ref, organisme=org)
    action = request.POST.get("action")
    note = (request.POST.get("note") or "").strip()

    thread_link = _thread_link(rdv)
    patient_link = thread_link or (reverse("healthcare:search") + "?pac=rdv")

    if action == "confirm" and rdv.status == RendezVous.STATUS_REQUESTED:
        rdv.confirm(note=note)
        if rdv.patient_id:
            _notify(
                "rdv.confirmed",
                context={
                    "rdv": rdv, "patient": rdv.patient, "organisme": org,
                    "link": patient_link,
                },
                actor=rdv.patient,
            )
        try:
            from messaging.thread import on_rdv_event
            on_rdv_event(rdv, "confirmed", note)
        except Exception:
            pass
        messages.success(request, f"RDV {rdv.reference} confirmé.")
    elif action == "decline" and rdv.status == RendezVous.STATUS_REQUESTED:
        rdv.decline(note=note)
        if rdv.patient_id:
            _notify(
                "rdv.declined",
                context={
                    "rdv": rdv, "patient": rdv.patient, "organisme": org,
                    "link": patient_link,
                },
                actor=rdv.patient,
            )
        try:
            from messaging.thread import on_rdv_event
            on_rdv_event(rdv, "declined", note)
        except Exception:
            pass
        messages.success(request, f"RDV {rdv.reference} refusé.")
    elif action == "complete" and rdv.status in RendezVous.LIVE_STATUSES:
        rdv.mark_completed(note=note)
        try:
            from messaging.thread import on_rdv_event
            on_rdv_event(rdv, "completed", note)
        except Exception:
            pass
        messages.success(request, f"RDV {rdv.reference} marqué honoré.")
    elif action == "no_show" and rdv.status in RendezVous.LIVE_STATUSES:
        rdv.mark_no_show(note=note)
        try:
            from messaging.thread import on_rdv_event
            on_rdv_event(rdv, "no_show", note)
        except Exception:
            pass
        messages.success(request, f"RDV {rdv.reference} marqué absent.")
    elif action == "cancel" and rdv.status in RendezVous.LIVE_STATUSES:
        rdv.cancel(by=RendezVous.BY_PRESTATAIRE, reason=note)
        if rdv.patient_id:
            _notify(
                "rdv.cancelled",
                context={
                    "rdv": rdv, "patient": rdv.patient, "organisme": org,
                    "link": patient_link,
                },
                actor=rdv.patient,
            )
        try:
            from messaging.thread import on_rdv_event
            on_rdv_event(rdv, "cancelled", note)
        except Exception:
            pass
        messages.success(request, f"RDV {rdv.reference} annulé.")
    else:
        messages.warning(request, "Action impossible pour l'état actuel du RDV.")

    nxt = request.POST.get("next", "")
    if nxt.startswith("/"):
        return redirect(nxt)
    return redirect(
        reverse("appointments:prestataire_rdv_list")
        + f"?status={request.POST.get('status', 'upcoming')}"
    )
