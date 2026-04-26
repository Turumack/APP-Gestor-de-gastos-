"""Helper para crear/verificar tablas en la BD SQLite local."""
from pathlib import Path
from sqlmodel import SQLModel, create_engine, text
from rxconfig import config

# Importar modelos para que se registren en SQLModel.metadata
from cuentas_pro import models  # noqa: F401


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
    """Añade columnas nuevas a tablas existentes (SQLite ALTER TABLE ADD COLUMN)."""
    with engine.begin() as conn:
        for tabla, col, definicion in _MIGRATIONS_ADD_COLUMNS:
            exists = conn.execute(
                text(f"SELECT name FROM pragma_table_info('{tabla}') WHERE name = :c"),
                {"c": col},
            ).first()
            if exists:
                continue
            # Tabla existe?
            tbl = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                {"t": tabla},
            ).first()
            if not tbl:
                continue
            conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} {definicion}"))


def _apply_indexes(engine):
    """Crea índices si la tabla existe (idempotente)."""
    with engine.begin() as conn:
        for nombre, tabla, columnas in _INDEXES:
            tbl = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                {"t": tabla},
            ).first()
            if not tbl:
                continue
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS {nombre} ON {tabla} ({columnas})"
            ))


def ensure_db():
    """Crea las tablas si no existen. Se llama al arrancar la app."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    engine = create_engine(config.db_url, echo=False)
    SQLModel.metadata.create_all(engine)
    _apply_lightweight_migrations(engine)
    _apply_indexes(engine)

    # Backup automático (silencioso si falla, con cooldown interno).
    try:
        from cuentas_pro.services.backup import hacer_backup
        hacer_backup()
    except Exception:
        pass


# Ejecutar al importar
ensure_db()
