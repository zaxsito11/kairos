# closing_brief.py — KAIROS
# Closing Brief: resumen de la sesión a las 4:00 PM ET (cierre NYSE).
# Compara predicciones del Morning Brief vs lo que realmente pasó.
# Esto es clave para medir la precisión de KAIROS.

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

client     = Groq(api_key=os.getenv("GROQ_API_KEY"))
LOG_FILE   = "outputs/closing_brief.log"
SENT_FILE  = "data/closing_enviados.json"

os.makedirs("outputs", exist_ok=True)
os.makedirs("data",    exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("KAIROS.closing_brief")


# ── Performance del día ───────────────────────────────────────────
def obtener_performance_dia() -> dict:
    """Performance real de la sesión de hoy."""
    import yfinance as yf

    tickers = {
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

    performance = {}
    for nombre, ticker in tickers.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue

            cierre_hoy  = float(hist["Close"].iloc[-1])
            cierre_ayer = float(hist["Close"].iloc[-2])
            cambio      = round(((cierre_hoy - cierre_ayer) / cierre_ayer) * 100, 2)
            high_dia    = round(float(hist["High"].iloc[-1]), 2)
            low_dia     = round(float(hist["Low"].iloc[-1]), 2)

            performance[nombre] = {
                "cierre":    round(cierre_hoy, 2),
                "cambio":    cambio,
                "high":      high_dia,
                "low":       low_dia,
                "direccion": "▲" if cambio > 0 else "▼",
            }
        except Exception as e:
            log.warning(f"  Error {nombre}: {e}")

    return performance


# ── Cargar predicciones del Morning Brief ─────────────────────────
def cargar_predicciones_morning() -> str:
    """Carga predicciones del Morning Brief Y targets de price_targets."""
    hoy       = datetime.now().strftime("%Y-%m-%d")
    resultado = []

    # 1. Cargar targets de price_targets.py
    targets_file = "data/price_targets_historico.json"
    if os.path.exists(targets_file):
        try:
            with open(targets_file) as f:
                historico = json.load(f)
            # Buscar predicción de hoy
            pred_hoy = next(
                (e for e in reversed(historico)
                 if e.get("fecha_prediccion") == hoy), None
            )
            if pred_hoy:
                resultado.append("TARGETS KAIROS DE HOY:")
                for activo, t in pred_hoy.get("predicciones", {}).items():
                    dir_ = t.get("direccion", "MIXTO")
                    prob = t.get("probabilidad", 50)
                    t24h = t.get("target_24h", t.get("precio_actual", 0))
                    resultado.append(
                        f"  {activo}: {dir_} ({prob}%) → target {t24h}"
                    )
        except Exception as e:
            resultado.append(f"Error targets: {e}")

    # 2. Cargar Morning Brief si existe
    brief_file = "data/ultimo_brief.json"
    if os.path.exists(brief_file):
        try:
            with open(brief_file) as f:
                data = json.load(f)
            if data.get("fecha") == hoy:
                brief = data.get("brief", "")
                lineas = brief.split("\n")
                pred_lineas = []
                en_pred = False
                for linea in lineas:
                    if "SESIÓN DE HOY" in linea or "QUÉ ESPERAR" in linea:
                        en_pred = True
                    if en_pred and linea.strip().startswith("**"):
                        if any(x in linea for x in ["NIVELES","EVENTOS","RIESGO","IDEA"]):
                            break
                    if en_pred:
                        pred_lineas.append(linea)
                if pred_lineas:
                    resultado.append("\nMORNING BRIEF PREDICCIONES:")
                    resultado.extend(pred_lineas[:15])
        except Exception:
            pass

    return "\n".join(resultado) if resultado else "Sin predicciones disponibles hoy"


# ── Generar Closing Brief ─────────────────────────────────────────
def generar_closing_brief_ia(performance: dict, predicciones: str,
                              contexto_extra: dict) -> str:
    """Genera el Closing Brief comparando predicciones vs realidad."""

    fecha = datetime.now().strftime("%A %d %B %Y")

    # Formatear performance real
    perf_lines = []
    for nombre, datos in performance.items():
        signo = "+" if datos["cambio"] > 0 else ""
        perf_lines.append(
            f"  {nombre:8}: {datos['cierre']:>10}  "
            f"{signo}{datos['cambio']}%  "
            f"[min {datos['low']} — max {datos['high']}]"
        )
    perf_str = "\n".join(perf_lines)

    # Identificar activos más movidos
    movidos = sorted(performance.items(),
                     key=lambda x: abs(x[1]["cambio"]), reverse=True)
    top_movidos = ", ".join([f"{k} {'+' if v['cambio']>0 else ''}{v['cambio']}%"
                             for k, v in movidos[:4]])

    prompt = f"""Eres el analista de cierre de KAIROS Markets.
Cada día a las 4 PM ET escribes el Closing Brief.
Tu trabajo MÁS IMPORTANTE es comparar las predicciones del Morning Brief
con lo que realmente pasó — esto mide la precisión de KAIROS.

HOY: {fecha}

════════════════════════════════
PERFORMANCE REAL DE LA SESIÓN:
════════════════════════════════
{perf_str}

Activos más movidos: {top_movidos}

════════════════════════════════
PREDICCIONES DEL MORNING BRIEF DE HOY:
════════════════════════════════
{predicciones}

RÉGIMEN MACRO: {contexto_extra.get('regimen','N/A')}
════════════════════════════════

Escribe el Closing Brief con EXACTAMENTE esta estructura.
Máximo 500 palabras. Honesto — si las predicciones fallaron, dilo.

**📊 KAIROS CLOSING BRIEF — {fecha.upper()}**
══════════════════════════════════════

**📈 CIERRE DE SESIÓN**
[Resumen de los movimientos reales del día.
Explica los movimientos más importantes y su causa.]

**🎯 PREDICCIONES vs REALIDAD**
[Para cada activo predicho en el Morning Brief:
  ✅ CORRECTO: [activo] — predicho [dirección], real [resultado]
  ❌ INCORRECTO: [activo] — predicho [dirección], real [resultado]
  ⚪ NEUTRAL: [activo] — mercado cerrado o sin movimiento relevante

Sé completamente honesto. Los errores son datos de mejora.]

**📊 PUNTUACIÓN DEL DÍA: X/10**
[Calcula una puntuación de precisión honesta.
Base: % de predicciones de dirección correctas.
Explica qué falló y por qué en 2 líneas.]

**🌍 CAUSA PRINCIPAL DE LOS MOVIMIENTOS**
[El factor que más dominó la sesión hoy.
Conecta con situaciones activas y contexto macro.]

**👀 QUÉ VIGILAR MAÑANA**
[2-3 factores o niveles clave para la sesión de mañana.
Si hay dato macro mañana, mencionarlo.]

---
KAIROS Markets | kairos-markets.streamlit.app
⚠️ Análisis informativo — no es recomendación de inversión

Responde SOLO con el Closing Brief. Sin comentarios extra."""

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres el analista de cierre de KAIROS. "
                    "Tu especialidad es comparar predicciones vs realidad. "
                    "Eres brutalmente honesto — los errores se reportan sin excusas. "
                    "Los aciertos también se reconocen con precisión."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )

    return respuesta.choices[0].message.content


# ── Función principal ─────────────────────────────────────────────
def generar_y_enviar_closing(forzar: bool = False):
    """
    Genera y envía el Closing Brief.
    Solo actúa entre 16:00 y 16:30 ET (cierre NYSE).
    """
    ahora = datetime.now()
    hoy   = ahora.strftime("%Y-%m-%d")

    if not forzar:
        # Solo entre 16:00 y 16:30 ET
        if not (ahora.hour == 16 and ahora.minute <= 30):
            log.info(f"  Closing Brief: fuera de ventana (hora {ahora.hour}:{ahora.minute})")
            return False

        # No reenviar si ya se envió hoy
        if os.path.exists(SENT_FILE):
            try:
                with open(SENT_FILE) as f:
                    enviados = json.load(f)
                if hoy in enviados:
                    log.info("  Closing Brief: ya enviado hoy")
                    return False
            except Exception:
                pass

    log.info("\n" + "="*50)
    log.info("📊 GENERANDO CLOSING BRIEF KAIROS")
    log.info("="*50)

    log.info("\n  [1/3] Performance del día...")
    performance = obtener_performance_dia()

    log.info("\n  [2/3] Cargando predicciones del Morning Brief...")
    predicciones = cargar_predicciones_morning()

    log.info("\n  [3/3] Generando análisis con IA...")
    contexto_extra = {"regimen": "NEUTRO"}
    try:
        from macro import obtener_datos_macro, evaluar_regimen_macro
        datos_macro     = obtener_datos_macro()
        regimen         = evaluar_regimen_macro(datos_macro)
        contexto_extra  = {"regimen": regimen.get("regimen", "NEUTRO")}
    except Exception:
        pass

    brief = generar_closing_brief_ia(performance, predicciones, contexto_extra)

    # Guardar
    fecha_str = datetime.now().strftime("%Y-%m-%d")
    with open(f"outputs/closing_brief_{fecha_str}.txt", "w", encoding="utf-8") as f:
        f.write(brief)

    # Marcar como enviado
    enviados = {}
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE) as f:
                enviados = json.load(f)
        except Exception:
            pass
    enviados[hoy] = datetime.now().isoformat()
    with open(SENT_FILE, "w") as f:
        json.dump(enviados, f, indent=2)

    # Enviar
    from alertas import enviar_alerta_telegram
    if len(brief) <= 4096:
        enviar_alerta_telegram(brief)
    else:
        partes = []
        lineas = brief.split('\n')
        parte_actual = []
        chars = 0
        for linea in lineas:
            if chars + len(linea) + 1 > 3800:
                partes.append('\n'.join(parte_actual))
                parte_actual = [linea]
                chars = len(linea)
            else:
                parte_actual.append(linea)
                chars += len(linea) + 1
        if parte_actual:
            partes.append('\n'.join(parte_actual))
        for i, parte in enumerate(partes, 1):
            if i > 1:
                parte = f"[{i}/{len(partes)}]\n" + parte
            enviar_alerta_telegram(parte)

    log.info("\n✅ Closing Brief completado y enviado")
    return True


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    generar_y_enviar_closing(forzar=True)
