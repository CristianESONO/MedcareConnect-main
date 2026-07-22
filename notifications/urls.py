from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    # Espace admin Medcare
    path("admin/settings/", views.admin_settings, name="admin_settings"),
    path("admin/rules/", views.admin_rules, name="admin_rules"),
    path("admin/rules/<int:event_id>/<int:channel_id>/", views.admin_rule_edit, name="admin_rule_edit"),
    path("admin/templates/", views.admin_templates, name="admin_templates"),
    path(
        "admin/messages-whatsapp-patient/",
        views.admin_patient_wa_messages,
        name="admin_patient_wa_messages",
    ),
    path("admin/logs/", views.admin_logs, name="admin_logs"),
    path("admin/logs/resend/", views.admin_log_resend, name="admin_log_resend"),
    # Préférences utilisateur
    path("preferences/", views.my_preferences, name="my_preferences"),
]
