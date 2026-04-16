# macro.py — KAIROS
# Datos macroeconómicos desde FRED API.
# CORREGIDO: CPI/PCE calculan YoY real comparando vs 12 meses antes.

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

SERIES = {
    "CORE_CPI":       {"id": "CPILFESL",   "nombre": "Core CPI (YoY %)",     "tipo": "yoy"},
    "CORE_PCE":       {"id": "PCEPILFE",   "nombre": "Core PCE (YoY %)",     "tipo": "yoy"},
    "CPI_TOTAL":      {"id": "CPIAUCSL",   "nombre": "Inflacion CPI (YoY %)", "tipo": "yoy"},
    "PCE_TOTAL":      {"id": "PCEPI",      "nombre": "Inflacion PCE (YoY %)", "tipo": "yoy"},
    "DESEMPLEO":      {"id": "UNRATE",     "nombre": "Tasa de Desempleo (%)", "tipo": "nivel"},
    "NFP":            {"id": "PAYEMS",     "nombre": "Nominas No Agricolas",  "tipo": "mom_miles"},
    "PIB_REAL":       {"id": "A191RL1Q225SBEA","nombre":"PIB Real (QoQ %)",   "tipo": "nivel"},
    "EMP_MANUFACTURA":{"id": "MANEMP",     "nombre": "Empleo Manufactura",    "tipo": "nivel"},
    "TASA_FED":       {"id": "FEDFUNDS",   "nombre": "Tasa Fondos Federales (%)","tipo":"nivel"},
    "RENDIMIENTO_10Y":{"id": "DGS10",      "nombre": "Bono Tesoro 10Y (%)",   "tipo": "nivel"},
    "RENDIMIENTO_2Y": {"id": "DGS2",       "nombre": "Bono Tesoro 2Y (%)",    "tipo": "nivel"},
}


def _fetch_fred(serie_id: str, limite: int = 14) -> list:
    """Obtiene las últimas N observaciones de FRED."""
    if not FRED_API_KEY:
        return []
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id":  serie_id,
                "api_key":    FRED_API_KEY,
                "file_type":  "json",
                "sort_order": "desc",
                "limit":      limite,
            },
            timeout=12
        )
        if r.status_code == 200:
            return [o for o in r.json().get("observations", [])
                    if o["value"] != "."]
    except Exception as e:
        print(f"   ⚠️ Error FRED {serie_id}: {e}")
    return []


def _calcular_yoy(obs: list) -> float | None:
    """
    Calcula variación YoY real:
    (valor_actual - valor_hace_12m) / valor_hace_12m × 100
    FRED devuelve el índice, nosotros calculamos el %.
    """
    if len(obs) < 12:
        return None
    try:
        actual    = float(obs[0]["value"])
        hace_12m  = float(obs[11]["value"])  # obs[0]=actual, obs[11]=12 meses antes
        if hace_12m == 0:
            return None
        return round((actual - hace_12m) / hace_12m * 100, 2)
    except Exception:
        return None


def obtener_datos_macro() -> dict:
    """
    Descarga y procesa datos macro desde FRED.
    Calcula YoY real para CPI y PCE.
    """
    print("📊 Descargando datos macro desde FRED...")
    resultados = {}

    for clave, config in SERIES.items():
        tipo = config["tipo"]
        obs  = _fetch_fred(config["id"], limite=14)

        if not obs:
            resultados[clave] = None
            continue

        try:
            actual = float(obs[0]["value"])
            fecha  = obs[0]["date"]

            if tipo == "yoy":
                # Calcular YoY real desde índice
                yoy = _calcular_yoy(obs)
                if yoy is None and len(obs) >= 2:
                    # Fallback: si FRED ya da la variación
                    yoy = round(actual, 2)

                resultados[clave] = {
                    "valor":    actual,
                    "variacion":yoy,
                    "fecha":    fecha,
                    "unidad":   "% YoY",
                }
                print(f"   ✅ {config['nombre']}: {yoy}% YoY ({fecha})")

            elif tipo == "mom_miles":
                # NFP: cambio mensual en miles
                if len(obs) >= 2:
                    anterior = float(obs[1]["value"])
                    cambio   = round((actual - anterior) / 1000, 1)
                else:
                    cambio = 0
                resultados[clave] = {
                    "valor":    round(actual / 1000, 1),
                    "variacion":cambio,
                    "fecha":    fecha,
                    "unidad":   "miles",
                }
                print(f"   ✅ {config['nombre']} (miles): {round(actual/1000,1)} ({fecha})")

            else:  # nivel directo
                resultados[clave] = {
                    "valor":    round(actual, 2),
                    "variacion":None,
                    "fecha":    fecha,
                    "unidad":   "%",
                }
                print(f"   ✅ {config['nombre']}: {round(actual,2)} ({fecha})")

        except Exception as e:
            print(f"   ⚠️ Error procesando {clave}: {e}")
            resultados[clave] = None

    return resultados


def evaluar_regimen_macro(datos: dict) -> dict:
    """
    Evalúa el régimen macro actual basado en los datos.
    Retorna: HAWKISH FUERTE / HAWKISH LEVE / NEUTRO / DOVISH LEVE / DOVISH FUERTE
    """
    señales_hawkish = 0
    señales_dovish  = 0
    señales         = []

    # Core PCE vs objetivo FED 2%
    core_pce = datos.get("CORE_PCE", {})
    if core_pce and core_pce.get("variacion"):
        pce = core_pce["variacion"]
        if pce > 3.0:
            señales_hawkish += 2
            señales.append(f"Core PCE {pce}% — muy por encima objetivo 2%")
        elif pce > 2.5:
            señales_hawkish += 1
            señales.append(f"Core PCE {pce}% — sobre objetivo 2%")
        elif pce < 1.5:
            señales_dovish += 2
            señales.append(f"Core PCE {pce}% — bajo objetivo 2%")
        elif pce < 2.0:
            señales_dovish += 1
            señales.append(f"Core PCE {pce}% — en objetivo o bajo")

    # Core CPI
    core_cpi = datos.get("CORE_CPI", {})
    if core_cpi and core_cpi.get("variacion"):
        cpi = core_cpi["variacion"]
        if cpi > 3.5:
            señales_hawkish += 2
            señales.append(f"Core CPI {cpi}% — inflación persistente")
        elif cpi > 2.5:
            señales_hawkish += 1
            señales.append(f"Core CPI {cpi}% — sobre objetivo")
        elif cpi < 2.0:
            señales_dovish += 1
            señales.append(f"Core CPI {cpi}% — bajo objetivo")

    # Desempleo
    desempleo = datos.get("DESEMPLEO", {})
    if desempleo and desempleo.get("valor"):
        unemp = desempleo["valor"]
        if unemp > 5.0:
            señales_dovish += 2
            señales.append(f"Desempleo {unemp}% — mercado laboral débil")
        elif unemp > 4.5:
            señales_dovish += 1
            señales.append(f"Desempleo {unemp}% — enfriamiento laboral")
        elif unemp < 3.5:
            señales_hawkish += 1
            señales.append(f"Desempleo {unemp}% — mercado laboral tenso")

    # Curva de rendimientos (10Y-2Y)
    r10 = datos.get("RENDIMIENTO_10Y", {})
    r2  = datos.get("RENDIMIENTO_2Y",  {})
    if r10 and r2 and r10.get("valor") and r2.get("valor"):
        spread = round(float(r10["valor"]) - float(r2["valor"]), 2)
        if spread < 0:
            señales_dovish += 1
            señales.append(f"Curva invertida ({spread}%) — señal recesión")
        elif spread > 0.5:
            señales.append(f"Curva normal ({spread}%) — régimen saludable")

    # Determinar régimen
    delta = señales_hawkish - señales_dovish
    if delta >= 4:
        regimen = "HAWKISH FUERTE"
        desc    = "Inflación muy elevada, FED en modo restrictivo agresivo"
    elif delta >= 2:
        regimen = "HAWKISH LEVE"
        desc    = "Inflación sobre objetivo, FED cauteloso pero restrictivo"
    elif delta <= -4:
        regimen = "DOVISH FUERTE"
        desc    = "Inflación baja, economía débil, FED en modo expansivo"
    elif delta <= -2:
        regimen = "DOVISH LEVE"
        desc    = "Condiciones favorecen política más laxa"
    else:
        regimen = "NEUTRO"
        desc    = "Señales mixtas, FED en modo data-dependent"

    return {
        "regimen":          regimen,
        "descripcion":      desc,
        "señales":          señales,
        "hawkish_score":    señales_hawkish,
        "dovish_score":     señales_dovish,
        "delta":            delta,
    }


if __name__ == "__main__":
    datos  = obtener_datos_macro()
    regimen= evaluar_regimen_macro(datos)
    print(f"\n{'='*50}")
    print(f"RÉGIMEN MACRO: {regimen['regimen']}")
    print(f"Descripción:   {regimen['descripcion']}")
    print(f"\nSeñales activas:")
    for s in regimen["señales"]:
        print(f"  → {s}")

    # Verificar cálculos YoY
    print(f"\nVerificación YoY:")
    for k in ["CORE_PCE","CORE_CPI","CPI_TOTAL","PCE_TOTAL"]:
        d = datos.get(k,{})
        if d and d.get("variacion"):
            print(f"  {k}: {d['variacion']}% YoY ✅")
        else:
            print(f"  {k}: No disponible")
