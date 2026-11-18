"""Résolution de la source d'une visite profil (UTM / query string)."""

from __future__ import annotations

from healthcare.models import ProfileView


def resolve_profile_view_source(request) -> str:
    """Déduit la source à partir de ?src=, utm_source= et utm_medium=."""
    raw = (request.GET.get("src") or request.GET.get("utm_source") or "").strip().lower()
    medium = (request.GET.get("utm_medium") or "").strip().lower()

    if raw in ("nfc", "medplaque_nfc") or (raw == "medplaque" and medium == "nfc"):
        return ProfileView.SOURCE_NFC
    if raw in ("qr", "qrcode", "medplaque_qr") or (raw == "medplaque" and medium == "qr"):
        return ProfileView.SOURCE_QR
    if raw in ("whatsapp", "wa", "whatsapp_devis"):
        return ProfileView.SOURCE_WHATSAPP
    if raw in ("annuaire", "search", "directory", "centres"):
        return ProfileView.SOURCE_ANNUAIRE

    ref = (request.META.get("HTTP_REFERER") or "").lower()
    if any(token in ref for token in ("/search", "/centres", "/annuaire", "q=", "acte=")):
        return ProfileView.SOURCE_ANNUAIRE

    return ProfileView.SOURCE_ANNUAIRE


VISIT_SOURCE_META = {
    ProfileView.SOURCE_ANNUAIRE: {
        "label": "Annuaire",
        "action": "Consultation fiche",
        "dot": "bg-blue-500",
        "badge": "bg-blue-50 text-blue-700",
    },
    ProfileView.SOURCE_WHATSAPP: {
        "label": "WhatsApp",
        "action": "Devis demandé",
        "dot": "bg-emerald-500",
        "badge": "bg-emerald-50 text-emerald-700",
    },
    ProfileView.SOURCE_NFC: {
        "label": "NFC",
        "action": "Scan MedPlaque NFC",
        "dot": "bg-violet-500",
        "badge": "bg-violet-50 text-violet-700",
    },
    ProfileView.SOURCE_QR: {
        "label": "QR",
        "action": "Scan MedPlaque QR",
        "dot": "bg-indigo-500",
        "badge": "bg-indigo-50 text-indigo-700",
    },
}


def visit_row_from_profile_view(view) -> dict:
    meta = VISIT_SOURCE_META.get(view.source, VISIT_SOURCE_META[ProfileView.SOURCE_ANNUAIRE])
    loc = view.organisme.city or "Dakar"
    return {
        "source": view.source,
        "label": meta["label"],
        "action": meta["action"],
        "dot_class": meta["dot"],
        "badge_class": meta["badge"],
        "meta": f"{loc} · {view.viewed_at.strftime('%d/%m · %Hh%M')}",
        "viewer_name": (
            view.viewer.display_name
            if view.viewer
            else "Visiteur anonyme"
        ),
    }
