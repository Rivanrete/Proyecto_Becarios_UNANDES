"""Diálogo para crear un informe del acta — pide N° de acta y nombre de archivo.

Sigue el estándar UX del proyecto: hereda DialogoBase (frameless), se
muestra con overlay y valida en línea con lbl_error (sin QMessageBox).
El nombre se sugiere como Acta_N{numero}_{gestion} y queda editable.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.services import gestion_service, informe_service
from app.ui import theme
from app.ui.dialogo_base import DialogoBase


class DialogoNuevoInforme(DialogoBase):
    """Modal pequeño: N° de acta + nombre de archivo editable."""

    def __init__(self, parent=None):
        super().__init__(parent, modal=True)
        self.setWindowTitle("UNANDES • Nuevo informe")
        self.numero_acta = ""
        self.nombre_archivo = ""
        try:
            self._gestion = gestion_service.obtener_gestion_predeterminada()
        except Exception:
            self._gestion = ""
        self._build_ui()
        self._apply_style()
        self._actualizar_sugerencia()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(24, 24, 24, 24)

        card = QFrame(self)
        card.setObjectName("cardInforme")
        card.setMinimumWidth(380)
        card.setMaximumWidth(480)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 28, 32, 28)

        encabezado = QHBoxLayout()
        titulo = QLabel("Crear nuevo informe", card)
        titulo.setObjectName("tituloInforme")
        encabezado.addWidget(titulo)
        encabezado.addStretch(1)
        encabezado.addWidget(self.crear_boton_x(card))
        layout.addLayout(encabezado)

        layout.addWidget(QLabel("N° de Acta", card))
        self.txt_numero = QLineEdit(card)
        self.txt_numero.setPlaceholderText("Ej: 4")
        self.txt_numero.textChanged.connect(lambda _t: self._actualizar_sugerencia())
        layout.addWidget(self.txt_numero)

        layout.addWidget(QLabel("Nombre del archivo", card))
        self.txt_nombre = QLineEdit(card)
        layout.addWidget(self.txt_nombre)

        self.lbl_error = QLabel("", card)
        self.lbl_error.setObjectName("errorInforme")
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        self.btn_crear = QPushButton("Crear informe", card)
        self.btn_crear.setObjectName("crearInforme")
        self.btn_crear.setDefault(True)
        self.btn_crear.clicked.connect(self._on_crear)
        layout.addWidget(self.btn_crear)

        self.btn_cancelar = QPushButton("Cancelar", card)
        self.btn_cancelar.setObjectName("cancelarInforme")
        self.btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancelar)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _actualizar_sugerencia(self):
        """Regenera el nombre sugerido al cambiar el número (conserva edición manual)."""
        actual = self.txt_nombre.text().strip()
        sugerido_previo = getattr(self, "_ultima_sugerencia", "")
        nuevo = informe_service.sugerir_nombre_acta(
            self.txt_numero.text().strip(), self._gestion)
        if not actual or actual == sugerido_previo:
            self.txt_nombre.setText(nuevo)
        self._ultima_sugerencia = nuevo

    def _on_crear(self):
        numero = self.txt_numero.text().strip()
        nombre = self.txt_nombre.text().strip()
        if not numero:
            self.lbl_error.setText("Ingrese el N° de Acta.")
            return
        if not nombre:
            self.lbl_error.setText("Ingrese el nombre del archivo.")
            return
        self.numero_acta = numero
        self.nombre_archivo = nombre if nombre.lower().endswith(".docx") else nombre + ".docx"
        self.accept()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QFrame#cardInforme {{
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 16px;
            }}
            QLabel#tituloInforme {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 16px; font-weight: 800; }}
            QLabel {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 13px; font-weight: 600; }}
            QToolButton#cerrar {{
                color: {theme.TEXTO_SECUNDARIO}; font-size: 14px; font-weight: 700;
                background: transparent; border: none; padding: 4px 8px;
            }}
            QToolButton#cerrar:hover {{ color: {theme.TEXTO_ERROR}; }}
            QLineEdit {{
                background-color: {theme.AZUL_FONDO}; color: {theme.TEXTO_PRINCIPAL};
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
                font-size: 13px;
            }}
            QLabel#errorInforme {{ color: {theme.TEXTO_ERROR}; font-size: 12px; font-weight: 600; }}
            QPushButton#crearInforme {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 11px;
            }}
            QPushButton#crearInforme:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QPushButton#cancelarInforme {{
                background-color: transparent; color: {theme.TEXTO_PRINCIPAL};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
            }}
        """)
