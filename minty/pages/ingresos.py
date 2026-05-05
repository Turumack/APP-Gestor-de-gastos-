"""P\u00e1gina Ingresos — simple + calculadora laboral."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    text_field, number_field, date_field,
    primary_button, ghost_button, field_label,
)
from minty.state.ingresos import IngresosState
from minty.state import PeriodoState


# ─────────────────────────────────────────────
# Tab RÁPIDO
# ─────────────────────────────────────────────
def _tab_simple() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.heading(
                    rx.cond(
                        IngresosState.editing_id,
                        "Editar ingreso",
                        "Registro rápido",
                    ),
                    size="5", font_family=T.FONT_HEAD, color=T.TEXT,
                    id="ingresos-form-top",
                ),
                rx.spacer(),
                rx.cond(
                    IngresosState.editing_id,
                    rx.badge("Modo edición", color_scheme="amber",
                             variant="soft"),
                    rx.fragment(),
                ),
                width="100%", align="center",
            ),
            rx.text("Para ingresos sin cálculo de horas extra.", size="2", color=T.TEXT_MUTED),
            rx.grid(
                text_field("Descripción", IngresosState.simple_desc,
                           IngresosState.set_simple_desc,
                           placeholder="Salario, Freelance, Bono..."),
                date_field("Fecha", IngresosState.simple_fecha,
                           IngresosState.set_simple_fecha),
                columns="2", spacing="3", width="100%",
            ),
            rx.grid(
                number_field("Salario Base (COP)", IngresosState.simple_salario,
                             IngresosState.set_simple_salario, step=10000),
                number_field("Aux. Transporte", IngresosState.simple_aux,
                             IngresosState.set_simple_aux, step=1000),
                number_field("Otros / Bonos", IngresosState.simple_otros,
                             IngresosState.set_simple_otros, step=10000),
                columns="3", spacing="3", width="100%",
            ),
            rx.grid(
                number_field("Meta Ahorro (%)", IngresosState.simple_meta,
                             IngresosState.set_simple_meta, step=1),
                number_field("Real depositado", IngresosState.simple_real,
                             IngresosState.set_simple_real, step=1000),
                columns="2", spacing="3", width="100%",
            ),
            rx.cond(
                IngresosState.cajas_opts.length() > 0,
                rx.vstack(
                    field_label("¿A qué caja llega este ingreso? (opcional)"),
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
                                IngresosState.cajas_opts,
                                lambda opt: rx.select.item(
                                    opt["etiqueta"],
                                    value=opt["id"].to_string(),
                                ),
                            ),
                        ),
                        value=IngresosState.simple_caja_id.to_string(),
                        on_change=IngresosState.set_simple_caja_id,
                        width="100%",
                    ),
                    spacing="1", align="stretch", width="100%",
                ),
                rx.fragment(),
            ),
            primary_button("Guardar ingreso", IngresosState.guardar_simple,
                           icon="save", width="100%"),
            rx.cond(
                IngresosState.editing_id,
                ghost_button("Cancelar edición",
                             IngresosState.cancelar_edicion,
                             icon="x", width="100%"),
                rx.fragment(),
            ),
            rx.cond(
                IngresosState.simple_msg != "",
                rx.text(IngresosState.simple_msg, size="2", color=T.GREEN),
                rx.fragment(),
            ),
            spacing="4",
            align="stretch",
            width="100%",
        ),
    )


# ─────────────────────────────────────────────
# Tab CALCULADORA laboral
# ─────────────────────────────────────────────
def _desglose_row(item) -> rx.Component:
    return rx.hstack(
        rx.text(item["label"], size="2", color=T.TEXT_MUTED),
        rx.spacer(),
        rx.text(f"{item['horas']} h", size="2", color=T.TEXT_DIM),
        rx.text(f"${item['monto']:,.0f}", size="2", color=T.TEXT, weight="medium",
                min_width="100px", text_align="right"),
        width="100%",
        padding="6px 0",
        border_bottom=f"1px solid {T.BORDER_SOFT}",
    )


def _mini_metric(label: str, value, color: str) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=T.TEXT_DIM, weight="medium", letter_spacing="0.05em"),
        rx.text(value, size="4", color=color, weight="bold", font_family=T.FONT_HEAD),
        spacing="1",
        align="start",
        padding="12px 16px",
        background="rgba(255,255,255,.03)",
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS,
        flex="1",
    )


def _tab_calc() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.vstack(
                rx.heading("Calculadora laboral", size="5", font_family=T.FONT_HEAD, color=T.TEXT),
                rx.text("Calcula tu neto con las 7 tarifas de extras del Código Sustantivo del Trabajo.",
                        size="2", color=T.TEXT_MUTED),
                spacing="1", align="start",
            ),

            # Datos contrato
            field_label("Datos del contrato"),
            rx.grid(
                text_field("Descripción", IngresosState.calc_desc, IngresosState.set_calc_desc),
                date_field("Fecha", IngresosState.calc_fecha, IngresosState.set_calc_fecha),
                number_field("Jornada semanal (h)", IngresosState.calc_horas_semana,
                             IngresosState.set_calc_horas_semana, step=1),
                columns="3", spacing="3", width="100%",
            ),
            rx.grid(
                number_field("Salario base (COP)", IngresosState.calc_salario,
                             IngresosState.set_calc_salario, step=10000),
                number_field("Aux. Transporte", IngresosState.calc_aux,
                             IngresosState.set_calc_aux, step=1000),
                columns="2", spacing="3", width="100%",
            ),

            rx.divider(opacity="0.3"),

            # Horas extra
            field_label("Horas extra y recargos del mes"),
            rx.grid(
                # No dominicales
                rx.vstack(
                    rx.text("No dominicales / festivas", size="2", color=T.PINK, weight="bold"),
                    number_field("Extra diurna (+25%)", IngresosState.h_ext_d,
                                 IngresosState.set_h_ext_d, step=0.5),
                    number_field("Extra nocturna (+75%)", IngresosState.h_ext_n,
                                 IngresosState.set_h_ext_n, step=0.5),
                    number_field("Recargo nocturno (+35%)", IngresosState.h_rec_n,
                                 IngresosState.set_h_rec_n, step=0.5),
                    spacing="3", align="stretch", width="100%",
                ),
                # Dominicales
                rx.vstack(
                    rx.text("Dominicales / festivas", size="2", color=T.VIOLET, weight="bold"),
                    number_field("Dominical diurna (+75%)", IngresosState.h_dom_d,
                                 IngresosState.set_h_dom_d, step=0.5),
                    number_field("Dominical nocturna (+110%)", IngresosState.h_dom_n,
                                 IngresosState.set_h_dom_n, step=0.5),
                    number_field("Extra dom. diurna (+100%)", IngresosState.h_ext_dom_d,
                                 IngresosState.set_h_ext_dom_d, step=0.5),
                    number_field("Extra dom. nocturna (+150%)", IngresosState.h_ext_dom_n,
                                 IngresosState.set_h_ext_dom_n, step=0.5),
                    spacing="3", align="stretch", width="100%",
                ),
                columns="2", spacing="4", width="100%",
            ),

            number_field("Otros bonos / comisiones (COP)",
                         IngresosState.h_otros_bonos,
                         IngresosState.set_h_otros_bonos, step=10000),

            rx.divider(opacity="0.3"),

            # Preview
            rx.cond(
                IngresosState.calc_salario > 0,
                rx.vstack(
                    rx.hstack(
                        rx.text("Valor hora ordinaria:", size="2", color=T.TEXT_MUTED),
                        rx.text(
                            rx.cond(IngresosState.valor_hora > 0,
                                    f"${IngresosState.valor_hora:.0f}", "-"),
                            size="2", color=T.VIOLET, weight="bold",
                        ),
                        spacing="2",
                    ),
                    rx.cond(
                        IngresosState.total_extras > 0,
                        glass_card(
                            rx.vstack(
                                rx.text("Desglose de extras", size="2", color=T.TEXT, weight="bold"),
                                rx.foreach(IngresosState.desglose_extras, _desglose_row),
                                rx.hstack(
                                    rx.text("Total extras", size="2", color=T.TEXT, weight="bold"),
                                    rx.spacer(),
                                    rx.text(f"${IngresosState.total_extras:,.0f}",
                                            size="3", color=T.GREEN, weight="bold",
                                            font_family=T.FONT_HEAD),
                                    width="100%", padding_top="8px",
                                ),
                                spacing="2", width="100%",
                            ),
                            padding="16px",
                            background="rgba(255,255,255,.02)",
                        ),
                        rx.fragment(),
                    ),
                    rx.hstack(
                        _mini_metric("Salario base",
                                     f"${IngresosState.calc_salario:,.0f}", T.TEXT),
                        _mini_metric("+ Extras",
                                     f"${IngresosState.total_extras:,.0f}", T.PINK),
                        _mini_metric("+ Aux. transporte",
                                     f"${IngresosState.calc_aux:,.0f}", T.BLUE),
                        _mini_metric("💵 Neto estimado",
                                     f"${IngresosState.calc_neto:,.0f}", T.GREEN),
                        spacing="3", width="100%",
                    ),
                    spacing="4", width="100%", align="stretch",
                ),
                rx.fragment(),
            ),

            rx.divider(opacity="0.3"),

            rx.grid(
                number_field("Meta Ahorro (%)", IngresosState.calc_meta,
                             IngresosState.set_calc_meta, step=1),
                number_field("Real depositado (si ya lo recibiste)",
                             IngresosState.calc_real,
                             IngresosState.set_calc_real, step=1000),
                columns="2", spacing="3", width="100%",
            ),
            rx.cond(
                IngresosState.cajas_opts.length() > 0,
                rx.vstack(
                    field_label("Caja destino del ingreso (opcional)"),
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
                                IngresosState.cajas_opts,
                                lambda opt: rx.select.item(
                                    opt["etiqueta"],
                                    value=opt["id"].to_string(),
                                ),
                            ),
                        ),
                        value=IngresosState.calc_caja_id.to_string(),
                        on_change=IngresosState.set_calc_caja_id,
                        width="100%",
                    ),
                    spacing="1", align="stretch", width="100%",
                ),
                rx.fragment(),
            ),
            primary_button("Guardar ingreso calculado", IngresosState.guardar_calc,
                           icon="save", width="100%"),
            rx.cond(
                IngresosState.calc_msg != "",
                rx.text(IngresosState.calc_msg, size="2", color=T.GREEN),
                rx.fragment(),
            ),
            spacing="4",
            align="stretch",
            width="100%",
        ),
    )


# ─────────────────────────────────────────────
# Lista de ingresos del período
# ─────────────────────────────────────────────
def _row_ingreso(r) -> rx.Component:
    return glass_card(
        rx.hstack(
            rx.vstack(
                rx.text(r.descripcion, size="3", color=T.TEXT, weight="bold"),
                rx.hstack(
                    rx.icon("calendar", size=12, color=T.TEXT_DIM),
                    rx.text(r.fecha, size="1", color=T.TEXT_DIM),
                    spacing="1",
                ),
                rx.cond(
                    r.caja_nombre != "",
                    rx.hstack(
                        rx.icon("wallet", size=12, color=T.VIOLET),
                        rx.text(r.caja_nombre, size="1", color=T.VIOLET, weight="medium"),
                        spacing="1",
                    ),
                    rx.fragment(),
                ),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.vstack(
                rx.text(f"Teórico: ${r.teorico:,.0f}", size="2", color=T.TEXT_MUTED),
                rx.cond(
                    r.real > 0,
                    rx.text(f"Real: ${r.real:,.0f}", size="2", color=T.GREEN, weight="bold"),
                    rx.text("Real: sin registrar", size="1", color=T.TEXT_DIM, style={"font_style": "italic"}),
                ),
                spacing="1", align="end",
            ),
            rx.button(
                rx.icon("pencil", size=14),
                on_click=IngresosState.editar(r.id),
                variant="ghost",
                color=T.VIOLET,
                cursor="pointer",
                size="1",
                title="Editar ingreso",
                _hover={"background": f"{T.VIOLET}15"},
            ),
            rx.button(
                rx.icon("trash-2", size=14),
                on_click=IngresosState.eliminar(r.id),
                variant="ghost",
                color=T.RED,
                cursor="pointer",
                size="1",
                _hover={"background": f"{T.RED}15"},
            ),
            spacing="3", width="100%", align="center",
        ),
        padding="16px 20px",
    )


def _resumen_mes() -> rx.Component:
    return rx.grid(
        glass_card(
            rx.vstack(
                rx.text("Total teórico", size="1", color=T.TEXT_DIM, weight="bold", letter_spacing="0.1em"),
                rx.text(f"${IngresosState.total_teorico:,.0f}",
                        size="6", color=T.TEXT, weight="bold", font_family=T.FONT_HEAD),
                spacing="1", align="start",
            ),
            padding="20px",
        ),
        glass_card(
            rx.vstack(
                rx.text("Total real", size="1", color=T.TEXT_DIM, weight="bold", letter_spacing="0.1em"),
                rx.cond(
                    IngresosState.total_real > 0,
                    rx.text(f"${IngresosState.total_real:,.0f}",
                            size="6", color=T.GREEN, weight="bold", font_family=T.FONT_HEAD),
                    rx.text("sin registrar", size="3", color=T.TEXT_DIM, style={"font_style": "italic"}),
                ),
                spacing="1", align="start",
            ),
            padding="20px",
        ),
        columns="2", spacing="4", width="100%",
    )


# ─────────────────────────────────────────────
# Página
# ─────────────────────────────────────────────
def ingresos_page() -> rx.Component:
    return main_layout(
        page_title(f"Ingresos", "Registra tu salario y extras del mes."),
        rx.hstack(
            rx.icon("calendar", size=14, color=T.VIOLET),
            rx.text(PeriodoState.periodo_label, size="2", color=T.VIOLET, weight="medium"),
            spacing="2",
            padding="6px 14px",
            border_radius="999px",
            background=f"{T.VIOLET}15",
            border=f"1px solid {T.VIOLET}33",
            display="inline-flex",
            align="center",
            margin_bottom="24px",
        ),

        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("⚡ Rápido", value="simple"),
                rx.tabs.trigger("🧮 Calculadora laboral", value="calc"),
            ),
            rx.tabs.content(_tab_simple(), value="simple", padding_top="20px"),
            rx.tabs.content(_tab_calc(), value="calc", padding_top="20px"),
            default_value="calc",
            width="100%",
        ),

        rx.box(height="40px"),
        rx.heading(f"Registrados en {PeriodoState.periodo_label}",
                   size="5", font_family=T.FONT_HEAD, padding_bottom="16px"),

        rx.cond(
            IngresosState.rows.length() > 0,
            rx.vstack(
                rx.foreach(IngresosState.rows, _row_ingreso),
                rx.box(height="16px"),
                _resumen_mes(),
                spacing="3", width="100%",
            ),
            glass_card(
                rx.vstack(
                    rx.icon("inbox", size=40, color=T.TEXT_DIM),
                    rx.text("Sin ingresos este período", size="3", color=T.TEXT_MUTED),
                    rx.text("Registra el primero usando alguna de las pestañas de arriba.",
                            size="2", color=T.TEXT_DIM),
                    spacing="3", align="center",
                    padding="40px 20px",
                ),
            ),
        ),
    )
