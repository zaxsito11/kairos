# news_scanner.py — KAIROS v4
# KAIROS es selectivo: solo alerta lo que puede mover mercados >1%
# Score mínimo: 70/100 — sin noticias irrelevantes

import feedparser
import hashlib
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

FUENTES_RSS = [
    {"nombre": "Reuters Business",   "url": "https://feeds.reuters.com/reuters/businessNews",  "peso": 10},
    {"nombre": "Reuters Markets",    "url": "https://feeds.reuters.com/reuters/UKdomesticNews", "peso": 10},
    {"nombre": "Reuters Top News",   "url": "https://feeds.reuters.com/reuters/topNews",        "peso": 9},
    {"nombre": "CNBC Markets",       "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html", "peso": 9},
    {"nombre": "Bloomberg Markets",  "url": "https://feeds.bloomberg.com/markets/news.rss",    "peso": 10},
    {"nombre": "Yahoo Finance",      "url": "https://finance.yahoo.com/rss/topstories",        "peso": 8},
    {"nombre": "Investing.com Global","url": "https://www.investing.com/rss/news_301.rss",     "peso": 8},
    {"nombre": "Investing.com ES",   "url": "https://es.investing.com/rss/news.rss",           "peso": 7},
    {"nombre": "MarketWatch",        "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "peso": 8},
]

# ── Situaciones activas — score SIEMPRE alto hasta resolución ─────
SITUACIONES_ACTIVAS = [
    {
        "nombre":    "Conflicto EEUU-Israel-Irán",
        "keywords":  [
            "iran", "hormuz", "strait of hormuz", "middle east war",
            "israel attack", "tehran", "persian gulf", "irán",
            "estrecho de ormuz", "operation", "military iran", "us iran",
        ],
        "tipo":       "CONFLICTO_ARMADO",
        "urgencia":   "MAXIMA",
        "score_base":  88,
        "activos":    ["WTI", "Gold", "VIX", "SPX", "DXY"],
        "resuelto":   False,
        "nota":       "Operación Furia Épica — semana 6. WTI $100.",
    },
    {
        "nombre":    "Guerra comercial EEUU-China",
        "keywords":  [
            "tariff china", "chinese tariffs", "trade war china",
            "us china trade", "arancel china", "guerra comercial",
            "trump tariff", "beijing retaliation",
        ],
        "tipo":       "TENSION_COMERCIAL",
        "urgencia":   "ALTA",
        "score_base":  78,
        "activos":    ["SPX", "NDX", "DXY", "Gold"],
        "resuelto":   False,
        "nota":       "Aranceles Trump activos — escalada en curso.",
    },
    {
        "nombre":    "Crisis energética — WTI $100",
        "keywords":  [
            "oil $100", "crude $100", "brent $100",
            "oil supply crisis", "energy crisis",
            "petróleo 100", "precio petróleo dispara",
        ],
        "tipo":       "CRISIS_ENERGETICA",
        "urgencia":   "ALTA",
        "score_base":  75,
        "activos":    ["WTI", "Gold", "SPX", "DXY"],
        "resuelto":   False,
        "nota":       "WTI en $100 por bloqueo Ormuz.",
    },
]

# ── Solo MAXIMA y ALTA — sin categoría MEDIA ──────────────────────
# La categoría MEDIA generaba ruido (deportes, entretenimiento, etc.)
# KAIROS solo alerta lo que históricamente mueve mercados >1%
KEYWORDS_URGENCIA = {
    "MAXIMA": {
        "palabras": [
            # Bancos centrales — decisiones en vivo
            "rate decision", "fomc statement", "fed raises", "fed cuts",
            "ecb raises", "ecb cuts", "emergency rate", "surprise rate",
            "fed rate decision", "ecb rate decision",
            # Conflictos y shocks sistémicos
            "military strike", "war escalation", "nuclear threat",
            "hormuz blockade", "oil supply cut", "pipeline attack",
            # Crisis financiera
            "bank collapse", "bank run", "circuit breaker",
            "market halt", "financial contagion", "systemic crisis",
        ],
        "ventana_horas": 2,
        "activos": ["SPX", "VIX", "Gold", "DXY", "UST10Y", "WTI"],
    },
    "ALTA": {
        "palabras": [
            # Datos macro con potencial de sorpresa
            "cpi report", "core cpi", "inflation report", "pce data",
            "nonfarm payroll", "nfp report", "jobs report",
            "unemployment rate", "gdp growth", "gdp contraction",
            # Política monetaria explícita
            "rate hike", "rate cut", "rate increase", "rate decrease",
            "quantitative tightening", "quantitative easing",
            "powell speech", "lagarde speech", "fed chair",
            # Comercio y sanciones con impacto directo
            "new tariffs", "tariff increase", "trade sanctions",
            "oil embargo", "energy sanctions",
            # OPEC decisiones
            "opec cut", "opec production", "output cut", "opec+ decision",
            # Geopolítica de alto impacto
            "invasion begins", "ceasefire agreement", "peace deal signed",
            "sanctions imposed", "nuclear agreement",
        ],
        "ventana_horas": 6,
        "activos": ["SPX", "NDX", "Gold", "DXY", "WTI", "VIX"],
    },
}

# ── Score mínimo para enviar alerta ──────────────────────────────
# 70 = solo eventos con alta probabilidad de mover mercados
# Esto elimina noticias de deportes, entretenimiento, etc.
SCORE_MINIMO_ALERTA = 70

PRECEDENTES = {
    "CONFLICTO_ARMADO": {
        "condicion":   "Escalada o nueva acción militar",
        "n_eventos":   6,
        "prediccion": {
            "Gold": {"direccion":"SUBE","promedio_24h":"+2.1%","probabilidad":"83%"},
            "WTI":  {"direccion":"SUBE","promedio_24h":"+4.5%","probabilidad":"70%"},
            "SPX":  {"direccion":"BAJA","promedio_24h":"-1.8%","probabilidad":"67%"},
            "VIX":  {"direccion":"SUBE","promedio_24h":"+22%", "probabilidad":"78%"},
        },
        "tiempo_reaccion": "0-6h — prima de riesgo activa",
    },
    "TENSION_COMERCIAL": {
        "condicion":   "Nuevos aranceles o escalada comercial",
        "n_eventos":   7,
        "prediccion": {
            "SPX":  {"direccion":"BAJA","promedio_24h":"-2.1%","probabilidad":"74%"},
            "NDX":  {"direccion":"BAJA","promedio_24h":"-2.8%","probabilidad":"76%"},
            "Gold": {"direccion":"SUBE","promedio_24h":"+1.1%","probabilidad":"65%"},
        },
        "tiempo_reaccion": "0-4h post anuncio",
    },
    "CRISIS_ENERGETICA": {
        "condicion":   "Shock de oferta energética",
        "n_eventos":   5,
        "prediccion": {
            "WTI":  {"direccion":"SUBE","promedio_24h":"+4.2%","probabilidad":"85%"},
            "Gold": {"direccion":"SUBE","promedio_24h":"+0.8%","probabilidad":"60%"},
            "SPX":  {"direccion":"BAJA","promedio_24h":"-0.8%","probabilidad":"58%"},
        },
        "tiempo_reaccion": "0-3h post anuncio",
    },
    "FOMC_HAWKISH": {
        "condicion":   "FED más hawkish que expectativa",
        "n_eventos":   10,
        "prediccion": {
            "DXY":  {"direccion":"SUBE","promedio_24h":"+0.7%","probabilidad":"80%"},
            "SPX":  {"direccion":"BAJA","promedio_24h":"-1.7%","probabilidad":"75%"},
            "Gold": {"direccion":"BAJA","promedio_24h":"-0.4%","probabilidad":"65%"},
            "VIX":  {"direccion":"SUBE","promedio_24h":"+15%", "probabilidad":"70%"},
        },
        "tiempo_reaccion": "0-2h post comunicado",
    },
    "CPI_HAWKISH": {
        "condicion":   "CPI supera consenso",
        "n_eventos":   8,
        "prediccion": {
            "DXY":    {"direccion":"SUBE","promedio_24h":"+0.8%","probabilidad":"72%"},
            "SPX":    {"direccion":"BAJA","promedio_24h":"-1.2%","probabilidad":"68%"},
            "UST10Y": {"direccion":"SUBE","promedio_24h":"+5bps","probabilidad":"75%"},
        },
        "tiempo_reaccion": "0-4h post publicación",
    },
}


def hash_titular(titular: str) -> str:
    return hashlib.md5(titular.lower().strip().encode()).hexdigest()


def obtener_edad_horas(entry) -> float | None:
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


def detectar_situacion_activa(titular: str) -> dict | None:
    titular_lower = titular.lower()
    for s in SITUACIONES_ACTIVAS:
        if s["resuelto"]:
            continue
        if any(kw in titular_lower for kw in s["keywords"]):
            return s
    return None


def calcular_ventana(titular: str, edad_horas: float,
                      situacion: dict = None) -> dict:
    if situacion:
        return {
            "ventana_activa":      True,
            "estado":              f"SITUACIÓN ACTIVA — {situacion['nombre']}",
            "urgencia":            situacion["urgencia"],
            "horas_restantes":     999,
            "es_situacion_activa": True,
        }

    titular_lower = titular.lower()
    for nivel, cfg in KEYWORDS_URGENCIA.items():
        if any(p in titular_lower for p in cfg["palabras"]):
            ventana   = cfg["ventana_horas"]
            activa    = edad_horas <= ventana
            restantes = max(0, ventana - edad_horas)
            return {
                "ventana_activa":      activa,
                "estado": (
                    f"VENTANA ACTIVA — {round(restantes,1)}h restantes"
                    if activa else
                    f"ABSORBIDO — {round(edad_horas,1)}h (ventana {ventana}h)"
                ),
                "urgencia":            nivel,
                "horas_restantes":     restantes,
                "activos":             cfg["activos"],
                "es_situacion_activa": False,
            }

    # Sin keyword de impacto → no es relevante para KAIROS
    return {
        "ventana_activa":      False,
        "estado":              "SIN IMPACTO EN MERCADOS",
        "urgencia":            "IRRELEVANTE",
        "horas_restantes":     0,
        "es_situacion_activa": False,
    }


def identificar_precedente(titular: str, situacion: dict = None) -> dict | None:
    if situacion:
        clave = {
            "CONFLICTO_ARMADO":  "CONFLICTO_ARMADO",
            "TENSION_COMERCIAL": "TENSION_COMERCIAL",
            "CRISIS_ENERGETICA": "CRISIS_ENERGETICA",
        }.get(situacion["tipo"])
        if clave:
            return {"clave": clave, "datos": PRECEDENTES[clave]}

    titular_lower = titular.lower()
    if any(k in titular_lower for k in ["fomc","fed decision","rate decision","powell speech"]):
        return {"clave": "FOMC_HAWKISH", "datos": PRECEDENTES["FOMC_HAWKISH"]}
    if any(k in titular_lower for k in ["cpi report","inflation report","consumer price"]):
        return {"clave": "CPI_HAWKISH", "datos": PRECEDENTES["CPI_HAWKISH"]}
    return None


def calcular_score(edad_horas: float, absorcion: dict,
                    situacion: dict = None, precedente: dict = None,
                    peso_fuente: int = 8) -> int:
    if not absorcion["ventana_activa"]:
        return 0

    if situacion:
        base = situacion["score_base"]
        if edad_horas <= 0.5:   base = min(base + 8, 99)
        elif edad_horas <= 2:   base = min(base + 4, 96)
        elif edad_horas <= 6:   base = base
        elif edad_horas <= 24:  base = base - 8
        else:                   base = max(base - 15, 60)
        base += max(0, peso_fuente - 7)
        return min(base, 99)

    urgencia_pts = {"MAXIMA": 60, "ALTA": 45}.get(absorcion["urgencia"], 0)
    if urgencia_pts == 0:
        return 0  # sin urgencia reconocida → no alertar

    if edad_horas <= 0.25:   frescura = 35
    elif edad_horas <= 0.5:  frescura = 28
    elif edad_horas <= 1:    frescura = 20
    elif edad_horas <= 3:    frescura = 12
    elif edad_horas <= 6:    frescura = 5
    else:                    frescura = 0

    bonus_fuente    = max(0, peso_fuente - 7) * 2
    bonus_precedente= 5 if precedente else 0

    return min(urgencia_pts + frescura + bonus_fuente + bonus_precedente, 100)


def escanear_noticias_kairos(noticias_vistas: list = None) -> list:
    """
    Escanea RSS y retorna SOLO noticias con alta probabilidad
    de mover mercados. Score mínimo: 70/100.
    """
    if noticias_vistas is None:
        noticias_vistas = []

    eventos = []

    for fuente in FUENTES_RSS:
        try:
            print(f"  {fuente['nombre']}")
            feed = feedparser.parse(fuente["url"])

            for entry in feed.entries[:20]:
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

                situacion = detectar_situacion_activa(titular)

                if edad_horas > 48 and not situacion:
                    continue

                absorcion = calcular_ventana(titular, edad_horas, situacion)
                if not absorcion["ventana_activa"]:
                    continue

                try:
                    from geopolitica import clasificar_evento_geopolitico
                    geo = clasificar_evento_geopolitico(titular)
                except Exception:
                    geo = None

                precedente = identificar_precedente(titular, situacion)
                score = calcular_score(
                    edad_horas, absorcion, situacion,
                    precedente, fuente["peso"]
                )

                # ── FILTRO CRÍTICO: solo alto impacto ─────────────
                if score < SCORE_MINIMO_ALERTA:
                    continue

                eventos.append({
                    "titular":          titular,
                    "fuente":           fuente["nombre"],
                    "link":             entry.get("link", ""),
                    "edad_horas":       round(edad_horas, 2),
                    "absorcion":        absorcion,
                    "urgencia":         absorcion["urgencia"],
                    "situacion_activa": situacion,
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
    titular   = evento["titular"]
    fuente    = evento["fuente"]
    link      = evento["link"]
    score     = evento["score"]
    urgencia  = evento["urgencia"]
    edad      = evento["edad_horas"]
    absorcion = evento["absorcion"]
    situacion = evento.get("situacion_activa")
    geo       = evento.get("geo")
    precedente= evento.get("precedente")

    emojis = {"MAXIMA": "🚨", "ALTA": "⚠️"}
    emoji  = emojis.get(urgencia, "⚠️")
    tiempo = (f"hace {int(edad*60)} min" if edad < 1
              else f"hace {round(edad,1)}h")

    lineas = [
        f"{emoji} KAIROS — {'SITUACIÓN ACTIVA' if situacion else 'ALERTA'}",
        f"{'='*38}",
        f"📰 {titular}",
        f"📡 {fuente} | {tiempo}",
        f"🔗 {link}",
        f"",
    ]

    if situacion:
        lineas += [
            f"🔴 {situacion['nombre']}",
            f"📌 {situacion['nota']}",
            f"🎯 Score: {score}/100",
        ]
    else:
        lineas += [
            f"⏱️ {absorcion['estado']}",
            f"🎯 Score: {score}/100",
        ]

    if geo and geo.get("tipo") not in (None, "NO_CLASIFICADO"):
        impacto = geo.get("impacto", {})
        suben = [a for a,d in impacto.items() if d["direccion"]=="SUBE"]
        bajan = [a for a,d in impacto.items() if d["direccion"]=="BAJA"]
        lineas += [
            f"",
            f"🌍 {geo['tipo'].replace('_',' ')}",
            f"🟢 Suben: {', '.join(suben) or 'N/A'}",
            f"🔴 Bajan: {', '.join(bajan) or 'N/A'}",
        ]

    if precedente:
        d = precedente["datos"]
        lineas += [f"", f"📊 PREDICCIÓN ({d['n_eventos']} precedentes):"]
        for activo, pred in list(d["prediccion"].items())[:4]:
            flecha = "📈" if pred["direccion"]=="SUBE" else "📉"
            lineas.append(
                f"  {flecha} {activo}: {pred['promedio_24h']} ({pred['probabilidad']})"
            )
        lineas.append(f"  ⏱️ {d['tiempo_reaccion']}")

    lineas += ["", "kairos-markets.streamlit.app"]
    return "\n".join(lineas)


if __name__ == "__main__":
    print(f"\n🔍 KAIROS NEWS SCANNER v4")
    print(f"   Fuentes RSS:         {len(FUENTES_RSS)}")
    print(f"   Score mínimo alerta: {SCORE_MINIMO_ALERTA}/100")
    print(f"   Categorías activas:  MAXIMA + ALTA (sin MEDIA)")
    print(f"   Situaciones activas: {sum(1 for s in SITUACIONES_ACTIVAS if not s['resuelto'])}")
    print()

    for s in SITUACIONES_ACTIVAS:
        if not s["resuelto"]:
            print(f"  🔴 {s['nombre']} — Score base: {s['score_base']}")
    print()

    eventos = escanear_noticias_kairos()
    print(f"\n✅ {len(eventos)} eventos de alto impacto (score ≥{SCORE_MINIMO_ALERTA})\n")
    for i, e in enumerate(eventos[:5], 1):
        emoji = "🔴" if e.get("situacion_activa") else "⚠️"
        print(f"{emoji} #{i} Score:{e['score']} | {e['urgencia']}")
        print(f"   {e['titular'][:70]}")
        print(f"   {e['fuente']} | {e['edad_horas']}h")
        print()
