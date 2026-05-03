"""State de Cajas (cuentas, tarjetas, efectivo) y Movimientos internos."""
from datetime import date
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from minty.models import Caja, Movimiento, Gasto, Ingreso
from minty.finance import (
    TIPOS_CAJA,
    TIPO_CAJA_LABEL,
    calcular_4x1000,
    calculate_net_income,
)
from minty.state._autosetters import auto_setters


class CajaRow(BaseModel):
    id: int
    nombre: str
    tipo: str
    tipo_label: str
    entidad: str
    exento_4x1000: bool
    saldo_inicial: float
    saldo_actual: float
    saldo_actual_fmt: str
    faltante_cero: float
    faltante_cero_fmt: str
    gasto_periodo: float
    gasto_periodo_fmt: str
    color: str
    orden: int
    activa: bool
    notas: str
    # ── Campos TC (sólo relevantes si tipo == "tarjeta_credito") ──
    es_tc: bool = False
    cupo_total_cop: float = 0.0
    cupo_total_fmt: str = "$0"
    deuda_cop: float = 0.0
    deuda_cop_fmt: str = "$0"
    cupo_disponible: float = 0.0
    cupo_disponible_fmt: str = "$0"
    pct_uso: float = 0.0
    pct_uso_fmt: str = "0%"
    interes_mensual_compras: float = 0.0
    interes_ea_compras: float = 0.0
    interes_mensual_avances: float = 0.0
    interes_ea_avances: float = 0.0
    cuota_manejo: float = 0.0
    cuota_manejo_fmt: str = "$0"
    dia_cobro_cuota: int = 1
    dia_corte: int = 1
    dia_pago: int = 1
    trm_tc: float = 0.0
    trm_tc_fmt: str = "$0"


class MovimientoRow(BaseModel):
    id: int
    fecha: str
    origen: str
    destino: str
    monto: float
    monto_fmt: str
    costo_4x1000: float
    costo_fmt: str
    descripcion: str


@auto_setters
class CajasState(rx.State):
    rows: list[CajaRow] = []
    movimientos: list[MovimientoRow] = []
    total_patrimonio: float = 0.0
    total_fmt: str = "$0"
    # Totales TC agregados (excluidos del patrimonio)
    total_deuda_tc: float = 0.0
    total_deuda_tc_fmt: str = "$0"
    total_cupo_tc: float = 0.0
    total_cupo_tc_fmt: str = "$0"
    total_disponible_tc: float = 0.0
    total_disponible_tc_fmt: str = "$0"

    # Form caja
    form_open: bool = False
    form_editing_id: Optional[int] = None
    form_nombre: str = ""
    form_tipo: str = "cuenta"
    form_entidad: str = ""
    form_exento_4x1000: bool = False
    form_saldo_inicial: float = 0.0
    form_color: str = "#a78bfa"
    form_notas: str = ""
    form_msg: str = ""
    # Form caja — campos TC
    form_cupo_total_cop: float = 0.0
    form_interes_mensual_compras: float = 0.0
    form_interes_ea_compras: float = 0.0
    form_interes_mensual_avances: float = 0.0
    form_interes_ea_avances: float = 0.0
    form_cuota_manejo: float = 0.0
    form_dia_cobro_cuota: int = 1
    form_dia_corte: int = 1
    form_usa_dos_cortes: bool = False
    form_dia_corte_2: int = 15
    form_dia_pago: int = 1
    form_trm_tc: float = 0.0

    # Form deuda directa (carga manual a TC sin pasar por gastos.py)
    deuda_open: bool = False
    deuda_caja_id: int = 0
    deuda_caja_nombre: str = ""
    deuda_fecha: str = date.today().isoformat()
    deuda_desc: str = ""
    deuda_moneda: str = "COP"        # "COP" | "USD"
    deuda_monto_cop: float = 0.0     # si moneda=COP: monto directo; si USD: convertido con trm_tc
    deuda_monto_usd: float = 0.0     # si moneda=USD
    deuda_trm_tc_actual: float = 0.0 # snapshot al abrir el modal (informativo)
    deuda_msg: str = ""

    # Form movimiento
    mov_open: bool = False
    mov_fecha: str = date.today().isoformat()
    mov_origen_id: int = 0
    mov_destino_id: int = 0
    mov_monto: float = 0.0
    mov_desc: str = ""
    mov_msg: str = ""
    auto_origen_preferido_id: int = 0

    @rx.var
    def tipos_opciones(self) -> list[str]:
        return [TIPO_CAJA_LABEL[t] for t in TIPOS_CAJA]

    @rx.var
    def cajas_opciones(self) -> list[str]:
        """Para selectores: lista de 'id::nombre (entidad)'."""
        return [f"{r.id}::{r.nombre}" for r in self.rows if r.activa]

    @rx.event
    async def load(self):
        from minty.state.periodo import PeriodoState

        per = await self.get_state(PeriodoState)
        ini = date.fromisoformat(per.fecha_inicio)
        fin = date.fromisoformat(per.fecha_fin)

        # Antes de calcular saldos: cobro automático de cuotas de manejo
        # (idempotente por mes mediante caja.ultimo_cobro_cuota = "YYYY-MM").
        self._cobrar_cuotas_manejo_si_corresponde()

        with rx.session() as s:
            cajas = s.exec(
                sqlmodel.select(Caja).where(Caja.activa == True).order_by(Caja.orden, Caja.id)  # noqa: E712
            ).all()

            # Proyección al cierre del período seleccionado:
            # saldo_inicial + ingresos(<=fin) - gastos(<=fin) + movs_in(<=fin) - movs_out(<=fin)
            saldos: dict[int, float] = {c.id: c.saldo_inicial for c in cajas}
            gasto_periodo: dict[int, float] = {c.id: 0.0 for c in cajas}

            for ing in s.exec(
                sqlmodel.select(Ingreso).where(
                    Ingreso.caja_id.is_not(None),
                    Ingreso.fecha < fin,
                )
            ).all():
                ingreso_val = max(
                    float(ing.ingreso_real_cuenta or 0),
                    float(calculate_net_income(
                        ing.salario_base or 0,
                        ing.aux_transporte or 0,
                        ing.otros or 0,
                    )),
                )
                saldos[ing.caja_id] = saldos.get(ing.caja_id, 0) + ingreso_val

            for g in s.exec(
                sqlmodel.select(Gasto).where(
                    Gasto.caja_id.is_not(None),
                    Gasto.fecha < fin,
                )
            ).all():
                saldos[g.caja_id] = saldos.get(g.caja_id, 0) - (g.monto or 0)
                if g.fecha >= ini:
                    gasto_periodo[g.caja_id] = gasto_periodo.get(g.caja_id, 0.0) + float(g.monto or 0)

            movs = s.exec(
                sqlmodel.select(Movimiento)
                .where(Movimiento.fecha < fin)
                .order_by(sqlmodel.desc(Movimiento.fecha))
            ).all()
            for m in movs:
                saldos[m.caja_origen_id] = saldos.get(m.caja_origen_id, 0) - m.monto - (m.costo_4x1000 or 0)
                saldos[m.caja_destino_id] = saldos.get(m.caja_destino_id, 0) + m.monto

            by_id = {c.id: c for c in cajas}

            rows: list[CajaRow] = []
            total = 0.0
            total_deuda_tc = 0.0
            total_cupo_tc = 0.0
            for c in cajas:
                saldo = saldos.get(c.id, 0.0)
                faltante = abs(saldo) if saldo < 0 else 0.0
                es_tc = (c.tipo == "tarjeta_credito")
                deuda_cop = abs(saldo) if (es_tc and saldo < 0) else 0.0
                cupo_disp = max(0.0, (c.cupo_total_cop or 0.0) - deuda_cop) if es_tc else 0.0
                pct_uso = (deuda_cop / c.cupo_total_cop * 100.0) if (es_tc and (c.cupo_total_cop or 0) > 0) else 0.0
                rows.append(CajaRow(
                    id=c.id, nombre=c.nombre, tipo=c.tipo,
                    tipo_label=TIPO_CAJA_LABEL.get(c.tipo, c.tipo),
                    entidad=c.entidad, exento_4x1000=c.exento_4x1000,
                    saldo_inicial=c.saldo_inicial,
                    saldo_actual=saldo,
                    saldo_actual_fmt=f"${saldo:,.0f}",
                    faltante_cero=faltante,
                    faltante_cero_fmt=f"${faltante:,.0f}",
                    gasto_periodo=gasto_periodo.get(c.id, 0.0),
                    gasto_periodo_fmt=f"${gasto_periodo.get(c.id, 0.0):,.0f}",
                    color=c.color, orden=c.orden, activa=c.activa, notas=c.notas or "",
                    es_tc=es_tc,
                    cupo_total_cop=c.cupo_total_cop or 0.0,
                    cupo_total_fmt=f"${(c.cupo_total_cop or 0.0):,.0f}",
                    deuda_cop=deuda_cop,
                    deuda_cop_fmt=f"${deuda_cop:,.0f}",
                    cupo_disponible=cupo_disp,
                    cupo_disponible_fmt=f"${cupo_disp:,.0f}",
                    pct_uso=pct_uso,
                    pct_uso_fmt=f"{pct_uso:.0f}%",
                    interes_mensual_compras=c.interes_mensual_compras or 0.0,
                    interes_ea_compras=c.interes_ea_compras or 0.0,
                    interes_mensual_avances=c.interes_mensual_avances or 0.0,
                    interes_ea_avances=c.interes_ea_avances or 0.0,
                    cuota_manejo=c.cuota_manejo or 0.0,
                    cuota_manejo_fmt=f"${(c.cuota_manejo or 0.0):,.0f}",
                    dia_cobro_cuota=c.dia_cobro_cuota or 1,
                    dia_corte=c.dia_corte or 1,
                    dia_pago=c.dia_pago or 1,
                    trm_tc=c.trm_tc or 0.0,
                    trm_tc_fmt=f"${(c.trm_tc or 0.0):,.2f}",
                ))
                if c.activa and not es_tc:
                    total += saldo
                if c.activa and es_tc:
                    total_deuda_tc += deuda_cop
                    total_cupo_tc += (c.cupo_total_cop or 0.0)

            mov_rows: list[MovimientoRow] = []
            for m in movs[:50]:
                o = by_id.get(m.caja_origen_id)
                d = by_id.get(m.caja_destino_id)
                mov_rows.append(MovimientoRow(
                    id=m.id, fecha=m.fecha.isoformat(),
                    origen=o.nombre if o else "?",
                    destino=d.nombre if d else "?",
                    monto=m.monto, monto_fmt=f"${m.monto:,.0f}",
                    costo_4x1000=m.costo_4x1000 or 0,
                    costo_fmt=(f"${m.costo_4x1000:,.0f}" if m.costo_4x1000 else ""),
                    descripcion=m.descripcion or "",
                ))

            self.rows = rows
            self.movimientos = mov_rows
            self.total_patrimonio = total
            self.total_fmt = f"${total:,.0f}"
            self.total_deuda_tc = total_deuda_tc
            self.total_deuda_tc_fmt = f"${total_deuda_tc:,.0f}"
            self.total_cupo_tc = total_cupo_tc
            self.total_cupo_tc_fmt = f"${total_cupo_tc:,.0f}"
            disponible_tc = max(0.0, total_cupo_tc - total_deuda_tc)
            self.total_disponible_tc = disponible_tc
            self.total_disponible_tc_fmt = f"${disponible_tc:,.0f}"

            # Si no hay preferida seleccionada o quedó inactiva, tomar una sugerida por nombre o primera activa.
            ids_activos = [r.id for r in rows if r.activa]
            if self.auto_origen_preferido_id not in ids_activos:
                sugerida = next((r.id for r in rows if r.activa and "nomina" in r.nombre.lower()), 0)
                self.auto_origen_preferido_id = sugerida or (ids_activos[0] if ids_activos else 0)

    def _resolver_origen_cobertura(self, caja_destino_id: int) -> Optional[CajaRow]:
        candidatas = [
            r for r in self.rows
            if r.activa and r.id != caja_destino_id and r.saldo_actual > 0
        ]
        if not candidatas:
            return None

        pref = next((r for r in candidatas if r.id == self.auto_origen_preferido_id), None)
        if pref:
            return pref
        return max(candidatas, key=lambda r: r.saldo_actual)

    @rx.event
    def toggle_form(self):
        self.form_open = not self.form_open
        self.form_msg = ""
        if not self.form_open:
            self._reset_form()

    def _reset_form(self):
        self.form_editing_id = None
        self.form_nombre = ""
        self.form_tipo = "cuenta"
        self.form_entidad = ""
        self.form_exento_4x1000 = False
        self.form_saldo_inicial = 0.0
        self.form_color = "#a78bfa"
        self.form_notas = ""
        self.form_cupo_total_cop = 0.0
        self.form_interes_mensual_compras = 0.0
        self.form_interes_ea_compras = 0.0
        self.form_interes_mensual_avances = 0.0
        self.form_interes_ea_avances = 0.0
        self.form_cuota_manejo = 0.0
        self.form_dia_cobro_cuota = 1
        self.form_dia_corte = 1
        self.form_usa_dos_cortes = False
        self.form_dia_corte_2 = 15
        self.form_dia_pago = 1
        self.form_trm_tc = 0.0

    @rx.event
    def editar(self, caja_id: int):
        with rx.session() as s:
            c = s.get(Caja, caja_id)
            if not c:
                return
            self.form_editing_id = c.id
            self.form_nombre = c.nombre
            self.form_tipo = c.tipo
            self.form_entidad = c.entidad
            self.form_exento_4x1000 = c.exento_4x1000
            self.form_saldo_inicial = c.saldo_inicial
            self.form_color = c.color
            self.form_notas = c.notas or ""
            self.form_cupo_total_cop = c.cupo_total_cop or 0.0
            self.form_interes_mensual_compras = c.interes_mensual_compras or 0.0
            self.form_interes_ea_compras = c.interes_ea_compras or 0.0
            self.form_interes_mensual_avances = c.interes_mensual_avances or 0.0
            self.form_interes_ea_avances = c.interes_ea_avances or 0.0
            self.form_cuota_manejo = c.cuota_manejo or 0.0
            self.form_dia_cobro_cuota = c.dia_cobro_cuota or 1
            self.form_dia_corte = c.dia_corte or 1
            self.form_usa_dos_cortes = bool(c.usa_dos_cortes)
            self.form_dia_corte_2 = c.dia_corte_2 or 15
            self.form_dia_pago = c.dia_pago or 1
            self.form_trm_tc = c.trm_tc or 0.0
            self.form_open = True

    @rx.event
    async def guardar(self):
        if not self.form_nombre.strip():
            self.form_msg = "⚠ El nombre es obligatorio."
            return
        es_tc = (self.form_tipo == "tarjeta_credito")
        # Para TC el saldo inicial siempre es 0 (la deuda se construye con gastos).
        saldo_ini = 0.0 if es_tc else self.form_saldo_inicial
        with rx.session() as s:
            if self.form_editing_id:
                c = s.get(Caja, self.form_editing_id)
                if not c:
                    return
                c.nombre = self.form_nombre.strip()
                c.tipo = self.form_tipo
                c.entidad = self.form_entidad.strip()
                c.exento_4x1000 = self.form_exento_4x1000
                c.saldo_inicial = saldo_ini
                c.color = self.form_color
                c.notas = self.form_notas.strip()
                if es_tc:
                    c.cupo_total_cop = self.form_cupo_total_cop
                    c.interes_mensual_compras = self.form_interes_mensual_compras
                    c.interes_ea_compras = self.form_interes_ea_compras
                    c.interes_mensual_avances = self.form_interes_mensual_avances
                    c.interes_ea_avances = self.form_interes_ea_avances
                    c.cuota_manejo = self.form_cuota_manejo
                    c.dia_cobro_cuota = max(1, min(31, int(self.form_dia_cobro_cuota or 1)))
                    c.dia_corte = max(1, min(31, int(self.form_dia_corte or 1)))
                    c.usa_dos_cortes = bool(self.form_usa_dos_cortes)
                    c.dia_corte_2 = max(1, min(31, int(self.form_dia_corte_2 or 15)))
                    c.dia_pago = max(1, min(31, int(self.form_dia_pago or 1)))
                    c.trm_tc = float(self.form_trm_tc or 0.0)
                s.add(c)
            else:
                c = Caja(
                    nombre=self.form_nombre.strip(),
                    tipo=self.form_tipo,
                    entidad=self.form_entidad.strip(),
                    exento_4x1000=self.form_exento_4x1000,
                    saldo_inicial=saldo_ini,
                    color=self.form_color,
                    notas=self.form_notas.strip(),
                    cupo_total_cop=(self.form_cupo_total_cop if es_tc else 0.0),
                    interes_mensual_compras=(self.form_interes_mensual_compras if es_tc else 0.0),
                    interes_ea_compras=(self.form_interes_ea_compras if es_tc else 0.0),
                    interes_mensual_avances=(self.form_interes_mensual_avances if es_tc else 0.0),
                    interes_ea_avances=(self.form_interes_ea_avances if es_tc else 0.0),
                    cuota_manejo=(self.form_cuota_manejo if es_tc else 0.0),
                    dia_cobro_cuota=(max(1, min(31, int(self.form_dia_cobro_cuota or 1))) if es_tc else 1),
                    dia_corte=(max(1, min(31, int(self.form_dia_corte or 1))) if es_tc else 1),
                    usa_dos_cortes=(bool(self.form_usa_dos_cortes) if es_tc else False),
                    dia_corte_2=(max(1, min(31, int(self.form_dia_corte_2 or 15))) if es_tc else 15),
                    dia_pago=(max(1, min(31, int(self.form_dia_pago or 1))) if es_tc else 1),
                    trm_tc=(float(self.form_trm_tc or 0.0) if es_tc else 0.0),
                )
                s.add(c)
            s.commit()
        self._reset_form()
        self.form_open = False
        self.form_msg = "✅ Guardado."
        await self.load()

    @rx.event
    async def eliminar(self, caja_id: int):
        with rx.session() as s:
            c = s.get(Caja, caja_id)
            if c:
                c.activa = False
                s.add(c)
                s.commit()
            await self.load()

    # ── Movimientos ──
    @rx.event
    def toggle_mov(self):
        self.mov_open = not self.mov_open
        self.mov_msg = ""

    @rx.event
    def sugerir_cobertura(self, caja_destino_id: int):
        destino = next((r for r in self.rows if r.id == caja_destino_id), None)
        if not destino:
            self.mov_msg = "⚠ Caja destino no encontrada."
            return
        if destino.saldo_actual >= 0:
            self.mov_msg = "ℹ Esa caja no está en negativo."
            return

        origen = self._resolver_origen_cobertura(caja_destino_id)
        if not origen:
            self.mov_open = True
            self.mov_destino_id = caja_destino_id
            self.mov_origen_id = 0
            self.mov_monto = destino.faltante_cero
            self.mov_desc = f"Cobertura {destino.nombre}"
            self.mov_msg = "⚠ No hay caja con saldo positivo para sugerir origen."
            return

        self.mov_open = True
        self.mov_destino_id = caja_destino_id
        self.mov_origen_id = origen.id
        self.mov_monto = destino.faltante_cero
        self.mov_desc = f"Cobertura {destino.nombre}"
        self.mov_msg = (
            f"💡 Sugerencia: mover {destino.faltante_cero_fmt} "
            f"desde {origen.nombre} para dejar {destino.nombre} en $0."
        )

    @rx.event
    async def auto_transferir_cobertura(self, caja_destino_id: int):
        """Aplica una transferencia automática para cubrir faltante usando fecha del ingreso."""
        from minty.state.periodo import PeriodoState

        destino = next((r for r in self.rows if r.id == caja_destino_id), None)
        if not destino:
            self.mov_msg = "⚠ Caja destino no encontrada."
            return
        if destino.saldo_actual >= 0:
            self.mov_msg = "ℹ Esa caja no está en negativo."
            return

        origen = self._resolver_origen_cobertura(caja_destino_id)
        if not origen:
            self.mov_msg = "⚠ No hay caja con saldo positivo para cubrir este faltante."
            return

        monto = destino.faltante_cero

        per = await self.get_state(PeriodoState)
        ini = date.fromisoformat(per.fecha_inicio)
        fin = date.fromisoformat(per.fecha_fin)

        with rx.session() as s:
            caja_origen = s.get(Caja, origen.id)
            if not caja_origen:
                self.mov_msg = "⚠ Caja origen inválida."
                return

            # 1) Prioriza el último ingreso de esa caja dentro del período seleccionado.
            # 2) Si no hay, usa el último ingreso histórico de esa caja.
            # 3) Si tampoco hay, usa hoy.
            ingreso_ref = s.exec(
                sqlmodel.select(Ingreso)
                .where(
                    Ingreso.caja_id == origen.id,
                    Ingreso.fecha >= ini,
                    Ingreso.fecha < fin,
                )
                .order_by(sqlmodel.desc(Ingreso.fecha))
            ).first()
            if not ingreso_ref:
                ingreso_ref = s.exec(
                    sqlmodel.select(Ingreso)
                    .where(Ingreso.caja_id == origen.id)
                    .order_by(sqlmodel.desc(Ingreso.fecha))
                ).first()

            fecha_mov = ingreso_ref.fecha if ingreso_ref else date.today()

            costo = calcular_4x1000(monto, caja_origen.tipo, caja_origen.exento_4x1000)
            mov = Movimiento(
                fecha=fecha_mov,
                caja_origen_id=origen.id,
                caja_destino_id=destino.id,
                monto=monto,
                aplica_4x1000=costo > 0,
                costo_4x1000=costo,
                descripcion=f"[AUTO] Cobertura {destino.nombre}",
            )
            s.add(mov)
            s.commit()

        self.mov_msg = (
            f"✅ Auto transferencia: {destino.faltante_cero_fmt} desde {origen.nombre} "
            f"a {destino.nombre} con fecha {fecha_mov.isoformat()}."
        )
        await self.load()

    @rx.event
    async def guardar_movimiento(self):
        if self.mov_origen_id == self.mov_destino_id:
            self.mov_msg = "⚠ Origen y destino deben ser distintos."
            return
        if self.mov_monto <= 0:
            self.mov_msg = "⚠ El monto debe ser > 0."
            return
        with rx.session() as s:
            origen = s.get(Caja, self.mov_origen_id)
            if not origen:
                self.mov_msg = "⚠ Caja origen inválida."
                return
            costo = calcular_4x1000(self.mov_monto, origen.tipo, origen.exento_4x1000)
            mov = Movimiento(
                fecha=date.fromisoformat(self.mov_fecha),
                caja_origen_id=self.mov_origen_id,
                caja_destino_id=self.mov_destino_id,
                monto=self.mov_monto,
                aplica_4x1000=costo > 0,
                costo_4x1000=costo,
                descripcion=self.mov_desc.strip(),
            )
            s.add(mov)
            s.commit()
        self.mov_monto = 0.0
        self.mov_desc = ""
        self.mov_msg = "✅ Transferencia registrada."
        self.mov_open = False
        await self.load()

    @rx.event
    async def eliminar_movimiento(self, mov_id: int):
        with rx.session() as s:
            m = s.get(Movimiento, mov_id)
            if m:
                s.delete(m)
                s.commit()
        await self.load()

    # ── Tarjetas de crédito ──
    def _cobrar_cuotas_manejo_si_corresponde(self):
        """Genera idempotentemente un Gasto por la cuota de manejo del mes
        para cada caja TC activa, si:
          - tiene cuota_manejo > 0
          - hoy >= dia_cobro_cuota
          - aún no se generó este mes (caja.ultimo_cobro_cuota != "YYYY-MM").
        El gasto incrementa la deuda (saldo se vuelve más negativo).
        """
        hoy = date.today()
        yyyymm = f"{hoy.year:04d}-{hoy.month:02d}"
        with rx.session() as s:
            tcs = s.exec(
                sqlmodel.select(Caja).where(
                    Caja.tipo == "tarjeta_credito",
                    Caja.activa == True,  # noqa: E712
                )
            ).all()
            cambios = False
            for c in tcs:
                if (c.cuota_manejo or 0) <= 0:
                    continue
                dia_obj = max(1, min(31, c.dia_cobro_cuota or 1))
                if hoy.day < dia_obj:
                    continue
                if (c.ultimo_cobro_cuota or "") == yyyymm:
                    continue
                # Fecha real del cobro: el día configurado (cap a fin de mes).
                try:
                    fecha_cobro = hoy.replace(day=dia_obj)
                except ValueError:
                    fecha_cobro = hoy
                gasto = Gasto(
                    fecha=fecha_cobro,
                    descripcion=f"Cuota de manejo {c.nombre}",
                    categoria="Servicios",
                    monto=float(c.cuota_manejo),
                    moneda="COP",
                    monto_original=float(c.cuota_manejo),
                    medio_pago="Tarjeta de crédito",
                    caja_id=c.id,
                    notas="[AUTO] Cuota de manejo mensual",
                )
                s.add(gasto)
                c.ultimo_cobro_cuota = yyyymm
                s.add(c)
                cambios = True
            if cambios:
                s.commit()

    @rx.event
    async def actualizar_trm_tc(self, caja_tc_id: int, valor: float):
        """Actualiza manualmente el TRM propio de la TC."""
        try:
            v = float(valor or 0)
        except (TypeError, ValueError):
            v = 0.0
        with rx.session() as s:
            c = s.get(Caja, caja_tc_id)
            if not c or c.tipo != "tarjeta_credito":
                return
            c.trm_tc = max(0.0, v)
            s.add(c)
            s.commit()
        await self.load()

    @rx.event
    def pagar_tarjeta(self, caja_tc_id: int):
        """Abre el modal de transferencia preconfigurado para pagar la TC:
        destino = TC, origen = caja preferida o primera cuenta con saldo positivo,
        monto sugerido = deuda actual.
        """
        tc = next((r for r in self.rows if r.id == caja_tc_id and r.es_tc), None)
        if not tc:
            return
        # Origen sugerido: preferida o cualquier cuenta no-TC con saldo positivo.
        candidatas = [
            r for r in self.rows
            if r.activa and not r.es_tc and r.id != caja_tc_id and r.saldo_actual > 0
        ]
        pref = next((r for r in candidatas if r.id == self.auto_origen_preferido_id), None)
        origen = pref or (max(candidatas, key=lambda r: r.saldo_actual) if candidatas else None)

        self.mov_open = True
        self.mov_fecha = date.today().isoformat()
        self.mov_destino_id = caja_tc_id
        self.mov_origen_id = origen.id if origen else 0
        self.mov_monto = tc.deuda_cop
        self.mov_desc = f"Pago tarjeta {tc.nombre}"
        if not origen:
            self.mov_msg = "⚠ No hay cuenta con saldo positivo para sugerir como origen."
        else:
            self.mov_msg = f"💡 Pago sugerido: {tc.deuda_cop_fmt} desde {origen.nombre}."

    # ── Carga directa de deuda a una TC ──
    @rx.event
    def abrir_cargar_deuda(self, caja_tc_id: int):
        """Abre el modal para cargar deuda directa (sin pasar por gastos.py)."""
        tc = next((r for r in self.rows if r.id == caja_tc_id and r.es_tc), None)
        if not tc:
            return
        self.deuda_open = True
        self.deuda_caja_id = caja_tc_id
        self.deuda_caja_nombre = tc.nombre
        self.deuda_fecha = date.today().isoformat()
        self.deuda_desc = ""
        self.deuda_moneda = "COP"
        self.deuda_monto_cop = 0.0
        self.deuda_monto_usd = 0.0
        self.deuda_trm_tc_actual = tc.trm_tc or 0.0
        self.deuda_msg = ""

    @rx.event
    def cerrar_cargar_deuda(self):
        self.deuda_open = False
        self.deuda_msg = ""

    @rx.event
    async def guardar_deuda(self):
        """Crea un Gasto directo sobre la TC con el monto en COP indicado.

        No aplica intereses ni recálculos: el monto se carga tal cual,
        ya que la idea es reflejar el cargo que el banco YA hizo
        (con su TRM y sus intereses incluidos en el monto cobrado).
        """
        if self.deuda_caja_id <= 0:
            self.deuda_msg = "⚠ Caja TC inválida."
            return
        if not self.deuda_desc.strip():
            self.deuda_msg = "⚠ La descripción es obligatoria."
            return

        if self.deuda_moneda == "USD":
            if self.deuda_monto_usd <= 0:
                self.deuda_msg = "⚠ El monto USD debe ser mayor a 0."
                return
            if self.deuda_trm_tc_actual <= 0:
                self.deuda_msg = (
                    "⚠ La TC no tiene TRM propio configurado. "
                    "Edita la caja y carga el TRM antes de continuar."
                )
                return
            monto_cop = float(self.deuda_monto_usd) * float(self.deuda_trm_tc_actual)
            monto_original = float(self.deuda_monto_usd)
            trm_aplicado = float(self.deuda_trm_tc_actual)
            moneda = "USD"
        else:
            if self.deuda_monto_cop <= 0:
                self.deuda_msg = "⚠ El monto COP debe ser mayor a 0."
                return
            monto_cop = float(self.deuda_monto_cop)
            monto_original = monto_cop
            trm_aplicado = 0.0
            moneda = "COP"

        try:
            fecha = date.fromisoformat(self.deuda_fecha) if self.deuda_fecha else date.today()
        except (TypeError, ValueError):
            fecha = date.today()

        with rx.session() as s:
            gasto = Gasto(
                fecha=fecha,
                descripcion=self.deuda_desc.strip(),
                categoria="Otros",
                monto=monto_cop,
                moneda=moneda,
                monto_original=monto_original,
                trm=trm_aplicado,
                medio_pago="Tarjeta de crédito",
                caja_id=self.deuda_caja_id,
                notas=(
                    f"[DEUDA TC] Carga directa con TRM TC={trm_aplicado:,.2f}"
                    if moneda == "USD" else
                    "[DEUDA TC] Carga directa (sin recálculo de intereses)."
                ),
            )
            s.add(gasto)
            s.commit()

        self.deuda_open = False
        self.deuda_msg = "✅ Deuda cargada."
        await self.load()
