"""P\u00e1gina Ba\u00fal."""
import reflex as rx
from cuentas_pro import theme as T
from cuentas_pro.components import (
    main_layout, glass_card, page_title,
    text_field, select_field,
    primary_button, ghost_button, field_label,
)
from cuentas_pro.state.baul import BaulState, CATEGORIAS_BAUL


def _form() -> rx.Component:
    return rx.cond(
        BaulState.form_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(BaulState.form_editing_id, "Editar documento", "Nuevo documento"),
                        size="5", font_family=T.FONT_HEAD,
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("x", size=16),
                              on_click=BaulState.toggle_form,
                              variant="ghost", cursor="pointer", color=T.TEXT_MUTED),
                    width="100%",
                ),
                rx.grid(
                    text_field("Título", BaulState.form_titulo,
                               BaulState.set_form_titulo,
                               placeholder="Ej: Contrato laboral 2026"),
                    select_field("Categoría", BaulState.form_cat,
                                 BaulState.set_form_cat, CATEGORIAS_BAUL),
                    columns="2", spacing="3", width="100%",
                ),
                text_field("Etiquetas (separadas por coma)",
                           BaulState.form_etiquetas, BaulState.set_form_etiquetas,
                           placeholder="trabajo, 2026, vigente"),
                rx.vstack(
                    field_label("Contenido"),
                    rx.text_area(
                        value=BaulState.form_contenido,
                        on_change=BaulState.set_form_contenido,
                        placeholder="Escribe o pega el contenido del documento...",
                        background="rgba(255,255,255,0.04)",
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS_SM,
                        color=T.TEXT,
                        min_height="180px",
                        padding="12px",
                        width="100%",
                    ),
                    spacing="1", width="100%", align="stretch",
                ),
                rx.hstack(
                    primary_button("Guardar", BaulState.guardar, icon="save", flex="1"),
                    ghost_button("Cancelar", BaulState.toggle_form),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    BaulState.form_msg != "",
                    rx.text(BaulState.form_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="4", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def _row_doc(r) -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("file-text", size=16, color="white"),
                    width="36px", height="36px", border_radius="10px",
                    background=T.GRADIENT_BRAND,
                    display="flex", align_items="center", justify_content="center",
                ),
                rx.vstack(
                    rx.text(r.titulo, size="3", color=T.TEXT, weight="bold"),
                    rx.hstack(
                        rx.box(
                            rx.text(r.categoria, size="1", color=T.VIOLET, weight="medium"),
                            padding="2px 8px", border_radius="999px",
                            background=f"{T.VIOLET}15",
                            border=f"1px solid {T.VIOLET}33",
                        ),
                        rx.text(r.creado_en, size="1", color=T.TEXT_DIM),
                        spacing="2",
                    ),
                    spacing="1", align="start",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.button(rx.icon("pencil", size=14),
                              on_click=BaulState.editar(r.id),
                              variant="ghost", cursor="pointer", size="1",
                              color=T.TEXT_MUTED,
                              _hover={"background": "rgba(255,255,255,.08)", "color": T.TEXT}),
                    rx.button(rx.icon("trash-2", size=14),
                              on_click=BaulState.eliminar(r.id),
                              variant="ghost", cursor="pointer", size="1",
                              color=T.RED,
                              _hover={"background": f"{T.RED}15"}),
                    spacing="1",
                ),
                spacing="3", width="100%", align="start",
            ),
            rx.cond(
                r.contenido != "",
                rx.text(r.contenido, size="2", color=T.TEXT_MUTED,
                        max_height="80px", overflow="hidden",
                        style={"display": "-webkit-box", "-webkit-line-clamp": "3",
                               "-webkit-box-orient": "vertical"}),
                rx.fragment(),
            ),
            rx.cond(
                r.etiquetas != "",
                rx.hstack(
                    rx.icon("tag", size=12, color=T.TEXT_DIM),
                    rx.text(r.etiquetas, size="1", color=T.TEXT_DIM),
                    spacing="1",
                ),
                rx.fragment(),
            ),
            spacing="2", width="100%", align="stretch",
        ),
    )


def baul_page() -> rx.Component:
    cats = ["Todas", *CATEGORIAS_BAUL]
    return main_layout(
        rx.hstack(
            page_title("Baúl", "Tus documentos y notas importantes."),
            rx.spacer(),
            primary_button(
                rx.cond(BaulState.form_open, "Cerrar", "Nuevo documento"),
                BaulState.toggle_form,
                icon=rx.cond(BaulState.form_open, "x", "plus"),
            ),
            width="100%", align="start",
        ),
        _form(),
        rx.cond(BaulState.form_open, rx.box(height="24px"), rx.fragment()),

        rx.grid(
            text_field("Buscar", BaulState.filtro, BaulState.set_filtro,
                       placeholder="Buscar por título, contenido o etiqueta..."),
            select_field("Categoría", BaulState.filtro_cat,
                         BaulState.set_filtro_cat, cats),
            columns="2", spacing="3", width="100%",
            grid_template_columns="2fr 1fr",
        ),
        rx.box(height="24px"),
        rx.cond(
            BaulState.rows_filtradas.length() > 0,
            rx.grid(
                rx.foreach(BaulState.rows_filtradas, _row_doc),
                columns="2", spacing="3", width="100%",
            ),
            glass_card(
                rx.vstack(
                    rx.icon("archive", size=40, color=T.TEXT_DIM),
                    rx.text("Sin documentos", size="3", color=T.TEXT_MUTED),
                    rx.text("Crea el primero con el botón de arriba.",
                            size="2", color=T.TEXT_DIM),
                    spacing="3", align="center",
                    padding="40px 20px",
                ),
            ),
        ),
    )
