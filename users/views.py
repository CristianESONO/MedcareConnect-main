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
                return render(request, "users/register.html", {"form": form})
            with transaction.atomic():
                user = form.save()
                if user.is_patient:
                    PatientProfile.objects.get_or_create(user=user)
                if user.is_prestataire:
                    d = form.cleaned_data
                    OrganismeDeSante.objects.create(
                        user=user,
                        name=d["organisme_name"],
                        raison_sociale=(d.get("organisme_raison_sociale") or "").strip() or None,
                        ninea=(d.get("organisme_ninea") or "").strip() or None,
                        type_organisme=d["organisme_type"],
                        address=d["organisme_address"],
                        quartier=(d.get("organisme_quartier") or "").strip() or None,
                        city=(d.get("organisme_city") or "Dakar").strip(),
                        region=d.get("organisme_region"),
                        contact_phone=d["organisme_contact_phone"],
                        contact_email=(d.get("organisme_contact_email") or user.email or "").strip() or None,
                        logo=d["organisme_logo"],
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
                messages.info(
                    request,
                    "Votre fiche établissement a été créée. Elle sera visible après validation par un administrateur. "
                    "Vous pouvez compléter vos actes, assurances et localisation précise (GPS) depuis votre tableau de bord.",
                )
                return redirect("healthcare:prestataire_dashboard")
            if user.is_patient:
                if next_after:
                    return redirect(next_after)
                return _after_patient_login_redirect(request)
            return redirect("home")
    else:
        form = UserRegistrationForm()
    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_patient:
            return redirect(panel_redirect("rdv"))
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
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


def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect("home")


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
