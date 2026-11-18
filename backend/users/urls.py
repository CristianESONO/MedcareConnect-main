from django.urls import include, path

from . import views
from .patient_panel import patient_panel_devis_detail_view, patient_panel_view

app_name = "users"

_account_urlpatterns = [
    path("deconnexion/", views.logout_view, name="logout"),
    path("compte/", views.patient_account, name="patient_account"),
    path("compte/panel/", patient_panel_view, {"tab": "accueil"}, name="patient_panel"),
    path("compte/panel/<str:tab>/", patient_panel_view, name="patient_panel_tab"),
    path(
        "compte/panel/devis/<str:ref>/",
        patient_panel_devis_detail_view,
        name="patient_panel_devis",
    ),
    path("compte/assurance/", views.patient_assurance, name="patient_assurance"),
    path("profil/", views.profile, name="profile"),
    path("mot-de-passe/", views.change_password, name="change_password"),
   ]

urlpatterns = [
    path("api/profile/", views.user_profile_api, name="user_profile_api"),
    path("api/patient/overview/", views.patient_overview_api, name="patient_overview_api"),
    path("api/patient/devis/", views.patient_quotes_api, name="patient_quotes_api"),
    path("api/patient/assurance/", views.patient_insurance_api, name="patient_insurance_api"),
    path("api/patient/recherches/", views.patient_search_history_api, name="patient_search_history_api"),
    path("api/patient/profile/", views.patient_profile_api, name="patient_profile_api"),
    path("api/patient/password/", views.patient_password_api, name="patient_password_api"),
    path("compte/panel/", views.patient_panel_react_home, name="patient_panel_react_home"),
    path(
        "compte/panel/accueil/",
        views.patient_panel_react_home,
        name="patient_panel_react_home_tab",
    ),
    path(
        "compte/panel/profil/",
        views.patient_panel_react_home,
        name="patient_panel_react_profile",
    ),
    path(
        "compte/panel/rdv/",
        views.patient_panel_react_home,
        name="patient_panel_react_rdv",
    ),
    path(
        "compte/panel/devis/",
        views.patient_panel_react_home,
        name="patient_panel_react_devis",
    ),
    path(
        "compte/panel/assurance/",
        views.patient_panel_react_home,
        name="patient_panel_react_assurance",
    ),
    path(
        "compte/panel/chariot/",
        views.patient_panel_react_home,
        name="patient_panel_react_cart",
    ),
    path(
        "compte/panel/recherches/",
        views.patient_panel_react_home,
        name="patient_panel_react_search_history",
    ),
    path("", include(_account_urlpatterns)),
]
