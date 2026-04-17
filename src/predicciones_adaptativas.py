# predicciones_adaptativas.py — KAIROS
# Si llega un evento score≥90 que cambia la narrativa,
# cancela las predicciones actuales y genera nuevas.
#
# PROBLEMA QUE RESUELVE:
#   "Trump Says Iran Deal" score 99 → el contexto cambió completamente
#   pero KAIROS seguía con predicciones basadas en conflicto activo
#
# SOLUCIÓN:
#   Detectar eventos que INVALIDAN el contexto actual
#   → Cancelar predicciones del día
#   → Generar nuevas predicciones con el nuevo contexto
#   → Alertar al canal: "⚠️ Predicciones actualizadas por nuevo evento"

import os, sys, json, logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

LOG_FILE     = "outputs/predicciones_adaptativas.log"
CAMBIOS_FILE = "data/cambios_narrativa.json"

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
log = logging.getLogger("KAIROS.adaptativo")


# ── Eventos que CAMBIAN la narrativa ─────────────────────────────
CAMBIOS_NARRATIVA = [
    {
        "patron":    ["ceasefire","cese al fuego","paz","peace deal","acuerdo iran",
                      "iran deal","negociaciones exitosas","tratado"],
        "contexto_invalida": ["CONFLICTO_ARMADO", "GEOPOLITICA_CONFLICTO"],
        "nuevo_contexto":    "DESESCALADA",
        "descripcion":       "Acuerdo/paz detectado — prima de riesgo se desinfla",
        "activos_afectados": {
            "WTI":  "BAJA",    # precio petróleo cae sin prima de guerra
            "Gold": "BAJA",    # cae demanda refugio
            "VIX":  "BAJA",    # cae volatilidad
            "SPX":  "SUBE",    # risk-on
            "NDX":  "SUBE",    # tech rebota
            "BTC":  "SUBE",    # risk-on
        }
    },
    {
        "patron":    ["invasion","ataque","attack","strike","escalation",
                      "guerra declarada","war declared","bomba","missile"],
        "contexto_invalida": ["NEUTRO", "DESESCALADA"],
        "nuevo_contexto":    "ESCALADA",
        "descripcion":       "Escalada detectada — prima de riesgo sube",
        "activos_afectados": {
            "WTI":  "SUBE",
            "Gold": "SUBE",
            "VIX":  "SUBE",
            "SPX":  "BAJA",
            "NDX":  "BAJA",
            "BTC":  "BAJA",
        }
    },
    {
        "patron":    ["fed rate cut","recorte tasas","dovish pivot","powell dovish",
                      "rate cut","bajada tipos"],
        "contexto_invalida": ["HAWKISH"],
        "nuevo_contexto":    "DOVISH_SORPRESA",
        "descripcion":       "Giro dovish FED detectado — expansión de valuaciones",
        "activos_afectados": {
            "SPX":    "SUBE",
            "NDX":    "SUBE",
            "Gold":   "SUBE",
            "DXY":    "BAJA",
            "UST10Y": "BAJA",
            "BTC":    "SUBE",
        }
    },
    {
        "patron":    ["emergency rate hike","subida emergencia","hawkish surprise",
                      "inflation spike","inflacion dispara"],
        "contexto_invalida": ["NEUTRO", "DOVISH"],
        "nuevo_contexto":    "HAWKISH_SORPRESA",
        "descripcion":       "Sorpresa hawkish FED — contracción de valuaciones",
        "activos_afectados": {
            "SPX":    "BAJA",
            "NDX":    "BAJA",
            "DXY":    "SUBE",
            "UST10Y": "SUBE",
            "Gold":   "BAJA",
        }
    },
    {
        "patron":    ["acuerdo comercial","trade deal","tariff removed","aranceles retirados",
                      "china deal","us china agreement"],
        "contexto_invalida": ["TENSION_COMERCIAL", "COMERCIO_ARANCELES"],
        "nuevo_contexto":    "ACUERDO_COMERCIAL",
        "descripcion":       "Acuerdo comercial — normalización de cadenas",
        "activos_afectados": {
            "SPX":    "SUBE",
            "NDX":    "SUBE",
            "DXY":    "BAJA",
            "Gold":   "BAJA",
        }
    },
]


def detectar_cambio_narrativa(evento: dict) -> dict | None:
    """
    Detecta si un evento invalida el contexto actual de predicciones.

    Args:
        evento: dict con 'titular', 'score', 'urgencia'

    Returns:
        dict con el cambio detectado o None
    """
    titular = evento.get("titular","").lower()
    score   = evento.get("score", 0)

    # Solo procesar eventos de muy alto impacto
    if score < 88:
        return None

    for cambio in CAMBIOS_NARRATIVA:
        if any(patron in titular for patron in cambio["patron"]):
            return {
                "titular":           evento.get("titular",""),
                "score":             score,
                "nuevo_contexto":    cambio["nuevo_contexto"],
                "descripcion":       cambio["descripcion"],
                "activos_afectados": cambio["activos_afectados"],
                "timestamp":         datetime.now().isoformat(),
            }

    return None


def ya_procesado_hoy(clave: str) -> bool:
    """Evita procesar el mismo cambio dos veces en el día."""
    if not os.path.exists(CAMBIOS_FILE):
        return False
    try:
        with open(CAMBIOS_FILE) as f:
            cambios = json.load(f)
        hoy = datetime.now().strftime("%Y-%m-%d")
        return any(c.get("fecha") == hoy and c.get("clave") == clave
                   for c in cambios)
    except Exception:
        return False


def guardar_cambio(cambio: dict, clave: str):
    cambios = []
    if os.path.exists(CAMBIOS_FILE):
        try:
            with open(CAMBIOS_FILE) as f:
                cambios = json.load(f)
        except Exception:
            pass
    cambios.append({**cambio, "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "clave": clave})
    cambios = cambios[-30:]  # máximo 30 días
    with open(CAMBIOS_FILE, "w") as f:
        json.dump(cambios, f, ensure_ascii=True, indent=2)


def regenerar_predicciones(cambio: dict) -> dict:
    """
    Genera nuevas predicciones con el contexto actualizado.
    Cancela las predicciones del día y genera nuevas.
    """
    log.info(f"\n⚡ REGENERANDO PREDICCIONES")
    log.info(f"   Contexto: {cambio['nuevo_contexto']}")
    log.info(f"   Evento:   {cambio['titular'][:60]}")

    activos_afectados = cambio["activos_afectados"]
    nuevas_preds      = {}

    try:
        import yfinance as yf
        tickers = {
            "SPX":"^GSPC","NDX":"^NDX","Gold":"GC=F","Silver":"SI=F",
            "WTI":"CL=F","BTC":"BTC-USD","DXY":"DX-Y.NYB",
            "VIX":"^VIX","UST10Y":"^TNX",
        }

        for activo, dir_nueva in activos_afectados.items():
            ticker = tickers.get(activo)
            if not ticker:
                continue
            try:
                precio = float(yf.Ticker(ticker).fast_info.last_price)
                nuevas_preds[activo] = {
                    "precio_actual":  round(precio, 2),
                    "direccion":      dir_nueva,
                    "probabilidad":   80,  # alta confianza en cambios de narrativa
                    "contexto":       cambio["nuevo_contexto"],
                    "razon":          cambio["descripcion"],
                    "adaptativa":     True,  # marca que fue regenerada
                }
                log.info(f"   {activo}: {precio} → {dir_nueva}")
            except Exception as e:
                log.warning(f"   Error {activo}: {e}")
    except Exception as e:
        log.error(f"   Error general: {e}")

    # Cancelar predicciones del día actual y guardar nuevas
    if os.path.exists("data/price_targets_historico.json"):
        try:
            with open("data/price_targets_historico.json") as f:
                historico = json.load(f)

            hoy = datetime.now().strftime("%Y-%m-%d")
            for entrada in historico:
                if entrada.get("fecha_prediccion") == hoy:
                    entrada["cancelada"]       = True
                    entrada["razon_cancelacion"]= cambio["descripcion"]
                    entrada["nuevo_contexto"]  = cambio["nuevo_contexto"]

            # Agregar nueva predicción adaptativa
            historico.append({
                "fecha_prediccion":      hoy,
                "fecha_evaluacion_24h":  (datetime.now() + timedelta(days=1))
                                         .strftime("%Y-%m-%d"),
                "predicciones":          nuevas_preds,
                "evaluado_24h":          False,
                "adaptativa":            True,
                "evento_trigger":        cambio["titular"][:80],
            })

            with open("data/price_targets_historico.json", "w") as f:
                json.dump(historico, f, ensure_ascii=True, indent=2)
            log.info("   ✅ Predicciones actualizadas en historial")
        except Exception as e:
            log.error(f"   Error guardando: {e}")

    return nuevas_preds


def procesar_evento_adaptativo(evento: dict) -> bool:
    """
    Función principal — llamar desde monitor.py cuando llega una noticia.
    Detecta si el evento cambia la narrativa y regenera predicciones.

    Returns: True si se regeneraron predicciones
    """
    cambio = detectar_cambio_narrativa(evento)
    if not cambio:
        return False

    clave = f"{cambio['nuevo_contexto']}_{datetime.now().strftime('%Y-%m-%d')}"
    if ya_procesado_hoy(clave):
        log.info(f"   Ya procesado hoy: {clave}")
        return False

    log.info(f"\n{'='*50}")
    log.info(f"⚡ CAMBIO DE NARRATIVA DETECTADO")
    log.info(f"   {cambio['descripcion']}")
    log.info(f"   Score: {cambio['score']}/100")

    # Regenerar predicciones
    nuevas_preds = regenerar_predicciones(cambio)

    # Guardar cambio para evitar duplicados
    guardar_cambio(cambio, clave)

    # Alertar al canal
    if nuevas_preds:
        try:
            from alertas import enviar_alerta_telegram
            lineas = [
                f"⚡ KAIROS — PREDICCIONES ACTUALIZADAS",
                f"{'='*38}",
                f"🔄 Contexto cambió: {cambio['nuevo_contexto']}",
                f"📰 {cambio['titular'][:70]}",
                f"",
                f"Nuevas predicciones del día:",
            ]
            for activo, p in nuevas_preds.items():
                emoji = "📈" if p["direccion"]=="SUBE" else "📉"
                lineas.append(f"  {emoji} {activo}: {p['direccion']} ({p['probabilidad']}%)")
            lineas += ["", "kairos-markets.streamlit.app"]
            enviar_alerta_telegram("\n".join(lineas))
            log.info("   ✅ Alerta enviada al canal")
        except Exception as e:
            log.error(f"   Error alerta: {e}")

    return True


if __name__ == "__main__":
    print("\n⚡ KAIROS — Test predicciones adaptativas\n")

    evento_test = {
        "titular": "Trump Says Iran Deal Looking Very Good, Ceasefire Imminent",
        "score":   99,
        "urgencia":"MAXIMA",
    }

    print(f"Evento: {evento_test['titular']}")
    print(f"Score:  {evento_test['score']}")

    cambio = detectar_cambio_narrativa(evento_test)
    if cambio:
        print(f"\n✅ Cambio detectado: {cambio['nuevo_contexto']}")
        print(f"   {cambio['descripcion']}")
        print(f"\nActivos afectados:")
        for activo, dir_ in cambio["activos_afectados"].items():
            emoji = "📈" if dir_=="SUBE" else "📉"
            print(f"  {emoji} {activo}: {dir_}")
    else:
        print("\n⚫ No se detectó cambio de narrativa")
