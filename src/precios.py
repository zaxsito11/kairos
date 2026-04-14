# precios.py — KAIROS
# Precios en tiempo real de los principales activos.
# Incluye correlaciones macro para el Morning Brief.

import yfinance as yf
from datetime import datetime

ACTIVOS = {
    # Índices
    "SPX":    "^GSPC",
    "NDX":    "^NDX",
    # Volatilidad
    "VIX":    "^VIX",
    # Metales
    "Gold":   "GC=F",
    "Silver": "SI=F",
    # Energía
    "WTI":    "CL=F",
    # Crypto
    "BTC":    "BTC-USD",
    # Divisas
    "DXY":    "DX-Y.NYB",
    "EURUSD": "EURUSD=X",
    # Bonos
    "UST10Y": "^TNX",
}

# ── Correlaciones macro conocidas ─────────────────────────────────
# Usadas en Morning Brief para alertar sobre movimientos en cadena
CORRELACIONES = {
    "WTI_SUBE": [
        "Gold suele subir (+0.6 correlación) — inflación importada",
        "Silver suele subir (amplifica Gold) — demanda industrial",
        "SPX suele bajar si WTI > $90 — presión en márgenes",
        "BTC suele bajar — risk-off activo",
    ],
    "VIX_SUBE": [
        "SPX suele bajar — presión vendedora",
        "Gold suele subir — demanda de refugio",
        "BTC suele bajar — correlación risk-off",
        "DXY suele subir — vuelo al dólar",
    ],
    "DXY_SUBE": [
        "Gold suele bajar — presión en commodities",
        "Silver suele bajar — amplifica Gold",
        "WTI suele bajar — commodities en USD",
        "EURUSD suele bajar — relación inversa",
    ],
    "GOLD_SUBE": [
        "Silver suele subir (amplifica x1.5) — refugio + industrial",
        "BTC mixto — a veces correlaciona como refugio",
        "DXY suele bajar — relación inversa histórica",
    ],
    "BTC_SUBE": [
        "NDX suele subir — correlación risk-on tecnológico",
        "VIX suele bajar — ambiente de apetito por riesgo",
    ],
}


def obtener_precios() -> dict:
    """
    Descarga precio actual y variación diaria.
    Usa fast_info para velocidad máxima.
    """
    print("📈 Obteniendo precios de mercado...")
    resultados = {}

    for nombre, ticker in ACTIVOS.items():
        try:
            datos = yf.Ticker(ticker)
            info  = datos.fast_info

            precio_actual = info.last_price
            precio_cierre = info.previous_close

            if precio_actual and precio_cierre:
                variacion     = precio_actual - precio_cierre
                variacion_pct = (variacion / precio_cierre) * 100

                resultados[nombre] = {
                    "ticker":        ticker,
                    "precio":        round(precio_actual, 2),
                    "variacion":     round(variacion, 2),
                    "variacion_pct": round(variacion_pct, 2),
                    "direccion":     "▲" if variacion >= 0 else "▼",
                }
            else:
                resultados[nombre] = None

        except Exception as e:
            print(f"   ⚠️ Error {nombre}: {e}")
            resultados[nombre] = None

    return resultados


def detectar_correlaciones_activas(precios: dict) -> list:
    """
    Detecta qué correlaciones están activas basándose
    en los movimientos del día. Usado por morning_brief.py.
    """
    alertas = []
    umbrales = {
        "WTI":  2.0,   # WTI sube >2%
        "VIX":  10.0,  # VIX sube >10%
        "DXY":  0.7,   # DXY sube >0.7%
        "Gold": 1.2,   # Gold sube >1.2%
        "BTC":  3.0,   # BTC sube >3%
    }

    for activo, umbral in umbrales.items():
        datos = precios.get(activo)
        if not datos:
            continue

        pct = datos["variacion_pct"]

        if pct >= umbral:
            clave = f"{activo}_SUBE"
            if clave in CORRELACIONES:
                alertas.append({
                    "activo":       activo,
                    "movimiento":   f"+{round(pct,1)}%",
                    "correlaciones": CORRELACIONES[clave],
                })

    return alertas


def mostrar_precios(precios: dict):
    """Muestra precios en consola."""
    print(f"\n{'='*55}")
    print(f"  MERCADOS — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*55}")
    print(f"  {'Activo':<10} {'Precio':>10} {'Cambio':>10} {'%':>8}")
    print(f"  {'-'*45}")

    for nombre, datos in precios.items():
        if datos:
            print(
                f"  {nombre:<10}"
                f" {datos['precio']:>10.2f}"
                f" {datos['variacion']:>+10.2f}"
                f" {datos['variacion_pct']:>+7.2f}%"
                f"  {datos['direccion']}"
            )
        else:
            print(f"  {nombre:<10} {'N/A':>10}")

    print(f"{'='*55}")

    # Mostrar correlaciones activas
    correlaciones = detectar_correlaciones_activas(precios)
    if correlaciones:
        print(f"\n  🔗 CORRELACIONES ACTIVAS:")
        for c in correlaciones:
            print(f"\n  {c['activo']} {c['movimiento']} → esperar:")
            for efecto in c["correlaciones"][:2]:
                print(f"    • {efecto}")
    print()


if __name__ == "__main__":
    precios = obtener_precios()
    mostrar_precios(precios)
