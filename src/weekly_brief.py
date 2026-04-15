# weekly_brief.py — KAIROS
# Weekly Brief: resumen semanal + outlook de la próxima semana.
# Se envía automáticamente los viernes a las 6:00 PM ET.
#
# ESTRUCTURA:
#   📊 Performance de la semana por activo
#   🏆 Mejor y peor activo de la semana
#   🌍 Eventos que dominaron la narrativa
#   🔮 Outlook próxima semana — eventos y predicciones
#   📅 Calendario eventos críticos próxima semana
#   💡 Tema dominante para la semana que viene

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
LOG_FILE   = "outputs/weekly_brief.log"
BRIEF_FILE = "data/ultimo_weekly_brief.json"

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
log = logging.getLogger("KAIROS.weekly_brief")


# ── Performance semanal ───────────────────────────────────────────
def obtener_performance_semanal() -> dict:
    """Obtiene el rendimiento de la semana para cada activo."""
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
            hist = yf.Ticker(ticker).history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue

            precio_actual = float(hist["Close"].iloc[-1])
            precio_lunes  = float(hist["Close"].iloc[0])
            cambio_sem    = round(((precio_actual - precio_lunes) / precio_lunes) * 100, 2)

            # High y Low de la semana
            high_sem = round(float(hist["High"].max()), 2)
            low_sem  = round(float(hist["Low"].min()), 2)

            performance[nombre] = {
                "precio_actual": round(precio_actual, 2),
                "precio_lunes":  round(precio_lunes, 2),
                "cambio_sem":    cambio_sem,
                "high_sem":      high_sem,
                "low_sem":       low_sem,
                "direccion":     "▲" if cambio_sem > 0 else "▼",
            }
        except Exception as e:
            log.warning(f"  Error {nombre}: {e}")

    return performance


def identificar_mejor_peor(performance: dict) -> tuple:
    """Identifica el mejor y peor activo de la semana."""
    if not performance:
        return None, None

    # Excluir VIX del ranking (inverso al mercado)
    filtrado = {k: v for k, v in performance.items() if k != "VIX"}

    mejor = max(filtrado.items(), key=lambda x: x[1]["cambio_sem"])
    peor  = min(filtrado.items(), key=lambda x: x[1]["cambio_sem"])
    return mejor, peor


# ── Recopilar contexto semanal ────────────────────────────────────
def recopilar_contexto_semanal() -> dict:
    """Recopila toda la información para el weekly brief."""
    contexto = {
        "semana":         datetime.now().strftime("Semana del %d al %d de %B %Y"),
        "fecha_envio":    datetime.now().strftime("%A %d %B %Y"),
        "performance":    {},
        "macro":          {},
        "situaciones":    [],
        "calendario_prox":[],
        "fed_bce":        {},
        "priced_in":      {},
        "alertas_semana": 0,
        "briefs_semana":  [],
    }

    # Performance semanal
    log.info("  [1/5] Performance semanal...")
    contexto["performance"] = obtener_performance_semanal()

    # Macro
    log.info("  [2/5] Datos macro...")
    try:
        from macro import obtener_datos_macro, evaluar_regimen_macro
        datos_macro = obtener_datos_macro()
        regimen     = evaluar_regimen_macro(datos_macro)
        contexto["macro"] = {
            "regimen":    regimen.get("regimen", "NEUTRO"),
            "descripcion":regimen.get("descripcion", ""),
            "core_pce":   datos_macro.get("CORE_PCE", {}).get("variacion", "N/A"),
            "cpi":        datos_macro.get("CORE_CPI", {}).get("variacion", "N/A"),
            "desempleo":  datos_macro.get("DESEMPLEO", {}).get("valor", "N/A"),
            "tasa_fed":   datos_macro.get("TASA_FED", {}).get("valor", "N/A"),
            "bono_10y":   datos_macro.get("RENDIMIENTO_10Y", {}).get("valor", "N/A"),
        }
    except Exception as e:
        log.warning(f"  Macro: {e}")

    # Situaciones activas
    try:
        from news_scanner import SITUACIONES_ACTIVAS
        contexto["situaciones"] = [
            {"nombre": s["nombre"], "nota": s["nota"], "score": s["score_base"]}
            for s in SITUACIONES_ACTIVAS if not s["resuelto"]
        ]
    except Exception as e:
        log.warning(f"  Situaciones: {e}")

    # Calendario próxima semana
    log.info("  [3/5] Calendario próxima semana...")
    try:
        from calendario_eco import obtener_eventos_proximos
        eventos = obtener_eventos_proximos(dias=10)
        # Solo eventos de la próxima semana (7 días)
        contexto["calendario_prox"] = [
            {
                "evento":   ev["evento"],
                "dias":     ev["dias_restantes"],
                "hora":     ev["hora_local_et"],
                "impacto":  ev["impacto"],
                "consenso": ev.get("consenso", "N/A"),
                "activos":  ev["activos"][:3],
            }
            for ev in eventos if ev["dias_restantes"] <= 7
        ]
    except Exception as e:
        log.warning(f"  Calendario: {e}")

    # FED/BCE
    log.info("  [4/5] Análisis FED/BCE...")
    try:
        archivos = sorted([
            f for f in os.listdir("outputs")
            if f.startswith("analisis_") and f.endswith(".txt")
        ], reverse=True)
        if archivos:
            with open(f"outputs/{archivos[0]}", "r", encoding="utf-8") as f:
                contenido = f.read()
            tono = "NEUTRO"
            for linea in contenido.split('\n'):
                if "Clasificación:" in linea or "Clasificacion:" in linea:
                    for t in ["HAWKISH FUERTE","HAWKISH LEVE","NEUTRO",
                               "DOVISH LEVE","DOVISH FUERTE"]:
                        if t in linea:
                            tono = t
                            break
            contexto["fed_bce"] = {"tono": tono, "fuente": archivos[0]}
    except Exception as e:
        log.warning(f"  FED/BCE: {e}")

    # Priced-in
    try:
        from priced_in import obtener_probabilidades_cme
        exp = obtener_probabilidades_cme()
        if exp:
            contexto["priced_in"] = {
                "descripcion":   exp[0]["descripcion"],
                "fecha":         exp[0]["fecha_reunion"],
                "dias":          exp[0]["dias_para_reunion"],
                "probabilidades":exp[0]["probabilidades"],
            }
    except Exception as e:
        log.warning(f"  Priced-in: {e}")

    # Briefs de la semana
    log.info("  [5/5] Briefs de la semana...")
    try:
        hace_7d = datetime.now() - timedelta(days=7)
        archivos_brief = sorted([
            f for f in os.listdir("outputs")
            if f.startswith("morning_brief_") and f.endswith(".txt")
        ], reverse=True)
        for arch in archivos_brief[:7]:
            try:
                fecha_arch = arch.replace("morning_brief_", "").replace(".txt", "")
                fecha_dt   = datetime.strptime(fecha_arch, "%Y-%m-%d")
                if fecha_dt >= hace_7d:
                    contexto["briefs_semana"].append(fecha_arch)
            except Exception:
                pass
    except Exception:
        pass

    return contexto


# ── Generador IA ──────────────────────────────────────────────────
def generar_weekly_brief_ia(contexto: dict) -> str:
    """Genera el Weekly Brief con IA."""

    perf      = contexto.get("performance", {})
    macro     = contexto.get("macro", {})
    sit       = contexto.get("situaciones", [])
    cal       = contexto.get("calendario_prox", [])
    fed_bce   = contexto.get("fed_bce", {})
    priced_in = contexto.get("priced_in", {})
    semana    = contexto.get("semana", "")

    # Formatear performance
    mejor, peor = identificar_mejor_peor(perf)

    perf_lines = []
    for nombre, datos in perf.items():
        signo = "+" if datos["cambio_sem"] > 0 else ""
        perf_lines.append(
            f"  {nombre:8}: {datos['precio_actual']:>10}  "
            f"{signo}{datos['cambio_sem']}%  "
            f"[{datos['low_sem']} - {datos['high_sem']}]"
        )
    perf_str = "\n".join(perf_lines)

    mejor_str = f"{mejor[0]}: {'+' if mejor[1]['cambio_sem']>0 else ''}{mejor[1]['cambio_sem']}%" if mejor else "N/A"
    peor_str  = f"{peor[0]}: {peor[1]['cambio_sem']}%" if peor else "N/A"

    sit_str = "\n".join([f"  🔴 {s['nombre']} — {s['nota']}" for s in sit]) or "Sin situaciones activas"

    cal_str = "\n".join([
        f"  {'🚨' if ev['impacto']=='CRÍTICO' else '⚠️'} {ev['evento']} — "
        f"en {ev['dias']} días | Consenso: {ev['consenso']}"
        for ev in cal
    ]) or "Sin eventos críticos la próxima semana"

    priced_str = ""
    if priced_in:
        probs = priced_in.get("probabilidades", {})
        probs_str = " | ".join([f"{k}: {v}%" for k, v in probs.items()])
        priced_str = (
            f"  {priced_in.get('descripcion')} ({priced_in.get('dias')} días)\n"
            f"  {probs_str}"
        )

    prompt = f"""Eres el analista jefe de KAIROS Markets.
Cada viernes escribes el Weekly Brief para los traders del canal.
Es el análisis más completo de la semana.

{semana}

════════════════════════════════
PERFORMANCE DE LA SEMANA:
════════════════════════════════
{perf_str}

Mejor activo: {mejor_str}
Peor activo:  {peor_str}

════════════════════════════════
RÉGIMEN MACRO: {macro.get('regimen','N/A')} — {macro.get('descripcion','')}
Core PCE: {macro.get('core_pce','N/A')}% | CPI: {macro.get('cpi','N/A')}%
Desempleo: {macro.get('desempleo','N/A')}% | Tasa FED: {macro.get('tasa_fed','N/A')}%
Tono FED/BCE: {fed_bce.get('tono','N/A')}
════════════════════════════════

SITUACIONES ACTIVAS:
{sit_str}

PRICED-IN FOMC:
{priced_str}

EVENTOS PRÓXIMA SEMANA:
{cal_str}
════════════════════════════════

Escribe el Weekly Brief con EXACTAMENTE esta estructura.
Máximo 700 palabras. Directo y accionable.

**📊 KAIROS WEEKLY BRIEF**
**{semana.upper()}**
══════════════════════════════════════

**📈 PERFORMANCE DE LA SEMANA**
[Tabla resumida de los principales activos con cambio semanal.
Explica el por qué de los movimientos más importantes.]

**🏆 GANADOR Y PERDEDOR**
[Mejor activo: por qué subió — contexto macro/geopolítico
Peor activo: por qué cayó — análisis honesto]

**🌍 NARRATIVA DOMINANTE DE LA SEMANA**
[El tema o evento que definió los mercados esta semana.
Máximo 3 párrafos. Conecta macro + geopolítica + movimientos.]

**🔮 OUTLOOK PRÓXIMA SEMANA**
[Predicción general del tono del mercado.
Qué eventos pueden cambiar la narrativa.
Activos a vigilar con más atención.]

**📅 EVENTOS CRÍTICOS PRÓXIMA SEMANA**
[Lista de eventos con hora ET, consenso y activo más afectado.
Para cada evento: qué significaría un dato hawkish vs dovish.]

**💡 TEMA DOMINANTE DE LA PRÓXIMA SEMANA**
[Un párrafo: el factor principal que definirá los mercados.
Puede ser un dato, un banco central, o una situación activa.]

**⚠️ RIESGO PRINCIPAL: [descripción del mayor riesgo]**

---
KAIROS Markets | kairos-markets.streamlit.app
⚠️ Análisis informativo — no es recomendación de inversión

Responde SOLO con el Weekly Brief. Sin comentarios extra."""

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres el analista jefe de KAIROS Markets. "
                    "Escribes weekly briefs institucionales cada viernes. "
                    "Tu análisis conecta macro, geopolítica y movimientos de mercado. "
                    "Eres directo, honesto y nunca inventas datos."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=2500
    )

    return respuesta.choices[0].message.content


# ── Envío y guardado ──────────────────────────────────────────────
def guardar_weekly(brief: str):
    fecha_str = datetime.now().strftime("%Y-%m-%d")
    nombre    = f"outputs/weekly_brief_{fecha_str}.txt"
    with open(nombre, "w", encoding="utf-8") as f:
        f.write(brief)
    with open(BRIEF_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "fecha":     fecha_str,
            "timestamp": datetime.now().isoformat(),
            "brief":     brief,
        }, f, ensure_ascii=False, indent=2)
    log.info(f"  Guardado: {nombre}")
    return nombre


def enviar_weekly_telegram(brief: str):
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
    log.info("  ✅ Weekly Brief enviado al canal Telegram")


# ── Verificador de horario ────────────────────────────────────────
def deberia_enviar_esta_semana() -> bool:
    if not os.path.exists(BRIEF_FILE):
        return True
    try:
        with open(BRIEF_FILE) as f:
            data = json.load(f)
        fecha_ultimo = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
        return datetime.now() - fecha_ultimo > timedelta(days=6)
    except Exception:
        return True


# ── Función principal ─────────────────────────────────────────────
def generar_y_enviar_weekly(forzar: bool = False):
    """
    Genera y envía el Weekly Brief.
    Solo actúa los viernes entre 17:30 y 18:30 ET.
    """
    ahora     = datetime.now()
    es_viernes = ahora.weekday() == 4  # 4 = viernes
    en_ventana = (ahora.hour == 17 and ahora.minute >= 30) or ahora.hour == 18

    if not forzar:
        if not es_viernes:
            log.info(f"  Weekly Brief: no es viernes (día {ahora.weekday()})")
            return False
        if not en_ventana:
            log.info(f"  Weekly Brief: fuera de ventana (hora {ahora.hour}:{ahora.minute})")
            return False
        if not deberia_enviar_esta_semana():
            log.info("  Weekly Brief: ya enviado esta semana")
            return False

    log.info("\n" + "="*50)
    log.info("📊 GENERANDO WEEKLY BRIEF KAIROS")
    log.info("="*50)

    log.info("\nRecopilando datos de la semana...")
    contexto = recopilar_contexto_semanal()

    log.info("\nGenerando análisis con IA...")
    brief = generar_weekly_brief_ia(contexto)

    guardar_weekly(brief)

    log.info("\nEnviando al canal...")
    enviar_weekly_telegram(brief)

    log.info("\n✅ Weekly Brief completado")
    return True


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KAIROS Weekly Brief")
    parser.add_argument("--forzar", action="store_true",
                        help="Genera el brief ahora sin esperar el viernes")
    args = parser.parse_args()
    generar_y_enviar_weekly(forzar=args.forzar or True)
