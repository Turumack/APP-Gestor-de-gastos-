"""State de Metas (bolsas de ahorro persistentes)."""
from datetime import date
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from minty.models import Meta, Gasto, Caja
from minty.state._autosetters import auto_setters


COLORES_META = [
    "#a78bfa", "#22d3ee", "#34d399", "#facc15",
    "#fb7185", "#f97316", "#60a5fa", "#c084fc",
]
ICONOS_META = [
    "target", "piggy-bank", "plane", "house",
    "car", "graduation-cap", "heart", "gift",
    "rocket", "trophy", "wallet", "shield",
]


class MetaRow(BaseModel):
    id: int
    nombre: str
    objetivo: float
    objetivo_fmt: str
    acumulado: float
    acumulado_fmt: str
    restante: float
    restante_fmt: str
    pct: float
    pct_fmt: str
    color: str
    icono: str
    activa: bool
    notas: str
    n_aportes: int
    fecha_objetivo: str  # iso o ""
    completada: bool


class AporteRow(BaseModel):
    id: int
    fecha: str
    monto: float
    monto_fmt: str
    descripcion: str
    caja_nombre: str
    meta_id: int
    meta_nombre: str
    color: str


@auto_setters
class MetasState(rx.State):
    rows: list[MetaRow] = []
    total_objetivo: float = 0.0
    total_acumulado: float = 0.0
    total_objetivo_fmt: str = "$0"
    total_acumulado_fmt: str = "$0"
    pct_global: float = 0.0

    # ── Form Meta ──
    form_open: bool = False
    form_nombre: str = ""
    form_objetivo: float = 0.0
    form_color: str = "#a78bfa"
    form_icono: str = "target"
    form_fecha_objetivo: str = ""
    form_notas: str = ""
    form_editing_id: Optional[int] = None
    form_msg: str = ""

    # ── Form Aporte ──
    aporte_open: bool = False
    aporte_meta_id: Optional[int] = None
    aporte_meta_nombre: str = ""
    aporte_monto: float = 0.0
    aporte_fecha: str = date.today().isoformat()
    aporte_caja_id: Optional[int] = None
    aporte_descripcion: str = ""
    aporte_msg: str = ""

    # ── Detalle ──
    detalle_meta_id: Optional[int] = None
    detalle_meta_nombre: str = ""
    detalle_aportes: list[AporteRow] = []

    # Cajas para selector
    cajas_opts: list[dict] = []  # [{label, value}]

    @rx.var
    def colores(self) -> list[str]:
        return COLORES_META

    @rx.var
    def iconos(self) -> list[str]:
        return ICONOS_META

    @rx.event
    async def load(self):
        with rx.session() as s:
            metas = s.exec(
                sqlmodel.select(Meta).where(Meta.activa == True)  # noqa: E712
                .order_by(Meta.creado_en)
            ).all()
            # Todos los aportes (gastos con meta_id)
            aportes = s.exec(
                sqlmodel.select(Gasto).where(Gasto.meta_id != None)  # noqa: E711
            ).all()
            cajas = s.exec(
                sqlmodel.select(Caja).where(
                    Caja.activa == True,  # noqa: E712
                    Caja.tipo != "tarjeta_credito",
                ).order_by(Caja.orden)
            ).all()

        self.cajas_opts = [
            {"label": c.nombre, "value": str(c.id)} for c in cajas
        ]
        if not self.aporte_caja_id and cajas:
            self.aporte_caja_id = cajas[0].id

        agrup: dict[int, list[Gasto]] = {}
        for a in aportes:
            agrup.setdefault(a.meta_id or 0, []).append(a)

        rows: list[MetaRow] = []
        total_obj = 0.0
        total_acum = 0.0
        for m in metas:
            lst = agrup.get(m.id or 0, [])
            acum = sum(float(g.monto or 0) for g in lst)
            obj = float(m.objetivo or 0)
            pct = (acum / obj * 100) if obj > 0 else 0.0
            restante = max(0.0, obj - acum)
            rows.append(MetaRow(
                id=m.id or 0,
                nombre=m.nombre,
                objetivo=obj,
                objetivo_fmt=f"${obj:,.0f}" if obj > 0 else "Sin objetivo",
                acumulado=acum,
                acumulado_fmt=f"${acum:,.0f}",
                restante=restante,
                restante_fmt=f"${restante:,.0f}",
                pct=min(pct, 100.0),
                pct_fmt=f"{pct:.1f}%" if obj > 0 else "—",
                color=m.color or "#a78bfa",
                icono=m.icono or "target",
                activa=m.activa,
                notas=m.notas or "",
                n_aportes=len(lst),
                fecha_objetivo=m.fecha_objetivo.isoformat() if m.fecha_objetivo else "",
                completada=(obj > 0 and acum >= obj),
            ))
            total_obj += obj
            total_acum += acum

        self.rows = rows
        self.total_objetivo = total_obj
        self.total_acumulado = total_acum
        self.total_objetivo_fmt = f"${total_obj:,.0f}"
        self.total_acumulado_fmt = f"${total_acum:,.0f}"
        self.pct_global = (total_acum / total_obj * 100) if total_obj > 0 else 0.0

        # Refrescar detalle si hay uno abierto
        if self.detalle_meta_id is not None:
            await self._cargar_detalle(self.detalle_meta_id)

    async def _cargar_detalle(self, meta_id: int):
        with rx.session() as s:
            meta = s.get(Meta, meta_id)
            if not meta:
                self.detalle_meta_id = None
                self.detalle_aportes = []
                return
            aportes = s.exec(
                sqlmodel.select(Gasto).where(Gasto.meta_id == meta_id)
                .order_by(sqlmodel.desc(Gasto.fecha))
            ).all()
            cajas_idx = {
                c.id: c.nombre for c in s.exec(sqlmodel.select(Caja)).all()
            }
        self.detalle_meta_nombre = meta.nombre
        self.detalle_aportes = [
            AporteRow(
                id=g.id or 0,
                fecha=g.fecha.isoformat(),
                monto=float(g.monto or 0),
                monto_fmt=f"${float(g.monto or 0):,.0f}",
                descripcion=g.descripcion or "",
                caja_nombre=cajas_idx.get(g.caja_id or 0, "—"),
                meta_id=meta_id,
                meta_nombre=meta.nombre,
                color=meta.color or "#a78bfa",
            )
            for g in aportes
        ]

    # ── Form Meta ──
    @rx.event
    def toggle_form(self):
        self.form_open = not self.form_open
        self.form_msg = ""
        if self.form_open and not self.form_editing_id:
            self.form_nombre = ""
            self.form_objetivo = 0.0
            self.form_color = "#a78bfa"
            self.form_icono = "target"
            self.form_fecha_objetivo = ""
            self.form_notas = ""

    @rx.event
    async def editar(self, mid: int):
        with rx.session() as s:
            m = s.get(Meta, mid)
            if not m:
                return
            self.form_editing_id = m.id
            self.form_nombre = m.nombre
            self.form_objetivo = float(m.objetivo or 0)
            self.form_color = m.color or "#a78bfa"
            self.form_icono = m.icono or "target"
            self.form_fecha_objetivo = (
                m.fecha_objetivo.isoformat() if m.fecha_objetivo else ""
            )
            self.form_notas = m.notas or ""
            self.form_open = True
            self.form_msg = ""

    @rx.event
    async def guardar(self):
        nombre = (self.form_nombre or "").strip()
        if not nombre:
            self.form_msg = "⚠ El nombre es obligatorio."
            return
        if self.form_objetivo < 0:
            self.form_msg = "⚠ El objetivo no puede ser negativo."
            return
        fecha_obj = None
        if self.form_fecha_objetivo:
            try:
                fecha_obj = date.fromisoformat(self.form_fecha_objetivo)
            except ValueError:
                self.form_msg = "⚠ Fecha objetivo inválida."
                return

        with rx.session() as s:
            if self.form_editing_id:
                m = s.get(Meta, self.form_editing_id)
                if not m:
                    self.form_msg = "⚠ Meta no encontrada."
                    return
                # Si cambia nombre, propagar a aportes existentes (categoria).
                if m.nombre != nombre:
                    aportes = s.exec(
                        sqlmodel.select(Gasto).where(Gasto.meta_id == m.id)
                    ).all()
                    for a in aportes:
                        a.categoria = nombre
                        s.add(a)
                m.nombre = nombre
                m.objetivo = float(self.form_objetivo)
                m.color = self.form_color
                m.icono = self.form_icono
                m.fecha_objetivo = fecha_obj
                m.notas = self.form_notas
                s.add(m)
            else:
                # Evitar duplicado por nombre
                existe = s.exec(
                    sqlmodel.select(Meta).where(Meta.nombre == nombre)
                ).first()
                if existe:
                    self.form_msg = "⚠ Ya existe una meta con ese nombre."
                    return
                s.add(Meta(
                    nombre=nombre,
                    objetivo=float(self.form_objetivo),
                    color=self.form_color,
                    icono=self.form_icono,
                    fecha_objetivo=fecha_obj,
                    notas=self.form_notas,
                    activa=True,
                ))
            s.commit()
        self.form_open = False
        self.form_editing_id = None
        await self.load()

    @rx.event
    async def eliminar(self, mid: int):
        """Elimina la meta y desvincula sus aportes (no los borra)."""
        with rx.session() as s:
            m = s.get(Meta, mid)
            if not m:
                return
            aportes = s.exec(
                sqlmodel.select(Gasto).where(Gasto.meta_id == mid)
            ).all()
            for a in aportes:
                a.meta_id = None
                s.add(a)
            s.delete(m)
            s.commit()
        if self.detalle_meta_id == mid:
            self.detalle_meta_id = None
            self.detalle_aportes = []
        await self.load()

    # ── Aporte ──
    @rx.event
    async def abrir_aporte(self, mid: int):
        with rx.session() as s:
            m = s.get(Meta, mid)
            if not m:
                return
        self.aporte_meta_id = mid
        self.aporte_meta_nombre = m.nombre
        self.aporte_monto = 0.0
        self.aporte_fecha = date.today().isoformat()
        self.aporte_descripcion = f"Aporte a {m.nombre}"
        self.aporte_msg = ""
        self.aporte_open = True

    @rx.event
    def cerrar_aporte(self):
        self.aporte_open = False
        self.aporte_meta_id = None
        self.aporte_msg = ""

    @rx.event
    async def guardar_aporte(self):
        if not self.aporte_meta_id:
            return
        if self.aporte_monto <= 0:
            self.aporte_msg = "⚠ El monto debe ser mayor a 0."
            return
        if not self.aporte_caja_id:
            self.aporte_msg = "⚠ Selecciona una caja origen."
            return
        try:
            f = date.fromisoformat(self.aporte_fecha)
        except ValueError:
            self.aporte_msg = "⚠ Fecha inválida."
            return

        with rx.session() as s:
            meta = s.get(Meta, self.aporte_meta_id)
            if not meta:
                self.aporte_msg = "⚠ Meta no encontrada."
                return
            s.add(Gasto(
                fecha=f,
                descripcion=self.aporte_descripcion or f"Aporte a {meta.nombre}",
                categoria=meta.nombre,
                monto=float(self.aporte_monto),
                moneda="COP",
                monto_original=float(self.aporte_monto),
                medio_pago="Transferencia",
                caja_id=int(self.aporte_caja_id),
                meta_id=meta.id,
            ))
            s.commit()
        self.aporte_open = False
        self.aporte_meta_id = None
        await self.load()

    @rx.event
    def set_aporte_caja(self, val: str):
        try:
            self.aporte_caja_id = int(val)
        except (TypeError, ValueError):
            self.aporte_caja_id = None

    # ── Detalle / aportes individuales ──
    @rx.event
    async def ver_detalle(self, mid: int):
        self.detalle_meta_id = mid
        await self._cargar_detalle(mid)

    @rx.event
    def cerrar_detalle(self):
        self.detalle_meta_id = None
        self.detalle_aportes = []

    @rx.event
    async def eliminar_aporte(self, gid: int):
        with rx.session() as s:
            g = s.get(Gasto, gid)
            if g and g.meta_id is not None:
                s.delete(g)
                s.commit()
        await self.load()
