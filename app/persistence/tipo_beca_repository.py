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
    """Tipos disponibles para los combos, en el orden oficial del catálogo."""
    asegurar_columna_orden(db_path)
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            f"SELECT {_COLUMNAS} FROM tipos_beca WHERE activo = 1 ORDER BY orden, id"
        ).fetchall()
    finally:
        conn.close()
    return [_mapear(f) for f in filas]


def listar_todos(db_path: Path = DB_PATH) -> list[TipoBeca]:
    asegurar_columna_orden(db_path)
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            f"SELECT {_COLUMNAS} FROM tipos_beca ORDER BY orden, id"
        ).fetchall()
    finally:
        conn.close()
    return [_mapear(f) for f in filas]


def asegurar_columna_orden(db_path: Path = DB_PATH):
    """Agrega tipos_beca.orden si falta (idempotente, conserva datos)."""
    conn = get_connection(db_path)
    try:
        columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(tipos_beca)")}
        if "orden" not in columnas:
            conn.execute("ALTER TABLE tipos_beca ADD COLUMN orden INTEGER NOT NULL DEFAULT 0")
            conn.commit()
    finally:
        conn.close()


def reparar_orden(db_path: Path = DB_PATH, orden_oficial: list[str] | None = None):
    """Fija tipos_beca.orden según la lista oficial (idempotente)."""
    if not orden_oficial:
        return
    conn = get_connection(db_path)
    try:
        columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(tipos_beca)")}
        if "orden" not in columnas:
            return
        for posicion, nombre in enumerate(orden_oficial):
            conn.execute("UPDATE tipos_beca SET orden = ? WHERE nombre = ?",
                         (posicion, nombre))
        conn.commit()
    finally:
        conn.close()


def obtener_por_nombre(nombre: str, db_path: Path = DB_PATH) -> Optional[TipoBeca]:
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            f"SELECT {_COLUMNAS} FROM tipos_beca WHERE nombre = ?", (nombre.strip(),)
        ).fetchone()
    finally:
        conn.close()
    return _mapear(fila) if fila is not None else None


def crear(nombre: str, db_path: Path = DB_PATH, orden: int | None = None) -> TipoBeca:
    tipo = TipoBeca(id=None, nombre=nombre, activo=True)
    asegurar_columna_orden(db_path)
    conn = get_connection(db_path)
    try:
        if orden is None:
            fila = conn.execute("SELECT COALESCE(MAX(orden), -1) AS m FROM tipos_beca").fetchone()
            orden = int(fila["m"]) + 1
        cur = conn.execute(
            "INSERT INTO tipos_beca (nombre, activo, orden) VALUES (?, 1, ?)",
            (tipo.nombre, orden),
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
