# news_realtime.py — KAIROS
# Noticias en tiempo real via NewsAPI.org — Plan GRATUITO optimizado.
#
# FILOSOFÍA: RSS cubre el volumen. NewsAPI cubre la VELOCIDAD.
# Solo 2 queries ultra-selectivas cada 30 minutos = 96 req/día
# (dentro del límite gratuito de 100/día)
#
# QUERY 1: Bancos centrales en acción (FED/BCE decisiones en vivo)
# QUERY 2: Shocks de mercado (guerra, energía, crisis sistémica)
#
# Estas 2 categorías representan el 80% de los movimientos
# de mercado >2% en los últimos 5 años.

import os
import json
import hashlib
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY  = os.getenv("NEWSAPI_KEY", "")
ESTADO_FILE  = "data/newsapi_estado.json"
INTERVALO_MIN = 30   # cada 30 minutos — respeta el límite gratuito

# ── Las 2 queries que cubren el 80% del impacto de mercado ────────

QUERY_BANCOS_CENTRALES = {
    "nombre":   "Bancos Centrales — Decisión en vivo",
    "query": (
        '"rate decision" OR "FOMC statement" OR "Fed raises" OR '
        '"Fed cuts" OR "ECB raises" OR "ECB cuts" OR '
        '"Powell press conference" OR "Lagarde press conference" OR '
        '"emergency rate" OR "surprise rate"'
    ),
    "urgencia":  "MAXIMA",
    "score_base": 95,
    "activos":   ["SPX", "DXY", "UST10Y", "Gold", "VIX", "EURUSD"],
    "ventana_h": 1,
    "razon":     "Decisiones de tasas mueven SPX >1.5% en <30 min históricamente",
}

QUERY_SHOCKS_MERCADO = {
    "nombre":   "Shocks — Guerra / Energía / Crisis sistémica",
    "query": (
        '"military strike" OR "invasion" OR "war escalation" OR '
        '"Hormuz blockade" OR "oil supply" OR "OPEC emergency" OR '
        '"bank collapse" OR "financial crisis" OR '
        '"nuclear threat" OR "sanctions oil" OR '
        '"circuit breaker" OR "market halt"'
    ),
    "urgencia":  "MAXIMA",
    "score_base": 90,
    "activos":   ["WTI", "Gold", "VIX", "SPX", "DXY"],
    "ventana_h": 2,
    "razon":     "Shocks geopolíticos y energéticos mueven WTI >3% y Gold >1.5%",
}

# Fuentes que primero publican noticias de alto impacto
FUENTES_PRIMARIAS = "reuters.com,bloomberg.com,ft.com,wsj.com,cnbc.com"


# ── Estado persistente ────────────────────────────────────────────
def cargar_estado() -> dict:
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "urls_vistas":        [],
        "ultima_consulta_bc": None,
        "ultima_consulta_sh": None,
        "requests_hoy":       0,
        "fecha_reset":        datetime.now().strftime("%Y-%m-%d"),
        "alertas_enviadas":   0,
    }


def guardar_estado(estado: dict):
    estado["urls_vistas"] = estado["urls_vistas"][-3000:]
    os.makedirs("data", exist_ok=True)
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def verificar_reset_diario(estado: dict):
    """Resetea el contador de requests si es un nuevo día."""
    hoy = datetime.now().strftime("%Y-%m-%d")
    if estado.get("fecha_reset") != hoy:
        estado["requests_hoy"] = 0
        estado["fecha_reset"]  = hoy
        print(f"  ✅ Contador NewsAPI reseteado para {hoy}")


def puede_consultar(estado: dict, limite: int = 95) -> bool:
    """Verifica que no se supere el límite gratuito (guardamos 5 de margen)."""
    verificar_reset_diario(estado)
    restantes = limite - estado.get("requests_hoy", 0)
    if restantes <= 0:
        print(f"  ⚠️ Límite diario NewsAPI alcanzado ({limite} requests)")
        return False
    print(f"  📊 NewsAPI: {estado['requests_hoy']}/{limite} requests hoy "
          f"({restantes} restantes)")
    return True


def deberia_consultar(ultima_consulta_iso: str | None,
                       intervalo_min: int = INTERVALO_MIN) -> bool:
    """Verifica si ya pasó el intervalo mínimo desde la última consulta."""
    if not ultima_consulta_iso:
        return True
    try:
        ultima = datetime.fromisoformat(ultima_consulta_iso)
        return datetime.now() - ultima >= timedelta(minutes=intervalo_min)
    except Exception:
        return True


# ── Consulta NewsAPI ──────────────────────────────────────────────
def consultar_query(query_config: dict, horas_atras: float,
                    estado: dict) -> list:
    """Realiza una consulta a NewsAPI y retorna artículos nuevos."""
    desde = (datetime.utcnow() - timedelta(hours=horas_atras)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        query_config["query"],
                "from":     desde,
                "sortBy":   "publishedAt",
                "language": "en",
                "sources":  FUENTES_PRIMARIAS,
                "pageSize": 5,   # máximo 5 por query — suficiente y eficiente
                "apiKey":   NEWSAPI_KEY,
            },
            timeout=10
        )
        estado["requests_hoy"] = estado.get("requests_hoy", 0) + 1

        if r.status_code == 200:
            return r.json().get("articles", [])
        elif r.status_code == 429:
            print(f"  ⚠️ Rate limit NewsAPI")
        elif r.status_code == 401:
            print(f"  ❌ NEWSAPI_KEY inválida")
        else:
            print(f"  ⚠️ NewsAPI error {r.status_code}")

    except Exception as e:
        print(f"  Error NewsAPI: {e}")

    return []


def procesar_articulos(articulos: list, query_config: dict,
                        estado: dict) -> list:
    """Convierte artículos en eventos KAIROS, filtrando duplicados."""
    eventos = []

    for art in articulos:
        url     = art.get("url", "")
        titular = art.get("title", "").strip()
        fuente  = art.get("source", {}).get("name", "")
        fecha   = art.get("publishedAt", "")

        if not url or not titular:
            continue

        # Filtrar ya vistas
        h = hashlib.md5(url.encode()).hexdigest()
        if h in estado["urls_vistas"]:
            continue
        estado["urls_vistas"].append(h)

        # Calcular edad
        edad_horas = 1.0
        if fecha:
            try:
                dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                edad_horas = (datetime.utcnow() - dt).total_seconds() / 3600
            except Exception:
                pass

        # Score ajustado por frescura
        score = query_config["score_base"]
        if edad_horas <= 0.25:   score = min(score + 5, 99)
        elif edad_horas <= 0.5:  score = score
        elif edad_horas <= 1:    score = score - 5
        elif edad_horas <= 2:    score = score - 10
        else:                    score = score - 15
        score = max(score, 55)

        eventos.append({
            "titular":     titular,
            "fuente":      fuente,
            "link":        url,
            "descripcion": art.get("description", "")[:200],
            "edad_horas":  round(edad_horas, 2),
            "urgencia":    query_config["urgencia"],
            "score":       score,
            "activos":     query_config["activos"],
            "tipo_evento": query_config["nombre"],
            "hash":        h,
            "timestamp":   datetime.now().isoformat(),
            "fuente_api":  "newsapi",
        })

    return eventos


# ── Función principal ─────────────────────────────────────────────
def escanear_noticias_realtime(urls_vistas_ext: list = None) -> list:
    """
    Escanea las 2 queries críticas de NewsAPI.
    Respeta el límite gratuito de 100 req/día.
    Intervalo mínimo: 30 minutos entre consultas.

    Returns:
        Lista de eventos de alto impacto, ordenados por score.
    """
    if not NEWSAPI_KEY:
        return []

    estado = cargar_estado()

    # Sincronizar URLs externas
    if urls_vistas_ext:
        for h in urls_vistas_ext:
            if h not in estado["urls_vistas"]:
                estado["urls_vistas"].append(h)

    if not puede_consultar(estado):
        guardar_estado(estado)
        return []

    todos_eventos = []

    # ── Query 1: Bancos Centrales ─────────────────────────────────
    clave_bc = "ultima_consulta_bc"
    if deberia_consultar(estado.get(clave_bc), INTERVALO_MIN):
        print(f"  Consultando: {QUERY_BANCOS_CENTRALES['nombre']}")
        arts = consultar_query(QUERY_BANCOS_CENTRALES, 1.0, estado)
        evs  = procesar_articulos(arts, QUERY_BANCOS_CENTRALES, estado)
        todos_eventos.extend(evs)
        estado[clave_bc] = datetime.now().isoformat()
        print(f"    → {len(evs)} eventos nuevos")
    else:
        print(f"  ⏳ Bancos Centrales: esperando intervalo de {INTERVALO_MIN}min")

    # ── Query 2: Shocks de mercado ────────────────────────────────
    clave_sh = "ultima_consulta_sh"
    if deberia_consultar(estado.get(clave_sh), INTERVALO_MIN):
        print(f"  Consultando: {QUERY_SHOCKS_MERCADO['nombre']}")
        arts = consultar_query(QUERY_SHOCKS_MERCADO, 2.0, estado)
        evs  = procesar_articulos(arts, QUERY_SHOCKS_MERCADO, estado)
        todos_eventos.extend(evs)
        estado[clave_sh] = datetime.now().isoformat()
        print(f"    → {len(evs)} eventos nuevos")
    else:
        print(f"  ⏳ Shocks: esperando intervalo de {INTERVALO_MIN}min")

    guardar_estado(estado)

    # Deduplicar y ordenar
    vistos = set()
    finales = []
    for e in sorted(todos_eventos, key=lambda x: x["score"], reverse=True):
        clave = e["titular"][:50].lower()
        if clave not in vistos:
            vistos.add(clave)
            finales.append(e)

    return finales


def formatear_alerta_realtime(evento: dict) -> str:
    """Genera el mensaje de Telegram para un evento de NewsAPI."""
    titular  = evento["titular"]
    fuente   = evento["fuente"]
    link     = evento["link"]
    score    = evento["score"]
    activos  = ", ".join(evento["activos"])
    tipo     = evento["tipo_evento"]
    edad     = evento["edad_horas"]
    desc     = evento.get("descripcion", "")
    urgencia = evento["urgencia"]

    emoji = "🚨" if urgencia == "MAXIMA" else "⚠️"
    tiempo = (f"hace {int(edad*60)} min" if edad < 1
              else f"hace {round(edad,1)}h")

    lineas = [
        f"{emoji} KAIROS — ALERTA TIEMPO REAL",
        f"{'='*38}",
        f"📰 {titular}",
        f"📡 {fuente} | {tiempo}",
        f"🔗 {link}",
        f"🏷️ {tipo}",
    ]
    if desc:
        lineas += [f"", f"📋 {desc}"]
    lineas += [
        f"",
        f"📊 Activos en riesgo: {activos}",
        f"🎯 Score: {score}/100",
        f"",
        f"kairos-markets.streamlit.app",
    ]
    return "\n".join(lineas)


def status_uso() -> dict:
    """Retorna el estado de uso de la API para mostrar en dashboard."""
    estado = cargar_estado()
    verificar_reset_diario(estado)
    return {
        "requests_hoy":     estado.get("requests_hoy", 0),
        "limite_diario":    100,
        "restantes":        100 - estado.get("requests_hoy", 0),
        "ultima_bc":        estado.get("ultima_consulta_bc", "nunca"),
        "ultima_sh":        estado.get("ultima_consulta_sh", "nunca"),
        "alertas_enviadas": estado.get("alertas_enviadas", 0),
    }


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n📡 KAIROS NEWS REALTIME — TEST")
    print("="*50)

    print(f"\nConfiguración actual:")
    print(f"  Intervalo:      cada {INTERVALO_MIN} minutos")
    print(f"  Requests/día:   2 queries × 48 ciclos = 96/día")
    print(f"  Límite gratuito: 100/día")
    print(f"  Margen:         4 requests de seguridad")

    print(f"\nQueries activas:")
    for q in [QUERY_BANCOS_CENTRALES, QUERY_SHOCKS_MERCADO]:
        print(f"\n  🎯 {q['nombre']}")
        print(f"     Score base: {q['score_base']}/100")
        print(f"     Activos:    {', '.join(q['activos'])}")
        print(f"     Razón:      {q['razon']}")

    if not NEWSAPI_KEY:
        print(f"\n⚠️ NEWSAPI_KEY no configurada en .env")
        print(f"\nPara activar (gratis):")
        print(f"  1. newsapi.org/register")
        print(f"  2. Copia tu API key")
        print(f"  3. Agrega en .env: NEWSAPI_KEY=tu_key")
    else:
        print(f"\n✅ NEWSAPI_KEY configurada")
        st = status_uso()
        print(f"   Requests hoy: {st['requests_hoy']}/{st['limite_diario']}")
        print(f"   Restantes:    {st['restantes']}")
        print(f"\nEscaneando...")
        eventos = escanear_noticias_realtime()
        if eventos:
            print(f"\n✅ {len(eventos)} eventos de alto impacto:")
            for i, e in enumerate(eventos, 1):
                print(f"\n  #{i} Score: {e['score']}/100")
                print(f"      {e['titular'][:70]}")
                print(f"      {e['fuente']} | {e['edad_horas']}h")
        else:
            print("\n✓ Sin eventos nuevos de alto impacto")
