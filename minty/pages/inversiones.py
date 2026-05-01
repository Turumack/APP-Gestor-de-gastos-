"""P\u00e1gina Inversiones (CDTs)."""
import reflex as rx
from cuentas_pro import theme as T
from cuentas_pro.components import (
    main_layout, glass_card, page_title, metric_card,
    text_field, number_field, date_field,
    primary_button, ghost_button, field_label,
)
from cuentas_pro.state.inversiones import InversionesState


def _form() -> rx.Component:
    return rx.cond(
        InversionesState.form_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(InversionesState.form_editing_id, "Editar CDT", "Nuevo CDT"),
                        size="5", font_family=T.FONT_HEAD,
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("x", size=16),
                              on_click=InversionesState.toggle_form,
                              variant="ghost", cursor="pointer", color=T.TEXT_MUTED),
                    width="100%",
                ),
                rx.grid(
                    text_field("Entidad", InversionesState.form_entidad,
                               InversionesState.set_form_entidad,
                               placeholder="Bancolombia, Davivienda..."),
                    number_field("Monto (COP)", InversionesState.form_monto,
                                 InversionesState.set_form_monto, step=100000),
                    columns="2", spacing="3", width="100%",
                ),
                rx.grid(
                    number_field("Tasa E.A. (%)", InversionesState.form_tasa,
                                 InversionesState.set_form_tasa, step=0.1),
                    date_field("Apertura", InversionesState.form_apertura,
                               InversionesState.set_form_apertura),
                    number_field("Plazo (días)", InversionesState.form_plazo,
                                 InversionesState.set_form_plazo, step=1),
                    columns="3", spacing="3", width="100%",
                ),
                rx.hstack(
                    rx.text("Vencimiento:", size="2", color=T.TEXT_MUTED),
                    rx.text(InversionesState.fecha_venc_preview,
                            size="2", color=T.VIOLET, weight="bold"),
                    rx.spacer(),
                    rx.text("Rendimiento estimado:", size="2", color=T.TEXT_MUTED),
                    rx.text(f"${InversionesState.rendimiento_preview:,.0f}",
                            size="2", color=T.GREEN, weight="bold"),
                    width="100%", spacing="2",
                ),
                text_field("Notas (opcional)", InversionesState.form_notas,
                           InversionesState.set_form_notas),
                rx.hstack(
                    primary_button("Guardar", InversionesState.guardar, icon="save", flex="1"),
                    ghost_button("Cancelar", InversionesState.toggle_form),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    InversionesState.form_msg != "",
                    rx.text(InversionesState.form_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="4", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def _row_cdt(r) -> rx.Component:
    return glass_card(
        rx.hstack(
            rx.box(
                rx.icon("landmark", size=20, color="white"),
                width="44px", height="44px", border_radius="12px",
                background=T.GRADIENT_GREEN,
                display="flex", align_items="center", justify_content="center",
            ),
            rx.vstack(
                rx.text(r.entidad, size="3", color=T.TEXT, weight="bold"),
                rx.hstack(
                    rx.text(f"${r.monto:,.0f}", size="2", color=T.TEXT),
                    rx.text("·", size="1", color=T.TEXT_DIM),
                    rx.text(f"{r.tasa_ea}% E.A.", size="2", color=T.AMBER, weight="medium"),
                    rx.text("·", size="1", color=T.TEXT_DIM),
                    rx.text(f"{r.plazo_dias} días", size="2", color=T.TEXT_DIM),
                    spacing="1",
                ),
                rx.text(f"Vence: {r.fecha_vencimiento}",
                        size="1", color=T.TEXT_DIM),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.vstack(
                rx.cond(
                    r.dias_restantes > 0,
                    rx.box(
                        rx.text(f"{r.dias_restantes} días",
                                size="1", color=T.BLUE, weight="bold"),
                        padding="4px 10px", border_radius="999px",
                        background=f"{T.BLUE}22",
                    ),
                    rx.box(
                        rx.text("Vencido",
                                size="1", color=T.AMBER, weight="bold"),
                        padding="4px 10px", border_radius="999px",
                        background=f"{T.AMBER}22",
                    ),
                ),
                rx.text(f"+${r.rendimiento_estimado:,.0f}",
                        size="2", color=T.GREEN, weight="bold"),
                spacing="1", align="end",
            ),
            rx.hstack(
                rx.button(rx.icon("pencil", size=14),
                          on_click=InversionesState.editar(r.id),
                          variant="ghost", cursor="pointer", size="1",
                          color=T.TEXT_MUTED,
                          _hover={"background": "rgba(255,255,255,.08)", "color": T.TEXT}),
                rx.button(rx.icon("trash-2", size=14),
                          on_click=InversionesState.eliminar(r.id),
                          variant="ghost", cursor="pointer", size="1",
                          color=T.RED,
                          _hover={"background": f"{T.RED}15"}),
                spacing="1",
            ),
            spacing="3", width="100%", align="center",
        ),
    )


def inversiones_page() -> rx.Component:
    return main_layout(
        rx.hstack(
            page_title("Inversiones", "CDTs activos y proyección de rendimientos."),
            rx.spacer(),
            primary_button(
                rx.cond(InversionesState.form_open, "Cerrar", "Nuevo CDT"),
                InversionesState.toggle_form,
                icon=rx.cond(InversionesState.form_open, "x", "plus"),
            ),
            width="100%", align="start",
        ),
        rx.grid(
            metric_card("Total invertido",
                        f"${InversionesState.total_invertido:,.0f}",
                        "landmark", T.BLUE),
            metric_card("Rendimiento proyectado",
                        f"${InversionesState.total_rendimiento:,.0f}",
                        "trending-up", T.GREEN),
            metric_card("CDTs activos",
                        InversionesState.rows.length().to_string(),
                        "list", T.VIOLET),
            columns="3", spacing="4", width="100%",
        ),
        rx.box(height="24px"),
        _form(),
        rx.cond(InversionesState.form_open, rx.box(height="24px"), rx.fragment()),

        rx.heading("Posiciones", size="5", font_family=T.FONT_HEAD, padding_bottom="16px"),
        rx.cond(
            InversionesState.rows.length() > 0,
            rx.vstack(
                rx.foreach(InversionesState.rows, _row_cdt),
                spacing="3", width="100%",
            ),
            glass_card(
                rx.vstack(
                    rx.icon("inbox", size=40, color=T.TEXT_DIM),
                    rx.text("Sin inversiones registradas", size="3", color=T.TEXT_MUTED),
                    spacing="3", align="center",
                    padding="40px 20px",
                ),
            ),
        ),
    )
