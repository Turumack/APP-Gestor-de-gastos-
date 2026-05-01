import reflex as rx

config = rx.Config(
    app_name="minty",
    db_url="sqlite:///data/minty.db",
    frontend_port=3000,
    backend_port=8000,
    telemetry_enabled=False,
    show_built_with_reflex=False,
    plugins=[rx.plugins.SitemapPlugin(), rx.plugins.TailwindV4Plugin()],
)
