"""State para gestión de listas/grupos de compra."""
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

import reflex as rx
import sqlmodel
from pydantic import BaseModel

from minty.models import ShoppingGroup, ShoppingItem
from minty.finance import CATEGORIAS_GASTO
from minty.services import auto_rellenar_desde_url
from minty.state._autosetters import auto_setters

log = logging.getLogger(__name__)

_EXT_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_BYTES_IMG = 5 * 1024 * 1024  # 5 MB


class ShoppingGroupRow(BaseModel):
    id: int
    nombre: str
    categoria_default: str
    activa: bool
    recurrente: bool
    notas: str
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
    recurrente: bool
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
    form_group_recurrente: bool = False
    form_group_editing_id: int = 0
    form_group_msg: str = ""

    # Form item
    form_item_group_id: int = 0
    form_item_nombre: str = ""
    form_item_categoria: str = "Otros"
    form_item_monto: float = 0.0
    form_item_notas: str = ""
    form_item_link: str = ""
    form_item_imagen: str = ""
    form_item_recurrente: bool = False
    form_item_editing_id: int = 0
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
            es_recurrente = bool(it.recurrente)
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
                recurrente=es_recurrente,
                notas=it.notas or "",
                imagen_url=it.imagen_url or "",
                link=it.link or "",
            ))
            # Recurrentes siempre cuentan como pendientes (nunca se "acaban").
            if it.group_id in by_group and (not it.comprado or es_recurrente):
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
                recurrente=bool(g.recurrente),
                notas=g.notas or "",
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
            if self.form_group_editing_id > 0:
                g = s.get(ShoppingGroup, self.form_group_editing_id)
                if not g:
                    self.form_group_msg = "⚠ Grupo no encontrado."
                    return
                g.nombre = self.form_group_nombre.strip()
                g.categoria_default = self.form_group_categoria
                g.notas = self.form_group_notas.strip()
                g.recurrente = bool(self.form_group_recurrente)
                s.add(g)
                msg = "✅ Grupo actualizado."
            else:
                s.add(ShoppingGroup(
                    nombre=self.form_group_nombre.strip(),
                    categoria_default=self.form_group_categoria,
                    notas=self.form_group_notas.strip(),
                    recurrente=bool(self.form_group_recurrente),
                ))
                msg = "✅ Grupo creado."
            s.commit()
        self.form_group_nombre = ""
        self.form_group_notas = ""
        self.form_group_recurrente = False
        self.form_group_editing_id = 0
        self.form_group_msg = msg
        await self.load()

    @rx.event
    def editar_grupo(self, group_id: int):
        with rx.session() as s:
            g = s.get(ShoppingGroup, int(group_id))
            if not g:
                self.form_group_msg = "⚠ Grupo no encontrado."
                return
            self.form_group_editing_id = g.id
            self.form_group_nombre = g.nombre
            self.form_group_categoria = g.categoria_default or "Otros"
            self.form_group_notas = g.notas or ""
            self.form_group_recurrente = bool(g.recurrente)
            self.form_group_msg = f"✏️ Editando grupo: {g.nombre}"

    @rx.event
    def cancelar_edicion_grupo(self):
        self.form_group_editing_id = 0
        self.form_group_nombre = ""
        self.form_group_notas = ""
        self.form_group_categoria = "Otros"
        self.form_group_recurrente = False
        self.form_group_msg = ""

    @rx.event
    async def crear_item(self):
        if self.form_item_group_id <= 0:
            self.form_item_msg = "⚠ Selecciona un grupo."
            self.form_item_msg_kind = "warn"
            return
        if not self.form_item_nombre.strip():
            self.form_item_msg = "⚠ Nombre del ítem obligatorio."
            self.form_item_msg_kind = "warn"
            return
        if self.form_item_monto <= 0:
            self.form_item_msg = "⚠ Monto estimado debe ser mayor a 0."
            self.form_item_msg_kind = "warn"
            return

        with rx.session() as s:
            if self.form_item_editing_id > 0:
                it = s.get(ShoppingItem, self.form_item_editing_id)
                if not it:
                    self.form_item_msg = "⚠ Ítem no encontrado."
                    self.form_item_msg_kind = "err"
                    return
                it.group_id = self.form_item_group_id
                it.nombre = self.form_item_nombre.strip()
                it.categoria = self.form_item_categoria
                it.monto_estimado = self.form_item_monto
                it.notas = self.form_item_notas.strip()
                it.imagen_url = self.form_item_imagen.strip()
                it.link = self.form_item_link.strip()
                it.recurrente = bool(self.form_item_recurrente)
                s.add(it)
                msg = "✅ Ítem actualizado."
            else:
                s.add(ShoppingItem(
                    group_id=self.form_item_group_id,
                    nombre=self.form_item_nombre.strip(),
                    categoria=self.form_item_categoria,
                    monto_estimado=self.form_item_monto,
                    notas=self.form_item_notas.strip(),
                    imagen_url=self.form_item_imagen.strip(),
                    link=self.form_item_link.strip(),
                    recurrente=bool(self.form_item_recurrente),
                ))
                msg = "✅ Ítem agregado."
            s.commit()

        self.form_item_nombre = ""
        self.form_item_monto = 0.0
        self.form_item_notas = ""
        self.form_item_link = ""
        self.form_item_imagen = ""
        self.form_item_recurrente = False
        self.form_item_editing_id = 0
        self.form_item_msg = msg
        self.form_item_msg_kind = "ok"
        await self.load()

    @rx.event
    def editar_item(self, item_id: int):
        with rx.session() as s:
            it = s.get(ShoppingItem, int(item_id))
            if not it:
                self.form_item_msg = "⚠ Ítem no encontrado."
                self.form_item_msg_kind = "err"
                return
            self.form_item_editing_id = it.id
            self.form_item_group_id = it.group_id
            self.form_item_nombre = it.nombre
            self.form_item_categoria = it.categoria or "Otros"
            self.form_item_monto = float(it.monto_estimado or 0.0)
            self.form_item_notas = it.notas or ""
            self.form_item_link = it.link or ""
            self.form_item_imagen = it.imagen_url or ""
            self.form_item_recurrente = bool(it.recurrente)
            self.form_item_msg = f"✏️ Editando: {it.nombre}"
            self.form_item_msg_kind = ""

    @rx.event
    def cancelar_edicion_item(self):
        self.form_item_editing_id = 0
        self.form_item_nombre = ""
        self.form_item_monto = 0.0
        self.form_item_notas = ""
        self.form_item_link = ""
        self.form_item_imagen = ""
        self.form_item_recurrente = False
        self.form_item_msg = ""
        self.form_item_msg_kind = ""

    @rx.event
    async def toggle_item_recurrente(self, item_id: int):
        with rx.session() as s:
            it = s.get(ShoppingItem, int(item_id))
            if not it:
                return
            it.recurrente = not bool(it.recurrente)
            # Si pasa a recurrente, lo des-marca como comprado para que vuelva a aparecer.
            if it.recurrente:
                it.comprado = False
            s.add(it)
            s.commit()
        await self.load()

    @rx.event
    async def toggle_group_recurrente(self, group_id: int):
        with rx.session() as s:
            g = s.get(ShoppingGroup, int(group_id))
            if not g:
                return
            g.recurrente = not bool(g.recurrente)
            s.add(g)
            s.commit()
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
    def quitar_imagen(self):
        """Limpia solo la imagen (deja el link y el resto del formulario)."""
        self.form_item_imagen = ""

    @rx.event
    async def subir_imagen_local(self, files: list[rx.UploadFile]):
        """Guarda una imagen subida desde el equipo en el directorio de uploads
        de Reflex y la asigna como ``form_item_imagen``.
        """
        if not files:
            self.form_item_msg = "⚠ No se seleccionó ninguna imagen."
            self.form_item_msg_kind = "warn"
            return
        f = files[0]
        nombre_orig = getattr(f, "name", None) or getattr(f, "filename", "imagen.png")
        ext = Path(nombre_orig).suffix.lower()
        if ext not in _EXT_PERMITIDAS:
            self.form_item_msg = (
                f"⚠ Extensión no permitida ({ext or 'sin extensión'}). "
                f"Usa: {', '.join(sorted(_EXT_PERMITIDAS))}."
            )
            self.form_item_msg_kind = "err"
            return
        try:
            data = await f.read()
            if len(data) > _MAX_BYTES_IMG:
                self.form_item_msg = "⚠ La imagen supera 5 MB."
                self.form_item_msg_kind = "err"
                return
            upload_dir = Path(rx.get_upload_dir())
            upload_dir.mkdir(parents=True, exist_ok=True)
            destino = upload_dir / f"item-{uuid.uuid4().hex}{ext}"
            destino.write_bytes(data)
            # Reflex sirve los uploads en /_upload/<filename>
            self.form_item_imagen = f"/_upload/{destino.name}"
            self.form_item_msg = "✓ Imagen subida."
            self.form_item_msg_kind = "ok"
        except Exception as e:  # noqa: BLE001
            log.exception("Error subiendo imagen de ítem")
            self.form_item_msg = f"⚠ Error subiendo imagen: {e}"
            self.form_item_msg_kind = "err"

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
