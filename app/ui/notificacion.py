"""Notificaciones propias del sistema — reemplazo de QMessageBox.

REGLA DE PROYECTO: prohibidos los diálogos nativos del SO. Usar
mostrar_notificacion(panel, mensaje, tipo) en confirmaciones, alertas
y avisos de todas las HU. Mismo overlay, paleta y animación que el
resto de modales.

Tipos: "exito" (acento lima, ✓) y "error" (acento rojo, ✕).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QLabel, QPushButton, QVBoxLayout

from app.ui import overlay, theme


class DialogoMensaje(QDialog):
    """Modal pequeño sin marco nativo: tarjeta, mensaje y botón propio."""

    def __init__(self, parent=None, mensaje: str = "", tipo: str = "exito"):
        super().__init__(parent)
        self.setWindowTitle("UNANDES • Aviso")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
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
    """Muestra la notificación centrada sobre el panel (overlay + animación).

    Retorna el código de resultado del diálogo.
    """
    dialogo = DialogoMensaje(panel, mensaje=mensaje, tipo=tipo)
    return overlay.ejecutar_con_overlay(panel, dialogo)
