from src.database import Database
import pandas as pd


# ══════════════════════════════════════════
#  RECARGOS LABORALES COLOMBIA (Código Sustantivo del Trabajo)
# ══════════════════════════════════════════
# Base: hora ordinaria = salario_mensual / 240 (jornada de 240h/mes, 8h día, 6 días)
RECARGOS = {
    "extra_diurna": 1.25,        # Extra diurna (no dominical)    +25%
    "extra_nocturna": 1.75,      # Extra nocturna (no dominical)  +75%
    "recargo_nocturno": 1.35,    # Nocturno ordinario (21:00-06:00) +35%
    "dominical_diurna": 1.75,    # Dominical/festivo diurna ordinaria +75%
    "dominical_nocturna": 2.10,  # Dominical/festivo nocturna ordinaria +75% +35%
    "extra_dominical_diurna": 2.00,   # Extra en dominical diurna +100%
    "extra_dominical_nocturna": 2.50, # Extra en dominical nocturna +150%
}


class FinanceManager:
    @staticmethod
    def valor_hora_ordinaria(salario_base: float) -> float:
        """Valor de una hora ordinaria = salario / 240."""
        try:
            return float(salario_base) / 240.0
        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0

    @classmethod
    def calcular_extras(cls, salario_base: float, horas: dict) -> dict:
        """Calcula el valor total de las horas extra y recargos.

        horas: dict con claves opcionales coincidiendo con RECARGOS y valores = horas.
        Retorna dict con valor por concepto y total.
        """
        vh = cls.valor_hora_ordinaria(salario_base)
        detalle = {}
        total = 0.0
        for concepto, factor in RECARGOS.items():
            h = float(horas.get(concepto, 0) or 0)
            valor = vh * factor * h
            detalle[concepto] = valor
            total += valor
        detalle["total"] = total
        detalle["valor_hora_ordinaria"] = vh
        return detalle

    @staticmethod
    def calculate_net_income(salario_base, aux_transporte, otros):
        """Calcula el ingreso neto aproximado.
        - 8% descuentos (Salud 4% + Pensión 4%) sobre salario_base
        - 0.4% GMF (4x1000) sobre el total final"""
        try:
            base_con_descuentos = float(salario_base) * 0.92
            total_pre_impuesto = base_con_descuentos + float(aux_transporte) + float(otros)
            return total_pre_impuesto * 0.996
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def get_period_summary(cls, fecha_inicio, fecha_fin):
        """Calcula el resumen de un período: ingresos netos vs gastos."""
        # Ingresos del período
        df_ingresos = Database.query(
            "SELECT * FROM ingresos WHERE fecha >= %s AND fecha < %s",
            (fecha_inicio, fecha_fin)
        )

        total_ingreso_neto = 0
        total_ingreso_real = 0
        meta_pct = 10

        if not df_ingresos.empty:
            for _, row in df_ingresos.iterrows():
                neto = cls.calculate_net_income(row['salario_base'], row['aux_transporte'], row['otros'])
                total_ingreso_neto += neto
                total_ingreso_real += float(row.get('ingreso_real_cuenta', 0))
                meta_pct = float(row.get('pct_ahorro_objetivo', 10))

        # Gastos del período
        df_gastos = Database.query(
            "SELECT * FROM gastos_detalle WHERE fecha_pago >= %s AND fecha_pago < %s",
            (fecha_inicio, fecha_fin)
        )
        total_gastos = float(df_gastos['valor_cop'].sum()) if not df_gastos.empty else 0

        # Usar ingreso real si está disponible, sino el teórico
        ingreso_base = total_ingreso_real if total_ingreso_real > 0 else total_ingreso_neto

        return {
            "ingreso_neto_teorico": total_ingreso_neto,
            "ingreso_real": total_ingreso_real,
            "total_gastos": total_gastos,
            "sobrante": ingreso_base - total_gastos,
            "meta_ahorro": ingreso_base * (meta_pct / 100),
            "meta_pct": meta_pct
        }

    @classmethod
    def get_global_bag(cls, fecha_fin):
        """Bolsa Global: suma todos los ingresos netos y resta todos los gastos hasta la fecha."""
        df_ingresos = Database.query(
            "SELECT * FROM ingresos WHERE fecha < %s", (fecha_fin,)
        )
        total_ingresos = 0
        if not df_ingresos.empty:
            for _, row in df_ingresos.iterrows():
                real = float(row.get('ingreso_real_cuenta', 0))
                if real > 0:
                    total_ingresos += real
                else:
                    total_ingresos += cls.calculate_net_income(row['salario_base'], row['aux_transporte'], row['otros'])

        df_gastos = Database.query(
            "SELECT * FROM gastos_detalle WHERE fecha_pago < %s", (fecha_fin,)
        )
        total_gastos = float(df_gastos['valor_cop'].sum()) if not df_gastos.empty else 0

        return total_ingresos - total_gastos

    @staticmethod
    def calculate_cdt_profit(monto, tasa_ea, plazo_dias):
        try:
            ganancia = float(monto) * (float(tasa_ea) / 100) * (int(plazo_dias) / 365)
            return ganancia
        except (ValueError, TypeError):
            return 0.0
