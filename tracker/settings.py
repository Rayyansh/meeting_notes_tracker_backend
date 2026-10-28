from datetime import timedelta
from pathlib import Path

from tracker.config import Configurations
from tracker.constants import Constants

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = Configurations.secret_key
DEBUG = Configurations.debug
ALLOWED_HOSTS = Configurations.allowed_hosts

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "tracker_apps.common",
    "tracker_apps.authentication",
    "tracker_apps.meeting",
    "tracker_apps.action_item",
    "tracker_apps.ai_service",
    "tracker_apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tracker.urls"
WSGI_APPLICATION = "tracker.wsgi.application"
ASGI_APPLICATION = "tracker.asgi.application"

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(Configurations.db_path)
        if Path(Configurations.db_path).is_absolute()
        else BASE_DIR / Configurations.db_path,
        "OPTIONS": {
            "timeout": Configurations.db_timeout_seconds,
            "init_command": Constants.sqlite_wal_pragma,
            "transaction_mode": "IMMEDIATE",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "tracker_apps.common.common.drf_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_THROTTLE_RATES": {
        "login": Configurations.login_throttle_rate,
        "register": Configurations.register_throttle_rate,
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=Configurations.access_token_minutes),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=Configurations.refresh_token_days),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "AI Meeting Notes & Action Tracker API",
    "DESCRIPTION": "Post-meeting workflow: meetings, transcripts, AI analysis, action items, dashboard.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"]
    if DEBUG
    else ["rest_framework.permissions.IsAuthenticated"],
}

CORS_ALLOWED_ORIGINS = Configurations.cors_allowed_origins
CORS_ALLOW_ALL_ORIGINS = False

DATA_UPLOAD_MAX_MEMORY_SIZE = Configurations.upload_max_bytes + 65536
FILE_UPLOAD_MAX_MEMORY_SIZE = Configurations.upload_max_bytes

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SECURE_SSL_REDIRECT = Configurations.secure_ssl_redirect
    SESSION_COOKIE_SECURE = Configurations.secure_ssl_redirect
    CSRF_COOKIE_SECURE = Configurations.secure_ssl_redirect

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": Configurations.log_level},
}
