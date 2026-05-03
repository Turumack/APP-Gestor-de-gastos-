"""Crea o actualiza la contraseña de la app.

La contraseña se hashea con **bcrypt** (sal aleatoria, costo 12) y se guarda
en la tabla ``user`` de la BD activa (la que apunte ``DATABASE_URL`` o, si no
está seteada, la SQLite local en ``data/minty.db``).

Uso típico:

    # Local (dev):
    python tools/set_password.py

    # Apuntando al Postgres de Railway:
    $env:DATABASE_URL = "postgresql://user:pass@host:5432/railway"
    python tools/set_password.py

    # Dentro del contenedor de Railway (DATABASE_URL ya inyectada):
    railway run python tools/set_password.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bcrypt  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from minty.db import get_engine  # noqa: E402  (también dispara ensure_db)
from minty.models import User  # noqa: E402


def main() -> None:
    print("─── Configurar credenciales de la app ───")
    username = input("Usuario [admin]: ").strip() or "admin"
    pwd1 = getpass.getpass("Contraseña: ")
    pwd2 = getpass.getpass("Repite la contraseña: ")
    if pwd1 != pwd2:
        print("✖ Las contraseñas no coinciden.")
        sys.exit(1)
    if len(pwd1) < 6:
        print("✖ La contraseña debe tener al menos 6 caracteres.")
        sys.exit(1)

    pwd_hash = bcrypt.hashpw(pwd1.encode("utf-8"), bcrypt.gensalt(rounds=12))

    with Session(get_engine()) as s:
        existing = s.exec(select(User).where(User.username == username)).first()
        if existing is None:
            # Si hay otro usuario activo con nombre distinto, lo desactivamos
            # para evitar tener varias credenciales válidas a la vez.
            otros = s.exec(select(User).where(User.activo == True)).all()  # noqa: E712
            for o in otros:
                if o.username != username:
                    o.activo = False
                    s.add(o)
            nuevo = User(
                username=username,
                password_hash=pwd_hash.decode("utf-8"),
                activo=True,
            )
            s.add(nuevo)
            s.commit()
            print(f"✓ Usuario '{username}' creado.")
        else:
            existing.password_hash = pwd_hash.decode("utf-8")
            existing.activo = True
            s.add(existing)
            s.commit()
            print(f"✓ Contraseña de '{username}' actualizada.")


if __name__ == "__main__":
    main()
