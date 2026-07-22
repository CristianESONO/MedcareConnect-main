"""Données d'affichage partagées : fiche publique patient + aperçu prestataire."""
from __future__ import annotations

from urllib.parse import quote

from django.urls import reverse

from .insurance_icons import chip_label_for_assurance_segment
from .models import PrestataireActe


def insurance_profil_filter_key(segment: str) -> str:
    if segment == "privee_iard":
        return "privee"
    if segment == "digitale":
        return "digitale"
    if segment == "mutuelle":
        return "mutuelle"
    if segment == "programme":
        return "programme"
    return "public"


def profil_hours_meta(hours_list) -> str:
    from .opening_hours_display import profil_hours_meta as _meta

    return _meta(hours_list)


def profil_hours_meta_chunks(hours_list) -> list[str]:
    from .opening_hours_display import profil_hours_meta_chunks as _chunks

    return _chunks(hours_list)


def maps_url_for_org(org) -> str:
    if org.latitude and org.longitude:
        lat = format(org.latitude, "f").rstrip("0").rstrip(".")
        lng = format(org.longitude, "f").rstrip("0").rstrip(".")
        return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
    if org.address:
        return (
            "https://www.google.com/maps/search/?api=1&query="
            + quote(f"{org.address} {org.city}")
        )
    return ""


def waze_url_for_org(org) -> str:
    if org.latitude and org.longitude:
        lat = format(org.latitude, "f").rstrip("0").rstrip(".")
        lng = format(org.longitude, "f").rstrip("0").rstrip(".")
        return f"https://waze.com/ul?ll={lat},{lng}&navigate=yes"
    if org.address:
        return (
            "https://waze.com/ul?q="
            + quote(f"{org.address} {org.city}")
            + "&navigate=yes"
        )
    return ""


def practical_chips_for_org(org) -> list[dict]:
    chips = []
    if org.sans_rendez_vous:
        chips.append({"label": "Sans rendez-vous", "icon": "walk"})
    if org.accepte_tiers_payant:
        chips.append({"label": "Tiers payant", "icon": "card"})
    if org.access_pmr:
        chips.append({"label": "Accès PMR", "icon": "accessibility"})
    if org.prises_sang_domicile:
        chips.append({"label": "Prestations à domicile", "icon": "home"})
    return chips


def open_today_from_hours(hours_list) -> str | None:
    for h in hours_list:
        if h.get("is_today"):
            return "closed" if h.get("closed") else "open"
    return None


def build_profil_pillars(actes) -> tuple[list[dict], dict]:
    """Retourne (profil_pillars, services_with_actes)."""
    services_with_actes: dict = {}
    for pa in actes:
        svc = pa.acte.service_medical_category
        svc_name = svc.name if svc else "Autres"
        services_with_actes.setdefault(svc_name, []).append(pa)

    pillars = []
    for idx, (svc_name, group) in enumerate(services_with_actes.items(), start=1):
        svc = group[0].acte.service_medical_category if group else None
        pillars.append(
            {
                "id": f"p{idx}",
                "name": svc_name,
                "icon": svc.display_icon if svc else "🏥",
                "actes": group,
                "count": len(group),
            }
        )
    return pillars, services_with_actes


def build_insurances_profil(insurances_qs) -> list[dict]:
    rows = []
    for pec in insurances_qs:
        seg = pec.assurance.segment
        rows.append(
            {
                "name": pec.assurance.name,
                "segment": seg,
                "filter_key": insurance_profil_filter_key(seg),
                "chip_label": chip_label_for_assurance_segment(
                    seg, pec.assurance.get_segment_display()
                ),
            }
        )
    return rows


def fiche_context_for_org(org, actes, hours_list, request) -> dict:
    """Contexte template commun (hors auth / favoris / wa sur actes)."""
    profil_pillars, services_with_actes = build_profil_pillars(actes)
    public_path = reverse("healthcare:organisme_detail", kwargs={"slug": org.slug})
    show_pioneer = bool(
        getattr(getattr(org, "subscription_plan", None), "is_pioneer_offer", False)
    )
    return {
        "services_with_actes": services_with_actes,
        "profil_pillars": profil_pillars,
        "actes_visible_count": len(actes) if hasattr(actes, "__len__") else actes.count(),
        "hours_meta": profil_hours_meta(hours_list),
        "hours_meta_chunks": profil_hours_meta_chunks(hours_list),
        "open_today": open_today_from_hours(hours_list),
        "practical_chips": practical_chips_for_org(org),
        "show_pioneer_badge": show_pioneer,
        "show_public_prices": bool(getattr(org, "show_prices_on_public_profile", True)),
        "maps_url": maps_url_for_org(org),
        "waze_url": waze_url_for_org(org),
        "public_absolute_url": request.build_absolute_uri(public_path),
        "public_path": public_path,
    }
