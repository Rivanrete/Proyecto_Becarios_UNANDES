"""Entidad Usuario — HU-01.

Solo los campos definidos en la HU: id, nombre_usuario, contraseña_hash.
Sin lógica de validación ni de UI aquí.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Usuario:
    id: Optional[int]
    nombre_usuario: str
    contrasena_hash: str

    def __post_init__(self) -> None:
        # Normalización mínima de identidad, sin reglas de negocio.
        self.nombre_usuario = self.nombre_usuario.strip().lower()
