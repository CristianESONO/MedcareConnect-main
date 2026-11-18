from django.urls import path
from . import api
from . import activity_api, report_api
from medcare_connect.views import react_app

app_name = "dashboard"


def dashboard_react_app(request, *args, **kwargs):
    return react_app(request)


urlpatterns = [
    # React administration APIs
    path("api/admin/activite/overview/", activity_api.activity_overview_api, name="admin_activity_overview_api"),
    path("api/admin/activite/devis/", activity_api.quotes_api, name="admin_activity_quotes_api"),
    path("api/admin/activite/devis/<str:reference>/", activity_api.quote_detail_api, name="admin_activity_quote_detail_api"),
    path("api/admin/activite/devis/<str:reference>/<str:action>/", activity_api.quote_action_api, name="admin_activity_quote_action_api"),
    path("api/admin/activite/rdv/", activity_api.appointments_api, name="admin_activity_appointments_api"),
    path("api/admin/activite/rdv/<str:reference>/", activity_api.appointment_detail_api, name="admin_activity_appointment_detail_api"),
    path("api/admin/activite/rappels/", activity_api.reminder_schedules_api, name="admin_activity_reminder_schedules_api"),
    path("api/admin/activite/rappels/<int:pk>/", activity_api.reminder_schedule_detail_api, name="admin_activity_reminder_schedule_detail_api"),
    path("api/admin/activite/messages/", activity_api.messaging_api, name="admin_activity_messaging_api"),
    path("api/admin/activite/messages/<int:pk>/", activity_api.messaging_detail_api, name="admin_activity_messaging_detail_api"),
    path("api/reports/subscriptions/", report_api.subscriptions, name="admin_reports_subscriptions_api"),
    path("api/reports/subscriptions/organizations/<int:org_id>/assign/", report_api.assign_plan, name="admin_reports_assign_plan_api"),
    path("api/reports/subscriptions/plans/", report_api.create_plan, name="admin_reports_create_plan_api"),
    path("api/reports/subscriptions/plans/<int:plan_id>/", report_api.update_plan, name="admin_reports_plan_detail_api"),
    path("api/reports/subscriptions/plans/<int:plan_id>/features/<int:feature_id>/toggle/", report_api.toggle_feature, name="admin_reports_toggle_feature_api"),
    path("api/reports/finances/", report_api.finances, name="admin_reports_finances_api"),
    path("api/reports/pioneers/", report_api.pioneers, name="admin_reports_pioneers_api"),
    path("api/reports/bilans/", report_api.bilans, name="admin_reports_bilans_api"),
    path("api/reports/compliance/", report_api.compliance, name="admin_reports_compliance_api"),
    path("api/admin/summary/", api.dashboard_summary_api, name="admin_summary_api"),
    path("api/admin/utilisateurs/", api.dashboard_users_api, name="admin_users_api"),
    path("api/admin/utilisateurs/<int:pk>/activer-desactiver/", api.dashboard_user_toggle_api, name="admin_user_toggle_api"),
    path("api/admin/organismes/", api.dashboard_organizations_api, name="admin_organizations_api"),
    path("api/admin/organismes/<int:pk>/", api.dashboard_organization_detail_api, name="admin_organization_detail_api"),
    path("api/admin/organismes/<int:pk>/<str:action>/", api.dashboard_organization_action_api, name="admin_organization_action_api"),
    path("api/admin/avis/", api.dashboard_reviews_api, name="admin_reviews_api"),
    path("api/admin/avis/<int:pk>/<str:action>/", api.dashboard_review_action_api, name="admin_review_action_api"),
    path("", dashboard_react_app, name="index"),
    # Users
    path("utilisateurs/", dashboard_react_app, name="users_list"),
    path("utilisateurs/<int:pk>/activer-desactiver/", dashboard_react_app, name="user_toggle_active"),
    # Organismes
    path("organismes/", dashboard_react_app, name="organismes_list"),
    path("organismes/<int:pk>/", dashboard_react_app, name="organisme_detail"),
    path("organismes/<int:pk>/approuver/", dashboard_react_app, name="organisme_approve"),
    path("organismes/<int:pk>/rejeter/", dashboard_react_app, name="organisme_reject"),

    # Services & Assurances (référentiel — CRUD)
    path("services/", dashboard_react_app, name="services_list"),
    path("services/ajouter/", dashboard_react_app, name="service_create"),
    path("services/<int:pk>/modifier/", dashboard_react_app, name="service_edit"),
    path("services/<int:pk>/supprimer/", dashboard_react_app, name="service_delete"),

    path("actes/", dashboard_react_app, name="actes_list"),
    path("actes/ajouter/", dashboard_react_app, name="acte_create"),
    path("actes/<int:pk>/modifier/", dashboard_react_app, name="acte_edit"),
    path("actes/<int:pk>/supprimer/", dashboard_react_app, name="acte_delete"),

    path("assurances/", dashboard_react_app, name="assurances_list"),
    path("assurances/ajouter/", dashboard_react_app, name="assurance_create"),
    path("assurances/<int:pk>/modifier/", dashboard_react_app, name="assurance_edit"),
    path("assurances/<int:pk>/supprimer/", dashboard_react_app, name="assurance_delete"),
    # Abonnements (formules & droits)
    path(
        "abonnements/fonctionnalites/",
        dashboard_react_app,
        name="subscription_features_list",
    ),
    path(
        "abonnements/fonctionnalites/ajouter/",
        dashboard_react_app,
        name="subscription_feature_create",
    ),
    path(
        "abonnements/fonctionnalites/<int:pk>/modifier/",
        dashboard_react_app,
        name="subscription_feature_edit",
    ),
    path(
        "abonnements/fonctionnalites/<int:pk>/supprimer/",
        dashboard_react_app,
        name="subscription_feature_delete",
    ),
    path(
        "abonnements/formules/",
        dashboard_react_app,
        name="subscription_plans_list",
    ),
    path(
        "abonnements/formules/ajouter/",
        dashboard_react_app,
        name="subscription_plan_create",
    ),
    path(
        "abonnements/formules/<int:pk>/modifier/",
        dashboard_react_app,
        name="subscription_plan_edit",
    ),
    path(
        "abonnements/formules/<int:pk>/supprimer/",
        dashboard_react_app,
        name="subscription_plan_delete",
    ),
    # Sprint B · Vue d'ensemble Abonnements (tableau structures + cartes config)
    path(
        "abonnements/",
        dashboard_react_app,
        name="subscriptions_overview",
    ),
    path(
        "abonnements/structures/<int:org_pk>/plan/",
        dashboard_react_app,
        name="subscription_assign_plan",
    ),
    path(
        "abonnements/formules/<int:plan_pk>/fonctionnalite/<int:feature_pk>/activer-desactiver/",
        dashboard_react_app,
        name="subscription_toggle_feature",
    ),
    # Sprint D · Finances & MRR
    path("finances/", dashboard_react_app, name="finances"),
    # Sprint E · Pionniers + Bilans
    path("pionniers/", dashboard_react_app, name="pioneers_overview"),
    path("bilans/", dashboard_react_app, name="bilans_overview"),
    # Sprint F · Conformité CDP
    path("conformite/", dashboard_react_app, name="conformite"),
    # Sprint C · Devis WA admin
    path("devis/", dashboard_react_app, name="devis_overview"),
    path("devis/<str:reference>/", dashboard_react_app, name="devis_admin_detail"),
    path("devis/<str:reference>/relance/", dashboard_react_app, name="devis_admin_relance"),
    path("devis/<str:reference>/archiver/", dashboard_react_app, name="devis_admin_archive"),
    # Activité plateforme · Vue 360°
    path("activite/", dashboard_react_app, name="activite_overview"),
    path("activite/rdv/", dashboard_react_app, name="rdv_overview"),
    path("activite/rdv/rappels/", dashboard_react_app, name="rdv_reminder_schedules_list"),
    path("activite/rdv/rappels/ajouter/", dashboard_react_app, name="rdv_reminder_schedule_create"),
    path("activite/rdv/rappels/<int:pk>/modifier/", dashboard_react_app, name="rdv_reminder_schedule_edit"),
    path("activite/rdv/rappels/<int:pk>/supprimer/", dashboard_react_app, name="rdv_reminder_schedule_delete"),
    path("activite/rdv/<str:reference>/", dashboard_react_app, name="rdv_admin_detail"),
    path("activite/messages/", dashboard_react_app, name="messaging_overview"),
    path("activite/messages/<int:pk>/", dashboard_react_app, name="messaging_admin_detail"),
    # Reviews
    path("avis/", dashboard_react_app, name="reviews_list"),
    path("avis/<int:pk>/approuver/", dashboard_react_app, name="review_approve"),
    path("avis/<int:pk>/supprimer/", dashboard_react_app, name="review_delete"),
]
