"""Página Home — landing + accesos rápidos."""
import reflex as rx
from cuentas_pro import theme as T
from cuentas_pro.components import main_layout, glass_card, page_title, metric_card
from cuentas_pro.state.resumen import ResumenState
from cuentas_pro.state import PeriodoState


def _feature_card(icon: str, title: str, desc: str, href: str, color: str) -> rx.Component:
    return rx.link(
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon(icon, size=20, color="white"),
                        width="44px",
                        height="44px",
                        border_radius="12px",
                        background=f"linear-gradient(135deg, {color} 0%, {color}aa 100%)",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.spacer(),
                    rx.icon("arrow-up-right", size=16, color=T.TEXT_DIM),
                    width="100%",
                    align="center",
                ),
                rx.heading(title, size="5", font_family=T.FONT_HEAD, weight="bold", color=T.TEXT),
                rx.text(desc, size="2", color=T.TEXT_MUTED, line_height="1.5"),
                spacing="3",
                align="start",
            ),
            height="100%",
            cursor="pointer",
            _hover={"transform": "translateY(-4px)", "box_shadow": T.SHADOW_HOVER, "border_color": f"{color}66"},
        ),
        href=href,
        text_decoration="none",
        width="100%",
    )


def home_page() -> rx.Component:
    return main_layout(
        # ── Hero ──
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("sparkles", size=14, color=T.VIOLET),
                    rx.text("Finanzas personales · 100% local", size="1", color=T.VIOLET, weight="medium"),
                    padding="6px 14px",
                    border_radius="999px",
                    background=f"{T.VIOLET}15",
                    border=f"1px solid {T.VIOLET}33",
                    display="inline-flex",
                    align_items="center",
                    gap="8px",
                ),
                padding_bottom="12px",
            ),
            rx.heading(
                "Tus cuentas, bajo control.",
                size="9",
                font_family=T.FONT_HEAD,
                weight="bold",
                line_height="1.05",
                color=T.TEXT,
            ),
            rx.heading(
                "Siempre claras.",
                size="9",
                font_family=T.FONT_HEAD,
                weight="bold",
                line_height="1.05",
                background=T.GRADIENT_BRAND,
                background_clip="text",
                color="transparent",
            ),
            rx.text(
                "Ingresos, gastos, inversiones y patrimonio en un solo lugar — "
                "rápido, privado y sin enviar nada a la nube.",
                size="4",
                color=T.TEXT_MUTED,
                max_width="600px",
                line_height="1.6",
                padding_top="12px",
            ),
            rx.hstack(
                rx.link(
                    rx.button(
                        "Ver resumen",
                        rx.icon("arrow-right", size=16),
                        size="3",
                        background=T.GRADIENT_BRAND,
                        color="white",
                        border_radius=T.RADIUS,
                        padding="0 24px",
                        height="44px",
                        cursor="pointer",
                        _hover={"transform": "translateY(-1px)", "box_shadow": T.SHADOW_GLOW},
                    ),
                    href="/resumen",
                ),
                rx.link(
                    rx.button(
                        "Registrar ingreso",
                        size="3",
                        variant="surface",
                        background="rgba(255,255,255,0.05)",
                        color=T.TEXT,
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS,
                        padding="0 24px",
                        height="44px",
                        cursor="pointer",
                        _hover={"background": "rgba(255,255,255,0.08)"},
                    ),
                    href="/ingresos",
                ),
                spacing="3",
                padding_top="24px",
            ),
            spacing="1",
            align="start",
            padding_bottom="56px",
        ),

        # ── Métricas demo ──
        rx.grid(
            metric_card("Saldo del mes", f"${ResumenState.balance:,.0f}", "wallet", T.VIOLET),
            metric_card("Ingresos", f"${ResumenState.total_ingresos:,.0f}", "trending-up", T.GREEN),
            metric_card("Gastos", f"${ResumenState.total_gastos:,.0f}", "trending-down", T.PINK),
            metric_card("Ahorro", f"{ResumenState.pct_ahorro_real:.1f}%", "piggy-bank", T.AMBER),
            columns="4",
            spacing="4",
            width="100%",
            padding_bottom="48px",
        ),

        # ── Accesos rápidos ──
        rx.heading(
            "Módulos",
            size="6",
            font_family=T.FONT_HEAD,
            weight="bold",
            padding_bottom="20px",
        ),
        rx.grid(
            _feature_card("trending-up", "Ingresos",
                          "Salario, extras, bonos. Calculadora de horas extra con las 7 tarifas de ley colombiana.",
                          "/ingresos", T.GREEN),
            _feature_card("calendar", "Gastos",
                          "Calendario visual, categorías y recurrentes. Añade, edita y elimina con un clic.",
                          "/gastos", T.PINK),
            _feature_card("chart-pie", "Resumen",
                          "KPIs, tendencias y distribución por categoría. Descubre en qué se va tu dinero.",
                          "/resumen", T.VIOLET),
            _feature_card("landmark", "Inversiones",
                          "CDTs, acciones y cripto. Rendimiento, metas y proyecciones.",
                          "/inversiones", T.BLUE),
            _feature_card("archive", "Baúl",
                          "Documentos, soportes y contratos. Tu archivo personal organizado.",
                          "/baul", T.AMBER),
            columns="3",
            spacing="4",
            width="100%",
        ),
    )