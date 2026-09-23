"""Exportación del reporte a PDF con lo que trae PySide6 (sin librerías nuevas).

Dibujo manual con QPdfWriter + QPainter: A4 horizontal, Arial negro,
encabezado del documento, resumen, tablas con encabezado repetido en
cada página, filas que nunca se parten y pie con número de página.
"""
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
    QFont,
    QFontMetrics,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QTextOption,
)

RESOLUCION_PPP = 96
MARGEN_PX = 48
NEGRO = Qt.GlobalColor.black
GRIS_LINEA = Qt.GlobalColor.black

FUENTE_TITULO = ("Arial", 13, True)
FUENTE_SUBTITULO = ("Arial", 9, False)
FUENTE_SECCION = ("Arial", 11, True)
FUENTE_TABLA_CABECERA = ("Arial", 8.5, True)
FUENTE_TABLA = ("Arial", 8.5, False)
FUENTE_PIE = ("Arial", 8, False)


def _fuente(nombre: str, puntos: float, negrita: bool) -> QFont:
    fuente = QFont(nombre, 0)
    fuente.setPointSizeF(puntos)
    fuente.setBold(negrita)
    return fuente


class _Compositor:
    """Junta operaciones de dibujo por página (para numerarlas al final)."""

    def __init__(self, ancho: int, alto: int):
        self.ancho = ancho
        self.alto = alto
        self.paginas: list[list] = [[]]
        self.y = MARGEN_PX
        self.limite = alto - MARGEN_PX - 30  # aire para el pie

    def _nueva_pagina(self):
        self.paginas.append([])
        self.y = MARGEN_PX

    def _operacion(self, funcion):
        self.paginas[-1].append(funcion)

    def espacio(self, pixeles: int):
        self.y += pixeles

    def parrafo(self, texto: str, fuente: QFont, alto_linea: int | None = None):
        metricas = QFontMetrics(fuente)
        rectangulo = metricas.boundingRect(
            0, 0, self.ancho - 2 * MARGEN_PX, 100000,
            Qt.TextFlag.TextWordWrap, texto)
        alto = (alto_linea or 0) + rectangulo.height() + 4
        if self.y + alto > self.limite:
            self._nueva_pagina()
        y = self.y
        ancho = self.ancho - 2 * MARGEN_PX
        rectangulo_dibujo = QRect(MARGEN_PX, y, ancho, 100000)
        self._operacion(lambda p, rectangulo_dibujo=rectangulo_dibujo: (
            p.setFont(fuente), p.setPen(NEGRO),
            p.drawText(rectangulo_dibujo,
                       Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft, texto)))
        self.y += alto

    def tabla(self, encabezados: list[str], filas: list[list[str]],
              anchos: list[int]):
        fuente_cab = _fuente(*FUENTE_TABLA_CABECERA)
        fuente = _fuente(*FUENTE_TABLA)
        metrica_cab = QFontMetrics(fuente_cab)
        metrica = QFontMetrics(fuente)
        alto_cab = metrica_cab.height() + 10

        def altura_fila(fila: list[str]) -> int:
            alta = 0
            for texto, ancho in zip(fila, anchos):
                rectangulo = metrica.boundingRect(
                    0, 0, ancho - 8, 100000, Qt.TextFlag.TextWordWrap, texto)
                alta = max(alta, rectangulo.height())
            return alta + 8

        def dibujar_encabezado(p, y):
            p.setFont(fuente_cab)
            x = MARGEN_PX
            for texto, ancho in zip(encabezados, anchos):
                p.setPen(GRIS_LINEA)
                p.drawRect(x, y, ancho, alto_cab)
                p.setPen(NEGRO)
                p.drawText(x + 4, y, ancho - 8, alto_cab,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                           texto)
                x += ancho

        def dibujar_fila(p, y, fila, alta):
            p.setFont(fuente)
            x = MARGEN_PX
            for texto, ancho in zip(fila, anchos):
                p.setPen(GRIS_LINEA)
                p.drawRect(x, y, ancho, alta)
                p.setPen(NEGRO)
                p.drawText(x + 4, y + 4, ancho - 8, alta - 8,
                           Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft,
                           texto)
                x += ancho

        if self.y + alto_cab > self.limite:
            self._nueva_pagina()
        y = self.y
        self._operacion(lambda p, y=y: dibujar_encabezado(p, y))
        self.y += alto_cab
        for fila in filas:
            alta = altura_fila(fila)
            if self.y + alta > self.limite:
                # La fila nunca se parte: antes del salto va el encabezado.
                self._nueva_pagina()
                y = self.y
                self._operacion(lambda p, y=y: dibujar_encabezado(p, y))
                self.y += alto_cab
            y = self.y
            self._operacion(lambda p, y=y, fila=list(fila), alta=alta:
                            dibujar_fila(p, y, fila, alta))
            self.y += alta


def _pie(pintor: QPainter, numero: int, total: int, ancho: int, alto: int):
    pintor.setFont(_fuente(*FUENTE_PIE))
    pintor.setPen(NEGRO)
    texto = f"Página {numero} de {total}"
    pintor.drawText(0, alto - 28, ancho - MARGEN_PX, 20,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    texto)


def exportar_reporte_pdf(datos: dict, ruta_destino: str) -> str:
    """Genera el PDF del reporte. Retorna la ruta. Lanza IOError si falla."""
    escritor = QPdfWriter(ruta_destino)
    escritor.setResolution(RESOLUCION_PPP)
    escritor.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    escritor.setPageOrientation(QPageLayout.Orientation.Landscape)
    tamano = escritor.pageLayout().paintRectPixels(RESOLUCION_PPP)
    ancho, alto = tamano.width(), tamano.height()

    compositor = _Compositor(ancho, alto)
    fecha = datos["generado_en"].strftime("%d/%m/%Y %H:%M")
    compositor.parrafo("Universidad de los Andes - Bienestar Estudiantil",
                       _fuente(*FUENTE_SUBTITULO))
    compositor.parrafo("Reporte de becarios en riesgo", _fuente(*FUENTE_TITULO))
    compositor.parrafo(f"Gestión: {datos['gestion']}   ·   "
                       f"Condición: {datos['condicion']}   ·   "
                       f"Generado: {fecha}", _fuente(*FUENTE_SUBTITULO))
    compositor.espacio(6)
    resumen = datos["resumen"]
    compositor.parrafo("Resumen", _fuente(*FUENTE_SECCION))
    compositor.parrafo(
        f"Total en la gestión: {resumen['total_gestion']}   ·   "
        f"En riesgo: {resumen['en_riesgo']} ({resumen['porcentaje_riesgo']} %)   ·   "
        f"Dados de baja: {resumen['en_baja']}", _fuente(*FUENTE_SUBTITULO))
    compositor.parrafo("Fallas por parámetro: " + "; ".join(
        f"{nombre}: {cantidad}" for nombre, cantidad in resumen["fallas"].items()),
        _fuente(*FUENTE_SUBTITULO))
    compositor.parrafo("En riesgo por tipo de beca: " + "; ".join(
        f"{nombre}: {cantidad}" for nombre, cantidad in resumen["por_tipo"].items()),
        _fuente(*FUENTE_SUBTITULO))
    compositor.espacio(6)
    compositor.parrafo(f"Becarios en riesgo ({len(datos['en_riesgo'])})",
                       _fuente(*FUENTE_SECCION))
    if datos["en_riesgo"]:
        disponible = ancho - 2 * MARGEN_PX
        resto = disponible - (70 + 70 + 80)
        anchos = [70, int(resto * 0.24), 70, int(resto * 0.30), 80,
                  disponible - (70 + int(resto * 0.24) + 70 + int(resto * 0.30) + 80)]
        compositor.tabla(
            ["Código", "Nombre completo", "Carrera", "Tipo de beca",
             "Condición", "Le falta"],
            [[f["codigo"], f["nombre"], f["carrera"], f["tipo_beca"],
              f["condicion"], ", ".join(f["faltantes"])] for f in datos["en_riesgo"]],
            anchos)
    else:
        compositor.parrafo("Sin becarios en riesgo en esta gestión. ¡Todo en orden!",
                           _fuente(*FUENTE_SUBTITULO))
    compositor.espacio(6)
    compositor.parrafo(f"Dados de baja ({len(datos['bajas'])})",
                       _fuente(*FUENTE_SECCION))
    if datos["nota_bajas"]:
        compositor.parrafo(datos["nota_bajas"], _fuente(*FUENTE_SUBTITULO))
    elif datos["bajas"]:
        disponible = ancho - 2 * MARGEN_PX
        resto = disponible - (80 + 90)
        anchos = [80, int(resto * 0.30), 90, int(resto * 0.55),
                  disponible - (80 + int(resto * 0.30) + 90 + int(resto * 0.55))]
        compositor.tabla(
            ["Código", "Nombre", "Carrera", "Tipo de beca", "Gestión"],
            [[f["codigo"], f["nombre"], f["carrera"], f["tipo_beca"], f["gestion"]]
             for f in datos["bajas"]],
            anchos)
    else:
        compositor.parrafo("Sin dados de baja.", _fuente(*FUENTE_SUBTITULO))

    total = len(compositor.paginas)
    pintor = QPainter(escritor)
    if not pintor.isActive():
        raise IOError(f"No se pudo escribir en {ruta_destino} "
                      "(carpeta sin permisos o archivo bloqueado).")
    try:
        for numero, operaciones in enumerate(compositor.paginas, start=1):
            if numero > 1:
                escritor.newPage()
            for operacion in operaciones:
                operacion(pintor)
            _pie(pintor, numero, total, ancho, alto)
    finally:
        pintor.end()
    return ruta_destino
