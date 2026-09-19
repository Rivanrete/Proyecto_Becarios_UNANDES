"""Un becario tal como estaba al cerrarse una gestión (solo lectura)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RespaldoBecario:
    id: Optional[int]
    gestion_respaldada: str
    becario_id: int
    nombres: str
    apellidos: str
    ci: str
    codigo_estudiante: str
    carrera: str
    contacto: str = ""
    tipo_beca: str = ""
    estado: str = ""
    porcentaje_anterior: str = "0%"
    porcentaje_gestion: str = "0%"
    horas_becarias: bool = False
    materias_en_orden: bool = False
    carpeta_cancelada: bool = False
    carta_renovacion: bool = False
    gestion_ingreso: str = ""
    creado_en: str = ""
