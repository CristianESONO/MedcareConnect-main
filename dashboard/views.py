import json

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, F, Min, Prefetch, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from datetime import timedelta

from .decorators import superadmin_required
from .models import ComplianceChecklistSettings
from .forms import (
    ActeMedicalForm,
    AssuranceForm,
    RdvReminderScheduleForm,
    ServiceMedicalForm,
    SubscriptionFeatureForm,
    SubscriptionPlanForm,
)
from users.models import User, PatientProfile
from appointments.models import RdvReminderSchedule, RendezVous
from healthcare.models import (
    ActeMedical,
    Assurance,
    OrganismeDeSante,
    PlatformReview,
    ServiceMedical,
    SubscriptionChangeRequest,
    SubscriptionFeature,
    SubscriptionPlan,
    SubscriptionPlanFeature,
)
from cart.models import Cart, Devis
from messaging.models import Message, Notification, Conversation


_PERIODS = {
    "7j": ("7 derniers jours", 7),
    "30j": ("30 derniers jours", 30),
    "M0": ("Depuis M0 (origine)", None),
}


def _series(qs, date_field, days, key="day"):
    """Retourne (labels[], values[]) sur `days` derniers jours (None = depuis l'origine)."""
    now = timezone.now()
    if days is None:
        first = qs.aggregate(first=Min(date_field))["first"]
        if first is None:
            days = 30
        else:
            delta = (now - first).days
            days = max(7, min(delta + 1, 90))
    start = now - timedelta(days=days - 1)
    raw = (
        qs.filter(**{f"{date_field}__gte": start.replace(hour=0, minute=0, second=0, microsecond=0)})
        .annotate(**{key: TruncDate(date_field)})
        .values(key)
        .annotate(n=Count("id"))
        .order_by(key)
    )
    by_day = {row[key]: row["n"] for row in raw}
    labels, values = [], []
    cur = start.date()
    end = now.date()
    while cur <= end:
        labels.append(cur.strftime("%d/%m"))
        values.append(by_day.get(cur, 0))
        cur += timedelta(days=1)
    return labels, values


@superadmin_required
def index(request):
    period = request.GET.get("period") or "7j"
    if period not in _PERIODS:
        period = "7j"
    period_label, period_days = _PERIODS[period]

    now = timezone.now()
    if period_days is None:
        period_start = OrganismeDeSante.objects.aggregate(first=Min("created_at"))["first"] or now - timedelta(days=30)
    else:
        period_start = now - timedelta(days=period_days)

    # ── KPIs période ───────────────────────────────────────────────────────────
    structures_actives = OrganismeDeSante.objects.filter(is_active=True).count()
    nouv_structures = OrganismeDeSante.objects.filter(created_at__gte=period_start, is_active=True).count()
    patients_periode = User.objects.filter(user_type="patient", date_joined__gte=period_start).count()
    devis_periode = Devis.objects.filter(created_at__gte=period_start).count()
    devis_total = Devis.objects.count()
    valeur_periode = Devis.objects.filter(created_at__gte=period_start).aggregate(s=Sum("total_brut"))["s"] or 0

    rdv_base = RendezVous.objects.all()
    rdv_confirmed_period = rdv_base.filter(confirmed_at__gte=period_start).count()
    rdv_confirmed_upcoming = rdv_base.filter(
        status=RendezVous.STATUS_CONFIRMED, start__gte=now
    ).count()
    rdv_confirmed_total = rdv_base.filter(status=RendezVous.STATUS_CONFIRMED).count()
    rdv_no_show = rdv_base.filter(status=RendezVous.STATUS_NO_SHOW).count()
    rdv_closed = rdv_base.filter(
        status__in=(RendezVous.STATUS_COMPLETED, RendezVous.STATUS_NO_SHOW)
    ).count()
    rdv_no_show_pct = round(100 * rdv_no_show / rdv_closed, 1) if rdv_closed else 0

    # ── KPIs fixes plateforme ──────────────────────────────────────────────────
    actes_total = ActeMedical.objects.count()
    pioneer_plans = SubscriptionPlan.objects.filter(is_pioneer_offer=True).values_list("id", flat=True)
    pioneer_orgs = OrganismeDeSante.objects.filter(subscription_plan__in=pioneer_plans).count()
    PIONEER_TARGET = 50
    slots_pionniers_restants = max(0, PIONEER_TARGET - pioneer_orgs)
    mrr_actuel = (
        SubscriptionPlan.objects.annotate(n=Count("organismes"))
        .aggregate(t=Sum(F("monthly_price_fcfa") * F("n")))
    )["t"] or 0

    # ── Listes d'appui ─────────────────────────────────────────────────────────
    pending_organismes = (
        OrganismeDeSante.objects.filter(is_active=False)
        .select_related("user", "type_organisme")
        .order_by("-created_at")[:6]
    )
    recent_users = User.objects.order_by("-date_joined")[:5]
    services_repartition = (
        ServiceMedical.objects.annotate(n=Count("acts", distinct=True))
        .order_by("-n")[:6]
    )

    # ── Graphique multi-variables ──────────────────────────────────────────────
    chart_days = period_days or 30
    labels, devis_series = _series(Devis.objects.all(), "created_at", chart_days)
    _, patients_series = _series(User.objects.filter(user_type="patient"), "date_joined", chart_days)
    _, structures_series = _series(OrganismeDeSante.objects.all(), "created_at", chart_days)
    valeur_raw = (
        Devis.objects.filter(created_at__gte=now - timedelta(days=chart_days - 1))
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(s=Sum("total_brut"))
        .order_by("day")
    )
    valeur_by_day = {r["day"]: int(r["s"] or 0) for r in valeur_raw}
    valeur_series = []
    cur = (now - timedelta(days=chart_days - 1)).date()
    end = now.date()
    while cur <= end:
        valeur_series.append(valeur_by_day.get(cur, 0))
        cur += timedelta(days=1)

    # ── Structures pour la carte Sénégal ───────────────────────────────────────
    map_orgs = []
    for o in OrganismeDeSante.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)[:200]:
        map_orgs.append({
            "id": o.id,
            "name": o.name,
            "type": str(o.type_organisme) if o.type_organisme_id else "",
            "city": o.city or "",
            "lat": float(o.latitude),
            "lng": float(o.longitude),
            "active": bool(o.is_active),
            "url": f"/healthcare/{o.slug}/",
        })

    context = {
        "period": period,
        "period_label": period_label,
        "periods": list(_PERIODS.items()),
        "show_bilan_btn": period == "M0",

        "kpi_structures_actives": structures_actives,
        "kpi_structures_nouv": nouv_structures,
        "kpi_patients": patients_periode,
        "kpi_devis": devis_periode,
        "kpi_devis_total": devis_total,
        "kpi_valeur": valeur_periode,
        "kpi_rdv_confirmed": rdv_confirmed_period,
        "kpi_rdv_confirmed_total": rdv_confirmed_total,
        "kpi_rdv_confirmed_upcoming": rdv_confirmed_upcoming,
        "kpi_rdv_no_show_pct": rdv_no_show_pct,
        "kpi_actes_total": actes_total,
        "kpi_pioneer_orgs": pioneer_orgs,
        "kpi_pioneer_target": PIONEER_TARGET,
        "kpi_pioneer_restants": slots_pionniers_restants,
        "kpi_mrr_actuel": mrr_actuel,

        "pending_organismes": pending_organismes,
        "recent_users": recent_users,
        "services_repartition": services_repartition,

        "chart_labels_json": json.dumps(labels),
        "chart_devis_json": json.dumps(devis_series),
        "chart_patients_json": json.dumps(patients_series),
        "chart_structures_json": json.dumps(structures_series),
        "chart_valeur_json": json.dumps(valeur_series),

        "map_orgs_json": json.dumps(map_orgs),
        "map_count_active": sum(1 for o in map_orgs if o["active"]),
        "map_count_pending": sum(1 for o in map_orgs if not o["active"]),
    }
    return render(request, "dashboard/index.html", context)


# ─── Users ────────────────────────────────────────────────────────────────────

@superadmin_required
def users_list(request):
    qs = User.objects.all().order_by("-date_joined")
    user_type = request.GET.get("type")
    search = request.GET.get("q", "").strip()
    if user_type in ("patient", "prestataire", "admin"):
        qs = qs.filter(user_type=user_type)
    if search:
        qs = qs.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "dashboard/users_list.html", {
        "page": page,
        "current_type": user_type,
        "search": search,
    })


@superadmin_required
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    status = "activé" if user.is_active else "désactivé"
    messages.success(request, f"L'utilisateur {user.username} a été {status}.")
    return redirect("dashboard:users_list")


# ─── Prestataires / Organismes ────────────────────────────────────────────────

@superadmin_required
def organismes_list(request):
    qs = OrganismeDeSante.objects.select_related(
        "user", "type_organisme", "region"
    ).order_by("-created_at")

    status = request.GET.get("status")
    search = request.GET.get("q", "").strip()
    if status == "pending":
        qs = qs.filter(is_active=False)
    elif status == "active":
        qs = qs.filter(is_active=True)
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(city__icontains=search))

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "dashboard/organismes_list.html", {
        "page": page,
        "current_status": status,
        "search": search,
    })


@superadmin_required
def organisme_detail(request, pk):
    org = get_object_or_404(
        OrganismeDeSante.objects.select_related(
            "user", "type_organisme", "region", "subscription_plan"
        ),
        pk=pk,
    )
    from cart.models import DevisPart

    bilan = _bilan_score_org(org)
    recent_rdv = (
        RendezVous.objects.filter(organisme=org)
        .select_related("patient", "devis")
        .order_by("-start")[:8]
    )
    recent_parts = (
        DevisPart.objects.filter(organisme=org)
        .exclude(status="draft")
        .select_related("devis", "devis__patient")
        .order_by("-created_at")[:8]
    )
    recent_conv = (
        Conversation.objects.filter(
            Q(devis_part__organisme=org) | Q(rendez_vous__organisme=org)
        )
        .select_related("patient", "prestataire", "devis_part", "rendez_vous")
        .distinct()
        .order_by("-updated_at")[:8]
    )
    stats = {
        "rdv_total": RendezVous.objects.filter(organisme=org).count(),
        "rdv_pending": RendezVous.objects.filter(
            organisme=org, status=RendezVous.STATUS_REQUESTED
        ).count(),
        "devis_parts": DevisPart.objects.filter(organisme=org).exclude(status="draft").count(),
        "conversations": Conversation.objects.filter(
            Q(devis_part__organisme=org) | Q(rendez_vous__organisme=org)
        ).distinct().count(),
    }
    return render(
        request,
        "dashboard/organisme_detail.html",
        {
            "org": org,
            "bilan": bilan,
            "recent_rdv": recent_rdv,
            "recent_parts": recent_parts,
            "recent_conv": recent_conv,
            "stats": stats,
        },
    )


@superadmin_required
def organisme_approve(request, pk):
    org = get_object_or_404(OrganismeDeSante, pk=pk)
    org.is_active = True
    org.is_verified = True
    org.save(update_fields=["is_active", "is_verified"])
    try:
        from notifications.dispatcher import dispatch as _notify
        _notify(
            "organisme.approved",
            context={"organisme": org, "link": f"/healthcare/{org.slug}/"},
            actor=org.user,
        )
    except Exception:
        pass
    messages.success(request, f"« {org.name} » a été approuvé.")
    return redirect("dashboard:organismes_list")


@superadmin_required
def organisme_reject(request, pk):
    org = get_object_or_404(OrganismeDeSante, pk=pk)
    org.is_active = False
    org.is_verified = False
    org.save(update_fields=["is_active", "is_verified"])
    try:
        from notifications.dispatcher import dispatch as _notify
        _notify(
            "organisme.rejected",
            context={"organisme": org, "link": "/healthcare/prestataire/"},
            actor=org.user,
        )
    except Exception:
        pass
    messages.warning(request, f"« {org.name} » a été rejeté.")
    return redirect("dashboard:organismes_list")


# ─── Services & Actes ─────────────────────────────────────────────────────────

@superadmin_required
def services_list(request):
    services = ServiceMedical.objects.annotate(
        actes_count=Count("acts"),
    ).order_by("order", "name")
    return render(request, "dashboard/services_list.html", {"services": services})


@superadmin_required
def assurances_list(request):
    assurances = Assurance.objects.annotate(
        providers_count=Count("prises_en_charge__organisme", distinct=True),
    ).order_by("segment", "name")
    return render(request, "dashboard/assurances_list.html", {"assurances": assurances})


# ─── Modération avis ──────────────────────────────────────────────────────────

@superadmin_required
def reviews_list(request):
    qs = (
        PlatformReview.objects.select_related("patient")
        .prefetch_related("actes__service_medical_category")
        .order_by("-created_at")
    )
    status = request.GET.get("status")
    if status == "pending":
        qs = qs.filter(is_approved=False)
    elif status == "approved":
        qs = qs.filter(is_approved=True)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "dashboard/reviews_list.html", {
        "page": page,
        "current_status": status,
    })


@superadmin_required
def review_approve(request, pk):
    review = get_object_or_404(PlatformReview, pk=pk)
    review.is_approved = True
    review.save(update_fields=["is_approved"])
    try:
        from notifications.dispatcher import dispatch as _notify

        _notify(
            "review.approved",
            context={
                "review": review,
                "organisme": None,
                "patient": review.patient,
                "link": reverse("healthcare:platform_review"),
            },
            actor=review.patient,
        )
    except Exception:
        pass
    messages.success(request, "Avis approuvé.")
    return redirect("dashboard:reviews_list")


@superadmin_required
def review_delete(request, pk):
    review = get_object_or_404(PlatformReview, pk=pk)
    review.delete()
    messages.success(request, "Avis supprimé.")
    return redirect("dashboard:reviews_list")


# ─── Référentiel : Services médicaux (CRUD) ───────────────────────────────────

@superadmin_required
def service_create(request):
    if request.method == "POST":
        form = ServiceMedicalForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Service médical créé.")
            return redirect("dashboard:services_list")
    else:
        form = ServiceMedicalForm()
    return render(request, "dashboard/service_form.html", {"form": form, "title": "Nouveau service médical"})


@superadmin_required
def service_edit(request, pk):
    service = get_object_or_404(ServiceMedical, pk=pk)
    if request.method == "POST":
        form = ServiceMedicalForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service médical mis à jour.")
            return redirect("dashboard:services_list")
    else:
        form = ServiceMedicalForm(instance=service)
    return render(
        request,
        "dashboard/service_form.html",
        {"form": form, "title": f"Modifier : {service.name}", "object": service},
    )


@superadmin_required
@require_POST
def service_delete(request, pk):
    service = get_object_or_404(ServiceMedical, pk=pk)
    n_actes = service.acts.count()
    name = service.name
    service.delete()
    messages.success(
        request,
        f"Service « {name} » supprimé ({n_actes} acte(s) associé(s) supprimé(s) en cascade).",
    )
    return redirect("dashboard:services_list")


# ─── Référentiel : Actes médicaux (CRUD) ──────────────────────────────────────

@superadmin_required
def actes_list(request):
    qs = ActeMedical.objects.select_related(
        "service_medical_category", "parent_service"
    ).order_by("service_medical_category__order", "service_medical_category__name", "level", "name")
    service_id_raw = request.GET.get("service")
    service_filter_id = None
    if service_id_raw:
        try:
            service_filter_id = int(service_id_raw)
            qs = qs.filter(service_medical_category_id=service_filter_id)
        except (TypeError, ValueError):
            pass
    search = request.GET.get("q", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))

    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get("page"))
    services = ServiceMedical.objects.order_by("order", "name")
    return render(
        request,
        "dashboard/actes_list.html",
        {
            "page": page,
            "services": services,
            "current_service_id": service_filter_id,
            "search": search,
        },
    )


@superadmin_required
def acte_create(request):
    initial = {}
    svc = request.GET.get("service")
    if svc:
        try:
            initial["service_medical_category"] = int(svc)
        except (TypeError, ValueError):
            pass
    if request.method == "POST":
        form = ActeMedicalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Acte médical créé.")
            return redirect("dashboard:actes_list")
    else:
        form = ActeMedicalForm(initial=initial)
    return render(request, "dashboard/acte_form.html", {"form": form, "title": "Nouvel acte médical"})


@superadmin_required
def acte_edit(request, pk):
    acte = get_object_or_404(ActeMedical, pk=pk)
    if request.method == "POST":
        form = ActeMedicalForm(request.POST, instance=acte)
        if form.is_valid():
            form.save()
            messages.success(request, "Acte médical mis à jour.")
            return redirect("dashboard:actes_list")
    else:
        form = ActeMedicalForm(instance=acte)
    return render(
        request,
        "dashboard/acte_form.html",
        {"form": form, "title": f"Modifier : {acte.name}", "object": acte},
    )


@superadmin_required
@require_POST
def acte_delete(request, pk):
    acte = get_object_or_404(ActeMedical, pk=pk)
    n_offers = acte.prestataire_actes.count()
    name = acte.name
    acte.delete()
    messages.success(
        request,
        f"Acte « {name} » supprimé ({n_offers} offre(s) prestataire supprimée(s) en cascade).",
    )
    return redirect("dashboard:actes_list")


# ─── Référentiel : Assurances (CRUD) ──────────────────────────────────────────

@superadmin_required
def assurance_create(request):
    if request.method == "POST":
        form = AssuranceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Assurance créée.")
            return redirect("dashboard:assurances_list")
    else:
        form = AssuranceForm()
    return render(request, "dashboard/assurance_form.html", {"form": form, "title": "Nouvelle assurance"})


@superadmin_required
def assurance_edit(request, pk):
    assurance = get_object_or_404(Assurance, pk=pk)
    if request.method == "POST":
        form = AssuranceForm(request.POST, request.FILES, instance=assurance)
        if form.is_valid():
            form.save()
            messages.success(request, "Assurance mise à jour.")
            return redirect("dashboard:assurances_list")
    else:
        form = AssuranceForm(instance=assurance)
    return render(
        request,
        "dashboard/assurance_form.html",
        {"form": form, "title": f"Modifier : {assurance.name}", "object": assurance},
    )


@superadmin_required
@require_POST
def assurance_delete(request, pk):
    assurance = get_object_or_404(Assurance, pk=pk)
    name = assurance.name
    assurance.delete()
    messages.success(request, f"Assurance « {name} » supprimée.")
    return redirect("dashboard:assurances_list")


# ─── Abonnements : fonctionnalités + formules ────────────────────────────────


@superadmin_required
def subscription_features_list(request):
    features = SubscriptionFeature.objects.annotate(
        plans_count=Count("plan_features", distinct=True),
    ).order_by("order", "label")
    return render(
        request,
        "dashboard/subscription_features_list.html",
        {"features": features},
    )


@superadmin_required
def subscription_feature_create(request):
    if request.method == "POST":
        form = SubscriptionFeatureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Fonctionnalité créée.")
            return redirect("dashboard:subscription_features_list")
    else:
        form = SubscriptionFeatureForm()
    return render(
        request,
        "dashboard/subscription_feature_form.html",
        {"form": form, "title": "Nouvelle fonctionnalité (droit)"},
    )


@superadmin_required
def subscription_feature_edit(request, pk):
    feat = get_object_or_404(SubscriptionFeature, pk=pk)
    if request.method == "POST":
        form = SubscriptionFeatureForm(request.POST, instance=feat)
        if form.is_valid():
            form.save()
            messages.success(request, "Fonctionnalité mise à jour.")
            return redirect("dashboard:subscription_features_list")
    else:
        form = SubscriptionFeatureForm(instance=feat)
    return render(
        request,
        "dashboard/subscription_feature_form.html",
        {
            "form": form,
            "title": f"Modifier : {feat.label}",
            "object": feat,
        },
    )


@superadmin_required
@require_POST
def subscription_feature_delete(request, pk):
    feat = get_object_or_404(SubscriptionFeature, pk=pk)
    label = feat.label
    feat.delete()
    messages.success(request, f"Fonctionnalité « {label} » supprimée (retrait des formules).")
    return redirect("dashboard:subscription_features_list")


@superadmin_required
def subscription_plans_list(request):
    from healthcare.subscription_admin import admin_assignable_plans_qs
    from healthcare.subscription_display import (
        build_subscription_display_context,
        prefetch_plan_features_queryset,
    )

    plans = (
        admin_assignable_plans_qs()
        .annotate(
            organismes_count=Count("organismes", distinct=True),
        )
        .prefetch_related(
            Prefetch("plan_features", queryset=prefetch_plan_features_queryset())
        )
    )
    pending_requests = SubscriptionChangeRequest.objects.filter(status="pending").count()
    ctx = build_subscription_display_context(plans)
    ctx.update({"plans": plans, "pending_requests": pending_requests})
    return render(request, "dashboard/subscription_plans_list.html", ctx)


@superadmin_required
def subscription_plan_create(request):
    if request.method == "POST":
        form = SubscriptionPlanForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                plan = form.save()
                if plan.is_default:
                    SubscriptionPlan.objects.exclude(pk=plan.pk).update(is_default=False)
            messages.success(request, "Formule créée.")
            return redirect("dashboard:subscription_plans_list")
    else:
        form = SubscriptionPlanForm()
    ctx = _subscription_plan_form_context(
        request, form=form, plan=None, title="Nouvelle formule d'abonnement"
    )
    return render(request, "dashboard/subscription_plan_form.html", ctx)


@superadmin_required
def subscription_plan_edit(request, pk):
    from healthcare.subscription_display import prefetch_plan_features_queryset

    plan = get_object_or_404(
        SubscriptionPlan.objects.prefetch_related(
            Prefetch("plan_features", queryset=prefetch_plan_features_queryset())
        ),
        pk=pk,
    )
    title = f"Modifier : {plan.name}"
    if request.method == "POST":
        form = SubscriptionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            with transaction.atomic():
                plan = form.save()
                if plan.is_default:
                    SubscriptionPlan.objects.exclude(pk=plan.pk).update(is_default=False)
            messages.success(request, "Formule mise à jour.")
            return redirect("dashboard:subscription_plans_list")
    else:
        form = SubscriptionPlanForm(instance=plan)
    ctx = _subscription_plan_form_context(request, form=form, plan=plan, title=title)
    return render(request, "dashboard/subscription_plan_form.html", ctx)


def _subscription_plan_form_context(request, form=None, plan=None, title=""):
    from healthcare.subscription_display import (
        build_feature_groups_for_form,
        build_plan_included_map,
        plan_structures,
    )

    features = list(SubscriptionFeature.objects.order_by("order", "label"))
    if request.method == "POST" and request.POST:
        included_feature_ids = {
            int(x) for x in request.POST.getlist("included_features") if x.isdigit()
        }
    elif plan and plan.pk:
        included_feature_ids = set(
            SubscriptionPlanFeature.objects.filter(
                plan=plan, included=True
            ).values_list("feature_id", flat=True)
        )
    else:
        included_feature_ids = set()

    preview_plan = None
    preview_plan_included = {}
    preview_structures = []
    if plan and plan.pk:
        preview_plan = plan
        preview_plan_included = build_plan_included_map([plan])
        preview_structures = plan_structures(plan)

    return {
        "form": form,
        "title": title,
        "object": plan,
        "feature_groups": build_feature_groups_for_form(),
        "subscription_features_all": features,
        "included_feature_ids": included_feature_ids,
        "preview_plan": preview_plan,
        "preview_plan_included": preview_plan_included,
        "preview_structures": preview_structures,
    }


@superadmin_required
@require_POST
def subscription_plan_delete(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk)
    name = plan.name
    try:
        plan.delete()
    except ProtectedError:
        messages.error(
            request,
            f"Impossible de supprimer « {name} » : une ou plusieurs structures utilisent encore cette formule. "
            "Réassignez-les dans l'admin Django ou modifiez leur formule avant suppression.",
        )
        return redirect("dashboard:subscription_plans_list")
    messages.success(request, f"Formule « {name} » supprimée.")
    return redirect("dashboard:subscription_plans_list")


# ─── Sprint B · Abonnements v2 — vue d'ensemble ───────────────────────────────

@superadmin_required
def subscriptions_overview(request):
    """Page admin v2 : KPIs + tableau structures avec dropdown plan inline + cartes config par plan."""
    from healthcare.subscription_admin import admin_assignable_plans_qs

    today = timezone.now().date()
    in_30_days = today + timedelta(days=30)

    plans = admin_assignable_plans_qs().annotate(
        orgs_count=Count("organismes", distinct=True)
    )
    features = SubscriptionFeature.objects.order_by("order", "label")

    plan_filter = request.GET.get("plan") or "all"
    qs = (
        OrganismeDeSante.objects.select_related("subscription_plan", "type_organisme")
        .order_by("name")
    )
    if plan_filter == "expire":
        qs = qs.filter(subscription_renewal_at__isnull=False, subscription_renewal_at__lte=in_30_days)
    elif plan_filter == "inactif":
        qs = qs.filter(is_active=False)
    elif plan_filter == "pionnier":
        qs = qs.filter(subscription_plan__is_pioneer_offer=True)
    elif plan_filter and plan_filter != "all":
        qs = qs.filter(subscription_plan__slug=plan_filter)

    organismes = list(qs)

    plans_actifs = OrganismeDeSante.objects.filter(is_active=True).count()
    expire_30j = OrganismeDeSante.objects.filter(
        subscription_renewal_at__isnull=False,
        subscription_renewal_at__lte=in_30_days,
    ).count()
    upgrade_pending = SubscriptionChangeRequest.objects.filter(status="pending").count()
    mrr_actuel = (
        admin_assignable_plans_qs()
        .annotate(n=Count("organismes"))
        .aggregate(t=Sum(F("monthly_price_fcfa") * F("n")))
    )["t"] or 0

    # Pré-calcul matrice plan → set(feature_id inclus)
    inclusions = {p.pk: set() for p in plans}
    for pf in SubscriptionPlanFeature.objects.filter(included=True).values("plan_id", "feature_id"):
        inclusions.setdefault(pf["plan_id"], set()).add(pf["feature_id"])

    plan_cards = []
    for p in plans:
        plan_cards.append({
            "obj": p,
            "included_ids": inclusions.get(p.pk, set()),
        })

    context = {
        "plans": plans,
        "features": features,
        "organismes": organismes,
        "plan_filter": plan_filter,
        "kpi_actifs": plans_actifs,
        "kpi_expire": expire_30j,
        "kpi_upgrade": upgrade_pending,
        "kpi_mrr": mrr_actuel,
        "in_30_days": in_30_days,
        "plan_cards": plan_cards,
    }
    return render(request, "dashboard/subscriptions_overview.html", context)


@superadmin_required
@require_POST
def subscription_assign_plan(request, org_pk):
    """Change le plan d'un organisme ou active / désactive la structure."""
    from healthcare.subscription_admin import (
        PLAN_ACTION_DEACTIVATE,
        admin_assignable_plans_qs,
        is_admin_assignable_plan,
    )

    org = get_object_or_404(OrganismeDeSante, pk=org_pk)
    plan_slug = (request.POST.get("plan_slug") or "").strip()
    redirect_url = f"{reverse('dashboard:subscriptions_overview')}?plan={request.POST.get('current_filter', 'all')}"

    if not plan_slug:
        messages.error(request, "Aucune formule sélectionnée.")
        return redirect(redirect_url)

    if plan_slug == PLAN_ACTION_DEACTIVATE:
        if org.is_active:
            org.is_active = False
            org.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"« {org.name} » désactivée — profil non visible dans l'annuaire.")
        else:
            messages.info(request, f"« {org.name} » est déjà inactive.")
        return redirect(redirect_url)

    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug)
    if not is_admin_assignable_plan(plan):
        messages.error(request, "Cette formule n'est plus disponible.")
        return redirect(redirect_url)

    update_fields = []
    if org.subscription_plan_id != plan.pk:
        org.subscription_plan = plan
        update_fields.append("subscription_plan")
        if not org.subscription_started_at:
            org.subscription_started_at = timezone.now().date()
            update_fields.append("subscription_started_at")
    if not org.is_active:
        org.is_active = True
        update_fields.append("is_active")

    if update_fields:
        org.save(update_fields=update_fields + ["updated_at"])
        parts = [f"formule {plan.name}"]
        if "is_active" in update_fields:
            parts.append("structure réactivée")
        messages.success(request, f"« {org.name} » — {' · '.join(parts)}.")
    return redirect(redirect_url)


# ─── Sprint F · Données & Conformité CDP ─────────────────────────────────────

COMPLIANCE_CHECKLIST = [
    {
        "key": "hebergement_souverain",
        "label": "Hébergement souverain",
        "suggested": True,
        "detail": "Données hébergées sur infrastructure dédiée localisée au Sénégal (à confirmer pour la mise en prod finale).",
    },
    {
        "key": "chiffrement_tls",
        "label": "Chiffrement des données en transit (TLS)",
        "suggested": True,
        "detail": "HTTPS forcé sur tous les domaines via reverse-proxy Nginx + Let's Encrypt.",
    },
    {
        "key": "mots_de_passe_hash",
        "label": "Chiffrement des mots de passe",
        "suggested": True,
        "detail": "Hashing PBKDF2-SHA256 (configuration Django par défaut) ; aucun mot de passe stocké en clair.",
    },
    {
        "key": "logs_audit_admin",
        "label": "Logs d'audit (admin Django)",
        "suggested": True,
        "detail": "Toutes les actions effectuées dans l'admin Django (création, modification, suppression) sont historisées.",
    },
    {
        "key": "droit_oubli",
        "label": "Droit à l'oubli (suppression de compte)",
        "suggested": False,
        "detail": "À implémenter : auto-service côté patient pour demander la suppression de son compte (RGPD-like).",
    },
    {
        "key": "registre_traitements",
        "label": "Registre des traitements (loi 2008-12)",
        "suggested": False,
        "detail": "À documenter : registre listant chaque traitement de données personnelles, finalité, durée de conservation.",
    },
    {
        "key": "declaration_cdp",
        "label": "Déclaration CDP (loi 2008-12)",
        "suggested": False,
        "detail": "Démarche administrative à initier auprès de la Commission de protection des données personnelles du Sénégal.",
    },
    {
        "key": "politique_confidentialite",
        "label": "Politique de confidentialité publiée",
        "suggested": False,
        "detail": "Page publique à créer (URL `/legal/privacy/`) listant les engagements MedCare.",
    },
]


@superadmin_required
def conformite(request):
    """Statut conformité CDP (loi 2008-12) + cases à cocher persistées + logs d'audit."""
    from django.contrib.admin.models import LogEntry

    solo = ComplianceChecklistSettings.get_solo()
    stored = solo.checks if isinstance(solo.checks, dict) else {}

    if request.method == "POST" and request.POST.get("action") == "save_checklist":
        new_checks = {}
        for row in COMPLIANCE_CHECKLIST:
            k = row["key"]
            # hidden 0 + checkbox 1 : getlast retourne "1" si coché
            raw = request.POST.get(k, "0")
            new_checks[k] = raw in ("1", "true", "on", "yes")
        solo.checks = new_checks
        solo.save(update_fields=["checks", "updated_at"])
        messages.success(request, "Checklist conformité enregistrée.")
        return redirect("dashboard:conformite")

    statut = []
    for row in COMPLIANCE_CHECKLIST:
        k = row["key"]
        ok = stored.get(k)
        if ok is None:
            ok = bool(row["suggested"])
        statut.append({
            "key": k,
            "label": row["label"],
            "detail": row["detail"],
            "suggested": row["suggested"],
            "ok": ok,
        })

    nb_ok = sum(1 for s in statut if s["ok"])

    logs = (
        LogEntry.objects.select_related("user", "content_type")
        .order_by("-action_time")[:30]
    )

    context = {
        "statut": statut,
        "nb_ok": nb_ok,
        "nb_total": len(statut),
        "logs": logs,
        "checklist_updated_at": solo.updated_at,
    }
    return render(request, "dashboard/conformite.html", context)


# ─── Sprint E · Pionniers + Bilans KPI M5 ────────────────────────────────────

PIONEER_TARGET = 50


def _bilan_score_org(org):
    """Réplique simplifiée du score Pionnier (cf. healthcare.views.prestataire_bilan)."""
    from cart.models import Devis
    from healthcare.models import PrestataireActe, PriseEnChargeAssurance

    devis_total = (
        Devis.objects.filter(
            cart__items__prestataire_acte__organisme=org,
            status__in=["sent", "viewed", "relanced"],
        )
        .distinct()
        .count()
    )
    actes_count = PrestataireActe.objects.filter(organisme=org).count()
    insurances_count = PriseEnChargeAssurance.objects.filter(organisme=org).count()
    completion_items = [
        bool(org.description),
        bool(org.contact_phone or org.whatsapp_number),
        bool(org.logo),
        actes_count > 0,
        insurances_count > 0,
        bool(org.latitude and org.longitude),
    ]
    completion_pct = int(round(sum(1 for x in completion_items if x) * 100.0 / len(completion_items)))
    score = min(
        100,
        round(
            min(devis_total, 30) * 1.5
            + min(org.profile_views_count, 500) * 0.05
            + completion_pct * 0.4
        ),
    )
    if score >= 70:
        signal = ("green", "Excellent")
        reco = "Plan recommandé M6 : Pro"
    elif score >= 35:
        signal = ("amber", "Encourageant")
        reco = "Plan recommandé M6 : Essentiel"
    else:
        signal = ("red", "À améliorer")
        reco = "Plan recommandé M6 : Pionnier (offre découverte)"
    return {
        "score": score,
        "signal": signal[0],
        "signal_label": signal[1],
        "reco": reco,
        "devis_total": devis_total,
        "actes_count": actes_count,
        "insurances_count": insurances_count,
        "completion_pct": completion_pct,
    }


@superadmin_required
def pioneers_overview(request):
    """Suivi des slots Pionniers CPP-2025 (50 max)."""
    pionniers = (
        OrganismeDeSante.objects.filter(subscription_plan__is_pioneer_offer=True)
        .select_related("subscription_plan", "type_organisme")
        .order_by("-created_at")
    )
    n_signed = pionniers.count()
    n_actifs = pionniers.filter(is_active=True).count()
    n_pending = pionniers.filter(is_active=False).count()
    onboarding_pioneer_orgs = pionniers.filter(profile_views_count__lt=10).count()
    progress_pct = min(100, int(round(n_signed * 100.0 / max(PIONEER_TARGET, 1))))

    rows = []
    for idx, p in enumerate(pionniers, start=1):
        ref = f"CPP-{p.created_at.year}-{p.id:03d}"
        b = _bilan_score_org(p)
        rows.append({
            "ref": ref,
            "org": p,
            "signal": b["signal"],
            "signal_label": b["signal_label"],
            "score": b["score"],
            "actes": b["actes_count"],
        })

    context = {
        "pioneer_target": PIONEER_TARGET,
        "n_signed": n_signed,
        "n_actifs": n_actifs,
        "n_pending": n_pending,
        "n_onboarding": onboarding_pioneer_orgs,
        "n_remaining": max(0, PIONEER_TARGET - n_signed),
        "progress_pct": progress_pct,
        "rows": rows,
    }
    return render(request, "dashboard/pioneers_overview.html", context)


@superadmin_required
def bilans_overview(request):
    """Bilans KPI M5 — vue consolidée admin."""
    organismes = (
        OrganismeDeSante.objects.filter(is_active=True)
        .select_related("subscription_plan", "type_organisme")
        .order_by("name")
    )
    rows = []
    counts = {"green": 0, "amber": 0, "red": 0}
    for o in organismes:
        b = _bilan_score_org(o)
        counts[b["signal"]] = counts.get(b["signal"], 0) + 1
        rows.append({"org": o, **b})
    rows.sort(key=lambda r: r["score"], reverse=True)
    context = {
        "rows": rows,
        "counts": counts,
        "total": len(rows),
    }
    return render(request, "dashboard/bilans_overview.html", context)


# ─── Sprint D · Finances & MRR ────────────────────────────────────────────────

@superadmin_required
def finances(request):
    """Page Finances & MRR : projections sur 3 scénarios à partir des plans actifs."""
    today = timezone.now().date()

    plans = (
        SubscriptionPlan.objects.annotate(orgs_count=Count("organismes"))
        .order_by("order", "name")
    )
    plan_rows = []
    mrr_actuel = 0
    for p in plans:
        sub = p.monthly_price_fcfa * p.orgs_count
        mrr_actuel += sub
        plan_rows.append({
            "plan": p,
            "subtotal": sub,
        })

    arr_an1 = mrr_actuel * 12

    # Scénarios BIZ-ECO-001 (lecture seule) — projection sur 12 mois à partir de M0.
    # Hypothèses : Pessimiste +2%/mois, Médian +6%/mois, Optimiste +12%/mois.
    growth = {"pessimiste": 0.02, "median": 0.06, "optimiste": 0.12}
    months = list(range(0, 13))  # M0 à M12
    scenarios = {}
    for label, rate in growth.items():
        series = []
        cur = float(mrr_actuel) if mrr_actuel else 100000.0
        for _ in months:
            series.append(int(cur))
            cur *= (1.0 + rate)
        scenarios[label] = series

    # Frais de service 500F (placeholder — actif à M6)
    frais_service = 0

    context = {
        "plan_rows": plan_rows,
        "kpi_mrr": mrr_actuel,
        "kpi_arr": arr_an1,
        "kpi_frais": frais_service,
        "kpi_conv_estim": "65 %",
        "months_json": json.dumps([f"M{m}" for m in months]),
        "scenarios_json": json.dumps(scenarios),
        "today": today,
    }
    return render(request, "dashboard/finances.html", context)


# ─── Sprint C · Devis WA admin ────────────────────────────────────────────────

@superadmin_required
def devis_overview(request):
    """Registre consolidé plateforme des devis WA."""
    status_filter = (request.GET.get("status") or "all").strip()
    valid = {"all", "sent", "viewed", "relanced", "expired", "archived"}
    if status_filter not in valid:
        status_filter = "all"
    search = (request.GET.get("q") or "").strip()

    qs = (
        Devis.objects.exclude(status="draft")
        .select_related("patient", "insurance", "cart")
        .annotate(parts_count=Count("parts", distinct=True))
        .order_by("-created_at")
    )
    if status_filter != "all":
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(
            Q(reference__icontains=search)
            | Q(patient__username__icontains=search)
            | Q(patient__email__icontains=search)
            | Q(patient__first_name__icontains=search)
            | Q(patient__last_name__icontains=search)
        )

    base_qs = Devis.objects.exclude(status="draft").annotate(parts_count=Count("parts", distinct=True))
    counts = {
        "all": base_qs.count(),
        "sent": base_qs.filter(status="sent").count(),
        "viewed": base_qs.filter(status="viewed").count(),
        "relanced": base_qs.filter(status="relanced").count(),
        "expired": base_qs.filter(status="expired").count(),
        "archived": base_qs.filter(status="archived").count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    rows = []
    for d in page.object_list:
        org_names = []
        if d.cart_id:
            for it in d.cart.items.select_related("prestataire_acte__organisme"):
                if it.prestataire_acte and it.prestataire_acte.organisme:
                    n = it.prestataire_acte.organisme.name
                    if n not in org_names:
                        org_names.append(n)
        rows.append({"d": d, "org_names": org_names, "parts_count": getattr(d, "parts_count", 0)})

    valeur_total = base_qs.aggregate(s=Sum("total_brut"))["s"] or 0
    accept_count = base_qs.filter(status="viewed").count()
    pending_count = base_qs.filter(status__in=["sent", "viewed"]).count()
    expired_count = base_qs.filter(status="expired").count()

    context = {
        "rows": rows,
        "page": page,
        "status_filter": status_filter,
        "search": search,
        "counts": counts,
        "kpi_total": counts["all"],
        "kpi_accept": accept_count,
        "kpi_pending": pending_count,
        "kpi_expired": expired_count,
        "kpi_valeur": valeur_total,
    }
    return render(request, "dashboard/devis_overview.html", context)


@superadmin_required
def devis_admin_detail(request, reference):
    from cart.models import DevisPart

    devis = get_object_or_404(
        Devis.objects.select_related("patient", "insurance", "cart")
        .prefetch_related(
            Prefetch(
                "parts",
                queryset=DevisPart.objects.select_related("organisme").order_by(
                    "organisme__name"
                ),
            )
        ),
        reference=reference,
    )
    parts_data = []
    for part in devis.parts.all():
        conv = Conversation.objects.filter(devis_part=part).first()
        rdv = RendezVous.objects.filter(devis_part=part).order_by("-created_at").first()
        parts_data.append({"part": part, "conversation": conv, "rdv": rdv})
    org_names = []
    for line in devis.details or []:
        n = line.get("organisme")
        if n and n not in org_names:
            org_names.append(n)
    return render(
        request,
        "dashboard/devis_admin_detail.html",
        {
            "devis": devis,
            "parts_data": parts_data,
            "org_names": org_names,
        },
    )


@superadmin_required
@require_POST
def devis_admin_relance(request, reference):
    """Relance : sur chaque sous-devis si présents, sinon sur le devis parent (legacy)."""
    devis = get_object_or_404(Devis.objects.prefetch_related("parts"), reference=reference)
    parts = list(devis.parts.all())
    if parts:
        relanced = 0
        for p in parts:
            if p.can_relance():
                p.mark_relance(by_user=request.user)
                relanced += 1
        if relanced:
            messages.success(
                request,
                f"{relanced} sous-devis relancé(s) pour le devis {devis.reference}.",
            )
        else:
            messages.warning(request, f"Aucun sous-devis relançable pour {devis.reference}.")
    elif not devis.can_relance():
        if devis.is_archived:
            messages.warning(request, f"Devis {devis.reference} déjà archivé.")
        else:
            messages.warning(request, f"Devis {devis.reference} : relances épuisées.")
    else:
        devis.mark_relance(by_user=request.user)
        msg = f"Devis {devis.reference} relancé ({devis.relance_count}/{devis.MAX_RELANCES})."
        if devis.is_archived:
            msg += " Archivage automatique appliqué."
        messages.success(request, msg)
    return redirect("dashboard:devis_admin_detail", reference=reference)


@superadmin_required
@require_POST
def devis_admin_archive(request, reference):
    devis = get_object_or_404(Devis.objects.prefetch_related("parts"), reference=reference)
    if devis.is_archived:
        messages.info(request, f"Devis {devis.reference} déjà archivé.")
    else:
        for p in devis.parts.all():
            if not p.is_archived:
                p.archive(reason="Archivé par admin")
        devis.archive(reason="Archivé par admin")
        messages.success(request, f"Devis {devis.reference} et sous-devis archivés.")
    return redirect("dashboard:devis_admin_detail", reference=reference)


@superadmin_required
@require_POST
def subscription_toggle_feature(request, plan_pk, feature_pk):
    """Toggle l'inclusion d'un droit dans une formule. Retourne JSON ou redirige."""
    from healthcare.subscription_admin import is_admin_assignable_plan

    plan = get_object_or_404(SubscriptionPlan, pk=plan_pk)
    if not is_admin_assignable_plan(plan):
        messages.error(request, "Cette formule n'est plus configurable.")
        return redirect("dashboard:subscriptions_overview")
    feature = get_object_or_404(SubscriptionFeature, pk=feature_pk)
    pf, _ = SubscriptionPlanFeature.objects.get_or_create(plan=plan, feature=feature)
    pf.included = not pf.included
    pf.save(update_fields=["included"])
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        from django.http import JsonResponse
        return JsonResponse({"ok": True, "included": pf.included})
    messages.success(
        request,
        f"« {feature.label} » {'activé' if pf.included else 'désactivé'} pour « {plan.name} ».",
    )
    return redirect("dashboard:subscriptions_overview")


# ─── Activité plateforme · Vue 360° ───────────────────────────────────────────


def _activite_kpis():
    """KPIs consolidés devis + RDV + messagerie."""
    now = timezone.now()
    since_7d = now - timedelta(days=7)

    devis_base = Devis.objects.exclude(status="draft")
    rdv_base = RendezVous.objects.all()
    conv_base = Conversation.objects.all()

    return {
        "devis_total": devis_base.count(),
        "devis_pending": devis_base.filter(status__in=["sent", "viewed"]).count(),
        "devis_expired": devis_base.filter(status="expired").count(),
        "devis_valeur": devis_base.aggregate(s=Sum("total_brut"))["s"] or 0,
        "rdv_total": rdv_base.count(),
        "rdv_requested": rdv_base.filter(status=RendezVous.STATUS_REQUESTED).count(),
        "rdv_confirmed_upcoming": rdv_base.filter(
            status=RendezVous.STATUS_CONFIRMED, start__gte=now
        ).count(),
        "rdv_completed_7d": rdv_base.filter(
            status=RendezVous.STATUS_COMPLETED, updated_at__gte=since_7d
        ).count(),
        "rdv_no_show": rdv_base.filter(status=RendezVous.STATUS_NO_SHOW).count(),
        "conv_total": conv_base.count(),
        "conv_active": conv_base.filter(thread_status=Conversation.STATUS_ACTIVE).count(),
        "conv_waiting": conv_base.filter(thread_status=Conversation.STATUS_WAITING).count(),
        "conv_devis": conv_base.filter(kind=Conversation.KIND_DEVIS).count(),
        "conv_rdv": conv_base.filter(kind=Conversation.KIND_RDV).count(),
        "messages_7d": Message.objects.filter(timestamp__gte=since_7d).count(),
    }


@superadmin_required
def activite_overview(request):
    """Hub activité patient ↔ plateforme (devis, RDV, messagerie)."""
    kpis = _activite_kpis()
    recent_devis = (
        Devis.objects.exclude(status="draft")
        .select_related("patient")
        .order_by("-created_at")[:6]
    )
    recent_rdv = (
        RendezVous.objects.select_related("patient", "organisme", "devis")
        .order_by("-created_at")[:6]
    )
    recent_conv = (
        Conversation.objects.select_related(
            "patient", "prestataire", "devis_part", "rendez_vous"
        )
        .annotate(msg_count=Count("messages"))
        .order_by("-updated_at")[:6]
    )
    return render(
        request,
        "dashboard/activite_overview.html",
        {
            "kpis": kpis,
            "recent_devis": recent_devis,
            "recent_rdv": recent_rdv,
            "recent_conv": recent_conv,
        },
    )


@superadmin_required
def rdv_overview(request):
    """Registre consolidé des rendez-vous."""
    status_filter = (request.GET.get("status") or "all").strip()
    valid = {
        "all",
        RendezVous.STATUS_REQUESTED,
        RendezVous.STATUS_CONFIRMED,
        RendezVous.STATUS_COMPLETED,
        RendezVous.STATUS_DECLINED,
        RendezVous.STATUS_CANCELLED,
        RendezVous.STATUS_NO_SHOW,
        "upcoming",
    }
    if status_filter not in valid:
        status_filter = "all"
    search = (request.GET.get("q") or "").strip()
    org_filter = (request.GET.get("org") or "").strip()

    qs = RendezVous.objects.select_related(
        "patient", "organisme", "devis", "devis_part"
    ).order_by("-start")
    now = timezone.now()
    if status_filter == "upcoming":
        qs = qs.filter(status__in=RendezVous.LIVE_STATUSES, start__gte=now)
    elif status_filter != "all":
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(
            Q(reference__icontains=search)
            | Q(walk_in_name__icontains=search)
            | Q(walk_in_phone__icontains=search)
            | Q(patient__username__icontains=search)
            | Q(patient__email__icontains=search)
            | Q(patient__first_name__icontains=search)
            | Q(patient__last_name__icontains=search)
            | Q(devis__reference__icontains=search)
        )
    if org_filter.isdigit():
        qs = qs.filter(organisme_id=int(org_filter))

    base_qs = RendezVous.objects.all()
    counts = {
        "all": base_qs.count(),
        RendezVous.STATUS_REQUESTED: base_qs.filter(
            status=RendezVous.STATUS_REQUESTED
        ).count(),
        RendezVous.STATUS_CONFIRMED: base_qs.filter(
            status=RendezVous.STATUS_CONFIRMED
        ).count(),
        "upcoming": base_qs.filter(
            status__in=RendezVous.LIVE_STATUSES, start__gte=now
        ).count(),
        RendezVous.STATUS_COMPLETED: base_qs.filter(
            status=RendezVous.STATUS_COMPLETED
        ).count(),
        RendezVous.STATUS_NO_SHOW: base_qs.filter(
            status=RendezVous.STATUS_NO_SHOW
        ).count(),
        RendezVous.STATUS_CANCELLED: base_qs.filter(
            status=RendezVous.STATUS_CANCELLED
        ).count(),
        RendezVous.STATUS_DECLINED: base_qs.filter(
            status=RendezVous.STATUS_DECLINED
        ).count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/rdv_overview.html",
        {
            "page": page,
            "rows": page.object_list,
            "status_filter": status_filter,
            "search": search,
            "org_filter": org_filter,
            "counts": counts,
            "kpis": _activite_kpis(),
        },
    )


@superadmin_required
def rdv_admin_detail(request, reference):
    rdv = get_object_or_404(
        RendezVous.objects.select_related(
            "patient", "organisme", "devis", "devis_part"
        ),
        reference=reference,
    )
    conversation = (
        Conversation.objects.filter(rendez_vous=rdv)
        .select_related("patient", "prestataire")
        .first()
    )
    if not conversation and rdv.devis_part_id:
        conversation = (
            Conversation.objects.filter(devis_part=rdv.devis_part)
            .select_related("patient", "prestataire")
            .first()
        )
    return render(
        request,
        "dashboard/rdv_admin_detail.html",
        {"rdv": rdv, "conversation": conversation},
    )


# ─── Rappels RDV (CRUD admin) ─────────────────────────────────────────────────


@superadmin_required
def rdv_reminder_schedules_list(request):
    schedules = (
        RdvReminderSchedule.objects.filter(organisme__isnull=True)
        .prefetch_related("actes")
        .annotate(sent_count=Count("sent_logs"))
        .order_by("order", "-offset_value")
    )
    return render(
        request,
        "dashboard/rdv_reminder_schedules_list.html",
        {"schedules": schedules},
    )


@superadmin_required
def rdv_reminder_schedule_create(request):
    if request.method == "POST":
        form = RdvReminderScheduleForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.organisme = None
            obj.save()
            form.save_m2m()
            messages.success(request, "Règle de rappel créée.")
            return redirect("dashboard:rdv_reminder_schedules_list")
    else:
        form = RdvReminderScheduleForm()
    return render(
        request,
        "dashboard/rdv_reminder_schedule_form.html",
        {"form": form, "title": "Nouvelle règle de rappel RDV"},
    )


@superadmin_required
def rdv_reminder_schedule_edit(request, pk):
    schedule = get_object_or_404(RdvReminderSchedule, pk=pk, organisme__isnull=True)
    if request.method == "POST":
        form = RdvReminderScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, "Règle de rappel mise à jour.")
            return redirect("dashboard:rdv_reminder_schedules_list")
    else:
        form = RdvReminderScheduleForm(instance=schedule)
    return render(
        request,
        "dashboard/rdv_reminder_schedule_form.html",
        {
            "form": form,
            "title": f"Modifier : {schedule.label}",
            "object": schedule,
        },
    )


@superadmin_required
@require_POST
def rdv_reminder_schedule_delete(request, pk):
    schedule = get_object_or_404(RdvReminderSchedule, pk=pk, organisme__isnull=True)
    label = schedule.label
    schedule.delete()
    messages.success(request, f"Règle « {label} » supprimée.")
    return redirect("dashboard:rdv_reminder_schedules_list")


@superadmin_required
def messaging_overview(request):
    """Supervision des fils de discussion (métadonnées, lecture seule)."""
    kind_filter = (request.GET.get("kind") or "all").strip()
    status_filter = (request.GET.get("status") or "all").strip()
    valid_kinds = {
        "all",
        Conversation.KIND_GENERAL,
        Conversation.KIND_DEVIS,
        Conversation.KIND_RDV,
    }
    valid_status = {
        "all",
        Conversation.STATUS_ACTIVE,
        Conversation.STATUS_WAITING,
        Conversation.STATUS_CLOSED,
    }
    if kind_filter not in valid_kinds:
        kind_filter = "all"
    if status_filter not in valid_status:
        status_filter = "all"
    search = (request.GET.get("q") or "").strip()

    qs = (
        Conversation.objects.select_related(
            "patient",
            "prestataire",
            "devis_part__organisme",
            "rendez_vous__organisme",
        )
        .annotate(msg_count=Count("messages"))
        .order_by("-updated_at")
    )
    if kind_filter != "all":
        qs = qs.filter(kind=kind_filter)
    if status_filter != "all":
        qs = qs.filter(thread_status=status_filter)
    if search:
        qs = qs.filter(
            Q(subject__icontains=search)
            | Q(patient__username__icontains=search)
            | Q(patient__email__icontains=search)
            | Q(patient__first_name__icontains=search)
            | Q(patient__last_name__icontains=search)
            | Q(prestataire__username__icontains=search)
            | Q(devis_part__reference__icontains=search)
            | Q(rendez_vous__reference__icontains=search)
        )

    base_qs = Conversation.objects.all()
    counts = {
        "all": base_qs.count(),
        Conversation.KIND_DEVIS: base_qs.filter(kind=Conversation.KIND_DEVIS).count(),
        Conversation.KIND_RDV: base_qs.filter(kind=Conversation.KIND_RDV).count(),
        Conversation.KIND_GENERAL: base_qs.filter(kind=Conversation.KIND_GENERAL).count(),
        Conversation.STATUS_ACTIVE: base_qs.filter(
            thread_status=Conversation.STATUS_ACTIVE
        ).count(),
        Conversation.STATUS_WAITING: base_qs.filter(
            thread_status=Conversation.STATUS_WAITING
        ).count(),
        Conversation.STATUS_CLOSED: base_qs.filter(
            thread_status=Conversation.STATUS_CLOSED
        ).count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    rows = []
    for conv in page.object_list:
        last = conv.messages.select_related("sender").order_by("-timestamp").first()
        rows.append({"conv": conv, "last_message": last})

    return render(
        request,
        "dashboard/messaging_overview.html",
        {
            "rows": rows,
            "page": page,
            "kind_filter": kind_filter,
            "status_filter": status_filter,
            "search": search,
            "counts": counts,
            "kpis": _activite_kpis(),
        },
    )


@superadmin_required
def messaging_admin_detail(request, pk):
    """Lecture seule d'un fil — supervision / support."""
    conv = get_object_or_404(
        Conversation.objects.select_related(
            "patient",
            "prestataire",
            "devis_part__organisme",
            "devis_part__devis",
            "rendez_vous__organisme",
            "rendez_vous__devis",
        ),
        pk=pk,
    )
    msg_list = conv.messages.select_related("sender", "receiver").order_by("timestamp")
    return render(
        request,
        "dashboard/messaging_admin_detail.html",
        {"conv": conv, "messages": msg_list},
    )

