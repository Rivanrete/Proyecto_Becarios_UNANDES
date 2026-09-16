"""Punto de entrada — HU-01 (credencial única) + Panel de Control.

Flujo: init BD local (+ seed prueba/1234 si está vacía) → muestra login
maximizado → si login aceptado Y hay sesión activa, muestra el Panel de
Control maximizado. Sin sesión no se abre el panel (bloqueo de bypass).
"""
import sys

from PySide6.QtWidgets import QApplication

from app.persistence.database import init_db
from app.services.auth_service import SesionActual, asegurar_credencial_unica
from app.ui.becario_form_window import BecarioFormWindow
from app.ui.login_window import LoginWindow
from app.ui.notificacion import mostrar_notificacion
from app.ui.overlay import ejecutar_con_overlay
from app.ui.panel_control_window import PanelControlWindow


def _abrir_formulario(panel: PanelControlWindow, becario_id: int | None):
    """Abre el formulario HU-02 (nuevo o editar) y confirma con notificación propia."""
    dialogo = BecarioFormWindow(panel, becario_id=becario_id)
    if ejecutar_con_overlay(panel, dialogo) == BecarioFormWindow.DialogCode.Accepted:
        panel.refrescar()
        if dialogo.mensaje_exito:
            mostrar_notificacion(panel, dialogo.mensaje_exito, tipo="exito")


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
