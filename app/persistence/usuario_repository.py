"""Acceso a datos para la entidad Usuario (SQLite)."""
import sqlite3
from pathlib import Path
from typing import Optional

from app.models.usuario import Usuario
from app.persistence.database import DB_PATH, get_connection


def buscar_por_nombre_usuario(nombre_usuario: str, db_path: Path = DB_PATH) -> Optional[Usuario]:
    """Retorna el Usuario con ese nombre (normalizado) o None."""
    clave = nombre_usuario.strip().lower()
    if not clave:
        return None
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, nombre_usuario, contrasena_hash FROM usuarios WHERE nombre_usuario = ?",
            (clave,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return Usuario(id=row["id"], nombre_usuario=row["nombre_usuario"], contrasena_hash=row["contrasena_hash"])


def crear_usuario(nombre_usuario: str, contrasena_hash: str, db_path: Path = DB_PATH) -> Usuario:
    """Inserta un usuario. Lanza sqlite3.IntegrityError si ya existe."""
    clave = nombre_usuario.strip().lower()
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO usuarios (nombre_usuario, contrasena_hash) VALUES (?, ?)",
            (clave, contrasena_hash),
        )
        conn.commit()
        return Usuario(id=cur.lastrowid, nombre_usuario=clave, contrasena_hash=contrasena_hash)
    finally:
        conn.close()


def contar_usuarios(db_path: Path = DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()
        return int(row["n"])
    finally:
        conn.close()
