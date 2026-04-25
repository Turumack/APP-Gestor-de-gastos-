"""Página para gestionar grupos e ítems de listas de compra."""
import reflex as rx
from cuentas_pro import theme as T
from cuentas_pro.components import (
    main_layout, glass_card, page_title,
    text_field, number_field, select_field,
    primary_button, field_label,
)
from cuentas_pro.state.compras import ComprasState


def _form_grupo() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.heading("Nuevo grupo", size="4", font_family=T.FONT_HEAD),
            text_field("Nombre", ComprasState.form_group_nombre,
                       ComprasState.set_form_group_nombre,
                       placeholder="Ej: Mercado quincenal"),
            select_field("Categoría por defecto", ComprasState.form_group_categoria,
                         ComprasState.set_form_group_categoria,
                         ComprasState.categorias_gasto),
            text_field("Notas", ComprasState.form_group_notas,
                       ComprasState.set_form_group_notas,
                       placeholder="Opcional"),
            primary_button("Crear grupo", ComprasState.crear_grupo, icon="plus", width="100%"),
            rx.cond(
                ComprasState.form_group_msg != "",
                rx.text(ComprasState.form_group_msg, size="2", color=T.AMBER),
                rx.fragment(),
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def _form_item() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.heading("Nuevo ítem", size="4", font_family=T.FONT_HEAD),
            rx.cond(
                ComprasState.groups.length() > 0,
                rx.vstack(
                    field_label("Grupo"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecciona grupo",
                            background="rgba(255,255,255,0.04)",
                            border=f"1px solid {T.BORDER}",
                            border_radius=T.RADIUS_SM,
                            width="100%", height="40px",
                        ),
                        rx.select.content(
                            rx.foreach(
                                ComprasState.groups,
                                lambda g: rx.select.item(g.nombre, value=g.id.to_string()),
                            ),
                        ),
                        value=ComprasState.form_item_group_id.to_string(),
                        on_change=ComprasState.set_form_item_group_id,
                        width="100%",
                    ),
                    spacing="1", width="100%",
                ),
                rx.text("Primero crea un grupo.", size="2", color=T.TEXT_DIM),
            ),

            # ── Auto-rellenar desde URL (Amazon, MercadoLibre, etc.) ──
            rx.vstack(
                field_label("Enlace del producto (opcional)"),
                rx.hstack(
                    rx.input(
                        value=ComprasState.form_item_link,
                        on_change=ComprasState.set_form_item_link,
                        placeholder="https://www.amazon.com/...",
                        background="rgba(255,255,255,0.04)",
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS_SM,
                        color=T.TEXT, padding="10px 12px",
                        height="40px", flex="1",
                    ),
                    rx.button(
                        rx.cond(
                            ComprasState.autorrellenando,
                            rx.spinner(size="1"),
                            rx.icon("sparkles", size=14),
                        ),
                        "Auto",
                        on_click=ComprasState.autorrellenar_link,
                        disabled=ComprasState.autorrellenando,
                        background=T.VIOLET, color="white",
                        height="40px", padding="0 14px",
                        cursor="pointer", border="none",
                        border_radius=T.RADIUS_SM,
                        title="Auto-rellenar nombre e imagen desde la URL",
                    ),
                    rx.cond(
                        ComprasState.form_item_link != "",
                        rx.button(
                            rx.icon("x", size=14),
                            on_click=ComprasState.limpiar_link,
                            variant="ghost", size="2", cursor="pointer",
                            color=T.TEXT_MUTED, height="40px",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2", width="100%",
                ),
                rx.cond(
                    ComprasState.form_item_imagen != "",
                    rx.hstack(
                        rx.image(
                            src=ComprasState.form_item_imagen,
                            width="64px", height="64px",
                            border_radius=T.RADIUS_SM,
                            object_fit="cover",
                            border=f"1px solid {T.BORDER}",
                        ),
                        rx.text("Imagen detectada ✓", size="1", color=T.GREEN),
                        spacing="2", align="center",
                    ),
                    rx.fragment(),
                ),
                spacing="1", width="100%", align="stretch",
            ),

            text_field("Nombre", ComprasState.form_item_nombre,
                       ComprasState.set_form_item_nombre,
                       placeholder="Ej: Arroz 5kg"),
            select_field("Categoría", ComprasState.form_item_categoria,
                         ComprasState.set_form_item_categoria,
                         ComprasState.categorias_gasto),
            number_field("Monto estimado", ComprasState.form_item_monto,
                         ComprasState.set_form_item_monto, step=1000),
            text_field("Notas", ComprasState.form_item_notas,
                       ComprasState.set_form_item_notas,
                       placeholder="Opcional"),
            primary_button("Agregar ítem", ComprasState.crear_item, icon="plus", width="100%"),
            rx.cond(
                ComprasState.form_item_msg != "",
                rx.text(
                    ComprasState.form_item_msg,
                    size="2",
                    color=rx.match(
                        ComprasState.form_item_msg_kind,
                        ("ok", T.GREEN),
                        ("err", T.RED),
                        ("warn", T.AMBER),
                        T.TEXT_MUTED,
                    ),
                ),
                rx.fragment(),
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def _row_group(g) -> rx.Component:
    return glass_card(
        rx.hstack(
            rx.vstack(
                rx.text(g.nombre, size="3", color=T.TEXT, weight="bold"),
                rx.text("Cat. default: " + g.categoria_default, size="1", color=T.TEXT_DIM),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.vstack(
                rx.text("Pendientes: " + g.pendientes.to_string(), size="2", color=T.TEXT_MUTED),
                rx.text(g.total_estimado_fmt, size="3", color=T.VIOLET, weight="bold"),
                spacing="0", align="end",
            ),
            rx.button(
                rx.icon("trash-2", size=14),
                on_click=ComprasState.eliminar_grupo(g.id),
                variant="ghost", cursor="pointer", size="1", color=T.RED,
            ),
            spacing="3", width="100%", align="center",
        ),
        padding="12px 14px",
    )


def _row_item(it) -> rx.Component:
    return glass_card(
        rx.hstack(
            rx.cond(
                it.imagen_url != "",
                rx.image(
                    src=it.imagen_url,
                    width="48px", height="48px",
                    border_radius=T.RADIUS_SM,
                    object_fit="cover",
                    border=f"1px solid {T.BORDER}",
                    flex_shrink="0",
                ),
                rx.box(
                    rx.icon("shopping-bag", size=20, color=T.TEXT_DIM),
                    width="48px", height="48px",
                    border_radius=T.RADIUS_SM,
                    background="rgba(255,255,255,0.04)",
                    border=f"1px solid {T.BORDER}",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(it.nombre, size="3", color=T.TEXT, weight="bold"),
                    rx.cond(
                        it.comprado,
                        rx.box(
                            rx.text("Comprado", size="1", color=T.GREEN, weight="medium"),
                            padding="2px 8px", border_radius="999px", background=f"{T.GREEN}22",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        it.link != "",
                        rx.link(
                            rx.icon("external-link", size=12, color=T.VIOLET),
                            href=it.link, is_external=True,
                            title="Abrir enlace del producto",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2", align="center",
                ),
                rx.text(it.group_nombre + " · " + it.categoria, size="1", color=T.TEXT_DIM),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.text(it.monto_fmt, size="3", color=T.TEXT, weight="bold", font_family=T.FONT_HEAD),
            rx.button(
                rx.icon(rx.cond(it.comprado, "rotate-ccw", "check"), size=14),
                on_click=ComprasState.toggle_item_comprado(it.id),
                variant="ghost", cursor="pointer", size="1",
                color=rx.cond(it.comprado, T.TEXT_MUTED, T.GREEN),
            ),
            rx.button(
                rx.icon("trash-2", size=14),
                on_click=ComprasState.eliminar_item(it.id),
                variant="ghost", cursor="pointer", size="1", color=T.RED,
            ),
            spacing="3", width="100%", align="center",
        ),
        padding="12px 14px",
    )


def compras_page() -> rx.Component:
    return main_layout(
        page_title("Listas de compra", "Crea grupos e ítems para luego cargarlos en Gastos."),

        rx.grid(
            _form_grupo(),
            _form_item(),
            columns="2", spacing="4", width="100%",
        ),

        rx.box(height="24px"),

        rx.vstack(
            rx.heading("Grupos", size="5", font_family=T.FONT_HEAD),
            rx.cond(
                ComprasState.groups.length() > 0,
                rx.vstack(rx.foreach(ComprasState.groups, _row_group), spacing="2", width="100%"),
                rx.text("Sin grupos todavía.", size="2", color=T.TEXT_DIM),
            ),
            spacing="2", width="100%", align="stretch",
        ),

        rx.box(height="20px"),

        rx.vstack(
            rx.heading("Ítems", size="5", font_family=T.FONT_HEAD),
            rx.cond(
                ComprasState.items.length() > 0,
                rx.vstack(rx.foreach(ComprasState.items, _row_item), spacing="2", width="100%"),
                rx.text("Sin ítems todavía.", size="2", color=T.TEXT_DIM),
            ),
            spacing="2", width="100%", align="stretch",
        ),
    )
