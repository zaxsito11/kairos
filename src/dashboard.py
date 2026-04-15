import streamlit as st
import sys
import os
import glob
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from fed_scraper    import obtener_comunicado_fed
from price_targets  import calcular_targets_fusionados
from bce_scraper    import obtener_comunicado_bce
from analizador     import analizar_comunicado
from precios        import obtener_precios, detectar_correlaciones_activas
from macro          import obtener_datos_macro, evaluar_regimen_macro
from historico      import encontrar_similares
from sorpresa_macro import analizar_sorpresas_recientes
from geopolitica    import clasificar_evento_geopolitico
from calendario_eco import obtener_eventos_proximos, resumen_semana
from priced_in      import obtener_probabilidades_cme, calcular_sorpresa

st.set_page_config(
    page_title="KAIROS — Inteligencia de Mercados",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.titulo-kairos { font-size:2.5rem;font-weight:800;color:#00d4aa;letter-spacing:4px; }
.subtitulo     { color:#8892a4;font-size:1rem; }
.precio-card   { background:#1a1f2e;border-radius:8px;padding:0.8rem 1rem;
                 text-align:center;border:1px solid #2a2f3e; }
.precio-nombre { color:#8892a4;font-size:0.75rem;font-weight:600; }
.precio-valor  { color:#ffffff;font-size:1.05rem;font-weight:700; }
.sube { color:#00d4aa;font-size:0.82rem; }
.baja { color:#ff4b4b;font-size:0.82rem; }
.brief-card    { background:#1a1f2e;border-radius:10px;padding:1.2rem;
                 border-left:4px solid #00d4aa;margin-bottom:1rem; }
.brief-fecha   { color:#8892a4;font-size:0.78rem; }
.brief-resumen { color:#c9d1d9;font-size:0.9rem;line-height:1.6; }
.corr-card     { background:#1a1f2e;border-radius:8px;padding:0.8rem 1rem;
                 border-left:3px solid #ffa500;margin-bottom:0.5rem; }
.corr-activo   { color:#ffa500;font-weight:700;font-size:0.85rem; }
.corr-efecto   { color:#8892a4;font-size:0.8rem;margin-top:2px; }
.cal-card      { background:#1a1f2e;border-radius:10px;padding:1rem 1.2rem;
                 margin-bottom:0.8rem;border-left:4px solid #2a2f3e; }
.cal-card.critico { border-left-color:#ff4b4b; }
.cal-card.alto    { border-left-color:#ffa500; }
.cal-titulo  { color:#ffffff;font-weight:700;font-size:1rem;margin:0; }
.cal-fecha   { color:#8892a4;font-size:0.8rem;margin:0.2rem 0; }
.cal-consenso{ color:#00d4aa;font-size:0.8rem; }
.cal-activos { color:#8892a4;font-size:0.75rem; }
.badge-critico { background:#ff4b4b22;color:#ff4b4b;border:1px solid #ff4b4b44;
    border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:700; }
.badge-alto { background:#ffa50022;color:#ffa500;border:1px solid #ffa50044;
    border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:700; }
.geo-tipo { background:linear-gradient(135deg,#1a1f2e,#0d1117);
    border-left:4px solid #00d4aa;border-radius:8px;padding:1rem 1.2rem;margin-bottom:1rem; }
.geo-tipo h3 { color:#ffffff;margin:0 0 0.3rem 0;font-size:1.2rem; }
.geo-tipo p  { color:#8892a4;margin:0;font-size:0.9rem; }
.activo-card { background:#1a1f2e;border-radius:8px;padding:0.7rem 0.5rem;
    text-align:center;border:1px solid #2a2f3e;height:100%; }
.activo-card.sube-card  { border-color:#00d4aa; }
.activo-card.baja-card  { border-color:#ff4b4b; }
.activo-card.mixto-card { border-color:#ffa500; }
.activo-nombre { color:#8892a4;font-size:0.7rem;font-weight:700; }
.activo-flecha { font-size:1.6rem;line-height:1.8rem; }
.activo-dir-sube  { color:#00d4aa;font-weight:700;font-size:0.85rem; }
.activo-dir-baja  { color:#ff4b4b;font-weight:700;font-size:0.85rem; }
.activo-dir-mixto { color:#ffa500;font-weight:700;font-size:0.85rem; }
.activo-mag { color:#8892a4;font-size:0.7rem; }
.precedente-item { background:#1a1f2e;border-radius:6px;padding:0.6rem 1rem;
    margin-bottom:0.4rem;border-left:3px solid #2a2f3e;color:#c9d1d9;font-size:0.88rem; }
.sit-activa { background:#ff4b4b15;border:1px solid #ff4b4b33;border-radius:8px;
    padding:0.7rem 1rem;margin-bottom:0.5rem; }
.sit-nombre { color:#ff4b4b;font-weight:700;font-size:0.85rem; }
.sit-nota   { color:#8892a4;font-size:0.78rem;margin-top:2px; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ─────────────────────────────────────────────────────────
st.markdown('<p class="titulo-kairos">KAIROS</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo">The intelligence between events and markets</p>',
            unsafe_allow_html=True)
st.divider()

# ── MORNING BRIEF ──────────────────────────────────────────────────
st.subheader("📊 Morning Brief")
brief_file = "data/ultimo_brief.json"
if os.path.exists(brief_file):
    try:
        with open(brief_file, "r", encoding="utf-8") as f:
            brief_data = json.load(f)
        fecha_brief = brief_data.get("fecha", "")
        brief_texto = brief_data.get("brief", "")

        hoy = datetime.now().strftime("%Y-%m-%d")
        badge_color = "#00d4aa" if fecha_brief == hoy else "#ffa500"
        badge_texto = "HOY" if fecha_brief == hoy else fecha_brief

        col_b1, col_b2 = st.columns([3, 1])
        with col_b1:
            # Extraer resumen ejecutivo del brief
            lineas = brief_texto.split('\n')
            resumen_lineas = []
            en_resumen = False
            for linea in lineas:
                if "RESUMEN EJECUTIVO" in linea:
                    en_resumen = True
                    continue
                if en_resumen and linea.strip().startswith("**") and "RESUMEN" not in linea:
                    break
                if en_resumen and linea.strip():
                    resumen_lineas.append(linea.strip())

            resumen_txt = " ".join(resumen_lineas[:3]) or brief_texto[:300]

            st.markdown(
                f'<div class="brief-card">'
                f'<div class="brief-fecha">📅 Brief del día — '
                f'<span style="color:{badge_color};font-weight:700">{badge_texto}</span></div>'
                f'<div class="brief-resumen" style="margin-top:0.5rem">{resumen_txt}...</div>'
                f'</div>', unsafe_allow_html=True
            )

        with col_b2:
            if st.button("📖 Ver brief completo", use_container_width=True):
                st.markdown("---")
                st.markdown(brief_texto)

        col_gen1, col_gen2 = st.columns(2)
        with col_gen1:
            if st.button("🔄 Generar nuevo brief ahora", use_container_width=True):
                with st.spinner("Generando Morning Brief con IA..."):
                    try:
                        from morning_brief import generar_y_enviar_brief
                        generar_y_enviar_brief(forzar=True)
                        st.success("✅ Brief generado y enviado al canal Telegram")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    except Exception as e:
        st.info("Sin brief disponible aún. Genera el primero con el botón.")
        if st.button("📊 Generar Morning Brief", use_container_width=True):
            with st.spinner("Generando..."):
                try:
                    from morning_brief import generar_y_enviar_brief
                    generar_y_enviar_brief(forzar=True)
                    st.success("✅ Enviado al canal Telegram")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.info("Sin brief disponible. El sistema lo genera automáticamente a las 8:00 AM.")
    if st.button("📊 Generar ahora"):
        with st.spinner("Generando Morning Brief con IA..."):
            try:
                from morning_brief import generar_y_enviar_brief
                generar_y_enviar_brief(forzar=True)
                st.success("✅ Generado y enviado al canal Telegram")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()

# ── CLOSING BRIEF + WEEKLY BRIEF ──────────────────────────────────
col_cl, col_wk = st.columns(2)

with col_cl:
    st.subheader("📉 Closing Brief")
    archivos_cl = sorted(glob.glob("outputs/closing_brief_*.txt"), reverse=True)
    if archivos_cl:
        nombre_cl = os.path.basename(archivos_cl[0]).replace("closing_brief_","").replace(".txt","")
        with open(archivos_cl[0], "r", encoding="utf-8") as f:
            texto_cl = f.read()
        # Extraer puntuación
        score_line = [l for l in texto_cl.split("\n") if "PUNTUACIÓN" in l or "PUNTUACION" in l]
        score_txt  = score_line[0] if score_line else ""
        st.caption(f"📅 {nombre_cl} {score_txt}")
        with st.expander("Ver Closing Brief completo"):
            st.markdown(texto_cl)
    else:
        st.caption("Se genera automáticamente a las 4:00 PM ET")
        if st.button("📉 Generar Closing Brief ahora", use_container_width=True):
            with st.spinner("Generando..."):
                try:
                    from closing_brief import generar_y_enviar_closing
                    generar_y_enviar_closing(forzar=True)
                    st.success("✅ Enviado al canal")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

with col_wk:
    st.subheader("📊 Weekly Brief")
    archivos_wk = sorted(glob.glob("outputs/weekly_brief_*.txt"), reverse=True)
    if archivos_wk:
        nombre_wk = os.path.basename(archivos_wk[0]).replace("weekly_brief_","").replace(".txt","")
        with open(archivos_wk[0], "r", encoding="utf-8") as f:
            texto_wk = f.read()
        st.caption(f"📅 Semana del {nombre_wk}")
        with st.expander("Ver Weekly Brief completo"):
            st.markdown(texto_wk)
    else:
        st.caption("Se genera automáticamente los viernes a las 6:00 PM ET")
        if st.button("📊 Generar Weekly Brief ahora", use_container_width=True):
            with st.spinner("Generando..."):
                try:
                    from weekly_brief import generar_y_enviar_weekly
                    generar_y_enviar_weekly(forzar=True)
                    st.success("✅ Enviado al canal")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

st.divider()

# ── PRECIOS EN TIEMPO REAL ─────────────────────────────────────────
st.subheader("📈 Mercados en tiempo real")
with st.spinner("Cargando precios..."):
    precios = obtener_precios()

if precios:
    # Fila 1: índices y volatilidad
    fila1 = ["SPX", "NDX", "VIX", "DXY"]
    # Fila 2: commodities y crypto
    fila2 = ["Gold", "Silver", "WTI", "BTC"]
    # Fila 3: divisas y bonos (si existen)
    fila3 = ["EURUSD", "UST10Y"]

    def render_fila(activos):
        cols = st.columns(len(activos))
        for i, nombre in enumerate(activos):
            datos = precios.get(nombre)
            with cols[i]:
                if datos:
                    clase = "sube" if datos["variacion_pct"] >= 0 else "baja"
                    signo = "+" if datos["variacion_pct"] >= 0 else ""
                    st.markdown(
                        f'<div class="precio-card">'
                        f'<div class="precio-nombre">{nombre}</div>'
                        f'<div class="precio-valor">{datos["precio"]}</div>'
                        f'<div class="{clase}">{signo}{datos["variacion_pct"]}% {datos["direccion"]}</div>'
                        f'</div>', unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="precio-card">'
                        f'<div class="precio-nombre">{nombre}</div>'
                        f'<div class="precio-valor">N/A</div></div>',
                        unsafe_allow_html=True
                    )

    st.caption("Índices y volatilidad")
    render_fila(fila1)
    st.caption("Commodities y Crypto")
    render_fila(fila2)
    st.caption("Divisas y bonos")
    render_fila(fila3)

    # ── Correlaciones activas
    correlaciones = detectar_correlaciones_activas(precios)
    if correlaciones:
        st.markdown("#### 🔗 Correlaciones activas hoy")
        st.caption("Movimientos que suelen arrastrar a otros activos")
        cols_corr = st.columns(min(len(correlaciones), 3))
        for i, corr in enumerate(correlaciones):
            with cols_corr[i % 3]:
                efectos = "<br>".join(
                    f"→ {e[:60]}" for e in corr["correlaciones"][:2]
                )
                st.markdown(
                    f'<div class="corr-card">'
                    f'<div class="corr-activo">{corr["activo"]} {corr["movimiento"]}</div>'
                    f'<div class="corr-efecto">{efectos}</div>'
                    f'</div>', unsafe_allow_html=True
                )

st.divider()

# ── TARGETS DE PRECIO ──────────────────────────────────────────────
st.subheader("🎯 Targets de Precio")
st.caption("Técnico (RSI/MACD/EMA/ATR) + macro + geopolítica — actualizado cada hora")

col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    if st.button("📊 Calcular Targets", use_container_width=True):
        with st.spinner("Calculando análisis técnico + macro..."):
            try:
                from news_scanner import SITUACIONES_ACTIVAS
                sits = [{"nombre":s["nombre"],"tipo":s["tipo"]}
                        for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
                tgts = calcular_targets_fusionados(
                    regimen_macro=regimen.get("regimen","NEUTRO"),
                    tono_fed="HAWKISH LEVE",
                    situaciones_activas=sits
                )
                st.session_state["targets"] = tgts
            except Exception as e:
                st.error(f"Error: {e}")

if "targets" in st.session_state:
    tgts = st.session_state["targets"]
    orden = ["SPX","NDX","Gold","Silver","WTI","BTC","DXY","VIX"]
    cols_targets = st.columns(4)
    for idx, nombre_t in enumerate([a for a in orden if a in tgts]):
        t = tgts[nombre_t]
        dir_  = t.get("direccion","MIXTO")
        prob  = t.get("probabilidad",50)
        rsi   = t.get("rsi",50)
        t24h  = t.get("target_24h",0)
        t7d   = t.get("target_7d",0)
        sop   = t.get("soporte_real", t.get("soporte_1",0))
        res   = t.get("resist_real",  t.get("resistencia_1",0))
        color = "#00d4aa" if dir_=="SUBE" else "#ff4b4b" if dir_=="BAJA" else "#ffa500"
        emoji = "📈" if dir_=="SUBE" else "📉" if dir_=="BAJA" else "↔️"
        with cols_targets[idx % 4]:
            st.markdown(
                f'<div style="background:#1a1f2e;border-radius:8px;padding:0.8rem;'
                f'border-left:3px solid {color};margin-bottom:8px">'
                f'<div style="color:#8892a4;font-size:0.7rem;font-weight:700">{nombre_t}</div>'
                f'<div style="color:{color};font-weight:700">{emoji} {dir_} ({prob}%)</div>'
                f'<div style="color:#c9d1d9;font-size:0.75rem">RSI:{rsi}</div>'
                f'<div style="color:#00d4aa;font-size:0.75rem">24h:{t24h}</div>'
                f'<div style="color:#8892a4;font-size:0.72rem">7d:{t7d}</div>'
                f'<div style="color:#8892a4;font-size:0.7rem">Sop:{sop}|Res:{res}</div>'
                f'</div>', unsafe_allow_html=True
            )

with col_t2:
    st.caption("Ponderacion:")
    st.caption("40% Tecnico RSI/MACD/EMA")
    st.caption("30% Macro FED/BCE")
    st.caption("20% Geopolitica")
    st.caption("10% Historicos")
    st.caption("No es recomendacion de inversion")

st.divider()

# ── SITUACIONES ACTIVAS ────────────────────────────────────────────
st.subheader("🔴 Situaciones Activas en el Mundo")
st.caption("Eventos sin resolver que mantienen ventana activa indefinidamente")
try:
    from news_scanner import SITUACIONES_ACTIVAS
    activas = [s for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
    if activas:
        cols_sit = st.columns(len(activas))
        for i, s in enumerate(activas):
            with cols_sit[i]:
                st.markdown(
                    f'<div class="sit-activa">'
                    f'<div class="sit-nombre">🔴 {s["nombre"]}</div>'
                    f'<div class="sit-nota">Score: {s["score_base"]}/100</div>'
                    f'<div class="sit-nota">{s["nota"]}</div>'
                    f'</div>', unsafe_allow_html=True
                )
    else:
        st.success("✅ Sin situaciones activas en este momento")
except Exception as e:
    st.caption(f"Error cargando situaciones: {e}")

st.divider()

# ── CALENDARIO ECONÓMICO ───────────────────────────────────────────
st.subheader("📅 Próximos Eventos Macro")
st.caption("Ordenados por impacto — eventos que pueden mover mercados")

with st.spinner("Cargando calendario..."):
    eventos_cal = obtener_eventos_proximos(dias=30)

if not eventos_cal:
    st.info("Sin eventos macro importantes en los próximos 30 días.")
else:
    criticos = [e for e in eventos_cal if e["impacto"] == "CRÍTICO"]
    altos    = [e for e in eventos_cal if e["impacto"] == "ALTO"]
    col_cal1, col_cal2 = st.columns([1, 1])

    with col_cal1:
        for ev in criticos + altos:
            horas   = ev["horas_restantes"]
            tiempo  = f"{int(horas)}h" if horas < 24 else f"{ev['dias_restantes']} días"
            css     = "critico" if ev["impacto"] == "CRÍTICO" else "alto"
            badge   = (f'<span class="badge-critico">🚨 CRÍTICO</span>'
                       if css == "critico" else f'<span class="badge-alto">⚠️ ALTO</span>')
            cons_html = (f'<div class="cal-consenso">Consenso: {ev["consenso"]}</div>'
                         if ev.get("consenso") else "")
            activos_txt = ", ".join(ev["activos"][:4])
            prob = ev.get("prob_sorpresa")
            prob_html = ""
            if prob:
                prob_html = (
                    f'<div style="margin-top:6px">'
                    f'<span style="color:#ff4b4b;font-size:0.72rem">🔴 Hawkish {prob["prob_sorpresa_hawkish"]}%</span>&nbsp;'
                    f'<span style="color:#00d4aa;font-size:0.72rem">🟢 Dovish {prob["prob_sorpresa_dovish"]}%</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div class="cal-card {css}">'
                f'{badge}&nbsp;&nbsp;'
                f'<span style="color:#8892a4;font-size:0.75rem">en {tiempo}</span>'
                f'<p class="cal-titulo">{ev["evento"]}</p>'
                f'<p class="cal-fecha">📅 {ev["hora_local_et"]}</p>'
                f'{cons_html}'
                f'<div class="cal-activos">📊 {activos_txt}</div>'
                f'{prob_html}</div>',
                unsafe_allow_html=True
            )

    with col_cal2:
        st.markdown("**Resumen próximos 30 días:**")
        for ev in eventos_cal[:8]:
            emoji = {"CRÍTICO":"🚨","ALTO":"⚠️","MEDIO":"📡"}.get(ev["impacto"],"📡")
            st.markdown(
                f"{emoji} **{ev['evento']}** — "
                f"<span style='color:#8892a4'>{ev['dias_restantes']} días</span>",
                unsafe_allow_html=True
            )

st.divider()

# ── CONTEXTO MACRO ─────────────────────────────────────────────────
st.subheader("🏦 Contexto Macro Actual")
with st.spinner("Cargando datos macro..."):
    datos_macro = obtener_datos_macro()
    regimen     = evaluar_regimen_macro(datos_macro)

emoji_reg = {"HAWKISH":"🔴","NEUTRO":"🟡","DOVISH":"🟢"}.get(regimen["regimen"],"⚪")
st.markdown(f"**Régimen macro:** {emoji_reg} **{regimen['regimen']}** — {regimen['descripcion']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Inflación**")
    if datos_macro.get("CORE_PCE") and datos_macro["CORE_PCE"].get("variacion"):
        st.metric("Core PCE (YoY)", f"{datos_macro['CORE_PCE']['variacion']}%", delta="Objetivo FED: 2%")
    if datos_macro.get("CORE_CPI") and datos_macro["CORE_CPI"].get("variacion"):
        st.metric("Core CPI (YoY)", f"{datos_macro['CORE_CPI']['variacion']}%")
with col2:
    st.markdown("**Empleo**")
    if datos_macro.get("DESEMPLEO") and datos_macro["DESEMPLEO"].get("valor"):
        st.metric("Desempleo", f"{datos_macro['DESEMPLEO']['valor']}%")
    if datos_macro.get("NFP") and datos_macro["NFP"].get("variacion"):
        st.metric("NFP (MoM%)", f"{datos_macro['NFP']['variacion']}%")
with col3:
    st.markdown("**Tasas y Curva**")
    if datos_macro.get("TASA_FED") and datos_macro["TASA_FED"].get("valor"):
        st.metric("Tasa FED", f"{datos_macro['TASA_FED']['valor']}%")
    if datos_macro.get("RENDIMIENTO_10Y") and datos_macro.get("RENDIMIENTO_2Y"):
        r10 = float(datos_macro["RENDIMIENTO_10Y"].get("valor", 0) or 0)
        r2  = float(datos_macro["RENDIMIENTO_2Y"].get("valor", 0) or 0)
        st.metric("Spread 10Y-2Y", f"{round(r10-r2, 2)}%")

st.markdown("**Sorpresas vs Consenso:**")
with st.spinner("Calculando sorpresas..."):
    sorpresas = analizar_sorpresas_recientes()
if sorpresas:
    cols_s = st.columns(len(sorpresas))
    for i, s in enumerate(sorpresas):
        with cols_s[i]:
            signo = "+" if s["diferencia"] > 0 else ""
            st.metric(s["nombre"], f"{s['real']} {s['unidad']}",
                      delta=f"{signo}{s['diferencia']} vs {s['consenso']}")
            st.caption(f"{s['emoji']} {s['nivel']}")

st.divider()

# ── ANÁLISIS GEOPOLÍTICO ───────────────────────────────────────────
st.subheader("🌍 Análisis Geopolítico")
st.caption("Detecta impacto y ventana activa de cualquier evento")

titular_geo = st.text_input(
    "Titular:",
    placeholder="Ej: US imposes new 25% tariffs on Chinese imports..."
)

if titular_geo:
    clasificacion = clasificar_evento_geopolitico(titular_geo)
    if clasificacion:
        config_tipo = {
            "CONFLICTO_ARMADO":       {"emoji":"🔴","color":"#ff4b4b","label":"Conflicto Armado"},
            "SANCION_ECONOMICA":      {"emoji":"🟠","color":"#ff8c00","label":"Sanción Económica"},
            "TENSION_COMERCIAL":      {"emoji":"🟡","color":"#ffd700","label":"Tensión Comercial"},
            "CRISIS_ENERGETICA":      {"emoji":"⚡","color":"#ffa500","label":"Crisis Energética"},
            "INESTABILIDAD_POLITICA": {"emoji":"🟣","color":"#9b59b6","label":"Inestabilidad Política"},
            "ACUERDO_PAZ_COMERCIAL":  {"emoji":"🟢","color":"#00d4aa","label":"Acuerdo / Paz"},
        }
        tipo = clasificacion["tipo"]
        cfg  = config_tipo.get(tipo, {"emoji":"⚪","color":"#8892a4","label":tipo})
        impacto  = clasificacion["impacto"]
        ejemplos = clasificacion.get("ejemplos", clasificacion.get("precedentes", []))
        palabras = clasificacion.get("palabras", [])

        st.markdown(
            f'<div class="geo-tipo" style="border-left-color:{cfg["color"]}">'
            f'<h3>{cfg["emoji"]} {cfg["label"]}</h3>'
            f'<p>{clasificacion["descripcion"]}</p></div>',
            unsafe_allow_html=True
        )
        if palabras:
            kw_html = " ".join(
                f'<span style="background:#1a1f2e;border:1px solid {cfg["color"]}44;'
                f'color:{cfg["color"]};border-radius:4px;padding:2px 7px;'
                f'font-size:0.75rem;margin:2px;display:inline-block">{kw}</span>'
                for kw in palabras
            )
            st.markdown(f"**Palabras detectadas:** {kw_html}", unsafe_allow_html=True)

        st.markdown("#### 📊 Impacto probable por activo")
        activos_list = list(impacto.items())
        cols_act = st.columns(len(activos_list))
        for i, (activo, datos) in enumerate(activos_list):
            dir_ = datos["direccion"]
            css_card = {"SUBE":"sube-card","BAJA":"baja-card"}.get(dir_,"mixto-card")
            css_dir  = {"SUBE":"activo-dir-sube","BAJA":"activo-dir-baja"}.get(dir_,"activo-dir-mixto")
            flecha   = {"SUBE":"📈","BAJA":"📉"}.get(dir_,"↔️")
            with cols_act[i]:
                st.markdown(
                    f'<div class="activo-card {css_card}">'
                    f'<div class="activo-nombre">{activo}</div>'
                    f'<div class="activo-flecha">{flecha}</div>'
                    f'<div class="{css_dir}">{dir_}</div>'
                    f'<div class="activo-mag">{datos["magnitud"]}</div>'
                    f'</div>', unsafe_allow_html=True
                )

        with st.expander("🔍 Ver razones por activo"):
            c1, c2 = st.columns(2)
            suben  = [(a,d) for a,d in impacto.items() if d["direccion"]=="SUBE"]
            bajan  = [(a,d) for a,d in impacto.items() if d["direccion"]=="BAJA"]
            mixtos = [(a,d) for a,d in impacto.items() if d["direccion"]=="MIXTO"]
            with c1:
                if suben:
                    st.markdown("**🟢 Suben**")
                    for a,d in suben:
                        st.markdown(f"- **{a}** `{d['magnitud']}` — {d['razon']}")
                if mixtos:
                    st.markdown("**🟡 Mixto**")
                    for a,d in mixtos:
                        st.markdown(f"- **{a}** `{d['magnitud']}` — {d['razon']}")
            with c2:
                if bajan:
                    st.markdown("**🔴 Bajan**")
                    for a,d in bajan:
                        st.markdown(f"- **{a}** `{d['magnitud']}` — {d['razon']}")

        if ejemplos:
            st.markdown("#### 📚 Precedentes históricos")
            for ej in ejemplos:
                texto = ej.get("evento", str(ej)) if isinstance(ej, dict) else ej
                st.markdown(f'<div class="precedente-item">• {texto}</div>',
                            unsafe_allow_html=True)
    else:
        st.info("ℹ️ No se detectó patrón geopolítico claro.")

st.divider()

# ── ANÁLISIS DE BANCO CENTRAL ──────────────────────────────────────
st.subheader("🏛️ Análisis de Banco Central")
st.caption("La IA lee el comunicado actual y clasifica el tono — cambia con cada informe")

col_fed, col_bce = st.columns(2)
with col_fed:
    st.markdown(
        '<div style="background:#1a1f2e;border-radius:10px;padding:1rem;'
        'border:2px solid #2a2f3e;text-align:center">'
        '<div style="font-size:2rem">🇺🇸</div>'
        '<div style="color:#ffffff;font-weight:700">Federal Reserve</div>'
        '<div style="color:#8892a4;font-size:0.8rem">Tasa actual: 3.64%</div>'
        '</div>', unsafe_allow_html=True
    )
    btn_fed = st.button("Analizar FED", use_container_width=True, type="primary")

with col_bce:
    st.markdown(
        '<div style="background:#1a1f2e;border-radius:10px;padding:1rem;'
        'border:2px solid #2a2f3e;text-align:center">'
        '<div style="font-size:2rem">🇪🇺</div>'
        '<div style="color:#ffffff;font-weight:700">Banco Central Europeo</div>'
        '<div style="color:#8892a4;font-size:0.8rem">Tasa depósito: 1.93%</div>'
        '</div>', unsafe_allow_html=True
    )
    btn_bce = st.button("Analizar BCE", use_container_width=True, type="secondary")


def mostrar_analisis(comunicado, banco="FED"):
    emoji_banco = "🇺🇸" if banco == "FED" else "🇪🇺"
    st.success(f"{emoji_banco} {comunicado['titulo']}")
    st.caption(f"Fecha: {comunicado['fecha']}")
    st.divider()

    contexto_macro = {"datos": datos_macro, "regimen": regimen}
    with st.spinner(f"Analizando {banco} con IA..."):
        analisis = analizar_comunicado(comunicado, contexto_macro)

    st.subheader(f"🤖 Análisis KAIROS — {banco}")
    lineas = analisis.split('\n')
    secciones = []
    sec_actual = []
    for linea in lineas:
        es_titulo = any(str(i)+"." in linea for i in range(1,8))
        if linea.strip().startswith('**') and es_titulo:
            if sec_actual:
                secciones.append('\n'.join(sec_actual))
            sec_actual = [linea]
        else:
            sec_actual.append(linea)
    if sec_actual:
        secciones.append('\n'.join(sec_actual))

    if len(secciones) > 1:
        for s in secciones:
            if s.strip():
                st.markdown(s)
                st.divider()
    else:
        st.markdown(analisis)

    tono_det  = "NEUTRO"
    score_det = 0
    for linea in analisis.split('\n'):
        if "Clasificacion:" in linea or "Clasificación:" in linea:
            for t in ["HAWKISH FUERTE","HAWKISH LEVE","NEUTRO","DOVISH LEVE","DOVISH FUERTE"]:
                if t in linea:
                    tono_det = t
                    break
        if "Score:" in linea and "Confidence" not in linea:
            try:
                score_det = int(linea.split(":")[-1].strip().replace("+",""))
            except Exception:
                pass

    if banco == "FED":
        st.divider()
        st.subheader("🎯 Scoring de Priced-In")
        expectativas = obtener_probabilidades_cme()
        sorpresa     = calcular_sorpresa(tono_det, score_det, expectativas)

        if expectativas:
            st.markdown("**Próximas reuniones FOMC:**")
            for exp in expectativas[:2]:
                st.markdown(f"📅 **{exp['descripcion']}** ({exp['fecha_reunion']})")
                cols_exp = st.columns(len(exp["probabilidades"]))
                for i, (accion, prob) in enumerate(exp["probabilidades"].items()):
                    with cols_exp[i]:
                        color = "🔴" if "SUBIDA" in accion else "🟢" if "RECORTE" in accion else "🟡"
                        st.metric(color + " " + accion, f"{prob:.1f}%")
                st.markdown("---")

        if sorpresa:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Sesgo mercado previo", sorpresa["sesgo_mercado_previo"],
                          delta=f"{sorpresa['confianza_mercado']:.1f}% confianza")
            with c2:
                dv = sorpresa["delta_sorpresa"]
                st.metric("Delta sorpresa", f"{'+' if dv>=0 else ''}{dv}",
                          delta=sorpresa["nivel_sorpresa"])
            with c3:
                st.metric("Días próxima reunión",
                          str(sorpresa.get("dias_proxima_reunion","N/A")),
                          delta="FOMC Mayo 2026")

            nivel = sorpresa["nivel_sorpresa"]
            if "SIN SORPRESA" in nivel:
                st.info("ℹ️ " + sorpresa["impacto_esperado"])
            elif "HAWKISH" in nivel:
                st.warning("⚠️ " + sorpresa["impacto_esperado"])
            else:
                st.success("✅ " + sorpresa["impacto_esperado"])

        st.divider()
        st.subheader("📚 Precedentes Históricos FOMC")
        similares = encontrar_similares(tono_det, score_det)
        for ev in similares:
            with st.expander(f"📅 {ev['fecha']} — {ev['evento']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Tono:** {ev['tono']} (Score: {ev['score']})")
                    st.markdown(f"**Contexto:** {ev['contexto']}")
                    st.markdown(f"**Lección:** {ev['leccion']}")
                with c2:
                    st.markdown("**Outcomes 24h:**")
                    for activo, cambio in ev["outcomes_24h"].items():
                        color = "🟢" if cambio >= 0 else "🔴"
                        signo = "+" if cambio >= 0 else ""
                        st.markdown(f"{color} {activo}: {signo}{cambio}%")

        if similares:
            spx_avg  = sum(e["outcomes_24h"]["SPX"]  for e in similares)/len(similares)
            gold_avg = sum(e["outcomes_24h"]["Gold"] for e in similares)/len(similares)
            dxy_avg  = sum(e["outcomes_24h"]["DXY"]  for e in similares)/len(similares)
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("SPX avg", f"{'+'if spx_avg>=0 else''}{round(spx_avg,1)}%")
            with c2: st.metric("Gold avg",f"{'+'if gold_avg>=0 else''}{round(gold_avg,1)}%")
            with c3: st.metric("DXY avg", f"{'+'if dxy_avg>=0 else''}{round(dxy_avg,1)}%")

    elif banco == "BCE":
        st.divider()
        st.info(
            "📅 **Próxima reunión BCE: 5 junio 2026**\n\n"
            "Tasa de depósito actual: **1.93%** | "
            "Inflación 2026: **2.6%** | "
            "Crecimiento 2026: **0.9%**"
        )


if btn_fed:
    with st.spinner("Conectando con la FED..."):
        comunicado = obtener_comunicado_fed()
    if comunicado:
        mostrar_analisis(comunicado, banco="FED")
    else:
        st.error("No se pudo obtener el comunicado de la FED.")

elif btn_bce:
    with st.spinner("Conectando con el BCE..."):
        comunicado = obtener_comunicado_bce()
    if comunicado:
        mostrar_analisis(comunicado, banco="BCE")
    else:
        st.error("No se pudo obtener el comunicado del BCE.")

else:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### ¿Cómo usar KAIROS?")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**1️⃣ Morning Brief**")
            st.write("Cada mañana a las 8AM — resumen del mercado y predicción del día")
        with c2:
            st.markdown("**2️⃣ Analiza banco central**")
            st.write("IA lee el comunicado actual y detecta tono — cambia con cada informe")
        with c3:
            st.markdown("**3️⃣ Recibe alertas**")
            st.write("Telegram te avisa antes de que el mercado descuente el evento")
    with col2:
        st.markdown("### 💾 Briefs anteriores")
        archivos = sorted(glob.glob("outputs/morning_brief_*.txt"), reverse=True)
        if archivos:
            for archivo in archivos[:5]:
                nombre = os.path.basename(archivo).replace("morning_brief_","").replace(".txt","")
                if st.button(f"📅 {nombre}", key=archivo):
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()
                    st.text_area("Brief", contenido, height=400)
        else:
            archivos_analisis = sorted(glob.glob("outputs/analisis_*.txt"), reverse=True)
            if archivos_analisis:
                for archivo in archivos_analisis[:3]:
                    nombre = os.path.basename(archivo)
                    if st.button(nombre, key=nombre):
                        with open(archivo, "r", encoding="utf-8") as f:
                            contenido = f.read()
                        st.text_area("Análisis", contenido, height=400)
            else:
                st.write("Sin análisis guardados aún.")
