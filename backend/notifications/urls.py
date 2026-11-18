from django.urls import path

from . import views
from . import admin_api
from medcare_connect.views import react_app

app_name = "notifications"

urlpatterns = [
    # Espace admin Medcare
    path("api/admin/settings/", admin_api.settings_api, name="admin_settings_api"),
    path("api/admin/rules/", admin_api.rules_api, name="admin_rules_api"),
    path("api/admin/rules/<int:event_id>/<int:channel_id>/", admin_api.rule_api, name="admin_rule_api"),
    path("api/admin/templates/", admin_api.templates_api, name="admin_templates_api"),
    path("api/admin/templates/<int:template_id>/", admin_api.templates_api, name="admin_template_api"),
    path("api/admin/patient-whatsapp/", admin_api.patient_wa_messages_api, name="admin_patient_wa_messages_api"),
    path("api/admin/logs/", admin_api.logs_api, name="admin_logs_api"),
    path("api/admin/logs/resend/", admin_api.log_resend_api, name="admin_log_resend_api"),
    path("admin/parametres/", react_app, name="admin_settings"),
    path("admin/", react_app, name="admin_home"),
    path("admin/regles/", react_app, name="admin_rules"),
    path("admin/regles/<int:event_id>/<int:channel_id>/", react_app, name="admin_rule_edit"),
    path("admin/modeles/", react_app, name="admin_templates"),
    path(
        "admin/messages-whatsapp-patient/",
        react_app,
        name="admin_patient_wa_messages",
    ),
    path("admin/journaux/", react_app, name="admin_logs"),
    path("admin/journaux/renvoyer/", react_app, name="admin_log_resend"),
    # Préférences utilisateur
    path("api/preferences/", views.preferences_api, name="preferences_api"),
    path("preferences/", views.my_preferences, name="my_preferences"),
]
