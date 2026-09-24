from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from app.ui import overlay, theme
from app.ui.dialogo_base import DialogoBase


class DialogoMensaje(DialogoBase):

    def __init__(self, parent=None, mensaje: str = "", tipo: str = "exito"):
        super().__init__(parent, modal=True)
        self.setWindowTitle("UNANDES • Aviso")
        self._tipo = tipo if tipo in ("exito", "error") else "exito"
        self._build_ui(mensaje)
        self._apply_style()

    def _build_ui(self, mensaje: str):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(24, 24, 24, 24)

        card = QFrame(self)
        card.setObjectName("cardMensaje")
        card.setMinimumWidth(320)
        card.setMaximumWidth(440)
        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(32, 28, 32, 28)

        encabezado = QHBoxLayout()
        encabezado.addStretch(1)
        encabezado.addWidget(self.crear_boton_x(card))
        layout.addLayout(encabezado)

        icono = QLabel("✓" if self._tipo == "exito" else "✕", card)
        icono.setObjectName("iconoExito" if self._tipo == "exito" else "iconoError")
        icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icono)

        texto = QLabel(mensaje, card)
        texto.setObjectName("textoMensaje")
        texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        texto.setWordWrap(True)
        layout.addWidget(texto)

        self.btn_aceptar = QPushButton("Aceptar", card)
        self.btn_aceptar.setObjectName(
            "aceptarExito" if self._tipo == "exito" else "aceptarError"
        )
        self.btn_aceptar.setDefault(True)
        self.btn_aceptar.clicked.connect(self.accept)
        layout.addWidget(self.btn_aceptar)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QFrame#cardMensaje {{
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 16px;
            }}
            QLabel#iconoExito {{ color: {theme.VERDE_LIMA}; font-size: 34px; font-weight: 800; }}
            QLabel#iconoError {{ color: {theme.TEXTO_ERROR}; font-size: 34px; font-weight: 800; }}
            QToolButton#cerrar {{
                color: {theme.TEXTO_SECUNDARIO}; font-size: 14px; font-weight: 700;
                background: transparent; border: none; padding: 4px 8px;
            }}
            QToolButton#cerrar:hover {{ color: {theme.TEXTO_ERROR}; }}
            QLabel#textoMensaje {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 14px; font-weight: 600; }}
            QPushButton#aceptarExito {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 11px;
            }}
            QPushButton#aceptarExito:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QPushButton#aceptarError {{
                background-color: {theme.TEXTO_ERROR}; color: #ffffff;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 11px;
            }}
        """)


def mostrar_notificacion(panel, mensaje: str, tipo: str = "exito"):
    dialogo = DialogoMensaje(panel, mensaje=mensaje, tipo=tipo)
    return overlay.ejecutar_con_overlay(panel, dialogo)


class DialogoConfirmacion(DialogoBase):

    def __init__(self, parent=None, mensaje: str = ""):
        super().__init__(parent, modal=True)
        self.setWindowTitle("UNANDES • Confirmar")
        self._build_ui(mensaje)
        self._apply_style()

    def _build_ui(self, mensaje: str):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(24, 24, 24, 24)

        card = QFrame(self)
        card.setObjectName("cardMensaje")
        card.setMinimumWidth(320)
        card.setMaximumWidth(440)
        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(32, 28, 32, 28)

        encabezado = QHBoxLayout()
        encabezado.addStretch(1)
        encabezado.addWidget(self.crear_boton_x(card))
        layout.addLayout(encabezado)

        icono = QLabel("⚠", card)
        icono.setObjectName("iconoAlerta")
        icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icono)

        texto = QLabel(mensaje, card)
        texto.setObjectName("textoMensaje")
        texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        texto.setWordWrap(True)
        layout.addWidget(texto)

        self.btn_eliminar = QPushButton("Eliminar", card)
        self.btn_eliminar.setObjectName("aceptarError")
        self.btn_eliminar.setDefault(True)
        self.btn_eliminar.clicked.connect(self.accept)
        layout.addWidget(self.btn_eliminar)

        self.btn_cancelar = QPushButton("Cancelar", card)
        self.btn_cancelar.setObjectName("cancelarMensaje")
        self.btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancelar)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QFrame#cardMensaje {{
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 16px;
            }}
            QLabel#iconoAlerta {{ color: {theme.TEXTO_ERROR}; font-size: 34px; font-weight: 800; }}
            QLabel#textoMensaje {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 14px; font-weight: 600; }}
            QToolButton#cerrar {{
                color: {theme.TEXTO_SECUNDARIO}; font-size: 14px; font-weight: 700;
                background: transparent; border: none; padding: 4px 8px;
            }}
            QToolButton#cerrar:hover {{ color: {theme.TEXTO_ERROR}; }}
            QPushButton#aceptarError {{
                background-color: {theme.TEXTO_ERROR}; color: #ffffff;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 11px;
            }}
            QPushButton#cancelarMensaje {{
                background-color: transparent; color: {theme.TEXTO_PRINCIPAL};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
            }}
        """)


def pedir_confirmacion(panel, mensaje: str) -> bool:
    dialogo = DialogoConfirmacion(panel, mensaje=mensaje)
    return overlay.ejecutar_con_overlay(panel, dialogo) == QDialog.DialogCode.Accepted
