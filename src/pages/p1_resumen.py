# Página 1 — Resumen Ejecutivo
import streamlit as st
import os, json, glob
from datetime import datetime

st.markdown("## 📊 Resumen Ejecutivo")
st.caption("Estado del mercado y señales del día")

# ── Fila top: métricas clave ──────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

# Brief de hoy
brief_file = "data/ultimo_brief.json"
hoy = datetime.now().strftime("%Y-%m-%d")
with col1:
    if os.path.exists(brief_file):
        try:
            with open(brief_file, encoding="utf-8", errors="ignore") as f:
                bd = json.load(f)
            estado = "✅ HOY" if bd.get("fecha")==hoy else f"📅 {bd.get('fecha','?')}"
            st.metric("Morning Brief", estado)
        except Exception:
            st.metric("Morning Brief", "⚠️ Error")
    else:
        st.metric("Morning Brief", "Sin datos")

# Señales accionables
with col2:
    sf = "data/señales_cache.json"
    if os.path.exists(sf):
        try:
            with open(sf) as f:
                sd = json.load(f)
            n = sd.get("n_accionables",0)
            st.metric("Señales accionables", f"{n} activos")
        except Exception:
            st.metric("Señales accionables", "—")
    else:
        st.metric("Señales accionables", "Calcular →")

# Precisión
with col3:
    fb_file = "data/feedback_estadisticas.json"
    if os.path.exists(fb_file):
        try:
            with open(fb_file) as f:
                fb = json.load(f)
            prec = fb.get("precision_dir_24h",0)
            n    = fb.get("total_evaluaciones",0)
            st.metric("Precisión 24h", f"{prec}%", delta=f"{n} evaluaciones")
        except Exception:
            st.metric("Precisión 24h","—")
    else:
        st.metric("Precisión 24h", "Acumulando...")

# Situaciones activas
with col4:
    try:
        from news_scanner import SITUACIONES_ACTIVAS
        n = len([s for s in SITUACIONES_ACTIVAS if not s["resuelto"]])
        st.metric("Situaciones activas", f"{n} eventos", delta="en monitoreo")
    except Exception:
        st.metric("Situaciones activas","—")

st.divider()

# ── Morning Brief ─────────────────────────────────────────────────
col_b, col_btn = st.columns([3,1])
with col_b:
    st.markdown("### 📋 Morning Brief del día")
with col_btn:
    if st.button("🔄 Generar nuevo", use_container_width=True):
        with st.spinner("Generando..."):
            try:
                from morning_brief import generar_y_enviar_brief
                generar_y_enviar_brief(forzar=True)
                st.success("✅ Enviado al canal")
                st.rerun()
            except Exception as e:
                st.error(f"{e}")

if os.path.exists(brief_file):
    try:
        with open(brief_file, encoding="utf-8", errors="ignore") as f:
            bd = json.load(f)
        brief_txt = bd.get("brief","")
        if brief_txt:
            with st.expander("Ver brief completo", expanded=True):
                st.markdown(brief_txt)
    except Exception as e:
        st.warning(f"Error leyendo brief: {e}")
else:
    st.info("Sin brief disponible. Genera el primero con el botón.")

st.divider()

# ── Precios en tiempo real ─────────────────────────────────────────
st.markdown("### 📈 Mercados en tiempo real")
with st.spinner("Cargando precios..."):
    try:
        from precios import obtener_precios
        precios = obtener_precios()
    except Exception as e:
        precios = {}
        st.warning(f"Error precios: {e}")

if precios:
    def precio_card(nombre, datos):
        if datos:
            clase = "color:#00d4aa" if datos["variacion_pct"] >= 0 else "color:#ff4b4b"
            signo = "+" if datos["variacion_pct"] >= 0 else ""
            return (
                f'<div style="background:#1a1f2e;border-radius:8px;padding:0.7rem;'
                f'text-align:center;border:1px solid #2a2f3e;height:80px">'
                f'<div style="color:#8892a4;font-size:0.7rem;font-weight:700">{nombre}</div>'
                f'<div style="color:#ffffff;font-size:0.95rem;font-weight:700">{datos["precio"]}</div>'
                f'<div style="{clase};font-size:0.78rem">{signo}{datos["variacion_pct"]}% {datos["direccion"]}</div>'
                f'</div>'
            )
        return f'<div style="background:#1a1f2e;border-radius:8px;padding:0.7rem;text-align:center"><div style="color:#8892a4;font-size:0.7rem">{nombre}</div><div style="color:#555">N/A</div></div>'

    filas = [
        ["SPX","NDX","VIX","DXY","UST10Y"],
        ["Gold","Silver","WTI","BTC","EURUSD"],
    ]
    for fila in filas:
        cols = st.columns(len(fila))
        for i, nombre in enumerate(fila):
            with cols[i]:
                st.markdown(precio_card(nombre, precios.get(nombre)), unsafe_allow_html=True)

st.divider()

# ── Situaciones activas ────────────────────────────────────────────
st.markdown("### 🌍 Situaciones activas en el mundo")
try:
    from news_scanner import SITUACIONES_ACTIVAS
    activas = [s for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
    if activas:
        cols = st.columns(len(activas))
        for i, s in enumerate(activas):
            with cols[i]:
                intensidad = "🔴" if s["score_base"] >= 85 else "🟠" if s["score_base"] >= 70 else "🟡"
                st.markdown(
                    f'<div style="background:#ff4b4b12;border:1px solid #ff4b4b33;'
                    f'border-radius:8px;padding:0.8rem">'
                    f'<div style="color:#ff4b4b;font-weight:700;font-size:0.85rem">'
                    f'{intensidad} {s["nombre"]}</div>'
                    f'<div style="color:#8892a4;font-size:0.75rem;margin-top:4px">'
                    f'Score: {s["score_base"]}/100</div>'
                    f'<div style="color:#8892a4;font-size:0.72rem">{s["nota"][:60]}...</div>'
                    f'</div>', unsafe_allow_html=True)
    else:
        st.success("✅ Sin situaciones activas")
except Exception as e:
    st.warning(f"Error situaciones: {e}")

st.divider()

# ── Próximos eventos ───────────────────────────────────────────────
st.markdown("### 📅 Próximos eventos críticos")
try:
    from calendario_eco import obtener_eventos_proximos
    eventos = obtener_eventos_proximos(dias=14)
    criticos = [e for e in eventos if e["impacto"] in ("CRÍTICO","ALTO")][:5]
    if criticos:
        for ev in criticos:
            dias  = ev["dias_restantes"]
            emoji = "🚨" if ev["impacto"]=="CRÍTICO" else "⚠️"
            color = "#ff4b4b" if ev["impacto"]=="CRÍTICO" else "#ffa500"
            st.markdown(
                f'<div style="background:#1a1f2e;border-radius:8px;padding:0.7rem;'
                f'margin-bottom:6px;border-left:3px solid {color}">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div style="color:#ffffff;font-size:0.88rem;font-weight:500">'
                f'{emoji} {ev["evento"]}</div>'
                f'<div style="color:{color};font-size:0.8rem;font-weight:700">'
                f'En {dias} días</div></div>'
                f'<div style="color:#8892a4;font-size:0.75rem;margin-top:2px">'
                f'{ev["hora_local_et"]} ET | Consenso: {ev.get("consenso","N/A")}</div>'
                f'</div>', unsafe_allow_html=True)
except Exception as e:
    st.warning(f"Error calendario: {e}")
