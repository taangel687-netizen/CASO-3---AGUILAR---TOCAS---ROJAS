from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone


def validar_marcacion(instante, objetivo):
    if timezone.is_naive(instante) or timezone.is_naive(objetivo):
        raise ValidationError("El horario de marcación debe incluir una zona horaria.")
    if abs(instante - objetivo) > timedelta(hours=2):
        raise ValidationError(
            "Marca dentro de las dos horas anteriores o posteriores a tu turno."
        )
