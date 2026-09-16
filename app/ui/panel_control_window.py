"""Panel de Control — listado y consulta de becarios (HU-05 + HU-08).

Integra: sidebar (solo "Panel de Control"), barra superior con título y
botón "+ Nuevo Becario" (abre el formulario HU-02), búsqueda con botón
"Filtrar" (visual, filtros reales en HU futura) y tabla de seguimiento
por gestión con badges verde/rojo.

FUENTE DE DATOS: consulta real (JOIN becario + seguimiento_becario)
vía becario_service.listar_para_panel(). Doble clic en una fila abre
el formulario en modo edición.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.seguimiento_becario import SeguimientoBecario
from app.models.usuario import Usuario
from app.services import becario_service
from app.services.auth_service import SesionActual
from app.ui import theme

COLUMNAS = [
    "N.",
    "Carrera",
    "Apellidos",
    "Nombres",
    "Código",
    "% Anterior",
    "Gestión",
    "Horas Becarias",
    "Materias en Orden",
    "Carpeta de Becas Cancelada",
    "Carta de Renovación Presentada",
]

TEXTO_BUSQUEDA = "Buscar por código Ej: 23718 o por nombre Beymar Condori Quispe"

ESTILO_BADGE_VERDE = (
    "background-color: #dcfce7; color: #166534; "
    "border-radius: 10px; padding: 3px 12px; font-weight: 700;"
)
ESTILO_BADGE_ROJO = (
    "background-color: #fee2e2; color: #991b1b; "
    "border-radius: 10px; padding: 3px 12px; font-weight: 700;"
)


class PanelControlWindow(QMainWindow):
    """Vista post-login del listado de becarios."""

    # HU-02: abrir formulario en modo "nuevo" / en modo "editar(id)".
    nuevo_becario_solicitado = Signal()
    becario_editar_solicitado = Signal(int)

    # Ítems del sidebar. Solo "Panel de Control" por ahora; las opciones
    # futuras (Becarios, Reportes, Configuración) se agregan aquí en su HU.
    ITEMS_SIDEBAR = ["Panel de Control"]

    def __init__(self, usuario: Usuario | None, parent=None):
        if usuario is None or not SesionActual.activa():
            raise PermissionError("Acceso denegado: debe iniciar sesión primero (HU-01).")
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle("UNANDES • Registro de Becarios — Panel de Control")
        self.setMinimumSize(900, 600)
        self._ids_fila: list[int] = []
        self._build_ui()
        self._apply_style()
        self.refrescar()

    # -- layout -----------------------------------------------------------
    def _build_ui(self):
        raiz = QWidget(self)
        layout_raiz = QHBoxLayout(raiz)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        layout_raiz.addWidget(self._construir_sidebar())

        contenido = QWidget(raiz)
        contenido.setObjectName("contenido")
        layout_contenido = QVBoxLayout(contenido)
        layout_contenido.setContentsMargins(28, 24, 28, 24)
        layout_contenido.setSpacing(14)

        barra_titulo = QHBoxLayout()
        titulo = QLabel("Listado de Becarios")
        titulo.setObjectName("tituloSeccion")
        barra_titulo.addWidget(titulo, alignment=Qt.AlignmentFlag.AlignVCenter)
        barra_titulo.addStretch(1)
        self.btn_nuevo = QPushButton("+ Nuevo Becario")
        self.btn_nuevo.setObjectName("nuevo")
        # HU-02: main.py conecta esta señal con el formulario en modo "nuevo".
        self.btn_nuevo.clicked.connect(self.nuevo_becario_solicitado.emit)
        barra_titulo.addWidget(self.btn_nuevo)
        layout_contenido.addLayout(barra_titulo)

        barra_busqueda = QHBoxLayout()
        barra_busqueda.setSpacing(10)
        self.txt_busqueda = QLineEdit()
        self.txt_busqueda.setPlaceholderText(TEXTO_BUSQUEDA)
        self.txt_busqueda.setClearButtonEnabled(True)
        lupa = QLabel("⌕")
        lupa.setObjectName("lupa")
        fila_busqueda = QHBoxLayout()
        fila_busqueda.setSpacing(6)
        fila_busqueda.addWidget(lupa)
        fila_busqueda.addWidget(self.txt_busqueda, 1)
        barra_busqueda.addLayout(fila_busqueda, 1)
        self.btn_filtrar = QPushButton("Filtrar")
        self.btn_filtrar.setObjectName("filtrar")
        # Sin funcionalidad todavía; HU futura de filtros avanzados.
        self.btn_filtrar.clicked.connect(self._filtrar_pendiente)
        barra_busqueda.addWidget(self.btn_filtrar)
        layout_contenido.addLayout(barra_busqueda)

        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        # Doble clic abre el becario en modo edición (HU-02, CA-1).
        self.tabla.cellDoubleClicked.connect(self._abrir_editar)
        layout_contenido.addWidget(self.tabla, 1)

        layout_raiz.addWidget(contenido, 1)
        self.setCentralWidget(raiz)

    def _construir_sidebar(self) -> QWidget:
        lateral = QFrame()
        lateral.setObjectName("sidebar")
        lateral.setFixedWidth(220)
        layout = QVBoxLayout(lateral)
        layout.setContentsMargins(0, 24, 0, 24)
        layout.setSpacing(4)

        marca = QLabel("UNANDES")
        marca.setObjectName("marca")
        marca.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(marca)
        layout.addSpacing(20)

        for item in self.ITEMS_SIDEBAR:
            etiqueta = QLabel(item)
            etiqueta.setObjectName("itemActivo")
            etiqueta.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            layout.addWidget(etiqueta)

        layout.addStretch(1)
        pie = QLabel(f"Sesión: {self.usuario.nombre_usuario}")
        pie.setObjectName("sesion")
        pie.setWordWrap(True)
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pie)
        return lateral

    # -- datos (fuente real: JOIN becario + seguimiento_becario) ------------
    def refrescar(self):
        """Recarga la tabla desde la base de datos."""
        filas = [
            (b.id, b.carrera, b.apellidos, b.nombres, b.codigo_estudiante,
             seg if seg is not None else SeguimientoBecario(
                 id=None, becario_id=b.id, gestion="—"),
             seg.gestion if seg is not None else "—")
            for b, seg in becario_service.listar_para_panel()
        ]
        self.cargar_seguimientos(filas)

    def cargar_seguimientos(self, filas):
        """Puebla la tabla. `filas`: (becario_id, carrera, apellidos,
        nombres, codigo, SeguimientoBecario, gestion)."""
        self.tabla.setRowCount(0)
        self._ids_fila = []
        for i, (becario_id, carrera, apellidos, nombres, codigo, seg, gestion) in enumerate(filas, start=1):
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            self._ids_fila.append(becario_id)
            self._celda_texto(fila, 0, str(i))
            self._celda_texto(fila, 1, carrera)
            self._celda_texto(fila, 2, apellidos)
            self._celda_texto(fila, 3, nombres)
            self._celda_texto(fila, 4, codigo)
            self._celda_texto(fila, 5, seg.porcentaje_anterior)
            self._celda_texto(fila, 6, gestion)
            self._celda_badge(fila, 7, "Cumplió" if seg.horas_becarias else "No cumplió",
                              positivo=seg.horas_becarias)
            self._celda_badge(fila, 8, "Sí" if seg.materias_en_orden else "No",
                              positivo=seg.materias_en_orden)
            self._celda_badge(fila, 9, "Sí" if seg.carpeta_cancelada else "No",
                              positivo=seg.carpeta_cancelada)
            self._celda_badge(fila, 10, "Sí" if seg.carta_renovacion else "No",
                              positivo=seg.carta_renovacion)
        self.tabla.resizeColumnsToContents()

    def _celda_texto(self, fila: int, columna: int, texto: str):
        item = QTableWidgetItem(texto)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabla.setItem(fila, columna, item)

    def _celda_badge(self, fila: int, columna: int, texto: str, positivo: bool):
        etiqueta = QLabel(texto)
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiqueta.setStyleSheet(
            ESTILO_BADGE_VERDE if positivo else ESTILO_BADGE_ROJO
        )
        self.tabla.setCellWidget(fila, columna, etiqueta)

    def _filtrar_pendiente(self):
        """Hook visual. La HU de filtros avanzados lo implementará."""

    def _abrir_editar(self, fila: int, _columna: int):
        """Doble clic en una fila: solicita edición del becario (HU-02)."""
        if 0 <= fila < len(self._ids_fila):
            self.becario_editar_solicitado.emit(self._ids_fila[fila])

    def _apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {theme.AZUL_FONDO}; }}
            QWidget#contenido {{ background-color: #f1f5f9; }}
            QFrame#sidebar {{
                background-color: {theme.AZUL_FONDO};
                border: none;
            }}
            QLabel#marca {{
                color: {theme.TEXTO_PRINCIPAL};
                font-size: 18px; font-weight: 800; letter-spacing: 2px;
            }}
            QLabel#itemActivo {{
                color: {theme.VERDE_LIMA}; font-size: 14px; font-weight: 700;
                padding: 10px 18px;
                border-left: 3px solid {theme.VERDE_LIMA};
            }}
            QLabel#sesion {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 11px; }}
            QLabel#tituloSeccion {{ color: {theme.TEXTO_OSCURO}; font-size: 22px; font-weight: 800; }}
            QLabel#lupa {{ color: {theme.TEXTO_GRIS}; font-size: 18px; }}
            QLineEdit {{
                background-color: {theme.CAMPO_FONDO}; color: {theme.TEXTO_OSCURO};
                border: 1px solid {theme.BORDE_SUAVE}; border-radius: 8px; padding: 10px;
                font-size: 13px;
            }}
            QPushButton#nuevo {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 10px 20px;
            }}
            QPushButton#nuevo:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QPushButton#filtrar {{
                background-color: {theme.BLANCO_TARJETA}; color: {theme.TEXTO_OSCURO};
                font-size: 13px; font-weight: 700;
                border: 1px solid {theme.BORDE_SUAVE}; border-radius: 8px; padding: 10px 20px;
            }}
            QTableWidget {{
                background-color: {theme.BLANCO_TARJETA}; color: {theme.TEXTO_OSCURO};
                gridline-color: #e2e8f0; font-size: 12px;
                border: 1px solid #e2e8f0; border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {theme.AZUL_FONDO}; color: {theme.TEXTO_PRINCIPAL};
                font-weight: 700; padding: 8px; border: none;
            }}
        """)
