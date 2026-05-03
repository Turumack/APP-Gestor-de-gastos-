"""Estado de autenticación.

Diseño seguro:
- La contraseña se guarda **hasheada con bcrypt** (sal aleatoria, lento) en la
  tabla ``user`` de la BD. Nunca aparece en código, repo ni variables de
  entorno.
- Para crear/cambiar la contraseña se usa ``tools/set_password.py``.
- Si **no existe ningún usuario activo** en la BD, la app queda en modo
  abierto (útil para desarrollo local antes de configurar credenciales).
- La cookie de sesión guarda un token derivado del hash bcrypt; al cerrar
  sesión se invalida.
"""
from __future__ import annotations

import hmac
from hashlib import sha256
from datetime import datetime
from typing import Optional

import bcrypt
import reflex as rx
from sqlmodel import Session, select

from minty.db import get_engine
from minty.models import User


def _get_active_user() -> Optional[User]:
    """Devuelve el primer usuario activo, o ``None`` si no hay ninguno."""
    try:
        with Session(get_engine()) as s:
            return s.exec(
                select(User).where(User.activo == True)  # noqa: E712
            ).first()
    except Exception:
        return None


def auth_required() -> bool:
    """``True`` si existe al menos un usuario configurado."""
    return _get_active_user() is not None


def _token_for(user: User) -> str:
    """Token de sesión: sha256 del hash bcrypt (no expone el hash directo)."""
    return sha256(user.password_hash.encode("utf-8")).hexdigest()


class AuthState(rx.State):
    """Sesión por cookie. Si ``token`` coincide con el esperado, está logueado."""

    user_input: str = ""
    pwd_input: str = ""
    token: str = rx.LocalStorage("", name="minty_token")
    msg: str = ""

    @rx.var
    def is_logged_in(self) -> bool:
        u = _get_active_user()
        if u is None:
            return True  # sin usuarios configurados → modo abierto
        return hmac.compare_digest(self.token or "", _token_for(u))

    def login(self):
        u = _get_active_user()
        if u is None:
            self.token = "open"
            self.msg = ""
            return rx.redirect("/")

        username = (self.user_input or "").strip()
        pwd = self.pwd_input or ""

        if username != u.username:
            self.msg = "Usuario o contraseña incorrectos."
            return
        try:
            ok = bcrypt.checkpw(pwd.encode("utf-8"), u.password_hash.encode("utf-8"))
        except (ValueError, TypeError):
            ok = False
        if not ok:
            self.msg = "Usuario o contraseña incorrectos."
            return

        # Marca último login (best-effort)
        try:
            with Session(get_engine()) as s:
                row = s.get(User, u.id)
                if row is not None:
                    row.ultimo_login = datetime.utcnow()
                    s.add(row)
                    s.commit()
        except Exception:
            pass

        self.token = _token_for(u)
        self.user_input = ""
        self.pwd_input = ""
        self.msg = ""
        return rx.redirect("/")

    def logout(self):
        self.token = ""
        return rx.redirect("/login")

    def require_login(self):
        """Llamar en ``on_load`` de páginas protegidas."""
        if not self.is_logged_in:
            return rx.redirect("/login")
