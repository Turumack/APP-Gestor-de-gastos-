"""State del Resumen / Dashboard."""
from datetime import date
import reflex as rx
import sqlmodel

from cuentas_pro.models import Ingreso, Gasto
from cuentas_pro.finance import calculate_net_income, COLOR_CATEGORIA
from cuentas_pro.state.periodo import PeriodoState


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

        # Ingresos
        total_ing = sum(
            max(i.ingreso_real_cuenta,
                calculate_net_income(i.salario_base, i.aux_transporte, i.otros))
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
