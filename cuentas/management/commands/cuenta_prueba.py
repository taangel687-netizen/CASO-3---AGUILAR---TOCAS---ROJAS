from getpass import getpass

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Crea una cuenta ficticia local y le asigna un grupo del caso."

    def add_arguments(self, parser):
        parser.add_argument("alias")
        parser.add_argument("rol", choices=settings.CASO.roles)

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Las cuentas de prueba requieren DJANGO_DEBUG=1.")
        alias = options["alias"].lower()
        if not alias.isascii() or not alias.replace("-", "").isalnum():
            raise CommandError("Usa letras ASCII, números y guiones para el alias.")
        correo = f"{alias}@{settings.CASO.dominio}"
        usuarios = get_user_model().objects
        if usuarios.filter(username=correo).exists():
            raise CommandError("La cuenta de prueba ya existe.")
        rol = options["rol"]
        grupo, _ = Group.objects.get_or_create(name=settings.CASO.roles[rol])
        usuario = usuarios.model(username=correo, email=correo, first_name=alias.capitalize())
        password = getpass("Contraseña temporal: ")
        try:
            password_validation.validate_password(password, usuario)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        usuario.set_password(password)
        usuario.is_staff = rol in {"admin", "rrhh"}
        usuario.save()
        usuario.groups.add(grupo)
        self.stdout.write(self.style.SUCCESS(correo))
