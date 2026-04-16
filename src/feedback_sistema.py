# feedback_sistema.py — KAIROS
# Sistema automático de evaluación de aciertos.
# Compara predicciones guardadas vs precios reales.
# Reporta precisión al canal Telegram.
#
# FLUJO:
#   1. Cada día a las 4:15 PM — evalúa predicciones de 24h anteriores
#   2. Cada lunes — evalúa predicciones de 7 días anteriores
#   3. Acumula estadísticas de precisión por activo y por factor
#   4. Alimenta el proceso de calibración continua

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

TARGETS_FILE  = "data/price_targets_historico.json"
FEEDBACK_FILE = "data/feedback_estadisticas.json"
LOG_FILE      = "outputs/feedback.log"

os.makedirs("data",    exist_ok=True)
os.makedirs("outputs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("KAIROS.feedback")


# ── Obtener precio real desde yfinance ───────────────────────────
def obtener_precio_real(activo: str) -> float | None:
    """Obtiene el precio de cierre más reciente."""
    try:
        import yfinance as yf
        tickers = {
            "SPX": "^GSPC", "NDX": "^NDX", "Gold": "GC=F",
            "Silver": "SI=F", "WTI": "CL=F", "BTC": "BTC-USD",
            "DXY": "DX-Y.NYB", "VIX": "^VIX", "UST10Y": "^TNX",
        }
        ticker = tickers.get(activo)
        if not ticker:
            return None
        info = yf.Ticker(ticker).fast_info
        return float(info.last_price)
    except Exception as e:
        log.warning(f"  Error precio {activo}: {e}")
        return None


# ── Evaluar predicción individual ─────────────────────────────────
def evaluar_prediccion(pred: dict, precio_real: float) -> dict:
    """
    Evalúa si la predicción fue correcta.
    Criterios:
      DIRECCIÓN: ¿subió o bajó en la dirección predicha?
      RANGO:     ¿el precio real cayó dentro del rango predicho?
      TARGET:    ¿qué tan cerca estuvo el precio del target?
    """
    precio_base = pred.get("precio_actual", 0)
    dir_pred    = pred.get("direccion", "MIXTO")
    target_24h  = pred.get("target_24h", precio_base)
    rango_bajo  = pred.get("rango_24h_bajo", precio_base * 0.98)
    rango_alto  = pred.get("rango_24h_alto", precio_base * 1.02)

    if precio_base == 0:
        return {"valido": False}

    # Dirección real
    dir_real   = "SUBE" if precio_real > precio_base else "BAJA" if precio_real < precio_base else "MIXTO"
    cambio_pct = round((precio_real - precio_base) / precio_base * 100, 2)

    # Acierto de dirección
    if dir_pred == "MIXTO":
        acierto_dir = True   # MIXTO siempre cuenta como correcto
        desc_dir    = "MIXTO — no evaluable"
    elif dir_pred == dir_real:
        acierto_dir = True
        desc_dir    = f"✅ CORRECTO — predicho {dir_pred}, real {dir_real} ({cambio_pct:+.2f}%)"
    else:
        acierto_dir = False
        desc_dir    = f"❌ INCORRECTO — predicho {dir_pred}, real {dir_real} ({cambio_pct:+.2f}%)"

    # Acierto de rango
    en_rango     = rango_bajo <= precio_real <= rango_alto
    desc_rango   = (f"✅ En rango [{rango_bajo}-{rango_alto}]"
                    if en_rango else
                    f"❌ Fuera de rango [{rango_bajo}-{rango_alto}]")

    # Error del target
    error_target = round(abs(precio_real - target_24h) / precio_base * 100, 2)
    desc_target  = f"Error target: {error_target:.2f}%"

    return {
        "valido":       True,
        "precio_base":  precio_base,
        "precio_real":  precio_real,
        "cambio_pct":   cambio_pct,
        "dir_pred":     dir_pred,
        "dir_real":     dir_real,
        "acierto_dir":  acierto_dir,
        "en_rango":     en_rango,
        "error_target": error_target,
        "target_24h":   target_24h,
        "desc_dir":     desc_dir,
        "desc_rango":   desc_rango,
        "desc_target":  desc_target,
    }


# ── Cargar estadísticas acumuladas ────────────────────────────────
def cargar_estadisticas() -> dict:
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "total_evaluaciones":  0,
        "aciertos_dir_24h":    0,
        "precision_dir_24h":   0.0,
        "aciertos_rango_24h":  0,
        "precision_rango_24h": 0.0,
        "error_target_avg":    0.0,
        "por_activo":          {},
        "historial":           [],
        "ultima_evaluacion":   None,
    }


def guardar_estadisticas(stats: dict):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=True, indent=2)


# ── Evaluación 24h ────────────────────────────────────────────────
def evaluar_24h() -> dict | None:
    """
    Evalúa las predicciones de 24h anteriores.
    Se ejecuta a las 4:15 PM ET (después del cierre).
    """
    if not os.path.exists(TARGETS_FILE):
        log.info("  Sin predicciones guardadas aún")
        return None

    try:
        with open(TARGETS_FILE) as f:
            historico = json.load(f)
    except Exception as e:
        log.error(f"  Error leyendo histórico: {e}")
        return None

    hoy    = datetime.now().strftime("%Y-%m-%d")
    ayer   = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    stats  = cargar_estadisticas()

    evaluadas     = []
    aciertos_dir  = 0
    aciertos_rango= 0
    errores_target= []
    total_validas = 0

    for entrada in historico:
        # Solo evaluar predicciones de ayer que no han sido evaluadas
        if entrada.get("fecha_prediccion") != ayer:
            continue
        if entrada.get("evaluado_24h", False):
            continue

        log.info(f"\n  Evaluando predicción del {ayer}...")
        resultados_entrada = {}

        for activo, pred in entrada.get("predicciones", {}).items():
            precio_real = obtener_precio_real(activo)
            if not precio_real:
                continue

            resultado = evaluar_prediccion(pred, precio_real)
            if not resultado.get("valido"):
                continue

            resultados_entrada[activo] = resultado
            total_validas += 1

            if resultado["acierto_dir"]:
                aciertos_dir += 1
            if resultado["en_rango"]:
                aciertos_rango += 1
            errores_target.append(resultado["error_target"])

            # Actualizar stats por activo
            if activo not in stats["por_activo"]:
                stats["por_activo"][activo] = {
                    "total": 0, "aciertos_dir": 0,
                    "aciertos_rango": 0, "error_avg": 0.0
                }
            a = stats["por_activo"][activo]
            a["total"] += 1
            if resultado["acierto_dir"]:
                a["aciertos_dir"] += 1
            if resultado["en_rango"]:
                a["aciertos_rango"] += 1
            a["error_avg"] = round(
                (a["error_avg"] * (a["total"]-1) + resultado["error_target"]) / a["total"], 2
            )

            log.info(f"    {activo}: {resultado['desc_dir']}")

        # Marcar como evaluada
        entrada["evaluado_24h"]       = True
        entrada["resultados_24h"]     = resultados_entrada
        entrada["fecha_evaluacion"]   = hoy

        evaluadas.append({
            "fecha":          ayer,
            "total_activos":  total_validas,
            "aciertos_dir":   aciertos_dir,
            "resultados":     resultados_entrada,
        })

    if total_validas == 0:
        log.info("  Sin predicciones para evaluar hoy")
        return None

    # Actualizar estadísticas globales
    stats["total_evaluaciones"] += total_validas
    stats["aciertos_dir_24h"]   += aciertos_dir
    stats["aciertos_rango_24h"] += aciertos_rango
    stats["precision_dir_24h"]   = round(
        stats["aciertos_dir_24h"] / stats["total_evaluaciones"] * 100, 1
    )
    stats["precision_rango_24h"] = round(
        stats["aciertos_rango_24h"] / stats["total_evaluaciones"] * 100, 1
    )
    if errores_target:
        stats["error_target_avg"] = round(
            (stats["error_target_avg"] + sum(errores_target) / len(errores_target)) / 2, 2
        )
    stats["ultima_evaluacion"] = hoy
    stats["historial"].append({
        "fecha": ayer,
        "precision_dir":   round(aciertos_dir / total_validas * 100, 1),
        "precision_rango": round(aciertos_rango / total_validas * 100, 1),
        "total":           total_validas,
    })
    stats["historial"] = stats["historial"][-90:]  # Máximo 90 días

    # Guardar histórico actualizado
    with open(TARGETS_FILE, "w") as f:
        json.dump(historico, f, ensure_ascii=True, indent=2)
    guardar_estadisticas(stats)

    return {
        "fecha":           ayer,
        "total_activos":   total_validas,
        "aciertos_dir":    aciertos_dir,
        "precision_dir":   round(aciertos_dir / total_validas * 100, 1),
        "precision_rango": round(aciertos_rango / total_validas * 100, 1),
        "error_avg":       round(sum(errores_target)/len(errores_target), 2) if errores_target else 0,
        "stats_globales":  stats,
        "resultados":      evaluadas,
    }


# ── Generar reporte de precisión ──────────────────────────────────
def generar_reporte_precision(resultado: dict) -> str:
    """Genera mensaje Telegram con el reporte de aciertos."""
    if not resultado:
        return ""

    stats  = resultado.get("stats_globales", {})
    fecha  = resultado.get("fecha", "")
    prec_d = resultado.get("precision_dir", 0)
    prec_r = resultado.get("precision_rango", 0)
    err    = resultado.get("error_avg", 0)
    total  = resultado.get("total_activos", 0)
    ac     = resultado.get("aciertos_dir", 0)

    # Score visual
    if prec_d >= 70:   score_emoji = "🟢"
    elif prec_d >= 55: score_emoji = "🟡"
    else:              score_emoji = "🔴"

    lineas = [
        f"📊 KAIROS — REPORTE DE PRECISIÓN",
        f"{'='*38}",
        f"📅 Evaluación: {fecha}",
        f"",
        f"🎯 PREDICCIONES 24H:",
        f"  Dirección correcta: {ac}/{total} ({prec_d}%) {score_emoji}",
        f"  En rango predicho:  {prec_r}%",
        f"  Error promedio target: {err}%",
        f"",
        f"📈 ACUMULADO TOTAL:",
        f"  Evaluaciones: {stats.get('total_evaluaciones',0)}",
        f"  Precisión dirección: {stats.get('precision_dir_24h',0)}%",
        f"  Precisión rango:     {stats.get('precision_rango_24h',0)}%",
        f"",
    ]

    # Detalle por activo
    por_activo = stats.get("por_activo", {})
    if por_activo:
        lineas.append("📊 POR ACTIVO (acumulado):")
        for activo, a in sorted(por_activo.items(),
                                key=lambda x: x[1]["aciertos_dir"]/max(x[1]["total"],1),
                                reverse=True):
            if a["total"] == 0:
                continue
            pct = round(a["aciertos_dir"]/a["total"]*100, 0)
            emoji = "✅" if pct >= 60 else "⚠️" if pct >= 45 else "❌"
            lineas.append(
                f"  {emoji} {activo:8}: {int(pct)}% ({a['aciertos_dir']}/{a['total']}) "
                f"err:{a['error_avg']}%"
            )

    lineas += [
        f"",
        f"💡 CALIBRACIÓN:",
    ]

    # Sugerencias de calibración
    if prec_d < 50:
        lineas.append("  ⚠️ Precisión baja — revisar pesos de factores")
    elif prec_d < 60:
        lineas.append("  📈 En proceso de calibración — normal en primeras semanas")
    else:
        lineas.append("  ✅ Precisión aceptable — sistema calibrado")

    # Activos más difíciles de predecir
    if por_activo:
        dificiles = [(k,v) for k,v in por_activo.items()
                     if v["total"] > 0 and v["aciertos_dir"]/v["total"] < 0.5]
        if dificiles:
            nombres = ", ".join([d[0] for d in dificiles])
            lineas.append(f"  Activos difíciles: {nombres} — revisar factores")

    lineas += ["", "kairos-markets.streamlit.app"]
    return "\n".join(lineas)


# ── Función principal ─────────────────────────────────────────────
def ejecutar_feedback_diario(forzar: bool = False) -> bool:
    """
    Ejecuta la evaluación diaria de aciertos.
    Se llama desde monitor.py a las 4:15 PM ET.
    """
    ahora = datetime.now()

    if not forzar:
        # Solo entre 16:15 y 16:45 ET
        en_ventana = (ahora.hour == 16 and 15 <= ahora.minute <= 45)
        if not en_ventana:
            return False

        # No repetir si ya se ejecutó hoy
        stats = cargar_estadisticas()
        if stats.get("ultima_evaluacion") == ahora.strftime("%Y-%m-%d"):
            log.info("  Feedback: ya ejecutado hoy")
            return False

    log.info("\n" + "="*50)
    log.info("📊 KAIROS FEEDBACK DIARIO — EVALUANDO ACIERTOS")
    log.info("="*50)

    resultado = evaluar_24h()

    if resultado:
        reporte = generar_reporte_precision(resultado)
        if reporte:
            try:
                from alertas import enviar_alerta_telegram
                enviar_alerta_telegram(reporte)
                log.info("  ✅ Reporte enviado al canal")
            except Exception as e:
                log.error(f"  Error enviando reporte: {e}")
        log.info(f"  Precisión 24h: {resultado['precision_dir']}%")
        return True

    return False


def mostrar_estadisticas_actuales():
    """Muestra estadísticas actuales en consola."""
    stats = cargar_estadisticas()

    print(f"\n📊 KAIROS — Estadísticas de Precisión")
    print(f"{'='*50}")
    print(f"Total evaluaciones: {stats['total_evaluaciones']}")
    print(f"Precisión dirección 24h: {stats['precision_dir_24h']}%")
    print(f"Precisión rango 24h:     {stats['precision_rango_24h']}%")
    print(f"Error promedio target:   {stats['error_target_avg']}%")
    print(f"Última evaluación:       {stats.get('ultima_evaluacion','nunca')}")

    if stats["por_activo"]:
        print(f"\nPor activo:")
        for activo, a in sorted(stats["por_activo"].items()):
            if a["total"] > 0:
                pct = round(a["aciertos_dir"]/a["total"]*100, 1)
                print(f"  {activo:8}: {pct}% ({a['aciertos_dir']}/{a['total']})")

    if stats["historial"]:
        print(f"\nÚltimos 7 días:")
        for h in stats["historial"][-7:]:
            print(f"  {h['fecha']}: dir {h['precision_dir']}% | rango {h['precision_rango']}%")


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KAIROS Feedback Sistema")
    parser.add_argument("--forzar",  action="store_true", help="Ejecutar evaluación ahora")
    parser.add_argument("--stats",   action="store_true", help="Ver estadísticas actuales")
    args = parser.parse_args()

    if args.stats:
        mostrar_estadisticas_actuales()
    else:
        ejecutar_feedback_diario(forzar=args.forzar or True)
