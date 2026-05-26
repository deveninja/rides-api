from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    DATABASE_CONN_MAX_AGE=(int, 60),
    PAGE_SIZE=(int, 20),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = [host.strip() for host in env("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "rest_framework.authtoken",
    "rides",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wingz_api.urls"

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

WSGI_APPLICATION = "wingz_api.wsgi.application"
ASGI_APPLICATION = "wingz_api.asgi.application"

if env("DATABASE_URL", default=""):
    DATABASES = {
        "default": env.db("DATABASE_URL"),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": env("DATABASE_ENGINE", default="django.db.backends.sqlite3"),
            "NAME": env("DATABASE_NAME", default=str(BASE_DIR / "db.sqlite3")),
            "USER": env("DATABASE_USER", default=""),
            "PASSWORD": env("DATABASE_PASSWORD", default=""),
            "HOST": env("DATABASE_HOST", default=""),
            "PORT": env("DATABASE_PORT", default=""),
            "CONN_MAX_AGE": env.int("DATABASE_CONN_MAX_AGE", default=60),
        }
    }

AUTH_USER_MODEL = "rides.User"
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
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_PAGINATION_CLASS": "rides.pagination.RidePagination",
    "PAGE_SIZE": env.int("PAGE_SIZE", default=20),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Wingz Ride API",
    "DESCRIPTION": "Interactive API documentation for the Wingz ride management service.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SECURITY": [{"tokenAuth": []}],
    "COMPONENT_SPLIT_REQUEST": True,
}
