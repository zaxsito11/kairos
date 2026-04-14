# morning_brief.py — KAIROS
# Morning Brief diario — enviado automáticamente a las 8:00 AM
#
# CONCEPTO:
# Fusiona todas las fuentes de KAIROS en un análisis ponderado único.
# La IA actúa como analista senior que escribe el morning note institucional.
#
# PONDERACIÓN:
#   40% — Contexto inmediato (últimas 24h)
#   30% — Contexto macro estructural (FED/BCE/datos)
#   20% — Precedentes históricos
#   10% — Calendario próximo

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

client   = Groq(api_key=os.getenv("GROQ_API_KEY"))
LOG_FILE = "outputs/morning_brief.log"
BRIEF_FILE = "data/ultimo_brief.json"

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
log = logging.getLogger("KAIROS.morning_brief")


# ── Recopilador de contexto ───────────────────────────────────────
def recopilar_contexto() -> dict:
    """
    Recopila todas las fuentes de KAIROS y las pondera.
    Retorna un dict estructurado listo para la IA.
    """
    contexto = {
        "fecha":           datetime.now().strftime("%A %d %B %Y"),
        "hora_generacion": datetime.now().strftime("%H:%M"),
        "macro":           {},
        "precios":         {},
        "fed_bce":         {},
        "situaciones":     [],
        "calendario":      [],
        "priced_in":       {},
        "alertas_ayer":    [],
        "precedentes":     {},
    }

    # ── BLOQUE 1 (40%): Contexto inmediato ───────────────────────
    log.info("  [1/5] Obteniendo precios de mercado...")
    try:
        from precios import obtener_precios
        precios = obtener_precios()
        contexto["precios"] = {
            nombre: {
                "precio":    datos["precio"],
                "cambio_pct":datos["variacion_pct"],
                "direccion": datos["direccion"],
            }
            for nombre, datos in precios.items() if datos
        }
    except Exception as e:
        log.warning(f"  Precios: {e}")

    # Alertas enviadas ayer
    log.info("  [1/5] Cargando alertas recientes...")
    try:
        estado_file = "data/monitor_estado.json"
        if os.path.exists(estado_file):
            with open(estado_file, "r", encoding="utf-8") as f:
                estado = json.load(f)
            contexto["alertas_ayer"] = estado.get("alertas_enviadas", 0)
    except Exception as e:
        log.warning(f"  Estado monitor: {e}")

    # Situaciones activas
    try:
        from news_scanner import SITUACIONES_ACTIVAS
        contexto["situaciones"] = [
            {"nombre": s["nombre"], "nota": s["nota"],
             "urgencia": s["urgencia"], "score": s["score_base"]}
            for s in SITUACIONES_ACTIVAS if not s["resuelto"]
        ]
    except Exception as e:
        log.warning(f"  Situaciones: {e}")

    # ── BLOQUE 2 (30%): Contexto macro estructural ────────────────
    log.info("  [2/5] Obteniendo datos macro FRED...")
    try:
        from macro import obtener_datos_macro, evaluar_regimen_macro
        datos_macro = obtener_datos_macro()
        regimen     = evaluar_regimen_macro(datos_macro)

        contexto["macro"] = {
            "regimen":    regimen.get("regimen", "N/A"),
            "descripcion":regimen.get("descripcion", ""),
            "señales":    regimen.get("señales", []),
            "core_pce":   datos_macro.get("CORE_PCE", {}).get("variacion", "N/A"),
            "cpi":        datos_macro.get("CORE_CPI", {}).get("variacion", "N/A"),
            "nfp":        datos_macro.get("NFP", {}).get("valor", "N/A"),
            "desempleo":  datos_macro.get("DESEMPLEO", {}).get("valor", "N/A"),
            "tasa_fed":   datos_macro.get("TASA_FED", {}).get("valor", "N/A"),
            "bono_10y":   datos_macro.get("RENDIMIENTO_10Y", {}).get("valor", "N/A"),
        }
    except Exception as e:
        log.warning(f"  Macro: {e}")

    # Sorpresas macro
    try:
        from sorpresa_macro import analizar_sorpresas_recientes
        sorpresas = analizar_sorpresas_recientes()
        contexto["sorpresas_macro"] = [
            {"nombre": s["nombre"], "nivel": s["nivel"],
             "diferencia": s["diferencia"], "emoji": s["emoji"]}
            for s in sorpresas
        ]
    except Exception as e:
        log.warning(f"  Sorpresas: {e}")

    # FED/BCE análisis reciente
    log.info("  [3/5] Cargando análisis FED/BCE...")
    try:
        archivos_analisis = sorted([
            f for f in os.listdir("outputs")
            if f.startswith("analisis_") and f.endswith(".txt")
        ], reverse=True)

        if archivos_analisis:
            with open(f"outputs/{archivos_analisis[0]}", "r", encoding="utf-8") as f:
                contenido = f.read()
            # Extraer tono y score
            tono  = "NEUTRO"
            score = 0
            banco = "FED"
            for linea in contenido.split('\n'):
                if "Clasificación:" in linea or "Clasificacion:" in linea:
                    for t in ["HAWKISH FUERTE","HAWKISH LEVE","NEUTRO",
                               "DOVISH LEVE","DOVISH FUERTE"]:
                        if t in linea:
                            tono = t
                            break
                if "Score:" in linea and "Confidence" not in linea:
                    try:
                        score = int(linea.split(":")[-1].strip().replace("+",""))
                    except Exception:
                        pass
                if "BCE" in archivos_analisis[0]:
                    banco = "BCE"

            contexto["fed_bce"] = {
                "banco":  banco,
                "tono":   tono,
                "score":  score,
                "fuente": archivos_analisis[0],
            }
    except Exception as e:
        log.warning(f"  FED/BCE: {e}")

    # Priced-in
    try:
        from priced_in import obtener_probabilidades_cme, calcular_sorpresa
        expectativas = obtener_probabilidades_cme()
        if expectativas:
            proxima = expectativas[0]
            sorpresa = calcular_sorpresa(
                contexto["fed_bce"].get("tono", "NEUTRO"),
                contexto["fed_bce"].get("score", 0),
                expectativas
            )
            contexto["priced_in"] = {
                "proxima_reunion":      proxima["descripcion"],
                "fecha_reunion":        proxima["fecha_reunion"],
                "dias_para_reunion":    proxima["dias_para_reunion"],
                "probabilidades":       proxima["probabilidades"],
                "sorpresa":             sorpresa,
            }
    except Exception as e:
        log.warning(f"  Priced-in: {e}")

    # ── BLOQUE 3 (20%): Precedentes históricos ────────────────────
    log.info("  [4/5] Consultando precedentes históricos...")
    try:
        from historico import encontrar_similares, generar_resumen_historico
        tono_actual  = contexto["fed_bce"].get("tono", "NEUTRO")
        score_actual = contexto["fed_bce"].get("score", 0)
        similares    = encontrar_similares(tono_actual, score_actual, n=3)

        if similares:
            spx_avg  = sum(e["outcomes_24h"]["SPX"]  for e in similares)/len(similares)
            gold_avg = sum(e["outcomes_24h"]["Gold"] for e in similares)/len(similares)
            dxy_avg  = sum(e["outcomes_24h"]["DXY"]  for e in similares)/len(similares)
            vix_avg  = sum(e["outcomes_24h"].get("VIX",0) for e in similares)/len(similares)

            contexto["precedentes"] = {
                "tono_analizado": tono_actual,
                "n_precedentes":  len(similares),
                "eventos":        [{"fecha": e["fecha"], "evento": e["evento"][:60],
                                    "leccion": e["leccion"][:100]}
                                   for e in similares],
                "promedio_24h": {
                    "SPX":  round(spx_avg, 2),
                    "Gold": round(gold_avg, 2),
                    "DXY":  round(dxy_avg, 2),
                    "VIX":  round(vix_avg, 2),
                },
            }
    except Exception as e:
        log.warning(f"  Precedentes: {e}")

    # ── BLOQUE 4 (10%): Calendario próximo ───────────────────────
    log.info("  [5/5] Cargando calendario económico...")
    try:
        from calendario_eco import obtener_eventos_proximos
        eventos = obtener_eventos_proximos(dias=7)
        contexto["calendario"] = [
            {
                "evento":        ev["evento"],
                "dias":          ev["dias_restantes"],
                "hora":          ev["hora_local_et"],
                "impacto":       ev["impacto"],
                "consenso":      ev.get("consenso", "N/A"),
                "activos":       ev["activos"][:3],
            }
            for ev in eventos[:5]
        ]
    except Exception as e:
        log.warning(f"  Calendario: {e}")

    return contexto


# ── Generador de brief con IA ─────────────────────────────────────
def generar_brief_ia(contexto: dict) -> str:
    """
    Pasa el contexto ponderado a Groq y genera el morning brief.
    La IA sintetiza como analista senior institucional.
    """

    # Construir el prompt con todos los bloques ponderados
    fecha     = contexto.get("fecha", "")
    precios   = contexto.get("precios", {})
    macro     = contexto.get("macro", {})
    fed_bce   = contexto.get("fed_bce", {})
    priced_in = contexto.get("priced_in", {})
    prec      = contexto.get("precedentes", {})
    cal       = contexto.get("calendario", [])
    sit       = contexto.get("situaciones", [])
    sorpresas = contexto.get("sorpresas_macro", [])

    # Formatear precios
    precios_str = "\n".join([
        f"  {nombre}: {datos['precio']} ({datos['cambio_pct']}% {datos['direccion']})"
        for nombre, datos in precios.items()
    ]) or "No disponible"

    # Formatear situaciones activas
    sit_str = "\n".join([
        f"  🔴 {s['nombre']} — Score: {s['score']}/100 — {s['nota']}"
        for s in sit
    ]) or "Sin situaciones activas"

    # Formatear calendario
    cal_str = "\n".join([
        f"  {'🚨' if ev['impacto']=='CRÍTICO' else '⚠️'} {ev['evento']} — "
        f"en {ev['dias']} días | Consenso: {ev['consenso']}"
        for ev in cal
    ]) or "Sin eventos próximos"

    # Formatear priced-in
    priced_str = ""
    if priced_in:
        probs = priced_in.get("probabilidades", {})
        probs_str = " | ".join([f"{k}: {v}%" for k, v in probs.items()])
        sorpresa_data = priced_in.get("sorpresa", {})
        priced_str = (
            f"  Próxima reunión: {priced_in.get('proxima_reunion')} "
            f"({priced_in.get('dias_para_reunion')} días)\n"
            f"  Probabilidades: {probs_str}\n"
            f"  Divergencia: {sorpresa_data.get('nivel_sorpresa','N/A')}\n"
            f"  Impacto si se confirma: {sorpresa_data.get('impacto_esperado','N/A')}"
        )

    # Formatear precedentes
    prec_str = ""
    if prec:
        prom = prec.get("promedio_24h", {})
        prec_str = (
            f"  Basado en {prec.get('n_precedentes')} casos históricos similares\n"
            f"  ({prec.get('tono_analizado')}):\n"
            f"  SPX promedio 24h:  {'+' if prom.get('SPX',0)>=0 else ''}{prom.get('SPX')}%\n"
            f"  Gold promedio 24h: {'+' if prom.get('Gold',0)>=0 else ''}{prom.get('Gold')}%\n"
            f"  DXY promedio 24h:  {'+' if prom.get('DXY',0)>=0 else ''}{prom.get('DXY')}%\n"
            f"  VIX promedio 24h:  {'+' if prom.get('VIX',0)>=0 else ''}{prom.get('VIX')}%"
        )

    # Formatear sorpresas macro
    sorpr_str = "\n".join([
        f"  {s['emoji']} {s['nombre']}: {s['nivel']} ({s['diferencia']:+.2f})"
        for s in sorpresas
    ]) or "Sin sorpresas macro recientes"

    prompt = f"""Eres el analista macro jefe de KAIROS, un sistema de inteligencia de mercados.
Cada mañana escribes el Morning Brief que reciben los traders del canal KAIROS Markets.
Tu análisis es directo, accionable y honesto. No exageras. No inventas certezas donde hay incertidumbre.

Hoy es {fecha}. Tienes toda la información ponderada del sistema:

═══════════════════════════════════════
BLOQUE 1 — CONTEXTO INMEDIATO (peso 40%)
═══════════════════════════════════════

PRECIOS DE CIERRE (sesión anterior):
{precios_str}

SITUACIONES ACTIVAS EN EL MUNDO:
{sit_str}

SORPRESAS MACRO RECIENTES:
{sorpr_str}

═══════════════════════════════════════
BLOQUE 2 — CONTEXTO MACRO ESTRUCTURAL (peso 30%)
═══════════════════════════════════════

RÉGIMEN MACRO: {macro.get('regimen','N/A')} — {macro.get('descripcion','')}
Señales activas: {' | '.join(macro.get('señales',[]))}

DATOS ECONÓMICOS:
  Core PCE: {macro.get('core_pce','N/A')}% YoY (objetivo FED: 2%)
  CPI Core: {macro.get('cpi','N/A')}% YoY
  NFP: {macro.get('nfp','N/A')}k empleos
  Desempleo: {macro.get('desempleo','N/A')}%
  Tasa FED: {macro.get('tasa_fed','N/A')}%
  Bono 10Y: {macro.get('bono_10y','N/A')}%

ANÁLISIS BANCO CENTRAL ({fed_bce.get('banco','FED')}):
  Tono: {fed_bce.get('tono','N/A')} (Score: {fed_bce.get('score',0):+d}/±5)

PRICED-IN (expectativas del mercado):
{priced_str}

═══════════════════════════════════════
BLOQUE 3 — PRECEDENTES HISTÓRICOS (peso 20%)
═══════════════════════════════════════

{prec_str}

═══════════════════════════════════════
BLOQUE 4 — CALENDARIO PRÓXIMO (peso 10%)
═══════════════════════════════════════

EVENTOS PRÓXIMOS 7 DÍAS:
{cal_str}

═══════════════════════════════════════

Escribe el Morning Brief de hoy con EXACTAMENTE esta estructura.
Usa emojis para hacer el mensaje legible en Telegram.
Sé directo. Máximo 600 palabras total.

**📊 KAIROS MORNING BRIEF — {fecha.upper()}**
════════════════════════════════════

**⚡ RESUMEN EJECUTIVO**
[3 líneas máximo. Lo más importante del día en 10 segundos.]

**🌍 CONTEXTO MACRO Y GEOPOLÍTICO**
[Fusiona situaciones activas + régimen macro + FED/BCE.
Pondera por urgencia. Si hay conflicto activo, domina este bloque.]

**📈 MERCADOS — SESIÓN ANTERIOR**
[Qué pasó ayer. Qué activos se movieron y por qué.]

**🔮 SESIÓN DE HOY — QUÉ ESPERAR**
[Predicción por activo. Usa los precedentes históricos + priced-in.
Incluye probabilidad y dirección. Sé honesto con la incertidumbre.
Formato: Activo → Dirección esperada (probabilidad%) — Razón]

**🎯 NIVELES CLAVE A VIGILAR HOY**
[3-4 niveles técnicos macro relevantes con su significado]

**📅 EVENTOS QUE PUEDEN MOVER EL MERCADO HOY**
[Solo los eventos del día. Si no hay ninguno, indicar que la sesión
depende de noticias sorpresa.]

**⚠️ RIESGO DEL DÍA: [BAJO / MEDIO / ALTO / CRÍTICO]**
[Una línea explicando el riesgo principal del día]

**💡 IDEA DIRECCIONAL**
[Una idea conceptual basada en el análisis. NO es recomendación de inversión.
Es la dirección que los datos sugieren con más fuerza hoy.]

---
KAIROS Markets | kairos-markets.streamlit.app
[Nota al pie: esto es análisis informativo, no recomendación de inversión]

Responde SOLO con el morning brief. Sin introducciones ni comentarios extras."""

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres el analista macro jefe de KAIROS Markets. "
                    "Escribes morning briefs institucionales diarios. "
                    "Tu estilo es directo, preciso y accionable. "
                    "Nunca inventas datos. Ponderas la evidencia disponible. "
                    "Eres honesto cuando hay incertidumbre."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=2000
    )

    return respuesta.choices[0].message.content


# ── Guardado y envío ──────────────────────────────────────────────
def guardar_brief(brief: str, contexto: dict):
    """Guarda el brief en archivo txt y json."""
    fecha_str = datetime.now().strftime("%Y-%m-%d")

    # TXT para leer
    nombre_txt = f"outputs/morning_brief_{fecha_str}.txt"
    with open(nombre_txt, "w", encoding="utf-8") as f:
        f.write(brief)

    # JSON con contexto completo
    with open(BRIEF_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "fecha":     fecha_str,
            "timestamp": datetime.now().isoformat(),
            "brief":     brief,
            "contexto":  {k: v for k, v in contexto.items()
                          if k not in ["precios"]},
        }, f, ensure_ascii=False, indent=2)

    log.info(f"  Brief guardado en {nombre_txt}")
    return nombre_txt


def enviar_brief_telegram(brief: str):
    """Envía el brief al canal Telegram en partes si es muy largo."""
    from alertas import enviar_alerta_telegram

    # Telegram tiene límite de 4096 caracteres por mensaje
    if len(brief) <= 4096:
        enviar_alerta_telegram(brief)
    else:
        # Dividir en partes coherentes
        partes = []
        lineas = brief.split('\n')
        parte_actual = []
        chars_actual = 0

        for linea in lineas:
            if chars_actual + len(linea) + 1 > 3800:
                partes.append('\n'.join(parte_actual))
                parte_actual = [linea]
                chars_actual = len(linea)
            else:
                parte_actual.append(linea)
                chars_actual += len(linea) + 1

        if parte_actual:
            partes.append('\n'.join(parte_actual))

        for i, parte in enumerate(partes, 1):
            if i > 1:
                parte = f"[{i}/{len(partes)}]\n" + parte
            enviar_alerta_telegram(parte)

    log.info("  ✅ Brief enviado al canal Telegram")


# ── Verificador de horario ────────────────────────────────────────
def deberia_enviar_hoy() -> bool:
    """Verifica si ya se envió el brief hoy."""
    if not os.path.exists(BRIEF_FILE):
        return True
    try:
        with open(BRIEF_FILE, "r") as f:
            data = json.load(f)
        fecha_ultimo = data.get("fecha", "")
        return fecha_ultimo != datetime.now().strftime("%Y-%m-%d")
    except Exception:
        return True


# ── Función principal ─────────────────────────────────────────────
def generar_y_enviar_brief(forzar: bool = False):
    """
    Genera y envía el Morning Brief.
    Se puede llamar desde monitor.py a las 8:00 AM.
    """
    hora_actual = datetime.now().hour

    if not forzar and not (7 <= hora_actual <= 9):
        log.info(f"  Morning Brief: fuera de ventana (hora {hora_actual})")
        return False

    if not forzar and not deberia_enviar_hoy():
        log.info("  Morning Brief: ya enviado hoy")
        return False

    log.info("\n" + "="*50)
    log.info("📊 GENERANDO MORNING BRIEF KAIROS")
    log.info("="*50)

    # Recopilar contexto ponderado
    log.info("\nRecopilando información de todas las fuentes...")
    contexto = recopilar_contexto()

    # Generar con IA
    log.info("\nGenerando análisis con IA...")
    brief = generar_brief_ia(contexto)

    # Guardar
    guardar_brief(brief, contexto)

    # Enviar
    log.info("\nEnviando al canal Telegram...")
    enviar_brief_telegram(brief)

    log.info("\n✅ Morning Brief completado")
    return True


# ── Scheduler integrado ───────────────────────────────────────────
def iniciar_scheduler():
    """
    Loop que verifica cada minuto si es hora de enviar el brief.
    Integrar con monitor.py o correr independiente.
    """
    import time
    log.info("⏰ Morning Brief scheduler activo — enviará a las 8:00 AM")

    while True:
        ahora = datetime.now()
        if ahora.hour == 8 and ahora.minute == 0:
            generar_y_enviar_brief()
        time.sleep(60)


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KAIROS Morning Brief")
    parser.add_argument("--forzar", action="store_true",
                        help="Genera y envía el brief ahora sin esperar las 8AM")
    parser.add_argument("--scheduler", action="store_true",
                        help="Corre en loop y envía a las 8AM automáticamente")
    args = parser.parse_args()

    if args.scheduler:
        iniciar_scheduler()
    else:
        generar_y_enviar_brief(forzar=True)


# ── Instrucciones de integración con monitor.py ───────────────────
# Agrega esto en run_monitor() de monitor.py, dentro del loop while:
#
# # Morning Brief — verificar cada ciclo
# try:
#     from morning_brief import generar_y_enviar_brief
#     generar_y_enviar_brief()  # solo actúa entre 7-9 AM y si no se envió hoy
# except Exception as e:
#     log.warning(f"Error morning brief: {e}")
