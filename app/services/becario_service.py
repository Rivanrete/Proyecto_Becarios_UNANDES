"""Casos de uso de becarios — HU-02.

registrar_becario(datos) y editar_becario(id, datos): única puerta de
escritura. La UI nunca valida por su cuenta, solo llama aquí y muestra
el resultado. Duplicados se señalan con BecarioDuplicadoError(campo).
"""
from pathlib import Path

from app.models.becario import Becario
from app.models.seguimiento_becario import SeguimientoBecario
from app.persistence import becario_repository, seguimiento_repository
from app.persistence.database import DB_PATH

CATALOGO_CARRERAS = ["IAU", "DTEX", "DER", "GAS", "SIS", "CON"]

# Sigla -> nombre completo (el combo muestra "Nombre - SIGLA", se guarda la sigla).
CARRERAS = {
    "CON": "Contaduría",
    "DER": "Derecho",
    "DTEX": "Diseño Textil y Moda",
    "GAS": "Gastronomía",
    "IAU": "Ingeniería Automotriz",
    "SIS": "Ingeniería de Sistemas",
}

# Categorías de beca (HU-03). El combo las lista tal cual, se guarda el texto.
TIPOS_BECA = [
    "Excelencia",
    "Económica Social",
    "Convenio",
    "Plantel Administrativo",
    "Directorio",
    "Ministerial",
]

GESTION_EJEMPLO = "II-2024"

CAMPOS_REQUERIDOS = ("nombres", "apellidos", "ci", "codigo_estudiante", "carrera", "tipo_beca")


def opciones_carrera() -> list[tuple[str, str]]:
    """(sigla, 'Nombre Completo - SIGLA') ordenadas por nombre completo."""
    return sorted(
        ((sigla, f"{nombre} - {sigla}") for sigla, nombre in CARRERAS.items()),
        key=lambda par: par[1],
    )


class BecarioDuplicadoError(ValueError):
    """CI o código de estudiante ya registrado. Atributo `campo`: 'ci' o 'codigo_estudiante'."""

    def __init__(self, campo: str):
        self.campo = campo
        detalle = "El CI ya está registrado." if campo == "ci" else "El código de estudiante ya está registrado."
        super().__init__(detalle)


def _normalizar(datos: dict) -> dict:
    limpio = {k: (str(datos.get(k, "") or "").strip()) for k in
              ("nombres", "apellidos", "ci", "codigo_estudiante", "carrera",
               "contacto", "tipo_beca")}
    # Acepta sigla ("SIS") o etiqueta del combo ("Ingeniería de Sistemas - SIS").
    if " - " in limpio["carrera"]:
        limpio["carrera"] = limpio["carrera"].rsplit(" - ", 1)[1]
    limpio["carrera"] = limpio["carrera"].upper()
    return limpio


def _validar_requeridos(datos: dict):
    faltantes = [c for c in CAMPOS_REQUERIDOS if not datos[c]]
    if faltantes:
        raise ValueError(f"Faltan datos obligatorios: {', '.join(faltantes)}.")
    if datos["carrera"] not in CARRERAS:
        raise ValueError(f"Carrera no válida. Use una de: {', '.join(CARRERAS)}.")
    if datos["tipo_beca"] not in TIPOS_BECA:
        raise ValueError(f"Tipo de beca no válido. Use uno de: {', '.join(TIPOS_BECA)}.")


def registrar_becario(datos: dict, db_path: Path = DB_PATH) -> Becario:
    """Valida y registra un becario nuevo. Lanza BecarioDuplicadoError si CI o código existen.

    Crea además su SeguimientoBecario inicial con valores automáticos:
    horas en "No cumplió" y materias en "Sí" (el resto en negativo/0%).
    """
    limpio = _normalizar(datos)
    _validar_requeridos(limpio)
    if becario_repository.existe_ci(limpio["ci"], db_path=db_path):
        raise BecarioDuplicadoError("ci")
    if becario_repository.existe_codigo(limpio["codigo_estudiante"], db_path=db_path):
        raise BecarioDuplicadoError("codigo_estudiante")
    becario = becario_repository.insertar_becario(Becario(id=None, **limpio), db_path)
    gestion = seguimiento_repository.obtener_ultima_gestion(db_path) or GESTION_EJEMPLO
    seguimiento_repository.crear_seguimiento(
        SeguimientoBecario(id=None, becario_id=becario.id, gestion=gestion,
                           porcentaje_anterior="0%", porcentaje_gestion="0%",
                           horas_becarias=False, materias_en_orden=True,
                           carpeta_cancelada=False, carta_renovacion=False),
        db_path,
    )
    return becario


def editar_becario(becario_id: int, datos: dict, db_path: Path = DB_PATH) -> Becario:
    """Actualiza un becario. El CI/código propio no cuenta como duplicado."""
    actual = becario_repository.buscar_por_id(becario_id, db_path)
    if actual is None:
        raise ValueError("El becario no existe.")
    limpio = _normalizar(datos)
    _validar_requeridos(limpio)
    if becario_repository.existe_ci(limpio["ci"], excluir_id=becario_id, db_path=db_path):
        raise BecarioDuplicadoError("ci")
    if becario_repository.existe_codigo(limpio["codigo_estudiante"], excluir_id=becario_id, db_path=db_path):
        raise BecarioDuplicadoError("codigo_estudiante")
    return becario_repository.actualizar_becario(Becario(id=becario_id, **limpio), db_path)


def obtener_becario(becario_id: int, db_path: Path = DB_PATH) -> Becario | None:
    return becario_repository.buscar_por_id(becario_id, db_path)


def listar_para_panel(db_path: Path = DB_PATH):
    """Filas del Panel de Control: (Becario, SeguimientoBecario o None)."""
    return seguimiento_repository.listar_para_panel(db_path)


# ---------------------------------------------------------------------------
# Datos de ejemplo para desarrollo (seed idempotente, 6 carreras × 2-3).
# Sirven para probar el listado y el futuro filtro por carrera.
# ---------------------------------------------------------------------------
_DATOS_EJEMPLO = [
    # (nombres, apellidos, ci, codigo, carrera, contacto, %ant, horas, mat, carpeta, carta)
    ("Beymar", "Condori Quispe", "8412035", "23718", "IAU", "71234501", "100%", True, True, True, True),
    ("Ana", "Quispe Ticona", "9021456", "24512", "IAU", "71234502", "0%", False, False, False, False),
    ("Diego", "Apaza Mamani", "7351892", "23801", "IAU", "71234503", "50%", True, False, False, True),
    ("Lucía", "Mamani Flores", "6890234", "24105", "DTEX", "71234504", "50%", True, True, False, True),
    ("José", "Ticona Huanca", "7745120", "24177", "DTEX", "71234505", "100%", True, True, True, False),
    ("Elena", "Paredes Quispe", "6534891", "24230", "DTEX", "71234506", "0%", False, True, False, False),
    ("Marco", "Choquehuanca Paredes", "5982103", "22987", "DER", "71234507", "100%", False, True, False, False),
    ("Camila", "Vargas Ríos", "8127465", "23112", "DER", "71234508", "50%", True, True, True, True),
    ("Miguel", "Huanca Copa", "7452309", "25034", "GAS", "71234509", "50%", True, False, True, True),
    ("Paola", "Ríos Fernández", "6981342", "25108", "GAS", "71234510", "100%", True, True, True, True),
    ("Luis", "Copa Ticona", "8234567", "25241", "GAS", "71234511", "0%", False, False, False, True),
    ("Andrea", "Quispe Mamani", "7348912", "26019", "SIS", "71234512", "100%", True, True, False, True),
    ("Daniel", "Fernández Choque", "6872345", "26177", "SIS", "71234513", "50%", False, True, False, False),
    ("Carolina", "Paredes Flores", "7981234", "27045", "CON", "71234514", "100%", True, True, True, True),
    ("Javier", "Ticona Ríos", "6456789", "27190", "CON", "71234515", "0%", False, False, False, False),
]


def asegurar_datos_ejemplo(db_path: Path = DB_PATH) -> int:
    """Inserta los ejemplos si la tabla está vacía. Retorna cuántos insertó."""
    if becario_repository.contar_becarios(db_path) > 0:
        return 0
    for (nombres, apellidos, ci, codigo, carrera, contacto,
         porc_ant, horas, mat, carpeta, carta) in _DATOS_EJEMPLO:
        becario = becario_repository.insertar_becario(
            Becario(id=None, nombres=nombres, apellidos=apellidos, ci=ci,
                    codigo_estudiante=codigo, carrera=carrera, contacto=contacto),
            db_path,
        )
        seguimiento_repository.crear_seguimiento(
            SeguimientoBecario(id=None, becario_id=becario.id, gestion=GESTION_EJEMPLO,
                               porcentaje_anterior=porc_ant, porcentaje_gestion=porc_ant,
                               horas_becarias=horas, materias_en_orden=mat,
                               carpeta_cancelada=carpeta, carta_renovacion=carta),
            db_path,
        )
    return len(_DATOS_EJEMPLO)
