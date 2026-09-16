"""Overlay + animación para modales — componente reutilizable del proyecto.

REGLA DE PROYECTO: ningún diálogo nativo del SO (QMessageBox, QInputDialog).
Todo emergente usa overlay de oscurecimiento + animación suave mediante
ejecutar_con_overlay(panel, dialogo).

El QDialog por sí solo NO oscurece el fondo en Qt: el overlay es un QWidget
explícito que cubre la ventana principal y se destruye al cerrar el modal.
"""
from PySide6.QtCore import (
    QEasingCurve,
    QEventLoop,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QDialog, QGraphicsOpacityEffect, QWidget

DURACION_ENTRADA_MS = 250
DURACION_SALIDA_MS = 150
DESPLAZAMIENTO_ENTRADA_PX = 12
OPACIDAD_OVERLAY = "background-color: rgba(0, 0, 0, 120);"


def mostrar_overlay(panel: QWidget) -> QWidget:
    """Cubre la ventana con el oscurecimiento. Se destruye en ejecutar_con_overlay."""
    overlay = QWidget(panel)
    overlay.setObjectName("overlayModal")
    overlay.setGeometry(panel.rect())
    overlay.setStyleSheet(OPACIDAD_OVERLAY)
    overlay.show()
    return overlay


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
    try:
        pos_final = posicion_centrada(dialogo, panel)
        grupo = _animacion_entrada(overlay, dialogo, pos_final)
        dialogo.show()
        grupo.start()  # corre dentro del loop de exec()
        return dialogo.exec()
    finally:
        _animacion_salida(overlay)
        overlay.hide()
        overlay.deleteLater()
