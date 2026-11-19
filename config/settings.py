import os
from pathlib import Path

from cuentas.casos import CASO

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = (
    os.getenv("DJANGO_SECRET_KEY", "django-insecure-local-development-only")
    if DEBUG else os.environ["DJANGO_SECRET_KEY"]
)
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
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

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{name}"}
    for name in (
        "UserAttributeSimilarityValidator", "MinimumLengthValidator",
        "CommonPasswordValidator", "NumericPasswordValidator",
    )
]

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

INSTALLED_APPS += ["cuentas"]
MIDDLEWARE += [
    "cuentas.middleware.AuditoriaMiddleware",
    "cuentas.middleware.SesionMiddleware",
    "cuentas.middleware.AvisosIngresoMiddleware",
    "cuentas.middleware.HorarioMiddleware",
]
TEMPLATES[0]["OPTIONS"]["context_processors"].append("cuentas.views.contexto_caso")

LOGIN_URL = "ingreso"
LOGIN_REDIRECT_URL = "panel"
LOGOUT_REDIRECT_URL = "inicio"
SESSION_COOKIE_NAME = "asistencia_sesion"
SESSION_COOKIE_AGE = CASO.minutos * 60
AVISOS_INGRESO = os.getenv("DJANGO_AVISOS_INGRESO", "")
PERMISOS_GRUPOS = {}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "loggers": {"cuentas.auditoria": {"handlers": ["consola"], "level": "INFO", "propagate": False}},
}

INSTALLED_APPS.append("asistencia")
AVISOS_INGRESO = os.getenv("DJANGO_AVISOS_INGRESO", "asistencia.avisos.avisos_ingreso")
PERMISOS_GRUPOS = {
    "rrhh": (
        "asistencia.area.view_area", "asistencia.area.add_area", "asistencia.area.change_area",
        "asistencia.empleado.view_empleado", "asistencia.empleado.add_empleado", "asistencia.empleado.change_empleado",
        "asistencia.asistencia.view_asistencia", "asistencia.asistencia.registrar_asistencia",
        "asistencia.asistencia.corregir_asistencia", "asistencia.asistencia.ver_reportes_globales",
        "asistencia.permiso.view_permiso", "asistencia.permiso.solicitar_permiso", "asistencia.permiso.aprobar_permiso",
    ),
    "jefe": (
        "asistencia.asistencia.registrar_asistencia", "asistencia.asistencia.ver_reportes_area",
        "asistencia.permiso.solicitar_permiso", "asistencia.permiso.aprobar_permiso",
    ),
    "empleado": ("asistencia.asistencia.registrar_asistencia", "asistencia.permiso.solicitar_permiso"),
    "contador": ("asistencia.asistencia.ver_reportes_globales",),
}
