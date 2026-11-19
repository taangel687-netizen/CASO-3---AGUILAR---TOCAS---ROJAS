from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import F
from django.utils import timezone

from cuentas.horarios import validar_marcacion

from .models import Asistencia, Empleado, Permiso


def bloquear_empleado(empleado):
    empleados = Empleado.objects.filter(pk=empleado.pk)
    if connection.vendor == "sqlite":
        empleados.update(cargo=F("cargo"))
    return empleados.select_for_update().get()


def turno(empleado, ahora, tipo):
    dia = timezone.localdate(ahora)
    if dia.weekday() >= 5:
        return None
    hora = empleado.hora_entrada if tipo == "entrada" else empleado.hora_salida
    return timezone.make_aware(datetime.combine(dia, hora))


def validar_turno(empleado, ahora, tipo):
    objetivo = turno(empleado, ahora, tipo)
    if objetivo is None:
        raise ValidationError("Este día no tiene un turno programado.")
    validar_marcacion(ahora, objetivo)


def marcar_asistencia(empleado, ahora, tipo):
    empleado = bloquear_empleado(empleado)
    validar_turno(empleado, ahora, tipo)
    dia = timezone.localdate(ahora)
    registro = empleado.asistencias.filter(fecha=dia, salida__isnull=True).first()
    if tipo == "entrada":
        if registro:
            raise ValidationError("Ya tienes una entrada sin salida para hoy.")
        return Asistencia.objects.create(empleado=empleado, fecha=dia, entrada=ahora)
    if not registro or ahora <= registro.entrada:
        raise ValidationError("Registra primero una entrada. La salida debe ser posterior.")
    registro.salida = ahora
    registro.save(update_fields=["salida"])
    return registro


def saldo_vacaciones(empleado):
    usados = sum((fin - inicio).days + 1 for inicio, fin in empleado.permisos.filter(
        tipo=Permiso.Tipo.VACACIONES, estado=Permiso.Estado.APROBADO,
    ).values_list("inicio", "fin"))
    return max(0, 30 - usados)


def validar_permiso(empleado, tipo, inicio, fin):
    if fin < inicio:
        raise ValidationError("La fecha de fin debe ser igual o posterior a la de inicio.")
    if empleado.permisos.exclude(estado=Permiso.Estado.RECHAZADO).filter(inicio__lte=fin, fin__gte=inicio).exists():
        raise ValidationError("Ya tienes un permiso que coincide con esas fechas.")
    if tipo == Permiso.Tipo.VACACIONES and (fin - inicio).days + 1 > saldo_vacaciones(empleado):
        raise ValidationError("La solicitud supera el saldo disponible de vacaciones.")


def resolver_permiso(permiso, usuario, estado):
    bloquear_empleado(permiso.empleado)
    permiso.refresh_from_db()
    if permiso.estado != Permiso.Estado.PENDIENTE:
        raise ValidationError("Esta solicitud ya fue resuelta.")
    if estado == Permiso.Estado.APROBADO and permiso.tipo == Permiso.Tipo.VACACIONES:
        if (permiso.fin - permiso.inicio).days + 1 > saldo_vacaciones(permiso.empleado):
            raise ValidationError("El empleado ya no tiene suficientes días de vacaciones.")
    permiso.estado = estado
    permiso.decidido_en = timezone.now()
    permiso.decidido_por = usuario
    permiso.save(update_fields=["estado", "decidido_en", "decidido_por"])


def resumir_asistencia(registros):
    jornadas = {}
    for registro in registros.select_related("empleado"):
        llave = (registro.empleado_id, registro.fecha)
        fila = jornadas.setdefault(llave, {
            "nombre": str(registro.empleado), "fecha": registro.fecha, "total": timedelta(),
        })
        if registro.salida:
            fila["total"] += registro.salida - registro.entrada
    filas = []
    for fila in jornadas.values():
        horas = fila["total"].total_seconds() / 3600
        filas.append({**fila, "horas": round(horas, 2), "extras": round(max(0, horas - 8), 2)})
    return filas
