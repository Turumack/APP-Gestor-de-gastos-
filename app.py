import streamlit as st
import os
from src.database import Database

st.set_page_config(
    page_title="Cuentas Pro",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None, "About": "Cuentas Pro — Finanzas personales locales"},
)

# Cargar estilos ANTES de inicializar BD (evita flash visual sin estilos)
if os.path.exists("assets/style.css"):
    with open("assets/style.css", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Inicializar BD local (SQLite) — silenciosa si todo va bien
try:
    Database.init_db()
except Exception as e:
    st.error(f"No se pudo inicializar la base de datos local: {e}")
    st.stop()


def show_home():
    # Hero section
    st.markdown(
        '''
        <div class="hero">
            <div class="hero-badge">✨ Finanzas personales</div>
            <h1 class="hero-title">Toma el control<br/><span class="gradient-text">de tu dinero</span></h1>
            <p class="hero-sub">Gestiona ingresos, gastos recurrentes, inversiones y documentos. Todo en un solo lugar, 100% local y privado.</p>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # Stats rápidas
    from datetime import datetime
    mes_actual = datetime.now().strftime("%B %Y").capitalize()
    st.markdown(
        f'<div class="hero-stats"><span>📍 {mes_actual}</span><span>🔒 100% Privado</span><span>💾 Datos locales</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="home-cards">', unsafe_allow_html=True)

    cards = [
        ("💰", "Ingresos", "Registra salarios, bonos y freelance. Compara lo teórico vs lo real.", "#a78bfa"),
        ("📅", "Calendario", "Vista mensual con categorías, recurrencia y recordatorios.", "#f472b6"),
        ("📊", "Dashboard", "KPIs, distribución de gastos y estado de pagos en tiempo real.", "#34d399"),
        ("🏦", "Inversiones", "CDTs con proyección de rentabilidad.", "#fbbf24"),
        ("📂", "Baúl", "Almacena recibos y documentos financieros importantes.", "#60a5fa"),
    ]

    cols = st.columns(len(cards))
    for col, (icon, title, desc, color) in zip(cols, cards):
        with col:
            st.markdown(
                f'''
                <div class="feat-card" style="--accent:{color}">
                    <div class="feat-icon">{icon}</div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>
                ''',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

    # Footer tip
    st.markdown(
        '<div class="home-tip">💡 Usa el menú lateral para navegar entre secciones</div>',
        unsafe_allow_html=True,
    )


try:
    pg = st.navigation([
        st.Page(show_home, title="Inicio", icon="🏠"),
        st.Page("pages/00_⚙️_Configuracion.py", title="Ingresos", icon="💰"),
        st.Page("pages/01_📊_Resumen.py", title="Resumen", icon="📊"),
        st.Page("pages/02_💸_Gastos.py", title="Calendario", icon="📅"),
        st.Page("pages/03_🏦_Inversiones.py", title="Inversiones", icon="🏦"),
        st.Page("pages/04_📂_Baul.py", title="Baúl", icon="📂"),
    ])
    pg.run()
except AttributeError:
    st.error("Actualiza Streamlit a >=1.35.0")