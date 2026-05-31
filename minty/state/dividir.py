"""State para Dividir cuenta — facturas/cuentas compartidas.

Modelo de reparto: cada ítem define qué participantes están "incluidos".
El monto del ítem se divide en partes iguales entre los incluidos. Cubre
el 90% de casos reales (cena con todos comparten plato base, alguien
agrega postre, propina opcional, etc.).
"""
from __future__ import annotations
import json
from datetime import date
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from minty.models import SplitCuenta, Caja, Gasto, Persona
from minty.state._autosetters import auto_setters


class SplitHistRow(BaseModel):
    id: int
    fecha: str
    nombre: str
    total_fmt: str
    mi_parte_fmt: str
    tiene_gasto: bool
    pagador_nombre: str = ""
    n_participantes: int = 0


class ParticipanteRow(BaseModel):
    idx: int
    nombre: str
    es_yo: bool
    paga_fmt: str            # cuánto le toca pagar
    paga: float
    pagado_str: str          # input ligado a pagos[idx]
    pagado: float
    balance: float           # pagado - paga (positivo: le deben)
    balance_fmt: str
    balance_signo: str       # "debe" | "recibe" | "ok"
    color: str
    emoji: str
    persona_id: int          # 0 si es manual


class TransferRow(BaseModel):
    de_idx: int
    de_nombre: str
    de_emoji: str
    de_color: str
    a_idx: int
    a_nombre: str
    a_emoji: str
    a_color: str
    monto: float
    monto_fmt: str


class PersonaPick(BaseModel):
    id: int
    nombre: str
    color: str
    emoji: str
    ya_agregada: bool


class PagadorPick(BaseModel):
    idx: int
    nombre: str
    emoji: str
    color: str
    seleccionado: bool


class SaldoGlobalRow(BaseModel):
    persona_id: int
    nombre: str
    emoji: str
    color: str
    balance: float
    balance_fmt: str
    balance_signo: str   # "debe" | "recibe" | "ok"


class ItemRow(BaseModel):
    nombre: str = ""
    monto: float = 0.0
    incluidos: list[int] = []
    monto_str: str = "0"


@auto_setters
class DividirState(rx.State):
    # Cabecera factura
    nombre: str = ""
    fecha: str = date.today().isoformat()
    notas: str = ""

    # Participantes (lista de nombres). Índice 0 = "Yo" por defecto.
    participantes: list[str] = ["Yo"]
    yo_idx: int = 0
    # Persona.id por participante (0 si es manual / no vinculado).
    participante_persona_ids: list[int] = [0]
    # Color/emoji por participante (paralelos).
    participante_colors: list[str] = ["#a78bfa"]
    participante_emojis: list[str] = ["\U0001F464"]
    # Cuánto pagó cada participante (paralelo a participantes).
    pagos: list[float] = [0.0]
    pagos_str: list[str] = ["0"]
    # Pagador único explícito. -1 = sin marcar / multi-pagador.
    pagador_idx: int = -1

    # Items: cada uno con nombre, monto e incluidos
    items: list[ItemRow] = []

    # Personas guardadas disponibles para el chip-picker.
    personas_disponibles: list[PersonaPick] = []

    # Inputs para añadir cosas
    nuevo_participante: str = ""
    nuevo_item_nombre: str = ""
    nuevo_item_monto: float = 0.0

    # Estado del registro como Gasto (modal)
    reg_open: bool = False
    reg_caja_id: int = 0
    reg_categoria: str = "Comida fuera"
    reg_descripcion: str = ""
    reg_msg: str = ""
    cajas_opts: list[dict] = []

    # Persistencia / historial
    editing_id: Optional[int] = None
    last_saved_id: Optional[int] = None
    last_gasto_id: Optional[int] = None
    historial: list[SplitHistRow] = []
    # Saldos acumulados entre todas las facturas (por persona guardada).
    saldos_globales: list[SaldoGlobalRow] = []
    transferencias_globales: list[TransferRow] = []
    msg: str = ""

    # ── Computed ─────────────────────────────────────────────
    @rx.var
    def total(self) -> float:
        return sum(float(i.monto or 0) for i in self.items)

    @rx.var
    def total_fmt(self) -> str:
        return f"${self.total:,.0f}"

    @rx.var
    def por_persona(self) -> list[ParticipanteRow]:
        n_part = len(self.participantes)
        if n_part == 0:
            return []
        acc = [0.0] * n_part
        for item in self.items:
            inc = list(item.incluidos or [])
            inc_validos = [i for i in inc if 0 <= int(i) < n_part]
            if not inc_validos:
                continue
            share = float(item.monto or 0) / len(inc_validos)
            for i in inc_validos:
                acc[int(i)] += share
        out: list[ParticipanteRow] = []
        for i, nombre in enumerate(self.participantes):
            paga = acc[i]
            pagado = float(self.pagos[i]) if i < len(self.pagos) else 0.0
            pagado_str = (self.pagos_str[i]
                          if i < len(self.pagos_str) else "0")
            balance = pagado - paga
            if abs(balance) < 0.5:
                signo = "ok"
            elif balance > 0:
                signo = "recibe"
            else:
                signo = "debe"
            color = (self.participante_colors[i]
                     if i < len(self.participante_colors) else "#a78bfa")
            emoji = (self.participante_emojis[i]
                     if i < len(self.participante_emojis) else "\U0001F464")
            pid = (self.participante_persona_ids[i]
                   if i < len(self.participante_persona_ids) else 0)
            sign_str = "" if balance >= 0 else "-"
            out.append(ParticipanteRow(
                idx=i, nombre=nombre, es_yo=(i == self.yo_idx),
                paga=paga, paga_fmt=f"${paga:,.0f}",
                pagado=pagado, pagado_str=pagado_str,
                balance=balance,
                balance_fmt=f"{sign_str}${abs(balance):,.0f}",
                balance_signo=signo,
                color=color, emoji=emoji,
                persona_id=pid,
            ))
        return out

    @rx.var
    def total_pagado(self) -> float:
        return sum(float(p or 0) for p in self.pagos)

    @rx.var
    def total_pagado_fmt(self) -> str:
        return f"${self.total_pagado:,.0f}"

    @rx.var
    def diferencia_pagos(self) -> float:
        return self.total_pagado - self.total

    @rx.var
    def diferencia_pagos_fmt(self) -> str:
        v = self.diferencia_pagos
        s = "" if v >= 0 else "-"
        return f"{s}${abs(v):,.0f}"

    @rx.var
    def pagos_balanceados(self) -> bool:
        return abs(self.diferencia_pagos) < 0.5

    @rx.var
    def transferencias(self) -> list[TransferRow]:
        """Algoritmo greedy: empareja deudores con acreedores hasta saldar."""
        rows = self.por_persona
        n = len(rows)
        if n == 0:
            return []
        # Copia mutable de balances
        bal = [r.balance for r in rows]
        result: list[TransferRow] = []
        # Iteración acotada para evitar bucles infinitos por floats
        for _ in range(n * n):
            # mayor deudor (más negativo) y mayor acreedor (más positivo)
            i_deb = min(range(n), key=lambda i: bal[i])
            i_cre = max(range(n), key=lambda i: bal[i])
            if bal[i_deb] >= -0.5 or bal[i_cre] <= 0.5:
                break
            monto = min(-bal[i_deb], bal[i_cre])
            if monto < 0.5:
                break
            d = rows[i_deb]
            c = rows[i_cre]
            result.append(TransferRow(
                de_idx=d.idx, de_nombre=d.nombre,
                de_emoji=d.emoji, de_color=d.color,
                a_idx=c.idx, a_nombre=c.nombre,
                a_emoji=c.emoji, a_color=c.color,
                monto=monto, monto_fmt=f"${monto:,.0f}",
            ))
            bal[i_deb] += monto
            bal[i_cre] -= monto
        return result

    @rx.var
    def hay_transferencias(self) -> bool:
        return len(self.transferencias) > 0

    @rx.var
    def pagadores(self) -> list[PagadorPick]:
        out: list[PagadorPick] = []
        for i, nombre in enumerate(self.participantes):
            color = (self.participante_colors[i]
                     if i < len(self.participante_colors) else "#a78bfa")
            emoji = (self.participante_emojis[i]
                     if i < len(self.participante_emojis) else "\U0001F464")
            out.append(PagadorPick(
                idx=i, nombre=nombre, emoji=emoji, color=color,
                seleccionado=(i == self.pagador_idx),
            ))
        return out

    @rx.var
    def pagador_nombre(self) -> str:
        if 0 <= self.pagador_idx < len(self.participantes):
            return self.participantes[self.pagador_idx]
        return ""

    @rx.var
    def hay_pagador(self) -> bool:
        return 0 <= self.pagador_idx < len(self.participantes)

    @rx.var
    def mi_parte(self) -> float:
        n_part = len(self.participantes)
        if not (0 <= self.yo_idx < n_part):
            return 0.0
        acc = 0.0
        for item in self.items:
            inc = [int(i) for i in (item.incluidos or [])
                   if 0 <= int(i) < n_part]
            if not inc:
                continue
            if self.yo_idx in inc:
                acc += float(item.monto or 0) / len(inc)
        return acc

    @rx.var
    def mi_parte_fmt(self) -> str:
        return f"${self.mi_parte:,.0f}"

    @rx.var
    def hay_items(self) -> bool:
        return len(self.items) > 0

    # ── Carga ────────────────────────────────────────────────
    @rx.event
    def load(self):
        with rx.session() as s:
            cajas = s.exec(
                sqlmodel.select(Caja).where(
                    Caja.activa == True  # noqa: E712
                ).order_by(Caja.orden, Caja.id)
            ).all()
            splits_hist = s.exec(
                sqlmodel.select(SplitCuenta)
                .order_by(sqlmodel.desc(SplitCuenta.fecha),
                          sqlmodel.desc(SplitCuenta.id))
                .limit(30)
            ).all()
            splits_all = s.exec(
                sqlmodel.select(SplitCuenta)
            ).all()
            personas = s.exec(
                sqlmodel.select(Persona).where(
                    Persona.activa == True  # noqa: E712
                ).order_by(Persona.nombre)
            ).all()

        self.cajas_opts = [
            {"id": c.id,
             "etiqueta": (f"{c.nombre} · {c.entidad}" if c.entidad else c.nombre)}
            for c in cajas
        ]
        if self.reg_caja_id == 0 and cajas:
            self.reg_caja_id = cajas[0].id

        ya_ids = set(self.participante_persona_ids or [])
        self.personas_disponibles = [
            PersonaPick(
                id=p.id or 0, nombre=p.nombre or "",
                color=p.color or "#a78bfa",
                emoji=p.emoji or "\U0001F464",
                ya_agregada=((p.id or 0) in ya_ids and (p.id or 0) != 0),
            )
            for p in personas
        ]

        info_personas = {
            (p.id or 0): {
                "nombre": p.nombre or "",
                "color": p.color or "#a78bfa",
                "emoji": p.emoji or "\U0001F464",
            }
            for p in personas
        }

        # Helper para extraer balance + persona_id por participante de un payload.
        def _extraer_balances(data: dict) -> list[tuple[int, float]]:
            parts = data.get("participantes") or []
            n = len(parts) if isinstance(parts, list) else 0
            if n == 0:
                return []
            pids: list[int] = []
            for p in parts:
                if isinstance(p, dict):
                    pids.append(int(p.get("persona_id", 0) or 0))
                else:
                    pids.append(0)
            balances = data.get("balances")
            if isinstance(balances, list) and balances:
                bals = [float(b or 0) for b in balances]
                while len(bals) < n:
                    bals.append(0.0)
            else:
                # Fallback: calcular desde pagos + items.
                pagos = [float(x or 0) for x in (data.get("pagos") or [])]
                while len(pagos) < n:
                    pagos.append(0.0)
                deb = [0.0] * n
                for it in (data.get("items") or []):
                    inc = [int(x) for x in (it.get("incluidos") or [])
                           if 0 <= int(x) < n]
                    if not inc:
                        continue
                    share = float(it.get("monto", 0) or 0) / len(inc)
                    for i in inc:
                        deb[i] += share
                bals = [pagos[i] - deb[i] for i in range(n)]
            return list(zip(pids, bals))

        # Historial reciente
        hist: list[SplitHistRow] = []
        for sp in splits_hist:
            try:
                data = json.loads(sp.payload or "{}")
            except json.JSONDecodeError:
                data = {}
            parts = data.get("participantes") or []
            n_part = len(parts) if isinstance(parts, list) else 0
            pagador = ""
            pid_pagador = int(data.get("pagador_idx", -1))
            pagos = data.get("pagos") or []
            idx_pag = -1
            if 0 <= pid_pagador < n_part:
                idx_pag = pid_pagador
            elif isinstance(pagos, list) and pagos:
                idx_max = max(range(len(pagos)),
                              key=lambda i: float(pagos[i] or 0))
                if float(pagos[idx_max] or 0) > 0:
                    idx_pag = idx_max
            if 0 <= idx_pag < n_part:
                p_obj = parts[idx_pag]
                if isinstance(p_obj, dict):
                    pagador = p_obj.get("nombre", "")
                else:
                    pagador = str(p_obj)
            hist.append(SplitHistRow(
                id=sp.id or 0,
                fecha=sp.fecha.isoformat(),
                nombre=sp.nombre or "(sin nombre)",
                total_fmt=f"${float(sp.total or 0):,.0f}",
                mi_parte_fmt=f"${float(sp.mi_parte or 0):,.0f}",
                tiene_gasto=(sp.gasto_id is not None),
                pagador_nombre=pagador,
                n_participantes=n_part,
            ))
        self.historial = hist

        # Saldos globales: agregar balances de TODAS las facturas por persona_id
        agg: dict[int, float] = {}
        for sp in splits_all:
            try:
                data = json.loads(sp.payload or "{}")
            except json.JSONDecodeError:
                continue
            for pid, bal in _extraer_balances(data):
                if pid <= 0:
                    continue
                agg[pid] = agg.get(pid, 0.0) + bal

        saldos: list[SaldoGlobalRow] = []
        for pid, bal in agg.items():
            info = info_personas.get(pid)
            if not info:
                continue
            if abs(bal) < 0.5:
                signo = "ok"
            elif bal > 0:
                signo = "recibe"
            else:
                signo = "debe"
            sign_str = "" if bal >= 0 else "-"
            saldos.append(SaldoGlobalRow(
                persona_id=pid, nombre=info["nombre"],
                color=info["color"], emoji=info["emoji"],
                balance=bal,
                balance_fmt=f"{sign_str}${abs(bal):,.0f}",
                balance_signo=signo,
            ))
        # Orden: deudores primero, luego saldados, luego acreedores
        order_signo = {"debe": 0, "ok": 1, "recibe": 2}
        saldos.sort(key=lambda r: (order_signo[r.balance_signo], -abs(r.balance)))
        self.saldos_globales = saldos

        # Transferencias mínimas globales (greedy)
        transfers: list[TransferRow] = []
        if saldos:
            bal_arr = [r.balance for r in saldos]
            n = len(saldos)
            for _ in range(n * n):
                i_deb = min(range(n), key=lambda i: bal_arr[i])
                i_cre = max(range(n), key=lambda i: bal_arr[i])
                if bal_arr[i_deb] >= -0.5 or bal_arr[i_cre] <= 0.5:
                    break
                monto = min(-bal_arr[i_deb], bal_arr[i_cre])
                if monto < 0.5:
                    break
                d = saldos[i_deb]
                c = saldos[i_cre]
                transfers.append(TransferRow(
                    de_idx=d.persona_id, de_nombre=d.nombre,
                    de_emoji=d.emoji, de_color=d.color,
                    a_idx=c.persona_id, a_nombre=c.nombre,
                    a_emoji=c.emoji, a_color=c.color,
                    monto=monto, monto_fmt=f"${monto:,.0f}",
                ))
                bal_arr[i_deb] += monto
                bal_arr[i_cre] -= monto
        self.transferencias_globales = transfers

    # ── Participantes ───────────────────────────────────────
    def _append_participante(self, nombre: str, persona_id: int = 0,
                             color: str = "#a78bfa",
                             emoji: str = "\U0001F464"):
        self.participantes = self.participantes + [nombre]
        self.participante_persona_ids = (
            self.participante_persona_ids + [persona_id]
        )
        self.participante_colors = self.participante_colors + [color]
        self.participante_emojis = self.participante_emojis + [emoji]
        self.pagos = self.pagos + [0.0]
        self.pagos_str = self.pagos_str + ["0"]
        new_idx = len(self.participantes) - 1
        new_items: list[ItemRow] = []
        for it in self.items:
            inc = list(it.incluidos or [])
            if new_idx not in inc:
                inc = sorted(inc + [new_idx])
            new_items.append(ItemRow(
                nombre=it.nombre, monto=it.monto,
                incluidos=inc, monto_str=it.monto_str,
            ))
        self.items = new_items
        if persona_id:
            self.personas_disponibles = [
                PersonaPick(
                    id=p.id, nombre=p.nombre,
                    color=p.color, emoji=p.emoji,
                    ya_agregada=(p.id == persona_id) or p.ya_agregada,
                )
                for p in self.personas_disponibles
            ]

    @rx.event
    def add_participante(self):
        nombre = self.nuevo_participante.strip()
        if not nombre:
            return
        self._append_participante(nombre)
        self.nuevo_participante = ""

    @rx.event
    def agregar_persona(self, pid: int):
        with rx.session() as s:
            p = s.get(Persona, pid)
            if not p:
                return
            if (p.id or 0) in (self.participante_persona_ids or []):
                return
            self._append_participante(
                nombre=p.nombre or "",
                persona_id=p.id or 0,
                color=p.color or "#a78bfa",
                emoji=p.emoji or "\U0001F464",
            )

    @rx.event
    def remove_participante(self, idx: int):
        if not (0 <= idx < len(self.participantes)):
            return
        if len(self.participantes) <= 1:
            return
        new_list = [p for i, p in enumerate(self.participantes) if i != idx]
        new_pids = [p for i, p in enumerate(self.participante_persona_ids) if i != idx]
        new_colors = [p for i, p in enumerate(self.participante_colors) if i != idx]
        new_emojis = [p for i, p in enumerate(self.participante_emojis) if i != idx]
        new_pagos = [p for i, p in enumerate(self.pagos) if i != idx]
        new_pagos_str = [p for i, p in enumerate(self.pagos_str) if i != idx]
        new_yo = self.yo_idx
        if idx == self.yo_idx:
            new_yo = 0
        elif idx < self.yo_idx:
            new_yo = self.yo_idx - 1
        new_items: list[ItemRow] = []
        for it in self.items:
            inc_old = [int(i) for i in (it.incluidos or [])]
            inc_new = [
                (i if i < idx else i - 1)
                for i in inc_old if i != idx
            ]
            new_items.append(ItemRow(
                nombre=it.nombre, monto=it.monto,
                incluidos=inc_new,
                monto_str=f"{it.monto:.0f}",
            ))
        self.participantes = new_list
        self.participante_persona_ids = new_pids
        self.participante_colors = new_colors
        self.participante_emojis = new_emojis
        self.pagos = new_pagos
        self.pagos_str = new_pagos_str
        self.yo_idx = new_yo
        self.items = new_items
        ya_ids = set(new_pids)
        self.personas_disponibles = [
            PersonaPick(
                id=p.id, nombre=p.nombre, color=p.color, emoji=p.emoji,
                ya_agregada=(p.id in ya_ids and p.id != 0),
            )
            for p in self.personas_disponibles
        ]

    @rx.event
    def set_pago(self, idx: int, val: str):
        if not (0 <= idx < len(self.pagos)):
            return
        try:
            v = float(val) if val else 0.0
        except (TypeError, ValueError):
            v = 0.0
        new_pagos = list(self.pagos)
        new_pagos[idx] = v
        new_str = list(self.pagos_str)
        new_str[idx] = val if val else "0"
        self.pagos = new_pagos
        self.pagos_str = new_str
        # Si edita manualmente los montos, deja de ser un pago único.
        if self.pagador_idx >= 0:
            n_no_cero = sum(1 for p in new_pagos if abs(p) > 0.01)
            if n_no_cero != 1 or (
                0 <= self.pagador_idx < len(new_pagos)
                and abs(new_pagos[self.pagador_idx] - float(self.total)) > 0.5
            ):
                self.pagador_idx = -1

    @rx.event
    def set_pagador(self, idx: int):
        """Marca un único pagador y le asigna el total de la factura."""
        if not (0 <= idx < len(self.participantes)):
            return
        # Toggle: clic en el mismo pagador lo desmarca.
        if self.pagador_idx == idx:
            self.pagador_idx = -1
            return
        self.pagador_idx = idx
        total = float(self.total)
        new_pagos = [0.0 for _ in self.pagos]
        if 0 <= idx < len(new_pagos):
            new_pagos[idx] = total
        self.pagos = new_pagos
        self.pagos_str = [f"{p:.0f}" for p in new_pagos]

    @rx.event
    def yo_pago_todo(self):
        if not (0 <= self.yo_idx < len(self.pagos)):
            return
        idx = self.yo_idx
        self.pagador_idx = idx
        total = float(self.total)
        new_pagos = [0.0 for _ in self.pagos]
        new_pagos[idx] = total
        self.pagos = new_pagos
        self.pagos_str = [f"{p:.0f}" for p in new_pagos]

    @rx.event
    def limpiar_pagos(self):
        self.pagos = [0.0 for _ in self.pagos]
        self.pagos_str = ["0" for _ in self.pagos]
        self.pagador_idx = -1

    @rx.event
    def set_yo(self, idx: int):
        if 0 <= idx < len(self.participantes):
            self.yo_idx = idx

    # ── Items ───────────────────────────────────────────────
    @rx.event
    def add_item(self):
        nombre = self.nuevo_item_nombre.strip() or "Ítem"
        monto = float(self.nuevo_item_monto or 0)
        if monto == 0:
            self.msg = "⚠ El monto no puede ser 0 (usa positivo para cargos, negativo para descuentos)."
            return
        # Por defecto incluye a todos los participantes
        incluidos = list(range(len(self.participantes)))
        self.items = self.items + [ItemRow(
            nombre=nombre,
            monto=monto,
            incluidos=incluidos,
            monto_str=f"{monto:.0f}",
        )]
        self.nuevo_item_nombre = ""
        self.nuevo_item_monto = 0.0
        self.msg = ""

    @rx.event
    def add_descuento(self):
        """Atajo: agrega un ítem con monto negativo (descuento/bono)."""
        nombre = self.nuevo_item_nombre.strip() or "Descuento"
        monto = float(self.nuevo_item_monto or 0)
        if monto == 0:
            self.msg = "⚠ Indica un monto a descontar."
            return
        # Forzar negativo
        monto = -abs(monto)
        incluidos = list(range(len(self.participantes)))
        self.items = self.items + [ItemRow(
            nombre=nombre,
            monto=monto,
            incluidos=incluidos,
            monto_str=f"{monto:.0f}",
        )]
        self.nuevo_item_nombre = ""
        self.nuevo_item_monto = 0.0
        self.msg = ""

    @rx.event
    def remove_item(self, idx: int):
        if not (0 <= idx < len(self.items)):
            return
        self.items = [it for i, it in enumerate(self.items) if i != idx]

    @rx.event
    def set_item_nombre(self, idx: int, val: str):
        if not (0 <= idx < len(self.items)):
            return
        items = [it.model_copy() for it in self.items]
        items[idx].nombre = val
        self.items = items

    @rx.event
    def set_item_monto(self, idx: int, val: str):
        if not (0 <= idx < len(self.items)):
            return
        try:
            v = float(val) if val else 0.0
        except (TypeError, ValueError):
            v = 0.0
        items = [it.model_copy() for it in self.items]
        items[idx].monto = v
        items[idx].monto_str = val if val else "0"
        self.items = items

    @rx.event
    def toggle_incluido(self, item_idx: int, part_idx: int):
        if not (0 <= item_idx < len(self.items)):
            return
        items = [it.model_copy() for it in self.items]
        inc = [int(i) for i in (items[item_idx].incluidos or [])]
        if part_idx in inc:
            inc = [i for i in inc if i != part_idx]
        else:
            inc = sorted(inc + [part_idx])
        items[item_idx].incluidos = inc
        self.items = items

    @rx.event
    def nueva_factura(self):
        self.nombre = ""
        self.fecha = date.today().isoformat()
        self.notas = ""
        self.participantes = ["Yo"]
        self.yo_idx = 0
        self.pagador_idx = -1
        self.participante_persona_ids = [0]
        self.participante_colors = ["#a78bfa"]
        self.participante_emojis = ["\U0001F464"]
        self.pagos = [0.0]
        self.pagos_str = ["0"]
        self.items = []
        self.nuevo_participante = ""
        self.nuevo_item_nombre = ""
        self.nuevo_item_monto = 0.0
        self.editing_id = None
        self.last_saved_id = None
        self.last_gasto_id = None
        self.msg = ""
        # Re-marca todas las personas disponibles como no agregadas
        self.personas_disponibles = [
            PersonaPick(
                id=p.id, nombre=p.nombre, color=p.color, emoji=p.emoji,
                ya_agregada=False,
            )
            for p in self.personas_disponibles
        ]

    # ── Persistencia ────────────────────────────────────────
    def _payload(self) -> str:
        # Cálculo de balances por participante para acumular en saldos globales
        rows = self.por_persona
        balances = [float(r.balance) for r in rows]
        return json.dumps({
            "participantes": [
                {"nombre": n,
                 "persona_id": int(self.participante_persona_ids[i])
                 if i < len(self.participante_persona_ids) else 0,
                 "color": self.participante_colors[i]
                 if i < len(self.participante_colors) else "#a78bfa",
                 "emoji": self.participante_emojis[i]
                 if i < len(self.participante_emojis) else "\U0001F464"}
                for i, n in enumerate(self.participantes)
            ],
            "yo_idx": int(self.yo_idx),
            "pagador_idx": int(self.pagador_idx),
            "pagos": [float(p or 0) for p in self.pagos],
            "balances": balances,
            "items": [
                {"nombre": str(i.nombre or ""),
                 "monto": float(i.monto or 0),
                 "incluidos": [int(x) for x in (i.incluidos or [])]}
                for i in self.items
            ],
            "notas": self.notas,
        }, ensure_ascii=False)

    @rx.event
    def guardar_factura(self):
        if not self.items:
            self.msg = "⚠ Agrega al menos un ítem antes de guardar."
            return
        try:
            f = date.fromisoformat(self.fecha)
        except ValueError:
            self.msg = "⚠ Fecha inválida."
            return
        nombre = self.nombre.strip() or "Cuenta compartida"
        total = float(self.total)
        mi_parte = float(self.mi_parte)
        payload = self._payload()
        with rx.session() as s:
            if self.editing_id:
                sp = s.get(SplitCuenta, self.editing_id)
                if not sp:
                    self.msg = "⚠ Factura no encontrada."
                    return
                sp.fecha = f
                sp.nombre = nombre
                sp.notas = self.notas
                sp.total = total
                sp.mi_parte = mi_parte
                sp.payload = payload
                s.add(sp)
                s.commit()
                self.last_saved_id = sp.id
            else:
                sp = SplitCuenta(
                    fecha=f, nombre=nombre, notas=self.notas,
                    total=total, mi_parte=mi_parte, payload=payload,
                )
                s.add(sp)
                s.commit()
                s.refresh(sp)
                self.last_saved_id = sp.id
                self.editing_id = sp.id
        self.msg = "✓ Factura guardada."
        self.load()

    @rx.event
    def cargar_factura(self, sid: int):
        with rx.session() as s:
            sp = s.get(SplitCuenta, sid)
            if not sp:
                return
            try:
                data = json.loads(sp.payload or "{}")
            except json.JSONDecodeError:
                data = {}
            self.editing_id = sp.id
            self.last_saved_id = sp.id
            self.last_gasto_id = sp.gasto_id
            self.nombre = sp.nombre
            self.fecha = sp.fecha.isoformat()
            self.notas = sp.notas or data.get("notas", "")

            raw_parts = data.get("participantes") or ["Yo"]
            nombres: list[str] = []
            pids: list[int] = []
            colors: list[str] = []
            emojis: list[str] = []
            for p in raw_parts:
                if isinstance(p, dict):
                    nombres.append(str(p.get("nombre", "")))
                    pids.append(int(p.get("persona_id", 0) or 0))
                    colors.append(str(p.get("color", "#a78bfa")))
                    emojis.append(str(p.get("emoji", "\U0001F464")))
                else:
                    nombres.append(str(p))
                    pids.append(0)
                    colors.append("#a78bfa")
                    emojis.append("\U0001F464")
            self.participantes = nombres
            self.participante_persona_ids = pids
            self.participante_colors = colors
            self.participante_emojis = emojis
            self.yo_idx = int(data.get("yo_idx", 0))
            self.pagador_idx = int(data.get("pagador_idx", -1))
            raw_pagos = data.get("pagos") or [0.0] * len(nombres)
            pagos_f = [float(x or 0) for x in raw_pagos]
            # Asegurar misma longitud que participantes
            while len(pagos_f) < len(nombres):
                pagos_f.append(0.0)
            pagos_f = pagos_f[:len(nombres)]
            self.pagos = pagos_f
            self.pagos_str = [f"{p:.0f}" for p in pagos_f]
            self.items = [
                ItemRow(
                    nombre=str(i.get("nombre", "")),
                    monto=float(i.get("monto", 0) or 0),
                    incluidos=[int(x) for x in (i.get("incluidos") or [])],
                    monto_str=f"{float(i.get('monto', 0) or 0):.0f}",
                )
                for i in (data.get("items") or [])
            ]
            # Refrescar marca de personas ya agregadas
            ya_ids = set(pids)
            self.personas_disponibles = [
                PersonaPick(
                    id=p.id, nombre=p.nombre, color=p.color, emoji=p.emoji,
                    ya_agregada=(p.id in ya_ids and p.id != 0),
                )
                for p in self.personas_disponibles
            ]
        self.msg = f"📂 Cargada factura «{self.nombre}»."

    @rx.event
    def eliminar_factura(self, sid: int):
        with rx.session() as s:
            sp = s.get(SplitCuenta, sid)
            if sp:
                s.delete(sp)
                s.commit()
        if self.editing_id == sid:
            self.nueva_factura()
        self.load()

    # ── Registrar mi parte como Gasto ───────────────────────
    @rx.event
    def abrir_registro(self):
        if self.mi_parte <= 0:
            self.msg = "⚠ Tu parte es 0. Agrega ítems donde participes."
            return
        self.reg_open = True
        self.reg_msg = ""
        if not self.reg_descripcion:
            self.reg_descripcion = self.nombre or "Cuenta compartida"

    @rx.event
    def cerrar_registro(self):
        self.reg_open = False
        self.reg_msg = ""

    @rx.event
    def set_reg_caja(self, val: str):
        try:
            self.reg_caja_id = int(val)
        except (TypeError, ValueError):
            self.reg_caja_id = 0

    @rx.event
    def registrar_mi_parte(self):
        if self.mi_parte <= 0:
            self.reg_msg = "⚠ Tu parte es 0."
            return
        if not self.reg_caja_id:
            self.reg_msg = "⚠ Selecciona una caja."
            return
        try:
            f = date.fromisoformat(self.fecha)
        except ValueError:
            self.reg_msg = "⚠ Fecha inválida."
            return
        with rx.session() as s:
            g = Gasto(
                fecha=f,
                descripcion=(self.reg_descripcion.strip()
                             or self.nombre.strip()
                             or "Cuenta compartida"),
                categoria=self.reg_categoria.strip() or "Otros",
                monto=float(self.mi_parte),
                caja_id=int(self.reg_caja_id),
            )
            s.add(g)
            s.commit()
            s.refresh(g)
            gid = g.id
            # Si la factura ya estaba guardada, vincular gasto_id
            if self.editing_id:
                sp = s.get(SplitCuenta, self.editing_id)
                if sp:
                    sp.gasto_id = gid
                    s.add(sp)
                    s.commit()
        self.last_gasto_id = gid
        self.reg_open = False
        self.msg = "✓ Tu parte fue registrada como gasto."
        self.load()
