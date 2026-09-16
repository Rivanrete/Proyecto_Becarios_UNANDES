"""Punto de entrada — HU-01 (credencial única).

Flujo: init BD local (+ seed prueba/1234 si está vacía) → muestra login
fullscreen → si login aceptado Y hay sesión activa, muestra principal
fullscreen. Sin sesión no se abre la principal (bloqueo de bypass).
"""
import sys

from PySide6.QtWidgets import QApplication

from app.persistence.database import init_db
from app.services.auth_service import SesionActual, asegurar_credencial_unica
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


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

    principal = MainWindow(SesionActual.usuario)
    principal.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
