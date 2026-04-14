# analizador.py — KAIROS
# Motor de análisis IA para comunicados de bancos centrales.
# Detecta automáticamente si es FED o BCE y aplica el prompt correcto.

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── Detector de banco central ─────────────────────────────────────
def detectar_banco(comunicado: dict) -> str:
    """
    Detecta si el comunicado es de la FED o del BCE.
    Retorna: "FED" o "BCE"
    """
    titulo = comunicado.get("titulo", "").lower()
    link   = comunicado.get("link", "").lower()
    contenido = (comunicado.get("contenido") or
                 comunicado.get("texto", ""))[:500].lower()

    señales_bce = [
        "ecb", "european central bank", "governing council",
        "lagarde", "ecb.europa.eu", "euro area", "eurozone",
        "deposit facility", "eurosystem"
    ]
    for señal in señales_bce:
        if señal in titulo or señal in link or señal in contenido:
            return "BCE"

    return "FED"


# ── Contexto macro ────────────────────────────────────────────────
def construir_contexto_macro(contexto_macro: dict, banco: str) -> str:
    """Construye el string de contexto macro según el banco."""
    if not contexto_macro:
        return ""

    datos   = contexto_macro.get("datos", {})
    regimen = contexto_macro.get("regimen", {})

    core_pce = datos.get("CORE_PCE", {})
    desempleo= datos.get("DESEMPLEO", {})
    nfp      = datos.get("NFP", {})
    tasa_fed = datos.get("TASA_FED", {})
    bono_2y  = datos.get("RENDIMIENTO_2Y", {})
    bono_10y = datos.get("RENDIMIENTO_10Y", {})

    try:
        spread = round(
            float(bono_10y.get("valor", 0) or 0) -
            float(bono_2y.get("valor", 0) or 0), 2
        )
    except Exception:
        spread = "N/A"

    señales     = regimen.get("señales", [])
    señales_str = " | ".join(señales) if señales else "Sin señales claras"

    if banco == "FED":
        return (
            "CONTEXTO MACRO EEUU (datos reales FRED):\n"
            f"- Régimen macro: {regimen.get('regimen', 'N/A')}\n"
            f"- Core PCE: {core_pce.get('variacion', 'N/A')}% YoY (objetivo FED: 2%)\n"
            f"- Desempleo: {desempleo.get('valor', 'N/A')}%\n"
            f"- NFP último mes: {nfp.get('valor', 'N/A')} miles\n"
            f"- Tasa FED actual: {tasa_fed.get('valor', 'N/A')}%\n"
            f"- Bono 10Y EEUU: {bono_10y.get('valor', 'N/A')}%\n"
            f"- Spread curva 10Y-2Y: {spread}%\n"
            f"- Señales macro: {señales_str}\n"
        )
    else:  # BCE
        return (
            "CONTEXTO MACRO GLOBAL (referencia para análisis BCE):\n"
            f"- Conflicto Medio Oriente: ACTIVO — semana 6. WTI en $100.\n"
            f"- Inflación energética eurozona: al alza por guerra.\n"
            f"- BCE marzo 2026: adoptó tono MÁS HAWKISH de lo esperado.\n"
            f"- Mercados descuentan 3 subidas de tasas BCE en 2026.\n"
            f"- Tasa depósito BCE actual: 1.93%\n"
            f"- Inflación eurozona 2026: ~2.6% (proyección BCE marzo).\n"
            f"- Crecimiento eurozona 2026: ~0.9% (revisado a la baja).\n"
            f"- Bono 10Y EEUU (referencia): {bono_10y.get('valor', 'N/A')}%\n"
            f"- Contexto FED (régimen): {regimen.get('regimen', 'N/A')}\n"
        )


# ── Prompt FED ────────────────────────────────────────────────────
def construir_prompt_fed(titulo: str, fecha: str,
                          texto: str, contexto_str: str) -> str:
    return (
        "Eres un analista macro senior especializado en política monetaria "
        "de la Reserva Federal. Llevas 20 años interpretando comunicados "
        "del FOMC para un hedge fund macro global.\n\n"
        + contexto_str + "\n"
        "GUÍA DE CLASIFICACIÓN DE TONO:\n"
        "- HAWKISH FUERTE (+3 a +5): inflación persistente preocupante, "
        "mercado laboral sólido, sin señales de recortes próximos.\n"
        "- HAWKISH LEVE (+1 a +2): inflación elevada pero controlada, "
        "datos sólidos, sin urgencia de recortar.\n"
        "- NEUTRO (0): balance perfecto entre riesgos, sin señal clara.\n"
        "- DOVISH LEVE (-1 a -2): enfriamiento económico, inflación "
        "acercándose al objetivo, apertura a recortes.\n"
        "- DOVISH FUERTE (-3 a -5): preocupación por recesión, desempleo "
        "subiendo, señales claras de recortes próximos.\n\n"
        "SEÑALES HAWKISH FED:\n"
        "inflation remains elevated, above the 2 percent objective, "
        "labor market remains strong, higher for longer, "
        "core PCE por encima de 2.5%.\n\n"
        "SEÑALES DOVISH FED:\n"
        "inflation has eased, labor market is cooling, "
        "appropriate to reduce, risks are becoming more balanced.\n\n"
        f"TÍTULO: {titulo}\n"
        f"FECHA: {fecha}\n\n"
        f"TEXTO DEL COMUNICADO:\n{texto}\n\n"
        "Produce un análisis institucional:\n\n"
        "**1. TONO GENERAL**\n"
        "- Clasificación: [HAWKISH FUERTE/HAWKISH LEVE/NEUTRO/DOVISH LEVE/DOVISH FUERTE]\n"
        "- Score: [número de -5 a +5]\n"
        "- Señales hawkish encontradas: [frases clave del texto]\n"
        "- Señales dovish encontradas: [frases clave del texto]\n"
        "- Justificación: [2-3 líneas]\n\n"
        "**2. MENSAJES CLAVE**\n"
        "- Los 3 mensajes más importantes para los mercados\n\n"
        "**3. CAMBIOS RESPECTO AL COMUNICADO ANTERIOR**\n"
        "- Qué lenguaje nuevo aparece\n"
        "- Qué se eliminó o suavizó\n\n"
        "**4. IMPACTO ESPERADO POR ACTIVO**\n"
        "- USD (Dólar):\n"
        "- Bonos del Tesoro UST 10Y:\n"
        "- S&P 500 (SPX):\n"
        "- Nasdaq (NDX):\n"
        "- Oro (Gold):\n"
        "- EUR/USD:\n"
        "- VIX (Volatilidad):\n\n"
        "**5. ESCENARIOS DE MERCADO**\n"
        "ESCENARIO A (probabilidad: X%): [nombre]\n"
        "[descripción]\n\n"
        "ESCENARIO B (probabilidad: X%): [nombre]\n"
        "[descripción]\n\n"
        "ESCENARIO C (probabilidad: X%): [nombre]\n"
        "[descripción]\n\n"
        "**6. VARIABLES CLAVE A MONITOREAR**\n"
        "- Datos próximos relevantes\n"
        "- Declaraciones de miembros del FOMC a seguir\n\n"
        "**7. CONFIDENCE SCORE**\n"
        "- Score: X/100\n"
        "- Factores que reducen la confianza: [lista]\n\n"
        "Responde en español. Sé directo y específico. "
        "Cada afirmación debe tener base en el texto o en el contexto macro."
    )


# ── Prompt BCE ────────────────────────────────────────────────────
def construir_prompt_bce(titulo: str, fecha: str,
                          texto: str, contexto_str: str) -> str:
    return (
        "Eres un analista macro senior especializado en política monetaria "
        "del Banco Central Europeo (BCE). Llevas 20 años interpretando "
        "comunicados del Governing Council para un hedge fund macro global.\n\n"
        + contexto_str + "\n"
        "CONTEXTO CRÍTICO PARA ESTE ANÁLISIS:\n"
        "En marzo 2026, el BCE sorprendió al mercado adoptando un tono "
        "MÁS HAWKISH de lo esperado debido a la guerra en Medio Oriente "
        "y su impacto inflacionario en energía. Los mercados pasaron a "
        "descontar 3 subidas de tasas en 2026 tras este comunicado. "
        "Este es el contexto que debes tener en cuenta para calibrar el tono.\n\n"
        "DIFERENCIAS CLAVE BCE vs FED:\n"
        "- El BCE es más gradual y menos explícito en forward guidance\n"
        "- Muy sensible a fragmentación financiera zona euro\n"
        "- La guerra en Medio Oriente es el factor dominante ahora\n"
        "- 'Data-dependent' en el BCE = sin compromiso de recortar\n"
        "- Un BCE que mantiene tasas CON riesgos inflacionarios = HAWKISH\n\n"
        "GUÍA DE CLASIFICACIÓN DE TONO BCE:\n"
        "- HAWKISH FUERTE (+3 a +5): inflación persistente, posible subida\n"
        "- HAWKISH LEVE (+1 a +2): inflación elevada, sin recortes próximos\n"
        "- NEUTRO (0): balance equilibrado, sin señal clara\n"
        "- DOVISH LEVE (-1 a -2): inflación controlada, apertura a recortes\n"
        "- DOVISH FUERTE (-3 a -5): crecimiento débil, recortes inminentes\n\n"
        "SEÑALES HAWKISH BCE a buscar:\n"
        "'upside risks to inflation', 'war in the Middle East', "
        "'higher energy prices', 'not pre-committing', "
        "'data-dependent', 'inflation above target', "
        "'close monitoring required', 'second-round effects'.\n\n"
        "SEÑALES DOVISH BCE a buscar:\n"
        "'inflation returning to 2%', 'easing monetary conditions', "
        "'supporting the economy', 'downside risks to growth dominant', "
        "'rate cuts appropriate'.\n\n"
        f"TÍTULO: {titulo}\n"
        f"FECHA: {fecha}\n\n"
        f"TEXTO DEL COMUNICADO:\n{texto}\n\n"
        "Produce un análisis institucional:\n\n"
        "**1. TONO GENERAL**\n"
        "- Clasificación: [HAWKISH FUERTE/HAWKISH LEVE/NEUTRO/DOVISH LEVE/DOVISH FUERTE]\n"
        "- Score: [número de -5 a +5]\n"
        "- Señales hawkish encontradas: [frases clave del texto]\n"
        "- Señales dovish encontradas: [frases clave del texto]\n"
        "- Justificación: [2-3 líneas — considera el contexto de la guerra]\n\n"
        "**2. MENSAJES CLAVE**\n"
        "- Los 3 mensajes más importantes para los mercados\n\n"
        "**3. DIVERGENCIA BCE vs FED**\n"
        "- ¿Va el BCE más hawkish o más dovish que la FED?\n"
        "- Implicaciones directas para EUR/USD\n\n"
        "**4. IMPACTO ESPERADO POR ACTIVO**\n"
        "- EUR/USD:\n"
        "- Bund alemán 10Y:\n"
        "- BTP italiano 10Y:\n"
        "- Euro Stoxx 50:\n"
        "- Gold (en EUR):\n"
        "- WTI (impacto energía eurozona):\n"
        "- Spread periferia (Italia vs Alemania):\n\n"
        "**5. ESCENARIOS DE MERCADO**\n"
        "ESCENARIO A (probabilidad: X%): [nombre]\n"
        "[descripción]\n\n"
        "ESCENARIO B (probabilidad: X%): [nombre]\n"
        "[descripción]\n\n"
        "ESCENARIO C (probabilidad: X%): [nombre]\n"
        "[descripción]\n\n"
        "**6. PRÓXIMA REUNIÓN BCE (5 junio 2026)**\n"
        "- Probabilidad de subida: X%\n"
        "- Probabilidad de pausa: X%\n"
        "- Variables clave antes de esa fecha\n\n"
        "**7. CONFIDENCE SCORE**\n"
        "- Score: X/100\n"
        "- Factores que reducen la confianza: [lista]\n\n"
        "Responde en español. Sé directo. "
        "El análisis debe reflejar la realidad del mercado actual."
    )


# ── Función principal ─────────────────────────────────────────────
def analizar_comunicado(comunicado: dict, contexto_macro: dict = None) -> str:
    """
    Analiza un comunicado de banco central con IA.
    Detecta automáticamente si es FED o BCE y aplica el prompt correcto.
    """
    titulo = comunicado["titulo"]
    fecha  = comunicado["fecha"]
    texto  = comunicado.get("contenido") or comunicado.get("texto", "")
    texto_recortado = texto[:6000]

    # ── Detectar banco central ────────────────────────────────────
    banco = detectar_banco(comunicado)

    print(f"🧠 Analizando comunicado con IA...")
    print(f"   Banco:     {banco}")
    print(f"   Documento: {titulo[:70]}")
    print(f"   Fecha:     {fecha}\n")

    # ── Construir contexto y prompt ───────────────────────────────
    contexto_str = construir_contexto_macro(contexto_macro, banco)

    if banco == "FED":
        prompt = construir_prompt_fed(
            titulo, fecha, texto_recortado, contexto_str
        )
        system_msg = (
            "Eres un analista macro senior especializado en política "
            "monetaria de la Reserva Federal. Produces análisis "
            "institucionales rigurosos, directos y accionables."
        )
        nombre_archivo = f"outputs/analisis_fed_{fecha[:3].lower()}.txt"
        header = "KAIROS — ANÁLISIS COMUNICADO FED"
    else:
        prompt = construir_prompt_bce(
            titulo, fecha, texto_recortado, contexto_str
        )
        system_msg = (
            "Eres un analista macro senior especializado en política "
            "monetaria del BCE. Produces análisis institucionales "
            "rigurosos sobre la eurozona, directos y accionables."
        )
        nombre_archivo = f"outputs/analisis_bce_{fecha[:3].lower()}.txt"
        header = "KAIROS — ANÁLISIS COMUNICADO BCE"

    # ── Llamada a la IA ───────────────────────────────────────────
    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.3,
        max_tokens=3000
    )

    analisis = respuesta.choices[0].message.content

    print("=" * 60)
    print(f"📊 {header}")
    print("=" * 60)
    print(analisis)
    print("=" * 60)

    # ── Guardar análisis ──────────────────────────────────────────
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(f"KAIROS — {header}\n")
        f.write("=" * 60 + "\n")
        f.write(f"Documento: {titulo}\n")
        f.write(f"Fecha:     {fecha}\n")
        f.write(f"Banco:     {banco}\n")
        f.write("=" * 60 + "\n\n")
        if contexto_str:
            f.write("CONTEXTO MACRO:\n")
            f.write(contexto_str + "\n\n")
        f.write(analisis)

    print(f"\n💾 Análisis guardado en: {nombre_archivo}")

    return analisis


if __name__ == "__main__":
    import sys
    banco_arg = sys.argv[1].upper() if len(sys.argv) > 1 else "FED"

    if banco_arg == "BCE":
        from bce_scraper import obtener_comunicado_bce
        comunicado = obtener_comunicado_bce(forzar=True)
    else:
        from fed_scraper import obtener_comunicado_fed
        comunicado = obtener_comunicado_fed()

    if comunicado:
        analizar_comunicado(comunicado)
    else:
        print(f"❌ No se pudo obtener el comunicado de {banco_arg}")
