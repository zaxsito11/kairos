import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fed_scraper import obtener_comunicado_fed
from bce_scraper import obtener_comunicado_bce
from analizador import analizar_comunicado
from precios import obtener_precios

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
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="titulo-kairos">KAIROS</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo">Sistema de Inteligencia de Mercados Financieros</p>', unsafe_allow_html=True)
st.divider()

# Precios en tiempo real
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
                    '<div class="precio-card"><div class="precio-nombre">' + nombre + '</div><div class="precio-valor">N/A</div></div>',
                    unsafe_allow_html=True
                )

# Panel de contexto macro
st.subheader("Contexto Macro Actual")

with st.spinner("Cargando datos macro..."):
    from macro import obtener_datos_macro, evaluar_regimen_macro
    datos_macro = obtener_datos_macro()
    regimen     = evaluar_regimen_macro(datos_macro)

# Color del regimen
color_regimen = {
    "HAWKISH": "🔴",
    "NEUTRO":  "🟡",
    "DOVISH":  "🟢"
}
emoji = color_regimen.get(regimen["regimen"], "⚪")

st.markdown(f"**Régimen macro:** {emoji} {regimen['regimen']} — {regimen['descripcion']}")

# Mostrar datos macro en columnas
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Inflación**")
    if datos_macro.get("CORE_PCE") and datos_macro["CORE_PCE"].get("variacion"):
        val = datos_macro["CORE_PCE"]["variacion"]
        color = "🔴" if val > 2.5 else "🟢"
        st.metric("Core PCE (YoY)", f"{val}%", delta="Objetivo: 2%")
    if datos_macro.get("CORE_CPI") and datos_macro["CORE_CPI"].get("variacion"):
        val = datos_macro["CORE_CPI"]["variacion"]
        st.metric("Core CPI (YoY)", f"{val}%")

with col2:
    st.markdown("**Empleo**")
    if datos_macro.get("DESEMPLEO") and datos_macro["DESEMPLEO"].get("valor"):
        val = datos_macro["DESEMPLEO"]["valor"]
        st.metric("Desempleo", f"{val}%")
    if datos_macro.get("NFP") and datos_macro["NFP"].get("variacion"):
        val = datos_macro["NFP"]["variacion"]
        st.metric("NFP (MoM%)", f"{val}%")

with col3:
    st.markdown("**Tasas y Curva**")
    if datos_macro.get("TASA_FED") and datos_macro["TASA_FED"].get("valor"):
        val = datos_macro["TASA_FED"]["valor"]
        st.metric("Tasa FED", f"{val}%")
    if datos_macro.get("RENDIMIENTO_10Y") and datos_macro.get("RENDIMIENTO_2Y"):
        r10 = datos_macro["RENDIMIENTO_10Y"].get("valor", 0) or 0
        r2  = datos_macro["RENDIMIENTO_2Y"].get("valor", 0) or 0
        spread = round(float(r10) - float(r2), 2)
        st.metric("Spread 10Y-2Y", f"{spread}%")

st.divider()

# Selector de banco central
st.subheader("Selecciona el banco central a analizar")
col1, col2 = st.columns(2)

with col1:
    btn_fed = st.button(
        "🇺🇸 Analizar FED",
        use_container_width=True,
        type="primary"
    )

with col2:
    btn_bce = st.button(
        "🇪🇺 Analizar BCE",
        use_container_width=True,
        type="secondary"
    )

def mostrar_analisis(comunicado):
    st.success("Comunicado: " + comunicado["titulo"])
    st.caption("Fecha: " + str(comunicado["fecha"]))
    st.divider()

    with st.spinner("Analizando con inteligencia artificial..."):
        analisis = analizar_comunicado(comunicado)

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


if btn_fed:
    with st.spinner("Conectando con la FED..."):
        comunicado = obtener_comunicado_fed()
    if comunicado:
        mostrar_analisis(comunicado)
    else:
        st.error("No se pudo obtener el comunicado de la FED.")

elif btn_bce:
    st.info("🔄 El módulo BCE está siendo mejorado con fuentes más robustas. Disponible próximamente.")
    st.markdown("**Próxima actualización incluirá:**")
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
            st.write("KAIROS descarga el comunicado oficial mas reciente")
        with c3:
            st.markdown("**Paso 3**")
            st.write("La IA analiza y genera escenarios de impacto en mercados")

    with col2:
        st.markdown("### Análisis guardados")
        import os
        import glob

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