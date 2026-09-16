"""Seed de catálogos (carreras y tipos de beca) — idempotente.

Inserta los valores iniciales solo si las tablas están vacías.
Después, las opciones de los combos salen de la base de datos.
"""
from pathlib import Path

from app.persistence import carrera_repository, tipo_beca_repository
from app.persistence.database import DB_PATH

CARRERAS_INICIALES = [
    ("CON", "Contaduría"),
    ("DER", "Derecho"),
    ("DTEX", "Diseño Textil y Moda"),
    ("GAS", "Gastronomía"),
    ("IAU", "Ingeniería Automotriz"),
    ("SIS", "Ingeniería de Sistemas"),
]

TIPOS_BECA_INICIALES = [
    "Excelencia",
    "Económica Social",
    "Convenio",
    "Plantel Administrativo",
    "Directorio",
    "Ministerial",
]


def asegurar_catalogos(db_path: Path = DB_PATH) -> tuple[int, int]:
    """Siembra catálogos vacíos. Retorna (carreras, tipos) insertados."""
    creadas = 0
    if carrera_repository.contar(db_path) == 0:
        for sigla, nombre in CARRERAS_INICIALES:
            carrera_repository.crear(sigla, nombre, db_path)
            creadas += 1
    creados = 0
    if tipo_beca_repository.contar(db_path) == 0:
        for nombre in TIPOS_BECA_INICIALES:
            tipo_beca_repository.crear(nombre, db_path)
            creados += 1
    return creadas, creados
