"""Primitivos UI reutilizables: cards, botones, headers."""
import reflex as rx
from cuentas_pro import theme as T


def glass_card(*children, **props) -> rx.Component:
    """Tarjeta con efecto glass morphism."""
    base = {
        "background": T.BG_CARD,
        "backdrop_filter": "blur(20px)",
        "border": f"1px solid {T.BORDER}",
        "border_radius": T.RADIUS_LG,
        "padding": "24px",
        "box_shadow": T.SHADOW_CARD,
        "transition": "all .2s ease",
    }
    base.update(props)
    return rx.box(*children, **base)


def page_title(title: str, subtitle: str = "") -> rx.Component:
    return rx.vstack(
        rx.heading(
            title,
            size="8",
            font_family=T.FONT_HEAD,
            weight="bold",
            color=T.TEXT,
            line_height="1.1",
        ),
        rx.cond(
            subtitle != "",
            rx.text(subtitle, size="3", color=T.TEXT_MUTED),
            rx.fragment(),
        ),
        spacing="2",
        align="start",
        padding_bottom="24px",
    )


def metric_card(
    label: str,
    value: str,
    icon: str,
    color: str = T.VIOLET,
    trend: str | None = None,
    trend_positive: bool = True,
) -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(icon, size=16, color="white"),
                    width="32px",
                    height="32px",
                    border_radius="10px",
                    background=f"linear-gradient(135deg, {color} 0%, {color}88 100%)",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.text(label, size="2", color=T.TEXT_MUTED, weight="medium"),
                spacing="3",
                align="center",
            ),
            rx.heading(value, size="7", font_family=T.FONT_HEAD, weight="bold", color=T.TEXT),
            rx.cond(
                trend is not None,
                rx.hstack(
                    rx.icon("trending-up" if trend_positive else "trending-down", size=14,
                            color=T.GREEN if trend_positive else T.RED),
                    rx.text(trend or "", size="1", color=T.GREEN if trend_positive else T.RED, weight="medium"),
                    spacing="1",
                ),
                rx.fragment(),
            ),
            spacing="3",
            align="start",
        ),
        _hover={"transform": "translateY(-2px)", "box_shadow": T.SHADOW_HOVER},
    )


def pill(text: str, color: str = T.VIOLET) -> rx.Component:
    return rx.box(
        text,
        padding="4px 12px",
        border_radius="999px",
        background=f"{color}22",
        color=color,
        border=f"1px solid {color}44",
        font_size="12px",
        font_weight="500",
        display="inline-block",
    )
