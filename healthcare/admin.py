from django.contrib import admin
from django.utils import timezone

from .models import (
    TypeOrganisme,
    Region,
    OrganismeDeSante,
    Photo,
    PrelevementZone,
    ServiceMedical,
    ActeMedical,
    PrestataireActe,
    Assurance,
    PriseEnChargeAssurance,
    ProfileView,
    PlatformReview,
    Favoris,
    SearchHistory,
    LotExamenPrefait,
    LotExamenPrefaitActe,
    SubscriptionFeature,
    SubscriptionPlan,
    SubscriptionPlanFeature,
    SubscriptionChangeRequest,
)


class PrelevementZoneInline(admin.TabularInline):
    model = PrelevementZone
    extra = 1
    fields = ("label", "forfait_fcfa", "is_active", "order", "notes")
    ordering = ("order", "label")


@admin.register(TypeOrganisme)
class TypeOrganismeAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "icon")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(OrganismeDeSante)
class OrganismeDeSanteAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type_organisme",
        "city",
        "subscription_plan",
        "contact_phone",
        "is_active",
        "is_verified",
        "profile_views_count",
        "created_at",
    )
    list_filter = ("type_organisme", "city", "region", "is_active", "is_verified", "subscription_plan")
    search_fields = ("name", "raison_sociale", "ninea", "address", "city", "quartier", "description")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("user",)
    readonly_fields = ("profile_views_count", "created_at", "updated_at")
    inlines = [PrelevementZoneInline]
    fieldsets = (
        ("Informations de base", {
            "fields": (
                "user", "name", "raison_sociale", "ninea", "slug", "type_organisme",
                "description", "logo",
            ),
        }),
        ("Localisation", {
            "fields": ("address", "quartier", "city", "region", "latitude", "longitude"),
        }),
        ("Contact", {
            "fields": ("contact_email", "contact_phone", "whatsapp_number", "website"),
        }),
        ("Horaires et médias", {
            "fields": ("opening_hours", "photos"),
        }),
        ("Services additionnels", {
            "fields": ("prises_sang_domicile", "sans_rendez_vous", "accepte_tiers_payant", "access_pmr"),
        }),
        ("Abonnement", {
            "fields": (
                "subscription_plan",
                "subscription_started_at",
                "subscription_renewal_at",
                "subscription_auto_renew",
            ),
        }),
        ("Statut", {
            "fields": ("is_active", "is_verified", "profile_views_count", "created_at", "updated_at"),
        }),
    )


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("caption", "image", "uploaded_at")


@admin.register(ServiceMedical)
class ServiceMedicalAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ActeMedical)
class ActeMedicalAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "service_medical_category", "level", "parent_service", "reference_price", "is_active")
    list_filter = ("level", "service_medical_category", "is_active")
    search_fields = ("name", "code")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("parent_service",)
    fieldsets = (
        (None, {
            "fields": (
                "name", "slug", "code", "description", "service_medical_category",
                "parent_service", "level", "reference_price", "is_active",
            ),
        }),
        ("Rendez-vous", {
            "fields": ("rdv_prerequisites",),
            "description": "Consignes patient incluses dans les rappels automatiques si la règle l'active.",
        }),
    )


@admin.register(PrestataireActe)
class PrestataireActeAdmin(admin.ModelAdmin):
    list_display = ("organisme", "acte", "price", "delai", "is_available", "updated_at")
    list_filter = ("is_available", "delai", "organisme__type_organisme")
    search_fields = ("organisme__name", "acte__name")
    raw_id_fields = ("organisme", "acte")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Assurance)
class AssuranceAdmin(admin.ModelAdmin):
    list_display = ("name", "segment", "contact_phone", "is_active")
    list_filter = ("segment", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PriseEnChargeAssurance)
class PriseEnChargeAssuranceAdmin(admin.ModelAdmin):
    list_display = ("organisme", "assurance", "is_active")
    list_filter = ("assurance", "is_active")
    search_fields = ("organisme__name", "assurance__name")
    raw_id_fields = ("organisme", "assurance")


@admin.register(ProfileView)
class ProfileViewAdmin(admin.ModelAdmin):
    list_display = ("organisme", "viewer", "ip_address", "viewed_at")
    list_filter = ("organisme",)
    readonly_fields = ("viewed_at",)


@admin.register(PlatformReview)
class PlatformReviewAdmin(admin.ModelAdmin):
    list_display = ("patient", "rating", "is_approved", "created_at")
    list_filter = ("rating", "is_approved")
    search_fields = ("patient__username", "tarifs_delais_comment")
    filter_horizontal = ("actes",)
    actions = ["approve_platform_reviews"]

    @admin.action(description="Approuver les avis plateforme sélectionnés")
    def approve_platform_reviews(self, request, queryset):
        queryset.update(is_approved=True)


@admin.register(Favoris)
class FavorisAdmin(admin.ModelAdmin):
    list_display = ("patient", "organisme", "created_at")
    raw_id_fields = ("patient", "organisme")


class LotExamenPrefaitActeInline(admin.TabularInline):
    model = LotExamenPrefaitActe
    extra = 1
    ordering = ("order",)
    raw_id_fields = ("acte",)


@admin.register(LotExamenPrefait)
class LotExamenPrefaitAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "teaser", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [LotExamenPrefaitActeInline]


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "query", "search_type", "results_count", "searched_at")
    list_filter = ("search_type",)
    search_fields = ("query", "user__username")
    readonly_fields = ("searched_at",)


class SubscriptionPlanFeatureInline(admin.TabularInline):
    model = SubscriptionPlanFeature
    extra = 0
    autocomplete_fields = ("feature",)


@admin.register(SubscriptionFeature)
class SubscriptionFeatureAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "order")
    search_fields = ("code", "label")
    ordering = ("order", "label")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "monthly_price_fcfa",
        "is_default",
        "is_public",
        "is_pioneer_offer",
        "order",
    )
    list_filter = ("is_default", "is_public", "is_pioneer_offer")
    search_fields = ("name", "slug", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubscriptionPlanFeatureInline]

    def get_queryset(self, request):
        from healthcare.subscription_admin import EXCLUDED_ADMIN_PLAN_SLUGS

        return super().get_queryset(request).exclude(slug__in=EXCLUDED_ADMIN_PLAN_SLUGS)


@admin.register(SubscriptionChangeRequest)
class SubscriptionChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "organisme",
        "previous_plan",
        "requested_plan",
        "status",
        "created_at",
        "processed_at",
    )
    list_filter = ("status", "requested_plan")
    search_fields = ("organisme__name", "message_from_structure", "staff_note")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("organisme", "previous_plan", "requested_plan", "processed_by")
    actions = ("approve_and_apply", "reject_requests")

    @admin.action(description="Approuver et appliquer la formule demandée")
    def approve_and_apply(self, request, queryset):
        from notifications.dispatcher import dispatch as _notify
        n = 0
        for req in queryset.filter(status="pending").select_related("organisme", "requested_plan"):
            org = req.organisme
            org.subscription_plan = req.requested_plan
            org.save(update_fields=["subscription_plan", "updated_at"])
            req.status = "approved"
            req.processed_at = timezone.now()
            req.processed_by = request.user
            req.save(update_fields=["status", "processed_at", "processed_by", "updated_at"])
            try:
                _notify(
                    "subscription.approved",
                    context={
                        "organisme": org,
                        "requested_plan": req.requested_plan,
                        "previous_plan": req.previous_plan,
                        "link": "/healthcare/prestataire/abonnement/",
                    },
                    actor=getattr(org, "user", None),
                )
            except Exception:
                pass
            n += 1
        self.message_user(request, f"{n} demande(s) approuvée(s) et formule appliquée.")

    @admin.action(description="Refuser les demandes sélectionnées")
    def reject_requests(self, request, queryset):
        from notifications.dispatcher import dispatch as _notify
        n = 0
        now = timezone.now()
        for req in queryset.filter(status="pending").select_related("organisme", "requested_plan"):
            req.status = "rejected"
            req.processed_at = now
            req.processed_by = request.user
            req.save(update_fields=["status", "processed_at", "processed_by", "updated_at"])
            try:
                _notify(
                    "subscription.rejected",
                    context={
                        "organisme": req.organisme,
                        "requested_plan": req.requested_plan,
                        "previous_plan": req.previous_plan,
                        "staff_note": req.staff_note,
                        "link": "/healthcare/prestataire/abonnement/",
                    },
                    actor=getattr(req.organisme, "user", None),
                )
            except Exception:
                pass
            n += 1
        self.message_user(request, f"{n} demande(s) refusée(s).")
