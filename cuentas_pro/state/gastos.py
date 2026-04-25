"""State de Gastos."""
from datetime import date
from calendar import monthrange
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from cuentas_pro.models import Gasto, Caja, ShoppingGroup, ShoppingItem
from cuentas_pro.finance import CATEGORIAS_GASTO, COLOR_CATEGORIA, MEDIOS_PAGO, MONEDAS
from cuentas_pro.services import obtener_trm
from cuentas_pro.state.periodo import PeriodoState
from cuentas_pro.state._autosetters import auto_setters


class GastoRow(BaseModel):
    id: int
    fecha: str
    descripcion: str
    categoria: str
    monto: float
    monto_fmt: str
    moneda: str
    monto_original: float
    trm: float
    origen_fmt: str   # p.ej. "USD 50 @ 4,210" o ""
    medio_pago: str
    caja_nombre: str
    shopping_ref: str
    recurrente: bool
    notas: str
    color: str


class DiaCelda(BaseModel):
    dia: int
    fecha: str
    total: float
    total_fmt: str
    count: int
    es_otro_mes: bool
    is_today: bool


@auto_setters
class GastosState(rx.State):
    rows: list[GastoRow] = []
    total_mes: float = 0.0
    por_categoria: list[dict] = []

    # Calendario
    celdas: list[DiaCelda] = []
    dia_seleccionado: str = ""  # fecha ISO seleccionada (filtro)

    # Form
    form_open: bool = False
    form_fecha: str = date.today().isoformat()
    form_desc: str = ""
    form_categoria: str = "Otros"
    form_monto: float = 0.0          # COP equivalente
    form_moneda: str = "COP"
    form_monto_original: float = 0.0  # USD si aplica
    form_trm: float = 0.0
    form_medio: str = "Efectivo"
    form_caja_id: int = 0             # 0 = sin caja asignada
    form_shopping_group_id: int = 0
    form_shopping_item_id: int = 0
    form_shopping_pct: float = 100.0
    form_recurrente: bool = False
    form_notas: str = ""
    form_editing_id: Optional[int] = None
    form_msg: str = ""

    # Cajas disponibles (cache ligero para el selector)
    cajas_opts: list[dict] = []
    shopping_groups_opts: list[dict] = []
    shopping_items_all: list[dict] = []
    shopping_items_opts: list[dict] = []

    @rx.var
    def rows_filtradas(self) -> list[GastoRow]:
        if self.dia_seleccionado == "":
            return self.rows
        return [r for r in self.rows if r.fecha == self.dia_seleccionado]

    @rx.event
    async def load(self):
        per = await self.get_state(PeriodoState)
        ini = date.fromisoformat(per.fecha_inicio)
        fin = date.fromisoformat(per.fecha_fin)

        with rx.session() as s:
            stmt = (
                sqlmodel.select(Gasto)
                .where(Gasto.fecha >= ini, Gasto.fecha < fin)
                .order_by(sqlmodel.desc(Gasto.fecha))
            )
            results = s.exec(stmt).all()
            cajas_all = s.exec(
                sqlmodel.select(Caja).where(Caja.activa == True).order_by(Caja.orden, Caja.id)
            ).all()
            groups_all = s.exec(
                sqlmodel.select(ShoppingGroup)
                .where(ShoppingGroup.activa == True)
                .order_by(sqlmodel.desc(ShoppingGroup.id))
            ).all()
            items_all = s.exec(
                sqlmodel.select(ShoppingItem)
                .where(ShoppingItem.activo == True)
                .order_by(sqlmodel.desc(ShoppingItem.id))
            ).all()

        cajas_by_id = {c.id: c for c in cajas_all}
        groups_by_id = {g.id: g for g in groups_all}
        items_by_id = {it.id: it for it in items_all}
        self.cajas_opts = [{"id": c.id, "nombre": c.nombre,
                            "etiqueta": f"{c.nombre} · {c.entidad}" if c.entidad else c.nombre}
                           for c in cajas_all]
        self.shopping_groups_opts = [
            {"id": g.id, "nombre": g.nombre, "etiqueta": g.nombre}
            for g in groups_all
        ]
        self.shopping_items_all = [
            {
                "id": it.id,
                "group_id": it.group_id,
                "nombre": it.nombre,
                "categoria": it.categoria or "Otros",
                "monto": float(it.monto_estimado or 0.0),
                "comprado": bool(it.comprado),
                "etiqueta": f"{it.nombre} · ${float(it.monto_estimado or 0.0):,.0f}",
            }
            for it in items_all
        ]
        self._refresh_shopping_items_opts()

        rows = []
        total = 0.0
        por_cat: dict[str, float] = {}
        por_dia: dict[str, float] = {}
        count_dia: dict[str, int] = {}

        for r in results:
            caja = cajas_by_id.get(r.caja_id) if r.caja_id else None
            origen_fmt = ""
            if r.moneda == "USD" and r.monto_original:
                origen_fmt = f"USD {r.monto_original:,.2f} @ {r.trm:,.0f}"
            rows.append(GastoRow(
                id=r.id, fecha=r.fecha.isoformat(), descripcion=r.descripcion,
                categoria=r.categoria, monto=r.monto,
                monto_fmt=f"${r.monto:,.0f}",
                moneda=r.moneda or "COP",
                monto_original=r.monto_original or r.monto,
                trm=r.trm or 0,
                origen_fmt=origen_fmt,
                medio_pago=r.medio_pago,
                caja_nombre=(caja.nombre if caja else ""),
                shopping_ref=self._shopping_ref_text(r.shopping_group_id, r.shopping_item_id,
                                                     groups_by_id, items_by_id),
                recurrente=r.recurrente, notas=r.notas or "",
                color=COLOR_CATEGORIA.get(r.categoria, "#94a3b8"),
            ))
            total += r.monto
            por_cat[r.categoria] = por_cat.get(r.categoria, 0) + r.monto
            key = r.fecha.isoformat()
            por_dia[key] = por_dia.get(key, 0) + r.monto
            count_dia[key] = count_dia.get(key, 0) + 1

        self.rows = rows
        self.total_mes = total
        self.por_categoria = [
            {"nombre": c, "total": v, "color": COLOR_CATEGORIA.get(c, "#94a3b8"),
             "pct": (v / total * 100) if total > 0 else 0}
            for c, v in sorted(por_cat.items(), key=lambda x: -x[1])
        ]

        # ── Generar grid de calendario (lunes a domingo, 6 filas × 7) ──
        self.celdas = self._build_calendario(per.mes, per.anio, por_dia, count_dia)

    def _build_calendario(self, mes: int, anio: int, por_dia: dict, count_dia: dict) -> list[DiaCelda]:
        # Primer día del mes, weekday (0 = lunes)
        primer = date(anio, mes, 1)
        start_weekday = primer.weekday()   # 0..6
        dias_mes = monthrange(anio, mes)[1]

        # Mes anterior para rellenar
        if mes == 1:
            prev_dias = monthrange(anio - 1, 12)[1]
            prev_mes, prev_anio = 12, anio - 1
        else:
            prev_dias = monthrange(anio, mes - 1)[1]
            prev_mes, prev_anio = mes - 1, anio

        celdas: list[DiaCelda] = []
        hoy_iso = date.today().isoformat()
        # Días del mes anterior
        for i in range(start_weekday):
            dia = prev_dias - start_weekday + 1 + i
            f = date(prev_anio, prev_mes, dia).isoformat()
            celdas.append(DiaCelda(dia=dia, fecha=f, total=0, total_fmt="",
                                   count=0, es_otro_mes=True,
                                   is_today=(f == hoy_iso)))

        # Días del mes actual
        for d in range(1, dias_mes + 1):
            f = date(anio, mes, d).isoformat()
            tot = por_dia.get(f, 0)
            celdas.append(DiaCelda(
                dia=d, fecha=f,
                total=tot,
                total_fmt=(f"${tot:,.0f}" if tot > 0 else ""),
                count=count_dia.get(f, 0),
                es_otro_mes=False,
                is_today=(f == hoy_iso),
            ))

        # Rellenar hasta 42 celdas (6 filas) con mes siguiente
        if mes == 12:
            next_mes, next_anio = 1, anio + 1
        else:
            next_mes, next_anio = mes + 1, anio

        d = 1
        while len(celdas) < 42:
            f = date(next_anio, next_mes, d).isoformat()
            celdas.append(DiaCelda(dia=d, fecha=f, total=0, total_fmt="",
                                   count=0, es_otro_mes=True,
                                   is_today=(f == hoy_iso)))
            d += 1
        return celdas

    @rx.event
    def toggle_form(self):
        self.form_open = not self.form_open
        self.form_msg = ""
        if self.form_open:
            self.form_editing_id = None
            self.form_desc = ""
            self.form_monto = 0.0
            self.form_moneda = "COP"
            self.form_monto_original = 0.0
            self.form_trm = 0.0
            self.form_notas = ""
            self.form_recurrente = False
            self.form_caja_id = 0
            self.form_shopping_group_id = 0
            self.form_shopping_item_id = 0
            self.form_shopping_pct = 100.0
            self._refresh_shopping_items_opts()

    def _shopping_ref_text(self, group_id, item_id, groups_by_id, items_by_id) -> str:
        item = items_by_id.get(item_id) if item_id else None
        if item:
            return f"{item.nombre}"
        grp = groups_by_id.get(group_id) if group_id else None
        if grp:
            return f"Lista: {grp.nombre}"
        return ""

    def _refresh_shopping_items_opts(self):
        gid = int(self.form_shopping_group_id or 0)
        if gid <= 0:
            self.shopping_items_opts = []
            return
        self.shopping_items_opts = [
            {"id": it["id"], "etiqueta": it["etiqueta"]}
            for it in self.shopping_items_all
            if int(it.get("group_id", 0)) == gid
        ]

    @rx.event
    def set_form_shopping_group_id(self, value):
        try:
            self.form_shopping_group_id = int(value) if value not in ("", None) else 0
        except (TypeError, ValueError):
            self.form_shopping_group_id = 0
        self.form_shopping_item_id = 0
        self._refresh_shopping_items_opts()

    @rx.event
    def aplicar_item_lista(self):
        item_id = int(self.form_shopping_item_id or 0)
        if item_id <= 0:
            self.form_msg = "⚠ Selecciona un ítem de lista."
            return
        item = next((it for it in self.shopping_items_all if int(it["id"]) == item_id), None)
        if not item:
            self.form_msg = "⚠ Ítem no encontrado."
            return
        pct = float(self.form_shopping_pct or 100)
        pct = max(1.0, min(100.0, pct))
        self.form_shopping_pct = pct
        monto = float(item["monto"]) * (pct / 100.0)
        self.form_desc = str(item["nombre"]) + (" (parcial)" if pct < 100 else "")
        self.form_categoria = str(item.get("categoria") or "Otros")
        self.form_monto = monto
        self.form_moneda = "COP"
        self.form_monto_original = monto
        self.form_trm = 0.0
        self.form_msg = "✓ Ítem cargado al formulario."

    @rx.event
    def aplicar_grupo_lista(self):
        gid = int(self.form_shopping_group_id or 0)
        if gid <= 0:
            self.form_msg = "⚠ Selecciona un grupo de lista."
            return
        pendientes = [
            it for it in self.shopping_items_all
            if int(it.get("group_id", 0)) == gid and not bool(it.get("comprado", False))
        ]
        if not pendientes:
            self.form_msg = "ℹ Este grupo no tiene ítems pendientes."
            return
        pct = float(self.form_shopping_pct or 100)
        pct = max(1.0, min(100.0, pct))
        self.form_shopping_pct = pct
        monto_total = sum(float(it.get("monto", 0.0)) for it in pendientes) * (pct / 100.0)
        grp = next((g for g in self.shopping_groups_opts if int(g["id"]) == gid), None)
        gname = grp["nombre"] if grp else "Lista"
        self.form_desc = f"Lista: {gname}" + (" (parcial)" if pct < 100 else "")
        self.form_categoria = "Otros"
        self.form_monto = monto_total
        self.form_moneda = "COP"
        self.form_monto_original = monto_total
        self.form_trm = 0.0
        self.form_msg = "✓ Grupo cargado al formulario."

    @rx.event
    def set_form_moneda(self, value: str):
        self.form_moneda = value
        if value == "USD" and self.form_trm <= 0:
            # Obtener TRM actual al cambiar a USD
            trm = obtener_trm(self.form_fecha)
            if trm > 0:
                self.form_trm = trm
                self._recalcular_monto_cop()

    @rx.event
    def refrescar_trm(self):
        trm = obtener_trm(self.form_fecha)
        if trm > 0:
            self.form_trm = trm
            self._recalcular_monto_cop()
            self.form_msg = f"✓ TRM actualizada: ${trm:,.2f}"
        else:
            self.form_msg = "⚠ No se pudo obtener la TRM."

    @rx.event
    def set_form_monto_original(self, value):
        try:
            self.form_monto_original = float(value) if value not in ("", None) else 0.0
        except (TypeError, ValueError):
            self.form_monto_original = 0.0
        self._recalcular_monto_cop()

    def _recalcular_monto_cop(self):
        if self.form_moneda == "USD":
            self.form_monto = self.form_monto_original * self.form_trm
        # Si es COP, form_monto se setea directamente por su setter

    @rx.event
    def seleccionar_dia(self, fecha: str):
        # Toggle: click dos veces limpia
        if self.dia_seleccionado == fecha:
            self.dia_seleccionado = ""
        else:
            self.dia_seleccionado = fecha
            self.form_fecha = fecha

    @rx.event
    def limpiar_filtro(self):
        self.dia_seleccionado = ""

    @rx.event
    async def guardar(self):
        if not self.form_desc.strip():
            self.form_msg = "⚠ La descripción es obligatoria."
            return

        # Calcular monto COP final según moneda
        if self.form_moneda == "USD":
            if self.form_monto_original <= 0:
                self.form_msg = "⚠ El monto en USD debe ser mayor a 0."
                return
            if self.form_trm <= 0:
                # Permite ingresar TRM manual cuando la API no respondió.
                self.form_msg = (
                    "⚠ TRM no disponible. Ingresa la TRM manualmente "
                    "(campo TRM) y vuelve a guardar."
                )
                return
            monto_cop = self.form_monto_original * self.form_trm
            monto_original = self.form_monto_original
            trm = self.form_trm
        else:
            if self.form_monto <= 0:
                self.form_msg = "⚠ El monto debe ser mayor a 0."
                return
            monto_cop = self.form_monto
            monto_original = self.form_monto
            trm = 0.0

        caja_id = self.form_caja_id if self.form_caja_id > 0 else None
        shopping_group_id = self.form_shopping_group_id if self.form_shopping_group_id > 0 else None
        shopping_item_id = self.form_shopping_item_id if self.form_shopping_item_id > 0 else None
        shopping_pct = float(self.form_shopping_pct or 100.0)

        with rx.session() as s:
            if self.form_editing_id:
                row = s.get(Gasto, self.form_editing_id)
                if row:
                    row.fecha = date.fromisoformat(self.form_fecha)
                    row.descripcion = self.form_desc.strip()
                    row.categoria = self.form_categoria
                    row.monto = monto_cop
                    row.moneda = self.form_moneda
                    row.monto_original = monto_original
                    row.trm = trm
                    row.medio_pago = self.form_medio
                    row.caja_id = caja_id
                    row.shopping_group_id = shopping_group_id
                    row.shopping_item_id = shopping_item_id
                    row.shopping_pct = shopping_pct
                    row.recurrente = self.form_recurrente
                    row.notas = self.form_notas
                    s.add(row)
            else:
                s.add(Gasto(
                    fecha=date.fromisoformat(self.form_fecha),
                    descripcion=self.form_desc.strip(),
                    categoria=self.form_categoria,
                    monto=monto_cop,
                    moneda=self.form_moneda,
                    monto_original=monto_original,
                    trm=trm,
                    medio_pago=self.form_medio,
                    caja_id=caja_id,
                    shopping_group_id=shopping_group_id,
                    shopping_item_id=shopping_item_id,
                    shopping_pct=shopping_pct,
                    recurrente=self.form_recurrente,
                    notas=self.form_notas,
                ))

            # Si se guardó un gasto con un ítem completo de lista, lo marca comprado.
            if shopping_item_id and shopping_pct >= 99.99:
                it = s.get(ShoppingItem, shopping_item_id)
                if it:
                    it.comprado = True
                    s.add(it)
            s.commit()

        self.form_open = False
        self.form_editing_id = None
        self.form_msg = ""
        await self.load()

    @rx.event
    async def editar(self, rid: int):
        with rx.session() as s:
            row = s.get(Gasto, rid)
            if row:
                self.form_editing_id = rid
                self.form_fecha = row.fecha.isoformat()
                self.form_desc = row.descripcion
                self.form_categoria = row.categoria
                self.form_monto = row.monto
                self.form_moneda = row.moneda or "COP"
                self.form_monto_original = row.monto_original or row.monto
                self.form_trm = row.trm or 0.0
                self.form_medio = row.medio_pago
                self.form_caja_id = row.caja_id or 0
                self.form_shopping_group_id = row.shopping_group_id or 0
                self.form_shopping_item_id = row.shopping_item_id or 0
                self.form_shopping_pct = row.shopping_pct or 100.0
                self._refresh_shopping_items_opts()
                self.form_recurrente = row.recurrente
                self.form_notas = row.notas or ""
                self.form_open = True

    @rx.event
    async def eliminar(self, rid: int):
        with rx.session() as s:
            row = s.get(Gasto, rid)
            if row:
                s.delete(row)
                s.commit()
        await self.load()
