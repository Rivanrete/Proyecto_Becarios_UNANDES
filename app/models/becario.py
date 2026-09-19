"""Entidad Becario — HU-02 (+ tipo_beca de HU-03, + estado para HU-04).

Datos generales del becario: id, nombres, apellidos, ci,
codigo_estudiante, carrera (sigla), contacto, tipo_beca y estado.
El estado se gestiona en HU-03; aquí solo se almacena y muestra.
Sin lógica de validación ni de UI aquí.
"""
from dataclasses import dataclass
from typing import Optional


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

    def __post_init__(self) -> None:
        self.nombres = self.nombres.strip()
        self.apellidos = self.apellidos.strip()
        self.ci = self.ci.strip()
        self.codigo_estudiante = self.codigo_estudiante.strip()
        self.carrera = self.carrera.strip().upper()
        self.contacto = self.contacto.strip()
        self.tipo_beca = self.tipo_beca.strip()
        self.estado = self.estado.strip() or "En renovación"
