from django.urls import path
from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("api/session/", views.messaging_session_api, name="messaging_session_api"),
    path("api/patient/inbox/", views.patient_inbox_api, name="patient_inbox_api"),
    path("api/provider/inbox/", views.provider_inbox_api, name="provider_inbox_api"),
    path(
        "api/patient/conversations/<int:pk>/",
        views.patient_conversation_api,
        name="patient_conversation_api",
    ),
    path(
        "api/provider/conversations/<int:pk>/",
        views.provider_conversation_api,
        name="provider_conversation_api",
    ),
    path(
        "api/patient/notifications/",
        views.patient_notifications_api,
        name="patient_notifications_api",
    ),
    path(
        "api/provider/notifications/",
        views.provider_notifications_api,
        name="provider_notifications_api",
    ),
    path("<int:pk>/", views.conversation_detail, name="conversation_detail"),
    path("demarrer/<slug:slug>/", views.start_conversation, name="start_conversation"),
    path("whatsapp/<slug:slug>/", views.whatsapp_contact, name="whatsapp_contact"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("rappels/", views.rappels_list, name="rappels"),
    path("notifications/<int:pk>/lu/", views.notification_read, name="notification_read"),
    path("notifications/tout-lire/", views.mark_all_read, name="mark_all_read"),
]
