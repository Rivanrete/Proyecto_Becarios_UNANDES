"""Entidad Carrera — catálogo (sigla única + nombre + activo).

Si activo es False, no aparece en los combos pero se conserva el
historial de becarios que la usan.
"""
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
