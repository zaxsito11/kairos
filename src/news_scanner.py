# news_scanner.py — KAIROS
#
# CONCEPTO CENTRAL:
# KAIROS distingue entre dos tipos de eventos:
#
# TIPO A — Evento puntual (ya absorbido):
#   "Fed sube tasas 25bps" → mercado reacciona en 2-4h → absorbido
#   Si llega 6h después → DESCARTAR
#
# TIPO B — Evento en desarrollo (nunca absorbido hasta resolución):
#   "Guerra EEUU-Irán" → dura semanas/meses → sigue moviendo mercados
#   Cada nueva escalada = nueva ventana activa
#   Score SIEMPRE ALTO mientras el evento no esté resuelto
#
# CORRECCIÓN v2: El filtro de absorción ahora distingue correctamente
# entre noticias viejas y eventos activos sin resolver.

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

# ── TIPO B: Situaciones activas en el mundo ───────────────────────
# Eventos que están sin resolver y siguen moviendo mercados.
# Cada titular relacionado con estos temas tiene VENTANA SIEMPRE ACTIVA.
# ⚠️ ACTUALIZAR cuando un evento se resuelva o aparezca uno nuevo.
SITUACIONES_ACTIVAS = [
    {
        "nombre":      "Conflicto EEUU-Israel-Irán",
        "keywords":    ["iran", "hormuz", "strait of hormuz", "middle east",
                        "israel", "tehran", "persian gulf", "irán",
                        "estrecho de ormuz", "oriente medio"],
        "tipo":        "CONFLICTO_ARMADO",
        "urgencia":    "MAXIMA",
        "score_base":  85,
        "activos":     ["WTI", "Gold", "VIX", "SPX", "DXY"],
        "resuelto":    False,
        "nota":        "Operación Furia Épica — semana 6 activa. WTI $100."
    },
    {
        "nombre":      "Guerra comercial EEUU-China",
        "keywords":    ["tariff", "china trade", "chinese imports",
                        "trade war", "arancel china", "guerra comercial"],
        "tipo":        "TENSION_COMERCIAL",
        "urgencia":    "ALTA",
        "score_base":  75,
        "activos":     ["SPX", "NDX", "DXY", "Gold"],
        "resuelto":    False,
        "nota":        "Aranceles Trump activos — escalada en curso."
    },
    {
        "nombre":      "Crisis energética global",
        "keywords":    ["oil price", "crude oil", "brent", "wti",
                        "energy crisis", "opec", "petróleo", "crudo"],
        "tipo":        "CRISIS_ENERGETICA",
        "urgencia":    "ALTA",
        "score_base":  70,
        "activos":     ["WTI", "Gold", "SPX", "DXY"],
        "resuelto":    False,
        "nota":        "WTI en $100 por bloqueo Ormuz. Riesgo inflacionario activo."
    },
]

# ── Eventos puntuales con ventana temporal ────────────────────────
KEYWORDS_URGENCIA = {
    "MAXIMA": {
        "palabras": [
            "fomc statement", "fed decision", "rate decision",
            "emergency meeting", "market halt", "circuit breaker",
            "bank collapse", "nuclear", "attack on",
        ],
        "ventana_horas": 2,
        "activos": ["SPX", "VIX", "Gold", "DXY", "UST10Y"],
    },
    "ALTA": {
        "palabras": [
            "inflation", "inflación", "cpi", "pce", "nfp",
            "jobs report", "unemployment", "gdp", "recession",
            "rate hike", "rate cut", "powell", "lagarde",
            "sanctions", "sanciones", "invasion", "invasión",
            "military strike", "ceasefire", "peace deal",
        ],
        "ventana_horas": 6,
        "activos": ["SPX", "NDX", "Gold", "DXY", "WTI", "VIX"],
    },
    "MEDIA": {
        "palabras": [
            "federal reserve", "interest rate", "monetary policy",
            "earnings", "guidance", "geopolitical", "default",
            "election", "elecciones", "debt ceiling",
        ],
        "ventana_horas": 24,
        "activos": ["SPX", "Gold", "DXY"],
    },
}

# ── Precedentes históricos predictivos ───────────────────────────
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
        "condicion":   "FED más hawkish que expectativa",
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
        "condicion":   "Nueva escalada o desarrollo en conflicto activo",
        "n_eventos":   6,
        "prediccion": {
            "Gold":   {"direccion": "SUBE",  "promedio_24h": "+2.1%",  "probabilidad": "83%"},
            "WTI":    {"direccion": "SUBE",  "promedio_24h": "+4.5%",  "probabilidad": "70%"},
            "SPX":    {"direccion": "BAJA",  "promedio_24h": "-1.8%",  "probabilidad": "67%"},
            "VIX":    {"direccion": "SUBE",  "promedio_24h": "+22%",   "probabilidad": "78%"},
        },
        "tiempo_reaccion": "0-6 horas — prima de riesgo activa",
    },
    "crisis_energia_opec": {
        "condicion":   "Shock de oferta energética o decisión OPEC",
        "n_eventos":   5,
        "prediccion": {
            "WTI":    {"direccion": "SUBE",  "promedio_24h": "+4.2%",  "probabilidad": "85%"},
            "Gold":   {"direccion": "SUBE",  "promedio_24h": "+0.8%",  "probabilidad": "60%"},
            "SPX":    {"direccion": "BAJA",  "promedio_24h": "-0.8%",  "probabilidad": "58%"},
            "DXY":    {"direccion": "SUBE",  "promedio_24h": "+0.3%",  "probabilidad": "55%"},
        },
        "tiempo_reaccion": "0-3 horas post anuncio",
    },
    "tension_comercial": {
        "condicion":   "Nuevos aranceles o escalada comercial",
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
    """Retorna edad de la noticia en horas. None si sin fecha."""
    for campo in ["published", "updated", "created"]:
        fecha_str = entry.get(campo, "")
        if fecha_str:
            try:
                fecha = parsedate_to_datetime(fecha_str)
                if fecha.tzinfo:
                    fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
                return (datetime.utcnow() - fecha).total_seconds() / 3600
            except Exception:
                continue
    return None


# ── Motor de clasificación ────────────────────────────────────────
def detectar_situacion_activa(titular: str) -> dict | None:
    """
    NUEVO: Verifica si el titular está relacionado con una
    situación activa en el mundo (evento sin resolver).
    Si es así, el score es SIEMPRE ALTO independientemente
    de la edad de la noticia.
    """
    titular_lower = titular.lower()
    for situacion in SITUACIONES_ACTIVAS:
        if situacion["resuelto"]:
            continue
        coincidencias = [kw for kw in situacion["keywords"]
                         if kw in titular_lower]
        if coincidencias:
            return {
                "situacion":    situacion["nombre"],
                "tipo":         situacion["tipo"],
                "urgencia":     situacion["urgencia"],
                "score_base":   situacion["score_base"],
                "activos":      situacion["activos"],
                "nota":         situacion["nota"],
                "keywords_match": coincidencias,
            }
    return None


def calcular_ventana_absorcion(titular: str, edad_horas: float,
                                situacion_activa: dict = None) -> dict:
    """
    CORREGIDO v2:
    - Si es situación activa → SIEMPRE ventana activa, score alto
    - Si es evento puntual → ventana según urgencia y edad
    """
    titular_lower = titular.lower()

    # ── TIPO B: Situación activa → siempre relevante ──────────────
    if situacion_activa:
        return {
            "ventana_activa":  True,
            "estado":          f"SITUACIÓN ACTIVA — {situacion_activa['situacion']}",
            "urgencia":        situacion_activa["urgencia"],
            "horas_restantes": 999,  # sin límite hasta resolución
            "es_situacion_activa": True,
        }

    # ── TIPO A: Evento puntual → ventana por urgencia ─────────────
    for nivel, config in KEYWORDS_URGENCIA.items():
        palabras_match = [p for p in config["palabras"] if p in titular_lower]
        if palabras_match:
            ventana  = config["ventana_horas"]
            activa   = edad_horas <= ventana
            restantes= max(0, ventana - edad_horas)
            return {
                "ventana_activa":  activa,
                "estado": (
                    f"VENTANA ACTIVA — {round(restantes,1)}h restantes"
                    if activa else
                    f"ABSORBIDO — hace {round(edad_horas,1)}h (ventana era {ventana}h)"
                ),
                "urgencia":        nivel,
                "horas_restantes": restantes,
                "palabras_match":  palabras_match,
                "activos":         config.get("activos", []),
                "es_situacion_activa": False,
            }

    # Sin clasificación — ventana corta de 4h
    activa = edad_horas <= 4
    return {
        "ventana_activa":  activa,
        "estado": (
            f"VENTANA ACTIVA — {round(max(0,4-edad_horas),1)}h restantes"
            if activa else "ABSORBIDO"
        ),
        "urgencia":        "MEDIA",
        "horas_restantes": max(0, 4 - edad_horas),
        "es_situacion_activa": False,
    }


def identificar_precedente(titular: str,
                            situacion_activa: dict = None) -> dict | None:
    """Identifica el precedente histórico aplicable."""
    titular_lower = titular.lower()

    # Si es situación activa, usar el precedente del tipo
    if situacion_activa:
        mapa_tipo = {
            "CONFLICTO_ARMADO":  "conflicto_armado_escalada",
            "TENSION_COMERCIAL": "tension_comercial",
            "CRISIS_ENERGETICA": "crisis_energia_opec",
        }
        clave = mapa_tipo.get(situacion_activa["tipo"])
        if clave:
            return {"clave": clave, "datos": PRECEDENTES_PREDICTIVOS[clave]}

    # Evento puntual
    mapeo = {
        "cpi_sorpresa_hawkish":  ["cpi", "inflation", "inflación", "core cpi"],
        "fomc_hawkish_sorpresa": ["fomc", "fed decision", "rate decision", "powell"],
        "conflicto_armado_escalada": ["war", "invasion", "military strike"],
        "crisis_energia_opec":   ["opec", "oil cut", "production cut"],
        "tension_comercial":     ["tariff", "arancel", "trade war"],
    }
    for clave, keywords in mapeo.items():
        if any(kw in titular_lower for kw in keywords):
            return {"clave": clave, "datos": PRECEDENTES_PREDICTIVOS[clave]}

    return None


def calcular_score(titular: str, edad_horas: float,
                   absorcion: dict, precedente: dict = None,
                   situacion_activa: dict = None) -> int:
    """
    CORREGIDO v2: Score 0-100.
    Situaciones activas → score siempre 75-95.
    Eventos puntuales → score por urgencia y frescura.
    """
    if not absorcion["ventana_activa"]:
        return 0

    # ── Situación activa: score alto fijo ─────────────────────────
    if situacion_activa:
        score_base = situacion_activa["score_base"]
        # Bonus si la noticia es reciente (nueva escalada)
        if edad_horas <= 1:    score_base = min(score_base + 10, 98)
        elif edad_horas <= 6:  score_base = min(score_base + 5,  95)
        elif edad_horas <= 24: score_base = score_base  # mantiene base
        else:                  score_base = max(score_base - 10, 65)
        return score_base

    # ── Evento puntual: score por urgencia + frescura ─────────────
    urgencia_base = {"MAXIMA": 60, "ALTA": 45, "MEDIA": 30}.get(
        absorcion["urgencia"], 20
    )
    if edad_horas <= 0.5:   frescura = 35
    elif edad_horas <= 1:   frescura = 28
    elif edad_horas <= 2:   frescura = 20
    elif edad_horas <= 6:   frescura = 10
    elif edad_horas <= 24:  frescura = 4
    else:                   frescura = 0

    bonus_precedente = 8 if precedente else 0

    return min(urgencia_base + frescura + bonus_precedente, 100)


# ── Función principal ─────────────────────────────────────────────
def escanear_noticias_kairos(noticias_vistas: list = None) -> list:
    """
    Escanea RSS y retorna eventos con ventana activa.
    v2: distingue correctamente entre noticias absorbidas
    y situaciones activas sin resolver.
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
                if h in noticias_vistas:
                    continue
                noticias_vistas.append(h)

                edad_horas = obtener_edad_horas(entry)
                if edad_horas is None:
                    continue

                # Descartar solo si es muy vieja Y no es situación activa
                situacion_activa = detectar_situacion_activa(titular)
                if edad_horas > 72 and not situacion_activa:
                    continue

                absorcion = calcular_ventana_absorcion(
                    titular, edad_horas, situacion_activa
                )
                if not absorcion["ventana_activa"]:
                    continue

                try:
                    from geopolitica import clasificar_evento_geopolitico
                    geo = clasificar_evento_geopolitico(titular)
                except Exception:
                    geo = None

                precedente = identificar_precedente(titular, situacion_activa)
                score = calcular_score(
                    titular, edad_horas, absorcion, precedente, situacion_activa
                )

                if score < 25:
                    continue

                eventos.append({
                    "titular":          titular,
                    "fuente":           fuente["nombre"],
                    "link":             entry.get("link", ""),
                    "edad_horas":       round(edad_horas, 2),
                    "absorcion":        absorcion,
                    "urgencia":         absorcion["urgencia"],
                    "situacion_activa": situacion_activa,
                    "geo":              geo,
                    "precedente":       precedente,
                    "score":            score,
                    "timestamp":        datetime.now().isoformat(),
                    "hash":             h,
                })

        except Exception as e:
            print(f"  Error en {fuente['nombre']}: {e}")

    eventos.sort(key=lambda x: x["score"], reverse=True)
    return eventos


def formatear_alerta_noticia(evento: dict) -> str:
    """Genera mensaje Telegram para una noticia detectada."""
    titular          = evento["titular"]
    fuente           = evento["fuente"]
    link             = evento["link"]
    absorcion        = evento["absorcion"]
    urgencia         = evento["urgencia"]
    score            = evento["score"]
    edad             = evento["edad_horas"]
    precedente       = evento.get("precedente")
    geo              = evento.get("geo")
    situacion_activa = evento.get("situacion_activa")

    emojis = {"MAXIMA": "🚨", "ALTA": "⚠️", "MEDIA": "📡"}
    emoji  = emojis.get(urgencia, "📡")

    tiempo_txt = (f"hace {int(edad*60)} min" if edad < 1
                  else f"hace {round(edad,1)}h")

    lineas = [
        f"{emoji} KAIROS — {'SITUACIÓN ACTIVA' if situacion_activa else 'VENTANA ACTIVA'}",
        f"{'='*38}",
        f"📰 {titular}",
        f"📡 {fuente} | {tiempo_txt}",
        f"🔗 {link}",
        f"",
    ]

    if situacion_activa:
        lineas += [
            f"🔴 {situacion_activa['situacion']}",
            f"📌 {situacion_activa['nota']}",
            f"🎯 Score: {score}/100 (evento en desarrollo)",
        ]
    else:
        lineas += [
            f"⏱️ {absorcion['estado']}",
            f"🎯 Score: {score}/100",
        ]

    if geo and geo.get("tipo") not in (None, "NO_CLASIFICADO"):
        impacto = geo.get("impacto", {})
        suben = [a for a, d in impacto.items() if d["direccion"] == "SUBE"]
        bajan = [a for a, d in impacto.items() if d["direccion"] == "BAJA"]
        lineas += [
            f"",
            f"🌍 {geo['tipo'].replace('_',' ')}",
            f"🟢 Suben: {', '.join(suben) or 'N/A'}",
            f"🔴 Bajan: {', '.join(bajan) or 'N/A'}",
        ]

    if precedente:
        datos    = precedente["datos"]
        condicion= datos["condicion"]
        n        = datos["n_eventos"]
        lineas  += [f"", f"📊 PREDICCIÓN ({n} precedentes — {condicion}):"]
        for activo, pred in list(datos["prediccion"].items())[:4]:
            flecha = "📈" if pred["direccion"] == "SUBE" else "📉"
            lineas.append(
                f"  {flecha} {activo}: {pred['promedio_24h']} ({pred['probabilidad']})"
            )
        lineas.append(f"  ⏱️ Reacción típica: {datos['tiempo_reaccion']}")

    lineas += ["", "kairos-markets.streamlit.app"]
    return "\n".join(lineas)


# ── Test directo ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔍 KAIROS NEWS SCANNER v2 — TEST")
    print("Buscando eventos relevantes...\n")

    # Mostrar situaciones activas configuradas
    print("SITUACIONES ACTIVAS CONFIGURADAS:")
    for s in SITUACIONES_ACTIVAS:
        estado = "ACTIVA" if not s["resuelto"] else "RESUELTA"
        print(f"  [{estado}] {s['nombre']} — Score base: {s['score_base']}")
    print()

    eventos = escanear_noticias_kairos()

    if not eventos:
        print("Sin eventos relevantes en este momento.")
    else:
        print(f"✅ {len(eventos)} eventos detectados:\n")
        for i, e in enumerate(eventos[:5], 1):
            tipo = "🔴 SITUACIÓN ACTIVA" if e.get("situacion_activa") else "⚠️ EVENTO PUNTUAL"
            print(f"{'─'*60}")
            print(f"#{i} {tipo}")
            print(f"    Score: {e['score']}/100 | Urgencia: {e['urgencia']}")
            print(f"    {e['titular'][:75]}")
            print(f"    Fuente: {e['fuente']} | Edad: {e['edad_horas']}h")
            if e.get("situacion_activa"):
                s = e["situacion_activa"]
                print(f"    Situación: {s['situacion']}")
                print(f"    Nota: {s['nota']}")
            if e.get("precedente"):
                datos = e["precedente"]["datos"]
                print(f"    Predicción ({datos['n_eventos']} casos):")
                for activo, pred in list(datos["prediccion"].items())[:3]:
                    print(f"      → {activo}: {pred['promedio_24h']} ({pred['probabilidad']})")
            print()
