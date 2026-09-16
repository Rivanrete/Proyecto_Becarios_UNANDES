"""Acceso a datos del catálogo de tipos de beca (SQLite).

Patrón plano como becario_repository.py. listar_activos() alimenta el
combobox; crear/editar/desactivar quedan listos para la HU de gestión
de catálogos (sin UI todavía).
"""
from pathlib import Path
from typing import Optional

from app.models.tipo_beca import TipoBeca
from app.persistence.database import DB_PATH, get_connection

_COLUMNAS = "id, nombre, activo"


def _mapear(fila) -> TipoBeca:
    return TipoBeca(
        id=fila["id"],
        nombre=fila["nombre"],
        activo=bool(fila["activo"]),
    )


def listar_activos(db_path: Path = DB_PATH) -> list[TipoBeca]:
    """Tipos disponibles para los combos, ordenados por nombre."""
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            f"SELECT {_COLUMNAS} FROM tipos_beca WHERE activo = 1 ORDER BY nombre"
        ).fetchall()
    finally:
        conn.close()
    return [_mapear(f) for f in filas]


def listar_todos(db_path: Path = DB_PATH) -> list[TipoBeca]:
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            f"SELECT {_COLUMNAS} FROM tipos_beca ORDER BY nombre"
        ).fetchall()
    finally:
        conn.close()
    return [_mapear(f) for f in filas]


def obtener_por_nombre(nombre: str, db_path: Path = DB_PATH) -> Optional[TipoBeca]:
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            f"SELECT {_COLUMNAS} FROM tipos_beca WHERE nombre = ?", (nombre.strip(),)
        ).fetchone()
    finally:
        conn.close()
    return _mapear(fila) if fila is not None else None


def crear(nombre: str, db_path: Path = DB_PATH) -> TipoBeca:
    tipo = TipoBeca(id=None, nombre=nombre, activo=True)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO tipos_beca (nombre, activo) VALUES (?, 1)", (tipo.nombre,)
        )
        conn.commit()
        tipo.id = cur.lastrowid
        return tipo
    finally:
        conn.close()


def editar(tipo_id: int, nombre: str, db_path: Path = DB_PATH):
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE tipos_beca SET nombre = ? WHERE id = ?", (nombre.strip(), tipo_id)
        )
        conn.commit()
    finally:
        conn.close()


def desactivar(tipo_id: int, db_path: Path = DB_PATH):
    """Oculta del combo sin borrar (conserva el historial de becarios)."""
    conn = get_connection(db_path)
    try:
        conn.execute("UPDATE tipos_beca SET activo = 0 WHERE id = ?", (tipo_id,))
        conn.commit()
    finally:
        conn.close()


def activar(tipo_id: int, db_path: Path = DB_PATH):
    conn = get_connection(db_path)
    try:
        conn.execute("UPDATE tipos_beca SET activo = 1 WHERE id = ?", (tipo_id,))
        conn.commit()
    finally:
        conn.close()


def contar(db_path: Path = DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        fila = conn.execute("SELECT COUNT(*) AS n FROM tipos_beca").fetchone()
        return int(fila["n"])
    finally:
        conn.close()
