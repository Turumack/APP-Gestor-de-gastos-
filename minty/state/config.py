"""State de la página de Configuración."""
from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import reflex as rx

from minty.services import (
    BACKUP_DIR, hacer_backup, listar_backups, restaurar_backup,
)

log = logging.getLogger(__name__)


class ConfigState(rx.State):
    backups: list[dict] = []
    msg: str = ""
    msg_kind: str = ""  # "ok" | "warn" | "err" | ""
    procesando: bool = False
    is_postgres: bool = False

    @rx.event
    def load(self):
        from rxconfig import config as _cfg
        self.is_postgres = (_cfg.db_url or "").startswith("postgresql")
        self.backups = [] if self.is_postgres else listar_backups()
        self.msg = ""
        self.msg_kind = ""

    @rx.event
    def crear_backup(self):
        try:
            ruta = hacer_backup(force=True)
            if ruta:
                self.msg = f"✓ Backup creado: {Path(ruta).name}"
                self.msg_kind = "ok"
            else:
                self.msg = "⚠ No se pudo crear el backup."
                self.msg_kind = "warn"
        except Exception as e:  # noqa: BLE001
            log.exception("Error creando backup")
            self.msg = f"⚠ Error creando backup: {e}"
            self.msg_kind = "err"
        self.backups = listar_backups()

    @rx.event
    def descargar_backup(self, nombre: str):
        ruta = BACKUP_DIR / nombre
        if not ruta.exists():
            self.msg = f"⚠ Backup no encontrado: {nombre}"
            self.msg_kind = "err"
            return None
        try:
            data = ruta.read_bytes()
        except Exception as e:  # noqa: BLE001
            self.msg = f"⚠ No se pudo leer: {e}"
            self.msg_kind = "err"
            return None
        return rx.download(data=data, filename=nombre)

    @rx.event
    def restaurar(self, nombre: str):
        try:
            restaurar_backup(nombre)
            # Re-aplicar migraciones por si el backup es de un esquema previo.
            try:
                from minty import db as _db
                _db.ensure_db()
            except Exception:  # noqa: BLE001
                log.exception("Fallo re-aplicando migraciones tras restaurar")
            self.msg = (
                f"✓ Backup '{nombre}' restaurado correctamente. "
                "Recarga la página (F5) para ver los datos restaurados."
            )
            self.msg_kind = "ok"
        except Exception as e:  # noqa: BLE001
            log.exception("Error restaurando backup")
            self.msg = f"⚠ No se pudo restaurar: {e}"
            self.msg_kind = "err"
        self.backups = listar_backups()

    @rx.event
    def eliminar_backup(self, nombre: str):
        ruta = BACKUP_DIR / nombre
        try:
            ruta.unlink(missing_ok=True)
            self.msg = f"✓ Backup eliminado: {nombre}"
            self.msg_kind = "ok"
        except Exception as e:  # noqa: BLE001
            self.msg = f"⚠ No se pudo eliminar: {e}"
            self.msg_kind = "err"
        self.backups = listar_backups()

    @rx.event
    async def subir_backup(self, files: list[rx.UploadFile]):
        """Recibe un .zip subido por el usuario, lo guarda en backups/
        y lo deja disponible para restaurar."""
        if not files:
            self.msg = "⚠ No se seleccionó ningún archivo."
            self.msg_kind = "warn"
            return
        f = files[0]
        nombre = getattr(f, "name", None) or getattr(f, "filename", "subido.zip")
        if not nombre.lower().endswith(".zip"):
            self.msg = "⚠ El archivo debe ser un .zip de backup."
            self.msg_kind = "err"
            return
        try:
            data = await f.read()
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            # Validar que contenga minty.db antes de aceptarlo.
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".zip", dir=str(BACKUP_DIR),
            ) as tmp:
                tmp.write(data)
                tmp_path = Path(tmp.name)
            try:
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    if "minty.db" not in zf.namelist():
                        raise ValueError("El zip no contiene 'minty.db'.")
                # Renombrar al nombre final (con timestamp para evitar choques).
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                base = Path(nombre).stem
                destino = BACKUP_DIR / f"{base}-uploaded-{ts}.zip"
                shutil.move(str(tmp_path), str(destino))
                self.msg = f"✓ Backup subido: {destino.name}"
                self.msg_kind = "ok"
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise
        except Exception as e:  # noqa: BLE001
            log.exception("Error subiendo backup")
            self.msg = f"⚠ Error subiendo backup: {e}"
            self.msg_kind = "err"
        self.backups = listar_backups()
