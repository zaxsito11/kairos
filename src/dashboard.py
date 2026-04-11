import streamlit as st
import sys
import os
import glob

sys.path.insert(0, os.path.dirname(__file__))

from fed_scraper import obtener_comunicado_fed
from bce_scraper import obtener_comunicado_bce
from analizador import analizar_comunicado
from precios import obtener_precios
from macro import obtener_datos_macro, evaluar_regimen_macro
from historico import encontrar_similares
from sorpresa_macro import analizar_sorpresas_recientes, generar_resumen_macro_sorpresas
from geopolitica import clasificar_evento_geopolitico, generar_alerta_geopolitica

st.set_page_config(
    page_title="KAIROS — Inteligencia de Mercados",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.titulo-kairos {
    font-size: 2.5rem;
    font-weight: 800;
    color: #00d4aa;
    letter-spacing: 4px;
}
.subtitulo { color: #8892a4; font-size: 1rem; }
.precio-card {
    background-color: #1a1f2e;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    text-align: center;
    border: 1px solid #2a2f3e;
}
.precio-nombre { color: #8892a4; font-size: 0.75rem; font-weight: 600; }
.precio-valor  { color: #ffffff; font-size: 1.1rem; font-weight: 700; }
.sube { color: #00d4aa; font-size: 0.85rem; }
.baja { color: #ff4b4b; font-size: 0.85rem; }

/* Panel geopolítico */
.geo-tipo {
    background: linear-gradient(135deg, #1a1f2e, #0d1117);
    border-left: 4px solid #00d4aa;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}
.geo-tipo h3 { color: #ffffff; margin: 0 0 0.3rem 0; font-size: 1.2rem; }
.geo-tipo p  { color: #8892a4; margin: 0; font-size: 0.9rem; }

.activo-card {
    background-color: #1a1f2e;
    border-radius: 8px;
    padding: 0.7rem 0.5rem;
    text-align: center;
    border: 1px solid #2a2f3e;
    height: 100%;
}
.activo-card.sube-card { border-color: #00d4aa; }
.activo-card.baja-card { border-color: #ff4b4b; }
.activo-card.mixto-card { border-color: #ffa500; }

.activo-nombre { color: #8892a4; font-size: 0.7rem; font-weight: 700; letter-spacing: 1px; }
.activo-flecha { font-size: 1.6rem; line-height: 1.8rem; }
.activo-dir-sube  { color: #00d4aa; font-weight: 700; font-size: 0.85rem; }
.activo-dir-baja  { color: #ff4b4b; font-weight: 700; font-size: 0.85rem; }
.activo-dir-mixto { color: #ffa500; font-weight: 700; font-size: 0.85rem; }
.activo-mag { color: #8892a4; font-size: 0.7rem; }

.precedente-item {
    background-color: #1a1f2e;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.4rem;
    border-left: 3px solid #2a2f3e;
    color: #c9d1d9;
    font-size: 0.88rem;
}

.tag-hawkish { background:#ff4b4b22; color:#ff4b4b; border:1px solid #ff4b4b44;
               border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
.tag-dovish  { background:#00d4aa22; color:#00d4aa; border:1px solid #00d4aa44;
               border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
.tag-neutro  { background:#ffa50022; color:#ffa500; border:1px solid #ffa50044;
               border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="titulo-kairos">KAIROS</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo">Sistema de Inteligencia de Mercados Financieros</p>', unsafe_allow_html=True)
st.divider()

# ── PRECIOS EN TIEMPO REAL ────────────────────────────────────────
st.subheader("Mercados en tiempo real")
with st.spinner("Cargando precios..."):
    precios = obtener_precios()

if precios:
    cols = st.columns(len(precios))
    for i, (nombre, datos) in enumerate(precios.items()):
        with cols[i]:
            if datos:
                clase = "sube" if datos["variacion"] >= 0 else "baja"
                signo = "+" if datos["variacion"] >= 0 else ""
                html = (
                    '<div class="precio-card">'
                    '<div class="precio-nombre">' + nombre + '</div>'
                    '<div class="precio-valor">' + str(datos["precio"]) + '</div>'
                    '<div class="' + clase + '">' + signo + str(datos["variacion_pct"]) + '% ' + datos["direccion"] + '</div>'
                    '</div>'
                )
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="precio-card"><div class="precio-nombre">' + nombre +
                    '</div><div class="precio-valor">N/A</div></div>',
                    unsafe_allow_html=True
                )

st.divider()

# ── CONTEXTO MACRO ────────────────────────────────────────────────
st.subheader("Contexto Macro Actual")
with st.spinner("Cargando datos macro..."):
    datos_macro = obtener_datos_macro()
    regimen = evaluar_regimen_macro(datos_macro)

color_regimen = {"HAWKISH": "🔴", "NEUTRO": "🟡", "DOVISH": "🟢"}
emoji = color_regimen.get(regimen["regimen"], "⚪")
st.markdown(f"**Régimen macro:** {emoji} {regimen['regimen']} — {regimen['descripcion']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Inflación**")
    if datos_macro.get("CORE_PCE") and datos_macro["CORE_PCE"].get("variacion"):
        st.metric("Core PCE (YoY)", f"{datos_macro['CORE_PCE']['variacion']}%", delta="Objetivo: 2%")
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
        st.metric("Spread 10Y-2Y", f"{round(r10 - r2, 2)}%")

st.markdown("**Sorpresas vs Consenso (últimos datos publicados):**")
with st.spinner("Calculando sorpresas..."):
    sorpresas = analizar_sorpresas_recientes()

if sorpresas:
    cols_s = st.columns(len(sorpresas))
    for i, s in enumerate(sorpresas):
        with cols_s[i]:
            signo = "+" if s["diferencia"] > 0 else ""
            st.metric(
                s["nombre"],
                str(s["real"]) + " " + s["unidad"],
                delta=signo + str(s["diferencia"]) + " vs " + str(s["consenso"])
            )
            st.caption(s["emoji"] + " " + s["nivel"])

st.divider()

# ── PANEL GEOPOLÍTICO ─────────────────────────────────────────────
st.subheader("🌍 Análisis Geopolítico")
st.caption("Pega un titular de noticias para detectar el tipo de evento y su impacto en mercados")

titular_geo = st.text_input(
    "Titular de noticia:",
    placeholder="Ej: US imposes new tariffs on Chinese imports amid escalating trade war..."
)

if titular_geo:
    clasificacion = clasificar_evento_geopolitico(titular_geo)

    if clasificacion:
        # Configuración visual por tipo de evento
        config_tipo = {
            "CONFLICTO_ARMADO":       {"emoji": "🔴", "color": "#ff4b4b", "label": "Conflicto Armado"},
            "SANCION_ECONOMICA":      {"emoji": "🟠", "color": "#ff8c00", "label": "Sanción Económica"},
            "TENSION_COMERCIAL":      {"emoji": "🟡", "color": "#ffd700", "label": "Tensión Comercial"},
            "CRISIS_ENERGETICA":      {"emoji": "⚡", "color": "#ffa500", "label": "Crisis Energética"},
            "INESTABILIDAD_POLITICA": {"emoji": "🟣", "color": "#9b59b6", "label": "Inestabilidad Política"},
            "ACUERDO_PAZ_COMERCIAL":  {"emoji": "🟢", "color": "#00d4aa", "label": "Acuerdo / Paz"},
        }
        tipo     = clasificacion["tipo"]
        cfg      = config_tipo.get(tipo, {"emoji": "⚪", "color": "#8892a4", "label": tipo})
        impacto  = clasificacion["impacto"]
        ejemplos = clasificacion.get("ejemplos", clasificacion.get("precedentes", []))
        palabras = clasificacion.get("palabras", [])

        # Cabecera del evento
        st.markdown(
            f'<div class="geo-tipo" style="border-left-color:{cfg["color"]}">'
            f'<h3>{cfg["emoji"]} {cfg["label"]}</h3>'
            f'<p>{clasificacion["descripcion"]}</p>'
            f'</div>',
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

        # Cards de activos
        st.markdown("#### 📊 Impacto esperado por activo")
        activos = list(impacto.items())
        cols_activos = st.columns(len(activos))

        for i, (activo, datos) in enumerate(activos):
            dir_ = datos["direccion"]
            mag  = datos["magnitud"]
            razon = datos["razon"]

            if dir_ == "SUBE":
                css_card  = "sube-card"
                css_dir   = "activo-dir-sube"
                flecha    = "📈"
            elif dir_ == "BAJA":
                css_card  = "baja-card"
                css_dir   = "activo-dir-baja"
                flecha    = "📉"
            else:
                css_card  = "mixto-card"
                css_dir   = "activo-dir-mixto"
                flecha    = "↔️"

            with cols_activos[i]:
                st.markdown(
                    f'<div class="activo-card {css_card}">'
                    f'<div class="activo-nombre">{activo}</div>'
                    f'<div class="activo-flecha">{flecha}</div>'
                    f'<div class="{css_dir}">{dir_}</div>'
                    f'<div class="activo-mag">{mag}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # Razones expandibles
        st.markdown("")
        with st.expander("🔍 Ver razones por activo"):
            col_sube, col_baja = st.columns(2)
            suben = [(a, d) for a, d in impacto.items() if d["direccion"] == "SUBE"]
            bajan = [(a, d) for a, d in impacto.items() if d["direccion"] == "BAJA"]
            mixtos = [(a, d) for a, d in impacto.items() if d["direccion"] == "MIXTO"]

            with col_sube:
                if suben:
                    st.markdown("**🟢 Suben**")
                    for activo, datos in suben:
                        st.markdown(
                            f"- **{activo}** `{datos['magnitud']}` — {datos['razon']}"
                        )
                if mixtos:
                    st.markdown("**🟡 Mixto**")
                    for activo, datos in mixtos:
                        st.markdown(
                            f"- **{activo}** `{datos['magnitud']}` — {datos['razon']}"
                        )
            with col_baja:
                if bajan:
                    st.markdown("**🔴 Bajan**")
                    for activo, datos in bajan:
                        st.markdown(
                            f"- **{activo}** `{datos['magnitud']}` — {datos['razon']}"
                        )

        # Precedentes históricos
        if ejemplos:
            st.markdown("#### 📚 Precedentes históricos similares")
            for ej in ejemplos:
                if isinstance(ej, dict):
                    texto = ej.get("evento", str(ej))
                else:
                    texto = ej
                st.markdown(
                    f'<div class="precedente-item">• {texto}</div>',
                    unsafe_allow_html=True
                )

    else:
        st.info(
            "ℹ️ No se detectaron patrones geopolíticos en ese titular. "
            "Intenta con palabras como: tariff, sanction, war, OPEC, coup, ceasefire..."
        )

st.divider()

# ── SELECTOR BANCO CENTRAL ────────────────────────────────────────
st.subheader("Selecciona el banco central a analizar")
col1, col2 = st.columns(2)
with col1:
    btn_fed = st.button("🇺🇸 Analizar FED", use_container_width=True, type="primary")
with col2:
    btn_bce = st.button("🇪🇺 Analizar BCE", use_container_width=True, type="secondary")


def mostrar_analisis(comunicado):
    st.success("Comunicado: " + comunicado["titulo"])
    st.caption("Fecha: " + str(comunicado["fecha"]))
    st.divider()

    contexto_macro = {"datos": datos_macro, "regimen": regimen}

    with st.spinner("Analizando con inteligencia artificial..."):
        analisis = analizar_comunicado(comunicado, contexto_macro)

    st.subheader("Analisis KAIROS")

    lineas = analisis.split('\n')
    secciones = []
    seccion_actual = []
    for linea in lineas:
        es_titulo = any(str(i) + "." in linea for i in range(1, 8))
        if linea.strip().startswith('**') and es_titulo:
            if seccion_actual:
                secciones.append('\n'.join(seccion_actual))
            seccion_actual = [linea]
        else:
            seccion_actual.append(linea)
    if seccion_actual:
        secciones.append('\n'.join(seccion_actual))

    if len(secciones) > 1:
        for seccion in secciones:
            if seccion.strip():
                st.markdown(seccion)
                st.divider()
    else:
        st.markdown(analisis)

    st.success("Analisis guardado en outputs/")

    # Detectar tono y score del análisis
    tono_det  = "NEUTRO"
    score_det = 0
    for linea in analisis.split('\n'):
        if "Clasificacion:" in linea or "Clasificación:" in linea:
            for t in ["HAWKISH FUERTE", "HAWKISH LEVE", "NEUTRO", "DOVISH LEVE", "DOVISH FUERTE"]:
                if t in linea:
                    tono_det = t
                    break
        if "Score:" in linea and "Confidence" not in linea:
            try:
                score_det = int(linea.split(":")[-1].strip().replace("+", ""))
            except:
                pass

    # Priced-in scoring
    st.divider()
    st.subheader("🎯 Scoring de Priced-In")
    st.caption("⚠️ Actualizar manualmente cada semana en src/priced_in.py con datos de CME FedWatch")

    from priced_in import obtener_probabilidades_cme, calcular_sorpresa

    expectativas = obtener_probabilidades_cme()
    sorpresa     = calcular_sorpresa(tono_det, score_det, expectativas)

    if expectativas:
        st.markdown("**Próximas reuniones FOMC — Expectativas del mercado:**")
        for exp in expectativas[:2]:
            st.markdown(f"📅 **{exp['descripcion']}** ({exp['fecha_reunion']})")
            cols_exp = st.columns(len(exp["probabilidades"]))
            for i, (accion, prob) in enumerate(exp["probabilidades"].items()):
                with cols_exp[i]:
                    color = "🔴" if "SUBIDA" in accion else "🟢" if "RECORTE" in accion else "🟡"
                    st.metric(color + " " + accion, f"{prob:.1f}%")
            st.markdown("---")

    if sorpresa:
        st.markdown("**Análisis de sorpresa:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Sesgo previo mercado",
                sorpresa["sesgo_mercado_previo"],
                delta=f"{sorpresa['confianza_mercado']:.1f}% confianza"
            )
        with col2:
            delta_val = sorpresa["delta_sorpresa"]
            st.metric(
                "Delta sorpresa",
                f"{'+' if delta_val >= 0 else ''}{delta_val}",
                delta=sorpresa["nivel_sorpresa"]
            )
        with col3:
            st.metric(
                "Días próxima reunión",
                str(sorpresa.get("dias_proxima_reunion", "N/A")),
                delta="FOMC Mayo 2026"
            )

        nivel = sorpresa["nivel_sorpresa"]
        if "SIN SORPRESA" in nivel:
            st.info("ℹ️ " + sorpresa["impacto_esperado"])
        elif "HAWKISH" in nivel:
            st.warning("⚠️ " + sorpresa["impacto_esperado"])
        else:
            st.success("✅ " + sorpresa["impacto_esperado"])

    # Precedentes históricos FOMC
    st.divider()
    st.subheader("📚 Precedentes Históricos")

    similares = encontrar_similares(tono_det, score_det)

    for ev in similares:
        with st.expander("📅 " + ev['fecha'] + " — " + ev['evento']):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Tono:** " + ev['tono'] + " (Score: " + str(ev['score']) + ")")
                st.markdown("**Contexto:** " + ev['contexto'])
                st.markdown("**Lección:** " + ev['leccion'])
            with c2:
                st.markdown("**Outcomes 24h:**")
                for activo, cambio in ev["outcomes_24h"].items():
                    color = "🟢" if cambio >= 0 else "🔴"
                    signo = "+" if cambio >= 0 else ""
                    st.markdown(color + " " + activo + ": " + signo + str(cambio) + "%")

    if similares:
        spx_avg  = sum(e["outcomes_24h"]["SPX"]  for e in similares) / len(similares)
        gold_avg = sum(e["outcomes_24h"]["Gold"] for e in similares) / len(similares)
        dxy_avg  = sum(e["outcomes_24h"]["DXY"]  for e in similares) / len(similares)
        st.markdown("**Promedio histórico de eventos similares (24h):**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("SPX",  ("+" if spx_avg  >= 0 else "") + str(round(spx_avg,  1)) + "%")
        with c2:
            st.metric("Gold", ("+" if gold_avg >= 0 else "") + str(round(gold_avg, 1)) + "%")
        with c3:
            st.metric("DXY",  ("+" if dxy_avg  >= 0 else "") + str(round(dxy_avg,  1)) + "%")


if btn_fed:
    with st.spinner("Conectando con la FED..."):
        comunicado = obtener_comunicado_fed()
    if comunicado:
        mostrar_analisis(comunicado)
    else:
        st.error("No se pudo obtener el comunicado de la FED.")

elif btn_bce:
    st.info("🔄 El módulo BCE está siendo mejorado. Disponible próximamente.")
    st.markdown("- Decisiones de tasas del BCE en tiempo real")
    st.markdown("- Conferencias de prensa de Christine Lagarde")
    st.markdown("- Comparación BCE vs FED en misma pantalla")

else:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Como usar KAIROS")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Paso 1**")
            st.write("Selecciona FED o BCE arriba")
        with c2:
            st.markdown("**Paso 2**")
            st.write("KAIROS descarga el comunicado oficial más reciente")
        with c3:
            st.markdown("**Paso 3**")
            st.write("La IA analiza y genera escenarios de impacto en mercados")
    with col2:
        st.markdown("### Análisis guardados")
        archivos = glob.glob("outputs/analisis_*.txt")
        archivos.sort(reverse=True)
        if archivos:
            for archivo in archivos[:5]:
                nombre = os.path.basename(archivo)
                if st.button(nombre, key=nombre):
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()
                    st.text_area("Análisis", contenido, height=400)
        else:
            st.write("No hay análisis guardados aún.")