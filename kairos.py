import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fed_scraper import obtener_comunicado_fed
from analizador import analizar_comunicado
from macro import obtener_datos_macro, evaluar_regimen_macro
from alertas import evaluar_y_alertar
from historico import encontrar_similares, generar_resumen_historico
from priced_in import obtener_probabilidades_cme, calcular_sorpresa, mostrar_priced_in

def ejecutar_kairos():

    print("\n")
    print("=" * 60)
    print("  ██╗  ██╗ █████╗ ██╗██████╗  ██████╗ ███████╗")
    print("  ██║ ██╔╝██╔══██╗██║██╔══██╗██╔═══██╗██╔════╝")
    print("  █████╔╝ ███████║██║██████╔╝██║   ██║███████╗")
    print("  ██╔═██╗ ██╔══██║██║██╔══██╗██║   ██║╚════██║")
    print("  ██║  ██╗██║  ██║██║██║  ██║╚██████╔╝███████║")
    print("  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝")
    print("=" * 60)
    print("  Sistema de Inteligencia de Mercados Financieros")
    print(f"  {datetime.now().strftime('%d %b %Y — %H:%M:%S')}")
    print("=" * 60)
    print()

    # PASO 1: Datos macro
    print("▶ PASO 1: Obteniendo contexto macro...")
    datos_macro = obtener_datos_macro()
    regimen     = evaluar_regimen_macro(datos_macro)
    print(f"   Regimen macro actual: {regimen['regimen']}")
    print()

    # PASO 1B: Expectativas del mercado (priced-in)
    print("▶ PASO 1B: Obteniendo expectativas del mercado...")
    expectativas = obtener_probabilidades_cme()
    print(f"   Próxima reunión FOMC: {expectativas[0]['fecha_reunion']}")
    print(f"   Probabilidad sin cambio: {expectativas[0]['probabilidades'].get('SIN CAMBIO', 0):.1f}%")
    print()

    # PASO 2: Comunicado FED
    print("▶ PASO 2: Obteniendo comunicado de la FED...")
    comunicado = obtener_comunicado_fed()
    if not comunicado:
        print("❌ No se pudo obtener el comunicado.")
        return
    print()

    # PASO 3: Analisis con contexto macro
    print("▶ PASO 3: Analizando con IA + contexto macro...")
    contexto_macro = {
        "datos":   datos_macro,
        "regimen": regimen
    }
    analisis = analizar_comunicado(comunicado, contexto_macro)

# PASO 3B: Calcular sorpresa vs expectativas
    tono_det = "NEUTRO"
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
            except:
                pass

    sorpresa = calcular_sorpresa(tono_det, score_det, expectativas)
    mostrar_priced_in(sorpresa, expectativas)
    
    # PASO 3B: Calcular sorpresa vs expectativas
    tono_det = "NEUTRO"
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
            except:
                pass

    sorpresa = calcular_sorpresa(tono_det, score_det, expectativas)
    mostrar_priced_in(sorpresa, expectativas)
    
    # PASO 4: Evaluar y enviar alerta si el evento es relevante
    print("▶ PASO 4: Evaluando si merece alerta...")
    evaluar_y_alertar(comunicado, analisis, regimen)

    # PASO 5: Comparacion historica
    print("▶ PASO 5: Buscando precedentes historicos...")
    
    # Extraer tono y score del analisis
    tono_detectado  = "HAWKISH LEVE"
    score_detectado = 2
    
    for linea in analisis.split('\n'):
        if "Clasificacion:" in linea or "Clasificación:" in linea:
            for tono in ["HAWKISH FUERTE", "HAWKISH LEVE", "NEUTRO", "DOVISH LEVE", "DOVISH FUERTE"]:
                if tono in linea:
                    tono_detectado = tono
                    break
        if "Score:" in linea and "Confidence" not in linea:
            try:
                val = linea.split(":")[-1].strip().replace("+","")
                score_detectado = int(val)
            except:
                pass

    similares = encontrar_similares(tono_detectado, score_detectado)
    resumen_hist = generar_resumen_historico(similares)
    print(resumen_hist)

    # Guardar historico junto al analisis
    nombre_hist = "outputs/historico_" + comunicado["fecha"][:3].lower() + ".txt"
    with open(nombre_hist, "w", encoding="utf-8") as f:
        f.write("KAIROS — PRECEDENTES HISTORICOS\n")
        f.write("=" * 60 + "\n\n")
        f.write(resumen_hist)
    print(f"💾 Historico guardado en: {nombre_hist}")

    print()
    print("=" * 60)
    print("  ✅ KAIROS completó el análisis")
    print(f"  📁 Revisa outputs/ para el reporte completo")
    print("=" * 60)


if __name__ == "__main__":
    ejecutar_kairos()