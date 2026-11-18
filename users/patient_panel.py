"""Mon compte patient — panneau latéral (contenu AJAX, comme la démo)."""

import json

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse

from cart.models import Cart, Devis
from healthcare.models import OrganismeDeSante, SearchHistory

from .forms import (
    CustomPasswordChangeForm,
    PatientInsuranceForm,
    PatientProfileCompteForm,
    UserProfileForm,
)
from .models import PatientProfile

PAC_TABS = frozenset({"accueil", "rdv", "devis", "assurance", "profil", "chariot", "recherches"})

PAC_PAGE_TITLES = {
    "accueil": "Tableau de bord",
    "rdv": "Mes RDV",
    "devis": "Mes devis",
    "assurance": "Assurance",
    "profil": "Mes informations",
    "chariot": "Panier",
    "recherches": "Historique des recherches",
}


def is_panel_request(request) -> bool:
    return (
        request.headers.get("X-MedCare-PAC") == "1"
        or request.GET.get("pac_partial") == "1"
    )


def panel_redirect(tab: str = "accueil", **extra) -> str:
    if tab not in PAC_TABS:
        tab = "accueil"
    url = reverse("users:patient_panel_tab", kwargs={"tab": tab})
    if extra:
        from urllib.parse import urlencode
        url += "?" + urlencode({k: v for k, v in extra.items() if v})
    return url


def _pac_messages(request):
    return list(messages.get_messages(request))


def _rdv_ctx(user):
    from appointments.panel import patient_rdv_context

    return patient_rdv_context(user)


def _devis_ctx(user):
    return {"devis_entries": _devis_list_entries(user)}


def messaging_url_for_devis_part(part, *, prefer_book=False) -> str:
    """URL du fil messagerie lié au sous-devis (option : ouvrir le choix de créneau)."""
    from appointments.models import RendezVous
    from messaging.thread import ensure_devis_thread, thread_url

    conv, _ = ensure_devis_thread(part)
    url = thread_url(conv)
    if prefer_book:
        has_live_rdv = RendezVous.objects.filter(
            devis_part=part,
            status__in=RendezVous.LIVE_STATUSES,
        ).exists()
        if not has_live_rdv:
            url += "?book=1"
    return url


def redirect_url_after_devis_generated(devis, *, prefer_organisme_id=None) -> str:
    """Après réservation depuis le panier → fil messagerie (créneau si possible)."""
    from appointments.models import RendezVous
    from appointments.slots import has_bookable_hours

    parts = list(
        devis.parts.select_related("organisme").order_by("organisme__name", "pk")
    )
    if not parts:
        return reverse("messaging:inbox")

    if prefer_organisme_id is not None:
        try:
            oid = int(prefer_organisme_id)
        except (TypeError, ValueError):
            oid = None
        if oid is not None:
            match = next((p for p in parts if p.organisme_id == oid), None)
            if match:
                return messaging_url_for_devis_part(match, prefer_book=True)

    # Plusieurs structures → inbox avec parcours de validation (démo patient).
    if len(parts) > 1:
        from urllib.parse import urlencode

        qs = urlencode({"devis": devis.reference, "validate": "1"})
        return f"{reverse('messaging:inbox')}?{qs}"

    bookable = []
    for part in parts:
        if not has_bookable_hours(part.organisme):
            continue
        if RendezVous.objects.filter(
            devis_part=part,
            status__in=RendezVous.LIVE_STATUSES,
        ).exists():
            continue
        bookable.append(part)

    target = bookable[0] if bookable else parts[0]
    return messaging_url_for_devis_part(target, prefer_book=True)


def devis_validate_inbox_context(devis) -> dict:
    """Bannière + surbrillance inbox après réservation panier multi-structures."""
    from appointments.models import RendezVous
    from appointments.slots import has_bookable_hours
    from messaging.thread import ensure_devis_thread

    items: list[dict] = []
    highlight_ids: set[int] = set()
    for part in devis.parts.select_related("organisme").order_by("organisme__name", "pk"):
        conv, _ = ensure_devis_thread(part)
        has_live_rdv = RendezVous.objects.filter(
            devis_part=part,
            status__in=RendezVous.LIVE_STATUSES,
        ).exists()
        needs_action = not has_live_rdv
        if needs_action:
            highlight_ids.add(conv.pk)

        details = part.details if isinstance(part.details, list) else []
        acte_names = [
            (row.get("acte") or "").strip()
            for row in details
            if (row.get("acte") or "").strip()
        ]
        if len(acte_names) > 2:
            acte_preview = f"{acte_names[0]}, {acte_names[1]} +{len(acte_names) - 2}"
        elif acte_names:
            acte_preview = ", ".join(acte_names)
        else:
            acte_preview = "Demande de devis"

        bookable = has_bookable_hours(part.organisme)
        if needs_action and bookable:
            cta = "Prendre un rendez-vous"
        elif needs_action:
            cta = "Ouvrir la conversation"
        else:
            cta = "Voir le fil"

        items.append(
            {
                "part": part,
                "organisme": part.organisme,
                "conv": conv,
                "url": messaging_url_for_devis_part(part, prefer_book=needs_action),
                "acte_count": len(acte_names) or len(details),
                "acte_preview": acte_preview,
                "total_patient": part.total_patient,
                "needs_action": needs_action,
                "cta": cta,
            }
        )

    pending = [row for row in items if row["needs_action"]]
    return {
        "devis_validate_banner": bool(pending),
        "devis_validate_ref": devis.reference,
        "devis_validate_items": items,
        "devis_validate_pending": pending,
        "devis_validate_highlight_ids": highlight_ids,
        "devis_validate_pending_count": len(pending),
    }


def _devis_status_badge(*, closed: bool, active_rdv, can_book: bool) -> dict:
    """Libellé + classe CSS du badge carte devis (aligné sur RDV / créneau)."""
    from appointments.models import RendezVous

    if closed:
        return {"label": "Expiré", "class": "pac-badge--expired"}
    if active_rdv:
        if active_rdv.status == RendezVous.STATUS_COMPLETED:
            return {"label": "Terminé", "class": "pac-badge--done"}
        if active_rdv.status == RendezVous.STATUS_CONFIRMED:
            return {"label": "Confirmé", "class": "pac-badge--ok"}
        if active_rdv.status == RendezVous.STATUS_NO_SHOW:
            return {"label": "Absent", "class": "pac-badge--expired"}
        return {"label": "En attente", "class": "pac-badge--wait"}
    if can_book:
        return {"label": "À planifier", "class": "pac-badge--wait"}
    return {"label": "En cours", "class": "pac-badge--ok"}


def _devis_list_entries(user):
    """Une carte par sous-devis (acte / structure) — pas de regroupement multi-structures."""
    from appointments.models import RendezVous
    from appointments.slots import has_bookable_hours
    from cart.devis_part_backfill import ensure_devis_has_parts
    from messaging.thread import ensure_devis_thread, thread_url

    devis_qs = (
        Devis.objects.filter(patient=user)
        .prefetch_related("parts__organisme")
        .order_by("-created_at")
    )
    entries = []
    for devis in devis_qs:
        ensure_devis_has_parts(devis)
        parts = list(devis.parts.select_related("organisme").order_by("organisme__name", "pk"))
        closed_parent = devis.status in ("expired", "archived")
        rdv_by_part = {}
        for r in (
            RendezVous.objects.filter(devis=devis)
            .exclude(status__in=[RendezVous.STATUS_CANCELLED, RendezVous.STATUS_DECLINED])
            .order_by("-created_at")
        ):
            rdv_by_part.setdefault(r.devis_part_id, r)

        if not parts:
            lines = devis.details or []
            entries.append(
                {
                    "devis": devis,
                    "part": None,
                    "lines": lines,
                    "total_patient": devis.total_patient,
                    "closed": closed_parent,
                    "actions": [],
                    "status_badge": _devis_status_badge(
                        closed=closed_parent, active_rdv=None, can_book=False
                    ),
                }
            )
            continue

        for part in parts:
            part_closed = closed_parent or part.status in ("expired", "archived")
            lines = part.details or []
            if not lines:
                lines = [{}]

            org = part.organisme
            active_rdv = rdv_by_part.get(part.pk)
            conv, _ = ensure_devis_thread(part)
            url = thread_url(conv)
            can_book = has_bookable_hours(org) and not active_rdv

            if can_book:
                url += "?book=1"
                button_text = "Prendre un rendez-vous"
            elif active_rdv:
                if active_rdv.status == RendezVous.STATUS_CONFIRMED:
                    status_label = "confirmé"
                elif active_rdv.status == RendezVous.STATUS_COMPLETED:
                    status_label = "honoré"
                else:
                    status_label = "demandé"
                button_text = f"Messagerie · RDV {status_label}"
            else:
                button_text = "Ouvrir la messagerie"

            part_action = {
                "kind": "message",
                "label": org.name,
                "url": url,
                "button_class": "pac-btn-wa" if can_book else "pac-btn-primary",
                "button_text": button_text,
            }

            for line in lines:
                patient_cost = line.get("patient_cost") or line.get("subtotal") or "0"
                actions = [part_action] if not part_closed else []
                entries.append(
                    {
                        "devis": devis,
                        "part": part,
                        "lines": [line],
                        "total_patient": patient_cost,
                        "closed": part_closed,
                        "actions": actions,
                        "status_badge": _devis_status_badge(
                            closed=part_closed,
                            active_rdv=active_rdv,
                            can_book=can_book,
                        ),
                    }
                )
    return entries


def _assurance_ctx(user, insurance_form=None):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    if insurance_form is None:
        insurance_form = PatientInsuranceForm(instance=profile)
    compatible_orgs = []
    reference_rates = {}
    if profile.insurance_id:
        from healthcare.coverage import reference_rates_for_assurance

        reference_rates = reference_rates_for_assurance(profile.insurance)
        compatible_orgs = (
            OrganismeDeSante.objects.filter(
                is_active=True,
                prises_en_charge__assurance=profile.insurance,
                prises_en_charge__is_active=True,
            )
            .distinct()[:6]
        )
    return {
        "patient_profile": profile,
        "insurance_form": insurance_form,
        "has_insurance": bool(profile.insurance_id),
        "compatible_orgs": compatible_orgs,
        "insurance_reference_rates": reference_rates,
    }


def _accueil_ctx(user):
    rdv = _rdv_ctx(user)
    devis_qs = Devis.objects.filter(patient=user)
    pending = devis_qs.exclude(status__in=("expired", "archived")).count()
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    cart = Cart.objects.filter(patient=user, status="active").prefetch_related(
        "items__prestataire_acte__acte"
    ).first()
    items = list(cart.items.all()) if cart else []
    name = (user.display_name or user.username or "").strip()
    first = name.split()[0] if name else "vous"
    return {
        **rdv,
        "devis_pending_count": pending,
        "insurance_count": 1 if profile.insurance_id else 0,
        "cart_items_count": sum(i.quantity for i in items),
        "first_name": first,
    }


def _recherches_ctx(user):
    return {
        "history": SearchHistory.objects.filter(user=user).order_by("-searched_at")[:50],
    }


def _chariot_ctx(user):
    from cart.insurance_helpers import (
        build_items_with_coverage,
        cart_coverage_totals,
        get_patient_profile,
        profile_uses_insurance_in_estimates,
        resolve_cart_insurance,
        resolve_estimation_insurance,
    )
    from healthcare.utils import assurances_grouped_for_select

    cart = Cart.get_active_cart(user)
    profile = get_patient_profile(user)
    items = list(
        cart.items.select_related(
            "prestataire_acte__acte__parent_service",
            "prestataire_acte__acte__service_medical_category",
            "prestataire_acte__organisme",
        )
    )
    insurance = resolve_cart_insurance(cart, user)
    estimation_insurance = resolve_estimation_insurance(cart, user)
    items_with_coverage = build_items_with_coverage(items, estimation_insurance, profile)
    totals = cart_coverage_totals(cart, estimation_insurance, profile)

    groups_map = {}
    for entry in items_with_coverage:
        item = entry["item"]
        org = item.prestataire_acte.organisme
        bucket = groups_map.setdefault(
            org.pk,
            {"organisme": org, "lines": [], "subtotal": 0, "patient_subtotal": 0},
        )
        bucket["lines"].append(entry)
        bucket["subtotal"] += item.subtotal
        bucket["patient_subtotal"] += entry["patient_cost"]
    cart_groups = sorted(groups_map.values(), key=lambda g: g["organisme"].name.lower())
    cart_in_panier_acte_pks = sorted({item.prestataire_acte.acte_id for item in items})

    return {
        "cart": cart,
        "cart_items": items,
        "cart_items_count": sum(i.quantity for i in items),
        "cart_total": totals["total_brut"],
        "cart_total_assurance": totals["total_assurance"],
        "cart_total_patient": totals["total_patient"],
        "cart_insurance": insurance,
        "cart_estimation_insurance": estimation_insurance,
        "insurance_use_in_estimates": profile_uses_insurance_in_estimates(profile),
        "profile_insurance": profile.insurance if profile else None,
        "assurances_grouped": assurances_grouped_for_select(),
        "cart_groups": cart_groups,
        "items_with_coverage": items_with_coverage,
        "cart_in_panier_acte_pks_json": json.dumps(cart_in_panier_acte_pks),
    }


def _profil_ctx(user, user_form=None, patient_form=None, password_form=None):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return {
        "user_form": user_form or UserProfileForm(instance=user, compte_style=True),
        "patient_form": patient_form or PatientProfileCompteForm(instance=profile),
        "password_form": password_form
        or CustomPasswordChangeForm(user, compte_style=True),
    }


def _render_panel(request, tab: str, template: str, ctx: dict):
    ctx["account_active"] = tab
    ctx["account_page_title"] = PAC_PAGE_TITLES.get(tab, "Mon compte")
    ctx["pac_messages"] = _pac_messages(request)
    return render(request, template, ctx)


def handle_assurance_post(request):
    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    has_ins = request.POST.get("has_insurance") == "1"
    if not has_ins:
        profile.insurance = None
        profile.insurance_number = ""
        profile.insurance_coverage_pct = None
        profile.insurance_coverage_by_category = {}
        profile.save(
            update_fields=[
                "insurance",
                "insurance_number",
                "insurance_coverage_pct",
                "insurance_coverage_by_category",
            ]
        )
        messages.success(request, "Paiement direct enregistré.")
        return _assurance_ctx(request.user)
    form = PatientInsuranceForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
        from cart.models import Cart
        from cart.insurance_helpers import sync_cart_insurance_from_profile

        cart = Cart.objects.filter(patient=request.user, status="active").first()
        if cart:
            cart.insurance_user_override = False
            cart.save(update_fields=["insurance_user_override"])
            sync_cart_insurance_from_profile(cart, request.user)
        messages.success(request, "Votre couverture a été enregistrée.")
        return _assurance_ctx(request.user)
    ctx = _assurance_ctx(request.user, insurance_form=form)
    return ctx


def handle_profil_post(request):
    user = request.user
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    if request.POST.get("save_password"):
        password_form = CustomPasswordChangeForm(
            user, request.POST, compte_style=True
        )
        if password_form.is_valid():
            from django.contrib.auth import update_session_auth_hash

            updated = password_form.save()
            update_session_auth_hash(request, updated)
            messages.success(request, "Mot de passe modifié avec succès.")
            return _profil_ctx(user)
        return _profil_ctx(
            user,
            password_form=password_form,
            user_form=UserProfileForm(instance=user, compte_style=True),
            patient_form=PatientProfileCompteForm(instance=profile),
        )
    user_form = UserProfileForm(
        request.POST, request.FILES, instance=user, compte_style=True
    )
    patient_form = PatientProfileCompteForm(request.POST, instance=profile)
    if user_form.is_valid() and patient_form.is_valid():
        user_form.save()
        patient_form.save()
        messages.success(request, "Profil mis à jour avec succès.")
        return _profil_ctx(user)
    return _profil_ctx(user, user_form=user_form, patient_form=patient_form)


def build_panel_context(request, tab: str):
    if tab == "accueil":
        return _accueil_ctx(request.user)
    if tab == "chariot":
        return _chariot_ctx(request.user)
    if tab == "recherches":
        return _recherches_ctx(request.user)
    if tab == "rdv":
        return _rdv_ctx(request.user)
    if tab == "devis":
        return _devis_ctx(request.user)
    if tab == "assurance":
        if request.method == "POST":
            return handle_assurance_post(request)
        return _assurance_ctx(request.user)
    if tab == "profil":
        if request.method == "POST":
            return handle_profil_post(request)
        return _profil_ctx(request.user)
    return None


def panel_template(tab: str) -> str:
    return f"users/patient_panel/_{tab}.html"


def patient_panel_view(request, tab: str = "accueil"):
    if not request.user.is_authenticated or not request.user.is_patient:
        return HttpResponseForbidden()
    if tab not in PAC_TABS:
        tab = "accueil"
    ctx = build_panel_context(request, tab)
    if ctx is None:
        return HttpResponseForbidden()
    tpl = panel_template(tab)
    if is_panel_request(request):
        return _render_panel(request, tab, tpl, ctx)
    ctx["panel_partial"] = tpl
    ctx["account_active"] = tab
    ctx["account_page_title"] = PAC_PAGE_TITLES.get(tab, "Mon compte")
    ctx["pac_messages"] = _pac_messages(request)
    return render(request, "users/patient_compte_page.html", ctx)


def patient_panel_devis_detail_view(request, ref: str):
    if not request.user.is_authenticated or not request.user.is_patient:
        return HttpResponseForbidden()
    from cart.devis_part_backfill import ensure_devis_has_parts
    from cart.views import wa_group_from_devis_part
    from cart.models import DevisPart
    from django.shortcuts import get_object_or_404

    devis = get_object_or_404(Devis, reference=ref, patient=request.user)
    ensure_devis_has_parts(devis)
    if devis.status in ("draft", "sent"):
        devis.status = "viewed"
        devis.save(update_fields=["status"])
    parts = list(
        DevisPart.objects.filter(devis=devis)
        .select_related("organisme")
        .order_by("organisme__name", "pk")
    )
    from appointments.models import RendezVous
    from appointments.slots import has_bookable_hours
    from messaging.thread import conversation_for_part, thread_url

    rdv_by_part = {}
    for r in (
        RendezVous.objects.filter(devis=devis)
        .exclude(status__in=[RendezVous.STATUS_CANCELLED, RendezVous.STATUS_DECLINED])
        .order_by("-created_at")
    ):
        rdv_by_part.setdefault(r.devis_part_id, r)
    for p in parts:
        p.active_rdv = rdv_by_part.get(p.pk)
        p.can_book = has_bookable_hours(p.organisme)
        conv = conversation_for_part(p)
        p.thread_url = thread_url(conv) if conv else None
        p.wa = None if p.can_book else wa_group_from_devis_part(devis, p)

    # Parcours direct : un seul sous-devis → fil messagerie (créneau si possible).
    if not is_panel_request(request) and len(parts) == 1:
        from django.shortcuts import redirect

        return redirect(
            messaging_url_for_devis_part(parts[0], prefer_book=True)
        )

    single_book = None
    if len(parts) == 1 and parts[0].can_book and not parts[0].active_rdv:
        from appointments.panel import book_data_json

        payload, has_slots = book_data_json(parts[0].organisme, parts[0])
        if has_slots:
            single_book = {"part": parts[0], "book_data_json": payload, "has_slots": True}

    ctx = {
        "devis": devis,
        "devis_parts": parts,
        "single_book": single_book,
        "account_active": "devis",
        "account_page_title": f"Devis {devis.reference}",
        "pac_messages": _pac_messages(request),
    }
    tpl = "users/patient_panel/_devis_detail.html"
    if is_panel_request(request):
        return render(request, tpl, ctx)
    ctx["panel_partial"] = tpl
    return render(request, "users/patient_compte_page.html", ctx)


def redirect_or_panel(request, tab: str):
    """Redirige vers la page courante + ouverture panneau, sauf requête AJAX panneau."""
    if is_panel_request(request):
        return patient_panel_view(request, tab)
    return redirect(panel_redirect(tab))
