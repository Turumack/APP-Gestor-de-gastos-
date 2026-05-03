"""Pantalla de login."""
import reflex as rx

from minty import theme as T
from minty.components import glass_card, primary_button, text_field
from minty.state.auth import AuthState


def login_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.image(src="/axium_icon.svg", width="80px", height="80px"),
            rx.heading(
                "MINTY",
                size="8",
                font_family=T.FONT_HEAD,
                background=T.GRADIENT_BRAND,
                background_clip="text",
                style={"-webkit-background-clip": "text"},
                color="transparent",
            ),
            rx.text("Inicia sesión para continuar.", size="2", color=T.TEXT_MUTED),
            glass_card(
                rx.vstack(
                    text_field(
                        "Usuario",
                        AuthState.user_input,
                        AuthState.set_user_input,
                        placeholder="usuario",
                    ),
                    rx.vstack(
                        rx.text("Contraseña", size="1", color=T.TEXT_MUTED),
                        rx.input(
                            type="password",
                            value=AuthState.pwd_input,
                            on_change=AuthState.set_pwd_input,
                            on_key_down=lambda k: rx.cond(
                                k == "Enter", AuthState.login, rx.noop()
                            ),
                            width="100%",
                        ),
                        spacing="1", width="100%", align="start",
                    ),
                    rx.cond(
                        AuthState.msg != "",
                        rx.text(AuthState.msg, size="2", color=T.RED),
                        rx.fragment(),
                    ),
                    primary_button("Entrar", AuthState.login, icon="log-in"),
                    spacing="3", width="320px", align="stretch",
                ),
                padding="24px",
            ),
            spacing="4", align="center",
        ),
        min_height="100vh",
        background=T.BG,
    )
