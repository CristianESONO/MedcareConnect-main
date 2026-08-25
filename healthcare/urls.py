from django.urls import path
from . import views
from . import bundle_views

app_name = "healthcare"

urlpatterns = [
    # Patient — routes fixes avant <slug>
    path("parcours/", bundle_views.bundle_planner, name="bundle_planner"),
    path("api/parcours/plan/", bundle_views.api_bundle_plan, name="api_bundle_plan"),
    path("api/parcours/actes/", bundle_views.api_actes_autocomplete, name="api_actes_autocomplete"),
    path("api/parcours/save-selection/", bundle_views.bundle_save_session, name="bundle_save_session"),
    path(
        "api/parcours/alternatives/<int:acte_id>/",
        bundle_views.api_pa_alternatives,
        name="api_pa_alternatives",
    ),
    path("search/", views.search, name="search"),
    path("annuaire/", views.annuaire, name="annuaire"),
    path("centres/", views.centres_list, name="centres_list"),
    path("favorites/", views.my_favorites, name="my_favorites"),
    path("history/", views.my_search_history, name="search_history"),
    path("avis/", views.platform_review, name="platform_review"),
    path("avis/google/", views.platform_review_google, name="platform_review_google"),
    path("api/autocomplete/", views.api_search_autocomplete, name="api_search_autocomplete"),
    path("api/ai-agent/", views.api_ai_agent_chat, name="api_ai_agent_chat"),
    path("api/actes-budget/", views.api_actes_budget, name="api_actes_budget"),
    path("api/geocode/", views.api_geocode, name="api_geocode"),
    path("api/reverse/", views.api_reverse, name="api_reverse"),
    path(
        "api/organisme/<slug:slug>/preview/",
        views.api_organisme_preview,
        name="api_organisme_preview",
    ),
    path("api/save-location/", views.save_search_location, name="save_search_location"),
    path("service/<slug:slug>/", views.service_detail, name="service_detail"),

    # Prestataire
    path("prestataire/dashboard/", views.prestataire_dashboard, name="prestataire_dashboard"),
    path("prestataire/devis/", views.prestataire_devis_list, name="prestataire_devis_list"),
    path(
        "prestataire/devis/part/<str:reference>/",
        views.prestataire_devis_part_detail,
        name="prestataire_devis_part_detail",
    ),
    path("prestataire/devis/<str:reference>/relance/", views.prestataire_devis_relance, name="prestataire_devis_relance"),
    path("prestataire/devis/<str:reference>/archiver/", views.prestataire_devis_archiver, name="prestataire_devis_archiver"),
    path("prestataire/organisme/create/", views.organisme_create, name="organisme_create"),
    path("prestataire/organisme/edit/", views.organisme_edit, name="organisme_edit"),
    path("prestataire/organisme/hours/", views.organisme_hours, name="organisme_hours"),
    path("prestataire/profil-public/", views.prestataire_profil_public, name="prestataire_profil_public"),
    path("prestataire/actes/", views.actes_list, name="actes_list"),
    path("prestataire/actes/add/", views.acte_add, name="acte_add"),
    path("prestataire/actes/<int:pk>/edit/", views.acte_edit, name="acte_edit"),
    path("prestataire/actes/<int:pk>/delete/", views.acte_delete, name="acte_delete"),
    path("prestataire/actes/<int:pk>/toggle/", views.acte_toggle_available, name="acte_toggle_available"),
    path("prestataire/actes/prep/<int:acte_id>/", views.prestataire_acte_prerequisites, name="prestataire_acte_prerequisites"),
    path("prestataire/actes/<int:acte_id>/rappels/add/", views.prestataire_acte_reminder_add, name="prestataire_acte_reminder_add"),
    path(
        "prestataire/actes/<int:acte_id>/rappels/<int:pk>/delete/",
        views.prestataire_acte_reminder_delete,
        name="prestataire_acte_reminder_delete",
    ),
    path("prestataire/actes/rappels/", views.prestataire_rdv_reminder_list, name="prestataire_rdv_reminder_list"),
    path("prestataire/actes/rappels/add/", views.prestataire_rdv_reminder_create, name="prestataire_rdv_reminder_create"),
    path("prestataire/actes/rappels/<int:pk>/edit/", views.prestataire_rdv_reminder_edit, name="prestataire_rdv_reminder_edit"),
    path("prestataire/actes/rappels/<int:pk>/delete/", views.prestataire_rdv_reminder_delete, name="prestataire_rdv_reminder_delete"),
    path("prestataire/zones-prelevement/", views.prestataire_zones_prelevement, name="prestataire_zones_prelevement"),
    path("prestataire/insurances/", views.insurances_manage, name="insurances_manage"),
    path("prestataire/insurances/<int:pk>/delete/", views.insurance_delete, name="insurance_delete"),
    path("prestataire/medplaque/", views.prestataire_medplaque, name="prestataire_medplaque"),
    path("prestataire/bilan/", views.prestataire_bilan, name="prestataire_bilan"),
    path("prestataire/parametres/", views.prestataire_settings, name="prestataire_settings"),
    path("prestataire/abonnement/", views.prestataire_subscription, name="prestataire_subscription"),

    # Fiche organisme (doit rester en dernier parmi les patterns « racine »)
    path("organisme/<int:org_id>/profil-drawer/", views.organisme_profil_drawer, name="organisme_profil_drawer"),
    path("<slug:slug>/", views.organisme_detail, name="organisme_detail"),
    path("<slug:slug>/favorite/", views.toggle_favorite, name="toggle_favorite"),
]
