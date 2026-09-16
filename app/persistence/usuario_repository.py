"""Acceso a datos — SISTEMA DE CREDENCIAL ÚNICA (no multiusuario).

El sistema solo tiene UN encargado (Responsable de Bienestar Estudiantil).
La tabla `usuarios` se conserva por simplicidad de esquema, pero la lógica
garantiza que solo exista UN registro:

- La única lectura real es obtener_credencial_unica().
- crear_usuario() SOLO existe para el seed inicial y rechaza un 2.º registro.
- NO hay alta/listado/gestión de usuarios: no existe ese caso de uso en las HU.
"""
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
    """Retorna el único registro de credencial, o None si la tabla está vacía."""
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
    """NO USAR en UI ni en HU. Solo seed inicial.

    Rechaza la creación si ya existe un registro (sistema de credencial única).
    """
    if contar_usuarios(db_path) > 0:
        raise RuntimeError("Ya existe la credencial única: no se permite crear otro usuario.")
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
