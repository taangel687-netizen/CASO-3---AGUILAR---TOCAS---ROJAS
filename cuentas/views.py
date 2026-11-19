from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .auditoria import registrar
from .forms import FormularioIngreso
from .models import EventoAuditoria
from .permisos import puede_auditar, roles_usuario


RUTAS_POR_ROL = {
    "rrhh": (("Reportes de asistencia", "asistencia:reportes_globales"),),
    "jefe": (("Solicitudes de mi área", "asistencia:permisos_area"),),
    "empleado": (("Marcar asistencia", "asistencia:marcar"), ("Mis solicitudes", "asistencia:mis_permisos")),
    "contador": (("Reportes de asistencia", "asistencia:reportes_globales"),),
}


def enlaces_por_rol(roles):
    enlaces = {}
    for rol in sorted(roles):
        for etiqueta, nombre in RUTAS_POR_ROL[rol]:
            try:
                enlaces[etiqueta] = reverse(nombre)
            except NoReverseMatch:
                continue
    return enlaces



class Ingreso(LoginView):
    authentication_form = FormularioIngreso
    template_name = "cuentas/ingreso.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session["ultima_actividad"] = int(timezone.now().timestamp())
        self.request.ingreso_exitoso = True
        registrar(self.request, "inicio_sesion", response.status_code)
        return response

    def form_invalid(self, form):
        registrar(self.request, "inicio_fallido", 200)
        return super().form_invalid(form)


class Salida(LogoutView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            registrar(request, "cierre_sesion", 302)
        return super().post(request, *args, **kwargs)


@login_required
@never_cache
def panel(request):
    roles = roles_usuario(request.user)
    return render(request, "cuentas/panel.html", {
        "puede_auditar": puede_auditar(request.user),
        "enlaces": enlaces_por_rol(roles),
        "roles": [settings.CASO.roles[rol] for rol in sorted(roles)],
    })


def contexto_caso(request):
    return {"caso": settings.CASO}

@login_required
@never_cache
def auditoria(request):
    if not puede_auditar(request.user):
        raise PermissionDenied
    eventos = EventoAuditoria.objects.select_related("usuario")[:50]
    return render(request, "cuentas/auditoria.html", {"eventos": eventos})
