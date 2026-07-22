import json
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from users.patient_panel import (
    is_panel_request,
    panel_redirect,
    patient_panel_devis_detail_view,
    patient_panel_view,
)

from .guest_merge import _normalize_guest_items, merge_guest_items_into_cart
from .forms import CartInsuranceSelectForm, GuestInsuranceSelectForm
from .devis_split import build_detail_lines_for_cart_items
from .insurance_helpers import (
    build_items_with_coverage,
    cart_coverage_totals,
    coverage_totals_for_acte_qty_pairs,
    get_patient_profile,
    indicative_coverage_totals_for_acte_qty_pairs,
    profile_uses_insurance_in_estimates,
    resolve_cart_insurance,
    resolve_estimation_insurance,
)
from .models import Cart, CartItem, Devis, DevisPart
from .whatsapp import wa_group_from_devis_part
from healthcare.models import OrganismeDeSante, PrestataireActe, Assurance, PriseEnChargeAssurance
from healthcare.utils import assurances_grouped_for_select


GUEST_CART_SESSION_KEY = "medcare_guest_cart_session_v1"
GUEST_INSURANCE_SESSION_KEY = "medcare_guest_insurance_id_v1"
GUEST_INSURANCE_OPT_OUT_KEY = "medcare_guest_insurance_opt_out_v1"


def _wants_json_response(request) -> bool:
    accept = (request.headers.get("Accept") or "").lower()
    if "application/json" in accept:
        return True
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _cart_total_qty_for_request(request) -> int:
    """Même logique que medcare_connect.context_processors (badge panier)."""
    if request.user.is_authenticated:
        if not getattr(request.user, "is_patient", False):
            return 0
        cart = Cart.objects.filter(patient=request.user, status="active").first()
        return cart.item_count if cart else 0
    mp = _guest_cart_get_map(request)
    return sum(max(0, int(v)) for v in mp.values())


def _guest_cart_get_map(request) -> dict[int, int]:
    raw = request.session.get(GUEST_CART_SESSION_KEY) or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[int, int] = {}
    for k, v in raw.items():
        try:
            pa_id = int(k)
            qty = int(v)
        except (TypeError, ValueError):
            continue
        if pa_id <= 0:
            continue
        out[pa_id] = max(1, min(999, qty))
    return out


def _guest_cart_set_map(request, mp: dict[int, int]) -> None:
    request.session[GUEST_CART_SESSION_KEY] = {
        str(int(k)): int(v)
        for k, v in mp.items()
        if int(k) > 0 and int(v) >= 1
    }
    request.session.modified = True


def _guest_cart_add(request, pa_id: int, qty: int = 1) -> bool:
    """Ajoute une offre au panier invité. Retourne False si l'acte est déjà pris ailleurs."""
    pa_id = int(pa_id)
    try:
        pa = PrestataireActe.objects.get(
            pk=pa_id, is_available=True, organisme__is_active=True
        )
    except PrestataireActe.DoesNotExist:
        return False
    if _guest_cart_has_acte_elsewhere(request, pa.acte_id, pa_id):
        return False
    mp = _guest_cart_get_map(request)
    qty = int(qty)
    mp[pa_id] = max(1, min(999, mp.get(pa_id, 0) + qty))
    _guest_cart_set_map(request, mp)
    return True


def _guest_cart_has_acte_elsewhere(request, acte_id: int, pa_id: int) -> bool:
    mp = _guest_cart_get_map(request)
    if not mp:
        return False
    other_pa_ids = [pid for pid in mp if int(pid) != int(pa_id)]
    if not other_pa_ids:
        return False
    return PrestataireActe.objects.filter(
        pk__in=other_pa_ids, acte_id=acte_id
    ).exists()


def _patient_cart_has_acte_elsewhere(cart, acte_id: int, pa_id: int) -> bool:
    return CartItem.objects.filter(
        cart=cart,
        prestataire_acte__acte_id=acte_id,
    ).exclude(prestataire_acte_id=pa_id).exists()


def _acte_cart_conflict_message(pa: PrestataireActe) -> str:
    return (
        f"« {pa.acte.name} » est déjà dans votre panier pour une autre structure. "
        "Retirez-le d'abord pour le choisir ailleurs."
    )


def _acte_cart_conflict_response(request, pa: PrestataireActe):
    msg = _acte_cart_conflict_message(pa)
    if _wants_json_response(request):
        return JsonResponse(
            {"ok": False, "error": "acte_already_in_cart", "message": msg},
            status=409,
        )
    messages.warning(request, msg)
    next_url = request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("cart:cart_view")


def _guest_cart_clear_all(request) -> None:
    request.session.pop(GUEST_CART_SESSION_KEY, None)
    request.session.pop(GUEST_INSURANCE_SESSION_KEY, None)
    request.session.pop(GUEST_INSURANCE_OPT_OUT_KEY, None)
    request.session.modified = True


def _prestataire_acte_ids_from_request(request) -> list[int]:
    ct = (request.content_type or "").lower()
    if "application/json" in ct:
        try:
            body = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return []
        raw = body.get("prestataire_acte_ids") or body.get("pa_ids") or body.get("actes") or []
    else:
        raw = request.POST.getlist("actes") or request.POST.getlist("pa_id")
    out: list[int] = []
    for x in raw:
        token = str(x or "").strip()
        if token.startswith("pa-"):
            token = token[3:]
        try:
            out.append(int(token))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(out))


def cart_view(request):
    if not request.user.is_authenticated:
        mp = _guest_cart_get_map(request)
        guest_items = []
        guest_total = Decimal(0)
        if mp:
            pas = (
                PrestataireActe.objects.filter(
                    pk__in=list(mp.keys()),
                    is_available=True,
                    organisme__is_active=True,
                )
                .select_related("acte", "organisme", "acte__service_medical_category")
            )
            found = {pa.pk: pa for pa in pas}
            for pa_id, qty in sorted(mp.items()):
                pa = found.get(pa_id)
                if not pa:
                    continue
                sub = pa.price * qty
                guest_total += sub
                guest_items.append({"pa": pa, "qty": qty, "subtotal": sub})

            # Si toutes les lignes sont invalides, on nettoie la session.
            if mp and not guest_items:
                _guest_cart_clear_all(request)

        guest_insurance_id = request.session.get(GUEST_INSURANCE_SESSION_KEY)
        guest_insurance = None
        if guest_insurance_id:
            try:
                guest_insurance = Assurance.objects.get(pk=int(guest_insurance_id), is_active=True)
            except (ValueError, Assurance.DoesNotExist):
                guest_insurance = None
        guest_insurance_form = GuestInsuranceSelectForm(initial={"insurance": guest_insurance})

        # Regroupement par structure (boutons estimation / RDV dans le panier visiteur).
        org_groups_map: dict[int, dict] = {}
        for row in guest_items:
            org = row["pa"].organisme
            bucket = org_groups_map.setdefault(
                org.pk,
                {"organisme": org, "lines": [], "total": Decimal(0), "count": 0},
            )
            bucket["lines"].append(row)
            bucket["total"] += row["subtotal"]
            bucket["count"] += row["qty"]
        guest_org_groups = sorted(
            org_groups_map.values(), key=lambda g: g["organisme"].name.lower()
        )
        cart_items_count = sum(row["qty"] for row in guest_items)
        cart_in_panier_acte_pks = sorted({row["pa"].acte_id for row in guest_items})

        return render(
            request,
            "cart/cart_guest.html",
            {
                "guest_items": guest_items,
                "guest_total": guest_total,
                "guest_org_groups": guest_org_groups,
                "cart_items_count": cart_items_count,
                "cart_in_panier_acte_pks_json": json.dumps(cart_in_panier_acte_pks),
                "guest_insurance_form": guest_insurance_form,
                "assurances_grouped": assurances_grouped_for_select(),
                "guest_selected_insurance_pk": guest_insurance.pk if guest_insurance else None,
                "guest_auth_next": reverse("users:patient_panel_tab", kwargs={"tab": "chariot"}),
            },
        )

    if request.user.is_patient:
        return redirect(panel_redirect("chariot"))

    cart = Cart.get_active_cart(request.user)
    profile = get_patient_profile(request.user)
    insurance = resolve_estimation_insurance(cart, request.user)
    items = cart.items.select_related(
        "prestataire_acte__acte__parent_service",
        "prestataire_acte__acte__service_medical_category",
        "prestataire_acte__organisme",
    )
    items_with_coverage = build_items_with_coverage(items, insurance)

    context = {
        "cart": cart,
        "items_with_coverage": items_with_coverage,
        "assurances_grouped": assurances_grouped_for_select(),
    }
    context["insurance_form"] = CartInsuranceSelectForm(initial={"insurance": insurance})
    return render(request, "cart/cart.html", context)


def _assurance_fallback_ids(request) -> list[int]:
    ids: list[int] = []
    for x in request.GET.getlist("assurance"):
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    return ids


def _resolve_coverage_insurances(request, fallback_ids: list[int]) -> list:
    """Assurances candidates pour l'estimation (profil, panier, invité, filtres URL)."""
    seen: set[int] = set()
    insurances: list[Assurance] = []

    def _add(ins):
        if ins and ins.pk not in seen:
            seen.add(ins.pk)
            insurances.append(ins)

    if request.user.is_authenticated and getattr(request.user, "is_patient", False):
        profile = get_patient_profile(request.user)
        use_in_estimates = profile_uses_insurance_in_estimates(profile)
        cart = Cart.objects.filter(patient=request.user, status="active").first()
        if cart and use_in_estimates:
            _add(resolve_cart_insurance(cart, request.user))
        if profile and profile.insurance_id and use_in_estimates:
            _add(profile.insurance)
    else:
        guest_ins_id = request.session.get(GUEST_INSURANCE_SESSION_KEY)
        if guest_ins_id:
            try:
                _add(
                    Assurance.objects.get(pk=int(guest_ins_id), is_active=True)
                )
            except (Assurance.DoesNotExist, TypeError, ValueError):
                pass

    if fallback_ids:
        for ins in Assurance.objects.filter(pk__in=fallback_ids, is_active=True):
            _add(ins)

    return insurances


def _cart_coverage_payload(request) -> dict | None:
    """Estimation prise en charge / reste à charge pour hydratation JS (recherche prestations)."""
    fallback_ids = _assurance_fallback_ids(request)
    profile = (
        get_patient_profile(request.user)
        if request.user.is_authenticated
        else None
    )
    insurances = _resolve_coverage_insurances(request, fallback_ids)
    if not insurances:
        return None

    pairs: list[tuple] = []

    if request.user.is_authenticated and getattr(request.user, "is_patient", False):
        cart = Cart.objects.filter(patient=request.user, status="active").first()
        if not cart or not cart.items.exists():
            return None
        for row in cart.items.select_related(
            "prestataire_acte__acte__parent_service",
            "prestataire_acte__acte__service_medical_category",
            "prestataire_acte__organisme",
        ):
            pairs.append((row.prestataire_acte, row.quantity))
    else:
        mp = _guest_cart_get_map(request)
        if not mp:
            return None
        pas = (
            PrestataireActe.objects.filter(
                pk__in=list(mp.keys()),
                is_available=True,
                organisme__is_active=True,
            )
            .select_related(
                "acte__parent_service",
                "acte__service_medical_category",
                "organisme",
            )
        )
        pa_by_id = {pa.pk: pa for pa in pas}
        pairs = [
            (pa_by_id[pa_id], qty)
            for pa_id, qty in mp.items()
            if pa_id in pa_by_id
        ]
        if not pairs:
            return None

    totals = indicative_coverage_totals_for_acte_qty_pairs(
        pairs, insurances, profile
    )

    if float(totals["total_assurance"]) <= 0:
        return None

    label = insurances[0].name if len(insurances) == 1 else ", ".join(
        i.name for i in insurances[:3]
    )

    return {
        "insurance_name": label,
        "total_brut": float(totals["total_brut"]),
        "total_assurance": float(totals["total_assurance"]),
        "total_patient": float(totals["total_patient"]),
    }


def _cart_snapshot_items(request) -> list[dict]:
    """Lignes panier pour hydratation JS (popup recherche mobile)."""
    items: list[dict] = []
    if not request.user.is_authenticated:
        mp = _guest_cart_get_map(request)
        if not mp:
            return items
        pas = (
            PrestataireActe.objects.filter(
                pk__in=list(mp.keys()),
                is_available=True,
                organisme__is_active=True,
            )
            .select_related("acte", "organisme")
        )
        for pa in pas:
            items.append(
                {
                    "id": pa.pk,
                    "acte": pa.acte.name,
                    "acte_pk": pa.acte_id,
                    "org": pa.organisme.name,
                    "org_id": pa.organisme_id,
                    "price": float(pa.price),
                    "insOk": True,
                    "qty": mp.get(pa.pk, 1),
                }
            )
        return items

    if not getattr(request.user, "is_patient", False):
        return items

    cart = Cart.objects.filter(patient=request.user, status="active").first()
    if not cart:
        return items
    for row in (
        CartItem.objects.filter(cart=cart)
        .select_related("prestataire_acte__acte", "prestataire_acte__organisme")
        .order_by("pk")
    ):
        pa = row.prestataire_acte
        if not pa.is_available or not pa.organisme.is_active:
            continue
        items.append(
            {
                "id": pa.pk,
                "cart_item_id": row.pk,
                "acte": pa.acte.name,
                "acte_pk": pa.acte_id,
                "org": pa.organisme.name,
                "org_id": pa.organisme_id,
                "price": float(pa.price),
                "insOk": True,
                "qty": row.quantity,
            }
        )
    return items


@require_GET
def cart_snapshot(request):
    """GET — contenu panier session / patient pour le popup mobile."""
    items = _cart_snapshot_items(request)
    return JsonResponse(
        {
            "ok": True,
            "items": items,
            "cart_count": _cart_total_qty_for_request(request),
            "coverage": _cart_coverage_payload(request),
        }
    )


@require_POST
def guest_cart_preview(request):
    """Hydrate les lignes panier invité (JSON) pour affichage — sans authentification."""
    try:
        data = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide."}, status=400)
    raw = data.get("items") or []
    if len(raw) > 100:
        return JsonResponse({"error": "Trop de lignes."}, status=400)

    merged = _normalize_guest_items(raw)
    if not merged:
        return JsonResponse({"items": [], "invalid_pa_ids": [], "total": "0"})

    pas = (
        PrestataireActe.objects.filter(
            pk__in=list(merged.keys()),
            is_available=True,
            organisme__is_active=True,
        )
        .select_related("acte", "organisme")
    )
    found = {pa.pk: pa for pa in pas}
    lines = []
    invalid = [pk for pk in merged if pk not in found]
    total = Decimal(0)
    for pa_id, qty in sorted(merged.items()):
        if pa_id not in found:
            continue
        pa = found[pa_id]
        sub = pa.price * qty
        total += sub
        lines.append({
            "pa_id": pa_id,
            "acte": pa.acte.name,
            "organisme": pa.organisme.name,
            "price": str(pa.price),
            "qty": qty,
            "subtotal": str(sub),
        })
    return JsonResponse({
        "items": lines,
        "invalid_pa_ids": invalid,
        "total": str(total),
    })


@login_required
@require_POST
def cart_merge_guest(request):
    """Fusionne le panier localStorage dans le panier serveur (comptes patient)."""
    if not request.user.is_patient:
        return JsonResponse({"error": "Réservé aux comptes patient."}, status=403)
    try:
        data = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide."}, status=400)
    raw = data.get("items") or []
    if len(raw) > 120:
        return JsonResponse({"error": "Trop de lignes."}, status=400)
    insurance_id = data.get("insurance_id")
    touched, line_count = merge_guest_items_into_cart(
        request.user, raw, insurance_id=insurance_id
    )
    return JsonResponse({
        "ok": True,
        "merged_distinct": touched,
        "cart_item_count": line_count,
        "cart_line_count": line_count,
    })


@require_POST
def cart_add_bundle(request):
    """Ajoute plusieurs offres (parcours d'examens) au panier d'un coup."""
    ids = _prestataire_acte_ids_from_request(request)
    if not ids:
        if "application/json" in (request.content_type or "").lower():
            return JsonResponse({"error": "Aucune offre sélectionnée."}, status=400)
        messages.warning(request, "Aucune offre à ajouter.")
        return redirect("healthcare:bundle_planner")

    found = {
        pa.id: pa
        for pa in PrestataireActe.objects.filter(
            pk__in=ids, is_available=True, organisme__is_active=True
        ).select_related("acte", "organisme")
    }
    ordered = [found[i] for i in ids if i in found]
    if len(ordered) != len(ids):
        if "application/json" in (request.content_type or "").lower():
            return JsonResponse(
                {"error": "Certaines offres sont invalides ou indisponibles."}, status=400
            )
        messages.error(request, "Certaines offres ne sont plus disponibles.")
        return redirect("healthcare:bundle_planner")

    # Visiteur : stockage session (pas de login requis).
    if not request.user.is_authenticated:
        for pa in ordered:
            if _guest_cart_has_acte_elsewhere(request, pa.acte_id, pa.pk):
                if "application/json" in (request.content_type or "").lower():
                    return JsonResponse(
                        {
                            "ok": False,
                            "error": "acte_already_in_cart",
                            "message": _acte_cart_conflict_message(pa),
                        },
                        status=409,
                    )
                messages.warning(request, _acte_cart_conflict_message(pa))
                return redirect("healthcare:bundle_planner")
            _guest_cart_add(request, pa.pk, 1)
        if "application/json" in (request.content_type or "").lower():
            return JsonResponse({"ok": True, "added": len(ordered), "cart_url": "/cart/"})
        messages.success(request, f"{len(ordered)} prestation(s) ajoutée(s) au panier (visiteur).")
        return redirect("cart:cart_view")

    cart = Cart.get_active_cart(request.user)
    added = 0
    for pa in ordered:
        if _patient_cart_has_acte_elsewhere(cart, pa.acte_id, pa.pk):
            if "application/json" in (request.content_type or "").lower():
                return JsonResponse(
                    {
                        "ok": False,
                        "error": "acte_already_in_cart",
                        "message": _acte_cart_conflict_message(pa),
                    },
                    status=409,
                )
            messages.warning(request, _acte_cart_conflict_message(pa))
            return redirect("healthcare:bundle_planner")
        existing = CartItem.objects.filter(cart=cart, prestataire_acte=pa).first()
        if existing:
            existing.quantity += 1
            existing.save(update_fields=["quantity"])
        else:
            CartItem.objects.create(cart=cart, prestataire_acte=pa, quantity=1)
        added += 1

    if "application/json" in (request.content_type or "").lower():
        return JsonResponse({"ok": True, "added": added, "cart_url": "/cart/"})

    messages.success(request, f"{added} prestation(s) ajoutée(s) au panier.")
    return redirect("cart:cart_view")


@login_required
@require_POST
def cart_fiche_request_devis(request):
    """Fiche prestataire : synchronise la sélection d'actes puis renvoie l'URL messagerie."""
    if not getattr(request.user, "is_patient", False):
        return JsonResponse(
            {"ok": False, "error": "Seuls les patients peuvent demander un devis via MedCare."},
            status=403,
        )

    org_slug = (request.POST.get("org_slug") or "").strip()
    if not org_slug:
        return JsonResponse({"ok": False, "error": "Structure introuvable."}, status=400)

    org = get_object_or_404(OrganismeDeSante, slug=org_slug, is_active=True)
    pa_ids = _prestataire_acte_ids_from_request(request)
    if not pa_ids:
        return JsonResponse(
            {"ok": False, "error": "Sélectionnez au moins un acte pour demander un devis."},
            status=400,
        )

    pas = PrestataireActe.objects.filter(
        pk__in=pa_ids,
        organisme=org,
        is_available=True,
    )
    if not pas.exists():
        return JsonResponse(
            {"ok": False, "error": "Actes invalides ou indisponibles."},
            status=400,
        )

    cart = Cart.get_active_cart(request.user)
    cart.items.exclude(prestataire_acte__organisme=org).delete()
    valid_pks = set(pas.values_list("pk", flat=True))
    cart.items.filter(prestataire_acte__organisme=org).exclude(
        prestataire_acte_id__in=valid_pks
    ).delete()
    for pa in pas:
        CartItem.objects.get_or_create(
            cart=cart,
            prestataire_acte=pa,
            defaults={"quantity": 1},
        )

    redirect_url = reverse("users:patient_panel_tab", kwargs={"tab": "chariot"})
    return JsonResponse({"ok": True, "redirect": redirect_url})


def cart_add(request, pk):
    pa = get_object_or_404(
        PrestataireActe,
        pk=pk,
        is_available=True,
        organisme__is_active=True,
    )

    if not request.user.is_authenticated:
        if _guest_cart_has_acte_elsewhere(request, pa.acte_id, pa.pk):
            return _acte_cart_conflict_response(request, pa)
        if not _guest_cart_add(request, pa.pk, 1):
            return _acte_cart_conflict_response(request, pa)
        if _wants_json_response(request):
            return JsonResponse(
                {
                    "ok": True,
                    "prestataire_acte_id": pa.pk,
                    "cart_count": _cart_total_qty_for_request(request),
                    "coverage": _cart_coverage_payload(request),
                }
            )
        messages.success(request, f"« {pa.acte.name} » ajouté au panier (visiteur).")
        next_url = request.GET.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("cart:cart_view")

    cart = Cart.get_active_cart(request.user)
    if _patient_cart_has_acte_elsewhere(cart, pa.acte_id, pa.pk):
        return _acte_cart_conflict_response(request, pa)
    existing = CartItem.objects.filter(cart=cart, prestataire_acte=pa).first()
    if existing:
        existing.quantity += 1
        existing.save(update_fields=["quantity"])
        cart_item = existing
        messages.info(request, f"Quantité mise à jour pour « {pa.acte.name} ».")
    else:
        cart_item = CartItem.objects.create(cart=cart, prestataire_acte=pa, quantity=1)
        messages.success(request, f"« {pa.acte.name} » ajouté au panier.")
    if _wants_json_response(request):
        return JsonResponse(
            {
                "ok": True,
                "prestataire_acte_id": pa.pk,
                "cart_item_id": cart_item.pk,
                "cart_count": _cart_total_qty_for_request(request),
                "coverage": _cart_coverage_payload(request),
            }
        )
    next_url = request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("cart:cart_view")


@require_POST
def cart_remove_pa(request, pa_id: int):
    """Retire une offre (PrestataireActe) du panier — visiteur (session) ou patient."""
    wants_json = _wants_json_response(request)
    try:
        pa_id = int(pa_id)
    except (TypeError, ValueError):
        if wants_json:
            return JsonResponse({"ok": False, "error": "invalid_id"}, status=400)
        return redirect("cart:cart_view")

    if not request.user.is_authenticated:
        mp = _guest_cart_get_map(request)
        mp.pop(pa_id, None)
        _guest_cart_set_map(request, mp)
    else:
        cart = Cart.get_active_cart(request.user)
        CartItem.objects.filter(cart=cart, prestataire_acte_id=pa_id).delete()

    if wants_json:
        return JsonResponse(
            {
                "ok": True,
                "prestataire_acte_id": pa_id,
                "cart_count": _cart_total_qty_for_request(request),
                "coverage": _cart_coverage_payload(request),
            }
        )
    return redirect("cart:cart_view")


@require_POST
def guest_cart_remove(request, pa_id: int):
    if request.user.is_authenticated:
        return redirect("cart:cart_view")
    mp = _guest_cart_get_map(request)
    mp.pop(int(pa_id), None)
    _guest_cart_set_map(request, mp)
    return redirect("cart:cart_view")


@require_POST
def guest_cart_update_quantity(request, pa_id: int):
    if request.user.is_authenticated:
        return redirect("cart:cart_view")
    mp = _guest_cart_get_map(request)
    qty = request.POST.get("quantity", 1)
    try:
        qty = max(1, min(999, int(qty)))
    except (ValueError, TypeError):
        qty = 1
    if int(pa_id) in mp:
        mp[int(pa_id)] = qty
        _guest_cart_set_map(request, mp)
    return redirect("cart:cart_view")


@require_POST
def guest_cart_select_insurance(request):
    if request.user.is_authenticated:
        return redirect("cart:cart_view")
    form = GuestInsuranceSelectForm(request.POST)
    if form.is_valid():
        ass = form.cleaned_data.get("insurance")
        if ass:
            request.session[GUEST_INSURANCE_SESSION_KEY] = ass.pk
            request.session.pop(GUEST_INSURANCE_OPT_OUT_KEY, None)
        else:
            request.session.pop(GUEST_INSURANCE_SESSION_KEY, None)
            request.session[GUEST_INSURANCE_OPT_OUT_KEY] = True
    request.session.modified = True
    return redirect("cart:cart_view")


@require_POST
def guest_cart_clear(request):
    if request.user.is_authenticated:
        return redirect("cart:cart_view")
    _guest_cart_clear_all(request)
    messages.info(request, "Panier vidé.")
    return redirect("cart:cart_view")


@login_required
def cart_remove(request, pk):
    cart = Cart.get_active_cart(request.user)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    item.delete()
    messages.success(request, "Article retiré du panier.")
    return redirect("cart:cart_view")


@login_required
def cart_update_quantity(request, pk):
    cart = Cart.get_active_cart(request.user)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    qty = request.POST.get("quantity", 1)
    try:
        qty = max(1, int(qty))
    except (ValueError, TypeError):
        qty = 1
    item.quantity = qty
    item.save(update_fields=["quantity"])
    return redirect("cart:cart_view")


@login_required
def cart_select_insurance(request):
    from users.patient_panel import panel_redirect

    cart = Cart.get_active_cart(request.user)
    form = CartInsuranceSelectForm(request.POST)
    if form.is_valid():
        cart.selected_insurance = form.cleaned_data.get("insurance")
        cart.insurance_user_override = True
    cart.save(update_fields=["selected_insurance", "insurance_user_override"])
    if getattr(request.user, "is_patient", False):
        return redirect(panel_redirect("chariot"))
    return redirect("cart:cart_view")


@login_required
def cart_clear(request):
    cart = Cart.get_active_cart(request.user)
    cart.items.all().delete()
    cart.selected_insurance = None
    cart.insurance_user_override = False
    cart.save(update_fields=["selected_insurance", "insurance_user_override"])
    messages.info(request, "Panier vidé.")
    return redirect("cart:cart_view")


@login_required
def generate_devis(request):
    cart = Cart.get_active_cart(request.user)
    insurance = resolve_estimation_insurance(cart, request.user)
    profile = get_patient_profile(request.user)
    items_qs = cart.items.select_related(
        "prestataire_acte__acte__parent_service",
        "prestataire_acte__acte__service_medical_category",
        "prestataire_acte__organisme",
    )
    if not items_qs.exists():
        messages.warning(request, "Votre panier est vide.")
        if request.user.is_patient:
            return redirect(panel_redirect("chariot"))
        return redirect("cart:cart_view")

    raw_org_id = request.GET.get("org") or request.GET.get("organisme")
    raw_item_id = request.GET.get("item") or request.GET.get("cart_item")
    if not raw_item_id and not raw_org_id:
        messages.info(
            request,
            "Choisissez une structure dans votre panier pour prendre rendez-vous.",
        )
        if request.user.is_patient:
            return redirect(panel_redirect("chariot"))
        return redirect("cart:cart_view")

    selected_items = []
    organisme = None
    if raw_org_id:
        try:
            org_id = int(raw_org_id)
        except (TypeError, ValueError):
            org_id = None
        if org_id is not None:
            selected_items = list(
                items_qs.filter(prestataire_acte__organisme_id=org_id).order_by("pk")
            )
    else:
        try:
            item_id = int(raw_item_id)
        except (TypeError, ValueError):
            item_id = None
        item = items_qs.filter(pk=item_id).first() if item_id is not None else None
        if item:
            selected_items = [item]

    if not selected_items:
        messages.warning(request, "Actes introuvables dans le panier.")
        if request.user.is_patient:
            return redirect(panel_redirect("chariot"))
        return redirect("cart:cart_view")

    organisme = selected_items[0].prestataire_acte.organisme
    part_details, total_brut, total_assurance, total_patient = (
        build_detail_lines_for_cart_items(selected_items, insurance, patient_profile=profile)
    )

    from notifications.dispatcher import dispatch as _notify
    from messaging.thread import ensure_devis_thread, thread_url

    with transaction.atomic():
        devis = Devis.objects.create(
            cart=cart,
            patient=request.user,
            insurance=insurance,
            total_brut=total_brut,
            total_assurance=total_assurance,
            total_patient=total_patient,
            details=part_details,
            valid_until=timezone.now().date() + timedelta(days=30),
            status="sent",
        )
        part = DevisPart.objects.create(
            devis=devis,
            organisme=organisme,
            details=part_details,
            total_brut=total_brut,
            total_assurance=total_assurance,
            total_patient=total_patient,
            status="sent",
        )
        conv, _ = ensure_devis_thread(part)
        link_patient = thread_url(conv)
        link_presta = link_patient
        _notify(
            "devis.created",
            context={
                "devis": devis,
                "devis_part": part,
                "patient": request.user,
                "organisme": organisme,
                "link": link_presta,
                "link_patient": link_patient,
                "link_prestataire": link_presta,
            },
            actor=getattr(organisme, "user", None),
        )
        item_ids = [item.pk for item in selected_items]
        cart.items.filter(pk__in=item_ids).delete()
        if not cart.items.exists():
            cart.status = "converted"
            cart.save(update_fields=["status"])

    acte_count = len(part_details)
    acte_label = part_details[0]["acte"] if acte_count == 1 else f"{acte_count} actes"
    messages.success(
        request,
        f"Demande envoyée pour {acte_label} chez « {organisme.name} » — prenez rendez-vous dans la messagerie.",
    )
    if request.user.is_patient:
        from users.patient_panel import redirect_url_after_devis_generated

        return redirect(
            redirect_url_after_devis_generated(
                devis, prefer_organisme_id=organisme.pk
            )
        )
    return redirect("cart:devis_detail", ref=devis.reference)


@login_required
def devis_detail(request, ref):
    from .devis_part_backfill import ensure_devis_has_parts

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
    devis_parts_wa = [(p, wa_group_from_devis_part(devis, p)) for p in parts]
    ctx = {
        "devis": devis,
        "devis_parts": parts,
        "devis_parts_wa": devis_parts_wa,
    }
    if request.user.is_patient:
        if is_panel_request(request):
            return patient_panel_devis_detail_view(request, ref)
        if len(parts) == 1:
            from users.patient_panel import messaging_url_for_devis_part

            return redirect(messaging_url_for_devis_part(parts[0], prefer_book=True))
        return redirect(panel_redirect("devis", devis_ref=ref))
    return render(request, "cart/devis_detail.html", ctx)


@login_required
def devis_list(request):
    devis = (
        Devis.objects.filter(patient=request.user)
        .prefetch_related("parts__organisme")
        .order_by("-created_at")
    )
    ctx = {"devis_list": devis}
    if request.user.is_patient:
        if is_panel_request(request):
            return patient_panel_view(request, "devis")
        return redirect(panel_redirect("devis"))
    return render(request, "cart/devis_list.html", ctx)


@login_required
def cart_history(request):
    carts = Cart.objects.filter(patient=request.user).exclude(status="active").order_by("-updated_at")
    ctx = {"carts": carts}
    if request.user.is_patient:
        return redirect(panel_redirect("rdv"))
    return render(request, "cart/history.html", ctx)
