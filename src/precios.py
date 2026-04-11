import yfinance as yf
from datetime import datetime

# Activos que monitorea KAIROS
ACTIVOS = {
    "SPX":   "^GSPC",
    "NDX":   "^NDX",
    "VIX":   "^VIX",
    "Gold":  "GC=F",
    "DXY":   "DX-Y.NYB",
    "EURUSD":"EURUSD=X",
    "UST10Y":"^TNX",
    "WTI":   "CL=F"
}

def obtener_precios():
    """
    Descarga el precio actual y variación diaria
    de los activos clave de KAIROS.
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
                    "direccion":     "▲" if variacion >= 0 else "▼"
                }
            else:
                resultados[nombre] = None

        except Exception as e:
            print(f"   ⚠️ Error obteniendo {nombre}: {e}")
            resultados[nombre] = None

    return resultados


def mostrar_precios(precios):
    """Imprime los precios en formato legible."""
    print(f"\n{'='*55}")
    print(f"  MERCADOS — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*55}")
    print(f"  {'Activo':<10} {'Precio':>10} {'Cambio':>10} {'%':>8}")
    print(f"  {'-'*45}")

    for nombre, datos in precios.items():
        if datos:
            color = datos["direccion"]
            print(
                f"  {nombre:<10}"
                f" {datos['precio']:>10.2f}"
                f" {datos['variacion']:>+10.2f}"
                f" {datos['variacion_pct']:>+7.2f}%"
                f"  {color}"
            )
        else:
            print(f"  {nombre:<10} {'N/A':>10}")

    print(f"{'='*55}\n")


if __name__ == "__main__":
    precios = obtener_precios()
    mostrar_precios(precios)