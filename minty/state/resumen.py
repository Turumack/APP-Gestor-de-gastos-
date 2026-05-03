"""State del Resumen / Dashboard."""
from datetime import date
import reflex as rx
import sqlmodel

from minty.models import Ingreso, Gasto, Presupuesto, Caja, Movimiento
from minty.finance import calculate_net_income, COLOR_CATEGORIA
from minty.state.periodo import PeriodoState


class ResumenState(rx.State):
    total_ingresos: float = 0.0
    total_gastos: float = 0.0
    balance: float = 0.0
    pct_ahorro_real: float = 0.0
    # Crédito (acumulado de TODAS las TC, no solo del periodo)
    tc_deuda: float = 0.0
    tc_deuda_fmt: str = "$0"
    tc_cupo_total: float = 0.0
    tc_cupo_total_fmt: str = "$0"
    tc_disponible: float = 0.0
    tc_disponible_fmt: str = "$0"
    tc_balance_fmt: str = "$0"  # alias firmado de la deuda (negativo)
    tiene_tc: bool = False
    # Δ Patrimonio = patrimonio fin − patrimonio inicio (excluye TC)
    delta_patrimonio: float = 0.0
    delta_patrimonio_fmt: str = "$0"
    delta_patrimonio_positivo: bool = True

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
            # IDs de cajas tipo "tarjeta_credito" para excluir sus gastos del resumen.
            tc_ids = set(s.exec(
                sqlmodel.select(Caja.id).where(Caja.tipo == "tarjeta_credito")
            ).all())
            gts_all = s.exec(
                sqlmodel.select(Gasto).where(Gasto.fecha >= ini, Gasto.fecha < fin)
                .order_by(sqlmodel.desc(Gasto.fecha))
            ).all()
            gts = [g for g in gts_all if g.caja_id not in tc_ids]

            # Deuda en cajas TC al cierre del periodo: gastos hasta < fin
            # menos pagos hasta < fin. Así si navegas meses pasados ves la
            # deuda real de ese momento, no la de hoy.
            tc_cajas = s.exec(
                sqlmodel.select(Caja).where(
                    Caja.tipo == "tarjeta_credito",
                    Caja.activa == True,  # noqa: E712
                )
            ).all()
            deuda_total = 0.0
            cupo_total = 0.0
            for tc in tc_cajas:
                cupo_total += float(tc.cupo_total_cop or 0)
                gastos_tc = s.exec(
                    sqlmodel.select(Gasto).where(
                        Gasto.caja_id == tc.id, Gasto.fecha < fin,
                    )
                ).all()
                deuda_total += sum(float(g.monto or 0) for g in gastos_tc)
                # Pagos a la TC (transferencias hacia ella) reducen la deuda.
                from minty.models import Movimiento
                movs = s.exec(
                    sqlmodel.select(Movimiento).where(
                        Movimiento.caja_destino_id == tc.id,
                        Movimiento.fecha < fin,
                    )
                ).all()
                deuda_total -= sum(float(m.monto or 0) for m in movs)
            deuda_total = max(0.0, deuda_total)
            disponible = max(0.0, cupo_total - deuda_total)

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
        # pct_ahorro real se calcula más abajo con delta_patrimonio + categoría "Ahorro"

        # Bloque crédito (acumulado total, no por periodo)
        self.tc_deuda = deuda_total
        self.tc_deuda_fmt = f"${deuda_total:,.0f}"
        self.tc_cupo_total = cupo_total
        self.tc_cupo_total_fmt = f"${cupo_total:,.0f}"
        self.tc_disponible = disponible
        self.tc_disponible_fmt = f"${disponible:,.0f}"
        self.tc_balance_fmt = f"$-{deuda_total:,.0f}" if deuda_total > 0 else "$0"
        self.tiene_tc = bool(tc_cajas)

        # Δ Patrimonio = saldo real de cajas no-TC al fin − al inicio.
        # Refleja exactamente cuánta plata tienes hoy en cuentas/efectivo
        # comparado con el inicio del periodo. Pagos a TC SÍ restan
        # (ese dinero salió de verdad de tu bolsillo).
        with rx.session() as s:
            cajas_no_tc = s.exec(
                sqlmodel.select(Caja).where(
                    Caja.tipo != "tarjeta_credito",
                    Caja.activa == True,  # noqa: E712
                )
            ).all()

            def _patrimonio_a(fecha):
                total = 0.0
                for c in cajas_no_tc:
                    saldo = float(c.saldo_inicial or 0)
                    ings_c = s.exec(
                        sqlmodel.select(Ingreso).where(
                            Ingreso.caja_id == c.id, Ingreso.fecha < fecha,
                        )
                    ).all()
                    for i in ings_c:
                        saldo += max(
                            float(i.ingreso_real_cuenta or 0),
                            float(calculate_net_income(
                                i.salario_base or 0,
                                i.aux_transporte or 0,
                                i.otros or 0,
                            )),
                        )
                    gts_c = s.exec(
                        sqlmodel.select(Gasto).where(
                            Gasto.caja_id == c.id, Gasto.fecha < fecha,
                        )
                    ).all()
                    saldo -= sum(float(g.monto or 0) for g in gts_c)
                    movs_in = s.exec(
                        sqlmodel.select(Movimiento).where(
                            Movimiento.caja_destino_id == c.id, Movimiento.fecha < fecha,
                        )
                    ).all()
                    saldo += sum(float(m.monto or 0) for m in movs_in)
                    movs_out = s.exec(
                        sqlmodel.select(Movimiento).where(
                            Movimiento.caja_origen_id == c.id, Movimiento.fecha < fecha,
                        )
                    ).all()
                    saldo -= sum(
                        float(m.monto or 0) + float(m.costo_4x1000 or 0)
                        for m in movs_out
                    )
                    total += saldo
                return total

            patrimonio_ini = _patrimonio_a(ini)
            patrimonio_fin = _patrimonio_a(fin)
            delta = patrimonio_fin - patrimonio_ini
            self.delta_patrimonio = delta
            signo = "" if delta >= 0 else "-"
            self.delta_patrimonio_fmt = f"{signo}${abs(delta):,.0f}"
            self.delta_patrimonio_positivo = delta >= 0

        # % Ahorro real = (Δ patrimonio + gastos categoría "Ahorro") / ingresos
        ahorro_categoria = por_cat.get("Ahorro", 0.0)
        ahorro_efectivo = self.delta_patrimonio + ahorro_categoria
        self.pct_ahorro_real = (
            (ahorro_efectivo / total_ing * 100) if total_ing > 0 else 0.0
        )

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
