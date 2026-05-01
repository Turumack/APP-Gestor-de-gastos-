"""State del Resumen / Dashboard."""
from datetime import date
import reflex as rx
import sqlmodel

from minty.models import Ingreso, Gasto, Presupuesto
from minty.finance import calculate_net_income, COLOR_CATEGORIA
from minty.state.periodo import PeriodoState


class ResumenState(rx.State):
    total_ingresos: float = 0.0
    total_gastos: float = 0.0
    balance: float = 0.0
    pct_ahorro_real: float = 0.0

    # Gráficos
    gastos_por_categoria: list[dict] = []    # [{nombre, total, color}]
    gastos_por_dia: list[dict] = []          # [{dia, total}] para line chart

    # Transacciones recientes
    recientes: list[dict] = []  # [{tipo, desc, monto, fecha, color}]

    # Alertas de presupuesto del periodo
    alertas_presupuesto: list[dict] = []  # [{categoria, pct, estado, color, gastado_fmt, monto_fmt}]

    @rx.event
    async def load(self):
        per = await self.get_state(PeriodoState)
        ini = date.fromisoformat(per.fecha_inicio)
        fin = date.fromisoformat(per.fecha_fin)

        with rx.session() as s:
            ings = s.exec(
                sqlmodel.select(Ingreso).where(Ingreso.fecha >= ini, Ingreso.fecha < fin)
            ).all()
            gts = s.exec(
                sqlmodel.select(Gasto).where(Gasto.fecha >= ini, Gasto.fecha < fin)
                .order_by(sqlmodel.desc(Gasto.fecha))
            ).all()

        # Ingresos (usar el mayor entre el ingreso real declarado y el neto calculado;
        # `ingreso_real_cuenta` puede ser None, por eso se normaliza a 0.0)
        total_ing = sum(
            max(
                i.ingreso_real_cuenta or 0.0,
                calculate_net_income(i.salario_base, i.aux_transporte, i.otros),
            )
            for i in ings
        ) if ings else 0.0

        # Gastos
        total_g = sum(g.monto for g in gts)

        por_cat: dict[str, float] = {}
        por_dia: dict[str, float] = {}
        for g in gts:
            por_cat[g.categoria] = por_cat.get(g.categoria, 0) + g.monto
            key = g.fecha.isoformat()
            por_dia[key] = por_dia.get(key, 0) + g.monto

        self.total_ingresos = total_ing
        self.total_gastos = total_g
        self.balance = total_ing - total_g
        self.pct_ahorro_real = (self.balance / total_ing * 100) if total_ing > 0 else 0.0

        self.gastos_por_categoria = [
            {"name": c, "value": v, "fill": COLOR_CATEGORIA.get(c, "#94a3b8")}
            for c, v in sorted(por_cat.items(), key=lambda x: -x[1])
        ]

        # Serie diaria acumulada
        fechas = sorted(por_dia.keys())
        acum = 0.0
        self.gastos_por_dia = []
        for f in fechas:
            acum += por_dia[f]
            self.gastos_por_dia.append({
                "dia": f[-2:],
                "gasto": por_dia[f],
                "acumulado": acum,
            })

        # Recientes (últimos 8 gastos)
        self.recientes = [
            {
                "tipo": "Gasto",
                "desc": g.descripcion,
                "monto": g.monto,
                "fecha": g.fecha.isoformat(),
                "categoria": g.categoria,
                "color": COLOR_CATEGORIA.get(g.categoria, "#94a3b8"),
            }
            for g in gts[:8]
        ]

        # Alertas de presupuesto: categorías con uso ≥ alerta_pct
        with rx.session() as s:
            presupuestos = s.exec(
                sqlmodel.select(Presupuesto).where(
                    Presupuesto.anio == per.anio,
                    Presupuesto.mes == per.mes,
                )
            ).all()
        alertas: list[dict] = []
        for p in presupuestos:
            gastado = por_cat.get(p.categoria, 0.0)
            pct = (gastado / p.monto * 100) if p.monto > 0 else 0.0
            if pct < p.alerta_pct:
                continue
            estado = "excedido" if pct >= 100 else "alerta"
            alertas.append({
                "categoria": p.categoria,
                "pct": pct,
                "pct_fmt": f"{pct:.0f}%",
                "estado": estado,
                "gastado_fmt": f"${gastado:,.0f}",
                "monto_fmt": f"${p.monto:,.0f}",
                "color": COLOR_CATEGORIA.get(p.categoria, "#94a3b8"),
            })
        alertas.sort(key=lambda a: -a["pct"])
        self.alertas_presupuesto = alertas
