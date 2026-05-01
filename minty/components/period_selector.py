"""Selector de mes/a\u00f1o compacto para el sidebar."""
import reflex as rx
from minty import theme as T
from minty.state import PeriodoState


def period_selector() -> rx.Component:
    return rx.vstack(
        rx.text("PER\u00cdODO", size="1", color=T.TEXT_DIM, weight="bold",
                letter_spacing="0.1em", padding_left="4px"),
        rx.box(
            rx.hstack(
                rx.button(
                    rx.icon("chevron-left", size=14),
                    on_click=PeriodoState.mes_anterior,
                    variant="ghost",
                    size="1",
                    color=T.TEXT_MUTED,
                    cursor="pointer",
                    padding="4px",
                    _hover={"background": "rgba(255,255,255,.06)", "color": T.TEXT},
                ),
                rx.vstack(
                    rx.text(PeriodoState.mes_nombre, size="2", weight="bold", color=T.TEXT, line_height="1"),
                    rx.text(PeriodoState.anio.to_string(), size="1", color=T.TEXT_MUTED, line_height="1"),
                    spacing="1",
                    align="center",
                    flex="1",
                ),
                rx.button(
                    rx.icon("chevron-right", size=14),
                    on_click=PeriodoState.mes_siguiente,
                    variant="ghost",
                    size="1",
                    color=T.TEXT_MUTED,
                    cursor="pointer",
                    padding="4px",
                    _hover={"background": "rgba(255,255,255,.06)", "color": T.TEXT},
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            padding="10px 12px",
            background="rgba(255,255,255,.03)",
            border=f"1px solid {T.BORDER}",
            border_radius=T.RADIUS,
            width="100%",
        ),
        rx.button(
            "Hoy",
            on_click=PeriodoState.set_hoy,
            variant="ghost",
            size="1",
            color=T.VIOLET,
            cursor="pointer",
            width="100%",
            _hover={"background": f"{T.VIOLET}15"},
        ),
        spacing="2",
        width="100%",
    )
