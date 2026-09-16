"""Entidad TipoBeca — catálogo (nombre único + activo).

Si activo es False, no aparece en los combos pero se conserva el
historial de becarios que lo usan.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TipoBeca:
    id: Optional[int]
    nombre: str
    activo: bool = True

    def __post_init__(self) -> None:
        self.nombre = self.nombre.strip()
