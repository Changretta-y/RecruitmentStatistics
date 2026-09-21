"""Django settings for the backend service."""

import os
from pathlib import Path
from datetime import timedelta
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip() or os.environ.get("SECRET_KEY", "").strip()
DEBUG = _env_bool("DJANGO_DEBUG", default=False)
IS_PRODUCTION = os.environ.get("DJANGO_ENV", "").strip().lower() == "production"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]
CORS_ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
)

ROOT_URLCONF = "backend.config.urls"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "backend.config.middleware.CorsSecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "backend.config.middleware.RequestAuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "backend.apps.accounts",
    "backend.apps.applications",
    "backend.apps.health",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


def _postgres_database_from_url(database_url: str) -> dict[str, object]:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ImproperlyConfigured(
            "DATABASE_URL must use the postgres:// or postgresql:// scheme"
        )

    name = unquote(parsed.path.lstrip("/"))
    if not parsed.hostname or not name:
        raise ImproperlyConfigured(
            "DATABASE_URL must include both a PostgreSQL host and database name"
        )

    query = parse_qs(parsed.query)
    options = {
        key: values[-1]
        for key, values in query.items()
        if key not in {"sslmode", "connect_timeout"}
    }
    if "sslmode" in query:
        options["sslmode"] = query["sslmode"][-1]
    if "connect_timeout" in query:
        options["connect_timeout"] = query["connect_timeout"][-1]

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": str(parsed.port or ""),
        "OPTIONS": options,
        "CONN_MAX_AGE": 60,
        "TEST": {"NAME": f"{name}_test"},
    }


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {"default": _postgres_database_from_url(DATABASE_URL)}
else:
    # Keep settings importable for API checks, but never silently use SQLite.
    # Any command that opens the database receives a clear configuration error.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "",
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "TEST": {"NAME": "_missing_database_url_test"},
        }
    }

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# Keep the static-files handler usable for the public development entry point
# without coupling production deployment to a writable source directory.
STATIC_URL = os.environ.get("DJANGO_STATIC_URL", "/static/").strip() or "/static/"
if (
    not STATIC_URL.startswith("/")
    or STATIC_URL.startswith("//")
    or not STATIC_URL.endswith("/")
):
    raise ImproperlyConfigured("DJANGO_STATIC_URL must be an absolute URL path ending with '/'")
STATIC_ROOT = Path(
    os.environ.get("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
).resolve()

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = os.environ.get(
    "SECURE_REFERRER_POLICY",
    "strict-origin-when-cross-origin",
)
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", default=IS_PRODUCTION)
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000" if IS_PRODUCTION else "0") or "0")
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=IS_PRODUCTION)
SECURE_HSTS_PRELOAD = _env_bool("SECURE_HSTS_PRELOAD", default=IS_PRODUCTION)
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", default=IS_PRODUCTION)
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", default=IS_PRODUCTION)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "EXCEPTION_HANDLER": "backend.config.exceptions.safe_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Campus Recruitment Progress API",
    "DESCRIPTION": "公开认证和投递进度 API。",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
