"""Lógica de cálculos financieros — salarios y extras Colombia."""
from __future__ import annotations

# ── Deducciones legales Colombia ───────────────────────
PCT_SALUD = 0.04
PCT_PENSION = 0.04
PCT_DEDUCCION_BASE = PCT_SALUD + PCT_PENSION   # 8% sobre salario base
PCT_GMF = 0.004                                # 4x1000

# ── Recargos Código Sustantivo del Trabajo ─────────────
RECARGOS: dict[str, float] = {
    "extra_diurna": 1.25,              # +25%
    "extra_nocturna": 1.75,            # +75%
    "recargo_nocturno": 1.35,          # +35% (hora ord. nocturna)
    "dominical_diurna": 1.75,          # +75% (hora ord. dom/festivo)
    "dominical_nocturna": 2.10,        # +110% (ord nocturna dom/festivo)
    "extra_dominical_diurna": 2.00,    # +100% (extra diurna dom/festivo)
    "extra_dominical_nocturna": 2.50,  # +150% (extra nocturna dom/festivo)
}

RECARGO_LABELS: dict[str, str] = {
    "extra_diurna": "Extra diurna (+25%)",
    "extra_nocturna": "Extra nocturna (+75%)",
    "recargo_nocturno": "Recargo nocturno (+35%)",
    "dominical_diurna": "Dominical diurna (+75%)",
    "dominical_nocturna": "Dominical nocturna (+110%)",
    "extra_dominical_diurna": "Extra dominical diurna (+100%)",
    "extra_dominical_nocturna": "Extra dominical nocturna (+150%)",
}

HORAS_SEMANA_LEGAL = 44  # Colombia 2026 (Ley 2101/2021)
HORAS_MES_LEGAL = 240    # 8h × 30 días (legal máximo histórico)


def horas_mes_desde_semana(horas_semana: float) -> float:
    """Convierte jornada semanal a mensual promedio (52/12 semanas/mes)."""
    return horas_semana * 52 / 12


def valor_hora_ordinaria(salario_base: float, horas_mes: int = HORAS_MES_LEGAL) -> float:
    if horas_mes <= 0:
        return 0.0
    return salario_base / horas_mes


def calcular_extras(salario_base: float, horas: dict[str, float], horas_mes: int = HORAS_MES_LEGAL) -> dict:
    """Calcula el pago de cada concepto de extras y el total."""
    vh = valor_hora_ordinaria(salario_base, horas_mes)
    detalle: dict = {"valor_hora_ordinaria": vh}
    total = 0.0
    for key, factor in RECARGOS.items():
        h = float(horas.get(key, 0) or 0)
        monto = h * vh * factor
        detalle[key] = monto
        total += monto
    detalle["total"] = total
    return detalle


def calculate_net_income(salario_base: float, aux_transporte: float, otros: float) -> float:
    """Salario neto estimado = (base * 0.92) + aux + otros, luego 4x1000."""
    base_descontado = salario_base * (1 - PCT_DEDUCCION_BASE)
    bruto = base_descontado + aux_transporte + otros
    return bruto * (1 - PCT_GMF)


# ── Categorías de gasto y colores ──────────────────────
CATEGORIAS_GASTO: list[str] = [
    "Alimentación",
    "Transporte",
    "Vivienda",
    "Servicios",
    "Entretenimiento",
    "Salud",
    "Educación",
    "Ropa",
    "Suscripciones",
    "Deuda",
    "Otros",
]

COLOR_CATEGORIA: dict[str, str] = {
    "Alimentación":    "#f472b6",
    "Transporte":      "#60a5fa",
    "Vivienda":        "#a78bfa",
    "Servicios":       "#34d399",
    "Entretenimiento": "#fbbf24",
    "Salud":           "#f87171",
    "Educación":       "#38bdf8",
    "Ropa":            "#fb7185",
    "Suscripciones":   "#c084fc",
    "Deuda":           "#ef4444",
    "Otros":           "#94a3b8",
}

MEDIOS_PAGO: list[str] = ["Efectivo", "Débito", "Crédito", "Transferencia", "Nequi", "Daviplata"]

# ── Cajas ──────────────────────────────────────────────
TIPOS_CAJA: list[str] = [
    "cuenta",           # Cuenta de ahorros/corriente
    "tarjeta_credito",  # TC
    "tarjeta_debito",   # TD prepago (Nequi, Lulo, Falabella débito...)
    "efectivo",
    "otro",
]

TIPO_CAJA_LABEL: dict[str, str] = {
    "cuenta":           "Cuenta bancaria",
    "tarjeta_credito":  "Tarjeta de crédito",
    "tarjeta_debito":   "Tarjeta débito / Billetera",
    "efectivo":         "Efectivo",
    "otro":             "Otro",
}

MONEDAS: list[str] = ["COP", "USD"]

# 4x1000: aplica en transferencias salientes desde cuenta bancaria NO exenta.
# Tarjetas de crédito, efectivo y cajas exentas no lo generan.
TASA_4X1000 = 0.004


def calcular_4x1000(monto: float, caja_origen_tipo: str, caja_origen_exenta: bool) -> float:
    """Devuelve el costo del GMF (4x1000) para un egreso desde la caja origen."""
    if caja_origen_exenta:
        return 0.0
    if caja_origen_tipo in ("efectivo", "tarjeta_credito"):
        return 0.0
    return monto * TASA_4X1000


# ── Utilidad: meses ────────────────────────────────────
MESES_NOMBRE = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
