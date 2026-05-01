"""Página Presupuestos por categoría."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    number_field, select_field, text_field,
    primary_button, ghost_button, field_label,
)
from minty.state.presupuestos import PresupuestosState
from minty.state import PeriodoState
from minty.finance import CATEGORIAS_GASTO


def _form() -> rx.Component:
    return rx.cond(
        PresupuestosState.form_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(
                            PresupuestosState.form_editing_id,
                            "Editar presupuesto",
                            "Nuevo presupuesto",
                        ),
                        size="5", font_family=T.FONT_HEAD,
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("x", size=16),
                              on_click=PresupuestosState.toggle_form,
                              variant="ghost", cursor="pointer", color=T.TEXT_MUTED),
                    width="100%",
                ),
                rx.grid(
                    select_field("Categoría",
                                 PresupuestosState.form_categoria,
                                 PresupuestosState.set_form_categoria,
                                 CATEGORIAS_GASTO),
                    number_field("Monto presupuestado (COP)",
                                 PresupuestosState.form_monto,
                                 PresupuestosState.set_form_monto, step=10_000),
                    number_field("Alerta al alcanzar (%)",
                                 PresupuestosState.form_alerta_pct,
                                 PresupuestosState.set_form_alerta_pct, step=5),
                    columns="3", spacing="3", width="100%",
                ),
                text_field("Notas (opcional)",
                           PresupuestosState.form_notas,
                           PresupuestosState.set_form_notas,
                           placeholder="Ej: Excluye supermercado mensual"),
                rx.hstack(
                    primary_button("Guardar", PresupuestosState.guardar,
                                   icon="save", flex="1"),
                    ghost_button("Cancelar", PresupuestosState.toggle_form),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    PresupuestosState.form_msg != "",
                    rx.text(PresupuestosState.form_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="4", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def _color_estado(estado: rx.Var) -> rx.Var:
    return rx.match(
        estado,
        ("excedido", T.RED),
        ("alerta", T.AMBER),
        T.GREEN,
    )


def _icon_estado(estado: rx.Var) -> rx.Var:
    return rx.match(
        estado,
        ("excedido", "circle-alert"),
        ("alerta", "triangle-alert"),
        "circle-check",
    )


def _row_pres(r) -> rx.Component:
    color = _color_estado(r.estado)
    icono = _icon_estado(r.estado)
    pct_barra = rx.cond(r.pct_uso > 100, 100, r.pct_uso)
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(icono, size=16, color="white"),
                    width="36px", height="36px", border_radius="10px",
                    background=color,
                    display="flex", align_items="center", justify_content="center",
                ),
                rx.vstack(
                    rx.text(r.categoria, size="3", color=T.TEXT, weight="bold"),
                    rx.hstack(
                        rx.text(r.gastado_fmt, size="2", color=color, weight="medium",
                                font_family=T.FONT_MONO),
                        rx.text("/", size="2", color=T.TEXT_DIM),
                        rx.text(r.monto_fmt, size="2", color=T.TEXT_MUTED,
                                font_family=T.FONT_MONO),
                        rx.text(r.pct_uso_fmt, size="1", color=color, weight="bold"),
                        spacing="2", align="center",
                    ),
                    spacing="1", align="start",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.button(rx.icon("pencil", size=14),
                              on_click=PresupuestosState.editar(r.id),
                              variant="ghost", cursor="pointer", size="1",
                              color=T.TEXT_MUTED),
                    rx.button(rx.icon("trash-2", size=14),
                              on_click=PresupuestosState.eliminar(r.id),
                              variant="ghost", cursor="pointer", size="1",
                              color=T.RED),
                    spacing="1",
                ),
                spacing="3", width="100%", align="center",
            ),
            # Barra de progreso
            rx.box(
                rx.box(
                    width=pct_barra.to_string() + "%",
                    height="100%",
                    background=color,
                    border_radius="999px",
                    transition="width .3s ease",
                ),
                width="100%", height="6px",
                background="rgba(255,255,255,0.06)",
                border_radius="999px",
                overflow="hidden",
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def presupuestos_page() -> rx.Component:
    return main_layout(
        rx.hstack(
            page_title(
                "Presupuestos",
                "Define cupos mensuales por categoría y recibe alertas.",
            ),
            rx.spacer(),
            primary_button(
                rx.cond(PresupuestosState.form_open, "Cerrar", "Nuevo presupuesto"),
                PresupuestosState.toggle_form,
                icon=rx.cond(PresupuestosState.form_open, "x", "plus"),
            ),
            width="100%", align="start",
        ),
        _form(),
        rx.cond(PresupuestosState.form_open, rx.box(height="24px"), rx.fragment()),

        # Resumen totales
        rx.grid(
            glass_card(
                rx.vstack(
                    rx.text("Presupuestado", size="1", color=T.TEXT_DIM,
                            weight="bold", letter_spacing="0.1em"),
                    rx.text(
                        "$" + PresupuestosState.total_presupuestado.to_string(),
                        size="6", color=T.TEXT, weight="bold",
                        font_family=T.FONT_MONO,
                    ),
                    rx.text(PeriodoState.periodo_label, size="1", color=T.TEXT_DIM),
                    spacing="1", align="start",
                ),
            ),
            glass_card(
                rx.vstack(
                    rx.text("Gastado", size="1", color=T.TEXT_DIM,
                            weight="bold", letter_spacing="0.1em"),
                    rx.text(
                        "$" + PresupuestosState.total_gastado.to_string(),
                        size="6", color=T.PINK, weight="bold",
                        font_family=T.FONT_MONO,
                    ),
                    rx.text("Total del mes", size="1", color=T.TEXT_DIM),
                    spacing="1", align="start",
                ),
            ),
            columns="2", spacing="3", width="100%",
        ),
        rx.box(height="24px"),

        rx.cond(
            PresupuestosState.rows.length() > 0,
            rx.grid(
                rx.foreach(PresupuestosState.rows, _row_pres),
                columns="2", spacing="3", width="100%",
            ),
            glass_card(
                rx.vstack(
                    rx.icon("piggy-bank", size=40, color=T.TEXT_DIM),
                    rx.text("Sin presupuestos en este periodo", size="3", color=T.TEXT_MUTED),
                    rx.text(
                        "Crea uno para empezar a controlar tus gastos por categoría.",
                        size="2", color=T.TEXT_DIM,
                    ),
                    spacing="3", align="center",
                    padding="40px 20px",
                ),
            ),
        ),
    )
