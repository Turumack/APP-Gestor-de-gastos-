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

        with rx.session() as s:
            cajas = s.exec(
                sqlmodel.select(Caja).order_by(Caja.orden, Caja.id)
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
            for c in cajas:
                saldo = saldos.get(c.id, 0.0)
                faltante = abs(saldo) if saldo < 0 else 0.0
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
                ))
                if c.activa and c.tipo != "tarjeta_credito":
                    total += saldo

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
            self.form_open = True

    @rx.event
    async def guardar(self):
        if not self.form_nombre.strip():
            self.form_msg = "⚠ El nombre es obligatorio."
            return
        with rx.session() as s:
            if self.form_editing_id:
                c = s.get(Caja, self.form_editing_id)
                if not c:
                    return
                c.nombre = self.form_nombre.strip()
                c.tipo = self.form_tipo
                c.entidad = self.form_entidad.strip()
                c.exento_4x1000 = self.form_exento_4x1000
                c.saldo_inicial = self.form_saldo_inicial
                c.color = self.form_color
                c.notas = self.form_notas.strip()
                s.add(c)
            else:
                c = Caja(
                    nombre=self.form_nombre.strip(),
                    tipo=self.form_tipo,
                    entidad=self.form_entidad.strip(),
                    exento_4x1000=self.form_exento_4x1000,
                    saldo_inicial=self.form_saldo_inicial,
                    color=self.form_color,
                    notas=self.form_notas.strip(),
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
