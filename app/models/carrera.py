from dataclasses import dataclass
from typing import Optional


@dataclass
class Carrera:
    id: Optional[int]
    sigla: str
    nombre_completo: str
    activo: bool = True

    def __post_init__(self) -> None:
        self.sigla = self.sigla.strip().upper()
        self.nombre_completo = self.nombre_completo.strip()
