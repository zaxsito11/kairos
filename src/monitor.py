# monitor.py — KAIROS
# Sistema de vigilancia automática de eventos con impacto en mercados.
# 5 módulos integrados:
#   [0] Morning Brief     — 8:00 AM diario, análisis ponderado con IA
#   [1] Noticias          — score≥70, solo MAXIMA+ALTA
#   [2] Calendario        — anticipa FOMC/CPI/NFP
#   [3] Mercados          — patrones macro con contexto causal
#   [4] FED               — nuevo comunicado genuino

import os
import sys
import time
import hashlib
import json
import logging
from datetime import datetime, timedelta

import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))

from news_scanner   import escanear_noticias_kairos, formatear_alerta_noticia, SCORE_MINIMO_ALERTA
from calendario_eco import verificar_alertas_calendario, resumen_semana
from market_alert   import ejecutar_market_alert
from event_brief    import verificar_y_enviar_event_briefs
from weekly_brief   import generar_y_enviar_weekly
from price_targets  import calcular_todos_los_targets, guardar_prediccion, formatear_targets_telegram
from closing_brief   import generar_y_enviar_closing
from feedback_sistema import ejecutar_feedback_diario
from signal_engine    import analizar_mercado_completo, formatear_señales_telegram
from alertas        import enviar_alerta_telegram

# ── Configuración ─────────────────────────────────────────────────
INTERVALO_SEGUNDOS = 300
LOG_FILE           = "outputs/monitor.log"
ESTADO_FILE        = "data/monitor_estado.json"

# ── Logging ───────────────────────────────────────────────────────
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
log = logging.getLogger("KAIROS.monitor")


# ── Estado persistente ────────────────────────────────────────────
def cargar_estado() -> dict:
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Error cargando estado: {e}. Creando nuevo.")
    return {
        "noticias_vistas":    [],
        "ultimo_hash_fed":    None,
        "alertas_enviadas":   0,
        "calendario_alertas": {},
        "brief_enviado_hoy":  None,
        "inicio_sesion":      datetime.now().isoformat(),
    }


def guardar_estado(estado: dict):
    estado["noticias_vistas"] = estado["noticias_vistas"][-1000:]
    estado["ultima_revision"] = datetime.now().isoformat()
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def hash_texto(texto: str) -> str:
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()


# ── Módulo 0: Morning Brief ───────────────────────────────────────
def verificar_morning_brief(estado: dict):
    """
    Envía el Morning Brief a las 8:00 AM si no se envió hoy.
    Solo actúa en la ventana 7:55-8:30 AM para mayor seguridad.
    """
    ahora = datetime.now()
    hoy   = ahora.strftime("%Y-%m-%d")

    # Verificar si ya se envió hoy
    if estado.get("brief_enviado_hoy") == hoy:
        return

    # Ventana de envío: 7:55 AM a 8:30 AM
    if not (7 <= ahora.hour <= 8 and ahora.minute >= 55 or ahora.hour == 8 and ahora.minute <= 30):
        if ahora.hour != 8:
            return

    try:
        from morning_brief import generar_y_enviar_brief
        log.info("\n[0] MORNING BRIEF — generando análisis diario...")
        exito = generar_y_enviar_brief(forzar=False)
        if exito:
            estado["brief_enviado_hoy"] = hoy
            log.info("  ✅ Morning Brief enviado")
    except Exception as e:
        log.error(f"  Error Morning Brief: {e}")


# ── Módulo 1: Noticias con filtro de alto impacto ────────────────
def escanear_noticias(estado: dict) -> list:
    """
    Usa news_scanner v4:
    - Score mínimo 70/100
    - Solo urgencia MAXIMA y ALTA
    - Sin categoría MEDIA (que generaba ruido)
    """
    try:
        eventos = escanear_noticias_kairos(estado["noticias_vistas"])
        log.info(f"    Eventos alto impacto (score≥{SCORE_MINIMO_ALERTA}): {len(eventos)}")
        return eventos
    except Exception as e:
        log.error(f"    Error news_scanner: {e}")
        return []


# ── Módulo 2: Calendario económico ───────────────────────────────
def verificar_calendario(estado: dict) -> list:
    """Alertas pre-evento: 24h antes de FOMC, 6h antes de CPI/NFP."""
    try:
        alertas = verificar_alertas_calendario(estado)
        log.info(f"    Alertas calendario: {len(alertas)}")
        return alertas
    except Exception as e:
        log.error(f"    Error calendario: {e}")
        return []


# ── Módulo 3: Mercados con contexto causal ────────────────────────
def monitorear_mercados(regimen: dict = None) -> list:
    """Detecta movimientos anómalos con patrón macro (risk-off, etc.)"""
    try:
        mensajes = ejecutar_market_alert(regimen)
        log.info(f"    Alertas mercado: {len(mensajes)}")
        return mensajes
    except Exception as e:
        log.error(f"    Error market_alert: {e}")
        return []


# ── Módulo 4: Detector FED ────────────────────────────────────────
def detectar_nuevo_fed(estado: dict):
    """Solo alerta si hay comunicado FED genuinamente nuevo."""
    try:
        from fed_scraper import obtener_comunicado_fed
        comunicado  = obtener_comunicado_fed()
        if not comunicado:
            return None

        contenido   = comunicado.get("contenido", "") or comunicado.get("titulo", "")
        hash_actual = hash_texto(contenido[:1000])

        if hash_actual == estado.get("ultimo_hash_fed"):
            log.info("  FED: mismo comunicado — sin cambios")
            return None

        log.info("  FED: NUEVO COMUNICADO DETECTADO")
        estado["ultimo_hash_fed"] = hash_actual
        return {
            "tipo":       "COMUNICADO_FED",
            "comunicado": comunicado,
            "timestamp":  datetime.now().isoformat(),
        }
    except Exception as e:
        log.warning(f"  Error FED: {e}")
        return None


# ── Procesador de eventos ─────────────────────────────────────────
def procesar_evento(evento: dict, datos_macro=None, regimen=None):
    tipo = evento.get("tipo", "")

    # ── Noticia de alto impacto
    if "titular" in evento:
        score = evento.get("score", 0)
        if score < SCORE_MINIMO_ALERTA:
            log.info(f"  DESCARTADO score:{score} — {evento['titular'][:50]}")
            return
        mensaje = formatear_alerta_noticia(evento)
        enviar_alerta_telegram(mensaje)
        log.info(f"  ✅ score:{score} — {evento['titular'][:50]}")

    # ── Alerta de calendario
    elif tipo == "CALENDARIO":
        enviar_alerta_telegram(evento["mensaje"])

    # ── Alerta de mercado
    elif tipo in ("ALERTA_MERCADO", "PATRON_MACRO"):
        enviar_alerta_telegram(evento["mensaje"])

    # ── Nuevo comunicado FED
    elif tipo == "COMUNICADO_FED":
        try:
            from analizador import analizar_comunicado
            comunicado = evento["comunicado"]
            analisis   = analizar_comunicado(
                comunicado,
                {"datos": datos_macro or {}, "regimen": regimen or {}}
            )

            tono  = "NEUTRO"
            score = 0
            for linea in analisis.split('\n'):
                if "Clasificacion:" in linea or "Clasificación:" in linea:
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

            emojis = {
                "HAWKISH FUERTE":"🔴🔴","HAWKISH LEVE":"🔴",
                "NEUTRO":"🟡",
                "DOVISH LEVE":"🟢","DOVISH FUERTE":"🟢🟢",
            }
            mensaje = (
                f"🏛️ KAIROS — NUEVO COMUNICADO FED\n{'='*38}\n"
                f"📄 {comunicado.get('titulo','')}\n\n"
                f"🎯 Tono IA: {emojis.get(tono,'⚪')} {tono}\n"
                f"📊 Score: {'+' if score >= 0 else ''}{score} / ±5\n\n"
                f"kairos-markets.streamlit.app"
            )
            enviar_alerta_telegram(mensaje)
            log.info(f"  Alerta FED — {tono} Score:{score}")

        except Exception as e:
            log.error(f"  Error analizando FED: {e}")


# ── Loop principal ────────────────────────────────────────────────
def run_monitor(intervalo: int = INTERVALO_SEGUNDOS):
    log.info("=" * 50)
    log.info("🚀 KAIROS MONITOR ACTIVO — 8 módulos")
    log.info(f"   [0] Morning Brief  — 8:00 AM diario")
    log.info(f"   [1] Noticias       — score≥{SCORE_MINIMO_ALERTA}, MAXIMA+ALTA")
    log.info(f"   [2] Calendario     — anticipa eventos macro")
    log.info(f"   [3] Mercados       — patrones macro causales")
    log.info(f"   [4] FED            — nuevo comunicado genuino")
    log.info(f"   [5] Event Brief    — 30 min antes de eventos críticos")
    log.info(f"   [6] Closing Brief  — 4:00 PM ET cierre de sesión")
    log.info(f"   [7] Weekly Brief   — viernes 6:00 PM resumen semanal")
    log.info(f"   [8] Feedback       — 4:15 PM evaluación de aciertos automática")
    log.info(f"   Intervalo: cada {intervalo//60} minutos")
    log.info("=" * 50)

    # Resumen semanal al arrancar
    try:
        resumen = resumen_semana()
        enviar_alerta_telegram(
            f"🚀 KAIROS MONITOR INICIADO\n{'='*38}\n\n{resumen}"
        )
    except Exception as e:
        log.warning(f"Error resumen inicial: {e}")

    estado       = cargar_estado()
    datos_macro  = None
    regimen      = None
    ultima_macro = datetime.min
    ciclo        = 0

    while True:
        ciclo += 1
        log.info(f"\n{'─'*50}")
        log.info(f"CICLO #{ciclo} — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        log.info(f"{'─'*50}")

        # Macro cada hora
        if datetime.now() - ultima_macro > timedelta(hours=1):
            try:
                from macro import obtener_datos_macro, evaluar_regimen_macro
                datos_macro  = obtener_datos_macro()
                regimen      = evaluar_regimen_macro(datos_macro)
                ultima_macro = datetime.now()
                log.info(f"Macro: {regimen.get('regimen','?')}")
                # Calcular y guardar targets de precio
                try:
                    from news_scanner import SITUACIONES_ACTIVAS
                    sits = [{"nombre":s["nombre"],"tipo":s["tipo"]}
                            for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
                    targets = calcular_todos_los_targets(
                        regimen_macro=regimen.get("regimen","NEUTRO"),
                        tono_fed="HAWKISH LEVE",
                        situaciones_activas=sits
                    )
                    guardar_prediccion(targets)
                    log.info(f"  Targets calculados para {len(targets)} activos")

                    # Motor de convergencia — señales reales
                    try:
                        señales_conv = analizar_mercado_completo(
                            regimen=regimen,
                            tono_fed="HAWKISH LEVE",
                            situaciones=sits,
                            generar_narrativas=True,
                        )
                        n_acc = señales_conv.get("n_accionables",0)
                        log.info(f"  Convergencia: {n_acc} señales accionables")

                        # Enviar al canal si hay señales fuertes
                        if n_acc > 0:
                            from alertas import enviar_alerta_telegram
                            msg = formatear_señales_telegram(señales_conv)
                            if msg:
                                enviar_alerta_telegram(msg)
                                estado["alertas_enviadas"] += 1
                    except Exception as se:
                        log.warning(f"  Error convergencia: {se}")
                except Exception as te:
                    log.warning(f"  Error targets: {te}")
            except Exception as e:
                log.warning(f"Error macro: {e}")

        # [0] Morning Brief
        log.info("\n[0] MORNING BRIEF")
        verificar_morning_brief(estado)

        # [1] Noticias
        log.info(f"\n[1] NOTICIAS — score≥{SCORE_MINIMO_ALERTA}")
        try:
            eventos = escanear_noticias(estado)
            for e in eventos:
                procesar_evento(e, datos_macro, regimen)
                estado["alertas_enviadas"] += 1
        except Exception as e:
            log.error(f"Error noticias: {e}")

        # [2] Calendario
        log.info("\n[2] CALENDARIO")
        try:
            cal_alertas = verificar_calendario(estado)
            for alerta in cal_alertas:
                procesar_evento(
                    {"tipo": "CALENDARIO", "mensaje": alerta["mensaje"]},
                    datos_macro, regimen
                )
                estado["alertas_enviadas"] += 1
        except Exception as e:
            log.error(f"Error calendario: {e}")

        # [3] Mercados
        log.info("\n[3] MERCADOS")
        try:
            mensajes_mkt = monitorear_mercados(regimen)
            for m in mensajes_mkt:
                procesar_evento(m, datos_macro, regimen)
                estado["alertas_enviadas"] += 1
        except Exception as e:
            log.error(f"Error mercados: {e}")

        # [4] FED
        log.info("\n[4] FED")
        try:
            fed = detectar_nuevo_fed(estado)
            if fed:
                procesar_evento(fed, datos_macro, regimen)
                estado["alertas_enviadas"] += 1
        except Exception as e:
            log.error(f"Error FED: {e}")

        # [5] Event Brief — 30 min antes de eventos críticos
        log.info("\n[5] EVENT BRIEF")
        try:
            n_briefs = verificar_y_enviar_event_briefs()
            if n_briefs > 0:
                estado["alertas_enviadas"] += n_briefs
                log.info(f"  ✅ {n_briefs} Event Briefs enviados")
            else:
                log.info("  ✓ Sin eventos en ventana de alerta")
        except Exception as e:
            log.error(f"Error event_brief: {e}")

        # [6] Closing Brief — 4:00 PM ET
        log.info("\n[6] CLOSING BRIEF")
        try:
            generar_y_enviar_closing()
        except Exception as e:
            log.error(f"Error closing brief: {e}")

        # [7] Weekly Brief — viernes 6:00 PM
        log.info("\n[7] WEEKLY BRIEF")
        try:
            generar_y_enviar_weekly()
        except Exception as e:
            log.error(f"Error weekly brief: {e}")

        # [8] Feedback automático — 4:15 PM
        log.info("\n[8] FEEDBACK SISTEMA")
        try:
            ejecutar_feedback_diario()
        except Exception as e:
            log.error(f"Error feedback: {e}")

        guardar_estado(estado)
        log.info(f"\n✅ Ciclo #{ciclo} — {estado['alertas_enviadas']} alertas totales")
        log.info(f"⏳ Próxima revisión en {intervalo//60} minutos...")
        time.sleep(intervalo)


# ── Test ──────────────────────────────────────────────────────────
def run_test():
    print(f"\n🧪 KAIROS MONITOR — TEST\n{'='*50}")
    estado = cargar_estado()

    # [0] Morning Brief
    print("\n[0] MORNING BRIEF")
    brief_file = "data/ultimo_brief.json"
    import json, os
    if os.path.exists(brief_file):
        with open(brief_file) as f:
            bd = json.load(f)
        print(f"  → Brief del: {bd.get('fecha','?')} — "
              f"{'✅ HOY' if bd.get('fecha')==__import__('datetime').datetime.now().strftime('%Y-%m-%d') else '📅 anterior'}")
    else:
        print("  → Ejecutar: python src/morning_brief.py --forzar")

    # [1] Noticias
    print(f"\n[1] NOTICIAS (score≥{SCORE_MINIMO_ALERTA})")
    try:
        eventos = escanear_noticias(estado)
        print(f"→ {len(eventos)} eventos de alto impacto")
        for e in eventos[:3]:
            print(f"  📰 {e['titular'][:70]}")
            print(f"     Score: {e['score']}/100 | {e['urgencia']}")
    except Exception as e:
        print(f"  Error: {e}")

    # [2] Calendario
    print("\n[2] CALENDARIO")
    try:
        from calendario_eco import obtener_eventos_proximos
        proximos = obtener_eventos_proximos(dias=30)
        print(f"→ {len(proximos)} eventos próximos:")
        for ev in proximos[:3]:
            emoji = {"CRÍTICO":"🚨","ALTO":"⚠️"}.get(ev["impacto"],"📡")
            print(f"  {emoji} {ev['evento']} — {ev['dias_restantes']} días")
    except Exception as e:
        print(f"  Error: {e}")

    # [3] Mercados
    print("\n[3] MERCADOS")
    try:
        from market_alert import obtener_snapshot
        snap = obtener_snapshot()
        print(f"→ Régimen: {snap['regimen_mercado']} | Alertas: {snap['n_alertas']}")
        for nombre, info in snap["datos"].items():
            pct = info["cambio_pct"]
            print(f"  {nombre:8} {info['precio']:>10}  {'+' if pct>0 else ''}{pct}%")
    except Exception as e:
        print(f"  Error: {e}")

    # [4] FED
    print("\n[4] FED")
    try:
        fed = detectar_nuevo_fed(estado)
        print(f"  {'🔴 NUEVO: '+fed['comunicado'].get('titulo','') if fed else '✓ Sin cambios'}")
    except Exception as e:
        print(f"  Error: {e}")

    # [5] Event Brief
    print("\n[5] EVENT BRIEF")
    try:
        from calendario_eco import obtener_eventos_proximos
        eventos_prox = obtener_eventos_proximos(dias=2)
        criticos = [e for e in eventos_prox if e["impacto"]=="CRÍTICO"]
        if criticos:
            for ev in criticos[:2]:
                print(f"  🎯 {ev['evento']} — en {int(ev['horas_restantes'])}h")
        else:
            print("  ✓ Sin eventos críticos en las próximas 48h")
    except Exception as e:
        print(f"  Error: {e}")

    # [6] Closing Brief
    print("\n[6] CLOSING BRIEF")
    cl_files = sorted(__import__('glob').glob("outputs/closing_brief_*.txt"), reverse=True)
    if cl_files:
        nombre_cl = __import__('os').path.basename(cl_files[0])
        print(f"  ✅ Último: {nombre_cl}")
    else:
        print("  → Se genera a las 4:00 PM ET")

    # [7] Weekly Brief
    print("\n[7] WEEKLY BRIEF")
    wk_files = sorted(__import__('glob').glob("outputs/weekly_brief_*.txt"), reverse=True)
    if wk_files:
        nombre_wk = __import__('os').path.basename(wk_files[0])
        print(f"  ✅ Último: {nombre_wk}")
    else:
        print("  → Se genera los viernes a las 6:00 PM ET")

    # [8] Feedback
    print("\n[8] FEEDBACK SISTEMA")
    fb_file = "data/feedback_estadisticas.json"
    if os.path.exists(fb_file):
        with open(fb_file) as f:
            fb = json.load(f)
        n    = fb.get("total_evaluaciones",0)
        prec = fb.get("precision_dir_24h",0)
        print(f"  Evaluaciones: {n} | Precisión 24h: {prec}%")
    else:
        print("  → Acumulando datos (primer día)")

    guardar_estado(estado)
    print(f"\n{'='*50}")
    print("✅ Test completado — todos los módulos verificados")


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KAIROS Monitor")
    parser.add_argument("--test",      action="store_true")
    parser.add_argument("--intervalo", type=int, default=INTERVALO_SEGUNDOS)
    args = parser.parse_args()

    if args.test:
        run_test()
    else:
        run_monitor(args.intervalo)
