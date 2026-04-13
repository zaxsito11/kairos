import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analizar_comunicado(comunicado, contexto_macro=None):

    titulo = comunicado["titulo"]
    fecha  = comunicado["fecha"]
    # Compatible con fed_scraper antiguo ("texto") y nuevo ("contenido")
    texto  = comunicado.get("contenido") or comunicado.get("texto", "")
    texto_recortado = texto[:6000]

    print("🧠 Analizando comunicado con IA...")
    print(f"   Documento: {titulo}")
    print(f"   Fecha    : {fecha}\n")

    # Construir contexto macro si existe
    contexto_str = ""
    if contexto_macro:
        datos   = contexto_macro.get("datos", {})
        regimen = contexto_macro.get("regimen", {})

        core_pce    = datos.get("CORE_PCE", {})
        desempleo   = datos.get("DESEMPLEO", {})
        nfp         = datos.get("NFP", {})
        tasa_fed    = datos.get("TASA_FED", {})
        bono_2y     = datos.get("RENDIMIENTO_2Y", {})
        bono_10y    = datos.get("RENDIMIENTO_10Y", {})

        try:
            spread = round(
                float(bono_10y.get("valor", 0) or 0) -
                float(bono_2y.get("valor", 0) or 0), 2
            )
        except:
            spread = "N/A"

        señales = regimen.get("señales", [])
        señales_str = " | ".join(señales) if señales else "Sin señales claras"

        contexto_str = (
            "CONTEXTO MACRO ACTUAL:\n"
            "Usa estos datos reales para calibrar tu analisis:\n"
            "- Regimen macro: " + regimen.get("regimen", "N/A") + "\n"
            "- Core PCE: " + str(core_pce.get("variacion", "N/A")) + "% YoY (objetivo FED: 2%)\n"
            "- Desempleo: " + str(desempleo.get("valor", "N/A")) + "%\n"
            "- NFP ultimo mes: " + str(nfp.get("valor", "N/A")) + " miles\n"
            "- Tasa FED actual: " + str(tasa_fed.get("valor", "N/A")) + "%\n"
            "- Bono 10Y: " + str(bono_10y.get("valor", "N/A")) + "%\n"
            "- Spread curva 10Y-2Y: " + str(spread) + "%\n"
            "- Señales macro: " + señales_str + "\n"
        )

    prompt = (
        "Eres un analista macro senior especializado en politica monetaria "
        "de la Reserva Federal. Llevas 20 anos interpretando comunicados "
        "del FOMC para un hedge fund macro global.\n\n"
        + contexto_str + "\n"
        "GUIA DE CLASIFICACION DE TONO:\n"
        "- HAWKISH FUERTE (+3 a +5): inflacion persistente preocupante, "
        "mercado laboral solido, sin senales de recortes proximos.\n"
        "- HAWKISH LEVE (+1 a +2): inflacion elevada pero controlada, "
        "datos solidos, sin urgencia de recortar.\n"
        "- NEUTRO (0): balance perfecto entre riesgos, sin senal clara.\n"
        "- DOVISH LEVE (-1 a -2): enfriamiento economico, inflacion "
        "acercandose al objetivo, apertura a recortes.\n"
        "- DOVISH FUERTE (-3 a -5): preocupacion por recesion, desempleo "
        "subiendo, senales claras de recortes proximos.\n\n"
        "SENALES HAWKISH a buscar:\n"
        "inflation remains elevated, above the 2 percent objective, "
        "labor market remains strong, higher for longer, "
        "core PCE por encima de 2.5 por ciento.\n\n"
        "SENALES DOVISH a buscar:\n"
        "inflation has eased, labor market is cooling, "
        "appropriate to reduce, risks are becoming more balanced.\n\n"
        "TITULO: " + titulo + "\n"
        "FECHA: " + fecha + "\n\n"
        "TEXTO DEL COMUNICADO:\n" + texto_recortado + "\n\n"
        "Produce un analisis institucional con estas secciones:\n\n"
        "**1. TONO GENERAL**\n"
        "- Clasificacion: [HAWKISH FUERTE / HAWKISH LEVE / NEUTRO / DOVISH LEVE / DOVISH FUERTE]\n"
        "- Score: [numero de -5 a +5]\n"
        "- Senales hawkish encontradas: [frases clave del texto]\n"
        "- Senales dovish encontradas: [frases clave del texto]\n"
        "- Justificacion: [2-3 lineas]\n\n"
        "**2. MENSAJES CLAVE**\n"
        "- Los 3 mensajes mas importantes para los mercados\n\n"
        "**3. CAMBIOS RESPECTO AL COMUNICADO ANTERIOR**\n"
        "- Que lenguaje nuevo aparece\n"
        "- Que se elimino o suavizo\n\n"
        "**4. IMPACTO ESPERADO POR ACTIVO**\n"
        "- USD (Dolar):\n"
        "- Bonos del Tesoro UST 10Y:\n"
        "- S&P 500 (SPX):\n"
        "- Nasdaq (NDX):\n"
        "- Oro (Gold):\n"
        "- EUR/USD:\n"
        "- VIX (Volatilidad):\n\n"
        "**5. ESCENARIOS DE MERCADO**\n"
        "ESCENARIO A (probabilidad: X%): [nombre]\n"
        "[descripcion de impacto en mercados]\n\n"
        "ESCENARIO B (probabilidad: X%): [nombre]\n"
        "[descripcion de impacto en mercados]\n\n"
        "ESCENARIO C (probabilidad: X%): [nombre]\n"
        "[descripcion de impacto en mercados]\n\n"
        "**6. VARIABLES CLAVE A MONITOREAR**\n"
        "- Datos proximos relevantes\n"
        "- Declaraciones de miembros del FOMC a seguir\n\n"
        "**7. CONFIDENCE SCORE**\n"
        "- Score: X/100\n"
        "- Factores que reducen la confianza: [lista]\n\n"
        "Responde en espanol. Se directo y especifico. "
        "Cada afirmacion debe tener base en el texto o en el contexto macro."
    )

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista macro senior especializado en politica "
                    "monetaria y mercados financieros. Produces analisis "
                    "institucionales rigurosos, directos y accionables."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=3000
    )

    analisis = respuesta.choices[0].message.content

    print("=" * 60)
    print("📊 ANALISIS KAIROS — COMUNICADO FED")
    print("=" * 60)
    print(analisis)
    print("=" * 60)

    # Guardar análisis
    nombre_archivo = "outputs/analisis_fed_" + fecha[:3].lower() + ".txt"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write("KAIROS — ANALISIS DE COMUNICADO FED\n")
        f.write("=" * 60 + "\n")
        f.write("Documento: " + titulo + "\n")
        f.write("Fecha    : " + fecha + "\n")
        f.write("=" * 60 + "\n\n")
        if contexto_str:
            f.write("CONTEXTO MACRO:\n")
            f.write(contexto_str + "\n\n")
        f.write(analisis)

    print("\n💾 Analisis guardado en: " + nombre_archivo)

    return analisis


if __name__ == "__main__":
    from fed_scraper import obtener_comunicado_fed
    comunicado = obtener_comunicado_fed()
    if comunicado:
        analizar_comunicado(comunicado)
