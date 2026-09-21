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
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from app.services import becario_service
from app.services.becario_service import BecarioDuplicadoError
from app.ui import theme
from app.ui.dialogo_base import DialogoBase


class BecarioFormWindow(DialogoBase):
    def __init__(self, parent=None, becario_id: int | None = None):
        # Sin marco nativo: ver DialogoBase (frameless, no modal).
        # El cierre es X / Cancelar / Esc / clic fuera (overlay).
        super().__init__(parent, modal=False)
        self.becario_id = becario_id
        self._modo_edicion = becario_id is None
        self._snapshot_original: dict = {}
        self._controles_editables = []
        # main.py lee este mensaje tras accept() y lo muestra con la
        # notificación propia del sistema (sin QMessageBox nativo).
        self.mensaje_exito: str | None = None
        self.setWindowTitle(
            "Ficha del Becario" if becario_id is not None else "Nuevo Becario"
        )
        self.setMinimumSize(800, 760)
        self._build_ui()
        self._apply_style()
        if becario_id is not None:
            self._precargar()
            self._guardar_snapshot()
            self._actualizar_estado_formulario()
        else:
            self._actualizar_estado_formulario()

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

        self.lbl_titulo = QLabel(
            "Ficha del Becario" if self.becario_id is not None else "Nuevo Becario", card
        )
        self.lbl_titulo.setObjectName("titulo")
        self.lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_titulo)

        form = QFormLayout()
        form.setSpacing(10)
        # Solo enteros positivos: no acepta letras, espacios ni caracteres
        # especiales. La BD sigue guardando TEXT, pero el input queda restringido.
        validador_enteros_positivos = QRegularExpressionValidator(
            QRegularExpression("^[1-9][0-9]*$"), card)
        validador_contacto = QRegularExpressionValidator(
            QRegularExpression("^[1-9][0-9]{0,7}$"), card)
        self.txt_nombres = QLineEdit(card)
        self.txt_apellidos = QLineEdit(card)
        self.txt_nombres.editingFinished.connect(
            lambda: self._aplicar_mayuscula_inicial(self.txt_nombres))
        self.txt_apellidos.editingFinished.connect(
            lambda: self._aplicar_mayuscula_inicial(self.txt_apellidos))
        self.txt_ci = QLineEdit(card)
        self.txt_ci.setValidator(validador_enteros_positivos)
        self.txt_ci.setMaxLength(15)
        self.txt_codigo = QLineEdit(card)
        self.txt_codigo.setValidator(validador_enteros_positivos)
        self.txt_codigo.setMaxLength(15)
        self.cmb_carrera = QComboBox(card)
        for sigla, etiqueta in becario_service.opciones_carrera():
            self.cmb_carrera.addItem(etiqueta, sigla)
        self.cmb_carrera.setMaxVisibleItems(self.cmb_carrera.count())
        self.cmb_carrera.setPlaceholderText("Seleccione una carrera")
        self.cmb_carrera.setCurrentIndex(-1)
        self.cmb_tipo = QComboBox(card)
        self.cmb_tipo.addItems(becario_service.listar_tipos_beca())
        self.cmb_tipo.setMaxVisibleItems(self.cmb_tipo.count())
        self.cmb_tipo.setPlaceholderText("Seleccione un tipo de beca")
        self.cmb_tipo.setCurrentIndex(-1)
        self.cmb_ingreso = QComboBox(card)
        if self.becario_id is None:
            for gestion in becario_service.gestiones_ingreso_nuevo():
                self.cmb_ingreso.addItem(gestion, gestion)
        else:
            for gestion in becario_service.gestiones_ingreso_editar():
                self.cmb_ingreso.addItem(gestion, gestion)
            self.cmb_ingreso.addItem("—", "")
        self.cmb_ingreso.setMaxVisibleItems(self.cmb_ingreso.count())
        self.cmb_ingreso.setPlaceholderText("Seleccione la gestión")
        self.cmb_ingreso.setCurrentIndex(0)
        self.txt_contacto = QLineEdit(card)
        self.txt_contacto.setValidator(validador_contacto)
        self.txt_contacto.setMaxLength(8)
        self.txt_contacto.setPlaceholderText("Celular, solo números (opcional)")
        for control in (
            self.txt_nombres,
            self.txt_apellidos,
            self.txt_ci,
            self.txt_codigo,
            self.cmb_carrera,
            self.cmb_tipo,
            self.cmb_ingreso,
            self.txt_contacto,
        ):
            self._controles_editables.append(control)
        form.addRow("Nombres:", self.txt_nombres)
        form.addRow("Apellidos:", self.txt_apellidos)
        form.addRow("CI:", self.txt_ci)
        form.addRow("Código:", self.txt_codigo)
        form.addRow("Carrera:", self.cmb_carrera)
        form.addRow("Tipo de Beca:", self.cmb_tipo)
        form.addRow("Gestión de ingreso:", self.cmb_ingreso)
        form.addRow("Contacto:", self.txt_contacto)
        layout.addLayout(form)

        self.lbl_error = QLabel("", card)
        self.lbl_error.setObjectName("error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(8)
        self.btn_editar = QPushButton("Editar Datos", card)
        self.btn_editar.setObjectName("editar")
        self.btn_editar.clicked.connect(self._on_editar)
        self.btn_guardar = QPushButton("Guardar", card)
        self.btn_guardar.setObjectName("guardar")
        self.btn_guardar.setDefault(True)
        self.btn_guardar.clicked.connect(self._on_guardar)
        self.btn_cancelar = QPushButton("Cancelar", card)
        self.btn_cancelar.setObjectName("cancelar")
        self.btn_cancelar.clicked.connect(self._on_cancelar)
        fila_botones.addStretch(1)
        fila_botones.addWidget(self.btn_editar)
        fila_botones.addWidget(self.btn_guardar)
        fila_botones.addWidget(self.btn_cancelar)
        layout.addLayout(fila_botones)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        self.txt_nombres.setFocus()

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
        indice_ingreso = self.cmb_ingreso.findData(becario.gestion_ingreso or "")
        if indice_ingreso < 0 and becario.gestion_ingreso:
            self.cmb_ingreso.insertItem(
                self.cmb_ingreso.count() - 1,
                becario.gestion_ingreso, becario.gestion_ingreso)
            indice_ingreso = self.cmb_ingreso.findData(becario.gestion_ingreso)
        if indice_ingreso >= 0:
            self.cmb_ingreso.setCurrentIndex(indice_ingreso)
        self.txt_contacto.setText(becario.contacto)

    def _guardar_snapshot(self):
        if self.becario_id is None:
            return
        self._snapshot_original = {
            "nombres": self.txt_nombres.text(),
            "apellidos": self.txt_apellidos.text(),
            "ci": self.txt_ci.text(),
            "codigo_estudiante": self.txt_codigo.text(),
            "carrera": self.cmb_carrera.currentData() or self.cmb_carrera.currentText(),
            "tipo_beca": self.cmb_tipo.currentText(),
            "gestion_ingreso": self.cmb_ingreso.currentData() or "",
            "contacto": self.txt_contacto.text(),
        }

    def _restaurar_snapshot(self):
        if self.becario_id is None:
            return
        self.txt_nombres.setText(self._snapshot_original.get("nombres", ""))
        self.txt_apellidos.setText(self._snapshot_original.get("apellidos", ""))
        self.txt_ci.setText(self._snapshot_original.get("ci", ""))
        self.txt_codigo.setText(self._snapshot_original.get("codigo_estudiante", ""))
        carrera = self._snapshot_original.get("carrera", "")
        indice = self.cmb_carrera.findData(carrera)
        if indice >= 0:
            self.cmb_carrera.setCurrentIndex(indice)
        tipo = self._snapshot_original.get("tipo_beca", "")
        indice_tipo = self.cmb_tipo.findText(tipo)
        if indice_tipo >= 0:
            self.cmb_tipo.setCurrentIndex(indice_tipo)
        ingreso = self._snapshot_original.get("gestion_ingreso", "")
        indice_ingreso = self.cmb_ingreso.findData(ingreso)
        if indice_ingreso >= 0:
            self.cmb_ingreso.setCurrentIndex(indice_ingreso)
        self.txt_contacto.setText(self._snapshot_original.get("contacto", ""))

    def _actualizar_estado_formulario(self):
        editable = self._modo_edicion
        if self.becario_id is not None:
            self.lbl_titulo.setText("Editar Becario" if editable else "Ficha del Becario")
            self.setWindowTitle("Editar Becario" if editable else "Ficha del Becario")
            self.btn_editar.setVisible(not editable)
            self.btn_guardar.setVisible(editable)
            self.btn_cancelar.setVisible(editable)
        else:
            self.lbl_titulo.setText("Nuevo Becario")
            self.setWindowTitle("Nuevo Becario")
            self.btn_editar.setVisible(False)
            self.btn_guardar.setVisible(True)
            self.btn_cancelar.setVisible(True)
        for control in self._controles_editables:
            if isinstance(control, QLineEdit):
                control.setReadOnly(not editable)
            else:
                control.setEnabled(editable)

    def _on_editar(self):
        self._guardar_snapshot()
        self._modo_edicion = True
        self._actualizar_estado_formulario()

    def _on_cancelar(self):
        if self.becario_id is not None:
            self._restaurar_snapshot()
            self._modo_edicion = False
            self._actualizar_estado_formulario()
            return
        self.reject()

    def _aplicar_mayuscula_inicial(self, campo: QLineEdit):
        """Normaliza el campo al salir de él (se ve el resultado de inmediato)."""
        campo.setText(becario_service.normalizar_nombre_propio(campo.text()))

    def _datos_formulario(self) -> dict:
        return {
            "nombres": self.txt_nombres.text(),
            "apellidos": self.txt_apellidos.text(),
            "ci": self.txt_ci.text(),
            "codigo_estudiante": self.txt_codigo.text(),
            "carrera": self.cmb_carrera.currentData() or self.cmb_carrera.currentText(),
            "tipo_beca": self.cmb_tipo.currentText(),
            "gestion_ingreso": self.cmb_ingreso.currentData() or "",
            "contacto": self.txt_contacto.text(),
        }

    def _on_guardar(self):
        self.lbl_error.setVisible(False)

        nombres = self.txt_nombres.text().strip()
        apellidos = self.txt_apellidos.text().strip()
        ci = self.txt_ci.text().strip()
        codigo = self.txt_codigo.text().strip()

        if not nombres or not apellidos or not ci or not codigo:
            QMessageBox.warning(
                self,
                "Campos obligatorios",
                "Completa los campos: Nombres, Apellidos, CI y Código.",
            )
            self.lbl_error.setText("Completa los campos obligatorios antes de guardar.")
            self.lbl_error.setVisible(True)
            return

        if self.becario_id is not None:
            excludes = self.becario_id
        else:
            excludes = None

        if becario_service.becario_repository.existe_ci(ci, excluir_id=excludes):
            QMessageBox.warning(
                self,
                "CI duplicado",
                "El CI ya se encuentra registrado por otro becario.",
            )
            self.lbl_error.setText("El CI ya se encuentra registrado por otro becario.")
            self.lbl_error.setVisible(True)
            return

        if becario_service.becario_repository.existe_codigo(codigo, excluir_id=excludes):
            QMessageBox.warning(
                self,
                "Código duplicado",
                "El código de estudiante ya existe en la base de datos.",
            )
            self.lbl_error.setText("El código de estudiante ya existe en la base de datos.")
            self.lbl_error.setVisible(True)
            return

        try:
            if self.becario_id is None:
                becario_service.registrar_becario(self._datos_formulario())
                mensaje = "Becario registrado correctamente."
            else:
                becario_service.editar_becario(self.becario_id, self._datos_formulario())
                mensaje = "Becario actualizado correctamente."
        except BecarioDuplicadoError as e:
            QMessageBox.warning(self, "Datos duplicados", str(e))
            self.lbl_error.setText(str(e) + " No se guardó el registro.")
            self.lbl_error.setVisible(True)
            return
        except ValueError as e:
            QMessageBox.warning(self, "Validación", str(e))
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
            QLineEdit, QComboBox, QTextEdit {{
                background-color: {theme.BLANCO_TARJETA}; color: {theme.TEXTO_INPUT};
                border: 1px solid {theme.BORDE_INPUT}; border-radius: 8px;
                padding: 10px; font-size: 14px; min-height: 22px;
            }}
            QLineEdit::placeholder, QTextEdit::placeholder {{ color: {theme.TEXTO_PLACEHOLDER}; }}
            QLineEdit {{ qproperty-placeholderTextColor: {theme.TEXTO_PLACEHOLDER}; }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 1px solid #60A5FA; background-color: {theme.BLANCO_TARJETA};
            }}
            QLineEdit:read-only, QTextEdit:read-only,
            QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled {{
                background-color: {theme.FONDO_INPUT_READONLY}; color: {theme.TEXTO_INPUT};
                border: 1px solid {theme.BORDE_INPUT};
            }}
            QComboBox {{
                padding: 10px 34px 10px 12px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px; border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.BLANCO_TARJETA}; color: {theme.TEXTO_INPUT};
                selection-background-color: #DBEAFE; selection-color: {theme.TEXTO_INPUT};
                border: 1px solid {theme.BORDE_INPUT}; outline: 0;
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
            QPushButton#editar {{
                background-color: {theme.AZUL_BORDE}; color: {theme.TEXTO_PRINCIPAL};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.AZUL_BORDE}; border-radius: 8px; padding: 10px;
            }}
        """)
