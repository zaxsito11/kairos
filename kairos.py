import sys
import os
from datetime import datetime

# Agregar src al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fed_scraper import obtener_comunicado_fed
from analizador import analizar_comunicado

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

    # PASO 1: Descargar comunicado
    print("▶ PASO 1: Obteniendo último comunicado de la FED...")
    comunicado = obtener_comunicado_fed()

    if not comunicado:
        print("❌ No se pudo obtener el comunicado. Abortando.")
        return

    print()

    # PASO 2: Analizar con IA
    print("▶ PASO 2: Analizando con inteligencia artificial...")
    analisis = analizar_comunicado(comunicado)

    print()
    print("=" * 60)
    print("  ✅ KAIROS completó el análisis exitosamente")
    print(f"  📁 Revisa la carpeta outputs/ para ver el reporte")
    print("=" * 60)
    print()


if __name__ == "__main__":
    ejecutar_kairos()