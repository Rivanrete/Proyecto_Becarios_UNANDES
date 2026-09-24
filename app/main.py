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
    panel._sesion_modal = None
    if resultado == BecarioFormWindow.DialogCode.Accepted:
        panel.refrescar()
        if dialogo.mensaje_exito:
            mostrar_notificacion(panel, dialogo.mensaje_exito, tipo="exito")


def _mostrar_aviso_gestion_si_cambio(panel: PanelControlWindow,
                                anterior: str | None, actual: str, hubo_cambio: bool,
                                detalle: dict | None):
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
    ventana_ficha = FichaBecarioWindow(panel, ficha=ficha)
    ventana_ficha.cambio_guardado.connect(panel.reflejar_cambio_externo)
    ejecutar_con_overlay(panel, ventana_ficha)


def main() -> int:
    init_db()
    asegurar_credencial_unica()
    gestion_anterior, gestion_actual, hubo_cambio, detalle_cambio = verificar_gestion_activa()

    app = QApplication(sys.argv)
    icono = rutas.assets_dir() / "icono-unandes.ico"
    if icono.is_file():
        app.setWindowIcon(QIcon(str(icono)))

    login = LoginWindow()
    if login.exec() != LoginWindow.DialogCode.Accepted:
        return 0
    if not SesionActual.activa() or SesionActual.usuario is None:
        return 0

    principal = PanelControlWindow(SesionActual.usuario)
    principal.nuevo_becario_solicitado.connect(lambda: _abrir_formulario(principal, None))
    principal.becario_editar_solicitado.connect(lambda bid: _abrir_formulario(principal, bid))
    principal.txt_busqueda.returnPressed.connect(lambda: _buscar_y_mostrar_ficha(principal))
    principal.showMaximized()
    _mostrar_aviso_gestion_si_cambio(
        principal, gestion_anterior, gestion_actual, hubo_cambio, detalle_cambio)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
