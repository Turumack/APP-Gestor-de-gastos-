"""P\u00e1gina Resumen / Dashboard."""
import reflex as rx
from minty import theme as T
from minty.components import main_layout, glass_card, page_title, metric_card
from minty.state.resumen import ResumenState
from minty.state import PeriodoState


def _metric_grid() -> rx.Component:
    return rx.grid(
        metric_card("Ingresos", f"${ResumenState.total_ingresos:,.0f}",
                    "trending-up", T.GREEN),
        metric_card("Gastos", f"${ResumenState.total_gastos:,.0f}",
                    "trending-down", T.PINK),
        metric_card("Balance",
                    f"${ResumenState.balance:,.0f}",
                    "wallet", T.VIOLET),
        metric_card("% Ahorro",
                    f"{ResumenState.pct_ahorro_real:.1f}%",
                    "piggy-bank", T.AMBER),
        columns="4", spacing="4", width="100%",
    )


def _pie_gastos() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.heading("Gastos por categoría", size="4", font_family=T.FONT_HEAD, color=T.TEXT),
            rx.cond(
                ResumenState.gastos_por_categoria.length() > 0,
                rx.recharts.pie_chart(
                    rx.recharts.pie(
                        data=ResumenState.gastos_por_categoria,
                        data_key="value",
                        name_key="name",
                        inner_radius="55%",
                        outer_radius="85%",
                        padding_angle=2,
                        stroke="transparent",
                    ),
                    rx.recharts.legend(
                        vertical_align="bottom",
                        wrapper_style={"color": T.TEXT_MUTED, "font_size": "12px"},
                    ),
                    rx.recharts.graphing_tooltip(
                        content_style={
                            "background": T.BG_SOFT,
                            "border": f"1px solid {T.BORDER}",
                            "border_radius": T.RADIUS_SM,
                            "color": T.TEXT,
                        },
                    ),
                    width="100%",
                    height=320,
                ),
                rx.box(
                    rx.text("Sin gastos para graficar", color=T.TEXT_MUTED, size="2"),
                    padding="60px", text_align="center",
                ),
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def _line_gastos() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.heading("Gasto acumulado del mes", size="4", font_family=T.FONT_HEAD, color=T.TEXT),
            rx.cond(
                ResumenState.gastos_por_dia.length() > 0,
                rx.recharts.area_chart(
                    rx.recharts.area(
                        data_key="acumulado",
                        stroke=T.VIOLET,
                        fill=T.VIOLET,
                        fill_opacity=0.25,
                        stroke_width=2,
                    ),
                    rx.recharts.x_axis(
                        data_key="dia",
                        stroke=T.TEXT_DIM,
                    ),
                    rx.recharts.y_axis(
                        stroke=T.TEXT_DIM,
                    ),
                    rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke=T.BORDER_SOFT),
                    rx.recharts.graphing_tooltip(),
                    data=ResumenState.gastos_por_dia,
                    width="100%",
                    height=320,
                ),
                rx.box(
                    rx.text("Sin datos para graficar", color=T.TEXT_MUTED, size="2"),
                    padding="60px", text_align="center",
                ),
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def _row_reciente(r) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon("trending-down", size=14, color="white"),
            width="32px", height="32px", border_radius="10px",
            background=r["color"],
            display="flex", align_items="center", justify_content="center",
        ),
        rx.vstack(
            rx.text(r["desc"], size="2", color=T.TEXT, weight="medium"),
            rx.hstack(
                rx.text(r["categoria"], size="1", color=r["color"], weight="medium"),
                rx.text("·", size="1", color=T.TEXT_DIM),
                rx.text(r["fecha"], size="1", color=T.TEXT_DIM),
                spacing="1",
            ),
            spacing="1", align="start",
        ),
        rx.spacer(),
        rx.text(f"-${r['monto']:,.0f}", size="2", color=T.PINK, weight="bold"),
        spacing="3", width="100%", align="center",
        padding="10px 12px",
        border_radius=T.RADIUS_SM,
        _hover={"background": "rgba(255,255,255,.03)"},
    )


def _recientes() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.heading("Movimientos recientes", size="4", font_family=T.FONT_HEAD, color=T.TEXT),
                rx.spacer(),
                rx.link(
                    rx.hstack(
                        rx.text("Ver todos", size="2", color=T.VIOLET),
                        rx.icon("arrow-right", size=14, color=T.VIOLET),
                        spacing="1",
                    ),
                    href="/gastos",
                ),
                width="100%", align="center",
            ),
            rx.cond(
                ResumenState.recientes.length() > 0,
                rx.vstack(
                    rx.foreach(ResumenState.recientes, _row_reciente),
                    spacing="1", width="100%",
                ),
                rx.text("Sin movimientos este período.", color=T.TEXT_MUTED, size="2",
                        padding="20px", text_align="center"),
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def _alerta_pres(a) -> rx.Component:
    color = rx.cond(a["estado"] == "excedido", T.RED, T.AMBER)
    icono = rx.cond(a["estado"] == "excedido", "circle-alert", "triangle-alert")
    return rx.hstack(
        rx.box(
            rx.icon(icono, size=14, color="white"),
            width="32px", height="32px", border_radius="10px",
            background=color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.vstack(
            rx.text(a["categoria"], size="2", color=T.TEXT, weight="medium"),
            rx.hstack(
                rx.text(a["gastado_fmt"], size="1", color=color, weight="medium",
                        font_family=T.FONT_MONO),
                rx.text("/", size="1", color=T.TEXT_DIM),
                rx.text(a["monto_fmt"], size="1", color=T.TEXT_DIM,
                        font_family=T.FONT_MONO),
                spacing="1",
            ),
            spacing="1", align="start",
        ),
        rx.spacer(),
        rx.text(a["pct_fmt"], size="2", color=color, weight="bold"),
        spacing="3", width="100%", align="center",
        padding="10px 12px",
        border_radius=T.RADIUS_SM,
        _hover={"background": "rgba(255,255,255,.03)"},
    )


def _alertas_card() -> rx.Component:
    return rx.cond(
        ResumenState.alertas_presupuesto.length() > 0,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.icon("triangle-alert", size=18, color=T.AMBER),
                    rx.heading("Alertas de presupuesto", size="4",
                               font_family=T.FONT_HEAD, color=T.TEXT),
                    rx.spacer(),
                    rx.link(
                        rx.hstack(
                            rx.text("Gestionar", size="2", color=T.VIOLET),
                            rx.icon("arrow-right", size=14, color=T.VIOLET),
                            spacing="1",
                        ),
                        href="/presupuestos",
                    ),
                    width="100%", align="center",
                ),
                rx.vstack(
                    rx.foreach(ResumenState.alertas_presupuesto, _alerta_pres),
                    spacing="1", width="100%",
                ),
                spacing="3", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def resumen_page() -> rx.Component:
    return main_layout(
        rx.hstack(
            page_title("Resumen", f"Vista general de {PeriodoState.periodo_label}."),
            rx.spacer(),
            width="100%", align="start",
        ),
        _metric_grid(),
        rx.box(height="24px"),
        _alertas_card(),
        rx.cond(
            ResumenState.alertas_presupuesto.length() > 0,
            rx.box(height="24px"),
            rx.fragment(),
        ),
        rx.grid(
            _line_gastos(),
            _pie_gastos(),
            columns="2", spacing="4", width="100%",
        ),
        rx.box(height="24px"),
        _recientes(),
    )
