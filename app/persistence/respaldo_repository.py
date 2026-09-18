"""Snapshots de cierre de gestión (solo lectura desde la UI).

Una fila por becario con todos sus campos + la gestión que terminaba.
"""
from datetime import datetime
from pathlib import Path

from app.models.respaldo_becario import RespaldoBecario
from app.persistence.database import DB_PATH, get_connection

_COLUMNAS = ("id, gestion_respaldada, becario_id, nombres, apellidos, ci,"
             " codigo_estudiante, carrera, contacto, tipo_beca, estado,"
             " porcentaje_anterior, porcentaje_gestion, horas_becarias,"
             " materias_en_orden, carpeta_cancelada, carta_renovacion, creado_en")


def _mapear(fila) -> RespaldoBecario:
    return RespaldoBecario(
        id=fila["id"], gestion_respaldada=fila["gestion_respaldada"],
        becario_id=fila["becario_id"], nombres=fila["nombres"],
        apellidos=fila["apellidos"], ci=fila["ci"],
        codigo_estudiante=fila["codigo_estudiante"], carrera=fila["carrera"],
        contacto=fila["contacto"], tipo_beca=fila["tipo_beca"], estado=fila["estado"],
        porcentaje_anterior=fila["porcentaje_anterior"],
        porcentaje_gestion=fila["porcentaje_gestion"],
        horas_becarias=bool(fila["horas_becarias"]),
        materias_en_orden=bool(fila["materias_en_orden"]),
        carpeta_cancelada=bool(fila["carpeta_cancelada"]),
        carta_renovacion=bool(fila["carta_renovacion"]),
        creado_en=fila["creado_en"],
    )


def guardar_respaldo(gestion: str, filas: list[tuple, ...], db_path: Path = DB_PATH) -> int:
    """Guarda el snapshot. `filas`: (Becario, SeguimientoBecario|None). Idempotente por gestión."""
    if existe_gestion(gestion, db_path):
        return 0
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection(db_path)
    try:
        for becario, seg in filas:
            conn.execute(
                "INSERT INTO respaldo_becario (gestion_respaldada, becario_id, nombres,"
                " apellidos, ci, codigo_estudiante, carrera, contacto, tipo_beca, estado,"
                " porcentaje_anterior, porcentaje_gestion, horas_becarias, materias_en_orden,"
                " carpeta_cancelada, carta_renovacion, creado_en)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (gestion, becario.id, becario.nombres, becario.apellidos, becario.ci,
                 becario.codigo_estudiante, becario.carrera, becario.contacto,
                 becario.tipo_beca, becario.estado,
                 seg.porcentaje_anterior if seg else "0%",
                 seg.porcentaje_gestion if seg else "0%",
                 int(seg.horas_becarias) if seg else 0,
                 int(seg.materias_en_orden) if seg else 0,
                 int(seg.carpeta_cancelada) if seg else 0,
                 int(seg.carta_renovacion) if seg else 0,
                 ahora),
            )
        conn.commit()
    finally:
        conn.close()
    return len(filas)


def existe_gestion(gestion: str, db_path: Path = DB_PATH) -> bool:
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            "SELECT id FROM respaldo_becario WHERE gestion_respaldada = ? LIMIT 1",
            (gestion,),
        ).fetchone()
    finally:
        conn.close()
    return fila is not None


def listar_gestiones(db_path: Path = DB_PATH) -> list[str]:
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            "SELECT gestion_respaldada FROM respaldo_becario"
            " GROUP BY gestion_respaldada ORDER BY MAX(id)"
        ).fetchall()
    finally:
        conn.close()
    return [fila["gestion_respaldada"] for fila in filas]


def listar_por_gestion(gestion: str, db_path: Path = DB_PATH) -> list[RespaldoBecario]:
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            f"SELECT {_COLUMNAS} FROM respaldo_becario"
            " WHERE gestion_respaldada = ? ORDER BY apellidos, nombres",
            (gestion,),
        ).fetchall()
    finally:
        conn.close()
    return [_mapear(f) for f in filas]
