import unicodedata
from pathlib import Path

from app.persistence import carrera_repository, tipo_beca_repository
from app.persistence.database import DB_PATH

CARRERAS_INICIALES = [
    ("SIS", "Ingeniería de Sistemas"),
    ("DER", "Derecho"),
    ("ADM", "Administración de Empresas"),
    ("ICO", "Ingeniería Comercial"),
    ("CIN", "Comercio Internacional"),
    ("CPU", "Contaduría Pública"),
    ("MKT", "Marketing"),
    ("LGYH", "Gastronomía y Hotelería"),
    ("IMA", "Ingeniería en Mecánica Automotriz"),
    ("PC-IMA", "Ingeniería en Mecánica Automotriz (Programa Complementario)"),
    ("DTEX", "Diseño Textil y Moda"),
    ("IAU", "Ingeniería Autotrónica"),
    ("CSOP", "Ciencias de la Salud - Optometría"),
    ("CSM", "Ciencias de la Salud - Medicina"),
    ("CSI", "Ciencias de la Salud - Imagenología"),
    ("EIP", "Educación Parvularia"),
    ("ODO", "Odontología"),
]

TIPOS_BECA_OFICIALES = [
    "Beca Excelencia Académica",
    "Beca Económica Social Renovación",
    "Beca Económica Social Nuevas",
    "Beca Convenio Interinstitucional Renovación",
    "Beca Convenio Interinstitucional Nuevas",
    "Beca Honorífica Directorio",
    "Beca Personal Administrativo",
    "Beca Social Ministerio de Educación Renovación",
    "Plan Beca Marketing Renovación",
    "Plan Beca Marketing Nuevas",
]

TIPOS_BECA_INICIALES = list(TIPOS_BECA_OFICIALES)

_MARCADORES_VIEJOS_CARRERAS = {"GAS", "CON"}
_MARCADORES_VIEJOS_TIPOS = {"Excelencia", "Convenio", "Directorio",
                            "Plantel Administrativo", "Ministerial"}

_TIPOS_AGRUPADOS_ANTERIORES = {
    "Excelencia Académica",
    "Económica Social",
    "Convenio Interinstitucional",
    "Honorífica Directorio",
    "Personal Administrativo",
    "Social - Ministerio de Educación",
    "Plan Beca MKT",
}


def _normalizar_tipo(valor: str) -> str:
    base = unicodedata.normalize("NFKD", valor or "")
    return "".join(c for c in base if not unicodedata.combining(c)).lower().strip()


def _destino_mas_cercano(valor_viejo: str) -> str:
    tipo = _normalizar_tipo(valor_viejo)
    if "minister" in tipo or "educacion" in tipo:
        return "Beca Social Ministerio de Educación Renovación"
    if "excelencia" in tipo:
        return "Beca Excelencia Académica"
    if "honor" in tipo or "directorio" in tipo:
        return "Beca Honorífica Directorio"
    if "personal" in tipo or "administrativo" in tipo or "plantel" in tipo:
        return "Beca Personal Administrativo"
    if "convenio" in tipo:
        return "Beca Convenio Interinstitucional Renovación"
    if "marketing" in tipo or "mkt" in tipo or "mercad" in tipo:
        return "Plan Beca Marketing Renovación"
    if "econom" in tipo or "social" in tipo:
        return "Beca Económica Social Renovación"
    return "Beca Económica Social Renovación"


def _reparto_renovacion_nuevas(valor_viejo: str, posicion: int) -> str | None:
    tipo = _normalizar_tipo(valor_viejo)
    if "economica" in tipo and "social" in tipo and "ministerio" not in tipo \
            and "educacion" not in tipo:
        base = "Beca Económica Social"
    elif "convenio" in tipo:
        base = "Beca Convenio Interinstitucional"
    elif "mkt" in tipo or "marketing" in tipo or "plan beca" in tipo:
        base = "Plan Beca Marketing"
    else:
        return None
    variante = "Renovación" if posicion % 2 == 0 else "Nuevas"
    return f"{base} {variante}"


_MAPEO_DIRECTO_OFICIAL = {
    "Excelencia Académica": "Beca Excelencia Académica",
    "Honorífica Directorio": "Beca Honorífica Directorio",
    "Personal Administrativo": "Beca Personal Administrativo",
    "Social - Ministerio de Educación":
        "Beca Social Ministerio de Educación Renovación",
}


def migrar_tipos_beca_oficiales(db_path: Path = DB_PATH) -> dict:
    from app.persistence.database import get_connection

    tipo_beca_repository.asegurar_columna_orden(db_path)
    conn = get_connection(db_path)
    try:
        tipos_actuales = [r[0] for r in
                          conn.execute("SELECT nombre FROM tipos_beca").fetchall()]
        filas_becarios = conn.execute(
            "SELECT id, tipo_beca FROM becario ORDER BY id").fetchall()
    finally:
        conn.close()

    tipos_reemplazados = 0
    if set(tipos_actuales) != set(TIPOS_BECA_OFICIALES):
        conn = get_connection(db_path)
        try:
            conn.execute("DELETE FROM tipos_beca")
            conn.commit()
        finally:
            conn.close()
        for posicion, nombre in enumerate(TIPOS_BECA_OFICIALES):
            tipo_beca_repository.crear(nombre, db_path, orden=posicion)
        tipos_reemplazados = len(TIPOS_BECA_OFICIALES)
    tipo_beca_repository.reparar_orden(db_path, TIPOS_BECA_OFICIALES)

    oficiales = set(TIPOS_BECA_OFICIALES)
    contadores_reparto: dict[str, int] = {}
    becarios_actualizados = 0
    no_reconocidos: list[tuple] = []
    for fila in filas_becarios:
        becario_id = int(fila[0])
        valor = (fila[1] or "").strip()
        if valor in oficiales:
            continue
        if not valor:
            destino = _destino_mas_cercano(valor)
            no_reconocidos.append((becario_id, valor, destino))
        elif valor in _MAPEO_DIRECTO_OFICIAL:
            destino = _MAPEO_DIRECTO_OFICIAL[valor]
        elif valor in _TIPOS_AGRUPADOS_ANTERIORES:
            posicion = contadores_reparto.get(valor, 0)
            contadores_reparto[valor] = posicion + 1
            destino = _reparto_renovacion_nuevas(valor, posicion) or \
                _destino_mas_cercano(valor)
        else:
            destino = _destino_mas_cercano(valor)
            no_reconocidos.append((becario_id, valor, destino))
        conn = get_connection(db_path)
        try:
            conn.execute("UPDATE becario SET tipo_beca = ? WHERE id = ?",
                         (destino, becario_id))
            conn.commit()
        finally:
            conn.close()
        becarios_actualizados += 1
    return {"tipos_reemplazados": tipos_reemplazados,
            "becarios_actualizados": becarios_actualizados,
            "no_reconocidos": no_reconocidos}


def asegurar_catalogos(db_path: Path = DB_PATH) -> tuple[int, int]:
    creadas = 0
    if carrera_repository.contar(db_path) == 0:
        for sigla, nombre in CARRERAS_INICIALES:
            carrera_repository.crear(sigla, nombre, db_path)
            creadas += 1
    creados = 0
    if tipo_beca_repository.contar(db_path) == 0:
        for nombre in TIPOS_BECA_INICIALES:
            tipo_beca_repository.crear(nombre, db_path)
            creados += 1
    return creadas, creados


def migrar_catalogos_v2(db_path: Path = DB_PATH) -> tuple[int, int]:
    from app.persistence.database import get_connection

    conn = get_connection(db_path)
    try:
        siglas = {r[0] for r in conn.execute("SELECT sigla FROM carreras")}
        tipos = {r[0] for r in conn.execute("SELECT nombre FROM tipos_beca")}
    finally:
        conn.close()
    hechas_carreras = hechas_tipos = 0
    if siglas & _MARCADORES_VIEJOS_CARRERAS:
        conn = get_connection(db_path)
        try:
            conn.execute("DELETE FROM carreras")
            conn.commit()
        finally:
            conn.close()
        for sigla, nombre in CARRERAS_INICIALES:
            carrera_repository.crear(sigla, nombre, db_path)
            hechas_carreras += 1
    if tipos & _MARCADORES_VIEJOS_TIPOS:
        conn = get_connection(db_path)
        try:
            conn.execute("DELETE FROM tipos_beca")
            conn.commit()
        finally:
            conn.close()
        for nombre in TIPOS_BECA_INICIALES:
            tipo_beca_repository.crear(nombre, db_path)
            hechas_tipos += 1
    return hechas_carreras, hechas_tipos
