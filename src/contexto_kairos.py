# contexto_kairos.py — KAIROS
# Fuente única de verdad para el contexto del sistema.
# Todos los módulos deben leer el contexto desde aquí.
#
# PROBLEMA QUE RESUELVE:
#   Antes: tono_fed = "HAWKISH LEVE" hardcodeado en 8 archivos
#   Ahora: un solo lugar que determina el contexto real y actual

import os
import json
import glob
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

CONTEXTO_FILE = "data/contexto_actual.json"


# ── Leer tono FED del último análisis real ────────────────────────
def obtener_tono_fed() -> str:
    """
    Lee el tono FED del último análisis guardado en outputs/.
    Fallback: HAWKISH LEVE si no hay análisis reciente.
    """
    # Buscar último análisis FED (no BCE)
    archivos = sorted([
        f for f in glob.glob("outputs/analisis_*.txt")
        if "bce" not in f.lower()
    ], reverse=True)

    if archivos:
        try:
            with open(archivos[0], "r", encoding="utf-8") as f:
                contenido = f.read()
            for tono in ["HAWKISH FUERTE","HAWKISH LEVE","NEUTRO",
                         "DOVISH LEVE","DOVISH FUERTE"]:
                if tono in contenido:
                    # Verificar que el análisis no sea muy viejo (>7 días)
                    fecha_archivo = os.path.getmtime(archivos[0])
                    hace_7d = (datetime.now() - timedelta(days=7)).timestamp()
                    if fecha_archivo > hace_7d:
                        return tono
        except Exception:
            pass

    return "HAWKISH LEVE"  # fallback basado en contexto actual


def obtener_tono_bce() -> str:
    """Lee el tono BCE del último análisis."""
    archivos = sorted([
        f for f in glob.glob("outputs/analisis_*.txt")
        if "bce" in f.lower()
    ], reverse=True)

    if archivos:
        try:
            with open(archivos[0], "r", encoding="utf-8") as f:
                contenido = f.read()
            for tono in ["HAWKISH FUERTE","HAWKISH LEVE","NEUTRO",
                         "DOVISH LEVE","DOVISH FUERTE"]:
                if tono in contenido:
                    return tono
        except Exception:
            pass

    return "HAWKISH LEVE"


# ── Situaciones activas ───────────────────────────────────────────
def obtener_situaciones_activas() -> list:
    """Retorna lista de situaciones geopolíticas activas."""
    try:
        from news_scanner import SITUACIONES_ACTIVAS
        return [
            {
                "nombre": s["nombre"],
                "tipo":   s.get("tipo", inferir_tipo(s["nombre"])),
                "score":  s.get("score_base", 75),
                "nota":   s.get("nota", ""),
            }
            for s in SITUACIONES_ACTIVAS if not s["resuelto"]
        ]
    except Exception:
        return []


def inferir_tipo(nombre: str) -> str:
    """Infiere el tipo de situación desde el nombre."""
    nombre_lower = nombre.lower()
    if any(x in nombre_lower for x in ["guerra","conflicto","militar","iran","irán"]):
        return "CONFLICTO_ARMADO"
    if any(x in nombre_lower for x in ["arancel","comercial","china","tariff"]):
        return "TENSION_COMERCIAL"
    if any(x in nombre_lower for x in ["energía","petroleo","oil","wti","opec"]):
        return "CRISIS_ENERGETICA"
    return "OTRO"


# ── Régimen macro ─────────────────────────────────────────────────
def obtener_regimen_macro() -> dict:
    """Obtiene el régimen macro actual desde datos FRED."""
    try:
        from macro import obtener_datos_macro, evaluar_regimen_macro
        datos   = obtener_datos_macro()
        regimen = evaluar_regimen_macro(datos)
        return regimen
    except Exception:
        return {"regimen": "NEUTRO", "descripcion": "No disponible"}


# ── Función principal: contexto completo ─────────────────────────
def obtener_contexto_completo(usar_cache: bool = True) -> dict:
    """
    Retorna el contexto completo y actualizado de KAIROS.
    Usado por signal_engine, morning_brief, monitor, etc.

    Cache: 1 hora para evitar llamadas repetidas a FRED.
    """
    # Intentar leer cache
    if usar_cache and os.path.exists(CONTEXTO_FILE):
        try:
            with open(CONTEXTO_FILE) as f:
                cache = json.load(f)
            ts = datetime.fromisoformat(cache.get("timestamp","2000-01-01"))
            if datetime.now() - ts < timedelta(hours=1):
                print(f"   📋 Contexto desde cache ({ts.strftime('%H:%M')})")
                return cache
        except Exception:
            pass

    print("   🔄 Actualizando contexto del sistema...")

    tono_fed    = obtener_tono_fed()
    tono_bce    = obtener_tono_bce()
    situaciones = obtener_situaciones_activas()
    regimen     = obtener_regimen_macro()

    # Calcular relevancia de cada factor HOY
    relevancia = calcular_relevancia_factores(
        regimen, tono_fed, situaciones
    )

    contexto = {
        "timestamp":         datetime.now().isoformat(),
        "tono_fed":          tono_fed,
        "tono_bce":          tono_bce,
        "regimen":           regimen,
        "situaciones":       situaciones,
        "relevancia":        relevancia,
        "n_situaciones":     len(situaciones),
        "factor_dominante":  relevancia[0]["factor"] if relevancia else "macro",
    }

    # Guardar cache
    os.makedirs("data", exist_ok=True)
    with open(CONTEXTO_FILE, "w") as f:
        json.dump(contexto, f, ensure_ascii=True, indent=2)

    return contexto


def calcular_relevancia_factores(regimen: dict, tono_fed: str,
                                  situaciones: list) -> list:
    """
    Calcula qué factores son MÁS relevantes HOY para predecir precios.
    La relevancia cambia según el contexto — no es fija.

    Retorna lista ordenada de mayor a menor relevancia.
    """
    factores = []

    # 1. Geopolítica — relevancia por score de situaciones activas
    score_geo = max([s.get("score", 0) for s in situaciones], default=0)
    if score_geo >= 85:
        rel_geo = 95
        desc_geo = "Conflicto armado activo — domina la narrativa del mercado"
    elif score_geo >= 75:
        rel_geo = 80
        desc_geo = "Situación geopolítica relevante — prime al riesgo"
    elif score_geo >= 60:
        rel_geo = 60
        desc_geo = "Tensión geopolítica moderada"
    else:
        rel_geo = 20
        desc_geo = "Sin situaciones geopolíticas relevantes"

    if score_geo > 0:
        factores.append({
            "factor":      "geopolitica",
            "relevancia":  rel_geo,
            "descripcion": desc_geo,
        })

    # 2. FED — relevancia depende de si ya está priced-in
    mapa_rel_fed = {
        "HAWKISH FUERTE": 90,   # sorpresa → alta relevancia
        "HAWKISH LEVE":   50,   # probablemente priced-in
        "NEUTRO":         40,   # mercado no espera sorpresa
        "DOVISH LEVE":    55,
        "DOVISH FUERTE":  85,   # giro dovish es siempre relevante
    }
    rel_fed = mapa_rel_fed.get(tono_fed, 50)

    # Si el tono es LEVE y el mercado espera lo mismo → menos relevante
    try:
        from priced_in import obtener_probabilidades_cme, calcular_sorpresa
        exp      = obtener_probabilidades_cme()
        sorpresa = calcular_sorpresa(tono_fed, 0, exp)
        if sorpresa:
            delta    = abs(sorpresa.get("delta_sorpresa", 0))
            if delta == 0:
                rel_fed = max(rel_fed - 25, 15)  # priced-in → irrelevante
            elif delta >= 2:
                rel_fed = min(rel_fed + 20, 95)  # gran sorpresa → muy relevante
    except Exception:
        pass

    factores.append({
        "factor":      "fed",
        "relevancia":  rel_fed,
        "descripcion": f"FED {tono_fed} — {'ya descontado' if rel_fed < 45 else 'impacto activo'}",
    })

    # 3. Régimen macro — relevancia por intensidad
    delta_macro = abs(regimen.get("delta", 0))
    rel_macro   = min(40 + delta_macro * 15, 85)
    factores.append({
        "factor":      "macro",
        "relevancia":  rel_macro,
        "descripcion": f"Régimen {regimen.get('regimen','NEUTRO')} — "
                       f"score hawkish:{regimen.get('hawkish_score',0)} "
                       f"dovish:{regimen.get('dovish_score',0)}",
    })

    # 4. Técnico — siempre relevante para timing
    factores.append({
        "factor":      "tecnico",
        "relevancia":  70,
        "descripcion": "Análisis técnico — confirma timing y niveles de entrada/salida",
    })

    # Ordenar por relevancia
    return sorted(factores, key=lambda x: x["relevancia"], reverse=True)


# ── Mostrar contexto actual ───────────────────────────────────────
def mostrar_contexto():
    ctx = obtener_contexto_completo(usar_cache=False)

    print(f"\n📊 KAIROS — CONTEXTO ACTUAL")
    print(f"{'='*55}")
    print(f"Timestamp: {ctx['timestamp'][:19]}")
    print(f"Tono FED:  {ctx['tono_fed']}")
    print(f"Tono BCE:  {ctx['tono_bce']}")
    print(f"Régimen:   {ctx['regimen']['regimen']}")

    print(f"\n🌍 Situaciones activas: {ctx['n_situaciones']}")
    for s in ctx['situaciones']:
        print(f"  🔴 {s['nombre']} (score:{s['score']}) tipo:{s['tipo']}")

    print(f"\n📈 RELEVANCIA DE FACTORES HOY:")
    print(f"{'─'*45}")
    for r in ctx['relevancia']:
        barra = "█" * (r['relevancia'] // 10)
        print(f"  {r['factor']:12} {r['relevancia']:3}%  {barra}")
        print(f"              → {r['descripcion'][:50]}")

    print(f"\n⭐ Factor dominante: {ctx['factor_dominante'].upper()}")
    print(f"{'='*55}")


if __name__ == "__main__":
    mostrar_contexto()
