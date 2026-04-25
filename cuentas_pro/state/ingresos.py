"""State de la p\u00e1gina Ingresos."""
from datetime import date, datetime
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from cuentas_pro.models import Ingreso, Caja
from cuentas_pro.finance import (
    calcular_extras, valor_hora_ordinaria, calculate_net_income,
    RECARGOS, RECARGO_LABELS, HORAS_SEMANA_LEGAL, horas_mes_desde_semana,
)
from cuentas_pro.state.periodo import PeriodoState
from cuentas_pro.state._autosetters import auto_setters


class IngresoRow(BaseModel):
    id: int
    fecha: str
    descripcion: str
    salario_base: float
    aux_transporte: float
    otros: float
    pct_ahorro_objetivo: int
    ingreso_real_cuenta: float
    caja_nombre: str
    teorico: float
    real: float
    diff_pct: float


@auto_setters
class IngresosState(rx.State):
    # Listado del mes
    rows: list[IngresoRow] = []
    total_teorico: float = 0.0
    total_real: float = 0.0

    # ── Tab RÁPIDO ──
    simple_desc: str = ""
    simple_fecha: str = date.today().isoformat()
    simple_salario: float = 0.0
    simple_aux: float = 0.0
    simple_otros: float = 0.0
    simple_meta: int = 10
    simple_real: float = 0.0
    simple_caja_id: int = 0
    simple_msg: str = ""

    # ── Tab CALCULADORA ──
    calc_desc: str = "Salario"
    calc_fecha: str = date.today().isoformat()
    calc_horas_semana: float = float(HORAS_SEMANA_LEGAL)
    calc_salario: float = 0.0
    calc_aux: float = 0.0
    h_ext_d: float = 0.0
    h_ext_n: float = 0.0
    h_rec_n: float = 0.0
    h_dom_d: float = 0.0
    h_dom_n: float = 0.0
    h_ext_dom_d: float = 0.0
    h_ext_dom_n: float = 0.0
    h_otros_bonos: float = 0.0
    calc_meta: int = 10
    calc_real: float = 0.0
    calc_caja_id: int = 0
    calc_msg: str = ""

    # Selector de cajas disponibles
    cajas_opts: list[dict] = []

    # Edición en línea
    editing_id: Optional[int] = None

    # ─── Derivados para el preview ───
    @rx.var
    def calc_horas_mes(self) -> float:
        return horas_mes_desde_semana(self.calc_horas_semana)

    @rx.var
    def valor_hora(self) -> float:
        return valor_hora_ordinaria(self.calc_salario, self.calc_horas_mes)

    @rx.var
    def total_extras(self) -> float:
        horas = {
            "extra_diurna": self.h_ext_d,
            "extra_nocturna": self.h_ext_n,
            "recargo_nocturno": self.h_rec_n,
            "dominical_diurna": self.h_dom_d,
            "dominical_nocturna": self.h_dom_n,
            "extra_dominical_diurna": self.h_ext_dom_d,
            "extra_dominical_nocturna": self.h_ext_dom_n,
        }
        return calcular_extras(self.calc_salario, horas, self.calc_horas_mes)["total"]

    @rx.var
    def calc_neto(self) -> float:
        return calculate_net_income(
            self.calc_salario, self.calc_aux, self.total_extras + self.h_otros_bonos,
        )

    @rx.var
    def desglose_extras(self) -> list[dict]:
        """Detalle de extras con horas > 0 para mostrar en UI."""
        horas = {
            "extra_diurna": self.h_ext_d,
            "extra_nocturna": self.h_ext_n,
            "recargo_nocturno": self.h_rec_n,
            "dominical_diurna": self.h_dom_d,
            "dominical_nocturna": self.h_dom_n,
            "extra_dominical_diurna": self.h_ext_dom_d,
            "extra_dominical_nocturna": self.h_ext_dom_n,
        }
        det = calcular_extras(self.calc_salario, horas, self.calc_horas_mes)
        items = []
        for k in RECARGOS.keys():
            h = horas[k]
            if h > 0:
                items.append({
                    "label": RECARGO_LABELS[k],
                    "horas": h,
                    "monto": det[k],
                })
        return items

    # ─── Carga ───
    @rx.event
    async def load(self):
        per = await self.get_state(PeriodoState)
        ini = date.fromisoformat(per.fecha_inicio)
        fin = date.fromisoformat(per.fecha_fin)
        with rx.session() as s:
            stmt = (
                sqlmodel.select(Ingreso)
                .where(Ingreso.fecha >= ini, Ingreso.fecha < fin)
                .order_by(sqlmodel.desc(Ingreso.fecha))
            )
            results = s.exec(stmt).all()
            cajas_all = s.exec(
                sqlmodel.select(Caja).where(Caja.activa == True).order_by(Caja.orden, Caja.id)
            ).all()

        cajas_by_id = {c.id: c for c in cajas_all}
        self.cajas_opts = [
            {
                "id": c.id,
                "nombre": c.nombre,
                "etiqueta": f"{c.nombre} · {c.entidad}" if c.entidad else c.nombre,
            }
            for c in cajas_all
        ]

        rows: list[IngresoRow] = []
        tot_t = 0.0
        tot_r = 0.0
        for r in results:
            teo = calculate_net_income(r.salario_base, r.aux_transporte, r.otros)
            real = float(r.ingreso_real_cuenta or 0)
            diff_pct = ((real - teo) / teo * 100) if (teo > 0 and real > 0) else 0.0
            caja = cajas_by_id.get(r.caja_id) if r.caja_id else None
            rows.append(IngresoRow(
                id=r.id, fecha=r.fecha.isoformat(), descripcion=r.descripcion,
                salario_base=r.salario_base, aux_transporte=r.aux_transporte,
                otros=r.otros, pct_ahorro_objetivo=r.pct_ahorro_objetivo,
                ingreso_real_cuenta=real,
                caja_nombre=(caja.nombre if caja else ""),
                teorico=teo, real=real, diff_pct=diff_pct,
            ))
            tot_t += teo
            tot_r += real
        self.rows = rows
        self.total_teorico = tot_t
        self.total_real = tot_r

    # ─── Guardado SIMPLE ───
    @rx.event
    async def guardar_simple(self):
        if not self.simple_desc.strip():
            self.simple_msg = "⚠ La descripción es obligatoria."
            return
        with rx.session() as s:
            s.add(Ingreso(
                fecha=date.fromisoformat(self.simple_fecha),
                descripcion=self.simple_desc.strip(),
                salario_base=self.simple_salario,
                aux_transporte=self.simple_aux,
                otros=self.simple_otros,
                pct_ahorro_objetivo=self.simple_meta,
                ingreso_real_cuenta=self.simple_real,
                caja_id=self.simple_caja_id if self.simple_caja_id > 0 else None,
            ))
            s.commit()
        self.simple_desc = ""
        self.simple_salario = 0.0
        self.simple_aux = 0.0
        self.simple_otros = 0.0
        self.simple_real = 0.0
        self.simple_caja_id = 0
        self.simple_msg = "✅ Ingreso registrado."
        await self.load()

    # ─── Guardado CALCULADORA ───
    @rx.event
    async def guardar_calc(self):
        if self.calc_salario <= 0:
            self.calc_msg = "⚠ Debes ingresar al menos el salario base."
            return
        otros_total = self.total_extras + self.h_otros_bonos
        with rx.session() as s:
            s.add(Ingreso(
                fecha=date.fromisoformat(self.calc_fecha),
                descripcion=self.calc_desc.strip() or "Salario",
                salario_base=self.calc_salario,
                aux_transporte=self.calc_aux,
                otros=otros_total,
                pct_ahorro_objetivo=self.calc_meta,
                ingreso_real_cuenta=self.calc_real,
                caja_id=self.calc_caja_id if self.calc_caja_id > 0 else None,
            ))
            s.commit()
        self.calc_msg = f"✅ Ingreso registrado · Neto ${self.calc_neto:,.0f}"
        self.h_ext_d = 0; self.h_ext_n = 0; self.h_rec_n = 0
        self.h_dom_d = 0; self.h_dom_n = 0
        self.h_ext_dom_d = 0; self.h_ext_dom_n = 0
        self.h_otros_bonos = 0; self.calc_real = 0; self.calc_caja_id = 0
        await self.load()

    # ─── Eliminar ───
    @rx.event
    async def eliminar(self, rid: int):
        with rx.session() as s:
            row = s.get(Ingreso, rid)
            if row:
                s.delete(row)
                s.commit()
        await self.load()

    # ─── Refrescar cuando cambia el mes ───
    @rx.event
    async def refrescar(self):
        await self.load()
