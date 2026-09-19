"""Casos de uso de becarios — HU-02.

registrar_becario(datos) y editar_becario(id, datos): única puerta de
escritura. La UI nunca valida por su cuenta, solo llama aquí y muestra
el resultado. Duplicados se señalan con BecarioDuplicadoError(campo).
"""
from pathlib import Path

from app.models.becario import Becario
from app.models.seguimiento_becario import SeguimientoBecario
from app.persistence import becario_repository, carrera_repository, seguimiento_repository, tipo_beca_repository
from app.persistence.database import DB_PATH
from app.services.gestion_service import obtener_gestion_actual

CAMPOS_REQUERIDOS = ("nombres", "apellidos", "ci", "codigo_estudiante", "carrera", "tipo_beca")


def opciones_carrera(db_path: Path = DB_PATH) -> list[tuple[str, str]]:
    """(sigla, 'Nombre Completo - SIGLA') desde la BD, ordenadas por nombre.

    Mismo formato de siempre para la UI; la fuente ahora es la tabla
    carreras (solo activas), no una lista fija en código.
    """
    return [
        (c.sigla, f"{c.nombre_completo} - {c.sigla}")
        for c in carrera_repository.listar_activos(db_path)
    ]


def listar_tipos_beca(db_path: Path = DB_PATH) -> list[str]:
    """Nombres de tipos activos para el combo, desde la BD."""
    return [t.nombre for t in tipo_beca_repository.listar_activos(db_path)]


GESTION_INGRESO_MINIMA = "I-2019"


def _clave_gestion(gestion: str) -> tuple[int, int]:
    """(año, semestre) para comparar gestiones I-AAAA < II-AAAA < I-(AAAA+1)."""
    mitad, anio = gestion.split("-", 1)
    return int(anio), (1 if mitad == "I" else 2)


def gestiones_ingreso_validas() -> list[str]:
    """De I-2019 a la gestión actual, sin futuras (para el desplegable)."""
    actual = obtener_gestion_actual()
    validas = []
    anio = 2019
    while True:
        for mitad in ("I", "II"):
            candidata = f"{mitad}-{anio}"
            if _clave_gestion(candidata) > _clave_gestion(actual):
                return validas
            validas.append(candidata)
        anio += 1


class BecarioDuplicadoError(ValueError):
    """CI o código de estudiante ya registrado. Atributo `campo`: 'ci' o 'codigo_estudiante'."""

    def __init__(self, campo: str):
        self.campo = campo
        detalle = "El CI ya está registrado." if campo == "ci" else "El código de estudiante ya está registrado."
        super().__init__(detalle)


def _normalizar(datos: dict) -> dict:
    limpio = {k: (str(datos.get(k, "") or "").strip()) for k in
              ("nombres", "apellidos", "ci", "codigo_estudiante", "carrera",
               "contacto", "tipo_beca", "gestion_ingreso")}
    # Acepta sigla ("SIS") o etiqueta del combo ("Ingeniería de Sistemas - SIS").
    if " - " in limpio["carrera"]:
        limpio["carrera"] = limpio["carrera"].rsplit(" - ", 1)[1]
    limpio["carrera"] = limpio["carrera"].upper()
    limpio["nombres"] = normalizar_nombre_propio(limpio["nombres"])
    limpio["apellidos"] = normalizar_nombre_propio(limpio["apellidos"])
    return limpio


_EXCEPCIONES_NOMBRE = {"de", "del", "la", "las", "los", "y", "e"}

_CARACTERES_NOMBRE_EXTRA = {" ", "-", "'", "’"}


def es_nombre_valido(texto: str) -> bool:
    """Mínimo 2 caracteres; solo letras (tildes, ü, ñ), espacios, guion y apóstrofo."""
    if len(texto or "") < 2:
        return False
    return all(c.isalpha() or c in _CARACTERES_NOMBRE_EXTRA for c in texto)


def _capitalizar_parte(palabra: str) -> str:
    """Primera en mayúscula y resto en minúscula (respeta tildes y ñ)."""
    return palabra[:1].upper() + palabra[1:].lower() if palabra else palabra


def _capitalizar_palabra(palabra: str) -> str:
    """Capitaliza cada parte separada por guion o apóstrofo."""
    for separador in ("-", "'", "’"):
        if separador in palabra:
            return separador.join(_capitalizar_parte(p) for p in palabra.split(separador))
    return _capitalizar_parte(palabra)


def normalizar_nombre_propio(texto: str) -> str:
    """Mayúscula inicial por palabra ("ana maría" -> "Ana María").

    Quita espacios de sobra; las excepciones (de, del, la, las, los, y, e)
    van en minúscula salvo que abran el nombre ("de la Cruz").
    No agrega ni quita tildes.
    """
    normalizadas = []
    for i, palabra in enumerate((texto or "").split()):
        base = palabra.lower()
        if i > 0 and base in _EXCEPCIONES_NOMBRE:
            normalizadas.append(base)
        else:
            normalizadas.append(_capitalizar_palabra(base))
    return " ".join(normalizadas)


def _validar_requeridos(datos: dict, db_path: Path = DB_PATH):
    faltantes = [c for c in CAMPOS_REQUERIDOS if not datos[c]]
    if faltantes:
        # Solo texto visible al usuario: "codigo_estudiante" se muestra como "código".
        # (Variables, columnas y lógica de validación no cambian.)
        visibles = ["código" if c == "codigo_estudiante" else c for c in faltantes]
        raise ValueError(f"Faltan datos obligatorios: {', '.join(visibles)}.")
    if datos["nombres"] and not es_nombre_valido(datos["nombres"]):
        raise ValueError("Nombres no válidos: mínimo 2 letras (tildes, ñ, espacios, guion y apóstrofo).")
    if datos["apellidos"] and not es_nombre_valido(datos["apellidos"]):
        raise ValueError("Apellidos no válidos: mínimo 2 letras (tildes, ñ, espacios, guion y apóstrofo).")
    siglas = [c.sigla for c in carrera_repository.listar_activos(db_path)]
    if datos["carrera"] not in siglas:
        raise ValueError(f"Carrera no válida. Use una de: {', '.join(siglas)}.")
    tipos = [t.nombre for t in tipo_beca_repository.listar_activos(db_path)]
    if datos["tipo_beca"] not in tipos:
        raise ValueError(f"Tipo de beca no válido. Use uno de: {', '.join(tipos)}.")
    if datos["gestion_ingreso"] and datos["gestion_ingreso"] not in gestiones_ingreso_validas():
        raise ValueError("Gestión de ingreso no válida. Use una del desplegable.")


def registrar_becario(datos: dict, db_path: Path = DB_PATH) -> Becario:
    """Valida y registra un becario nuevo. Lanza BecarioDuplicadoError si CI o código existen.

    Crea además su SeguimientoBecario inicial con valores automáticos:
    horas en "No cumplió" y materias en "Sí" (el resto en negativo/0%).
    """
    limpio = _normalizar(datos)
    _validar_requeridos(limpio, db_path)
    if not limpio["gestion_ingreso"]:
        limpio["gestion_ingreso"] = obtener_gestion_actual()
    if becario_repository.existe_ci(limpio["ci"], db_path=db_path):
        raise BecarioDuplicadoError("ci")
    if becario_repository.existe_codigo(limpio["codigo_estudiante"], db_path=db_path):
        raise BecarioDuplicadoError("codigo_estudiante")
    becario = becario_repository.insertar_becario(Becario(id=None, **limpio), db_path)
    gestion = obtener_gestion_actual()
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
    _validar_requeridos(limpio, db_path)
    if becario_repository.existe_ci(limpio["ci"], excluir_id=becario_id, db_path=db_path):
        raise BecarioDuplicadoError("ci")
    if becario_repository.existe_codigo(limpio["codigo_estudiante"], excluir_id=becario_id, db_path=db_path):
        raise BecarioDuplicadoError("codigo_estudiante")
    actualizado = Becario(id=becario_id, **limpio)
    # El estado se gestiona en HU-03, no en este formulario: se preserva.
    actualizado.estado = actual.estado
    return becario_repository.actualizar_becario(actualizado, db_path)


def obtener_becario(becario_id: int, db_path: Path = DB_PATH) -> Becario | None:
    return becario_repository.buscar_por_id(becario_id, db_path)


def buscar_becario(codigo_o_ci: str, db_path: Path = DB_PATH) -> Becario | None:
    """HU-04: busca primero por código de estudiante y, si no hay, por CI.

    Retorna el Becario encontrado o None (la UI muestra "sin resultados").
    """
    texto = (codigo_o_ci or "").strip()
    if not texto:
        return None
    encontrado = becario_repository.buscar_por_codigo(texto, db_path)
    if encontrado is None:
        encontrado = becario_repository.buscar_por_ci(texto, db_path)
    return encontrado


def obtener_ficha_completa(becario_id: int, db_path: Path = DB_PATH) -> dict | None:
    """HU-04: agrega Becario + SeguimientoBecario más reciente.

    Claves: becario, seguimiento (o None), registro_academico (None,
    reservado para HU-05). Sin DocumentoBecario: esa HU salió del alcance
    vigente, por eso la ficha no tiene sección de documentos.
    """
    becario = becario_repository.buscar_por_id(becario_id, db_path)
    if becario is None:
        return None
    seguimientos = [
        seg for b, seg in seguimiento_repository.listar_para_panel(db_path)
        if b.id == becario_id
    ]
    seguimiento = seguimientos[0] if seguimientos else None
    carrera = carrera_repository.obtener_por_sigla(becario.carrera, db_path)
    etiqueta = f"{carrera.nombre_completo} - {carrera.sigla}" if carrera else becario.carrera
    return {
        "becario": becario,
        "seguimiento": seguimiento,
        "carrera_etiqueta": etiqueta,
        "registro_academico": None,  # HU-05: notas y horas del periodo
    }


def _asegurar_seguimiento(becario_id: int, periodo: str | None, db_path: Path = DB_PATH) -> SeguimientoBecario:
    """Retorna el SeguimientoBecario de (becario, periodo), creándolo si falta.

    Comportamiento definido HU-05: si no hay registro para el periodo
    (gestion más reciente, o la indicada), se crea uno con valores por
    defecto (0%, horas "No cumplió", materias "Sí") y se actualiza sobre él.
    La acción nunca se bloquea por falta de registro.
    """
    gestion = (periodo or "").strip()
    if not gestion or gestion == "—":
        gestion = obtener_gestion_actual()
    seg = seguimiento_repository.obtener_por_becario(becario_id, gestion, db_path)
    if seg is None:
        seg = SeguimientoBecario(id=None, becario_id=becario_id, gestion=gestion)
        seguimiento_repository.crear_seguimiento(seg, db_path)
    return seg


def actualizar_materias_en_orden(
    becario_id: int, periodo: str | None, valor: bool, db_path: Path = DB_PATH
) -> SeguimientoBecario:
    """HU-05: guarda Sí/No de materias en el registro del periodo (existe o creado)."""
    seg = _asegurar_seguimiento(becario_id, periodo, db_path)
    seg.materias_en_orden = bool(valor)
    return seguimiento_repository.actualizar(seg, db_path)


def actualizar_horas_becarias(
    becario_id: int, periodo: str | None, valor: bool, db_path: Path = DB_PATH
) -> SeguimientoBecario:
    """HU-05: guarda Cumplió/No cumplió de horas en el registro del periodo (existe o creado)."""
    seg = _asegurar_seguimiento(becario_id, periodo, db_path)
    seg.horas_becarias = bool(valor)
    return seguimiento_repository.actualizar(seg, db_path)


def actualizar_carpeta_cancelada(
    becario_id: int, periodo: str | None, valor: bool, db_path: Path = DB_PATH
) -> SeguimientoBecario:
    """HU-05 ext.: guarda Sí/No de carpeta en el registro del periodo (existe o creado)."""
    seg = _asegurar_seguimiento(becario_id, periodo, db_path)
    seg.carpeta_cancelada = bool(valor)
    return seguimiento_repository.actualizar(seg, db_path)


def actualizar_carta_renovacion(
    becario_id: int, periodo: str | None, valor: bool, db_path: Path = DB_PATH
) -> SeguimientoBecario:
    """HU-05 ext.: guarda Sí/No de carta en el registro del periodo (existe o creado)."""
    seg = _asegurar_seguimiento(becario_id, periodo, db_path)
    seg.carta_renovacion = bool(valor)
    return seguimiento_repository.actualizar(seg, db_path)


ESTADOS_BECARIO = ["Activo", "En renovación", "Baja/Inactivo"]


def actualizar_estado(becario_id: int, estado: str, db_path: Path = DB_PATH) -> Becario:
    """HU-03: cambia el estado del becario (validado contra los 3 permitidos)."""
    valor = (estado or "").strip()
    if valor not in ESTADOS_BECARIO:
        raise ValueError(f"Estado no válido. Use uno de: {', '.join(ESTADOS_BECARIO)}.")
    if becario_repository.buscar_por_id(becario_id, db_path) is None:
        raise ValueError("El becario no existe.")
    becario_repository.actualizar_estado(becario_id, valor, db_path)
    return becario_repository.buscar_por_id(becario_id, db_path)


def listar_para_panel(db_path: Path = DB_PATH):
    """Filas del Panel de Control: (Becario, SeguimientoBecario o None)."""
    return seguimiento_repository.listar_para_panel(db_path)


def listar_inactivos(db_path: Path = DB_PATH):
    """Becarios con estado Baja/Inactivo (no salen en el listado principal)."""
    return [
        (b, seg) for b, seg in seguimiento_repository.listar_para_panel(db_path)
        if b.estado == "Baja/Inactivo"
    ]


def eliminar_becario(becario_id: int, db_path: Path = DB_PATH) -> bool:
    """Elimina el becario y sus seguimientos (hijos primero). Solo con confirmación UI."""
    if becario_repository.buscar_por_id(becario_id, db_path) is None:
        raise ValueError("El becario no existe.")
    seguimiento_repository.eliminar_por_becario(becario_id, db_path)
    return becario_repository.eliminar(becario_id, db_path)


def eliminar_inactivos(db_path: Path = DB_PATH) -> int:
    """Elimina TODOS los Baja/Inactivo (becario + seguimientos). Retorna cuántos."""
    eliminados = 0
    for becario, _seg in listar_inactivos(db_path):
        if becario.id is not None and eliminar_becario(becario.id, db_path):
            eliminados += 1
    return eliminados


def historial_gestiones(becario_id: int, db_path: Path = DB_PATH) -> list[str]:
    """Historial del becario (primera a más reciente). Solo lectura, sin tablas nuevas."""
    return seguimiento_repository.listar_gestiones(becario_id, db_path)


def contar_becarios_por_categoria(db_path: Path = DB_PATH) -> list[tuple[str, int]]:
    """HU-06: [(categoria, cantidad)] para cada tipo del catálogo, con 0 incluidos."""
    conteo = becario_repository.contar_por_tipo_beca(db_path)
    return [
        (t.nombre, conteo.get(t.nombre, 0))
        for t in tipo_beca_repository.listar_todos(db_path)
    ]


# ---------------------------------------------------------------------------
# Datos de ejemplo para desarrollo (seed idempotente, 6 carreras × 2-3,
# repartidos también entre los 6 tipos de beca para probar el filtro).
# Sirven para probar el listado y el futuro filtro por carrera.
# ---------------------------------------------------------------------------
_DATOS_EJEMPLO = [
    # (nombres, apellidos, ci, codigo, carrera, contacto, tipo, estado, %ant, horas, mat, carpeta, carta, ingreso)
    ("Beymar", "Condori Quispe", "8412035", "23718", "IAU", "71234501", "Excelencia Académica", "Activo", "100%", True, True, True, True, "I-2024"),
    ("Ana", "Quispe Ticona", "9021456", "24512", "IAU", "71234502", "Económica Social", "Activo", "0%", False, False, False, False, "II-2024"),
    ("Diego", "Apaza Mamani", "7351892", "23801", "IAU", "71234503", "Convenio Interinstitucional", "Activo", "50%", True, False, False, True, "I-2025"),
    ("Lucía", "Mamani Flores", "6890234", "24105", "DTEX", "71234504", "Personal Administrativo", "Activo", "50%", True, True, False, True, "II-2025"),
    ("José", "Ticona Huanca", "7745120", "24177", "DTEX", "71234505", "Honorífica Directorio", "Activo", "100%", True, True, True, False, "I-2026"),
    ("Elena", "Paredes Quispe", "6534891", "24230", "DTEX", "71234506", "Social - Ministerio de Educación", "En renovación", "0%", False, True, False, False, "II-2026"),
    ("Marco", "Choquehuanca Paredes", "5982103", "22987", "DER", "71234507", "Excelencia Académica", "En renovación", "100%", False, True, False, False, "I-2024"),
    ("Camila", "Vargas Ríos", "8127465", "23112", "DER", "71234508", "Económica Social", "Activo", "50%", True, True, True, True, "II-2024"),
    ("Miguel", "Huanca Copa", "7452309", "25034", "LGYH", "71234509", "Convenio Interinstitucional", "Activo", "50%", True, False, True, True, "I-2025"),
    ("Paola", "Ríos Fernández", "6981342", "25108", "LGYH", "71234510", "Personal Administrativo", "Activo", "100%", True, True, True, True, "II-2025"),
    ("Luis", "Copa Ticona", "8234567", "25241", "LGYH", "71234511", "Honorífica Directorio", "Baja/Inactivo", "0%", False, False, False, True, "I-2026"),
    ("Andrea", "Quispe Mamani", "7348912", "26019", "SIS", "71234512", "Social - Ministerio de Educación", "Activo", "100%", True, True, False, True, "II-2026"),
    ("Daniel", "Fernández Choque", "6872345", "26177", "SIS", "71234513", "Excelencia Académica", "Activo", "50%", False, True, False, False, "I-2024"),
    ("Carolina", "Paredes Flores", "7981234", "27045", "CPU", "71234514", "Económica Social", "Activo", "100%", True, True, True, True, "I-2025"),
    ("Javier", "Ticona Ríos", "6456789", "27190", "CPU", "71234515", "Convenio Interinstitucional", "En renovación", "0%", False, False, False, False, "II-2025"),
]


def asegurar_datos_ejemplo(db_path: Path = DB_PATH) -> int:
    """Inserta los ejemplos si la tabla está vacía. Retorna cuántos insertó."""
    if becario_repository.contar_becarios(db_path) > 0:
        return 0
    for (nombres, apellidos, ci, codigo, carrera, contacto, tipo_beca, estado,
         porc_ant, horas, mat, carpeta, carta, ingreso) in _DATOS_EJEMPLO:
        becario = becario_repository.insertar_becario(
            Becario(id=None, nombres=nombres, apellidos=apellidos, ci=ci,
                    codigo_estudiante=codigo, carrera=carrera, contacto=contacto,
                    tipo_beca=tipo_beca, estado=estado, gestion_ingreso=ingreso),
            db_path,
        )
        seguimiento_repository.crear_seguimiento(
            SeguimientoBecario(id=None, becario_id=becario.id, gestion=obtener_gestion_actual(),
                               porcentaje_anterior=porc_ant, porcentaje_gestion=porc_ant,
                               horas_becarias=horas, materias_en_orden=mat,
                               carpeta_cancelada=carpeta, carta_renovacion=carta),
            db_path,
        )
    return len(_DATOS_EJEMPLO)


def completar_tipos_vacios(db_path: Path = DB_PATH) -> int:
    """Backfill puntual HU-06: becarios pre-HU-03 con tipo vacío ('').

    Les asigna tipos del catálogo en reparto rotativo por orden de id.
    No toca a los que ya tienen tipo. Idempotente (0 si no hay vacíos).
    """
    tipos = [t.nombre for t in tipo_beca_repository.listar_activos(db_path)]
    if not tipos:
        return 0
    ids = becario_repository.listar_ids_sin_tipo(db_path)
    for i, becario_id in enumerate(ids):
        becario_repository.asignar_tipo_beca(becario_id, tipos[i % len(tipos)], db_path)
    return len(ids)


def distribuir_estados_ejemplo(db_path: Path = DB_PATH) -> int:
    """Reparto puntual: si TODOS los becarios están en "Activo" (valor por
    defecto, nunca clasificados porque no había UI para cambiarlo), asigna
    estados variados por orden de id (En renovación ×3, Baja ×1).

    Si algún registro ya tiene otro estado, no toca nada (dato real).
    Idempotente: segunda corrida encuentra no-Activos y retorna 0.
    """
    todos = becario_repository.listar_todos(db_path)
    if not todos or any(b.estado != "Activo" for b in todos):
        return 0
    ids = sorted(b.id for b in todos if b.id is not None)
    # Reparto simple y trazable: posiciones 5, 9, 13 -> En renovación; 11 -> Baja.
    cambiados = 0
    for posicion, estado in ((5, "En renovación"), (9, "En renovación"),
                            (11, "Baja/Inactivo"), (13, "En renovación")):
        if posicion < len(ids):
            becario_repository.actualizar_estado(ids[posicion], estado, db_path)
            cambiados += 1
    return cambiados
