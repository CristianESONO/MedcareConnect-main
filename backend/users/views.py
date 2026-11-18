from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .redirect_utils import safe_next_redirect
from .forms import (
    UserRegistrationForm,
    UserProfileForm,
    PatientProfileCompteForm,
    CustomPasswordChangeForm,
)
from .models import PatientProfile
from .patient_panel import (
    is_panel_request,
    panel_redirect,
    patient_panel_view,
    redirect_or_panel,
)
from healthcare.models import OrganismeDeSante, get_default_subscription_plan
from cart.guest_merge import merge_session_cart_into_cart


def _after_patient_login_redirect(request, next_url=None):
    if next_url:
        return redirect(next_url)
    return redirect(panel_redirect("rdv"))


from medcare_connect.views import _home_vitrine_context, react_app


def _wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


def _json_form_errors(form):
    return JsonResponse(
        {"errors": {field: list(errors) for field, errors in form.errors.items()}},
        status=400,
    )


def _json_redirect(response):
    return JsonResponse({"redirect_url": response["Location"]})


def register(request):
    if request.user.is_authenticated:
        if request.user.is_patient:
            response = redirect(panel_redirect("rdv"))
        else:
            response = redirect("home")
        return _json_redirect(response) if _wants_json(request) else response
    if request.method != "POST":
        return react_app(request)

    if request.method == "POST":
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            default_plan = get_default_subscription_plan() if form.cleaned_data.get("user_type") == "prestataire" else None
            if form.cleaned_data.get("user_type") == "prestataire" and not default_plan:
                if _wants_json(request):
                    return JsonResponse(
                        {
                            "errors": {
                                "account": [
                                    "Inscription temporairement indisponible : aucune formule d'abonnement n'est configurée. Contactez l'administrateur."
                                ]
                            }
                        },
                        status=503,
                    )
                messages.error(
                    request,
                    "Inscription temporairement indisponible : aucune formule d'abonnement "
                    "n'est configurée. Contactez l'administrateur.",
                )
                return react_app(request)
            with transaction.atomic():
                user = form.save()
                if user.is_patient:
                    PatientProfile.objects.get_or_create(user=user)
                if user.is_prestataire:
                    d = form.cleaned_data
                    account_nature = d.get("account_nature") or "structure"
                    import json

                    if account_nature == "praticien":
                        raw_spe = d.get("praticien_specialties") or ""
                        if raw_spe.startswith("["):
                            try:
                                spe_list = json.loads(raw_spe)
                            except Exception:
                                spe_list = [s.strip() for s in raw_spe.split(",") if s.strip()]
                        else:
                            spe_list = [s.strip() for s in raw_spe.split(",") if s.strip()]

                        raw_modes = d.get("praticien_modes") or ""
                        modes_list = [m.strip() for m in raw_modes.split(",") if m.strip()]

                        full_name = f"{user.first_name} {user.last_name}".strip()
                        OrganismeDeSante.objects.create(
                            user=user,
                            name=full_name or user.username,
                            account_nature="praticien",
                            is_individual=True,
                            profession=d.get("praticien_profession") or "",
                            ordre_numero=d.get("praticien_ordre") or "",
                            specialties=spe_list,
                            exercise_modes=modes_list,
                            intervention_zone=d.get("praticien_zone") or "",
                            address=d.get("praticien_address") or "Dakar",
                            city=(d.get("praticien_city") or "Dakar").strip(),
                            contact_phone=d.get("praticien_phone") or user.phone_number,
                            contact_email=user.email,
                            logo=d.get("praticien_photo"),
                            subscription_plan=default_plan,
                            is_active=False,
                            is_verified=False,
                        )
                    else:
                        if not user.first_name and d.get("organisme_name"):
                            parts = d["organisme_name"].split()
                            user.first_name = parts[0]
                            user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
                            user.save(update_fields=["first_name", "last_name"])
                        OrganismeDeSante.objects.create(
                            user=user,
                            name=d["organisme_name"],
                            account_nature="structure",
                            is_individual=False,
                            topology_type=d.get("organisme_topology") or "simple",
                            raison_sociale=(d.get("organisme_raison_sociale") or "").strip() or None,
                            ninea=(d.get("organisme_ninea") or "").strip() or None,
                            type_organisme=d.get("organisme_type"),
                            address=d["organisme_address"],
                            quartier=(d.get("organisme_quartier") or "").strip() or None,
                            city=(d.get("organisme_city") or "Dakar").strip(),
                            region=d.get("organisme_region"),
                            contact_phone=d["organisme_contact_phone"],
                            contact_email=(d.get("organisme_contact_email") or user.email or "").strip() or None,
                            logo=d.get("organisme_logo"),
                            subscription_plan=default_plan,
                            is_active=False,
                            is_verified=False,
                        )
            login(request, user)
            messages.success(request, "Inscription réussie ! Bienvenue sur MedCare Connect.")
            if user.is_patient:
                merge_session_cart_into_cart(request, user)
            next_after = safe_next_redirect(request, request.POST.get("next"))
            if user.is_patient and next_after and "chariot" in next_after:
                messages.info(
                    request,
                    "Votre panier a été synchronisé — vous pouvez réserver vos actes.",
                )
            if user.is_prestataire:
                nature_label = "praticien" if form.cleaned_data.get("account_nature") == "praticien" else "établissement"
                messages.info(
                    request,
                    f"Votre compte {nature_label} a été créé avec le nom d'utilisateur : {user.username}. "
                    "Vous pouvez l'utiliser pour vous connecter à tout moment. "
                    "Votre compte sera actif dès validation par l'administrateur.",
                )
                response = redirect("healthcare:prestataire_dashboard")
                return _json_redirect(response) if _wants_json(request) else response
            if user.is_patient:
                if next_after:
                    response = redirect(next_after)
                else:
                    response = _after_patient_login_redirect(request)
                return _json_redirect(response) if _wants_json(request) else response
            response = redirect("home")
            return _json_redirect(response) if _wants_json(request) else response
        if _wants_json(request):
            return _json_form_errors(form)
    return react_app(request)


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_patient:
            response = redirect(panel_redirect("rdv"))
        else:
            response = redirect("home")
        return _json_redirect(response) if _wants_json(request) else response
    if request.method == "POST":
        identifier = (request.POST.get("username") or "").strip()
        password = request.POST.get("password")
        user = authenticate(request, username=identifier, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Connexion réussie !")
            if user.is_patient:
                merge_session_cart_into_cart(request, user)
            next_url = safe_next_redirect(
                request,
                (request.POST.get("next") or request.GET.get("next") or "").strip(),
            )
            if next_url:
                response = redirect(next_url)
            elif user.is_prestataire:
                response = redirect("healthcare:prestataire_dashboard")
            elif user.is_superuser or getattr(user, "is_admin_user", False):
                response = redirect("dashboard:index")
            elif user.is_patient:
                response = _after_patient_login_redirect(request)
            else:
                response = redirect("home")
            return _json_redirect(response) if _wants_json(request) else response
        else:
            if _wants_json(request):
                return JsonResponse(
                    {"errors": {"username": ["Nom d'utilisateur ou mot de passe incorrect."]}},
                    status=400,
                )
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    return react_app(request)


from django.views.decorators.cache import never_cache


@never_cache
def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    response = redirect("login")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@never_cache
@login_required
def patient_account(request):
    if not request.user.is_patient:
        messages.info(request, "L’espace « Mon compte » est réservé aux patients.")
        return redirect("users:profile")
    if is_panel_request(request):
        return patient_panel_view(request, "accueil")
    return redirect(panel_redirect("accueil"))


def patient_panel_react_home(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), login_url=reverse("login"))
    if not request.user.is_patient:
        return HttpResponseForbidden()
    return react_app(request)


@require_GET
def patient_overview_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse({"error": "Cette page est réservée aux patients."}, status=403)

    from .patient_panel import _accueil_ctx

    context = _accueil_ctx(request.user)
    rdv = context["rdv_upcoming"][0] if context["rdv_upcoming"] else None
    return JsonResponse(
        {
            "first_name": context["first_name"],
            "stats": {
                "upcoming_appointments": len(context["rdv_upcoming"]),
                "pending_quotes": context["devis_pending_count"],
                "insurances": context["insurance_count"],
                "cart_items": context["cart_items_count"],
            },
            "next_appointment": (
                {
                    "reference": rdv.reference,
                    "organization": rdv.organisme.name,
                    "start": rdv.start.isoformat(),
                    "status": rdv.get_status_display(),
                    "conversation_url": rdv.thread_url,
                }
                if rdv
                else None
            ),
        }
    )


@require_GET
def patient_quotes_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse({"error": "Cette page est réservée aux patients."}, status=403)

    from .patient_panel import _devis_list_entries

    entries = []
    for entry in _devis_list_entries(request.user):
        devis = entry["devis"]
        part = entry["part"]
        lines = []
        for line in entry["lines"]:
            raw_quantity = line.get("quantity") or 1
            try:
                quantity = max(1, int(raw_quantity))
            except (TypeError, ValueError):
                quantity = 1
            lines.append(
                {
                    "name": str(line.get("acte") or "Acte médical"),
                    "quantity": quantity,
                    "subtotal": str(
                        line.get("subtotal") or line.get("patient_cost") or "0"
                    ),
                }
            )
        action = (entry["actions"] or [None])[0]
        entries.append(
            {
                "reference": part.reference if part else devis.reference,
                "organization": (
                    part.organisme.name
                    if part
                    else str((entry["lines"][0] or {}).get("organisme") or "Devis")
                ),
                "created_at": devis.created_at.isoformat(),
                "status": entry["status_badge"]["label"],
                "status_class": entry["status_badge"]["class"],
                "closed": entry["closed"],
                "lines": lines,
                "total_patient": str(entry["total_patient"] or "0"),
                "action": (
                    {
                        "url": action["url"],
                        "label": action["button_text"],
                    }
                    if action
                    else None
                ),
            }
        )
    return JsonResponse({"entries": entries})


def _patient_insurance_payload(profile, insurance_form, selected_insurance):
    insurance_options = [
        {
            "id": insurance.pk,
            "name": insurance.name,
            "segment": insurance.get_segment_display(),
        }
        for insurance in insurance_form.fields["insurance"].queryset
    ]
    category_rates = [
        {
            "field": name,
            "label": bound_field.label,
            "value": (
                str(bound_field.field.initial)
                if bound_field.field.initial is not None
                else ""
            ),
            "reference": str(
                bound_field.field.widget.attrs.get("placeholder") or ""
            ),
        }
        for name, bound_field in insurance_form.category_rate_fields
    ]
    compatible_structures = []
    if selected_insurance:
        organizations = OrganismeDeSante.objects.filter(
            is_active=True,
            prises_en_charge__assurance=selected_insurance,
            prises_en_charge__is_active=True,
        ).distinct()[:6]
        compatible_structures = [
            {
                "name": organization.name,
                "location": organization.quartier or organization.city,
                "url": reverse("healthcare:organisme_detail", args=[organization.slug]),
            }
            for organization in organizations
        ]

    return {
        "has_insurance": bool(profile.insurance_id),
        "insurance_id": selected_insurance.pk if selected_insurance else None,
        "insurance_name": selected_insurance.name if selected_insurance else "",
        "insurance_number": profile.insurance_number or "",
        "insurance_coverage_pct": (
            str(profile.insurance_coverage_pct)
            if profile.insurance_coverage_pct is not None
            else ""
        ),
        "insurance_use_in_estimates": profile.insurance_use_in_estimates,
        "insurance_options": insurance_options,
        "category_rates": category_rates,
        "compatible_structures": compatible_structures,
    }


@require_http_methods(["GET", "POST"])
def patient_insurance_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse({"error": "Cette page est réservée aux patients."}, status=403)

    from healthcare.models import Assurance
    from .forms import PatientInsuranceForm

    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        if request.POST.get("has_insurance") != "1":
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
        else:
            insurance_form = PatientInsuranceForm(request.POST, instance=profile)
            if not insurance_form.is_valid():
                errors = insurance_form.errors.get_json_data()
                message = " ".join(
                    error["message"]
                    for field_errors in errors.values()
                    for error in field_errors
                )
                return JsonResponse(
                    {"error": message, "errors": errors},
                    status=400,
                )
            insurance_form.save()
            from cart.models import Cart
            from cart.insurance_helpers import sync_cart_insurance_from_profile

            cart = Cart.objects.filter(
                patient=request.user, status="active"
            ).first()
            if cart:
                cart.insurance_user_override = False
                cart.save(update_fields=["insurance_user_override"])
                sync_cart_insurance_from_profile(cart, request.user)

    selected_id = request.GET.get("insurance")
    if selected_id:
        try:
            selected_insurance = Assurance.objects.get(
                pk=int(selected_id), is_active=True
            )
        except (ValueError, Assurance.DoesNotExist):
            return JsonResponse(
                {"error": "Organisme d’assurance invalide."},
                status=400,
            )
        form = PatientInsuranceForm(
            data={"insurance": str(selected_insurance.pk)},
            instance=profile,
        )
    else:
        selected_insurance = profile.insurance
        form = PatientInsuranceForm(instance=profile)

    return JsonResponse(
        _patient_insurance_payload(
            profile, form, selected_insurance
        )
    )


@require_GET
def patient_search_history_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse({"error": "Cette page est réservée aux patients."}, status=403)

    from healthcare.models import SearchHistory
    from urllib.parse import urlencode

    entries = SearchHistory.objects.filter(user=request.user).order_by("-searched_at")[:50]
    return JsonResponse(
        {
            "entries": [
                {
                    "query": entry.query,
                    "results_count": entry.results_count,
                    "searched_at": entry.searched_at.isoformat(),
                    "url": f"{reverse('healthcare:search')}?{urlencode({'q': entry.query})}",
                }
                for entry in entries
            ]
        }
    )


@require_http_methods(["GET", "POST"])
def patient_profile_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse({"error": "Cette page est réservée aux patients."}, status=403)

    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        user_form = UserProfileForm(
            request.POST, request.FILES, instance=request.user, compte_style=True
        )
        patient_form = PatientProfileCompteForm(request.POST, instance=profile)
        if user_form.is_valid() and patient_form.is_valid():
            with transaction.atomic():
                user_form.save()
                patient_form.save()
        else:
            errors = {
                **user_form.errors.get_json_data(),
                **patient_form.errors.get_json_data(),
            }
            return JsonResponse({"errors": errors}, status=400)

    avatar = request.user.avatar
    return JsonResponse(
        {
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "phone_number": request.user.phone_number,
            "avatar_url": avatar.url if avatar and avatar.name else None,
            "date_of_birth": (
                profile.date_of_birth.isoformat() if profile.date_of_birth else ""
            ),
            "address": profile.address,
            "city": profile.city,
            "quartier": profile.quartier or "",
            "last_known_latitude": (
                str(profile.last_known_latitude)
                if profile.last_known_latitude is not None
                else ""
            ),
            "last_known_longitude": (
                str(profile.last_known_longitude)
                if profile.last_known_longitude is not None
                else ""
            ),
        }
    )


@require_POST
def patient_password_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_patient:
        return JsonResponse({"error": "Cette page est réservée aux patients."}, status=403)

    password_form = CustomPasswordChangeForm(
        request.user, request.POST, compte_style=True
    )
    if not password_form.is_valid():
        return JsonResponse(
            {"errors": password_form.errors.get_json_data()}, status=400
        )
    updated_user = password_form.save()
    update_session_auth_hash(request, updated_user)
    return JsonResponse({"ok": True})


@login_required
def patient_assurance(request):
    if not request.user.is_patient:
        messages.info(request, "L’espace « Mon compte » est réservé aux patients.")
        return redirect("users:profile")
    return redirect_or_panel(request, "assurance")


@login_required
def profile(request):
    user = request.user

    if user.is_patient:
        if is_panel_request(request):
            return patient_panel_view(request, "profil")
        if request.method == "POST":
            return patient_panel_view(request, "profil")
        return redirect(panel_redirect("profil"))

    user_form = UserProfileForm(instance=user)
    if request.method == "POST":
        user_form = UserProfileForm(request.POST, request.FILES, instance=user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Profil mis à jour avec succès.")
            return redirect("users:profile")

    return react_app(request)


@require_http_methods(["GET", "POST"])
def user_profile_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if request.user.is_patient:
        return JsonResponse(
            {"error": "Les patients gèrent leur profil depuis leur espace compte."},
            status=403,
        )

    if request.method == "POST":
        user_form = UserProfileForm(
            request.POST, request.FILES, instance=request.user
        )
        if not user_form.is_valid():
            return JsonResponse({"errors": user_form.errors.get_json_data()}, status=400)
        user_form.save()

    avatar = request.user.avatar
    return JsonResponse(
        {
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "phone_number": request.user.phone_number,
            "avatar_url": avatar.url if avatar and avatar.name else None,
        }
    )


@login_required
def change_password(request):
    if request.user.is_patient:
        return redirect(panel_redirect("profil"))
    wants_json = "application/json" in request.headers.get("Accept", "")
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            if wants_json:
                return JsonResponse({"ok": True, "message": "Mot de passe modifié."})
            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect("users:profile")
        if wants_json:
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    return react_app(request)


@ensure_csrf_cookie
@require_GET
def password_reset_page(request, *args, **kwargs):
    return react_app(request)


@require_POST
def password_reset_api(request):
    form = PasswordResetForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    form.save(
        request=request,
        use_https=request.is_secure(),
        from_email=settings.DEFAULT_FROM_EMAIL,
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt",
        html_email_template_name=None,
        token_generator=default_token_generator,
    )
    return JsonResponse(
        {
            "ok": True,
            "message": "Si cette adresse correspond à un compte, un lien de réinitialisation sera envoyé.",
        }
    )


@require_http_methods(["GET", "POST"])
def password_reset_confirm_api(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model()._default_manager.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        return JsonResponse({"error": "Ce lien de réinitialisation est invalide ou expiré."}, status=400)

    if not default_token_generator.check_token(user, token):
        return JsonResponse({"error": "Ce lien de réinitialisation est invalide ou expiré."}, status=400)
    if request.method == "GET":
        return JsonResponse({"valid": True})

    form = SetPasswordForm(user, request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    form.save()
    return JsonResponse({"ok": True, "redirect_url": "/mot-de-passe-oublie/succes/"})
