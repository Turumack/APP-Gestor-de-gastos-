import streamlit as st
from datetime import date
from components.sidebar import render_sidebar, get_periodo, MESES_NOMBRE
from src.database import Database
from src.finance import FinanceManager

render_sidebar()
mes, anio, fecha_inicio, fecha_fin = get_periodo()

st.markdown(f"## 💰 Ingresos — {MESES_NOMBRE[mes]} {anio}")
st.caption("Registra salarios, freelance o bonos. Usa la calculadora laboral para cálculos exactos con horas extra.")

# ══════════════════════════════════════════
# REGISTRAR INGRESO — Simple vs Calculadora
# ══════════════════════════════════════════
tab_simple, tab_calc = st.tabs(["⚡ Rápido", "🧮 Calculadora laboral (Colombia)"])

# ─────── Tab Rápido ───────
with tab_simple:
    with st.form("form_ingreso_simple", clear_on_submit=True):
        c1, c2 = st.columns(2)
        descripcion = c1.text_input("Descripción", placeholder="Ej: Salario, Freelance, Bono")
        fecha_ingreso = c2.date_input("Fecha", value=date.today())

        c3, c4, c5 = st.columns(3)
        salario_base = c3.number_input("Salario Base (Bruto)", min_value=0.0, step=10000.0)
        aux_transporte = c4.number_input("Aux. Transporte", min_value=0.0, step=1000.0)
        otros = c5.number_input("Otros / Bonos", min_value=0.0, step=10000.0)

        c6, c7 = st.columns(2)
        meta_ahorro = c6.slider("Meta de Ahorro (%)", 0, 100, 10)
        ingreso_real = c7.number_input("Monto real depositado (COP)", min_value=0.0, step=1000.0)

        if st.form_submit_button("💾 Guardar Ingreso", use_container_width=True):
            if descripcion:
                Database.insert("ingresos", [{
                    "fecha": fecha_ingreso.strftime("%Y-%m-%d"),
                    "descripcion": descripcion,
                    "salario_base": salario_base,
                    "aux_transporte": aux_transporte,
                    "otros": otros,
                    "pct_ahorro_objetivo": meta_ahorro,
                    "ingreso_real_cuenta": ingreso_real,
                }])
                st.success("Ingreso registrado.")
                st.rerun()
            else:
                st.error("La descripción es obligatoria.")

# ─────── Tab Calculadora laboral ───────
with tab_calc:
    st.markdown("#### Datos del contrato")
    cc1, cc2, cc3 = st.columns(3)
    calc_desc = cc1.text_input("Descripción", value="Salario", key="calc_desc")
    calc_fecha = cc2.date_input("Fecha", value=date.today(), key="calc_fecha")
    calc_horas = cc3.number_input("Jornada mensual (h)", min_value=1, max_value=300, value=240, step=1,
                                   help="Por ley en Colombia = 240 h/mes (8h × 30 días)")

    cs1, cs2 = st.columns(2)
    calc_salario = cs1.number_input("Salario base mensual (COP)", min_value=0.0, step=10000.0, key="calc_sal")
    calc_aux = cs2.number_input("Auxilio de transporte", min_value=0.0, step=1000.0, key="calc_aux")

    st.markdown("#### Horas extra y recargos del mes")
    st.caption("Solo diligencia los conceptos que apliquen. Los porcentajes son los que exige el Código Sustantivo del Trabajo.")

    h1, h2 = st.columns(2)
    with h1:
        st.markdown("**No dominicales / festivas**")
        h_ext_d = st.number_input("Extra diurna (+25%)", min_value=0.0, step=0.5, key="h_ext_d")
        h_ext_n = st.number_input("Extra nocturna (+75%)", min_value=0.0, step=0.5, key="h_ext_n")
        h_rec_n = st.number_input("Recargo nocturno ordinario (+35%)", min_value=0.0, step=0.5, key="h_rec_n")
    with h2:
        st.markdown("**Dominicales / festivas**")
        h_dom_d = st.number_input("Dominical diurna ordinaria (+75%)", min_value=0.0, step=0.5, key="h_dom_d")
        h_dom_n = st.number_input("Dominical nocturna ordinaria (+110%)", min_value=0.0, step=0.5, key="h_dom_n")
        h_ext_dom_d = st.number_input("Extra dominical diurna (+100%)", min_value=0.0, step=0.5, key="h_ext_dom_d")
        h_ext_dom_n = st.number_input("Extra dominical nocturna (+150%)", min_value=0.0, step=0.5, key="h_ext_dom_n")

    h_otros_bonos = st.number_input("Otros bonos / comisiones (COP)", min_value=0.0, step=10000.0, key="h_otros")

    # ── Calcular ──
    horas_dict = {
        "extra_diurna": h_ext_d,
        "extra_nocturna": h_ext_n,
        "recargo_nocturno": h_rec_n,
        "dominical_diurna": h_dom_d,
        "dominical_nocturna": h_dom_n,
        "extra_dominical_diurna": h_ext_dom_d,
        "extra_dominical_nocturna": h_ext_dom_n,
    }
    detalle = FinanceManager.calcular_extras(calc_salario, horas_dict)

    total_extras = detalle["total"]
    otros_total = total_extras + h_otros_bonos
    neto = FinanceManager.calculate_net_income(calc_salario, calc_aux, otros_total)

    # ── Vista previa ──
    st.markdown("---")
    st.markdown("#### Vista previa del cálculo")

    if calc_salario > 0:
        vh = detalle["valor_hora_ordinaria"]
        st.caption(f"Valor hora ordinaria: **${vh:,.0f}**")

        # Mostrar detalle de extras si hay
        if total_extras > 0:
            with st.expander("🔎 Desglose de extras", expanded=True):
                labels = {
                    "extra_diurna": "Extra diurna (+25%)",
                    "extra_nocturna": "Extra nocturna (+75%)",
                    "recargo_nocturno": "Recargo nocturno (+35%)",
                    "dominical_diurna": "Dominical diurna (+75%)",
                    "dominical_nocturna": "Dominical nocturna (+110%)",
                    "extra_dominical_diurna": "Extra dominical diurna (+100%)",
                    "extra_dominical_nocturna": "Extra dominical nocturna (+150%)",
                }
                for k, lbl in labels.items():
                    h = horas_dict[k]
                    v = detalle[k]
                    if h > 0:
                        st.markdown(f"• **{lbl}** — {h} h → `${v:,.0f}`")
                st.markdown(f"**Total extras: ${total_extras:,.0f}**")

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Salario base", f"${calc_salario:,.0f}")
        mc2.metric("+ Extras", f"${total_extras:,.0f}")
        mc3.metric("+ Aux. transporte", f"${calc_aux:,.0f}")
        mc4.metric("💵 Neto estimado", f"${neto:,.0f}")

    # ── Guardar ──
    cm1, cm2 = st.columns(2)
    meta_calc = cm1.slider("Meta de Ahorro (%)", 0, 100, 10, key="meta_calc")
    real_calc = cm2.number_input("Monto real depositado (si ya lo recibiste)",
                                 min_value=0.0, step=1000.0, key="real_calc")

    if st.button("💾 Guardar ingreso calculado", use_container_width=True, type="primary"):
        if calc_salario > 0:
            Database.insert("ingresos", [{
                "fecha": calc_fecha.strftime("%Y-%m-%d"),
                "descripcion": calc_desc or "Salario",
                "salario_base": calc_salario,
                "aux_transporte": calc_aux,
                "otros": otros_total,   # extras + bonos van a 'otros'
                "pct_ahorro_objetivo": meta_calc,
                "ingreso_real_cuenta": real_calc,
            }])
            st.success(f"✅ Ingreso registrado · Neto estimado ${neto:,.0f}")
            st.rerun()
        else:
            st.error("Debes ingresar al menos el salario base.")

# ══════════════════════════════════════════
# INGRESOS DEL PERÍODO
# ══════════════════════════════════════════
st.markdown("---")
st.markdown(f"### 📋 Ingresos registrados · {MESES_NOMBRE[mes]} {anio}")

df = Database.query(
    "SELECT * FROM ingresos WHERE fecha >= %s AND fecha < %s ORDER BY fecha DESC",
    (fecha_inicio, fecha_fin),
)

if not df.empty:
    for _, row in df.iterrows():
        rid = row["id"]
        teorico = FinanceManager.calculate_net_income(
            row["salario_base"], row["aux_transporte"], row["otros"]
        )
        real = float(row.get("ingreso_real_cuenta", 0))

        with st.container(border=True):
            ci, cv, ca = st.columns([3, 4, 1])
            with ci:
                st.markdown(f"**{row['descripcion']}**")
                st.caption(f"📅 {row['fecha']}")
            with cv:
                if real > 0:
                    dif = real - teorico
                    pct = (dif / teorico * 100) if teorico > 0 else 0
                    st.markdown(f"Teórico **${teorico:,.0f}** → Real **${real:,.0f}**")
                    st.caption(f"Diferencia: {pct:+.1f}%")
                else:
                    st.markdown(f"Teórico **${teorico:,.0f}** · Real: *sin registrar*")
            with ca:
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("✏️", key=f"ei_{rid}"):
                        st.session_state[f"editing_ing_{rid}"] = True
                with b2:
                    if st.button("🗑", key=f"di_{rid}"):
                        Database.delete("ingresos", rid)
                        st.rerun()

            if st.session_state.get(f"editing_ing_{rid}"):
                with st.form(f"fedit_ing_{rid}"):
                    e1, e2 = st.columns(2)
                    ed = e1.text_input("Descripción", value=row["descripcion"], key=f"eid_{rid}")
                    ef = e2.date_input("Fecha", value=date.fromisoformat(str(row["fecha"])), key=f"eif_{rid}")
                    e3, e4, e5 = st.columns(3)
                    es = e3.number_input("Salario Base", value=float(row["salario_base"]), step=10000.0, key=f"eis_{rid}")
                    ea = e4.number_input("Aux. Transporte", value=float(row["aux_transporte"]), step=1000.0, key=f"eia_{rid}")
                    eo = e5.number_input("Otros (extras + bonos)", value=float(row["otros"]), step=10000.0, key=f"eio_{rid}")
                    e6, e7 = st.columns(2)
                    em = e6.slider("Meta %", 0, 100, int(row["pct_ahorro_objetivo"]), key=f"eim_{rid}")
                    er = e7.number_input("Real en cuenta", value=float(row.get("ingreso_real_cuenta", 0)), step=1000.0, key=f"eir_{rid}")

                    s1, s2 = st.columns(2)
                    if s1.form_submit_button("💾 Guardar"):
                        Database.update("ingresos", rid, {
                            "descripcion": ed, "fecha": ef.strftime("%Y-%m-%d"),
                            "salario_base": es, "aux_transporte": ea, "otros": eo,
                            "pct_ahorro_objetivo": em, "ingreso_real_cuenta": er,
                        })
                        st.session_state[f"editing_ing_{rid}"] = False
                        st.rerun()
                    if s2.form_submit_button("Cancelar"):
                        st.session_state[f"editing_ing_{rid}"] = False
                        st.rerun()

    # ── Resumen ──
    st.markdown("---")
    total_t = sum(
        FinanceManager.calculate_net_income(r["salario_base"], r["aux_transporte"], r["otros"])
        for _, r in df.iterrows()
    )
    total_r = float(df["ingreso_real_cuenta"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Teórico", f"${total_t:,.0f}")
    c2.metric("Total Real", f"${total_r:,.0f}" if total_r > 0 else "Sin registrar")
    if total_r > 0 and total_t > 0:
        dif = total_r - total_t
        pct = (dif / total_t) * 100
        c3.metric("Error", f"{abs(pct):.2f}%", delta=f"${dif:+,.0f}",
                   delta_color="normal" if dif >= 0 else "inverse")
else:
    st.info("Sin ingresos este período. Registra el primero arriba.")
