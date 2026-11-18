"""JSON API for the React notification administration pages."""
import json
from functools import wraps

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse, QueryDict
from django.utils import timezone

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
)


def _api_methods(*methods):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = JsonResponse({"error": "Méthode HTTP non autorisée."}, status=405)
                response["Allow"] = ", ".join(methods)
                return response
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def _admin_api(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or not user.is_active:
            return JsonResponse({"error": "Authentification requise."}, status=401)
        if not (user.is_superuser or user.is_admin_user):
            return JsonResponse({"error": "Accès réservé aux administrateurs."}, status=403)
        return view(request, *args, **kwargs)

    return wrapped


def _payload(request):
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body or b"{}")
        except (TypeError, ValueError):
            return None
        return data if isinstance(data, dict) else None
    return request.POST


def _form_data(data, multi_fields=(), boolean_fields=()):
    """Adapt JSON/form data to Django forms, retaining multiple-choice values."""
    result = QueryDict("", mutable=True)
    for key, value in data.items():
        if key in multi_fields:
            values = value if isinstance(value, list) else ([] if value in (None, "") else [value])
            result.setlist(key, [str(item) for item in values])
        elif key in boolean_fields:
            if value is True or str(value).lower() in ("1", "true", "on", "yes"):
                result[key] = "on"
        elif value is not None:
            result[key] = str(value)
    return result


def _form_errors(form):
    return {
        field: [str(error) for error in errors]
        for field, errors in form.errors.items()
    }


def _settings_payload(obj):
    return {
        "email_enabled": obj.email_enabled,
        "smtp_host": obj.smtp_host,
        "smtp_port": obj.smtp_port,
        "smtp_user": obj.smtp_user,
        "smtp_password_configured": bool(obj.smtp_password),
        "smtp_use_tls": obj.smtp_use_tls,
        "smtp_use_ssl": obj.smtp_use_ssl,
        "smtp_from_email": obj.smtp_from_email,
        "smtp_from_name": obj.smtp_from_name,
        "smtp_reply_to": obj.smtp_reply_to,
        "whatsapp_enabled": obj.whatsapp_enabled,
        "wa_phone_number_id": obj.wa_phone_number_id,
        "wa_business_account_id": obj.wa_business_account_id,
        "wa_access_token_configured": bool(obj.wa_access_token),
        "wa_api_version": obj.wa_api_version,
        "in_app_enabled": obj.in_app_enabled,
        "log_retention_days": obj.log_retention_days,
        "google_reviews_url": obj.google_reviews_url,
    }


@_api_methods("GET", "POST")
@_admin_api
def settings_api(request):
    obj = NotificationSettings.load()
    if request.method == "GET":
        return JsonResponse({
            "settings": _settings_payload(obj),
            "channels": [
                {
                    "id": item.pk,
                    "code": item.code,
                    "label": item.label,
                    "description": item.description,
                    "is_enabled": item.is_enabled,
                }
                for item in NotificationChannel.objects.all()
            ],
        })

    data = _payload(request)
    if data is None:
        return JsonResponse({"error": "Corps JSON invalide."}, status=400)
    action = data.get("action")
    form_map = {
        "save_smtp": (SmtpSettingsForm, ("smtp_password",), ("email_enabled", "smtp_use_tls", "smtp_use_ssl")),
        "save_wa": (WhatsAppSettingsForm, ("wa_access_token",), ("whatsapp_enabled",)),
        "save_general": (GeneralSettingsForm, (), ("in_app_enabled",)),
    }
    if action in form_map:
        form_class, secret_fields, boolean_fields = form_map[action]
        fields = form_class.Meta.fields
        submitted = {field: data.get(field, "") for field in fields}
        for field in secret_fields:
            # Browsers and API clients send an empty password when retaining it.
            if not submitted[field]:
                submitted[field] = getattr(obj, field)
        form = form_class(_form_data(submitted, boolean_fields=boolean_fields), instance=obj)
        if not form.is_valid():
            return JsonResponse(
                {"error": "Vérifiez les champs saisis.", "errors": _form_errors(form)},
                status=400,
            )
        form.save()
        return JsonResponse({"ok": True, "message": "Configuration enregistrée.", "settings": _settings_payload(obj)})

    if action in ("test_email", "test_wa"):
        form_class = TestEmailForm if action == "test_email" else TestWhatsAppForm
        form = form_class(_form_data(data))
        if not form.is_valid():
            return JsonResponse(
                {"error": "Vérifiez les champs saisis.", "errors": _form_errors(form)},
                status=400,
            )
        if action == "test_email":
            status, error = _send_email(
                settings_obj=obj,
                user=request.user,
                address=form.cleaned_data["to_email"],
                subject="[MedCare] Test SMTP",
                body="Ceci est un message de test envoyé depuis l'espace admin MedCare.",
            )
        else:
            status, error = _send_whatsapp_cloud(
                settings_obj=obj,
                user=None,
                address=form.cleaned_data["to_number"],
                body=form.cleaned_data["message"],
                context={},
            )
        http_status = 200 if status == NotificationLog.STATUS_SENT else (
            502 if status == NotificationLog.STATUS_FAILED else 409
        )
        return JsonResponse({"ok": status == NotificationLog.STATUS_SENT, "delivery_status": status, "error": error}, status=http_status)

    return JsonResponse({"error": "Action inconnue."}, status=400)


def _rule_payload(rule):
    return {
        "id": rule.pk,
        "event_id": rule.event_id,
        "channel_id": rule.channel_id,
        "target_roles": rule.target_roles or [],
        "target_user_ids": list(rule.target_users.values_list("pk", flat=True)),
        "target_users": [
            {
                "id": user.pk,
                "label": f"{user.display_name} ({user.username})" + (f" — {user.email}" if user.email else ""),
            }
            for user in rule.target_users.all()
        ],
        "extra_emails": rule.extra_emails,
        "notify_event_actor": rule.notify_event_actor,
        "is_active": rule.is_active,
        "note": rule.note,
        "template_exists": NotificationTemplate.objects.filter(
            event=rule.event, channel=rule.channel
        ).exists(),
    }


@_api_methods("GET")
@_admin_api
def rules_api(request):
    events = NotificationEvent.objects.all().order_by("order", "label")
    channels = NotificationChannel.objects.all().order_by("order", "label")
    rules = {
        (rule.event_id, rule.channel_id): rule
        for rule in NotificationRule.objects.select_related("event", "channel").prefetch_related("target_users")
    }
    return JsonResponse({
        "events": [
            {
                "id": event.pk,
                "label": event.label,
                "code": event.code,
                "description": event.description,
                "audience": event.get_audience_display(),
            }
            for event in events
        ],
        "channels": [
            {"id": channel.pk, "code": channel.code, "label": channel.label, "is_enabled": channel.is_enabled}
            for channel in channels
        ],
        "rules": [
            {
                "event_id": event.pk,
                "channel_id": channel.pk,
                "rule": _rule_payload(rule) if rule else None,
            }
            for event in events
            for channel in channels
            for rule in [rules.get((event.pk, channel.pk))]
        ],
    })


@_api_methods("GET", "POST")
@_admin_api
def rule_api(request, event_id, channel_id):
    event = NotificationEvent.objects.filter(pk=event_id).first()
    channel = NotificationChannel.objects.filter(pk=channel_id).first()
    if event is None or channel is None:
        return JsonResponse({"error": "Événement ou canal introuvable."}, status=404)
    rule, created = NotificationRule.objects.get_or_create(
        event=event, channel=channel, defaults={"is_active": True}
    )
    if request.method == "GET":
        from django.db.models.functions import Lower
        from users.models import User

        payload = _rule_payload(rule)
        payload["users"] = [
            {
                "id": user.pk,
                "label": f"{user.display_name} ({user.username})" + (f" — {user.email}" if user.email else ""),
            }
            for user in User.objects.filter(is_active=True).order_by(Lower("username"))
        ]
        return JsonResponse({
            "event": {"id": event.pk, "label": event.label, "code": event.code, "description": event.description},
            "channel": {"id": channel.pk, "label": channel.label, "code": channel.code},
            "rule": payload,
            "created": created,
        })

    data = _payload(request)
    if data is None:
        return JsonResponse({"error": "Corps JSON invalide."}, status=400)
    form_data = _form_data(
        data,
        multi_fields=("target_roles", "target_users"),
        boolean_fields=("notify_event_actor", "is_active"),
    )
    form = NotificationRuleForm(form_data, instance=rule)
    if not form.is_valid():
        return JsonResponse({"error": "Vérifiez les champs saisis.", "errors": _form_errors(form)}, status=400)
    form.save()
    return JsonResponse({"ok": True, "rule": _rule_payload(rule)})


def _template_payload(template):
    return {
        "id": template.pk,
        "event_id": template.event_id,
        "event_label": template.event.label,
        "event_code": template.event.code,
        "channel_id": template.channel_id,
        "channel_label": template.channel.label,
        "channel_code": template.channel.code,
        "subject": template.subject,
        "body": template.body,
        "is_enabled": template.is_enabled,
        "updated_at": template.updated_at.isoformat(),
    }


@_api_methods("GET", "POST", "PUT")
@_admin_api
def templates_api(request, template_id=None):
    if request.method == "GET":
        templates = NotificationTemplate.objects.select_related("event", "channel").order_by(
            "event__order", "event__label", "channel__order"
        )
        return JsonResponse({
            "templates": [_template_payload(item) for item in templates],
            "events": list(NotificationEvent.objects.order_by("order", "label").values("id", "label", "code")),
            "channels": list(NotificationChannel.objects.order_by("order", "label").values("id", "label", "code")),
        })
    data = _payload(request)
    if data is None:
        return JsonResponse({"error": "Corps JSON invalide."}, status=400)
    if template_id is None:
        if request.method != "POST":
            return JsonResponse({"error": "Identifiant de template requis."}, status=400)
        template = NotificationTemplate()
        try:
            template.event = NotificationEvent.objects.get(pk=data.get("event_id"))
            template.channel = NotificationChannel.objects.get(pk=data.get("channel_id"))
        except (NotificationEvent.DoesNotExist, NotificationChannel.DoesNotExist, TypeError, ValueError):
            return JsonResponse({"error": "Événement ou canal introuvable."}, status=400)
    else:
        template = NotificationTemplate.objects.filter(pk=template_id).select_related("event", "channel").first()
        if template is None:
            return JsonResponse({"error": "Template introuvable."}, status=404)
    for field in ("subject", "body", "is_enabled"):
        if field in data:
            setattr(template, field, data[field])
    try:
        template.full_clean()
        template.save()
    except Exception as exc:
        from django.core.exceptions import ValidationError

        if isinstance(exc, ValidationError):
            return JsonResponse(
                {"error": "Vérifiez les champs saisis.", "errors": exc.message_dict if hasattr(exc, "message_dict") else {"__all__": exc.messages}},
                status=400,
            )
        raise
    return JsonResponse({"ok": True, "template": _template_payload(template)}, status=201 if template_id is None else 200)


@_api_methods("GET", "POST")
@_admin_api
def patient_wa_messages_api(request):
    obj = NotificationSettings.load()
    if request.method == "GET":
        return JsonResponse({
            "messages": {
                "patient_wa_me_message_general": obj.patient_wa_me_message_general,
                "patient_wa_me_message_acte": obj.patient_wa_me_message_acte,
                "patient_wa_me_message_devis_formal": obj.patient_wa_me_message_devis_formal,
            }
        })
    data = _payload(request)
    if data is None:
        return JsonResponse({"error": "Corps JSON invalide."}, status=400)
    form = PatientWaMeTemplatesForm(_form_data(data), instance=obj)
    if not form.is_valid():
        return JsonResponse({"error": "Vérifiez les champs saisis.", "errors": _form_errors(form)}, status=400)
    form.save()
    return JsonResponse({"ok": True, "message": "Messages WhatsApp enregistrés."})


@_api_methods("GET")
@_admin_api
def logs_api(request):
    queryset = NotificationLog.objects.select_related("event", "channel", "recipient_user").order_by("-created_at")
    status = (request.GET.get("status") or "").strip()
    if status in ("sent", "failed", "skipped", "queued"):
        queryset = queryset.filter(status=status)
    channel = (request.GET.get("channel") or "").strip()
    if channel:
        queryset = queryset.filter(channel__code=channel)
    query = (request.GET.get("q") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(subject__icontains=query)
            | Q(recipient_address__icontains=query)
            | Q(recipient_user__username__icontains=query)
            | Q(recipient_user__email__icontains=query)
            | Q(error__icontains=query)
        )
    paginator = Paginator(queryset, 30)
    page = paginator.get_page(request.GET.get("page"))
    counts = {
        row["status"]: row["count"]
        for row in NotificationLog.objects.values("status").annotate(count=Count("id"))
    }
    return JsonResponse({
        "logs": [
            {
                "id": log.pk,
                "created_at": timezone.localtime(log.created_at).isoformat(),
                "event_label": log.event.label if log.event else "",
                "event_code": log.event.code if log.event else "",
                "channel_label": log.channel.label if log.channel else "",
                "channel_code": log.channel.code if log.channel else "",
                "recipient_name": (
                    (log.recipient_user.display_name or log.recipient_user.username)
                    if log.recipient_user else ""
                ),
                "recipient_address": log.recipient_address,
                "status": log.status,
                "status_label": log.get_status_display(),
                "subject": log.subject,
                "error": log.error,
                "can_resend": bool(log.channel_id),
            }
            for log in page.object_list
        ],
        "filters": {"q": query, "status": status, "channel": channel},
        "channels": list(NotificationChannel.objects.values("code", "label")),
        "counts_by_status": counts,
        "pagination": {
            "number": page.number,
            "pages": paginator.num_pages,
            "total": paginator.count,
            "has_previous": page.has_previous(),
            "previous": page.previous_page_number() if page.has_previous() else None,
            "has_next": page.has_next(),
            "next": page.next_page_number() if page.has_next() else None,
        },
    })


@_api_methods("POST")
@_admin_api
def log_resend_api(request):
    data = _payload(request)
    if data is None:
        return JsonResponse({"error": "Corps JSON invalide."}, status=400)
    try:
        log_id = int(data.get("log_id", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Identifiant de journal invalide."}, status=400)
    new_log, error = resend_notification_log(log_id)
    if new_log is None:
        return JsonResponse({"error": error or "Renvoi impossible."}, status=404)
    result = {
        "ok": new_log.status == NotificationLog.STATUS_SENT,
        "new_log_id": new_log.pk,
        "status": new_log.status,
        "error": new_log.error,
    }
    http_status = 200 if new_log.status == NotificationLog.STATUS_SENT else (
        502 if new_log.status == NotificationLog.STATUS_FAILED else 409
    )
    return JsonResponse(result, status=http_status)
