from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def roles_usuario(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        return set()
    nombres = set(usuario.groups.values_list("name", flat=True))
    return {rol for rol, nombre in settings.CASO.roles.items() if nombre in nombres}


def exige_rol(usuario, *roles):
    if roles_usuario(usuario).isdisjoint(roles):
        raise PermissionDenied


def requiere_rol(*roles):
    def decorar(vista):
        @login_required
        @wraps(vista)
        def protegida(request, *args, **kwargs):
            exige_rol(request.user, *roles)
            return vista(request, *args, **kwargs)
        return protegida
    return decorar


def registrar_asistencia(usuario, empleado_usuario_id):
    exige_rol(usuario, "empleado", "jefe", "rrhh")
    if usuario.pk != empleado_usuario_id:
        raise PermissionDenied


solicitar_permiso = registrar_asistencia


def ver_expediente(usuario, empleado_usuario_id):
    roles = roles_usuario(usuario)
    if "rrhh" not in roles and not (roles.intersection({"empleado", "jefe"}) and usuario.pk == empleado_usuario_id):
        raise PermissionDenied


def aprobar_permiso(usuario, area_jefe_id, area_solicitud_id):
    roles = roles_usuario(usuario)
    if "rrhh" in roles:
        return
    if "jefe" not in roles or area_jefe_id is None or area_jefe_id != area_solicitud_id:
        raise PermissionDenied


def ver_reportes_area(usuario, area_jefe_id, area_reporte_id):
    aprobar_permiso(usuario, area_jefe_id, area_reporte_id)


def ver_reportes_globales(usuario, metodo):
    roles = ("rrhh", "contador") if metodo in {"GET", "HEAD"} else ("rrhh",)
    exige_rol(usuario, *roles)


def corregir_asistencia(usuario):
    exige_rol(usuario, "rrhh")


def puede_auditar(usuario):
    return usuario.is_superuser or "rrhh" in roles_usuario(usuario)
