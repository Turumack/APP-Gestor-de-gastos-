"""Tests unitarios para cuentas_pro.finance.

Ejecutar con::

    python -m pytest tests/ -q
"""
import pytest

from cuentas_pro.finance import (
    PCT_DEDUCCION_BASE,
    PCT_GMF,
    RECARGOS,
    TASA_4X1000,
    calcular_4x1000,
    calcular_extras,
    calculate_net_income,
    horas_mes_desde_semana,
    valor_hora_ordinaria,
)


# ── valor_hora_ordinaria ─────────────────────────────
def test_valor_hora_ordinaria_basico():
    assert valor_hora_ordinaria(2_400_000, 240) == 10_000


def test_valor_hora_ordinaria_horas_cero():
    assert valor_hora_ordinaria(2_400_000, 0) == 0.0


def test_valor_hora_ordinaria_horas_negativas():
    assert valor_hora_ordinaria(2_400_000, -5) == 0.0


# ── horas_mes_desde_semana ──────────────────────────
def test_horas_mes_desde_semana_44():
    # 44 horas/semana × 52/12 ≈ 190.666...
    assert horas_mes_desde_semana(44) == pytest.approx(44 * 52 / 12)


# ── calculate_net_income ─────────────────────────────
def test_neto_sin_extras():
    base = 1_000_000
    aux = 0
    otros = 0
    esperado = base * (1 - PCT_DEDUCCION_BASE) * (1 - PCT_GMF)
    assert calculate_net_income(base, aux, otros) == pytest.approx(esperado)


def test_neto_con_aux_y_otros():
    base = 1_300_000
    aux = 200_000
    otros = 100_000
    bruto = base * (1 - PCT_DEDUCCION_BASE) + aux + otros
    esperado = bruto * (1 - PCT_GMF)
    assert calculate_net_income(base, aux, otros) == pytest.approx(esperado)


def test_neto_cero():
    assert calculate_net_income(0, 0, 0) == 0.0


# ── calcular_extras ──────────────────────────────────
def test_calcular_extras_total_cero_si_no_hay_horas():
    detalle = calcular_extras(2_400_000, {}, 240)
    assert detalle["total"] == 0.0
    assert detalle["valor_hora_ordinaria"] == 10_000


def test_calcular_extras_diurnas():
    horas = {"extra_diurna": 10}
    detalle = calcular_extras(2_400_000, horas, 240)
    # 10 h × 10_000/h × 1.25 = 125_000
    assert detalle["extra_diurna"] == pytest.approx(125_000)
    assert detalle["total"] == pytest.approx(125_000)


def test_calcular_extras_combinadas():
    horas = {
        "extra_diurna": 5,
        "extra_nocturna": 3,
        "dominical_diurna": 8,
    }
    detalle = calcular_extras(2_400_000, horas, 240)
    vh = 10_000
    esperado = (
        5 * vh * RECARGOS["extra_diurna"]
        + 3 * vh * RECARGOS["extra_nocturna"]
        + 8 * vh * RECARGOS["dominical_diurna"]
    )
    assert detalle["total"] == pytest.approx(esperado)


def test_calcular_extras_ignora_keys_desconocidas():
    horas = {"extra_diurna": 4, "concepto_inventado": 999}
    detalle = calcular_extras(2_400_000, horas, 240)
    assert detalle["total"] == pytest.approx(4 * 10_000 * 1.25)


def test_calcular_extras_horas_none():
    horas = {"extra_diurna": None}
    detalle = calcular_extras(2_400_000, horas, 240)
    assert detalle["total"] == 0.0


# ── calcular_4x1000 ──────────────────────────────────
def test_4x1000_cuenta_no_exenta():
    assert calcular_4x1000(1_000_000, "cuenta", False) == pytest.approx(4_000)


def test_4x1000_cuenta_exenta():
    assert calcular_4x1000(1_000_000, "cuenta", True) == 0.0


def test_4x1000_efectivo_no_aplica():
    assert calcular_4x1000(1_000_000, "efectivo", False) == 0.0


def test_4x1000_tarjeta_credito_no_aplica():
    assert calcular_4x1000(1_000_000, "tarjeta_credito", False) == 0.0


def test_4x1000_tarjeta_debito_aplica():
    assert calcular_4x1000(500_000, "tarjeta_debito", False) == pytest.approx(2_000)


def test_4x1000_tipo_invalido_lanza():
    with pytest.raises(ValueError):
        calcular_4x1000(1_000, "no_existe", False)


def test_tasa_constante_correcta():
    # Sentinela: si alguien cambia accidentalmente la constante.
    assert TASA_4X1000 == 0.004
