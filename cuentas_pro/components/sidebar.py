"""Sidebar lateral con navegación tipo app moderna."""
import reflex as rx
from cuentas_pro import theme as T
from cuentas_pro.components.period_selector import period_selector


# ── Item individual ─────────────────────────────────────
def _nav_item(label: str, icon: str, href: str, active_route: rx.Var) -> rx.Component:
    is_active = active_route == href
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(label, size="3", weight="medium"),
            spacing="3",
            align="center",
            width="100%",
        ),
        href=href,
        padding="10px 14px",
        border_radius=T.RADIUS,
        width="100%",
        color=rx.cond(is_active, T.TEXT, T.TEXT_MUTED),
        background=rx.cond(is_active, T.GRADIENT_BRAND_SOFT, "transparent"),
        border=rx.cond(is_active, f"1px solid {T.VIOLET}44", "1px solid transparent"),
        transition="all .15s ease",
        _hover={
            "background": "rgba(255,255,255,0.04)",
            "color": T.TEXT,
        },
        text_decoration="none",
    )


def sidebar() -> rx.Component:
    route = rx.State.router.page.path

    return rx.box(
        rx.vstack(
            # ── Logo ──
            rx.hstack(
                rx.image(
                    src="/axium_icon.svg",
                    width="70px", 
                    height="70px",
                    border_radius="1px",
                ),
                rx.vstack(
                    rx.heading(
                        "MINTY",
                        size="4",
                        weight="bold",
                       font_family=T.FONT_HEAD,
                        background=T.GRADIENT_BRAND,
                        background_clip="text",
                        color="transparent",
                        line_height="1",
                    ),
                    rx.text("Cuentas seguras y privadas", size="1", color=T.TEXT_DIM, weight="medium", letter_spacing="0.1em"),
                    spacing="1",
                    align="start",
                ),
                spacing="3",
                align="center",
                padding="8px 4px 24px 4px",
            ),

            # ── Nav principal ──
            rx.text("GENERAL", size="1", color=T.TEXT_DIM, weight="bold", letter_spacing="0.1em", padding_left="14px"),
            _nav_item("Inicio", "home", "/", route),
            _nav_item("Resumen", "chart-pie", "/resumen", route),

            rx.spacer(height="20px"),
            rx.text("MOVIMIENTOS", size="1", color=T.TEXT_DIM, weight="bold", letter_spacing="0.1em", padding_left="14px"),
            _nav_item("Ingresos", "trending-up", "/ingresos", route),
            _nav_item("Gastos", "trending-down", "/gastos", route),
            _nav_item("Listas", "list", "/compras", route),

            rx.spacer(height="20px"),
            rx.text("PATRIMONIO", size="1", color=T.TEXT_DIM, weight="bold", letter_spacing="0.1em", padding_left="14px"),
            _nav_item("Cajas", "wallet", "/cajas", route),
            _nav_item("Presupuestos", "piggy-bank", "/presupuestos", route),
            _nav_item("Inversiones", "landmark", "/inversiones", route),
            _nav_item("Baúl", "archive", "/baul", route),

            rx.spacer(height="20px"),
            rx.text("SISTEMA", size="1", color=T.TEXT_DIM, weight="bold", letter_spacing="0.1em", padding_left="14px"),
            _nav_item("Configuración", "settings", "/configuracion", route),

            rx.spacer(),

            # ── Selector de período ──
            period_selector(),

            # ── Footer ──
            rx.box(
                rx.text("v2.5 · Local", size="1", color=T.TEXT_DIM, text_align="center"),
                padding="12px",
                width="100%",
            ),
            spacing="1",
            height="98vh",
            align="stretch",
        ),
        position="sticky",
        top="0",
        width="240px",
        min_width="240px",
        height="100vh",
        padding="20px 12px",
        background="rgba(10,10,15,0.6)",
        backdrop_filter="blur(20px)",
        border_right=f"1px solid {T.BORDER}",
    )
