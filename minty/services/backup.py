"""Backup automático de la base de datos local.

Crea un snapshot comprimido (.zip) de ``data/minty.db`` en
``data/backups/`` cada vez que la app arranca y han pasado al menos
``MIN_HOURS_BETWEEN_BACKUPS`` horas desde el último backup. Mantiene los
``MAX_BACKUPS`` más recientes y elimina el resto.

Diseñado para ser silencioso: cualquier fallo se loguea y se ignora
(no debe bloquear el arranque de la app).
"""
from __future__ import annotations

import logging
import os
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "minty.db"
BACKUP_DIR = DATA_DIR / "backups"

MIN_HOURS_BETWEEN_BACKUPS = 24
MAX_BACKUPS = 14  # ~2 semanas


def listar_backups() -> list[dict]:
    """Lista los backups existentes ordenados por fecha (más reciente primero).

    Cada item: ``{"nombre": str, "ruta": str, "tamano": int, "fecha": str}``.
    """
    if not BACKUP_DIR.exists():
        return []
    items = []
    for p in sorted(BACKUP_DIR.glob("cuentas-*.zip"), reverse=True):
        st = p.stat()
        items.append({
            "nombre": p.name,
            "ruta": str(p),
            "tamano": st.st_size,
            "tamano_fmt": _fmt_bytes(st.st_size),
            "fecha": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return items


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


def _liberar_db():
    """Cierra todas las conexiones SQLAlchemy a la BD para poder
    sobrescribir el archivo .sqlite en Windows.

    Limpia tanto los engines de Reflex como el engine local de minty.db.
    Tras llamar a esta función, el siguiente acceso recreará el engine
    apuntando ya al nuevo archivo restaurado.
    """
    # Engine local (migraciones, índices)
    try:
        from minty import db as _localdb
        if getattr(_localdb, "_ENGINE", None) is not None:
            try:
                _localdb._ENGINE.dispose()
            except Exception:  # noqa: BLE001
                pass
            _localdb._ENGINE = None
    except Exception:  # noqa: BLE001
        log.warning("No se pudo disponer engine local", exc_info=True)

    # Engines de Reflex (sync y async)
    try:
        import reflex.model as _rxmodel  # type: ignore
        for eng in list(getattr(_rxmodel, "_ENGINE", {}).values()):
            try:
                eng.dispose()
            except Exception:  # noqa: BLE001
                pass
        if hasattr(_rxmodel, "_ENGINE"):
            _rxmodel._ENGINE.clear()
        for eng in list(getattr(_rxmodel, "_ASYNC_ENGINE", {}).values()):
            try:
                # AsyncEngine.dispose es coroutine; en práctica sync_close basta
                eng.sync_engine.dispose()
            except Exception:  # noqa: BLE001
                pass
        if hasattr(_rxmodel, "_ASYNC_ENGINE"):
            _rxmodel._ASYNC_ENGINE.clear()
    except Exception:  # noqa: BLE001
        log.warning("No se pudo disponer engines de Reflex", exc_info=True)

    # GC para soltar handles colgantes en Windows
    import gc
    gc.collect()


def restaurar_backup(nombre_zip: str) -> bool:
    """Restaura la BD desde un backup existente. Crea un backup de
    seguridad de la BD actual antes de sobrescribirla.

    Devuelve True si la restauración fue exitosa.
    Lanza FileNotFoundError si el zip no existe.
    """
    src = BACKUP_DIR / nombre_zip
    if not src.exists() or src.suffix != ".zip":
        raise FileNotFoundError(f"Backup no encontrado: {nombre_zip}")

    # Snapshot de seguridad antes de restaurar.
    if DB_PATH.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        seguridad = BACKUP_DIR / f"cuentas-pre-restore-{ts}.zip"
        try:
            with zipfile.ZipFile(seguridad, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(DB_PATH, arcname="minty.db")
        except Exception as e:  # no abortar si falla la copia previa
            log.warning("No se pudo crear backup pre-restore: %s", e)

    # Validar contenido del zip antes de tocar nada.
    with zipfile.ZipFile(src, "r") as zf:
        nombres = zf.namelist()
        if "minty.db" not in nombres:
            raise ValueError(f"El zip no contiene 'minty.db': {nombre_zip}")

    # Liberar conexiones SQLAlchemy para poder sobrescribir el archivo en Windows.
    _liberar_db()

    # Extraer a temp y luego mover atómicamente sobre minty.db. Eliminar
    # también los archivos auxiliares -wal y -shm de SQLite, que de lo
    # contrario contendrían transacciones del archivo viejo.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = DATA_DIR / "minty.db.restore.tmp"
    with zipfile.ZipFile(src, "r") as zf:
        with zf.open("minty.db") as fsrc, open(tmp_path, "wb") as fdst:
            shutil.copyfileobj(fsrc, fdst)

    for aux in (DATA_DIR / "minty.db-wal", DATA_DIR / "minty.db-shm"):
        try:
            aux.unlink(missing_ok=True)
        except OSError:
            log.warning("No se pudo eliminar archivo auxiliar: %s", aux)

    try:
        os.replace(tmp_path, DB_PATH)
    except OSError as e:
        # Reintento: si algún handle quedó colgando, forzar otro GC y volver.
        import gc
        gc.collect()
        try:
            os.replace(tmp_path, DB_PATH)
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise RuntimeError(
                "No se pudo sobrescribir minty.db (archivo en uso). "
                "Reinicia la aplicación e intenta de nuevo."
            ) from e
    return True


def _ultimo_backup_ts() -> float:
    if not BACKUP_DIR.exists():
        return 0.0
    backups = sorted(BACKUP_DIR.glob("cuentas-*.zip"))
    if not backups:
        return 0.0
    return backups[-1].stat().st_mtime


def _purgar_antiguos() -> None:
    backups = sorted(BACKUP_DIR.glob("cuentas-*.zip"))
    excedente = len(backups) - MAX_BACKUPS
    for old in backups[:max(0, excedente)]:
        try:
            old.unlink()
        except OSError:
            log.warning("No se pudo eliminar backup antiguo: %s", old)


def hacer_backup(force: bool = False) -> Path | None:
    """Crea backup .zip de la BD si corresponde. Retorna ruta o None."""
    try:
        if not DB_PATH.exists():
            return None
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        ahora = time.time()
        if not force:
            ultimo = _ultimo_backup_ts()
            horas = (ahora - ultimo) / 3600 if ultimo else float("inf")
            if horas < MIN_HOURS_BETWEEN_BACKUPS:
                return None

        ts = datetime.fromtimestamp(ahora).strftime("%Y%m%d-%H%M%S")
        zip_path = BACKUP_DIR / f"cuentas-{ts}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(DB_PATH, arcname="minty.db")

        _purgar_antiguos()
        log.info("Backup creado: %s", zip_path)
        return zip_path
    except Exception as e:  # nunca bloquea el arranque
        log.warning("No se pudo crear backup: %s", e)
        return None
