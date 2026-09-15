"""Ventana de login — HU-01.

Solo UI: captura usuario/contraseña y delega a validar_credenciales().
NO contiene reglas de validación.

Incluye (y solo esto):
- campo usuario, campo contraseña con mostrar/ocultar,
  botón "Iniciar Sesión", mensaje de error inline.
Excluye deliberadamente (fuera de alcance HU-01):
- indicador de servidor, periodo académico, recordar sesión, ¿olvidó su clave?
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QFrame,
)

from app.services import auth_service
from app.ui import theme


class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UNANDES • Registro de Becarios — Iniciar sesión")
        self.setMinimumSize(460, 560)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(12)

        card = QFrame(self)
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(28, 28, 28, 28)

        # Logo placeholder (la HU no exige logo real; solo referencia de estilo).
        logo = QLabel("UNANDES", card)
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titulo = QLabel("Bienestar Estudiantil", card)
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitulo = QLabel("Control y Seguimiento de Becarios", card)
        subtitulo.setObjectName("subtitulo")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_usuario = QLabel("USUARIO", card)
        lbl_usuario.setObjectName("etiqueta")
        self.txt_usuario = QLineEdit(card)
        self.txt_usuario.setPlaceholderText("Ej. bienestar")
        self.txt_usuario.setClearButtonEnabled(True)

        lbl_clave = QLabel("CONTRASEÑA", card)
        lbl_clave.setObjectName("etiqueta")

        fila_clave = QHBoxLayout()
        fila_clave.setSpacing(0)
        self.txt_clave = QLineEdit(card)
        self.txt_clave.setPlaceholderText("Ingrese su contraseña")
        self.txt_clave.setEchoMode(QLineEdit.EchoMode.Password)
        self.btn_mostrar = QToolButton(card)
        self.btn_mostrar.setObjectName("mostrar")
        self.btn_mostrar.setText("👁")
        self.btn_mostrar.setCheckable(True)
        self.btn_mostrar.setToolTip("Mostrar / ocultar contraseña")
        self.btn_mostrar.toggled.connect(self._alternar_clave)
        fila_clave.addWidget(self.txt_clave, 1)
        fila_clave.addWidget(self.btn_mostrar)

        # Mensaje de error inline (CA-5). Oculto hasta que falla un intento.
        self.lbl_error = QLabel("", card)
        self.lbl_error.setObjectName("error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setVisible(False)

        self.btn_login = QPushButton("Iniciar Sesión  →", card)
        self.btn_login.setObjectName("login")
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self._on_login)

        pie = QLabel("Universidad de los Andes • Bienestar Estudiantil", card)
        pie.setObjectName("pie")
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for w in (logo, titulo, subtitulo, lbl_usuario, self.txt_usuario,
                  lbl_clave, self.lbl_error, self.btn_login, pie):
            if isinstance(w, QHBoxLayout):
                continue
            card_layout.addWidget(w)
        card_layout.insertLayout(6, fila_clave)

        root.addWidget(card)
        self.txt_usuario.returnPressed.connect(self._on_login)
        self.txt_clave.returnPressed.connect(self._on_login)

    def _alternar_clave(self, mostrar: bool):
        self.txt_clave.setEchoMode(
            QLineEdit.EchoMode.Normal if mostrar else QLineEdit.EchoMode.Password
        )

    def _on_login(self):
        """Delegación total a la capa de negocio. Sin validación en la UI."""
        self.lbl_error.setVisible(False)
        usuario = auth_service.validar_credenciales(
            self.txt_usuario.text(), self.txt_clave.text()
        )
        if usuario is not None:
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
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 12px;
            }}
            QLabel#logo {{
                color: {theme.TEXTO_PRINCIPAL}; font-size: 22px; font-weight: 800;
                letter-spacing: 2px;
            }}
            QLabel#titulo {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 24px; font-weight: 800; }}
            QLabel#subtitulo {{ color: {theme.VERDE_TEXTO}; font-size: 13px; font-weight: 600; }}
            QLabel#etiqueta {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
            QLineEdit {{
                background-color: {theme.AZUL_CAMPO}; color: {theme.TEXTO_PRINCIPAL};
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border: 1px solid {theme.VERDE_LIMA}; }}
            QToolButton#mostrar {{
                background-color: {theme.AZUL_CAMPO}; color: {theme.TEXTO_SECUNDARIO};
                border: 1px solid {theme.AZUL_BORDE}; border-left: none;
                border-top-right-radius: 8px; border-bottom-right-radius: 8px;
                padding: 10px;
            }}
            QLabel#error {{ color: {theme.TEXTO_ERROR}; font-size: 12px; font-weight: 600; }}
            QPushButton#login {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 15px; font-weight: 800; border: none;
                border-radius: 8px; padding: 12px;
            }}
            QPushButton#login:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QLabel#pie {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 11px; }}
        """)
