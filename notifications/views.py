from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard.decorators import superadmin_required

from .dispatcher import _send_email, _send_whatsapp_cloud, resend_notification_log
from .forms import (
    GeneralSettingsForm,
    NotificationRuleForm,
    PatientWaMeTemplatesForm,
    SmtpSettingsForm,
    TestEmailForm,
    TestWhatsAppForm,
    WhatsAppSettingsForm,
)
from .models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationRule,
    NotificationSettings,
    NotificationTemplate,
    UserNotificationPreference,
)


# ─────────────────────────────────────────────────────────────────────────────
# Espace Admin Medcare
# ─────────────────────────────────────────────────────────────────────────────


def _admin_ctx(active="settings"):
    return {"notif_admin_active": active}


@superadmin_required
def admin_settings(request):
    """Configuration SMTP + WhatsApp Cloud + général + boutons de test."""
    obj = NotificationSettings.load()

    smtp_form = SmtpSettingsForm(instance=obj, prefix="smtp")
    wa_form = WhatsAppSettingsForm(instance=obj, prefix="wa")
    general_form = GeneralSettingsForm(instance=obj, prefix="gen")
    test_email_form = TestEmailForm(prefix="test_email")
    test_wa_form = TestWhatsAppForm(prefix="test_wa")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_smtp":
            smtp_form = SmtpSettingsForm(request.POST, instance=obj, prefix="smtp")
            if smtp_form.is_valid():
                smtp_form.save()
                messages.success(request, "Configuration SMTP enregistrée.")
                return redirect("notifications:admin_settings")
        elif action == "save_wa":
            wa_form = WhatsAppSettingsForm(request.POST, instance=obj, prefix="wa")
            if wa_form.is_valid():
                wa_form.save()
                messages.success(request, "Configuration WhatsApp Cloud enregistrée.")
                return redirect("notifications:admin_settings")
        elif action == "save_general":
            general_form = GeneralSettingsForm(request.POST, instance=obj, prefix="gen")
            if general_form.is_valid():
                general_form.save()
                messages.success(request, "Réglages généraux enregistrés.")
                return redirect("notifications:admin_settings")
        elif action == "test_email":
            test_email_form = TestEmailForm(request.POST, prefix="test_email")
            if test_email_form.is_valid():
                status, error = _send_email(
                    settings_obj=obj,
                    user=request.user,
                    address=test_email_form.cleaned_data["to_email"],
                    subject="[MedCare] Test SMTP",
                    body="Ceci est un message de test envoyé depuis l'espace admin MedCare.",
                )
                if status == NotificationLog.STATUS_SENT:
                    messages.success(request, "Email de test envoyé.")
                else:
                    messages.error(request, f"Échec test email : {error}")
                return redirect("notifications:admin_settings")
        elif action == "test_wa":
            test_wa_form = TestWhatsAppForm(request.POST, prefix="test_wa")
            if test_wa_form.is_valid():
                status, error = _send_whatsapp_cloud(
                    settings_obj=obj,
                    user=None,
                    address=test_wa_form.cleaned_data["to_number"],
                    body=test_wa_form.cleaned_data["message"],
                    context={},
                )
                if status == NotificationLog.STATUS_SENT:
                    messages.success(request, "Message WhatsApp de test envoyé.")
                else:
                    messages.error(request, f"Échec test WhatsApp : {error}")
                return redirect("notifications:admin_settings")

    ctx = _admin_ctx("settings")
    ctx.update(
        {
            "obj": obj,
            "smtp_form": smtp_form,
            "wa_form": wa_form,
            "general_form": general_form,
            "test_email_form": test_email_form,
            "test_wa_form": test_wa_form,
            "channels": NotificationChannel.objects.all(),
        }
    )
    return render(request, "notifications/admin/settings.html", ctx)


@superadmin_required
def admin_rules(request):
    """Tableau matriciel des règles : événements × canaux, lien vers édition."""
    events = NotificationEvent.objects.all().order_by("order", "label")
    channels = NotificationChannel.objects.all().order_by("order", "label")
    rules = NotificationRule.objects.select_related("event", "channel")
    rule_map = {(r.event_id, r.channel_id): r for r in rules}

    matrix = []
    for ev in events:
        row = {"event": ev, "cells": []}
        for ch in channels:
            row["cells"].append({"channel": ch, "rule": rule_map.get((ev.pk, ch.pk))})
        matrix.append(row)

    ctx = _admin_ctx("rules")
    ctx.update({"matrix": matrix, "channels": channels})
    return render(request, "notifications/admin/rules_matrix.html", ctx)


@superadmin_required
def admin_rule_edit(request, event_id: int, channel_id: int):
    event = get_object_or_404(NotificationEvent, pk=event_id)
    channel = get_object_or_404(NotificationChannel, pk=channel_id)
    rule, created = NotificationRule.objects.get_or_create(
        event=event, channel=channel, defaults={"is_active": True}
    )
    if request.method == "POST":
        form = NotificationRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, "Règle enregistrée.")
            return redirect("notifications:admin_rules")
    else:
        form = NotificationRuleForm(instance=rule)

    template = NotificationTemplate.objects.filter(event=event, channel=channel).first()

    if request.method == "POST":
        role_selected = request.POST.getlist("target_roles")
    else:
        role_selected = list(rule.target_roles or [])

    ctx = _admin_ctx("rules")
    ctx.update(
        {
            "event": event,
            "channel": channel,
            "rule": rule,
            "form": form,
            "template": template,
            "created": created,
            "role_selected": role_selected,
        }
    )
    return render(request, "notifications/admin/rule_form.html", ctx)


@superadmin_required
def admin_logs(request):
    qs = NotificationLog.objects.select_related("event", "channel", "recipient_user").order_by(
        "-created_at"
    )
    status = (request.GET.get("status") or "").strip()
    if status in ("sent", "failed", "skipped", "queued"):
        qs = qs.filter(status=status)
    channel_code = (request.GET.get("channel") or "").strip()
    if channel_code:
        qs = qs.filter(channel__code=channel_code)
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(subject__icontains=q)
            | Q(recipient_address__icontains=q)
            | Q(recipient_user__username__icontains=q)
            | Q(recipient_user__email__icontains=q)
            | Q(error__icontains=q)
        )

    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get("page"))

    counts_by_status = (
        NotificationLog.objects.values("status").annotate(n=Count("id")).order_by("status")
    )

    ctx = _admin_ctx("logs")
    ctx.update(
        {
            "page": page,
            "status_filter": status,
            "channel_filter": channel_code,
            "q": q,
            "channels": NotificationChannel.objects.all(),
            "counts_by_status": {row["status"]: row["n"] for row in counts_by_status},
        }
    )
    return render(request, "notifications/admin/logs.html", ctx)


@superadmin_required
@require_POST
def admin_log_resend(request):
    """Renvoie une notification à partir d'une ligne du journal (nouvelle entrée de log)."""
    try:
        log_id = int(request.POST.get("log_id", "0"))
    except (TypeError, ValueError):
        log_id = 0

    new_log, err = resend_notification_log(log_id)
    if new_log is None:
        messages.error(request, err or "Renvoi impossible.")
    elif new_log.status == NotificationLog.STATUS_SENT:
        messages.success(request, "Message renvoyé avec succès.")
    elif new_log.status == NotificationLog.STATUS_FAILED:
        messages.error(
            request,
            f"Échec du renvoi : {new_log.error or 'erreur inconnue'}",
        )
    else:
        messages.warning(
            request,
            f"Renvoi ignoré ou non envoyé : {new_log.error or new_log.get_status_display()}",
        )

    next_url = (request.POST.get("next") or "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("notifications:admin_logs")


@superadmin_required
def admin_templates(request):
    """Catalogue des templates d’événements (email, in-app, WhatsApp API…)."""
    templates = NotificationTemplate.objects.select_related("event", "channel").order_by(
        "event__order", "event__label", "channel__order"
    )
    ctx = _admin_ctx("templates")
    ctx.update({"templates": templates})
    return render(request, "notifications/admin/templates.html", ctx)


@superadmin_required
def admin_patient_wa_messages(request):
    """Édition des textes préremplis wa.me (fiche organisme + fiche devis), hors templates d’événements."""
    notif_settings = NotificationSettings.load()
    form = PatientWaMeTemplatesForm(instance=notif_settings)

    if request.method == "POST":
        form = PatientWaMeTemplatesForm(request.POST, instance=notif_settings)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Messages WhatsApp (wa.me) enregistrés — fiches prestataires et devis patient.",
            )
            return redirect("notifications:admin_patient_wa_messages")

    ctx = _admin_ctx("patient_whatsapp")
    ctx.update({"wa_me_form": form})
    return render(request, "notifications/admin/patient_whatsapp.html", ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Préférences utilisateur (côté espace prestataire / autres rôles)
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def my_preferences(request):
    """
    Permet à l'utilisateur connecté d'opt-out par event × channel
    (pour les events où il est destinataire potentiel selon les règles).
    """
    user = request.user
    if request.method == "POST":
        # On reconstruit les préférences à partir des cases cochées.
        # Convention : un input nommé `pref-<event_id>-<channel_id>` présent => enabled=True.
        for event in NotificationEvent.objects.all():
            for channel in NotificationChannel.objects.all():
                key = f"pref-{event.pk}-{channel.pk}"
                enabled = key in request.POST
                pref, _ = UserNotificationPreference.objects.update_or_create(
                    user=user,
                    event=event,
                    channel=channel,
                    defaults={"enabled": enabled},
                )
        messages.success(request, "Préférences mises à jour.")
        return redirect(request.path)

    events = NotificationEvent.objects.filter(is_enabled=True).order_by("order", "label")
    channels = NotificationChannel.objects.filter(is_enabled=True).order_by("order", "label")
    prefs = {
        (p.event_id, p.channel_id): p.enabled
        for p in UserNotificationPreference.objects.filter(user=user)
    }

    rows = []
    for ev in events:
        cells = []
        for ch in channels:
            cells.append({"channel": ch, "enabled": prefs.get((ev.pk, ch.pk), True)})
        rows.append({"event": ev, "cells": cells})

    template = "notifications/preferences.html"
    extra_ctx = {"events_rows": rows, "channels": channels}
    if user.is_prestataire:
        # Utilise le shell prestataire pour cohérence visuelle
        from healthcare.views import _dash_context

        extra_ctx.update(_dash_context(request, "settings"))
        template = "notifications/preferences_prestataire.html"
    return render(request, template, extra_ctx)
