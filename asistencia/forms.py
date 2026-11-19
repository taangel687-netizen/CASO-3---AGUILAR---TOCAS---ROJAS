from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Asistencia, Permiso
from .servicios import validar_permiso


class MarcacionForm(forms.Form):
    tipo = forms.ChoiceField(choices=(("entrada", "Entrada"), ("salida", "Salida")))


class PermisoForm(forms.ModelForm):
    class Meta:
        model = Permiso
        fields = ("tipo", "inicio", "fin", "motivo", "adjunto")
        widgets = {
            "inicio": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "fin": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "motivo": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, empleado, **kwargs):
        super().__init__(*args, **kwargs)
        self.empleado = empleado

    def clean_motivo(self):
        motivo = strip_tags(self.cleaned_data["motivo"]).strip()
        if len(motivo) < 30:
            raise ValidationError("Detalla el motivo con al menos 30 caracteres.")
        return motivo

    def clean_adjunto(self):
        return strip_tags(self.cleaned_data["adjunto"]).strip()

    def clean(self):
        datos = super().clean()
        if all(campo in datos for campo in ("tipo", "inicio", "fin")):
            validar_permiso(self.empleado, datos["tipo"], datos["inicio"], datos["fin"])
        return datos


class ResolverForm(forms.Form):
    estado = forms.ChoiceField(choices=(
        (Permiso.Estado.APROBADO, "Aprobar"), (Permiso.Estado.RECHAZADO, "Rechazar"),
    ))


class CorreccionForm(forms.ModelForm):
    motivo = forms.ChoiceField(choices=(
        ("sistema", "Error de sistema"), ("olvido", "Olvido"), ("otro", "Otro"),
    ))
    justificacion = forms.CharField(label="Justificación", max_length=1200, widget=forms.Textarea)

    class Meta:
        model = Asistencia
        fields = ("entrada", "salida")
        widgets = {
            "entrada": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "salida": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
        }

    def clean_justificacion(self):
        texto = strip_tags(self.cleaned_data["justificacion"]).strip()
        if len(texto) < 50:
            raise ValidationError("Justifica el cambio con al menos 50 caracteres.")
        return texto

    def clean(self):
        datos = super().clean()
        entrada, salida = datos.get("entrada"), datos.get("salida")
        if entrada and timezone.localdate(entrada) != self.instance.fecha:
            self.add_error("entrada", "La entrada debe conservar la fecha del registro.")
        if salida and entrada and salida <= entrada:
            self.add_error("salida", "La salida debe ser posterior a la entrada.")
        return datos
