"""Configuración de Reflex.

Variables de entorno relevantes:
- ``DATABASE_URL``  Postgres en producción (Railway la inyecta sola).
                    Si está vacía, usa SQLite local en ``data/minty.db``.
- ``MINTY_HOST``    Host público para producción (ej. ``minty.up.railway.app``).
- ``PORT``          Puerto del backend (Railway lo inyecta).
"""
import os

import reflex as rx

# ── Base de datos ──────────────────────────────────────────────
_db_url = os.getenv("DATABASE_URL", "").strip()
if _db_url.startswith("postgres://"):
    # SQLAlchemy 2 exige el dialecto explícito.
    _db_url = "postgresql://" + _db_url[len("postgres://"):]
if not _db_url:
    _db_url = "sqlite:///data/minty.db"

# ── Host / puertos ─────────────────────────────────────────────
_host = os.getenv("MINTY_HOST", "").strip()
_backend_port = int(os.getenv("PORT", "8000"))

_kwargs: dict = dict(
    app_name="minty",
    db_url=_db_url,
    frontend_port=3000,
    backend_port=_backend_port,
    telemetry_enabled=False,
    show_built_with_reflex=False,
    state_auto_setters=False,
    plugins=[rx.plugins.SitemapPlugin(), rx.plugins.TailwindV4Plugin()],
)
if _host:
    _kwargs["api_url"] = f"https://{_host}"
    _kwargs["deploy_url"] = f"https://{_host}"

config = rx.Config(**_kwargs)
