from dataclasses import dataclass
from typing import Optional


@dataclass
class SeguimientoBecario:
    id: Optional[int]
    becario_id: int
    gestion: str
    porcentaje_anterior: str = "0%"
    porcentaje_gestion: str = "0%"
    condicion: str = "Nueva"
    horas_becarias: bool = False
    materias_en_orden: bool = False
    carpeta_cancelada: bool = False
    carta_renovacion: bool = False
