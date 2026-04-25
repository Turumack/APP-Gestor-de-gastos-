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


def ensure_db():
    """Crea las tablas si no existen. Se llama al arrancar la app."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    engine = create_engine(config.db_url, echo=False)
    SQLModel.metadata.create_all(engine)
    _apply_lightweight_migrations(engine)


# Ejecutar al importar
ensure_db()
