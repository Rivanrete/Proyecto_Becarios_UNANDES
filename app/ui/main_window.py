from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton

from app.models.usuario import Usuario
from app.services.auth_service import SesionActual
from app.ui import theme


class MainWindow(QMainWindow):
    def __init__(self, usuario: Usuario | None, parent=None):
        if usuario is None or not SesionActual.activa():
            raise PermissionError("Acceso denegado: debe iniciar sesión primero (HU-01).")
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle("UNANDES • Registro de Becarios — Principal")
        self.setMinimumSize(640, 420)
        self._build_ui()

    def _build_ui(self):
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titulo = QLabel(f"Sesión iniciada como: {self.usuario.nombre_usuario}")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nota = QLabel("Pantalla principal (placeholder HU-01).\nAquí irá el registro y consulta de becarios en las siguientes HU.")
        nota.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_salir = QPushButton("Cerrar sesión")
        btn_salir.clicked.connect(self._cerrar_sesion)

        layout.addWidget(titulo)
        layout.addWidget(nota)
        layout.addWidget(btn_salir, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(central)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {theme.FONDO_TRABAJO}; }}
            QLabel {{ color: {theme.TEXTO_OSCURO}; font-size: 14px; }}
            QPushButton {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-weight: 700; border: none; border-radius: 8px; padding: 10px 24px;
            }}
            QPushButton:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
        """)

    def _cerrar_sesion(self):
        SesionActual.cerrar()
        self.close()
