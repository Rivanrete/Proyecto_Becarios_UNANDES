"""Overlay + animación para modales — componente reutilizable del proyecto.

REGLA DE PROYECTO: ningún diálogo nativo del SO (QMessageBox, QInputDialog).
Todo emergente usa overlay de oscurecimiento + animación suave mediante
ejecutar_con_overlay(panel, dialogo) —o mostrar_sin_bloqueo() cuando el
diálogo no debe bloquear. Estándar UX: X propia + clic fuera (overlay) + Esc.

El QDialog por sí solo NO oscurece el fondo en Qt: el overlay es un QWidget
explícito que cubre la ventana principal y se destruye al cerrar el modal.
"""
from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QEventLoop,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QDialog, QFrame, QGraphicsOpacityEffect, QWidget

DURACION_ENTRADA_MS = 250
DURACION_SALIDA_MS = 150
DESPLAZAMIENTO_ENTRADA_PX = 12
OPACIDAD_OVERLAY = "background-color: rgba(0, 0, 0, 120);"


def mostrar_overlay(panel: QWidget) -> QWidget:
    """Cubre la ventana con el oscurecimiento. Se destruye en ejecutar_con_overlay."""
    overlay = QWidget(panel)
    overlay.setObjectName("overlayModal")
    overlay.setGeometry(panel.rect())
    overlay.show()
    return overlay


class _SeguidorVentanaPrincipal(QObject):
    """Mantiene el velo pegado a la ventana y el diálogo centrado en ella.

    El velo nace con el tamaño que tiene la ventana al crearse (a veces
    previo al maximizado); sin este seguidor, al maximizar o redimensionar
    parte de la ventana quedaba sin oscurecer y el diálogo descentrado.
    Solo observa el Resize: nunca consume el evento (retorna False).
    """

    def __init__(self, velo: QWidget, ventana: QWidget, dialogo: QDialog | None = None):
        super().__init__(velo)
        self._velo = velo
        self._ventana = ventana
        self._dialogo = dialogo

    def eventFilter(self, objeto, evento):
        if objeto is self._ventana and evento.type() == QEvent.Type.Resize:
            self._velo.setGeometry(self._ventana.rect())
            if self._dialogo is not None and self._dialogo.isVisible():
                self._dialogo.move(posicion_centrada(self._dialogo, self._ventana))
        return False


def _pegar_velo_a_ventana(velo: QWidget, ventana: QWidget,
                          dialogo: QDialog | None = None):
    """El velo sigue el tamaño de la ventana hasta que se retire."""
    seguidor = _SeguidorVentanaPrincipal(velo, ventana, dialogo)
    ventana.installEventFilter(seguidor)
    return seguidor


def _despegar_velo_de_ventana(ventana: QWidget, seguidor: QObject):
    """Retira el seguidor para no dejar un filtro colgando en la ventana."""
    ventana.removeEventFilter(seguidor)
    seguidor.deleteLater()


def posicion_centrada(dialogo: QDialog, panel: QWidget) -> QPoint:
    """Posición centrada del diálogo (solo tarjeta, sin marco) sobre la ventana."""
    dialogo.adjustSize()
    centro = panel.rect().center()
    return QPoint(
        max(0, centro.x() - dialogo.width() // 2),
        max(0, centro.y() - dialogo.height() // 2),
    )


def _efecto_opacidad(widget: QWidget, inicial: float) -> QGraphicsOpacityEffect:
    efecto = QGraphicsOpacityEffect(widget)
    efecto.setOpacity(inicial)
    widget.setGraphicsEffect(efecto)
    return efecto


def _animacion_entrada(overlay: QWidget, dialogo: QDialog, pos_final: QPoint) -> QParallelAnimationGroup:
    """Fade in del overlay + fade in con subida suave del diálogo."""
    grupo = QParallelAnimationGroup(dialogo)

    anim_overlay = QPropertyAnimation(_efecto_opacidad(overlay, 0.0), b"opacity", overlay)
    anim_overlay.setDuration(DURACION_ENTRADA_MS)
    anim_overlay.setStartValue(0.0)
    anim_overlay.setEndValue(1.0)
    anim_overlay.setEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))
    grupo.addAnimation(anim_overlay)

    anim_opacidad = QPropertyAnimation(_efecto_opacidad(dialogo, 0.0), b"opacity", dialogo)
    anim_opacidad.setDuration(DURACION_ENTRADA_MS)
    anim_opacidad.setStartValue(0.0)
    anim_opacidad.setEndValue(1.0)
    anim_opacidad.setEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))
    grupo.addAnimation(anim_opacidad)

    dialogo.move(pos_final + QPoint(0, DESPLAZAMIENTO_ENTRADA_PX))
    anim_posicion = QPropertyAnimation(dialogo, b"pos", dialogo)
    anim_posicion.setDuration(DURACION_ENTRADA_MS)
    anim_posicion.setStartValue(pos_final + QPoint(0, DESPLAZAMIENTO_ENTRADA_PX))
    anim_posicion.setEndValue(pos_final)
    anim_posicion.setEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))
    grupo.addAnimation(anim_posicion)

    return grupo


def _animacion_salida(overlay: QWidget):
    """Fade out rápido del overlay al cerrar el modal."""
    efecto = overlay.graphicsEffect()
    if not isinstance(efecto, QGraphicsOpacityEffect):
        efecto = _efecto_opacidad(overlay, 1.0)
    animacion = QPropertyAnimation(efecto, b"opacity", overlay)
    animacion.setDuration(DURACION_SALIDA_MS)
    animacion.setStartValue(efecto.opacity())
    animacion.setEndValue(0.0)
    animacion.setEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))
    bucle = QEventLoop()
    animacion.finished.connect(bucle.quit)
    animacion.start()
    bucle.exec()


def ejecutar_con_overlay(panel: QWidget, dialogo: QDialog) -> int:
    """Muestra el diálogo centrado sobre el panel oscurecido y animado.

    Retorna el código de resultado (QDialog.Accepted / Rejected).
    El overlay se destruye siempre al cerrar, sin residuos ni bloqueo.
    """
    overlay = mostrar_overlay(panel)
    seguidor = _pegar_velo_a_ventana(overlay, panel, dialogo)
    try:
        pos_final = posicion_centrada(dialogo, panel)
        grupo = _animacion_entrada(overlay, dialogo, pos_final)
        dialogo.show()
        grupo.start()  # corre dentro del loop de exec()
        overlay.mousePressEvent = lambda event: dialogo.reject()
        return dialogo.exec()
    finally:
        _despegar_velo_de_ventana(panel, seguidor)
        _animacion_salida(overlay)
        overlay.hide()
        overlay.deleteLater()


ESPACIO_LATERAL_PX = 16


def _posicionar_dual(panel: QWidget, dialogo: QDialog, lateral: QDialog) -> QPoint:
    """Ubica el diálogo a la izquierda y el lateral a su derecha.

    Iguala lo VISIBLE (las tarjetas, no solo las ventanas): la tarjeta
    lateral toma el alto exacto de la tarjeta del diálogo y ambas ventanas
    el mismo alto total, con los mismos márgenes -> bordes alineados.
    Retorna la posición del diálogo.
    """
    dialogo.adjustSize()
    lateral.adjustSize()
    tarjeta = dialogo.findChild(QFrame, "card")
    tarjeta_lat = lateral.findChild(QFrame, "cardHistorial")
    if tarjeta is not None and tarjeta_lat is not None:
        tarjeta_lat.setFixedHeight(tarjeta.height())
    lateral.setMinimumHeight(dialogo.height())
    lateral.adjustSize()
    ancho_total = dialogo.width() + ESPACIO_LATERAL_PX + lateral.width()
    x_inicio = max(0, panel.rect().center().x() - ancho_total // 2)
    y_comun = max(0, panel.rect().center().y() - dialogo.height() // 2)
    lateral.move(x_inicio + dialogo.width() + ESPACIO_LATERAL_PX, y_comun)
    return QPoint(x_inicio, y_comun)


def mostrar_sin_bloqueo(panel: QWidget, dialogo: QDialog, lateral: QDialog | None = None,
                        al_terminar=None):
    """Muestra diálogos NO modales sobre overlay (approach: sin exec()).

    - Un clic fuera del diálogo (sobre el overlay) lo cierra vía reject(),
      igual que la X, Cancelar o Esc: sin eventFilter manual.
    - Al cerrarse el principal se cierra el lateral y se limpia el overlay.
    - al_terminar(resultado) se invoca una sola vez al cerrar.
    Retorna el overlay (para rastreo de sesión).
    """
    overlay = mostrar_overlay(panel)
    # El velo sigue a la ventana; los diálogos conservan su posición
    # (el layout dual tiene la suya propia y no se recentra).
    seguidor = _pegar_velo_a_ventana(overlay, panel)
    if lateral is None:
        pos_final = posicion_centrada(dialogo, panel)
    else:
        pos_final = _posicionar_dual(panel, dialogo, lateral)
    grupo = _animacion_entrada(overlay, dialogo, pos_final)
    dialogo.show()
    if lateral is not None:
        lateral.show()
    grupo.start()
    estado = {"terminado": False}

    def _al_cerrar(resultado):
        if estado["terminado"]:
            return
        estado["terminado"] = True
        try:
            if lateral is not None:
                lateral.close()
        finally:
            _despegar_velo_de_ventana(panel, seguidor)
            _animacion_salida(overlay)
            overlay.hide()
            overlay.deleteLater()
        if al_terminar is not None:
            al_terminar(resultado)

    dialogo.finished.connect(_al_cerrar)
    overlay.mousePressEvent = lambda event: dialogo.reject()
    return overlay
