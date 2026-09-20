"""Acceso a datos para la entidad Becario (SQLite) — HU-02.

Mismo patrón que usuario_repository.py: funciones planas, get_connection
y cierre con try/finally. Sin reglas de negocio (viven en becario_service).
"""
from pathlib import Path
from typing import Optional

from app.models.becario import Becario
from app.persistence.database import DB_PATH, get_connection

_COLUMNAS = "id, nombres, apellidos, ci, codigo_estudiante, carrera, contacto, tipo_beca, estado, gestion_ingreso"


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
        estado=fila["estado"],
        gestion_ingreso=fila["gestion_ingreso"] if "gestion_ingreso" in fila.keys() else "",
    )


def insertar_becario(becario: Becario, db_path: Path = DB_PATH) -> Becario:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO becario (nombres, apellidos, ci, codigo_estudiante, carrera, contacto, tipo_beca, estado, gestion_ingreso)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (becario.nombres, becario.apellidos, becario.ci,
             becario.codigo_estudiante, becario.carrera, becario.contacto,
             becario.tipo_beca, becario.estado, becario.gestion_ingreso),
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
            " codigo_estudiante = ?, carrera = ?, contacto = ?, tipo_beca = ?, estado = ?, gestion_ingreso = ? WHERE id = ?",
            (becario.nombres, becario.apellidos, becario.ci,
             becario.codigo_estudiante, becario.carrera, becario.contacto,
             becario.tipo_beca, becario.estado, becario.gestion_ingreso, becario.id),
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


def buscar_por_codigo(codigo: str, db_path: Path = DB_PATH) -> Optional[Becario]:
    """Busca por código de estudiante exacto (sin normalizar caso)."""
    clave = (codigo or "").strip()
    if not clave:
        return None
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            f"SELECT {_COLUMNAS} FROM becario WHERE codigo_estudiante = ?", (clave,)
        ).fetchone()
    finally:
        conn.close()
    return _mapear(fila) if fila is not None else None


def buscar_por_ci(ci: str, db_path: Path = DB_PATH) -> Optional[Becario]:
    """Busca por CI exacto."""
    clave = (ci or "").strip()
    if not clave:
        return None
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            f"SELECT {_COLUMNAS} FROM becario WHERE ci = ?", (clave,)
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


def contar_por_tipo_beca(db_path: Path = DB_PATH) -> dict[str, int]:
    """Cantidad de becarios por tipo_beca tal cual está guardado."""
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            "SELECT tipo_beca AS tipo, COUNT(*) AS n FROM becario GROUP BY tipo_beca"
        ).fetchall()
    finally:
        conn.close()
    return {fila["tipo"]: int(fila["n"]) for fila in filas}


def listar_ids_sin_tipo(db_path: Path = DB_PATH) -> list[int]:
    """Ids con tipo vacío (pre-HU-03), en orden de creación para reparto."""
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            "SELECT id FROM becario WHERE tipo_beca IS NULL OR TRIM(tipo_beca) = '' ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return [int(f["id"]) for f in filas]


def asignar_tipo_beca(becario_id: int, tipo: str, db_path: Path = DB_PATH):
    """Fija el tipo de un becario (backfill o futura HU-03 de reclasificar)."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE becario SET tipo_beca = ? WHERE id = ?", (tipo.strip(), becario_id)
        )
        conn.commit()
    finally:
        conn.close()


def actualizar_estado(becario_id: int, estado: str, db_path: Path = DB_PATH):
    """Fija el estado de un becario (HU-03). La validación vive en el servicio."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE becario SET estado = ? WHERE id = ?", (estado.strip(), becario_id)
        )
        conn.commit()
    finally:
        conn.close()


def eliminar(becario_id: int, db_path: Path = DB_PATH) -> bool:
    """Borra el becario. Los seguimientos se borran antes (ver servicio)."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute("DELETE FROM becario WHERE id = ?", (becario_id,))
        conn.commit()
        return cur.rowcount > 0
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
