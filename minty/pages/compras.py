"""Página para gestionar grupos e ítems de listas de compra."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    text_field, number_field, select_field,
    primary_button, ghost_button, field_label,
)
from minty.state.compras import ComprasState

_UPLOAD_IMG_ID = "compras_upload_imagen"


def _form_grupo() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.heading(
                rx.cond(ComprasState.form_group_editing_id > 0,
                        "Editar grupo", "Nuevo grupo"),
                size="4", font_family=T.FONT_HEAD,
            ),
            text_field("Nombre", ComprasState.form_group_nombre,
                       ComprasState.set_form_group_nombre,
                       placeholder="Ej: Mercado quincenal"),
            select_field("Categoría por defecto", ComprasState.form_group_categoria,
                         ComprasState.set_form_group_categoria,
                         ComprasState.categorias_gasto),
            text_field("Notas", ComprasState.form_group_notas,
                       ComprasState.set_form_group_notas,
                       placeholder="Opcional"),
            rx.hstack(
                rx.checkbox(
                    "Compra recurrente (sus ítems se repiten, p.ej. mercado)",
                    checked=ComprasState.form_group_recurrente,
                    on_change=ComprasState.set_form_group_recurrente,
                ),
                spacing="2",
            ),
            rx.hstack(
                primary_button(
                    rx.cond(ComprasState.form_group_editing_id > 0,
                            "Guardar cambios", "Crear grupo"),
                    ComprasState.crear_grupo,
                    icon=rx.cond(ComprasState.form_group_editing_id > 0, "save", "plus"),
                    flex="1",
                ),
                rx.cond(
                    ComprasState.form_group_editing_id > 0,
                    ghost_button("Cancelar", ComprasState.cancelar_edicion_grupo),
                    rx.fragment(),
                ),
                spacing="2", width="100%",
            ),
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
            rx.heading(
                rx.cond(ComprasState.form_item_editing_id > 0,
                        "Editar ítem", "Nuevo ítem"),
                size="4", font_family=T.FONT_HEAD,
            ),
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
                        rx.spacer(),
                        rx.button(
                            rx.icon("x", size=12),
                            "Quitar imagen",
                            on_click=ComprasState.quitar_imagen,
                            variant="ghost", size="1",
                            color=T.TEXT_MUTED, cursor="pointer",
                        ),
                        spacing="2", align="center", width="100%",
                    ),
                    rx.fragment(),
                ),
                spacing="1", width="100%", align="stretch",
            ),

            # ── Imagen manual: URL o archivo local ──
            rx.vstack(
                field_label("Imagen del ítem (opcional)"),
                text_field(
                    "URL de imagen",
                    ComprasState.form_item_imagen,
                    ComprasState.set_form_item_imagen,
                    placeholder="https://ejemplo.com/foto.jpg",
                ),
                rx.upload(
                    rx.hstack(
                        rx.icon("image-up", size=18, color=T.TEXT_DIM),
                        rx.vstack(
                            rx.text(
                                "Subir imagen desde tu equipo",
                                size="2", color=T.TEXT_MUTED,
                            ),
                            rx.text(
                                "JPG, PNG, WEBP o GIF · máx. 5 MB",
                                size="1", color=T.TEXT_DIM,
                            ),
                            rx.text(
                                rx.selected_files(_UPLOAD_IMG_ID),
                                size="1", color=T.TEXT_DIM,
                            ),
                            spacing="0", align="start",
                        ),
                        rx.spacer(),
                        rx.button(
                            "Subir",
                            on_click=ComprasState.subir_imagen_local(
                                rx.upload_files(upload_id=_UPLOAD_IMG_ID)
                            ),
                            background=T.VIOLET, color="white",
                            cursor="pointer", border="none",
                            border_radius=T.RADIUS_SM,
                            padding="6px 14px",
                        ),
                        spacing="3", width="100%", align="center",
                    ),
                    id=_UPLOAD_IMG_ID,
                    accept={
                        "image/jpeg": [".jpg", ".jpeg"],
                        "image/png": [".png"],
                        "image/webp": [".webp"],
                        "image/gif": [".gif"],
                    },
                    multiple=False,
                    border=f"1px dashed {T.BORDER}",
                    border_radius=T.RADIUS_SM,
                    padding="12px",
                    width="100%",
                ),
                spacing="2", width="100%", align="stretch",
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
            rx.hstack(
                rx.checkbox(
                    "Compra recurrente (no se marca como comprada al pagarla)",
                    checked=ComprasState.form_item_recurrente,
                    on_change=ComprasState.set_form_item_recurrente,
                ),
                spacing="2",
            ),
            rx.hstack(
                primary_button(
                    rx.cond(ComprasState.form_item_editing_id > 0,
                            "Guardar cambios", "Agregar ítem"),
                    ComprasState.crear_item,
                    icon=rx.cond(ComprasState.form_item_editing_id > 0, "save", "plus"),
                    flex="1",
                ),
                rx.cond(
                    ComprasState.form_item_editing_id > 0,
                    ghost_button("Cancelar", ComprasState.cancelar_edicion_item),
                    rx.fragment(),
                ),
                spacing="2", width="100%",
            ),
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
                rx.hstack(
                    rx.text(g.nombre, size="3", color=T.TEXT, weight="bold"),
                    rx.cond(
                        g.recurrente,
                        rx.box(
                            rx.hstack(
                                rx.icon("repeat", size=10, color=T.BLUE),
                                rx.text("Recurrente", size="1", color=T.BLUE, weight="medium"),
                                spacing="1", align="center",
                            ),
                            padding="2px 8px", border_radius="999px",
                            background=f"{T.BLUE}22",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2", align="center",
                ),
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
                rx.icon("pencil", size=14),
                on_click=ComprasState.editar_grupo(g.id),
                variant="ghost", cursor="pointer", size="1", color=T.TEXT_MUTED,
                title="Editar grupo",
                _hover={"background": "rgba(255,255,255,.08)", "color": T.TEXT},
            ),
            rx.button(
                rx.icon("repeat", size=14),
                on_click=ComprasState.toggle_group_recurrente(g.id),
                variant="ghost", cursor="pointer", size="1",
                color=rx.cond(g.recurrente, T.BLUE, T.TEXT_MUTED),
                title="Activar/desactivar recurrente",
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
                        it.recurrente,
                        rx.box(
                            rx.hstack(
                                rx.icon("repeat", size=10, color=T.BLUE),
                                rx.text("Recurrente", size="1", color=T.BLUE, weight="medium"),
                                spacing="1", align="center",
                            ),
                            padding="2px 8px", border_radius="999px",
                            background=f"{T.BLUE}22",
                        ),
                        rx.cond(
                            it.comprado,
                            rx.box(
                                rx.text("Comprado", size="1", color=T.GREEN, weight="medium"),
                                padding="2px 8px", border_radius="999px", background=f"{T.GREEN}22",
                            ),
                            rx.fragment(),
                        ),
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
                rx.icon("pencil", size=14),
                on_click=ComprasState.editar_item(it.id),
                variant="ghost", cursor="pointer", size="1", color=T.TEXT_MUTED,
                title="Editar ítem",
                _hover={"background": "rgba(255,255,255,.08)", "color": T.TEXT},
            ),
            rx.button(
                rx.icon("repeat", size=14),
                on_click=ComprasState.toggle_item_recurrente(it.id),
                variant="ghost", cursor="pointer", size="1",
                color=rx.cond(it.recurrente, T.BLUE, T.TEXT_MUTED),
                title="Activar/desactivar recurrente",
            ),
            rx.cond(
                it.recurrente,
                rx.fragment(),
                rx.button(
                    rx.icon(rx.cond(it.comprado, "rotate-ccw", "check"), size=14),
                    on_click=ComprasState.toggle_item_comprado(it.id),
                    variant="ghost", cursor="pointer", size="1",
                    color=rx.cond(it.comprado, T.TEXT_MUTED, T.GREEN),
                    title="Marcar comprado / desmarcar",
                ),
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
