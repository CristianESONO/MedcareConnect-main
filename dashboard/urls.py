from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    # Users
    path("utilisateurs/", views.users_list, name="users_list"),
    path("utilisateurs/<int:pk>/activer-desactiver/", views.user_toggle_active, name="user_toggle_active"),
    # Organismes
    path("organismes/", views.organismes_list, name="organismes_list"),
    path("organismes/<int:pk>/", views.organisme_detail, name="organisme_detail"),
    path("organismes/<int:pk>/approuver/", views.organisme_approve, name="organisme_approve"),
    path("organismes/<int:pk>/rejeter/", views.organisme_reject, name="organisme_reject"),

    # Services & Assurances (référentiel — CRUD)
    path("services/", views.services_list, name="services_list"),
    path("services/ajouter/", views.service_create, name="service_create"),
    path("services/<int:pk>/modifier/", views.service_edit, name="service_edit"),
    path("services/<int:pk>/supprimer/", views.service_delete, name="service_delete"),

    path("actes/", views.actes_list, name="actes_list"),
    path("actes/ajouter/", views.acte_create, name="acte_create"),
    path("actes/<int:pk>/modifier/", views.acte_edit, name="acte_edit"),
    path("actes/<int:pk>/supprimer/", views.acte_delete, name="acte_delete"),

    path("assurances/", views.assurances_list, name="assurances_list"),
    path("assurances/ajouter/", views.assurance_create, name="assurance_create"),
    path("assurances/<int:pk>/modifier/", views.assurance_edit, name="assurance_edit"),
    path("assurances/<int:pk>/supprimer/", views.assurance_delete, name="assurance_delete"),
    # Abonnements (formules & droits)
    path(
        "abonnements/fonctionnalites/",
        views.subscription_features_list,
        name="subscription_features_list",
    ),
    path(
        "abonnements/fonctionnalites/ajouter/",
        views.subscription_feature_create,
        name="subscription_feature_create",
    ),
    path(
        "abonnements/fonctionnalites/<int:pk>/modifier/",
        views.subscription_feature_edit,
        name="subscription_feature_edit",
    ),
    path(
        "abonnements/fonctionnalites/<int:pk>/supprimer/",
        views.subscription_feature_delete,
        name="subscription_feature_delete",
    ),
    path(
        "abonnements/formules/",
        views.subscription_plans_list,
        name="subscription_plans_list",
    ),
    path(
        "abonnements/formules/ajouter/",
        views.subscription_plan_create,
        name="subscription_plan_create",
    ),
    path(
        "abonnements/formules/<int:pk>/modifier/",
        views.subscription_plan_edit,
        name="subscription_plan_edit",
    ),
    path(
        "abonnements/formules/<int:pk>/supprimer/",
        views.subscription_plan_delete,
        name="subscription_plan_delete",
    ),
    # Sprint B · Vue d'ensemble Abonnements (tableau structures + cartes config)
    path(
        "abonnements/",
        views.subscriptions_overview,
        name="subscriptions_overview",
    ),
    path(
        "abonnements/structures/<int:org_pk>/plan/",
        views.subscription_assign_plan,
        name="subscription_assign_plan",
    ),
    path(
        "abonnements/formules/<int:plan_pk>/fonctionnalite/<int:feature_pk>/activer-desactiver/",
        views.subscription_toggle_feature,
        name="subscription_toggle_feature",
    ),
    # Sprint D · Finances & MRR
    path("finances/", views.finances, name="finances"),
    # Sprint E · Pionniers + Bilans
    path("pionniers/", views.pioneers_overview, name="pioneers_overview"),
    path("bilans/", views.bilans_overview, name="bilans_overview"),
    # Sprint F · Conformité CDP
    path("conformite/", views.conformite, name="conformite"),
    # Sprint C · Devis WA admin
    path("devis/", views.devis_overview, name="devis_overview"),
    path("devis/<str:reference>/", views.devis_admin_detail, name="devis_admin_detail"),
    path("devis/<str:reference>/relance/", views.devis_admin_relance, name="devis_admin_relance"),
    path("devis/<str:reference>/archiver/", views.devis_admin_archive, name="devis_admin_archive"),
    # Activité plateforme · Vue 360°
    path("activite/", views.activite_overview, name="activite_overview"),
    path("activite/rdv/", views.rdv_overview, name="rdv_overview"),
    path("activite/rdv/rappels/", views.rdv_reminder_schedules_list, name="rdv_reminder_schedules_list"),
    path("activite/rdv/rappels/ajouter/", views.rdv_reminder_schedule_create, name="rdv_reminder_schedule_create"),
    path("activite/rdv/rappels/<int:pk>/modifier/", views.rdv_reminder_schedule_edit, name="rdv_reminder_schedule_edit"),
    path("activite/rdv/rappels/<int:pk>/supprimer/", views.rdv_reminder_schedule_delete, name="rdv_reminder_schedule_delete"),
    path("activite/rdv/<str:reference>/", views.rdv_admin_detail, name="rdv_admin_detail"),
    path("activite/messages/", views.messaging_overview, name="messaging_overview"),
    path("activite/messages/<int:pk>/", views.messaging_admin_detail, name="messaging_admin_detail"),
    # Reviews
    path("avis/", views.reviews_list, name="reviews_list"),
    path("avis/<int:pk>/approuver/", views.review_approve, name="review_approve"),
    path("avis/<int:pk>/supprimer/", views.review_delete, name="review_delete"),
]
