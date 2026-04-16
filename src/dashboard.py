import streamlit as st
import sys, os, glob, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from fed_scraper      import obtener_comunicado_fed
from bce_scraper      import obtener_comunicado_bce
from analizador       import analizar_comunicado
from precios          import obtener_precios, detectar_correlaciones_activas
from macro            import obtener_datos_macro, evaluar_regimen_macro
from historico        import encontrar_similares
from sorpresa_macro   import analizar_sorpresas_recientes
from geopolitica      import clasificar_evento_geopolitico
from calendario_eco   import obtener_eventos_proximos, resumen_semana
from priced_in        import obtener_probabilidades_cme, calcular_sorpresa
from price_targets    import calcular_targets_fusionados
from signal_engine    import analizar_mercado_completo, formatear_señales_telegram

st.set_page_config(
    page_title="KAIROS — Inteligencia de Mercados",
    page_icon="📊", layout="wide"
)

st.markdown("""<style>
.titulo-kairos{font-size:2.5rem;font-weight:800;color:#00d4aa;letter-spacing:4px;}
.subtitulo{color:#8892a4;font-size:1rem;}
.precio-card{background:#1a1f2e;border-radius:8px;padding:0.8rem 1rem;
  text-align:center;border:1px solid #2a2f3e;}
.precio-nombre{color:#8892a4;font-size:0.75rem;font-weight:600;}
.precio-valor{color:#ffffff;font-size:1.05rem;font-weight:700;}
.sube{color:#00d4aa;font-size:0.82rem;}
.baja{color:#ff4b4b;font-size:0.82rem;}
.brief-card{background:#1a1f2e;border-radius:10px;padding:1.2rem;
  border-left:4px solid #00d4aa;margin-bottom:0.5rem;}
.brief-fecha{color:#8892a4;font-size:0.78rem;}
.brief-resumen{color:#c9d1d9;font-size:0.88rem;line-height:1.6;}
.cal-card{background:#1a1f2e;border-radius:10px;padding:1rem 1.2rem;
  margin-bottom:0.8rem;border-left:4px solid #2a2f3e;}
.cal-card.critico{border-left-color:#ff4b4b;}
.cal-card.alto{border-left-color:#ffa500;}
.cal-titulo{color:#ffffff;font-weight:700;font-size:1rem;margin:0;}
.cal-fecha{color:#8892a4;font-size:0.8rem;margin:0.2rem 0;}
.cal-consenso{color:#00d4aa;font-size:0.8rem;}
.cal-activos{color:#8892a4;font-size:0.75rem;}
.badge-critico{background:#ff4b4b22;color:#ff4b4b;border:1px solid #ff4b4b44;
  border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:700;}
.badge-alto{background:#ffa50022;color:#ffa500;border:1px solid #ffa50044;
  border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:700;}
.geo-tipo{background:linear-gradient(135deg,#1a1f2e,#0d1117);
  border-left:4px solid #00d4aa;border-radius:8px;padding:1rem 1.2rem;margin-bottom:1rem;}
.geo-tipo h3{color:#ffffff;margin:0 0 0.3rem 0;font-size:1.2rem;}
.geo-tipo p{color:#8892a4;margin:0;font-size:0.9rem;}
.activo-card{background:#1a1f2e;border-radius:8px;padding:0.7rem 0.5rem;
  text-align:center;border:1px solid #2a2f3e;height:100%;}
.activo-card.sube-card{border-color:#00d4aa;}
.activo-card.baja-card{border-color:#ff4b4b;}
.activo-card.mixto-card{border-color:#ffa500;}
.activo-nombre{color:#8892a4;font-size:0.7rem;font-weight:700;}
.activo-flecha{font-size:1.6rem;line-height:1.8rem;}
.activo-dir-sube{color:#00d4aa;font-weight:700;font-size:0.85rem;}
.activo-dir-baja{color:#ff4b4b;font-weight:700;font-size:0.85rem;}
.activo-dir-mixto{color:#ffa500;font-weight:700;font-size:0.85rem;}
.activo-mag{color:#8892a4;font-size:0.7rem;}
.sit-activa{background:#ff4b4b15;border:1px solid #ff4b4b33;border-radius:8px;
  padding:0.7rem 1rem;margin-bottom:0.5rem;}
.sit-nombre{color:#ff4b4b;font-weight:700;font-size:0.85rem;}
.sit-nota{color:#8892a4;font-size:0.78rem;margin-top:2px;}
.alerta-item{background:#1a1f2e;border-radius:6px;padding:0.5rem 0.8rem;
  margin-bottom:0.4rem;border-left:3px solid #00d4aa;font-size:0.8rem;color:#c9d1d9;}
</style>""", unsafe_allow_html=True)

# ── HEADER ─────────────────────────────────────────────────────────
st.markdown('<p class="titulo-kairos">KAIROS</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo">The intelligence between events and markets</p>',
            unsafe_allow_html=True)
st.divider()

# ── MACRO (carga temprana para usar en targets) ───────────────────
with st.spinner("Cargando datos macro..."):
    datos_macro = obtener_datos_macro()
    regimen     = evaluar_regimen_macro(datos_macro)

# ── MORNING BRIEF ──────────────────────────────────────────────────
st.subheader("📊 Morning Brief")
brief_file = "data/ultimo_brief.json"
col_b1, col_b2, col_b3 = st.columns([3, 1, 1])

if os.path.exists(brief_file):
    try:
        with open(brief_file, "r", encoding="utf-8") as f:
            brief_data = json.load(f)
        hoy         = datetime.now().strftime("%Y-%m-%d")
        fecha_brief = brief_data.get("fecha","")
        brief_texto = brief_data.get("brief","")
        badge_color = "#00d4aa" if fecha_brief == hoy else "#ffa500"
        badge_txt   = "HOY" if fecha_brief == hoy else fecha_brief

        lineas = brief_texto.split('\n')
        resumen_lineas = []
        en_res = False
        for l in lineas:
            if "RESUMEN EJECUTIVO" in l: en_res = True; continue
            if en_res and l.strip().startswith("**") and "RESUMEN" not in l: break
            if en_res and l.strip(): resumen_lineas.append(l.strip())

        resumen = " ".join(resumen_lineas[:3]) or brief_texto[:250]
        with col_b1:
            st.markdown(
                f'<div class="brief-card">'
                f'<div class="brief-fecha">📅 Brief — <span style="color:{badge_color};font-weight:700">{badge_txt}</span></div>'
                f'<div class="brief-resumen" style="margin-top:0.4rem">{resumen}...</div>'
                f'</div>', unsafe_allow_html=True)
            with st.expander("📖 Ver brief completo"):
                st.markdown(brief_texto)
    except Exception:
        with col_b1:
            st.info("Sin brief disponible aún.")

with col_b2:
    if st.button("🔄 Generar Brief", use_container_width=True):
        with st.spinner("Generando..."):
            try:
                from morning_brief import generar_y_enviar_brief
                generar_y_enviar_brief(forzar=True)
                st.success("✅ Enviado")
                st.rerun()
            except Exception as e:
                st.error(f"{e}")

with col_b3:
    if st.button("📉 Closing Brief", use_container_width=True):
        with st.spinner("Generando..."):
            try:
                from closing_brief import generar_y_enviar_closing
                generar_y_enviar_closing(forzar=True)
                st.success("✅ Enviado")
            except Exception as e:
                st.error(f"{e}")

st.divider()

# ── PRECIOS EN TIEMPO REAL ─────────────────────────────────────────
st.subheader("📈 Mercados en tiempo real")
with st.spinner("Cargando precios..."):
    precios = obtener_precios()

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
                    f'</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="precio-card"><div class="precio-nombre">{nombre}</div>'
                    f'<div class="precio-valor">N/A</div></div>', unsafe_allow_html=True)

if precios:
    st.caption("Índices y volatilidad")
    render_fila(["SPX","NDX","VIX","DXY"])
    st.caption("Commodities y Crypto")
    render_fila(["Gold","Silver","WTI","BTC"])
    st.caption("Divisas y bonos")
    render_fila(["EURUSD","UST10Y"])

    correlaciones = detectar_correlaciones_activas(precios)
    if correlaciones:
        st.markdown("#### 🔗 Correlaciones activas")
        cols_c = st.columns(min(len(correlaciones),3))
        for i,c in enumerate(correlaciones):
            with cols_c[i%3]:
                efectos = " | ".join([e[:45] for e in c["correlaciones"][:2]])
                st.markdown(
                    f'<div style="background:#1a1f2e;border-left:3px solid #ffa500;'
                    f'border-radius:6px;padding:0.6rem;margin-bottom:4px">'
                    f'<div style="color:#ffa500;font-weight:700;font-size:0.82rem">'
                    f'{c["activo"]} {c["movimiento"]}</div>'
                    f'<div style="color:#8892a4;font-size:0.75rem">{efectos}</div>'
                    f'</div>', unsafe_allow_html=True)

st.divider()

# ── TARGETS DE PRECIO ──────────────────────────────────────────────
# Tabs: Convergencia y Targets
tab_conv, tab_tgt = st.tabs(["🎯 Señales Convergentes", "📊 Targets de Precio"])

with tab_conv:
    st.caption("Solo se muestran activos con múltiples factores alineados — silencio = sin señal clara")
    col_cv1, col_cv2 = st.columns([3,1])
    with col_cv1:
        if st.button("🔍 Analizar Convergencia", use_container_width=True, type="primary"):
            with st.spinner("Analizando convergencia técnico + macro + geopolítica..."):
                try:
                    from news_scanner import SITUACIONES_ACTIVAS
                    sits = [{"nombre":s["nombre"],"tipo":s["tipo"],"score":s["score_base"]}
                            for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
                    tono = "HAWKISH LEVE"
                    conv = analizar_mercado_completo(
                        regimen=regimen,
                        tono_fed=tono,
                        situaciones=sits,
                        generar_narrativas=True,
                    )
                    st.session_state["convergencia"] = conv
                except Exception as e:
                    st.error(f"Error: {e}")

    with col_cv2:
        n_acc = st.session_state.get("convergencia",{}).get("n_accionables",0)
        if n_acc > 0:
            st.markdown(f'<div style="color:#00d4aa;font-size:1.5rem;font-weight:700">{n_acc}</div>',
                        unsafe_allow_html=True)
            st.caption("señales accionables")

    if "convergencia" in st.session_state:
        conv    = st.session_state["convergencia"]
        señales = conv.get("señales",{})
        accion  = conv.get("accionables",[])
        neutros = [k for k,v in señales.items() if not v.get("accionable")]

        if accion:
            st.markdown("#### Señales accionables:")
            cols_cv = st.columns(min(len(accion),3))
            for idx,nombre in enumerate(accion):
                s     = señales[nombre]
                dir_  = s.get("direccion","NEUTRO")
                conf  = s.get("confianza",0)
                nivel = s.get("nivel","")
                narrv = s.get("narrativa","")
                t24h  = s.get("target_24h")
                precio= s.get("precio",0)
                n_af  = s.get("n_factores_a_favor",0)
                color = "#00d4aa" if dir_=="SUBE" else "#ff4b4b"
                emoji = "📈" if dir_=="SUBE" else "📉"
                nivel_emoji = {"FUERTE":"🔴","MEDIA":"🟡","DÉBIL":"⚪"}.get(nivel,"⚪")

                with cols_cv[idx%3]:
                    factores_html = "".join([
                        f'<div style="color:#8892a4;font-size:0.72rem">✓ {d[:55]}</div>'
                        for _,d in s.get("factores_a_favor",[])[:3]
                    ])
                    en_contra_html = "".join([
                        f'<div style="color:#ff4b4b;font-size:0.7rem">✗ {d[:50]}</div>'
                        for _,d in s.get("factores_en_contra",[])[:1]
                    ])
                    st.markdown(
                        f'<div style="background:#1a1f2e;border-radius:10px;padding:1rem;'
                        f'border-left:4px solid {color};margin-bottom:8px">'
                        f'<div style="color:{color};font-size:1.1rem;font-weight:700">'
                        f'{emoji} {nombre} {dir_} {nivel_emoji}</div>'
                        f'<div style="color:#ffffff;font-size:0.85rem">{conf}% confianza</div>'
                        f'<div style="color:#00d4aa;font-size:0.8rem;margin:4px 0">'
                        f'Precio: {precio} → T24h: {t24h}</div>'
                        f'<div style="color:#c9d1d9;font-size:0.8rem;font-style:italic;margin:4px 0">'
                        f'"{narrv[:90]}"</div>'
                        f'{factores_html}{en_contra_html}'
                        f'<div style="color:#8892a4;font-size:0.7rem;margin-top:4px">'
                        f'{n_af} factores convergentes</div>'
                        f'</div>', unsafe_allow_html=True)

        # Activos neutros
        if neutros:
            with st.expander(f"⚫ {len(neutros)} activos sin señal convergente"):
                cols_n = st.columns(len(neutros))
                for i,nombre in enumerate(neutros):
                    s   = señales.get(nombre,{})
                    dir_= s.get("direccion","NEUTRO")
                    conf= s.get("confianza",0)
                    with cols_n[i]:
                        st.markdown(
                            f'<div style="background:#0d1117;border-radius:6px;'
                            f'padding:0.5rem;text-align:center;border:1px solid #2a2f3e">'
                            f'<div style="color:#8892a4;font-size:0.75rem">{nombre}</div>'
                            f'<div style="color:#555;font-size:0.7rem">↔️ NEUTRO</div>'
                            f'</div>', unsafe_allow_html=True)

st.divider()

with tab_tgt:
    st.caption("Técnico (RSI/MACD/EMA/Vol/OBV) + Macro + Geopolítica — 40%/30%/20%/10%")
    st.subheader("🎯 Targets de Precio")
    st.caption("Técnico (RSI/MACD/EMA/Vol/OBV) + Macro + Geopolítica — 40%/30%/20%/10%")

col_t1, col_t2 = st.columns([4,1])
with col_t1:
    if st.button("📊 Calcular Targets Ahora", use_container_width=True, type="primary"):
        with st.spinner("Analizando técnico + macro + geopolítica..."):
            try:
                from news_scanner import SITUACIONES_ACTIVAS
                from feedback_sistema import mostrar_estadisticas_actuales
                sits = [{"nombre":s["nombre"],"tipo":s["tipo"]}
                        for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
                tono_fed = "HAWKISH LEVE"
                # Intentar leer tono del último análisis
                archivos_an = sorted(glob.glob("outputs/analisis_*.txt"), reverse=True)
                if archivos_an:
                    with open(archivos_an[0], "r", encoding="utf-8") as f:
                        contenido_an = f.read()
                    for t in ["HAWKISH FUERTE","HAWKISH LEVE","NEUTRO","DOVISH LEVE","DOVISH FUERTE"]:
                        if t in contenido_an:
                            tono_fed = t
                            break

                tgts = calcular_targets_fusionados(
                    regimen_macro=regimen.get("regimen","NEUTRO"),
                    tono_fed=tono_fed,
                    situaciones_activas=sits
                )
                from price_targets import guardar_prediccion
                guardar_prediccion(tgts)
                st.session_state["targets"] = tgts
                st.session_state["tono_fed_usado"] = tono_fed
            except Exception as e:
                st.error(f"Error: {e}")

with col_t2:
    st.caption(f"Régimen: **{regimen.get('regimen','?')}**")
    stats_file = "data/feedback_estadisticas.json"
    if os.path.exists(stats_file):
        try:
            with open(stats_file) as f:
                fb = json.load(f)
            prec = fb.get("precision_dir_24h",0)
            n    = fb.get("total_evaluaciones",0)
            if n > 0:
                color = "#00d4aa" if prec>=60 else "#ffa500" if prec>=45 else "#ff4b4b"
                st.markdown(f'<div style="color:{color};font-weight:700">Precisión: {prec}%</div>',
                            unsafe_allow_html=True)
                st.caption(f"({n} evaluaciones)")
        except Exception:
            pass

if "targets" in st.session_state:
    tgts  = st.session_state["targets"]
    orden = ["SPX","NDX","Gold","Silver","WTI","BTC","DXY","VIX","UST10Y"]
    cols_t = st.columns(4)
    for idx, nombre_t in enumerate([a for a in orden if a in tgts]):
        t     = tgts[nombre_t]
        dir_  = t.get("direccion","MIXTO")
        prob  = t.get("probabilidad",50)
        rsi   = t.get("rsi",50)
        vol   = t.get("vol_relativo",1.0)
        obv   = t.get("obv_tendencia","─")[:5]
        t24h  = t.get("target_24h",0)
        t7d   = t.get("target_7d",0)
        t30d  = t.get("target_30d",0)
        sop   = t.get("soporte_real", t.get("soporte_1",0))
        res   = t.get("resist_real",  t.get("resistencia_1",0))
        color = "#00d4aa" if dir_=="SUBE" else "#ff4b4b" if dir_=="BAJA" else "#ffa500"
        emoji = "📈" if dir_=="SUBE" else "📉" if dir_=="BAJA" else "↔️"
        warn  = " ⚠️" if (vol < 0.7 or (obv and "DISTRIB" in obv)) else ""
        with cols_t[idx % 4]:
            st.markdown(
                f'<div style="background:#1a1f2e;border-radius:8px;padding:0.8rem;'
                f'border-left:3px solid {color};margin-bottom:8px">'
                f'<div style="color:#8892a4;font-size:0.7rem;font-weight:700">{nombre_t}</div>'
                f'<div style="color:{color};font-weight:700">{emoji} {dir_} ({prob}%){warn}</div>'
                f'<div style="color:#8892a4;font-size:0.72rem">RSI:{rsi} Vol:{vol:.1f}x {obv}</div>'
                f'<div style="color:#00d4aa;font-size:0.78rem;margin-top:3px">24h: {t24h}</div>'
                f'<div style="color:#8892a4;font-size:0.72rem">7d:{t7d} | 30d:{t30d}</div>'
                f'<div style="color:#8892a4;font-size:0.7rem">S:{sop} R:{res}</div>'
                f'</div>', unsafe_allow_html=True)

st.divider()

# ── SITUACIONES ACTIVAS ────────────────────────────────────────────
st.subheader("🔴 Situaciones Activas")
try:
    from news_scanner import SITUACIONES_ACTIVAS
    activas = [s for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
    if activas:
        cols_sit = st.columns(len(activas))
        for i,s in enumerate(activas):
            with cols_sit[i]:
                st.markdown(
                    f'<div class="sit-activa">'
                    f'<div class="sit-nombre">🔴 {s["nombre"]}</div>'
                    f'<div class="sit-nota">Score: {s["score_base"]}/100</div>'
                    f'<div class="sit-nota">{s["nota"]}</div>'
                    f'</div>', unsafe_allow_html=True)
    else:
        st.success("✅ Sin situaciones activas")
except Exception:
    pass

st.divider()

# ── HISTORIAL DE ALERTAS ───────────────────────────────────────────
st.subheader("📋 Últimas Alertas Enviadas")
st.caption("Registro de alertas del canal KAIROS Markets")

col_al1, col_al2 = st.columns([2,1])
with col_al1:
    log_file = "outputs/monitor.log"
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lineas_log = f.readlines()
            alertas_log = [l.strip() for l in lineas_log
                           if "Alerta enviada" in l or "✅ score:" in l or
                           "Event Brief" in l or "Morning Brief" in l][-15:]
            if alertas_log:
                for al in reversed(alertas_log[-8:]):
                    hora = al[:19] if len(al) > 19 else al
                    texto = al[25:] if len(al) > 25 else al
                    st.markdown(
                        f'<div class="alerta-item">🕐 {hora} — {texto[:80]}</div>',
                        unsafe_allow_html=True)
            else:
                st.caption("Sin alertas registradas aún")
        except Exception as e:
            st.caption(f"Log no disponible: {e}")
    else:
        st.caption("Monitor no ha corrido aún")

with col_al2:
    st.caption("Briefs anteriores:")
    archivos_briefs = sorted(
        glob.glob("outputs/morning_brief_*.txt") +
        glob.glob("outputs/closing_brief_*.txt") +
        glob.glob("outputs/weekly_brief_*.txt") +
        glob.glob("outputs/event_brief_*.txt"),
        reverse=True
    )
    for arch in archivos_briefs[:6]:
        nombre_arch = os.path.basename(arch)
        tipo = ("📊" if "morning" in nombre_arch else
                "📉" if "closing" in nombre_arch else
                "📈" if "weekly" in nombre_arch else "⚡")
        label = nombre_arch.replace("morning_brief_","").replace("closing_brief_","") \
                            .replace("weekly_brief_","").replace("event_brief_","") \
                            .replace(".txt","")[:12]
        if st.button(f"{tipo} {label}", key=arch, use_container_width=True):
            with open(arch, "r", encoding="utf-8") as f:
                contenido = f.read()
            st.text_area("", contenido, height=300)

st.divider()

# ── CALENDARIO ECONÓMICO ───────────────────────────────────────────
st.subheader("📅 Próximos Eventos Macro")
with st.spinner("Cargando calendario..."):
    eventos_cal = obtener_eventos_proximos(dias=30)

if eventos_cal:
    criticos = [e for e in eventos_cal if e["impacto"]=="CRÍTICO"]
    altos    = [e for e in eventos_cal if e["impacto"]=="ALTO"]
    col_cal1, col_cal2 = st.columns([1,1])
    with col_cal1:
        for ev in (criticos + altos)[:6]:
            horas  = ev["horas_restantes"]
            tiempo = f"{int(horas)}h" if horas < 24 else f"{ev['dias_restantes']} días"
            css    = "critico" if ev["impacto"]=="CRÍTICO" else "alto"
            badge  = (f'<span class="badge-critico">🚨 CRÍTICO</span>'
                      if css=="critico" else f'<span class="badge-alto">⚠️ ALTO</span>')
            cons_h = (f'<div class="cal-consenso">Consenso: {ev["consenso"]}</div>'
                      if ev.get("consenso") else "")
            prob   = ev.get("prob_sorpresa",{})
            prob_h = ""
            if prob:
                prob_h = (f'<div style="margin-top:6px">'
                          f'<span style="color:#ff4b4b;font-size:0.72rem">🔴 Hawkish {prob.get("prob_sorpresa_hawkish",0)}%</span>&nbsp;'
                          f'<span style="color:#00d4aa;font-size:0.72rem">🟢 Dovish {prob.get("prob_sorpresa_dovish",0)}%</span>'
                          f'</div>')
            st.markdown(
                f'<div class="cal-card {css}">'
                f'{badge}&nbsp;&nbsp;<span style="color:#8892a4;font-size:0.75rem">en {tiempo}</span>'
                f'<p class="cal-titulo">{ev["evento"]}</p>'
                f'<p class="cal-fecha">📅 {ev["hora_local_et"]}</p>'
                f'{cons_h}<div class="cal-activos">📊 {", ".join(ev["activos"][:4])}</div>'
                f'{prob_h}</div>', unsafe_allow_html=True)
    with col_cal2:
        st.markdown("**Próximos 30 días:**")
        for ev in eventos_cal[:8]:
            emoji = {"CRÍTICO":"🚨","ALTO":"⚠️"}.get(ev["impacto"],"📡")
            st.markdown(f"{emoji} **{ev['evento']}** — "
                        f"<span style='color:#8892a4'>{ev['dias_restantes']} días</span>",
                        unsafe_allow_html=True)
else:
    st.info("Sin eventos macro en los próximos 30 días.")

st.divider()

# ── CONTEXTO MACRO ─────────────────────────────────────────────────
st.subheader("🏦 Contexto Macro")
emoji_reg = {"HAWKISH":"🔴","NEUTRO":"🟡","DOVISH":"🟢"}.get(regimen["regimen"],"⚪")
st.markdown(f"**Régimen:** {emoji_reg} **{regimen['regimen']}** — {regimen['descripcion']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Inflación**")
    if datos_macro.get("CORE_PCE") and datos_macro["CORE_PCE"].get("variacion"):
        st.metric("Core PCE (YoY)", f"{datos_macro['CORE_PCE']['variacion']}%", delta="Obj: 2%")
    if datos_macro.get("CORE_CPI") and datos_macro["CORE_CPI"].get("variacion"):
        st.metric("Core CPI (YoY)", f"{datos_macro['CORE_CPI']['variacion']}%")
with col2:
    st.markdown("**Empleo**")
    if datos_macro.get("DESEMPLEO") and datos_macro["DESEMPLEO"].get("valor"):
        st.metric("Desempleo", f"{datos_macro['DESEMPLEO']['valor']}%")
    if datos_macro.get("NFP") and datos_macro["NFP"].get("variacion"):
        st.metric("NFP (MoM%)", f"{datos_macro['NFP']['variacion']}%")
with col3:
    st.markdown("**Tasas**")
    if datos_macro.get("TASA_FED") and datos_macro["TASA_FED"].get("valor"):
        st.metric("Tasa FED", f"{datos_macro['TASA_FED']['valor']}%")
    if datos_macro.get("RENDIMIENTO_10Y") and datos_macro.get("RENDIMIENTO_2Y"):
        r10 = float(datos_macro["RENDIMIENTO_10Y"].get("valor",0) or 0)
        r2  = float(datos_macro["RENDIMIENTO_2Y"].get("valor",0)  or 0)
        st.metric("Spread 10Y-2Y", f"{round(r10-r2,2)}%")

with st.spinner("Calculando sorpresas..."):
    sorpresas = analizar_sorpresas_recientes()
if sorpresas:
    cols_s = st.columns(len(sorpresas))
    for i,s in enumerate(sorpresas):
        with cols_s[i]:
            signo = "+" if s["diferencia"]>0 else ""
            st.metric(s["nombre"], f"{s['real']} {s['unidad']}",
                      delta=f"{signo}{s['diferencia']} vs {s['consenso']}")
            st.caption(f"{s['emoji']} {s['nivel']}")

st.divider()

# ── ANÁLISIS GEOPOLÍTICO ───────────────────────────────────────────
st.subheader("🌍 Análisis Geopolítico")
titular_geo = st.text_input("Titular:",
    placeholder="US imposes new 25% tariffs on Chinese imports...")

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
        tipo    = clasificacion["tipo"]
        cfg     = config_tipo.get(tipo,{"emoji":"⚪","color":"#8892a4","label":tipo})
        impacto = clasificacion["impacto"]
        st.markdown(
            f'<div class="geo-tipo" style="border-left-color:{cfg["color"]}">'
            f'<h3>{cfg["emoji"]} {cfg["label"]}</h3>'
            f'<p>{clasificacion["descripcion"]}</p></div>', unsafe_allow_html=True)

        st.markdown("#### 📊 Impacto por activo")
        cols_act = st.columns(len(impacto))
        for i,(activo,datos) in enumerate(impacto.items()):
            dir_      = datos["direccion"]
            css_card  = {"SUBE":"sube-card","BAJA":"baja-card"}.get(dir_,"mixto-card")
            css_dir   = {"SUBE":"activo-dir-sube","BAJA":"activo-dir-baja"}.get(dir_,"activo-dir-mixto")
            flecha    = {"SUBE":"📈","BAJA":"📉"}.get(dir_,"↔️")
            with cols_act[i]:
                st.markdown(
                    f'<div class="activo-card {css_card}">'
                    f'<div class="activo-nombre">{activo}</div>'
                    f'<div class="activo-flecha">{flecha}</div>'
                    f'<div class="{css_dir}">{dir_}</div>'
                    f'<div class="activo-mag">{datos["magnitud"]}</div>'
                    f'</div>', unsafe_allow_html=True)
    else:
        st.info("No se detectó patrón geopolítico.")

st.divider()

# ── ANÁLISIS BANCO CENTRAL ─────────────────────────────────────────
st.subheader("🏛️ Análisis de Banco Central")
col_fed, col_bce = st.columns(2)
with col_fed:
    st.markdown(
        '<div style="background:#1a1f2e;border-radius:10px;padding:1rem;'
        'border:2px solid #2a2f3e;text-align:center">'
        '<div style="font-size:2rem">🇺🇸</div>'
        '<div style="color:#fff;font-weight:700">Federal Reserve</div>'
        '<div style="color:#8892a4;font-size:0.8rem">Tasa: 3.64%</div>'
        '</div>', unsafe_allow_html=True)
    btn_fed = st.button("Analizar FED", use_container_width=True, type="primary")

with col_bce:
    st.markdown(
        '<div style="background:#1a1f2e;border-radius:10px;padding:1rem;'
        'border:2px solid #2a2f3e;text-align:center">'
        '<div style="font-size:2rem">🇪🇺</div>'
        '<div style="color:#fff;font-weight:700">Banco Central Europeo</div>'
        '<div style="color:#8892a4;font-size:0.8rem">Tasa depósito: 1.93%</div>'
        '</div>', unsafe_allow_html=True)
    btn_bce = st.button("Analizar BCE", use_container_width=True, type="secondary")


def mostrar_analisis(comunicado, banco="FED"):
    st.success(f"{'🇺🇸' if banco=='FED' else '🇪🇺'} {comunicado['titulo']}")
    st.caption(f"Fecha: {comunicado['fecha']}")
    contexto_macro = {"datos": datos_macro, "regimen": regimen}
    with st.spinner(f"Analizando {banco} con IA..."):
        analisis = analizar_comunicado(comunicado, contexto_macro)
    st.subheader(f"🤖 Análisis KAIROS — {banco}")
    lineas = analisis.split('\n')
    secciones, sec_actual = [], []
    for linea in lineas:
        es_titulo = any(str(i)+"." in linea for i in range(1,8))
        if linea.strip().startswith('**') and es_titulo:
            if sec_actual: secciones.append('\n'.join(sec_actual))
            sec_actual = [linea]
        else:
            sec_actual.append(linea)
    if sec_actual: secciones.append('\n'.join(sec_actual))
    for s in (secciones if len(secciones)>1 else [analisis]):
        if s.strip(): st.markdown(s); st.divider()

    tono_det, score_det = "NEUTRO", 0
    for linea in analisis.split('\n'):
        if "Clasificacion:" in linea or "Clasificación:" in linea:
            for t in ["HAWKISH FUERTE","HAWKISH LEVE","NEUTRO","DOVISH LEVE","DOVISH FUERTE"]:
                if t in linea: tono_det = t; break
        if "Score:" in linea and "Confidence" not in linea:
            try: score_det = int(linea.split(":")[-1].strip().replace("+",""))
            except: pass

    if banco == "FED":
        st.divider()
        st.subheader("🎯 Priced-In")
        expectativas = obtener_probabilidades_cme()
        sorpresa     = calcular_sorpresa(tono_det, score_det, expectativas)
        if expectativas:
            for exp in expectativas[:2]:
                st.markdown(f"📅 **{exp['descripcion']}** ({exp['fecha_reunion']})")
                cols_exp = st.columns(len(exp["probabilidades"]))
                for i,(accion,prob) in enumerate(exp["probabilidades"].items()):
                    with cols_exp[i]:
                        color = "🔴" if "SUBIDA" in accion else "🟢" if "RECORTE" in accion else "🟡"
                        st.metric(color+" "+accion, f"{prob:.1f}%")
                st.markdown("---")
        if sorpresa:
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("Sesgo mercado", sorpresa["sesgo_mercado_previo"],
                               delta=f"{sorpresa['confianza_mercado']:.1f}%")
            with c2: st.metric("Delta sorpresa",
                               f"{'+' if sorpresa['delta_sorpresa']>=0 else ''}{sorpresa['delta_sorpresa']}",
                               delta=sorpresa["nivel_sorpresa"])
            with c3: st.metric("Días próx reunión",
                               str(sorpresa.get("dias_proxima_reunion","N/A")))
            nivel = sorpresa["nivel_sorpresa"]
            if "SIN SORPRESA" in nivel: st.info("ℹ️ "+sorpresa["impacto_esperado"])
            elif "HAWKISH" in nivel:    st.warning("⚠️ "+sorpresa["impacto_esperado"])
            else:                       st.success("✅ "+sorpresa["impacto_esperado"])

        st.divider()
        st.subheader("📚 Precedentes Históricos")
        similares = encontrar_similares(tono_det, score_det)
        for ev in similares:
            with st.expander(f"📅 {ev['fecha']} — {ev['evento']}"):
                c1,c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Tono:** {ev['tono']} ({ev['score']})")
                    st.markdown(f"**Contexto:** {ev['contexto']}")
                    st.markdown(f"**Lección:** {ev['leccion']}")
                with c2:
                    st.markdown("**Outcomes 24h:**")
                    for activo,cambio in ev["outcomes_24h"].items():
                        st.markdown(f"{'🟢' if cambio>=0 else '🔴'} {activo}: {'+' if cambio>=0 else ''}{cambio}%")
        if similares:
            spx_avg  = sum(e["outcomes_24h"]["SPX"]  for e in similares)/len(similares)
            gold_avg = sum(e["outcomes_24h"]["Gold"] for e in similares)/len(similares)
            dxy_avg  = sum(e["outcomes_24h"]["DXY"]  for e in similares)/len(similares)
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("SPX avg",  f"{'+'if spx_avg>=0 else''}{round(spx_avg,1)}%")
            with c2: st.metric("Gold avg", f"{'+'if gold_avg>=0 else''}{round(gold_avg,1)}%")
            with c3: st.metric("DXY avg",  f"{'+'if dxy_avg>=0 else''}{round(dxy_avg,1)}%")
    else:
        st.divider()
        st.info("📅 **Próxima reunión BCE: 5 junio 2026** | Tasa: 1.93% | Probabilidad subida: 60%")


if btn_fed:
    with st.spinner("Conectando con la FED..."):
        comunicado = obtener_comunicado_fed()
    if comunicado: mostrar_analisis(comunicado, banco="FED")
    else: st.error("No se pudo obtener el comunicado de la FED.")
elif btn_bce:
    with st.spinner("Conectando con el BCE..."):
        comunicado = obtener_comunicado_bce()
    if comunicado: mostrar_analisis(comunicado, banco="BCE")
    else: st.error("No se pudo obtener el comunicado del BCE.")
else:
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("### ¿Cómo usar KAIROS?")
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("**1️⃣ Morning Brief 8AM**")
            st.write("Predicciones + targets del día con análisis técnico y macro")
        with c2:
            st.markdown("**2️⃣ Targets de Precio**")
            st.write("RSI/MACD/EMA + macro + geopolítica fusionados en un target")
        with c3:
            st.markdown("**3️⃣ Canal Telegram**")
            st.write("Alertas en tiempo real antes de que el mercado lo descuente")
    with col2:
        st.markdown("### 📊 Precisión del sistema")
        stats_file = "data/feedback_estadisticas.json"
        if os.path.exists(stats_file):
            try:
                with open(stats_file) as f:
                    fb = json.load(f)
                n    = fb.get("total_evaluaciones",0)
                prec = fb.get("precision_dir_24h",0)
                err  = fb.get("error_target_avg",0)
                if n > 0:
                    color = "#00d4aa" if prec>=60 else "#ffa500" if prec>=45 else "#ff4b4b"
                    st.markdown(f'<div style="color:{color};font-size:2rem;font-weight:700">{prec}%</div>',
                                unsafe_allow_html=True)
                    st.caption(f"Dirección correcta ({n} evaluaciones)")
                    st.caption(f"Error target promedio: {err}%")
                    st.progress(min(prec/100, 1.0))
                else:
                    st.caption("Recopilando datos...")
                    st.caption("Feedback disponible mañana")
            except Exception:
                pass
        else:
            st.caption("Sistema activo — datos desde hoy")
