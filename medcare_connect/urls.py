from django.contrib import admin
from django.views.generic import RedirectView
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from medcare_connect import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("select2/", include("django_select2.urls")),
    path("", views.home, name="home"),
    path("landing/", RedirectView.as_view(url="/users/inscription/", permanent=True), name="landing"),
    path("medcare-sn/", views.home_medcare_sn, name="medcare_sn"),
    path("connexion/", RedirectView.as_view(url="/users/connexion/", permanent=False)),
    path("inscription/", RedirectView.as_view(url="/users/inscription/", permanent=False)),
    path("users/", include("users.urls")),
    path("healthcare/", include("healthcare.urls")),
    path("cart/", include("cart.urls")),
    path("messaging/", include("messaging.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("notifications/", include("notifications.urls")),
    path("rdv/", include("appointments.urls")),
    path("about/", views.about, name="about"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("contact/", views.contact, name="contact"),
    path("trust/", views.trust, name="trust"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "medcare_connect.views.page_not_found"
