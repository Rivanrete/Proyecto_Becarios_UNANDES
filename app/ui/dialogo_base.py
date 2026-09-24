from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QToolButton


class DialogoBase(QDialog):
    def __init__(self, parent=None, modal: bool = False):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(modal)

    def crear_boton_x(self, padre) -> QToolButton:
        boton = QToolButton(padre)
        boton.setObjectName("cerrar")
        boton.setText("✕")
        boton.setToolTip("Cerrar")
        boton.clicked.connect(self.reject)
        return boton
