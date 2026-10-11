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
    "oauth2_provider",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "backend.apps.accounts",
    "backend.apps.applications",
    "backend.apps.mcp",
    "backend.apps.calendar_events",
    "backend.apps.notifications",
    "backend.apps.health",
    "backend.apps.sharing",
]

try:
    SHARING_RECOMMENDATION_COUNT = int(os.environ.get("SHARING_RECOMMENDATION_COUNT", "10"))
except ValueError as exc:
    raise ImproperlyConfigured("SHARING_RECOMMENDATION_COUNT must be an integer from 1 to 50.") from exc
if not 1 <= SHARING_RECOMMENDATION_COUNT <= 50:
    raise ImproperlyConfigured("SHARING_RECOMMENDATION_COUNT must be an integer from 1 to 50.")

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

# Platform-owned SMTP configuration. The local development default follows
# Django's conventional local SMTP host; production must set EMAIL_HOST to the
# platform's managed SMTP endpoint. An explicitly empty host disables delivery.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
).strip()
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost").strip()
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587") or "587")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "noreply@example.com"
).strip()
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "").rstrip("/")

# MCP is deliberately configured with an explicit public origin.  OAuth
# issuers and RFC 8707 resource indicators are exact strings, so deriving
# these values from an arbitrary reverse-proxy request would make discovery
# and audience validation depend on the proxy headers received by one call.
MCP_PUBLIC_BASE_URL = os.environ.get(
    "MCP_PUBLIC_BASE_URL", FRONTEND_BASE_URL or "https://testserver"
).rstrip("/")
MCP_AUTHORIZATION_ISSUER = os.environ.get(
    "MCP_AUTHORIZATION_ISSUER", MCP_PUBLIC_BASE_URL
).rstrip("/")
MCP_ENDPOINT = os.environ.get("MCP_ENDPOINT", "/mcp").strip() or "/mcp"
if not MCP_ENDPOINT.startswith("/") or MCP_ENDPOINT.endswith("/"):
    raise ImproperlyConfigured("MCP_ENDPOINT must be an absolute path without a trailing slash")
MCP_RESOURCE_URI = os.environ.get(
    "MCP_RESOURCE_URI", f"{MCP_PUBLIC_BASE_URL}{MCP_ENDPOINT}"
).rstrip("/")
try:
    MCP_PROPOSAL_TTL_SECONDS = int(os.environ.get("MCP_PROPOSAL_TTL_SECONDS", "600"))
except ValueError as exc:
    raise ImproperlyConfigured("MCP_PROPOSAL_TTL_SECONDS must be an integer") from exc
if not 60 <= MCP_PROPOSAL_TTL_SECONDS <= 900:
    raise ImproperlyConfigured("MCP_PROPOSAL_TTL_SECONDS must be between 60 and 900 seconds")
# These two switches are deliberately not part of the production configuration
# surface.  They are useful for black-box acceptance tests that must exercise
# expiry and an audit sink outage through the public MCP endpoint.  Production
# settings ignore them even if a deployment accidentally leaves the variables
# in its process environment.
if IS_PRODUCTION:
    MCP_TEST_EXPIRED_PROPOSAL_ID = ""
    MCP_TEST_PROPOSAL_TTL_SECONDS = None
    MCP_TEST_AUDIT_FAILURE_MODE = False
else:
    MCP_TEST_EXPIRED_PROPOSAL_ID = os.environ.get("MCP_TEST_EXPIRED_PROPOSAL_ID", "").strip()
    try:
        _test_ttl = os.environ.get("MCP_TEST_PROPOSAL_TTL_SECONDS", "").strip()
        MCP_TEST_PROPOSAL_TTL_SECONDS = int(_test_ttl) if _test_ttl else None
    except ValueError as exc:
        raise ImproperlyConfigured("MCP_TEST_PROPOSAL_TTL_SECONDS must be an integer") from exc
    if MCP_TEST_PROPOSAL_TTL_SECONDS is not None and not 1 <= MCP_TEST_PROPOSAL_TTL_SECONDS <= 900:
        raise ImproperlyConfigured("MCP_TEST_PROPOSAL_TTL_SECONDS must be between 1 and 900 seconds")
    MCP_TEST_AUDIT_FAILURE_MODE = os.environ.get("MCP_TEST_AUDIT_FAILURE_MODE", "") == "1"
MCP_PROTECTED_RESOURCE_METADATA_URI = (
    f"{MCP_AUTHORIZATION_ISSUER}/.well-known/oauth-protected-resource{MCP_ENDPOINT}"
)
MCP_ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.environ.get(
        "MCP_ALLOWED_ORIGINS", "https://client.example.test"
    ).split(",")
    if origin.strip()
)
MCP_ALLOWED_HOSTS = tuple(
    host.strip()
    for host in os.environ.get(
        "MCP_ALLOWED_HOSTS",
        "testserver,localhost:*,127.0.0.1:*,[::1]:*",
    ).split(",")
    if host.strip()
)

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

OAUTH2_PROVIDER = {
    # MCP uses the OAuth Toolkit store as the Authorization Server.  The
    # normal web JWT remains a separate authentication system and is never
    # accepted by the MCP resource server.
    "SCOPES": {
        "applications:read": "读取当前用户的投递进度",
        "applications:write": "写入当前用户的投递进度",
    },
    "DEFAULT_SCOPES": [],
    "PKCE_REQUIRED": True,
    "COMPLIANT_BCP_RFC9700_PKCE_METHOD": True,
    "COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS": True,
    "COMPLIANT_BCP_RFC9700_TOKEN_STORAGE": True,
    "COMPLIANT_BCP_RFC9700_IMPLICIT_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PASSWORD_GRANT": True,
    "COMPLIANT_BCP_RFC9700_ACCESS_TOKEN_TRANSPORT": True,
    "REFRESH_TOKEN_REUSE_PROTECTION": True,
    "CIMD_ENABLED": True,
    "DCR_ENABLED": True,
    "DCR_REGISTRATION_PERMISSION_CLASSES": (
        "oauth2_provider.dcr.AllowAllDCRPermission",
    ),
    "OAUTH2_RESPONSE_TYPES_SUPPORTED": ["code"],
    "OAUTH2_GRANT_TYPES_SUPPORTED": ["authorization_code", "refresh_token"],
    "OAUTH2_TOKEN_ENDPOINT_AUTH_METHODS_SUPPORTED": ["none"],
    "ALLOWED_REDIRECT_URI_SCHEMES": ["https"],
    "OIDC_ISS_ENDPOINT": MCP_AUTHORIZATION_ISSUER,
    "OAUTH2_PROTECTED_RESOURCE_IDENTIFIER": MCP_RESOURCE_URI,
    "OAUTH2_PROTECTED_RESOURCE_AUTHORIZATION_SERVERS": [MCP_AUTHORIZATION_ISSUER],
    "OAUTH2_PROTECTED_RESOURCE_BEARER_METHODS_SUPPORTED": ["header"],
}

# AuthorizationView uses Django's session boundary.  The MCP login view is a
# deliberately small browser hand-off; the existing JWT endpoints remain the
# API login mechanism and are not reused as OAuth credentials.
LOGIN_URL = "/oauth/login"
