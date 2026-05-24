"""Página /ajustes — correcciones manuales de saldo de caja."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    number_field, text_field, date_field,
    primary_button, ghost_button, field_label,
)
from minty.state.ajustes import AjustesState


def _metric(title: str, value, icon: str, gradient, accent=None) -> rx.Component:
    color = accent if accent is not None else T.TEXT
    return glass_card(
        rx.hstack(
            rx.box(
                rx.icon(icon, size=22, color="white"),
                background=gradient,
                border_radius="10px",
                padding="10px",
            ),
            rx.vstack(
                rx.text(title, size="2", color=T.TEXT_MUTED),
                rx.heading(value, size="6",
                           font_family=T.FONT_HEAD,
                           color=color),
                spacing="0", align="start",
            ),
            spacing="3", align="center", width="100%",
        ),
        padding="16px 20px",
    )


def _metrics() -> rx.Component:
    neto_color = rx.cond(AjustesState.neto_positivo, T.GREEN, T.RED)
    return rx.grid(
        _metric("Sumas al saldo", AjustesState.total_positivos_fmt,
                "trending-up", T.GREEN, T.GREEN),
        _metric("Restas al saldo", AjustesState.total_negativos_fmt,
                "trending-down", T.RED, T.RED),
        _metric("Neto del período", AjustesState.neto_fmt,
                "scale", T.GRADIENT_BRAND, neto_color),
        columns="3", spacing="4", width="100%",
    )


def _form() -> rx.Component:
    return rx.cond(
        AjustesState.form_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.icon("sliders-horizontal", size=18, color=T.VIOLET),
                    rx.heading(
                        rx.cond(AjustesState.form_editing_id,
                                "Editar ajuste", "Nuevo ajuste"),
                        size="4", font_family=T.FONT_HEAD, color=T.TEXT,
                    ),
                    spacing="2", align="center",
                ),
                rx.text(
                    "Suma o resta dinero del saldo de una caja sin generar "
                    "ingreso, gasto ni cobro de 4×1000. Úsalo solo para "
                    "corregir desfases (transacciones olvidadas, errores de "
                    "cuenta, etc.).",
                    size="2", color=T.TEXT_MUTED,
                ),
                rx.grid(
                    date_field("Fecha", AjustesState.form_fecha,
                               AjustesState.set_form_fecha),
                    rx.vstack(
                        field_label("Caja"),
                        rx.select.root(
                            rx.select.trigger(
                                placeholder="Selecciona caja…",
                                background="rgba(255,255,255,0.04)",
                                border=f"1px solid {T.BORDER}",
                                border_radius=T.RADIUS_SM,
                                width="100%", height="40px",
                            ),
                            rx.select.content(
                                rx.foreach(
                                    AjustesState.cajas_opts,
                                    lambda opt: rx.select.item(
                                        opt["etiqueta"],
                                        value=opt["id"].to_string(),
                                    ),
                                ),
                            ),
                            value=AjustesState.form_caja_id.to_string(),
                            on_change=AjustesState.set_form_caja,
                            width="100%",
                        ),
                        spacing="1", align="stretch", width="100%",
                    ),
                    columns="2", spacing="3", width="100%",
                ),
                rx.vstack(
                    field_label("Operación"),
                    rx.hstack(
                        rx.button(
                            rx.hstack(rx.icon("plus", size=14),
                                      rx.text("Sumar al saldo"),
                                      spacing="2", align="center"),
                            on_click=AjustesState.set_form_modo("sumar"),
                            background=rx.cond(
                                AjustesState.form_modo == "sumar",
                                T.GREEN, "rgba(255,255,255,0.04)"),
                            color=rx.cond(
                                AjustesState.form_modo == "sumar",
                                "white", T.TEXT_MUTED),
                            border=f"1px solid {T.BORDER}",
                            border_radius=T.RADIUS_SM,
                            padding="10px 16px", height="40px",
                            cursor="pointer", flex="1",
                        ),
                        rx.button(
                            rx.hstack(rx.icon("minus", size=14),
                                      rx.text("Restar del saldo"),
                                      spacing="2", align="center"),
                            on_click=AjustesState.set_form_modo("restar"),
                            background=rx.cond(
                                AjustesState.form_modo == "restar",
                                T.RED, "rgba(255,255,255,0.04)"),
                            color=rx.cond(
                                AjustesState.form_modo == "restar",
                                "white", T.TEXT_MUTED),
                            border=f"1px solid {T.BORDER}",
                            border_radius=T.RADIUS_SM,
                            padding="10px 16px", height="40px",
                            cursor="pointer", flex="1",
                        ),
                        spacing="2", width="100%",
                    ),
                    spacing="1", align="stretch", width="100%",
                ),
                rx.grid(
                    number_field("Monto (COP)", AjustesState.form_monto,
                                 AjustesState.set_form_monto, step=1000),
                    text_field("Descripción", AjustesState.form_descripcion,
                               AjustesState.set_form_descripcion,
                               placeholder="Ej: pago Spotify que olvidé registrar"),
                    columns="2", spacing="3", width="100%",
                ),
                rx.cond(
                    AjustesState.form_msg != "",
                    rx.text(AjustesState.form_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                rx.hstack(
                    primary_button("Guardar", AjustesState.guardar,
                                   icon="save"),
                    ghost_button("Cancelar", AjustesState.cancelar,
                                 icon="x"),
                    spacing="2", justify="end", width="100%",
                ),
                spacing="3", align="stretch", width="100%",
            ),
            padding="20px",
        ),
        rx.fragment(),
    )


def _row(r) -> rx.Component:
    signo_color = rx.cond(r.positivo, T.GREEN, T.RED)
    return rx.hstack(
        rx.box(
            rx.icon(
                rx.cond(r.positivo, "trending-up", "trending-down"),
                size=18, color="white",
            ),
            background=signo_color,
            border_radius="8px",
            padding="8px",
        ),
        rx.vstack(
            rx.hstack(
                rx.text(r.caja_nombre, size="3", color=T.TEXT, weight="medium"),
                rx.text("·", color=T.TEXT_DIM),
                rx.text(r.fecha, size="2", color=T.TEXT_MUTED,
                        font_family=T.FONT_MONO),
                spacing="2", align="center",
            ),
            rx.cond(
                r.descripcion != "",
                rx.text(r.descripcion, size="2", color=T.TEXT_MUTED),
                rx.fragment(),
            ),
            spacing="0", align="start", flex="1",
        ),
        rx.heading(r.monto_signo_fmt, size="5",
                   font_family=T.FONT_HEAD, color=signo_color),
        rx.hstack(
            rx.icon_button(
                rx.icon("pencil", size=14),
                on_click=AjustesState.editar(r.id),
                variant="ghost", color_scheme="violet", size="1",
            ),
            rx.icon_button(
                rx.icon("trash-2", size=14),
                on_click=AjustesState.eliminar(r.id),
                variant="ghost", color_scheme="red", size="1",
            ),
            spacing="1",
        ),
        spacing="3", align="center", width="100%",
        padding="12px 16px",
        border_bottom=f"1px solid {T.BORDER_SOFT}",
    )


def _lista() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.heading(f"Ajustes del período",
                           size="4", font_family=T.FONT_HEAD, color=T.TEXT),
                rx.spacer(),
                rx.text(AjustesState.rango_label,
                        size="2", color=T.TEXT_MUTED),
                width="100%", align="center",
            ),
            rx.cond(
                AjustesState.rows.length() > 0,
                rx.vstack(
                    rx.foreach(AjustesState.rows, _row),
                    spacing="0", align="stretch", width="100%",
                ),
                rx.vstack(
                    rx.icon("inbox", size=32, color=T.TEXT_DIM),
                    rx.text("Sin ajustes en este período.",
                            size="2", color=T.TEXT_MUTED),
                    spacing="2", align="center", padding="32px",
                ),
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


def ajustes_page() -> rx.Component:
    header = rx.hstack(
        page_title("Ajustes de cuenta",
                   "Corrige el saldo de una caja sin afectar ingresos ni gastos."),
        rx.spacer(),
        primary_button("Nuevo ajuste", AjustesState.toggle_form, icon="plus"),
        align="center", width="100%",
    )
    return main_layout(
        rx.vstack(
            header,
            _metrics(),
            _form(),
            _lista(),
            spacing="4", align="stretch", width="100%",
        ),
    )
