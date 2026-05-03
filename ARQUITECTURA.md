# MINTY — Guía de arquitectura y soporte

> Documento técnico para entender, mantener y extender la app.
> Si solo quieres correrla, mira el [README](README.md).

---

## Tabla de contenidos

1. [Stack y filosofía](#1-stack-y-filosofía)
2. [Arranque rápido](#2-arranque-rápido)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Archivo por archivo](#4-archivo-por-archivo)
5. [Ciclo de una request en Reflex](#5-ciclo-de-una-request-en-reflex)
6. [Modelo de datos](#6-modelo-de-datos)
7. [Migraciones ligeras](#7-migraciones-ligeras)
8. [Recetas comunes](#8-recetas-comunes)
9. [Convenciones de código](#9-convenciones-de-código)
10. [Tests](#10-tests)
11. [Backups](#11-backups)
12. [Solución de problemas](#12-solución-de-problemas)
13. [Conceptos básicos para principiantes](#13-conceptos-básicos-para-principiantes)
14. [Branding y assets](#14-branding-y-assets)
15. [Recetas visuales](#15-recetas-visuales)
16. [Workflow diario](#16-workflow-diario)

---

## 1. Stack y filosofía

| Capa | Herramienta |
|---|---|
| **Lenguaje** | Python 3.14+ |
| **Framework full-stack** | [Reflex](https://reflex.dev) 0.9+ — UI (React generado) + backend (FastAPI) |
| **ORM / modelos** | [SQLModel](https://sqlmodel.tiangolo.com/) sobre SQLite |
| **CSS** | Tailwind v4 (plugin oficial de Reflex) |
| **Iconos** | [Lucide](https://lucide.dev) vía `rx.icon()` |
| **Reportes** | Pandas |
| **HTTP externo** | `requests` (TRM datos.gov.co + Frankfurter) |
| **Tests** | pytest |

**Principios:**
- 🐍 **Todo en Python**: no escribimos JS ni HTML a mano.
- 💾 **Local-first**: la BD vive en `data/minty.db`. Sin servidores, sin telemetría.
- 🧱 **Estado por dominio**: una clase de `State` por área funcional (gastos, ingresos, cajas…).
- 🎨 **Tokens centralizados**: colores y tipografías en `minty/theme.py`. **Nunca** hardcodear colores en componentes.
- 🔁 **Reactividad**: la UI es función del estado. Cambia el estado y la UI se redibuja sola.

---

## 2. Arranque rápido

```bash
# 1. Activar venv
.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate    # macOS/Linux

# 2. Instalar deps (solo la primera vez o tras cambiar requirements)
pip install -r requirements.txt

# 3. Lanzar la app (esto crea data/minty.db si no existe)
reflex run
```

Abre http://localhost:3000.

> 💡 **Hot reload**: Reflex recarga al guardar cualquier `.py`. Si algo se vuelve loco, `Ctrl+F5` en el navegador o borra `.web/` y `.states/`.

---

## 3. Estructura del proyecto

```
APP Gestor de Gastos/
├── rxconfig.py               # Config Reflex (app_name="minty", db_url, plugins)
├── requirements.txt
├── README.md
├── ARQUITECTURA.md            ← estás aquí
├── LICENSE                    # PolyForm Noncommercial 1.0.0
├── .env.example               # plantilla pública (sin secretos reales)
│
├── assets/                    # archivos estáticos servidos en /
│   ├── axium-logo-full.svg
│   ├── axium-logo-text.svg
│   ├── axium_icon.svg         # favicon SVG
│   └── axium_icon.ico
│
├── data/                      # gitignored — tus datos reales
│   └── minty.db
│
├── minty/                     # 🟣 paquete principal
│   ├── __init__.py
│   ├── minty.py               # entrypoint que Reflex busca por convención
│   ├── app.py                 # registro de páginas y rutas
│   ├── models.py              # SQLModel (Gasto, Ingreso, Caja, ...)
│   ├── db.py                  # conexión + migraciones ligeras
│   ├── finance.py             # cálculos puros (saldos, cuotas, recurrencia)
│   ├── theme.py               # tokens (colores, tipografías, gradientes)
│   │
│   ├── components/            # UI reutilizable
│   │   ├── __init__.py        # re-exports
│   │   ├── sidebar.py
│   │   ├── layout.py          # main_layout(content)
│   │   ├── ui.py              # glass_card, page_title, metric_card, pill
│   │   ├── inputs.py          # input/select/date estilizados
│   │   └── period_selector.py
│   │
│   ├── pages/                 # una página = un .py
│   │   ├── home.py
│   │   ├── resumen.py
│   │   ├── ingresos.py
│   │   ├── gastos.py
│   │   ├── compras.py
│   │   ├── cajas.py
│   │   ├── inversiones.py
│   │   ├── baul.py
│   │   ├── presupuestos.py
│   │   └── configuracion.py
│   │
│   ├── state/                 # estado reactivo por dominio
│   │   ├── __init__.py        # exports (PeriodoState, ...)
│   │   ├── _autosetters.py    # decorator @auto_setters
│   │   ├── periodo.py         # mes activo (compartido)
│   │   ├── resumen.py
│   │   ├── ingresos.py
│   │   ├── gastos.py
│   │   ├── compras.py
│   │   ├── cajas.py
│   │   ├── inversiones.py
│   │   ├── baul.py
│   │   ├── presupuestos.py
│   │   └── config.py
│   │
│   └── services/              # integraciones / lógica de I/O
│       ├── trm.py             # TRM oficial (datos.gov.co)
│       ├── fx.py              # Frankfurter (EUR, GBP, ...)
│       ├── scrape.py          # scraping de productos (compras)
│       ├── backup.py          # exportar BD a ZIP
│       └── export.py
│
└── tests/
    └── test_finance.py        # 19 tests sobre finance.py
```

---

## 4. Archivo por archivo

### Raíz

| Archivo | Qué hace |
|---|---|
| `rxconfig.py` | Configura Reflex: `app_name="minty"`, `db_url="sqlite:///data/minty.db"`, plugins (Sitemap + Tailwind v4). |
| `.env.example` | Plantilla pública. La real (`.env`) está gitignored. |
| `LICENSE` | PolyForm Noncommercial 1.0.0. |

### `minty/`

| Archivo | Qué hace |
|---|---|
| `minty.py` | Solo re-exporta `app`. Reflex lo busca por convención (`<app_name>/<app_name>.py`). |
| `app.py` | Crea `rx.App()`, registra cada página con `app.add_page(...)`, define `on_load` (carga inicial). |
| `models.py` | Tablas SQLModel: `Caja`, `Ingreso`, `Gasto`, `Compra`, `ShoppingGroup`, `ShoppingItem`, `Inversion`, `BaulItem`, `Presupuesto`, etc. |
| `db.py` | `engine`, `init_db()` (crea tablas), `_MIGRATIONS_ADD_COLUMNS` (añade columnas en BDs viejas), backup automático opcional. |
| `finance.py` | Funciones puras (sin I/O): cálculo de saldos, reparto de cuotas, avance de recurrencias. **Es lo único que se testea con pytest.** |
| `theme.py` | Tokens: `BG`, `CARD`, `TEXT`, `TEXT_MUTED`, `VIOLET`, `BLUE`, `GREEN`, `RED`, `GRADIENT_BRAND`, `FONT_BODY`, `FONT_HEAD`. |

### `minty/components/`

UI reutilizable. **Solo presentación**, no leen ni escriben BD.

- `sidebar.py` — navegación principal con estado activo según `route`.
- `layout.py` — `main_layout(content)` envuelve cada página con sidebar + contenedor.
- `ui.py` — `glass_card`, `page_title`, `metric_card`, `pill`, `ghost_button`.
- `inputs.py` — wrappers estilizados de `rx.input`, `rx.select`, etc.
- `period_selector.py` — picker de mes/año compartido.

### `minty/pages/`

Una función por página, registrada en `app.py`:

```python
def home_page() -> rx.Component:
    return main_layout(
        rx.vstack(
            page_title("Inicio"),
            ...
        )
    )
```

### `minty/state/`

Cada módulo expone una `class XxxState(rx.State)` con:
- **Vars** — atributos tipados (los que cambian disparan re-render).
- **Event handlers** — métodos que mutan el estado (decorados con `@rx.event` cuando es necesario).
- **`load(self)`** — método llamado en `on_load` que carga datos de la BD.

`_autosetters.py` define `@auto_setters` que genera `set_form_xxx` para cada `form_*` automáticamente (evita boilerplate).

### `minty/services/`

I/O y lógica externa, separada del estado:
- `trm.py` — fetch de TRM oficial COP/USD desde datos.gov.co.
- `fx.py` — conversiones EUR/GBP/etc. vía Frankfurter.
- `backup.py` — `hacer_backup()` exporta `data/minty.db` a un ZIP con timestamp.
- `scrape.py` — scraping de páginas de productos para auto-rellenar precios.

---

## 5. Ciclo de una request en Reflex

```
[Usuario] click → [Frontend React] → [WebSocket] → [Backend Python]
                                                         ↓
                                              event handler en State
                                                         ↓
                                              muta self.var = ...
                                                         ↓
                                              Reflex calcula diff
                                                         ↓
[Usuario] ve cambio ← [Frontend React] ← [WebSocket] ← [Diff JSON]
```

**Implicación práctica:**
- Los métodos del `State` son la "API" interna.
- Las páginas/componentes solo leen `State.var` y enganchan handlers (`on_click=State.guardar`).
- **Nunca** llames `init_db()` o queries SQL desde una página — eso va en el `State`.

---

## 6. Modelo de datos

Tablas principales (todas en `models.py`):

| Tabla | Propósito |
|---|---|
| `Caja` | Cuenta donde está el dinero (efectivo, banco, ahorros, tarjeta de crédito, tarjeta débito). Las TC tienen campos extra: `cupo_total_cop`, `interes_mensual_compras`, `interes_ea_compras`, `interes_mensual_avances`, `interes_ea_avances`, `cuota_manejo`, `dia_cobro_cuota`, `dia_corte`, `usa_dos_cortes`, `dia_corte_2`, `dia_pago`, `trm_tc` (TRM propio del banco), `ultimo_cobro_cuota` (idempotencia mensual). |
| `Ingreso` | Movimiento positivo. Soporta recurrencia. |
| `Gasto` | Movimiento negativo. Soporta cuotas (`cuotas_total`, `cuota_num`, `compra_id`) y recurrencia (`recurrencia_unidad`, `recurrencia_intervalo`). |
| `ShoppingGroup` | Grupo de items en lista de compra (Mercado, Casa, etc.). |
| `ShoppingItem` | Item individual con `precio_estimado`, `recurrente`, `comprado`. |
| `Inversion` | Activo de portafolio. |
| `BaulItem` | Inventario de bienes durables. |
| `Presupuesto` | Límite de gasto por categoría/periodo. |

**Convenciones:**
- Todos los IDs son `int | None = Field(default=None, primary_key=True)`.
- Las fechas son `date` ISO (`YYYY-MM-DD`).
- Los montos son `float` (no `Decimal` — pragmatismo, pero ojo con redondeo en cuotas).

---

## 7. Migraciones ligeras

**No usamos Alembic.** En su lugar, `db.py` tiene una lista declarativa:

```python
_MIGRATIONS_ADD_COLUMNS = [
    ("shoppingitem", "recurrente", "BOOLEAN DEFAULT 0"),
    ("shoppinggroup", "recurrente", "BOOLEAN DEFAULT 0"),
    ("gasto", "recurrencia_unidad", "VARCHAR DEFAULT ''"),
    ("gasto", "recurrencia_intervalo", "INTEGER DEFAULT 1"),
    # ... añade aquí cada columna nueva
]
```

Al iniciar, `db.py` recorre la lista y ejecuta `ALTER TABLE ADD COLUMN` solo si la columna no existe (idempotente).

**Cuándo añadir una entrada:**
- Cuando agregas un campo nuevo a un modelo existente.
- Para campos en tablas nuevas, no hace falta — `SQLModel.metadata.create_all()` los crea.

---

## 8. Recetas comunes

### 8.0 Tarjetas de crédito

- **Modelado**: una TC es una `Caja` con `tipo="tarjeta_credito"` y `saldo_inicial=0`. La deuda emerge de los `Gasto` cuyo `caja_id` apunta a la TC; los pagos son `Movimiento` con `caja_destino_id` = TC.
- **Resumen**: la deuda y disponible se calculan al cierre del periodo activo (`fecha < fin`), no como acumulado eterno.
- **Patrimonio**: el cálculo de Δ Patrimonio en `state/resumen.py` excluye cajas TC y gastos hechos con TC. Los pagos a TC sí restan (es plata real que sale de tus cajas).
- **% Ahorro**: `(Patrimonio + gastos categoría "Ahorro") / Ingresos × 100`. Permite reflejar plata destinada a ahorro/inversión aunque no esté "sobrando".
- **Cuota de manejo automática**: `CajasState._cobrar_cuotas_manejo_si_corresponde()` corre al cargar la página de Cajas y crea un `Gasto` mensual con `notas="[AUTO] Cuota de manejo mensual"` cuando hoy ≥ `dia_cobro_cuota` y aún no se generó este mes (`Caja.ultimo_cobro_cuota = "YYYY-MM"`).
- **Generar recurrentes**: además de gastos recurrentes, el botón también crea cuotas de manejo TC del periodo destino, **solo si la fecha del cobro ya pasó** (no anticipa cobros futuros). Idempotente por (descripción, monto, fecha).

### 8.1 Añadir una página nueva

```python
# minty/pages/mi_pagina.py
import reflex as rx
from minty import theme as T
from minty.components import main_layout, page_title

def mi_pagina() -> rx.Component:
    return main_layout(
        rx.vstack(
            page_title("Mi Página"),
            rx.text("Hola"),
        )
    )
```

```python
# minty/pages/__init__.py
from minty.pages.mi_pagina import mi_pagina
```

```python
# minty/app.py
from minty.pages import mi_pagina
app.add_page(mi_pagina, route="/mi-pagina", title="Mi Página · MINTY")
```

Listo, también añade un `_nav_item(...)` en `sidebar.py` para que aparezca en el menú.

### 8.2 Añadir un campo a un modelo

1. **Añadir el campo** en `minty/models.py`:
   ```python
   class Gasto(SQLModel, table=True):
       ...
       categoria_color: str = ""   # ← nuevo
   ```
2. **Registrar la migración** en `minty/db.py`:
   ```python
   _MIGRATIONS_ADD_COLUMNS = [
       ...
       ("gasto", "categoria_color", "VARCHAR DEFAULT ''"),
   ]
   ```
3. **Reiniciar `reflex run`** — la columna se añade sola.

### 8.3 Añadir un input al formulario

```python
# en state/X.py
form_categoria: str = ""

# en pages/X.py
rx.input(
    placeholder="Categoría",
    value=XState.form_categoria,
    on_change=XState.set_form_categoria,   # generado por @auto_setters
)
```

### 8.4 Llamar lógica al cargar la página

```python
# en app.py
app.add_page(mi_pagina, route="/x", on_load=MiState.load)

# en state/x.py
class MiState(rx.State):
    def load(self):
        with rx.session() as s:
            ...
```

---

## 9. Convenciones de código

- **Nombres**:
  - Clases en `PascalCase`, funciones/variables en `snake_case`.
  - State classes terminan en `State`: `GastosState`, `CajasState`.
  - Páginas terminan en `_page`: `home_page`, `gastos_page`.
- **Imports**: orden estándar (stdlib → third-party → `minty.*`).
- **Colores**: SIEMPRE desde `theme.py` (`T.VIOLET`, no `"#7c3aed"`).
- **Iconos**: `rx.icon("trending-up")` (kebab-case, [Lucide names](https://lucide.dev/icons/)).
- **Strings con datos**: f-strings o `.format()`; no `%`.
- **Tipado**: usa hints en parámetros y retornos siempre que aporte (`def foo(x: int) -> str:`).

---

## 10. Tests

```bash
pytest -v
```

Los tests viven en `tests/test_finance.py` (19 tests). Cubren funciones puras de `finance.py`:
- Reparto de cuotas (12 cuotas con resto correcto).
- Avance de recurrencias (días/semanas/meses/años con intervalo).
- Cálculo de saldos por caja.

**Filosofía**: solo se testea lo que es lógica pura (sin I/O). Los `State` y páginas se prueban manualmente con la app corriendo.

---

## 11. Backups

`minty/services/backup.py` ofrece `hacer_backup()` que copia `data/minty.db` a `backup-YYYYMMDD-HHMMSS.zip`.

Los ZIP están en `.gitignore` (`backup-*.zip`).

**Restaurar**: descomprime el ZIP y reemplaza `data/minty.db`. Reinicia la app.

---

## 12. Solución de problemas

| Síntoma | Solución |
|---|---|
| `ModuleNotFoundError: minty` | ¿Activaste el venv? ¿Estás en la raíz del proyecto? |
| HMR/WebSocket errors en consola | Ruido inofensivo de hot reload. `Ctrl+F5` o borra `.web/` y `.states/`. |
| Cambios en modelos no se ven | Añade la migración en `db.py` y reinicia. |
| El logo no aparece | Verifica que `assets/axium_icon.svg` existe y `app.py` lo referencia con `/axium_icon.svg`. |
| Reflex no encuentra la app | Asegúrate de que `minty/minty.py` exporta `app` y `rxconfig.py` tiene `app_name="minty"`. |
| BD bloqueada (`database is locked`) | Cierra cualquier visor SQLite (DB Browser, etc.) que tenga el archivo abierto. |
| `pytest` falla por imports | `pytest` se corre desde la raíz con el venv activo. |

---

## 13. Conceptos básicos para principiantes

### 13.1 La trinidad de Reflex: Modelo + State + Página

Para construir cualquier funcionalidad necesitas tres archivos coordinados:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  models.py   │───▶│   state/x.py │───▶│   pages/x.py │
│  (la tabla)  │    │  (la lógica) │    │   (la UI)    │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 13.2 Ejemplo mínimo: contador

```python
# minty/state/contador.py
import reflex as rx

class ContadorState(rx.State):
    n: int = 0

    def aumentar(self):
        self.n += 1

# minty/pages/contador.py
import reflex as rx
from minty.state.contador import ContadorState
from minty.components import main_layout

def contador_page() -> rx.Component:
    return main_layout(
        rx.vstack(
            rx.heading(ContadorState.n),
            rx.button("Sumar", on_click=ContadorState.aumentar),
        )
    )
```

Cuando haces click:
1. El botón emite el evento `aumentar`.
2. Reflex llama `ContadorState.aumentar()` en el backend.
3. `self.n` cambia → Reflex detecta el cambio.
4. El frontend recibe el nuevo valor → el `rx.heading` se redibuja.

### 13.3 Condicionales y listas

**Mostrar algo solo si una condición es cierta:**
```python
rx.cond(
    GastosState.form_recurrente,
    rx.text("Sí es recurrente"),
    rx.text("No lo es"),  # else (opcional)
)
```

**Renderizar una lista:**
```python
rx.foreach(
    GastosState.lista_gastos,
    lambda g: rx.text(g.descripcion),
)
```

⚠️ **No uses `if` ni `for` normales sobre vars de estado** — Reflex no puede rastrearlos. Usa siempre `rx.cond` y `rx.foreach`.

### 13.4 ¿Qué es un "var"?

Un atributo de tu `State` con tipo. Ej: `n: int = 0`. Cuando lo modificas con `self.n = ...`, Reflex notifica al frontend. Cuando lo lees en una página (`State.n`), Reflex genera el binding automáticamente.

---

## 14. Branding y assets

### 14.1 ¿Dónde van los archivos estáticos?

Todo en `assets/`. Reflex los sirve en `/`:

```
assets/axium_icon.svg   →   http://localhost:3000/axium_icon.svg
assets/foto.png         →   http://localhost:3000/foto.png
```

### 14.2 Favicon

Configurado en `minty/app.py`:

```python
app = rx.App(
    ...
    head_components=[
        rx.el.link(rel="icon", type="image/svg+xml", href="/axium_icon.svg"),
    ],
)
```

> 💡 Si quieres cambiar el favicon, reemplaza el SVG y refresca con `Ctrl+F5`.

### 14.3 Logo en sidebar

En `minty/components/sidebar.py`:

```python
rx.image(src="/axium_icon.svg", width="70px", height="70px")
rx.heading(
    "MINTY",
    background=T.GRADIENT_BRAND,
    background_clip="text",
    color="transparent",
)
```

**Para cambiar el texto "MINTY":** edita el `rx.heading` en `sidebar.py`.

### 14.4 Tipografías

Cargadas desde Google Fonts en `app.py`:
```python
stylesheets=[
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap",
],
```

Y referenciadas en `theme.py`:
```python
FONT_BODY = "'Inter', sans-serif"
FONT_HEAD = "'Space Grotesk', sans-serif"
```

---

## 15. Recetas visuales

### 15.1 Cambiar el color de marca

Edita `minty/theme.py`:
```python
VIOLET = "#7c3aed"
GRADIENT_BRAND = "linear-gradient(135deg, #7c3aed 0%, #ec4899 100%)"
```

Todo lo que use `T.VIOLET` o `T.GRADIENT_BRAND` se actualiza al guardar.

### 15.2 Cambiar el fondo

```python
# theme.py
BG = "#0a0a0f"      # fondo general
CARD = "#13131a"    # fondo de tarjetas
```

### 15.3 Radios y sombras

Convención: `border_radius="14px"` para tarjetas, `"8px"` para inputs, `"999px"` para chips/pills.

### 15.4 Iconos Lucide

```python
rx.icon("piggy-bank", size=20, color=T.VIOLET)
```

Catálogo completo: [lucide.dev/icons](https://lucide.dev/icons/). Usa **kebab-case** (no `PiggyBank`, sí `"piggy-bank"`).

---

## 16. Workflow diario

### 16.1 Dos terminales

| Terminal 1 | Terminal 2 |
|---|---|
| `reflex run` (servidor + hot reload) | edits, `pytest`, `git status` |

### 16.2 Smoke test rápido

```bash
python -c "from minty.app import app; print('OK')"
pytest -q
```

### 16.3 Antes de hacer push

```bash
pytest -v                       # 19/19 verde
git status                      # ¿hay archivos sensibles trackeados?
git diff --stat                 # ¿el diff es lo que esperabas?
git add -A
git commit -m "..."
git push
```

### 16.4 Glosario

| Término | Significado |
|---|---|
| **Var** | atributo de un `State` que dispara re-render al cambiar. |
| **Event handler** | método de un `State` que muta vars y se llama desde la UI. |
| **Hot reload** | recarga automática al guardar archivos `.py`. |
| **HMR** | Hot Module Replacement (a veces tira errores en consola — son inofensivos). |
| **State scope** | un `rx.State` por usuario/sesión; los datos no se mezclan entre pestañas. |
| **Token** | constante en `theme.py` (color/tipografía/spacing). |
| **Migración ligera** | entrada en `_MIGRATIONS_ADD_COLUMNS` que añade una columna sin Alembic. |

---

> **¿Encontraste algo desactualizado o confuso?** Edita este archivo y abre un PR.
