from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from cuentas.models import EventoAuditoria

from .models import Area, Asistencia, Empleado, Permiso


class AsistenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("configurar_roles", stdout=StringIO())
        call_command("cargar_asistencia_demo", stdout=StringIO())

    def cuenta(self, alias):
        return get_user_model().objects.get(username=f"{alias}@tecnoandes.pe")

    def test_marcacion_ventana_y_recordatorio(self):
        empleado = self.cuenta("demo-empleado-05")
        empleado.set_password("Clave-de-prueba-2026")
        empleado.save(update_fields=["password"])
        entrada = datetime(2026, 11, 23, 8, tzinfo=ZoneInfo("America/Lima"))
        ruta = reverse("asistencia:marcar")
        with patch("asistencia.views.timezone.now", return_value=entrada):
            respuesta = self.client.post(reverse("ingreso"), {
                "username": empleado.username, "password": "Clave-de-prueba-2026",
            }, follow=True)
            self.assertContains(respuesta, "Todavía no registras tu entrada")
            self.assertRedirects(self.client.post(ruta, {"tipo": "entrada"}), ruta)
            self.assertContains(self.client.post(ruta, {"tipo": "entrada"}), "Ya tienes una entrada")
        with patch("asistencia.views.timezone.now", return_value=entrada + timedelta(hours=9)):
            self.client.force_login(empleado)
            self.assertRedirects(self.client.post(ruta, {"tipo": "salida"}), ruta)
        registro = Asistencia.objects.get(empleado__usuario=empleado, fecha=entrada.date())
        self.assertEqual(registro.horas, 9)
        with patch("asistencia.views.timezone.now", return_value=entrada + timedelta(hours=5)):
            self.client.force_login(empleado)
            self.assertEqual(self.client.post(ruta, {"tipo": "entrada"}).status_code, 400)

    def test_jefatura_solo_resuelve_su_area_y_contador_solo_lee(self):
        jefe = self.cuenta("demo-jefe")
        propio = Permiso.objects.get(empleado__usuario=self.cuenta("demo-empleado-05"))
        ajeno = Permiso.objects.get(empleado__usuario=self.cuenta("demo-empleado-01"))
        self.client.force_login(jefe)
        datos = {"estado": "aprobado"}
        ruta_ajena = reverse("asistencia:decidir", args=[ajeno.pk])
        ruta_propia = reverse("asistencia:decidir", args=[propio.pk])
        self.assertEqual(self.client.post(ruta_ajena, datos).status_code, 403)
        self.assertRedirects(self.client.post(ruta_propia, datos), reverse("asistencia:permisos_area"))
        propio.refresh_from_db()
        self.assertEqual(propio.estado, Permiso.Estado.APROBADO)
        self.assertTrue(EventoAuditoria.objects.filter(usuario=jefe, accion="permiso_aprobado").exists())
        self.client.force_login(self.cuenta("demo-contador"))
        self.assertContains(self.client.get(reverse("asistencia:reportes_globales")), "Reporte de asistencia")
        self.assertEqual(self.client.post(ruta_propia, datos).status_code, 403)

    def test_carga_repetible(self):
        call_command("cargar_asistencia_demo", stdout=StringIO())
        self.assertEqual(Area.objects.count(), 5)
        self.assertEqual(Empleado.objects.count(), 10)
        self.assertEqual(Asistencia.objects.count(), 50)
        self.assertEqual(Permiso.objects.count(), 10)
