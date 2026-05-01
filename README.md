<div align="center">

<img src="assets/axium-logo-full.svg" alt="Axium / Cuentas PRO" width="320" />

# Cuentas PRO

**Gestor personal de finanzas, hecho con [Reflex](https://reflex.dev) puro Python.**
Controla gastos, ingresos, cajas, inversiones y compras recurrentes desde una sola app local — sin nube, sin telemetría, sin ataduras.

[![Python](https://img.shields.io/badge/Python-3.14+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Reflex](https://img.shields.io/badge/Reflex-0.9+-5646ED?style=for-the-badge&logo=reflex&logoColor=white)](https://reflex.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-Local-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#-licencia)

[Funcionalidades](#-funcionalidades) • [Instalación](#-instalación) • [Estructura](#-estructura-del-proyecto) • [Arquitectura](ARQUITECTURA.md) • [Roadmap](#-roadmap)

</div>

---

## ✨ ¿Qué es esto?

**Cuentas PRO** es una app full-stack escrita 100 % en Python que te permite llevar tu contabilidad personal con la potencia de una hoja de cálculo y la comodidad de una interfaz moderna.

A diferencia de un Excel, tiene **estado reactivo**, formularios, validación, reportes por periodo y soporte para compras a cuotas, recurrencias avanzadas y conversiones de divisas en vivo. Todo corriendo en tu máquina, con SQLite y sin enviar ni un byte a la nube.

> 💡 **Ideal para:** quien quiera control fino de sus finanzas, programadores curiosos por aprender Reflex, o cualquiera que prefiera privacidad sobre comodidad de un SaaS.

---

## 🚀 Funcionalidades

### 📊 Módulos principales

| Módulo | Descripción |
|---|---|
| 🏠 **Inicio** | Dashboard con totales del periodo activo y accesos rápidos. |
| 📈 **Resumen** | Análisis del periodo: ingresos vs. gastos, saldos por caja, top categorías. |
| 💸 **Gastos** | Registro detallado, categorías, compras a cuotas, **recurrencias avanzadas** (días/semanas/meses/años con intervalo). |
| 💰 **Ingresos** | Salarios, freelance, devoluciones — con soporte multi-moneda y recurrencia. |
| 🏦 **Cajas** | Múltiples cuentas (efectivo, banco, ahorros, tarjeta) con saldos calculados en tiempo real. |
| 🛒 **Compras** | Lista de mercado / wishlist con grupos, ítems recurrentes y conversión a gasto en un click. |
| 📦 **Baúl** | Inventario de bienes durables con depreciación opcional. |
| 📉 **Inversiones** | Seguimiento de portafolio, P&L, rendimiento por activo. |

### 🛠️ Características técnicas

- ⚡ **Reactividad total** — la UI se actualiza sola cuando el state cambia (sin `setState` ni Redux).
- 🔁 **Recurrencias inteligentes** — define un gasto cada 2 meses, cada 15 días o cada año; la app genera las ocurrencias automáticamente y de forma idempotente.
- 💳 **Compras a cuotas** — registra una compra a 12 cuotas y se reparten correctamente entre los periodos.
- 🌍 **Conversión de divisas en vivo** — TRM oficial (datos.gov.co) + Frankfurter para EUR/GBP/etc.
- 🎨 **Tema claro/oscuro** con animación de transición de vista (View Transitions API).
- 🔐 **100 % local** — tus datos nunca salen de tu máquina (`data/cuentas.db`).
- 🔄 **Backups manuales** integrados (export ZIP de la base de datos).
- ✅ **Tests** con `pytest` (19/19 verdes).

---

## 🖼️ Capturas

(assets/screenshots/home.png)
(assets/screenshots/gastos.png)

---

## 🧰 Stack

- **[Reflex](https://reflex.dev)** 0.9+ — frontend (React generado) + backend (FastAPI) en un solo Python.
- **[SQLModel](https://sqlmodel.tiangolo.com/)** sobre SQLite — modelos tipados, migraciones ligeras propias.
- **[Tailwind v4](https://tailwindcss.com)** vía plugin oficial de Reflex.
- **[Lucide Icons](https://lucide.dev)** — iconos consistentes en toda la app.
- **[Pandas](https://pandas.pydata.org/)** — para reportes y agregaciones.
- **[Requests](https://docs.python-requests.org/)** — fetch de TRM y tasas de cambio.

---

## ⚙️ Instalación

### Requisitos

- **Python 3.14+** (probado en 3.14.0)
- **Node.js 18+** (Reflex lo usa para el frontend; lo instala solo la primera vez)
- Windows / macOS / Linux

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Turumack/APP-Gestor-de-gastos-.git
cd APP-Gestor-de-gastos-

# 2. Crear y activar entorno virtual
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Configurar variables de entorno
cp .env.example .env
# edita .env si quieres usar Supabase, etc.

# 5. Inicializar Reflex (solo la primera vez)
reflex init

# 6. ¡Lanzar la app!
reflex run
```

La app abre en:
- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000

> 💡 La base de datos SQLite se crea automáticamente en `data/cuentas.db` la primera vez que la lanzas. Está en `.gitignore`, así que es 100 % tuya.

---

## 📁 Estructura del proyecto

```
APP Gestor de Gastos/
├── 📄 rxconfig.py              # Configuración de Reflex (puertos, BD, plugins)
├── 📄 requirements.txt         # Dependencias Python
├── 📄 ARQUITECTURA.md          # Guía técnica detallada
├── 📁 assets/                  # Logos, iconos, fuentes
├── 📁 data/                    # SQLite local (gitignored)
└── 📁 cuentas_pro/             # App principal
    ├── app.py                  # Entry point + montaje de páginas
    ├── models.py               # SQLModel (Gasto, Ingreso, Caja, ...)
    ├── db.py                   # Conexión + migraciones ligeras
    ├── theme.py                # Paleta de colores y tokens
    ├── 📁 components/          # UI reutilizable (sidebar, inputs, layout, ...)
    ├── 📁 pages/               # Una página = un .py (home, gastos, ingresos, ...)
    ├── 📁 state/               # Estado reactivo por dominio
    └── 📁 services/            # Integraciones externas (TRM, scraping)
```

> 📖 Para entender cómo encaja todo, ver **[ARQUITECTURA.md](ARQUITECTURA.md)** — incluye glosario, recetas y guía para principiantes.

---

## 🧪 Tests

```bash
pytest -v
```

Los tests cubren cálculos de saldos, generación de recurrencias y reparto de cuotas.

---

## 🛣️ Roadmap

- [x] Recurrencia avanzada (días / semanas / meses / años)
- [x] Editar grupos e ítems de compra
- [x] Compras únicas vs. recurrentes
- [x] Eliminar compra completa (todas sus cuotas)
- [x] Theme toggle con View Transitions API
- [ ] Importar extractos bancarios (CSV / OFX)
- [ ] Gráficos interactivos en el resumen
- [ ] App móvil (Reflex Native cuando esté maduro)
- [ ] Exportar reportes a PDF
- [ ] Soporte multi-usuario opcional con Supabase

---

## 🤝 Contribuir

Pull requests bienvenidos. Para cambios grandes, abre primero un issue para discutir qué te gustaría añadir.

```bash
# Flujo recomendado
git checkout -b feat/mi-feature
# ... haz cambios ...
pytest -v          # asegúrate de que todo pasa
git commit -m "feat: descripción corta"
git push origin feat/mi-feature
# abre el PR en GitHub
```

---

## 🔒 Privacidad y datos

- Esta app **no envía datos a ningún servidor externo** por defecto.
- La telemetría de Reflex está **desactivada** (`telemetry_enabled=False` en `rxconfig.py`).
- Tu base de datos vive solo en `data/cuentas.db` (gitignored).
- Si configuras Supabase en `.env`, **ese archivo está gitignored**.

---

## 📜 Licencia

Distribuido bajo licencia **MIT**. Ver [LICENSE](LICENSE) para más detalles.

---

## 💬 Autor

Hecho con ❤️ por [**@Turumack**](https://github.com/Turumack)

> *Si esta app te resulta útil, ⭐ una estrella en GitHub me hace el día.*

