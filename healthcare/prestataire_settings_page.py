"""Page Paramètres prestataire — alignée DEMO_STRUCTURES."""

from __future__ import annotations

from django.contrib.auth import update_session_auth_hash

from notifications.models import (
    NotificationChannel,
    NotificationEvent,
    UserNotificationPreference,
)
from users.forms import UserProfileForm

PRESTATAIRE_NOTIF_TOGGLES: tuple[tuple[str, str, str], ...] = (
    (
        "devis.created",
        "Nouveau devis WhatsApp reçu",
        "Notification in-app à chaque nouveau devis",
    ),
    (
        "rdv.requested",
        "Nouvelle réservation en attente",
        "Alerte immédiate pour les RDV à confirmer",
    ),
    (
        "rdv.reminder",
        "Rappel RDV (J-1)",
        "Rappel automatique avant le rendez-vous",
    ),
    (
        "devis.relanced",
        "Devis relancé / sans réponse",
        "Alerte quand un devis est relancé",
    ),
    (
        "subscription.approved",
        "Changement de formule approuvé",
        "Confirmation lors d'une mise à jour d'abonnement",
    ),
    (
        "organisme.approved",
        "Structure activée",
        "Notification quand votre fiche est validée",
    ),
)


TEAM_ROLE_LABELS = {
    "secretaire": "Accès limité · Devis + Réservations",
    "readonly": "Lecture seule",
}

DASHBOARD_PERIOD_CHOICES = ("7j", "30j", "total")
LOCALE_CHOICES = ("fr", "wo", "en")
CURRENCY_CHOICES = ("XOF", "EUR", "USD")


def team_rows_for_org(org) -> list[dict]:
    """Membres invités (hors administrateur principal)."""
    rows = []
    for idx, raw in enumerate(org.dashboard_team or []):
        if not isinstance(raw, dict):
            continue
        role = (raw.get("role") or "secretaire").strip()
        rows.append(
            {
                "index": idx,
                "name": (raw.get("name") or raw.get("email") or "Utilisateur").strip(),
                "email": (raw.get("email") or "").strip(),
                "role": role,
                "role_label": TEAM_ROLE_LABELS.get(role, role),
                "status": (raw.get("status") or "pending").strip(),
            }
        )
    return rows


def preferences_context(org) -> dict:
    period = org.settings_dashboard_period or "30j"
    if period not in DASHBOARD_PERIOD_CHOICES:
        period = "30j"
    locale = org.settings_locale or "fr"
    if locale not in LOCALE_CHOICES:
        locale = "fr"
    currency = org.settings_currency or "XOF"
    if currency not in CURRENCY_CHOICES:
        currency = "XOF"
    return {
        "settings_dashboard_period": period,
        "settings_locale": locale,
        "settings_currency": currency,
        "show_prices_on_public_profile": bool(org.show_prices_on_public_profile),
        "team_rows": team_rows_for_org(org),
    }


def save_org_preferences(org, post) -> None:
    period = (post.get("settings_dashboard_period") or "30j").strip()
    if period not in DASHBOARD_PERIOD_CHOICES:
        period = "30j"
    locale = (post.get("settings_locale") or "fr").strip()
    if locale not in LOCALE_CHOICES:
        locale = "fr"
    currency = (post.get("settings_currency") or "XOF").strip()
    if currency not in CURRENCY_CHOICES:
        currency = "XOF"
    org.settings_dashboard_period = period
    org.settings_locale = locale
    org.settings_currency = currency
    org.show_prices_on_public_profile = post.get("show_prices_on_public_profile") == "on"
    org.save(
        update_fields=[
            "settings_dashboard_period",
            "settings_locale",
            "settings_currency",
            "show_prices_on_public_profile",
            "updated_at",
        ]
    )


def handle_team_actions(org, post) -> list[str]:
    """Invite ou retire un membre — retourne messages info."""
    notes: list[str] = []
    remove_raw = (post.get("team_remove") or "").strip()
    if remove_raw.isdigit():
        idx = int(remove_raw)
        team = list(org.dashboard_team or [])
        if 0 <= idx < len(team):
            team.pop(idx)
            org.dashboard_team = team
            org.save(update_fields=["dashboard_team", "updated_at"])
            notes.append("Accès retiré.")

    invite_email = (post.get("team_invite_email") or "").strip().lower()
    if invite_email:
        invite_name = (post.get("team_invite_name") or "").strip()
        role = (post.get("team_invite_role") or "secretaire").strip()
        if role not in TEAM_ROLE_LABELS:
            role = "secretaire"
        team = list(org.dashboard_team or [])
        if any(
            isinstance(m, dict) and (m.get("email") or "").strip().lower() == invite_email
            for m in team
        ):
            notes.append("Cet email est déjà invité.")
        else:
            team.append(
                {
                    "name": invite_name or invite_email.split("@")[0],
                    "email": invite_email,
                    "role": role,
                    "status": "pending",
                }
            )
            org.dashboard_team = team
            org.save(update_fields=["dashboard_team", "updated_at"])
            notes.append(f"Invitation enregistrée pour {invite_email}.")
    return notes


def notification_toggle_rows(user) -> list[dict]:
    """Une ligne = un event, toggle = canal in_app (comme la démo)."""
    in_app = NotificationChannel.objects.filter(code="in_app", is_enabled=True).first()
    prefs = {}
    if in_app:
        prefs = {
            p.event_id: p.enabled
            for p in UserNotificationPreference.objects.filter(user=user, channel=in_app)
        }
    rows = []
    for code, label, subtitle in PRESTATAIRE_NOTIF_TOGGLES:
        event = NotificationEvent.objects.filter(code=code, is_enabled=True).first()
        if not event:
            continue
        default_on = True
        enabled = prefs.get(event.pk, default_on)
        rows.append(
            {
                "event": event,
                "label": label,
                "subtitle": subtitle,
                "enabled": enabled,
                "field_name": f"notif-{event.pk}",
            }
        )
    return rows


def save_notification_toggles(user, post) -> None:
    in_app = NotificationChannel.objects.filter(code="in_app", is_enabled=True).first()
    if not in_app:
        return
    for code, _, _ in PRESTATAIRE_NOTIF_TOGGLES:
        event = NotificationEvent.objects.filter(code=code, is_enabled=True).first()
        if not event:
            continue
        key = f"notif-{event.pk}"
        enabled = key in post
        UserNotificationPreference.objects.update_or_create(
            user=user,
            event=event,
            channel=in_app,
            defaults={"enabled": enabled},
        )


def handle_settings_post(request, user, org) -> dict:
    """Enregistre compte, mot de passe (optionnel) et notifications."""
    errors: list[str] = []
    team_notes: list[str] = []

    user_form = UserProfileForm(request.POST, request.FILES, instance=user)
    if user_form.is_valid():
        user = user_form.save()
    else:
        for field, msgs in user_form.errors.items():
            errors.extend(msgs)

    new_password = (request.POST.get("new_password") or "").strip()
    confirm_password = (request.POST.get("confirm_password") or "").strip()
    if new_password or confirm_password:
        if new_password != confirm_password:
            errors.append("Les mots de passe ne correspondent pas.")
        elif len(new_password) < 8:
            errors.append("Le mot de passe doit contenir au moins 8 caractères.")
        else:
            user.set_password(new_password)
            user.save(update_fields=["password"])
            update_session_auth_hash(request, user)

    if not errors:
        save_notification_toggles(user, request.POST)
        save_org_preferences(org, request.POST)
        team_notes = handle_team_actions(org, request.POST)

    if errors:
        return {"ok": False, "errors": errors}
    msg = "Paramètres sauvegardés."
    if team_notes:
        msg = " ".join([msg, *team_notes])
    return {"ok": True, "message": msg}
