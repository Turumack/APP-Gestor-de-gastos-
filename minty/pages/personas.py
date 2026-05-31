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
