"""Página Metas — bolsas de ahorro persistentes."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    number_field, text_field, date_field,
    primary_button, ghost_button, field_label,
)
from minty.state.metas import MetasState, COLORES_META, ICONOS_META


def _metric_top() -> rx.Component:
    return rx.grid(
        glass_card(
            rx.hstack(
                rx.box(
                    rx.icon("piggy-bank", size=22, color="white"),
                    background=T.GRADIENT_BRAND,
                    border_radius="10px",
                    padding="10px",
                ),
                rx.vstack(
                    rx.text("Acumulado total", size="2", color=T.TEXT_MUTED),
                    rx.heading(MetasState.total_acumulado_fmt, size="6",
                               font_family=T.FONT_HEAD, color=T.TEXT),
                    spacing="0", align="start",
                ),
                spacing="3", align="center", width="100%",
            ),
            padding="16px 20px",
        ),
        glass_card(
            rx.hstack(
                rx.box(
                    rx.icon("target", size=22, color="white"),
                    background=T.GRADIENT_BRAND_SOFT,
                    border_radius="10px",
                    padding="10px",
                ),
                rx.vstack(
                    rx.text("Objetivo total", size="2", color=T.TEXT_MUTED),
                    rx.heading(MetasState.total_objetivo_fmt, size="6",
                               font_family=T.FONT_HEAD, color=T.TEXT),
                    spacing="0", align="start",
                ),
                spacing="3", align="center", width="100%",
            ),
            padding="16px 20px",
        ),
        glass_card(
            rx.hstack(
                rx.box(
                    rx.icon("trending-up", size=22, color="white"),
                    background=T.VIOLET,
                    border_radius="10px",
                    padding="10px",
                ),
                rx.vstack(
                    rx.text("Progreso global", size="2", color=T.TEXT_MUTED),
                    rx.heading(f"{MetasState.pct_global:.1f}%", size="6",
                               font_family=T.FONT_HEAD, color=T.TEXT),
                    spacing="0", align="start",
                ),
                spacing="3", align="center", width="100%",
            ),
            padding="16px 20px",
        ),
        columns="3", spacing="4", width="100%",
    )


def _color_swatch(color: str) -> rx.Component:
    is_sel = MetasState.form_color == color
    return rx.box(
        on_click=MetasState.set_form_color(color),
        width="32px", height="32px",
        border_radius="50%",
        background=color,
        cursor="pointer",
        border=rx.cond(is_sel, "3px solid white", "2px solid transparent"),
        transition="all .15s ease",
        _hover={"transform": "scale(1.1)"},
    )


def _icon_swatch(icon: str) -> rx.Component:
    is_sel = MetasState.form_icono == icon
    return rx.box(
        rx.icon(icon, size=18, color=rx.cond(is_sel, "white", T.TEXT_MUTED)),
        on_click=MetasState.set_form_icono(icon),
        width="40px", height="40px",
        border_radius="10px",
        background=rx.cond(is_sel, T.VIOLET, "rgba(255,255,255,0.04)"),
        border=f"1px solid {T.BORDER}",
        cursor="pointer",
        display="flex",
        align_items="center",
        justify_content="center",
        transition="all .15s ease",
        _hover={"background": "rgba(255,255,255,0.08)"},
    )


def _form_meta() -> rx.Component:
    return rx.cond(
        MetasState.form_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(MetasState.form_editing_id,
                                "Editar meta", "Nueva meta"),
                        size="5", font_family=T.FONT_HEAD,
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("x", size=16),
                              on_click=MetasState.toggle_form,
                              variant="ghost", color=T.TEXT_MUTED,
                              cursor="pointer"),
                    width="100%",
                ),
                rx.grid(
                    text_field("Nombre",
                               MetasState.form_nombre,
                               MetasState.set_form_nombre,
                               placeholder="Ej: Vacaciones, Carro, Emergencia"),
                    number_field("Objetivo (COP, 0 = sin objetivo)",
                                 MetasState.form_objetivo,
                                 MetasState.set_form_objetivo, step=10_000),
                    date_field("Fecha objetivo (opcional)",
                               MetasState.form_fecha_objetivo,
                               MetasState.set_form_fecha_objetivo),
                    columns="3", spacing="3", width="100%",
                ),
                rx.vstack(
                    field_label("Color"),
                    rx.hstack(
                        rx.foreach(MetasState.colores, _color_swatch),
                        spacing="2", wrap="wrap",
                    ),
                    spacing="1", width="100%", align="stretch",
                ),
                rx.vstack(
                    field_label("Icono"),
                    rx.hstack(
                        rx.foreach(MetasState.iconos, _icon_swatch),
                        spacing="2", wrap="wrap",
                    ),
                    spacing="1", width="100%", align="stretch",
                ),
                text_field("Notas (opcional)",
                           MetasState.form_notas,
                           MetasState.set_form_notas,
                           placeholder="¿Para qué es esta meta?"),
                rx.hstack(
                    primary_button("Guardar", MetasState.guardar,
                                   icon="save", flex="1"),
                    ghost_button("Cancelar", MetasState.toggle_form),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    MetasState.form_msg != "",
                    rx.text(MetasState.form_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="3", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def _form_aporte() -> rx.Component:
    return rx.cond(
        MetasState.aporte_open,
        rx.box(
            rx.box(
                glass_card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("plus", size=20, color=T.VIOLET),
                            rx.heading(
                                "Aportar a " + MetasState.aporte_meta_nombre,
                                size="5", font_family=T.FONT_HEAD,
                            ),
                            rx.spacer(),
                            rx.button(rx.icon("x", size=16),
                                      on_click=MetasState.cerrar_aporte,
                                      variant="ghost", color=T.TEXT_MUTED,
                                      cursor="pointer"),
                            width="100%", align="center",
                        ),
                        rx.grid(
                            number_field("Monto (COP)",
                                         MetasState.aporte_monto,
                                         MetasState.set_aporte_monto,
                                         step=10_000),
                            date_field("Fecha",
                                       MetasState.aporte_fecha,
                                       MetasState.set_aporte_fecha),
                            columns="2", spacing="3", width="100%",
                        ),
                        rx.vstack(
                            field_label("Caja origen"),
                            rx.select.root(
                                rx.select.trigger(width="100%"),
                                rx.select.content(
                                    rx.foreach(
                                        MetasState.cajas_opts,
                                        lambda c: rx.select.item(
                                            c["label"], value=c["value"],
                                        ),
                                    ),
                                ),
                                value=MetasState.aporte_caja_id.to_string(),
                                on_change=MetasState.set_aporte_caja,
                            ),
                            spacing="1", width="100%", align="stretch",
                        ),
                        text_field("Descripción",
                                   MetasState.aporte_descripcion,
                                   MetasState.set_aporte_descripcion,
                                   placeholder="Aporte mensual"),
                        rx.cond(
                            MetasState.aporte_msg != "",
                            rx.text(MetasState.aporte_msg, size="2", color=T.AMBER),
                            rx.fragment(),
                        ),
                        rx.hstack(
                            primary_button("Aportar",
                                           MetasState.guardar_aporte,
                                           icon="check", flex="1"),
                            ghost_button("Cancelar",
                                         MetasState.cerrar_aporte),
                            spacing="3", width="100%",
                        ),
                        spacing="3", width="100%", align="stretch",
                    ),
                ),
                width="100%",
                max_width="520px",
            ),
            position="fixed",
            top="0", left="0", right="0", bottom="0",
            background="rgba(0,0,0,0.6)",
            backdrop_filter="blur(4px)",
            z_index="100",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="20px",
        ),
        rx.fragment(),
    )


def _meta_card(m) -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(m.icono, size=20, color="white"),
                    width="44px", height="44px",
                    border_radius="12px",
                    background=m.color,
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.heading(m.nombre, size="4",
                               font_family=T.FONT_HEAD, color=T.TEXT),
                    rx.text(
                        m.n_aportes.to_string() + " aportes",
                        size="1", color=T.TEXT_DIM,
                    ),
                    spacing="0", align="start",
                ),
                rx.spacer(),
                rx.cond(
                    m.completada,
                    rx.badge("Completada", color_scheme="green",
                             variant="soft"),
                    rx.fragment(),
                ),
                width="100%", align="center", spacing="3",
            ),

            rx.hstack(
                rx.vstack(
                    rx.text("Acumulado", size="1", color=T.TEXT_DIM),
                    rx.heading(m.acumulado_fmt, size="5",
                               font_family=T.FONT_HEAD, color=m.color),
                    spacing="0", align="start",
                ),
                rx.spacer(),
                rx.vstack(
                    rx.text("Objetivo", size="1", color=T.TEXT_DIM),
                    rx.heading(m.objetivo_fmt, size="5",
                               font_family=T.FONT_HEAD, color=T.TEXT_MUTED),
                    spacing="0", align="end",
                ),
                width="100%",
            ),

            # Barra de progreso (solo si tiene objetivo)
            rx.cond(
                m.objetivo > 0,
                rx.vstack(
                    rx.box(
                        rx.box(
                            width=m.pct.to_string() + "%",
                            height="100%",
                            background=m.color,
                            border_radius="999px",
                            transition="width .3s ease",
                        ),
                        width="100%", height="8px",
                        background="rgba(255,255,255,0.06)",
                        border_radius="999px",
                        overflow="hidden",
                    ),
                    rx.hstack(
                        rx.text(m.pct_fmt, size="1", color=m.color, weight="bold"),
                        rx.spacer(),
                        rx.text("Faltan " + m.restante_fmt,
                                size="1", color=T.TEXT_DIM),
                        width="100%",
                    ),
                    spacing="1", width="100%",
                ),
                rx.fragment(),
            ),

            rx.hstack(
                rx.button(
                    rx.hstack(rx.icon("plus", size=14),
                              rx.text("Aportar", size="2"), spacing="1"),
                    on_click=MetasState.abrir_aporte(m.id),
                    background=T.GRADIENT_BRAND, color="white",
                    cursor="pointer", border="none",
                    border_radius=T.RADIUS, padding="6px 14px",
                ),
                rx.button(
                    rx.icon("list", size=14),
                    on_click=MetasState.ver_detalle(m.id),
                    variant="ghost", color=T.TEXT_MUTED,
                    cursor="pointer", title="Ver aportes",
                ),
                rx.button(
                    rx.icon("pencil", size=14),
                    on_click=MetasState.editar(m.id),
                    variant="ghost", color=T.TEXT_MUTED,
                    cursor="pointer", title="Editar",
                ),
                rx.button(
                    rx.icon("trash-2", size=14),
                    on_click=MetasState.eliminar(m.id),
                    variant="ghost", color=T.PINK,
                    cursor="pointer", title="Eliminar",
                ),
                spacing="2", width="100%", align="center",
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def _aporte_row(a) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon("arrow-down-right", size=14, color="white"),
            width="32px", height="32px",
            border_radius="10px",
            background=a.color,
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.vstack(
            rx.text(a.descripcion, size="2", color=T.TEXT, weight="medium"),
            rx.hstack(
                rx.text(a.fecha, size="1", color=T.TEXT_DIM),
                rx.text("·", size="1", color=T.TEXT_DIM),
                rx.text(a.caja_nombre, size="1", color=T.TEXT_DIM),
                spacing="1",
            ),
            spacing="1", align="start",
        ),
        rx.spacer(),
        rx.text(a.monto_fmt, size="2", color=T.GREEN, weight="bold"),
        rx.button(
            rx.icon("trash-2", size=12),
            on_click=MetasState.eliminar_aporte(a.id),
            variant="ghost", color=T.PINK,
            cursor="pointer", size="1",
        ),
        spacing="3", width="100%", align="center",
        padding="10px 12px",
        border_radius=T.RADIUS_SM,
        _hover={"background": "rgba(255,255,255,.03)"},
    )


def _detalle_card() -> rx.Component:
    return rx.cond(
        MetasState.detalle_meta_id != None,  # noqa: E711
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.icon("list", size=18, color=T.VIOLET),
                    rx.heading(
                        "Aportes a " + MetasState.detalle_meta_nombre,
                        size="4", font_family=T.FONT_HEAD,
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("x", size=14),
                              on_click=MetasState.cerrar_detalle,
                              variant="ghost", color=T.TEXT_MUTED,
                              cursor="pointer"),
                    width="100%", align="center",
                ),
                rx.cond(
                    MetasState.detalle_aportes.length() > 0,
                    rx.vstack(
                        rx.foreach(MetasState.detalle_aportes, _aporte_row),
                        spacing="1", width="100%",
                    ),
                    rx.text("Aún no hay aportes a esta meta.",
                            size="2", color=T.TEXT_MUTED,
                            padding="20px", text_align="center"),
                ),
                spacing="3", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def metas_page() -> rx.Component:
    return main_layout(
        rx.hstack(
            page_title("Metas",
                       "Bolsas de ahorro persistentes — atraviesan periodos."),
            rx.spacer(),
            primary_button("Nueva meta", MetasState.toggle_form, icon="plus"),
            width="100%", align="start",
        ),
        _metric_top(),
        rx.box(height="16px"),
        _form_meta(),
        rx.cond(
            MetasState.form_open,
            rx.box(height="16px"),
            rx.fragment(),
        ),
        rx.cond(
            MetasState.rows.length() > 0,
            rx.grid(
                rx.foreach(MetasState.rows, _meta_card),
                columns="2", spacing="4", width="100%",
            ),
            glass_card(
                rx.vstack(
                    rx.icon("piggy-bank", size=40, color=T.TEXT_DIM),
                    rx.heading("Sin metas aún", size="4",
                               font_family=T.FONT_HEAD, color=T.TEXT_MUTED),
                    rx.text(
                        "Crea tu primera meta y empieza a apartar dinero "
                        "para lo que de verdad te importa.",
                        size="2", color=T.TEXT_DIM, text_align="center",
                    ),
                    primary_button("Crear meta",
                                   MetasState.toggle_form, icon="plus"),
                    spacing="3", align="center",
                    padding="40px 20px",
                ),
            ),
        ),
        rx.box(height="24px"),
        _detalle_card(),
        _form_aporte(),
    )
