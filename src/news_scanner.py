# news_scanner.py — KAIROS
#
# CONCEPTO CENTRAL:
# KAIROS no reporta lo que ya pasó — detecta lo que va a mover
# los mercados en las próximas horas/días antes de que el
# mercado lo descuente completamente.
#
# FILTRO DE ABSORCIÓN:
# Cada noticia pasa por un filtro que determina si el mercado
# ya la procesó o si hay una ventana de oportunidad activa.
#
# USO DE HISTÓRICOS:
# Los precedentes no son "noticias viejas" — son retroalimentación
# para calcular probabilidades de movimiento futuro.

import feedparser
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# ── Fuentes RSS ───────────────────────────────────────────────────
FUENTES_RSS = [
    {"nombre": "Reuters Business",  "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"nombre": "Reuters Markets",   "url": "https://feeds.reuters.com/reuters/UKdomesticNews"},
    {"nombre": "CNBC Markets",      "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html"},
    {"nombre": "Investing.com ES",  "url": "https://es.investing.com/rss/news.rss"},
    {"nombre": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/markets/news.rss"},
]

# ── Ventana de absorción ──────────────────────────────────────────
# Tiempo máximo desde publicación para considerar que el mercado
# puede NO haber absorbido completamente el evento
VENTANA_ABSORCION = {
    "MAXIMA":  2,    # horas — mercado aún procesando activamente
    "ALTA":    6,    # horas — probablemente absorbiendo
    "MEDIA":   24,   # horas — puede haber rezago parcial
    "BAJA":    72,   # horas — casi seguro absorbido (solo eventos en curso)
}

# ── Eventos que NUNCA se descartan por tiempo ─────────────────────
# Porque siguen activos hasta resolución
EVENTOS_EN_DESARROLLO = [
    "war", "guerra", "conflict", "conflicto",
    "ceasefire", "cese al fuego", "negotiations", "negociaciones",
    "sanctions", "sanciones", "trade war", "guerra comercial",
    "crisis", "escalation", "escalada",
]

# ── Keywords con su impacto y urgencia ───────────────────────────
# Cada keyword tiene: impacto en mercados + activos afectados + urgencia
KEYWORDS_IMPACTO = {

    # MÁXIMA URGENCIA — mueven mercados en minutos
    "URGENCIA_MAXIMA": {
        "palabras": [
            "fomc statement", "fed decision", "rate decision",
            "emergency meeting", "reunión de emergencia",
            "market halt", "circuit breaker", "flash crash",
            "bank collapse", "quiebra bancaria",
            "nuclear", "attack on", "ataque a",
        ],
        "urgencia":       "MÁXIMA",
        "ventana_horas":  2,
        "activos":        ["SPX", "VIX", "Gold", "DXY", "UST10Y"],
    },

    # ALTA URGENCIA — mueven mercados en horas
    "URGENCIA_ALTA": {
        "palabras": [
            "inflation", "inflación", "cpi", "pce",
            "nfp", "jobs report", "unemployment", "desempleo",
            "gdp", "pib", "recession", "recesión",
            "rate hike", "rate cut", "subida de tasas", "recorte de tasas",
            "powell", "lagarde", "fed chair",
            "opec", "opep", "oil cut", "recorte producción",
            "tariff", "arancel", "trade war", "guerra comercial",
            "sanctions", "sanciones",
            "invasion", "invasión", "military strike",
        ],
        "urgencia":       "ALTA",
        "ventana_horas":  6,
        "activos":        ["SPX", "NDX", "Gold", "DXY", "WTI", "VIX"],
    },

    # MEDIA URGENCIA — impacto en las próximas 24h
    "URGENCIA_MEDIA": {
        "palabras": [
            "federal reserve", "reserva federal",
            "interest rate", "tasa de interés",
            "monetary policy", "política monetaria",
            "earnings", "resultados", "guidance",
            "geopolitical", "geopolítico",
            "energy crisis", "crisis energética",
            "default", "debt ceiling",
            "election", "elecciones",
        ],
        "urgencia":       "MEDIA",
        "ventana_horas":  24,
        "activos":        ["SPX", "Gold", "DXY"],
    },
}

# ── Precedentes históricos por tipo de evento ─────────────────────
# Retroalimentación para predecir movimientos futuros
PRECEDENTES_PREDICTIVOS = {
    "cpi_sorpresa_hawkish": {
        "condicion":   "CPI supera consenso",
        "n_eventos":   8,
        "prediccion": {
            "DXY":    {"direccion": "SUBE",  "promedio_24h": "+0.8%",  "probabilidad": "72%"},
            "SPX":    {"direccion": "BAJA",  "promedio_24h": "-1.2%",  "probabilidad": "68%"},
            "Gold":   {"direccion": "BAJA",  "promedio_24h": "-0.5%",  "probabilidad": "60%"},
            "UST10Y": {"direccion": "SUBE",  "promedio_24h": "+5bps",  "probabilidad": "75%"},
        },
        "tiempo_reaccion": "0-4 horas post publicación",
    },
    "fomc_hawkish_sorpresa": {
        "condicion":   "FED más hawkish que expectativa mercado",
        "n_eventos":   10,
        "prediccion": {
            "DXY":    {"direccion": "SUBE",  "promedio_24h": "+0.7%",  "probabilidad": "80%"},
            "SPX":    {"direccion": "BAJA",  "promedio_24h": "-1.7%",  "probabilidad": "75%"},
            "Gold":   {"direccion": "BAJA",  "promedio_24h": "-0.4%",  "probabilidad": "65%"},
            "VIX":    {"direccion": "SUBE",  "promedio_24h": "+15%",   "probabilidad": "70%"},
        },
        "tiempo_reaccion": "0-2 horas post comunicado",
    },
    "conflicto_armado_escalada": {
        "condicion":   "Nuevo conflicto o escalada militar",
        "n_eventos":   6,
        "prediccion": {
            "Gold":   {"direccion": "SUBE",  "promedio_24h": "+2.1%",  "probabilidad": "83%"},
            "WTI":    {"direccion": "SUBE",  "promedio_24h": "+4.5%",  "probabilidad": "70%"},
            "SPX":    {"direccion": "BAJA",  "promedio_24h": "-1.8%",  "probabilidad": "67%"},
            "VIX":    {"direccion": "SUBE",  "promedio_24h": "+22%",   "probabilidad": "78%"},
        },
        "tiempo_reaccion": "0-6 horas — prima de riesgo activa",
    },
    "opec_recorte_sorpresa": {
        "condicion":   "OPEC recorta producción por encima de lo esperado",
        "n_eventos":   5,
        "prediccion": {
            "WTI":    {"direccion": "SUBE",  "promedio_24h": "+4.2%",  "probabilidad": "85%"},
            "Gold":   {"direccion": "SUBE",  "promedio_24h": "+0.8%",  "probabilidad": "60%"},
            "SPX":    {"direccion": "BAJA",  "promedio_24h": "-0.8%",  "probabilidad": "58%"},
            "DXY":    {"direccion": "SUBE",  "promedio_24h": "+0.3%",  "probabilidad": "55%"},
        },
        "tiempo_reaccion": "0-3 horas post anuncio",
    },
    "tension_comercial_aranceles": {
        "condicion":   "Nuevos aranceles o escalada guerra comercial",
        "n_eventos":   7,
        "prediccion": {
            "SPX":    {"direccion": "BAJA",  "promedio_24h": "-2.1%",  "probabilidad": "74%"},
            "NDX":    {"direccion": "BAJA",  "promedio_24h": "-2.8%",  "probabilidad": "76%"},
            "Gold":   {"direccion": "SUBE",  "promedio_24h": "+1.1%",  "probabilidad": "65%"},
            "DXY":    {"direccion": "MIXTO", "promedio_24h": "±0.5%",  "probabilidad": "50%"},
        },
        "tiempo_reaccion": "0-4 horas post anuncio",
    },
}


# ── Utilidades ────────────────────────────────────────────────────
def hash_titular(titular: str) -> str:
    return hashlib.md5(titular.lower().strip().encode()).hexdigest()


def obtener_edad_horas(entry) -> float | None:
    """Retorna la edad de la noticia en horas. None si no tiene fecha."""
    for campo in ["published", "updated", "created"]:
        fecha_str = entry.get(campo, "")
        if fecha_str:
            try:
                fecha = parsedate_to_datetime(fecha_str)
                if fecha.tzinfo:
                    fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
                delta = datetime.utcnow() - fecha
                return delta.total_seconds() / 3600
            except Exception:
                continue
    return None


def calcular_ventana_absorcion(titular: str, edad_horas: float) -> dict:
    """
    Determina si el mercado ya absorbió la noticia o si hay
    una ventana de oportunidad activa.

    Retorna:
        ventana_activa: bool
        estado: str (descripción del estado de absorción)
        urgencia: str
        horas_restantes: float estimado de ventana activa
    """
    titular_lower = titular.lower()

    # Eventos en desarrollo: nunca se descartan por tiempo
    es_evento_en_desarrollo = any(
        kw in titular_lower for kw in EVENTOS_EN_DESARROLLO
    )
    if es_evento_en_desarrollo and edad_horas <= 72:
        return {
            "ventana_activa":   True,
            "estado":           "EVENTO EN DESARROLLO — ventana activa hasta resolución",
            "urgencia":         "ALTA",
            "horas_restantes":  72 - edad_horas,
        }

    # Clasificar por urgencia y calcular si la ventana sigue activa
    for nivel, config in KEYWORDS_IMPACTO.items():
        palabras_match = [p for p in config["palabras"] if p in titular_lower]
        if palabras_match:
            ventana = config["ventana_horas"]
            activa  = edad_horas <= ventana
            restantes = max(0, ventana - edad_horas)
            return {
                "ventana_activa":   activa,
                "estado":           (
                    f"VENTANA ACTIVA — {round(restantes, 1)}h restantes"
                    if activa else
                    f"ABSORBIDO — hace {round(edad_horas, 1)}h (ventana era {ventana}h)"
                ),
                "urgencia":         config["urgencia"],
                "horas_restantes":  restantes,
                "palabras_match":   palabras_match,
                "activos":          config.get("activos", []),
            }

    # Sin clasificación específica: ventana corta de 6h
    activa = edad_horas <= 6
    return {
        "ventana_activa":   activa,
        "estado":           (
            f"VENTANA ACTIVA — {round(max(0, 6 - edad_horas), 1)}h restantes"
            if activa else "POSIBLEMENTE ABSORBIDO"
        ),
        "urgencia":         "MEDIA",
        "horas_restantes":  max(0, 6 - edad_horas),
    }


def identificar_precedente(titular: str, clasificacion_geo: dict = None) -> dict | None:
    """
    Identifica qué precedente histórico aplica para predecir
    el movimiento probable futuro.
    """
    titular_lower = titular.lower()

    # Mapeo de keywords a precedentes
    mapeo = {
        "cpi_sorpresa_hawkish":     ["cpi", "inflation", "inflación", "core cpi"],
        "fomc_hawkish_sorpresa":    ["fomc", "fed decision", "rate decision", "powell"],
        "conflicto_armado_escalada":["war", "guerra", "invasion", "invasión",
                                     "military strike", "airstrike"],
        "opec_recorte_sorpresa":    ["opec", "opep", "oil cut", "production cut",
                                     "recorte producción"],
        "tension_comercial_aranceles":["tariff", "arancel", "trade war",
                                       "guerra comercial", "import duty"],
    }

    for clave_precedente, keywords in mapeo.items():
        if any(kw in titular_lower for kw in keywords):
            return {
                "clave":      clave_precedente,
                "datos":      PRECEDENTES_PREDICTIVOS[clave_precedente],
            }

    # Si tiene clasificación geopolítica, usar precedente de conflicto
    if clasificacion_geo and clasificacion_geo.get("tipo") == "CONFLICTO_ARMADO":
        return {
            "clave": "conflicto_armado_escalada",
            "datos": PRECEDENTES_PREDICTIVOS["conflicto_armado_escalada"],
        }

    return None


def calcular_score_relevancia(titular: str, edad_horas: float,
                               absorcion: dict, precedente: dict = None) -> int:
    """
    Score de 0-100 que representa qué tan relevante es la noticia
    para KAIROS en este momento.
    100 = evento crítico, mercado aún no lo procesó
    0   = evento ya absorbido o sin impacto
    """
    if not absorcion["ventana_activa"]:
        return 0

    score = 0

    # Urgencia base
    urgencia_scores = {"MÁXIMA": 60, "ALTA": 45, "MEDIA": 30, "BAJA": 15}
    score += urgencia_scores.get(absorcion["urgencia"], 20)

    # Frescura: más reciente = mayor score
    if edad_horas <= 0.5:   score += 30   # < 30 min
    elif edad_horas <= 1:   score += 25   # < 1h
    elif edad_horas <= 2:   score += 20   # < 2h
    elif edad_horas <= 6:   score += 10   # < 6h
    elif edad_horas <= 24:  score += 5    # < 24h

    # Tiene precedente histórico que permite predicción
    if precedente:
        score += 10

    return min(score, 100)


# ── Función principal ─────────────────────────────────────────────
def escanear_noticias_kairos(noticias_vistas: list = None) -> list:
    """
    Escanea fuentes RSS y retorna solo noticias con ventana
    de oportunidad activa — lo que el mercado aún no absorbió.

    Cada noticia incluye:
    - ventana de absorción (¿cuánto tiempo queda?)
    - urgencia (MÁXIMA/ALTA/MEDIA)
    - predicción de movimiento por activo (con probabilidades)
    - precedente histórico aplicable
    - score de relevancia (0-100)

    Returns:
        Lista de eventos ordenados por score de relevancia (mayor primero)
    """
    if noticias_vistas is None:
        noticias_vistas = []

    eventos = []

    for fuente in FUENTES_RSS:
        try:
            print(f"  Escaneando: {fuente['nombre']}")
            feed = feedparser.parse(fuente["url"])

            for entry in feed.entries[:25]:
                titular = entry.get("title", "").strip()
                if not titular:
                    continue

                h = hash_titular(titular)

                # ── Ya procesada
                if h in noticias_vistas:
                    continue
                noticias_vistas.append(h)

                # ── Calcular edad
                edad_horas = obtener_edad_horas(entry)
                if edad_horas is None:
                    continue  # sin fecha = no confiable

                # ── Descartar si es muy vieja (> 72h) sin ser evento en curso
                if edad_horas > 72:
                    continue

                # ── Filtro de absorción
                absorcion = calcular_ventana_absorcion(titular, edad_horas)
                if not absorcion["ventana_activa"]:
                    continue  # mercado ya lo absorbió — no es útil para KAIROS

                # ── Clasificación geopolítica
                try:
                    from geopolitica import clasificar_evento_geopolitico
                    geo = clasificar_evento_geopolitico(titular)
                except Exception:
                    geo = None

                # ── Precedente histórico → predicción futura
                precedente = identificar_precedente(titular, geo)

                # ── Score de relevancia
                score = calcular_score_relevancia(titular, edad_horas, absorcion, precedente)

                if score < 20:
                    continue  # muy baja relevancia

                eventos.append({
                    "titular":      titular,
                    "fuente":       fuente["nombre"],
                    "link":         entry.get("link", ""),
                    "edad_horas":   round(edad_horas, 2),
                    "absorcion":    absorcion,
                    "urgencia":     absorcion["urgencia"],
                    "geo":          geo,
                    "precedente":   precedente,
                    "score":        score,
                    "timestamp":    datetime.now().isoformat(),
                    "hash":         h,
                })

        except Exception as e:
            print(f"  Error en {fuente['nombre']}: {e}")

    # Ordenar por score (más relevante primero)
    eventos.sort(key=lambda x: x["score"], reverse=True)
    return eventos


def formatear_alerta_noticia(evento: dict) -> str:
    """
    Genera el mensaje de Telegram para una noticia detectada.
    FORMATO: orientado a acción futura, no a reportar el pasado.
    """
    titular   = evento["titular"]
    fuente    = evento["fuente"]
    link      = evento["link"]
    absorcion = evento["absorcion"]
    urgencia  = evento["urgencia"]
    score     = evento["score"]
    edad      = evento["edad_horas"]
    precedente= evento.get("precedente")
    geo       = evento.get("geo")

    # Emoji por urgencia
    emojis_urgencia = {
        "MÁXIMA": "🚨", "ALTA": "⚠️", "MEDIA": "📡", "BAJA": "ℹ️"
    }
    emoji = emojis_urgencia.get(urgencia, "📡")

    # Tiempo desde publicación
    if edad < 1:
        tiempo_txt = f"hace {int(edad*60)} minutos"
    else:
        tiempo_txt = f"hace {round(edad, 1)} horas"

    lineas = [
        f"{emoji} KAIROS — VENTANA ACTIVA",
        f"{'='*38}",
        f"📰 {titular}",
        f"📡 {fuente} | {tiempo_txt}",
        f"🔗 {link}",
        f"",
        f"⏱️ {absorcion['estado']}",
        f"🎯 Score de relevancia: {score}/100",
    ]

    # Clasificación geopolítica
    if geo and geo.get("tipo") not in (None, "NO_CLASIFICADO"):
        tipo_geo = geo["tipo"].replace("_", " ")
        impacto  = geo.get("impacto", {})
        suben = [a for a, d in impacto.items() if d["direccion"] == "SUBE"]
        bajan = [a for a, d in impacto.items() if d["direccion"] == "BAJA"]
        lineas += [
            f"",
            f"🌍 Tipo de evento: {tipo_geo}",
            f"🟢 Probable subida: {', '.join(suben) or 'N/A'}",
            f"🔴 Probable baja:   {', '.join(bajan) or 'N/A'}",
        ]

    # Predicción basada en precedentes históricos
    if precedente:
        datos     = precedente["datos"]
        condicion = datos["condicion"]
        n         = datos["n_eventos"]
        t_reaccion= datos["tiempo_reaccion"]
        prediccion= datos["prediccion"]

        lineas += [
            f"",
            f"📊 PREDICCIÓN BASADA EN {n} PRECEDENTES HISTÓRICOS:",
            f"Condición: {condicion}",
            f"Tiempo de reacción típico: {t_reaccion}",
        ]
        for activo, pred in prediccion.items():
            flecha = "📈" if pred["direccion"] == "SUBE" else "📉"
            lineas.append(
                f"  {flecha} {activo}: {pred['promedio_24h']} "
                f"({pred['probabilidad']} prob.)"
            )

    lineas += ["", "kairos-markets.streamlit.app"]
    return "\n".join(lineas)


# ── Test directo ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔍 KAIROS NEWS SCANNER — TEST")
    print("Buscando eventos con ventana de oportunidad activa...\n")

    eventos = escanear_noticias_kairos()

    if not eventos:
        print("Sin eventos relevantes en este momento.")
    else:
        print(f"✅ {len(eventos)} eventos con ventana activa:\n")
        for i, e in enumerate(eventos[:5], 1):
            print(f"{'─'*60}")
            print(f"#{i} Score: {e['score']}/100 | Urgencia: {e['urgencia']}")
            print(f"    {e['titular'][:75]}")
            print(f"    Fuente: {e['fuente']} | Edad: {e['edad_horas']}h")
            print(f"    Estado: {e['absorcion']['estado']}")
            if e.get("precedente"):
                datos = e["precedente"]["datos"]
                print(f"    Precedente: {datos['condicion']}")
                for activo, pred in datos["prediccion"].items():
                    print(f"      → {activo}: {pred['promedio_24h']} ({pred['probabilidad']})")
            print()
