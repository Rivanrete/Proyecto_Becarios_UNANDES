"""Punto de entrada — HU-01 (credencial única) + Panel de Control.

Flujo: init BD local (+ seed prueba/1234 si está vacía) → muestra login
maximizado → si login aceptado Y hay sesión activa, muestra el Panel de
Control maximizado. Sin sesión no se abre el panel (bloqueo de bypass).
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import rutas
from app.persistence.database import init_db
from app.services import becario_service
from app.services.auth_service import SesionActual, asegurar_credencial_unica
from app.services.gestion_service import verificar_gestion_activa
from app.ui.becario_form_window import BecarioFormWindow
from app.ui.dialogo_cambio_gestion import DialogoCambioGestion
from app.ui.ficha_becario_window import FichaBecarioWindow
from app.ui.historial_gestiones_window import HistorialGestionesWindow
from app.ui.login_window import LoginWindow
from app.ui.notificacion import mostrar_notificacion
from app.ui.overlay import ejecutar_con_overlay, mostrar_sin_bloqueo
from app.ui.panel_control_window import PanelControlWindow


def _abrir_formulario(panel: PanelControlWindow, becario_id: int | None):
    """Abre el formulario HU-02 (nuevo o editar) sin bloquear, con overlay.

    Sesiones no modales: el formulario se cierra con X, Cancelar, Esc o
    clic fuera; el historial (si hay) lo cierra el formulario al terminar.
    Si ya hay una sesión abierta se ignora el pedido (sin overlays apilados).
    """
    if getattr(panel, "_sesion_modal", None) is not None:
        return
    dialogo = BecarioFormWindow(panel, becario_id=becario_id)
    if becario_id is None:
        panel._sesion_modal = mostrar_sin_bloqueo(
            panel, dialogo, al_terminar=lambda r: _tras_formulario(panel, dialogo, r))
    else:
        lateral = HistorialGestionesWindow(
            panel, gestiones=becario_service.historial_gestiones(becario_id))
        panel._sesion_modal = mostrar_sin_bloqueo(
            panel, dialogo, lateral=lateral,
            al_terminar=lambda r: _tras_formulario(panel, dialogo, r))


def _tras_formulario(panel: PanelControlWindow, dialogo: BecarioFormWindow, resultado: int):
    """Limpieza al cerrar el formulario + refresco y aviso si se guardó."""
    panel._sesion_modal = None
    if resultado == BecarioFormWindow.DialogCode.Accepted:
        panel.refrescar()
        if dialogo.mensaje_exito:
            mostrar_notificacion(panel, dialogo.mensaje_exito, tipo="exito")


def _mostrar_aviso_gestion_si_cambio(panel: PanelControlWindow,
                                anterior: str | None, actual: str, hubo_cambio: bool,
                                detalle: dict | None):
    """Muestra una sola vez el aviso del cambio recién aplicado.

    Solo si hubo transición real (con gestión anterior y números del
    proceso). Sin cambio no muestra nada. Se invoca con el panel ya
    visible, nunca antes ni detrás del login.
    """
    if not (hubo_cambio and anterior and detalle):
        return
    dialogo = DialogoCambioGestion(
        panel, anterior=anterior, nueva=actual,
        respaldados=detalle["respaldados"],
        reiniciados=detalle["reiniciados"],
        sin_modificar=detalle["sin_modificar"])
    QTimer.singleShot(
        0, lambda: ejecutar_con_overlay(panel, dialogo))


def _buscar_y_mostrar_ficha(panel: PanelControlWindow):
    """HU-04: el Enter del buscador abre la ficha consolidada.

    El botón Filtrar NO dispara esto (solo abre su dropdown HU-06);
    por eso un clic en Filtrar con texto vacío jamás muestra el aviso.
    Con resultado abre la ficha; sin resultado notifica con el
    componente propio (sin QMessageBox nativo). Texto vacío = no hace nada.
    """
    texto = panel.txt_busqueda.text().strip()
    if not texto:
        return
    encontrado = becario_service.buscar_becario(texto)
    if encontrado is None:
        mostrar_notificacion(
            panel, f"No se encontraron resultados para '{texto}'.", tipo="error"
        )
        return
    ficha = becario_service.obtener_ficha_completa(encontrado.id)
    if ficha is None:
        mostrar_notificacion(panel, "No se encontraron resultados.", tipo="error")
        return
    ejecutar_con_overlay(panel, FichaBecarioWindow(panel, ficha=ficha))


def main() -> int:
    init_db()  # ya incluye el seed único; llamada idempotente extra por seguridad
    asegurar_credencial_unica()
    # El cambio de gestión se aplica aquí (antes del login, en silencio);
    # el aviso se muestra después, con el panel ya visible (una sola vez).
    gestion_anterior, gestion_actual, hubo_cambio, detalle_cambio = verificar_gestion_activa()

    app = QApplication(sys.argv)
    icono = rutas.assets_dir() / "icono-unandes.ico"
    if icono.is_file():
        app.setWindowIcon(QIcon(str(icono)))

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
    # HU-04: el Enter del buscador abre la ficha del becario.
    # (El botón Filtrar solo abre su dropdown HU-06; no busca la ficha.)
    principal.txt_busqueda.returnPressed.connect(lambda: _buscar_y_mostrar_ficha(principal))
    principal.showMaximized()
    _mostrar_aviso_gestion_si_cambio(
        principal, gestion_anterior, gestion_actual, hubo_cambio, detalle_cambio)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
