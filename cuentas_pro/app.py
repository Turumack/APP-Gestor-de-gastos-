"""Entrypoint de Reflex — registra la app y todas sus rutas."""
import reflex as rx
from cuentas_pro import theme as T
from cuentas_pro import db as _db  # noqa: F401  (crea tablas SQLite al importar)
from cuentas_pro.pages import (
    home_page, resumen_page, ingresos_page,
    gastos_page, compras_page, cajas_page, inversiones_page, baul_page,
    presupuestos_page, configuracion_page,
)
from cuentas_pro.state.resumen import ResumenState
from cuentas_pro.state.ingresos import IngresosState
from cuentas_pro.state.gastos import GastosState
from cuentas_pro.state.compras import ComprasState
from cuentas_pro.state.cajas import CajasState
from cuentas_pro.state.inversiones import InversionesState
from cuentas_pro.state.baul import BaulState
from cuentas_pro.state.presupuestos import PresupuestosState
from cuentas_pro.state.config import ConfigState


app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="violet",
        radius="large",
        scaling="100%",
    ),
    style=T.GLOBAL_CSS,
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap",
    ],
    head_components=[
        rx.el.link(rel="icon", type="image/svg+xml", href="/axium_icon.svg"),
    ],
)

app.add_page(home_page,        route="/",            title="Minty",
             on_load=ResumenState.load)
app.add_page(resumen_page,     route="/resumen",     title="Resumen · Minty",
             on_load=ResumenState.load)
app.add_page(ingresos_page,    route="/ingresos",    title="Ingresos · Minty",
             on_load=IngresosState.load)
app.add_page(gastos_page,      route="/gastos",      title="Gastos · Minty",
             on_load=GastosState.load)
app.add_page(compras_page,     route="/compras",     title="Listas de compra · Minty",
             on_load=ComprasState.load)
app.add_page(cajas_page,       route="/cajas",       title="Cajas · Minty",
             on_load=CajasState.load)
app.add_page(inversiones_page, route="/inversiones", title="Inversiones · Minty",
             on_load=InversionesState.load)
app.add_page(baul_page,        route="/baul",        title="Baúl · Minty",
             on_load=BaulState.load)
app.add_page(presupuestos_page, route="/presupuestos", title="Presupuestos · Minty",
             on_load=PresupuestosState.load)
app.add_page(configuracion_page, route="/configuracion", title="Configuración · Minty",
             on_load=ConfigState.load)
