"""Modelos SQLModel para la BD local SQLite."""
from datetime import date as _date, datetime
from typing import Optional
import reflex as rx
import sqlmodel


class Caja(rx.Model, table=True):
    """Cuenta, tarjeta o bolsa de dinero del usuario."""
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    nombre: str = ""
    tipo: str = "cuenta"        # cuenta | tarjeta_credito | tarjeta_debito | efectivo | otro
    entidad: str = ""           # Bancolombia, Nequi, Falabella, Lulo...
    exento_4x1000: bool = False
    saldo_inicial: float = 0.0
    color: str = "#a78bfa"
    orden: int = 0
    activa: bool = True
    notas: str = ""
    creado_en: datetime = sqlmodel.Field(default_factory=datetime.utcnow)


class Ingreso(rx.Model, table=True):
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    fecha: _date
    descripcion: str = ""
    salario_base: float = 0.0
    aux_transporte: float = 0.0
    otros: float = 0.0
    pct_ahorro_objetivo: int = 10
    ingreso_real_cuenta: float = 0.0
    caja_id: Optional[int] = sqlmodel.Field(default=None, foreign_key="caja.id")
    creado_en: datetime = sqlmodel.Field(default_factory=datetime.utcnow)


class Gasto(rx.Model, table=True):
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    fecha: _date
    descripcion: str = ""
    categoria: str = "Otros"
    monto: float = 0.0           # Siempre en COP (monto equivalente)
    moneda: str = "COP"          # COP | USD
    monto_original: float = 0.0  # Si moneda=USD, monto en USD; si COP, igual a monto
    trm: float = 0.0             # TRM aplicado si fue USD
    medio_pago: str = "Efectivo"
    caja_id: Optional[int] = sqlmodel.Field(default=None, foreign_key="caja.id")
    shopping_group_id: Optional[int] = sqlmodel.Field(default=None, foreign_key="shoppinggroup.id")
    shopping_item_id: Optional[int] = sqlmodel.Field(default=None, foreign_key="shoppingitem.id")
    shopping_pct: float = 100.0
    recurrente: bool = False
    notas: str = ""
    creado_en: datetime = sqlmodel.Field(default_factory=datetime.utcnow)


class Movimiento(rx.Model, table=True):
    """Transferencia interna entre cajas (no es gasto ni ingreso)."""
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    fecha: _date
    caja_origen_id: int = sqlmodel.Field(foreign_key="caja.id")
    caja_destino_id: int = sqlmodel.Field(foreign_key="caja.id")
    monto: float = 0.0           # COP
    aplica_4x1000: bool = False  # calculado al guardar según cajas
    costo_4x1000: float = 0.0
    descripcion: str = ""
    creado_en: datetime = sqlmodel.Field(default_factory=datetime.utcnow)


class CDT(rx.Model, table=True):
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    entidad: str = ""
    monto: float = 0.0
    tasa_ea: float = 0.0       # % efectivo anual
    fecha_apertura: _date
    plazo_dias: int = 30
    fecha_vencimiento: _date
    notas: str = ""


class BaulDoc(rx.Model, table=True):
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    titulo: str = ""
    categoria: str = "General"
    contenido: str = ""
    etiquetas: str = ""
    creado_en: datetime = sqlmodel.Field(default_factory=datetime.utcnow)


class ShoppingGroup(rx.Model, table=True):
    """Grupo/lista de compras (ej: Mercado quincenal, Hogar, Tecnología)."""
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    nombre: str = ""
    categoria_default: str = "Otros"
    activa: bool = True
    notas: str = ""
    creado_en: datetime = sqlmodel.Field(default_factory=datetime.utcnow)


class ShoppingItem(rx.Model, table=True):
    """Ítem de compra perteneciente a un grupo."""
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    group_id: int = sqlmodel.Field(foreign_key="shoppinggroup.id")
    nombre: str = ""
    categoria: str = ""
    monto_estimado: float = 0.0
    comprado: bool = False
    activo: bool = True
    notas: str = ""
    imagen_url: str = ""   # miniatura (OpenGraph image)
    link: str = ""         # URL del producto (Amazon, MercadoLibre, etc.)
    creado_en: datetime = sqlmodel.Field(default_factory=datetime.utcnow)


class Presupuesto(rx.Model, table=True):
    """Presupuesto mensual por categoría de gasto."""
    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    categoria: str = "Otros"
    anio: int = 0
    mes: int = 0  # 1..12
    monto: float = 0.0
    alerta_pct: int = 90  # alerta cuando se alcance este % del cupo
    notas: str = ""
    creado_en: datetime = sqlmodel.Field(default_factory=datetime.utcnow)

