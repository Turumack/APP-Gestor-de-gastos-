"""State Ba\u00fal (documentos / notas guardadas)."""
from typing import Optional
import reflex as rx
import sqlmodel
from pydantic import BaseModel

from cuentas_pro.models import BaulDoc
from cuentas_pro.state._autosetters import auto_setters


CATEGORIAS_BAUL = ["General", "Contratos", "Soportes", "Facturas",
                   "Certificados", "Legal", "Medicina", "Otros"]


class DocRow(BaseModel):
    id: int
    titulo: str
    categoria: str
    contenido: str
    etiquetas: str
    creado_en: str


@auto_setters
class BaulState(rx.State):
    rows: list[DocRow] = []
    filtro: str = ""
    filtro_cat: str = "Todas"

    form_open: bool = False
    form_titulo: str = ""
    form_cat: str = "General"
    form_contenido: str = ""
    form_etiquetas: str = ""
    form_editing_id: Optional[int] = None
    form_msg: str = ""

    @rx.var
    def rows_filtradas(self) -> list[DocRow]:
        data = self.rows
        if self.filtro_cat != "Todas":
            data = [r for r in data if r.categoria == self.filtro_cat]
        if self.filtro.strip():
            q = self.filtro.lower()
            data = [r for r in data
                    if q in r.titulo.lower()
                    or q in r.contenido.lower()
                    or q in r.etiquetas.lower()]
        return data

    @rx.event
    async def load(self):
        with rx.session() as s:
            results = s.exec(
                sqlmodel.select(BaulDoc).order_by(sqlmodel.desc(BaulDoc.creado_en))
            ).all()
        self.rows = [
            DocRow(
                id=r.id, titulo=r.titulo, categoria=r.categoria,
                contenido=r.contenido, etiquetas=r.etiquetas,
                creado_en=r.creado_en.strftime("%Y-%m-%d"),
            )
            for r in results
        ]

    @rx.event
    def toggle_form(self):
        self.form_open = not self.form_open
        self.form_msg = ""
        if self.form_open:
            self.form_editing_id = None
            self.form_titulo = ""
            self.form_contenido = ""
            self.form_etiquetas = ""

    @rx.event
    async def guardar(self):
        if not self.form_titulo.strip():
            self.form_msg = "⚠ El título es obligatorio."
            return
        with rx.session() as s:
            if self.form_editing_id:
                row = s.get(BaulDoc, self.form_editing_id)
                if row:
                    row.titulo = self.form_titulo.strip()
                    row.categoria = self.form_cat
                    row.contenido = self.form_contenido
                    row.etiquetas = self.form_etiquetas
                    s.add(row)
            else:
                s.add(BaulDoc(
                    titulo=self.form_titulo.strip(),
                    categoria=self.form_cat,
                    contenido=self.form_contenido,
                    etiquetas=self.form_etiquetas,
                ))
            s.commit()
        self.form_open = False
        self.form_editing_id = None
        await self.load()

    @rx.event
    async def editar(self, rid: int):
        with rx.session() as s:
            row = s.get(BaulDoc, rid)
            if row:
                self.form_editing_id = rid
                self.form_titulo = row.titulo
                self.form_cat = row.categoria
                self.form_contenido = row.contenido
                self.form_etiquetas = row.etiquetas
                self.form_open = True

    @rx.event
    async def eliminar(self, rid: int):
        with rx.session() as s:
            row = s.get(BaulDoc, rid)
            if row:
                s.delete(row)
                s.commit()
        await self.load()
