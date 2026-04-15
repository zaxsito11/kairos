# sorpresa_macro.py — KAIROS
# Compara datos reales vs consenso de analistas.
# ⚠️ ACTUALIZAR consensos 24h antes de cada publicación.

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# ══════════════════════════════════════════════════════════════════
# CONSENSOS ACTUALES — ACTUALIZAR ANTES DE CADA PUBLICACIÓN
# ══════════════════════════════════════════════════════════════════
#
# PRÓXIMOS DATOS CRÍTICOS:
#   📅 GDP Q1 2026 (prelim)  — 29 abril 08:30 ET → actualizar 28 abril
#   📅 PCE Marzo             — 30 abril 08:30 ET → actualizar 29 abril
#   📅 NFP Abril             — 2  mayo  08:30 ET → actualizar 1 mayo
#   📅 CPI Abril             — 13 mayo  08:30 ET → actualizar 12 mayo
#
# Fuentes de consenso: Bloomberg, Reuters, Investing.com
# ══════════════════════════════════════════════════════════════════

CONSENSO_ACTUAL = {
    "NFP": {
        "nombre":    "Nóminas No Agrícolas",
        "consenso":  138.0,      # miles de empleos — actualizar
        "unidad":    "miles",
        "fuente":    "Bloomberg consensus 14-abr-2026",
    },
    "DESEMPLEO": {
        "nombre":    "Tasa de Desempleo",
        "consenso":  4.3,        # % — actualizar
        "unidad":    "%",
        "fuente":    "Bloomberg consensus 14-abr-2026",
    },
    "CPI_YOY": {
        "nombre":    "CPI YoY",
        "consenso":  3.1,        # % — CPI Abril actualizar 12 mayo
        "unidad":    "%",
        "fuente":    "Bloomberg consensus 14-abr-2026",
    },
    "CORE_CPI_YOY": {
        "nombre":    "Core CPI YoY",
        "consenso":  2.6,        # % — actualizar
        "unidad":    "%",
        "fuente":    "Bloomberg consensus 14-abr-2026",
    },
    "PCE_YOY": {
        "nombre":    "PCE YoY",
        "consenso":  2.6,        # % — PCE Marzo actualizar 29 abril
        "unidad":    "%",
        "fuente":    "Bloomberg consensus 14-abr-2026",
    },
    "CORE_PCE_YOY": {
        "nombre":    "Core PCE YoY",
        "consenso":  2.7,        # % — actualizar
        "unidad":    "%",
        "fuente":    "Bloomberg consensus 14-abr-2026",
    },
    "GDP_QOQ": {
        "nombre":    "GDP QoQ (preliminar)",
        "consenso":  1.8,        # % anualizado — GDP Q1 actualizar 28 abril
        "unidad":    "%",
        "fuente":    "Bloomberg consensus 14-abr-2026",
    },
}

# ── Umbrales de sorpresa ──────────────────────────────────────────
# Cuánto tiene que desviarse del consenso para ser "sorpresa"
UMBRALES_SORPRESA = {
    "NFP":         15.0,   # miles — >15k vs consenso = sorpresa
    "DESEMPLEO":   0.1,    # puntos porcentuales
    "CPI_YOY":     0.1,    # puntos
    "CORE_CPI_YOY":0.1,
    "PCE_YOY":     0.1,
    "CORE_PCE_YOY":0.1,
    "GDP_QOQ":     0.3,    # puntos — GDP más volátil
}


# ── Obtener dato real desde FRED ──────────────────────────────────
def obtener_dato_fred(serie: str) -> float | None:
    if not FRED_API_KEY:
        return None
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id":  serie,
                "api_key":    FRED_API_KEY,
                "file_type":  "json",
                "sort_order": "desc",
                "limit":      1,
            },
            timeout=10
        )
        if r.status_code == 200:
            obs = r.json().get("observations", [])
            if obs and obs[0]["value"] != ".":
                return float(obs[0]["value"])
    except Exception:
        pass
    return None


# ── Clasificar nivel de sorpresa ──────────────────────────────────
def clasificar_sorpresa(diferencia: float, umbral: float,
                         inverso: bool = False) -> tuple:
    """
    Clasifica el nivel de sorpresa.
    inverso=True para desempleo (subida = malo = hawkish dovish)

    Returns: (nivel, emoji, impacto_macro)
    """
    abs_dif = abs(diferencia)
    es_alto = diferencia > 0 if not inverso else diferencia < 0

    if abs_dif < umbral * 0.5:
        return "EN LÍNEA CON CONSENSO", "⚪", "Impacto mínimo — ya priced-in"

    if abs_dif < umbral:
        if es_alto:
            return "SORPRESA MODERADA HAWKISH", "🟠", "DXY leve alza, SPX leve baja"
        else:
            return "SORPRESA MODERADA DOVISH", "🟡", "DXY leve baja, SPX leve alza"

    if abs_dif < umbral * 2:
        if es_alto:
            return "SORPRESA ALTA HAWKISH", "🔴", "DXY sube, SPX baja, Gold baja"
        else:
            return "SORPRESA ALTA DOVISH", "🟢", "DXY baja, SPX sube, Gold sube"

    if es_alto:
        return "SORPRESA MUY ALTA HAWKISH", "🔴🔴", "Movimiento fuerte: DXY+, SPX-, bonds sell"
    else:
        return "SORPRESA MUY ALTA DOVISH", "🟢🟢", "Rally: SPX+, Gold+, DXY-"


# ── Análisis principal ────────────────────────────────────────────
def analizar_sorpresas_recientes() -> list:
    """
    Compara datos reales de FRED vs consenso.
    Retorna lista de sorpresas para el dashboard y morning brief.
    """
    resultados = []

    SERIES_FRED = {
        "NFP": {
            "serie":   "PAYEMS",
            "clave":   "NFP",
            "inverso": False,
            "transform": lambda x, prev: round((x - prev) / 1000, 1) if prev else x,
        },
        "DESEMPLEO": {
            "serie":   "UNRATE",
            "clave":   "DESEMPLEO",
            "inverso": True,
            "transform": lambda x, prev: x,
        },
        "CORE_CPI_YOY": {
            "serie":   "CPILFESL",
            "clave":   "CORE_CPI_YOY",
            "inverso": False,
            "transform": lambda x, prev: round(((x - prev) / prev) * 100, 2) if prev else x,
        },
        "CORE_PCE_YOY": {
            "serie":   "PCEPILFE",
            "clave":   "CORE_PCE_YOY",
            "inverso": False,
            "transform": lambda x, prev: round(((x - prev) / prev) * 100, 2) if prev else x,
        },
    }

    for nombre_display, config in [
        ("NFP",         {"serie": "PAYEMS",   "clave": "NFP",          "inverso": False}),
        ("Desempleo",   {"serie": "UNRATE",   "clave": "DESEMPLEO",    "inverso": True}),
        ("Core CPI",    {"serie": "CPILFESL", "clave": "CORE_CPI_YOY", "inverso": False}),
        ("Core PCE",    {"serie": "PCEPILFE", "clave": "CORE_PCE_YOY", "inverso": False}),
    ]:
        try:
            clave    = config["clave"]
            consenso = CONSENSO_ACTUAL.get(clave, {})
            if not consenso:
                continue

            # Obtener datos FRED
            r = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id":  config["serie"],
                    "api_key":    FRED_API_KEY,
                    "file_type":  "json",
                    "sort_order": "desc",
                    "limit":      2,
                },
                timeout=10
            )

            if r.status_code != 200:
                continue

            obs = [o for o in r.json().get("observations", [])
                   if o["value"] != "."]
            if not obs:
                continue

            valor_actual = float(obs[0]["value"])
            valor_prev   = float(obs[1]["value"]) if len(obs) > 1 else None

            # Calcular el valor real a comparar
            if clave == "NFP" and valor_prev:
                real = round((valor_actual - valor_prev) / 1000, 1)
            elif clave in ("CORE_CPI_YOY", "CORE_PCE_YOY") and valor_prev:
                real = round(((valor_actual - valor_prev) / valor_prev) * 100, 2)
            else:
                real = round(valor_actual, 2)

            val_consenso = consenso["consenso"]
            diferencia   = round(real - val_consenso, 2)
            umbral       = UMBRALES_SORPRESA.get(clave, 0.1)

            nivel, emoji, impacto = clasificar_sorpresa(
                diferencia, umbral, config["inverso"]
            )

            resultados.append({
                "nombre":     nombre_display,
                "real":       real,
                "consenso":   val_consenso,
                "diferencia": diferencia,
                "unidad":     consenso["unidad"],
                "nivel":      nivel,
                "emoji":      emoji,
                "impacto":    impacto,
                "fuente_consenso": consenso["fuente"],
            })

        except Exception as e:
            print(f"   ⚠️ Error {nombre_display}: {e}")
            continue

    return resultados


def mostrar_sorpresas():
    print(f"\n📊 KAIROS — Sorpresas Macro vs Consenso")
    print(f"{'='*55}")

    sorpresas = analizar_sorpresas_recientes()

    if not sorpresas:
        print("  Sin datos disponibles (verificar FRED_API_KEY)")
        return

    for s in sorpresas:
        signo = "+" if s["diferencia"] > 0 else ""
        print(f"\n  {s['emoji']} {s['nombre']}")
        print(f"     Real:     {s['real']} {s['unidad']}")
        print(f"     Consenso: {s['consenso']} {s['unidad']}")
        print(f"     Diferencia: {signo}{s['diferencia']}")
        print(f"     Nivel: {s['nivel']}")
        print(f"     Impacto: {s['impacto']}")

    print(f"\n{'='*55}")
    print(f"\n⚠️ PRÓXIMOS CONSENSOS A ACTUALIZAR:")
    print(f"  📅 GDP Q1 2026  — 29 abril 08:30 ET — consenso: +1.8% QoQ")
    print(f"  📅 PCE Marzo    — 30 abril 08:30 ET — consenso: 2.6% YoY")
    print(f"  📅 NFP Abril    — 2  mayo  08:30 ET — consenso: 138k")
    print(f"  📅 FOMC Mayo    — 7  mayo  14:00 ET — sin cambio 78.4%")
    print(f"  📅 CPI Abril    — 13 mayo  08:30 ET — consenso: 2.4% YoY")


if __name__ == "__main__":
    mostrar_sorpresas()
