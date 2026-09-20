"""Historial de gestiones — ventana lateral de solo lectura.

Lista las gestiones registradas en seguimiento_becario para un becario,
de la primera a la más reciente. Sin lógica: recibe la lista ya armada
por becario_service.historial_gestiones(). Mismo lenguaje visual
(frameless, tarjeta azul, overlay + animación del llamador).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QVBoxLayout,
)

from app.ui import theme
from app.ui.dialogo_base import DialogoBase


class HistorialGestionesWindow(DialogoBase):
    def __init__(self, parent=None, gestiones: list | None = None):
        # Sin marco nativo: ver DialogoBase (frameless, no modal).
        super().__init__(parent, modal=False)
        self.setWindowTitle("Historial de gestiones")
        self._build_ui(gestiones or [])
        self._apply_style()

    def _build_ui(self, gestiones: list):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Mismos márgenes que el formulario: con igual alto de tarjeta,
        # los bordes superior e inferior quedan pixel a pixel alineados.
        root.setContentsMargins(40, 32, 40, 32)

        card = QFrame(self)
        card.setObjectName("cardHistorial")
        card.setFixedWidth(280)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 24, 24, 24)

        encabezado = QHBoxLayout()
        encabezado.addStretch(1)
        encabezado.addWidget(self.crear_boton_x(card))
        layout.addLayout(encabezado)

        subtitulo = QLabel("Historial de gestiones", card)
        subtitulo.setObjectName("subHist")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitulo)

        self.lista = QListWidget(card)
        self.lista.setObjectName("listaHist")
        if gestiones:
            self.lista.addItems(gestiones)
        else:
            self.lista.addItem("Sin gestiones registradas")
        layout.addWidget(self.lista)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QFrame#cardHistorial {{
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 16px;
            }}
            QLabel#subHist {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 12px; }}
            QToolButton#cerrar {{
                color: {theme.TEXTO_SECUNDARIO}; font-size: 14px; font-weight: 700;
                background: transparent; border: none; padding: 4px 8px;
            }}
            QToolButton#cerrar:hover {{ color: {theme.TEXTO_ERROR}; }}
            QListWidget#listaHist {{
                background-color: {theme.AZUL_TARJETA}; color: {theme.TEXTO_PRINCIPAL};
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px;
                font-size: 13px; padding: 6px;
            }}
            QListWidget#listaHist::item {{
                color: {theme.TEXTO_PRINCIPAL}; background-color: transparent; padding: 6px;
            }}
            QListWidget#listaHist::item:selected {{
                background-color: rgba(140,184,44,0.25); color: {theme.TEXTO_PRINCIPAL};
            }}
        """)
