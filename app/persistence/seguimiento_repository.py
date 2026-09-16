"""Acceso a datos para SeguimientoBecario (SQLite) — HU-02/HU-05/HU-08.

Incluye listar_para_panel(): JOIN entre becario y seguimiento_becario
que alimenta la tabla del Panel de Control.
"""
from pathlib import Path
from typing import Optional

from app.models.becario import Becario
from app.models.seguimiento_becario import SeguimientoBecario
from app.persistence.database import DB_PATH, get_connection


def crear_seguimiento(seg: SeguimientoBecario, db_path: Path = DB_PATH) -> SeguimientoBecario:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO seguimiento_becario (becario_id, gestion, porcentaje_anterior,"
            " porcentaje_gestion, horas_becarias, materias_en_orden,"
            " carpeta_cancelada, carta_renovacion)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (seg.becario_id, seg.gestion, seg.porcentaje_anterior, seg.porcentaje_gestion,
             int(seg.horas_becarias), int(seg.materias_en_orden),
             int(seg.carpeta_cancelada), int(seg.carta_renovacion)),
        )
        conn.commit()
        seg.id = cur.lastrowid
        return seg
    finally:
        conn.close()


def obtener_por_becario(becario_id: int, gestion: str, db_path: Path = DB_PATH) -> Optional[SeguimientoBecario]:
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            "SELECT id, becario_id, gestion, porcentaje_anterior, porcentaje_gestion,"
            " horas_becarias, materias_en_orden, carpeta_cancelada, carta_renovacion"
            " FROM seguimiento_becario WHERE becario_id = ? AND gestion = ?",
            (becario_id, gestion),
        ).fetchone()
    finally:
        conn.close()
    return _mapear(fila) if fila is not None else None


def actualizar(seg: SeguimientoBecario, db_path: Path = DB_PATH) -> SeguimientoBecario:
    """Actualiza el registro existente de (becario_id, gestion)."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE seguimiento_becario SET porcentaje_anterior = ?, porcentaje_gestion = ?,"
            " horas_becarias = ?, materias_en_orden = ?, carpeta_cancelada = ?,"
            " carta_renovacion = ? WHERE becario_id = ? AND gestion = ?",
            (seg.porcentaje_anterior, seg.porcentaje_gestion, int(seg.horas_becarias),
             int(seg.materias_en_orden), int(seg.carpeta_cancelada),
             int(seg.carta_renovacion), seg.becario_id, seg.gestion),
        )
        conn.commit()
        return seg
    finally:
        conn.close()


def obtener_ultima_gestion(db_path: Path = DB_PATH) -> Optional[str]:
    """Retorna la gestión más reciente con seguimientos, o None si no hay."""
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            "SELECT gestion FROM seguimiento_becario ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    return fila["gestion"] if fila is not None else None


def _mapear(fila) -> SeguimientoBecario:
    return SeguimientoBecario(
        id=fila["id"],
        becario_id=fila["becario_id"],
        gestion=fila["gestion"],
        porcentaje_anterior=fila["porcentaje_anterior"],
        porcentaje_gestion=fila["porcentaje_gestion"],
        horas_becarias=bool(fila["horas_becarias"]),
        materias_en_orden=bool(fila["materias_en_orden"]),
        carpeta_cancelada=bool(fila["carpeta_cancelada"]),
        carta_renovacion=bool(fila["carta_renovacion"]),
    )


def listar_para_panel(db_path: Path = DB_PATH) -> list[tuple[Becario, Optional[SeguimientoBecario]]]:
    """JOIN becario + su seguimiento más reciente (uno por becario).

    Retorna (Becario, SeguimientoBecario o None si aún no tiene).
    """
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            "SELECT b.id AS bid, b.nombres, b.apellidos, b.ci, b.codigo_estudiante,"
            " b.carrera, b.contacto, b.tipo_beca, b.estado,"
            " s.id AS sid, s.becario_id, s.gestion, s.porcentaje_anterior,"
            " s.porcentaje_gestion, s.horas_becarias, s.materias_en_orden,"
            " s.carpeta_cancelada, s.carta_renovacion"
            " FROM becario b LEFT JOIN seguimiento_becario s ON s.id = ("
            "   SELECT id FROM seguimiento_becario WHERE becario_id = b.id"
            "   ORDER BY id DESC LIMIT 1)"
            " ORDER BY b.apellidos, b.nombres"
        ).fetchall()
    finally:
        conn.close()
    resultado = []
    for f in filas:
        becario = Becario(
            id=f["bid"], nombres=f["nombres"], apellidos=f["apellidos"], ci=f["ci"],
            codigo_estudiante=f["codigo_estudiante"], carrera=f["carrera"],
            contacto=f["contacto"], tipo_beca=f["tipo_beca"], estado=f["estado"],
        )
        seg = None
        if f["sid"] is not None:
            seg = SeguimientoBecario(
                id=f["sid"], becario_id=f["becario_id"], gestion=f["gestion"],
                porcentaje_anterior=f["porcentaje_anterior"],
                porcentaje_gestion=f["porcentaje_gestion"],
                horas_becarias=bool(f["horas_becarias"]),
                materias_en_orden=bool(f["materias_en_orden"]),
                carpeta_cancelada=bool(f["carpeta_cancelada"]),
                carta_renovacion=bool(f["carta_renovacion"]),
            )
        resultado.append((becario, seg))
    return resultado
