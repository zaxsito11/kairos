# Página 2 — Análisis Fundamental
import streamlit as st
import json, os
from datetime import datetime

st.markdown("## 🌍 Análisis Fundamental")
st.caption("Macro · Geopolítica · Política · FED/BCE · Energía · Comercio")

# ── Tabs internos ─────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Contexto Macro",
    "🌍 Geopolítica y Eventos",
    "🏛️ Bancos Centrales",
    "🔍 Analizar Evento"
])

# ─────────────── TAB 1: Contexto Macro ───────────────────────────
with tab1:
    col1, col2 = st.columns([3,1])
    with col2:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("Cargando datos macro..."):
        try:
            from macro import obtener_datos_macro, evaluar_regimen_macro
            datos_macro = obtener_datos_macro()
            regimen     = evaluar_regimen_macro(datos_macro)
        except Exception as e:
            st.error(f"Error macro: {e}")
            datos_macro = {}
            regimen = {"regimen":"NEUTRO","descripcion":"Error"}

    # Régimen
    emoji_reg = {"HAWKISH FUERTE":"🔴🔴","HAWKISH LEVE":"🔴",
                 "NEUTRO":"🟡","DOVISH LEVE":"🟢","DOVISH FUERTE":"🟢🟢"}.get(
                 regimen.get("regimen","NEUTRO"),"⚪")
    st.markdown(
        f'<div style="background:#1a1f2e;border-radius:10px;padding:1rem;margin-bottom:1rem">'
        f'<div style="font-size:1.2rem;font-weight:700;color:#ffffff">'
        f'{emoji_reg} Régimen: {regimen.get("regimen","?")}</div>'
        f'<div style="color:#8892a4;margin-top:4px">{regimen.get("descripcion","")}</div>'
        f'</div>', unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown("**💰 Inflación**")
        cpi = datos_macro.get("CORE_CPI",{})
        pce = datos_macro.get("CORE_PCE",{})
        if cpi and cpi.get("variacion"):
            st.metric("Core CPI YoY", f"{cpi['variacion']}%",
                      delta=f"Obj FED: 2%")
        if pce and pce.get("variacion"):
            st.metric("Core PCE YoY", f"{pce['variacion']}%")
    with c2:
        st.markdown("**👥 Empleo**")
        ump = datos_macro.get("DESEMPLEO",{})
        nfp = datos_macro.get("NFP",{})
        if ump and ump.get("valor"):
            st.metric("Desempleo", f"{ump['valor']}%")
        if nfp and nfp.get("variacion"):
            st.metric("NFP (MoM k)", f"{nfp['variacion']}")
    with c3:
        st.markdown("**📊 Tasas**")
        fed  = datos_macro.get("TASA_FED",{})
        r10  = datos_macro.get("RENDIMIENTO_10Y",{})
        r2   = datos_macro.get("RENDIMIENTO_2Y",{})
        if fed and fed.get("valor"):
            st.metric("Tasa FED", f"{fed['valor']}%")
        if r10 and r2 and r10.get("valor") and r2.get("valor"):
            spread = round(float(r10["valor"]) - float(r2["valor"]),2)
            st.metric("Spread 10Y-2Y", f"{spread}%")

    # Sorpresas
    st.markdown("**⚡ Sorpresas vs Consenso**")
    try:
        from sorpresa_macro import analizar_sorpresas_recientes
        sorpresas = analizar_sorpresas_recientes()
        if sorpresas:
            cols_s = st.columns(len(sorpresas))
            for i,s in enumerate(sorpresas):
                with cols_s[i]:
                    signo = "+" if s["diferencia"]>0 else ""
                    st.metric(s["nombre"], f"{s['real']} {s['unidad']}",
                              delta=f"{signo}{s['diferencia']} vs {s['consenso']}")
                    st.caption(f"{s['emoji']} {s['nivel']}")
    except Exception as e:
        st.caption(f"Error sorpresas: {e}")

    # Priced-in
    st.markdown("**🎯 Priced-In CME FedWatch**")
    try:
        from priced_in import obtener_probabilidades_cme
        exp = obtener_probabilidades_cme()
        if exp:
            for e in exp[:2]:
                st.markdown(f"📅 **{e['descripcion']}** ({e['fecha_reunion']}) — {e['dias_para_reunion']} días")
                cols_e = st.columns(len(e["probabilidades"]))
                for i,(k,v) in enumerate(e["probabilidades"].items()):
                    with cols_e[i]:
                        c = "🔴" if "SUBIDA" in k else "🟢" if "RECORTE" in k else "🟡"
                        st.metric(f"{c} {k}", f"{v:.1f}%")
                st.markdown("---")
    except Exception as e:
        st.caption(f"Error priced-in: {e}")


# ─────────────── TAB 2: Geopolítica ──────────────────────────────
with tab2:
    st.markdown("**🔴 Situaciones activas — ventana de oportunidad permanente**")
    try:
        from news_scanner import SITUACIONES_ACTIVAS
        activas = [s for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
        for s in activas:
            with st.expander(f"🔴 {s['nombre']} — Score {s['score_base']}/100"):
                st.markdown(f"**Estado:** {s['nota']}")
                st.markdown(f"**Tipo:** {s.get('tipo','Conflicto')}")
                st.markdown(f"**Ventana:** Activa mientras esté sin resolver")
                # Impacto por activo
                from geopolitica import clasificar_evento_geopolitico
                cl = clasificar_evento_geopolitico(s["nombre"])
                if cl and cl.get("impacto"):
                    st.markdown("**Impacto por activo:**")
                    imp = cl["impacto"]
                    cols_imp = st.columns(min(len(imp),5))
                    for i,(activo,datos) in enumerate(list(imp.items())[:5]):
                        with cols_imp[i]:
                            color = "#00d4aa" if datos["direccion"]=="SUBE" else "#ff4b4b"
                            st.markdown(
                                f'<div style="text-align:center;padding:0.4rem;background:#1a1f2e;'
                                f'border-radius:6px;border-left:2px solid {color}">'
                                f'<div style="color:#8892a4;font-size:0.7rem">{activo}</div>'
                                f'<div style="color:{color};font-weight:700;font-size:0.85rem">'
                                f'{datos["direccion"]}</div></div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Error: {e}")

    st.markdown("---")
    st.markdown("**📊 Análisis fundamental contextual**")
    if st.button("🔍 Analizar contexto completo ahora", type="primary"):
        with st.spinner("Analizando contexto fundamental..."):
            try:
                from analisis_fundamental import analizar_contexto_fundamental_completo
                ctx = analizar_contexto_fundamental_completo()
                st.session_state["fundamental_ctx"] = ctx
                st.success(f"✅ Análisis completado")
            except Exception as e:
                st.error(f"{e}")

    if "fundamental_ctx" in st.session_state:
        ctx   = st.session_state["fundamental_ctx"]
        sesgo = ctx.get("sesgo_global",{})
        if sesgo:
            st.markdown("**Sesgo fundamental por activo:**")
            activos_orden = ["SPX","NDX","Gold","Silver","WTI","BTC","DXY","VIX"]
            cols = st.columns(4)
            for i,activo in enumerate([a for a in activos_orden if a in sesgo]):
                s = sesgo[activo]
                dir_  = s.get("direccion","NEUTRO")
                conf  = s.get("confianza",0)
                color = "#00d4aa" if dir_=="ALCISTA" else "#ff4b4b" if dir_=="BAJISTA" else "#8892a4"
                emoji = "📈" if dir_=="ALCISTA" else "📉" if dir_=="BAJISTA" else "↔️"
                with cols[i%4]:
                    st.markdown(
                        f'<div style="background:#1a1f2e;border-radius:8px;padding:0.7rem;'
                        f'border-left:3px solid {color};margin-bottom:6px">'
                        f'<div style="color:#8892a4;font-size:0.7rem">{activo}</div>'
                        f'<div style="color:{color};font-weight:700">{emoji} {dir_}</div>'
                        f'<div style="color:#8892a4;font-size:0.72rem">{conf}% confianza</div>'
                        f'</div>', unsafe_allow_html=True)


# ─────────────── TAB 3: Bancos Centrales ─────────────────────────
with tab3:
    col_fed, col_bce = st.columns(2)
    with col_fed:
        st.markdown("#### 🇺🇸 Federal Reserve")
        btn_fed = st.button("Analizar último comunicado FED",
                            use_container_width=True, type="primary")
    with col_bce:
        st.markdown("#### 🇪🇺 Banco Central Europeo")
        btn_bce = st.button("Analizar último comunicado BCE",
                            use_container_width=True)

    if btn_fed or btn_bce:
        banco = "FED" if btn_fed else "BCE"
        with st.spinner(f"Conectando con {banco}..."):
            try:
                if btn_fed:
                    from fed_scraper import obtener_comunicado_fed
                    comunicado = obtener_comunicado_fed()
                else:
                    from bce_scraper import obtener_comunicado_bce
                    comunicado = obtener_comunicado_bce()

                from macro import obtener_datos_macro, evaluar_regimen_macro
                dm = obtener_datos_macro()
                rg = evaluar_regimen_macro(dm)
                from analizador import analizar_comunicado
                analisis = analizar_comunicado(comunicado, {"datos":dm,"regimen":rg})
                st.success(f"✅ {comunicado.get('titulo','')}")
                st.markdown(analisis)
            except Exception as e:
                st.error(f"Error: {e}")

    # Info próximas reuniones
    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        st.info("📅 **Próximo FOMC:** 7 mayo 2026 — 14:00 ET\nConsenso: Sin cambio (78%)")
    with c2:
        st.info("📅 **Próximo BCE:** 5 junio 2026 — 14:15 ET\nConsenso: Subida 25bps (60%)")


# ─────────────── TAB 4: Analizar Evento ──────────────────────────
with tab4:
    st.markdown("**Analiza cualquier evento y su impacto en los mercados**")
    evento_input = st.text_area(
        "Describe el evento:",
        placeholder="Ej: Trump anuncia aranceles del 25% a importaciones chinas de semiconductores",
        height=100
    )
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        analizar_btn = st.button("🔍 Analizar impacto", type="primary",
                                  use_container_width=True)
    with col_btn2:
        # Geopolítico
        geo_btn = st.button("🌍 Análisis geopolítico", use_container_width=True)

    if analizar_btn and evento_input:
        with st.spinner("Analizando evento con IA..."):
            try:
                from analisis_fundamental import (analizar_evento_fundamental,
                                                   detectar_categoria_evento)
                cat, sub = detectar_categoria_evento(evento_input)
                resultado = analizar_evento_fundamental(evento_input, cat, sub)
                ai        = resultado.get("analisis_ia",{})

                st.markdown(f"**Categoría:** {cat} / {sub}")
                st.markdown(f"**Narrativa:** {ai.get('narrativa_evento','')}")
                st.markdown(f"**Ventana:** {ai.get('ventana_oportunidad','')}")

                sesgo = ai.get("sesgo_por_activo",{})
                if sesgo:
                    st.markdown("**Impacto por activo:**")
                    cols = st.columns(4)
                    for i,(activo,s) in enumerate(sesgo.items()):
                        dir_  = s.get("direccion","NEUTRO")
                        conf  = s.get("confianza",0)
                        razon = s.get("razon","")
                        color = "#00d4aa" if dir_=="ALCISTA" else "#ff4b4b" if dir_=="BAJISTA" else "#8892a4"
                        emoji = "📈" if dir_=="ALCISTA" else "📉" if dir_=="BAJISTA" else "↔️"
                        with cols[i%4]:
                            st.markdown(
                                f'<div style="background:#1a1f2e;border-radius:8px;'
                                f'padding:0.8rem;border-left:3px solid {color};margin-bottom:6px">'
                                f'<div style="color:#8892a4;font-size:0.72rem">{activo}</div>'
                                f'<div style="color:{color};font-weight:700">{emoji} {dir_}</div>'
                                f'<div style="color:#8892a4;font-size:0.7rem">{conf}%</div>'
                                f'<div style="color:#c9d1d9;font-size:0.7rem;margin-top:3px">'
                                f'{razon[:50]}</div></div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")

    if geo_btn and evento_input:
        try:
            from geopolitica import clasificar_evento_geopolitico
            cl = clasificar_evento_geopolitico(evento_input)
            if cl:
                st.markdown(f"**Tipo geopolítico:** {cl['tipo']}")
                st.markdown(f"**Descripción:** {cl['descripcion']}")
        except Exception as e:
            st.error(f"Error: {e}")
