from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.seguimiento_becario import SeguimientoBecario
from app.persistence import configuracion_repository, respaldo_repository, seguimiento_repository
from app.persistence import becario_repository
from app.persistence.database import DB_PATH

CLAVE_GESTION = "gestion_activa"


def clave_gestion(gestion: str | None) -> tuple[int, int]:
    texto = (gestion or "").strip()
    if not texto or "-" not in texto:
        return (0, 0)
    periodo, anio = texto.split("-", 1)
    return int(anio), 1 if periodo.upper() == "I" else 2


def ordenar_gestiones(gestiones: list[str] | tuple[str, ...] | set[str]) -> list[str]:
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
    f = fecha or datetime.now()
    if 3 <= f.month <= 8:
        return f"I-{f.year}"
    if f.month >= 9:
        return f"II-{f.year}"
    return f"II-{f.year - 1}"


def obtener_gestion_almacenada(db_path: Path = DB_PATH) -> Optional[str]:
    return configuracion_repository.obtener(CLAVE_GESTION, db_path)


def obtener_gestion_predeterminada(db_path: Path = DB_PATH) -> str:
    return obtener_gestion_almacenada(db_path) or obtener_gestion_actual()

def resetear_periodo(db_path: Path = DB_PATH, gestion_nueva: str | None = None) -> dict:
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
    from app.services import becario_service
    becario_service.limpiar_fecha_limite(db_path)
    return res


def verificar_gestion_activa(db_path: Path = DB_PATH, fecha_referencia=None) -> tuple[Optional[str], str, bool, dict | None]:
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
