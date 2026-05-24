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

from minty.models import SplitCuenta, Caja, Gasto
from minty.state._autosetters import auto_setters


class SplitHistRow(BaseModel):
    id: int
    fecha: str
    nombre: str
    total_fmt: str
    mi_parte_fmt: str
    tiene_gasto: bool


class ParticipanteRow(BaseModel):
    idx: int
    nombre: str
    es_yo: bool
    paga_fmt: str
    paga: float


@auto_setters
class DividirState(rx.State):
    # Cabecera factura
    nombre: str = ""
    fecha: str = date.today().isoformat()
    notas: str = ""

    # Participantes (lista de nombres). Índice 0 = "Yo" por defecto.
    participantes: list[str] = ["Yo"]
    yo_idx: int = 0

    # Items: cada uno {nombre, monto, incluidos: list[int]}
    items: list[dict] = []

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
    msg: str = ""

    # ── Computed ─────────────────────────────────────────────
    @rx.var
    def total(self) -> float:
        return sum(float(i.get("monto", 0) or 0) for i in self.items)

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
            inc = item.get("incluidos") or []
            inc_validos = [i for i in inc if 0 <= int(i) < n_part]
            if not inc_validos:
                continue
            share = float(item.get("monto", 0) or 0) / len(inc_validos)
            for i in inc_validos:
                acc[int(i)] += share
        out: list[ParticipanteRow] = []
        for i, nombre in enumerate(self.participantes):
            v = acc[i]
            out.append(ParticipanteRow(
                idx=i, nombre=nombre, es_yo=(i == self.yo_idx),
                paga=v, paga_fmt=f"${v:,.0f}",
            ))
        return out

    @rx.var
    def mi_parte(self) -> float:
        n_part = len(self.participantes)
        if not (0 <= self.yo_idx < n_part):
            return 0.0
        acc = 0.0
        for item in self.items:
            inc = [int(i) for i in (item.get("incluidos") or [])
                   if 0 <= int(i) < n_part]
            if not inc:
                continue
            if self.yo_idx in inc:
                acc += float(item.get("monto", 0) or 0) / len(inc)
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
            splits = s.exec(
                sqlmodel.select(SplitCuenta)
                .order_by(sqlmodel.desc(SplitCuenta.fecha),
                          sqlmodel.desc(SplitCuenta.id))
                .limit(30)
            ).all()

        self.cajas_opts = [
            {"id": c.id,
             "etiqueta": (f"{c.nombre} · {c.entidad}" if c.entidad else c.nombre)}
            for c in cajas
        ]
        if self.reg_caja_id == 0 and cajas:
            self.reg_caja_id = cajas[0].id

        self.historial = [
            SplitHistRow(
                id=sp.id or 0,
                fecha=sp.fecha.isoformat(),
                nombre=sp.nombre or "(sin nombre)",
                total_fmt=f"${float(sp.total or 0):,.0f}",
                mi_parte_fmt=f"${float(sp.mi_parte or 0):,.0f}",
                tiene_gasto=(sp.gasto_id is not None),
            )
            for sp in splits
        ]

    # ── Participantes ───────────────────────────────────────
    @rx.event
    def add_participante(self):
        nombre = self.nuevo_participante.strip()
        if not nombre:
            return
        self.participantes = self.participantes + [nombre]
        self.nuevo_participante = ""

    @rx.event
    def remove_participante(self, idx: int):
        if not (0 <= idx < len(self.participantes)):
            return
        if len(self.participantes) <= 1:
            return  # debe quedar al menos uno
        new_list = [p for i, p in enumerate(self.participantes) if i != idx]
        # Re-mapeo de "yo" y "incluidos" en cada item
        new_yo = self.yo_idx
        if idx == self.yo_idx:
            new_yo = 0
        elif idx < self.yo_idx:
            new_yo = self.yo_idx - 1
        new_items = []
        for it in self.items:
            inc_old = [int(i) for i in (it.get("incluidos") or [])]
            inc_new = [
                (i if i < idx else i - 1)
                for i in inc_old if i != idx
            ]
            new_items.append({**it, "incluidos": inc_new})
        self.participantes = new_list
        self.yo_idx = new_yo
        self.items = new_items

    @rx.event
    def set_yo(self, idx: int):
        if 0 <= idx < len(self.participantes):
            self.yo_idx = idx

    # ── Items ───────────────────────────────────────────────
    @rx.event
    def add_item(self):
        nombre = self.nuevo_item_nombre.strip() or "Ítem"
        monto = float(self.nuevo_item_monto or 0)
        if monto <= 0:
            self.msg = "⚠ Indica un monto mayor a 0 para el ítem."
            return
        # Por defecto incluye a todos los participantes
        incluidos = list(range(len(self.participantes)))
        self.items = self.items + [{
            "nombre": nombre,
            "monto": monto,
            "incluidos": incluidos,
        }]
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
        items = [dict(it) for it in self.items]
        items[idx]["nombre"] = val
        self.items = items

    @rx.event
    def set_item_monto(self, idx: int, val: str):
        if not (0 <= idx < len(self.items)):
            return
        try:
            v = float(val) if val else 0.0
        except (TypeError, ValueError):
            v = 0.0
        items = [dict(it) for it in self.items]
        items[idx]["monto"] = v
        self.items = items

    @rx.event
    def toggle_incluido(self, item_idx: int, part_idx: int):
        if not (0 <= item_idx < len(self.items)):
            return
        items = [dict(it) for it in self.items]
        inc = [int(i) for i in (items[item_idx].get("incluidos") or [])]
        if part_idx in inc:
            inc = [i for i in inc if i != part_idx]
        else:
            inc = sorted(inc + [part_idx])
        items[item_idx]["incluidos"] = inc
        self.items = items

    @rx.event
    def reset(self):
        self.nombre = ""
        self.fecha = date.today().isoformat()
        self.notas = ""
        self.participantes = ["Yo"]
        self.yo_idx = 0
        self.items = []
        self.nuevo_participante = ""
        self.nuevo_item_nombre = ""
        self.nuevo_item_monto = 0.0
        self.editing_id = None
        self.last_saved_id = None
        self.last_gasto_id = None
        self.msg = ""

    # ── Persistencia ────────────────────────────────────────
    def _payload(self) -> str:
        return json.dumps({
            "participantes": list(self.participantes),
            "yo_idx": int(self.yo_idx),
            "items": [
                {"nombre": str(i.get("nombre", "")),
                 "monto": float(i.get("monto", 0) or 0),
                 "incluidos": [int(x) for x in (i.get("incluidos") or [])]}
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
            self.participantes = list(data.get("participantes") or ["Yo"])
            self.yo_idx = int(data.get("yo_idx", 0))
            self.items = [
                {"nombre": str(i.get("nombre", "")),
                 "monto": float(i.get("monto", 0) or 0),
                 "incluidos": [int(x) for x in (i.get("incluidos") or [])]}
                for i in (data.get("items") or [])
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
            self.reset()
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
