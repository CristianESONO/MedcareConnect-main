from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "appointments"

urlpatterns = [
    # Patient — partials du panneau « Mon compte »
    path("reserver/<str:part_ref>/", views.patient_book, name="patient_book"),
    path("<str:ref>/annuler/", views.patient_cancel, name="patient_cancel"),
    path("<str:ref>/reprogrammer/", views.patient_reschedule, name="patient_reschedule"),
    # Prestataire — espace pro (liste par défaut)
    path("pro/agenda/", views.prestataire_rdv_list, name="prestataire_rdv_list"),
    path("pro/agenda/grille/", views.prestataire_agenda, name="prestataire_agenda"),
    path(
        "pro/agenda/liste/",
        RedirectView.as_view(pattern_name="appointments:prestataire_rdv_list", permanent=False),
    ),
    path(
        "pro/agenda/ticket/",
        RedirectView.as_view(url="/rdv/pro/agenda/?view=ticket", permanent=False),
    ),
    path("pro/sans-rendez-vous/", views.prestataire_rdv_create, name="prestataire_rdv_create"),
    path("pro/<str:ref>/deplacer/", views.prestataire_rdv_move, name="prestataire_rdv_move"),
    path("pro/<str:ref>/modifier/", views.prestataire_rdv_update, name="prestataire_rdv_update"),
    path("pro/<str:ref>/action/", views.prestataire_rdv_action, name="prestataire_rdv_action"),
]
