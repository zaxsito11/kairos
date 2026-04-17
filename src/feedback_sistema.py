# feedback_sistema.py — KAIROS v2
# Fix crítico: calcula precisión correctamente usando precio real de cierre.

import os, sys, json, logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

TARGETS_FILE  = "data/price_targets_historico.json"
FEEDBACK_FILE = "data/feedback_estadisticas.json"
LOG_FILE      = "outputs/feedback.log"

os.makedirs("data", exist_ok=True)
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


def obtener_precio_cierre(activo: str, fecha: str) -> float | None:
    """Obtiene el precio de cierre real de un activo en una fecha específica."""
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        tickers = {
            "SPX":"^GSPC","NDX":"^NDX","Gold":"GC=F","Silver":"SI=F",
            "WTI":"CL=F","BTC":"BTC-USD","DXY":"DX-Y.NYB",
            "VIX":"^VIX","UST10Y":"^TNX",
        }
        ticker = tickers.get(activo)
        if not ticker:
            return None

        fecha_dt   = datetime.strptime(fecha, "%Y-%m-%d")
        fecha_fin  = fecha_dt + timedelta(days=1)
        hist = yf.Ticker(ticker).history(
            start=fecha_dt.strftime("%Y-%m-%d"),
            end=fecha_fin.strftime("%Y-%m-%d")
        )
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        log.warning(f"  Error precio {activo} en {fecha}: {e}")
    return None


def evaluar_prediccion_real(pred: dict, fecha_eval: str) -> dict:
    """
    Evalúa una predicción comparando:
    - Precio base: precio del día de la predicción (guardado)
    - Precio real: precio de cierre del día siguiente (descargado)
    """
    activo      = pred.get("activo","?")
    precio_base = pred.get("precio_actual", 0)
    dir_pred    = pred.get("direccion", "MIXTO")
    target_24h  = pred.get("target_24h", precio_base)

    if precio_base == 0:
        return {"valido": False, "razon": "Sin precio base"}

    # Obtener precio real del día de evaluación
    precio_real = obtener_precio_cierre(activo, fecha_eval)
    if not precio_real:
        return {"valido": False, "razon": f"Sin datos para {fecha_eval}"}

    cambio_pct = round((precio_real - precio_base) / precio_base * 100, 2)
    dir_real   = "SUBE" if precio_real > precio_base else "BAJA"

    # Acierto de dirección
    if dir_pred == "MIXTO":
        acierto = True
        desc    = "MIXTO — no evaluable"
    elif dir_pred == dir_real:
        acierto = True
        desc    = f"✅ {dir_pred} predicho, {dir_real} real ({cambio_pct:+.2f}%)"
    else:
        acierto = False
        desc    = f"❌ {dir_pred} predicho, {dir_real} real ({cambio_pct:+.2f}%)"

    # En rango
    rango_bajo  = pred.get("rango_24h_bajo", precio_base * 0.98)
    rango_alto  = pred.get("rango_24h_alto", precio_base * 1.02)
    en_rango    = rango_bajo <= precio_real <= rango_alto
    error_target= round(abs(precio_real - target_24h) / precio_base * 100, 2)

    return {
        "valido":        True,
        "activo":        activo,
        "precio_base":   precio_base,
        "precio_real":   precio_real,
        "cambio_pct":    cambio_pct,
        "dir_pred":      dir_pred,
        "dir_real":      dir_real,
        "acierto_dir":   acierto,
        "en_rango":      en_rango,
        "error_target":  error_target,
        "descripcion":   desc,
    }


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


def evaluar_24h() -> dict | None:
    """Evalúa predicciones del día anterior."""
    if not os.path.exists(TARGETS_FILE):
        log.info("  Sin predicciones guardadas")
        return None

    try:
        with open(TARGETS_FILE) as f:
            historico = json.load(f)
    except Exception as e:
        log.error(f"  Error: {e}")
        return None

    hoy  = datetime.now().strftime("%Y-%m-%d")
    ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    stats = cargar_estadisticas()

    total_validas = 0
    aciertos_dir  = 0
    aciertos_rango= 0
    errores_target= []
    resultados_hoy= {}

    for entrada in historico:
        if entrada.get("fecha_prediccion") != ayer:
            continue
        if entrada.get("evaluado_24h", False):
            continue

        log.info(f"\n  Evaluando predicción del {ayer}...")
        preds = entrada.get("predicciones", {})

        for activo, pred in preds.items():
            pred["activo"] = activo
            resultado = evaluar_prediccion_real(pred, hoy)

            if not resultado.get("valido"):
                log.info(f"    {activo}: {resultado.get('razon','?')}")
                continue

            total_validas += 1
            resultados_hoy[activo] = resultado
            log.info(f"    {activo}: {resultado['descripcion']}")

            if resultado["acierto_dir"]:
                aciertos_dir += 1
            if resultado["en_rango"]:
                aciertos_rango += 1
            errores_target.append(resultado["error_target"])

            # Actualizar por activo
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

        if resultados_hoy:
            prec_dia = round(aciertos_dir / total_validas * 100, 1) if total_validas > 0 else 0
            entrada["evaluado_24h"]     = True
            entrada["resultados_24h"]   = resultados_hoy
            entrada["aciertos_24h"]     = prec_dia
            entrada["fecha_evaluacion"] = hoy

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
        nuevo_avg = sum(errores_target) / len(errores_target)
        total_prev = stats["total_evaluaciones"] - total_validas
        if total_prev > 0:
            stats["error_target_avg"] = round(
                (stats["error_target_avg"] * total_prev + nuevo_avg * total_validas)
                / stats["total_evaluaciones"], 2
            )
        else:
            stats["error_target_avg"] = round(nuevo_avg, 2)

    stats["ultima_evaluacion"] = hoy
    prec_hoy = round(aciertos_dir / total_validas * 100, 1) if total_validas > 0 else 0
    stats["historial"].append({
        "fecha":           ayer,
        "precision_dir":   prec_hoy,
        "precision_rango": round(aciertos_rango/total_validas*100,1) if total_validas else 0,
        "total":           total_validas,
        "aciertos":        aciertos_dir,
    })
    stats["historial"] = stats["historial"][-90:]

    # Guardar
    with open(TARGETS_FILE, "w") as f:
        json.dump(historico, f, ensure_ascii=True, indent=2)
    guardar_estadisticas(stats)

    return {
        "fecha":           ayer,
        "total":           total_validas,
        "aciertos":        aciertos_dir,
        "precision_dir":   prec_hoy,
        "precision_rango": round(aciertos_rango/total_validas*100,1) if total_validas else 0,
        "error_avg":       round(sum(errores_target)/len(errores_target),2) if errores_target else 0,
        "stats":           stats,
        "resultados":      resultados_hoy,
    }


def generar_reporte(resultado: dict) -> str:
    if not resultado:
        return ""
    prec  = resultado.get("precision_dir",0)
    total = resultado.get("total",0)
    ac    = resultado.get("aciertos",0)
    fecha = resultado.get("fecha","")
    err   = resultado.get("error_avg",0)
    emoji = "🟢" if prec>=65 else "🟡" if prec>=50 else "🔴"

    lineas = [
        f"📊 KAIROS — REPORTE DE PRECISIÓN",
        f"{'='*38}",
        f"📅 {fecha}",
        f"",
        f"{emoji} Dirección correcta: {ac}/{total} ({prec}%)",
        f"📊 Error promedio target: {err}%",
        f"",
    ]

    # Detalle por activo
    for activo, r in resultado.get("resultados",{}).items():
        ok = "✅" if r.get("acierto_dir") else "❌"
        lineas.append(f"  {ok} {activo}: {r.get('descripcion','')[:60]}")

    stats = resultado.get("stats",{})
    lineas += [
        f"",
        f"📈 ACUMULADO: {stats.get('precision_dir_24h',0)}% ({stats.get('total_evaluaciones',0)} eval.)",
        f"",
        f"kairos-markets.streamlit.app",
    ]
    return "\n".join(lineas)


def ejecutar_feedback_diario(forzar: bool = False) -> bool:
    ahora = datetime.now()
    if not forzar:
        en_ventana = (ahora.hour == 16 and 15 <= ahora.minute <= 45)
        if not en_ventana:
            return False
        stats = cargar_estadisticas()
        if stats.get("ultima_evaluacion") == ahora.strftime("%Y-%m-%d"):
            return False

    log.info("\n" + "="*50)
    log.info("📊 KAIROS FEEDBACK — EVALUANDO ACIERTOS")
    log.info("="*50)

    resultado = evaluar_24h()
    if resultado:
        reporte = generar_reporte(resultado)
        if reporte:
            try:
                from alertas import enviar_alerta_telegram
                enviar_alerta_telegram(reporte)
                log.info("  ✅ Reporte enviado")
            except Exception as e:
                log.error(f"  Error: {e}")
        log.info(f"  Precisión: {resultado['precision_dir']}%")
        return True
    return False


def mostrar_estadisticas_actuales():
    stats = cargar_estadisticas()
    print(f"\n📊 KAIROS — Estadísticas de Precisión")
    print(f"{'='*45}")
    print(f"Total evaluaciones: {stats['total_evaluaciones']}")
    print(f"Precisión dirección: {stats['precision_dir_24h']}%")
    print(f"Error promedio:      {stats['error_target_avg']}%")

    if stats.get("por_activo"):
        print(f"\nPor activo:")
        for activo, a in sorted(stats["por_activo"].items()):
            if a["total"] > 0:
                pct = round(a["aciertos_dir"]/a["total"]*100,1)
                ok  = "✅" if pct >= 50 else "❌"
                print(f"  {ok} {activo:8}: {pct}% ({a['aciertos_dir']}/{a['total']})")

    if stats.get("historial"):
        print(f"\nÚltimos días:")
        for h in stats["historial"][-7:]:
            bar = "█" * int(h["precision_dir"]//10)
            print(f"  {h['fecha']}: {h['precision_dir']:5.1f}% {bar}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--forzar", action="store_true")
    parser.add_argument("--stats",  action="store_true")
    args = parser.parse_args()

    if args.stats:
        mostrar_estadisticas_actuales()
    else:
        ejecutar_feedback_diario(forzar=args.forzar or True)
