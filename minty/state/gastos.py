"""State de Gastos."""
import uuid
from datetime import date, timedelta
from calendar import monthrange
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from minty.models import Gasto, Caja, ShoppingGroup, ShoppingItem
from minty.finance import CATEGORIAS_GASTO, COLOR_CATEGORIA, MEDIOS_PAGO, MONEDAS
from minty.services import obtener_trm, obtener_tasa_a_cop
from minty.state.periodo import PeriodoState
from minty.state._autosetters import auto_setters


def _avanzar_meses(f: date, n: int) -> date:
    """Suma ``n`` meses a ``f`` respetando el fin de mes."""
    if n == 0:
        return f
    y, m = f.year, f.month + n
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    d = min(f.day, monthrange(y, m)[1])
    return date(y, m, d)


def _avanzar_periodo(f: date, unidad: str, intervalo: int) -> date:
    """Devuelve la siguiente ocurrencia avanzando ``intervalo`` unidades."""
    intervalo = max(1, int(intervalo or 1))
    u = (unidad or "mes").lower()
    from datetime import timedelta
    if u == "dia":
        return f + timedelta(days=intervalo)
    if u == "semana":
        return f + timedelta(weeks=intervalo)
    if u == "anio" or u == "año":
        return _avanzar_meses(f, intervalo * 12)
    # default: mes
    return _avanzar_meses(f, intervalo)


def _label_recurrencia(unidad: str, intervalo: int) -> str:
    """Etiqueta humana corta para la recurrencia (ej. 'cada 2 meses')."""
    intervalo = max(1, int(intervalo or 1))
    u = (unidad or "mes").lower()
    nombres = {
        "dia": ("día", "días"),
        "semana": ("semana", "semanas"),
        "mes": ("mes", "meses"),
        "anio": ("año", "años"),
        "año": ("año", "años"),
    }
    sing, plur = nombres.get(u, ("mes", "meses"))
    if intervalo == 1:
        return f"cada {sing}"
    return f"cada {intervalo} {plur}"


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
    recurrencia_label: str  # "cada 2 meses" o "" si no es recurrente
    cuotas_label: str  # "2/4" si es cuota, "" si no
    compra_id: str     # uuid agrupador de cuotas ("" si no es a cuotas)
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
    busqueda: str = ""          # filtro de texto libre

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
    # Recurrencia avanzada
    form_recurrencia_unidad: str = "mes"   # dia|semana|mes|anio
    form_recurrencia_intervalo: int = 1
    # Cuotas: 1 = pago único. >1 = se generan N gastos mensuales
    # con monto = total/cuotas, fechas avanzando un mes cada vez.
    form_cuotas: int = 1
    form_notas: str = ""
    form_editing_id: Optional[int] = None
    form_msg: str = ""
    # Confirmación cuando se detecta un posible duplicado.
    form_confirmar_duplicado: bool = False

    # Cajas disponibles (cache ligero para el selector)
    cajas_opts: list[dict] = []
    shopping_groups_opts: list[dict] = []
    shopping_items_all: list[dict] = []
    shopping_items_opts: list[dict] = []

    @rx.var(cache=True)
    def rows_filtradas(self) -> list[GastoRow]:
        data = self.rows
        if self.dia_seleccionado != "":
            data = [r for r in data if r.fecha == self.dia_seleccionado]
        if self.busqueda.strip():
            q = self.busqueda.strip().lower()
            data = [
                r for r in data
                if q in r.descripcion.lower()
                or q in r.categoria.lower()
                or q in (r.notas or "").lower()
                or q in (r.medio_pago or "").lower()
                or q in (r.caja_nombre or "").lower()
            ]
        return data

    @rx.event
    def limpiar_busqueda(self):
        self.busqueda = ""

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
            if r.moneda and r.moneda != "COP" and r.monto_original:
                origen_fmt = f"{r.moneda} {r.monto_original:,.2f} @ {r.trm:,.0f}"
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
                recurrente=r.recurrente,
                recurrencia_label=(
                    _label_recurrencia(r.recurrencia_unidad or "mes",
                                       r.recurrencia_intervalo or 1)
                    if r.recurrente else ""
                ),
                cuotas_label=(
                    f"{r.cuota_num}/{r.cuotas_total}"
                    if (r.cuotas_total or 0) > 1 and (r.cuota_num or 0) > 0
                    else ""
                ),
                compra_id=(r.compra_id or ""),
                notas=r.notas or "",
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
        self.form_confirmar_duplicado = False
        if self.form_open:
            self.form_editing_id = None
            self.form_desc = ""
            self.form_monto = 0.0
            self.form_moneda = "COP"
            self.form_monto_original = 0.0
            self.form_trm = 0.0
            self.form_notas = ""
            self.form_recurrente = False
            self.form_recurrencia_unidad = "mes"
            self.form_recurrencia_intervalo = 1
            self.form_cuotas = 1
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
    def set_form_shopping_item_id(self, value):
        """Al seleccionar un ítem de lista, auto-carga monto/desc/categoría."""
        try:
            self.form_shopping_item_id = int(value) if value not in ("", None) else 0
        except (TypeError, ValueError):
            self.form_shopping_item_id = 0
        if self.form_shopping_item_id > 0:
            # Reutiliza la lógica de "Cargar ítem".
            self.aplicar_item_lista()

    @rx.event
    def set_form_cuotas(self, value):
        """A cuotas > 1, recurrente deja de tener sentido: lo apaga."""
        try:
            v = int(float(value)) if value not in ("", None) else 1
        except (TypeError, ValueError):
            v = 1
        self.form_cuotas = max(1, v)
        if self.form_cuotas > 1:
            self.form_recurrente = False

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
        # Para cualquier moneda no-COP intenta obtener tasa automáticamente.
        if value != "COP" and self.form_trm <= 0:
            # Si la caja seleccionada es una TC con TRM propio configurado,
            # úsalo en vez de la tasa de mercado (los bancos cobran con su
            # propio TRM, no con el oficial).
            trm_tc = self._trm_de_caja_tc(self.form_caja_id)
            if trm_tc > 0:
                self.form_trm = trm_tc
                self._recalcular_monto_cop()
                return
            tasa = obtener_tasa_a_cop(value, self.form_fecha)
            if tasa > 0:
                self.form_trm = tasa
                self._recalcular_monto_cop()

    @rx.event
    def set_form_caja_id(self, value):
        try:
            cid = int(value) if value not in ("", None) else 0
        except (TypeError, ValueError):
            cid = 0
        self.form_caja_id = cid
        # Si la caja es una TC con TRM propio y la moneda actual es no-COP,
        # aplica el TRM del banco automáticamente.
        if self.form_moneda != "COP":
            trm_tc = self._trm_de_caja_tc(cid)
            if trm_tc > 0:
                self.form_trm = trm_tc
                self._recalcular_monto_cop()

    @rx.event
    def aplicar_trm_tc_form(self):
        """Forza el uso del TRM propio de la TC seleccionada (botón manual)."""
        if self.form_caja_id <= 0:
            self.form_msg = "⚠ Selecciona primero la caja TC."
            return
        trm_tc = self._trm_de_caja_tc(self.form_caja_id)
        if trm_tc <= 0:
            self.form_msg = "⚠ La caja seleccionada no es TC o no tiene TRM propio configurado."
            return
        self.form_trm = trm_tc
        self._recalcular_monto_cop()
        self.form_msg = f"✓ TRM TC aplicado: ${trm_tc:,.2f}"

    def _trm_de_caja_tc(self, caja_id: int) -> float:
        if not caja_id or caja_id <= 0:
            return 0.0
        try:
            with rx.session() as s:
                c = s.get(Caja, caja_id)
                if not c or c.tipo != "tarjeta_credito":
                    return 0.0
                return float(c.trm_tc or 0.0)
        except Exception:
            return 0.0

    @rx.event
    def refrescar_trm(self):
        if self.form_moneda == "COP":
            self.form_msg = "ℹ La moneda actual es COP, no requiere tasa."
            return
        tasa = obtener_tasa_a_cop(self.form_moneda, self.form_fecha)
        if tasa > 0:
            self.form_trm = tasa
            self._recalcular_monto_cop()
            self.form_msg = f"✓ Tasa {self.form_moneda}→COP actualizada: ${tasa:,.2f}"
        else:
            self.form_msg = f"⚠ No se pudo obtener la tasa para {self.form_moneda}."

    @rx.event
    def set_form_monto_original(self, value):
        try:
            self.form_monto_original = float(value) if value not in ("", None) else 0.0
        except (TypeError, ValueError):
            self.form_monto_original = 0.0
        self._recalcular_monto_cop()

    def _recalcular_monto_cop(self):
        if self.form_moneda != "COP":
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
        if self.form_moneda != "COP":
            if self.form_monto_original <= 0:
                self.form_msg = f"⚠ El monto en {self.form_moneda} debe ser mayor a 0."
                return
            if self.form_trm <= 0:
                # Permite ingresar tasa manual cuando la API no respondió.
                self.form_msg = (
                    f"⚠ Tasa {self.form_moneda}→COP no disponible. Ingrésala "
                    "manualmente y vuelve a guardar."
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

        # ── Detección de duplicados (solo al CREAR) ──
        # Si ya existe un gasto con la misma fecha, descripción y monto,
        # pedimos confirmación para evitar capturas dobles accidentales.
        if not self.form_editing_id and not self.form_confirmar_duplicado:
            fecha_obj = date.fromisoformat(self.form_fecha)
            desc_norm = self.form_desc.strip().lower()
            with rx.session() as s:
                candidatos = s.exec(
                    sqlmodel.select(Gasto).where(
                        Gasto.fecha == fecha_obj,
                        Gasto.monto == monto_cop,
                    )
                ).all()
            for c in candidatos:
                if (c.descripcion or "").strip().lower() == desc_norm:
                    self.form_msg = (
                        "⚠ Posible duplicado: ya existe un gasto idéntico hoy. "
                        "Pulsa Guardar nuevamente para confirmar."
                    )
                    self.form_confirmar_duplicado = True
                    return

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
                    row.recurrencia_unidad = (
                        self.form_recurrencia_unidad if self.form_recurrente else ""
                    )
                    row.recurrencia_intervalo = (
                        max(1, int(self.form_recurrencia_intervalo or 1))
                        if self.form_recurrente else 1
                    )
                    row.notas = self.form_notas
                    s.add(row)
            else:
                cuotas = max(1, int(self.form_cuotas or 1))
                if cuotas > 1:
                    # ── Compra a cuotas: generar N gastos mensuales ──
                    compra_id = uuid.uuid4().hex[:12]
                    monto_cuota = round(monto_cop / cuotas)
                    monto_orig_cuota = (
                        round(monto_original / cuotas, 2)
                        if self.form_moneda != "COP" else monto_cuota
                    )
                    # Ajuste para que la suma cuadre exactamente con el total.
                    delta = monto_cop - monto_cuota * cuotas
                    fecha0 = date.fromisoformat(self.form_fecha)
                    desc_base = self.form_desc.strip()
                    for i in range(cuotas):
                        f_i = _avanzar_meses(fecha0, i)
                        m_i = monto_cuota + (delta if i == cuotas - 1 else 0)
                        mo_i = (
                            monto_orig_cuota + (
                                round(monto_original - monto_orig_cuota * cuotas, 2)
                                if self.form_moneda != "COP" else 0
                            )
                            if i == cuotas - 1 else monto_orig_cuota
                        )
                        s.add(Gasto(
                            fecha=f_i,
                            descripcion=f"{desc_base} ({i + 1}/{cuotas})",
                            categoria=self.form_categoria,
                            monto=m_i,
                            moneda=self.form_moneda,
                            monto_original=mo_i,
                            trm=trm,
                            medio_pago=self.form_medio,
                            caja_id=caja_id,
                            shopping_group_id=shopping_group_id,
                            shopping_item_id=shopping_item_id,
                            shopping_pct=shopping_pct,
                            recurrente=False,           # cuotas NO se replican
                            cuotas_total=cuotas,
                            cuota_num=i + 1,
                            compra_id=compra_id,
                            notas=self.form_notas,
                        ))
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
                        recurrencia_unidad=(
                            self.form_recurrencia_unidad if self.form_recurrente else ""
                        ),
                        recurrencia_intervalo=(
                            max(1, int(self.form_recurrencia_intervalo or 1))
                            if self.form_recurrente else 1
                        ),
                        notas=self.form_notas,
                    ))

            # Si se guardó un gasto con un ítem completo de lista, lo marca comprado
            # — excepto si el ítem es recurrente (mercado, etc.), que no se "agota".
            if shopping_item_id and shopping_pct >= 99.99:
                it = s.get(ShoppingItem, shopping_item_id)
                if it and not bool(getattr(it, "recurrente", False)):
                    it.comprado = True
                    s.add(it)
            s.commit()

        self.form_open = False
        self.form_editing_id = None
        self.form_msg = ""
        self.form_confirmar_duplicado = False
        self.form_cuotas = 1
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
                self.form_recurrencia_unidad = row.recurrencia_unidad or "mes"
                self.form_recurrencia_intervalo = max(1, int(row.recurrencia_intervalo or 1))
                self.form_cuotas = 1  # al editar, no se vuelve a dividir
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

    @rx.event
    async def eliminar_compra(self, compra_id: str):
        """Elimina TODAS las cuotas de una compra (mismo ``compra_id``)."""
        cid = (compra_id or "").strip()
        if not cid:
            return
        with rx.session() as s:
            filas = s.exec(
                sqlmodel.select(Gasto).where(Gasto.compra_id == cid)
            ).all()
            n = 0
            for f in filas:
                s.delete(f)
                n += 1
            s.commit()
        self.form_msg = f"✓ {n} cuota(s) eliminada(s) de la compra."
        await self.load()

    @rx.event
    async def generar_recurrentes(self):
        """Genera las ocurrencias de gastos recurrentes que caen en el periodo activo.

        Para cada Gasto con ``recurrente=True``, se calculan las fechas
        siguientes a partir de ``fecha`` avanzando ``recurrencia_intervalo``
        unidades de ``recurrencia_unidad`` (día/semana/mes/año) hasta llegar
        al final del periodo. Las que caigan dentro del periodo activo se
        crean como copias (``recurrente=False`` para no encadenar).

        Es idempotente: omite copias si ya existe un gasto con la misma
        descripción, monto y fecha.
        """
        per = await self.get_state(PeriodoState)
        ini_dest = date.fromisoformat(per.fecha_inicio)
        fin_dest = date.fromisoformat(per.fecha_fin)

        creados = 0
        omitidos = 0
        # Tope de seguridad: evita bucles infinitos por configuraciones raras.
        _MAX_ITER = 5000

        with rx.session() as s:
            recurrentes = s.exec(
                sqlmodel.select(Gasto).where(
                    Gasto.recurrente == True,  # noqa: E712
                    Gasto.fecha < fin_dest,
                )
            ).all()

            existentes = s.exec(
                sqlmodel.select(Gasto).where(
                    Gasto.fecha >= ini_dest,
                    Gasto.fecha < fin_dest,
                )
            ).all()
            claves_existentes = {
                ((g.descripcion or "").strip().lower(),
                 round(g.monto or 0.0, 2),
                 g.fecha.isoformat())
                for g in existentes
            }

            for g in recurrentes:
                unidad = g.recurrencia_unidad or "mes"
                intervalo = max(1, int(g.recurrencia_intervalo or 1))
                # Avanza desde la fecha original hasta el periodo destino.
                f = g.fecha
                it = 0
                while f < ini_dest and it < _MAX_ITER:
                    f = _avanzar_periodo(f, unidad, intervalo)
                    it += 1
                # Genera todas las ocurrencias que caigan dentro del periodo.
                while ini_dest <= f < fin_dest and it < _MAX_ITER:
                    clave = (
                        (g.descripcion or "").strip().lower(),
                        round(g.monto or 0.0, 2),
                        f.isoformat(),
                    )
                    if clave in claves_existentes:
                        omitidos += 1
                    else:
                        s.add(Gasto(
                            fecha=f,
                            descripcion=g.descripcion,
                            categoria=g.categoria,
                            monto=g.monto,
                            moneda=g.moneda or "COP",
                            monto_original=g.monto_original or g.monto,
                            trm=g.trm or 0.0,
                            medio_pago=g.medio_pago,
                            caja_id=g.caja_id,
                            shopping_group_id=None,
                            shopping_item_id=None,
                            shopping_pct=100.0,
                            recurrente=False,  # las copias NO encadenan
                            recurrencia_unidad="",
                            recurrencia_intervalo=1,
                            notas=g.notas or "",
                        ))
                        creados += 1
                        claves_existentes.add(clave)
                    f = _avanzar_periodo(f, unidad, intervalo)
                    it += 1

            # ── Cuotas de manejo de tarjetas de crédito ──
            # Solo crear si la fecha del cobro YA pasó (no anticipar cuotas
            # futuras: la TC es una cuenta global y duplicaría/inflaría deuda).
            hoy_real = date.today()
            tcs = s.exec(
                sqlmodel.select(Caja).where(
                    Caja.tipo == "tarjeta_credito",
                    Caja.activa == True,  # noqa: E712
                )
            ).all()
            cuotas_creadas = 0
            for c in tcs:
                cuota = float(c.cuota_manejo or 0)
                if cuota <= 0:
                    continue
                dia_obj = max(1, min(31, c.dia_cobro_cuota or 1))
                # Fecha del cobro dentro del periodo destino (cap a fin de mes).
                try:
                    fecha_cuota = ini_dest.replace(day=dia_obj)
                except ValueError:
                    next_m = ini_dest.replace(day=28) + timedelta(days=4)
                    fecha_cuota = (next_m.replace(day=1)) - timedelta(days=1)
                if not (ini_dest <= fecha_cuota < fin_dest):
                    continue
                if fecha_cuota > hoy_real:
                    # No anticipar cobros futuros.
                    continue
                desc = f"Cuota de manejo {c.nombre}"
                clave = (desc.strip().lower(), round(cuota, 2),
                         fecha_cuota.isoformat())
                if clave in claves_existentes:
                    omitidos += 1
                    continue
                s.add(Gasto(
                    fecha=fecha_cuota,
                    descripcion=desc,
                    categoria="Servicios",
                    monto=cuota,
                    moneda="COP",
                    monto_original=cuota,
                    medio_pago="Tarjeta de crédito",
                    caja_id=c.id,
                    recurrente=False,
                    recurrencia_unidad="",
                    recurrencia_intervalo=1,
                    notas="[AUTO] Cuota de manejo mensual",
                ))
                claves_existentes.add(clave)
                cuotas_creadas += 1
            creados += cuotas_creadas

            s.commit()

        if creados == 0 and omitidos == 0:
            self.form_msg = "ℹ No hay gastos recurrentes que apliquen al periodo."
        else:
            self.form_msg = (
                f"✓ {creados} gasto(s) recurrente(s) generado(s)."
                + (f" {omitidos} ya exist\u00edan." if omitidos else "")
            )
        await self.load()

    @rx.event
    async def exportar_csv(self):
        """Genera CSV con los gastos del periodo activo y lo descarga."""
        per = await self.get_state(PeriodoState)
        ini = date.fromisoformat(per.fecha_inicio)
        fin = date.fromisoformat(per.fecha_fin)
        with rx.session() as s:
            gastos = s.exec(
                sqlmodel.select(Gasto)
                .where(Gasto.fecha >= ini, Gasto.fecha < fin)
                .order_by(Gasto.fecha)
            ).all()
            cajas_by_id = {
                c.id: c.nombre
                for c in s.exec(sqlmodel.select(Caja)).all()
            }

        headers = [
            "Fecha", "Descripción", "Categoría", "Monto (COP)",
            "Moneda", "Monto original", "TRM", "Medio de pago",
            "Caja", "Recurrente", "Notas",
        ]
        filas = [
            (
                g.fecha.isoformat(),
                g.descripcion,
                g.categoria,
                f"{g.monto:.2f}",
                g.moneda or "COP",
                f"{(g.monto_original or 0):.2f}",
                f"{(g.trm or 0):.2f}",
                g.medio_pago,
                cajas_by_id.get(g.caja_id, "") if g.caja_id else "",
                "Sí" if g.recurrente else "No",
                (g.notas or "").replace("\n", " ").replace("\r", " "),
            )
            for g in gastos
        ]
        from minty.services import filas_a_csv

        data = filas_a_csv(headers, filas)
        nombre = f"gastos-{per.anio:04d}-{per.mes:02d}.csv"
        return rx.download(data=data, filename=nombre)
