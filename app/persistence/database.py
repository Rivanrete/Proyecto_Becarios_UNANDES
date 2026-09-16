"""Persistencia local SQLite — standalone, sin red ni servidor.

La BD vive en <raiz_proyecto>/data/becarios.db
Sistema de CREDENCIAL ÚNICA: init_db crea el esquema y, si la tabla
está vacía, inserta el seed de pruebas (prueba / 1234 hasheada).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "becarios.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario TEXT UNIQUE NOT NULL,
    contrasena_hash TEXT NOT NULL
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
    # Seed de credencial única (idempotente). Import diferido para
    # evitar dependencia circular database -> auth_service.
    from app.services.auth_service import asegurar_credencial_unica

    asegurar_credencial_unica(db_path=db_path)
