"""Diálogo para definir la fecha límite de requisitos — la fija la Lic. a mano.

Sigue el estándar UX del proyecto: hereda DialogoBase (frameless), se
muestra con overlay y valida en línea con lbl_error (sin QMessageBox).
Guardar devuelve la fecha ISO; "Quitar fecha límite" la deja sin límite.

Sin fecha guardada el selector inicia vacío y Guardar arranca
deshabilitado: imposible guardar por accidente. La fecha se MUESTRA como
DD/MM/AA pero se guarda en ISO (YYYY-MM-DD).

El selector es línea de solo lectura + botón con ícono SVG (mismo método
de render que el ojo de login_window) que abre un calendario emergente
tipo popup anclado al campo: no modal, se cierra con un clic en una fecha
o fuera de él, sin bloquear el diálogo principal.
"""
from PySide6.QtCore import QPoint, Qt, QDate, QSize, QEvent, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.becario_service import formato_fecha_corta
from app.ui import theme
from app.ui.dialogo_base import DialogoBase

# Calendario outline monocromático (SVG en línea, como el ojo del login).
# Color = texto principal de la paleta sobre la tarjeta.
_CALENDARIO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"'
    ' viewBox="0 0 24 24" fill="none" stroke="' + theme.TEXTO_PRINCIPAL + '"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>'
    '<line x1="16" y1="2" x2="16" y2="6"/>'
    '<line x1="8" y1="2" x2="8" y2="6"/>'
    '<line x1="3" y1="10" x2="21" y2="10"/></svg>'
)


def icono_calendario():
    """Renderiza el SVG del calendario a QIcon (mismo método que el ojo)."""
    from PySide6.QtGui import QIcon
    renderer = QSvgRenderer(bytearray(_CALENDARIO_SVG.encode("utf-8")))
    imagen = QImage(24, 24, QImage.Format.Format_ARGB32)
    imagen.fill(0)
    pintor = QPainter(imagen)
    try:
        renderer.render(pintor)
    finally:
        pintor.end()
    return QIcon(QPixmap.fromImage(imagen))


class _PopupCalendario(QWidget):
    """Calendario flotante anclado al campo (Popup: no modal, cierra solo).

    Un clic en una fecha la elige y cierra; un clic fuera o Esc cierra sin
    cambiar nada. El diálogo principal sigue interactuable en todo momento.
    """

    fecha_elegida = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("popupCalendario")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.calendario = QCalendarWidget(self)
        self.calendario.setGridVisible(True)
        self.calendario.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendario.clicked.connect(self._on_fecha)
        self.calendario.activated.connect(self._on_fecha)
        layout.addWidget(self.calendario)
        self.setStyleSheet(f"""
            QWidget#popupCalendario {{
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 12px;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {theme.AZUL_FONDO};
            }}
            QCalendarWidget QToolButton {{
                color: {theme.TEXTO_PRINCIPAL};
                background-color: transparent;
                font-size: 13px; font-weight: 700;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: {theme.AZUL_TARJETA};
                color: {theme.TEXTO_PRINCIPAL};
                selection-background-color: {theme.VERDE_LIMA};
                selection-color: {theme.AZUL_FONDO};
                font-size: 12px;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: {theme.TEXTO_SECUNDARIO};
            }}
        """)

    def mostrar_anclado(self, campo: QWidget, fecha: QDate | None):
        """Muestra pegado al campo: debajo, o arriba/al costado sin espacio."""
        self.calendario.setSelectedDate(
            fecha if (fecha is not None and fecha.isValid()) else QDate.currentDate())
        self.adjustSize()
        esquina = campo.mapToGlobal(QPoint(0, campo.height()))
        pantalla = QApplication.primaryScreen()
        area = pantalla.availableGeometry() if pantalla is not None else None
        x, y = esquina.x(), esquina.y()
        if area is not None:
            if y + self.height() > area.bottom():
                y = campo.mapToGlobal(QPoint(0, 0)).y() - self.height()
            if x + self.width() > area.right():
                x = area.right() - self.width()
            x, y = max(area.left(), x), max(area.top(), y)
        self.move(x, y)
        self.show()
        self.raise_()

    def _on_fecha(self, fecha: QDate):
        self.fecha_elegida.emit(fecha)
        self.close()


class DialogoFechaLimite(DialogoBase):
    """Modal pequeño: muestra la vigente (o "Sin fecha límite") y edita."""

    def __init__(self, parent=None, fecha_actual: str | None = None):
        super().__init__(parent, modal=True)
        self.setWindowTitle("UNANDES • Fecha límite")
        self.fecha_iso: str | None = None
        self._fecha: QDate | None = None
        self._popup: _PopupCalendario | None = None
        self._vigente = (fecha_actual or "").strip() or None
        self._build_ui()
        self._apply_style()
        self._precargar()
        # Red de seguridad para el cierre-fuera del popup (además del
        # autocierre nativo de Qt.Popup): mientras el calendario está
        # visible, un clic fuera de él lo cierra sin cambiar la fecha.
        QApplication.instance().installEventFilter(self)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(20, 20, 20, 20)

        card = QFrame(self)
        card.setObjectName("cardFecha")
        card.setMinimumWidth(320)
        card.setMaximumWidth(400)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(28, 24, 28, 24)

        encabezado = QHBoxLayout()
        titulo = QLabel("Fecha límite de requisitos", card)
        titulo.setObjectName("tituloFecha")
        encabezado.addWidget(titulo)
        encabezado.addStretch(1)
        encabezado.addWidget(self.crear_boton_x(card))
        layout.addLayout(encabezado)

        self.lbl_vigente = QLabel("", card)
        self.lbl_vigente.setObjectName("vigenteFecha")
        self.lbl_vigente.setWordWrap(True)
        layout.addWidget(self.lbl_vigente)

        fila_fecha = QHBoxLayout()
        fila_fecha.setSpacing(8)
        self.txt_fecha = QLineEdit(card)
        self.txt_fecha.setReadOnly(True)
        self.txt_fecha.setPlaceholderText("Elegir fecha… (DD/MM/AA)")
        fila_fecha.addWidget(self.txt_fecha, 1)
        self.btn_elegir = QPushButton(card)
        self.btn_elegir.setObjectName("elegirFecha")
        self.btn_elegir.setIcon(icono_calendario())
        self.btn_elegir.setIconSize(QSize(20, 20))
        self.btn_elegir.setToolTip("Abrir calendario")
        self.btn_elegir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_elegir.clicked.connect(self._abrir_calendario)
        fila_fecha.addWidget(self.btn_elegir)
        layout.addLayout(fila_fecha)

        self.lbl_error = QLabel("", card)
        self.lbl_error.setObjectName("errorFecha")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        self.btn_guardar = QPushButton("Guardar fecha", card)
        self.btn_guardar.setObjectName("guardarFecha")
        self.btn_guardar.setDefault(True)
        self.btn_guardar.clicked.connect(self._on_guardar)
        layout.addWidget(self.btn_guardar)

        self.btn_quitar = QPushButton("Quitar fecha límite", card)
        self.btn_quitar.setObjectName("quitarFecha")
        self.btn_quitar.clicked.connect(self._on_quitar)
        layout.addWidget(self.btn_quitar)

        self.btn_cancelar = QPushButton("Cancelar", card)
        self.btn_cancelar.setObjectName("cancelarFecha")
        self.btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancelar)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _precargar(self):
        """Con fecha guardada muestra esa exacta; si no, vacío real."""
        if self._vigente:
            guardada = QDate.fromString(self._vigente, "yyyy-MM-dd")
            if guardada.isValid():
                self._fijar_fecha(guardada)
                self.lbl_vigente.setText(
                    f"Fecha límite actual: {formato_fecha_corta(self._vigente)}")
                return
        self._fecha = None
        self.txt_fecha.setText("")
        self.lbl_vigente.setText("Sin fecha límite")
        self.btn_guardar.setEnabled(False)

    def _fijar_fecha(self, fecha: QDate):
        """Refleja la fecha elegida (línea DD/MM/AA + Guardar habilitado)."""
        self._fecha = fecha
        self.txt_fecha.setText(fecha.toString("dd/MM/yy"))
        self.btn_guardar.setEnabled(True)
        self.lbl_error.setText("")
        self.lbl_error.setVisible(False)

    def _abrir_calendario(self):
        if self._popup is None:
            self._popup = _PopupCalendario(self)
            self._popup.fecha_elegida.connect(self._fijar_fecha)
        if self._popup.isVisible():
            self._popup.close()
            return
        self._popup.mostrar_anclado(self.txt_fecha, self._fecha)

    def closeEvent(self, event):
        if self._popup is not None and self._popup.isVisible():
            self._popup.close()
        try:
            QApplication.instance().removeEventFilter(self)
        except RuntimeError:
            pass
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        """Cierra el calendario ante un clic fuera de él (sin tocar la fecha)."""
        pop = self._popup
        if (pop is not None and pop.isVisible()
                and event.type() == QEvent.Type.MouseButtonPress):
            origen = obj if isinstance(obj, QWidget) else None
            dentro = (
                origen is not None
                and (pop.isAncestorOf(origen) or origen is pop
                     or origen is self.btn_elegir or origen is self.txt_fecha
                     or self.btn_elegir.isAncestorOf(origen)
                     or self.txt_fecha.isAncestorOf(origen)))
            if not dentro:
                posicion = event.globalPosition().toPoint()
                if not pop.geometry().contains(posicion):
                    pop.close()
        return super().eventFilter(obj, event)

    def _on_guardar(self):
        if self._fecha is None or not self._fecha.isValid():
            self.lbl_error.setText("Elija primero una fecha del calendario.")
            self.lbl_error.setVisible(True)
            return
        self.fecha_iso = self._fecha.toString("yyyy-MM-dd")
        self.accept()

    def _on_quitar(self):
        self.fecha_iso = None
        self.accept()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QFrame#cardFecha {{
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 16px;
            }}
            QLabel#tituloFecha {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 16px; font-weight: 800; }}
            QLabel {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 13px; font-weight: 600; }}
            QLabel#vigenteFecha {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 13px; }}
            QToolButton#cerrar {{
                color: {theme.TEXTO_SECUNDARIO}; font-size: 14px; font-weight: 700;
                background: transparent; border: none; padding: 4px 8px;
            }}
            QToolButton#cerrar:hover {{ color: {theme.TEXTO_ERROR}; }}
            QLineEdit {{
                background-color: {theme.AZUL_CAMPO}; color: {theme.TEXTO_PRINCIPAL};
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 9px 10px;
                font-size: 13px;
            }}
            QPushButton#elegirFecha {{
                background-color: {theme.AZUL_CAMPO}; color: {theme.TEXTO_PRINCIPAL};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 8px; padding: 7px 10px;
            }}
            QPushButton#elegirFecha:hover {{ border-color: {theme.VERDE_LIMA}; }}
            QLabel#errorFecha {{ color: {theme.TEXTO_ERROR}; font-size: 12px; font-weight: 600; }}
            QPushButton#guardarFecha {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 10px;
            }}
            QPushButton#guardarFecha:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QPushButton#guardarFecha:disabled {{
                background-color: {theme.AZUL_BORDE}; color: {theme.TEXTO_SECUNDARIO};
            }}
            QPushButton#quitarFecha {{
                background-color: transparent; color: {theme.TEXTO_ERROR};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.TEXTO_ERROR}; border-radius: 8px; padding: 9px;
            }}
            QPushButton#cancelarFecha {{
                background-color: transparent; color: {theme.TEXTO_PRINCIPAL};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 9px;
            }}
        """)
