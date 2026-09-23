"""Reporte "Becarios en riesgo" — capa de servicios.

Lee siempre de la BD (cada apertura, actualización y exportación).
La regla de riesgo es parametros_faltantes(): la misma que pinta las
filas en rojo, sin duplicarla aquí.
"""
from datetime import datetime
from pathlib import Path

from app.persistence import becario_repository, seguimiento_repository
from app.persistence.database import DB_PATH
from app.services import becario_service
from app.services.catalogo_service import TIPOS_BECA_OFICIALES
from app.services.gestion_service import (
    obtener_gestion_predeterminada,
    ordenar_gestiones,
)

CONDICIONES_REPORTE = ("Todos", "Nueva", "Renovación")


def gestiones_reporte(db_path: Path = DB_PATH) -> list[str]:
    """Gestiones con registros + la predeterminada (siempre disponible)."""
    gestiones = set(seguimiento_repository.listar_gestiones_todas(db_path))
    gestiones.add(obtener_gestion_predeterminada(db_path))
    return ordenar_gestiones(gestiones)


def _condicion_de_seg(seg) -> str:
    return (seg.condicion or "") if seg is not None else ""


def datos_reporte_riesgo(gestion: str, condicion: str | None = None,
                         incluir_bajas: bool = True,
                         db_path: Path = DB_PATH) -> dict:
    """Arma el reporte de la gestión indicada.

    `condicion`: None (Todos), "Nueva" o "Renovación". Universo: becarios
    con registro en la gestión. Retorna {"gestion", "generado_en", "resumen",
    "en_riesgo" [...], "bajas" [...], "nota_bajas"} con filas ya filtradas.
    """
    gestion = (gestion or "").strip()
    solo_condicion = (condicion or "").strip() or None
    if solo_condicion == "Todos":
        solo_condicion = None
    en_riesgo: list[dict] = []
    bajas: list[dict] = []
    universo = 0
    for becario in becario_repository.listar_todos(db_path):
        seg = seguimiento_repository.obtener_por_becario(becario.id, gestion, db_path)
        es_baja = (becario.estado or "").strip() == "Baja/Inactivo"
        if es_baja:
            if not incluir_bajas:
                continue
            seg_vista = seg
            if seg_vista is None:
                anteriores = seguimiento_repository.listar_por_becario(becario.id, db_path)
                seg_vista = anteriores[-1] if anteriores else None
            if solo_condicion is not None and _condicion_de_seg(seg_vista) != solo_condicion:
                continue
            bajas.append({
                "codigo": becario.codigo_estudiante or "",
                "nombre": f"{becario.nombres} {becario.apellidos}".strip(),
                "carrera": becario.carrera or "",
                "tipo_beca": becario.tipo_beca or "",
                "gestion": (seg_vista.gestion if seg_vista is not None
                            else becario.gestion_ingreso or "—"),
            })
            continue
        if seg is None:
            continue  # sin registro en la gestión: no se puede evaluar
        if solo_condicion is not None and _condicion_de_seg(seg) != solo_condicion:
            continue
        universo += 1
        faltantes = becario_service.parametros_faltantes(becario.estado, seg)
        if not faltantes:
            continue
        en_riesgo.append({
            "codigo": becario.codigo_estudiante or "",
            "nombre": f"{becario.nombres} {becario.apellidos}".strip(),
            "carrera": becario.carrera or "",
            "tipo_beca": becario.tipo_beca or "",
            "condicion": _condicion_de_seg(seg) or "—",
            "faltantes": list(faltantes),
        })
    fallas = {nombre: 0 for nombre in becario_service.NOMBRES_PARAMETROS.values()}
    por_tipo = {nombre: 0 for nombre in TIPOS_BECA_OFICIALES}
    for fila in en_riesgo:
        for nombre in fila["faltantes"]:
            fallas[nombre] = fallas.get(nombre, 0) + 1
        if fila["tipo_beca"] in por_tipo:
            por_tipo[fila["tipo_beca"]] += 1
    total_riesgo = len(en_riesgo)
    resumen = {
        "total_gestion": universo,
        "en_riesgo": total_riesgo,
        "porcentaje_riesgo": round(total_riesgo * 100 / universo, 1) if universo else 0.0,
        "en_baja": len(bajas),
        "fallas": fallas,
        "por_tipo": por_tipo,
    }
    nota_bajas = ""
    if not incluir_bajas:
        nota_bajas = "Dados de baja excluidos por filtro (casilla sin marcar)."
    return {"gestion": gestion, "condicion": solo_condicion or "Todos",
            "generado_en": datetime.now(),
            "resumen": resumen, "en_riesgo": en_riesgo, "bajas": bajas,
            "nota_bajas": nota_bajas}


def html_vista_previa(datos: dict) -> str:
    """HTML sobrio para la vista previa en pantalla (mismos números del PDF)."""
    resumen = datos["resumen"]
    partes = [f"<h2>Becarios en riesgo — {datos['gestion']}</h2>",
              f"<p>Generado: {datos['generado_en'].strftime('%d/%m/%Y %H:%M')} · "
              f"Condición: {datos['condicion']}</p>",
              "<h3>Resumen</h3><ul>",
              f"<li>Total en la gestión: <b>{resumen['total_gestion']}</b></li>",
              f"<li>En riesgo: <b>{resumen['en_riesgo']}</b> "
              f"({resumen['porcentaje_riesgo']} %)</li>",
              f"<li>Dados de baja: <b>{resumen['en_baja']}</b></li>",
              "<li>Fallas por parámetro:<ul>"]
    for nombre, cantidad in resumen["fallas"].items():
        partes.append(f"<li>{nombre}: <b>{cantidad}</b></li>")
    partes.append("</ul></li><li>En riesgo por tipo de beca:<ul>")
    for nombre, cantidad in resumen["por_tipo"].items():
        partes.append(f"<li>{nombre}: <b>{cantidad}</b></li>")
    partes.append("</ul></li></ul>")
    partes.append("<h3>En riesgo</h3>")
    if datos["en_riesgo"]:
        partes.append("<table border='1' cellspacing='0' cellpadding='4'>"
                      "<tr><th>Código</th><th>Nombre</th><th>Carrera</th>"
                      "<th>Tipo de beca</th><th>Condición</th><th>Le falta</th></tr>")
        for fila in datos["en_riesgo"]:
            partes.append("<tr><td>{codigo}</td><td>{nombre}</td><td>{carrera}</td>"
                          "<td>{tipo_beca}</td><td>{condicion}</td><td>{faltan}</td></tr>".format(
                              faltan=", ".join(fila["faltantes"]), **fila))
        partes.append("</table>")
    else:
        partes.append("<p><i>Sin becarios en riesgo en esta gestión. ¡Todo en orden!</i></p>")
    partes.append("<h3>Dados de baja</h3>")
    if datos["nota_bajas"]:
        partes.append(f"<p><i>{datos['nota_bajas']}</i></p>")
    elif datos["bajas"]:
        partes.append("<table border='1' cellspacing='0' cellpadding='4'>"
                      "<tr><th>Código</th><th>Nombre</th><th>Carrera</th>"
                      "<th>Tipo de beca</th><th>Gestión</th></tr>")
        for fila in datos["bajas"]:
            partes.append("<tr><td>{codigo}</td><td>{nombre}</td><td>{carrera}</td>"
                          "<td>{tipo_beca}</td><td>{gestion}</td></tr>".format(**fila))
        partes.append("</table>")
    else:
        partes.append("<p><i>Sin dados de baja.</i></p>")
    return "\n".join(partes)


def nombre_pdf_sugerido(gestion: str, ahora: datetime | None = None) -> str:
    """Reporte becarios en riesgo - {gestión} - {fecha}.pdf (nombre seguro)."""
    fecha = (ahora or datetime.now()).strftime("%Y-%m-%d")
    base = f"Reporte becarios en riesgo - {(gestion or '').strip()} - {fecha}.pdf"
    return "".join(c for c in base if c not in '\\/:*?"<>|').strip() or "Reporte.pdf"
