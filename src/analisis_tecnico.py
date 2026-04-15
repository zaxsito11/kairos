# analisis_tecnico.py — KAIROS
# Análisis técnico real usando datos de yfinance.
# Calcula indicadores reales para mejorar la precisión de targets.
#
# INDICADORES:
#   RSI (14) — sobrecomprado/sobrevendido
#   EMA 20/50/200 — tendencia corto/medio/largo plazo
#   MACD — momentum y señales de cruce
#   Bandas de Bollinger — volatilidad y rangos
#   Soporte/Resistencia — niveles dinámicos reales
#   ATR — rango verdadero promedio (volatilidad)

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

TICKERS = {
    "SPX":    "^GSPC",
    "NDX":    "^NDX",
    "Gold":   "GC=F",
    "Silver": "SI=F",
    "WTI":    "CL=F",
    "BTC":    "BTC-USD",
    "DXY":    "DX-Y.NYB",
    "VIX":    "^VIX",
    "UST10Y": "^TNX",
}


# ── Funciones de cálculo ──────────────────────────────────────────
def calcular_rsi(precios: list, periodo: int = 14) -> float:
    """RSI de Wilder. Retorna valor 0-100."""
    if len(precios) < periodo + 1:
        return 50.0

    cambios = [precios[i] - precios[i-1] for i in range(1, len(precios))]
    ganancias = [max(c, 0) for c in cambios]
    perdidas  = [abs(min(c, 0)) for c in cambios]

    avg_g = sum(ganancias[:periodo]) / periodo
    avg_p = sum(perdidas[:periodo])  / periodo

    for i in range(periodo, len(cambios)):
        avg_g = (avg_g * (periodo - 1) + ganancias[i]) / periodo
        avg_p = (avg_p * (periodo - 1) + perdidas[i])  / periodo

    if avg_p == 0:
        return 100.0
    rs = avg_g / avg_p
    return round(100 - (100 / (1 + rs)), 2)


def calcular_ema(precios: list, periodo: int) -> float:
    """EMA (Media Móvil Exponencial)."""
    if len(precios) < periodo:
        return sum(precios) / len(precios)
    k = 2 / (periodo + 1)
    ema = sum(precios[:periodo]) / periodo
    for p in precios[periodo:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 4)


def calcular_sma(precios: list, periodo: int) -> float:
    """SMA (Media Móvil Simple)."""
    if len(precios) < periodo:
        return sum(precios) / len(precios)
    return round(sum(precios[-periodo:]) / periodo, 4)


def calcular_macd(precios: list) -> dict:
    """MACD (12, 26, 9)."""
    if len(precios) < 26:
        return {"macd": 0, "signal": 0, "histograma": 0, "cruce": "NEUTRAL"}

    ema12   = calcular_ema(precios, 12)
    ema26   = calcular_ema(precios, 26)
    macd    = round(ema12 - ema26, 4)

    # Signal line (EMA 9 del MACD)
    macd_values = []
    for i in range(26, len(precios) + 1):
        e12 = calcular_ema(precios[:i], 12)
        e26 = calcular_ema(precios[:i], 26)
        macd_values.append(e12 - e26)

    signal = round(calcular_ema(macd_values, 9) if len(macd_values) >= 9 else macd, 4)
    histo  = round(macd - signal, 4)

    # Detectar cruce
    cruce = "NEUTRAL"
    if len(macd_values) >= 2:
        if macd_values[-2] < 0 and macd > 0:
            cruce = "CRUCE_ALCISTA"
        elif macd_values[-2] > 0 and macd < 0:
            cruce = "CRUCE_BAJISTA"
        elif macd > signal:
            cruce = "ALCISTA"
        else:
            cruce = "BAJISTA"

    return {"macd": macd, "signal": signal, "histograma": histo, "cruce": cruce}


def calcular_bollinger(precios: list, periodo: int = 20, desv: float = 2.0) -> dict:
    """Bandas de Bollinger."""
    if len(precios) < periodo:
        precio = precios[-1]
        return {"banda_alta": precio, "banda_media": precio,
                "banda_baja": precio, "ancho": 0, "posicion": 0.5}

    ultimos = precios[-periodo:]
    media   = sum(ultimos) / periodo
    varianza= sum((p - media) ** 2 for p in ultimos) / periodo
    std     = varianza ** 0.5

    alta  = round(media + desv * std, 4)
    baja  = round(media - desv * std, 4)
    ancho = round((alta - baja) / media * 100, 2)

    # Posición relativa: 0=banda baja, 1=banda alta
    precio_actual = precios[-1]
    posicion = round((precio_actual - baja) / (alta - baja), 3) if alta != baja else 0.5

    return {
        "banda_alta":   alta,
        "banda_media":  round(media, 4),
        "banda_baja":   baja,
        "ancho":        ancho,
        "posicion":     posicion,  # 0=sobreventa, 1=sobrecompra
    }


def calcular_atr(highs: list, lows: list, closes: list, periodo: int = 14) -> float:
    """ATR (Average True Range) — mide volatilidad real."""
    if len(closes) < 2:
        return 0

    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i]  - closes[i-1])
        )
        tr_list.append(tr)

    if len(tr_list) < periodo:
        return round(sum(tr_list) / len(tr_list), 4)
    return round(sum(tr_list[-periodo:]) / periodo, 4)


def detectar_soporte_resistencia(precios: list, ventana: int = 20) -> dict:
    """Detecta niveles de soporte y resistencia dinámicos."""
    if len(precios) < ventana:
        return {"soporte": min(precios), "resistencia": max(precios)}

    ultimos  = precios[-ventana:]
    maximo   = max(ultimos)
    minimo   = min(ultimos)
    rango    = maximo - minimo
    actual   = precios[-1]

    # Soporte: nivel más cercano por debajo
    soporte     = round(minimo + rango * 0.15, 2)
    resistencia = round(maximo - rango * 0.15, 2)

    # Zona de valor: entre 40%-60% del rango
    zona_valor_bajo = round(minimo + rango * 0.40, 2)
    zona_valor_alto = round(minimo + rango * 0.60, 2)

    return {
        "soporte":        soporte,
        "resistencia":    resistencia,
        "zona_valor_bajo":zona_valor_bajo,
        "zona_valor_alto":zona_valor_alto,
        "en_zona_valor":  zona_valor_bajo <= actual <= zona_valor_alto,
        "distancia_soporte_pct":    round((actual - soporte) / actual * 100, 2),
        "distancia_resistencia_pct":round((resistencia - actual) / actual * 100, 2),
    }


# ── Función principal ─────────────────────────────────────────────
def analizar_activo(nombre: str) -> dict:
    """
    Analiza un activo con todos los indicadores técnicos.
    Retorna señal consolidada: ALCISTA / BAJISTA / NEUTRAL
    con score de confianza 0-100.
    """
    try:
        import yfinance as yf

        ticker = TICKERS.get(nombre)
        if not ticker:
            return {}

        # Descargar 6 meses de datos diarios
        hist = yf.Ticker(ticker).history(period="6mo", interval="1d")
        if hist.empty or len(hist) < 30:
            return {}

        closes = [float(c) for c in hist["Close"].tolist()]
        highs  = [float(h) for h in hist["High"].tolist()]
        lows   = [float(l) for l in hist["Low"].tolist()]

        precio = closes[-1]

        # Calcular todos los indicadores
        rsi   = calcular_rsi(closes, 14)
        ema20 = calcular_ema(closes, 20)
        ema50 = calcular_ema(closes, 50)
        ema200= calcular_ema(closes, 200) if len(closes) >= 200 else calcular_sma(closes, len(closes))
        macd  = calcular_macd(closes)
        boll  = calcular_bollinger(closes, 20)
        atr   = calcular_atr(highs, lows, closes, 14)
        sr    = detectar_soporte_resistencia(closes, 60)

        # ── Señales individuales ──────────────────────────────────
        señales = []
        score_alcista = 0
        score_bajista = 0

        # RSI
        if rsi < 30:
            señales.append(("RSI", "ALCISTA", f"Sobrevendido ({rsi})"))
            score_alcista += 20
        elif rsi > 70:
            señales.append(("RSI", "BAJISTA", f"Sobrecomprado ({rsi})"))
            score_bajista += 20
        elif rsi > 55:
            señales.append(("RSI", "ALCISTA", f"Momentum positivo ({rsi})"))
            score_alcista += 8
        elif rsi < 45:
            señales.append(("RSI", "BAJISTA", f"Momentum negativo ({rsi})"))
            score_bajista += 8

        # EMAs — tendencia
        if precio > ema20 > ema50:
            señales.append(("EMA", "ALCISTA", "Precio > EMA20 > EMA50"))
            score_alcista += 15
        elif precio < ema20 < ema50:
            señales.append(("EMA", "BAJISTA", "Precio < EMA20 < EMA50"))
            score_bajista += 15
        if precio > ema200:
            señales.append(("EMA200", "ALCISTA", f"Precio sobre media 200"))
            score_alcista += 10
        else:
            señales.append(("EMA200", "BAJISTA", f"Precio bajo media 200"))
            score_bajista += 10

        # MACD
        if macd["cruce"] == "CRUCE_ALCISTA":
            señales.append(("MACD", "ALCISTA", "Cruce alcista — momentum cambia"))
            score_alcista += 18
        elif macd["cruce"] == "CRUCE_BAJISTA":
            señales.append(("MACD", "BAJISTA", "Cruce bajista — momentum cambia"))
            score_bajista += 18
        elif macd["cruce"] == "ALCISTA":
            señales.append(("MACD", "ALCISTA", "MACD sobre signal"))
            score_alcista += 8
        elif macd["cruce"] == "BAJISTA":
            señales.append(("MACD", "BAJISTA", "MACD bajo signal"))
            score_bajista += 8

        # Bollinger
        if boll["posicion"] < 0.15:
            señales.append(("BOLLINGER", "ALCISTA", "Cerca de banda baja — rebote probable"))
            score_alcista += 12
        elif boll["posicion"] > 0.85:
            señales.append(("BOLLINGER", "BAJISTA", "Cerca de banda alta — corrección probable"))
            score_bajista += 12

        # Soporte/Resistencia
        if sr["distancia_soporte_pct"] < 2:
            señales.append(("S/R", "ALCISTA", f"Cerca de soporte ({sr['soporte']})"))
            score_alcista += 10
        if sr["distancia_resistencia_pct"] < 2:
            señales.append(("S/R", "BAJISTA", f"Cerca de resistencia ({sr['resistencia']})"))
            score_bajista += 10

        # ── Señal consolidada ─────────────────────────────────────
        total = score_alcista + score_bajista
        if total == 0:
            señal_final = "NEUTRAL"
            confianza   = 50
        elif score_alcista > score_bajista:
            señal_final = "ALCISTA"
            confianza   = min(round(score_alcista / total * 100), 88)
        elif score_bajista > score_alcista:
            señal_final = "BAJISTA"
            confianza   = min(round(score_bajista / total * 100), 88)
        else:
            señal_final = "NEUTRAL"
            confianza   = 50

        # ── Targets técnicos ──────────────────────────────────────
        # Basados en ATR y niveles de soporte/resistencia reales
        atr_pct = (atr / precio) * 100

        if señal_final == "ALCISTA":
            target_24h = round(precio + atr * 0.8, 2)
            target_7d  = round(min(precio + atr * 2.5, sr["resistencia"]), 2)
            target_30d = round(min(precio + atr * 5.0, sr["resistencia"] * 1.05), 2)
        elif señal_final == "BAJISTA":
            target_24h = round(precio - atr * 0.8, 2)
            target_7d  = round(max(precio - atr * 2.5, sr["soporte"]), 2)
            target_30d = round(max(precio - atr * 5.0, sr["soporte"] * 0.95), 2)
        else:
            target_24h = round(precio + atr * 0.3, 2)
            target_7d  = round(precio + atr * 0.5, 2)
            target_30d = round(precio + atr * 1.0, 2)

        return {
            "activo":        nombre,
            "precio":        round(precio, 2),
            "señal":         señal_final,
            "confianza":     confianza,

            # Indicadores
            "rsi":           rsi,
            "ema20":         round(ema20, 2),
            "ema50":         round(ema50, 2),
            "ema200":        round(ema200, 2),
            "macd_cruce":    macd["cruce"],
            "macd_histo":    macd["histograma"],
            "bollinger_pos": boll["posicion"],
            "atr":           round(atr, 4),
            "atr_pct":       round(atr_pct, 2),

            # Niveles
            "soporte":       sr["soporte"],
            "resistencia":   sr["resistencia"],
            "boll_alta":     boll["banda_alta"],
            "boll_baja":     boll["banda_baja"],

            # Targets técnicos
            "target_24h":    target_24h,
            "target_7d":     target_7d,
            "target_30d":    target_30d,

            # Señales individuales
            "señales":       señales,
            "score_alcista": score_alcista,
            "score_bajista": score_bajista,

            "timestamp":     datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"  Error analizando {nombre}: {e}")
        return {}


def analizar_todos() -> dict:
    """Analiza todos los activos monitoreados por KAIROS."""
    print("📊 Analizando indicadores técnicos...")
    resultados = {}
    for nombre in TICKERS:
        print(f"  {nombre}...")
        resultado = analizar_activo(nombre)
        if resultado:
            resultados[nombre] = resultado
    return resultados


def formatear_tecnico_telegram(analisis: dict) -> str:
    """Formatea análisis técnico para Telegram."""
    fecha  = datetime.now().strftime("%d %B %Y")
    lineas = [
        f"📊 KAIROS — ANÁLISIS TÉCNICO",
        f"{'='*38}",
        f"📅 {fecha}",
        f"",
    ]

    secciones = {
        "ÍNDICES":  ["SPX", "NDX"],
        "METALES":  ["Gold", "Silver"],
        "ENERGÍA":  ["WTI"],
        "CRYPTO":   ["BTC"],
        "DIVISAS":  ["DXY"],
    }

    emojis_señal = {
        "ALCISTA": "📈", "BAJISTA": "📉", "NEUTRAL": "↔️"
    }
    emojis_macd = {
        "CRUCE_ALCISTA": "🚀", "CRUCE_BAJISTA": "⬇️",
        "ALCISTA": "▲", "BAJISTA": "▼", "NEUTRAL": "─"
    }

    for seccion, activos in secciones.items():
        lineas.append(f"\n{seccion}")
        for nombre in activos:
            a = analisis.get(nombre)
            if not a:
                continue
            e = emojis_señal.get(a["señal"], "↔️")
            m = emojis_macd.get(a["macd_cruce"], "─")
            rsi_txt = f"RSI:{a['rsi']}"
            if a["rsi"] < 30:   rsi_txt += "🟢"
            elif a["rsi"] > 70: rsi_txt += "🔴"

            lineas += [
                f"  {e} {nombre} {a['precio']} ({a['confianza']}%)",
                f"  {rsi_txt} | MACD:{m} | ATR:{a['atr_pct']}%",
                f"  Sop:{a['soporte']} | Res:{a['resistencia']}",
                f"  T24h:{a['target_24h']} | T7d:{a['target_7d']}",
            ]

    lineas += ["", "kairos-markets.streamlit.app"]
    return "\n".join(lineas)


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n📊 KAIROS — Análisis Técnico Real")
    print("="*55)

    resultados = analizar_todos()

    print(f"\n{'─'*55}")
    print(f"{'Activo':8} {'Precio':>9} {'Señal':>8} {'Conf':>5} "
          f"{'RSI':>6} {'MACD':>12} {'T-24h':>10}")
    print(f"{'─'*55}")

    for nombre, a in resultados.items():
        emoji = "▲" if a["señal"]=="ALCISTA" else "▼" if a["señal"]=="BAJISTA" else "↔"
        print(
            f"{nombre:8} {a['precio']:>9} {emoji:>8} {a['confianza']:>4}% "
            f"{a['rsi']:>6} {a['macd_cruce']:>12} {a['target_24h']:>10}"
        )

    print(f"\n{'─'*55}")
    print("\nSeñales detalladas SPX:")
    if "SPX" in resultados:
        for s in resultados["SPX"]["señales"]:
            emoji = "🟢" if s[1]=="ALCISTA" else "🔴"
            print(f"  {emoji} {s[0]:10} — {s[2]}")
