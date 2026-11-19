from django.utils import timezone

from cuentas.avisos import entrada_pendiente

from .models import Empleado
from .servicios import turno


def avisos_ingreso(usuario, ahora):
    empleado = Empleado.objects.filter(usuario=usuario).first()
    if empleado is None:
        return ()
    entrada = turno(empleado, ahora, "entrada")
    marco = empleado.asistencias.filter(fecha=timezone.localdate(ahora)).exists()
    return entrada_pendiente(entrada, marco, ahora)
