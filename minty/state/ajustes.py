"""State de Ajustes manuales de saldo de caja."""
from datetime import date
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from minty.models import Ajuste, Caja
from minty.state.periodo import PeriodoState
from minty.state._autosetters import auto_setters


class AjusteRow(BaseModel):
    id: int
    fecha: str
    caja_id: int
    caja_nombre: str
    monto: float
    monto_abs_fmt: str
    monto_signo_fmt: str  # "+$10.000" o "-$5.000"
    descripcion: str
    positivo: bool


@auto_setters
class AjustesState(rx.State):
    rows: list[AjusteRow] = []
    cajas_opts: list[dict] = []
    total_positivos: float = 0.0
    total_negativos: float = 0.0
    total_positivos_fmt: str = "$0"
    total_negativos_fmt: str = "$0"
    neto_fmt: str = "$0"
    neto_positivo: bool = True
    rango_label: str = ""

    # Form
    form_open: bool = False
    form_fecha: str = date.today().isoformat()
    form_caja_id: int = 0
    form_modo: str = "sumar"          # "sumar" | "restar"
    form_monto: float = 0.0           # siempre positivo en el form
    form_descripcion: str = ""
    form_editing_id: Optional[int] = None
    form_msg: str = ""

    @rx.event
    async def load(self):
        per = await self.get_state(PeriodoState)
        ini = date.fromisoformat(per.fecha_inicio)
        fin = date.fromisoformat(per.fecha_fin)
        self.rango_label = per.periodo_label

        with rx.session() as s:
            ajustes = s.exec(
                sqlmodel.select(Ajuste).where(
                    Ajuste.fecha >= ini, Ajuste.fecha < fin,
                ).order_by(sqlmodel.desc(Ajuste.fecha))
            ).all()
            cajas = s.exec(
                sqlmodel.select(Caja).where(
                    Caja.activa == True  # noqa: E712
                ).order_by(Caja.orden, Caja.id)
            ).all()

        cajas_by_id = {c.id: c for c in cajas}
        self.cajas_opts = [
            {"id": c.id,
             "etiqueta": (f"{c.nombre} · {c.entidad}" if c.entidad else c.nombre)}
            for c in cajas
        ]
        if self.form_caja_id == 0 and cajas:
            self.form_caja_id = cajas[0].id

        rows: list[AjusteRow] = []
        pos = 0.0
        neg = 0.0
        for a in ajustes:
            m = float(a.monto or 0)
            if m >= 0:
                pos += m
            else:
                neg += -m
            caja = cajas_by_id.get(a.caja_id)
            signo = "+" if m >= 0 else "-"
            rows.append(AjusteRow(
                id=a.id or 0,
                fecha=a.fecha.isoformat(),
                caja_id=a.caja_id,
                caja_nombre=caja.nombre if caja else "(caja eliminada)",
                monto=m,
                monto_abs_fmt=f"${abs(m):,.0f}",
                monto_signo_fmt=f"{signo}${abs(m):,.0f}",
                descripcion=a.descripcion or "",
                positivo=(m >= 0),
            ))

        self.rows = rows
        self.total_positivos = pos
        self.total_negativos = neg
        self.total_positivos_fmt = f"${pos:,.0f}"
        self.total_negativos_fmt = f"${neg:,.0f}"
        neto = pos - neg
        self.neto_positivo = neto >= 0
        signo = "" if neto >= 0 else "-"
        self.neto_fmt = f"{signo}${abs(neto):,.0f}"

    # ── Form ──
    @rx.event
    def toggle_form(self):
        self.form_open = not self.form_open
        self.form_msg = ""
        if self.form_open and not self.form_editing_id:
            self.form_fecha = date.today().isoformat()
            self.form_monto = 0.0
            self.form_modo = "sumar"
            self.form_descripcion = ""

    @rx.event
    def set_form_caja(self, val: str):
        try:
            self.form_caja_id = int(val)
        except (TypeError, ValueError):
            self.form_caja_id = 0

    @rx.event
    async def editar(self, rid: int):
        with rx.session() as s:
            a = s.get(Ajuste, rid)
            if not a:
                return
            self.form_editing_id = a.id
            self.form_fecha = a.fecha.isoformat()
            self.form_caja_id = a.caja_id
            monto = float(a.monto or 0)
            self.form_modo = "sumar" if monto >= 0 else "restar"
            self.form_monto = abs(monto)
            self.form_descripcion = a.descripcion or ""
            self.form_open = True
            self.form_msg = "✏ Editando ajuste."

    @rx.event
    def cancelar(self):
        self.form_open = False
        self.form_editing_id = None
        self.form_msg = ""

    @rx.event
    async def guardar(self):
        if self.form_monto <= 0:
            self.form_msg = "⚠ El monto debe ser mayor a 0."
            return
        if not self.form_caja_id:
            self.form_msg = "⚠ Selecciona una caja."
            return
        try:
            f = date.fromisoformat(self.form_fecha)
        except ValueError:
            self.form_msg = "⚠ Fecha inválida."
            return

        monto_firmado = float(self.form_monto)
        if self.form_modo == "restar":
            monto_firmado = -monto_firmado

        with rx.session() as s:
            if self.form_editing_id:
                a = s.get(Ajuste, self.form_editing_id)
                if not a:
                    self.form_msg = "⚠ Ajuste no encontrado."
                    return
                a.fecha = f
                a.caja_id = int(self.form_caja_id)
                a.monto = monto_firmado
                a.descripcion = self.form_descripcion.strip()
                s.add(a)
            else:
                s.add(Ajuste(
                    fecha=f,
                    caja_id=int(self.form_caja_id),
                    monto=monto_firmado,
                    descripcion=self.form_descripcion.strip(),
                ))
            s.commit()

        self.form_open = False
        self.form_editing_id = None
        await self.load()

    @rx.event
    async def eliminar(self, rid: int):
        with rx.session() as s:
            a = s.get(Ajuste, rid)
            if a:
                s.delete(a)
                s.commit()
        await self.load()
