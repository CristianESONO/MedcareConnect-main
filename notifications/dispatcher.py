"""
Dispatcher central de notifications.

Usage côté code métier :

    from notifications.dispatcher import dispatch
    dispatch(
        "devis.created",
        context={"devis": devis, "patient": devis.patient, "organisme": org},
        actor=org.user,           # facultatif — utilisé si la règle coche `notify_event_actor`
    )

Aucune exception n'est propagée : les erreurs sont enregistrées dans `NotificationLog`
pour ne pas casser le flux métier.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable

from django.db.models import Q
from django.template import Context, Template
from django.utils import timezone

from users.models import User

from .models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationRule,
    NotificationSettings,
    NotificationTemplate,
    UserNotificationPreference,
)

log = logging.getLogger(__name__)


# ─── Templates ───────────────────────────────────────────────────────────────


def _render(template_str: str, context: dict[str, Any]) -> str:
    if not template_str:
        return ""
    try:
        return Template(template_str).render(Context(context, autoescape=False))
    except Exception as exc:  # pragma: no cover — affichage best-effort
        log.warning("notifications: template render failed: %s", exc)
        return template_str


def render_notification_template_string(template_str: str, context: dict[str, Any]) -> str:
    """Interprète une chaîne au format Django Template (ex. textes wa.me patient)."""
    return _render(template_str, context)


# ─── Recipient resolution ────────────────────────────────────────────────────


def _resolve_recipients(rule: NotificationRule, actor: User | None) -> list[dict]:
    """
    Retourne une liste de dicts {user, address}.
    `user` peut être None si on a uniquement une adresse (extra_emails).
    """
    seen_users = set()
    seen_addresses = set()
    out: list[dict] = []

    def push_user(u: User | None):
        if not u or u.pk in seen_users:
            return
        seen_users.add(u.pk)
        out.append({"user": u, "address": (u.email or "").strip()})

    # Rôles (les superutilisateurs reçoivent aussi les notifications « admin » même si user_type ≠ admin)
    roles = rule.target_roles or []
    if roles:
        role_q = Q()
        for role in roles:
            if role == NotificationRule.ROLE_ADMIN:
                role_q |= Q(user_type=NotificationRule.ROLE_ADMIN) | Q(is_superuser=True)
            else:
                role_q |= Q(user_type=role)
        for u in User.objects.filter(role_q, is_active=True).distinct().iterator():
            push_user(u)

    # Users explicites
    for u in rule.target_users.filter(is_active=True):
        push_user(u)

    # Acteur de l'événement
    if rule.notify_event_actor and actor is not None:
        push_user(actor)

    # Emails libres
    for addr in rule.parse_extra_emails():
        if addr.lower() in seen_addresses:
            continue
        seen_addresses.add(addr.lower())
        out.append({"user": None, "address": addr})

    return out


def _is_opted_out(user: User | None, event: NotificationEvent, channel: NotificationChannel) -> bool:
    if user is None:
        return False
    pref = UserNotificationPreference.objects.filter(
        user=user, event=event, channel=channel
    ).first()
    return bool(pref and pref.enabled is False)


# ─── Drivers ─────────────────────────────────────────────────────────────────


def _send_in_app(
    *,
    user: User | None,
    subject: str,
    body: str,
    event: NotificationEvent,
    context: dict,
) -> tuple[str, str]:
    """Crée un `messaging.Notification` lié au user."""
    if user is None:
        return NotificationLog.STATUS_SKIPPED, "in-app sans user destinataire"
    from messaging.models import Notification as InAppNotification

    type_map = {
        "devis": "devis",
        "review": "review",
        "subscription": "system",
        "org": "approval",
        "message": "message",
        "rdv": "rdv",
    }
    head = (event.code.split(".") or ["system"])[0]
    notif_type = type_map.get(head, "system")
    link = (context.get("link") or "")[:500] if isinstance(context, dict) else ""

    InAppNotification.objects.create(
        user=user,
        notification_type=notif_type,
        title=(subject or event.label)[:255],
        content=body or "",
        link=link or None,
    )
    return NotificationLog.STATUS_SENT, ""


def _send_email(
    *,
    settings_obj: NotificationSettings,
    user: User | None,
    address: str,
    subject: str,
    body: str,
) -> tuple[str, str]:
    if not settings_obj.email_enabled:
        return NotificationLog.STATUS_SKIPPED, "Canal email désactivé en configuration."
    if not settings_obj.smtp_host or not settings_obj.smtp_from_email:
        return NotificationLog.STATUS_SKIPPED, "SMTP non configuré (host/from manquant)."
    if not address:
        return NotificationLog.STATUS_SKIPPED, "Pas d'adresse email destinataire."

    try:
        from django.core.mail import EmailMessage, get_connection

        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=settings_obj.smtp_host,
            port=settings_obj.smtp_port or 587,
            username=settings_obj.smtp_user or None,
            password=settings_obj.smtp_password or None,
            use_tls=settings_obj.smtp_use_tls,
            use_ssl=settings_obj.smtp_use_ssl,
            timeout=20,
        )
        from_email = settings_obj.smtp_from_email
        if settings_obj.smtp_from_name:
            from_email = f"{settings_obj.smtp_from_name} <{settings_obj.smtp_from_email}>"

        msg = EmailMessage(
            subject=subject or "(sans objet)",
            body=body or "",
            from_email=from_email,
            to=[address],
            reply_to=[settings_obj.smtp_reply_to] if settings_obj.smtp_reply_to else None,
            connection=connection,
        )
        msg.send(fail_silently=False)
    except Exception as exc:
        return NotificationLog.STATUS_FAILED, f"SMTP error: {exc}"
    return NotificationLog.STATUS_SENT, ""


def _resolve_whatsapp_number(user: User | None, context: dict) -> str:
    """Récupère un numéro WhatsApp utilisable depuis le user ou le contexte."""
    candidates: list[str] = []
    if user is not None:
        candidates.append(getattr(user, "phone_number", "") or "")
        prof = getattr(user, "healthcare_provider_profile", None)
        if prof is not None:
            candidates.append(getattr(prof, "whatsapp_number", "") or "")
            candidates.append(getattr(prof, "contact_phone", "") or "")
    if isinstance(context, dict):
        for key in ("whatsapp_number", "phone_number"):
            v = context.get(key)
            if isinstance(v, str):
                candidates.append(v)
    for raw in candidates:
        digits = "".join(c for c in raw if c.isdigit())
        if digits:
            return digits
    return ""


def _send_whatsapp_cloud(
    *,
    settings_obj: NotificationSettings,
    user: User | None,
    address: str,
    body: str,
    context: dict,
) -> tuple[str, str]:
    if not settings_obj.whatsapp_enabled:
        return NotificationLog.STATUS_SKIPPED, "Canal WhatsApp désactivé en configuration."
    if not (settings_obj.wa_phone_number_id and settings_obj.wa_access_token):
        return NotificationLog.STATUS_SKIPPED, "WhatsApp Cloud non configuré (phone_id/token manquants)."

    digits = "".join(c for c in (address or "") if c.isdigit()) or _resolve_whatsapp_number(user, context)
    if not digits:
        return NotificationLog.STATUS_SKIPPED, "Pas de numéro WhatsApp pour le destinataire."

    # Import différé : on n'oblige pas `requests` au runtime tant que WA est désactivé.
    try:
        import requests  # type: ignore[import-not-found]
    except ImportError:
        return NotificationLog.STATUS_FAILED, "Le paquet `requests` est requis pour WhatsApp Cloud API."

    url = f"https://graph.facebook.com/{settings_obj.wa_api_version}/{settings_obj.wa_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings_obj.wa_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": digits,
        "type": "text",
        "text": {"body": body[:4096] or "(message vide)"},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
    except Exception as exc:
        return NotificationLog.STATUS_FAILED, f"HTTP error: {exc}"
    if 200 <= resp.status_code < 300:
        return NotificationLog.STATUS_SENT, ""
    return NotificationLog.STATUS_FAILED, f"WhatsApp Cloud {resp.status_code}: {resp.text[:500]}"


# ─── Public API ──────────────────────────────────────────────────────────────


def dispatch(
    event_code: str,
    *,
    context: dict | None = None,
    actor: User | None = None,
) -> dict:
    """
    Déclenche les envois pour un événement métier.

    Retourne un compteur résumé : {sent, skipped, failed}.
    Aucune exception n'est levée vers l'appelant.
    """
    counters = {"sent": 0, "skipped": 0, "failed": 0}
    context = dict(context or {})

    try:
        event = NotificationEvent.objects.filter(code=event_code, is_enabled=True).first()
        if event is None:
            log.info("notifications: event %r introuvable ou désactivé", event_code)
            return counters

        settings_obj = NotificationSettings.load()
        rules = (
            NotificationRule.objects.filter(event=event, is_active=True)
            .select_related("channel")
            .prefetch_related("target_users")
        )
        for rule in rules:
            channel = rule.channel
            if not channel.is_enabled:
                continue
            template = (
                NotificationTemplate.objects.filter(
                    event=event, channel=channel, is_enabled=True
                ).first()
            )
            if template is None:
                continue
            subject = _render(template.subject or event.label, context)
            body = _render(template.body, context)

            recipients = _resolve_recipients(rule, actor)
            for r in recipients:
                user = r["user"]
                address = r["address"]
                if _is_opted_out(user, event, channel):
                    counters["skipped"] += 1
                    continue
                status, error = _dispatch_one(
                    channel=channel,
                    settings_obj=settings_obj,
                    user=user,
                    address=address,
                    subject=subject,
                    body=body,
                    event=event,
                    context=context,
                )
                NotificationLog.objects.create(
                    event=event,
                    channel=channel,
                    recipient_user=user,
                    recipient_address=address or "",
                    subject=subject[:255],
                    body=body,
                    status=status,
                    error=error,
                    context_snapshot=_safe_snapshot(context),
                    sent_at=timezone.now() if status == NotificationLog.STATUS_SENT else None,
                )
                if status == NotificationLog.STATUS_SENT:
                    counters["sent"] += 1
                elif status == NotificationLog.STATUS_FAILED:
                    counters["failed"] += 1
                else:
                    counters["skipped"] += 1
    except Exception as exc:
        log.exception("notifications.dispatch crashed: %s", exc)
    return counters


def _dispatch_one(
    *,
    channel: NotificationChannel,
    settings_obj: NotificationSettings,
    user: User | None,
    address: str,
    subject: str,
    body: str,
    event: NotificationEvent,
    context: dict,
) -> tuple[str, str]:
    code = channel.code
    if code == "in_app":
        if not settings_obj.in_app_enabled:
            return NotificationLog.STATUS_SKIPPED, "Canal in-app désactivé."
        return _send_in_app(user=user, subject=subject, body=body, event=event, context=context)
    if code == "email":
        return _send_email(
            settings_obj=settings_obj,
            user=user,
            address=address,
            subject=subject,
            body=body,
        )
    if code == "whatsapp_cloud":
        return _send_whatsapp_cloud(
            settings_obj=settings_obj,
            user=user,
            address=address,
            body=body,
            context=context,
        )
    return NotificationLog.STATUS_SKIPPED, f"Driver inconnu pour le canal {code!r}."


def _safe_snapshot(context: dict) -> dict:
    """Réduit le contexte aux types JSON-sérialisables."""
    out: dict = {}
    for k, v in (context or {}).items():
        try:
            if isinstance(v, (str, int, float, bool)) or v is None:
                out[k] = v
            else:
                out[k] = str(v)[:500]
        except Exception:
            continue
    return out


def resend_notification_log(log_id: int) -> tuple[NotificationLog | None, str]:
    """
    Renvoie une notification à partir d'une ligne de journal (même sujet/corps/destinataire).
    Crée une nouvelle entrée de journal ; ne modifie pas l'entrée d'origine.
    """
    try:
        log_entry = NotificationLog.objects.select_related(
            "event", "channel", "recipient_user"
        ).get(pk=log_id)
    except NotificationLog.DoesNotExist:
        return None, "Entrée de journal introuvable."

    if not log_entry.channel:
        return None, "Canal inconnu : impossible de renvoyer."

    if log_entry.channel.code == "in_app" and not log_entry.event:
        return None, "Événement manquant : le renvoi in-app nécessite l'événement d'origine."

    settings_obj = NotificationSettings.load()
    context = dict(log_entry.context_snapshot or {})

    status, error = _dispatch_one(
        channel=log_entry.channel,
        settings_obj=settings_obj,
        user=log_entry.recipient_user,
        address=(log_entry.recipient_address or "").strip(),
        subject=log_entry.subject or "",
        body=log_entry.body or "",
        event=log_entry.event,
        context=context,
    )

    new_log = NotificationLog.objects.create(
        event=log_entry.event,
        channel=log_entry.channel,
        recipient_user=log_entry.recipient_user,
        recipient_address=(log_entry.recipient_address or "").strip(),
        subject=(log_entry.subject or "")[:255],
        body=log_entry.body or "",
        status=status,
        error=error,
        context_snapshot=_safe_snapshot(context),
        sent_at=timezone.now() if status == NotificationLog.STATUS_SENT else None,
    )
    return new_log, ""
