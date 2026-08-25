from django.contrib import admin
from django.views.generic import RedirectView
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from medcare_connect import views
from users import views as users_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("select2/", include("django_select2.urls")),
    path("", views.home, name="home"),

    # Routes canoniques en français pour l'authentification (Accès racine /inscription/ & /connexion/)
    path("inscription/", users_views.register, name="register"),
    path("connexion/", users_views.login_view, name="login"),
    path("deconnexion/", users_views.logout_view, name="logout"),

    # Routes canoniques en français pour les pages d'information
    path("comment-ca-marche/", views.how_it_works, name="how_it_works"),
    path("a-propos/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("confiance/", views.trust, name="trust"),

    # Redirections de compatibilité vers les routes canoniques en français
    path("users/inscription/", RedirectView.as_view(url="/inscription/", permanent=True)),
    path("users/connexion/", RedirectView.as_view(url="/connexion/", permanent=True)),
    path("users/logout/", RedirectView.as_view(url="/deconnexion/", permanent=True)),
    path("landing/", RedirectView.as_view(url="/inscription/", permanent=True), name="landing"),
    path("rejoindre/", RedirectView.as_view(url="/inscription/", permanent=True), name="rejoindre"),
    path("how-it-works/", RedirectView.as_view(url="/comment-ca-marche/", permanent=True)),
    path("about/", RedirectView.as_view(url="/a-propos/", permanent=True)),
    path("trust/", RedirectView.as_view(url="/confiance/", permanent=True)),
    path("medcare-sn/", views.home_medcare_sn, name="medcare_sn"),

    # Applications
    path("users/", include("users.urls")),
    path("healthcare/", include("healthcare.urls")),
    path("cart/", include("cart.urls")),
    path("messaging/", include("messaging.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("notifications/", include("notifications.urls")),
    path("rdv/", include("appointments.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "medcare_connect.views.page_not_found"
