"""Layout principal: sidebar + contenido."""
import reflex as rx
from minty import theme as T
from minty.components.sidebar import sidebar


def main_layout(*content) -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.box(
            rx.box(
                *content,
                max_width="1280px",
                margin="0 auto",
                padding="40px 48px",
            ),
            flex="1",
            min_height="100vh",
            overflow_y="auto",
        ),
        spacing="0",
        align="start",
        width="100%",
        min_height="100vh",
    )
