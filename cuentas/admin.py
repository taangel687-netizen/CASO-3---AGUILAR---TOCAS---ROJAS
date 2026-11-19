from django.contrib import admin

from .models import EventoAuditoria
from .permisos import puede_auditar


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "accion", "recurso", "ip", "estado")
    list_filter = ("accion", "estado", "fecha")
    list_select_related = ("usuario",)
    search_fields = ("usuario__username", "recurso", "ip")
    readonly_fields = ("fecha", "usuario", "accion", "recurso", "ip", "estado")

    def has_view_permission(self, request, obj=None):
        return puede_auditar(request.user)

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
