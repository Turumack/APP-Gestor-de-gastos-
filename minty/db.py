"""Helper para crear/verificar tablas. Soporta SQLite (dev) y Postgres (prod)."""
from pathlib import Path
from sqlmodel import SQLModel, create_engine, text
from sqlalchemy import inspect
from rxconfig import config

# Importar modelos para que se registren en SQLModel.metadata
from minty import models  # noqa: F401


def _is_postgres() -> bool:
    return config.db_url.startswith("postgresql")


def _norm_def(definicion: str) -> str:
    """Normaliza defaults entre dialectos.

    SQLite acepta ``DEFAULT 0`` para booleanos; Postgres no — exige TRUE/FALSE.
    """
    if not _is_postgres():
        return definicion
    up = definicion.upper()
    if "BOOLEAN" in up:
        return (
            definicion.replace("DEFAULT 0", "DEFAULT FALSE")
            .replace("DEFAULT 1", "DEFAULT TRUE")
        )
    return definicion


# Columnas añadidas después de la creación inicial.
# Formato: (tabla, columna, definición SQL con default).
_MIGRATIONS_ADD_COLUMNS = [
    ("ingreso", "caja_id",         "INTEGER"),
    ("gasto",   "moneda",          "VARCHAR DEFAULT 'COP'"),
    ("gasto",   "monto_original",  "FLOAT DEFAULT 0"),
    ("gasto",   "trm",             "FLOAT DEFAULT 0"),
    ("gasto",   "caja_id",         "INTEGER"),
    ("gasto",   "shopping_group_id", "INTEGER"),
    ("gasto",   "shopping_item_id",  "INTEGER"),
    ("gasto",   "shopping_pct",      "FLOAT DEFAULT 100"),
    ("gasto",   "cuotas_total",      "INTEGER DEFAULT 0"),
    ("gasto",   "cuota_num",         "INTEGER DEFAULT 0"),
    ("gasto",   "compra_id",         "VARCHAR DEFAULT ''"),
    ("shoppingitem", "imagen_url",   "VARCHAR DEFAULT ''"),
    ("shoppingitem", "link",         "VARCHAR DEFAULT ''"),
    ("shoppingitem", "recurrente",   "BOOLEAN DEFAULT 0"),
    ("shoppinggroup", "recurrente",  "BOOLEAN DEFAULT 0"),
    ("gasto", "recurrencia_unidad",     "VARCHAR DEFAULT ''"),
    ("gasto", "recurrencia_intervalo",  "INTEGER DEFAULT 1"),
    # Campos TC (tarjeta de crédito) en caja
    ("caja", "cupo_total_cop",          "FLOAT DEFAULT 0"),
    ("caja", "interes_mensual_compras", "FLOAT DEFAULT 0"),
    ("caja", "interes_ea_compras",      "FLOAT DEFAULT 0"),
    ("caja", "interes_mensual_avances", "FLOAT DEFAULT 0"),
    ("caja", "interes_ea_avances",      "FLOAT DEFAULT 0"),
    ("caja", "cuota_manejo",            "FLOAT DEFAULT 0"),
    ("caja", "dia_cobro_cuota",         "INTEGER DEFAULT 1"),
    ("caja", "dia_corte",               "INTEGER DEFAULT 1"),
    ("caja", "usa_dos_cortes",          "BOOLEAN DEFAULT 0"),
    ("caja", "dia_corte_2",             "INTEGER DEFAULT 15"),
    ("caja", "dia_pago",                "INTEGER DEFAULT 1"),
    ("caja", "trm_tc",                  "FLOAT DEFAULT 0"),
    ("caja", "ultimo_cobro_cuota",      "VARCHAR DEFAULT ''"),
]

# Índices para acelerar queries por período y por caja.
_INDEXES = [
    ("idx_gasto_fecha",            "gasto",        "fecha"),
    ("idx_gasto_caja_id",          "gasto",        "caja_id"),
    ("idx_gasto_categoria",        "gasto",        "categoria"),
    ("idx_ingreso_fecha",          "ingreso",      "fecha"),
    ("idx_ingreso_caja_id",        "ingreso",      "caja_id"),
    ("idx_movimiento_fecha",       "movimiento",   "fecha"),
    ("idx_movimiento_origen",      "movimiento",   "caja_origen_id"),
    ("idx_movimiento_destino",     "movimiento",   "caja_destino_id"),
    ("idx_shoppingitem_group",     "shoppingitem", "group_id"),
    ("idx_presupuesto_periodo",    "presupuesto",  "anio, mes"),
    ("idx_gasto_compra_id",        "gasto",        "compra_id"),
]


def _apply_lightweight_migrations(engine):
    """Añade columnas nuevas a tablas existentes. Idempotente, cross-DB."""
    insp = inspect(engine)
    with engine.begin() as conn:
        for tabla, col, definicion in _MIGRATIONS_ADD_COLUMNS:
            if not insp.has_table(tabla):
                continue
            cols_existentes = {c["name"] for c in insp.get_columns(tabla)}
            if col in cols_existentes:
                continue
            conn.execute(text(
                f"ALTER TABLE {tabla} ADD COLUMN {col} {_norm_def(definicion)}"
            ))


def _apply_indexes(engine):
    """Crea índices si la tabla existe (idempotente, cross-DB)."""
    insp = inspect(engine)
    with engine.begin() as conn:
        for nombre, tabla, columnas in _INDEXES:
            if not insp.has_table(tabla):
                continue
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS {nombre} ON {tabla} ({columnas})"
            ))


def ensure_db():
    """Crea las tablas si no existen. Se llama al arrancar la app."""
    global _ENGINE
    if not _is_postgres():
        Path("data").mkdir(exist_ok=True)
    engine = create_engine(config.db_url, echo=False)
    _ENGINE = engine
    SQLModel.metadata.create_all(engine)
    _apply_lightweight_migrations(engine)
    _apply_indexes(engine)

    # Backup automático solo en modo SQLite local.
    if not _is_postgres():
        try:
            from minty.services.backup import hacer_backup
            hacer_backup()
        except Exception:
            pass


def get_engine():
    """Devuelve el engine ya inicializado (llamando a ``ensure_db`` si hace falta)."""
    if _ENGINE is None:
        ensure_db()
    return _ENGINE


# Ejecutar al importar
# Ejecutar al importar
_ENGINE = None
ensure_db()

