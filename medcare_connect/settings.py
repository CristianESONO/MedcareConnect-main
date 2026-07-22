import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Charge .env sans dépendance (PEP 668 / prod sans venv système)
_env_file = BASE_DIR / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k and _k not in os.environ:
            os.environ[_k] = _v

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-dev-key-change-in-production-medcare-connect-2024",
)

DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",") if h.strip()]


def _running_tests() -> bool:
    if "test" in sys.argv:
        return True
    if any("pytest" in (arg or "") for arg in sys.argv):
        return True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    if os.environ.get("MEDCARE_TESTING"):
        return True
    return False


# Tests Django / pytest : pas de redirect HTTPS, host testserver autorisé.
if _running_tests():
    if "testserver" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append("testserver")

# Origines autorisées pour le cookie CSRF (connexion / formulaires via IP ou nom de domaine public)
_csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]

# Politique d’usage Nominatim (OpenStreetMap) — identifiant obligatoire côté requêtes HTTP
NOMINATIM_USER_AGENT = os.environ.get(
    "NOMINATIM_USER_AGENT",
    "MedCareConnect/1.0 (+https://medcareconnect.sn; contact@medcareconnect.sn)",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third-party
    "django_select2",
    # Project apps
    "users",
    "healthcare",
    "cart",
    "messaging",
    "dashboard",
    "notifications",
    "appointments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "medcare_connect.middleware.Select2DebugMiddleware",
]

ROOT_URLCONF = "medcare_connect.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "medcare_connect.context_processors.global_context",
            ],
        },
    },
]

WSGI_APPLICATION = "medcare_connect.wsgi.application"

# Database — PostgreSQL in Docker, SQLite for local dev
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "medcare_db"),
            "USER": os.environ.get("POSTGRES_USER", "medcare_user"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "medcare_password"),
            "HOST": "db",
            "PORT": "5432",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Serveur Playwright (runserver) : base SQLite jetable, jamais db.sqlite3 prod.
_E2E_SQLITE = BASE_DIR / ".cache" / "e2e_playwright.sqlite3"
if (
    os.environ.get("MEDCARE_TESTING")
    and "test" not in sys.argv
    and not any("pytest" in (arg or "") for arg in sys.argv)
):
    _E2E_SQLITE.parent.mkdir(parents=True, exist_ok=True)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _E2E_SQLITE,
        }
    }

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-FR"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/connexion/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

_SERVE_HTTPS = os.environ.get("HTTPS_ENABLED", "").lower() in ("true", "1", "yes")
_TRUST_PROXY = os.environ.get("TRUST_PROXY_HEADERS", "").lower() in ("true", "1", "yes")

# Reverse proxy (Nginx) : cookies / redirects HTTPS corrects derrière TLS
if _TRUST_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

CSRF_COOKIE_SECURE = _SERVE_HTTPS
SESSION_COOKIE_SECURE = _SERVE_HTTPS
CSRF_COOKIE_HTTPONLY = _SERVE_HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

if _SERVE_HTTPS:
    SECURE_SSL_REDIRECT = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

if _running_tests():
    SECURE_SSL_REDIRECT = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False

(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "select2_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "filename": str(BASE_DIR / "logs" / "select2.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Logs très verbeux dédiés à django-select2 (middleware).
        "medcare.select2": {"handlers": ["console", "select2_file"], "level": "DEBUG", "propagate": False},
        # Verbeux sur lib django-select2 elle-même.
        "django_select2": {"handlers": ["console", "select2_file"], "level": "DEBUG", "propagate": False},
        # Verbeux sur backend Redis cache.
        "django_redis": {"handlers": ["console", "select2_file"], "level": "DEBUG", "propagate": False},
    },
}

# Cache
# Important pour django-select2 (widgets "heavy") : le field_id est stocké en cache entre
# le rendu de la page et l'appel AJAX. Avec plusieurs workers Gunicorn, un cache
# locmem (par-process) provoque des 404 sur /select2/fields/auto.json.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "select2": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

SELECT2_CACHE_BACKEND = "select2"

# Secours si le champ « URL Avis Google » est vide dans Admin → Réglages notifications
MEDCARE_GOOGLE_REVIEWS_URL = os.environ.get("MEDCARE_GOOGLE_REVIEWS_URL", "").strip()

# Active les logs ultra détaillés du middleware Select2DebugMiddleware.
SELECT2_DEBUG_LOGS = os.environ.get("SELECT2_DEBUG_LOGS", "1").lower() in ("true", "1", "yes")
