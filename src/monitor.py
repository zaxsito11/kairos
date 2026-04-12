# monitor.py — KAIROS
# Sistema de vigilancia automática de eventos con impacto en mercados.
# CONCEPTO: detecta lo que va a mover los mercados ANTES de que ocurra.

import os
import sys
import time
import hashlib
import json
import logging
from datetime import datetime, timedelta

import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))

from news_scanner import escanear_noticias_kairos, formatear_alerta_noticia
from alertas import enviar_alerta_telegram

# ── Configuración ─────────────────────────────────────────────────
INTERVALO_SEGUNDOS     = 300
LOG_FILE               = "outputs/monitor.log"
ESTADO_FILE            = "data/monitor_estado.json"

# Umbrales alertas de mercado
UMBRAL_VIX_SPIKE       = 15.0
UMBRAL_SPX_CAIDA       = -1.5
UMBRAL_DXY_MOVIMIENTO  =  0.7
UMBRAL_GOLD_MOVIMIENTO =  1.2
UMBRAL_WTI_MOVIMIENTO  =  2.0

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
            log.warning(f"Error cargando estado: {e}. Creando estado nuevo.")
    return {
        "noticias_vistas":  [],
        "ultimo_hash_fed":  None,
        "alertas_enviadas": 0,
        "inicio_sesion":    datetime.now().isoformat(),
    }


def guardar_estado(estado: dict):
    estado["noticias_vistas"] = estado["noticias_vistas"][-1000:]
    estado["ultima_revision"] = datetime.now().isoformat()
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def hash_texto(texto: str) -> str:
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()


# ── Módulo 1: Noticias (usa news_scanner inteligente) ────────────
def escanear_noticias(estado: dict) -> list:
    """
    Usa news_scanner_kairos que aplica:
    - Filtro de absorción de mercado
    - Score de relevancia 0-100
    - Predicciones basadas en precedentes históricos
    - Solo eventos con ventana de oportunidad activa
    """
    try:
        eventos = escanear_noticias_kairos(estado["noticias_vistas"])
        log.info(f"    Eventos con ventana activa: {len(eventos)}")
        return eventos
    except Exception as e:
        log.error(f"    Error en news_scanner: {e}")
        return []


# ── Módulo 2: Monitor de mercados ─────────────────────────────────
def monitorear_mercados() -> list:
    alertas = []
    tickers = {
        "VIX":  "^VIX",
        "SPX":  "^GSPC",
        "DXY":  "DX-Y.NYB",
        "Gold": "GC=F",
        "WTI":  "CL=F",
    }

    for nombre, ticker in tickers.items():
        try:
            datos = yf.Ticker(ticker).history(period="2d", interval="1d")
            if datos.empty or len(datos) < 2:
                continue

            hoy   = float(datos["Close"].iloc[-1])
            ayer  = float(datos["Close"].iloc[-2])
            pct   = ((hoy - ayer) / ayer) * 100
            signo = "+" if pct > 0 else ""

            disparado = (
                (nombre == "VIX"  and pct >= UMBRAL_VIX_SPIKE)  or
                (nombre == "SPX"  and pct <= UMBRAL_SPX_CAIDA)  or
                (nombre == "DXY"  and abs(pct) >= UMBRAL_DXY_MOVIMIENTO)  or
                (nombre == "Gold" and abs(pct) >= UMBRAL_GOLD_MOVIMIENTO) or
                (nombre == "WTI"  and abs(pct) >= UMBRAL_WTI_MOVIMIENTO)
            )

            mensajes = {
                "VIX":  f"⚡ VIX SPIKE: +{round(pct,1)}% (nivel {round(hoy,1)}) — Risk-off activado",
                "SPX":  f"📉 SPX CAÍDA: {round(pct,1)}% (nivel {round(hoy,0)}) — Presión vendedora",
                "DXY":  f"💵 DXY: {signo}{round(pct,1)}% (nivel {round(hoy,2)}) — Movimiento relevante",
                "Gold": f"🥇 Gold: {signo}{round(pct,1)}% (nivel {round(hoy,0)}) — Demanda de refugio",
                "WTI":  f"🛢️ WTI: {signo}{round(pct,1)}% (nivel {round(hoy,2)}) — Movimiento relevante",
            }

            log.info(f"  {nombre}: {signo}{round(pct,2)}% {'⚠️ ALERTA' if disparado else '✓ normal'}")

            if disparado:
                alertas.append({
                    "tipo":      f"MERCADO_{nombre}",
                    "activo":    nombre,
                    "valor":     round(hoy, 2),
                    "cambio":    round(pct, 2),
                    "mensaje":   mensajes[nombre],
                    "timestamp": datetime.now().isoformat(),
                })

        except Exception as e:
            log.warning(f"  Error en {nombre}: {e}")

    return alertas


# ── Módulo 3: Detector FED ────────────────────────────────────────
def detectar_nuevo_fed(estado: dict):
    try:
        from fed_scraper import obtener_comunicado_fed
        comunicado = obtener_comunicado_fed()
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

    # ── Noticia con ventana activa (viene de news_scanner)
    if tipo == "NOTICIA" or "titular" in evento:
        mensaje = formatear_alerta_noticia(evento)
        enviar_alerta_telegram(mensaje)

    # ── Alerta de mercado
    elif tipo.startswith("MERCADO_"):
        r_texto = f"\n📊 Régimen: {regimen.get('regimen','?')}" if regimen else ""
        mensaje = (
            f"⚠️ KAIROS — ALERTA MERCADO\n{'='*38}\n"
            f"{evento['mensaje']}{r_texto}\n\n"
            f"kairos-markets.streamlit.app"
        )
        enviar_alerta_telegram(mensaje)

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
                "HAWKISH FUERTE": "🔴🔴", "HAWKISH LEVE": "🔴",
                "NEUTRO":         "🟡",
                "DOVISH LEVE":    "🟢",   "DOVISH FUERTE": "🟢🟢",
            }
            mensaje = (
                f"🏛️ KAIROS — NUEVO COMUNICADO FED\n{'='*38}\n"
                f"📄 {comunicado.get('titulo','')}\n\n"
                f"🎯 Tono: {emojis.get(tono,'⚪')} {tono}\n"
                f"📊 Score: {'+' if score >= 0 else ''}{score} / ±5\n\n"
                f"kairos-markets.streamlit.app"
            )
            enviar_alerta_telegram(mensaje)
            log.info(f"  Alerta FED enviada — {tono} Score:{score}")

        except Exception as e:
            log.error(f"  Error analizando FED: {e}")


# ── Loop principal ────────────────────────────────────────────────
def run_monitor(intervalo: int = INTERVALO_SEGUNDOS):
    log.info("=" * 50)
    log.info("🚀 KAIROS MONITOR ACTIVO")
    log.info(f"   Intervalo: cada {intervalo//60} minutos")
    log.info(f"   Scanner: news_scanner con filtro de absorción")
    log.info(f"   Concepto: solo eventos NO absorbidos por el mercado")
    log.info("=" * 50)

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

        # Actualizar macro cada hora
        if datetime.now() - ultima_macro > timedelta(hours=1):
            try:
                from macro import obtener_datos_macro, evaluar_regimen_macro
                datos_macro  = obtener_datos_macro()
                regimen      = evaluar_regimen_macro(datos_macro)
                ultima_macro = datetime.now()
                log.info(f"Macro: {regimen.get('regimen','?')}")
            except Exception as e:
                log.warning(f"Error macro: {e}")

        # [1] Noticias con filtro de absorción
        log.info("\n[1] NOTICIAS — filtro de absorción activo")
        try:
            eventos = escanear_noticias(estado)
            for e in eventos:
                procesar_evento(e, datos_macro, regimen)
                estado["alertas_enviadas"] += 1
        except Exception as e:
            log.error(f"Error noticias: {e}")

        # [2] Mercados
        log.info("\n[2] MERCADOS")
        try:
            alertas = monitorear_mercados()
            for a in alertas:
                procesar_evento(a, datos_macro, regimen)
                estado["alertas_enviadas"] += 1
        except Exception as e:
            log.error(f"Error mercados: {e}")

        # [3] FED
        log.info("\n[3] FED")
        try:
            fed = detectar_nuevo_fed(estado)
            if fed:
                procesar_evento(fed, datos_macro, regimen)
                estado["alertas_enviadas"] += 1
        except Exception as e:
            log.error(f"Error FED: {e}")

        guardar_estado(estado)
        log.info(f"\n✅ Ciclo #{ciclo} — {estado['alertas_enviadas']} alertas totales")
        log.info(f"⏳ Próxima revisión en {intervalo//60} minutos...")
        time.sleep(intervalo)


# ── Test: una pasada ──────────────────────────────────────────────
def run_test():
    print("\n🧪 KAIROS MONITOR — MODO TEST\n" + "="*50)
    estado = cargar_estado()

    print("\n[1] NOTICIAS con filtro de absorción")
    eventos = escanear_noticias(estado)
    print(f"→ {len(eventos)} eventos con ventana activa")
    for e in eventos[:5]:
        print(f"\n  📰 {e['titular'][:75]}")
        print(f"     Score: {e['score']}/100 | Urgencia: {e['urgencia']}")
        print(f"     {e['absorcion']['estado']}")
        if e.get("precedente"):
            datos = e["precedente"]["datos"]
            print(f"     Precedente: {datos['condicion']}")
            for activo, pred in list(datos["prediccion"].items())[:3]:
                print(f"       → {activo}: {pred['promedio_24h']} ({pred['probabilidad']})")

    print("\n[2] MERCADOS")
    alertas = monitorear_mercados()
    if alertas:
        for a in alertas:
            print(f"  ⚠️  {a['mensaje']}")
    else:
        print("  ✓ Sin movimientos anómalos")

    print("\n[3] FED")
    fed = detectar_nuevo_fed(estado)
    if fed:
        print(f"  🔴 NUEVO: {fed['comunicado'].get('titulo','')}")
    else:
        print("  ✓ Sin nuevo comunicado")

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
