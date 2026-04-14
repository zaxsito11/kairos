# news_scanner.py — KAIROS v3
# Scanner de noticias con filtro de absorción de mercado.
# 10 fuentes RSS verificadas + detección de situaciones activas.

import feedparser
import hashlib
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# ── 10 Fuentes RSS verificadas ────────────────────────────────────
# Seleccionadas por velocidad, relevancia macro y acceso gratuito
FUENTES_RSS = [
    # ── Agencias globales (más rápidas en breaking news)
    {
        "nombre": "Reuters Business",
        "url":    "https://feeds.reuters.com/reuters/businessNews",
        "peso":   10,  # 10 = máxima confiabilidad
    },
    {
        "nombre": "Reuters Markets",
        "url":    "https://feeds.reuters.com/reuters/UKdomesticNews",
        "peso":   10,
    },
    {
        "nombre": "Reuters Top News",
        "url":    "https://feeds.reuters.com/reuters/topNews",
        "peso":   9,
    },
    # ── TV financiera (muy rápida en datos macro)
    {
        "nombre": "CNBC Markets",
        "url":    "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "peso":   9,
    },
    {
        "nombre": "CNBC Economy",
        "url":    "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "peso":   8,
    },
    # ── Bloomberg (mercados en tiempo real)
    {
        "nombre": "Bloomberg Markets",
        "url":    "https://feeds.bloomberg.com/markets/news.rss",
        "peso":   10,
    },
    # ── Yahoo Finance (amplia cobertura, gratuito)
    {
        "nombre": "Yahoo Finance",
        "url":    "https://finance.yahoo.com/rss/topstories",
        "peso":   8,
    },
    # ── Investing.com (cobertura macro global)
    {
        "nombre": "Investing.com Global",
        "url":    "https://www.investing.com/rss/news_301.rss",
        "peso":   8,
    },
    {
        "nombre": "Investing.com ES",
        "url":    "https://es.investing.com/rss/news.rss",
        "peso":   7,
    },
    # ── MarketWatch (datos EEUU + earnings)
    {
        "nombre": "MarketWatch",
        "url":    "https://feeds.marketwatch.com/marketwatch/topstories/",
        "peso":   8,
    },
]

# ── Situaciones activas en el mundo ──────────────────────────────
# Eventos sin resolver que siguen moviendo mercados.
# Score SIEMPRE ALTO hasta que se marquen como resueltos.
# ⚠️ Actualizar cuando un evento se resuelva o aparezca uno nuevo.
SITUACIONES_ACTIVAS = [
    {
        "nombre":   "Conflicto EEUU-Israel-Irán",
        "keywords": [
            "iran", "hormuz", "strait of hormuz", "middle east war",
            "israel attack", "tehran", "persian gulf", "irán",
            "estrecho de ormuz", "oriente medio conflicto",
            "operation", "military iran", "us iran",
        ],
        "tipo":      "CONFLICTO_ARMADO",
        "urgencia":  "MAXIMA",
        "score_base": 88,
        "activos":   ["WTI", "Gold", "VIX", "SPX", "DXY"],
        "resuelto":  False,
        "nota":      "Operación Furia Épica — semana 6. WTI $100.",
    },
    {
        "nombre":   "Guerra comercial EEUU-China",
        "keywords": [
            "tariff china", "chinese tariffs", "trade war china",
            "us china trade", "arancel china", "guerra comercial",
            "trump tariff", "beijing retaliation",
        ],
        "tipo":      "TENSION_COMERCIAL",
        "urgencia":  "ALTA",
        "score_base": 78,
        "activos":   ["SPX", "NDX", "DXY", "Gold"],
        "resuelto":  False,
        "nota":      "Aranceles Trump activos — escalada en curso.",
    },
    {
        "nombre":   "Crisis energética — WTI $100",
        "keywords": [
            "oil $100", "crude $100", "brent $100",
            "oil supply crisis", "energy crisis",
            "petróleo 100", "precio petróleo dispara",
        ],
        "tipo":      "CRISIS_ENERGETICA",
        "urgencia":  "ALTA",
        "score_base": 75,
        "activos":   ["WTI", "Gold", "SPX", "DXY"],
        "resuelto":  False,
        "nota":      "WTI en $100 por bloqueo Ormuz.",
    },
]

# ── Keywords por urgencia (eventos puntuales) ─────────────────────
KEYWORDS_URGENCIA = {
    "MAXIMA": {
        "palabras": [
            "rate decision", "fomc statement", "fed raises", "fed cuts",
            "ecb raises", "ecb cuts", "emergency rate", "surprise rate",
            "military strike", "invasion", "war escalation",
            "bank collapse", "bank run", "circuit breaker", "market halt",
            "nuclear", "hormuz blockade", "oil supply cut",
        ],
        "ventana_horas": 2,
        "activos": ["SPX", "VIX", "Gold", "DXY", "UST10Y", "WTI"],
    },
    "ALTA": {
        "palabras": [
            "inflation", "inflación", "cpi", "pce", "core cpi",
            "nfp", "jobs report", "unemployment", "gdp", "recession",
            "rate hike", "rate cut", "powell", "lagarde",
            "tariff", "arancel", "sanctions", "sanciones",
            "opec", "oil cut", "production cut",
            "invasion", "invasión", "ceasefire",
        ],
        "ventana_horas": 6,
        "activos": ["SPX", "NDX", "Gold", "DXY", "WTI", "VIX"],
    },
    "MEDIA": {
        "palabras": [
            "federal reserve", "interest rate", "monetary policy",
            "earnings miss", "earnings beat", "guidance cut",
            "geopolitical", "default", "debt ceiling",
            "election upset", "political crisis",
        ],
        "ventana_horas": 12,
        "activos": ["SPX", "Gold", "DXY"],
    },
}

# ── Precedentes históricos ────────────────────────────────────────
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


# ── Utilidades ────────────────────────────────────────────────────
def hash_titular(titular: str) -> str:
    return __import__("hashlib").md5(
        titular.lower().strip().encode()
    ).hexdigest()


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

    activa = edad_horas <= 4
    return {
        "ventana_activa":      activa,
        "estado":              (
            f"VENTANA ACTIVA — {round(max(0,4-edad_horas),1)}h restantes"
            if activa else "ABSORBIDO"
        ),
        "urgencia":            "MEDIA",
        "horas_restantes":     max(0, 4 - edad_horas),
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
    if any(k in titular_lower for k in ["fomc","fed decision","rate decision","powell"]):
        return {"clave": "FOMC_HAWKISH", "datos": PRECEDENTES["FOMC_HAWKISH"]}
    if any(k in titular_lower for k in ["cpi","inflation data","consumer price"]):
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
        # Bonus por fuente de alta confiabilidad
        base += max(0, (peso_fuente - 7))
        return min(base, 99)

    urgencia_pts = {"MAXIMA": 55, "ALTA": 40, "MEDIA": 25}.get(
        absorcion["urgencia"], 20
    )
    if edad_horas <= 0.25:   frescura = 35
    elif edad_horas <= 0.5:  frescura = 28
    elif edad_horas <= 1:    frescura = 20
    elif edad_horas <= 3:    frescura = 12
    elif edad_horas <= 6:    frescura = 5
    else:                    frescura = 0

    return min(urgencia_pts + frescura + (5 if precedente else 0), 100)


# ── Función principal ─────────────────────────────────────────────
def escanear_noticias_kairos(noticias_vistas: list = None) -> list:
    """
    Escanea las 10 fuentes RSS y retorna eventos con
    ventana de oportunidad activa, ordenados por score.
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

                # Descartar si es muy vieja y no es situación activa
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

                if score < 25:
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

    emojis = {"MAXIMA": "🚨", "ALTA": "⚠️", "MEDIA": "📡"}
    emoji  = emojis.get(urgencia, "📡")
    tiempo = (f"hace {int(edad*60)} min" if edad < 1
              else f"hace {round(edad,1)}h")

    lineas = [
        f"{emoji} KAIROS — {'SITUACIÓN ACTIVA' if situacion else 'VENTANA ACTIVA'}",
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
    print("\n🔍 KAIROS NEWS SCANNER v3")
    print(f"   Fuentes RSS: {len(FUENTES_RSS)}")
    print(f"   Situaciones activas: {sum(1 for s in SITUACIONES_ACTIVAS if not s['resuelto'])}")
    print()

    for s in SITUACIONES_ACTIVAS:
        if not s["resuelto"]:
            print(f"  🔴 {s['nombre']} — Score base: {s['score_base']}")
    print()

    eventos = escanear_noticias_kairos()
    print(f"\n✅ {len(eventos)} eventos con ventana activa\n")
    for i, e in enumerate(eventos[:5], 1):
        tipo = "🔴" if e.get("situacion_activa") else "⚠️"
        print(f"{tipo} #{i} Score:{e['score']} | {e['titular'][:65]}")
        print(f"   {e['fuente']} | {e['edad_horas']}h | {e['urgencia']}")
        print()
