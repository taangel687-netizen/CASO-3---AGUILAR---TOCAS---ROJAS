from django.urls import path

from .views import Ingreso, Salida, auditoria, panel

urlpatterns = [
    path("ingresar/", Ingreso.as_view(), name="ingreso"),
    path("salir/", Salida.as_view(), name="salida"),
    path("mi-cuenta/", panel, name="panel"),
    path("auditoria/", auditoria, name="auditoria"),
]
