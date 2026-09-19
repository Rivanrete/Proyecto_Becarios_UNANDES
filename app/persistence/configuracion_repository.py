"""Parámetros simples del sistema (SQLite) — clave/valor.

Patrón plano como los demás repositorios. Hoy guarda la gestión
académica activa; sirve para futuros parámetros sin nuevas tablas.
"""
from pathlib import Path
from typing import Optional

from app.persistence.database import DB_PATH, get_connection


def obtener(clave: str, db_path: Path = DB_PATH) -> Optional[str]:
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            "SELECT valor FROM configuracion WHERE clave = ?", (clave.strip(),)
        ).fetchone()
    finally:
        conn.close()
    return fila["valor"] if fila is not None else None


def guardar(clave: str, valor: str, db_path: Path = DB_PATH):
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO configuracion (clave, valor) VALUES (?, ?)"
            " ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave.strip(), valor),
        )
        conn.commit()
    finally:
        conn.close()
