# Página 4 — Señales y Targets
import streamlit as st

st.markdown("## 🎯 Señales y Targets de Precio")
st.caption("Técnico vs Fundamental contrastados — solo señales con convergencia real")

# ── Botón de análisis completo ────────────────────────────────────
col_btn, col_info = st.columns([2,1])
with col_btn:
    run_btn = st.button("🔬 Ejecutar análisis completo (Técnico + Fundamental)",
                         type="primary", use_container_width=True)
with col_info:
    st.caption("⏱️ ~60 segundos — técnico + IA fundamental + contraste")

if run_btn:
    with st.spinner("Ejecutando análisis técnico..."):
        try:
            from motor_contraste import analisis_completo_mercado
            resultado = analisis_completo_mercado()
            st.session_state["contraste_resultado"] = resultado
            st.success(f"✅ {resultado['n_accionables']} señales accionables detectadas")
        except Exception as e:
            st.error(f"Error: {e}")

if "contraste_resultado" in st.session_state:
    resultado    = st.session_state["contraste_resultado"]
    resultados   = resultado.get("resultados",{})
    accionables  = resultado.get("accionables",[])
    no_accion    = [k for k,v in resultados.items() if not v.get("accionable")]

    # ── Señales accionables ───────────────────────────────────────
    if accionables:
        st.markdown(f"### ✅ {len(accionables)} señales accionables")
        for activo in accionables:
            r     = resultados[activo]
            dir_  = r.get("direccion","NEUTRO")
            conf  = r.get("confianza",0)
            emj   = r.get("emoji","")
            conv  = r.get("convergencia",False)
            conf_ = r.get("conflicto",False)
            t24h  = r.get("target_24h",0)
            t7d   = r.get("target_7d",0)
            precio= r.get("precio",0)
            color = "#00d4aa" if dir_=="ALCISTA" else "#ff4b4b"

            # Header del activo
            tipo_badge = ""
            if conv:
                tipo_badge = '<span style="background:#00d4aa22;color:#00d4aa;font-size:0.7rem;padding:2px 6px;border-radius:4px;margin-left:8px">CONVERGENCIA</span>'
            elif conf_:
                dom = "FUNDAMENTAL domina" if "FUNDAMENTAL" in r.get("veredicto","") else "TÉCNICO domina"
                tipo_badge = f'<span style="background:#ffa50022;color:#ffa500;font-size:0.7rem;padding:2px 6px;border-radius:4px;margin-left:8px">CONFLICTO → {dom}</span>'

            with st.expander(f"{emj} {activo} {dir_} — {conf}% confianza", expanded=True):
                c1,c2,c3,c4 = st.columns(4)
                with c1:
                    st.markdown(
                        f'<div style="text-align:center">'
                        f'<div style="color:#8892a4;font-size:0.72rem">Veredicto</div>'
                        f'<div style="color:{color};font-size:1.2rem;font-weight:700">{dir_}</div>'
                        f'<div style="color:#ffffff;font-size:0.85rem">{conf}% confianza</div>'
                        f'{tipo_badge}</div>', unsafe_allow_html=True)
                with c2:
                    dir_tec  = r.get("dir_tecnica","?")
                    conf_tec = r.get("conf_tecnica",0)
                    c_tec    = "#00d4aa" if dir_tec=="ALCISTA" else "#ff4b4b" if dir_tec=="BAJISTA" else "#8892a4"
                    st.markdown(
                        f'<div style="text-align:center">'
                        f'<div style="color:#8892a4;font-size:0.72rem">Técnico</div>'
                        f'<div style="color:{c_tec};font-weight:700">{dir_tec}</div>'
                        f'<div style="color:#8892a4;font-size:0.75rem">{conf_tec}% | RSI:{r.get("rsi",50)}</div>'
                        f'<div style="color:#8892a4;font-size:0.7rem">Vol:{r.get("vol_relativo",1):.1f}x</div>'
                        f'</div>', unsafe_allow_html=True)
                with c3:
                    dir_fund  = r.get("dir_fundamental","?")
                    conf_fund = r.get("conf_fundamental",0)
                    c_fund    = "#00d4aa" if dir_fund=="ALCISTA" else "#ff4b4b" if dir_fund=="BAJISTA" else "#8892a4"
                    st.markdown(
                        f'<div style="text-align:center">'
                        f'<div style="color:#8892a4;font-size:0.72rem">Fundamental</div>'
                        f'<div style="color:{c_fund};font-weight:700">{dir_fund}</div>'
                        f'<div style="color:#8892a4;font-size:0.75rem">{conf_fund}% confianza</div>'
                        f'</div>', unsafe_allow_html=True)
                with c4:
                    st.markdown(
                        f'<div style="text-align:center">'
                        f'<div style="color:#8892a4;font-size:0.72rem">Targets</div>'
                        f'<div style="color:#ffffff;font-size:0.85rem">Precio: {precio}</div>'
                        f'<div style="color:#00d4aa;font-size:0.82rem">T24h: {t24h}</div>'
                        f'<div style="color:#8892a4;font-size:0.75rem">T7d: {t7d}</div>'
                        f'</div>', unsafe_allow_html=True)

                # Razones fundamentales
                razones = r.get("razones_fundamental",[])
                if razones:
                    st.markdown("**Razones fundamentales:**")
                    for rz in razones[:2]:
                        if rz:
                            st.markdown(f"• {rz}")

    # ── Activos neutros ───────────────────────────────────────────
    if no_accion:
        with st.expander(f"⚫ {len(no_accion)} activos sin señal convergente"):
            cols = st.columns(len(no_accion))
            for i,activo in enumerate(no_accion):
                r = resultados.get(activo,{})
                with cols[i]:
                    st.markdown(
                        f'<div style="background:#0d1117;border-radius:6px;'
                        f'padding:0.6rem;text-align:center;border:1px solid #2a2f3e">'
                        f'<div style="color:#8892a4;font-size:0.75rem">{activo}</div>'
                        f'<div style="color:#555;font-size:0.7rem">↔️ Sin convergencia</div>'
                        f'<div style="color:#444;font-size:0.65rem">'
                        f'Tec:{r.get("dir_tecnica","?")} Fund:{r.get("dir_fundamental","?")}</div>'
                        f'</div>', unsafe_allow_html=True)
else:
    st.info("Presiona el botón para ejecutar el análisis completo.")
    st.markdown("""
    **Cómo funciona el contraste:**
    
    | Técnico | Fundamental | Resultado |
    |---------|------------|-----------|
    | ALCISTA | ALCISTA | 🟢🟢 CONVERGENCIA FUERTE |
    | BAJISTA | BAJISTA | 🔴🔴 CONVERGENCIA FUERTE |
    | ALCISTA | BAJISTA | ⚡ CONFLICTO — Fundamental domina |
    | BAJISTA | ALCISTA | ⚡ CONFLICTO — Técnico domina |
    | NEUTRO  | cualquiera| ↔️ Sin señal |
    
    Solo se reportan activos **accionables** (confianza > 60%).
    El silencio es inteligente — neutro significa "no hay señal clara".
    """)
