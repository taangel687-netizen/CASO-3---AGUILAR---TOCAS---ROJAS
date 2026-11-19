from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from asistencia.models import Area, Asistencia, Empleado, Permiso


def cuenta(alias, rol, nombre):
    correo = f"{alias}@tecnoandes.pe"
    usuario, creado = get_user_model().objects.get_or_create(
        username=correo,
        defaults={"first_name": nombre, "email": f"{alias}@example.test", "is_staff": rol == "rrhh"},
    )
    if creado:
        usuario.set_unusable_password()
        usuario.save(update_fields=["password"])
    grupo, _ = Group.objects.get_or_create(name=settings.CASO.roles[rol])
    usuario.groups.add(grupo)
    return usuario


class Command(BaseCommand):
    help = "Carga 10 empleados, 5 áreas, 50 asistencias y 10 permisos ficticios."

    @transaction.atomic
    def handle(self, *args, **options):
        areas = [Area.objects.get_or_create(nombre=nombre)[0] for nombre in (
            "Sistemas", "Contabilidad", "Ventas", "Logística", "RRHH",
        )]
        cuenta("demo-contador", "contador", "Contabilidad de prueba")
        base = date(2026, 11, 9)
        for indice in range(10):
            rol, alias = ("empleado", f"demo-empleado-{indice:02d}")
            if indice == 0:
                rol, alias = "jefe", "demo-jefe"
            if indice == 4:
                rol, alias = "rrhh", "demo-rrhh"
            usuario = cuenta(alias, rol, f"Empleado {indice + 1}")
            empleado, _ = Empleado.objects.get_or_create(usuario=usuario, defaults={
                "area": areas[indice % len(areas)], "dni": f"98{indice + 1:06d}",
                "nombres": usuario.first_name, "apellidos": "Demostración",
                "cargo": "Jefatura" if rol == "jefe" else "Personal de apoyo",
                "fecha_ingreso": date(2020 + indice % 5, 3, 1), "contrato": Empleado.Contrato.PLANILLA,
                "email": usuario.username, "hora_entrada": time(8), "hora_salida": time(16),
            })
            for offset in range(5):
                fecha = base + timedelta(days=offset)
                entrada = timezone.make_aware(datetime.combine(fecha, time(8)))
                salida = entrada + timedelta(hours=9 if offset == 4 else 8)
                Asistencia.objects.get_or_create(
                    empleado=empleado, fecha=fecha, defaults={"entrada": entrada, "salida": salida},
                )
            inicio = base + timedelta(days=21 + indice)
            Permiso.objects.get_or_create(
                empleado=empleado, inicio=inicio, defaults={
                    "fin": inicio + timedelta(days=1),
                    "tipo": Permiso.Tipo.VACACIONES if indice % 2 else Permiso.Tipo.PERSONAL,
                    "motivo": "Solicitud ficticia de demostración del flujo de aprobación.",
                },
            )
        self.stdout.write(self.style.SUCCESS("Datos ficticios de asistencia listos."))
