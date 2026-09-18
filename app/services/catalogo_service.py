"""Seed y migración de catálogos (carreras y tipos de beca).

NOTA: las listas vigentes son la mejor interpretación cruzando el Excel
real con el sitio oficial, aún NO reconfirmadas por la encargada.
Revisar antes de la entrega final.

Asegurar siembra tablas vacías; migrar_catalogos_v2 reemplaza una sola
vez los catálogos viejos (detección por marcadores viejos).
"""
from pathlib import Path

from app.persistence import carrera_repository, tipo_beca_repository
from app.persistence.database import DB_PATH

CARRERAS_INICIALES = [
    ("SIS", "Ingeniería de Sistemas"),
    ("DER", "Derecho"),
    ("ADM", "Administración de Empresas"),
    ("ICO", "Ingeniería Comercial"),
    ("CIN", "Comercio Internacional"),
    ("CPU", "Contaduría Pública"),
    ("MKT", "Marketing"),
    ("LGYH", "Gastronomía y Hotelería"),
    ("IMA", "Ingeniería en Mecánica Automotriz"),
    ("PC-IMA", "Ingeniería en Mecánica Automotriz (Programa Complementario)"),
    ("DTEX", "Diseño Textil y Moda"),
    ("IAU", "Ingeniería Autotrónica"),
    ("CSOP", "Ciencias de la Salud - Optometría"),
    ("CSM", "Ciencias de la Salud - Medicina"),
    ("CSI", "Ciencias de la Salud - Imagenología"),
    ("EIP", "Educación Parvularia"),
    ("ODO", "Odontología"),
]

TIPOS_BECA_INICIALES = [
    "Excelencia Académica",
    "Económica Social",
    "Convenio Interinstitucional",
    "Honorífica Directorio",
    "Personal Administrativo",
    "Social - Ministerio de Educación",
    "Plan Beca MKT",
]

# Marcadores de los catálogos viejos (si aparecen, hay que migrar una vez).
_MARCADORES_VIEJOS_CARRERAS = {"GAS", "CON"}
_MARCADORES_VIEJOS_TIPOS = {"Excelencia", "Convenio", "Directorio",
                            "Plantel Administrativo", "Ministerial"}


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


def migrar_catalogos_v2(db_path: Path = DB_PATH) -> tuple[int, int]:
    """Reemplaza una sola vez los catálogos viejos por los vigentes.

    Solo actúa si detecta marcadores viejos; si ya están los nuevos,
    retorna (0, 0). No toca becarios (eso lo hace otro paso).
    """
    from app.persistence.database import get_connection

    conn = get_connection(db_path)
    try:
        siglas = {r[0] for r in conn.execute("SELECT sigla FROM carreras")}
        tipos = {r[0] for r in conn.execute("SELECT nombre FROM tipos_beca")}
    finally:
        conn.close()
    hechas_carreras = hechas_tipos = 0
    if siglas & _MARCADORES_VIEJOS_CARRERAS:
        conn = get_connection(db_path)
        try:
            conn.execute("DELETE FROM carreras")
            conn.commit()
        finally:
            conn.close()
        for sigla, nombre in CARRERAS_INICIALES:
            carrera_repository.crear(sigla, nombre, db_path)
            hechas_carreras += 1
    if tipos & _MARCADORES_VIEJOS_TIPOS:
        conn = get_connection(db_path)
        try:
            conn.execute("DELETE FROM tipos_beca")
            conn.commit()
        finally:
            conn.close()
        for nombre in TIPOS_BECA_INICIALES:
            tipo_beca_repository.crear(nombre, db_path)
            hechas_tipos += 1
    return hechas_carreras, hechas_tipos
