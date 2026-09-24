import hashlib
import hmac
import secrets
from pathlib import Path
from typing import Optional

from app.models.usuario import Usuario
from app.persistence import usuario_repository
from app.persistence.database import DB_PATH

_ITERACIONES = 200_000

USUARIO_SEMILLA = "BienestarEstudiantil"

_HASH_SEMILLA = "unandes-bienestar-01$b0e2ce04c09a615e0bc30c8598920615448166095b5be7f71557b75612ff5118"


class SesionActual:

    usuario: Optional[Usuario] = None

    @classmethod
    def iniciar(cls, usuario: Usuario) -> None:
        cls.usuario = usuario

    @classmethod
    def cerrar(cls) -> None:
        cls.usuario = None

    @classmethod
    def activa(cls) -> bool:
        return cls.usuario is not None


def generar_hash_contrasena(contrasena_plana: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", contrasena_plana.encode("utf-8"), salt.encode("utf-8"), _ITERACIONES)
    return f"{salt}${dk.hex()}"


def verificar_contrasena(contrasena_plana: str, contrasena_hash: str) -> bool:
    try:
        salt, esperado = contrasena_hash.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", contrasena_plana.encode("utf-8"), salt.encode("utf-8"), _ITERACIONES)
    return hmac.compare_digest(dk.hex(), esperado)


def validar_credenciales(nombre_usuario: str, contrasena: str, db_path: Path = DB_PATH) -> Optional[Usuario]:
    usuario = (nombre_usuario or "").strip().lower()
    clave = contrasena or ""
    if not usuario or not clave:
        return None
    cred = usuario_repository.obtener_credencial_unica(db_path)
    if cred is None:
        return None
    if usuario != (cred.nombre_usuario or "").strip().lower():
        return None
    if not verificar_contrasena(clave, cred.contrasena_hash):
        return None
    SesionActual.iniciar(cred)
    return cred


def asegurar_credencial_unica(
    nombre_usuario: str = USUARIO_SEMILLA,
    contrasena_hash: str = _HASH_SEMILLA,
    db_path: Path = DB_PATH,
) -> Usuario:
    existente = usuario_repository.obtener_credencial_unica(db_path)
    if existente is not None:
        return existente
    return usuario_repository.crear_usuario(
        nombre_usuario, contrasena_hash, db_path
    )


def asegurar_usuario_inicial(
    nombre_usuario: str = USUARIO_SEMILLA,
    contrasena_hash: str = _HASH_SEMILLA,
    db_path: Path = DB_PATH,
) -> Usuario:
    return asegurar_credencial_unica(nombre_usuario, contrasena_hash, db_path)
