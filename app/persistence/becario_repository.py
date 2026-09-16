"""Acceso a datos para la entidad Becario (SQLite) — HU-02.

Mismo patrón que usuario_repository.py: funciones planas, get_connection
y cierre con try/finally. Sin reglas de negocio (viven en becario_service).
"""
from pathlib import Path
from typing import Optional

from app.models.becario import Becario
from app.persistence.database import DB_PATH, get_connection

_COLUMNAS = "id, nombres, apellidos, ci, codigo_estudiante, carrera, contacto, tipo_beca"


def _mapear(fila) -> Becario:
    return Becario(
        id=fila["id"],
        nombres=fila["nombres"],
        apellidos=fila["apellidos"],
        ci=fila["ci"],
        codigo_estudiante=fila["codigo_estudiante"],
        carrera=fila["carrera"],
        contacto=fila["contacto"],
        tipo_beca=fila["tipo_beca"],
    )


def insertar_becario(becario: Becario, db_path: Path = DB_PATH) -> Becario:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO becario (nombres, apellidos, ci, codigo_estudiante, carrera, contacto, tipo_beca)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (becario.nombres, becario.apellidos, becario.ci,
             becario.codigo_estudiante, becario.carrera, becario.contacto,
             becario.tipo_beca),
        )
        conn.commit()
        becario.id = cur.lastrowid
        return becario
    finally:
        conn.close()


def actualizar_becario(becario: Becario, db_path: Path = DB_PATH) -> Becario:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE becario SET nombres = ?, apellidos = ?, ci = ?,"
            " codigo_estudiante = ?, carrera = ?, contacto = ?, tipo_beca = ? WHERE id = ?",
            (becario.nombres, becario.apellidos, becario.ci,
             becario.codigo_estudiante, becario.carrera, becario.contacto,
             becario.tipo_beca, becario.id),
        )
        conn.commit()
        return becario
    finally:
        conn.close()


def buscar_por_id(becario_id: int, db_path: Path = DB_PATH) -> Optional[Becario]:
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            f"SELECT {_COLUMNAS} FROM becario WHERE id = ?", (becario_id,)
        ).fetchone()
    finally:
        conn.close()
    return _mapear(fila) if fila is not None else None


def existe_ci(ci: str, excluir_id: Optional[int] = None, db_path: Path = DB_PATH) -> bool:
    """True si el CI pertenece a un becario distinto de excluir_id."""
    conn = get_connection(db_path)
    try:
        if excluir_id is None:
            fila = conn.execute(
                "SELECT id FROM becario WHERE ci = ?", (ci.strip(),)
            ).fetchone()
        else:
            fila = conn.execute(
                "SELECT id FROM becario WHERE ci = ? AND id != ?", (ci.strip(), excluir_id)
            ).fetchone()
    finally:
        conn.close()
    return fila is not None


def existe_codigo(codigo: str, excluir_id: Optional[int] = None, db_path: Path = DB_PATH) -> bool:
    """True si el código pertenece a un becario distinto de excluir_id."""
    conn = get_connection(db_path)
    try:
        if excluir_id is None:
            fila = conn.execute(
                "SELECT id FROM becario WHERE codigo_estudiante = ?", (codigo.strip(),)
            ).fetchone()
        else:
            fila = conn.execute(
                "SELECT id FROM becario WHERE codigo_estudiante = ? AND id != ?",
                (codigo.strip(), excluir_id),
            ).fetchone()
    finally:
        conn.close()
    return fila is not None


def contar_becarios(db_path: Path = DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        fila = conn.execute("SELECT COUNT(*) AS n FROM becario").fetchone()
        return int(fila["n"])
    finally:
        conn.close()


def listar_todos(db_path: Path = DB_PATH) -> list[Becario]:
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            f"SELECT {_COLUMNAS} FROM becario ORDER BY apellidos, nombres"
        ).fetchall()
    finally:
        conn.close()
    return [_mapear(f) for f in filas]
