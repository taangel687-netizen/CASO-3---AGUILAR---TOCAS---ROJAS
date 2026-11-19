from dataclasses import dataclass


@dataclass(frozen=True)
class Caso:
    titulo: str
    institucion: str
    dominio: str
    minutos: int
    roles: dict


CASO = Caso(
    titulo="Asistencia y permisos",
    institucion="TecnoAndes S.A.C.",
    dominio="tecnoandes.pe",
    minutos=45,
    roles={
        "rrhh": "RRHH",
        "jefe": "Jefes de área",
        "empleado": "Empleados",
        "contador": "Contadores",
    },
)
