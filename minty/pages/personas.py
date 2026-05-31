"""Página /personas — libreta de personas recurrentes para Dividir cuenta."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    text_field, primary_button, ghost_button, field_label,
)
from minty.state.personas import PersonasState, PALETA, EMOJIS


def _color_swatch(color: str) -> rx.Component:
    is_sel = PersonasState.form_color == color
    return rx.box(
        on_click=PersonasState.set_form_color(color),
        width="28px", height="28px",
        border_radius="50%",
        background=color,
        cursor="pointer",
        border=rx.cond(is_sel, "3px solid white", "2px solid transparent"),
    )


def _emoji_pick(emoji: str) -> rx.Component:
    is_sel = PersonasState.form_emoji == emoji
    return rx.box(
        rx.text(emoji, font_size="20px"),
        on_click=PersonasState.set_form_emoji(emoji),
        width="36px", height="36px",
        border_radius="8px",
        cursor="pointer",
        display="flex", align_items="center", justify_content="center",
        border=rx.cond(is_sel, f"2px solid {T.VIOLET}",
                       f"1px solid {T.BORDER}"),
        background=rx.cond(is_sel, "rgba(167,139,250,0.12)",
                           "rgba(255,255,255,0.03)"),
    )


def _form() -> rx.Component:
    return rx.cond(
        PersonasState.form_open,
        glass_card(
            rx.vstack(
                rx.heading(
                    rx.cond(PersonasState.form_editing_id,
                            "Editar persona", "Nueva persona"),
                    size="4", font_family=T.FONT_HEAD, color=T.TEXT,
                ),
                text_field("Nombre", PersonasState.form_nombre,
                           PersonasState.set_form_nombre,
                           placeholder="Ej: Andrés"),
                rx.vstack(
                    field_label("Color"),
                    rx.flex(
                        *[_color_swatch(c) for c in PALETA],
                        wrap="wrap", gap="8px",
                    ),
                    spacing="1", align="stretch", width="100%",
                ),
                rx.vstack(
                    field_label("Emoji / avatar"),
                    rx.flex(
                        *[_emoji_pick(e) for e in EMOJIS],
                        wrap="wrap", gap="6px",
                    ),
                    spacing="1", align="stretch", width="100%",
                ),
                text_field("Notas", PersonasState.form_notas,
                           PersonasState.set_form_notas,
                           placeholder="(opcional)"),
                rx.cond(
                    PersonasState.form_msg != "",
                    rx.text(PersonasState.form_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                rx.hstack(
                    primary_button("Guardar", PersonasState.guardar,
                                   icon="save"),
                    ghost_button("Cancelar", PersonasState.cancelar, icon="x"),
                    spacing="2", justify="end", width="100%",
                ),
                spacing="3", align="stretch", width="100%",
            ),
            padding="20px",
        ),
        rx.fragment(),
    )


def _persona_card(p) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.text(p.emoji, font_size="28px"),
                    width="56px", height="56px",
                    border_radius="50%",
                    background=p.color,
                    display="flex", align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.heading(p.nombre, size="4",
                               font_family=T.FONT_HEAD, color=T.TEXT),
                    rx.cond(
                        p.notas != "",
                        rx.text(p.notas, size="1", color=T.TEXT_MUTED),
                        rx.fragment(),
                    ),
                    spacing="0", align="start",
                ),
                spacing="3", align="center", width="100%",
            ),
            rx.hstack(
                rx.cond(
                    p.activa,
                    rx.badge("Activa", color_scheme="green", size="1"),
                    rx.badge("Inactiva", color_scheme="gray", size="1"),
                ),
                rx.spacer(),
                rx.icon_button(
                    rx.icon("pencil", size=14),
                    on_click=PersonasState.editar(p.id),
                    variant="ghost", color_scheme="violet", size="1",
                ),
                rx.icon_button(
                    rx.icon(rx.cond(p.activa, "eye-off", "eye"), size=14),
                    on_click=PersonasState.toggle_activa(p.id),
                    variant="ghost", color_scheme="gray", size="1",
                ),
                rx.icon_button(
                    rx.icon("trash-2", size=14),
                    on_click=PersonasState.eliminar(p.id),
                    variant="ghost", color_scheme="red", size="1",
                ),
                spacing="1", align="center", width="100%",
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="16px",
        background="rgba(255,255,255,0.03)",
        border=f"1px solid {T.BORDER_SOFT}",
        border_radius=T.RADIUS,
        width="100%",
    )


def _saldo_row(p) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.text(p.emoji, font_size="14px"),
            width="26px", height="26px",
            border_radius="50%",
            background=p.color,
            display="flex", align_items="center", justify_content="center",
            flex_shrink="0",
        ),
        rx.text(p.nombre, size="2", color=T.TEXT, weight="medium"),
        rx.cond(
            p.es_yo,
            rx.badge("Tú", color_scheme="violet", variant="soft"),
            rx.fragment(),
        ),
        rx.spacer(),
        rx.text(p.balance_fmt, size="2", font_family=T.FONT_MONO,
                weight="bold",
                color=rx.match(
                    p.balance_signo,
                    ("debe", T.RED),
                    ("recibe", T.GREEN),
                    T.TEXT_DIM,
                )),
        rx.match(
            p.balance_signo,
            ("debe", rx.badge("Deudor", color_scheme="red", variant="soft")),
            ("recibe", rx.badge("Acreedor", color_scheme="green",
                                variant="soft")),
            rx.badge("Saldado", color_scheme="gray", variant="soft"),
        ),
        spacing="2", align="center", width="100%",
        padding="10px 12px",
        background=rx.cond(p.es_yo,
                           "rgba(167,139,250,0.06)",
                           "transparent"),
        border_bottom=f"1px solid {T.BORDER_SOFT}",
    )


def _transfer_row(t) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.text(t.de_emoji, font_size="14px"),
            width="22px", height="22px",
            border_radius="50%",
            background=t.de_color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.text(t.de_nombre, size="2", color=T.TEXT),
        rx.icon("arrow-right", size=14, color=T.TEXT_DIM),
        rx.text(t.monto_fmt, size="2", color=T.VIOLET,
                font_family=T.FONT_MONO, weight="bold"),
        rx.icon("arrow-right", size=14, color=T.TEXT_DIM),
        rx.box(
            rx.text(t.a_emoji, font_size="14px"),
            width="22px", height="22px",
            border_radius="50%",
            background=t.a_color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.text(t.a_nombre, size="2", color=T.TEXT),
        spacing="2", align="center",
        padding="8px 12px",
        background="rgba(255,255,255,0.03)",
        border=f"1px solid {T.BORDER_SOFT}",
        border_radius=T.RADIUS_SM,
    )


def _saldos_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("scale", size=18, color=T.VIOLET),
                rx.heading("Saldos acumulados", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                spacing="2", align="center",
            ),
            rx.text(
                "Cruce de TODAS las facturas guardadas. Positivo (verde) = "
                "le deben / acreedor; negativo (rojo) = debe / deudor.",
                size="2", color=T.TEXT_MUTED,
            ),
            rx.cond(
                PersonasState.saldos_globales.length() > 0,
                rx.vstack(
                    rx.foreach(PersonasState.saldos_globales, _saldo_row),
                    spacing="0", align="stretch", width="100%",
                ),
                rx.vstack(
                    rx.icon("inbox", size=24, color=T.TEXT_DIM),
                    rx.text("Aún no hay facturas guardadas para cruzar.",
                            size="2", color=T.TEXT_MUTED),
                    spacing="2", align="center", padding="20px",
                ),
            ),
            rx.cond(
                PersonasState.transferencias_globales.length() > 0,
                rx.vstack(
                    rx.divider(color_scheme="gray"),
                    rx.hstack(
                        rx.icon("arrow-right-left", size=16, color=T.VIOLET),
                        rx.heading("Liquidación sugerida", size="3",
                                   font_family=T.FONT_HEAD, color=T.TEXT),
                        spacing="2", align="center",
                    ),
                    rx.text(
                        "Mínimo número de transferencias para saldar todo.",
                        size="1", color=T.TEXT_DIM,
                    ),
                    rx.foreach(PersonasState.transferencias_globales,
                               _transfer_row),
                    spacing="2", align="stretch", width="100%",
                ),
                rx.fragment(),
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


def personas_page() -> rx.Component:
    header = rx.hstack(
        page_title("Personas",
                   "Tu libreta de personas recurrentes para dividir cuentas."),
        rx.spacer(),
        primary_button("Nueva persona", PersonasState.toggle_form, icon="plus"),
        align="center", width="100%",
    )
    return main_layout(
        rx.vstack(
            header,
            _form(),
            _saldos_card(),
            rx.cond(
                PersonasState.rows.length() > 0,
                rx.grid(
                    rx.foreach(PersonasState.rows, _persona_card),
                    columns=rx.breakpoints(initial="1", sm="2", md="3"),
                    spacing="3", width="100%",
                ),
                glass_card(
                    rx.vstack(
                        rx.icon("users", size=36, color=T.TEXT_DIM),
                        rx.text("Aún no has agregado personas.",
                                size="2", color=T.TEXT_MUTED),
                        rx.text("Crea aquí a tus amigos, familia o "
                                "compañeros para reutilizarlos al dividir "
                                "cuentas.", size="1", color=T.TEXT_DIM),
                        spacing="2", align="center", padding="32px",
                    ),
                    padding="20px",
                ),
            ),
            spacing="4", align="stretch", width="100%",
        ),
    )
