"""Gestión académica activa — cálculo automático por fecha del sistema.

- I-XXXX: 1-mar a 31-ago del año XXXX.
- II-XXXX: 1-sep a 28/29-feb del año siguiente (en ene/feb la gestión
  II es la del año anterior: ene-2027 sigue siendo II-2026).
Todo se deriva de datetime.now(): sin años hardcodeados.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.seguimiento_becario import SeguimientoBecario
from app.persistence import configuracion_repository, respaldo_repository, seguimiento_repository
from app.persistence import becario_repository
from app.persistence.database import DB_PATH

CLAVE_GESTION = "gestion_activa"


def clave_gestion(gestion: str | None) -> tuple[int, int]:
    """Orden estable para comparar gestiones del tipo I-2024 o II-2026."""
    texto = (gestion or "").strip()
    if not texto or "-" not in texto:
        return (0, 0)
    periodo, anio = texto.split("-", 1)
    return int(anio), 1 if periodo.upper() == "I" else 2


def ordenar_gestiones(gestiones: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    """Devuelve gestiones sin duplicados y en orden cronológico."""
    visibles = []
    vistos = set()
    for gestion in gestiones:
        texto = (gestion or "").strip()
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        visibles.append(texto)
    return sorted(visibles, key=clave_gestion)


def obtener_gestion_actual(fecha: Optional[datetime] = None) -> str:
    """Calcula la gestión vigente. `fecha` solo existe para pruebas."""
    f = fecha or datetime.now()
    if 3 <= f.month <= 8:
        return f"I-{f.year}"
    if f.month >= 9:
        return f"II-{f.year}"
    return f"II-{f.year - 1}"


def obtener_gestion_almacenada(db_path: Path = DB_PATH) -> Optional[str]:
    return configuracion_repository.obtener(CLAVE_GESTION, db_path)


def obtener_gestion_predeterminada(db_path: Path = DB_PATH) -> str:
    """Gestión activa guardada (vale tras cambios reales o simulados).

    Si aún no hay ninguna guardada (primer arranque), calcula con la fecha.
    """
    return obtener_gestion_almacenada(db_path) or obtener_gestion_actual()

def resetear_periodo(db_path: Path = DB_PATH, gestion_nueva: str | None = None) -> dict:
    """Prepara la nueva gestión en becarios ACTIVOS (Baja/Inactivo no se toca).

    La fila de la gestión que termina se conserva intacta; se crea una
    fila NUEVA para la gestión indicada con los valores reiniciados:
    - horas_becarias, carpeta_cancelada, carta_renovacion -> False (0/No).
    - materias_en_orden, porcentajes y condicion (Nueva/Renovación) se
      heredan de la fila anterior (la condición nunca se reinicia ni
      cambia sola: no hay transición Nueva -> Renovación).
    - estado -> "En renovación".
    - Nombres, CI, carrera y demás campos no se tocan.
    Si la fila nueva ya existe (reintento), se reinicia sobre ella.
    Retorna {"becarios": n, "seguimientos": m} afectados.
    """
    nueva = (gestion_nueva or "").strip() or obtener_gestion_actual()
    res = {"becarios": 0, "seguimientos": 0}
    for becario in becario_repository.listar_todos(db_path):
        if becario.estado == "Baja/Inactivo":
            continue
        becario_repository.actualizar_estado(becario.id, "En renovación", db_path)
        res["becarios"] += 1
        anteriores = seguimiento_repository.listar_por_becario(becario.id, db_path)
        existente = next((s for s in anteriores if s.gestion == nueva), None)
        if existente is not None:
            existente.horas_becarias = False
            existente.carpeta_cancelada = False
            existente.carta_renovacion = False
            seguimiento_repository.actualizar(existente, db_path)
        elif anteriores:
            base = anteriores[-1]
            seguimiento_repository.crear_seguimiento(SeguimientoBecario(
                id=None, becario_id=becario.id, gestion=nueva,
                porcentaje_anterior=base.porcentaje_anterior,
                porcentaje_gestion=base.porcentaje_gestion,
                condicion=base.condicion or "Nueva",
                horas_becarias=False, materias_en_orden=base.materias_en_orden,
                carpeta_cancelada=False, carta_renovacion=False), db_path)
        else:
            seguimiento_repository.crear_seguimiento(SeguimientoBecario(
                id=None, becario_id=becario.id, gestion=nueva), db_path)
        res["seguimientos"] += 1
    # Cada gestión empieza sin fecha límite: la Lic. la define a mano.
    # Import local: becario_service importa este módulo (ciclo si es global).
    from app.services import becario_service
    becario_service.limpiar_fecha_limite(db_path)
    return res


def verificar_gestion_activa(db_path: Path = DB_PATH, fecha_referencia=None) -> tuple[Optional[str], str, bool, dict | None]:
    """Compara la gestión guardada con la calculada y aplica el cambio si difiere.

    Orden: 1) snapshot completo en Respaldos con la gestión que termina,
    2) reset de periodo (parte 2), 3) actualización del valor guardado.
    `fecha_referencia` solo existe para simular transiciones en pruebas.
    Retorna (anterior, actual, hubo_cambio, detalle). `detalle` trae los
    números reales de lo que se hizo (respaldados, reiniciados,
    sin_modificar) o None si no se aplicó ningún cambio.

    TODO: conectar aquí el backup/cierre de gestión (punto 7 de la lista)
    cuando ese proceso exista.
    """
    actual = obtener_gestion_actual(fecha_referencia)
    guardada = configuracion_repository.obtener(CLAVE_GESTION, db_path)
    if guardada != actual:
        if guardada:
            filas = seguimiento_repository.listar_para_panel(db_path)
            respaldados = respaldo_repository.guardar_respaldo(
                guardada, filas, db_path)
            reiniciados = resetear_periodo(db_path, actual)["becarios"]
            detalle = {
                "respaldados": respaldados,
                "reiniciados": reiniciados,
                "sin_modificar": len(filas) - reiniciados,
            }
            configuracion_repository.guardar(CLAVE_GESTION, actual, db_path)
            return guardada, actual, True, detalle
        configuracion_repository.guardar(CLAVE_GESTION, actual, db_path)
        return guardada, actual, True, None
    return guardada, actual, False, None


def gestiones_respaldadas(db_path: Path = DB_PATH) -> list[str]:
    return respaldo_repository.listar_gestiones(db_path)


def leer_respaldo(gestion: str, db_path: Path = DB_PATH):
    return respaldo_repository.listar_por_gestion(gestion, db_path)
