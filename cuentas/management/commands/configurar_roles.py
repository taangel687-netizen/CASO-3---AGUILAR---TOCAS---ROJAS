from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Crea los grupos del caso y asigna permisos de dominio configurados."

    @transaction.atomic
    def handle(self, *args, **options):
        for rol, nombre in settings.CASO.roles.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            for clave in settings.PERMISOS_GRUPOS.get(rol, ()):
                app, modelo, codigo = clave.split(".")
                try:
                    permiso = Permission.objects.get(
                        content_type__app_label=app, content_type__model=modelo, codename=codigo,
                    )
                except Permission.DoesNotExist as error:
                    raise CommandError(f"Falta el permiso {clave}. Revisa las migraciones.") from error
                grupo.permissions.add(permiso)
            self.stdout.write(nombre)
