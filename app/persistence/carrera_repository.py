from pathlib import Path
from typing import Optional

from app.models.carrera import Carrera
from app.persistence.database import DB_PATH, get_connection

_COLUMNAS = "id, sigla, nombre_completo, activo"


def _mapear(fila) -> Carrera:
    return Carrera(
        id=fila["id"],
        sigla=fila["sigla"],
        nombre_completo=fila["nombre_completo"],
        activo=bool(fila["activo"]),
    )


def listar_activos(db_path: Path = DB_PATH) -> list[Carrera]:
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            f"SELECT {_COLUMNAS} FROM carreras WHERE activo = 1 ORDER BY nombre_completo"
        ).fetchall()
    finally:
        conn.close()
    return [_mapear(f) for f in filas]


def listar_todos(db_path: Path = DB_PATH) -> list[Carrera]:
    conn = get_connection(db_path)
    try:
        filas = conn.execute(
            f"SELECT {_COLUMNAS} FROM carreras ORDER BY nombre_completo"
        ).fetchall()
    finally:
        conn.close()
    return [_mapear(f) for f in filas]


def obtener_por_sigla(sigla: str, db_path: Path = DB_PATH) -> Optional[Carrera]:
    conn = get_connection(db_path)
    try:
        fila = conn.execute(
            f"SELECT {_COLUMNAS} FROM carreras WHERE sigla = ?", (sigla.strip().upper(),)
        ).fetchone()
    finally:
        conn.close()
    return _mapear(fila) if fila is not None else None


def crear(sigla: str, nombre_completo: str, db_path: Path = DB_PATH) -> Carrera:
    carrera = Carrera(id=None, sigla=sigla, nombre_completo=nombre_completo, activo=True)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO carreras (sigla, nombre_completo, activo) VALUES (?, ?, 1)",
            (carrera.sigla, carrera.nombre_completo),
        )
        conn.commit()
        carrera.id = cur.lastrowid
        return carrera
    finally:
        conn.close()


def editar(carrera_id: int, nombre_completo: str, db_path: Path = DB_PATH):
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE carreras SET nombre_completo = ? WHERE id = ?",
            (nombre_completo.strip(), carrera_id),
        )
        conn.commit()
    finally:
        conn.close()


def desactivar(carrera_id: int, db_path: Path = DB_PATH):
    conn = get_connection(db_path)
    try:
        conn.execute("UPDATE carreras SET activo = 0 WHERE id = ?", (carrera_id,))
        conn.commit()
    finally:
        conn.close()


def activar(carrera_id: int, db_path: Path = DB_PATH):
    conn = get_connection(db_path)
    try:
        conn.execute("UPDATE carreras SET activo = 1 WHERE id = ?", (carrera_id,))
        conn.commit()
    finally:
        conn.close()


def contar(db_path: Path = DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        fila = conn.execute("SELECT COUNT(*) AS n FROM carreras").fetchone()
        return int(fila["n"])
    finally:
        conn.close()
