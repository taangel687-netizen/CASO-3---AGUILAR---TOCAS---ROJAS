# Caso 3 · Asistencia y permisos

Práctica grupal de Desarrollo de Aplicaciones Web. Este repositorio usa el perfil TecnoAndes de la base de Django, con sesión de 45 minutos y una base SQLite propia.

## Ejecutar en PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py configurar_roles
.\.venv\Scripts\python.exe manage.py cargar_asistencia_demo
.\.venv\Scripts\python.exe manage.py changepassword demo-empleado-05@tecnoandes.pe
.\.venv\Scripts\python.exe manage.py runserver
```

El acceso local usa el correo corporativo. La carga incluye 10 empleados, 5 áreas, 50 marcaciones y 10 permisos ficticios. Habilita con `changepassword` las cuentas `demo-jefe@tecnoandes.pe`, `demo-rrhh@tecnoandes.pe` o `demo-contador@tecnoandes.pe` para comprobar sus permisos.

- **Empleado.** Marca entrada o salida, consulta su historial y solicita permisos.
- **Jefe.** Decide solicitudes y consulta reportes de su propia área.
- **RRHH.** Consulta reportes globales, corrige marcaciones con justificación y aprueba permisos desde el portal o Django Admin.
- **Contabilidad.** Consulta y exporta el reporte de asistencia como texto.

Las horas extra se calculan por jornada sobre el total trabajado por encima de ocho horas. El saldo inicial de vacaciones es de 30 días calendario. El sistema muestra la decisión en **Mis solicitudes**. Las correcciones y las decisiones quedan en auditoría.

[Manual breve para empleados](MANUAL.md)
