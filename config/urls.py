from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", include("cuentas.urls")),
    path("", TemplateView.as_view(template_name="inicio.html"), name="inicio"),
    path("admin/", admin.site.urls),
    path("asistencia/", include("asistencia.urls")),
]
