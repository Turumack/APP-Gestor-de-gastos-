# MINTY — Guía de arquitectura y soporte

Documento de referencia para entender la app, qué tecnología usa y dónde tocar para
agregar o modificar funcionalidad.

> 🆕 **¿Nuevo en Reflex?** Salta directamente al apartado **13. Conceptos básicos**
> (al final), que explica desde cero cómo se relacionan página + state + componente,
> y luego vuelve aquí. Las secciones **14–17** son recetas visuales (favicon, logo,
> modo claro/oscuro animado, etc.) explicadas paso a paso.

---

## 1. Stack tecnológico

| Capa | Tecnología | Para qué |
|---|---|---|
| **Framework full-stack** | [Reflex](https://reflex.dev) `>=0.9` | Define UI, estado y backend en Python puro. Compila el front a React/Vite. |
| **UI / componentes** | Reflex Radix Themes (`rx.button`, `rx.grid`, etc.) | Componentes ya con estilos. |
| **Lenguaje** | Python 3.14+ | Todo el código (front + back) se escribe en Python. |
| **ORM** | [SQLModel](https://sqlmodel.tiangolo.com) | Modelos de base de datos basados en Pydantic + SQLAlchemy. |
| **Base de datos** | SQLite (archivo `data/cuentas.db`) | Persistencia local, sin servidor. |
| **Migraciones** | Custom ligeras en `cuentas_pro/db.py` (`ALTER TABLE ADD COLUMN`) | NO se usa Alembic (genera errores con FKs sin nombre de SQLModel). |
| **Validación / tipos** | Pydantic (vía SQLModel) | Schemas de filas (`*Row` BaseModel) que se envían a la UI. |
| **HTTP cliente** | `requests` | Para `services/scrape.py` (auto-rellenar URLs) y `services/trm.py` (TRM oficial). |
| **APIs externas** | datos.gov.co (TRM USD→COP), Frankfurter (FX otras monedas), OpenGraph + Amazon HTML | Tasas y scraping de productos. |
| **Pandas** | `pandas` | Reservado para reportes / exports CSV. |
| **Tests** | `pytest` | 19 tests en `tests/test_finance.py`. |
| **Compilación frontend** | Vite (lo gestiona Reflex automáticamente) | Bundle JS en `.web/` (regenerado en cada `reflex run`). |

### Conceptos clave de Reflex que usa la app
- **`rx.State`**: clase con campos reactivos. Un cambio en un campo actualiza la UI.
- **`@rx.event`** y **`@rx.event(background=True)`**: decoran handlers de UI.
  Background permite operaciones asíncronas largas (scraping HTTP) sin bloquear.
- **`@rx.var(cache=True)`**: propiedad calculada cacheada que se invalida al cambiar
  sus dependencias (ej. `rows_filtradas`).
- **`auto_setters`** (decorador propio): genera automáticamente un `set_<campo>`
  para cada var del State (Reflex 0.9 ya no lo hace solo). Está en
  `cuentas_pro/state/_autosetters.py`.
- **`rx.session()`**: context manager que abre una sesión SQLModel a la BD.
- **`rx.upload`** + `rx.get_upload_dir()`: manejo de archivos subidos por el usuario
  (imágenes de ítems, restauración de backups). Se sirven en `/_upload/<file>`.
- **`rx.download(data=..., filename=...)`**: dispara la descarga de un archivo
  generado en memoria (backups ZIP).

---

## 2. Cómo arrancar la app

```powershell
# Primera vez
reflex init                # crea estructura .web (solo si no existe)

# Cada vez
reflex run                 # arranca backend (8000) + frontend (3000)
```

> ⚠ El warning `Database is not initialized, run reflex db init first` es **inofensivo**.
> La BD se crea sola desde `cuentas_pro/db.py → ensure_db()`.
> No ejecutes `reflex db init` (rompe por FKs sin nombre).

### Tests
```powershell
python -m pytest tests/ -q
```

---

## 3. Estructura de carpetas

```
APP Gestor de Gastos/
├─ rxconfig.py              # Config de Reflex (nombre app, etc.)
├─ requirements.txt
├─ data/                    # cuentas.db + backups ZIP
├─ uploaded_files/          # imágenes subidas por el usuario
├─ .web/                    # frontend compilado por Vite (auto-generado)
├─ tests/                   # pytest
└─ cuentas_pro/             # ⭐ TODO el código de la app
   ├─ app.py                # punto de entrada Reflex (registra páginas)
   ├─ cuentas_pro.py        # alias / shim para reflex
   ├─ __init__.py
   ├─ db.py                 # init BD, migraciones ligeras, índices
   ├─ models.py             # tablas SQLModel (Gasto, Caja, ShoppingItem…)
   ├─ finance.py            # constantes de dominio (categorías, monedas, colores)
   ├─ theme.py              # tokens de diseño (T.VIOLET, T.RADIUS_SM, fuentes…)
   ├─ components/           # widgets reutilizables de UI
   ├─ pages/                # cada página de la app (1 archivo = 1 ruta)
   ├─ state/                # estados (lógica) por página
   └─ services/             # módulos sin estado (scraping, FX, backups, export)
```

---

## 4. Núcleo (`cuentas_pro/`)

### `app.py`
Punto de entrada de Reflex. Crea el `app = rx.App(...)` y registra cada página
con `app.add_page(funcion_pagina, route="...", on_load=Estado.load)`.
**Para añadir una página nueva**: crea el archivo en `pages/`, su State en
`state/`, y registra la ruta aquí.

### `cuentas_pro.py`
Pequeño shim que Reflex requiere por convención de nombre del paquete principal.

### `db.py`
- `ensure_db()`: crea las tablas si no existen (`SQLModel.metadata.create_all`),
  aplica migraciones ligeras de columnas y crea índices.
- `_MIGRATIONS_ADD_COLUMNS`: lista `(tabla, columna, definición SQL)` que se
  ejecuta como `ALTER TABLE ADD COLUMN` solo si la columna no existe.
  **Cuando agregues un campo nuevo a un modelo, añade aquí la migración** o los
  usuarios con BD antigua reventarán.
- `_INDEXES`: lista de índices a crear (por fecha, por caja, etc.).

### `models.py`
Define todas las tablas con SQLModel. Tablas principales:
- `Caja` — cuentas / billeteras / tarjetas (orígenes de dinero).
- `Ingreso`, `Gasto` — movimientos básicos. Gasto contiene además: `recurrente`,
  `recurrencia_unidad`, `recurrencia_intervalo`, `cuotas_total`, `cuota_num`,
  `compra_id`, vínculo a lista de compra (`shopping_group_id`, `shopping_item_id`).
- `Movimiento` — transferencias internas entre cajas (con cálculo de 4×1000).
- `CDT` — inversiones a plazo fijo.
- `BaulItem` — fondos / metas de ahorro.
- `ShoppingGroup`, `ShoppingItem` — listas de compra (con flag `recurrente` para
  ítems que se compran cíclicamente: mercado, comida del gato, etc.).
- `Presupuesto` — cupos mensuales por categoría.

### `finance.py`
Constantes de dominio: `CATEGORIAS_GASTO`, `CATEGORIAS_INGRESO`, `MEDIOS_PAGO`,
`MONEDAS` (lista + `MONEDAS_FX` con metadatos de Frankfurter), `COLOR_CATEGORIA`
(mapeo categoría → hex). **Para añadir una categoría nueva o cambiar un color,
es aquí**.

### `theme.py`
Tokens de diseño centralizados (no Tailwind, ni CSS-in-JS): `T.VIOLET`, `T.AMBER`,
`T.GREEN`, `T.RED`, `T.BLUE`, `T.PINK`, `T.TEXT`, `T.TEXT_MUTED`, `T.TEXT_DIM`,
`T.BORDER`, `T.RADIUS_SM`, `T.FONT_HEAD`, `T.FONT_MONO`. Si quieres rebrandear,
cambia los hex aquí y se propaga a toda la app.

---

## 5. Componentes (`cuentas_pro/components/`)

UI reutilizable. **Si vas a crear una página nueva, primero mira aquí qué hay.**

| Archivo | Exporta | Para qué |
|---|---|---|
| `inputs.py` | `text_field`, `number_field`, `date_field`, `select_field`, `field_label` | Inputs estándar con label arriba y estilos del tema. |
| `ui.py` | `glass_card`, `pill`, `metric_card`, `primary_button`, `ghost_button`, `page_title` | Tarjetas, chips, botones con estilo tema. |
| `layout.py` | `main_layout` | Wrapper de página: sidebar + contenido + selector de período. |
| `sidebar.py` | `sidebar` | Menú lateral con grupos (FINANZAS, COMPRAS, SISTEMA…). |
| `period_selector.py` | `period_selector` | Selector mes/año en el header. |
| `__init__.py` | (re-exports) | Permite `from cuentas_pro.components import …`. |

---

## 6. Páginas (`cuentas_pro/pages/`)

Cada archivo define UNA función que devuelve `rx.Component`. Está conectada a un
State en `state/`. **Convención: la función se llama `<nombre>_page()`.**

| Archivo | Ruta | State | Para qué |
|---|---|---|---|
| `home.py` | `/` | varios | Dashboard de bienvenida. |
| `resumen.py` | `/resumen` | `ResumenState` | Resumen del periodo activo: KPIs, totales, gráficos. |
| `gastos.py` | `/gastos` | `GastosState` | Calendario visual + lista + formulario de gastos (con cuotas, recurrencia, multimoneda, vínculo a listas de compra). |
| `ingresos.py` | `/ingresos` | `IngresosState` | Registro de ingresos. |
| `cajas.py` | `/cajas` | `CajasState` | Cuentas/billeteras + transferencias internas + cálculo 4×1000. |
| `compras.py` | `/compras` | `ComprasState` | Listas de compra (grupos + ítems con foto, link, recurrencia). Incluye auto-rellenar desde URL Amazon/OG. |
| `inversiones.py` | `/inversiones` | `InversionesState` | CDTs / inversiones. |
| `baul.py` | `/baul` | `BaulState` | Fondos / metas de ahorro. |
| `presupuestos.py` | `/presupuestos` | `PresupuestosState` | Cupos mensuales por categoría con alertas. |
| `configuracion.py` | `/configuracion` | `ConfigState` | Backup/restore manual de la BD. |

---

## 7. Estados (`cuentas_pro/state/`)

Un State por página, con la lógica + datos reactivos. **Aquí está el 80% de la
lógica de negocio.**

| Archivo | Clase | Responsabilidad clave |
|---|---|---|
| `periodo.py` | `PeriodoState` | Mes/año activo (filtro global). Recalcula `fecha_inicio` / `fecha_fin`. |
| `gastos.py` | `GastosState` | CRUD gastos + calendario + cuotas (`_avanzar_meses`) + recurrencia avanzada (`_avanzar_periodo`) + duplicados + multimoneda + listas de compra. |
| `ingresos.py` | `IngresosState` | CRUD ingresos. |
| `cajas.py` | `CajasState` | CRUD cajas + transferencias + saldos calculados. |
| `compras.py` | `ComprasState` | CRUD grupos/ítems de listas. Auto-rellenar URL. Subir imagen local/URL. Toggle recurrente, marcar comprado, editar. |
| `inversiones.py` | `InversionesState` | CDTs. |
| `baul.py` | `BaulState` | Fondos/metas. |
| `presupuestos.py` | `PresupuestosState` | Cupos por categoría/mes. |
| `resumen.py` | `ResumenState` | Agrega datos del periodo para el dashboard. |
| `config.py` | `ConfigState` | Backup/restore (lista, descarga, sube ZIP, restaura). |
| `_autosetters.py` | `auto_setters` decorator | Genera `set_<campo>` para cada var del State, con coerción de tipos. |
| `__init__.py` | re-exports | Export central de States. |

### Flujo típico al guardar (ejemplo gasto)
1. Usuario llena el formulario → `set_form_*` actualizan el State.
2. Click "Guardar" → `GastosState.guardar()` valida, calcula COP, abre `rx.session()`.
3. Inserta `Gasto(...)`, marca ítem comprado si aplica.
4. `await self.load()` recarga `rows`, totales, `por_categoria`, calendario.

---

## 8. Servicios (`cuentas_pro/services/`)

Funciones puras / módulos sin estado (no son `rx.State`). Llamados desde States.

| Archivo | Exporta | Para qué |
|---|---|---|
| `trm.py` | `obtener_trm(fecha)` | Consulta TRM USD→COP en datos.gov.co. |
| `fx.py` | `obtener_tasa_a_cop(moneda, fecha)`, `MONEDAS_FX` | Otras divisas vía Frankfurter. |
| `scrape.py` | `auto_rellenar_desde_url(url) -> ScrapeResult` | Descarga HTML (límite 1.5 MB), extrae OpenGraph + Amazon (`productTitle`, `landingImage`). Devuelve `nombre`, `imagen_url`, `link`, `fuente`, `error`. Nunca lanza. |
| `backup.py` | `hacer_backup`, `listar_backups`, `restaurar_backup`, `BACKUP_DIR` | Backups ZIP de `cuentas.db` con safety snapshot al restaurar. |
| `export.py` | `filas_a_csv` | Exporta filas a CSV en memoria. |
| `__init__.py` | re-exports | API pública del paquete. |

---

## 9. Datos en disco

| Carpeta / Archivo | Contenido |
|---|---|
| `data/cuentas.db` | SQLite principal. **No editar a mano.** |
| `data/backup-*.zip` | Backups manuales. Cada ZIP contiene `cuentas.db`. |
| `uploaded_files/` | Imágenes subidas (`item-<uuid>.jpg`, etc.) servidas en `/_upload/<archivo>`. |
| `.web/` | Frontend compilado. Si algo se ve raro tras un cambio fuerte, bórralo y `reflex run` lo regenera. |
| `.states/` | Estado serializado de Reflex (cache interno). Borrable. |

---

## 10. Cómo añadir cosas nuevas (recetas)

### 🔹 Añadir un campo a una tabla existente
1. Edita el modelo en [models.py](cuentas_pro/models.py).
2. Añade la migración en `_MIGRATIONS_ADD_COLUMNS` de [db.py](cuentas_pro/db.py).
3. Si vas a indexarlo, añade en `_INDEXES`.
4. Actualiza el `*Row` BaseModel del state correspondiente.
5. Persiste el campo al guardar y léelo al cargar.
6. Muestra el campo en la página.

### 🔹 Añadir una categoría de gasto
Edita `CATEGORIAS_GASTO` y `COLOR_CATEGORIA` en [finance.py](cuentas_pro/finance.py).

### 🔹 Añadir una página nueva
1. Crea `cuentas_pro/state/mipagina.py` con `class MiPaginaState(rx.State)`
   decorada con `@auto_setters`.
2. Crea `cuentas_pro/pages/mipagina.py` con `def mipagina_page() -> rx.Component`.
3. Regístrala en [app.py](cuentas_pro/app.py): `app.add_page(mipagina_page, route="/mipagina", on_load=MiPaginaState.load)`.
4. Añade el item en la sidebar en [components/sidebar.py](cuentas_pro/components/sidebar.py).

### 🔹 Cambiar colores / fuentes
Solo [theme.py](cuentas_pro/theme.py).

### 🔹 Añadir un nuevo formato de recurrencia o cuota
Lógica en [state/gastos.py](cuentas_pro/state/gastos.py) — helpers
`_avanzar_meses`, `_avanzar_periodo`, `_label_recurrencia` y los métodos
`guardar()` / `generar_recurrentes()`.

### 🔹 Soporte de una nueva tienda en auto-rellenar
Edita [services/scrape.py](cuentas_pro/services/scrape.py) y añade selectores
específicos antes del fallback OpenGraph.

---

## 11. Tips de soporte / debugging

- **Smoke rápido**: `python -c "from cuentas_pro.app import app; print('OK')"` valida que toda la app importa.
- **Tests**: `python -m pytest tests/ -q` (19 tests sobre cálculos financieros).
- **El warning de "Database is not initialized"**: ignorar. La BD la crea `ensure_db()`.
- **Errores de HMR `No module update found for route routes/._index`**: ruido del frontend, refresca con `Ctrl+F5`. Si persiste, borra `.web/` y vuelve a `reflex run`.
- **Ver tablas reales**: cualquier visor SQLite (DB Browser for SQLite) sobre `data/cuentas.db`.
- **Reset total de BD** (¡destructivo!): cierra `reflex run`, borra `data/cuentas.db`, vuelve a arrancar. Las tablas se crean vacías. Haz backup antes desde la página `/configuracion`.

---

## 12. Convenciones de código

- UI y nombres de dominio en **español** (`form_cuotas`, `compra_id`, `recurrencia_unidad`).
- Mensajes a usuario con prefijo: `✓` ok, `⚠` warn, `ℹ` info, `⏳` cargando.
- En State: handlers `@rx.event`; vars derivadas `@rx.var(cache=True)`.
- En componentes: importar tema como `from cuentas_pro import theme as T` y usar `T.VIOLET`, `T.RADIUS_SM`, etc.
- BD: NO usar Alembic. Cambios de esquema vía `_MIGRATIONS_ADD_COLUMNS` en `db.py`.
- Filas hacia la UI: siempre via `pydantic.BaseModel` (`*Row`) — nunca pasar un objeto SQLModel directamente al State.

---

## 13. Conceptos básicos (lectura obligatoria si nunca usaste Reflex)

Reflex te deja escribir **todo en Python**: tanto el backend (BD, validación,
lógica) como el frontend (HTML/CSS/JS). Cuando ejecutas `reflex run`, Reflex:

1. Levanta un servidor web en `http://localhost:8000` (backend).
2. Compila tus archivos `.py` a un proyecto React/Vite y lo sirve en
   `http://localhost:3000` (frontend). El bundle compilado vive en `.web/`.
3. Conecta ambos por WebSocket: cuando cambias un campo del State en Python,
   Reflex envía el cambio al navegador y la UI se actualiza sola.

### Las 3 piezas de toda funcionalidad

| Pieza | Archivo típico | Qué es |
|---|---|---|
| **Modelo (BD)** | [models.py](cuentas_pro/models.py) | Una tabla. Define columnas. |
| **Estado (lógica)** | [state/<algo>.py](cuentas_pro/state/) | Variables reactivas + funciones (`@rx.event`). |
| **Página (UI)** | [pages/<algo>.py](cuentas_pro/pages/) | Función que devuelve componentes (`rx.box`, `rx.button`…). |

Ejemplo mental: un botón "Guardar" en `pages/gastos.py` llama a
`GastosState.guardar` (en `state/gastos.py`), el cual abre una sesión SQLModel
y guarda un objeto `Gasto` (en `models.py`) en `data/cuentas.db`.

### Anatomía mínima de una página Reflex

```python
# state/contador.py
import reflex as rx

class ContadorState(rx.State):
    n: int = 0

    @rx.event
    def aumentar(self):
        self.n += 1

# pages/contador.py
import reflex as rx
from cuentas_pro.state.contador import ContadorState

def contador_page():
    return rx.vstack(
        rx.heading(ContadorState.n),         # se actualiza solo
        rx.button("Sumar", on_click=ContadorState.aumentar),
    )

# app.py
app.add_page(contador_page, route="/contador")
```

### Reglas que confunden al principio
- **No puedes hacer `if state.n > 0:` directamente en una página** porque la
  página se renderiza una sola vez. Usa `rx.cond(state.n > 0, ComponenteSi, ComponenteNo)`.
- **No puedes hacer `for x in state.lista:`** en la página. Usa `rx.foreach(state.lista, lambda x: ...)`.
- **Las funciones decoradas con `@rx.event` se llaman SIN paréntesis** cuando
  no llevan argumentos: `on_click=Estado.guardar`. Con argumentos: `on_click=Estado.editar(item.id)`.
- **`rx.var` es para campos calculados** (cache automático). `@rx.event` es para acciones.

---

## 14. Branding: favicon, logo y título de la pestaña

### 14.1 Carpeta `assets/`
Reflex sirve cualquier archivo dentro de `assets/` en la raíz del sitio.
Hoy esta carpeta **no existe** en el proyecto. Créala así:

```powershell
mkdir assets
```

Y mete dentro tus imágenes:
```
assets/
├─ favicon.ico        # icono pestaña navegador (16x16/32x32)
├─ logo.svg           # logo grande (preferible SVG por nitidez)
├─ logo.png           # alternativa PNG si no tienes SVG
└─ apple-touch-icon.png  # 180x180 para iOS al "guardar en pantalla de inicio"
```

> Reflex NO regenera `.web/` automáticamente cuando cambias `assets/`. Si tras
> meter un archivo no lo ves: detén `reflex run`, borra `.web/` y vuelve a arrancar.

### 14.2 Cambiar el favicon (icono de la pestaña del navegador)

Pon `assets/favicon.ico` (puedes generarlo en https://favicon.io a partir de
una imagen). Reflex lo enlaza solo. Si quieres uno custom o un PNG, edítalo en
[cuentas_pro/app.py](cuentas_pro/app.py) en la creación de `rx.App`:

```python
app = rx.App(
    theme=rx.theme(...),
    style=T.GLOBAL_CSS,
    stylesheets=[...],
    head_components=[
        rx.el.link(rel="icon", type="image/svg+xml", href="/logo.svg"),
        rx.el.link(rel="apple-touch-icon", href="/apple-touch-icon.png"),
    ],
)
```

> Las rutas empiezan con `/` y se sirven desde `assets/`. Es decir:
> `assets/logo.svg` → URL `/logo.svg`.

### 14.3 Cambiar el título de cada pestaña
Ya está hecho en `app.py` con el parámetro `title="..."` de cada `add_page`.
Cambia "Minty" por lo que quieras allí. Si quieres un título global por defecto,
usa el parámetro `head_components` con `rx.el.title("Mi App")`.

### 14.4 Cambiar el logo del sidebar
El logo actual es un cuadrado con el icono de "wallet" sobre un gradiente
violeta→pink. Está en [cuentas_pro/components/sidebar.py](cuentas_pro/components/sidebar.py)
en el bloque marcado `# ── Logo ──`.

**Para cambiar a una imagen propia:**

```python
# Reemplaza el rx.box con icon por:
rx.image(
    src="/logo.svg",     # o "/logo.png"
    width="38px",
    height="38px",
    border_radius="12px",
),
```

**Para cambiar solo el icono o el color del gradiente:**
- Icono: cambia `rx.icon("wallet", ...)` por otro nombre de
  [Lucide](https://lucide.dev) (ej. `"piggy-bank"`, `"sparkles"`, `"coins"`).
- Gradiente: edita `GRADIENT_BRAND` en [cuentas_pro/theme.py](cuentas_pro/theme.py).

**Para cambiar el texto "MINTY":**
Está justo debajo del logo en el mismo archivo (`rx.heading("Cuentas", ...)` y `rx.text("PRO", ...)`).

### 14.5 Tipografía
Las fuentes Inter + Space Grotesk se cargan desde Google Fonts en `app.py`
(`stylesheets=[...]`) y se aplican en `theme.py` (`FONT_BODY`, `FONT_HEAD`).
Para cambiarlas:
1. Reemplaza la URL en `app.py` por la nueva familia de Google Fonts.
2. Cambia los strings `FONT_BODY` y `FONT_HEAD` en `theme.py`.

---

## 15. Modo claro/oscuro con animación custom (theme-toggle.rdsx.dev)

El componente de https://theme-toggle.rdsx.dev usa la **View Transitions API**
del navegador para hacer un "barrido circular" cuando cambia el tema. Sí se puede
integrar en Reflex pero hay que entender que:

- Reflex actualmente soporta `dark` / `light` en `rx.theme(appearance=...)`,
  pero para que el toggle anime y persista, hay que mezclar State + JS inyectado.

### 15.1 Plan en 4 pasos
1. **Variable de tema en el State** (Python).
2. **CSS para variantes light/dark** (en `theme.py`).
3. **Inyectar el JS de la View Transition** (con `rx.script`).
4. **Botón toggle** que dispara la animación y cambia el estado.

### 15.2 Crear un State global de tema
Crea `cuentas_pro/state/ui.py`:

```python
"""Estado global de UI: modo claro/oscuro, sidebar, etc."""
import reflex as rx
from cuentas_pro.state._autosetters import auto_setters


@auto_setters
class UIState(rx.State):
    # "dark" o "light"
    appearance: str = "dark"

    @rx.event
    def toggle_tema(self):
        self.appearance = "light" if self.appearance == "dark" else "dark"
```

### 15.3 Inyectar el JS de la transición circular
En `cuentas_pro/components/` crea `theme_toggle.py`:

```python
"""Botón con animación circular de cambio de tema (estilo theme-toggle.rdsx.dev)."""
import reflex as rx
from cuentas_pro import theme as T
from cuentas_pro.state.ui import UIState


# JS que dispara la animación con la View Transitions API.
# Si el navegador no la soporta, simplemente cambia el data-attribute sin animar.
_THEME_TOGGLE_JS = """
function _applyTheme(t, x, y) {
    const root = document.documentElement;
    if (!document.startViewTransition) {
        root.dataset.theme = t;
        return;
    }
    const transition = document.startViewTransition(() => {
        root.dataset.theme = t;
    });
    transition.ready.then(() => {
        const radius = Math.hypot(
            Math.max(x, innerWidth - x),
            Math.max(y, innerHeight - y)
        );
        document.documentElement.animate(
            {
                clipPath: [
                    `circle(0px at ${x}px ${y}px)`,
                    `circle(${radius}px at ${x}px ${y}px)`,
                ],
            },
            {
                duration: 500,
                easing: "ease-in-out",
                pseudoElement: "::view-transition-new(root)",
            }
        );
    });
}
"""


def theme_toggle() -> rx.Component:
    return rx.fragment(
        rx.script(_THEME_TOGGLE_JS),
        rx.button(
            rx.icon(
                rx.cond(UIState.appearance == "dark", "sun", "moon"),
                size=18,
            ),
            # on_click llama JS antes de cambiar el state (la animación
            # necesita el evento real para tomar coords del click).
            on_click=[
                rx.call_script(
                    "_applyTheme("
                    f"'{rx.cond(UIState.appearance == 'dark', 'light', 'dark')}', "
                    "event.clientX, event.clientY)"
                ),
                UIState.toggle_tema,
            ],
            variant="ghost",
            cursor="pointer",
            color=T.TEXT_MUTED,
            _hover={"color": T.TEXT, "background": "rgba(255,255,255,.06)"},
        ),
    )
```

> ⚠ La función `rx.call_script` ejecuta JS con acceso al `event`. La sintaxis
> exacta puede variar entre versiones de Reflex; si te da problemas, usa
> `on_click=rx.call_script(_THEME_TOGGLE_JS_INLINE)` con el JS embebido y
> que él mismo cambie el atributo + envíe un `fetch` al backend para persistir.

### 15.4 Variables CSS por tema
En [cuentas_pro/theme.py](cuentas_pro/theme.py) añade al `GLOBAL_CSS`:

```python
GLOBAL_CSS = {
    # ...lo que ya existe...
    ":root": {
        "--bg": BG,
        "--text": TEXT,
        # ...todas las variables que uses...
    },
    "[data-theme='light']": {
        "--bg": "#f7f7fb",
        "--text": "#0a0a0f",
        # ...overrides para light...
    },
    "::view-transition-old(root), ::view-transition-new(root)": {
        "animation": "none",
        "mix-blend-mode": "normal",
    },
}
```

Y en los componentes usa `var(--bg)` en lugar de `T.BG`. (Es un refactor grande;
puedes empezar solo con `body { background: var(--bg) }` y migrar gradualmente.)

### 15.5 Montar el botón
En [cuentas_pro/components/sidebar.py](cuentas_pro/components/sidebar.py) o en
[components/layout.py](cuentas_pro/components/layout.py) (en el header), importa
`from cuentas_pro.components.theme_toggle import theme_toggle` y mételo donde
quieras: `theme_toggle()`.

### 15.6 Persistencia (opcional)
Para que el tema sobreviva al refresh del navegador, usa `rx.LocalStorage` en
lugar de `str` plano en el State:

```python
appearance: str = rx.LocalStorage("dark")
```

Reflex serializa esa var en `localStorage` y la lee al cargar.

---

## 16. Recetas visuales rápidas

### 16.1 Cambiar el color de marca
Edita `VIOLET` y/o `PINK` en [theme.py](cuentas_pro/theme.py) — todo se actualiza
porque el resto del código solo usa `T.VIOLET`, `T.PINK`, `T.GRADIENT_BRAND`.

### 16.2 Cambiar el fondo de la app
Edita `BG` en `theme.py` (color base) y/o el `body { background }` dentro de
`GLOBAL_CSS` (los radial-gradients de fondo).

### 16.3 Cambiar el radio de las tarjetas
Edita `RADIUS`, `RADIUS_SM`, etc. en `theme.py`. Los componentes de
`components/ui.py` (`glass_card`, etc.) los consumen.

### 16.4 Añadir un icono nuevo
Reflex usa Lucide. Lista completa en https://lucide.dev. Uso:
```python
rx.icon("piggy-bank", size=18, color=T.VIOLET)
```

### 16.5 Añadir un item al menú lateral
Edita [components/sidebar.py](cuentas_pro/components/sidebar.py) y agrega:
```python
_nav_item("Mi cosa", "sparkles", "/mi-ruta", route)
```
dentro del grupo correspondiente. Recuerda registrar la página en `app.py`.

### 16.6 Inyectar CSS personalizado global
Todo lo que pongas en el dict `GLOBAL_CSS` de `theme.py` se aplica como CSS
global. Soporta `@import`, selectores normales, pseudo-clases, media queries
(con strings tipo `"@media (max-width: 768px)": {...}`).

---

## 17. Workflow recomendado para tocar la app

1. **Abre dos terminales**: en una `reflex run` (déjala corriendo); en otra,
   editas código.
2. Reflex hace **hot reload** de Python: al guardar un `.py` la app se reinicia
   sola (mira la terminal de `reflex run` por errores).
3. Si el navegador queda raro tras un cambio (errores HMR, página en blanco):
   `Ctrl+F5` y, si persiste, detén `reflex run`, borra `.web/`, arranca otra vez.
4. Antes de subir cambios:
   ```powershell
   python -c "from cuentas_pro.app import app; print('OK')"
   python -m pytest tests/ -q
   ```
5. **Commit**: si modificaste el esquema de BD, recuerda migrar
   `_MIGRATIONS_ADD_COLUMNS` (sección 10).

### Glosario rápido
- **HMR** (Hot Module Reload): el navegador actualiza sin recargar entera la página.
- **State**: contenedor de variables reactivas en Python.
- **Var**: cualquier atributo del State; al cambiar, la UI que lo usa se redibuja.
- **Event**: función decorada con `@rx.event` que reacciona a un click, submit, etc.
- **Cond / Foreach**: equivalentes a `if`/`for` que SÍ se pueden usar dentro de
  componentes (`rx.cond(...)`, `rx.foreach(...)`).
- **Componente**: cualquier `rx.algo(...)` que devuelve UI. Pueden anidarse.
- **Asset**: archivo estático (imagen, fuente, ícono SVG) servido desde `assets/`.
