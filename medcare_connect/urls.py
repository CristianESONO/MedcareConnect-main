from django.contrib import admin
from django.views.generic import RedirectView
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from medcare_connect import views
from users import views as users_views
from healthcare import practitioner_views as pr_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("select2/", include("django_select2.urls")),
    path("", views.home, name="home"),

    # Routes d'authentification à la racine
    path("inscription/", users_views.register, name="register"),
    path("connexion/", users_views.login_view, name="login"),
    path("deconnexion/", users_views.logout_view, name="logout"),

    # Routes canoniques en français pour les pages d'information
    path("comment-ca-marche/", views.how_it_works, name="how_it_works"),
    path("a-propos/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("confiance/", views.trust, name="trust"),

    # Redirections d'anciennes pages
    path("landing/", RedirectView.as_view(url="/inscription/", permanent=True), name="landing"),
    path("rejoindre/", RedirectView.as_view(url="/inscription/", permanent=True), name="rejoindre"),
    path("how-it-works/", RedirectView.as_view(url="/comment-ca-marche/", permanent=True)),
    path("about/", RedirectView.as_view(url="/a-propos/", permanent=True)),
    path("trust/", RedirectView.as_view(url="/confiance/", permanent=True)),
    path("medcare-sn/", views.home_medcare_sn, name="medcare_sn"),

    # Applications
    path("users/", include("users.urls")),
    path("sante/", include("healthcare.urls")),
    path("cart/", include("cart.urls")),
    path("messaging/", include("messaging.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("notifications/", include("notifications.urls")),
    path("rdv/", include("appointments.urls")),

    # Étape 5 — Tickets de prestation (liens directs praticien → patient)
    # Route courte /t/<identifiant> : non indexée (noindex), accessible sans login
    path("t/<str:token>/", pr_views.patient_ticket_view, name="patient_ticket_view"),
    path("patient-mobile/", pr_views.patient_mobile_view, name="patient_mobile"),
    path("demo-patient/", pr_views.patient_mobile_view, name="demo_patient"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "medcare_connect.views.page_not_found"
