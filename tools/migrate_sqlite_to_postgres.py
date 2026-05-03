"""Migra todos los datos de la SQLite local a la BD apuntada por DATABASE_URL.

Uso:
    $env:DATABASE_URL = "postgresql://..."   # Postgres destino
    python tools/migrate_sqlite_to_postgres.py

- Lee de  data/minty.db  (SQLite local).
- Escribe en la BD de DATABASE_URL (Postgres de Railway).
- NO toca la tabla `user` (preserva tu admin con bcrypt).
- Resetea las secuencias de Postgres después de insertar para que los
  próximos INSERT no choquen con los IDs migrados.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

# Importa modelos
from minty.models import (  # noqa: E402
    Caja,
    Ingreso,
    Gasto,
    Movimiento,
    CDT,
    BaulDoc,
    ShoppingGroup,
    ShoppingItem,
    Presupuesto,
)

# Tablas a migrar en orden (respetando FKs)
TABLES = [
    Caja,
    ShoppingGroup,
    ShoppingItem,
    Ingreso,
    Gasto,
    Movimiento,
    CDT,
    BaulDoc,
    Presupuesto,
]


def main() -> None:
    dest_url = os.environ.get("DATABASE_URL", "")
    if not dest_url:
        print("✖ Define DATABASE_URL antes de correr este script.")
        sys.exit(1)
    if dest_url.startswith("postgres://"):
        dest_url = "postgresql://" + dest_url[len("postgres://"):]

    sqlite_path = ROOT / "data" / "minty.db"
    if not sqlite_path.exists():
        print(f"✖ No existe {sqlite_path}")
        sys.exit(1)

    src_url = f"sqlite:///{sqlite_path.as_posix()}"

    print(f"  Origen : {src_url}")
    print(f"  Destino: {dest_url.split('@')[-1]}")
    print()

    src_engine = create_engine(src_url)
    dst_engine = create_engine(dest_url)

    # Asegura que las tablas existan en destino
    from minty.models import User  # noqa: F401  (para que se registre)
    import sqlmodel
    sqlmodel.SQLModel.metadata.create_all(dst_engine)

    is_postgres = dest_url.startswith("postgresql")
    total = 0

    with Session(src_engine) as src, Session(dst_engine) as dst:
        for Model in TABLES:
            rows = src.exec(select(Model)).all()
            if not rows:
                print(f"  · {Model.__tablename__:20s} (vacía)")
                continue
            for r in rows:
                # Crea una copia limpia (sin sesión) en destino
                data = r.model_dump()
                dst.add(Model(**data))
            dst.commit()
            print(f"  ✓ {Model.__tablename__:20s} {len(rows)} filas")
            total += len(rows)

        # Reset secuencias en Postgres para que el próximo INSERT no choque
        if is_postgres:
            for Model in TABLES:
                tname = Model.__tablename__
                try:
                    dst.exec(
                        text(
                            f"SELECT setval(pg_get_serial_sequence('{tname}', 'id'), "
                            f"COALESCE((SELECT MAX(id) FROM {tname}), 0) + 1, false)"
                        )
                    )
                except Exception as e:
                    print(f"  ! No se pudo resetear secuencia de {tname}: {e}")
            dst.commit()
            print("  ✓ Secuencias de Postgres reseteadas.")

    print(f"\n✓ Migración completa. {total} filas copiadas.")


if __name__ == "__main__":
    main()
