from dataclasses import dataclass
from typing import Optional


@dataclass
class TipoBeca:
    id: Optional[int]
    nombre: str
    activo: bool = True

    def __post_init__(self) -> None:
        self.nombre = self.nombre.strip()
