# price_targets.py — KAIROS
# Motor de predicción de targets de precio.
#
# OBJETIVO: Calcular niveles de precio objetivo para cada activo
# usando análisis combinado de múltiples factores ponderados.
#
# FACTORES:
#   30% — Régimen macro + FED/BCE (hawkish/dovish)
#   25% — Situaciones geopolíticas activas
#   25% — Precedentes históricos (base estadística)
#   20% — Momentum técnico (distancia a niveles clave)
#
# OUTPUTS:
#   • Target diario   (próximas 24h)
#   • Target semanal  (próximos 7 días)
#   • Target mensual  (próximos 30 días)
#   • Rango de confianza
#   • Dirección dominante con probabilidad

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

TARGETS_FILE = "data/price_targets_historico.json"
os.makedirs("data", exist_ok=True)


# ── Niveles técnicos clave por activo ─────────────────────────────
# Actualizar semanalmente — son los niveles macro más importantes
NIVELES_TECNICOS = {
    "SPX": {
        "precio_ref":    7001.91,
        "soporte_1":     6800,     # soporte fuerte
        "soporte_2":     6500,     # soporte crítico
        "resistencia_1": 7200,     # resistencia próxima
        "resistencia_2": 7500,     # resistencia fuerte
        "maximo_52s":    7200,     # máximo 52 semanas
        "minimo_52s":    4800,     # mínimo 52 semanas
        "ma200":         6650,     # media móvil 200 días (estimada)
        "nota":          "Conflicto Irán presiona. Soporte $6800 clave.",
    },
    "NDX": {
        "precio_ref":    26042,
        "soporte_1":     25000,
        "soporte_2":     23500,
        "resistencia_1": 27000,
        "resistencia_2": 28500,
        "maximo_52s":    27500,
        "minimo_52s":    17000,
        "ma200":         24000,
        "nota":          "Alta sensibilidad a tasas. Amplifica SPX x1.3.",
    },
    "Gold": {
        "precio_ref":    4816,
        "soporte_1":     4600,
        "soporte_2":     4300,
        "resistencia_1": 5000,     # nivel psicológico $5000
        "resistencia_2": 5500,
        "maximo_52s":    5000,
        "minimo_52s":    2800,
        "ma200":         4200,
        "nota":          "Refugio activo. Irán + FED hawkish = soporte fuerte.",
    },
    "Silver": {
        "precio_ref":    34.0,
        "soporte_1":     31.0,
        "soporte_2":     28.0,
        "resistencia_1": 36.0,
        "resistencia_2": 40.0,
        "maximo_52s":    38.0,
        "minimo_52s":    22.0,
        "ma200":         29.0,
        "nota":          "Amplifica Gold x1.5. Componente industrial sensible a guerra.",
    },
    "WTI": {
        "precio_ref":    92.1,
        "soporte_1":     85.0,     # soporte si negociaciones avanzan
        "soporte_2":     75.0,     # soporte con resolución Irán
        "resistencia_1": 100.0,    # resistencia psicológica
        "resistencia_2": 110.0,    # nivel de crisis energética
        "maximo_52s":    105.0,
        "minimo_52s":    65.0,
        "ma200":         78.0,
        "nota":          "Irán = clave. Acuerdo → $75-80. Escalada → $100-110.",
    },
    "BTC": {
        "precio_ref":    85000,
        "soporte_1":     80000,
        "soporte_2":     70000,
        "resistencia_1": 90000,
        "resistencia_2": 100000,   # nivel psicológico
        "maximo_52s":    110000,
        "minimo_52s":    50000,
        "ma200":         75000,
        "nota":          "Correlación risk-on. Risk-off → baja con SPX.",
    },
    "DXY": {
        "precio_ref":    98.11,
        "soporte_1":     97.0,
        "soporte_2":     95.0,
        "resistencia_1": 100.0,    # nivel psicológico
        "resistencia_2": 103.0,
        "maximo_52s":    107.0,
        "minimo_52s":    95.0,
        "ma200":         103.0,
        "nota":          "FED hawkish = soporte DXY. Debilitamiento en recortes.",
    },
    "VIX": {
        "precio_ref":    18.17,
        "soporte_1":     15.0,     # VIX bajo = calma
        "soporte_2":     12.0,
        "resistencia_1": 20.0,     # umbral de precaución
        "resistencia_2": 25.0,     # umbral de alerta
        "maximo_52s":    35.0,
        "minimo_52s":    12.0,
        "ma200":         20.0,
        "nota":          "Conflicto Irán mantiene VIX elevado. >25 = riesgo sistémico.",
    },
    "UST10Y": {
        "precio_ref":    4.28,
        "soporte_1":     4.0,      # soporte yield (precio bono sube)
        "soporte_2":     3.5,
        "resistencia_1": 4.5,      # resistencia yield
        "resistencia_2": 5.0,      # nivel crítico para valoraciones
        "maximo_52s":    5.2,
        "minimo_52s":    3.6,
        "ma200":         4.3,
        "nota":          "FED hawkish → yields arriba. >4.5% = presión en SPX/NDX.",
    },
}

# ── Impacto del régimen macro por activo ──────────────────────────
# Basado en histórico de rendimientos por régimen
IMPACTO_REGIMEN = {
    "HAWKISH FUERTE": {
        "SPX":    {"dir": "BAJA",  "pct_24h": -1.5, "pct_7d": -2.8, "pct_30d": -3.5},
        "NDX":    {"dir": "BAJA",  "pct_24h": -2.0, "pct_7d": -3.8, "pct_30d": -4.8},
        "Gold":   {"dir": "BAJA",  "pct_24h": -0.8, "pct_7d": -1.2, "pct_30d": -1.5},
        "Silver": {"dir": "BAJA",  "pct_24h": -1.2, "pct_7d": -1.8, "pct_30d": -2.2},
        "WTI":    {"dir": "MIXTO", "pct_24h": +0.3, "pct_7d": +0.5, "pct_30d": +0.8},
        "BTC":    {"dir": "BAJA",  "pct_24h": -2.5, "pct_7d": -4.0, "pct_30d": -5.0},
        "DXY":    {"dir": "SUBE",  "pct_24h": +0.8, "pct_7d": +1.2, "pct_30d": +1.5},
        "VIX":    {"dir": "SUBE",  "pct_24h": +12,  "pct_7d": +8,   "pct_30d": +5},
        "UST10Y": {"dir": "SUBE",  "pct_24h": +0.10,"pct_7d": +0.15,"pct_30d": +0.20},
    },
    "HAWKISH LEVE": {
        "SPX":    {"dir": "BAJA",  "pct_24h": -0.7, "pct_7d": -1.2, "pct_30d": -1.8},
        "NDX":    {"dir": "BAJA",  "pct_24h": -1.0, "pct_7d": -1.6, "pct_30d": -2.4},
        "Gold":   {"dir": "SUBE",  "pct_24h": +0.3, "pct_7d": +0.8, "pct_30d": +1.5},
        "Silver": {"dir": "SUBE",  "pct_24h": +0.4, "pct_7d": +1.0, "pct_30d": +1.8},
        "WTI":    {"dir": "SUBE",  "pct_24h": +0.5, "pct_7d": +1.0, "pct_30d": +1.5},
        "BTC":    {"dir": "BAJA",  "pct_24h": -1.2, "pct_7d": -2.0, "pct_30d": -2.8},
        "DXY":    {"dir": "SUBE",  "pct_24h": +0.4, "pct_7d": +0.7, "pct_30d": +1.0},
        "VIX":    {"dir": "SUBE",  "pct_24h": +5,   "pct_7d": +3,   "pct_30d": +2},
        "UST10Y": {"dir": "SUBE",  "pct_24h": +0.05,"pct_7d": +0.08,"pct_30d": +0.12},
    },
    "NEUTRO": {
        "SPX":    {"dir": "SUBE",  "pct_24h": +0.5, "pct_7d": +0.8, "pct_30d": +1.5},
        "NDX":    {"dir": "SUBE",  "pct_24h": +0.7, "pct_7d": +1.1, "pct_30d": +2.0},
        "Gold":   {"dir": "SUBE",  "pct_24h": +0.3, "pct_7d": +0.5, "pct_30d": +0.8},
        "Silver": {"dir": "SUBE",  "pct_24h": +0.3, "pct_7d": +0.6, "pct_30d": +1.0},
        "WTI":    {"dir": "MIXTO", "pct_24h": +0.2, "pct_7d": +0.3, "pct_30d": +0.5},
        "BTC":    {"dir": "SUBE",  "pct_24h": +1.0, "pct_7d": +2.0, "pct_30d": +3.5},
        "DXY":    {"dir": "BAJA",  "pct_24h": -0.2, "pct_7d": -0.3, "pct_30d": -0.5},
        "VIX":    {"dir": "BAJA",  "pct_24h": -3,   "pct_7d": -5,   "pct_30d": -4},
        "UST10Y": {"dir": "BAJA",  "pct_24h": -0.03,"pct_7d": -0.05,"pct_30d": -0.08},
    },
    "DOVISH LEVE": {
        "SPX":    {"dir": "SUBE",  "pct_24h": +0.8, "pct_7d": +1.5, "pct_30d": +3.0},
        "NDX":    {"dir": "SUBE",  "pct_24h": +1.2, "pct_7d": +2.2, "pct_30d": +4.0},
        "Gold":   {"dir": "SUBE",  "pct_24h": +1.0, "pct_7d": +2.0, "pct_30d": +3.5},
        "Silver": {"dir": "SUBE",  "pct_24h": +1.4, "pct_7d": +2.8, "pct_30d": +4.8},
        "WTI":    {"dir": "SUBE",  "pct_24h": +0.8, "pct_7d": +1.5, "pct_30d": +2.5},
        "BTC":    {"dir": "SUBE",  "pct_24h": +3.0, "pct_7d": +6.0, "pct_30d": +10.0},
        "DXY":    {"dir": "BAJA",  "pct_24h": -0.5, "pct_7d": -1.0, "pct_30d": -1.8},
        "VIX":    {"dir": "BAJA",  "pct_24h": -8,   "pct_7d": -10,  "pct_30d": -8},
        "UST10Y": {"dir": "BAJA",  "pct_24h": -0.08,"pct_7d": -0.12,"pct_30d": -0.18},
    },
    "DOVISH FUERTE": {
        "SPX":    {"dir": "SUBE",  "pct_24h": +1.5, "pct_7d": +3.0, "pct_30d": +5.5},
        "NDX":    {"dir": "SUBE",  "pct_24h": +2.2, "pct_7d": +4.5, "pct_30d": +7.5},
        "Gold":   {"dir": "SUBE",  "pct_24h": +1.8, "pct_7d": +3.5, "pct_30d": +5.5},
        "Silver": {"dir": "SUBE",  "pct_24h": +2.5, "pct_7d": +5.0, "pct_30d": +8.0},
        "WTI":    {"dir": "SUBE",  "pct_24h": +1.5, "pct_7d": +3.0, "pct_30d": +4.5},
        "BTC":    {"dir": "SUBE",  "pct_24h": +5.0, "pct_7d": +10.0,"pct_30d": +18.0},
        "DXY":    {"dir": "BAJA",  "pct_24h": -1.0, "pct_7d": -2.0, "pct_30d": -3.5},
        "VIX":    {"dir": "BAJA",  "pct_24h": -15,  "pct_7d": -18,  "pct_30d": -15},
        "UST10Y": {"dir": "BAJA",  "pct_24h": -0.15,"pct_7d": -0.25,"pct_30d": -0.40},
    },
}

# ── Impacto geopolítico por situación ─────────────────────────────
IMPACTO_GEOPOLITICO = {
    "CONFLICTO_ARMADO_ACTIVO": {
        "WTI":    {"extra_pct": +8.0,  "descripcion": "Prima de riesgo energético"},
        "Gold":   {"extra_pct": +4.0,  "descripcion": "Demanda de refugio"},
        "Silver": {"extra_pct": +3.0,  "descripcion": "Amplifica Gold"},
        "SPX":    {"extra_pct": -3.0,  "descripcion": "Risk-off"},
        "NDX":    {"extra_pct": -4.0,  "descripcion": "Amplifica SPX"},
        "BTC":    {"extra_pct": -2.5,  "descripcion": "Correlación risk-off"},
        "DXY":    {"extra_pct": +1.5,  "descripcion": "Vuelo al dólar"},
        "VIX":    {"extra_pct": +25.0, "descripcion": "Spike de volatilidad"},
        "UST10Y": {"extra_pct": +0.05, "descripcion": "Yields arriba por inflación energía"},
    },
    "NEGOCIACIONES_EN_CURSO": {
        "WTI":    {"extra_pct": -3.0,  "descripcion": "Reducción prima de riesgo"},
        "Gold":   {"extra_pct": -1.5,  "descripcion": "Reducción demanda refugio"},
        "Silver": {"extra_pct": -1.0,  "descripcion": "Normalización"},
        "SPX":    {"extra_pct": +1.5,  "descripcion": "Alivio geopolítico"},
        "NDX":    {"extra_pct": +2.0,  "descripcion": "Amplifica SPX"},
        "BTC":    {"extra_pct": +2.0,  "descripcion": "Risk-on moderado"},
        "DXY":    {"extra_pct": -0.8,  "descripcion": "Reducción vuelo al dólar"},
        "VIX":    {"extra_pct": -10.0, "descripcion": "Compresión volatilidad"},
    },
    "TENSION_COMERCIAL_ACTIVA": {
        "SPX":    {"extra_pct": -2.0,  "descripcion": "Impacto en earnings"},
        "NDX":    {"extra_pct": -3.0,  "descripcion": "Tech más expuesto a China"},
        "Gold":   {"extra_pct": +1.5,  "descripcion": "Refugio ante incertidumbre"},
        "DXY":    {"extra_pct": +0.5,  "descripcion": "Vuelo al dólar moderado"},
        "BTC":    {"extra_pct": -1.5,  "descripcion": "Risk-off moderado"},
    },
}


# ── Motor de cálculo de targets ───────────────────────────────────
def calcular_targets(activo: str, precio_actual: float,
                      regimen_macro: str = "NEUTRO",
                      tono_fed: str = "NEUTRO",
                      situaciones_activas: list = None) -> dict:
    """
    Calcula targets de precio diario/semanal/mensual para un activo.

    Ponderación:
      30% régimen macro + FED
      25% geopolítica activa
      25% precedentes históricos (en IMPACTO_REGIMEN)
      20% momentum técnico (distancia a niveles clave)

    Returns:
        dict con targets, rangos, dirección y confianza
    """
    if activo not in NIVELES_TECNICOS:
        return {}

    niveles  = NIVELES_TECNICOS[activo]
    impacto  = IMPACTO_REGIMEN.get(tono_fed or regimen_macro, IMPACTO_REGIMEN["NEUTRO"])
    impacto_activo = impacto.get(activo, {"dir":"MIXTO","pct_24h":0,"pct_7d":0,"pct_30d":0})

    # ── Factor 1: Régimen macro (30%) ─────────────────────────────
    pct_24h = impacto_activo["pct_24h"] * 0.30
    pct_7d  = impacto_activo["pct_7d"]  * 0.30
    pct_30d = impacto_activo["pct_30d"] * 0.30

    # ── Factor 2: Geopolítica (25%) ───────────────────────────────
    geo_24h = geo_7d = geo_30d = 0.0
    geo_descripcion = []

    if situaciones_activas:
        for sit in situaciones_activas:
            tipo = sit.get("tipo", "")
            if tipo == "CONFLICTO_ARMADO":
                geo = IMPACTO_GEOPOLITICO["CONFLICTO_ARMADO_ACTIVO"]
            elif tipo == "TENSION_COMERCIAL":
                geo = IMPACTO_GEOPOLITICO["TENSION_COMERCIAL_ACTIVA"]
            else:
                continue

            if activo in geo:
                extra = geo[activo]["extra_pct"]
                geo_24h += extra * 0.10   # máximo impacto en 24h
                geo_7d  += extra * 0.20   # mayor impacto en semana
                geo_30d += extra * 0.25   # máximo impacto en mes
                geo_descripcion.append(geo[activo]["descripcion"])

    pct_24h += geo_24h * 0.25
    pct_7d  += geo_7d  * 0.25
    pct_30d += geo_30d * 0.25

    # ── Factor 3: Precedentes históricos (25%) ────────────────────
    # Ya incluidos en IMPACTO_REGIMEN — el mismo factor 1 usa datos históricos
    # Añadimos volatilidad histórica como rango de confianza
    volatilidad = {
        "SPX": 1.2, "NDX": 1.8, "Gold": 1.0, "Silver": 1.8,
        "WTI": 2.5, "BTC": 4.5, "DXY": 0.5, "VIX": 12.0, "UST10Y": 0.08,
    }.get(activo, 1.5)

    # ── Factor 4: Momentum técnico (20%) ──────────────────────────
    dist_sop1 = ((precio_actual - niveles["soporte_1"]) / precio_actual) * 100
    dist_res1 = ((niveles["resistencia_1"] - precio_actual) / precio_actual) * 100

    # Si el precio está cerca de soporte → tendencia bajista tiene freno
    # Si está cerca de resistencia → tendencia alcista tiene techo
    if dist_sop1 < 3 and pct_24h < 0:
        pct_24h *= 0.6   # soporte amortigua la caída
    if dist_res1 < 3 and pct_24h > 0:
        pct_24h *= 0.6   # resistencia amortigua la subida

    pct_24h *= 1.0   # factor técnico ya aplicado arriba
    pct_7d  *= 1.0
    pct_30d *= 1.0

    # ── Calcular precios objetivo ─────────────────────────────────
    target_24h  = round(precio_actual * (1 + pct_24h / 100), 2)
    target_7d   = round(precio_actual * (1 + pct_7d  / 100), 2)
    target_30d  = round(precio_actual * (1 + pct_30d / 100), 2)

    # Rangos (±1 sigma basado en volatilidad histórica del activo)
    rango_24h = round(precio_actual * volatilidad / 100, 2)
    rango_7d  = round(precio_actual * volatilidad * 2.2 / 100, 2)
    rango_30d = round(precio_actual * volatilidad * 4.5 / 100, 2)

    # Dirección y probabilidad
    dir_dom = impacto_activo["dir"]
    if dir_dom == "MIXTO":
        prob = 50
    elif abs(pct_24h) > volatilidad * 0.5:
        prob = 68   # >1 sigma → 68% probabilidad
    elif abs(pct_24h) > volatilidad * 0.25:
        prob = 58
    else:
        prob = 52

    # Ajustar probabilidad por geopolítica
    if geo_descripcion:
        prob = min(prob + 8, 82)

    # Nivel técnico más relevante
    if pct_24h < 0:
        nivel_clave = {"precio": niveles["soporte_1"], "tipo": "Soporte clave"}
    else:
        nivel_clave = {"precio": niveles["resistencia_1"], "tipo": "Resistencia clave"}

    return {
        "activo":          activo,
        "precio_actual":   precio_actual,
        "direccion":       dir_dom,
        "probabilidad":    prob,

        # Targets
        "target_24h":      target_24h,
        "target_7d":       target_7d,
        "target_30d":      target_30d,

        # Rangos (escenario pesimista/optimista)
        "rango_24h_bajo":  round(target_24h - rango_24h, 2),
        "rango_24h_alto":  round(target_24h + rango_24h, 2),
        "rango_7d_bajo":   round(target_7d  - rango_7d,  2),
        "rango_7d_alto":   round(target_7d  + rango_7d,  2),
        "rango_30d_bajo":  round(target_30d - rango_30d, 2),
        "rango_30d_alto":  round(target_30d + rango_30d, 2),

        # Niveles técnicos
        "soporte_1":       niveles["soporte_1"],
        "resistencia_1":   niveles["resistencia_1"],
        "nivel_clave":     nivel_clave,

        # Contexto
        "regimen":         tono_fed or regimen_macro,
        "geo_factores":    geo_descripcion,
        "nota_tecnica":    niveles["nota"],

        # Cambios esperados en %
        "cambio_pct_24h":  round(pct_24h, 2),
        "cambio_pct_7d":   round(pct_7d,  2),
        "cambio_pct_30d":  round(pct_30d, 2),

        "timestamp":       datetime.now().isoformat(),
    }


def calcular_todos_los_targets(regimen_macro: str = "NEUTRO",
                                 tono_fed: str = "HAWKISH LEVE",
                                 situaciones_activas: list = None) -> dict:
    """
    Calcula targets para todos los activos monitoreados.
    Obtiene precios actuales de yfinance.
    """
    try:
        import yfinance as yf

        tickers = {
            "SPX": "^GSPC", "NDX": "^NDX", "Gold": "GC=F",
            "Silver": "SI=F", "WTI": "CL=F", "BTC": "BTC-USD",
            "DXY": "DX-Y.NYB", "VIX": "^VIX", "UST10Y": "^TNX",
        }

        precios = {}
        for nombre, ticker in tickers.items():
            try:
                info = yf.Ticker(ticker).fast_info
                precio = info.last_price
                if precio:
                    precios[nombre] = round(float(precio), 2)
            except Exception:
                # Usar precio de referencia si falla yfinance
                precios[nombre] = NIVELES_TECNICOS.get(nombre, {}).get("precio_ref", 0)

    except Exception:
        precios = {k: v["precio_ref"] for k, v in NIVELES_TECNICOS.items()}

    targets = {}
    for activo, precio in precios.items():
        if precio and precio > 0:
            targets[activo] = calcular_targets(
                activo, precio, regimen_macro,
                tono_fed, situaciones_activas
            )

    return targets


def guardar_prediccion(targets: dict):
    """Guarda las predicciones para tracking de aciertos."""
    historico = []
    if os.path.exists(TARGETS_FILE):
        try:
            with open(TARGETS_FILE) as f:
                historico = json.load(f)
        except Exception:
            pass

    entrada = {
        "fecha_prediccion": datetime.now().strftime("%Y-%m-%d"),
        "fecha_evaluacion_24h": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "fecha_evaluacion_7d":  (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        "fecha_evaluacion_30d": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "predicciones":         targets,
        "evaluado_24h":         False,
        "evaluado_7d":          False,
        "evaluado_30d":         False,
        "aciertos_24h":         None,
        "aciertos_7d":          None,
    }
    historico.append(entrada)
    historico = historico[-90:]  # Máximo 90 días de historial

    with open(TARGETS_FILE, "w") as f:
        json.dump(historico, f, ensure_ascii=True, indent=2)


def formatear_targets_telegram(targets: dict) -> str:
    """Formatea los targets para el canal Telegram."""
    fecha  = datetime.now().strftime("%d %B %Y")
    lineas = [
        f"🎯 KAIROS — TARGETS DE PRECIO",
        f"{'='*38}",
        f"📅 {fecha}",
        f"",
    ]

    secciones = {
        "📈 ÍNDICES":   ["SPX", "NDX"],
        "💰 METALES":  ["Gold", "Silver"],
        "🛢️ ENERGÍA": ["WTI"],
        "₿ CRYPTO":   ["BTC"],
        "💵 DIVISAS":  ["DXY"],
        "⚡ VOLAT.":   ["VIX"],
    }

    for seccion, activos in secciones.items():
        lineas.append(f"\n{seccion}")
        for nombre in activos:
            t = targets.get(nombre)
            if not t:
                continue

            emoji_dir = "📈" if t["direccion"] == "SUBE" else "📉" if t["direccion"] == "BAJA" else "↔️"
            signo     = "+" if t["cambio_pct_24h"] >= 0 else ""

            lineas += [
                f"  {nombre} — {t['precio_actual']} {emoji_dir} ({t['probabilidad']}%)",
                f"  24h: {t['target_24h']} [{t['rango_24h_bajo']}-{t['rango_24h_alto']}]",
                f"  7d:  {t['target_7d']}  | 30d: {t['target_30d']}",
                f"  🔑 {t['nivel_clave']['tipo']}: {t['nivel_clave']['precio']}",
            ]

    lineas += [
        f"",
        f"⚠️ Targets probabilísticos — no garantizados",
        f"kairos-markets.streamlit.app",
    ]

    return "\n".join(lineas)


def evaluar_aciertos() -> dict:
    """
    Evalúa las predicciones anteriores comparando target vs precio real.
    Actualiza el historial con los resultados.
    """
    if not os.path.exists(TARGETS_FILE):
        return {}

    try:
        import yfinance as yf
        with open(TARGETS_FILE) as f:
            historico = json.load(f)
    except Exception:
        return {}

    hoy = datetime.now().strftime("%Y-%m-%d")
    aciertos_total = {"24h": [], "7d": []}

    for entrada in historico:
        # Evaluar predicciones de 24h
        if not entrada.get("evaluado_24h") and \
           entrada.get("fecha_evaluacion_24h") <= hoy:
            correctas = 0
            total     = 0
            for activo, pred in entrada["predicciones"].items():
                try:
                    tickers = {
                        "SPX":"^GSPC","NDX":"^NDX","Gold":"GC=F",
                        "Silver":"SI=F","WTI":"CL=F","BTC":"BTC-USD",
                        "DXY":"DX-Y.NYB","VIX":"^VIX","UST10Y":"^TNX",
                    }
                    ticker  = tickers.get(activo)
                    if not ticker:
                        continue
                    hist    = yf.Ticker(ticker).history(period="2d")
                    if hist.empty:
                        continue
                    precio_real = float(hist["Close"].iloc[-1])
                    precio_pred = pred["precio_actual"]
                    dir_pred    = pred["direccion"]
                    dir_real    = "SUBE" if precio_real > precio_pred else "BAJA"

                    total += 1
                    if dir_pred == dir_real or dir_pred == "MIXTO":
                        correctas += 1
                except Exception:
                    pass

            if total > 0:
                pct_acierto = round(correctas / total * 100, 1)
                entrada["evaluado_24h"] = True
                entrada["aciertos_24h"] = pct_acierto
                aciertos_total["24h"].append(pct_acierto)

    # Guardar historial actualizado
    with open(TARGETS_FILE, "w") as f:
        json.dump(historico, f, ensure_ascii=True, indent=2)

    # Calcular precisión promedio
    resultado = {}
    if aciertos_total["24h"]:
        resultado["precision_24h_promedio"] = round(
            sum(aciertos_total["24h"]) / len(aciertos_total["24h"]), 1
        )
    if aciertos_total["7d"]:
        resultado["precision_7d_promedio"] = round(
            sum(aciertos_total["7d"]) / len(aciertos_total["7d"]), 1
        )

    return resultado


# ── Targets fusionados: técnico + macro ──────────────────────────
def calcular_targets_fusionados(regimen_macro: str = "NEUTRO",
                                  tono_fed: str = "HAWKISH LEVE",
                                  situaciones_activas: list = None) -> dict:
    """
    Combina análisis técnico real + análisis macro para targets finales.
    El técnico da la dirección del precio.
    El macro da el contexto que amplifica o amortigua.

    Ponderación final:
      40% Análisis técnico (RSI, MACD, EMAs, Bollinger)
      30% Régimen macro + FED/BCE
      20% Geopolítica activa
      10% Precedentes históricos
    """
    # Obtener análisis técnico real
    tecnico = {}
    try:
        from analisis_tecnico import analizar_todos
        print("  Calculando indicadores técnicos...")
        tecnico = analizar_todos()
    except Exception as e:
        print(f"  Técnico no disponible: {e}")

    # Obtener targets macro base
    macro_targets = calcular_todos_los_targets(
        regimen_macro, tono_fed, situaciones_activas
    )

    targets_finales = {}

    for activo, macro_t in macro_targets.items():
        tec = tecnico.get(activo, {})

        if not tec:
            targets_finales[activo] = macro_t
            continue

        precio = macro_t["precio_actual"]

        # ── Fusión de señales ─────────────────────────────────────
        # El técnico da target basado en ATR real
        # El macro ajusta según régimen y geopolítica
        tec_24h = tec.get("target_24h", precio)
        mac_24h = macro_t["target_24h"]
        tec_7d  = tec.get("target_7d",  precio)
        mac_7d  = macro_t["target_7d"]
        tec_30d = tec.get("target_30d", precio)
        mac_30d = macro_t["target_30d"]

        # Ponderación 40% técnico, 60% macro
        target_24h = round(tec_24h * 0.40 + mac_24h * 0.60, 2)
        target_7d  = round(tec_7d  * 0.40 + mac_7d  * 0.60, 2)
        target_30d = round(tec_30d * 0.40 + mac_30d * 0.60, 2)

        # Dirección consolidada
        dir_tec   = tec.get("señal", "NEUTRAL")
        dir_mac   = macro_t["direccion"]
        conf_tec  = tec.get("confianza", 50)
        conf_mac  = macro_t["probabilidad"]

        # Si ambos coinciden — alta confianza
        if dir_tec == "ALCISTA" and dir_mac == "SUBE":
            dir_final  = "SUBE"
            confianza  = min(round((conf_tec + conf_mac) / 2 + 10), 88)
        elif dir_tec == "BAJISTA" and dir_mac == "BAJA":
            dir_final  = "BAJA"
            confianza  = min(round((conf_tec + conf_mac) / 2 + 10), 88)
        elif dir_tec == "NEUTRAL" or dir_mac == "MIXTO":
            dir_final  = "MIXTO"
            confianza  = 50
        else:
            # Conflicto entre técnico y macro — usar el más fuerte
            if conf_tec > conf_mac:
                dir_final = "SUBE" if dir_tec == "ALCISTA" else "BAJA"
                confianza = round(conf_tec * 0.7)
            else:
                dir_final = dir_mac
                confianza = round(conf_mac * 0.7)

        # Rangos usando ATR real
        atr = tec.get("atr", abs(precio * 0.01))
        targets_finales[activo] = {
            **macro_t,
            "target_24h":    target_24h,
            "target_7d":     target_7d,
            "target_30d":    target_30d,
            "direccion":     dir_final,
            "probabilidad":  confianza,

            # Rangos con ATR real
            "rango_24h_bajo": round(target_24h - atr, 2),
            "rango_24h_alto": round(target_24h + atr, 2),
            "rango_7d_bajo":  round(target_7d  - atr * 2, 2),
            "rango_7d_alto":  round(target_7d  + atr * 2, 2),

            # Indicadores técnicos para el dashboard
            "rsi":           tec.get("rsi", 50),
            "macd_cruce":    tec.get("macd_cruce", "NEUTRAL"),
            "soporte_real":  tec.get("soporte", macro_t.get("soporte_1")),
            "resist_real":   tec.get("resistencia", macro_t.get("resistencia_1")),
            "señal_tecnica": tec.get("señal", "NEUTRAL"),
            "confianza_tec": conf_tec,
            "fuente":        "TÉCNICO + MACRO",
        }

    return targets_finales


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🎯 KAIROS — Motor de Targets de Precio")
    print("="*55)

    # Situaciones activas de ejemplo
    situaciones = [
        {"nombre": "Conflicto EEUU-Israel-Irán", "tipo": "CONFLICTO_ARMADO"},
        {"nombre": "Guerra comercial EEUU-China", "tipo": "TENSION_COMERCIAL"},
    ]

    print("\nCalculando targets...")
    print("  Régimen macro: NEUTRO")
    print("  Tono FED:      HAWKISH LEVE")
    print("  Situaciones:   2 activas\n")

    targets = calcular_todos_los_targets(
        regimen_macro="NEUTRO",
        tono_fed="HAWKISH LEVE",
        situaciones_activas=situaciones
    )

    print(f"{'─'*55}")
    print(f"{'Activo':8} {'Precio':>10} {'Dir':>6} {'Prob':>6} "
          f"{'24h':>10} {'7d':>10} {'30d':>10}")
    print(f"{'─'*55}")

    for nombre, t in targets.items():
        emoji = "▲" if t["direccion"]=="SUBE" else "▼" if t["direccion"]=="BAJA" else "↔"
        print(
            f"{nombre:8} {t['precio_actual']:>10} {emoji:>6} "
            f"{t['probabilidad']:>5}% "
            f"{t['target_24h']:>10} {t['target_7d']:>10} {t['target_30d']:>10}"
        )

    print(f"{'─'*55}")

    # Guardar predicción de hoy
    guardar_prediccion(targets)
    print("\n💾 Predicción guardada en data/price_targets_historico.json")
    print("   Se evaluará automáticamente en 24h, 7d y 30d")

    # Mostrar mensaje Telegram
    print("\n" + "="*55)
    print(formatear_targets_telegram(targets))
