from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    # Espace admin Medcare
    path("admin/parametres/", views.admin_settings, name="admin_settings"),
    path("admin/regles/", views.admin_rules, name="admin_rules"),
    path("admin/regles/<int:event_id>/<int:channel_id>/", views.admin_rule_edit, name="admin_rule_edit"),
    path("admin/modeles/", views.admin_templates, name="admin_templates"),
    path(
        "admin/messages-whatsapp-patient/",
        views.admin_patient_wa_messages,
        name="admin_patient_wa_messages",
    ),
    path("admin/journaux/", views.admin_logs, name="admin_logs"),
    path("admin/journaux/renvoyer/", views.admin_log_resend, name="admin_log_resend"),
    # Préférences utilisateur
    path("preferences/", views.my_preferences, name="my_preferences"),
]
