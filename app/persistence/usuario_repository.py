from pathlib import Path
from typing import Optional

from app.models.usuario import Usuario
from app.persistence.database import DB_PATH, get_connection


def contar_usuarios(db_path: Path = DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()
        return int(row["n"])
    finally:
        conn.close()


def obtener_credencial_unica(db_path: Path = DB_PATH) -> Optional[Usuario]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, nombre_usuario, contrasena_hash FROM usuarios ORDER BY id LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return Usuario(id=row["id"], nombre_usuario=row["nombre_usuario"], contrasena_hash=row["contrasena_hash"])


def crear_usuario(nombre_usuario: str, contrasena_hash: str, db_path: Path = DB_PATH) -> Usuario:
    if contar_usuarios(db_path) > 0:
        raise RuntimeError("Ya existe la credencial única: no se permite crear otro usuario.")
    clave = nombre_usuario.strip()
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
