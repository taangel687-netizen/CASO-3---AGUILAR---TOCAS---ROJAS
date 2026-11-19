from django.urls import path

from . import views

app_name = "asistencia"
urlpatterns = [
    path("", views.marcar, name="marcar"),
    path("permisos/", views.mis_permisos, name="mis_permisos"),
    path("permisos/solicitar/", views.solicitar, name="solicitar"),
    path("permisos/area/", views.permisos_area, name="permisos_area"),
    path("permisos/<int:permiso_id>/resolver/", views.decidir, name="decidir"),
    path("reportes/", views.reportes, name="reportes_globales"),
    path("reportes/area/", views.reportes, {"area": True}, name="reportes_area"),
    path("registros/<int:registro_id>/corregir/", views.corregir, name="corregir"),
]
