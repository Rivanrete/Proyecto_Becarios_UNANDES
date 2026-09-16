"""Panel de Control — listado y consulta de becarios (HU-05 + HU-08).

Integra: sidebar (solo "Panel de Control"), barra superior con título y
botón "+ Nuevo Becario" (abre el formulario HU-02), búsqueda con botón
"Filtrar" (visual, filtros reales en HU futura) y tabla de seguimiento
por gestión con badges verde/rojo.

FUENTE DE DATOS: consulta real (JOIN becario + seguimiento_becario)
vía becario_service.listar_para_panel(). Doble clic en una fila abre
el formulario en modo edición.

Búsqueda en vivo: el campo filtra por coincidencia parcial (contiene)
en código, nombres y apellidos, sin importar mayúsculas ni tildes.
"""
import unicodedata

from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
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
from app.ui.notificacion import mostrar_notificacion

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
TEXTO_SIN_RESULTADOS = "Ninguna coincidencia"


def _normalizar_texto(texto: str) -> str:
    """Minúsculas sin tildes para comparar (búsqueda insensible a ambas)."""
    base = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in base if not unicodedata.combining(c)).lower()

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
        self._filas_completas: list = []
        self._toggle_info: dict = {}
        self._categoria_filtro: str | None = None
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
        # HU-06 (+ adelanto HU-07): despliega categorías con conteo y filtra.
        self.btn_filtrar.clicked.connect(self._mostrar_menu_filtrar)
        barra_busqueda.addWidget(self.btn_filtrar)
        layout_contenido.addLayout(barra_busqueda)

        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.verticalHeader().setVisible(False)
        # Reparto híbrido: columnas 0-8 al tamaño de su contenido y las dos
        # últimas (encabezados largos) en Stretch para absorber todo el
        # ancho sobrante. Así no hay franja vacía ni encabezados cortados.
        cabecera = self.tabla.horizontalHeader()
        for i in range(len(COLUMNAS) - 2):
            cabecera.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        for i in (len(COLUMNAS) - 2, len(COLUMNAS) - 1):
            cabecera.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        # Doble clic abre el becario en modo edición (HU-02, CA-1).
        self.tabla.cellDoubleClicked.connect(self._abrir_editar)
        layout_contenido.addWidget(self.tabla, 1)

        # Búsqueda en vivo: filtra mientras se escribe (sin Enter ni botón).
        self.txt_busqueda.textChanged.connect(self._al_escribir)

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
        """Recarga la tabla desde la base de datos (respeta los filtros)."""
        self._filas_completas = [
            (b.id, b.carrera, b.apellidos, b.nombres, b.codigo_estudiante,
             seg if seg is not None else SeguimientoBecario(
                 id=None, becario_id=b.id, gestion="—"),
             seg.gestion if seg is not None else "—",
             seg,
             b.tipo_beca)
            for b, seg in becario_service.listar_para_panel()
        ]
        self.aplicar_filtro(self.txt_busqueda.text())

    def _al_escribir(self, texto: str):
        """Filtra en tiempo real con cada tecla (coincidencia parcial)."""
        self.aplicar_filtro(texto)

    def aplicar_filtro(self, texto: str):
        """Aplica texto (contiene) Y categoría a la vez: solo pasa la intersección.

        Vacío + "Todas" = todo. "Todas" limpia solo la categoría y conserva
        el texto escrito.
        """
        consulta = _normalizar_texto(texto.strip())
        categoria = self._categoria_filtro
        if not consulta and categoria is None:
            self.cargar_seguimientos(list(self._filas_completas))
            return
        filtradas = [
            fila for fila in self._filas_completas
            if (not consulta
                or consulta in _normalizar_texto(fila[4])
                or consulta in _normalizar_texto(fila[3])
                or consulta in _normalizar_texto(fila[2])
                or consulta in _normalizar_texto(f"{fila[3]} {fila[2]}")
                or consulta in _normalizar_texto(f"{fila[2]} {fila[3]}"))
            and (categoria is None or fila[8] == categoria)
        ]
        self.cargar_seguimientos(filtradas)

    def cargar_seguimientos(self, filas):
        """Puebla la tabla. `filas`: (becario_id, carrera, apellidos,
        nombres, codigo, SeguimientoBecario a mostrar, gestion, SeguimientoBecario
        real o None si aún no tiene registro, tipo_beca)."""
        self.tabla.setRowCount(0)
        self._ids_fila = []
        self._toggle_info = {}
        for i, (becario_id, carrera, apellidos, nombres, codigo, seg, gestion, real, _tipo) in enumerate(filas, start=1):
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
            self._celda_badge_toggle(fila, 7, "Cumplió" if seg.horas_becarias else "No cumplió",
                                     seg.horas_becarias, becario_id, "horas_becarias",
                                     real.gestion if real is not None else None)
            self._celda_badge_toggle(fila, 8, "Sí" if seg.materias_en_orden else "No",
                                     seg.materias_en_orden, becario_id, "materias_en_orden",
                                     real.gestion if real is not None else None)
            self._celda_badge_toggle(fila, 9, "Sí" if seg.carpeta_cancelada else "No",
                                     seg.carpeta_cancelada, becario_id, "carpeta_cancelada",
                                     real.gestion if real is not None else None)
            self._celda_badge_toggle(fila, 10, "Sí" if seg.carta_renovacion else "No",
                                     seg.carta_renovacion, becario_id, "carta_renovacion",
                                     real.gestion if real is not None else None)
        if self.tabla.rowCount() == 0:
            self._fila_sin_resultados()

    def _fila_sin_resultados(self):
        """Fila fantasma dentro de la tabla: una celda fusionada (colspan)
        con el aviso centrado, en el área blanca de las filas."""
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        self.tabla.setSpan(fila, 0, 1, len(COLUMNAS))
        self.tabla.setRowHeight(fila, 64)
        item = QTableWidgetItem(TEXTO_SIN_RESULTADOS)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        fuente = QFont()
        fuente.setItalic(True)
        item.setFont(fuente)
        item.setForeground(QColor(theme.TEXTO_GRIS))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.tabla.setItem(fila, 0, item)

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

    def _celda_badge_toggle(self, fila: int, columna: int, texto: str, positivo: bool,
                            becario_id: int, campo: str, gestion: str | None):
        """Badge clickeable HU-05: mano, tooltip y alternancia al clic."""
        etiqueta = QLabel(texto)
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiqueta.setStyleSheet(
            ESTILO_BADGE_VERDE if positivo else ESTILO_BADGE_ROJO
        )
        etiqueta.setCursor(Qt.CursorShape.PointingHandCursor)
        etiqueta.setToolTip("Clic para cambiar")
        etiqueta.installEventFilter(self)
        self._toggle_info[etiqueta] = {
            "becario_id": becario_id, "campo": campo,
            "valor": positivo, "gestion": gestion,
        }
        self.tabla.setCellWidget(fila, columna, etiqueta)

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
        if info is None:
            return
        nuevo = not info["valor"]
        try:
            if info["campo"] == "horas_becarias":
                becario_service.actualizar_horas_becarias(
                    info["becario_id"], info["gestion"], nuevo)
                texto = "Cumplió" if nuevo else "No cumplió"
            elif info["campo"] == "materias_en_orden":
                becario_service.actualizar_materias_en_orden(
                    info["becario_id"], info["gestion"], nuevo)
                texto = "Sí" if nuevo else "No"
            elif info["campo"] == "carpeta_cancelada":
                becario_service.actualizar_carpeta_cancelada(
                    info["becario_id"], info["gestion"], nuevo)
                texto = "Sí" if nuevo else "No"
            else:
                becario_service.actualizar_carta_renovacion(
                    info["becario_id"], info["gestion"], nuevo)
                texto = "Sí" if nuevo else "No"
        except Exception as e:
            mostrar_notificacion(self, f"No se pudo guardar el cambio: {e}", tipo="error")
            return
        info["valor"] = nuevo
        etiqueta.setText(texto)
        etiqueta.setStyleSheet(ESTILO_BADGE_VERDE if nuevo else ESTILO_BADGE_ROJO)

    def _mostrar_menu_filtrar(self):
        """HU-06 (conteo) + funcionalidad adelantada de HU-07 (filtro por categoría).

        El botón "Filtrar" cubre ambos: el dropdown lista cada categoría con
        su conteo real, y elegir una filtra la tabla (combinado con el texto).
        """
        menu = self._construir_menu_filtrar()
        menu.exec(self.btn_filtrar.mapToGlobal(self.btn_filtrar.rect().bottomLeft()))

    def _construir_menu_filtrar(self) -> QMenu:
        """Arma el dropdown con conteos frescos de la BD (se recalcula al abrir).

        Regla HU-06: la suma por categoría siempre cuadra con "Todas".
        Si algún becario queda sin tipo (''), no desaparece del conteo:
        aparece la opción "Sin categoría (N)" que filtra tipo_beca vacío.
        """
        menu = QMenu(self)
        menu.setObjectName("menuFiltrar")
        conteos = becario_service.contar_becarios_por_categoria()
        total = len(self._filas_completas)  # todas las filas, incluso sin categoría
        accion_todas = menu.addAction(f"Todas las categorías ({total})")
        accion_todas.setCheckable(True)
        accion_todas.setChecked(self._categoria_filtro is None)
        accion_todas.triggered.connect(lambda: self._elegir_categoria(None))
        menu.addSeparator()
        for categoria, cantidad in conteos:
            accion = menu.addAction(f"{categoria} ({cantidad})")
            accion.setCheckable(True)
            accion.setChecked(self._categoria_filtro == categoria)
            accion.triggered.connect(
                lambda checked=False, c=categoria: self._elegir_categoria(c)
            )
        sin_categoria = total - sum(cantidad for _, cantidad in conteos)
        if sin_categoria > 0:
            accion_sin = menu.addAction(f"Sin categoría ({sin_categoria})")
            accion_sin.setCheckable(True)
            accion_sin.setChecked(self._categoria_filtro == "")
            accion_sin.triggered.connect(lambda: self._elegir_categoria(""))
        return menu

    def _elegir_categoria(self, categoria: str | None):
        """Fija el filtro de categoría ("Todas" lo limpia, conserva el texto)."""
        self._categoria_filtro = categoria
        if categoria is None:
            etiqueta = "Filtrar"
        elif categoria == "":
            etiqueta = "Filtrar: Sin categoría"
        else:
            etiqueta = f"Filtrar: {categoria}"
        self.btn_filtrar.setText(etiqueta)
        self.aplicar_filtro(self.txt_busqueda.text())

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
            QMenu#menuFiltrar {{
                background-color: {theme.BLANCO_TARJETA}; color: {theme.TEXTO_OSCURO};
                border: 1px solid {theme.BORDE_SUAVE}; padding: 6px;
            }}
            QMenu#menuFiltrar::item {{ padding: 8px 24px 8px 28px; border-radius: 6px; }}
            QMenu#menuFiltrar::item:selected {{ background-color: #ecfccb; }}
            QMenu#menuFiltrar::separator {{ height: 1px; background: #e2e8f0; margin: 6px 10px; }}
            QMenu#menuFiltrar::indicator {{ width: 14px; height: 14px; }}
            QTableWidget {{
                background-color: {theme.BLANCO_TARJETA}; color: {theme.TEXTO_OSCURO};
                gridline-color: #e2e8f0; font-size: 12px;
                border: 1px solid #e2e8f0; border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {theme.AZUL_FONDO}; color: {theme.TEXTO_PRINCIPAL};
                font-weight: 700; padding: 6px; border: none;
            }}
        """)
