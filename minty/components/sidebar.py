"""Sidebar lateral con navegación tipo app moderna."""
import reflex as rx
from minty import theme as T
from minty.components.period_selector import period_selector
from minty.state.auth import AuthState, auth_required


class SidebarState(rx.State):
    """Estado de la sidebar (colapsada/expandida)."""

    collapsed: bool = False

    @rx.event
    def toggle(self):
        self.collapsed = not self.collapsed


# ── Item individual ─────────────────────────────────────
def _nav_item(label: str, icon: str, href: str, active_route: rx.Var) -> rx.Component:
    is_active = active_route == href
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.cond(
                SidebarState.collapsed,
                rx.fragment(),
                rx.text(label, size="3", weight="medium"),
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        href=href,
        padding=rx.cond(SidebarState.collapsed, "10px 0", "10px 14px"),
        border_radius=T.RADIUS,
        width="100%",
        color=rx.cond(is_active, T.TEXT, T.TEXT_MUTED),
        background=rx.cond(is_active, T.GRADIENT_BRAND_SOFT, "transparent"),
        border=rx.cond(is_active, f"1px solid {T.VIOLET}44", "1px solid transparent"),
        transition="all .15s ease",
        title=label,
        _hover={
            "background": "rgba(255,255,255,0.04)",
            "color": T.TEXT,
        },
        text_decoration="none",
    )


def _section_label(text: str) -> rx.Component:
    return rx.cond(
        SidebarState.collapsed,
        rx.box(height="8px"),
        rx.text(
            text,
            size="1",
            color=T.TEXT_DIM,
            weight="bold",
            letter_spacing="0.1em",
            padding_left="14px",
        ),
    )


def sidebar() -> rx.Component:
    route = rx.State.router.page.path

    return rx.box(
        rx.vstack(
            # ── Logo + toggle ──
            rx.hstack(
                rx.image(
                    src="/axium_icon.svg",
                    width=rx.cond(SidebarState.collapsed, "36px", "70px"),
                    height=rx.cond(SidebarState.collapsed, "36px", "70px"),
                    border_radius="1px",
                ),
                rx.cond(
                    SidebarState.collapsed,
                    rx.fragment(),
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
                ),
                rx.spacer(),
                rx.cond(
                    SidebarState.collapsed,
                    rx.fragment(),
                    rx.icon_button(
                        rx.icon("panel-left-close", size=16),
                        on_click=SidebarState.toggle,
                        variant="ghost",
                        color=T.TEXT_MUTED,
                        title="Ocultar barra",
                    ),
                ),
                spacing="3",
                align="center",
                width="100%",
                padding="8px 4px 24px 4px",
            ),
            rx.cond(
                SidebarState.collapsed,
                rx.icon_button(
                    rx.icon("panel-left-open", size=16),
                    on_click=SidebarState.toggle,
                    variant="ghost",
                    color=T.TEXT_MUTED,
                    title="Mostrar barra",
                    margin_bottom="8px",
                ),
                rx.fragment(),
            ),

            # ── Nav principal ──
            _section_label("GENERAL"),
            _nav_item("Inicio", "home", "/", route),
            _nav_item("Resumen", "chart-pie", "/resumen", route),

            rx.spacer(height="20px"),
            _section_label("MOVIMIENTOS"),
            _nav_item("Ingresos", "trending-up", "/ingresos", route),
            _nav_item("Gastos", "trending-down", "/gastos", route),
            _nav_item("Listas", "list", "/compras", route),

            rx.spacer(height="20px"),
            _section_label("PATRIMONIO"),
            _nav_item("Cajas", "wallet", "/cajas", route),
            _nav_item("Presupuestos", "piggy-bank", "/presupuestos", route),
            _nav_item("Inversiones", "landmark", "/inversiones", route),
            _nav_item("Baúl", "archive", "/baul", route),

            rx.spacer(height="20px"),
            _section_label("SISTEMA"),
            _nav_item("Configuración", "settings", "/configuracion", route),
            rx.cond(
                auth_required(),
                rx.box(
                    rx.hstack(
                        rx.icon("log-out", size=16, color=T.TEXT_MUTED),
                        rx.cond(
                            SidebarState.collapsed,
                            rx.fragment(),
                            rx.text("Cerrar sesión", size="2", color=T.TEXT_MUTED),
                        ),
                        spacing="3",
                        align="center",
                        width="100%",
                    ),
                    padding=rx.cond(SidebarState.collapsed, "10px 0", "10px 14px"),
                    border_radius="10px",
                    cursor="pointer",
                    on_click=AuthState.logout,
                    title="Cerrar sesión",
                    _hover={"background": "rgba(255,255,255,0.04)"},
                ),
                rx.fragment(),
            ),

            rx.spacer(),

            # ── Selector de período ──
            rx.cond(
                SidebarState.collapsed,
                rx.fragment(),
                period_selector(),
            ),

            # ── Footer ──
            rx.cond(
                SidebarState.collapsed,
                rx.fragment(),
                rx.box(
                    rx.text("v2.6 · Online", size="1", color=T.TEXT_DIM, text_align="center"),
                    padding="12px",
                    width="100%",
                ),
            ),
            spacing="1",
            height="98vh",
            align="stretch",
        ),
        position="sticky",
        top="0",
        width=rx.cond(SidebarState.collapsed, "72px", "240px"),
        min_width=rx.cond(SidebarState.collapsed, "72px", "240px"),
        height="100vh",
        padding="20px 12px",
        background="rgba(10,10,15,0.6)",
        backdrop_filter="blur(20px)",
        border_right=f"1px solid {T.BORDER}",
        transition="width .2s ease, min-width .2s ease",
    )
