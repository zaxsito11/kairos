# monitor.py — KAIROS
# Sistema de vigilancia automática de eventos con impacto en mercados.
# KAIROS es selectivo: solo alerta lo que puede mover mercados >1%

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
        "alertas_descartadas": 0,
        "calendario_alertas": {},
        "inicio_sesion":      datetime.now().isoformat(),
    }


def guardar_estado(estado: dict):
    estado["noticias_vistas"] = estado["noticias_vistas"][-1000:]
    estado["ultima_revision"] = datetime.now().isoformat()
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def hash_texto(texto: str) -> str:
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()


# ── Módulo 1: Noticias con filtro de alto impacto ────────────────
def escanear_noticias(estado: dict) -> list:
    """
    Usa news_scanner v4 que solo retorna eventos con:
    - Score >= 70/100
    - Urgencia MAXIMA o ALTA únicamente
    - Sin categoría MEDIA (que generaba ruido)
    """
    try:
        eventos = escanear_noticias_kairos(estado["noticias_vistas"])
        log.info(f"    Eventos de alto impacto (score≥{SCORE_MINIMO_ALERTA}): {len(eventos)}")
        return eventos
    except Exception as e:
        log.error(f"    Error en news_scanner: {e}")
        return []


# ── Módulo 2: Calendario económico ───────────────────────────────
def verificar_calendario(estado: dict) -> list:
    """Alertas pre-evento: 24h antes de FOMC, 6h antes de CPI/NFP."""
    try:
        alertas = verificar_alertas_calendario(estado)
        log.info(f"    Alertas de calendario: {len(alertas)}")
        return alertas
    except Exception as e:
        log.error(f"    Error en calendario: {e}")
        return []


# ── Módulo 3: Mercados con contexto causal ────────────────────────
def monitorear_mercados(regimen: dict = None) -> list:
    """Detecta movimientos anómalos con patrón macro (risk-off, etc.)"""
    try:
        mensajes = ejecutar_market_alert(regimen)
        log.info(f"    Alertas de mercado: {len(mensajes)}")
        return mensajes
    except Exception as e:
        log.error(f"    Error en market_alert: {e}")
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

    # ── Noticia de alto impacto (news_scanner v4)
    if "titular" in evento:
        score = evento.get("score", 0)
        # Doble verificación — nunca mandar score bajo a Telegram
        if score < SCORE_MINIMO_ALERTA:
            log.info(f"  DESCARTADO (score {score}): {evento['titular'][:50]}")
            return
        mensaje = formatear_alerta_noticia(evento)
        enviar_alerta_telegram(mensaje)
        log.info(f"  ✅ Alerta enviada score:{score} — {evento['titular'][:50]}")

    # ── Alerta de calendario
    elif tipo == "CALENDARIO":
        enviar_alerta_telegram(evento["mensaje"])

    # ── Alerta de mercado (market_alert)
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
                "HAWKISH FUERTE":"🔴🔴", "HAWKISH LEVE":"🔴",
                "NEUTRO":"🟡",
                "DOVISH LEVE":"🟢",     "DOVISH FUERTE":"🟢🟢",
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
    log.info("🚀 KAIROS MONITOR ACTIVO — 4 fuentes")
    log.info(f"   [1] Noticias — score mínimo {SCORE_MINIMO_ALERTA}/100 (sin ruido)")
    log.info(f"   [2] Calendario — anticipación de eventos macro")
    log.info(f"   [3] Mercados — patrones macro con contexto causal")
    log.info(f"   [4] FED — nuevo comunicado genuino")
    log.info(f"   Intervalo: cada {intervalo//60} minutos")
    log.info("=" * 50)

    # Resumen semanal al arrancar
    try:
        resumen = resumen_semana()
        enviar_alerta_telegram(
            f"🚀 KAIROS MONITOR INICIADO\n{'='*38}\n\n{resumen}"
        )
    except Exception as e:
        log.warning(f"Error enviando resumen: {e}")

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
            except Exception as e:
                log.warning(f"Error macro: {e}")

        # [1] Noticias
        log.info(f"\n[1] NOTICIAS — solo score≥{SCORE_MINIMO_ALERTA}")
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
                log.info(f"  Alerta: {alerta['clave_alerta']}")
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

        guardar_estado(estado)
        log.info(f"\n✅ Ciclo #{ciclo} — {estado['alertas_enviadas']} alertas enviadas")
        log.info(f"⏳ Próxima revisión en {intervalo//60} minutos...")
        time.sleep(intervalo)


# ── Test ──────────────────────────────────────────────────────────
def run_test():
    print(f"\n🧪 KAIROS MONITOR — TEST\n" + "="*50)
    estado = cargar_estado()

    print(f"\n[1] NOTICIAS (score≥{SCORE_MINIMO_ALERTA})")
    eventos = escanear_noticias(estado)
    print(f"→ {len(eventos)} eventos de alto impacto")
    for e in eventos[:3]:
        print(f"\n  📰 {e['titular'][:70]}")
        print(f"     Score: {e['score']}/100 | {e['urgencia']}")
        print(f"     {e['absorcion']['estado']}")

    print("\n[2] CALENDARIO")
    from calendario_eco import obtener_eventos_proximos
    proximos = obtener_eventos_proximos(dias=30)
    print(f"→ {len(proximos)} eventos próximos:")
    for ev in proximos[:3]:
        emoji = {"CRÍTICO":"🚨","ALTO":"⚠️"}.get(ev["impacto"],"📡")
        print(f"  {emoji} {ev['evento']} — {ev['dias_restantes']} días")

    print("\n[3] MERCADOS")
    from market_alert import obtener_snapshot
    snap = obtener_snapshot()
    print(f"→ Régimen: {snap['regimen_mercado']} | Alertas: {snap['n_alertas']}")
    for nombre, info in snap["datos"].items():
        pct = info["cambio_pct"]
        print(f"  {nombre:8} {info['precio']:>10}  {'+' if pct>0 else ''}{pct}%")

    print("\n[4] FED")
    fed = detectar_nuevo_fed(estado)
    print(f"  {'🔴 NUEVO: ' + fed['comunicado'].get('titulo','') if fed else '✓ Sin cambios'}")

    guardar_estado(estado)
    print("\n✅ Test completado")


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
