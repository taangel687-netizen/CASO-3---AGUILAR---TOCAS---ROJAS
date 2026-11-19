from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class FormularioIngreso(AuthenticationForm):
    username = forms.EmailField(label="Correo", max_length=150, widget=forms.EmailInput(attrs={
        "autocomplete": "username", "autofocus": True,
    }))

    def clean(self):
        correo = self.cleaned_data.get("username", "").lower()
        password = self.cleaned_data.get("password")
        if correo and password:
            if correo.rpartition("@")[2] != settings.CASO.dominio:
                raise ValidationError(f"Usa una cuenta @{settings.CASO.dominio}.")
            self.user_cache = authenticate(self.request, username=correo, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data
