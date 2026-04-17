# dashboard_main.py — KAIROS
# Punto de entrada del dashboard multipágina.
# Ejecutar: streamlit run src/dashboard_main.py

import streamlit as st

st.set_page_config(
    page_title="KAIROS — Inteligencia de Mercados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none; }
.titulo-kairos {
    font-size: 2rem; font-weight: 800;
    color: #00d4aa; letter-spacing: 4px;
    margin: 0; padding: 0;
}
.subtitulo { color: #8892a4; font-size: 0.85rem; margin-top: 2px; }
section[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #1a1f2e;
}
.nav-item {
    padding: 0.6rem 1rem;
    border-radius: 8px;
    cursor: pointer;
    color: #8892a4;
    font-size: 0.88rem;
    margin-bottom: 4px;
    display: block;
}
.nav-item:hover { background: #1a1f2e; color: #ffffff; }
.nav-item.active { background: #00d4aa22; color: #00d4aa; font-weight: 600; }
.nav-section {
    color: #444c5e;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 0.8rem 1rem 0.3rem;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar navegación ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="titulo-kairos">KAIROS</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo">Intelligence between events and markets</p>',
                unsafe_allow_html=True)
    st.markdown("---")

    paginas = {
        "📊 Resumen":           "resumen",
        "🌍 Análisis Fundamental": "fundamental",
        "📈 Análisis Técnico":  "tecnico",
        "🎯 Señales y Targets": "senales",
        "📋 Historial":         "historial",
    }

    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "resumen"

    st.markdown('<div class="nav-section">Navegación</div>', unsafe_allow_html=True)
    for label, key in paginas.items():
        is_active = st.session_state["pagina"] == key
        css = "nav-item active" if is_active else "nav-item"
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state["pagina"] = key
            st.rerun()

    st.markdown("---")
    st.markdown('<div class="nav-section">Sistema</div>', unsafe_allow_html=True)
    st.caption(f"📅 {__import__('datetime').datetime.now().strftime('%d %b %Y %H:%M')}")

    import os, json
    fb_file = "data/feedback_estadisticas.json"
    if os.path.exists(fb_file):
        try:
            with open(fb_file) as f:
                fb = json.load(f)
            prec = fb.get("precision_dir_24h", 0)
            n    = fb.get("total_evaluaciones", 0)
            if n > 0:
                color = "#00d4aa" if prec>=60 else "#ffa500" if prec>=45 else "#ff4b4b"
                st.markdown(
                    f'<div style="color:{color};font-size:1.2rem;font-weight:700">{prec}%</div>'
                    f'<div style="color:#8892a4;font-size:0.72rem">precisión ({n} eval.)</div>',
                    unsafe_allow_html=True)
        except Exception:
            pass

    st.markdown('<a href="https://t.me/+Jk7_RXqqhAxlOGZh" target="_blank" '
                'style="color:#00d4aa;font-size:0.8rem">📱 Canal Telegram</a>',
                unsafe_allow_html=True)

# ── Routing de páginas ────────────────────────────────────────────
pagina_actual = st.session_state.get("pagina", "resumen")

import sys, pathlib
_base = pathlib.Path(__file__).parent

if pagina_actual == "resumen":
    sys.path.insert(0, str(_base))
    exec(open(_base/"pages/p1_resumen.py", encoding="utf-8", errors="ignore").read())
elif pagina_actual == "fundamental":
    exec(open(_base/"pages/p2_fundamental.py", encoding="utf-8", errors="ignore").read())
elif pagina_actual == "tecnico":
    exec(open(_base/"pages/p3_tecnico.py", encoding="utf-8", errors="ignore").read())
elif pagina_actual == "senales":
    exec(open(_base/"pages/p4_senales.py", encoding="utf-8", errors="ignore").read())
elif pagina_actual == "historial":
    exec(open(_base/"pages/p5_historial.py", encoding="utf-8", errors="ignore").read())
