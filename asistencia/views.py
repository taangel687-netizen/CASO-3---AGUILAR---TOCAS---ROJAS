from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from cuentas import permisos as politicas
from cuentas.auditoria import auditar_operacion
from cuentas.middleware import controla_horario

from .forms import CorreccionForm, MarcacionForm, PermisoForm, ResolverForm
from .models import Asistencia, Correccion, Empleado, Permiso
from .servicios import (
    bloquear_empleado, marcar_asistencia, resolver_permiso, resumir_asistencia,
    saldo_vacaciones, validar_permiso, validar_turno,
)


def validar_marcacion_request(request):
    if politicas.roles_usuario(request.user).isdisjoint({"empleado", "jefe", "rrhh"}):
        return
    form = MarcacionForm(request.POST)
    if form.is_valid():
        request.empleado_marcacion = get_object_or_404(Empleado, usuario=request.user)
        request.hora_marcacion = timezone.now()
        validar_turno(request.empleado_marcacion, request.hora_marcacion, form.cleaned_data["tipo"])


@require_http_methods(["GET", "POST"])
@politicas.requiere_rol("empleado", "jefe", "rrhh")
@controla_horario(validar_marcacion_request)
def marcar(request):
    empleado = getattr(request, "empleado_marcacion", None) or get_object_or_404(Empleado, usuario=request.user)
    politicas.registrar_asistencia(request.user, empleado.usuario_id)
    form = MarcacionForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                tipo = form.cleaned_data["tipo"]
                ahora = getattr(request, "hora_marcacion", None) or timezone.now()
                registro = marcar_asistencia(empleado, ahora, tipo)
                auditar_operacion(request, f"asistencia_{tipo}", "asistencia", registro.pk)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Marcación de {tipo} registrada.")
            return redirect("asistencia:marcar")
    return render(request, "asistencia/marcar.html", {
        "form": form, "registros": empleado.asistencias.all()[:30],
    })


@require_safe
@politicas.requiere_rol("empleado", "jefe", "rrhh")
def mis_permisos(request):
    empleado = get_object_or_404(Empleado, usuario=request.user)
    politicas.ver_expediente(request.user, empleado.usuario_id)
    return render(request, "asistencia/permisos.html", {
        "titulo": "Mis solicitudes", "permisos": empleado.permisos.all(),
        "saldo": saldo_vacaciones(empleado), "propio": True,
    })


@require_http_methods(["GET", "POST"])
@politicas.requiere_rol("empleado", "jefe", "rrhh")
def solicitar(request):
    empleado = get_object_or_404(Empleado, usuario=request.user)
    politicas.solicitar_permiso(request.user, empleado.usuario_id)
    form = PermisoForm(request.POST if request.method == "POST" else None, empleado=empleado)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                empleado = bloquear_empleado(empleado)
                permiso = form.save(commit=False)
                validar_permiso(empleado, permiso.tipo, permiso.inicio, permiso.fin)
                permiso.empleado = empleado
                permiso.save()
                auditar_operacion(request, "permiso_solicitado", "permiso", permiso.pk)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "La solicitud quedó pendiente de aprobación.")
            return redirect("asistencia:mis_permisos")
    return render(request, "asistencia/formulario.html", {"form": form, "titulo": "Solicitar permiso"})


def area_jefe(usuario):
    return Empleado.objects.filter(usuario=usuario).values_list("area_id", flat=True).first()


@require_safe
@politicas.requiere_rol("jefe", "rrhh")
def permisos_area(request):
    solicitudes = Permiso.objects.select_related("empleado")
    if "rrhh" not in politicas.roles_usuario(request.user):
        solicitudes = solicitudes.filter(empleado__area_id=area_jefe(request.user))
    return render(request, "asistencia/permisos.html", {
        "titulo": "Solicitudes por revisar", "permisos": solicitudes, "gestionar": True,
    })


@require_POST
@politicas.requiere_rol("jefe", "rrhh")
def decidir(request, permiso_id):
    permiso = get_object_or_404(Permiso.objects.select_related("empleado"), pk=permiso_id)
    politicas.aprobar_permiso(request.user, area_jefe(request.user), permiso.empleado.area_id)
    form = ResolverForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                resolver_permiso(permiso, request.user, form.cleaned_data["estado"])
                auditar_operacion(request, f"permiso_{permiso.estado}", "permiso", permiso.pk)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "La decisión ya aparece en las solicitudes del empleado.")
    return redirect("asistencia:permisos_area")


@require_safe
@politicas.requiere_rol("jefe", "rrhh", "contador")
def reportes(request, *, area=False):
    registros = Asistencia.objects.all()
    if area:
        area_id = area_jefe(request.user)
        politicas.ver_reportes_area(request.user, area_id, area_id)
        registros = registros.filter(empleado__area_id=area_id)
    else:
        politicas.ver_reportes_globales(request.user, request.method)
    filas = resumir_asistencia(registros)
    if request.GET.get("formato") == "texto":
        lineas = ["Empleado | Fecha | Horas trabajadas | Horas extra"]
        lineas += [f'{fila["nombre"]} | {fila["fecha"]} | {fila["horas"]} | {fila["extras"]}' for fila in filas]
        return HttpResponse("\n".join(lineas), content_type="text/plain; charset=utf-8")
    return render(request, "asistencia/reportes.html", {
        "filas": filas, "registros": registros.select_related("empleado"),
        "rrhh": "rrhh" in politicas.roles_usuario(request.user),
    })


@require_http_methods(["GET", "POST"])
@politicas.requiere_rol("rrhh")
def corregir(request, registro_id):
    politicas.corregir_asistencia(request.user)
    registro = get_object_or_404(Asistencia.objects.select_related("empleado"), pk=registro_id)
    form = CorreccionForm(request.POST if request.method == "POST" else None, instance=registro)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                bloquear_empleado(registro.empleado)
                original = Asistencia.objects.get(pk=registro.pk)
                if form.cleaned_data["salida"] is None and original.empleado.asistencias.filter(
                    fecha=original.fecha, salida__isnull=True,
                ).exclude(pk=original.pk).exists():
                    raise ValidationError("Ya hay otro registro abierto para esa fecha.")
                Correccion.objects.create(
                    asistencia=original, usuario=request.user, motivo=form.cleaned_data["motivo"],
                    justificacion=form.cleaned_data["justificacion"],
                    entrada_anterior=original.entrada, salida_anterior=original.salida,
                )
                form.save()
                auditar_operacion(request, "asistencia_corregida", "asistencia", registro.pk)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "La corrección quedó registrada.")
            return redirect("asistencia:reportes_globales")
    return render(request, "asistencia/formulario.html", {"form": form, "titulo": "Corregir asistencia"})
