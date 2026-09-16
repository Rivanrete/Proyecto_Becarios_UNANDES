"""Ventana de login — HU-01 (tarjeta blanca, maximizada, escudo, recordar usuario).

Solo UI: captura usuario/contraseña y delega a validar_credenciales().
NO contiene reglas de validación.

"Recordar usuario" solo pre-rellena el nombre de usuario (QSettings
local). NO guarda la contraseña ni mantiene sesión.
"""
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QSettings
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from app.services import auth_service
from app.ui import theme

ORG = "UNANDES"
APP = "RegistroBecarios"
KEY_USUARIO = "usuario_recordado"
_DIR_ASSETS = Path(__file__).resolve().parents[1] / "assets"


def _ruta_escudo() -> Path | None:
    """Retorna la ruta del escudo si existe (.png, .jpg o .jpeg), o None."""
    for nombre in ("escudo_unandes.png", "escudo_unandes.jpg", "escudo_unandes.jpeg"):
        ruta = _DIR_ASSETS / nombre
        try:
            if ruta.is_file():
                return ruta
        except OSError:
            continue
    return None


# Ojo abierto / cerrado estilo outline monocromático (SVG en línea, sin
# librerías externas; se renderiza con QtSvg del propio PySide6).
# Color = texto secundario de la paleta sobre la tarjeta.
_COLOR_OJO = "#b9c2d8"
_OJO_ABIERTO = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"'
    ' viewBox="0 0 24 24" fill="none" stroke="' + _COLOR_OJO + '"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>'
    '<circle cx="12" cy="12" r="3"/></svg>'
)
_OJO_CERRADO = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"'
    ' viewBox="0 0 24 24" fill="none" stroke="' + _COLOR_OJO + '"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8'
    'a18.45 18.45 0 0 1 5.06-5.94"/>'
    '<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8'
    'a18.5 18.5 0 0 1-2.16 3.19"/>'
    '<path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>'
    '<line x1="1" y1="1" x2="23" y2="23"/></svg>'
)


def _icono_ojo(abierto: bool) -> QIcon:
    """Renderiza el SVG del ojo a QIcon (24px, monocromático de paleta)."""
    renderer = QSvgRenderer(bytearray((_OJO_ABIERTO if abierto else _OJO_CERRADO).encode("utf-8")))
    imagen = QImage(24, 24, QImage.Format.Format_ARGB32)
    imagen.fill(0)
    pintor = QPainter(imagen)
    try:
        renderer.render(pintor)
    finally:
        pintor.end()
    return QIcon(QPixmap.fromImage(imagen))


class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UNANDES • Registro de Becarios — Iniciar sesión")
        # Controles nativos de ventana (minimizar, maximizar/restaurar, cerrar).
        # Necesarios porque la ventana abre maximizada.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(480, 620)
        self._maximizado_aplicado = False
        self.settings = QSettings(ORG, APP)
        self._build_ui()
        self._apply_style()
        self._cargar_usuario_recordado()

    def showEvent(self, event):
        """Abre maximizada (respeta la barra de tareas).

        Se fuerza aquí porque el estado fijado en __init__ se pierde
        en diálogos modales cuando exec() re-muestra la ventana.
        Se usa showMaximized(), NO showFullScreen(), para no tapar
        la barra de tareas de Windows.
        """
        super().showEvent(event)
        if not self._maximizado_aplicado:
            self._maximizado_aplicado = True
            self.showMaximized()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(48, 40, 48, 40)
        root.setSpacing(16)

        card = QFrame(self)
        card.setObjectName("card")
        card.setMinimumWidth(440)
        card.setMaximumWidth(520)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(40, 36, 40, 36)

        # Escudo UNANDES centrado arriba. Si el archivo falta, el espacio
        # queda vacío: nunca rompe la app ni muestra texto de error.
        self.lbl_escudo = QLabel(card)
        self.lbl_escudo.setObjectName("escudo")
        self.lbl_escudo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_escudo.setFixedHeight(120)
        try:
            ruta = _ruta_escudo()
            pix = QPixmap(str(ruta)) if ruta is not None else QPixmap()
            if not pix.isNull():
                self.lbl_escudo.setPixmap(
                    pix.scaledToHeight(120, Qt.TransformationMode.SmoothTransformation)
                )
        except Exception:
            pass
        card_layout.addWidget(self.lbl_escudo)

        titulo = QLabel("Bienestar Estudiantil", card)
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(titulo)

        subtitulo = QLabel("Control y Seguimiento de Becarios", card)
        subtitulo.setObjectName("subtitulo")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitulo)

        card_layout.addSpacing(8)

        lbl_usuario = QLabel("USUARIO", card)
        lbl_usuario.setObjectName("etiqueta")
        card_layout.addWidget(lbl_usuario)

        self.txt_usuario = QLineEdit(card)
        self.txt_usuario.setPlaceholderText("Ej. prueba")
        self.txt_usuario.setClearButtonEnabled(True)
        card_layout.addWidget(self.txt_usuario)

        lbl_clave = QLabel("CONTRASEÑA", card)
        lbl_clave.setObjectName("etiqueta")
        card_layout.addWidget(lbl_clave)

        fila_clave = QHBoxLayout()
        fila_clave.setSpacing(0)
        self.txt_clave = QLineEdit(card)
        self.txt_clave.setPlaceholderText("Ingrese su contraseña")
        self.txt_clave.setEchoMode(QLineEdit.EchoMode.Password)
        self.btn_mostrar = QToolButton(card)
        self.btn_mostrar.setObjectName("mostrar")
        self.btn_mostrar.setIcon(_icono_ojo(True))
        self.btn_mostrar.setIconSize(QSize(20, 20))
        self.btn_mostrar.setCheckable(True)
        self.btn_mostrar.setToolTip("Mostrar / ocultar contraseña")
        self.btn_mostrar.toggled.connect(self._alternar_clave)
        fila_clave.addWidget(self.txt_clave, 1)
        fila_clave.addWidget(self.btn_mostrar)
        card_layout.addLayout(fila_clave)

        # Mensaje de error inline (CA-5). Oculto hasta que falla un intento.
        self.lbl_error = QLabel("", card)
        self.lbl_error.setObjectName("error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setVisible(False)
        card_layout.addWidget(self.lbl_error)

        self.chk_recordar = QCheckBox("Recordar usuario en este equipo", card)
        self.chk_recordar.setObjectName("recordar")
        card_layout.addWidget(self.chk_recordar)

        card_layout.addSpacing(4)

        self.btn_login = QPushButton("Iniciar Sesión  →", card)
        self.btn_login.setObjectName("login")
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self._on_login)
        card_layout.addWidget(self.btn_login)

        card_layout.addSpacing(4)

        pie = QLabel("Universidad de los Andes • Bienestar Estudiantil", card)
        pie.setObjectName("pie")
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(pie)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        self.txt_usuario.returnPressed.connect(self._on_login)
        self.txt_clave.returnPressed.connect(self._on_login)

    def _cargar_usuario_recordado(self):
        recordado = (self.settings.value(KEY_USUARIO, "") or "").strip()
        if recordado:
            self.txt_usuario.setText(recordado)
            self.chk_recordar.setChecked(True)
            self.txt_clave.setFocus()
        else:
            self.txt_usuario.setFocus()

    def _alternar_clave(self, mostrar: bool):
        self.txt_clave.setEchoMode(
            QLineEdit.EchoMode.Normal if mostrar else QLineEdit.EchoMode.Password
        )
        self.btn_mostrar.setIcon(_icono_ojo(not mostrar))

    def _on_login(self):
        """Delegación total a la capa de negocio. Sin validación en la UI."""
        self.lbl_error.setVisible(False)
        usuario = auth_service.validar_credenciales(
            self.txt_usuario.text(), self.txt_clave.text()
        )
        if usuario is not None:
            if self.chk_recordar.isChecked():
                self.settings.setValue(KEY_USUARIO, usuario.nombre_usuario)
            else:
                self.settings.remove(KEY_USUARIO)
            self.accept()  # main.py abrirá la pantalla principal
        else:
            self.lbl_error.setText("Usuario o contraseña incorrectos. Intente nuevamente.")
            self.lbl_error.setVisible(True)
            self.txt_clave.clear()
            self.txt_clave.setFocus()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme.AZUL_FONDO}; }}
            QFrame#card {{
                background-color: {theme.BLANCO_TARJETA};
                border: 1px solid #e5e7eb;
                border-radius: 16px;
            }}
            QLabel#titulo {{ color: {theme.TEXTO_OSCURO}; font-size: 26px; font-weight: 800; }}
            QLabel#subtitulo {{ color: {theme.VERDE_OSCURO}; font-size: 14px; font-weight: 600; }}
            QLabel#etiqueta {{ color: {theme.TEXTO_GRIS}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
            QLineEdit {{
                background-color: {theme.CAMPO_FONDO}; color: {theme.TEXTO_OSCURO};
                border: 1px solid {theme.BORDE_SUAVE}; border-radius: 8px; padding: 11px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border: 1px solid {theme.VERDE_OSCURO}; }}
            QToolButton#mostrar {{
                background-color: {theme.CAMPO_FONDO}; color: {theme.TEXTO_GRIS};
                border: 1px solid {theme.BORDE_SUAVE}; border-left: none;
                border-top-right-radius: 8px; border-bottom-right-radius: 8px;
                padding: 11px;
            }}
            QLabel#error {{ color: {theme.TEXTO_ERROR_CLARO}; font-size: 12px; font-weight: 600; }}
            QCheckBox#recordar {{ color: {theme.TEXTO_GRIS}; font-size: 12px; }}
            QCheckBox#recordar::indicator {{ width: 16px; height: 16px; }}
            QPushButton#login {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 15px; font-weight: 800; border: none;
                border-radius: 8px; padding: 13px;
            }}
            QPushButton#login:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QLabel#pie {{ color: {theme.TEXTO_GRIS_SUAVE}; font-size: 11px; }}
        """)
