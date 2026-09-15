"""Lógica de negocio de autenticación — HU-01 / CU-01.

- validar_credenciales(usuario, contraseña): única puerta de validación.
  La UI nunca debe validar por su cuenta, solo llama a esta función
  y muestra el resultado.
- Sesión activa como variable de estado en memoria (sin tokens ni expiración).
"""
import hashlib
import hmac
import secrets
from pathlib import Path
from typing import Optional

from app.models.usuario import Usuario
from app.persistence import usuario_repository
from app.persistence.database import DB_PATH

_ITERACIONES = 200_000


class SesionActual:
    """Estado de sesión en memoria. Un solo usuario (perfil único)."""

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
    """Genera 'salt$hash' con PBKDF2-HMAC-SHA256 (stdlib, sin dependencias)."""
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
    """Valida credenciales.

    Retorna el Usuario si son correctas (e inicia SesionActual),
    o None si son incorrectas / vacías / usuario inexistente.
    """
    usuario = (nombre_usuario or "").strip()
    clave = contrasena or ""
    if not usuario or not clave:
        return None
    encontrado = usuario_repository.buscar_por_nombre_usuario(usuario, db_path)
    if encontrado is None:
        return None
    if not verificar_contrasena(clave, encontrado.contrasena_hash):
        return None
    SesionActual.iniciar(encontrado)
    return encontrado


def asegurar_usuario_inicial(
    nombre_usuario: str = "bienestar",
    contrasena_plana: str = "Bienestar123",
    db_path: Path = DB_PATH,
) -> Usuario:
    """Crea el usuario inicial si no existe. PROVISIONAL (la HU no define seed).

    Pregunta abierta para la Responsable: ¿qué usuario/clave inicial usar?
    Por ahora se usa bienestar / Bienestar123 solo para desarrollo local.
    """
    existente = usuario_repository.buscar_por_nombre_usuario(nombre_usuario, db_path)
    if existente is not None:
        return existente
    return usuario_repository.crear_usuario(
        nombre_usuario, generar_hash_contrasena(contrasena_plana), db_path
    )
