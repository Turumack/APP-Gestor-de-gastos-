"""Página de Configuración: backups manuales, restore, mantenimiento."""
import reflex as rx
from minty import theme as T
from minty.components import (
    main_layout, glass_card, page_title,
    primary_button, ghost_button,
)
from minty.state.config import ConfigState


def _msg() -> rx.Component:
    color = rx.match(
        ConfigState.msg_kind,
        ("ok", T.GREEN),
        ("warn", T.AMBER),
        ("err", T.RED),
        T.TEXT_MUTED,
    )
    return rx.cond(
        ConfigState.msg != "",
        rx.box(
            rx.text(ConfigState.msg, size="2", color=color),
            padding="10px 12px",
            border=f"1px solid {T.BORDER}",
            border_radius=T.RADIUS_SM,
            background="rgba(255,255,255,0.03)",
            width="100%",
        ),
        rx.fragment(),
    )


def _row_backup(b) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon("archive", size=14, color="white"),
            width="32px", height="32px", border_radius="10px",
            background=T.VIOLET,
            display="flex", align_items="center", justify_content="center",
        ),
        rx.vstack(
            rx.text(b["nombre"], size="2", color=T.TEXT, weight="medium",
                    font_family=T.FONT_MONO),
            rx.hstack(
                rx.text(b["fecha"], size="1", color=T.TEXT_DIM),
                rx.text("·", size="1", color=T.TEXT_DIM),
                rx.text(b["tamano_fmt"], size="1", color=T.TEXT_DIM),
                spacing="1",
            ),
            spacing="1", align="start",
        ),
        rx.spacer(),
        rx.button(
            rx.icon("download", size=14),
            "Descargar",
            on_click=lambda: ConfigState.descargar_backup(b["nombre"]),
            variant="ghost", size="2", cursor="pointer",
            color=T.TEXT_MUTED,
        ),
        rx.button(
            rx.icon("rotate-ccw", size=14),
            "Restaurar",
            on_click=lambda: ConfigState.restaurar(b["nombre"]),
            variant="ghost", size="2", cursor="pointer",
            color=T.AMBER,
        ),
        rx.button(
            rx.icon("trash-2", size=14),
            on_click=lambda: ConfigState.eliminar_backup(b["nombre"]),
            variant="ghost", size="2", cursor="pointer",
            color=T.RED, title="Eliminar backup",
        ),
        spacing="2", width="100%", align="center",
        padding="10px 12px",
        border_radius=T.RADIUS_SM,
        _hover={"background": "rgba(255,255,255,.03)"},
    )


def _seccion_backups() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("database", size=18, color=T.VIOLET),
                rx.heading("Backups de la base de datos", size="5",
                           font_family=T.FONT_HEAD),
                rx.spacer(),
                primary_button(
                    "Crear backup ahora",
                    on_click=ConfigState.crear_backup,
                    icon="plus",
                ),
                width="100%", align="center",
            ),
            rx.text(
                "Los backups se crean automáticamente al iniciar la app "
                "(máximo 1 cada 24 h). Aquí puedes generarlos manualmente, "
                "descargarlos o restaurar uno previo.",
                size="2", color=T.TEXT_MUTED,
            ),
            _msg(),
            rx.box(height="8px"),
            rx.cond(
                ConfigState.backups.length() > 0,
                rx.vstack(
                    rx.foreach(ConfigState.backups, _row_backup),
                    spacing="1", width="100%",
                ),
                rx.box(
                    rx.text("Sin backups todavía.",
                            color=T.TEXT_MUTED, size="2"),
                    padding="20px", text_align="center",
                ),
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def _seccion_subir() -> rx.Component:
    upload_id = "config_upload_backup"
    return glass_card(
        rx.vstack(
            rx.hstack(
                rx.icon("upload", size=18, color=T.AMBER),
                rx.heading("Importar backup", size="5",
                           font_family=T.FONT_HEAD),
                width="100%", align="center", spacing="2",
            ),
            rx.text(
                "Sube un .zip generado por esta app. Se validará que contenga "
                "'minty.db' antes de guardarlo en la lista de backups.",
                size="2", color=T.TEXT_MUTED,
            ),
            rx.upload(
                rx.vstack(
                    rx.icon("file-up", size=28, color=T.TEXT_DIM),
                    rx.text("Arrastra un .zip o haz clic para seleccionarlo",
                            size="2", color=T.TEXT_MUTED),
                    rx.text(rx.selected_files(upload_id),
                            size="1", color=T.TEXT_DIM),
                    spacing="2", align="center",
                ),
                id=upload_id,
                accept={"application/zip": [".zip"]},
                multiple=False,
                border=f"1px dashed {T.BORDER}",
                border_radius=T.RADIUS_SM,
                padding="24px",
                width="100%",
            ),
            rx.hstack(
                ghost_button(
                    "Limpiar",
                    on_click=rx.clear_selected_files(upload_id),
                ),
                rx.spacer(),
                primary_button(
                    "Subir backup",
                    on_click=ConfigState.subir_backup(
                        rx.upload_files(upload_id=upload_id)
                    ),
                    icon="upload",
                ),
                width="100%",
            ),
            spacing="3", width="100%", align="stretch",
        ),
    )


def _aviso_postgres() -> rx.Component:
    return glass_card(
        rx.hstack(
            rx.icon("info", size=18, color=T.VIOLET),
            rx.vstack(
                rx.heading("Modo producción (Postgres)", size="4",
                           font_family=T.FONT_HEAD, color=T.TEXT),
                rx.text(
                    "La app está conectada a una base de datos remota. Los "
                    "backups locales (.zip de minty.db) no aplican aquí: usa "
                    "los snapshots de Railway o pg_dump para respaldar.",
                    size="2", color=T.TEXT_MUTED,
                ),
                spacing="1", align="start",
            ),
            spacing="3", align="start", width="100%",
        ),
        padding="18px 22px",
    )


def configuracion_page() -> rx.Component:
    return main_layout(
        page_title("Configuración",
                   "Backups, importación y mantenimiento."),
        rx.box(height="16px"),
        rx.cond(
            ConfigState.is_postgres,
            _aviso_postgres(),
            rx.vstack(
                _seccion_backups(),
                rx.box(height="24px"),
                _seccion_subir(),
                spacing="0", width="100%", align="stretch",
            ),
        ),
    )
