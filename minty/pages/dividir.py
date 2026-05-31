"""Página /dividir — calcular y registrar cuentas compartidas."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    number_field, text_field, date_field,
    primary_button, ghost_button, field_label,
)
from minty.state.dividir import DividirState


# ── Sección Cabecera ─────────────────────────────────────────
def _header_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("receipt", size=18, color=T.VIOLET),
                rx.heading("Cuenta compartida", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                spacing="2", align="center",
            ),
            rx.grid(
                text_field("Nombre", DividirState.nombre,
                           DividirState.set_nombre,
                           placeholder="Ej: Cena Andrés Carne de Res"),
                date_field("Fecha", DividirState.fecha,
                           DividirState.set_fecha),
                columns="2", spacing="3", width="100%",
            ),
            text_field("Notas", DividirState.notas,
                       DividirState.set_notas,
                       placeholder="(opcional)"),
            rx.cond(
                DividirState.msg != "",
                rx.text(DividirState.msg, size="2", color=T.AMBER),
                rx.fragment(),
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


# ── Participantes ───────────────────────────────────────────
def _chip_participante(p) -> rx.Component:
    es_yo = p.es_yo
    return rx.hstack(
        rx.box(
            rx.text(p.emoji, font_size="14px"),
            width="22px", height="22px",
            border_radius="50%",
            background=p.color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.button(
            rx.cond(
                es_yo,
                rx.icon("circle-dot", size=14, color=T.VIOLET),
                rx.icon("circle", size=14, color=T.TEXT_DIM),
            ),
            on_click=DividirState.set_yo(p.idx),
            background="transparent", padding="0",
            cursor="pointer", title="Marcar como 'Yo'",
        ),
        rx.text(p.nombre, size="2", color=T.TEXT, weight="medium"),
        rx.text(p.paga_fmt, size="2",
                color=rx.cond(es_yo, T.VIOLET, T.TEXT_MUTED),
                font_family=T.FONT_MONO),
        rx.icon_button(
            rx.icon("x", size=12),
            on_click=DividirState.remove_participante(p.idx),
            variant="ghost", color_scheme="red", size="1",
        ),
        spacing="2", align="center",
        padding="6px 10px",
        border=rx.cond(es_yo,
                       f"1px solid {T.VIOLET}",
                       f"1px solid {T.BORDER}"),
        border_radius="999px",
        background=rx.cond(es_yo,
                           "rgba(167,139,250,0.08)",
                           "rgba(255,255,255,0.03)"),
    )


def _persona_pick_chip(p) -> rx.Component:
    return rx.button(
        rx.hstack(
            rx.box(
                rx.text(p.emoji, font_size="14px"),
                width="22px", height="22px",
                border_radius="50%",
                background=p.color,
                display="flex", align_items="center", justify_content="center",
            ),
            rx.text(p.nombre, size="2", color=T.TEXT),
            rx.cond(
                p.ya_agregada,
                rx.icon("check", size=12, color=T.GREEN),
                rx.icon("plus", size=12, color=T.TEXT_MUTED),
            ),
            spacing="2", align="center",
        ),
        on_click=DividirState.agregar_persona(p.id),
        disabled=p.ya_agregada,
        background=rx.cond(p.ya_agregada,
                           "rgba(74,222,128,0.08)",
                           "rgba(255,255,255,0.03)"),
        border=f"1px solid {T.BORDER}",
        border_radius="999px",
        padding="6px 10px",
        cursor=rx.cond(p.ya_agregada, "default", "pointer"),
        opacity=rx.cond(p.ya_agregada, "0.6", "1"),
    )


def _participantes_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("users", size=18, color=T.VIOLET),
                rx.heading("Participantes", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                rx.spacer(),
                rx.link(
                    rx.hstack(
                        rx.icon("contact", size=14),
                        rx.text("Gestionar personas", size="1"),
                        spacing="1", align="center",
                    ),
                    href="/personas",
                    color=T.TEXT_MUTED,
                ),
                spacing="2", align="center", width="100%",
            ),
            rx.text(
                "Marca con ● cuál de ellos eres tú. Añade personas desde tu "
                "libreta o escribe un nombre puntual.",
                size="2", color=T.TEXT_MUTED,
            ),
            rx.flex(
                rx.foreach(DividirState.por_persona, _chip_participante),
                wrap="wrap", gap="8px",
            ),
            rx.cond(
                DividirState.personas_disponibles.length() > 0,
                rx.vstack(
                    rx.text("De tu libreta:", size="1", color=T.TEXT_DIM),
                    rx.flex(
                        rx.foreach(DividirState.personas_disponibles,
                                   _persona_pick_chip),
                        wrap="wrap", gap="6px",
                    ),
                    spacing="1", align="stretch", width="100%",
                ),
                rx.fragment(),
            ),
            rx.hstack(
                rx.input(
                    value=DividirState.nuevo_participante,
                    on_change=DividirState.set_nuevo_participante,
                    placeholder="Nombre puntual (no se guarda en la libreta)…",
                    background="rgba(255,255,255,0.04)",
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_SM,
                    color=T.TEXT, padding="10px 12px",
                    height="40px", flex="1",
                ),
                primary_button("Agregar", DividirState.add_participante,
                               icon="user-plus"),
                spacing="2", align="center", width="100%",
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


# ── Items ───────────────────────────────────────────────────
def _checkbox_participante(item_idx, incluidos, part) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=incluidos.contains(part.idx),
            on_change=lambda _v: DividirState.toggle_incluido(
                item_idx, part.idx),
            color_scheme="violet",
        ),
        rx.text(part.nombre, size="2", color=T.TEXT_MUTED),
        spacing="1", align="center",
    )


def _item_row(item_with_idx) -> rx.Component:
    # item_with_idx es un tuple (idx, item_dict) tras enumerate via rx
    # Reflex no soporta enumerate; usamos índice por foreach con var
    pass  # placeholder — usamos otra estrategia


def _item_card(idx_item, item) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.input(
                    value=item.nombre,
                    on_change=lambda v: DividirState.set_item_nombre(idx_item, v),
                    placeholder="Concepto",
                    background="rgba(255,255,255,0.04)",
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_SM,
                    color=T.TEXT, padding="8px 10px",
                    height="36px", flex="2",
                ),
                rx.input(
                    value=item.monto_str,
                    on_change=lambda v: DividirState.set_item_monto(idx_item, v),
                    placeholder="0",
                    type="number", step=100,
                    background="rgba(255,255,255,0.04)",
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_SM,
                    color=rx.cond(item.monto < 0, T.RED, T.TEXT),
                    padding="8px 10px",
                    height="36px", width="140px",
                    text_align="right",
                    font_family=T.FONT_MONO,
                ),
                rx.icon_button(
                    rx.icon("trash-2", size=14),
                    on_click=DividirState.remove_item(idx_item),
                    variant="ghost", color_scheme="red", size="1",
                ),
                spacing="2", align="center", width="100%",
            ),
            rx.text("Pagan:", size="1", color=T.TEXT_DIM),
            rx.flex(
                rx.foreach(
                    DividirState.por_persona,
                    lambda part: _checkbox_participante(
                        idx_item, item.incluidos, part),
                ),
                wrap="wrap", gap="12px",
            ),
            spacing="2", align="stretch", width="100%",
        ),
        padding="12px",
        border=f"1px solid {T.BORDER_SOFT}",
        border_radius=T.RADIUS_SM,
        background="rgba(255,255,255,0.02)",
        width="100%",
    )


def _items_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("list", size=18, color=T.VIOLET),
                rx.heading("Ítems de la cuenta", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                rx.spacer(),
                rx.text("Total: ", size="2", color=T.TEXT_MUTED),
                rx.heading(DividirState.total_fmt, size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                spacing="2", align="center", width="100%",
            ),
            rx.text(
                "Agrega cada producto/servicio con su monto. Marca quiénes "
                "pagan ese ítem y se dividirá en partes iguales entre ellos. "
                "Usa montos negativos (o el botón “Descuento”) para "
                "descuentos, bonos o créditos que resten al total.",
                size="2", color=T.TEXT_MUTED,
            ),
            rx.cond(
                DividirState.hay_items,
                rx.vstack(
                    rx.foreach(
                        DividirState.items,
                        lambda it, i: _item_card(i, it),
                    ),
                    spacing="2", align="stretch", width="100%",
                ),
                rx.fragment(),
            ),
            rx.hstack(
                rx.input(
                    value=DividirState.nuevo_item_nombre,
                    on_change=DividirState.set_nuevo_item_nombre,
                    placeholder="Concepto del ítem (ej: Pizza, Postre, Propina)",
                    background="rgba(255,255,255,0.04)",
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_SM,
                    color=T.TEXT, padding="10px 12px",
                    height="40px", flex="2",
                ),
                rx.input(
                    value=DividirState.nuevo_item_monto.to_string(),
                    on_change=DividirState.set_nuevo_item_monto,
                    placeholder="Monto",
                    type="number", step=100,
                    background="rgba(255,255,255,0.04)",
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_SM,
                    color=T.TEXT, padding="10px 12px",
                    height="40px", width="160px",
                    text_align="right", font_family=T.FONT_MONO,
                ),
                primary_button("Agregar cargo", DividirState.add_item,
                               icon="plus"),
                ghost_button("Agregar descuento", DividirState.add_descuento,
                             icon="minus"),
                spacing="2", align="center", width="100%",
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


# ── Resultado ───────────────────────────────────────────────
def _result_row(p) -> rx.Component:
    es_yo = p.es_yo
    return rx.hstack(
        rx.box(
            rx.text(p.emoji, font_size="14px"),
            width="22px", height="22px",
            border_radius="50%",
            background=p.color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.text(p.nombre, size="3",
                color=rx.cond(es_yo, T.TEXT, T.TEXT_MUTED),
                weight=rx.cond(es_yo, "bold", "regular")),
        rx.spacer(),
        rx.heading(p.paga_fmt, size="4",
                   font_family=T.FONT_HEAD,
                   color=rx.cond(es_yo, T.VIOLET, T.TEXT)),
        spacing="2", align="center", width="100%",
        padding="8px 12px",
        border_bottom=f"1px solid {T.BORDER_SOFT}",
    )


# ── Pagos ───────────────────────────────────────────────────
def _pagador_chip(p) -> rx.Component:
    return rx.button(
        rx.hstack(
            rx.box(
                rx.text(p.emoji, font_size="14px"),
                width="22px", height="22px",
                border_radius="50%",
                background=p.color,
                display="flex", align_items="center",
                justify_content="center",
            ),
            rx.text(p.nombre, size="2",
                    color=rx.cond(p.seleccionado, "white", T.TEXT)),
            rx.cond(
                p.seleccionado,
                rx.icon("check", size=12, color="white"),
                rx.fragment(),
            ),
            spacing="2", align="center",
        ),
        on_click=DividirState.set_pagador(p.idx),
        background=rx.cond(p.seleccionado,
                           T.GRADIENT_BRAND,
                           "rgba(255,255,255,0.03)"),
        border=rx.cond(p.seleccionado,
                       f"1px solid {T.VIOLET}",
                       f"1px solid {T.BORDER}"),
        border_radius="999px",
        padding="6px 12px",
        cursor="pointer",
    )


def _pago_row(p) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.text(p.emoji, font_size="14px"),
            width="24px", height="24px",
            border_radius="50%",
            background=p.color,
            display="flex", align_items="center", justify_content="center",
            flex_shrink="0",
        ),
        rx.text(p.nombre, size="2", color=T.TEXT, weight="medium",
                width="120px"),
        rx.input(
            value=p.pagado_str,
            on_change=lambda v: DividirState.set_pago(p.idx, v),
            placeholder="0",
            type="number",
            background="rgba(255,255,255,0.04)",
            border=f"1px solid {T.BORDER}",
            border_radius=T.RADIUS_SM,
            color=T.TEXT, padding="8px 12px",
            height="36px", flex="1",
            font_family=T.FONT_MONO,
            text_align="right",
        ),
        spacing="2", align="center", width="100%",
    )


def _pagos_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("hand-coins", size=18, color=T.VIOLET),
                rx.heading("¿Quién pagó?", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                spacing="2", align="center",
            ),
            rx.text(
                "Indica cuánto pagó cada persona en realidad. Sirve para "
                "calcular quién le debe a quién.",
                size="2", color=T.TEXT_MUTED,
            ),
            rx.vstack(
                rx.text("¿Quién hizo el pago de la cuenta?", size="1",
                        color=T.TEXT_DIM),
                rx.flex(
                    rx.foreach(DividirState.pagadores, _pagador_chip),
                    wrap="wrap", gap="6px",
                ),
                rx.cond(
                    DividirState.hay_pagador,
                    rx.text(
                        DividirState.pagador_nombre +
                        " hizo el pago. Es solo etiqueta — abajo pones lo "
                        "que cada uno aportó.",
                        size="1", color=T.VIOLET,
                    ),
                    rx.text(
                        "Sin pagador definido (opcional).",
                        size="1", color=T.TEXT_DIM,
                    ),
                ),
                spacing="1", align="stretch", width="100%",
            ),
            rx.divider(color_scheme="gray"),
            rx.vstack(
                rx.foreach(DividirState.por_persona, _pago_row),
                spacing="2", align="stretch", width="100%",
            ),
            rx.hstack(
                primary_button("Yo pagué todo",
                               DividirState.yo_pago_todo,
                               icon="user-check"),
                ghost_button("Limpiar pagos",
                             DividirState.limpiar_pagos, icon="eraser"),
                spacing="2", align="center",
            ),
            rx.divider(color_scheme="gray"),
            rx.hstack(
                rx.text("Pagado:", size="2", color=T.TEXT_MUTED),
                rx.text(DividirState.total_pagado_fmt, size="2",
                        color=T.TEXT, font_family=T.FONT_MONO,
                        weight="bold"),
                rx.text("/", size="2", color=T.TEXT_DIM),
                rx.text(DividirState.total_fmt, size="2",
                        color=T.TEXT_MUTED, font_family=T.FONT_MONO),
                rx.spacer(),
                rx.cond(
                    DividirState.pagos_balanceados,
                    rx.hstack(
                        rx.icon("circle-check", size=14, color=T.GREEN),
                        rx.text("Cuadra", size="2", color=T.GREEN),
                        spacing="1", align="center",
                    ),
                    rx.hstack(
                        rx.icon("triangle-alert", size=14, color=T.AMBER),
                        rx.text("Falta " + DividirState.diferencia_pagos_fmt,
                                size="2", color=T.AMBER,
                                font_family=T.FONT_MONO),
                        spacing="1", align="center",
                    ),
                ),
                spacing="2", align="center", width="100%",
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


# ── Saldos y transferencias ─────────────────────────────────
def _saldo_row(p) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.text(p.emoji, font_size="14px"),
            width="24px", height="24px",
            border_radius="50%",
            background=p.color,
            display="flex", align_items="center", justify_content="center",
            flex_shrink="0",
        ),
        rx.text(p.nombre, size="2", color=T.TEXT, weight="medium"),
        rx.spacer(),
        rx.text(p.balance_fmt, size="2", font_family=T.FONT_MONO,
                color=rx.match(
                    p.balance_signo,
                    ("debe", T.RED),
                    ("recibe", T.GREEN),
                    T.TEXT_DIM,
                )),
        rx.match(
            p.balance_signo,
            ("debe", rx.badge("Debe", color_scheme="red", variant="soft")),
            ("recibe", rx.badge("Recibe", color_scheme="green",
                                variant="soft")),
            rx.badge("Saldado", color_scheme="gray", variant="soft"),
        ),
        spacing="2", align="center", width="100%",
        padding="8px 12px",
        border_bottom=f"1px solid {T.BORDER_SOFT}",
    )


def _transfer_row(t) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.text(t.de_emoji, font_size="14px"),
            width="22px", height="22px",
            border_radius="50%",
            background=t.de_color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.text(t.de_nombre, size="2", color=T.TEXT),
        rx.icon("arrow-right", size=14, color=T.TEXT_DIM),
        rx.text(t.monto_fmt, size="2", color=T.VIOLET,
                font_family=T.FONT_MONO, weight="bold"),
        rx.icon("arrow-right", size=14, color=T.TEXT_DIM),
        rx.box(
            rx.text(t.a_emoji, font_size="14px"),
            width="22px", height="22px",
            border_radius="50%",
            background=t.a_color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.text(t.a_nombre, size="2", color=T.TEXT),
        spacing="2", align="center",
        padding="8px 12px",
        background="rgba(255,255,255,0.03)",
        border=f"1px solid {T.BORDER_SOFT}",
        border_radius=T.RADIUS_SM,
    )


def _saldos_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("scale", size=18, color=T.VIOLET),
                rx.heading("Saldos", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                spacing="2", align="center",
            ),
            rx.text(
                "Diferencia entre lo que debería pagar cada persona y lo "
                "que realmente pagó.",
                size="2", color=T.TEXT_MUTED,
            ),
            rx.vstack(
                rx.foreach(DividirState.por_persona, _saldo_row),
                spacing="0", align="stretch", width="100%",
            ),
            rx.divider(color_scheme="gray"),
            rx.hstack(
                rx.icon("arrow-right-left", size=16, color=T.VIOLET),
                rx.heading("Transferencias sugeridas", size="3",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                spacing="2", align="center",
            ),
            rx.cond(
                DividirState.hay_transferencias,
                rx.vstack(
                    rx.foreach(DividirState.transferencias, _transfer_row),
                    spacing="2", align="stretch", width="100%",
                ),
                rx.hstack(
                    rx.icon("circle-check", size=16, color=T.GREEN),
                    rx.text("Cuentas saldadas — nadie debe nada.",
                            size="2", color=T.GREEN),
                    spacing="2", align="center", padding="8px",
                ),
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


def _result_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("calculator", size=18, color=T.VIOLET),
                rx.heading("Resultado", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                spacing="2", align="center",
            ),
            rx.grid(
                rx.box(
                    rx.vstack(
                        rx.text("Total de la cuenta", size="2",
                                color=T.TEXT_MUTED),
                        rx.heading(DividirState.total_fmt, size="7",
                                   font_family=T.FONT_HEAD, color=T.TEXT),
                        spacing="0", align="start",
                    ),
                    padding="16px",
                    background="rgba(255,255,255,0.03)",
                    border=f"1px solid {T.BORDER_SOFT}",
                    border_radius=T.RADIUS_SM,
                ),
                rx.box(
                    rx.vstack(
                        rx.text("Tu parte", size="2", color=T.TEXT_MUTED),
                        rx.heading(DividirState.mi_parte_fmt, size="7",
                                   font_family=T.FONT_HEAD, color=T.VIOLET),
                        spacing="0", align="start",
                    ),
                    padding="16px",
                    background="rgba(167,139,250,0.08)",
                    border=f"1px solid {T.VIOLET}",
                    border_radius=T.RADIUS_SM,
                ),
                columns="2", spacing="3", width="100%",
            ),
            rx.vstack(
                rx.foreach(DividirState.por_persona, _result_row),
                spacing="0", align="stretch", width="100%",
            ),
            rx.hstack(
                primary_button("Registrar mi parte como gasto",
                               DividirState.abrir_registro,
                               icon="wallet"),
                ghost_button("Guardar factura",
                             DividirState.guardar_factura, icon="save"),
                ghost_button("Nueva cuenta", DividirState.nueva_factura, icon="plus"),
                spacing="2", justify="end", width="100%",
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


# ── Modal registrar mi parte ────────────────────────────────
def _registro_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Registrar mi parte como gasto"),
            rx.dialog.description(
                "Crea un Gasto por tu parte (",
                rx.text(DividirState.mi_parte_fmt, as_="span",
                        weight="bold", color=T.VIOLET),
                ") en la caja que elijas.",
            ),
            rx.vstack(
                rx.vstack(
                    field_label("Caja"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecciona caja…",
                            background="rgba(255,255,255,0.04)",
                            border=f"1px solid {T.BORDER}",
                            border_radius=T.RADIUS_SM,
                            width="100%", height="40px",
                        ),
                        rx.select.content(
                            rx.foreach(
                                DividirState.cajas_opts,
                                lambda opt: rx.select.item(
                                    opt["etiqueta"],
                                    value=opt["id"].to_string(),
                                ),
                            ),
                        ),
                        value=DividirState.reg_caja_id.to_string(),
                        on_change=DividirState.set_reg_caja,
                        width="100%",
                    ),
                    spacing="1", align="stretch", width="100%",
                ),
                text_field("Categoría", DividirState.reg_categoria,
                           DividirState.set_reg_categoria,
                           placeholder="Comida fuera, Compras, Domicilios…"),
                text_field("Descripción", DividirState.reg_descripcion,
                           DividirState.set_reg_descripcion),
                rx.cond(
                    DividirState.reg_msg != "",
                    rx.text(DividirState.reg_msg, size="2", color=T.AMBER),
                    rx.fragment(),
                ),
                spacing="3", align="stretch", width="100%",
                margin_top="12px",
            ),
            rx.hstack(
                rx.spacer(),
                ghost_button("Cancelar", DividirState.cerrar_registro,
                             icon="x"),
                primary_button("Registrar gasto",
                               DividirState.registrar_mi_parte, icon="check"),
                spacing="2", margin_top="16px", width="100%",
            ),
            max_width="500px",
        ),
        open=DividirState.reg_open,
    )


# ── Historial ───────────────────────────────────────────────
def _hist_row(h) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon("receipt", size=16, color="white"),
            background=T.GRADIENT_BRAND_SOFT,
            border_radius="8px", padding="8px",
        ),
        rx.vstack(
            rx.text(h.nombre, size="3", color=T.TEXT, weight="medium"),
            rx.hstack(
                rx.text(h.fecha, size="1", color=T.TEXT_DIM,
                        font_family=T.FONT_MONO),
                rx.cond(
                    h.n_participantes > 0,
                    rx.hstack(
                        rx.icon("users", size=12, color=T.TEXT_DIM),
                        rx.text(h.n_participantes.to_string(), size="1",
                                color=T.TEXT_DIM),
                        spacing="1", align="center",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    h.pagador_nombre != "",
                    rx.hstack(
                        rx.icon("hand-coins", size=12, color=T.AMBER),
                        rx.text("Pagó " + h.pagador_nombre, size="1",
                                color=T.AMBER),
                        spacing="1", align="center",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    h.tiene_gasto,
                    rx.hstack(
                        rx.icon("check", size=12, color=T.GREEN),
                        rx.text("Mi parte registrada", size="1",
                                color=T.GREEN),
                        spacing="1", align="center",
                    ),
                    rx.fragment(),
                ),
                spacing="2", align="center", wrap="wrap",
            ),
            spacing="0", align="start", flex="1",
        ),
        rx.vstack(
            rx.text("Total", size="1", color=T.TEXT_DIM),
            rx.text(h.total_fmt, size="2", color=T.TEXT,
                    font_family=T.FONT_MONO),
            spacing="0", align="end",
        ),
        rx.vstack(
            rx.text("Tu parte", size="1", color=T.TEXT_DIM),
            rx.text(h.mi_parte_fmt, size="2", color=T.VIOLET,
                    font_family=T.FONT_MONO, weight="bold"),
            spacing="0", align="end",
        ),
        rx.hstack(
            rx.icon_button(
                rx.icon("folder-open", size=14),
                on_click=DividirState.cargar_factura(h.id),
                variant="ghost", color_scheme="violet", size="1",
            ),
            rx.icon_button(
                rx.icon("trash-2", size=14),
                on_click=DividirState.eliminar_factura(h.id),
                variant="ghost", color_scheme="red", size="1",
            ),
            spacing="1",
        ),
        spacing="3", align="center", width="100%",
        padding="10px 16px",
        border_bottom=f"1px solid {T.BORDER_SOFT}",
    )


# ── Saldos globales (cruce entre todas las facturas) ────────
def _saldo_global_row(p) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.text(p.emoji, font_size="14px"),
            width="26px", height="26px",
            border_radius="50%",
            background=p.color,
            display="flex", align_items="center", justify_content="center",
            flex_shrink="0",
        ),
        rx.text(p.nombre, size="2", color=T.TEXT, weight="medium"),
        rx.cond(
            p.es_yo,
            rx.badge("Tú", color_scheme="violet", variant="soft"),
            rx.fragment(),
        ),
        rx.spacer(),
        rx.text(p.balance_fmt, size="2", font_family=T.FONT_MONO,
                weight="bold",
                color=rx.match(
                    p.balance_signo,
                    ("debe", T.RED),
                    ("recibe", T.GREEN),
                    T.TEXT_DIM,
                )),
        rx.match(
            p.balance_signo,
            ("debe", rx.badge("Deudor", color_scheme="red", variant="soft")),
            ("recibe", rx.badge("Acreedor", color_scheme="green",
                                variant="soft")),
            rx.badge("Saldado", color_scheme="gray", variant="soft"),
        ),
        spacing="2", align="center", width="100%",
        padding="10px 12px",
        background=rx.cond(p.es_yo,
                           "rgba(167,139,250,0.06)",
                           "transparent"),
        border_bottom=f"1px solid {T.BORDER_SOFT}",
    )


def _saldo_global_transfer(t) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.text(t.de_emoji, font_size="14px"),
            width="22px", height="22px",
            border_radius="50%",
            background=t.de_color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.text(t.de_nombre, size="2", color=T.TEXT),
        rx.icon("arrow-right", size=14, color=T.TEXT_DIM),
        rx.text(t.monto_fmt, size="2", color=T.VIOLET,
                font_family=T.FONT_MONO, weight="bold"),
        rx.icon("arrow-right", size=14, color=T.TEXT_DIM),
        rx.box(
            rx.text(t.a_emoji, font_size="14px"),
            width="22px", height="22px",
            border_radius="50%",
            background=t.a_color,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.text(t.a_nombre, size="2", color=T.TEXT),
        spacing="2", align="center",
        padding="8px 12px",
        background="rgba(255,255,255,0.03)",
        border=f"1px solid {T.BORDER_SOFT}",
        border_radius=T.RADIUS_SM,
    )


def _saldos_globales_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("scale", size=18, color=T.VIOLET),
                rx.heading("Saldos acumulados", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                spacing="2", align="center",
            ),
            rx.text(
                "Cruce de TODAS las facturas guardadas. Incluye a todas "
                "las personas (también a ti). Verde = acreedor, rojo = deudor.",
                size="2", color=T.TEXT_MUTED,
            ),
            rx.cond(
                DividirState.saldos_globales.length() > 0,
                rx.vstack(
                    rx.foreach(DividirState.saldos_globales, _saldo_global_row),
                    spacing="0", align="stretch", width="100%",
                ),
                rx.vstack(
                    rx.icon("inbox", size=24, color=T.TEXT_DIM),
                    rx.text(
                        "Aún no hay facturas guardadas con personas de tu libreta.",
                        size="2", color=T.TEXT_MUTED,
                    ),
                    spacing="2", align="center", padding="20px",
                ),
            ),
            rx.cond(
                DividirState.transferencias_globales.length() > 0,
                rx.vstack(
                    rx.divider(color_scheme="gray"),
                    rx.hstack(
                        rx.icon("arrow-right-left", size=16, color=T.VIOLET),
                        rx.heading("Liquidación sugerida", size="3",
                                   font_family=T.FONT_HEAD, color=T.TEXT),
                        spacing="2", align="center",
                    ),
                    rx.text(
                        "Mínimo número de transferencias para saldar todo.",
                        size="1", color=T.TEXT_DIM,
                    ),
                    rx.foreach(DividirState.transferencias_globales,
                               _saldo_global_transfer),
                    spacing="2", align="stretch", width="100%",
                ),
                rx.fragment(),
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


def _hist_card() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.heading("Historial reciente", size="4",
                       font_family=T.FONT_HEAD, color=T.TEXT),
            rx.cond(
                DividirState.historial.length() > 0,
                rx.vstack(
                    rx.foreach(DividirState.historial, _hist_row),
                    spacing="0", align="stretch", width="100%",
                ),
                rx.vstack(
                    rx.icon("inbox", size=28, color=T.TEXT_DIM),
                    rx.text("Aún no has guardado ninguna cuenta compartida.",
                            size="2", color=T.TEXT_MUTED),
                    spacing="2", align="center", padding="24px",
                ),
            ),
            spacing="3", align="stretch", width="100%",
        ),
        padding="20px",
    )


def dividir_page() -> rx.Component:
    return main_layout(
        rx.vstack(
            page_title(
                "Dividir cuenta",
                "Reparte facturas compartidas (restaurante, Amazon, "
                "domicilios) y registra solo tu parte.",
            ),
            _header_card(),
            _participantes_card(),
            _items_card(),
            _pagos_card(),
            _result_card(),
            _saldos_card(),
            _registro_dialog(),
            _saldos_globales_card(),
            _hist_card(),
            spacing="4", align="stretch", width="100%",
        ),
    )
