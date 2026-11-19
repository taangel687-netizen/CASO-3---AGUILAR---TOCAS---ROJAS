from django.conf import settings
from django.db import models


class EventoAuditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True)
    accion = models.CharField(max_length=48)
    recurso = models.CharField(max_length=100, blank=True)
    estado = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("-fecha", "-pk")
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"
