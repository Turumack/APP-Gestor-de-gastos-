"""Entrypoint de Reflex — registra la app y todas sus rutas."""
import reflex as rx
from minty import theme as T
from minty import db as _db  # noqa: F401  (crea tablas SQLite al importar)
from minty.pages import (
    home_page, resumen_page, ingresos_page,
    gastos_page, compras_page, cajas_page, inversiones_page, baul_page,
    presupuestos_page, configuracion_page,
)
from minty.state.resumen import ResumenState
from minty.state.ingresos import IngresosState
from minty.state.gastos import GastosState
from minty.state.compras import ComprasState
from minty.state.cajas import CajasState
from minty.state.inversiones import InversionesState
from minty.state.baul import BaulState
from minty.state.presupuestos import PresupuestosState
from minty.state.config import ConfigState


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

app.add_page(home_page,        route="/",            title="MINTY",
             on_load=ResumenState.load)
app.add_page(resumen_page,     route="/resumen",     title="Resumen · MINTY",
             on_load=ResumenState.load)
app.add_page(ingresos_page,    route="/ingresos",    title="Ingresos · MINTY",
             on_load=IngresosState.load)
app.add_page(gastos_page,      route="/gastos",      title="Gastos · MINTY",
             on_load=GastosState.load)
app.add_page(compras_page,     route="/compras",     title="Listas de compra · MINTY",
             on_load=ComprasState.load)
app.add_page(cajas_page,       route="/cajas",       title="Cajas · MINTY",
             on_load=CajasState.load)
app.add_page(inversiones_page, route="/inversiones", title="Inversiones · MINTY",
             on_load=InversionesState.load)
app.add_page(baul_page,        route="/baul",        title="Baúl · MINTY",
             on_load=BaulState.load)
app.add_page(presupuestos_page, route="/presupuestos", title="Presupuestos · MINTY",
             on_load=PresupuestosState.load)
app.add_page(configuracion_page, route="/configuracion", title="Configuración · MINTY",
             on_load=ConfigState.load)
