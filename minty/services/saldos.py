"""Cálculo de saldos globales acumulados entre todas las facturas
de SplitCuenta. Cruza todas las personas (incluido "Yo" como bucket
virtual con id=-1) y devuelve los balances + transferencias mínimas.
"""
from __future__ import annotations
import json
from typing import Iterable
from pydantic import BaseModel

from minty.models import SplitCuenta, Persona

# ID virtual reservado para representar al usuario ("Yo").
YO_PID = -1


class SaldoGlobalRow(BaseModel):
    persona_id: int
    nombre: str
    emoji: str
    color: str
    balance: float
    balance_fmt: str
    balance_signo: str   # "debe" | "recibe" | "ok"
    es_yo: bool = False


class TransferGlobalRow(BaseModel):
    de_idx: int          # persona_id (o -1 = Yo)
    de_nombre: str
    de_emoji: str
    de_color: str
    a_idx: int
    a_nombre: str
    a_emoji: str
    a_color: str
    monto: float
    monto_fmt: str


class PairDebtRow(BaseModel):
    """Una persona le debe a otra (ya neteado)."""
    de_idx: int
    de_nombre: str
    de_emoji: str
    de_color: str
    de_es_yo: bool
    a_idx: int
    a_nombre: str
    a_emoji: str
    a_color: str
    a_es_yo: bool
    monto: float
    monto_fmt: str
    involucra_yo: bool


def _extraer_balances(data: dict) -> list[tuple[int, float, bool]]:
    """Devuelve [(persona_id, balance, es_yo)] por participante.

    `persona_id == 0` significa participante manual no vinculado a la
    libreta — se descarta al agregar.
    `es_yo == True` cuando es el participante en `yo_idx` (lo agrupamos
    bajo `YO_PID`).
    """
    parts = data.get("participantes") or []
    n = len(parts) if isinstance(parts, list) else 0
    if n == 0:
        return []
    yo_idx = int(data.get("yo_idx", 0))
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
        # Fallback para facturas viejas: calcular desde pagos + items.
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
    out: list[tuple[int, float, bool]] = []
    for i in range(n):
        out.append((pids[i], bals[i], i == yo_idx))
    return out


def compute_saldos_globales(
    splits: Iterable[SplitCuenta],
    personas: Iterable[Persona],
    yo_color: str = "#a78bfa",
    yo_emoji: str = "\U0001F642",
    yo_nombre: str = "Yo",
) -> tuple[list[SaldoGlobalRow], list[TransferGlobalRow]]:
    info_personas: dict[int, dict] = {
        (p.id or 0): {
            "nombre": p.nombre or "",
            "color": p.color or "#a78bfa",
            "emoji": p.emoji or "\U0001F464",
        }
        for p in personas
    }

    # Acumular: clave es persona_id (>0) o YO_PID para Yo.
    agg: dict[int, float] = {}
    for sp in splits:
        try:
            data = json.loads(sp.payload or "{}")
        except json.JSONDecodeError:
            continue
        for pid, bal, es_yo in _extraer_balances(data):
            if es_yo:
                agg[YO_PID] = agg.get(YO_PID, 0.0) + bal
            elif pid > 0:
                agg[pid] = agg.get(pid, 0.0) + bal
            # pid == 0 y no-yo: participante manual, se descarta.

    saldos: list[SaldoGlobalRow] = []
    for pid, bal in agg.items():
        if pid == YO_PID:
            nombre, color, emoji = yo_nombre, yo_color, yo_emoji
        else:
            info = info_personas.get(pid)
            if not info:
                continue
            nombre, color, emoji = info["nombre"], info["color"], info["emoji"]
        if abs(bal) < 0.5:
            signo = "ok"
        elif bal > 0:
            signo = "recibe"
        else:
            signo = "debe"
        sign_str = "" if bal >= 0 else "-"
        saldos.append(SaldoGlobalRow(
            persona_id=pid, nombre=nombre, color=color, emoji=emoji,
            balance=bal,
            balance_fmt=f"{sign_str}${abs(bal):,.0f}",
            balance_signo=signo,
            es_yo=(pid == YO_PID),
        ))
    # Orden: Yo primero, luego deudores, saldados, acreedores
    order_signo = {"debe": 0, "ok": 1, "recibe": 2}
    saldos.sort(key=lambda r: (
        0 if r.es_yo else 1,
        order_signo[r.balance_signo],
        -abs(r.balance),
    ))

    # Transferencias mínimas (greedy)
    transfers: list[TransferGlobalRow] = []
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
            transfers.append(TransferGlobalRow(
                de_idx=d.persona_id, de_nombre=d.nombre,
                de_emoji=d.emoji, de_color=d.color,
                a_idx=c.persona_id, a_nombre=c.nombre,
                a_emoji=c.emoji, a_color=c.color,
                monto=monto, monto_fmt=f"${monto:,.0f}",
            ))
            bal_arr[i_deb] += monto
            bal_arr[i_cre] -= monto
    return saldos, transfers


def compute_pairwise_debts(
    splits: Iterable[SplitCuenta],
    personas: Iterable[Persona],
    yo_color: str = "#a78bfa",
    yo_emoji: str = "\U0001F642",
    yo_nombre: str = "Yo",
) -> list[PairDebtRow]:
    """Para cada factura, atribuye proporcionalmente lo que cada deudor
    le debe a cada acreedor, y luego suma globalmente y netea por pares.

    Resultado: filas concretas «X le debe a Y: $Z» entre cualquier par,
    incluyendo otro→otro.
    """
    info_personas: dict[int, dict] = {
        (p.id or 0): {
            "nombre": p.nombre or "",
            "color": p.color or "#a78bfa",
            "emoji": p.emoji or "\U0001F464",
        }
        for p in personas
    }
    info_personas[YO_PID] = {
        "nombre": yo_nombre, "color": yo_color, "emoji": yo_emoji,
    }

    # Acumulador bruto: {(deudor_pid, acreedor_pid): monto}
    pair: dict[tuple[int, int], float] = {}

    for sp in splits:
        try:
            data = json.loads(sp.payload or "{}")
        except json.JSONDecodeError:
            continue
        # balances de la factura (uno por participante)
        bals = _extraer_balances(data)
        # Convertir a pid efectivo (Yo o pid>0); descartar manuales.
        agg_factura: dict[int, float] = {}
        for pid, bal, es_yo in bals:
            if es_yo:
                pid_eff = YO_PID
            elif pid > 0:
                pid_eff = pid
            else:
                continue
            agg_factura[pid_eff] = agg_factura.get(pid_eff, 0.0) + bal

        deudores = [(p, -b) for p, b in agg_factura.items() if b < -0.01]
        acreedores = [(p, b) for p, b in agg_factura.items() if b > 0.01]
        total_acr = sum(b for _, b in acreedores)
        if total_acr < 0.01 or not deudores:
            continue
        for d_pid, monto_debe in deudores:
            for a_pid, b in acreedores:
                share = monto_debe * (b / total_acr)
                if share < 0.01:
                    continue
                pair[(d_pid, a_pid)] = pair.get((d_pid, a_pid), 0.0) + share

    # Netear (A→B) contra (B→A)
    netos: dict[tuple[int, int], float] = {}
    seen: set[tuple[int, int]] = set()
    for (a, b), m in pair.items():
        if (a, b) in seen:
            continue
        m_ba = pair.get((b, a), 0.0)
        neto = m - m_ba
        seen.add((a, b))
        seen.add((b, a))
        if abs(neto) < 0.5:
            continue
        if neto > 0:
            netos[(a, b)] = neto
        else:
            netos[(b, a)] = -neto

    out: list[PairDebtRow] = []
    for (d_pid, a_pid), monto in netos.items():
        d_info = info_personas.get(d_pid)
        a_info = info_personas.get(a_pid)
        if not d_info or not a_info:
            continue
        out.append(PairDebtRow(
            de_idx=d_pid, de_nombre=d_info["nombre"],
            de_emoji=d_info["emoji"], de_color=d_info["color"],
            de_es_yo=(d_pid == YO_PID),
            a_idx=a_pid, a_nombre=a_info["nombre"],
            a_emoji=a_info["emoji"], a_color=a_info["color"],
            a_es_yo=(a_pid == YO_PID),
            monto=monto, monto_fmt=f"${monto:,.0f}",
            involucra_yo=(d_pid == YO_PID or a_pid == YO_PID),
        ))
    # Orden: primero los que NO me involucran (otro→otro), luego los míos,
    # cada bloque por monto descendente.
    out.sort(key=lambda r: (r.involucra_yo, -r.monto))
    return out
