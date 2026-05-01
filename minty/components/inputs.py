"""Inputs estilizados reutilizables (dark theme)."""
import reflex as rx
from minty import theme as T


def field_label(text: str) -> rx.Component:
    return rx.text(text, size="2", color=T.TEXT_MUTED, weight="medium", padding_bottom="4px")


def text_field(label: str, value, on_change, placeholder: str = "", **kw) -> rx.Component:
    return rx.vstack(
        field_label(label),
        rx.input(
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            background="rgba(255,255,255,0.04)",
            border=f"1px solid {T.BORDER}",
            border_radius=T.RADIUS_SM,
            color=T.TEXT,
            padding="10px 12px",
            height="40px",
            width="100%",
            _focus={"border_color": T.VIOLET, "outline": "none"},
            **kw,
        ),
        spacing="1",
        align="stretch",
        width="100%",
    )


def number_field(label: str, value, on_change, step: float = 1.0, **kw) -> rx.Component:
    return rx.vstack(
        field_label(label),
        rx.input(
            value=value.to_string(),
            on_change=on_change,
            type="number",
            step=step,
            background="rgba(255,255,255,0.04)",
            border=f"1px solid {T.BORDER}",
            border_radius=T.RADIUS_SM,
            color=T.TEXT,
            padding="10px 12px",
            height="40px",
            width="100%",
            _focus={"border_color": T.VIOLET, "outline": "none"},
            **kw,
        ),
        spacing="1",
        align="stretch",
        width="100%",
    )


def date_field(label: str, value, on_change, **kw) -> rx.Component:
    return rx.vstack(
        field_label(label),
        rx.input(
            value=value,
            on_change=on_change,
            type="date",
            background="rgba(255,255,255,0.04)",
            border=f"1px solid {T.BORDER}",
            border_radius=T.RADIUS_SM,
            color=T.TEXT,
            padding="10px 12px",
            height="40px",
            width="100%",
            _focus={"border_color": T.VIOLET, "outline": "none"},
            **kw,
        ),
        spacing="1",
        align="stretch",
        width="100%",
    )


def select_field(label: str, value, on_change, options: list[str], **kw) -> rx.Component:
    return rx.vstack(
        field_label(label),
        rx.select(
            options,
            value=value,
            on_change=on_change,
            width="100%",
            **kw,
        ),
        spacing="1",
        align="stretch",
        width="100%",
    )


def primary_button(label, on_click, icon: str | None = None, **kw) -> rx.Component:
    if icon is None:
        inner = rx.text(label, weight="medium")
    else:
        inner = rx.hstack(
            rx.icon(icon, size=16),
            rx.text(label, weight="medium"),
            spacing="2", align="center",
        )
    return rx.button(
        inner,
        on_click=on_click,
        background=T.GRADIENT_BRAND,
        color="white",
        border_radius=T.RADIUS,
        padding="0 20px",
        height="40px",
        cursor="pointer",
        border="none",
        _hover={"transform": "translateY(-1px)", "box_shadow": T.SHADOW_GLOW},
        **kw,
    )


def ghost_button(label, on_click, icon: str | None = None, **kw) -> rx.Component:
    if icon is None:
        inner = rx.text(label, weight="medium")
    else:
        inner = rx.hstack(
            rx.icon(icon, size=16),
            rx.text(label, weight="medium"),
            spacing="2", align="center",
        )
    return rx.button(
        inner,
        on_click=on_click,
        background="rgba(255,255,255,0.05)",
        color=T.TEXT,
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS,
        padding="0 20px",
        height="40px",
        cursor="pointer",
        _hover={"background": "rgba(255,255,255,0.08)"},
        **kw,
    )
