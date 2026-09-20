"""Panel de Control — listado y consulta de becarios (HU-05 + HU-08).

Integra: sidebar (Panel de Control, Respaldos, Becarios Inactivos,
Informes), barra superior con título y botón "+ Nuevo Becario" (abre el
formulario HU-02), búsqueda con botón "Filtrar" y tabla de seguimiento
por gestión con badges verde/rojo.

FUENTE DE DATOS: consulta real (JOIN becario + seguimiento_becario)
vía becario_service.listar_para_panel(). Doble clic en una fila abre
el formulario en modo edición.

Búsqueda en vivo: el campo filtra por coincidencia parcial (contiene)
en código, nombres y apellidos, sin importar mayúsculas ni tildes.
"""
import unicodedata
import webbrowser

from PySide6.QtCore import Qt, QEvent, QTimer, Signal, QUrl
from PySide6.QtGui import QBrush, QColor, QCursor, QDesktopServices, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.seguimiento_becario import SeguimientoBecario
from app.models.usuario import Usuario
from app.services import becario_service
from app.services import gestion_service
from app.services import informe_service
from app.services.auth_service import SesionActual
from app.ui import theme
from app.ui.dialogo_fecha_limite import DialogoFechaLimite
from app.ui.dialogo_nuevo_informe import DialogoNuevoInforme
from app.ui.notificacion import mostrar_notificacion, pedir_confirmacion
from app.ui.overlay import ejecutar_con_overlay

COLUMNAS = [
    "N.",
    "Carrera",
    "Apellidos",
    "Nombres",
    "Código",
    "%\nAnterior",
    "Gestión",
    "Horas\nBecarias",
    "Materias\nen Orden",
    "Carpeta\nCancelada",
    "Carta\nRenovación",
    "Estado",
]

# Pesos proporcionales de columna (suman 100): se aplican sobre el ancho
# visible para que la tabla quepa sin scroll en pantallas chicas.
# Horas (7) y Estado (11) reservan lo medido para "No cumplió"/"En renovación".
PESOS_COLUMNAS = (5, 7, 13, 12, 8, 8, 7, 8, 8, 8, 8, 8)

# Abreviaturas fijas (antes que "…") para los dos badges largos.
_ABREVIATURAS_FIJAS = {"No cumplió": "No cump.", "En renovación": "En renov."}

# Variante corta de encabezado (de beymar) cuando la columna queda angosta.
_ABREVIATURAS_ENCABEZADO = {9: "C. C.", 10: "C. de R."}

# Margen que se reserva al abreviar badges (acolchado del estilo + aire).
MARGEN_BADGE_PX = 26

ESTILO_BADGE_NEUTRO = (
    "background-color: #fef3c7; color: #92400e; "
    "border-radius: 10px; padding: 3px 12px; font-weight: 700;"
)

# Capa adicional sobre la fila: rojo tenue para requisitos vencidos.
# Solo tiñe las celdas de texto; los badges conservan sus colores propios.
FONDO_FILA_VENCIDA = QBrush(QColor("#fecaca"))
TOOLTIP_VENCIDO = "Requisitos vencidos: complete los flags pendientes"


def estilo_estado(estado: str) -> str:
    """Verde Activo, rojo Baja/Inactivo, ámbar el resto (igual que la ficha)."""
    if estado == "Activo":
        return ESTILO_BADGE_VERDE
    if estado == "Baja/Inactivo":
        return ESTILO_BADGE_ROJO
    return ESTILO_BADGE_NEUTRO


def _opciones_campo(campo: str) -> list:
    """Opciones válidas del desplegable: coinciden con lo que usa el sistema."""
    if campo == "estado":
        return list(becario_service.ESTADOS_BECARIO)
    return [True, False]


def _texto_opcion(campo: str, valor) -> str:
    """Etiqueta visible de cada opción (misma que ya mostraban los badges)."""
    if campo == "horas_becarias":
        return "Cumplió" if valor else "No cumplió"
    if campo == "estado":
        return str(valor)
    return "Sí" if valor else "No"


def _estilo_opcion(campo: str, valor) -> str:
    if campo == "estado":
        return estilo_estado(valor)
    return ESTILO_BADGE_VERDE if valor else ESTILO_BADGE_ROJO

TEXTO_BUSQUEDA = "Buscar por código Ej: 23718 o por nombre Beymar Condori Quispe"
TEXTO_SIN_RESULTADOS = "Ninguna coincidencia"

# Índice de la columna Código en la tabla principal (doble clic = perfil SIAC).
INDICE_COLUMNA_CODIGO = 4
URL_PERFIL_SIAC = "https://udelosandes.com/siac/estudiante/informacion_academica/{codigo}/218"


def abrir_perfil_siac(codigo: str):
    """Abre el perfil SIAC del código en el navegador predeterminado."""
    webbrowser.open(URL_PERFIL_SIAC.format(codigo=(codigo or "").strip()))

COLUMNAS_INACTIVOS = ["N.", "Apellidos", "Nombres", "CI", "Código", "Carrera", "", ""]

COLUMNAS_RESPALDO = ["N.", "Carrera", "Apellidos", "Nombres", "Código",
                     "% Anterior", "Gestión de ingreso", "Horas Becarias", "Materias en Orden",
                     "Carpeta Cancelada", "Carta Renovación",
                     "Estado"]

COLUMNAS_INFORMES = ["N.", "Archivo", "Tamaño", "", ""]


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

    # Ítems del sidebar como (etiqueta, página). El orden visual es
    # independiente del índice de página en el QStackedWidget.
    # Las opciones futuras (Reportes, Configuración) se agregan aquí en su HU.
    ITEMS_SIDEBAR = [("Panel de Control", 0), ("Respaldos", 2),
                     ("Becarios Inactivos", 1), ("Informes", 3)]

    def __init__(self, usuario: Usuario | None, parent=None):
        if usuario is None or not SesionActual.activa():
            raise PermissionError("Acceso denegado: debe iniciar sesión primero (HU-01).")
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle("UNANDES • Registro de Becarios — Panel de Control")
        self.setMinimumSize(900, 600)
        self._ids_fila: list[int] = []
        self._filas_completas: list = []
        self._inactivos_completos: list = []
        self._menu_info: dict = {}
        self._categoria_filtro: str | None = None
        self._solo_pendientes = False
        self._fecha_limite: str | None = None
        self._botones_sidebar: list = []
        self._anchos_proporcionales_listos = False
        self._reajuste_columnas_pendiente = False
        self._build_ui()
        self._apply_style()
        self.refrescar()

    def showEvent(self, event):
        """Programa el cálculo con la ventana ya en su tamaño final."""
        super().showEvent(event)
        self._programar_reajuste_columnas()

    def _programar_reajuste_columnas(self):
        """Calcula anchos tras el layout (coalesca redimensionados seguidos)."""
        if self._reajuste_columnas_pendiente:
            return
        self._reajuste_columnas_pendiente = True
        QTimer.singleShot(0, self._reajustar_columnas_diferido)

    def _reajustar_columnas_diferido(self):
        self._reajuste_columnas_pendiente = False
        try:
            if self._aplicar_anchos_proporcionales():
                self._anchos_proporcionales_listos = True
        except RuntimeError:
            pass  # ventana cerrada antes del ciclo de eventos

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
        self.btn_fecha_limite = QPushButton("Fecha límite")
        self.btn_fecha_limite.setObjectName("filtrar")
        self.btn_fecha_limite.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fecha_limite.clicked.connect(self._definir_fecha_limite)
        barra_busqueda.addWidget(self.btn_fecha_limite)
        layout_contenido.addLayout(barra_busqueda)

        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Sin foco: ninguna fila se ve distinta hasta que el usuario la seleccione.
        self.tabla.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tabla.verticalHeader().setVisible(False)
        # Anchos proporcionales al viewport (Interactive): caben sin scroll
        # en pantallas chicas y el texto que sobra se abrevia con "…".
        self.tabla.setTextElideMode(Qt.TextElideMode.ElideRight)
        cabecera = self.tabla.horizontalHeader()
        for i in range(len(COLUMNAS)):
            cabecera.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        self.tabla.installEventFilter(self)
        # Doble clic abre el becario en modo edición (HU-02, CA-1).
        self.tabla.cellDoubleClicked.connect(self._abrir_editar)
        layout_contenido.addWidget(self.tabla, 1)

        # Búsqueda en vivo: filtra mientras se escribe (sin Enter ni botón).
        self.txt_busqueda.textChanged.connect(self._al_escribir)

        self.paginas = QStackedWidget(raiz)
        self.paginas.addWidget(contenido)
        self.paginas.addWidget(self._construir_pagina_inactivos())
        self.paginas.addWidget(self._construir_pagina_respaldos())
        self.paginas.addWidget(self._construir_pagina_informes())
        layout_raiz.addWidget(self.paginas, 1)
        self.setCentralWidget(raiz)

    def _construir_pagina_inactivos(self) -> QWidget:
        """Segunda página: solo Baja/Inactivo, con botón Eliminar por fila."""
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        titulo = QLabel("Becarios Inactivos")
        titulo.setObjectName("tituloSeccion")
        layout.addWidget(titulo)

        self.tabla_inactivos = QTableWidget(0, len(COLUMNAS_INACTIVOS))
        self.tabla_inactivos.setHorizontalHeaderLabels(COLUMNAS_INACTIVOS)
        self.tabla_inactivos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_inactivos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_inactivos.verticalHeader().setVisible(False)
        self.tabla_inactivos.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_inactivos, 1)

        # Acción masiva separada de las filas (espacio + alineada a la derecha).
        layout.addSpacing(12)
        fila_masiva = QHBoxLayout()
        fila_masiva.addStretch(1)
        self.btn_eliminar_todos = QPushButton("Eliminar todos")
        self.btn_eliminar_todos.setObjectName("eliminarTodos")
        self.btn_eliminar_todos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar_todos.clicked.connect(self._eliminar_todos)
        fila_masiva.addWidget(self.btn_eliminar_todos)
        layout.addLayout(fila_masiva)
        return pagina

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

        for indice, (item, pagina) in enumerate(self.ITEMS_SIDEBAR):
            boton = QPushButton(item, lateral)
            boton.setObjectName("itemActivo" if pagina == 0 else "item")
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.clicked.connect(lambda checked=False, i=pagina: self._cambiar_vista(i))
            layout.addWidget(boton)
            self._botones_sidebar.append(boton)

        layout.addStretch(1)
        pie = QLabel(f"Sesión: {self.usuario.nombre_usuario}")
        pie.setObjectName("sesion")
        pie.setWordWrap(True)
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pie)
        return lateral

    def _construir_pagina_respaldos(self) -> QWidget:
        """Tercera página: snapshots de gestiones cerradas, solo lectura."""
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        titulo = QLabel("Respaldos")
        titulo.setObjectName("tituloSeccion")
        layout.addWidget(titulo)

        fila_gestion = QHBoxLayout()
        etiqueta = QLabel("Gestión respaldada:")
        etiqueta.setObjectName("etiquetaRespaldo")
        fila_gestion.addWidget(etiqueta)
        self.cmb_respaldo = QComboBox()
        self.cmb_respaldo.setObjectName("comboRespaldo")
        self.cmb_respaldo.currentIndexChanged.connect(
            lambda _i: self._cargar_respaldo(self.cmb_respaldo.currentText()))
        fila_gestion.addWidget(self.cmb_respaldo, 1)
        layout.addLayout(fila_gestion)

        self.lbl_titulo_respaldo = QLabel("Respaldo", pagina)
        self.lbl_titulo_respaldo.setObjectName("tituloRespaldo")
        layout.addWidget(self.lbl_titulo_respaldo)

        self.tabla_respaldos = QTableWidget(0, len(COLUMNAS_RESPALDO))
        self.tabla_respaldos.setHorizontalHeaderLabels(COLUMNAS_RESPALDO)
        self.tabla_respaldos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_respaldos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_respaldos.verticalHeader().setVisible(False)
        cabecera = self.tabla_respaldos.horizontalHeader()
        for i in range(len(COLUMNAS_RESPALDO) - 2):
            cabecera.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        for i in (len(COLUMNAS_RESPALDO) - 2, len(COLUMNAS_RESPALDO) - 1):
            cabecera.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_respaldos, 1)
        return pagina

    def _cargar_respaldo(self, gestion: str):
        """Puebla la tabla con el snapshot (celdas de texto y badges fijos)."""
        self.tabla_respaldos.setRowCount(0)
        self.lbl_titulo_respaldo.setText(
            f"Respaldo de {gestion}" if gestion else "Respaldo")
        if not gestion:
            return
        for i, r in enumerate(gestion_service.leer_respaldo(gestion), start=1):
            fila = self.tabla_respaldos.rowCount()
            self.tabla_respaldos.insertRow(fila)
            for columna, valor in enumerate(
                    [str(i), r.carrera, r.apellidos, r.nombres, r.codigo_estudiante,
                      r.porcentaje_anterior, r.gestion_ingreso or "—"]):
                item = QTableWidgetItem(valor)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla_respaldos.setItem(fila, columna, item)
            for columna, texto, positivo in (
                    (7, "Cumplió" if r.horas_becarias else "No cumplió", r.horas_becarias),
                    (8, "Sí" if r.materias_en_orden else "No", r.materias_en_orden),
                    (9, "Sí" if r.carpeta_cancelada else "No", r.carpeta_cancelada),
                    (10, "Sí" if r.carta_renovacion else "No", r.carta_renovacion)):
                etiqueta = QLabel(texto)
                etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
                etiqueta.setStyleSheet(
                    ESTILO_BADGE_VERDE if positivo else ESTILO_BADGE_ROJO)
                self.tabla_respaldos.setCellWidget(fila, columna, etiqueta)
            estado = QLabel(r.estado)
            estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
            estado.setStyleSheet(estilo_estado(r.estado))
            self.tabla_respaldos.setCellWidget(fila, 11, estado)

    def _construir_pagina_informes(self) -> QWidget:
        """Cuarta página: actas generadas en data/informes/, con Abrir/Eliminar."""
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        fila_titulo = QHBoxLayout()
        titulo = QLabel("Informes — Actas del Comité")
        titulo.setObjectName("tituloSeccion")
        fila_titulo.addWidget(titulo, alignment=Qt.AlignmentFlag.AlignVCenter)
        fila_titulo.addStretch(1)
        self.btn_nuevo_informe = QPushButton("Crear nuevo informe")
        self.btn_nuevo_informe.setObjectName("nuevo")
        self.btn_nuevo_informe.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nuevo_informe.clicked.connect(self._crear_informe)
        fila_titulo.addWidget(self.btn_nuevo_informe)
        layout.addLayout(fila_titulo)

        self.tabla_informes = QTableWidget(0, len(COLUMNAS_INFORMES))
        self.tabla_informes.setHorizontalHeaderLabels(COLUMNAS_INFORMES)
        self.tabla_informes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_informes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_informes.verticalHeader().setVisible(False)
        self.tabla_informes.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_informes, 1)
        return pagina

    @staticmethod
    def _tamano_legible(tamano_bytes: int) -> str:
        """1234 -> '1,2 KB' (coma decimal, formato local)."""
        if tamano_bytes < 1024:
            return f"{tamano_bytes} B"
        kb = tamano_bytes / 1024
        if kb < 1024:
            return f"{kb:.1f} KB".replace(".", ",")
        return f"{kb / 1024:.1f} MB".replace(".", ",")

    def _cargar_informes(self):
        """Puebla la tabla de informes con Abrir/Eliminar por fila."""
        self.tabla_informes.setRowCount(0)
        for i, info in enumerate(informe_service.listar_informes(), start=1):
            fila = self.tabla_informes.rowCount()
            self.tabla_informes.insertRow(fila)
            for columna, valor in enumerate(
                    [str(i), info["nombre"], self._tamano_legible(info["tamano_bytes"])]):
                item = QTableWidgetItem(valor)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla_informes.setItem(fila, columna, item)
            btn_abrir = QPushButton("Abrir")
            btn_abrir.setObjectName("reactivar")
            btn_abrir.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_abrir.clicked.connect(
                lambda checked=False, ruta=info["ruta"]: self._abrir_informe(ruta))
            self.tabla_informes.setCellWidget(fila, 3, btn_abrir)
            btn_eliminar = QPushButton("Eliminar")
            btn_eliminar.setObjectName("eliminar")
            btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_eliminar.clicked.connect(
                lambda checked=False, nombre=info["nombre"]: self._eliminar_informe(nombre))
            self.tabla_informes.setCellWidget(fila, 4, btn_eliminar)
        if self.tabla_informes.rowCount() == 0:
            fila = 0
            self.tabla_informes.insertRow(fila)
            self.tabla_informes.setSpan(fila, 0, 1, len(COLUMNAS_INFORMES))
            item = QTableWidgetItem("Aún no hay informes generados")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            fuente = QFont()
            fuente.setItalic(True)
            item.setFont(fuente)
            item.setForeground(QColor(theme.TEXTO_GRIS))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tabla_informes.setItem(fila, 0, item)

    def _crear_informe(self):
        """Pide N° de acta + nombre y genera el .docx (notifica éxito/error)."""
        dialogo = DialogoNuevoInforme(self)
        if ejecutar_con_overlay(self, dialogo) != DialogoNuevoInforme.DialogCode.Accepted:
            return
        try:
            resultado = informe_service.generar_acta(
                dialogo.numero_acta, nombre_archivo=dialogo.nombre_archivo)
        except Exception as e:
            mostrar_notificacion(self, f"No se pudo generar el informe: {e}", tipo="error")
            return
        self._cargar_informes()
        mostrar_notificacion(
            self, f"Informe {resultado['nombre_archivo']} generado con "
                  f"{resultado['total']} becarios. "
                  f"{resultado['celdas_vacias']} celdas quedaron vacías "
                  "para completar a mano en Word.", tipo="exito")

    def _abrir_informe(self, ruta: str):
        """Abre el .docx con la app predeterminada de Windows."""
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
            mostrar_notificacion(self, "No se pudo abrir el informe.", tipo="error")

    def _eliminar_informe(self, nombre: str):
        """Pide confirmación explícita y elimina el archivo (igual que inactivos)."""
        if not pedir_confirmacion(
                self, f"¿Eliminar permanentemente el informe {nombre}? "
                       "Esta acción no se puede deshacer."):
            return
        try:
            if not informe_service.eliminar_informe(nombre):
                mostrar_notificacion(self, "El informe ya no existe.", tipo="error")
                self._cargar_informes()
                return
        except Exception as e:
            mostrar_notificacion(self, f"No se pudo eliminar: {e}", tipo="error")
            return
        self._cargar_informes()
        mostrar_notificacion(self, "Informe eliminado correctamente.", tipo="exito")

    def _cambiar_vista(self, indice: int):
        """Navegación del sidebar (0 = listado, 1 = inactivos, 2 = respaldos, 3 = informes)."""
        self.paginas.setCurrentIndex(indice)
        for boton, (_etiqueta, pagina) in zip(self._botones_sidebar, self.ITEMS_SIDEBAR):
            boton.setObjectName("itemActivo" if pagina == indice else "item")
        self._apply_style()

    # -- datos (fuente real: JOIN becario + seguimiento_becario) ------------
    def refrescar(self):
        """Recarga ambas vistas (respeta los filtros). El listado principal
        excluye Baja/Inactivo; esos van a la página de inactivos."""
        self._filas_completas = [
            (b.id, b.carrera, b.apellidos, b.nombres, b.codigo_estudiante,
             seg if seg is not None else SeguimientoBecario(
                 id=None, becario_id=b.id, gestion="—"),
             seg.gestion if seg is not None else "—",
             seg,
             b.tipo_beca,
             b.estado)
            for b, seg in becario_service.listar_para_panel()
            if b.estado != "Baja/Inactivo"
        ]
        self._inactivos_completos = [
            (b.id, b.apellidos, b.nombres, b.ci, b.codigo_estudiante, b.carrera)
            for b, _seg in becario_service.listar_inactivos()
        ]
        self._fecha_limite = becario_service.obtener_fecha_limite()
        self.btn_fecha_limite.setToolTip(
            f"Fecha límite vigente: {self._fecha_limite}"
            if self._fecha_limite else "Sin fecha límite")
        self.aplicar_filtro(self.txt_busqueda.text())
        self._filtrar_inactivos(self.txt_busqueda.text())
        actual = self.cmb_respaldo.currentText()
        gestiones = gestion_service.gestiones_respaldadas()
        self.cmb_respaldo.blockSignals(True)
        self.cmb_respaldo.clear()
        self.cmb_respaldo.addItems(gestiones)
        if actual in gestiones:
            self.cmb_respaldo.setCurrentText(actual)
        self.cmb_respaldo.blockSignals(False)
        self._cargar_respaldo(self.cmb_respaldo.currentText())
        self._cargar_informes()

    def _al_escribir(self, texto: str):
        """Filtra en tiempo real con cada tecla (coincidencia parcial)."""
        self.aplicar_filtro(texto)
        self._filtrar_inactivos(texto)

    def _filtrar_inactivos(self, texto: str):
        """Mismo criterio parcial sobre código/nombres/apellidos (sin categoría)."""
        consulta = _normalizar_texto(texto.strip())
        if not consulta:
            self._cargar_inactivos(list(self._inactivos_completos))
            return
        self._cargar_inactivos([
            fila for fila in self._inactivos_completos
            if consulta in _normalizar_texto(fila[4])
            or consulta in _normalizar_texto(fila[3])
            or consulta in _normalizar_texto(fila[2])
            or consulta in _normalizar_texto(f"{fila[3]} {fila[2]}")
            or consulta in _normalizar_texto(f"{fila[2]} {fila[3]}")
        ])

    def _cargar_inactivos(self, filas):
        """Puebla la tabla de inactivos. `filas`: (id, apellidos, nombres, ci, codigo, carrera)."""
        self.tabla_inactivos.setRowCount(0)
        self.btn_eliminar_todos.setVisible(len(filas) > 0)
        for i, (becario_id, apellidos, nombres, ci, codigo, carrera) in enumerate(filas, start=1):
            fila = self.tabla_inactivos.rowCount()
            self.tabla_inactivos.insertRow(fila)
            for columna, valor in enumerate(
                    [str(i), apellidos, nombres, ci, codigo, carrera]):
                item = QTableWidgetItem(valor)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla_inactivos.setItem(fila, columna, item)
            boton = QPushButton("Eliminar")
            boton.setObjectName("eliminar")
            boton.clicked.connect(
                lambda checked=False, bid=becario_id,
                nombre=f"{nombres} {apellidos}": self._eliminar_becario(bid, nombre))
            self.tabla_inactivos.setCellWidget(fila, 6, boton)
            btn_reactivar = QPushButton("Reactivar")
            btn_reactivar.setObjectName("reactivar")
            btn_reactivar.clicked.connect(
                lambda checked=False, bid=becario_id,
                nombre=f"{nombres} {apellidos}": self._reactivar_becario(bid, nombre))
            self.tabla_inactivos.setCellWidget(fila, 7, btn_reactivar)
        if self.tabla_inactivos.rowCount() == 0:
            fila = 0
            self.tabla_inactivos.insertRow(fila)
            self.tabla_inactivos.setSpan(fila, 0, 1, len(COLUMNAS_INACTIVOS))
            item = QTableWidgetItem(TEXTO_SIN_RESULTADOS)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            fuente = QFont()
            fuente.setItalic(True)
            item.setFont(fuente)
            item.setForeground(QColor(theme.TEXTO_GRIS))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tabla_inactivos.setItem(fila, 0, item)

    def _reactivar_becario(self, becario_id: int, nombre: str):
        """Vuelve a 'En renovación' (igual que un becario nuevo). Sin confirmación."""
        try:
            becario_service.actualizar_estado(becario_id, "En renovación")
        except Exception as e:
            mostrar_notificacion(self, f"No se pudo reactivar: {e}", tipo="error")
            return
        self.refrescar()
        mostrar_notificacion(
            self, f"{nombre} vuelve a estar activo (En renovación).", tipo="exito")

    def _eliminar_todos(self):
        """Vacía TODOS los inactivos (conjunto completo, aunque haya texto filtrando).

        El mensaje dice el N exacto para que no haya sorpresas.
        """
        total = len(self._inactivos_completos)
        if total == 0:
            return
        if not pedir_confirmacion(
                self, f"¿Eliminar permanentemente a los {total} becarios"
                      " inactivos? Esta acción no se puede deshacer."):
            return
        try:
            eliminados = becario_service.eliminar_inactivos()
        except Exception as e:
            mostrar_notificacion(self, f"No se pudo eliminar: {e}", tipo="error")
            return
        self.refrescar()
        mostrar_notificacion(
            self, f"Se eliminaron {eliminados} becarios inactivos.", tipo="exito")

    def _eliminar_becario(self, becario_id: int, nombre: str):
        """Pide confirmación explícita y elimina (becario + seguimientos)."""
        if not pedir_confirmacion(
                self, f"¿Eliminar permanentemente a {nombre}? Esta acción no se puede deshacer."):
            return
        try:
            becario_service.eliminar_becario(becario_id)
        except Exception as e:
            mostrar_notificacion(self, f"No se pudo eliminar: {e}", tipo="error")
            return
        self.refrescar()
        mostrar_notificacion(self, "Becario eliminado correctamente.", tipo="exito")

    def _fila_es_pendiente(self, fila) -> bool:
        """True si la fila (tupla de _filas_completas) incumple requisitos.

        Evalúa sobre la caché, sin consultas: usa el seguimiento real si
        existe, si no el de exhibición. Sin fecha límite nunca es pendiente.
        """
        (_bid, _carrera, _ape, _nom, _cod, seg_mostrar, _gestion,
         seg_real, _tipo, estado) = fila
        return becario_service.incumple_requisitos(
            estado, seg_real if seg_real is not None else seg_mostrar,
            self._fecha_limite)

    def contar_pendientes(self) -> int:
        """Cuántos vencidos hay en el listado (para el menú Filtrar)."""
        return sum(1 for fila in self._filas_completas if self._fila_es_pendiente(fila))

    def aplicar_filtro(self, texto: str):
        """Aplica texto Y categoría Y pendientes a la vez: solo pasa la intersección.

        El código filtra por "empieza con"; nombres/apellidos por "contiene".
        Vacío + "Todas" = todo. "Todas" limpia categoría y pendientes, y
        conserva el texto escrito.
        """
        consulta = _normalizar_texto(texto.strip())
        categoria = self._categoria_filtro
        solo_pendientes = self._solo_pendientes
        if not consulta and categoria is None and not solo_pendientes:
            self.cargar_seguimientos(list(self._filas_completas))
            return
        filtradas = [
            fila for fila in self._filas_completas
            if (not consulta
                or _normalizar_texto(fila[4]).startswith(consulta)
                or consulta in _normalizar_texto(fila[3])
                or consulta in _normalizar_texto(fila[2])
                or consulta in _normalizar_texto(f"{fila[3]} {fila[2]}")
                or consulta in _normalizar_texto(f"{fila[2]} {fila[3]}"))
            and (categoria is None or fila[8] == categoria)
            and (not solo_pendientes or self._fila_es_pendiente(fila))
        ]
        self.cargar_seguimientos(filtradas)

    def cargar_seguimientos(self, filas):
        """Puebla la tabla. `filas`: (becario_id, carrera, apellidos,
        nombres, codigo, SeguimientoBecario a mostrar, gestion, SeguimientoBecario
        real o None si aún no tiene registro, tipo_beca, estado)."""
        self.tabla.setRowCount(0)
        self._ids_fila = []
        self._menu_info = {}
        for i, (becario_id, carrera, apellidos, nombres, codigo, seg, gestion, real, _tipo, estado) in enumerate(filas, start=1):
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
            self._celda_badge_menu(fila, 7, becario_id, "horas_becarias",
                                     seg.horas_becarias,
                                     real.gestion if real is not None else None)
            self._celda_badge_menu(fila, 8, becario_id, "materias_en_orden",
                                     seg.materias_en_orden,
                                     real.gestion if real is not None else None)
            self._celda_badge_menu(fila, 9, becario_id, "carpeta_cancelada",
                                     seg.carpeta_cancelada,
                                     real.gestion if real is not None else None)
            self._celda_badge_menu(fila, 10, becario_id, "carta_renovacion",
                                     seg.carta_renovacion,
                                     real.gestion if real is not None else None)
            self._celda_badge_menu(fila, 11, becario_id, "estado", estado, None)
            if becario_service.incumple_requisitos(
                    estado, real if real is not None else seg, self._fecha_limite):
                self._resaltar_fila_vencida(fila)
        if not self._anchos_proporcionales_listos and self.isVisible():
            if self._aplicar_anchos_proporcionales():
                self._anchos_proporcionales_listos = True
        self._reabreviar_badges()
        if self.tabla.rowCount() == 0:
            self._fila_sin_resultados()

    def _resaltar_fila_vencida(self, fila_visible: int):
        """Tiñe las celdas de texto de la fila (los badges no se tocan)."""
        for columna in range(INDICE_COLUMNA_CODIGO + 3):  # 0..6: solo texto
            item = self.tabla.item(fila_visible, columna)
            if item is not None:
                item.setBackground(FONDO_FILA_VENCIDA)
                item.setToolTip(TOOLTIP_VENCIDO)

    def _quitar_resaltado_fila(self, fila_visible: int):
        """Devuelve la fila a su fondo normal (tras cumplir los requisitos)."""
        for columna in range(INDICE_COLUMNA_CODIGO + 3):
            item = self.tabla.item(fila_visible, columna)
            if item is not None:
                item.setBackground(QBrush())
                item.setToolTip("")

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

    def _celda_badge_menu(self, fila: int, columna: int, becario_id: int,
                            campo: str, valor_actual, gestion: str | None):
        """Badge clickeable: mano, tooltip y desplegable con opciones válidas."""
        etiqueta = QLabel()
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiqueta.setCursor(Qt.CursorShape.PointingHandCursor)
        etiqueta.installEventFilter(self)
        self._menu_info[etiqueta] = {
            "becario_id": becario_id, "campo": campo,
            "valor": valor_actual, "gestion": gestion,
            "columna": columna, "completo": "",
        }
        self._pintar_badge(etiqueta, campo, valor_actual)
        self.tabla.setCellWidget(fila, columna, etiqueta)

    def _texto_visible_badge(self, columna: int, completo: str, fuente) -> str:
        """Completo si cabe; si no, abreviatura fija; "…" solo al final."""
        disponible = max(20, self.tabla.columnWidth(columna) - MARGEN_BADGE_PX)
        metricas = QFontMetrics(fuente)
        if metricas.horizontalAdvance(completo) <= disponible:
            return completo
        fija = _ABREVIATURAS_FIJAS.get(completo)
        if fija is not None and metricas.horizontalAdvance(fija) <= disponible:
            return fija
        return metricas.elidedText(completo, Qt.TextElideMode.ElideRight, disponible)

    def _pintar_badge(self, etiqueta: QLabel, campo: str, valor):
        """Texto (abreviado si no cabe) + estilo + tooltip con valor completo."""
        info = self._menu_info.get(etiqueta, {})
        completo = _texto_opcion(campo, valor)
        info["valor"] = valor
        info["completo"] = completo
        etiqueta.setText(self._texto_visible_badge(
            info.get("columna", 0), completo, etiqueta.font()))
        etiqueta.setStyleSheet(_estilo_opcion(campo, valor))
        etiqueta.setToolTip(f"{completo} — Clic para cambiar")

    def _reabreviar_badges(self):
        """Re-abrevia los badges al ancho actual (tras poblar o redimensionar)."""
        for etiqueta, info in self._menu_info.items():
            etiqueta.setText(self._texto_visible_badge(
                info.get("columna", 0), info.get("completo", ""), etiqueta.font()))

    def _aplicar_anchos_proporcionales(self) -> bool:
        """Reparte el ancho visible según PESOS_COLUMNAS (sin scroll)."""
        base = max(0, self.tabla.viewport().width())
        if base <= 0:
            return False
        for i, peso in enumerate(PESOS_COLUMNAS):
            self.tabla.setColumnWidth(i, max(30, base * peso // 100))
        self._ajustar_encabezados_al_ancho()
        self._reabreviar_badges()
        return True

    def _ajustar_encabezados_al_ancho(self):
        """Título completo en dos líneas; corto ("C. C.") solo si no cabe."""
        fuente = QFontMetrics(self.tabla.horizontalHeader().font())
        for columna, corto in _ABREVIATURAS_ENCABEZADO.items():
            largo = COLUMNAS[columna]
            linea_mayor = max(largo.split("\n"), key=len)
            if fuente.horizontalAdvance(linea_mayor) + 12 <= self.tabla.columnWidth(columna):
                texto = largo
            else:
                texto = corto
            if (item := self.tabla.horizontalHeaderItem(columna)) is not None:
                item.setText(texto)

    def eventFilter(self, obj, event):
        if obj is self.tabla and event.type() == QEvent.Type.Resize:
            # Diferido: aquí el viewport aún tiene el tamaño anterior.
            self._programar_reajuste_columnas()
            return False
        if (event.type() == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
                and obj in self._menu_info):
            self._mostrar_menu_opciones(obj)
            return True
        return super().eventFilter(obj, event)

    def _construir_menu_opciones(self, etiqueta: QLabel):
        """Arma el desplegable (sin mostrarlo): una acción por opción válida,
        marcada la actual. Cerrar sin elegir no cambia nada."""
        info = self._menu_info.get(etiqueta)
        menu = QMenu(self)
        menu.setObjectName("menuFiltrar")  # reutiliza el estilo del dropdown
        if info is None:
            return menu
        for opcion in _opciones_campo(info["campo"]):
            accion = menu.addAction(_texto_opcion(info["campo"], opcion))
            accion.setCheckable(True)
            accion.setChecked(opcion == info["valor"])
            accion.triggered.connect(
                lambda checked=False, o=opcion: self._elegir_opcion(etiqueta, o)
            )
        return menu

    def _mostrar_menu_opciones(self, etiqueta: QLabel):
        self._construir_menu_opciones(etiqueta).exec(QCursor.pos())

    def _elegir_opcion(self, etiqueta: QLabel, opcion):
        """Guarda la opción elegida y refleja el cambio sin recargar todo.

        Vía rápida: actualiza la celda en su sitio (texto + estilo
        idénticos) y la caché de filas. Solo el pase a "Baja/Inactivo"
        toca la página de inactivos (quitar la fila aquí y recargarla
        allá). Sin cambios de aspecto ni de comportamiento del menú:
        cerrar sin elegir no dispara esto y conserva el valor anterior.
        """
        info = self._menu_info.get(etiqueta)
        if info is None:
            return
        if opcion == info["valor"]:
            return
        try:
            campo, bid = info["campo"], info["becario_id"]
            if campo == "horas_becarias":
                becario_service.actualizar_horas_becarias(bid, info["gestion"], opcion)
            elif campo == "materias_en_orden":
                becario_service.actualizar_materias_en_orden(bid, info["gestion"], opcion)
            elif campo == "carpeta_cancelada":
                becario_service.actualizar_carpeta_cancelada(bid, info["gestion"], opcion)
            elif campo == "carta_renovacion":
                becario_service.actualizar_carta_renovacion(bid, info["gestion"], opcion)
            else:
                becario_service.actualizar_estado(bid, opcion)
        except Exception as e:
            mostrar_notificacion(self, f"No se pudo guardar el cambio: {e}", tipo="error")
            return
        self._reflejar_cambio_en_listado(etiqueta, info["campo"], info["becario_id"], opcion, info)

    def _reflejar_cambio_en_listado(self, etiqueta: QLabel, campo: str,
                                    becario_id: int, nuevo_valor, info: dict):
        """Actualiza la celda/fila afectada sin reconstruir la tabla."""
        if campo == "estado":
            self._reflejar_cambio_estado(etiqueta, becario_id, nuevo_valor)
            return
        if info.get("gestion") is None or info.get("gestion") == "—":
            self.refrescar()  # caso raro sin seguimiento: recarga completa
            return
        if self._actualizar_cache_campo(becario_id, campo, nuevo_valor):
            self._pintar_badge(etiqueta, campo, nuevo_valor)
            self._tras_cambio_flag(becario_id)
        else:
            self.refrescar()

    def _actualizar_cache_campo(self, becario_id: int, campo: str, nuevo_valor) -> bool:
        """Actualiza el seguimiento en caché. False si el becario no está."""
        for fila in self._filas_completas:
            if fila[0] == becario_id:
                for seg in (fila[5], fila[7]):
                    if seg is not None:
                        setattr(seg, campo, bool(nuevo_valor))
                return True
        return False

    def reflejar_cambio_externo(self, becario_id: int, campo: str, nuevo_valor: bool):
        """Refleja un cambio guardado desde la ficha (misma vía rápida, sin recargar).

        Solo los 4 campos de seguimiento llegan aquí (la ficha no edita
        estado); inactivos y respaldos no dependen de ellos.
        """
        if campo not in ("horas_becarias", "materias_en_orden",
                         "carpeta_cancelada", "carta_renovacion"):
            return
        if not self._actualizar_cache_campo(becario_id, campo, nuevo_valor):
            return
        for etiqueta, info in self._menu_info.items():
            if info.get("becario_id") == becario_id and info.get("campo") == campo:
                self._pintar_badge(etiqueta, campo, bool(nuevo_valor))
                break
        self._tras_cambio_flag(becario_id)

    def _tras_cambio_flag(self, becario_id: int):
        """Reevalúa el vencimiento tras marcar un flag, sin recarga completa.

        Si sigue pendiente, asegura el resaltado; si dejó de serlo, lo
        quita; y si la vista está filtrada en "Pendientes", la fila sale
        de la vista (igual que un pase a Baja/Inactivo).
        """
        indice_cache = next(
            (i for i, fila in enumerate(self._filas_completas) if fila[0] == becario_id), None)
        if indice_cache is None:
            return
        pendiente = self._fila_es_pendiente(self._filas_completas[indice_cache])
        fila_visible = self._indice_visible_de_becario(becario_id)
        if fila_visible is None:
            return
        if pendiente:
            self._resaltar_fila_vencida(fila_visible)
            return
        self._quitar_resaltado_fila(fila_visible)
        if self._solo_pendientes:
            self._olvidar_badges_de_fila(fila_visible)
            self.tabla.removeRow(fila_visible)
            self._ids_fila.pop(fila_visible)
            self._renumerar_columna_n()
            if not self._ids_fila:
                self._fila_sin_resultados()

    def _reflejar_cambio_estado(self, etiqueta: QLabel, becario_id: int, nuevo_estado: str):
        """Refleja el cambio de estado: badge en sitio, o salida a inactivos."""
        indice_cache = next(
            (i for i, fila in enumerate(self._filas_completas) if fila[0] == becario_id), None)
        if indice_cache is None:
            self.refrescar()
            return
        if nuevo_estado == "Baja/Inactivo":
            self._filas_completas.pop(indice_cache)
            fila_visible = self._indice_visible_de_becario(becario_id)
            if fila_visible is not None:
                self._olvidar_badges_de_fila(fila_visible)
                self.tabla.removeRow(fila_visible)
                self._ids_fila.pop(fila_visible)
                self._renumerar_columna_n()
                if not self._ids_fila:
                    self._fila_sin_resultados()
            self._recargar_inactivos()
            return
        fila = self._filas_completas[indice_cache]
        self._filas_completas[indice_cache] = (
            fila[0], fila[1], fila[2], fila[3], fila[4], fila[5],
            fila[6], fila[7], fila[8], nuevo_estado)
        self._pintar_badge(etiqueta, "estado", nuevo_estado)

    def _indice_visible_de_becario(self, becario_id: int) -> int | None:
        """Fila visible del becario en la tabla (None si el filtro la oculta)."""
        try:
            return self._ids_fila.index(becario_id)
        except ValueError:
            return None

    def _olvidar_badges_de_fila(self, fila_visible: int):
        """Limpia el registro del menú de los 5 badges de la fila eliminada."""
        for columna in (7, 8, 9, 10, 11):
            insignia = self.tabla.cellWidget(fila_visible, columna)
            if insignia in self._menu_info:
                del self._menu_info[insignia]

    def _renumerar_columna_n(self):
        """Reescribe la columna N. (1..n) tras quitar una fila visible."""
        if len(self._ids_fila) != self.tabla.rowCount():
            return
        for numero in range(self.tabla.rowCount()):
            celda = self.tabla.item(numero, 0)
            if celda is not None:
                celda.setText(str(numero + 1))

    def _recargar_inactivos(self):
        """Actualiza solo la página de inactivos (barato: 1 consulta + filtro)."""
        self._inactivos_completos = [
            (b.id, b.apellidos, b.nombres, b.ci, b.codigo_estudiante, b.carrera)
            for b, _seg in becario_service.listar_inactivos()
        ]
        self._filtrar_inactivos(self.txt_busqueda.text())

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
        "Pendientes (N)" filtra solo requisitos vencidos (fecha límite manual).
        """
        menu = QMenu(self)
        menu.setObjectName("menuFiltrar")
        conteos = becario_service.contar_becarios_por_categoria()
        total = len(self._filas_completas)  # todas las filas, incluso sin categoría
        accion_todas = menu.addAction(f"Todas las categorías ({total})")
        accion_todas.setCheckable(True)
        accion_todas.setChecked(self._categoria_filtro is None and not self._solo_pendientes)
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
        menu.addSeparator()
        pendientes = self.contar_pendientes()
        accion_pend = menu.addAction(f"Pendientes ({pendientes})")
        accion_pend.setCheckable(True)
        accion_pend.setChecked(self._solo_pendientes)
        accion_pend.triggered.connect(lambda: self._elegir_pendientes())
        return menu

    def _elegir_categoria(self, categoria: str | None):
        """Fija el filtro de categoría ("Todas" lo limpia, conserva el texto)."""
        self._categoria_filtro = categoria
        self._solo_pendientes = False
        if categoria is None:
            etiqueta = "Filtrar"
        elif categoria == "":
            etiqueta = "Filtrar: Sin categoría"
        else:
            etiqueta = f"Filtrar: {categoria}"
        self.btn_filtrar.setText(etiqueta)
        self.aplicar_filtro(self.txt_busqueda.text())

    def _elegir_pendientes(self):
        """Filtra solo vencidos (exclusivo: limpia la categoría, conserva el texto)."""
        self._solo_pendientes = True
        self._categoria_filtro = None
        self.btn_filtrar.setText("Filtrar: Pendientes")
        self.aplicar_filtro(self.txt_busqueda.text())

    def _definir_fecha_limite(self):
        """Abre el diálogo de fecha límite; al guardar refresca y notifica."""
        dialogo = DialogoFechaLimite(self, fecha_actual=self._fecha_limite)
        if ejecutar_con_overlay(self, dialogo) != DialogoFechaLimite.DialogCode.Accepted:
            return
        try:
            guardada = becario_service.guardar_fecha_limite(dialogo.fecha_iso)
        except ValueError as e:
            mostrar_notificacion(self, str(e), tipo="error")
            return
        self.refrescar()
        if guardada is None:
            mostrar_notificacion(self, "Fecha límite eliminada: sin vencidos.", tipo="exito")
        else:
            mostrar_notificacion(
                self, f"Fecha límite guardada: {guardada} "
                      f"({self.contar_pendientes()} pendientes).", tipo="exito")

    def _abrir_editar(self, fila: int, columna: int):
        """Doble clic en una fila: columna Código abre solo el SIAC;
        el resto abre la ventana de editar (HU-02)."""
        if not 0 <= fila < len(self._ids_fila):
            return
        if columna == INDICE_COLUMNA_CODIGO:
            item = self.tabla.item(fila, INDICE_COLUMNA_CODIGO)
            if item is not None:
                abrir_perfil_siac(item.text())
            return
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
            QPushButton#item {{
                color: {theme.TEXTO_SECUNDARIO}; font-size: 14px; font-weight: 600;
                padding: 10px 18px; text-align: left;
                background: transparent; border: none;
                border-left: 3px solid transparent;
            }}
            QPushButton#item:hover {{ color: {theme.TEXTO_PRINCIPAL}; }}
            QPushButton#itemActivo {{
                color: {theme.VERDE_LIMA}; font-size: 14px; font-weight: 700;
                padding: 10px 18px; text-align: left;
                background: transparent; border: none;
                border-left: 3px solid {theme.VERDE_LIMA};
            }}
            QPushButton#eliminar {{
                background-color: {theme.BLANCO_TARJETA}; color: {theme.TEXTO_ERROR_CLARO};
                font-size: 12px; font-weight: 700;
                border: 1px solid {theme.TEXTO_ERROR_CLARO}; border-radius: 8px; padding: 6px 12px;
            }}
            QPushButton#eliminar:hover {{
                background-color: {theme.TEXTO_ERROR_CLARO}; color: #ffffff;
            }}
            QPushButton#eliminarTodos {{
                background-color: {theme.TEXTO_ERROR_CLARO}; color: #ffffff;
                font-size: 14px; font-weight: 800; border: none;
                border-radius: 8px; padding: 12px 28px;
            }}
            QPushButton#eliminarTodos:hover {{
                background-color: {theme.TEXTO_ERROR}; color: #ffffff;
            }}
            QPushButton#reactivar {{
                background-color: {theme.VERDE_LIMA}; color: #0a1633;
                font-size: 12px; font-weight: 800; border: none;
                border-radius: 8px; padding: 6px 12px;
            }}
            QPushButton#reactivar:hover {{ background-color: {theme.VERDE_LIMA_HOVER}; }}
            QLabel#sesion {{ color: {theme.TEXTO_SECUNDARIO}; font-size: 11px; }}
            QLabel#tituloSeccion {{ color: {theme.TEXTO_OSCURO}; font-size: 22px; font-weight: 800; }}
            QLabel#lupa {{ color: {theme.TEXTO_GRIS}; font-size: 18px; }}
            QLineEdit {{
                background-color: {theme.CAMPO_FONDO}; color: {theme.TEXTO_OSCURO};
                border: 1px solid {theme.BORDE_SUAVE}; border-radius: 8px; padding: 10px;
                font-size: 13px;
            }}
            QLabel#etiquetaRespaldo {{ color: {theme.TEXTO_GRIS}; font-size: 13px; font-weight: 600; }}
            QLabel#tituloRespaldo {{ color: {theme.TEXTO_OSCURO}; font-size: 16px; font-weight: 800; }}
            QComboBox#comboRespaldo {{
                background-color: {theme.CAMPO_FONDO}; color: {theme.TEXTO_OSCURO};
                border: 1px solid {theme.BORDE_SUAVE}; border-radius: 8px; padding: 10px;
                font-size: 13px;
            }}
            QComboBox#comboRespaldo QAbstractItemView {{
                background-color: {theme.CAMPO_FONDO}; color: {theme.TEXTO_OSCURO};
                selection-background-color: #ecfccb; selection-color: {theme.TEXTO_OSCURO};
                border: 1px solid {theme.BORDE_SUAVE}; outline: 0;
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
