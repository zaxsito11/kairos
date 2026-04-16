# signal_engine.py — KAIROS
# Motor de convergencia de señales.
#
# PROBLEMA QUE RESUELVE:
#   Antes: técnico dice ALCISTA, macro dice BAJISTA → KAIROS no resuelve
#   Ahora: pondera cada señal, detecta convergencia real, da UN resultado
#
# PRINCIPIO:
#   Solo hay señal cuando MÚLTIPLES factores apuntan en la misma dirección.
#   Cuando hay conflicto → NEUTRO. No alertar ruido.
#
# OUTPUTS:
#   - Dirección: SUBE / BAJA / NEUTRO
#   - Confianza: 0-100 (solo alerta si >60)
#   - Narrativa: por qué se va a mover este activo HOY
#   - Factores convergentes: qué está alineado
#   - Factores en conflicto: qué está en contra

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

# ── Umbrales de confianza ─────────────────────────────────────────
CONFIANZA_MINIMA_ALERTA  = 65  # mínimo para enviar alerta
CONFIANZA_SEÑAL_FUERTE   = 80  # señal muy confiable
CONFIANZA_SEÑAL_MEDIA    = 65  # señal moderada
CONVERGENCIA_MINIMA      = 3   # mínimo de factores alineados para señal

# ── Pesos por factor ──────────────────────────────────────────────
PESOS = {
    "tecnico_rsi":       15,   # RSI sobrecomprado/sobrevendido
    "tecnico_macd":      15,   # MACD cruce o dirección
    "tecnico_ema":       12,   # EMAs alineadas
    "tecnico_bollinger": 10,   # posición en bandas
    "tecnico_volumen":   18,   # volumen confirma o invalida
    "macro_fed":         20,   # tono FED vs expectativa
    "macro_regimen":     15,   # régimen macro general
    "geopolitica":       20,   # situaciones activas
    "historico":         15,   # precedentes similares
    "priced_in":         10,   # sorpresa vs mercado
}

PESO_TOTAL = sum(PESOS.values())  # 150


# ── Evaluadores por factor ────────────────────────────────────────

def evaluar_tecnico(analisis_tec: dict) -> list:
    """
    Convierte indicadores técnicos en señales ponderadas.
    Retorna lista de (factor, dirección, peso, descripción)
    """
    señales = []
    if not analisis_tec:
        return señales

    rsi  = analisis_tec.get("rsi", 50)
    macd = analisis_tec.get("macd_cruce", "NEUTRAL")
    boll = analisis_tec.get("bollinger_pos", 0.5)
    vol  = analisis_tec.get("vol_relativo", 1.0)
    obv  = analisis_tec.get("obv_tendencia", "NEUTRAL")
    ema_señal = analisis_tec.get("señal", "NEUTRAL")

    # RSI
    if rsi <= 30:
        señales.append(("tecnico_rsi", "SUBE", PESOS["tecnico_rsi"],
                        f"RSI {rsi} — sobrevendido extremo, rebote técnico esperado"))
    elif rsi >= 70:
        señales.append(("tecnico_rsi", "BAJA", PESOS["tecnico_rsi"],
                        f"RSI {rsi} — sobrecomprado, corrección técnica esperada"))
    elif rsi >= 60:
        señales.append(("tecnico_rsi", "SUBE", round(PESOS["tecnico_rsi"]*0.5),
                        f"RSI {rsi} — momentum positivo moderado"))
    elif rsi <= 40:
        señales.append(("tecnico_rsi", "BAJA", round(PESOS["tecnico_rsi"]*0.5),
                        f"RSI {rsi} — momentum negativo moderado"))

    # MACD
    if macd == "CRUCE_ALCISTA":
        señales.append(("tecnico_macd", "SUBE", PESOS["tecnico_macd"],
                        "MACD cruce alcista — cambio de momentum confirmado"))
    elif macd == "CRUCE_BAJISTA":
        señales.append(("tecnico_macd", "BAJA", PESOS["tecnico_macd"],
                        "MACD cruce bajista — cambio de momentum confirmado"))
    elif macd == "ALCISTA":
        señales.append(("tecnico_macd", "SUBE", round(PESOS["tecnico_macd"]*0.6),
                        "MACD sobre signal — momentum alcista activo"))
    elif macd == "BAJISTA":
        señales.append(("tecnico_macd", "BAJA", round(PESOS["tecnico_macd"]*0.6),
                        "MACD bajo signal — momentum bajista activo"))

    # EMA
    if ema_señal == "ALCISTA":
        señales.append(("tecnico_ema", "SUBE", PESOS["tecnico_ema"],
                        "Precio sobre EMAs 20/50/200 — tendencia alcista confirmada"))
    elif ema_señal == "BAJISTA":
        señales.append(("tecnico_ema", "BAJA", PESOS["tecnico_ema"],
                        "Precio bajo EMAs — tendencia bajista confirmada"))

    # Bollinger
    if boll <= 0.15:
        señales.append(("tecnico_bollinger", "SUBE", PESOS["tecnico_bollinger"],
                        f"Precio cerca de banda baja Bollinger — rebote probable"))
    elif boll >= 0.85:
        señales.append(("tecnico_bollinger", "BAJA", PESOS["tecnico_bollinger"],
                        f"Precio cerca de banda alta Bollinger — corrección probable"))

    # Volumen + OBV — el más importante (confirma o invalida TODO)
    if vol >= 1.5 and obv == "ACUMULACION":
        señales.append(("tecnico_volumen", "SUBE", PESOS["tecnico_volumen"],
                        f"Volumen {vol:.1f}x + OBV acumulación — institucionales comprando"))
    elif vol >= 1.5 and obv == "DISTRIBUCION":
        señales.append(("tecnico_volumen", "BAJA", PESOS["tecnico_volumen"],
                        f"Volumen {vol:.1f}x + OBV distribución — institucionales vendiendo ⚠️"))
    elif vol < 0.7:
        # Volumen bajo invalida cualquier señal
        señales.append(("tecnico_volumen", "NEUTRO", -PESOS["tecnico_volumen"]//2,
                        f"Volumen {vol:.1f}x — muy bajo, señales técnicas no confiables"))
    elif obv == "ACUMULACION":
        señales.append(("tecnico_volumen", "SUBE", round(PESOS["tecnico_volumen"]*0.6),
                        "OBV en acumulación — presión compradora moderada"))
    elif obv == "DISTRIBUCION":
        señales.append(("tecnico_volumen", "BAJA", round(PESOS["tecnico_volumen"]*0.6),
                        "OBV en distribución — presión vendedora moderada"))

    return señales


def evaluar_macro(regimen: dict, tono_fed: str,
                   sorpresa_priced_in: dict = None) -> list:
    """Convierte régimen macro y FED en señales ponderadas."""
    señales = []
    reg = regimen.get("regimen", "NEUTRO") if regimen else "NEUTRO"

    # Régimen macro
    mapa_regimen = {
        "HAWKISH FUERTE": ("BAJA", PESOS["macro_regimen"],
                           "Régimen HAWKISH FUERTE — presión bajista en activos de riesgo"),
        "HAWKISH LEVE":   ("BAJA", round(PESOS["macro_regimen"]*0.6),
                           "Régimen HAWKISH LEVE — leve presión bajista"),
        "NEUTRO":         ("NEUTRO", 0, "Régimen neutro — sin sesgo macro claro"),
        "DOVISH LEVE":    ("SUBE", round(PESOS["macro_regimen"]*0.6),
                           "Régimen DOVISH LEVE — leve apoyo alcista"),
        "DOVISH FUERTE":  ("SUBE", PESOS["macro_regimen"],
                           "Régimen DOVISH FUERTE — fuerte impulso alcista en riesgo"),
    }
    if reg in mapa_regimen:
        dir_, peso, desc = mapa_regimen[reg]
        if dir_ != "NEUTRO" and peso > 0:
            señales.append(("macro_regimen", dir_, peso, desc))

    # Tono FED vs expectativa del mercado (priced-in)
    if sorpresa_priced_in:
        delta    = sorpresa_priced_in.get("delta_sorpresa", 0)
        nivel    = sorpresa_priced_in.get("nivel_sorpresa", "")
        impacto  = sorpresa_priced_in.get("impacto_esperado", "")
        dias     = sorpresa_priced_in.get("dias_proxima_reunion", 999)

        # Cuanto más cerca el FOMC, más peso tiene esta señal
        factor_tiempo = 1.5 if dias <= 7 else 1.2 if dias <= 14 else 1.0

        if delta >= 2:
            señales.append(("macro_fed", "BAJA",
                            round(PESOS["macro_fed"] * factor_tiempo),
                            f"FED más hawkish que mercado espera — sorpresa hawkish"))
        elif delta <= -2:
            señales.append(("macro_fed", "SUBE",
                            round(PESOS["macro_fed"] * factor_tiempo),
                            f"FED más dovish que mercado espera — sorpresa dovish"))
        elif delta == 1:
            señales.append(("macro_fed", "BAJA",
                            round(PESOS["macro_fed"] * 0.5 * factor_tiempo),
                            f"FED ligeramente más hawkish — presión moderada"))
        elif delta == -1:
            señales.append(("macro_fed", "SUBE",
                            round(PESOS["macro_fed"] * 0.5 * factor_tiempo),
                            f"FED ligeramente más dovish — apoyo moderado"))

    return señales


def evaluar_geopolitica(situaciones: list, activo: str) -> list:
    """Evalúa impacto geopolítico sobre un activo específico."""
    señales = []

    # Mapa de impacto por tipo de situación para cada activo
    IMPACTO_ACTIVOS = {
        "CONFLICTO_ARMADO": {
            "WTI":    ("SUBE", PESOS["geopolitica"],    "Conflicto activo — prima de riesgo energético"),
            "Gold":   ("SUBE", PESOS["geopolitica"],    "Conflicto activo — demanda de refugio"),
            "Silver": ("SUBE", round(PESOS["geopolitica"]*0.8), "Conflicto — sigue a Gold"),
            "DXY":    ("SUBE", round(PESOS["geopolitica"]*0.7), "Vuelo al dólar por conflicto"),
            "SPX":    ("BAJA", PESOS["geopolitica"],    "Risk-off — conflicto armado activo"),
            "NDX":    ("BAJA", PESOS["geopolitica"],    "Risk-off amplificado — tech más sensible"),
            "BTC":    ("BAJA", round(PESOS["geopolitica"]*0.8), "Risk-off — BTC correlaciona"),
            "VIX":    ("SUBE", PESOS["geopolitica"],    "Spike de volatilidad por conflicto"),
            "UST10Y": ("SUBE", round(PESOS["geopolitica"]*0.5), "Yields arriba por inflación energía"),
        },
        "TENSION_COMERCIAL": {
            "SPX":    ("BAJA", round(PESOS["geopolitica"]*0.7), "Aranceles — impacto en earnings"),
            "NDX":    ("BAJA", PESOS["geopolitica"],    "Tech más expuesto — supply chains China"),
            "Gold":   ("SUBE", round(PESOS["geopolitica"]*0.6), "Refugio ante incertidumbre comercial"),
            "DXY":    ("SUBE", round(PESOS["geopolitica"]*0.5), "Vuelo al dólar moderado"),
            "BTC":    ("BAJA", round(PESOS["geopolitica"]*0.5), "Risk-off moderado"),
            "WTI":    ("BAJA", round(PESOS["geopolitica"]*0.4), "Menor demanda por desaceleración"),
            "Silver": ("BAJA", round(PESOS["geopolitica"]*0.5), "Menor demanda industrial"),
        },
    }

    for sit in (situaciones or []):
        tipo  = sit.get("tipo", "")
        score = sit.get("score", sit.get("score_base", 50))

        if tipo not in IMPACTO_ACTIVOS:
            continue

        activos_impacto = IMPACTO_ACTIVOS[tipo]
        if activo not in activos_impacto:
            continue

        dir_, peso_base, desc = activos_impacto[activo]
        # Ajustar peso por intensidad de la situación
        peso = round(peso_base * (score / 100))
        if peso > 0:
            señales.append(("geopolitica", dir_, peso,
                            f"{sit.get('nombre','Situación activa')}: {desc}"))

    return señales


def evaluar_historico(tono_fed: str, activo: str,
                       similares: list = None) -> list:
    """Usa precedentes históricos para evaluar dirección probable."""
    señales = []

    # Promedio histórico por activo y tono FED
    # Basado en los 33 eventos FOMC de historico.py
    HISTORICO_PROMEDIO = {
        "HAWKISH FUERTE": {
            "SPX": -1.5, "NDX": -2.0, "Gold": -0.8, "Silver": -1.2,
            "WTI": +0.3, "BTC": -2.5, "DXY": +0.8, "VIX": +12.0, "UST10Y": +0.10
        },
        "HAWKISH LEVE": {
            "SPX": -0.7, "NDX": -1.0, "Gold": +0.3, "Silver": +0.4,
            "WTI": +0.5, "BTC": -1.2, "DXY": +0.4, "VIX": +5.0, "UST10Y": +0.05
        },
        "NEUTRO": {
            "SPX": +0.5, "NDX": +0.7, "Gold": +0.3, "Silver": +0.3,
            "WTI": +0.2, "BTC": +1.0, "DXY": -0.2, "VIX": -3.0, "UST10Y": -0.03
        },
        "DOVISH LEVE": {
            "SPX": +0.8, "NDX": +1.2, "Gold": +1.0, "Silver": +1.4,
            "WTI": +0.8, "BTC": +3.0, "DXY": -0.5, "VIX": -8.0, "UST10Y": -0.08
        },
        "DOVISH FUERTE": {
            "SPX": +1.5, "NDX": +2.2, "Gold": +1.8, "Silver": +2.5,
            "WTI": +1.5, "BTC": +5.0, "DXY": -1.0, "VIX": -15.0, "UST10Y": -0.15
        },
    }

    hist = HISTORICO_PROMEDIO.get(tono_fed, HISTORICO_PROMEDIO["NEUTRO"])
    cambio = hist.get(activo, 0)

    if abs(cambio) < 0.3:
        return señales  # Señal muy débil — ignorar

    dir_    = "SUBE" if cambio > 0 else "BAJA"
    intensidad = abs(cambio)
    if intensidad >= 1.5:
        peso = PESOS["historico"]
    elif intensidad >= 0.7:
        peso = round(PESOS["historico"] * 0.7)
    else:
        peso = round(PESOS["historico"] * 0.4)

    n_similares = len(similares) if similares else 0
    desc = (f"Precedente histórico ({tono_fed}): "
            f"{'+' if cambio>0 else ''}{cambio}% promedio en {n_similares} casos similares")
    señales.append(("historico", dir_, peso, desc))

    return señales


# ── Motor de convergencia principal ──────────────────────────────
def calcular_señal_convergente(activo: str,
                                analisis_tec: dict = None,
                                regimen: dict = None,
                                tono_fed: str = "NEUTRO",
                                situaciones: list = None,
                                sorpresa_priced_in: dict = None,
                                similares: list = None) -> dict:
    """
    Calcula la señal convergente para un activo.
    Combina técnico + macro + geopolítica + histórico.
    Solo da señal cuando hay convergencia real.

    Returns:
        dict con:
          - direccion: SUBE / BAJA / NEUTRO
          - confianza: 0-100
          - nivel: FUERTE / MEDIA / DÉBIL / NEUTRO
          - factores_a_favor: lista de señales alineadas
          - factores_en_contra: lista de señales opuestas
          - narrativa: por qué se moverá así HOY
          - accionable: True si confianza > umbral
    """
    todas_señales = []

    # Recopilar señales de cada factor
    if analisis_tec:
        todas_señales += evaluar_tecnico(analisis_tec)
    todas_señales += evaluar_macro(regimen, tono_fed, sorpresa_priced_in)
    todas_señales += evaluar_geopolitica(situaciones, activo)
    todas_señales += evaluar_historico(tono_fed, activo, similares)

    if not todas_señales:
        return _resultado_neutro(activo, "Sin señales disponibles")

    # Separar por dirección
    señales_sube  = [(f,p,d) for f,dir_,p,d in todas_señales if dir_=="SUBE"   and p>0]
    señales_baja  = [(f,p,d) for f,dir_,p,d in todas_señales if dir_=="BAJA"   and p>0]
    señales_neutro= [(f,p,d) for f,dir_,p,d in todas_señales if dir_=="NEUTRO"]

    peso_sube = sum(p for _,p,_ in señales_sube)
    peso_baja = sum(p for _,p,_ in señales_baja)

    # Aplicar penalización por señales neutras (volumen bajo, etc.)
    penalizacion = sum(abs(p) for _,_,p,_ in todas_señales if p < 0)
    peso_sube = max(0, peso_sube - penalizacion//2)
    peso_baja = max(0, peso_baja - penalizacion//2)

    total = peso_sube + peso_baja
    if total == 0:
        return _resultado_neutro(activo, "Señales se cancelan mutuamente")

    # Determinar dirección dominante
    if peso_sube > peso_baja:
        dir_dom     = "SUBE"
        señales_a_favor   = señales_sube
        señales_en_contra = señales_baja
        peso_dom    = peso_sube
    else:
        dir_dom     = "BAJA"
        señales_a_favor   = señales_baja
        señales_en_contra = señales_sube
        peso_dom    = peso_baja

    # Confianza: % del peso total que apoya la dirección dominante
    # Penalizar si hay muchas señales en contra
    ratio_a_favor   = peso_dom / total
    n_a_favor       = len(señales_a_favor)
    n_en_contra     = len(señales_en_contra)

    # Confianza base
    confianza_base = round(ratio_a_favor * 100)

    # Ajustar por convergencia
    if n_a_favor >= 5 and n_en_contra <= 1:
        # Alta convergencia → subir confianza
        confianza = min(confianza_base + 15, 92)
    elif n_a_favor >= 3 and n_en_contra <= 2:
        # Convergencia moderada
        confianza = min(confianza_base + 5, 88)
    elif n_en_contra >= n_a_favor:
        # Muchas señales en contra → reducir confianza
        confianza = max(confianza_base - 20, 30)
    else:
        confianza = confianza_base

    # Si hay señal de volumen bajo → reducir confianza
    if any(p < 0 for _,_,p,_ in todas_señales):
        confianza = max(confianza - 10, 30)

    # Determinar nivel
    if confianza >= CONFIANZA_SEÑAL_FUERTE:
        nivel = "FUERTE"
    elif confianza >= CONFIANZA_SEÑAL_MEDIA:
        nivel = "MEDIA"
    elif confianza >= 50:
        nivel = "DÉBIL"
    else:
        return _resultado_neutro(activo,
            f"Confianza insuficiente ({confianza}%) — señales contradictorias")

    # ¿Es accionable?
    accionable = confianza >= CONFIANZA_MINIMA_ALERTA and n_a_favor >= CONVERGENCIA_MINIMA

    return {
        "activo":            activo,
        "direccion":         dir_dom,
        "confianza":         confianza,
        "nivel":             nivel,
        "accionable":        accionable,
        "peso_a_favor":      peso_dom,
        "peso_en_contra":    peso_baja if dir_dom=="SUBE" else peso_sube,
        "n_factores_a_favor":n_a_favor,
        "n_factores_contra": n_en_contra,
        "factores_a_favor":  [(f,d) for f,_,d in señales_a_favor],
        "factores_en_contra":[(f,d) for f,_,d in señales_en_contra],
        "todas_señales":     todas_señales,
        "timestamp":         datetime.now().isoformat(),
    }


def _resultado_neutro(activo: str, razon: str) -> dict:
    return {
        "activo":            activo,
        "direccion":         "NEUTRO",
        "confianza":         0,
        "nivel":             "NEUTRO",
        "accionable":        False,
        "peso_a_favor":      0,
        "peso_en_contra":    0,
        "n_factores_a_favor":0,
        "n_factores_contra": 0,
        "factores_a_favor":  [],
        "factores_en_contra":[],
        "razon_neutro":      razon,
        "timestamp":         datetime.now().isoformat(),
    }


# ── Narrativa con IA ──────────────────────────────────────────────
def generar_narrativa(activo: str, señal: dict,
                       precio_actual: float,
                       target_24h: float = None) -> str:
    """
    Genera explicación en lenguaje natural de POR QUÉ
    el activo se va a mover en esa dirección HOY.
    Usa IA solo cuando la señal es accionable.
    """
    if not señal.get("accionable"):
        return ""

    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        dir_     = señal["direccion"]
        confianza= señal["confianza"]
        nivel    = señal["nivel"]
        a_favor  = "\n".join([f"  + {d}" for _,d in señal["factores_a_favor"][:4]])
        en_contra= "\n".join([f"  - {d}" for _,d in señal["factores_en_contra"][:2]])
        target   = f"Target 24h: {target_24h}" if target_24h else ""

        prompt = f"""Eres el analista de KAIROS. Explica en 2-3 líneas concisas 
por qué {activo} va a {dir_} hoy con {confianza}% de confianza.

Precio actual: {precio_actual}
{target}
Señal nivel: {nivel}

Factores a favor ({dir_}):
{a_favor}

Factores en contra:
{en_contra}

Responde en español. Máximo 60 palabras. 
Directo, sin introducción. Solo la razón específica de HOY.
No menciones porcentajes de confianza. 
Si hay señal de volumen/OBV, menciónala como la más importante."""

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.3,
            max_tokens=150
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        # Fallback sin IA
        a_favor_txt = señal["factores_a_favor"][0][1] if señal["factores_a_favor"] else ""
        return f"{activo} {dir_}: {a_favor_txt[:80]}"


# ── Análisis completo de todos los activos ────────────────────────
def analizar_mercado_completo(regimen: dict = None,
                               tono_fed: str = "NEUTRO",
                               situaciones: list = None,
                               generar_narrativas: bool = True) -> dict:
    """
    Analiza todos los activos con el motor de convergencia.
    Solo reporta activos ACCIONABLES.
    """
    from analisis_tecnico import analizar_todos
    from price_targets    import calcular_targets_fusionados, guardar_prediccion
    from historico        import encontrar_similares

    print("🔍 Analizando mercado con motor de convergencia...")

    # 1. Análisis técnico
    print("  [1/4] Indicadores técnicos...")
    tecnico_todos = analizar_todos()

    # 2. Priced-in
    print("  [2/4] Priced-in CME FedWatch...")
    sorpresa_pi = None
    try:
        from priced_in import obtener_probabilidades_cme, calcular_sorpresa
        exp = obtener_probabilidades_cme()
        sorpresa_pi = calcular_sorpresa(tono_fed, 0, exp)
    except Exception:
        pass

    # 3. Precedentes
    print("  [3/4] Precedentes históricos...")
    similares = []
    try:
        similares = encontrar_similares(tono_fed, 0, n=5)
    except Exception:
        pass

    # 4. Convergencia por activo
    print("  [4/4] Calculando convergencia...")
    resultados     = {}
    accionables    = []

    activos = ["SPX","NDX","Gold","Silver","WTI","BTC","DXY","VIX","UST10Y"]

    for activo in activos:
        tec = tecnico_todos.get(activo, {})
        precio = tec.get("precio", 0)

        señal = calcular_señal_convergente(
            activo        = activo,
            analisis_tec  = tec,
            regimen       = regimen,
            tono_fed      = tono_fed,
            situaciones   = situaciones,
            sorpresa_priced_in = sorpresa_pi,
            similares     = similares,
        )

        # Obtener target
        target_24h = None
        try:
            from price_targets import calcular_targets
            t = calcular_targets(activo, precio, 
                                  regimen.get("regimen","NEUTRO") if regimen else "NEUTRO",
                                  tono_fed, situaciones)
            target_24h = t.get("target_24h")
        except Exception:
            pass

        # Narrativa solo para accionables
        narrativa = ""
        if señal.get("accionable") and generar_narrativas and precio > 0:
            narrativa = generar_narrativa(activo, señal, precio, target_24h)

        señal["narrativa"]  = narrativa
        señal["precio"]     = precio
        señal["target_24h"] = target_24h
        resultados[activo]  = señal

        if señal.get("accionable"):
            accionables.append(activo)

    return {
        "timestamp":   datetime.now().isoformat(),
        "tono_fed":    tono_fed,
        "n_accionables": len(accionables),
        "accionables": accionables,
        "señales":     resultados,
    }


def formatear_señales_telegram(analisis: dict) -> str:
    """
    Formatea las señales accionables para el canal Telegram.
    Solo incluye activos con señal convergente real.
    """
    if not analisis.get("accionables"):
        return ""

    fecha   = datetime.now().strftime("%d %B %Y %H:%M")
    lineas  = [
        f"🎯 KAIROS — SEÑALES CONVERGENTES",
        f"{'='*38}",
        f"📅 {fecha}",
        f"",
    ]

    señales = analisis.get("señales", {})
    niveles = {"FUERTE": "🔴", "MEDIA": "🟡", "DÉBIL": "⚪"}

    for activo in analisis.get("accionables", []):
        s     = señales.get(activo, {})
        dir_  = s.get("direccion", "NEUTRO")
        conf  = s.get("confianza", 0)
        nivel = s.get("nivel", "")
        narrv = s.get("narrativa", "")
        t24h  = s.get("target_24h")
        precio= s.get("precio", 0)
        n_af  = s.get("n_factores_a_favor", 0)
        emoji_dir = "📈" if dir_=="SUBE" else "📉"
        emoji_niv = niveles.get(nivel, "⚪")

        lineas.append(f"{emoji_dir} {activo} {dir_} — {conf}% {emoji_niv} {nivel}")
        if precio and t24h:
            lineas.append(f"   Precio: {precio} → Target 24h: {t24h}")
        if narrv:
            lineas.append(f"   {narrv}")
        lineas.append(f"   ({n_af} factores convergentes)")
        lineas.append("")

    lineas += [
        f"Solo se muestran activos con señal convergente.",
        f"kairos-markets.streamlit.app",
    ]
    return "\n".join(lineas)


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🎯 KAIROS — Motor de Convergencia de Señales")
    print("="*55)
    print("Cargando contexto del sistema...")

    regimen    = {"regimen": "NEUTRO", "descripcion": "Régimen mixto actual"}
    tono_fed   = "HAWKISH LEVE"
    situaciones= [
        {"nombre": "Conflicto EEUU-Israel-Irán",
         "tipo":   "CONFLICTO_ARMADO", "score": 88},
        {"nombre": "Guerra comercial EEUU-China",
         "tipo":   "TENSION_COMERCIAL", "score": 78},
    ]

    try:
        from macro import obtener_datos_macro, evaluar_regimen_macro
        datos_macro = obtener_datos_macro()
        regimen     = evaluar_regimen_macro(datos_macro)
        print(f"  Régimen: {regimen.get('regimen')}")
    except Exception as e:
        print(f"  Macro: {e}")

    resultado = analizar_mercado_completo(
        regimen            = regimen,
        tono_fed           = tono_fed,
        situaciones        = situaciones,
        generar_narrativas = True,
    )

    print(f"\n{'='*55}")
    print(f"RESULTADOS — {resultado['n_accionables']} señales accionables")
    print(f"{'='*55}\n")

    señales = resultado.get("señales", {})
    for activo, s in señales.items():
        dir_  = s.get("direccion","NEUTRO")
        conf  = s.get("confianza",0)
        nivel = s.get("nivel","NEUTRO")
        acc   = "✅ ACCIONABLE" if s.get("accionable") else "⚫ neutro"
        emoji = "📈" if dir_=="SUBE" else "📉" if dir_=="BAJA" else "↔️"

        print(f"{emoji} {activo:8} {dir_:6} {conf:3}% [{nivel:6}] {acc}")
        if s.get("accionable"):
            for _,desc in s.get("factores_a_favor",[])[:3]:
                print(f"         ✓ {desc[:65]}")
            for _,desc in s.get("factores_en_contra",[])[:1]:
                print(f"         ✗ {desc[:65]}")
            if s.get("narrativa"):
                print(f"         💬 {s['narrativa']}")
            if s.get("target_24h"):
                print(f"         🎯 Target 24h: {s['target_24h']}")
        print()

    if resultado.get("accionables"):
        print("\n" + "="*55)
        print(formatear_señales_telegram(resultado))
