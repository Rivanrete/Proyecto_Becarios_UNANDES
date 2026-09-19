"""Base de todos los popups del sistema (estándar UX).

Toda ventana emergente hereda de aquí y por tanto:
- Sin marco nativo (frameless) + fondo transparente.
- Se cierra con su botón X (ver crear_boton_x), con clic fuera
  (lo gestiona overlay) y con Esc (comportamiento Qt de QDialog).
No reinventar esto por ventana: extender esta base.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QToolButton


class DialogoBase(QDialog):
    def __init__(self, parent=None, modal: bool = False):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(modal)

    def crear_boton_x(self, padre) -> QToolButton:
        """X propia (objectName 'cerrar'): cada diálogo la ubica en su layout."""
        boton = QToolButton(padre)
        boton.setObjectName("cerrar")
        boton.setText("✕")
        boton.setToolTip("Cerrar")
        boton.clicked.connect(self.reject)
        return boton
