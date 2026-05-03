"""Página Cajas: gestión de cuentas, tarjetas y efectivo."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    text_field, number_field, date_field, select_field,
    primary_button, ghost_button, field_label,
)
from minty.state.cajas import CajasState
from minty.finance import TIPOS_CAJA, TIPO_CAJA_LABEL


COLORES_DISPONIBLES = ["#a78bfa", "#f472b6", "#34d399", "#fbbf24",
                       "#60a5fa", "#f87171", "#38bdf8", "#c084fc"]


def _metric_total() -> rx.Component:
    return rx.grid(
        glass_card(
            rx.vstack(
                rx.text("Patrimonio proyectado", size="2", color=T.TEXT_MUTED, weight="medium"),
                rx.heading(CajasState.total_fmt, size="8",
                           font_family=T.FONT_HEAD, color=T.VIOLET),
                rx.text("Cierre del período (excluye tarjetas de crédito)",
                        size="1", color=T.TEXT_DIM),
                spacing="1", align="start",
            ),
            padding="20px 24px",
        ),
        rx.cond(
            CajasState.total_cupo_tc > 0,
            glass_card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("credit-card", size=14, color=T.PINK),
                        rx.text("Tarjetas de crédito", size="2",
                                color=T.TEXT_MUTED, weight="medium"),
                        spacing="2", align="center",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Deuda", size="1", color=T.TEXT_DIM),
                            rx.heading(CajasState.total_deuda_tc_fmt, size="6",
                                       font_family=T.FONT_HEAD, color=T.PINK),
                            spacing="0",
                        ),
                        rx.vstack(
                            rx.text("Disponible", size="1", color=T.TEXT_DIM),
                            rx.heading(CajasState.total_disponible_tc_fmt, size="6",
                                       font_family=T.FONT_HEAD, color=T.GREEN),
                            spacing="0",
                        ),
                        rx.vstack(
                            rx.text("Cupo total", size="1", color=T.TEXT_DIM),
                            rx.heading(CajasState.total_cupo_tc_fmt, size="6",
                                       font_family=T.FONT_HEAD, color=T.TEXT),
                            spacing="0",
                        ),
                        spacing="5", align="start",
                    ),
                    spacing="2", align="start",
                ),
                padding="20px 24px",
            ),
            rx.fragment(),
        ),
        columns="2", spacing="3", width="100%",
    )


def _row_caja(c) -> rx.Component:
    return rx.cond(c.es_tc, _row_caja_tc(c), _row_caja_normal(c))


def _row_caja_tc(c) -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.box(width="4px", height="42px", border_radius="4px",
                       background=T.GRADIENT_BRAND),
                rx.vstack(
                    rx.hstack(
                        rx.icon("credit-card", size=16, color=T.PINK),
                        rx.text(c.nombre, size="3", color=T.TEXT, weight="bold"),
                        rx.box(
                            rx.text("TC", size="1", color=T.PINK, weight="bold"),
                            padding="2px 8px", border_radius="999px",
                            background=f"{T.PINK}22",
                        ),
                        spacing="2", align="center",
                    ),
                    rx.cond(
                        c.entidad != "",
                        rx.text(c.entidad, size="1", color=T.TEXT_DIM),
                        rx.fragment(),
                    ),
                    spacing="1", align="start",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.button(
                        rx.icon("banknote", size=14),
                        rx.text("Pagar tarjeta", size="1", weight="medium"),
                        on_click=CajasState.pagar_tarjeta(c.id),
                        variant="ghost", cursor="pointer", size="1",
                        color=T.GREEN,
                        _hover={"background": f"{T.GREEN}18"},
                    ),
                    rx.button(
                        rx.icon("plus", size=14),
                        rx.text("Cargar deuda", size="1", weight="medium"),
                        on_click=CajasState.abrir_cargar_deuda(c.id),
                        variant="ghost", cursor="pointer", size="1",
                        color=T.PINK,
                        _hover={"background": f"{T.PINK}18"},
                        title="Carga directa de deuda (sin recálculo de intereses)",
                    ),
                    rx.button(
                        rx.icon("pencil", size=14),
                        on_click=CajasState.editar(c.id),
                        variant="ghost", cursor="pointer", size="1",
                        color=T.TEXT_MUTED,
                    ),
                    rx.button(
                        rx.icon("trash-2", size=14),
                        on_click=CajasState.eliminar(c.id),
                        variant="ghost", cursor="pointer", size="1",
                        color=T.RED,
                    ),
                    spacing="1",
                ),
                width="100%", align="center",
            ),
            rx.grid(
                rx.vstack(
                    rx.text("Deuda actual", size="1", color=T.TEXT_DIM),
                    rx.text(c.deuda_cop_fmt, size="5", color=T.PINK,
                            weight="bold", font_family=T.FONT_HEAD),
                    spacing="0",
                ),
                rx.vstack(
                    rx.text("Cupo disponible", size="1", color=T.TEXT_DIM),
                    rx.text(c.cupo_disponible_fmt, size="5", color=T.GREEN,
                            weight="bold", font_family=T.FONT_HEAD),
                    rx.text("de " + c.cupo_total_fmt, size="1", color=T.TEXT_DIM),
                    spacing="0",
                ),
                rx.vstack(
                    rx.text("Cuota de manejo", size="1", color=T.TEXT_DIM),
                    rx.text(c.cuota_manejo_fmt, size="3", color=T.TEXT,
                            weight="bold", font_family=T.FONT_HEAD),
                    rx.text("Día " + c.dia_cobro_cuota.to_string()
                            + " · Pago " + c.dia_pago.to_string(),
                            size="1", color=T.TEXT_DIM),
                    spacing="0",
                ),
                columns="3", spacing="3", width="100%",
            ),
            rx.box(
                rx.box(
                    width=c.pct_uso_fmt, height="6px",
                    background=T.GRADIENT_BRAND, border_radius="3px",
                ),
                width="100%", height="6px",
                background="rgba(255,255,255,0.06)", border_radius="3px",
            ),
            rx.hstack(
                rx.text("Uso del cupo: " + c.pct_uso_fmt,
                        size="1", color=T.TEXT_MUTED),
                rx.spacer(),
                rx.cond(
                    c.interes_ea_compras > 0,
                    rx.text("EA compras: " + c.interes_ea_compras.to_string() + "%",
                            size="1", color=T.TEXT_DIM),
                    rx.fragment(),
                ),
                rx.cond(
                    c.interes_ea_avances > 0,
                    rx.text("· EA avances: " + c.interes_ea_avances.to_string() + "%",
                            size="1", color=T.TEXT_DIM),
                    rx.fragment(),
                ),
                width="100%",
            ),
            rx.hstack(
                rx.icon("dollar-sign", size=14, color=T.TEXT_MUTED),
                rx.text("TRM propio del banco:", size="1", color=T.TEXT_MUTED),
                rx.input(
                    default_value=c.trm_tc.to_string(),
                    type="number",
                    step="1",
                    on_blur=lambda v: CajasState.actualizar_trm_tc(c.id, v),
                    width="120px", height="30px",
                    background="rgba(255,255,255,0.04)",
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_SM,
                    color=T.TEXT,
                ),
                rx.text("COP/USD", size="1", color=T.TEXT_DIM),
                rx.text("(actual: " + c.trm_tc_fmt + ")",
                        size="1", color=T.TEXT_DIM),
                spacing="2", align="center", width="100%",
            ),
            spacing="3", width="100%", align="stretch",
        ),
        padding="16px 20px",
    )


def _row_caja_normal(c) -> rx.Component:
    return glass_card(
        rx.hstack(
            rx.box(width="4px", height="56px", border_radius="4px", background=c.color),
            rx.vstack(
                rx.hstack(
                    rx.text(c.nombre, size="3", color=T.TEXT, weight="bold"),
                    rx.cond(
                        c.exento_4x1000,
                        rx.box(
                            rx.text("Exento 4×1000", size="1", color=T.GREEN, weight="medium"),
                            padding="2px 8px", border_radius="999px",
                            background=f"{T.GREEN}22",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2", align="center",
                ),
                rx.hstack(
                    rx.text(c.tipo_label, size="1", color=T.TEXT_MUTED),
                    rx.cond(
                        c.entidad != "",
                        rx.hstack(
                            rx.text("·", size="1", color=T.TEXT_DIM),
                            rx.text(c.entidad, size="1", color=T.TEXT_DIM),
                            spacing="1",
                        ),
                        rx.fragment(),
                    ),
                    spacing="1",
                ),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.vstack(
                rx.text(c.saldo_actual_fmt, size="4", color=T.TEXT,
                        weight="bold", font_family=T.FONT_HEAD),
                rx.cond(
                    c.saldo_actual < 0,
                    rx.text("Saldo proyectado", size="1", color=T.RED),
                    rx.text("Saldo proyectado", size="1", color=T.TEXT_DIM),
                ),
                rx.cond(
                    c.faltante_cero > 0,
                    rx.text("Faltante a 0: " + c.faltante_cero_fmt,
                            size="1", color=T.RED, weight="medium"),
                    rx.fragment(),
                ),
                rx.text("Gasto del período: " + c.gasto_periodo_fmt,
                        size="1", color=T.TEXT_DIM),
                spacing="0", align="end",
            ),
            rx.hstack(
                rx.cond(
                    c.faltante_cero > 0,
                    rx.hstack(
                        rx.button(
                            rx.icon("zap", size=14),
                            rx.text("Auto traspaso", size="1", weight="medium"),
                            on_click=CajasState.auto_transferir_cobertura(c.id),
                            variant="ghost", cursor="pointer", size="1",
                            color=T.AMBER,
                            _hover={"background": f"{T.AMBER}18"},
                            title="Transfiere automáticamente usando fecha del ingreso",
                        ),
                        rx.button(
                            rx.icon("file-pen-line", size=14),
                            rx.text("Preparar", size="1", weight="medium"),
                            on_click=CajasState.sugerir_cobertura(c.id),
                            variant="ghost", cursor="pointer", size="1",
                            color=T.TEXT_MUTED,
                            title="Abre formulario prellenado para revisar antes de guardar",
                        ),
                        spacing="1",
                    ),
                    rx.fragment(),
                ),
                rx.button(
                    rx.icon("pencil", size=14),
                    on_click=CajasState.editar(c.id),
                    variant="ghost", cursor="pointer", size="1",
                    color=T.TEXT_MUTED,
                ),
                rx.button(
                    rx.icon("trash-2", size=14),
                    on_click=CajasState.eliminar(c.id),
                    variant="ghost", cursor="pointer", size="1",
                    color=T.RED,
                ),
                spacing="1",
            ),
            spacing="3", width="100%", align="center",
        ),
        padding="14px 18px",
    )


def _form_caja() -> rx.Component:
    return rx.cond(
        CajasState.form_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(CajasState.form_editing_id, "Editar caja", "Nueva caja"),
                        size="5", font_family=T.FONT_HEAD,
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=16),
                        on_click=CajasState.toggle_form,
                        variant="ghost", cursor="pointer", color=T.TEXT_MUTED,
                    ),
                    width="100%",
                ),
                rx.grid(
                    text_field("Nombre", CajasState.form_nombre,
                               CajasState.set_form_nombre,
                               placeholder="Ej: Cuenta ahorro Bancolombia"),
                    select_field("Tipo", CajasState.form_tipo,
                                 CajasState.set_form_tipo, TIPOS_CAJA),
                    columns="2", spacing="3", width="100%",
                ),
                rx.grid(
                    text_field("Entidad", CajasState.form_entidad,
                               CajasState.set_form_entidad,
                               placeholder="Bancolombia / Nequi / Lulo..."),
                    number_field("Saldo inicial (COP)", CajasState.form_saldo_inicial,
                                 CajasState.set_form_saldo_inicial, step=10000),
                    columns="2", spacing="3", width="100%",
                ),
                rx.cond(
                    CajasState.form_tipo == "tarjeta_credito",
                    rx.vstack(
                        rx.text(
                            "💳 Tarjeta de crédito: el saldo inicial se ignora ($0). "
                            "La deuda se construye con cada gasto a crédito; pagos = transferencia a la TC.",
                            size="1", color=T.TEXT_DIM,
                        ),
                        rx.grid(
                            number_field("Cupo total (COP)", CajasState.form_cupo_total_cop,
                                         CajasState.set_form_cupo_total_cop, step=100000),
                            number_field("Cuota de manejo mensual (COP)",
                                         CajasState.form_cuota_manejo,
                                         CajasState.set_form_cuota_manejo, step=1000),
                            number_field("TRM propio del banco (COP/USD)",
                                         CajasState.form_trm_tc,
                                         CajasState.set_form_trm_tc, step=1),
                            columns="3", spacing="3", width="100%",
                        ),
                        rx.grid(
                            number_field("Interés mensual compras (%)",
                                         CajasState.form_interes_mensual_compras,
                                         CajasState.set_form_interes_mensual_compras, step=0.1),
                            number_field("Interés EA compras (%)",
                                         CajasState.form_interes_ea_compras,
                                         CajasState.set_form_interes_ea_compras, step=0.1),
                            number_field("Interés mensual avances (%)",
                                         CajasState.form_interes_mensual_avances,
                                         CajasState.set_form_interes_mensual_avances, step=0.1),
                            number_field("Interés EA avances (%)",
                                         CajasState.form_interes_ea_avances,
                                         CajasState.set_form_interes_ea_avances, step=0.1),
                            columns="2", spacing="3", width="100%",
                        ),
                        rx.grid(
                            number_field("Día cobro cuota manejo",
                                         CajasState.form_dia_cobro_cuota,
                                         CajasState.set_form_dia_cobro_cuota, step=1),
                            number_field("Día de corte",
                                         CajasState.form_dia_corte,
                                         CajasState.set_form_dia_corte, step=1),
                            number_field("Día límite de pago",
                                         CajasState.form_dia_pago,
                                         CajasState.set_form_dia_pago, step=1),
                            columns="3", spacing="3", width="100%",
                        ),
                        rx.hstack(
                            rx.checkbox(
                                "Usa 2 fechas de corte",
                                checked=CajasState.form_usa_dos_cortes,
                                on_change=CajasState.set_form_usa_dos_cortes,
                            ),
                            spacing="2",
                        ),
                        rx.cond(
                            CajasState.form_usa_dos_cortes,
                            number_field("Segunda fecha de corte",
                                         CajasState.form_dia_corte_2,
                                         CajasState.set_form_dia_corte_2, step=1),
                            rx.fragment(),
                        ),
                        spacing="3", width="100%", align="stretch",
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.checkbox(
                        "Exenta del 4×1000",
                        checked=CajasState.form_exento_4x1000,
                        on_change=CajasState.set_form_exento_4x1000,
                    ),
                    spacing="2",
                ),
                text_field("Notas (opcional)", CajasState.form_notas,
                           CajasState.set_form_notas),
                rx.hstack(
                    primary_button("Guardar", CajasState.guardar, icon="save", flex="1"),
                    ghost_button("Cancelar", CajasState.toggle_form),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    CajasState.form_msg != "",
                    rx.text(CajasState.form_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="3", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def _form_movimiento() -> rx.Component:
    return rx.cond(
        CajasState.mov_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Nueva transferencia", size="5", font_family=T.FONT_HEAD),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=16),
                        on_click=CajasState.toggle_mov,
                        variant="ghost", cursor="pointer", color=T.TEXT_MUTED,
                    ),
                    width="100%",
                ),
                rx.grid(
                    date_field("Fecha", CajasState.mov_fecha, CajasState.set_mov_fecha),
                    number_field("Monto (COP)", CajasState.mov_monto,
                                 CajasState.set_mov_monto, step=10000),
                    columns="2", spacing="3", width="100%",
                ),
                rx.grid(
                    rx.vstack(
                        field_label("Desde"),
                        rx.select.root(
                            rx.select.trigger(
                                placeholder="Caja origen",
                                background="rgba(255,255,255,0.04)",
                                border=f"1px solid {T.BORDER}",
                                border_radius=T.RADIUS_SM,
                                width="100%", height="40px",
                            ),
                            rx.select.content(
                                rx.foreach(
                                    CajasState.rows,
                                    lambda c: rx.select.item(c.nombre, value=c.id.to_string()),
                                ),
                            ),
                            value=CajasState.mov_origen_id.to_string(),
                            on_change=CajasState.set_mov_origen_id,
                            width="100%",
                        ),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        field_label("Hacia"),
                        rx.select.root(
                            rx.select.trigger(
                                placeholder="Caja destino",
                                background="rgba(255,255,255,0.04)",
                                border=f"1px solid {T.BORDER}",
                                border_radius=T.RADIUS_SM,
                                width="100%", height="40px",
                            ),
                            rx.select.content(
                                rx.foreach(
                                    CajasState.rows,
                                    lambda c: rx.select.item(c.nombre, value=c.id.to_string()),
                                ),
                            ),
                            value=CajasState.mov_destino_id.to_string(),
                            on_change=CajasState.set_mov_destino_id,
                            width="100%",
                        ),
                        spacing="1", width="100%",
                    ),
                    columns="2", spacing="3", width="100%",
                ),
                text_field("Descripción (opcional)", CajasState.mov_desc,
                           CajasState.set_mov_desc),
                rx.text("💡 El 4×1000 se calcula automáticamente si la caja origen no está exenta.",
                        size="1", color=T.TEXT_DIM),
                rx.hstack(
                    primary_button("Guardar transferencia", CajasState.guardar_movimiento,
                                   icon="arrow-right", flex="1"),
                    ghost_button("Cancelar", CajasState.toggle_mov),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    CajasState.mov_msg != "",
                    rx.text(CajasState.mov_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="3", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def _form_cargar_deuda() -> rx.Component:
    return rx.cond(
        CajasState.deuda_open,
        glass_card(
            rx.vstack(
                rx.hstack(
                    rx.icon("credit-card", size=18, color=T.PINK),
                    rx.heading(
                        "Cargar deuda · " + CajasState.deuda_caja_nombre,
                        size="5", font_family=T.FONT_HEAD,
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=16),
                        on_click=CajasState.cerrar_cargar_deuda,
                        variant="ghost", cursor="pointer", color=T.TEXT_MUTED,
                    ),
                    spacing="2", align="center", width="100%",
                ),
                rx.text(
                    "Carga directa de un cargo a la TC. El monto se registra tal cual "
                    "(sin recálculo de intereses), porque el banco ya los aplicó al cobrarte.",
                    size="1", color=T.TEXT_DIM,
                ),
                rx.grid(
                    text_field("Descripción", CajasState.deuda_desc,
                               CajasState.set_deuda_desc,
                               placeholder="Ej: Saldo actual, Compras pendientes, Avance..."),
                    select_field("Moneda", CajasState.deuda_moneda,
                                 CajasState.set_deuda_moneda, ["COP", "USD"]),
                    columns="2", spacing="3", width="100%",
                ),
                rx.cond(
                    CajasState.deuda_moneda == "USD",
                    number_field("Monto (USD)", CajasState.deuda_monto_usd,
                                 CajasState.set_deuda_monto_usd, step=1),
                    number_field("Monto (COP)", CajasState.deuda_monto_cop,
                                 CajasState.set_deuda_monto_cop, step=10000),
                ),
                rx.cond(
                    CajasState.deuda_moneda == "USD",
                    rx.text(
                        "TRM propio del banco aplicado: $"
                        + CajasState.deuda_trm_tc_actual.to_string()
                        + " (configúralo en la caja si está en 0).",
                        size="1", color=T.TEXT_DIM,
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    primary_button("Cargar deuda", CajasState.guardar_deuda,
                                   icon="plus", flex="1"),
                    ghost_button("Cancelar", CajasState.cerrar_cargar_deuda),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    CajasState.deuda_msg != "",
                    rx.text(CajasState.deuda_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="3", width="100%", align="stretch",
            ),
        ),
        rx.fragment(),
    )


def _row_movimiento(m) -> rx.Component:
    return rx.hstack(
        rx.icon("arrow-right", size=14, color=T.TEXT_MUTED),
        rx.vstack(
            rx.hstack(
                rx.text(m.origen, size="2", color=T.TEXT, weight="medium"),
                rx.icon("chevron-right", size=12, color=T.TEXT_DIM),
                rx.text(m.destino, size="2", color=T.TEXT, weight="medium"),
                spacing="1",
            ),
            rx.hstack(
                rx.text(m.fecha, size="1", color=T.TEXT_DIM),
                rx.cond(
                    m.descripcion != "",
                    rx.hstack(
                        rx.text("·", size="1", color=T.TEXT_DIM),
                        rx.text(m.descripcion, size="1", color=T.TEXT_DIM),
                        spacing="1",
                    ),
                    rx.fragment(),
                ),
                spacing="1",
            ),
            spacing="0", align="start",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(m.monto_fmt, size="3", color=T.TEXT,
                    weight="bold", font_family=T.FONT_HEAD),
            rx.cond(
                m.costo_4x1000 > 0,
                rx.text("4×1000: " + m.costo_fmt, size="1", color=T.RED),
                rx.fragment(),
            ),
            spacing="0", align="end",
        ),
        rx.button(
            rx.icon("trash-2", size=14),
            on_click=CajasState.eliminar_movimiento(m.id),
            variant="ghost", cursor="pointer", size="1", color=T.RED,
        ),
        spacing="3", width="100%", align="center",
        padding="10px 14px",
        border_bottom=f"1px solid {T.BORDER_SOFT}",
    )


def cajas_page() -> rx.Component:
    return main_layout(
        rx.hstack(
            page_title("Cajas", "Cuentas, tarjetas y dinero disponible."),
            rx.spacer(),
            rx.hstack(
                ghost_button("Transferir", CajasState.toggle_mov, icon="arrow-right"),
                primary_button(
                    rx.cond(CajasState.form_open, "Cerrar", "Nueva caja"),
                    CajasState.toggle_form,
                    icon=rx.cond(CajasState.form_open, "x", "plus"),
                ),
                spacing="2",
            ),
            width="100%", align="center",
        ),

        rx.box(height="16px"),
        _metric_total(),
        rx.cond(
            CajasState.rows.length() > 0,
            glass_card(
                rx.vstack(
                    field_label("Caja origen preferida para Auto traspaso"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecciona caja preferida",
                            background="rgba(255,255,255,0.04)",
                            border=f"1px solid {T.BORDER}",
                            border_radius=T.RADIUS_SM,
                            width="100%", height="40px",
                        ),
                        rx.select.content(
                            rx.foreach(
                                CajasState.rows,
                                lambda c: rx.select.item(c.nombre, value=c.id.to_string()),
                            ),
                        ),
                        value=CajasState.auto_origen_preferido_id.to_string(),
                        on_change=CajasState.set_auto_origen_preferido_id,
                        width="100%",
                    ),
                    rx.text("Si tiene saldo positivo, se prioriza como origen en Auto traspaso.",
                            size="1", color=T.TEXT_DIM),
                    spacing="1", width="100%", align="stretch",
                ),
                padding="12px 16px",
            ),
            rx.fragment(),
        ),
        rx.box(height="16px"),
        _form_caja(),
        _form_movimiento(),
        _form_cargar_deuda(),
        rx.box(height="12px"),

        # Grid de cajas
        rx.cond(
            CajasState.rows.length() > 0,
            rx.vstack(
                rx.foreach(CajasState.rows, _row_caja),
                spacing="2", width="100%", align="stretch",
            ),
            glass_card(
                rx.vstack(
                    rx.icon("wallet", size=40, color=T.TEXT_DIM),
                    rx.text("Aún no has creado ninguna caja.",
                            size="3", color=T.TEXT_MUTED),
                    rx.text("Crea tu primera cuenta, tarjeta o bolsa de efectivo.",
                            size="2", color=T.TEXT_DIM),
                    spacing="2", align="center", padding="40px",
                ),
            ),
        ),

        rx.box(height="32px"),

        # Historial de movimientos
        rx.cond(
            CajasState.movimientos.length() > 0,
            rx.vstack(
                rx.heading("Últimas transferencias", size="5", font_family=T.FONT_HEAD),
                glass_card(
                    rx.vstack(
                        rx.foreach(CajasState.movimientos, _row_movimiento),
                        spacing="0", width="100%", align="stretch",
                    ),
                    padding="0",
                ),
                spacing="3", width="100%", align="stretch",
            ),
            rx.fragment(),
        ),
    )
