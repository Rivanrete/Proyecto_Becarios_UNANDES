"""Persistencia local SQLite — standalone, sin red ni servidor.

La BD vive en <raiz_proyecto>/data/becarios.db
Sistema de CREDENCIAL ÚNICA: init_db crea el esquema y la credencial
(prueba / 1234 hasheada). El CI es opcional y sin UNIQUE (muchos
becarios reales no tienen); el código de estudiante sigue único.
"""
import sqlite3
from pathlib import Path

from app import rutas

DB_PATH = rutas.datos_dir() / "becarios.db"

_TABLA_BECARIO = """
CREATE TABLE becario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    ci TEXT NOT NULL DEFAULT '',
    codigo_estudiante TEXT NOT NULL UNIQUE,
    carrera TEXT NOT NULL,
    contacto TEXT NOT NULL DEFAULT '',
    tipo_beca TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'En renovación',
    gestion_ingreso TEXT NOT NULL DEFAULT ''
);
"""

_COLUMNAS_BECARIO = ("id, nombres, apellidos, ci, codigo_estudiante, carrera,"
                     " contacto, tipo_beca, estado, gestion_ingreso")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario TEXT UNIQUE NOT NULL,
    contrasena_hash TEXT NOT NULL
);
""" + _TABLA_BECARIO.replace("CREATE TABLE becario (",
                             "CREATE TABLE IF NOT EXISTS becario (") + """
CREATE TABLE IF NOT EXISTS seguimiento_becario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    becario_id INTEGER NOT NULL REFERENCES becario(id),
    gestion TEXT NOT NULL,
    porcentaje_anterior TEXT NOT NULL DEFAULT '0%',
    porcentaje_gestion TEXT NOT NULL DEFAULT '0%',
    condicion TEXT NOT NULL DEFAULT '',
    horas_becarias INTEGER NOT NULL DEFAULT 0,
    materias_en_orden INTEGER NOT NULL DEFAULT 0,
    carpeta_cancelada INTEGER NOT NULL DEFAULT 0,
    carta_renovacion INTEGER NOT NULL DEFAULT 0,
    UNIQUE (becario_id, gestion)
);
CREATE TABLE IF NOT EXISTS carreras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sigla TEXT NOT NULL UNIQUE,
    nombre_completo TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS tipos_beca (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    activo INTEGER NOT NULL DEFAULT 1,
    orden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS respaldo_becario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gestion_respaldada TEXT NOT NULL,
    becario_id INTEGER NOT NULL,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    ci TEXT NOT NULL,
    codigo_estudiante TEXT NOT NULL,
    carrera TEXT NOT NULL,
    contacto TEXT NOT NULL DEFAULT '',
    tipo_beca TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'En renovación',
    porcentaje_anterior TEXT NOT NULL DEFAULT '0%',
    porcentaje_gestion TEXT NOT NULL DEFAULT '0%',
    condicion TEXT NOT NULL DEFAULT '',
    horas_becarias INTEGER NOT NULL DEFAULT 0,
    materias_en_orden INTEGER NOT NULL DEFAULT 0,
    carpeta_cancelada INTEGER NOT NULL DEFAULT 0,
    carta_renovacion INTEGER NOT NULL DEFAULT 0,
    gestion_ingreso TEXT NOT NULL DEFAULT '',
    creado_en TEXT NOT NULL DEFAULT ''
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _migrar_becario(conn) -> None:
    """Agrega columnas nuevas a BDs creadas con un esquema anterior.

    CREATE TABLE IF NOT EXISTS no toca tablas ya existentes, por eso las
    columnas que se suman después (ej. tipo_beca de HU-03) se migran aquí.
    """
    columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(becario)")}
    if "tipo_beca" not in columnas:
        conn.execute("ALTER TABLE becario ADD COLUMN tipo_beca TEXT NOT NULL DEFAULT ''")
    if "estado" not in columnas:
        conn.execute("ALTER TABLE becario ADD COLUMN estado TEXT NOT NULL DEFAULT 'En renovación'")
    if "gestion_ingreso" not in columnas:
        conn.execute("ALTER TABLE becario ADD COLUMN gestion_ingreso TEXT NOT NULL DEFAULT ''")
    _migrar_ci_no_unico(conn)


def _migrar_ci_no_unico(conn) -> None:
    """Quita el UNIQUE de ci (idempotente, conserva todos los datos).

    SQLite no permite soltar un UNIQUE con ALTER: se reconstruye la tabla
    (los reales sin CI comparten el vacío y no deben chocar entre sí).
    """
    sql = (conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'becario'").fetchone() or [None])[0] or ""
    normalizado = " ".join(sql.upper().split())
    if "CI TEXT NOT NULL UNIQUE" not in normalizado:
        return
    conn.execute("ALTER TABLE becario RENAME TO becario_anterior")
    conn.execute(_TABLA_BECARIO)
    conn.execute(f"INSERT INTO becario ({_COLUMNAS_BECARIO}) SELECT {_COLUMNAS_BECARIO}"
                 " FROM becario_anterior")
    conn.execute("DROP TABLE becario_anterior")


def _migrar_respaldo(conn) -> None:
    """Agrega gestion_ingreso a respaldos viejos (idempotente, sin perder datos)."""
    columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(respaldo_becario)")}
    if "gestion_ingreso" not in columnas:
        conn.execute("ALTER TABLE respaldo_becario ADD COLUMN gestion_ingreso TEXT NOT NULL DEFAULT ''")
    if "condicion" not in columnas:
        conn.execute("ALTER TABLE respaldo_becario ADD COLUMN condicion TEXT NOT NULL DEFAULT ''")


def _migrar_seguimiento(conn) -> None:
    """Agrega condicion a seguimientos viejos (idempotente, sin perder datos).

    Las columnas de porcentaje NO se tocan: se conservan en la BD aunque
    la UI ya no las muestre.
    """
    columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(seguimiento_becario)")}
    if "condicion" not in columnas:
        conn.execute("ALTER TABLE seguimiento_becario ADD COLUMN condicion TEXT NOT NULL DEFAULT ''")


def init_db(db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
        _migrar_becario(conn)
        _migrar_respaldo(conn)
        _migrar_seguimiento(conn)
        conn.commit()
    finally:
        conn.close()
    # Seeds idempotentes. Imports diferidos para evitar dependencias
    # circulares database -> services.
    from app.services.auth_service import asegurar_credencial_unica
    from app.services.becario_service import (
        completar_tipos_vacios,
        distribuir_estados_ejemplo,
        migrar_condicion_inicial,
    )
    from app.services.catalogo_service import (
        asegurar_catalogos,
        migrar_catalogos_v2,
        migrar_tipos_beca_oficiales,
    )

    asegurar_credencial_unica(db_path=db_path)
    asegurar_catalogos(db_path=db_path)
    migrar_catalogos_v2(db_path=db_path)
    migrar_tipos_beca_oficiales(db_path=db_path)
    completar_tipos_vacios(db_path=db_path)
    distribuir_estados_ejemplo(db_path=db_path)
    migrar_condicion_inicial(db_path=db_path)
