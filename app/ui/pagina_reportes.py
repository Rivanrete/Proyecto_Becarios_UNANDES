"""Página de Reportes — "Becarios en riesgo" (solo lectura + PDF).

Mismo estilo visual que las demás páginas del panel. Los datos se leen
siempre de la BD (al abrir, al actualizar y al exportar).
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.services import reporte_service
from app.services.gestion_service import obtener_gestion_predeterminada
from app.services.reporte_pdf import exportar_reporte_pdf
from app.ui.notificacion import mostrar_notificacion, pedir_confirmacion


class PaginaReportes(QWidget):
    """Vista previa del reporte con filtros y exportación a PDF."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refrescar()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        titulo = QLabel("Reportes — Becarios en riesgo")
        titulo.setObjectName("tituloSeccion")
        layout.addWidget(titulo)

        fila_gestion = QHBoxLayout()
        etiqueta = QLabel("Gestión:")
        etiqueta.setObjectName("etiquetaRespaldo")
        fila_gestion.addWidget(etiqueta)
        self.cmb_gestion = QComboBox()
        self.cmb_gestion.setObjectName("comboRespaldo")
        self.cmb_gestion.currentIndexChanged.connect(lambda _i: self.refrescar())
        fila_gestion.addWidget(self.cmb_gestion, 1)
        layout.addLayout(fila_gestion)

        fila_filtros = QHBoxLayout()
        etiqueta_cond = QLabel("Condición:")
        etiqueta_cond.setObjectName("etiquetaRespaldo")
        fila_filtros.addWidget(etiqueta_cond)
        self.cmb_condicion = QComboBox()
        self.cmb_condicion.setObjectName("comboRespaldo")
        self.cmb_condicion.addItems(list(reporte_service.CONDICIONES_REPORTE))
        self.cmb_condicion.currentIndexChanged.connect(lambda _i: self.refrescar())
        fila_filtros.addWidget(self.cmb_condicion)
        self.chk_bajas = QCheckBox("Incluir dados de baja")
        self.chk_bajas.setChecked(True)
        self.chk_bajas.checkStateChanged.connect(lambda _e: self.refrescar())
        fila_filtros.addWidget(self.chk_bajas)
        fila_filtros.addStretch(1)
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setObjectName("filtrar")
        self.btn_actualizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_actualizar.clicked.connect(self.refrescar)
        fila_filtros.addWidget(self.btn_actualizar)
        self.btn_exportar = QPushButton("Exportar a PDF")
        self.btn_exportar.setObjectName("nuevo")
        self.btn_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exportar.clicked.connect(self._exportar_pdf)
        fila_filtros.addWidget(self.btn_exportar)
        layout.addLayout(fila_filtros)

        self.vista = QTextBrowser()
        self.vista.setObjectName("vistaReporte")
        self.vista.setReadOnly(True)
        self.vista.setOpenExternalLinks(False)
        layout.addWidget(self.vista, 1)

    def _gestion_elegida(self) -> str:
        return self.cmb_gestion.currentText() or obtener_gestion_predeterminada()

    def _condicion_elegida(self) -> str | None:
        valor = self.cmb_condicion.currentText()
        return None if valor == "Todos" else valor

    def refrescar(self):
        """Relee gestiones y datos de la BD y repinta la vista previa."""
        actual = self._gestion_elegida()
        gestiones = reporte_service.gestiones_reporte()
        self.cmb_gestion.blockSignals(True)
        self.cmb_gestion.clear()
        self.cmb_gestion.addItems(gestiones)
        if actual in gestiones:
            self.cmb_gestion.setCurrentText(actual)
        else:
            self.cmb_gestion.setCurrentText(obtener_gestion_predeterminada())
        self.cmb_gestion.blockSignals(False)
        datos = reporte_service.datos_reporte_riesgo(
            self._gestion_elegida(), self._condicion_elegida(),
            self.chk_bajas.isChecked())
        self.vista.setHtml(reporte_service.html_vista_previa(datos))

    def _exportar_pdf(self):
        """Pide destino y genera el PDF con datos recién leídos de la BD."""
        ventana = self.window()
        datos = reporte_service.datos_reporte_riesgo(
            self._gestion_elegida(), self._condicion_elegida(),
            self.chk_bajas.isChecked())
        sugerido = reporte_service.nombre_pdf_sugerido(datos["gestion"])
        carpeta = Path.home() / "Documents"
        if not carpeta.is_dir():
            carpeta = Path(sugerido).parent
        destino_inicial = str(carpeta / sugerido)
        ruta, _filtro = QFileDialog.getSaveFileName(
            self, "Exportar reporte a PDF", destino_inicial, "PDF (*.pdf)")
        if not ruta:
            return  # canceló el diálogo
        ruta = ruta if ruta.lower().endswith(".pdf") else ruta + ".pdf"
        if Path(ruta).exists() and not pedir_confirmacion(
                ventana, f"El archivo {Path(ruta).name} ya existe. "
                         "¿Desea reemplazarlo?"):
            return
        try:
            exportar_reporte_pdf(datos, ruta)
        except (OSError, IOError, RuntimeError, ValueError) as e:
            mostrar_notificacion(
                ventana, "No se pudo guardar el PDF. Revise que la carpeta "
                         f"exista, tenga permisos y el archivo no esté abierto. ({e})",
                tipo="error")
            return
        self.refrescar()
        mostrar_notificacion(
            ventana, f"Reporte guardado en {Path(ruta).name} "
                     f"con {datos['resumen']['en_riesgo']} en riesgo.", tipo="exito")
