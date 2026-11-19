from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Area(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name = "área"

    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    class Contrato(models.TextChoices):
        PLANILLA = "planilla", "Planilla"
        LOCACION = "locacion", "Locación"

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, verbose_name="área")
    dni = models.CharField("DNI", max_length=8, unique=True, validators=[RegexValidator(r"^[0-9]{8}$")])
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100)
    fecha_ingreso = models.DateField()
    contrato = models.CharField(max_length=10, choices=Contrato)
    email = models.EmailField("correo corporativo")
    hora_entrada = models.TimeField("inicio del turno")
    hora_salida = models.TimeField("fin del turno")

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    def clean(self):
        errores = {}
        if self.email.lower().rpartition("@")[2] != "tecnoandes.pe":
            errores["email"] = "Usa un correo @tecnoandes.pe."
        if self.fecha_ingreso and self.fecha_ingreso > timezone.localdate():
            errores["fecha_ingreso"] = "La fecha de ingreso no puede ser futura."
        if not self.cargo.strip():
            errores["cargo"] = "Escribe el cargo del empleado."
        if self.hora_entrada and self.hora_salida and self.hora_salida <= self.hora_entrada:
            errores["hora_salida"] = "El fin del turno debe ser posterior al inicio."
        if errores:
            raise ValidationError(errores)

    @property
    def antiguedad(self):
        hoy = timezone.localdate()
        ingreso = self.fecha_ingreso
        meses = 12 * (hoy.year - ingreso.year) + hoy.month - ingreso.month - (hoy.day < ingreso.day)
        anos, meses = divmod(meses, 12)
        return f"{anos} años, {meses} meses"


class Asistencia(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name="asistencias")
    fecha = models.DateField()
    entrada = models.DateTimeField()
    salida = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-entrada",)
        constraints = [
            models.UniqueConstraint(
                fields=("empleado", "fecha"), condition=models.Q(salida__isnull=True),
                name="asistencia_abierta_unica",
            ),
            models.CheckConstraint(
                condition=models.Q(salida__isnull=True) | models.Q(salida__gt=models.F("entrada")),
                name="asistencia_horas_en_orden",
            ),
        ]
        permissions = [
            ("registrar_asistencia", "Puede marcar asistencia"),
            ("corregir_asistencia", "Puede corregir asistencia"),
            ("ver_reportes_area", "Puede ver reportes de su área"),
            ("ver_reportes_globales", "Puede ver reportes globales"),
        ]

    @property
    def horas(self):
        return round((self.salida - self.entrada).total_seconds() / 3600, 2) if self.salida else None


class Permiso(models.Model):
    class Tipo(models.TextChoices):
        PERSONAL = "personal", "Personal"
        MEDICO = "medico", "Médico"
        DUELO = "duelo", "Duelo"
        MATERNIDAD = "maternidad", "Maternidad o paternidad"
        VACACIONES = "vacaciones", "Vacaciones"
        OTRO = "otro", "Otro"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name="permisos")
    tipo = models.CharField(max_length=12, choices=Tipo)
    inicio = models.DateField()
    fin = models.DateField()
    motivo = models.TextField(max_length=1200)
    adjunto = models.CharField("descripción del adjunto", max_length=300, blank=True)
    estado = models.CharField(max_length=10, choices=Estado, default=Estado.PENDIENTE)
    decidido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    decidido_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-inicio",)
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__gte=models.F("inicio")), name="permiso_fechas_en_orden"),
        ]
        permissions = [
            ("solicitar_permiso", "Puede solicitar permisos"),
            ("aprobar_permiso", "Puede resolver permisos"),
        ]


class Correccion(models.Model):
    asistencia = models.ForeignKey(Asistencia, on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    motivo = models.CharField(max_length=16)
    justificacion = models.TextField(max_length=1200)
    entrada_anterior = models.DateTimeField()
    salida_anterior = models.DateTimeField(null=True)
    registrada_en = models.DateTimeField(auto_now_add=True)
