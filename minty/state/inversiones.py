"""State Inversiones (CDTs)."""
from datetime import date, timedelta
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from minty.models import CDT
from minty.state._autosetters import auto_setters


class CDTRow(BaseModel):
    id: int
    entidad: str
    monto: float
    tasa_ea: float
    fecha_apertura: str
    plazo_dias: int
    fecha_vencimiento: str
    dias_restantes: int
    rendimiento_estimado: float
    notas: str


@auto_setters
class InversionesState(rx.State):
    rows: list[CDTRow] = []
    total_invertido: float = 0.0
    total_rendimiento: float = 0.0

    # Form
    form_open: bool = False
    form_entidad: str = ""
    form_monto: float = 0.0
    form_tasa: float = 0.0
    form_apertura: str = date.today().isoformat()
    form_plazo: int = 90
    form_notas: str = ""
    form_editing_id: Optional[int] = None
    form_msg: str = ""

    @rx.var
    def fecha_venc_preview(self) -> str:
        try:
            ini = date.fromisoformat(self.form_apertura)
            return (ini + timedelta(days=self.form_plazo)).isoformat()
        except Exception:
            return ""

    @rx.var
    def rendimiento_preview(self) -> float:
        # Aproximación simple: monto × (1 + tasa)^(dias/365) - monto
        if self.form_monto <= 0 or self.form_tasa <= 0:
            return 0.0
        r = self.form_tasa / 100
        return self.form_monto * ((1 + r) ** (self.form_plazo / 365) - 1)

    @rx.event
    def toggle_form(self):
        self.form_open = not self.form_open
        self.form_msg = ""
        if self.form_open:
            self.form_editing_id = None
            self.form_entidad = ""
            self.form_monto = 0.0
            self.form_tasa = 0.0
            self.form_notas = ""

    @rx.event
    async def load(self):
        hoy = date.today()
        with rx.session() as s:
            results = s.exec(
                sqlmodel.select(CDT).order_by(sqlmodel.desc(CDT.fecha_apertura))
            ).all()

        rows = []
        tot = 0.0
        tot_r = 0.0
        for c in results:
            dias_rest = (c.fecha_vencimiento - hoy).days
            rend = c.monto * ((1 + c.tasa_ea / 100) ** (c.plazo_dias / 365) - 1) if c.tasa_ea > 0 else 0
            rows.append(CDTRow(
                id=c.id, entidad=c.entidad, monto=c.monto, tasa_ea=c.tasa_ea,
                fecha_apertura=c.fecha_apertura.isoformat(),
                plazo_dias=c.plazo_dias,
                fecha_vencimiento=c.fecha_vencimiento.isoformat(),
                dias_restantes=dias_rest,
                rendimiento_estimado=rend,
                notas=c.notas or "",
            ))
            tot += c.monto
            tot_r += rend
        self.rows = rows
        self.total_invertido = tot
        self.total_rendimiento = tot_r

    @rx.event
    async def guardar(self):
        if not self.form_entidad.strip():
            self.form_msg = "⚠ La entidad es obligatoria."
            return
        if self.form_monto <= 0:
            self.form_msg = "⚠ El monto debe ser mayor a 0."
            return

        ap = date.fromisoformat(self.form_apertura)
        venc = ap + timedelta(days=self.form_plazo)

        with rx.session() as s:
            if self.form_editing_id:
                row = s.get(CDT, self.form_editing_id)
                if row:
                    row.entidad = self.form_entidad.strip()
                    row.monto = self.form_monto
                    row.tasa_ea = self.form_tasa
                    row.fecha_apertura = ap
                    row.plazo_dias = self.form_plazo
                    row.fecha_vencimiento = venc
                    row.notas = self.form_notas
                    s.add(row)
            else:
                s.add(CDT(
                    entidad=self.form_entidad.strip(),
                    monto=self.form_monto,
                    tasa_ea=self.form_tasa,
                    fecha_apertura=ap,
                    plazo_dias=self.form_plazo,
                    fecha_vencimiento=venc,
                    notas=self.form_notas,
                ))
            s.commit()
        self.form_open = False
        self.form_editing_id = None
        await self.load()

    @rx.event
    async def editar(self, rid: int):
        with rx.session() as s:
            row = s.get(CDT, rid)
            if row:
                self.form_editing_id = rid
                self.form_entidad = row.entidad
                self.form_monto = row.monto
                self.form_tasa = row.tasa_ea
                self.form_apertura = row.fecha_apertura.isoformat()
                self.form_plazo = row.plazo_dias
                self.form_notas = row.notas or ""
                self.form_open = True

    @rx.event
    async def eliminar(self, rid: int):
        with rx.session() as s:
            row = s.get(CDT, rid)
            if row:
                s.delete(row)
                s.commit()
        await self.load()
