# Página 5 — Historial y Precisión
import streamlit as st
import os, json, glob
from datetime import datetime

st.markdown("## 📋 Historial y Precisión")
st.caption("Registro de alertas, briefs y evolución de la precisión del sistema")

tab1, tab2, tab3 = st.tabs(["🎯 Precisión del sistema",
                              "📋 Historial de briefs",
                              "📡 Log de alertas"])

with tab1:
    fb_file = "data/feedback_estadisticas.json"
    if os.path.exists(fb_file):
        try:
            with open(fb_file) as f:
                fb = json.load(f)

            n     = fb.get("total_evaluaciones",0)
            prec  = fb.get("precision_dir_24h",0)
            rango = fb.get("precision_rango_24h",0)
            err   = fb.get("error_target_avg",0)

            c1,c2,c3,c4 = st.columns(4)
            with c1:
                color = "#00d4aa" if prec>=60 else "#ffa500" if prec>=45 else "#ff4b4b"
                st.markdown(f'<div style="text-align:center;padding:1rem;background:#1a1f2e;border-radius:8px">'
                            f'<div style="color:#8892a4;font-size:0.75rem">Dirección correcta</div>'
                            f'<div style="color:{color};font-size:2rem;font-weight:700">{prec}%</div>'
                            f'<div style="color:#8892a4;font-size:0.72rem">{n} evaluaciones</div>'
                            f'</div>', unsafe_allow_html=True)
            with c2:
                st.metric("En rango predicho", f"{rango}%")
            with c3:
                st.metric("Error target promedio", f"{err}%")
            with c4:
                ultima = fb.get("ultima_evaluacion","N/A")
                st.metric("Última evaluación", ultima)

            # Por activo
            por_activo = fb.get("por_activo",{})
            if por_activo:
                st.markdown("### Por activo")
                datos_tabla = []
                for activo, a in sorted(por_activo.items()):
                    if a["total"] > 0:
                        pct = round(a["aciertos_dir"]/a["total"]*100,1)
                        datos_tabla.append({
                            "Activo": activo,
                            "Precisión": f"{pct}%",
                            "Aciertos": f"{a['aciertos_dir']}/{a['total']}",
                            "Error target": f"{a.get('error_avg',0)}%",
                        })
                import pandas as pd
                st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True)

            # Historial
            historial = fb.get("historial",[])
            if historial:
                st.markdown("### Evolución de precisión")
                import pandas as pd
                df = pd.DataFrame(historial[-30:])
                if not df.empty:
                    st.line_chart(df.set_index("fecha")["precision_dir"])
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("Sin datos de feedback aún. El sistema evalúa automáticamente cada día a las 4:15 PM ET.")
        if st.button("🔄 Ejecutar evaluación ahora"):
            try:
                from feedback_sistema import ejecutar_feedback_diario
                ejecutar_feedback_diario(forzar=True)
                st.success("✅ Evaluación completada")
                st.rerun()
            except Exception as e:
                st.error(f"{e}")

with tab2:
    st.markdown("### Briefs anteriores")
    tipos = {
        "📊 Morning": "outputs/morning_brief_*.txt",
        "📉 Closing": "outputs/closing_brief_*.txt",
        "📈 Weekly":  "outputs/weekly_brief_*.txt",
        "⚡ Event":   "outputs/event_brief_*.txt",
    }
    for tipo_label, patron in tipos.items():
        archivos = sorted(glob.glob(patron), reverse=True)
        if archivos:
            with st.expander(f"{tipo_label} ({len(archivos)} briefs)"):
                for arch in archivos[:5]:
                    nombre = os.path.basename(arch)
                    label  = nombre.replace("morning_brief_","").replace("closing_brief_","") \
                                   .replace("weekly_brief_","").replace("event_brief_","") \
                                   .replace(".txt","")
                    if st.button(f"Ver: {label}", key=arch):
                        with open(arch, "r", encoding="utf-8", errors="ignore") as f:
                            st.text_area("", f.read(), height=300, key=f"ta_{arch}")

with tab3:
    log_file = "outputs/monitor.log"
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lineas = f.readlines()
            # Últimas 100 líneas relevantes
            relevantes = [l.strip() for l in lineas[-200:]
                         if any(x in l for x in ["Alerta","Brief","ERROR","WARNING",
                                                   "accionable","score:"])][-50:]
            st.markdown(f"**Últimas actividades del sistema:**")
            for l in reversed(relevantes[-30:]):
                color = "#ff4b4b" if "ERROR" in l else "#ffa500" if "WARNING" in l else "#c9d1d9"
                st.markdown(
                    f'<div style="font-family:monospace;font-size:0.75rem;'
                    f'color:{color};padding:2px 0;border-bottom:1px solid #1a1f2e">'
                    f'{l[:120]}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Error leyendo log: {e}")
    else:
        st.info("Log no disponible. Ejecuta el monitor para generar actividad.")
