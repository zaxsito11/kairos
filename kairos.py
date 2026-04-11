import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fed_scraper import obtener_comunicado_fed
from analizador import analizar_comunicado
from macro import obtener_datos_macro, evaluar_regimen_macro

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

    print()
    print("=" * 60)
    print("  ✅ KAIROS completó el análisis")
    print(f"  📁 Revisa outputs/ para el reporte completo")
    print("=" * 60)


if __name__ == "__main__":
    ejecutar_kairos()