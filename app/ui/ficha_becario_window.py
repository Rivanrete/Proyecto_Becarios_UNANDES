"""Ficha del Becario — HU-04 (vista consolidada de solo lectura).

Muestra en una sola pantalla: datos personales, categoría/estado (HU-03)
y seguimiento (SeguimientoBecario). La sección académica es un placeholder
para HU-05 ("Sin registro académico del periodo aún").

Sin sección de documentos (opción A): la HU de documentos fue removida
del alcance vigente del proyecto, por eso no existe ni se referencia
DocumentoBecario en ninguna parte de esta ficha. No es un olvido.

Se abre como modal integrado (frameless + overlay + animación) igual que
el resto de modales, vía overlay.ejecutar_con_overlay().

HU-05: los badges de Horas Becarias y Materias en Orden son clickeables
y alternan su valor guardándolo en el periodo vigente.
"""
from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from app.services import becario_service
from app.ui import theme
from app.ui.notificacion import mostrar_notificacion
from app.ui.panel_control_window import ESTILO_BADGE_ROJO, ESTILO_BADGE_VERDE

ESTILO_BADGE_NEUTRO = (
    "background-color: #fef3c7; color: #92400e; "
    "border-radius: 10px; padding: 3px 12px; font-weight: 700;"
)

PLACEHOLDER_ACADEMICO = "Sin registro académico del periodo aún"


def estilo_estado(estado: str) -> str:
    if estado == "Activo":
        return ESTILO_BADGE_VERDE
    if estado == "Baja/Inactivo":
        return ESTILO_BADGE_ROJO
    return ESTILO_BADGE_NEUTRO


class FichaBecarioWindow(QDialog):
    """Recibe la ficha ya armada por obtener_ficha_completa(). Solo muestra."""

    def __init__(self, parent=None, ficha: dict | None = None):
        super().__init__(parent)
        if not ficha or ficha.get("becario") is None:
            raise ValueError("La ficha no existe.")
        self.ficha = ficha
        self._toggle_info: dict = {}
        self.setWindowTitle("Ficha del Becario")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumSize(560, 600)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(40, 32, 40, 32)

        card = QFrame(self)
        card.setObjectName("cardFicha")
        card.setMinimumWidth(480)
        card.setMaximumWidth(600)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(36, 24, 36, 32)

        encabezado = QHBoxLayout()
        encabezado.addStretch(1)
        btn_cerrar_x = QToolButton(card)
        btn_cerrar_x.setObjectName("cerrar")
        btn_cerrar_x.setText("✕")
        btn_cerrar_x.setToolTip("Cerrar")
        btn_cerrar_x.clicked.connect(self.reject)
        encabezado.addWidget(btn_cerrar_x)
        layout.addLayout(encabezado)

        becario = self.ficha["becario"]
        titulo = QLabel(f"{becario.nombres} {becario.apellidos}", card)
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        subtitulo = QLabel(f"Código {becario.codigo_estudiante}", card)
        subtitulo.setObjectName("subtitulo")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitulo)

        layout.addWidget(self._seccion("Datos personales"))
        form = QFormLayout()
        form.setSpacing(8)
        form.addRow("CI:", self._dato(becario.ci, card))
        form.addRow("Código:", self._dato(becario.codigo_estudiante, card))
        form.addRow("Carrera:", self._dato(self.ficha["carrera_etiqueta"], card))
        form.addRow("Contacto:", self._dato(becario.contacto or "—", card))
        layout.addLayout(form)

        layout.addWidget(self._seccion("Clasificación"))
        form_clase = QFormLayout()
        form_clase.setSpacing(8)
        form_clase.addRow("Categoría:", self._dato(becario.tipo_beca or "—", card))
        form_clase.addRow("Estado:", self._badge(becario.estado, estilo_estado(becario.estado), card))
        layout.addLayout(form_clase)

        layout.addWidget(self._seccion("Seguimiento"))
        seg = self.ficha["seguimiento"]
        if seg is None:
            layout.addWidget(self._dato("Sin seguimiento registrado", card))
        else:
            form_seg = QFormLayout()
            form_seg.setSpacing(8)
            form_seg.addRow("% Anterior:", self._dato(seg.porcentaje_anterior, card))
            form_seg.addRow("Gestión:", self._dato(seg.gestion, card))
            form_seg.addRow("Horas Becarias:",
                            self._badge_toggle("Cumplió" if seg.horas_becarias else "No cumplió",
                                               seg.horas_becarias, "horas_becarias", card))
            form_seg.addRow("Materias en Orden:",
                            self._badge_toggle("Sí" if seg.materias_en_orden else "No",
                                               seg.materias_en_orden, "materias_en_orden", card))
            form_seg.addRow("Carpeta Cancelada:",
                            self._badge_toggle("Sí" if seg.carpeta_cancelada else "No",
                                               seg.carpeta_cancelada, "carpeta_cancelada", card))
            form_seg.addRow("Carta Renovación:",
                            self._badge_toggle("Sí" if seg.carta_renovacion else "No",
                                               seg.carta_renovacion, "carta_renovacion", card))
            layout.addLayout(form_seg)

        layout.addWidget(self._seccion("Registro académico"))
        academico = QLabel(PLACEHOLDER_ACADEMICO, card)
        academico.setObjectName("placeholder")
        academico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        academico.setWordWrap(True)
        layout.addWidget(academico)

        self.btn_cerrar = QPushButton("Cerrar", card)
        self.btn_cerrar.setObjectName("cerrarBtn")
        self.btn_cerrar.setDefault(True)
        self.btn_cerrar.clicked.connect(self.reject)
        layout.addWidget(self.btn_cerrar)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _seccion(self, texto: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setObjectName("seccion")
        return etiqueta

    def _dato(self, texto: str, padre) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setObjectName("dato")
        etiqueta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return etiqueta

    def _badge(self, texto: str, estilo: str, padre) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet(estilo)
        return etiqueta

    def _badge_toggle(self, texto: str, positivo: bool, campo: str, padre) -> QLabel:
        """Badge clickeable HU-05: mano, tooltip y alternancia al clic."""
        etiqueta = self._badge(
            texto, ESTILO_BADGE_VERDE if positivo else ESTILO_BADGE_ROJO, padre)
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiqueta.setCursor(Qt.CursorShape.PointingHandCursor)
        etiqueta.setToolTip("Clic para cambiar")
        etiqueta.installEventFilter(self)
        self._toggle_info[etiqueta] = {"campo": campo, "valor": positivo}
        return etiqueta

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.MouseButtonRelease
                and obj in self._toggle_info
                and event.button() == Qt.MouseButton.LeftButton):
            self._alternar_campo(obj)
            return True
        return super().eventFilter(obj, event)

    def _alternar_campo(self, etiqueta: QLabel):
        """Alterna el badge y guarda en BD con feedback inmediato (sin recargar)."""
        info = self._toggle_info.get(etiqueta)
        seg = self.ficha["seguimiento"]
        if info is None or seg is None:
            return
        nuevo = not info["valor"]
        try:
            if info["campo"] == "horas_becarias":
                becario_service.actualizar_horas_becarias(seg.becario_id, seg.gestion, nuevo)
                seg.horas_becarias = nuevo
                texto = "Cumplió" if nuevo else "No cumplió"
            elif info["campo"] == "materias_en_orden":
                becario_service.actualizar_materias_en_orden(seg.becario_id, seg.gestion, nuevo)
                seg.materias_en_orden = nuevo
                texto = "Sí" if nuevo else "No"
            elif info["campo"] == "carpeta_cancelada":
                becario_service.actualizar_carpeta_cancelada(seg.becario_id, seg.gestion, nuevo)
                seg.carpeta_cancelada = nuevo
                texto = "Sí" if nuevo else "No"
            else:
                becario_service.actualizar_carta_renovacion(seg.becario_id, seg.gestion, nuevo)
                seg.carta_renovacion = nuevo
                texto = "Sí" if nuevo else "No"
        except Exception as e:
            mostrar_notificacion(self, f"No se pudo guardar el cambio: {e}", tipo="error")
            return
        info["valor"] = nuevo
        etiqueta.setText(texto)
        etiqueta.setStyleSheet(ESTILO_BADGE_VERDE if nuevo else ESTILO_BADGE_ROJO)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QFrame#cardFicha {{
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
            QLabel#subtitulo {{ color: {theme.VERDE_LIMA}; font-size: 13px; font-weight: 600; }}
            QLabel {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 13px; font-weight: 600; }}
            QLabel#seccion {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 14px; font-weight: 800; }}
            QLabel#dato {{ color: {theme.TEXTO_PRINCIPAL}; font-size: 13px; }}
            QLabel#placeholder {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 12px; font-style: italic; }}
            QPushButton#cerrarBtn {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 11px;
            }}
            QPushButton#cerrarBtn:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
        """)
