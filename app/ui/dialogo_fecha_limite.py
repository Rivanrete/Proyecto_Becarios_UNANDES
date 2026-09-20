"""Diálogo para definir la fecha límite de requisitos — la fija la Lic. a mano.

Sigue el estándar UX del proyecto: hereda DialogoBase (frameless), se
muestra con overlay y valida en línea con lbl_error (sin QMessageBox).
Guardar devuelve la fecha ISO; "Quitar fecha" la deja sin límite.
"""
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.ui import theme
from app.ui.dialogo_base import DialogoBase


class DialogoFechaLimite(DialogoBase):
    """Modal pequeño: muestra la vigente (o "Sin fecha límite") y edita."""

    def __init__(self, parent=None, fecha_actual: str | None = None):
        super().__init__(parent, modal=True)
        self.setWindowTitle("UNANDES • Fecha límite")
        self.fecha_iso: str | None = None
        self._quitar = False
        self._vigente = (fecha_actual or "").strip() or None
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(24, 24, 24, 24)

        card = QFrame(self)
        card.setObjectName("cardFecha")
        card.setMinimumWidth(360)
        card.setMaximumWidth(440)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 28, 32, 28)

        encabezado = QHBoxLayout()
        titulo = QLabel("Fecha límite de requisitos", card)
        titulo.setObjectName("tituloFecha")
        encabezado.addWidget(titulo)
        encabezado.addStretch(1)
        encabezado.addWidget(self.crear_boton_x(card))
        layout.addLayout(encabezado)

        vigente = QLabel(
            f"Vigente: {self._vigente}" if self._vigente else "Sin fecha límite", card)
        vigente.setObjectName("vigenteFecha")
        vigente.setWordWrap(True)
        layout.addWidget(vigente)

        self.calendario = QDateEdit(card)
        self.calendario.setCalendarPopup(True)
        self.calendario.setDisplayFormat("yyyy-MM-dd")
        if self._vigente:
            actual = QDate.fromString(self._vigente, "yyyy-MM-dd")
            self.calendario.setDate(actual if actual.isValid() else QDate.currentDate())
        else:
            self.calendario.setDate(QDate.currentDate())
        layout.addWidget(self.calendario)

        self.lbl_error = QLabel("", card)
        self.lbl_error.setObjectName("errorFecha")
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        self.btn_guardar = QPushButton("Guardar fecha", card)
        self.btn_guardar.setObjectName("guardarFecha")
        self.btn_guardar.setDefault(True)
        self.btn_guardar.clicked.connect(self._on_guardar)
        layout.addWidget(self.btn_guardar)

        self.btn_quitar = QPushButton("Quitar fecha", card)
        self.btn_quitar.setObjectName("quitarFecha")
        self.btn_quitar.clicked.connect(self._on_quitar)
        layout.addWidget(self.btn_quitar)

        self.btn_cancelar = QPushButton("Cancelar", card)
        self.btn_cancelar.setObjectName("cancelarFecha")
        self.btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancelar)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _on_guardar(self):
        self.fecha_iso = self.calendario.date().toString("yyyy-MM-dd")
        self._quitar = False
        self.accept()

    def _on_quitar(self):
        self.fecha_iso = None
        self._quitar = True
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
            QDateEdit {{
                background-color: {theme.AZUL_CAMPO}; color: {theme.TEXTO_PRINCIPAL};
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
                font-size: 13px;
            }}
            QLabel#errorFecha {{ color: {theme.TEXTO_ERROR}; font-size: 12px; font-weight: 600; }}
            QPushButton#guardarFecha {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 11px;
            }}
            QPushButton#guardarFecha:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QPushButton#quitarFecha {{
                background-color: transparent; color: {theme.TEXTO_ERROR};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.TEXTO_ERROR}; border-radius: 8px; padding: 10px;
            }}
            QPushButton#cancelarFecha {{
                background-color: transparent; color: {theme.TEXTO_PRINCIPAL};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
            }}
        """)
