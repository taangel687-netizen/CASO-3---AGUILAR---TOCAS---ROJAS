import logging
from ipaddress import ip_address

from django.db import transaction

from .models import EventoAuditoria

logger = logging.getLogger("cuentas.auditoria")


def registrar(request, accion, estado, recurso="", *, usuario=None):
    origen = request.META.get("REMOTE_ADDR", "")
    try:
        ip = str(ip_address(origen))
    except ValueError:
        ip = None

    evento = EventoAuditoria.objects.create(
        usuario=usuario or (request.user if request.user.is_authenticated else None),
        ip=ip, accion=accion, recurso=str(recurso), estado=estado,
    )
    transaction.on_commit(lambda: logger.info(
        "evento=%s usuario=%s ip=%s accion=%s recurso=%s estado=%s",
        evento.pk, evento.usuario_id, evento.ip, evento.accion, evento.recurso, evento.estado,
    ))


def auditar_operacion(request, accion, tipo, objeto_id):
    """Llamar dentro de la transacción que guarda el cambio de dominio."""
    registrar(request, accion, 200, f"{tipo}:{objeto_id}")
