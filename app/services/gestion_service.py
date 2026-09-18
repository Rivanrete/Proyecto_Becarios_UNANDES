"""Gestión académica activa — cálculo automático por fecha del sistema.

- I-XXXX: 1-mar a 31-ago del año XXXX.
- II-XXXX: 1-sep a 28/29-feb del año siguiente (en ene/feb la gestión
  II es la del año anterior: ene-2027 sigue siendo II-2026).
Todo se deriva de datetime.now(): sin años hardcodeados.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.persistence import configuracion_repository, respaldo_repository, seguimiento_repository
from app.persistence import becario_repository
from app.persistence.database import DB_PATH

CLAVE_GESTION = "gestion_activa"


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

def resetear_periodo(db_path: Path = DB_PATH) -> dict:
    """Prepara la nueva gestión en becarios ACTIVOS (Baja/Inactivo no se toca).

    - horas_becarias, carpeta_cancelada, carta_renovacion -> False (0/No).
    - materias_en_orden NO se toca (conserva su valor).
    - estado -> "En renovación".
    - Nombres, CI, carrera y demás campos no se tocan.
    Retorna {"becarios": n, "seguimientos": m} afectados.
    """
    res = {"becarios": 0, "seguimientos": 0}
    for becario in becario_repository.listar_todos(db_path):
        if becario.estado == "Baja/Inactivo":
            continue
        becario_repository.actualizar_estado(becario.id, "En renovación", db_path)
        res["becarios"] += 1
        for seg in seguimiento_repository.listar_por_becario(becario.id, db_path):
            seg.horas_becarias = False
            seg.carpeta_cancelada = False
            seg.carta_renovacion = False
            seguimiento_repository.actualizar(seg, db_path)
            res["seguimientos"] += 1
    return res


def verificar_gestion_activa(db_path: Path = DB_PATH, fecha_referencia=None) -> tuple[Optional[str], str, bool]:
    """Compara la gestión guardada con la calculada y aplica el cambio si difiere.

    Orden: 1) snapshot completo en Respaldos con la gestión que termina,
    2) reset de periodo (parte 2), 3) actualización del valor guardado.
    `fecha_referencia` solo existe para simular transiciones en pruebas.
    Retorna (anterior, actual, hubo_cambio).

    TODO: conectar aquí el backup/cierre de gestión (punto 7 de la lista)
    cuando ese proceso exista.
    """
    actual = obtener_gestion_actual(fecha_referencia)
    guardada = configuracion_repository.obtener(CLAVE_GESTION, db_path)
    if guardada != actual:
        if guardada:
            respaldo_repository.guardar_respaldo(
                guardada, seguimiento_repository.listar_para_panel(db_path), db_path)
            resetear_periodo(db_path)
        configuracion_repository.guardar(CLAVE_GESTION, actual, db_path)
        return guardada, actual, True
    return guardada, actual, False


def gestiones_respaldadas(db_path: Path = DB_PATH) -> list[str]:
    return respaldo_repository.listar_gestiones(db_path)


def leer_respaldo(gestion: str, db_path: Path = DB_PATH):
    return respaldo_repository.listar_por_gestion(gestion, db_path)
