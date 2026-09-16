"""Punto de entrada — HU-01 (credencial única) + Panel de Control.

Flujo: init BD local (+ seed prueba/1234 si está vacía) → muestra login
maximizado → si login aceptado Y hay sesión activa, muestra el Panel de
Control maximizado. Sin sesión no se abre el panel (bloqueo de bypass).
"""
import sys

from PySide6.QtCore import (
    QEasingCurve,
    QEventLoop,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QWidget

from app.persistence.database import init_db
from app.services.auth_service import SesionActual, asegurar_credencial_unica
from app.ui.becario_form_window import BecarioFormWindow
from app.ui.login_window import LoginWindow
from app.ui.panel_control_window import PanelControlWindow

DURACION_ENTRADA_MS = 250
DURACION_SALIDA_MS = 150
DESPLAZAMIENTO_ENTRADA_PX = 12


def _mostrar_overlay(panel: PanelControlWindow) -> QWidget:
    """Cubre la ventana principal con un oscurecimiento semitransparente.

    El QDialog por sí solo NO oscurece el fondo en Qt, por eso el overlay
    es un widget explícito que se muestra antes del modal y se destruye
    al cerrarlo (ver _abrir_formulario).
    """
    overlay = QWidget(panel)
    overlay.setObjectName("overlayModal")
    overlay.setGeometry(panel.rect())
    overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
    overlay.show()
    return overlay


def _centrar_en_panel(dialogo: BecarioFormWindow, panel: PanelControlWindow) -> QPoint:
    """Posición centrada del diálogo (solo tarjeta, sin marco) sobre la principal."""
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


def _animacion_entrada(
    overlay: QWidget, dialogo: BecarioFormWindow, pos_final: QPoint
) -> QParallelAnimationGroup:
    """Fade in del overlay + fade in con subida suave del diálogo (250 ms)."""
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
    """Fade out rápido del overlay (150 ms) al cerrar el modal."""
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


def _abrir_formulario(panel: PanelControlWindow, becario_id: int | None):
    """Abre el formulario HU-02 (nuevo o editar) sobre el panel oscurecido.

    Entrada animada (overlay + tarjeta) y salida con fade del overlay.
    El overlay se destruye siempre al cerrar (Guardar, Cancelar, ✕ o Esc),
    sin dejar residuos ni bloquear el panel después.
    """
    overlay = _mostrar_overlay(panel)
    try:
        dialogo = BecarioFormWindow(panel, becario_id=becario_id)
        pos_final = _centrar_en_panel(dialogo, panel)
        grupo = _animacion_entrada(overlay, dialogo, pos_final)
        dialogo.show()
        grupo.start()  # corre dentro del loop de exec()
        aceptado = dialogo.exec() == BecarioFormWindow.DialogCode.Accepted
    finally:
        _animacion_salida(overlay)
        overlay.hide()
        overlay.deleteLater()
    if aceptado:
        panel.refrescar()


def main() -> int:
    init_db()  # ya incluye el seed único; llamada idempotente extra por seguridad
    asegurar_credencial_unica()

    app = QApplication(sys.argv)

    login = LoginWindow()
    # Sin showMaximized() previo: el showEvent del login lo maximiza
    # al ejecutarse exec(). La principal hereda el estado
    # con showMaximized() al pasar el login (respeta la barra de tareas).
    if login.exec() != LoginWindow.DialogCode.Accepted:
        return 0  # usuario cerró el login sin autenticarse
    if not SesionActual.activa() or SesionActual.usuario is None:
        return 0  # defensa extra: no abrir principal sin sesión

    principal = PanelControlWindow(SesionActual.usuario)
    # HU-02: "+ Nuevo Becario" abre el formulario en modo nuevo;
    # doble clic en una fila lo abre en modo edición.
    principal.nuevo_becario_solicitado.connect(lambda: _abrir_formulario(principal, None))
    principal.becario_editar_solicitado.connect(lambda bid: _abrir_formulario(principal, bid))
    principal.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
