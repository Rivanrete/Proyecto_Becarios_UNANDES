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
    overlay = QWidget(panel)
    overlay.setObjectName("overlayModal")
    overlay.setGeometry(panel.rect())
    overlay.setStyleSheet(OPACIDAD_OVERLAY)
    overlay.show()
    return overlay


class _SeguidorVentanaPrincipal(QObject):

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
    seguidor = _SeguidorVentanaPrincipal(velo, ventana, dialogo)
    ventana.installEventFilter(seguidor)
    return seguidor


def _despegar_velo_de_ventana(ventana: QWidget, seguidor: QObject):
    ventana.removeEventFilter(seguidor)
    seguidor.deleteLater()


def posicion_centrada(dialogo: QDialog, panel: QWidget) -> QPoint:
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
    overlay = mostrar_overlay(panel)
    seguidor = _pegar_velo_a_ventana(overlay, panel, dialogo)
    try:
        pos_final = posicion_centrada(dialogo, panel)
        grupo = _animacion_entrada(overlay, dialogo, pos_final)
        dialogo.show()
        grupo.start()
        overlay.mousePressEvent = lambda event: dialogo.reject()
        return dialogo.exec()
    finally:
        _despegar_velo_de_ventana(panel, seguidor)
        _animacion_salida(overlay)
        overlay.hide()
        overlay.deleteLater()


ESPACIO_LATERAL_PX = 16
ANCHO_SIDEBAR_PX = 220


def _posicionar_dual(panel: QWidget, dialogo: QDialog, lateral: QDialog) -> QPoint:
    dialogo.adjustSize()
    lateral.adjustSize()
    tarjeta = dialogo.findChild(QFrame, "card")
    tarjeta_lat = lateral.findChild(QFrame, "cardHistorial")
    if tarjeta is not None and tarjeta_lat is not None:
        tarjeta_lat.setFixedHeight(tarjeta.height())
    lateral.setMinimumHeight(dialogo.height())
    lateral.adjustSize()
    ancho_total = dialogo.width() + ESPACIO_LATERAL_PX + lateral.width()
    izquierda_contenido = ANCHO_SIDEBAR_PX if panel.width() > ANCHO_SIDEBAR_PX else 0
    ancho_contenido = max(0, panel.width() - izquierda_contenido)
    centro_x = izquierda_contenido + ancho_contenido // 2
    x_inicio = min(max(izquierda_contenido, centro_x - ancho_total // 2),
                   max(0, panel.width() - ancho_total))
    alto = dialogo.height()
    y_comun = min(max(0, panel.rect().center().y() - alto // 2),
                  max(0, panel.height() - alto))
    lateral.move(x_inicio + dialogo.width() + ESPACIO_LATERAL_PX, y_comun)
    return QPoint(x_inicio, y_comun)


def mostrar_sin_bloqueo(panel: QWidget, dialogo: QDialog, lateral: QDialog | None = None,
                        al_terminar=None):
    overlay = mostrar_overlay(panel)
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
