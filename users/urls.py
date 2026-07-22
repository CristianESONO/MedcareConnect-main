from django.urls import include, path

from . import views
from .patient_panel import patient_panel_devis_detail_view, patient_panel_view

app_name = "users"

_account_urlpatterns = [
    path("logout/", views.logout_view, name="logout"),
    path("compte/", views.patient_account, name="patient_account"),
    path("compte/panel/", patient_panel_view, {"tab": "accueil"}, name="patient_panel"),
    path("compte/panel/<str:tab>/", patient_panel_view, name="patient_panel_tab"),
    path(
        "compte/panel/devis/<str:ref>/",
        patient_panel_devis_detail_view,
        name="patient_panel_devis",
    ),
    path("compte/assurance/", views.patient_assurance, name="patient_assurance"),
    path("profile/", views.profile, name="profile"),
    path("password/", views.change_password, name="change_password"),
]

urlpatterns = [
    path("inscription/", views.register, name="register"),
    path("connexion/", views.login_view, name="login"),
    path("", include(_account_urlpatterns)),
]
