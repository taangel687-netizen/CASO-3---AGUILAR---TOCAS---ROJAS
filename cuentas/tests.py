from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import transaction
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import path, reverse
from django.utils import timezone

from config.urls import urlpatterns as portal

from .auditoria import auditar_operacion
from .horarios import validar_marcacion
from .middleware import controla_horario
from .models import EventoAuditoria
from .permisos import (
    aprobar_permiso, corregir_asistencia, registrar_asistencia, solicitar_permiso, ver_reportes_globales,
)

CLAVE = "Clave-local-para-pruebas-81"
LIMA = ZoneInfo("America/Lima")


def cuenta(rol):
    correo = f"{rol}@{settings.CASO.dominio}"
    usuario = get_user_model().objects.create_user(correo, password=CLAVE)
    usuario.groups.add(Group.objects.get(name=settings.CASO.roles[rol]))
    return usuario


def aviso_prueba(usuario, ahora):
    return ("Todavía no registras tu entrada de hoy.",)


def validar_prueba(request):
    apertura = datetime(2026, 11, 21, 8, tzinfo=LIMA)
    horas = int(request.POST.get("horas", "0"))
    validar_marcacion(apertura + timedelta(hours=horas), apertura)


@controla_horario(validar_prueba)
def operacion(request):
    return HttpResponse("Guardado")


def cambio(request):
    with transaction.atomic():
        auditar_operacion(request, "asistencia_corregida", "asistencia", 14)
        if request.GET.get("revertir"):
            transaction.set_rollback(True)
    return HttpResponse("Operación de prueba")


urlpatterns = [*portal, path("prueba/horario/", operacion), path("prueba/cambio/", cambio)]


@override_settings(ROOT_URLCONF=__name__)
class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("configurar_roles", verbosity=0)
        cls.usuario = cuenta("empleado")

    def ingresar(self, **extras):
        return self.client.post(reverse("ingreso"), {
            "username": self.usuario.username.upper(),
            "password": CLAVE,
            **extras,
        })

    def test_cookie_y_salida(self):
        respuesta = self.ingresar(next="https://otro.invalid/")
        self.assertRedirects(respuesta, reverse("panel"))
        cookie = respuesta.cookies[settings.SESSION_COOKIE_NAME]
        self.assertEqual(int(cookie["max-age"]), 2700)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(self.client.get(reverse("salida")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("salida")), reverse("inicio"))
        self.assertRedirects(self.client.get(reverse("panel")), "/ingresar/?next=/mi-cuenta/")

    def test_csrf_y_dominio(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse("ingreso")).status_code, 403)
        self.assertContains(self.ingresar(username="usuario@otro.invalid"), "@tecnoandes.pe")

    def test_acceso_denegado_visible_en_bitacora(self):
        self.ingresar()
        self.assertEqual(self.client.get(reverse("auditoria")).status_code, 403)
        self.assertTrue(EventoAuditoria.objects.filter(
            accion="acceso_denegado", usuario=self.usuario, recurso="auditoria",
        ).exists())
        self.client.force_login(cuenta("rrhh"))
        self.assertContains(self.client.get(reverse("auditoria")), "acceso_denegado")

    def test_inactividad_y_bloqueo(self):
        self.ingresar()
        futuro = timezone.now() + timedelta(minutes=45)
        with patch("cuentas.middleware.timezone.now", return_value=futuro):
            self.assertRedirects(self.client.get(reverse("panel")), "/ingresar/?next=/mi-cuenta/")
        self.ingresar()
        get_user_model().objects.filter(pk=self.usuario.pk).update(is_active=False)
        self.assertRedirects(self.client.get(reverse("panel")), "/ingresar/?next=/mi-cuenta/")
        self.assertTrue(EventoAuditoria.objects.filter(
            accion="cuenta_desactivada", usuario=self.usuario,
        ).exists())

    @override_settings(AVISOS_INGRESO="cuentas.tests.aviso_prueba")
    def test_aviso_de_ingreso_una_vez(self):
        self.ingresar()
        self.assertContains(self.client.get(reverse("panel")), "Todavía no registras tu entrada de hoy.")
        self.assertNotContains(self.client.get(reverse("panel")), "Todavía no registras tu entrada de hoy.")

    def test_middleware_rechaza_post_fuera_de_horario(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.post("/prueba/horario/", {"horas": "2"}).status_code, 200)
        self.assertEqual(self.client.post("/prueba/horario/", {"horas": "3"}).status_code, 400)

    def test_aprobacion_restringida_por_area(self):
        jefe = cuenta("jefe")
        rrhh = cuenta("rrhh")
        aprobar_permiso(jefe, 1, 1)
        aprobar_permiso(rrhh, None, 2)
        with self.assertRaises(PermissionDenied):
            aprobar_permiso(jefe, 1, 2)
        with self.assertRaises(PermissionDenied):
            aprobar_permiso(jefe, None, None)
        with self.assertRaises(PermissionDenied):
            aprobar_permiso(self.usuario, 1, 1)

    def test_marcacion_propia_y_reportes_solo_lectura(self):
        contador = cuenta("contador")
        registrar_asistencia(self.usuario, self.usuario.pk)
        solicitar_permiso(self.usuario, self.usuario.pk)
        with self.assertRaises(PermissionDenied):
            registrar_asistencia(self.usuario, self.usuario.pk + 1)
        ver_reportes_globales(contador, "GET")
        with self.assertRaises(PermissionDenied):
            ver_reportes_globales(contador, "POST")
        with self.assertRaises(PermissionDenied):
            corregir_asistencia(contador)
        corregir_asistencia(cuenta("rrhh"))

    def test_auditoria_respeta_la_transaccion_del_dominio(self):
        self.client.force_login(cuenta("rrhh"))
        self.assertEqual(self.client.post("/prueba/cambio/").status_code, 200)
        self.assertEqual(self.client.post("/prueba/cambio/?revertir=1").status_code, 200)
        self.assertEqual(EventoAuditoria.objects.filter(accion="asistencia_corregida").count(), 1)
