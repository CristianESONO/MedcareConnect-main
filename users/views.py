from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

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


from medcare_connect.views import _home_vitrine_context


def _register_context(form):
    ctx = _home_vitrine_context()
    ctx["form"] = form
    return ctx


def register(request):
    if request.user.is_authenticated:
        if request.user.is_patient:
            return redirect(panel_redirect("rdv"))
        return redirect("home")
    if request.method == "POST":
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            default_plan = get_default_subscription_plan() if form.cleaned_data.get("user_type") == "prestataire" else None
            if form.cleaned_data.get("user_type") == "prestataire" and not default_plan:
                messages.error(
                    request,
                    "Inscription temporairement indisponible : aucune formule d'abonnement "
                    "n'est configurée. Contactez l'administrateur.",
                )
                return render(request, "users/register.html", _register_context(form))
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
                return redirect("healthcare:prestataire_dashboard")
            if user.is_patient:
                if next_after:
                    return redirect(next_after)
                return _after_patient_login_redirect(request)
            return redirect("home")
    else:
        initial_type = (
            request.GET.get("type")
            or request.GET.get("role")
            or request.GET.get("mode")
            or ""
        ).lower()
        if initial_type in ("prestataire", "structure", "soignant"):
            form = UserRegistrationForm(initial={"user_type": "prestataire"})
        else:
            form = UserRegistrationForm(initial={"user_type": "patient"})
    return render(request, "users/register.html", _register_context(form))


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_patient:
            return redirect(panel_redirect("rdv"))
        return redirect("home")
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
                return redirect(next_url)
            if user.is_prestataire:
                return redirect("healthcare:prestataire_dashboard")
            if user.is_superuser or getattr(user, "is_admin_user", False):
                return redirect("dashboard:index")
            if user.is_patient:
                return _after_patient_login_redirect(request)
            return redirect("home")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    return render(request, "users/login.html")


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

    return render(request, "users/profile.html", {"user_form": user_form})


@login_required
def change_password(request):
    if request.user.is_patient:
        return redirect(panel_redirect("profil"))
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect("users:profile")
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, "users/change_password.html", {"form": form})
