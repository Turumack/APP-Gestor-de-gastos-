"""State para presupuestos mensuales por categoría."""
from datetime import date
import reflex as rx
import sqlmodel
from pydantic import BaseModel
from typing import Optional

from minty.models import Presupuesto, Gasto
from minty.finance import CATEGORIAS_GASTO, COLOR_CATEGORIA
from minty.state.periodo import PeriodoState
from minty.state._autosetters import auto_setters


class PresupuestoRow(BaseModel):
    id: int
    categoria: str
    monto: float
    monto_fmt: str
    gastado: float
    gastado_fmt: str
    pct_uso: float
    pct_uso_fmt: str
    alerta_pct: int
    estado: str           # "ok" | "alerta" | "excedido"
    color: str
    notas: str


@auto_setters
class PresupuestosState(rx.State):
    rows: list[PresupuestoRow] = []
    total_presupuestado: float = 0.0
    total_gastado: float = 0.0

    # Form
    form_open: bool = False
    form_categoria: str = "Otros"
    form_monto: float = 0.0
    form_alerta_pct: int = 90
    form_notas: str = ""
    form_editing_id: Optional[int] = None
    form_msg: str = ""

    @rx.var
    def categorias(self) -> list[str]:
        return CATEGORIAS_GASTO

    @rx.var(cache=True)
    def hay_alertas(self) -> bool:
        return any(r.estado in ("alerta", "excedido") for r in self.rows)

    @rx.event
    async def load(self):
        per = await self.get_state(PeriodoState)
        ini = date.fromisoformat(per.fecha_inicio)
        fin = date.fromisoformat(per.fecha_fin)

        with rx.session() as s:
            presupuestos = s.exec(
                sqlmodel.select(Presupuesto).where(
                    Presupuesto.anio == per.anio,
                    Presupuesto.mes == per.mes,
                )
            ).all()
            gastos = s.exec(
                sqlmodel.select(Gasto).where(
                    Gasto.fecha >= ini, Gasto.fecha < fin,
                )
            ).all()

        gastado_por_cat: dict[str, float] = {}
        for g in gastos:
            gastado_por_cat[g.categoria] = gastado_por_cat.get(g.categoria, 0.0) + (g.monto or 0.0)

        rows: list[PresupuestoRow] = []
        total_p = 0.0
        for p in presupuestos:
            gastado = gastado_por_cat.get(p.categoria, 0.0)
            pct = (gastado / p.monto * 100) if p.monto > 0 else 0.0
            if pct >= 100:
                estado = "excedido"
            elif pct >= p.alerta_pct:
                estado = "alerta"
            else:
                estado = "ok"
            rows.append(PresupuestoRow(
                id=p.id,
                categoria=p.categoria,
                monto=p.monto,
                monto_fmt=f"${p.monto:,.0f}",
                gastado=gastado,
                gastado_fmt=f"${gastado:,.0f}",
                pct_uso=pct,
                pct_uso_fmt=f"{pct:.1f}%",
                alerta_pct=p.alerta_pct,
                estado=estado,
                color=COLOR_CATEGORIA.get(p.categoria, "#94a3b8"),
                notas=p.notas or "",
            ))
            total_p += p.monto

        rows.sort(key=lambda r: -r.pct_uso)
        self.rows = rows
        self.total_presupuestado = total_p
        self.total_gastado = sum(gastado_por_cat.values())

    @rx.event
    def toggle_form(self):
        self.form_open = not self.form_open
        self.form_msg = ""
        if self.form_open:
            self.form_editing_id = None
            self.form_categoria = "Otros"
            self.form_monto = 0.0
            self.form_alerta_pct = 90
            self.form_notas = ""

    @rx.event
    async def guardar(self):
        if self.form_monto <= 0:
            self.form_msg = "⚠ El monto debe ser mayor a 0."
            return
        if not (0 < self.form_alerta_pct <= 100):
            self.form_msg = "⚠ El % de alerta debe estar entre 1 y 100."
            return

        per = await self.get_state(PeriodoState)
        with rx.session() as s:
            if self.form_editing_id:
                row = s.get(Presupuesto, self.form_editing_id)
                if row:
                    row.categoria = self.form_categoria
                    row.monto = float(self.form_monto)
                    row.alerta_pct = int(self.form_alerta_pct)
                    row.notas = self.form_notas
                    s.add(row)
            else:
                # Evitar duplicados: misma categoría + año + mes.
                existente = s.exec(
                    sqlmodel.select(Presupuesto).where(
                        Presupuesto.anio == per.anio,
                        Presupuesto.mes == per.mes,
                        Presupuesto.categoria == self.form_categoria,
                    )
                ).first()
                if existente:
                    self.form_msg = (
                        f"⚠ Ya existe un presupuesto para {self.form_categoria} "
                        "en este periodo. Edítalo en su lugar."
                    )
                    return
                s.add(Presupuesto(
                    categoria=self.form_categoria,
                    anio=per.anio,
                    mes=per.mes,
                    monto=float(self.form_monto),
                    alerta_pct=int(self.form_alerta_pct),
                    notas=self.form_notas,
                ))
            s.commit()
        self.form_open = False
        self.form_editing_id = None
        await self.load()

    @rx.event
    async def editar(self, rid: int):
        with rx.session() as s:
            row = s.get(Presupuesto, rid)
            if row:
                self.form_editing_id = rid
                self.form_categoria = row.categoria
                self.form_monto = row.monto
                self.form_alerta_pct = row.alerta_pct
                self.form_notas = row.notas or ""
                self.form_open = True

    @rx.event
    async def eliminar(self, rid: int):
        with rx.session() as s:
            row = s.get(Presupuesto, rid)
            if row:
                s.delete(row)
                s.commit()
        await self.load()
