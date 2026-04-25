"""State para gestión de listas/grupos de compra."""
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from cuentas_pro.models import ShoppingGroup, ShoppingItem
from cuentas_pro.finance import CATEGORIAS_GASTO
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
    form_item_msg: str = ""

    @rx.var
    def categorias_gasto(self) -> list[str]:
        return CATEGORIAS_GASTO

    @rx.event
    def load(self):
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
    def crear_grupo(self):
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
        self.load()

    @rx.event
    def crear_item(self):
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
            ))
            s.commit()

        self.form_item_nombre = ""
        self.form_item_monto = 0.0
        self.form_item_notas = ""
        self.form_item_msg = "✅ Ítem agregado."
        self.load()

    @rx.event
    def toggle_item_comprado(self, item_id: int):
        with rx.session() as s:
            it = s.get(ShoppingItem, item_id)
            if not it:
                return
            it.comprado = not bool(it.comprado)
            s.add(it)
            s.commit()
        self.load()

    @rx.event
    def eliminar_item(self, item_id: int):
        with rx.session() as s:
            it = s.get(ShoppingItem, item_id)
            if it:
                it.activo = False
                s.add(it)
                s.commit()
        self.load()

    @rx.event
    def eliminar_grupo(self, group_id: int):
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
        self.load()
