# analisis_fundamental.py — KAIROS
# Análisis fundamental puro: macro, geopolítica, política, FED/BCE,
# decisiones corporativas, acuerdos comerciales.
#
# OBJETIVO: Determinar el SESGO DIRECCIONAL basado en eventos del mundo real.
# NO mezcla con técnico. Su output es:
#   - Sesgo: ALCISTA / BAJISTA / NEUTRO por activo
#   - Narrativa: por qué ese activo se moverá en esa dirección
#   - Confianza: basada en la solidez de los eventos detectados
#   - Horizonte: cuánto tiempo durará el impacto (horas / días / semanas)

import os, sys, json
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Tipos de eventos por categoría ───────────────────────────────
CATEGORIAS_EVENTOS = {
    "BANCO_CENTRAL": {
        "descripcion": "Decisiones FED/BCE/BoJ — tasas, QE, forward guidance",
        "ejemplos":    ["Fed sube tasas", "BCE pausa", "Powell hawkish"],
        "horizonte":   "días-semanas",
        "activos_primarios": ["DXY","UST10Y","SPX","NDX","Gold"],
    },
    "GEOPOLITICA_CONFLICTO": {
        "descripcion": "Guerras, conflictos armados, ataques, bloqueos militares",
        "ejemplos":    ["Ataque Irán", "Bloqueo Ormuz", "Invasión"],
        "horizonte":   "horas-días (ventana activa mientras dure)",
        "activos_primarios": ["WTI","Gold","VIX","SPX"],
    },
    "COMERCIO_ARANCELES": {
        "descripcion": "Aranceles, sanciones, guerras comerciales, acuerdos",
        "ejemplos":    ["Aranceles Trump", "Sanciones Rusia", "Acuerdo EEUU-China"],
        "horizonte":   "días-semanas",
        "activos_primarios": ["SPX","NDX","DXY","BTC"],
    },
    "MACRO_DATO": {
        "descripcion": "GDP, CPI, NFP, PCE — datos económicos vs consenso",
        "ejemplos":    ["CPI supera consenso", "NFP decepciona", "GDP negativo"],
        "horizonte":   "horas-días",
        "activos_primarios": ["DXY","UST10Y","SPX","Gold"],
    },
    "ENERGIA": {
        "descripcion": "OPEC, bloqueos, crisis energética, producción",
        "ejemplos":    ["OPEC recorta", "Bloqueo Ormuz", "Descubrimiento gas"],
        "horizonte":   "días-semanas",
        "activos_primarios": ["WTI","Gold","Silver","SPX"],
    },
    "CORPORATIVO": {
        "descripcion": "Decisiones de grandes compañías con impacto macro",
        "ejemplos":    ["Apple bate earnings", "Tesla recall masivo", "Amazon despidos"],
        "horizonte":   "horas-días",
        "activos_primarios": ["NDX","SPX"],
    },
    "POLITICO": {
        "descripcion": "Elecciones, cambios de gobierno, decisiones presidenciales",
        "ejemplos":    ["Trump gana elección", "Gobierno colapsa", "Decreto ejecutivo"],
        "horizonte":   "días-semanas",
        "activos_primarios": ["DXY","SPX","BTC","Gold"],
    },
    "ACUERDO_PAZ": {
        "descripcion": "Acuerdos comerciales, paz, normalización diplomática",
        "ejemplos":    ["EEUU-China firman acuerdo", "Cese al fuego Irán"],
        "horizonte":   "horas-días (reversión de prima de riesgo)",
        "activos_primarios": ["WTI","Gold","VIX","SPX"],
    },
}

# ── Impacto por categoría y activo ────────────────────────────────
IMPACTO_FUNDAMENTAL = {
    "BANCO_CENTRAL": {
        "HAWKISH": {
            "SPX":    ("BAJISTA", 0.75, "Tasas altas → valuaciones bajo presión"),
            "NDX":    ("BAJISTA", 0.80, "Tech más sensible a tasas — múltiplos comprimidos"),
            "Gold":   ("BAJISTA", 0.60, "Tasas reales altas → costo de oportunidad Gold"),
            "DXY":    ("ALCISTA", 0.80, "Tasas altas → dólar atractivo"),
            "UST10Y": ("ALCISTA", 0.85, "Yields suben con expectativas hawkish"),
            "BTC":    ("BAJISTA", 0.70, "Risk-off + costo de oportunidad"),
        },
        "DOVISH": {
            "SPX":    ("ALCISTA", 0.75, "Tasas bajas → valuaciones se expanden"),
            "NDX":    ("ALCISTA", 0.80, "Tech lidera rally dovish"),
            "Gold":   ("ALCISTA", 0.80, "Tasas reales bajas → Gold brilla"),
            "DXY":    ("BAJISTA", 0.75, "Dólar pierde atractivo"),
            "UST10Y": ("BAJISTA", 0.85, "Yields bajan con expectativas dovish"),
            "BTC":    ("ALCISTA", 0.70, "Risk-on + liquidez"),
        },
    },
    "GEOPOLITICA_CONFLICTO": {
        "ESCALADA": {
            "WTI":    ("ALCISTA", 0.90, "Prima de riesgo energético directa"),
            "Gold":   ("ALCISTA", 0.85, "Refugio seguro clásico"),
            "Silver": ("ALCISTA", 0.75, "Sigue a Gold + demanda industrial defensiva"),
            "VIX":    ("ALCISTA", 0.90, "Volatilidad spike garantizado"),
            "SPX":    ("BAJISTA", 0.80, "Risk-off — salida de riesgo"),
            "NDX":    ("BAJISTA", 0.80, "Tech cae más en risk-off"),
            "BTC":    ("BAJISTA", 0.65, "Correlación risk-off moderada"),
            "DXY":    ("ALCISTA", 0.75, "Vuelo al dólar"),
        },
        "DESESCALADA": {
            "WTI":    ("BAJISTA", 0.85, "Reversión de prima de riesgo"),
            "Gold":   ("BAJISTA", 0.75, "Reducción demanda refugio"),
            "VIX":    ("BAJISTA", 0.85, "Compresión volatilidad"),
            "SPX":    ("ALCISTA", 0.75, "Risk-on — regreso al mercado"),
            "NDX":    ("ALCISTA", 0.75, "Tech rebota en risk-on"),
            "BTC":    ("ALCISTA", 0.65, "Risk-on moderado"),
        },
    },
    "COMERCIO_ARANCELES": {
        "ESCALADA": {
            "SPX":    ("BAJISTA", 0.75, "Impacto en earnings corporativos"),
            "NDX":    ("BAJISTA", 0.80, "Tech más expuesto — supply chains China"),
            "Gold":   ("ALCISTA", 0.65, "Refugio ante incertidumbre"),
            "DXY":    ("ALCISTA", 0.60, "Dólar como refugio moderado"),
            "BTC":    ("BAJISTA", 0.55, "Risk-off moderado"),
        },
        "ACUERDO": {
            "SPX":    ("ALCISTA", 0.80, "Certeza comercial → expansión valuaciones"),
            "NDX":    ("ALCISTA", 0.85, "Tech más beneficiado — normalización cadenas"),
            "Gold":   ("BAJISTA", 0.55, "Menor necesidad de refugio"),
        },
    },
    "ENERGIA": {
        "RECORTE_OFERTA": {
            "WTI":    ("ALCISTA", 0.90, "Menos oferta → precio sube"),
            "Gold":   ("ALCISTA", 0.70, "Inflación importada → hedge"),
            "Silver": ("ALCISTA", 0.65, "Amplifica Gold"),
            "SPX":    ("BAJISTA", 0.60, "Energía cara → costos corporativos"),
        },
        "AUMENTO_OFERTA": {
            "WTI":    ("BAJISTA", 0.90, "Más oferta → precio baja"),
            "SPX":    ("ALCISTA", 0.50, "Costos energía menores"),
        },
    },
}


def analizar_evento_fundamental(evento: str, categoria: str = None,
                                  subtipo: str = None) -> dict:
    """
    Analiza un evento específico y determina su impacto fundamental
    en cada activo. Usa IA para interpretar el evento en contexto.
    """
    # Determinar categoría si no se especifica
    if not categoria:
        categoria, subtipo = detectar_categoria_evento(evento)

    # Obtener impacto base desde el mapa
    impacto_base = {}
    if categoria in IMPACTO_FUNDAMENTAL and subtipo in IMPACTO_FUNDAMENTAL[categoria]:
        impacto_base = IMPACTO_FUNDAMENTAL[categoria][subtipo]

    # Usar IA para análisis contextualizado
    activos_str = ", ".join(CATEGORIAS_EVENTOS.get(categoria, {})
                            .get("activos_primarios", ["SPX","Gold","DXY"]))

    prompt = f"""Eres el analista fundamental de KAIROS Markets.
Tu tarea: analizar este evento y su impacto directo en los precios de mercado.

EVENTO: {evento}
CATEGORÍA: {categoria} — {subtipo}

Analiza el impacto en estos activos: {activos_str}

Para cada activo responde con este formato EXACTO (JSON):
{{
  "sesgo_por_activo": {{
    "SPX": {{"direccion": "ALCISTA/BAJISTA/NEUTRO", "confianza": 0-100, "razon": "max 40 palabras", "horizonte": "horas/días/semanas"}},
    "NDX": {{...}},
    "Gold": {{...}},
    "WTI": {{...}},
    "DXY": {{...}},
    "BTC": {{...}},
    "VIX": {{...}}
  }},
  "narrativa_evento": "Explicación del evento en 2-3 líneas. Qué pasó, por qué importa, qué mueve.",
  "factor_dominante": "El activo más afectado y por qué",
  "ventana_oportunidad": "Cuánto tiempo dura la ventana antes de que el mercado lo descuente"
}}

Responde SOLO con el JSON. Sin explicaciones adicionales."""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres analista fundamental senior. Responde solo en JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=800
        )
        texto = resp.choices[0].message.content.strip()
        # Limpiar markdown si viene con ```json
        if "```" in texto:
            texto = texto.split("```")[1].replace("json","").strip()
        analisis_ia = json.loads(texto)
    except Exception as e:
        print(f"  IA: {e} — usando impacto base")
        analisis_ia = _generar_analisis_base(impacto_base, evento, categoria)

    return {
        "evento":       evento,
        "categoria":    categoria,
        "subtipo":      subtipo,
        "analisis_ia":  analisis_ia,
        "impacto_base": impacto_base,
        "timestamp":    datetime.now().isoformat(),
    }


def _generar_analisis_base(impacto_base: dict, evento: str,
                            categoria: str) -> dict:
    """Fallback sin IA usando el mapa de impacto base."""
    sesgo = {}
    for activo, (dir_, conf, razon) in impacto_base.items():
        sesgo[activo] = {
            "direccion": dir_, "confianza": round(conf*100),
            "razon": razon, "horizonte": "días"
        }
    return {
        "sesgo_por_activo":     sesgo,
        "narrativa_evento":     f"Evento de {categoria}: {evento[:80]}",
        "factor_dominante":     list(impacto_base.keys())[0] if impacto_base else "SPX",
        "ventana_oportunidad":  "horas-días",
    }


def detectar_categoria_evento(evento: str) -> tuple:
    """Detecta automáticamente la categoría de un evento."""
    evento_lower = evento.lower()

    # Banco central
    if any(x in evento_lower for x in ["fed","fomc","powell","bce","lagarde",
                                         "rate","tasas","hawkish","dovish","monetary"]):
        subtipo = "HAWKISH" if any(x in evento_lower for x in
                   ["hike","sube","hawkish","restrictive","inflation high"]) else "DOVISH"
        return "BANCO_CENTRAL", subtipo

    # Conflicto
    if any(x in evento_lower for x in ["war","guerra","attack","ataque","strike","military",
                                         "iran","israel","nuclear","sanctions","bloqueo"]):
        subtipo = "ESCALADA" if any(x in evento_lower for x in
                   ["attack","ataque","escalation","strike","invasion"]) else "DESESCALADA"
        return "GEOPOLITICA_CONFLICTO", subtipo

    # Comercio
    if any(x in evento_lower for x in ["tariff","arancel","trade war","sanctions","embargo",
                                         "china","agreement","deal","acuerdo"]):
        subtipo = "ACUERDO" if any(x in evento_lower for x in
                   ["deal","acuerdo","agreement","peace","reducción"]) else "ESCALADA"
        return "COMERCIO_ARANCELES", subtipo

    # Energía
    if any(x in evento_lower for x in ["opec","oil","petróleo","energy","gas","wti",
                                         "pipeline","refinery"]):
        subtipo = "RECORTE_OFERTA" if any(x in evento_lower for x in
                   ["cut","recorte","reducción","bloqueo","sanction"]) else "AUMENTO_OFERTA"
        return "ENERGIA", subtipo

    # Macro datos
    if any(x in evento_lower for x in ["cpi","pce","nfp","gdp","unemployment",
                                         "inflation","jobs","economic"]):
        return "MACRO_DATO", "SORPRESA_HAWKISH"

    # Político
    if any(x in evento_lower for x in ["election","trump","president","government",
                                         "congress","senate","decreto","policy"]):
        return "POLITICO", "INCERTIDUMBRE"

    return "MACRO_DATO", "NEUTRAL"


def analizar_contexto_fundamental_completo() -> dict:
    """
    Analiza el contexto fundamental completo del momento actual.
    Combina: situaciones activas + FED/BCE + datos macro recientes.
    """
    from contexto_kairos import obtener_contexto_completo
    from news_scanner    import SITUACIONES_ACTIVAS

    ctx = obtener_contexto_completo()
    sits = [s for s in SITUACIONES_ACTIVAS if not s["resuelto"]]

    resultados = {
        "timestamp":    datetime.now().isoformat(),
        "tono_fed":     ctx.get("tono_fed","NEUTRO"),
        "regimen":      ctx.get("regimen",{}),
        "situaciones":  [],
        "sesgo_global": {},  # sesgo consolidado por activo
    }

    # Analizar cada situación activa
    for sit in sits:
        evento = sit["nombre"] + " — " + sit.get("nota","")
        analisis = analizar_evento_fundamental(evento)
        resultados["situaciones"].append({
            "situacion": sit["nombre"],
            "analisis":  analisis,
        })

    # Consolidar sesgo global por activo
    activos = ["SPX","NDX","Gold","Silver","WTI","BTC","DXY","VIX","UST10Y"]
    for activo in activos:
        votos_alcista = 0
        votos_bajista = 0
        razones       = []

        for sit in resultados["situaciones"]:
            sesgo = sit["analisis"]["analisis_ia"].get("sesgo_por_activo",{})
            if activo in sesgo:
                s = sesgo[activo]
                conf = s.get("confianza",50) / 100
                if s.get("direccion") == "ALCISTA":
                    votos_alcista += conf
                    razones.append(s.get("razon",""))
                elif s.get("direccion") == "BAJISTA":
                    votos_bajista += conf
                    razones.append(s.get("razon",""))

        total = votos_alcista + votos_bajista
        if total == 0:
            resultados["sesgo_global"][activo] = {
                "direccion": "NEUTRO", "confianza": 0, "razones": []
            }
        elif votos_alcista > votos_bajista:
            resultados["sesgo_global"][activo] = {
                "direccion": "ALCISTA",
                "confianza": round(votos_alcista/total*100),
                "razones":   razones[:2],
            }
        else:
            resultados["sesgo_global"][activo] = {
                "direccion": "BAJISTA",
                "confianza": round(votos_bajista/total*100),
                "razones":   razones[:2],
            }

    return resultados


if __name__ == "__main__":
    print("\n🌍 KAIROS — Análisis Fundamental")
    print("="*55)

    # Test con evento real
    eventos_test = [
        "US and Iran reach preliminary ceasefire agreement — oil prices drop",
        "Fed Chair Powell signals rates will stay higher for longer due to inflation",
        "Trump announces 25% tariffs on Chinese electronics starting next month",
    ]

    for ev in eventos_test:
        print(f"\nEvento: {ev[:60]}...")
        cat, sub = detectar_categoria_evento(ev)
        print(f"Categoría: {cat} / {sub}")
        resultado = analizar_evento_fundamental(ev, cat, sub)
        sesgo = resultado["analisis_ia"].get("sesgo_por_activo", {})
        for activo, s in list(sesgo.items())[:4]:
            emoji = "📈" if s.get("direccion")=="ALCISTA" else "📉" if s.get("direccion")=="BAJISTA" else "↔️"
            print(f"  {emoji} {activo:8}: {s.get('direccion','?'):8} ({s.get('confianza',0)}%) — {s.get('razon','')[:50]}")
        print(f"  Ventana: {resultado['analisis_ia'].get('ventana_oportunidad','N/A')}")
