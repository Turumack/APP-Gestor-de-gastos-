"""P\u00e1gina Gastos con calendario visual."""
import reflex as rx
from cuentas_pro import theme as T
from cuentas_pro.components import (
    main_layout, glass_card, page_title, pill,
    text_field, number_field, date_field, select_field,
    primary_button, ghost_button, field_label,
)
from cuentas_pro.state.gastos import GastosState
from cuentas_pro.state import PeriodoState
from cuentas_pro.finance import CATEGORIAS_GASTO, MEDIOS_PAGO, MONEDAS


DOW = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


# ─────────── Celda calendario ───────────
def _celda(c) -> rx.Component:
    is_selected = GastosState.dia_seleccionado == c.fecha
    has_gastos = c.total > 0

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    c.dia.to_string(),
                    size="2",
                    weight="bold",
                    color=rx.cond(c.es_otro_mes, T.TEXT_DIM, T.TEXT),
                ),
                rx.spacer(),
                rx.cond(
                    c.count > 0,
                    rx.box(
                        rx.text(c.count.to_string(), size="1", color="white", weight="bold"),
                        width="16px", height="16px", border_radius="999px",
                        background=T.PINK,
                        display="flex", align_items="center", justify_content="center",
                        font_size="10px",
                    ),
                    rx.fragment(),
                ),
                width="100%",
            ),
            rx.spacer(),
            rx.cond(
                has_gastos,
                rx.text(c.total_fmt,
                        size="1", color=T.PINK, weight="medium",
                        font_family=T.FONT_MONO),
                rx.fragment(),
            ),
            spacing="1", height="100%", align="stretch",
        ),
        on_click=GastosState.seleccionar_dia(c.fecha),
        cursor="pointer",
        padding="8px",
        height="84px",
        border_radius=T.RADIUS_SM,
        background=rx.cond(
            is_selected,
            f"{T.VIOLET}22",
            rx.cond(c.es_otro_mes, "transparent", "rgba(255,255,255,.02)"),
        ),
        border=rx.cond(
            is_selected,
            f"1px solid {T.VIOLET}",
            f"1px solid {T.BORDER_SOFT}",
        ),
        opacity=rx.cond(c.es_otro_mes, "0.4", "1"),
        transition="all .15s ease",
        _hover={"background": "rgba(255,255,255,.05)", "border_color": T.BORDER},
    )


def _calendario() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.heading(PeriodoState.periodo_label, size="5", font_family=T.FONT_HEAD),
                rx.spacer(),
                rx.cond(
                    GastosState.dia_seleccionado != "",
                    ghost_button("Quitar filtro", GastosState.limpiar_filtro, icon="x"),
                    rx.fragment(),
                ),
                width="100%", align="center",
            ),
            rx.grid(
                *[rx.text(d, size="1", color=T.TEXT_DIM, weight="bold",
                          text_align="center", letter_spacing="0.1em") for d in DOW],
                columns="7", spacing="2", width="100%",
            ),
            rx.grid(
                rx.foreach(GastosState.celdas, _celda),
                columns="7", spacing="2", width="100%",
            ),
            spacing="3", align="stretch", width="100%",
        ),
    )


# ─────────── Formulario ───────────
def _form() -> rx.Component:
    return rx.cond(
        GastosState.form_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(GastosState.form_editing_id, "Editar gasto", "Nuevo gasto"),
                        size="5", font_family=T.FONT_HEAD,
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=16),
                        on_click=GastosState.toggle_form,
                        variant="ghost", cursor="pointer", color=T.TEXT_MUTED,
                    ),
                    width="100%",
                ),
                rx.grid(
                    date_field("Fecha", GastosState.form_fecha, GastosState.set_form_fecha),
                    text_field("Descripción", GastosState.form_desc,
                               GastosState.set_form_desc, placeholder="Ej: Mercado"),
                    columns="2", spacing="3", width="100%",
                ),

                # Moneda + monto (muestra bloque de tasa si la moneda no es COP)
                rx.grid(
                    select_field("Moneda", GastosState.form_moneda,
                                 GastosState.set_form_moneda, MONEDAS),
                    rx.cond(
                        GastosState.form_moneda != "COP",
                        number_field(
                            "Monto (" + GastosState.form_moneda + ")",
                            GastosState.form_monto_original,
                            GastosState.set_form_monto_original, step=1,
                        ),
                        number_field("Monto (COP)", GastosState.form_monto,
                                     GastosState.set_form_monto, step=1000),
                    ),
                    rx.cond(
                        GastosState.form_moneda != "COP",
                        rx.vstack(
                            field_label("Tasa " + GastosState.form_moneda + "→COP"),
                            rx.hstack(
                                rx.input(
                                    value=GastosState.form_trm.to_string(),
                                    on_change=GastosState.set_form_trm,
                                    type="number", step=0.01,
                                    background="rgba(255,255,255,0.04)",
                                    border=f"1px solid {T.BORDER}",
                                    border_radius=T.RADIUS_SM,
                                    color=T.TEXT, padding="10px 12px",
                                    height="40px", flex="1",
                                ),
                                rx.button(
                                    rx.icon("refresh-cw", size=14),
                                    on_click=GastosState.refrescar_trm,
                                    background=T.VIOLET,
                                    color="white",
                                    height="40px", padding="0 12px",
                                    cursor="pointer", border="none",
                                    border_radius=T.RADIUS_SM,
                                    title="Obtener tasa oficial",
                                ),
                                spacing="2", width="100%",
                            ),
                            spacing="1", align="stretch", width="100%",
                        ),
                        rx.fragment(),
                    ),
                    columns="3", spacing="3", width="100%",
                ),

                rx.cond(
                    (GastosState.form_moneda != "COP") & (GastosState.form_monto > 0),
                    rx.text(
                        "Equivalente: $" + GastosState.form_monto.to_string(),
                        size="2", color=T.TEXT_MUTED,
                    ),
                    rx.fragment(),
                ),

                rx.grid(
                    select_field("Categoría", GastosState.form_categoria,
                                 GastosState.set_form_categoria, CATEGORIAS_GASTO),
                    select_field("Medio de pago", GastosState.form_medio,
                                 GastosState.set_form_medio, MEDIOS_PAGO),
                    columns="2", spacing="3", width="100%",
                ),

                # Selector de caja (origen del dinero)
                rx.cond(
                    GastosState.cajas_opts.length() > 0,
                    rx.vstack(
                        field_label("¿Desde qué caja? (opcional)"),
                        rx.select.root(
                            rx.select.trigger(
                                placeholder="Sin caja asignada",
                                background="rgba(255,255,255,0.04)",
                                border=f"1px solid {T.BORDER}",
                                border_radius=T.RADIUS_SM,
                                width="100%", height="40px",
                            ),
                            rx.select.content(
                                rx.select.item("— Sin caja —", value="0"),
                                rx.foreach(
                                    GastosState.cajas_opts,
                                    lambda opt: rx.select.item(
                                        opt["etiqueta"],
                                        value=opt["id"].to_string(),
                                    ),
                                ),
                            ),
                            value=GastosState.form_caja_id.to_string(),
                            on_change=GastosState.set_form_caja_id,
                            width="100%",
                        ),
                        spacing="1", align="stretch", width="100%",
                    ),
                    rx.box(
                        rx.text("Tip: crea tus cajas (cuentas/tarjetas) para rastrear desde dónde pagas.",
                                size="1", color=T.TEXT_DIM),
                        padding="4px 0",
                    ),
                ),

                # Listas de compra: cargar ítem o grupo (total/parcial) al formulario
                rx.cond(
                    GastosState.shopping_groups_opts.length() > 0,
                    glass_card(
                        rx.vstack(
                            rx.text("Listas de compra", size="2", color=T.TEXT, weight="bold"),
                            rx.grid(
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
                                            rx.select.item("— Sin grupo —", value="0"),
                                            rx.foreach(
                                                GastosState.shopping_groups_opts,
                                                lambda g: rx.select.item(g["etiqueta"], value=g["id"].to_string()),
                                            ),
                                        ),
                                        value=GastosState.form_shopping_group_id.to_string(),
                                        on_change=GastosState.set_form_shopping_group_id,
                                        width="100%",
                                    ),
                                    spacing="1", width="100%",
                                ),
                                rx.vstack(
                                    field_label("Ítem (opcional)"),
                                    rx.select.root(
                                        rx.select.trigger(
                                            placeholder="Selecciona ítem",
                                            background="rgba(255,255,255,0.04)",
                                            border=f"1px solid {T.BORDER}",
                                            border_radius=T.RADIUS_SM,
                                            width="100%", height="40px",
                                        ),
                                        rx.select.content(
                                            rx.select.item("— Todo el grupo —", value="0"),
                                            rx.foreach(
                                                GastosState.shopping_items_opts,
                                                lambda it: rx.select.item(it["etiqueta"], value=it["id"].to_string()),
                                            ),
                                        ),
                                        value=GastosState.form_shopping_item_id.to_string(),
                                        on_change=GastosState.set_form_shopping_item_id,
                                        width="100%",
                                    ),
                                    spacing="1", width="100%",
                                ),
                                number_field("% a aplicar", GastosState.form_shopping_pct,
                                             GastosState.set_form_shopping_pct, step=5),
                                columns="3", spacing="3", width="100%",
                            ),
                            rx.hstack(
                                ghost_button("Cargar ítem", GastosState.aplicar_item_lista, icon="list"),
                                ghost_button("Cargar grupo", GastosState.aplicar_grupo_lista, icon="clipboard"),
                                spacing="2",
                            ),
                            rx.text("Tip: con 50% puedes registrar solo una parte de la lista/ítem.",
                                    size="1", color=T.TEXT_DIM),
                            spacing="2", width="100%", align="stretch",
                        ),
                        padding="12px 14px",
                    ),
                    rx.fragment(),
                ),
                text_field("Notas (opcional)", GastosState.form_notas,
                           GastosState.set_form_notas),
                rx.hstack(
                    rx.checkbox(
                        "Gasto recurrente",
                        checked=GastosState.form_recurrente,
                        on_change=GastosState.set_form_recurrente,
                    ),
                    spacing="2",
                ),
                rx.hstack(
                    primary_button("Guardar", GastosState.guardar, icon="save", flex="1"),
                    ghost_button("Cancelar", GastosState.toggle_form),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    GastosState.form_msg != "",
                    rx.text(GastosState.form_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="4", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


# ─────────── Fila de gasto ───────────
def _row_gasto(r) -> rx.Component:
    return glass_card(
        rx.hstack(
            rx.box(width="4px", height="40px", border_radius="4px",
                   background=r.color),
            rx.vstack(
                rx.hstack(
                    rx.text(r.descripcion, size="3", color=T.TEXT, weight="bold"),
                    rx.cond(
                        r.recurrente,
                        rx.box(
                            rx.icon("repeat", size=10, color=T.BLUE),
                            padding="2px 6px", border_radius="999px",
                            background=f"{T.BLUE}22",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2", align="center",
                ),
                rx.hstack(
                    rx.text(r.categoria, size="1", color=r.color, weight="medium"),
                    rx.text("·", size="1", color=T.TEXT_DIM),
                    rx.text(r.fecha, size="1", color=T.TEXT_DIM),
                    rx.text("·", size="1", color=T.TEXT_DIM),
                    rx.text(r.medio_pago, size="1", color=T.TEXT_DIM),
                    spacing="1",
                ),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.vstack(
                rx.text(r.monto_fmt, size="4", color=T.TEXT,
                        weight="bold", font_family=T.FONT_HEAD),
                rx.cond(
                    r.origen_fmt != "",
                    rx.text(r.origen_fmt, size="1", color=T.TEXT_DIM),
                    rx.fragment(),
                ),
                rx.cond(
                    r.caja_nombre != "",
                    rx.hstack(
                        rx.icon("wallet", size=10, color=T.VIOLET),
                        rx.text(r.caja_nombre, size="1", color=T.VIOLET, weight="medium"),
                        spacing="1",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    r.shopping_ref != "",
                    rx.hstack(
                        rx.icon("list", size=10, color=T.BLUE),
                        rx.text(r.shopping_ref, size="1", color=T.BLUE, weight="medium"),
                        spacing="1",
                    ),
                    rx.fragment(),
                ),
                spacing="0", align="end",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=14),
                    on_click=GastosState.editar(r.id),
                    variant="ghost", cursor="pointer", size="1",
                    color=T.TEXT_MUTED,
                    _hover={"background": "rgba(255,255,255,.08)", "color": T.TEXT},
                ),
                rx.button(
                    rx.icon("trash-2", size=14),
                    on_click=GastosState.eliminar(r.id),
                    variant="ghost", cursor="pointer", size="1",
                    color=T.RED,
                    _hover={"background": f"{T.RED}15"},
                ),
                spacing="1",
            ),
            spacing="3", width="100%", align="center",
        ),
        padding="12px 16px",
    )


# ─────────── Resumen por categoría ───────────
def _bar_categoria(c) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.box(width="10px", height="10px", border_radius="999px", background=c["color"]),
            rx.text(c["nombre"], size="2", color=T.TEXT),
            rx.spacer(),
            rx.text(f"${c['total']:,.0f}", size="2", color=T.TEXT, weight="bold"),
            rx.text(f"{c['pct']:.1f}%", size="1", color=T.TEXT_DIM, min_width="50px", text_align="right"),
            width="100%", spacing="2",
        ),
        rx.box(
            rx.box(
                width=f"{c['pct']}%", height="100%",
                background=c["color"], border_radius="999px",
                transition="width .5s ease",
            ),
            width="100%", height="6px",
            background="rgba(255,255,255,.05)",
            border_radius="999px",
        ),
        spacing="1", width="100%",
    )


def _resumen_categorias() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.heading("Por categoría", size="4", font_family=T.FONT_HEAD, color=T.TEXT),
            rx.foreach(GastosState.por_categoria, _bar_categoria),
            spacing="3", width="100%", align="stretch",
        ),
    )


# ─────────── Página ───────────
def gastos_page() -> rx.Component:
    return main_layout(
        rx.hstack(
            page_title("Gastos", "Tus egresos del período con calendario visual."),
            rx.spacer(),
            ghost_button("Generar recurrentes", GastosState.generar_recurrentes, icon="repeat"),
            ghost_button("Exportar CSV", GastosState.exportar_csv, icon="download"),
            primary_button(
                rx.cond(GastosState.form_open, "Cerrar", "Nuevo gasto"),
                GastosState.toggle_form,
                icon=rx.cond(GastosState.form_open, "x", "plus"),
            ),
            width="100%", align="start",
            spacing="3",
        ),

        rx.hstack(
            rx.box(
                rx.vstack(
                    rx.text("Total del mes", size="1", color=T.TEXT_DIM,
                            weight="bold", letter_spacing="0.1em"),
                    rx.text(f"${GastosState.total_mes:,.0f}",
                            size="7", color=T.PINK, weight="bold",
                            font_family=T.FONT_HEAD),
                    spacing="1",
                ),
                padding="20px 24px",
                background=f"linear-gradient(135deg, {T.PINK}15 0%, {T.VIOLET}15 100%)",
                border=f"1px solid {T.PINK}33",
                border_radius=T.RADIUS_LG,
                flex="1",
            ),
            spacing="3", width="100%", padding_bottom="24px",
        ),

        _form(),
        rx.cond(GastosState.form_open, rx.box(height="24px"), rx.fragment()),

        rx.grid(
            _calendario(),
            _resumen_categorias(),
            columns="2",
            spacing="4",
            width="100%",
            grid_template_columns="2fr 1fr",
        ),

        rx.box(height="32px"),
        rx.hstack(
            rx.heading(
                rx.cond(
                    GastosState.dia_seleccionado != "",
                    f"Gastos del {GastosState.dia_seleccionado}",
                    "Todos los gastos del mes",
                ),
                size="5", font_family=T.FONT_HEAD,
            ),
            rx.spacer(),
            rx.hstack(
                rx.icon("search", size=14, color=T.TEXT_DIM),
                rx.input(
                    value=GastosState.busqueda,
                    on_change=GastosState.set_busqueda,
                    placeholder="Buscar descripción, categoría, notas…",
                    background="rgba(255,255,255,0.04)",
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_SM,
                    color=T.TEXT,
                    padding="8px 12px",
                    height="36px",
                    width="280px",
                ),
                rx.cond(
                    GastosState.busqueda != "",
                    rx.button(
                        rx.icon("x", size=14),
                        on_click=GastosState.limpiar_busqueda,
                        variant="ghost", size="1",
                        cursor="pointer", color=T.TEXT_MUTED,
                    ),
                    rx.fragment(),
                ),
                spacing="2", align="center",
            ),
            width="100%",
            padding_bottom="16px",
            align="center",
        ),

        rx.cond(
            GastosState.rows_filtradas.length() > 0,
            rx.vstack(
                rx.foreach(GastosState.rows_filtradas, _row_gasto),
                spacing="2", width="100%",
            ),
            glass_card(
                rx.vstack(
                    rx.icon("inbox", size=40, color=T.TEXT_DIM),
                    rx.text("Sin gastos registrados", size="3", color=T.TEXT_MUTED),
                    spacing="3", align="center",
                    padding="40px 20px",
                ),
            ),
        ),
    )
