from dataclasses import dataclass
from typing import Optional


@dataclass
class Usuario:
    id: Optional[int]
    nombre_usuario: str
    contrasena_hash: str

    def __post_init__(self) -> None:
        self.nombre_usuario = self.nombre_usuario.strip()
