from django.views.generic import RedirectView
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from medcare_connect import views
from users import views as users_views
from healthcare import practitioner_views as pr_views

urlpatterns = [
    path("admin/", include("medcare_connect.admin_urls")),
    path("select2/", include("django_select2.urls")),
    path("", views.home, name="home"),
    path("api/auth/csrf/", views.csrf_token, name="auth_csrf"),
    path("api/public/home/", views.home_vitrine_data, name="home_vitrine_data"),
    path("api/dashboard/stats/", views.dashboard_stats_api, name="dashboard_stats_api"),
    path("api/auth/register/", users_views.register, name="api_register"),
    path("api/auth/login/", users_views.login_view, name="api_login"),
    path("api/auth/password-reset/", users_views.password_reset_api, name="api_password_reset"),
    path("api/patient-mobile/", pr_views.patient_mobile_data_api, name="patient_mobile_data_api"),
    path(
        "api/auth/password-reset/confirm/<uidb64>/<token>/",
        users_views.password_reset_confirm_api,
        name="api_password_reset_confirm",
    ),
    path("register", views.react_app),
    path("login", views.react_app),
    path(
        "search",
        RedirectView.as_view(url="/sante/recherche/", query_string=True, permanent=True),
    ),
    path("mobile", views.react_app),
    path("dashboard", views.react_app),
    path("panels", views.react_app),
    path("contact", views.react_app),
    path("about", views.react_app),
    path("how-it-works", views.react_app),

    # Routes d'authentification à la racine
    path("inscription/", users_views.register, name="register"),
    path("connexion/", users_views.login_view, name="login"),
    path("deconnexion/", users_views.logout_view, name="logout"),

    # Réinitialisation du mot de passe (mot de passe oublié)
    path("mot-de-passe-oublie/", users_views.password_reset_page, name="password_reset"),
    path("mot-de-passe-oublie/envoye/", users_views.password_reset_page, name="password_reset_done"),
    path(
        "mot-de-passe-oublie/confirmer/<uidb64>/<token>/",
        users_views.password_reset_page,
        name="password_reset_confirm",
    ),
    path("mot-de-passe-oublie/succes/", users_views.password_reset_page, name="password_reset_complete"),

    # Routes canoniques en français pour les pages d'information
    path("comment-ca-marche/", views.react_app, name="how_it_works"),
    path("a-propos/", views.react_app, name="about"),
    path("contact/", views.react_app, name="contact"),
    path("confiance/", views.react_app, name="trust"),

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

    # Favicon
    path("favicon.ico", RedirectView.as_view(url="/static/images/logo-sm.png", permanent=True)),

    # Étape 5 — Tickets de prestation (liens directs praticien → patient)
    # Route courte /t/<identifiant> : non indexée (noindex), accessible sans login
    path("t/<str:token>/", pr_views.patient_ticket_view, name="patient_ticket_view"),
    path("patient-mobile/", pr_views.patient_mobile_view, name="patient_mobile"),
    path("demo-patient/", pr_views.patient_mobile_view, name="demo_patient"),
    path("assistant/", RedirectView.as_view(url="/sante/assistant-collecte/", permanent=False), name="assistant_shortcut"),
    path("chatbot/", RedirectView.as_view(url="/sante/assistant-collecte/", permanent=False), name="chatbot_shortcut"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "medcare_connect.views.page_not_found"
