from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html

from cuentas.auditoria import auditar_operacion
from cuentas.permisos import corregir_asistencia, roles_usuario

from .models import Area, Asistencia, Empleado, Permiso
from .servicios import resolver_permiso, saldo_vacaciones


admin.site.register(Area)


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("dni", "nombres", "apellidos", "area", "cargo", "antiguedad", "vacaciones")
    list_filter = ("area", "contrato")
    search_fields = ("dni", "nombres", "apellidos", "cargo")
    list_select_related = ("area",)

    @admin.display(description="Días de vacaciones disponibles")
    def vacaciones(self, empleado):
        return saldo_vacaciones(empleado)


class RegistroAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Asistencia)
class AsistenciaAdmin(RegistroAdmin):
    list_display = ("empleado", "fecha", "entrada", "salida", "horas", "correccion")
    list_filter = ("fecha", "empleado__area")
    search_fields = ("empleado__nombres", "empleado__apellidos")
    list_select_related = ("empleado",)
    date_hierarchy = "fecha"

    @admin.display(description="Corrección")
    def correccion(self, registro):
        return format_html('<a href="{}">Corregir</a>', reverse("asistencia:corregir", args=[registro.pk]))


@admin.register(Permiso)
class PermisoAdmin(RegistroAdmin):
    list_display = ("empleado", "tipo", "inicio", "fin", "estado")
    list_filter = ("estado", "tipo", "empleado__area")
    list_select_related = ("empleado",)
    search_fields = ("empleado__nombres", "empleado__apellidos")
    actions = ("aprobar_seleccionados",)

    def has_aprobar_permission(self, request):
        return "rrhh" in roles_usuario(request.user) and request.user.has_perm("asistencia.aprobar_permiso")

    @admin.action(description="Aprobar permisos seleccionados", permissions=["aprobar"])
    def aprobar_seleccionados(self, request, queryset):
        aprobados = 0
        for permiso in queryset.filter(estado=Permiso.Estado.PENDIENTE).order_by("empleado_id", "pk"):
            try:
                with transaction.atomic():
                    resolver_permiso(permiso, request.user, Permiso.Estado.APROBADO)
                    auditar_operacion(request, "permiso_aprobado", "permiso", permiso.pk)
            except ValidationError as error:
                self.message_user(request, " ".join(error.messages), messages.WARNING)
            else:
                aprobados += 1
        self.message_user(request, f"Permisos aprobados: {aprobados}.")
