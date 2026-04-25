"""State para gestión de listas/grupos de compra."""
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from cuentas_pro.models import ShoppingGroup, ShoppingItem
from cuentas_pro.finance import CATEGORIAS_GASTO
from cuentas_pro.services import auto_rellenar_desde_url
from cuentas_pro.state._autosetters import auto_setters


class ShoppingGroupRow(BaseModel):
    id: int
    nombre: str
    categoria_default: str
    activa: bool
    total_estimado: float
    total_estimado_fmt: str
    pendientes: int


class ShoppingItemRow(BaseModel):
    id: int
    group_id: int
    group_nombre: str
    nombre: str
    categoria: str
    monto_estimado: float
    monto_fmt: str
    comprado: bool
    activo: bool
    notas: str
    imagen_url: str
    link: str


@auto_setters
class ComprasState(rx.State):
    groups: list[ShoppingGroupRow] = []
    items: list[ShoppingItemRow] = []

    # Form grupo
    form_group_nombre: str = ""
    form_group_categoria: str = "Otros"
    form_group_notas: str = ""
    form_group_msg: str = ""

    # Form item
    form_item_group_id: int = 0
    form_item_nombre: str = ""
    form_item_categoria: str = "Otros"
    form_item_monto: float = 0.0
    form_item_notas: str = ""
    form_item_link: str = ""
    form_item_imagen: str = ""
    form_item_msg: str = ""
    form_item_msg_kind: str = ""  # ok | warn | err
    autorrellenando: bool = False

    @rx.var
    def categorias_gasto(self) -> list[str]:
        return CATEGORIAS_GASTO

    @rx.event
    async def load(self):
        with rx.session() as s:
            groups = s.exec(
                sqlmodel.select(ShoppingGroup)
                .where(ShoppingGroup.activa == True)
                .order_by(sqlmodel.desc(ShoppingGroup.id))
            ).all()
            items = s.exec(
                sqlmodel.select(ShoppingItem)
                .where(ShoppingItem.activo == True)
                .order_by(sqlmodel.desc(ShoppingItem.id))
            ).all()

        by_group: dict[int, dict] = {}
        for g in groups:
            by_group[g.id] = {"nombre": g.nombre, "total": 0.0, "pend": 0}

        rows_items: list[ShoppingItemRow] = []
        for it in items:
            gname = by_group.get(it.group_id, {}).get("nombre", "?")
            rows_items.append(ShoppingItemRow(
                id=it.id,
                group_id=it.group_id,
                group_nombre=gname,
                nombre=it.nombre,
                categoria=it.categoria or "Otros",
                monto_estimado=it.monto_estimado or 0.0,
                monto_fmt=f"${(it.monto_estimado or 0.0):,.0f}",
                comprado=bool(it.comprado),
                activo=bool(it.activo),
                notas=it.notas or "",
                imagen_url=it.imagen_url or "",
                link=it.link or "",
            ))
            if it.group_id in by_group and not it.comprado:
                by_group[it.group_id]["total"] += float(it.monto_estimado or 0.0)
                by_group[it.group_id]["pend"] += 1

        rows_groups: list[ShoppingGroupRow] = []
        for g in groups:
            acc = by_group.get(g.id, {"total": 0.0, "pend": 0})
            rows_groups.append(ShoppingGroupRow(
                id=g.id,
                nombre=g.nombre,
                categoria_default=g.categoria_default or "Otros",
                activa=bool(g.activa),
                total_estimado=acc["total"],
                total_estimado_fmt=f"${acc['total']:,.0f}",
                pendientes=acc["pend"],
            ))

        self.groups = rows_groups
        self.items = rows_items

    @rx.event
    async def crear_grupo(self):
        if not self.form_group_nombre.strip():
            self.form_group_msg = "⚠ Nombre de grupo obligatorio."
            return
        with rx.session() as s:
            s.add(ShoppingGroup(
                nombre=self.form_group_nombre.strip(),
                categoria_default=self.form_group_categoria,
                notas=self.form_group_notas.strip(),
            ))
            s.commit()
        self.form_group_nombre = ""
        self.form_group_notas = ""
        self.form_group_msg = "✅ Grupo creado."
        await self.load()

    @rx.event
    async def crear_item(self):
        if self.form_item_group_id <= 0:
            self.form_item_msg = "⚠ Selecciona un grupo."
            return
        if not self.form_item_nombre.strip():
            self.form_item_msg = "⚠ Nombre del ítem obligatorio."
            return
        if self.form_item_monto <= 0:
            self.form_item_msg = "⚠ Monto estimado debe ser mayor a 0."
            return

        with rx.session() as s:
            s.add(ShoppingItem(
                group_id=self.form_item_group_id,
                nombre=self.form_item_nombre.strip(),
                categoria=self.form_item_categoria,
                monto_estimado=self.form_item_monto,
                notas=self.form_item_notas.strip(),
                imagen_url=self.form_item_imagen.strip(),
                link=self.form_item_link.strip(),
            ))
            s.commit()

        self.form_item_nombre = ""
        self.form_item_monto = 0.0
        self.form_item_notas = ""
        self.form_item_link = ""
        self.form_item_imagen = ""
        self.form_item_msg = "✅ Ítem agregado."
        self.form_item_msg_kind = "ok"
        await self.load()

    @rx.event(background=True)
    async def autorrellenar_link(self):
        """Descarga la URL y rellena nombre/imagen automáticamente.

        Corre en background para no bloquear la UI mientras se hace la
        petición HTTP (puede tardar 2-8 s).
        """
        async with self:
            link = self.form_item_link.strip()
            if not link:
                self.form_item_msg = "⚠ Pega primero un enlace."
                self.form_item_msg_kind = "warn"
                return
            self.autorrellenando = True
            self.form_item_msg = "⏳ Buscando datos…"
            self.form_item_msg_kind = ""

        try:
            data = auto_rellenar_desde_url(link)
        except Exception as e:  # noqa: BLE001
            data = {"nombre": "", "imagen_url": "", "link": link,
                    "fuente": "", "error": str(e)}

        async with self:
            self.autorrellenando = False
            self.form_item_link = data.get("link") or link
            if data.get("error"):
                self.form_item_msg = f"⚠ {data['error']}"
                self.form_item_msg_kind = "err"
                return
            if data.get("nombre") and not self.form_item_nombre.strip():
                self.form_item_nombre = data["nombre"]
            if data.get("imagen_url"):
                self.form_item_imagen = data["imagen_url"]
            fuente = data.get("fuente") or "web"
            self.form_item_msg = f"✓ Datos cargados (fuente: {fuente}). Falta el precio."
            self.form_item_msg_kind = "ok"

    @rx.event
    def limpiar_link(self):
        self.form_item_link = ""
        self.form_item_imagen = ""
        self.form_item_msg = ""
        self.form_item_msg_kind = ""

    @rx.event
    async def toggle_item_comprado(self, item_id: int):
        with rx.session() as s:
            it = s.get(ShoppingItem, item_id)
            if not it:
                return
            it.comprado = not bool(it.comprado)
            s.add(it)
            s.commit()
        await self.load()

    @rx.event
    async def eliminar_item(self, item_id: int):
        with rx.session() as s:
            it = s.get(ShoppingItem, item_id)
            if it:
                it.activo = False
                s.add(it)
                s.commit()
        await self.load()

    @rx.event
    async def eliminar_grupo(self, group_id: int):
        with rx.session() as s:
            g = s.get(ShoppingGroup, group_id)
            if g:
                g.activa = False
                s.add(g)
                # También ocultar ítems activos del grupo
                for it in s.exec(sqlmodel.select(ShoppingItem).where(ShoppingItem.group_id == group_id)).all():
                    it.activo = False
                    s.add(it)
                s.commit()
        await self.load()
