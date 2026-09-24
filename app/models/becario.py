from dataclasses import dataclass
from typing import Optional


def _capitalizar_persona(valor: str) -> str:
    texto = (valor or "").strip()
    if not texto:
        return ""
    return " ".join(
        parte[:1].upper() + parte[1:].lower() if parte else ""
        for parte in texto.split()
    )


@dataclass
class Becario:
    id: Optional[int]
    nombres: str
    apellidos: str
    ci: str
    codigo_estudiante: str
    carrera: str
    contacto: str = ""
    tipo_beca: str = ""
    estado: str = "En renovación"
    gestion_ingreso: str = ""

    def __post_init__(self) -> None:
        self.nombres = _capitalizar_persona(self.nombres)
        self.apellidos = _capitalizar_persona(self.apellidos)
        self.ci = self.ci.strip()
        self.codigo_estudiante = self.codigo_estudiante.strip()
        self.carrera = self.carrera.strip().upper()
        self.contacto = self.contacto.strip()
        self.tipo_beca = self.tipo_beca.strip()
        self.estado = self.estado.strip() or "En renovación"
        self.gestion_ingreso = self.gestion_ingreso.strip()
