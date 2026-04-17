# Página 3 — Análisis Técnico
import streamlit as st

st.markdown("## 📈 Análisis Técnico")
st.caption("RSI · MACD · EMA 20/50/200 · Bollinger · Volumen · OBV · ATR")

col_run, col_info = st.columns([2,1])
with col_run:
    run_btn = st.button("📊 Ejecutar análisis técnico completo",
                         type="primary", use_container_width=True)
with col_info:
    st.caption("⏱️ ~30 segundos — descarga datos reales de mercado")

if run_btn:
    with st.spinner("Calculando indicadores técnicos para 9 activos..."):
        try:
            from analisis_tecnico import analizar_todos
            resultados = analizar_todos()
            st.session_state["tecnico_resultados"] = resultados
            st.success(f"✅ Análisis completado para {len(resultados)} activos")
        except Exception as e:
            st.error(f"Error: {e}")

if "tecnico_resultados" in st.session_state:
    resultados = st.session_state["tecnico_resultados"]

    # ── Tabla resumen ─────────────────────────────────────────────
    st.markdown("### Resumen técnico")
    activos_ord = ["SPX","NDX","Gold","Silver","WTI","BTC","DXY","VIX","UST10Y"]
    cols = st.columns(5)
    for i, activo in enumerate([a for a in activos_ord if a in resultados]):
        a     = resultados[activo]
        señal = a.get("señal","NEUTRAL")
        conf  = a.get("confianza",0)
        rsi   = a.get("rsi",50)
        vol   = a.get("vol_relativo",1.0)
        obv   = a.get("obv_tendencia","─")[:6]
        color = "#00d4aa" if señal=="ALCISTA" else "#ff4b4b" if señal=="BAJISTA" else "#8892a4"
        emoji = "📈" if señal=="ALCISTA" else "📉" if señal=="BAJISTA" else "↔️"

        # Advertencias
        warn = ""
        if vol < 0.7: warn = "⚠️ Vol bajo"
        elif obv == "DISTRIB" and señal=="ALCISTA": warn = "⚠️ OBV dist"

        with cols[i%5]:
            st.markdown(
                f'<div style="background:#1a1f2e;border-radius:8px;padding:0.8rem;'
                f'border-left:3px solid {color};margin-bottom:8px;min-height:110px">'
                f'<div style="color:#8892a4;font-size:0.72rem;font-weight:700">{activo}</div>'
                f'<div style="color:{color};font-weight:700;font-size:0.95rem">{emoji} {señal}</div>'
                f'<div style="color:#ffffff;font-size:0.82rem">{conf}% confianza</div>'
                f'<div style="color:#8892a4;font-size:0.7rem">RSI: {rsi}</div>'
                f'<div style="color:#8892a4;font-size:0.7rem">Vol: {vol:.1f}x | OBV: {obv}</div>'
                f'<div style="color:#ffa500;font-size:0.68rem">{warn}</div>'
                f'</div>', unsafe_allow_html=True)

    st.divider()

    # ── Detalle por activo ────────────────────────────────────────
    st.markdown("### Detalle por activo")
    activo_sel = st.selectbox("Seleccionar activo:",
                               [a for a in activos_ord if a in resultados])

    if activo_sel:
        a = resultados[activo_sel]
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            rsi = a.get("rsi",50)
            color_rsi = "#ff4b4b" if rsi>70 else "#00d4aa" if rsi<30 else "#ffffff"
            st.markdown(f'<div style="text-align:center"><div style="color:#8892a4;font-size:0.75rem">RSI (14)</div>'
                        f'<div style="font-size:1.5rem;font-weight:700;color:{color_rsi}">{rsi}</div>'
                        f'<div style="color:#8892a4;font-size:0.7rem">{"Sobrecomprado" if rsi>70 else "Sobrevendido" if rsi<30 else "Normal"}</div></div>',
                        unsafe_allow_html=True)
        with c2:
            macd = a.get("macd_cruce","─")
            color_macd = "#00d4aa" if "ALCISTA" in macd else "#ff4b4b" if "BAJISTA" in macd else "#ffffff"
            st.markdown(f'<div style="text-align:center"><div style="color:#8892a4;font-size:0.75rem">MACD</div>'
                        f'<div style="font-size:1rem;font-weight:700;color:{color_macd}">{macd[:12]}</div></div>',
                        unsafe_allow_html=True)
        with c3:
            vol  = a.get("vol_relativo",1.0)
            obv  = a.get("obv_tendencia","─")
            color_v = "#00d4aa" if vol>1.5 else "#ff4b4b" if vol<0.7 else "#ffffff"
            st.markdown(f'<div style="text-align:center"><div style="color:#8892a4;font-size:0.75rem">Volumen</div>'
                        f'<div style="font-size:1.3rem;font-weight:700;color:{color_v}">{vol:.1f}x</div>'
                        f'<div style="color:#8892a4;font-size:0.7rem">OBV: {obv}</div></div>',
                        unsafe_allow_html=True)
        with c4:
            atr = a.get("atr_pct",0)
            st.markdown(f'<div style="text-align:center"><div style="color:#8892a4;font-size:0.75rem">ATR (%)</div>'
                        f'<div style="font-size:1.3rem;font-weight:700;color:#ffffff">{atr:.2f}%</div>'
                        f'<div style="color:#8892a4;font-size:0.7rem">Volatilidad real</div></div>',
                        unsafe_allow_html=True)

        st.markdown("---")
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**EMAs y niveles:**")
            st.markdown(f"- EMA 20: `{a.get('ema20',0)}`")
            st.markdown(f"- EMA 50: `{a.get('ema50',0)}`")
            st.markdown(f"- EMA 200: `{a.get('ema200',0)}`")
            st.markdown(f"- Soporte dinámico: `{a.get('soporte',0)}`")
            st.markdown(f"- Resistencia dinámica: `{a.get('resistencia',0)}`")
        with c2:
            st.markdown("**Targets técnicos (ATR-based):**")
            st.metric("Target 24h", a.get("target_24h",0))
            st.metric("Target 7d",  a.get("target_7d",0))
            st.metric("Target 30d", a.get("target_30d",0))

        # Señales individuales
        señales = a.get("señales",[])
        if señales:
            st.markdown("**Señales detectadas:**")
            for s in señales:
                ind,dir_,desc = s
                color = "#00d4aa" if dir_=="ALCISTA" else "#ff4b4b" if dir_=="BAJISTA" else "#8892a4"
                emoji = "🟢" if dir_=="ALCISTA" else "🔴" if dir_=="BAJISTA" else "⚪"
                st.markdown(
                    f'<div style="padding:4px 8px;border-left:2px solid {color};'
                    f'margin-bottom:3px;font-size:0.82rem;color:#c9d1d9">'
                    f'{emoji} <b>{ind}</b> — {desc}</div>',
                    unsafe_allow_html=True)
else:
    st.info("Presiona el botón para ejecutar el análisis técnico de los 9 activos.")
    st.markdown("""
    **Indicadores calculados:**
    - RSI (14) — detecta sobrecompra/sobreventa
    - MACD (12,26,9) — momentum y cruces de señal
    - EMA 20/50/200 — tendencia en 3 horizontes
    - Bollinger Bands (20,2σ) — volatilidad y rangos
    - Volumen + OBV — confirma o invalida señales de precio
    - ATR (14) — volatilidad real para calcular targets
    """)
