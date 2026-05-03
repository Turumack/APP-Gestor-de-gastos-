"""Copia los datos de la BD local SQLite a la BD remota Postgres.

Uso (desde la raíz del proyecto, con el .venv activo):

    # 1. Exporta la URL de Postgres de Railway (settings → Variables → DATABASE_URL).
    $env:PG_URL = "postgresql://user:pass@host:5432/railway"

    # 2. Ejecuta el script.
    python tools/migrar_sqlite_a_postgres.py

El script:
- Crea las tablas en Postgres (idempotente).
- Vacía cada tabla destino y reinserta TODAS las filas desde SQLite.
- Reinicia las secuencias de IDs para que el siguiente INSERT funcione.

⚠️ DESTRUCTIVO en destino. Confirma antes de correr.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlmodel import SQLModel, Session, create_engine, select  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from minty import models  # noqa: E402,F401  registra metadata


def main() -> None:
    src_url = "sqlite:///" + str(ROOT / "data" / "minty.db")
    dst_url = (os.getenv("PG_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not dst_url:
        print("✖ Falta variable PG_URL (o DATABASE_URL) con la URL de Postgres.")
        sys.exit(1)
    if dst_url.startswith("postgres://"):
        dst_url = "postgresql://" + dst_url[len("postgres://"):]

    if not (ROOT / "data" / "minty.db").exists():
        print("✖ No encontré data/minty.db.")
        sys.exit(1)

    print(f"Origen:  {src_url}")
    print(f"Destino: {dst_url.split('@')[-1]}")
    if input("¿Continuar? (s/N) ").strip().lower() != "s":
        print("Cancelado.")
        return

    src = create_engine(src_url)
    dst = create_engine(dst_url)

    print("• Creando tablas en destino...")
    SQLModel.metadata.create_all(dst)

    insp_src = inspect(src)
    tablas = SQLModel.metadata.sorted_tables  # respeta FKs

    with Session(src) as s_src, Session(dst) as s_dst:
        # Borra en orden inverso (respeta FKs)
        for t in reversed(tablas):
            if not insp_src.has_table(t.name):
                continue
            s_dst.execute(text(f'DELETE FROM "{t.name}"'))
        s_dst.commit()

        # Inserta
        total = 0
        for t in tablas:
            if not insp_src.has_table(t.name):
                continue
            rows = s_src.execute(select(t)).all()
            if not rows:
                continue
            cols = [c.name for c in t.columns]
            for r in rows:
                data = dict(zip(cols, r))
                s_dst.execute(t.insert().values(**data))
                total += 1
            s_dst.commit()
            print(f"  · {t.name}: {len(rows)} fila(s)")

        # Reinicia secuencias en Postgres (los IDs vienen del origen).
        for t in tablas:
            if "id" not in [c.name for c in t.columns]:
                continue
            try:
                s_dst.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM \"{t.name}\"), 1))"
                ))
            except Exception:
                pass
        s_dst.commit()

    print(f"✓ Migración completa. {total} filas copiadas.")


if __name__ == "__main__":
    main()
