# Asistencia y permisos · Caso 3

Práctica grupal de Desarrollo de Aplicaciones Web. TecnoAndes S.A.C.. Este avance cubre el portal de acceso, las políticas por rol, la bitácora y el middleware. Los formularios, modelos y datos del dominio se integrarán en colaboración con Zair.

## Puesta en marcha

Desde PowerShell con Python 3.12 o posterior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py configurar_roles
.\.venv\Scripts\python.exe manage.py cuenta_prueba demo-empleado empleado
.\.venv\Scripts\python.exe manage.py cuenta_prueba demo-rrhh rrhh
.\.venv\Scripts\python.exe manage.py runserver
```

Cada cuenta requiere una contraseña temporal. Abre http://127.0.0.1:8000/ e ingresa con `demo-empleado@tecnoandes.pe` o `demo-rrhh@tecnoandes.pe`. El portal usa usuarios locales de Django con ese dominio. Las cuentas de prueba y SQLite están pensadas para datos ficticios.

La cookie `asistencia_sesion` usa `HttpOnly` y `SameSite=Lax` y dura **45 minutos de inactividad**. Para HTTPS, configura `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS`. Django exigirá HTTPS y marcará las cookies de sesión y CSRF como `Secure`.

Como empleado, abre `/auditoria/` para reproducir un 403. Ingresa como rrhh para ver el evento en el portal o en Django Admin.

## Permisos por rol

| Acción | RRHH | Jefe de área | Empleado | Contador |
| --- | --- | --- | --- | --- |
| Marcar asistencia y solicitar permiso | Propios | Propios | Propios | — |
| Aprobar o rechazar solicitudes | Cualquier área | Su área | — | — |
| Ver reportes de área | Cualquier área | Su área | — | — |
| Ver reportes globales | Sí | — | — | Solo lectura |
| Corregir asistencia | Sí | — | — | — |

## Integración con el dominio

- Vincula cada empleado con su usuario de Django. Antes de marcar o solicitar un permiso, llama a `registrar_asistencia(usuario, empleado.usuario_id)` o `solicitar_permiso(usuario, empleado.usuario_id)`. Para consultar datos privados aplica `ver_expediente` y limita los campos sensibles a RRHH.
- En el cambio de estado llama a `aprobar_permiso(usuario, area_del_jefe_id, area_solicitud_id)` y vuelve a comprobar que la solicitud siga pendiente dentro de la misma transacción. Obtén ambas áreas desde la base de datos. Usa `ver_reportes_area`, `ver_reportes_globales(usuario, request.method)` y `corregir_asistencia(usuario)` en las vistas correspondientes. Aplica los mismos controles en Django Admin y en las acciones masivas.
- Anota las vistas POST de marcación con `@controla_horario(validador)`. El validador comprueba el permiso y obtiene la hora programada de entrada o salida del turno. Pasa `timezone.now()` y la hora del turno a `validar_marcacion`. Se aceptan los límites exactos de dos horas.
- Configura `DJANGO_AVISOS_INGRESO=asistencia.avisos.avisos_ingreso` cuando exista esa función. Recibe `usuario, ahora` y devuelve `entrada_pendiente(entrada_programada, marco_entrada, ahora)` con el turno laborable del empleado. Para días sin turno usa `None`.
- Llama a `auditar_operacion(request, accion, tipo, objeto_id)` en cada alta o cambio de asistencia o permisos dentro de la transacción que lo guarda. Por ejemplo, `asistencia_corregida` y `permiso_aprobado`. Las cuentas desactivadas pierden la sesión vigente y el evento queda en la bitácora.
- Si se incluyen `asistencia:reportes_globales`, `asistencia:permisos_area`, `asistencia:marcar` y `asistencia:mis_permisos`, aparecen los enlaces correspondientes al rol en **Mi cuenta**.

`configurar_roles` crea los grupos del caso. Cuando se declaren y migren permisos de modelos del dominio, lista sus nombres en `PERMISOS_GRUPOS` por rol, en formato `app.modelo.codename`, y vuelve a ejecutar el comando. Los controles de propiedad y área siempre se aplican sobre los objetos del servidor.

## Pruebas

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```
