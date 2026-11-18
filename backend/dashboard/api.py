from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Count, F, Min, Q, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from appointments.models import RendezVous
from cart.models import Devis
from healthcare.models import (
    OrganismeDeSante,
    PlatformReview,
    ServiceMedical,
    SubscriptionPlan,
)
from users.models import User

from . import views


def _admin_error(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not request.user.is_active or not (
        request.user.is_superuser or request.user.is_admin_user
    ):
        return JsonResponse({"error": "Accès réservé aux administrateurs."}, status=403)
    return None


def _page_data(page):
    return {
        "page": page.number,
        "pages": page.paginator.num_pages,
        "total": page.paginator.count,
        "has_previous": page.has_previous(),
        "has_next": page.has_next(),
    }


@require_GET
def dashboard_summary_api(request):
    denied = _admin_error(request)
    if denied:
        return denied

    period = request.GET.get("period") or "7j"
    if period not in views._PERIODS:
        period = "7j"
    period_label, period_days = views._PERIODS[period]
    now = timezone.now()
    if period_days is None:
        period_start = (
            OrganismeDeSante.objects.aggregate(first=Min("created_at"))["first"]
            or now - timedelta(days=30)
        )
    else:
        period_start = now - timedelta(days=period_days)

    structures_active = OrganismeDeSante.objects.filter(is_active=True).count()
    new_structures = OrganismeDeSante.objects.filter(
        created_at__gte=period_start, is_active=True
    ).count()
    patients = User.objects.filter(
        user_type="patient", date_joined__gte=period_start
    ).count()
    devis_period = Devis.objects.filter(created_at__gte=period_start)
    rdv = RendezVous.objects.all()
    rdv_closed = rdv.filter(
        status__in=(RendezVous.STATUS_COMPLETED, RendezVous.STATUS_NO_SHOW)
    ).count()
    no_show = rdv.filter(status=RendezVous.STATUS_NO_SHOW).count()
    pioneer_plans = SubscriptionPlan.objects.filter(
        is_pioneer_offer=True
    ).values_list("pk", flat=True)
    pioneer_orgs = OrganismeDeSante.objects.filter(
        subscription_plan__in=pioneer_plans
    ).count()
    mrr = (
        SubscriptionPlan.objects.annotate(n=Count("organismes"))
        .aggregate(total=Sum(F("monthly_price_fcfa") * F("n")))
        .get("total")
        or 0
    )

    chart_days = period_days or 30
    labels, devis_series = views._series(Devis.objects.all(), "created_at", chart_days)
    _, patients_series = views._series(
        User.objects.filter(user_type="patient"), "date_joined", chart_days
    )
    _, structures_series = views._series(
        OrganismeDeSante.objects.all(), "created_at", chart_days
    )
    start = now - timedelta(days=chart_days - 1)
    value_rows = (
        Devis.objects.filter(created_at__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("total_brut"))
        .order_by("day")
    )
    values_by_day = {row["day"]: int(row["total"] or 0) for row in value_rows}
    value_series = []
    current = start.date()
    while current <= now.date():
        value_series.append(values_by_day.get(current, 0))
        current += timedelta(days=1)

    mapped_orgs = [
        {
            "id": org.pk,
            "name": org.name,
            "city": org.city or "",
            "type": str(org.type_organisme) if org.type_organisme_id else "",
            "latitude": float(org.latitude),
            "longitude": float(org.longitude),
            "active": org.is_active,
        }
        for org in OrganismeDeSante.objects.exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .select_related("type_organisme")[:200]
    ]

    return JsonResponse({
        "period": period,
        "period_label": period_label,
        "kpis": {
            "active_structures": structures_active,
            "new_structures": new_structures,
            "patients": patients,
            "quotes": devis_period.count(),
            "quotes_total": Devis.objects.count(),
            "quote_value": int(devis_period.aggregate(total=Sum("total_brut"))["total"] or 0),
            "confirmed_appointments": rdv.filter(
                confirmed_at__gte=period_start
            ).count(),
            "upcoming_appointments": rdv.filter(
                status=RendezVous.STATUS_CONFIRMED, start__gte=now
            ).count(),
            "no_show_pct": round(100 * no_show / rdv_closed, 1) if rdv_closed else 0,
            "acts": views.ActeMedical.objects.count(),
            "pioneer_slots_remaining": max(0, views.PIONEER_TARGET - pioneer_orgs),
            "pioneer_target": views.PIONEER_TARGET,
            "mrr": int(mrr),
        },
        "chart": {
            "labels": labels,
            "quotes": devis_series,
            "patients": patients_series,
            "structures": structures_series,
            "value": value_series,
        },
        "map": mapped_orgs,
        "pending_organizations": [
            {
                "id": org.pk,
                "name": org.name,
                "city": org.city or "",
                "type": str(org.type_organisme) if org.type_organisme_id else "",
            }
            for org in OrganismeDeSante.objects.filter(is_active=False)
            .select_related("type_organisme")
            .order_by("-created_at")[:6]
        ],
        "recent_users": [
            {
                "id": user.pk,
                "name": user.display_name,
                "email": user.email,
                "type": user.get_user_type_display(),
                "created_at": user.date_joined.isoformat(),
            }
            for user in User.objects.order_by("-date_joined")[:5]
        ],
        "services": [
            {"id": row.pk, "name": row.name, "acts": row.act_count}
            for row in ServiceMedical.objects.annotate(
                act_count=Count("acts", distinct=True)
            ).order_by("-act_count")[:6]
        ],
    })


@require_GET
def dashboard_users_api(request):
    denied = _admin_error(request)
    if denied:
        return denied

    queryset = User.objects.select_related(
        "healthcare_provider_profile__type_organisme"
    ).order_by("-date_joined")
    user_type = (request.GET.get("type") or "").strip()
    search = (request.GET.get("q") or "").strip()
    filters = {
        "patient": Q(user_type="patient"),
        "structure": Q(user_type="prestataire", healthcare_provider_profile__account_nature="structure"),
        "praticien": Q(user_type="prestataire", healthcare_provider_profile__account_nature="praticien"),
        "prestataire": Q(user_type="prestataire"),
        "admin": Q(user_type="admin"),
    }
    if user_type in filters:
        queryset = queryset.filter(filters[user_type])
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(healthcare_provider_profile__name__icontains=search)
        )

    page = Paginator(queryset, 20).get_page(request.GET.get("page"))
    all_users = User.objects.all()
    rows = []
    for user in page.object_list:
        org = getattr(user, "healthcare_provider_profile", None)
        rows.append({
            "id": user.pk,
            "username": user.username,
            "name": user.display_name,
            "email": user.email,
            "type": user.user_type,
            "type_label": user.get_user_type_display(),
            "organization": org.name if org else "",
            "is_active": user.is_active,
            "date_joined": user.date_joined.isoformat(),
        })
    return JsonResponse({
        "rows": rows,
        "pagination": _page_data(page),
        "filters": {
            "type": user_type,
            "q": search,
            "counts": {
                "all": all_users.count(),
                "patients": all_users.filter(user_type="patient").count(),
                "structures": all_users.filter(
                    user_type="prestataire",
                    healthcare_provider_profile__account_nature="structure",
                ).count(),
                "practitioners": all_users.filter(
                    user_type="prestataire",
                    healthcare_provider_profile__account_nature="praticien",
                ).count(),
                "admins": all_users.filter(user_type="admin").count(),
            },
        },
    })


@require_POST
def dashboard_user_toggle_api(request, pk):
    denied = _admin_error(request)
    if denied:
        return denied
    user = User.objects.filter(pk=pk).first()
    if user is None:
        return JsonResponse({"error": "Utilisateur introuvable."}, status=404)
    if user.pk == request.user.pk and user.is_active:
        return JsonResponse(
            {"error": "Vous ne pouvez pas désactiver votre propre compte."},
            status=400,
        )
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    return JsonResponse({"ok": True, "is_active": user.is_active})


@require_GET
def dashboard_organizations_api(request):
    denied = _admin_error(request)
    if denied:
        return denied
    queryset = OrganismeDeSante.objects.select_related(
        "user", "type_organisme", "region"
    ).order_by("-created_at")
    status = (request.GET.get("status") or "").strip()
    nature = (request.GET.get("nature") or "").strip()
    search = (request.GET.get("q") or "").strip()
    if status == "pending":
        queryset = queryset.filter(is_active=False)
    elif status == "active":
        queryset = queryset.filter(is_active=True)
    if nature in ("structure", "praticien"):
        queryset = queryset.filter(account_nature=nature)
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(city__icontains=search))

    page = Paginator(queryset, 20).get_page(request.GET.get("page"))
    return JsonResponse({
        "rows": [
            {
                "id": org.pk,
                "name": org.name,
                "slug": org.slug,
                "city": org.city or "",
                "type": str(org.type_organisme) if org.type_organisme_id else "",
                "nature": org.account_nature,
                "user": org.user.username,
                "is_active": org.is_active,
                "is_verified": org.is_verified,
                "created_at": org.created_at.isoformat(),
            }
            for org in page.object_list
        ],
        "pagination": _page_data(page),
        "filters": {
            "status": status,
            "nature": nature,
            "q": search,
            "counts": {
                "all": OrganismeDeSante.objects.count(),
                "structures": OrganismeDeSante.objects.filter(account_nature="structure").count(),
                "practitioners": OrganismeDeSante.objects.filter(account_nature="praticien").count(),
            },
        },
    })


@require_GET
def dashboard_organization_detail_api(request, pk):
    denied = _admin_error(request)
    if denied:
        return denied
    org = (
        OrganismeDeSante.objects.select_related(
            "user", "type_organisme", "region", "subscription_plan"
        )
        .filter(pk=pk)
        .first()
    )
    if org is None:
        return JsonResponse({"error": "Structure introuvable."}, status=404)

    from cart.models import DevisPart
    from messaging.models import Conversation

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
    recent_conversations = (
        Conversation.objects.filter(
            Q(devis_part__organisme=org) | Q(rendez_vous__organisme=org)
        )
        .select_related("patient", "prestataire", "devis_part", "rendez_vous")
        .distinct()
        .order_by("-updated_at")[:8]
    )
    return JsonResponse({
        "organization": {
            "id": org.pk,
            "name": org.name,
            "slug": org.slug,
            "city": org.city or "",
            "address": org.address or "",
            "type": str(org.type_organisme) if org.type_organisme_id else "",
            "nature": org.account_nature,
            "account": org.user.username if org.user_id else "",
            "is_active": org.is_active,
            "is_verified": org.is_verified,
            "created_at": org.created_at.isoformat(),
            "subscription_plan": str(org.subscription_plan) if org.subscription_plan_id else "",
            "public_url": org.get_public_url(),
        },
        "bilan": views._bilan_score_org(org),
        "stats": {
            "appointments": RendezVous.objects.filter(organisme=org).count(),
            "pending_appointments": RendezVous.objects.filter(
                organisme=org, status=RendezVous.STATUS_REQUESTED
            ).count(),
            "quotes": DevisPart.objects.filter(organisme=org).exclude(status="draft").count(),
            "conversations": Conversation.objects.filter(
                Q(devis_part__organisme=org) | Q(rendez_vous__organisme=org)
            ).distinct().count(),
        },
        "recent_appointments": [
            {
                "reference": item.reference,
                "patient": item.patient_label,
                "status": item.get_status_display(),
                "start": item.start.isoformat(),
            }
            for item in recent_rdv
        ],
        "recent_quotes": [
            {
                "reference": item.reference,
                "parent_reference": item.devis.reference if item.devis_id else "",
                "patient": item.devis.patient.display_name if item.devis_id else "",
                "status": item.get_status_display(),
                "created_at": item.created_at.isoformat(),
            }
            for item in recent_parts
        ],
        "recent_conversations": [
            {
                "id": item.pk,
                "label": item.dossier_label,
                "patient": item.patient.display_name if item.patient_id else "",
                "updated_at": item.updated_at.isoformat(),
            }
            for item in recent_conversations
        ],
    })


@require_POST
def dashboard_organization_action_api(request, pk, action):
    denied = _admin_error(request)
    if denied:
        return denied
    org = OrganismeDeSante.objects.filter(pk=pk).first()
    if org is None:
        return JsonResponse({"error": "Structure introuvable."}, status=404)
    if action not in ("approve", "reject"):
        return JsonResponse({"error": "Action inconnue."}, status=400)

    org.is_active = action == "approve"
    org.is_verified = action == "approve"
    org.save(update_fields=["is_active", "is_verified"])
    from notifications.dispatcher import dispatch

    event = "organisme.approved" if action == "approve" else "organisme.rejected"
    link = f"/sante/{org.slug}/" if action == "approve" else "/sante/prestataire/"
    dispatch(event, context={"organisme": org, "link": link}, actor=org.user)
    return JsonResponse({
        "ok": True,
        "is_active": org.is_active,
        "is_verified": org.is_verified,
    })


@require_GET
def dashboard_reviews_api(request):
    denied = _admin_error(request)
    if denied:
        return denied
    status = (request.GET.get("status") or "").strip()
    queryset = PlatformReview.objects.select_related("patient").prefetch_related(
        "actes__service_medical_category"
    ).order_by("-created_at")
    if status == "pending":
        queryset = queryset.filter(is_approved=False)
    elif status == "approved":
        queryset = queryset.filter(is_approved=True)
    page = Paginator(queryset, 20).get_page(request.GET.get("page"))
    return JsonResponse({
        "rows": [
            {
                "id": review.pk,
                "patient": review.patient.display_name or review.patient.username,
                "patient_email": review.patient.email,
                "rating": review.rating,
                "comment": review.tarifs_delais_comment,
                "actes": [str(acte) for acte in review.actes.all()],
                "is_approved": review.is_approved,
                "created_at": review.created_at.isoformat(),
            }
            for review in page.object_list
        ],
        "status": status,
        "counts": {
            "all": PlatformReview.objects.count(),
            "pending": PlatformReview.objects.filter(is_approved=False).count(),
            "approved": PlatformReview.objects.filter(is_approved=True).count(),
        },
        "pagination": _page_data(page),
    })


@require_POST
def dashboard_review_action_api(request, pk, action):
    denied = _admin_error(request)
    if denied:
        return denied
    review = (
        PlatformReview.objects.select_related("patient")
        .filter(pk=pk)
        .first()
    )
    if review is None:
        return JsonResponse({"error": "Avis introuvable."}, status=404)
    if action == "approve":
        review.is_approved = True
        review.save(update_fields=["is_approved"])
        from django.urls import reverse
        from notifications.dispatcher import dispatch

        dispatch(
            "review.approved",
            context={
                "review": review,
                "organisme": None,
                "patient": review.patient,
                "link": reverse("healthcare:platform_review"),
            },
            actor=review.patient,
        )
        return JsonResponse({"ok": True, "is_approved": True})
    if action == "delete":
        review.delete()
        return JsonResponse({"ok": True, "deleted": True})
    return JsonResponse({"error": "Action inconnue."}, status=400)
