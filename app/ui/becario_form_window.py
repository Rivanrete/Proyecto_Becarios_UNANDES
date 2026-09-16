"""Formulario Nuevo / Editar Becario — HU-02 (un solo formulario, no wizard).

Se muestra como modal INTEGRADO al Panel de Control: QDialog sin marco
nativo (FramelessWindowHint) con fondo transparente; solo se pinta la
tarjeta. Quien lo instancia (main._abrir_formulario) pone detrás un
overlay semitransparente sobre la ventana principal y centra el diálogo.
Sin barra de título del SO; el cierre va en la ✕ propia y en "Cancelar"
(o tecla Esc).

Modo "nuevo": BecarioFormWindow(parent) con campos vacíos.
Modo "editar": BecarioFormWindow(parent, becario_id=...) precargado.
Toda validación y duplicados pasan por becario_service; aquí solo se
muestran (error inline estilo login, éxito con diálogo de confirmación).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from app.services import becario_service
from app.services.becario_service import BecarioDuplicadoError
from app.ui import theme


class BecarioFormWindow(QDialog):
    def __init__(self, parent=None, becario_id: int | None = None):
        super().__init__(parent)
        self.becario_id = becario_id
        # main.py lee este mensaje tras accept() y lo muestra con la
        # notificación propia del sistema (sin QMessageBox nativo).
        self.mensaje_exito: str | None = None
        self.setWindowTitle(
            "Editar Becario" if becario_id is not None else "Nuevo Becario"
        )
        # Sin marco nativo: el diálogo es un overlay sobre la ventana padre.
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumSize(800, 760)
        self._build_ui()
        self._apply_style()
        if becario_id is not None:
            self._precargar()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(40, 32, 40, 32)

        card = QFrame(self)
        card.setObjectName("card")
        card.setMinimumWidth(620)
        card.setMaximumWidth(700)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(36, 24, 36, 32)

        encabezado = QHBoxLayout()
        encabezado.addStretch(1)
        self.btn_cerrar = QToolButton(card)
        self.btn_cerrar.setObjectName("cerrar")
        self.btn_cerrar.setText("✕")
        self.btn_cerrar.setToolTip("Cerrar")
        self.btn_cerrar.clicked.connect(self.reject)
        encabezado.addWidget(self.btn_cerrar)
        layout.addLayout(encabezado)

        titulo = QLabel("Editar Becario" if self.becario_id is not None else "Nuevo Becario", card)
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        form = QFormLayout()
        form.setSpacing(10)
        self.txt_nombres = QLineEdit(card)
        self.txt_apellidos = QLineEdit(card)
        self.txt_ci = QLineEdit(card)
        self.txt_codigo = QLineEdit(card)
        self.cmb_carrera = QComboBox(card)
        for sigla, etiqueta in becario_service.opciones_carrera():
            self.cmb_carrera.addItem(etiqueta, sigla)
        self.cmb_carrera.setMaxVisibleItems(self.cmb_carrera.count())
        self.cmb_tipo = QComboBox(card)
        self.cmb_tipo.addItems(becario_service.listar_tipos_beca())
        self.cmb_tipo.setMaxVisibleItems(self.cmb_tipo.count())
        self.txt_contacto = QLineEdit(card)
        self.txt_contacto.setPlaceholderText("Teléfono o correo (opcional)")
        form.addRow("Nombres:", self.txt_nombres)
        form.addRow("Apellidos:", self.txt_apellidos)
        form.addRow("CI:", self.txt_ci)
        form.addRow("Código:", self.txt_codigo)
        form.addRow("Carrera:", self.cmb_carrera)
        form.addRow("Tipo de Beca:", self.cmb_tipo)
        form.addRow("Contacto:", self.txt_contacto)
        layout.addLayout(form)

        self.lbl_error = QLabel("", card)
        self.lbl_error.setObjectName("error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        fila_botones = QVBoxLayout()
        fila_botones.setSpacing(8)
        self.btn_guardar = QPushButton("Guardar", card)
        self.btn_guardar.setObjectName("guardar")
        self.btn_guardar.setDefault(True)
        self.btn_guardar.clicked.connect(self._on_guardar)
        self.btn_cancelar = QPushButton("Cancelar", card)
        self.btn_cancelar.setObjectName("cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        fila_botones.addWidget(self.btn_guardar)
        fila_botones.addWidget(self.btn_cancelar)
        layout.addLayout(fila_botones)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _precargar(self):
        becario = becario_service.obtener_becario(self.becario_id)
        if becario is None:
            raise ValueError("El becario no existe.")
        self.txt_nombres.setText(becario.nombres)
        self.txt_apellidos.setText(becario.apellidos)
        self.txt_ci.setText(becario.ci)
        self.txt_codigo.setText(becario.codigo_estudiante)
        indice = self.cmb_carrera.findData(becario.carrera)
        if indice >= 0:
            self.cmb_carrera.setCurrentIndex(indice)
        indice_tipo = self.cmb_tipo.findText(becario.tipo_beca)
        if indice_tipo >= 0:
            self.cmb_tipo.setCurrentIndex(indice_tipo)
        self.txt_contacto.setText(becario.contacto)

    def _datos_formulario(self) -> dict:
        return {
            "nombres": self.txt_nombres.text(),
            "apellidos": self.txt_apellidos.text(),
            "ci": self.txt_ci.text(),
            "codigo_estudiante": self.txt_codigo.text(),
            "carrera": self.cmb_carrera.currentData() or self.cmb_carrera.currentText(),
            "tipo_beca": self.cmb_tipo.currentText(),
            "contacto": self.txt_contacto.text(),
        }

    def _on_guardar(self):
        self.lbl_error.setVisible(False)
        try:
            if self.becario_id is None:
                becario_service.registrar_becario(self._datos_formulario())
                mensaje = "Becario registrado correctamente."
            else:
                becario_service.editar_becario(self.becario_id, self._datos_formulario())
                mensaje = "Becario actualizado correctamente."
        except BecarioDuplicadoError as e:
            self.lbl_error.setText(str(e) + " No se guardó el registro.")
            self.lbl_error.setVisible(True)
            return
        except ValueError as e:
            self.lbl_error.setText(str(e))
            self.lbl_error.setVisible(True)
            return
        self.mensaje_exito = mensaje
        self.accept()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QFrame#card {{
                background-color: {theme.AZUL_TARJETA};
                border: 1px solid {theme.AZUL_BORDE};
                border-radius: 16px;
            }}
            QToolButton#cerrar {{
                color: {theme.TEXTO_SECUNDARIO}; font-size: 14px; font-weight: 700;
                background: transparent; border: none; padding: 4px 8px;
            }}
            QToolButton#cerrar:hover {{ color: {theme.TEXTO_ERROR}; }}
            QLabel#titulo {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 22px; font-weight: 800; }}
            QLabel {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 13px; font-weight: 600; }}
            QLineEdit {{
                background-color: {theme.AZUL_CAMPO}; color: {theme.TEXTO_PRINCIPAL};
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
                font-size: 14px; min-height: 22px;
            }}
            QLineEdit:focus {{ border: 1px solid {theme.VERDE_LIMA}; }}
            QComboBox {{
                background-color: {theme.AZUL_CAMPO}; color: {theme.TEXTO_PRINCIPAL};
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px;
                padding: 10px 34px 10px 12px;
                font-size: 14px; min-height: 22px;
            }}
            QComboBox:focus {{ border: 1px solid {theme.VERDE_LIMA}; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px; border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.AZUL_CAMPO}; color: {theme.TEXTO_PRINCIPAL};
                selection-background-color: {theme.VERDE_LIMA}; selection-color: #0a1633;
                border: 1px solid {theme.AZUL_BORDE}; outline: 0;
                font-size: 14px;
            }}
            QComboBox QAbstractItemView::item {{ min-height: 30px; padding: 4px 8px; }}
            QLabel#error {{ color: {theme.TEXTO_ERROR}; font-size: 12px; font-weight: 600; }}
            QPushButton#guardar {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 15px; font-weight: 800; border: none;
                border-radius: 8px; padding: 12px;
            }}
            QPushButton#guardar:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QPushButton#cancelar {{
                background-color: transparent; color: {theme.TEXTO_PRINCIPAL};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
            }}
        """)
