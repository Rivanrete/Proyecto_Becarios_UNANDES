from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.ui import theme
from app.ui.dialogo_base import DialogoBase


class DialogoCambioGestion(DialogoBase):
    def __init__(self, parent=None, anterior: str = "", nueva: str = "",
                 respaldados: int = 0, reiniciados: int = 0,
                 sin_modificar: int = 0):
        super().__init__(parent, modal=True)
        self.setWindowTitle("UNANDES • Cambio de gestión")
        self._build_ui(anterior, nueva, respaldados, reiniciados, sin_modificar)
        self._apply_style()

    def _build_ui(self, anterior: str, nueva: str, respaldados: int,
                  reiniciados: int, sin_modificar: int):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(24, 24, 24, 24)

        card = QFrame(self)
        card.setObjectName("cardMensaje")
        card.setMinimumWidth(360)
        card.setMaximumWidth(480)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(32, 24, 32, 28)

        encabezado = QHBoxLayout()
        encabezado.addStretch(1)
        encabezado.addWidget(self.crear_boton_x(card))
        layout.addLayout(encabezado)

        titulo = QLabel("Cambio de gestión", card)
        titulo.setObjectName("tituloMensaje")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        transicion = QLabel(f"{anterior} -> {nueva}", card)
        transicion.setObjectName("transicionMensaje")
        transicion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(transicion)

        lineas = [
            f"Se guardaron {respaldados} becarios en el respaldo de la gestión {anterior}.",
            f"Se reiniciaron {reiniciados} becarios "
            "(horas, carpeta y carta a \u00abNo\u00bb, estado a \u00abEn renovaci\u00f3n\u00bb).",
        ]
        if sin_modificar > 0:
            lineas.append(
                f"{sin_modificar} becario(s) en Baja/Inactivo no se modificaron.")
        lineas.append("El respaldo qued\u00f3 disponible en la ventana Respaldos.")
        for texto in lineas:
            linea = QLabel(texto, card)
            linea.setObjectName("textoMensaje")
            linea.setAlignment(Qt.AlignmentFlag.AlignCenter)
            linea.setWordWrap(True)
            layout.addWidget(linea)

        self.btn_entendido = QPushButton("Entendido", card)
        self.btn_entendido.setObjectName("aceptarExito")
        self.btn_entendido.setDefault(True)
        self.btn_entendido.clicked.connect(self.accept)
        layout.addWidget(self.btn_entendido)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QFrame#cardMensaje {{
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 16px;
            }}
            QToolButton#cerrar {{
                color: {theme.TEXTO_SECUNDARIO}; font-size: 14px; font-weight: 700;
                background: transparent; border: none; padding: 4px 8px;
            }}
            QToolButton#cerrar:hover {{ color: {theme.TEXTO_ERROR}; }}
            QLabel#tituloMensaje {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 18px; font-weight: 800; }}
            QLabel#transicionMensaje {{ color: {theme.VERDE_LIMA}; font-size: 15px; font-weight: 800; }}
            QLabel#textoMensaje {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 13px; font-weight: 600; }}
            QPushButton#aceptarExito {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 11px;
            }}
            QPushButton#aceptarExito:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
        """)
