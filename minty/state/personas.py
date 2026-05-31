"""State para Personas recurrentes (libreta para Dividir cuenta)."""
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from minty.models import Persona, SplitCuenta
from minty.state._autosetters import auto_setters
from minty.services.saldos import (
    compute_saldos_globales, compute_pairwise_debts, compute_persona_balances,
    SaldoGlobalRow, TransferGlobalRow, PairDebtRow, PersonaBalanceRow,
    YO_PID,
)


PALETA = [
    "#a78bfa", "#f472b6", "#fb923c", "#facc15",
    "#4ade80", "#34d399", "#22d3ee", "#60a5fa",
    "#818cf8", "#f87171",
]
EMOJIS = ["👤", "🧑", "👩", "👨", "🧔", "👧", "👦", "🧒",
          "🐱", "🐶", "🦊", "🐼", "🐨", "🐸", "🐯", "🦁"]


class PersonaCard(BaseModel):
    id: int
    nombre: str
    color: str
    emoji: str
    notas: str
    activa: bool
    es_yo: bool = False
    balance_total: float = 0.0
    balance_total_fmt: str = "$0"
    balance_signo: str = "ok"   # "debe" | "recibe" | "ok"
    balances: list[PersonaBalanceRow] = []


@auto_setters
class PersonasState(rx.State):
    rows: list[PersonaCard] = []

    # Saldos acumulados entre todas las facturas
    saldos_globales: list[SaldoGlobalRow] = []
    transferencias_globales: list[TransferGlobalRow] = []
    deudas_pares: list[PairDebtRow] = []

    # Form
    form_open: bool = False
    form_editing_id: Optional[int] = None
    form_nombre: str = ""
    form_color: str = "#a78bfa"
    form_emoji: str = "👤"
    form_notas: str = ""
    form_msg: str = ""

    @rx.event
    def load(self):
        with rx.session() as s:
            personas = s.exec(
                sqlmodel.select(Persona).order_by(
                    sqlmodel.desc(Persona.activa), Persona.nombre
                )
            ).all()
            splits = s.exec(sqlmodel.select(SplitCuenta)).all()

        saldos, transfers = compute_saldos_globales(splits, personas)
        pares = compute_pairwise_debts(splits, personas)
        desglose = compute_persona_balances(pares)
        self.saldos_globales = saldos
        self.transferencias_globales = transfers
        self.deudas_pares = pares

        # Mapa rápido: persona_id → balance global y signo
        bal_global: dict[int, tuple[float, str, str]] = {
            r.persona_id: (r.balance, r.balance_fmt, r.balance_signo)
            for r in saldos
        }

        rows: list[PersonaCard] = []

        # Tarjeta virtual "Yo" al principio (si tiene movimiento o
        # facturas guardadas).
        yo_bal, yo_fmt, yo_signo = bal_global.get(YO_PID, (0.0, "$0", "ok"))
        yo_balances = desglose.get(YO_PID, [])
        if yo_balances or abs(yo_bal) > 0.5:
            rows.append(PersonaCard(
                id=0, nombre="Yo",
                color="#a78bfa", emoji="\U0001F642",
                notas="Tu saldo personal con cada otra persona.",
                activa=True, es_yo=True,
                balance_total=yo_bal,
                balance_total_fmt=yo_fmt,
                balance_signo=yo_signo,
                balances=yo_balances,
            ))

        for p in personas:
            pid = p.id or 0
            bal, fmt, signo = bal_global.get(pid, (0.0, "$0", "ok"))
            rows.append(PersonaCard(
                id=pid, nombre=p.nombre or "(sin nombre)",
                color=p.color or "#a78bfa",
                emoji=p.emoji or "👤",
                notas=p.notas or "",
                activa=bool(p.activa),
                es_yo=False,
                balance_total=bal,
                balance_total_fmt=fmt,
                balance_signo=signo,
                balances=desglose.get(pid, []),
            ))
        self.rows = rows

    @rx.event
    def toggle_form(self):
        self.form_open = not self.form_open
        if self.form_open and not self.form_editing_id:
            self.form_nombre = ""
            self.form_color = "#a78bfa"
            self.form_emoji = "👤"
            self.form_notas = ""
        self.form_msg = ""

    @rx.event
    def cancelar(self):
        self.form_open = False
        self.form_editing_id = None
        self.form_msg = ""

    @rx.event
    def editar(self, pid: int):
        with rx.session() as s:
            p = s.get(Persona, pid)
            if not p:
                return
            self.form_editing_id = p.id
            self.form_nombre = p.nombre
            self.form_color = p.color or "#a78bfa"
            self.form_emoji = p.emoji or "👤"
            self.form_notas = p.notas or ""
            self.form_open = True
            self.form_msg = "✏ Editando persona."

    @rx.event
    def guardar(self):
        nombre = self.form_nombre.strip()
        if not nombre:
            self.form_msg = "⚠ Indica un nombre."
            return
        with rx.session() as s:
            if self.form_editing_id:
                p = s.get(Persona, self.form_editing_id)
                if not p:
                    self.form_msg = "⚠ No encontrada."
                    return
                p.nombre = nombre
                p.color = self.form_color
                p.emoji = self.form_emoji
                p.notas = self.form_notas
                s.add(p)
            else:
                s.add(Persona(
                    nombre=nombre,
                    color=self.form_color,
                    emoji=self.form_emoji,
                    notas=self.form_notas,
                ))
            s.commit()
        self.form_open = False
        self.form_editing_id = None
        self.load()

    @rx.event
    def toggle_activa(self, pid: int):
        with rx.session() as s:
            p = s.get(Persona, pid)
            if p:
                p.activa = not p.activa
                s.add(p)
                s.commit()
        self.load()

    @rx.event
    def eliminar(self, pid: int):
        with rx.session() as s:
            p = s.get(Persona, pid)
            if p:
                s.delete(p)
                s.commit()
        self.load()
