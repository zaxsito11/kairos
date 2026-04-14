# priced_in.py — KAIROS
# Probabilidades de decisión FED desde CME FedWatch.
# AUTOMATIZADO: cascada CME API → FRED → fallback manual
# Cache de 6h para no sobrecargar APIs.

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
CACHE_FILE   = "data/priced_in_cache.json"
CACHE_HORAS  = 6
TASA_ACTUAL  = 3.625  # actualizar si cambia la tasa FED

# ── Historial de reuniones FOMC (para contexto) ───────────────────
REUNIONES_FOMC = [
    {"fecha":"2025-01-29","tasa_antes":4.375,"tasa_despues":4.375,
     "decision":"PAUSA","sorpresa":False,"prob_pausa_previa":97.3},
    {"fecha":"2025-03-19","tasa_antes":4.375,"tasa_despues":4.375,
     "decision":"PAUSA","sorpresa":False,"prob_pausa_previa":95.1},
    {"fecha":"2025-05-07","tasa_antes":4.375,"tasa_despues":4.375,
     "decision":"PAUSA","sorpresa":False,"prob_pausa_previa":96.2},
    {"fecha":"2025-06-18","tasa_antes":4.375,"tasa_despues":4.125,
     "decision":"RECORTE 25bps","sorpresa":False,"prob_pausa_previa":28.4},
    {"fecha":"2025-07-30","tasa_antes":4.125,"tasa_despues":4.125,
     "decision":"PAUSA","sorpresa":False,"prob_pausa_previa":93.8},
    {"fecha":"2025-09-17","tasa_antes":4.125,"tasa_despues":3.875,
     "decision":"RECORTE 25bps","sorpresa":False,"prob_pausa_previa":31.2},
    {"fecha":"2025-10-29","tasa_antes":3.875,"tasa_despues":3.875,
     "decision":"PAUSA","sorpresa":False,"prob_pausa_previa":94.5},
    {"fecha":"2025-12-10","tasa_antes":3.875,"tasa_despues":3.625,
     "decision":"RECORTE 25bps","sorpresa":False,"prob_pausa_previa":35.8},
    {"fecha":"2026-01-28","tasa_antes":3.625,"tasa_despues":3.625,
     "decision":"PAUSA","sorpresa":False,"prob_pausa_previa":91.2},
    {"fecha":"2026-03-18","tasa_antes":3.625,"tasa_despues":3.625,
     "decision":"PAUSA","sorpresa":False,"prob_pausa_previa":88.7},
]

# ── Próximas reuniones ────────────────────────────────────────────
PROXIMAS_REUNIONES = [
    {"fecha":"2026-05-06","descripcion":"FOMC Mayo 2026"},
    {"fecha":"2026-06-17","descripcion":"FOMC Junio 2026"},
    {"fecha":"2026-07-29","descripcion":"FOMC Julio 2026"},
    {"fecha":"2026-09-16","descripcion":"FOMC Septiembre 2026"},
    {"fecha":"2026-11-04","descripcion":"FOMC Noviembre 2026"},
    {"fecha":"2026-12-16","descripcion":"FOMC Diciembre 2026"},
]


# ── Cache ─────────────────────────────────────────────────────────
def cargar_cache() -> list | None:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        ultima = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
        if datetime.now() - ultima < timedelta(hours=CACHE_HORAS):
            print(f"   📋 Usando cache FedWatch (válido {CACHE_HORAS}h)")
            return data.get("expectativas")
    except Exception:
        pass
    return None


def guardar_cache(expectativas: list):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({
            "timestamp":    datetime.now().isoformat(),
            "expectativas": expectativas,
        }, f, ensure_ascii=False, indent=2)
    print(f"   💾 Cache guardado ({CACHE_HORAS}h)")


# ── Estrategia 1: CME API ─────────────────────────────────────────
def intentar_cme_api() -> list | None:
    try:
        url = "https://www.cmegroup.com/CmeWS/mvc/Probabilities/getFedFundProbabilities"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer":    "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",
            "Accept":     "application/json",
        }
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()
        if not isinstance(data, list) or not data:
            return None

        resultados = []
        for item in data[:3]:
            fecha     = item.get("meetingDate", "")
            probs_raw = item.get("probabilities", [])
            if not fecha:
                continue

            probs = {}
            for p in probs_raw:
                accion = p.get("action", "")
                valor  = float(p.get("probability", 0))
                if accion and valor > 0:
                    probs[accion] = round(valor, 1)

            if not probs:
                continue

            fecha_dt  = datetime.strptime(fecha[:10], "%Y-%m-%d")
            dias      = (fecha_dt - datetime.now()).days
            desc      = next(
                (r["descripcion"] for r in PROXIMAS_REUNIONES
                 if r["fecha"][:7] == fecha[:7]),
                f"FOMC {fecha[:7]}"
            )
            resultados.append({
                "fecha_reunion":         fecha[:10],
                "descripcion":           desc,
                "tasa_actual":           TASA_ACTUAL,
                "probabilidades":        probs,
                "expectativa_dominante": max(probs, key=probs.get),
                "prob_dominante":        max(probs.values()),
                "dias_para_reunion":     dias,
                "fuente":                "CME API",
            })

        if resultados:
            print(f"   ✅ CME API: {len(resultados)} reuniones")
            return resultados

    except Exception as e:
        print(f"   CME API: {e}")

    return None


# ── Estrategia 2: FRED ────────────────────────────────────────────
def intentar_fred() -> list | None:
    if not FRED_API_KEY:
        return None
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id":        "FEDTARMD",
                "api_key":          FRED_API_KEY,
                "file_type":        "json",
                "sort_order":       "desc",
                "limit":            1,
            },
            timeout=10
        )
        if r.status_code == 200:
            obs = r.json().get("observations", [])
            if obs:
                tasa = float(obs[0]["value"])
                diff = tasa - TASA_ACTUAL

                if abs(diff) < 0.05:
                    probs = {"SIN CAMBIO": 80.0, "RECORTE 25bps": 18.0, "SUBIDA 25bps": 2.0}
                elif diff < -0.1:
                    probs = {"RECORTE 25bps": 65.0, "SIN CAMBIO": 30.0, "RECORTE 50bps": 5.0}
                else:
                    probs = {"SUBIDA 25bps": 60.0, "SIN CAMBIO": 35.0, "RECORTE 25bps": 5.0}

                proxima  = PROXIMAS_REUNIONES[0]
                fecha_dt = datetime.strptime(proxima["fecha"], "%Y-%m-%d")
                dias     = (fecha_dt - datetime.now()).days

                print(f"   ✅ FRED: tasa implícita {tasa}%")
                return [{
                    "fecha_reunion":         proxima["fecha"],
                    "descripcion":           proxima["descripcion"],
                    "tasa_actual":           TASA_ACTUAL,
                    "probabilidades":        probs,
                    "expectativa_dominante": max(probs, key=probs.get),
                    "prob_dominante":        max(probs.values()),
                    "dias_para_reunion":     dias,
                    "fuente":                "FRED estimado",
                }]
    except Exception as e:
        print(f"   FRED: {e}")

    return None


# ── Fallback: datos manuales actualizados ─────────────────────────
def obtener_fallback() -> list:
    """
    ⚠️ Actualizar cada semana.
    Última actualización: 13 abril 2026
    Fuente: cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html
    """
    print("   Usando datos manuales CME FedWatch (13 abril 2026)")

    ahora       = datetime.now()
    resultados  = []

    datos_manual = {
        "2026-05": {
            "SIN CAMBIO":    78.4,
            "RECORTE 25bps": 19.8,
            "SUBIDA 25bps":   1.8,
        },
        "2026-06": {
            "SIN CAMBIO":    45.2,
            "RECORTE 25bps": 48.1,
            "RECORTE 50bps":  5.9,
            "SUBIDA 25bps":   0.8,
        },
        "2026-07": {
            "SIN CAMBIO":    38.0,
            "RECORTE 25bps": 52.0,
            "RECORTE 50bps": 10.0,
        },
    }

    for reunion in PROXIMAS_REUNIONES[:3]:
        fecha_dt  = datetime.strptime(reunion["fecha"], "%Y-%m-%d")
        dias      = (fecha_dt - ahora).days
        if dias < 0:
            continue

        clave = reunion["fecha"][:7]
        probs = datos_manual.get(clave, {"SIN CAMBIO": 50.0, "RECORTE 25bps": 50.0})

        resultados.append({
            "fecha_reunion":         reunion["fecha"],
            "descripcion":           reunion["descripcion"],
            "tasa_actual":           TASA_ACTUAL,
            "probabilidades":        probs,
            "expectativa_dominante": max(probs, key=probs.get),
            "prob_dominante":        max(probs.values()),
            "dias_para_reunion":     dias,
            "fuente":                "Manual CME 13-abr-2026",
        })

    return resultados


# ── Función principal ─────────────────────────────────────────────
def obtener_probabilidades_cme() -> list:
    """
    Cascada automática:
    1. Cache (< 6h)
    2. CME API oficial
    3. FRED Fed Funds
    4. Datos manuales
    """
    print("📡 Consultando expectativas del mercado (CME FedWatch)...")

    cached = cargar_cache()
    if cached:
        return cached

    resultado = intentar_cme_api()
    if resultado:
        guardar_cache(resultado)
        return resultado

    resultado = intentar_fred()
    if resultado:
        guardar_cache(resultado)
        return resultado

    resultado = obtener_fallback()
    guardar_cache(resultado)
    return resultado


def calcular_sorpresa(tono_analisis: str, score_analisis: int,
                       expectativas: list) -> dict | None:
    if not expectativas:
        return None

    proxima         = expectativas[0]
    prob_sin_cambio = proxima["probabilidades"].get("SIN CAMBIO", 50)
    prob_recorte    = proxima["probabilidades"].get("RECORTE 25bps", 0)
    prob_subida     = proxima["probabilidades"].get("SUBIDA 25bps", 0)

    if prob_sin_cambio > 60:
        sesgo_mercado     = "NEUTRO"
        confianza_mercado = prob_sin_cambio
    elif prob_recorte > prob_subida:
        sesgo_mercado     = "DOVISH"
        confianza_mercado = prob_recorte
    else:
        sesgo_mercado     = "HAWKISH"
        confianza_mercado = prob_subida

    mapa_tono  = {"HAWKISH FUERTE":2,"HAWKISH LEVE":1,"NEUTRO":0,
                  "DOVISH LEVE":-1,"DOVISH FUERTE":-2}
    mapa_sesgo = {"HAWKISH":1,"NEUTRO":0,"DOVISH":-1}

    delta = mapa_tono.get(tono_analisis,0) - mapa_sesgo.get(sesgo_mercado,0)

    mapeo = {
         2: ("ALTA SORPRESA HAWKISH",    "Movimiento fuerte: DXY sube, SPX baja, bonos caen"),
         1: ("SORPRESA HAWKISH MODERADA","Movimiento moderado: DXY sube, presión en SPX"),
         0: ("SIN SORPRESA — PRICED IN", "Movimiento mínimo — mercado ya lo esperaba"),
        -1: ("SORPRESA DOVISH MODERADA", "Movimiento moderado: DXY baja, SPX sube"),
        -2: ("ALTA SORPRESA DOVISH",     "Movimiento fuerte: DXY baja, bonos suben, SPX sube"),
    }
    nivel, impacto = mapeo.get(delta, ("NEUTRO","Sin impacto claro"))

    return {
        "sesgo_mercado_previo":  sesgo_mercado,
        "confianza_mercado":     confianza_mercado,
        "tono_detectado":        tono_analisis,
        "delta_sorpresa":        delta,
        "nivel_sorpresa":        nivel,
        "impacto_esperado":      impacto,
        "prob_sin_cambio_mayo":  prob_sin_cambio,
        "prob_recorte_mayo":     prob_recorte,
        "dias_proxima_reunion":  proxima.get("dias_para_reunion","N/A"),
        "fuente":                proxima.get("fuente","N/A"),
    }


def mostrar_priced_in(sorpresa: dict, expectativas: list):
    print("\n" + "="*60)
    print("  SCORING DE PRICED-IN")
    print("="*60)

    if expectativas:
        print(f"\n  Fuente: {expectativas[0].get('fuente','N/A')}")
        print(f"\n  HISTORIAL FOMC (últimas reuniones):")
        for r in REUNIONES_FOMC[-4:]:
            icono = "✅" if not r["sorpresa"] else "⚡"
            print(f"  {icono} {r['fecha']}  {r['decision']:20}  "
                  f"Pausa prob previa: {r['prob_pausa_previa']}%")

        print(f"\n  PRÓXIMAS REUNIONES FOMC:")
        for exp in expectativas[:2]:
            print(f"\n  {exp['descripcion']} ({exp['fecha_reunion']}) "
                  f"— {exp['dias_para_reunion']} días")
            for accion, prob in exp["probabilidades"].items():
                barra = "█" * int(prob / 5)
                print(f"    {accion:<22} {prob:>5.1f}%  {barra}")

    if sorpresa:
        print(f"\n  ANÁLISIS DE SORPRESA:")
        print(f"  Sesgo mercado previo: {sorpresa['sesgo_mercado_previo']} "
              f"({sorpresa['confianza_mercado']:.1f}%)")
        print(f"  Tono detectado:       {sorpresa['tono_detectado']}")
        print(f"  Delta sorpresa:       {sorpresa['delta_sorpresa']:+d}")
        print(f"  Nivel:                {sorpresa['nivel_sorpresa']}")
        print(f"  Impacto esperado:     {sorpresa['impacto_esperado']}")
    print("="*60)


if __name__ == "__main__":
    expectativas = obtener_probabilidades_cme()
    sorpresa     = calcular_sorpresa("HAWKISH LEVE", 2, expectativas)
    mostrar_priced_in(sorpresa, expectativas)
