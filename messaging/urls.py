from django.urls import path
from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/", views.conversation_detail, name="conversation_detail"),
    path("start/<slug:slug>/", views.start_conversation, name="start_conversation"),
    path("whatsapp/<slug:slug>/", views.whatsapp_contact, name="whatsapp_contact"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("rappels/", views.rappels_list, name="rappels"),
    path("notifications/<int:pk>/read/", views.notification_read, name="notification_read"),
    path("notifications/mark-all-read/", views.mark_all_read, name="mark_all_read"),
]
