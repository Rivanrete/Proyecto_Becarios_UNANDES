"""Punto de entrada — HU-01.

Flujo: init BD local → asegura usuario inicial → muestra login →
si login aceptado Y hay sesión activa, muestra pantalla principal.
Sin sesión no se abre la principal (bloqueo de bypass).
"""
import sys

from PySide6.QtWidgets import QApplication

from app.persistence.database import init_db
from app.services.auth_service import SesionActual, asegurar_usuario_inicial
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


def main() -> int:
    init_db()
    asegurar_usuario_inicial()  # provisional, ver auth_service.py

    app = QApplication(sys.argv)

    login = LoginWindow()
    if login.exec() != LoginWindow.DialogCode.Accepted:
        return 0  # usuario cerró el login sin autenticarse
    if not SesionActual.activa() or SesionActual.usuario is None:
        return 0  # defensa extra: no abrir principal sin sesión

    principal = MainWindow(SesionActual.usuario)
    principal.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
