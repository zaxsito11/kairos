# api.py — KAIROS Public API
# FastAPI REST API para acceso programático a KAIROS.
# Ejecutar: uvicorn src.api:app --reload --port 8000
#
# ENDPOINTS:
#   GET  /                     → info del sistema
#   GET  /status               → estado actual
#   GET  /señales              → señales accionables del momento
#   GET  /precios              → precios en tiempo real
#   GET  /targets              → targets de precio 24h/7d/30d
#   GET  /tecnico/{activo}     → análisis técnico de un activo
#   GET  /fundamental          → contexto fundamental actual
#   GET  /calendario           → próximos eventos macro
#   GET  /brief/morning        → último morning brief
#   GET  /brief/weekly         → último weekly brief
#   POST /analizar/noticia     → analizar cualquier noticia
#   POST /analizar/evento      → analizar evento geopolítico
#   GET  /precision            → estadísticas de precisión
#   GET  /historial/alertas    → últimas alertas enviadas
#
# AUTENTICACIÓN:
#   Free:  sin API key — endpoints básicos con rate limit
#   Pro:   API key — todos los endpoints sin límite

import os, sys, json, glob
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

app = FastAPI(
    title       = "KAIROS Markets API",
    description = "Inteligencia de mercados en tiempo real. Predicciones, targets y análisis.",
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Rate limiting simple ──────────────────────────────────────────
_requests_hoy = {}

def check_rate_limit(api_key: str | None, endpoint: str) -> bool:
    """Free: 10 req/hora. Pro: ilimitado."""
    if api_key and api_key == os.getenv("KAIROS_PRO_KEY",""):
        return True  # Pro sin límite
    clave = f"{api_key or 'free'}_{datetime.now().strftime('%Y-%m-%d_%H')}"
    _requests_hoy[clave] = _requests_hoy.get(clave, 0) + 1
    return _requests_hoy[clave] <= 10


def es_pro(api_key: str | None) -> bool:
    return api_key and api_key == os.getenv("KAIROS_PRO_KEY","kairos-pro-2026")


# ── Modelos de request ────────────────────────────────────────────
class NoticiaRequest(BaseModel):
    titular: str
    fuente:  Optional[str] = ""
    link:    Optional[str] = ""

class EventoRequest(BaseModel):
    evento:   str
    categoria:Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────
def leer_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/", tags=["Info"])
def root():
    """Información del sistema KAIROS."""
    return {
        "nombre":      "KAIROS Markets API",
        "version":     "1.0.0",
        "descripcion": "The intelligence between events and markets",
        "docs":        "/docs",
        "canal":       "https://t.me/+Jk7_RXqqhAxlOGZh",
        "dashboard":   "https://kairos-markets.streamlit.app",
        "timestamp":   datetime.now().isoformat(),
    }


@app.get("/status", tags=["Sistema"])
def status(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Estado actual del sistema KAIROS."""
    if not check_rate_limit(api_key, "status"):
        raise HTTPException(429, "Rate limit: 10 req/hora. Obtén API Pro en kairos-markets.streamlit.app")

    estado = leer_json("data/monitor_estado.json")
    feedback = leer_json("data/feedback_estadisticas.json")

    return {
        "sistema":    "KAIROS v1",
        "estado":     "activo",
        "timestamp":  datetime.now().isoformat(),
        "monitor": {
            "alertas_enviadas": estado.get("alertas_enviadas", 0),
            "ultima_revision":  estado.get("ultima_revision","nunca"),
        },
        "precision": {
            "dir_24h": feedback.get("precision_dir_24h", 0),
            "total":   feedback.get("total_evaluaciones", 0),
        },
        "plan": "pro" if es_pro(api_key) else "free",
    }


@app.get("/señales", tags=["Análisis"])
def señales(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Señales accionables del momento — técnico + fundamental contrastados."""
    if not check_rate_limit(api_key, "señales"):
        raise HTTPException(429, "Rate limit alcanzado")

    try:
        from motor_contraste    import analisis_completo_mercado
        from contexto_kairos    import obtener_contexto_completo
        from news_scanner       import SITUACIONES_ACTIVAS

        ctx  = obtener_contexto_completo()
        resultado = analisis_completo_mercado()

        # Solo devolver accionables a free, todos a pro
        res = resultado.get("resultados",{})
        if not es_pro(api_key):
            # Free: solo los 3 más fuertes
            accionables = sorted(
                [r for r in res.values() if r.get("accionable")],
                key=lambda x: x.get("confianza",0), reverse=True
            )[:3]
            res_filtrado = {r["activo"]: r for r in accionables}
        else:
            res_filtrado = {k:v for k,v in res.items() if v.get("accionable")}

        return {
            "timestamp":     datetime.now().isoformat(),
            "n_accionables": resultado.get("n_accionables",0),
            "señales":       res_filtrado,
            "tono_fed":      ctx.get("tono_fed","N/A"),
            "regimen":       ctx.get("regimen",{}).get("regimen","N/A"),
        }
    except Exception as e:
        raise HTTPException(500, f"Error calculando señales: {e}")


@app.get("/precios", tags=["Mercados"])
def precios(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Precios en tiempo real de los 10 activos monitoreados."""
    if not check_rate_limit(api_key, "precios"):
        raise HTTPException(429, "Rate limit alcanzado")

    try:
        from precios import obtener_precios
        data = obtener_precios()
        return {
            "timestamp": datetime.now().isoformat(),
            "precios":   {k:v for k,v in data.items() if v},
        }
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo precios: {e}")


@app.get("/targets", tags=["Análisis"])
def targets(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Targets de precio 24h/7d/30d para todos los activos."""
    if not check_rate_limit(api_key, "targets"):
        raise HTTPException(429, "Rate limit alcanzado")

    try:
        from price_targets    import calcular_targets_fusionados
        from contexto_kairos  import obtener_contexto_completo
        ctx  = obtener_contexto_completo()
        data = calcular_targets_fusionados(
            regimen_macro     = ctx.get("regimen",{}).get("regimen","NEUTRO"),
            tono_fed          = ctx.get("tono_fed","NEUTRO"),
            situaciones_activas= ctx.get("situaciones",[]),
        )
        # Simplificar para API
        resultado = {}
        for activo, t in data.items():
            resultado[activo] = {
                "precio_actual": t.get("precio_actual"),
                "direccion":     t.get("direccion"),
                "probabilidad":  t.get("probabilidad"),
                "target_24h":    t.get("target_24h"),
                "target_7d":     t.get("target_7d"),
                "target_30d":    t.get("target_30d"),
                "soporte":       t.get("soporte_real"),
                "resistencia":   t.get("resist_real"),
                "rsi":           t.get("rsi"),
            }
        return {"timestamp": datetime.now().isoformat(), "targets": resultado}
    except Exception as e:
        raise HTTPException(500, f"Error calculando targets: {e}")


@app.get("/tecnico/{activo}", tags=["Análisis"])
def tecnico_activo(activo: str,
                    api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Análisis técnico completo de un activo (RSI, MACD, EMA, Vol, OBV, ATR)."""
    activos_validos = ["SPX","NDX","Gold","Silver","WTI","BTC","DXY","VIX","UST10Y"]
    if activo.upper() not in activos_validos:
        raise HTTPException(400, f"Activo no válido. Use: {activos_validos}")

    if not check_rate_limit(api_key, f"tecnico_{activo}"):
        raise HTTPException(429, "Rate limit alcanzado")

    try:
        from analisis_tecnico import analizar_activo
        data = analizar_activo(activo.upper())
        if not data:
            raise HTTPException(404, f"Sin datos para {activo}")
        return {"timestamp": datetime.now().isoformat(), "analisis": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.get("/fundamental", tags=["Análisis"])
def fundamental(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Contexto fundamental actual — macro, geopolítica, FED/BCE."""
    if not check_rate_limit(api_key, "fundamental"):
        raise HTTPException(429, "Rate limit alcanzado")

    try:
        from contexto_kairos import obtener_contexto_completo
        ctx = obtener_contexto_completo()
        return {
            "timestamp":    datetime.now().isoformat(),
            "tono_fed":     ctx.get("tono_fed"),
            "tono_bce":     ctx.get("tono_bce"),
            "regimen":      ctx.get("regimen"),
            "situaciones":  ctx.get("situaciones"),
            "relevancia":   ctx.get("relevancia"),
            "factor_dominante": ctx.get("factor_dominante"),
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.get("/calendario", tags=["Eventos"])
def calendario(dias: int = Query(30, ge=1, le=90),
                api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Próximos eventos macro con capacidad de mover mercados."""
    if not check_rate_limit(api_key, "calendario"):
        raise HTTPException(429, "Rate limit alcanzado")

    try:
        from calendario_eco import obtener_eventos_proximos
        eventos = obtener_eventos_proximos(dias=dias)
        return {
            "timestamp": datetime.now().isoformat(),
            "total":     len(eventos),
            "eventos":   eventos,
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.get("/brief/morning", tags=["Briefs"])
def brief_morning(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Último Morning Brief generado."""
    if not check_rate_limit(api_key, "brief_morning"):
        raise HTTPException(429, "Rate limit alcanzado")

    data = leer_json("data/ultimo_brief.json")
    if not data:
        raise HTTPException(404, "Sin brief disponible")

    # Free: solo resumen. Pro: brief completo
    if es_pro(api_key):
        return data
    else:
        brief = data.get("brief","")
        # Extraer solo resumen ejecutivo
        lineas = brief.split("\n")
        resumen = []
        en_res = False
        for l in lineas:
            if "RESUMEN EJECUTIVO" in l: en_res = True; continue
            if en_res and l.strip().startswith("**") and "RESUMEN" not in l: break
            if en_res: resumen.append(l)
        return {
            "fecha":   data.get("fecha"),
            "resumen": "\n".join(resumen[:5]),
            "nota":    "Brief completo disponible en plan Pro",
        }


@app.get("/brief/weekly", tags=["Briefs"])
def brief_weekly(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Último Weekly Brief."""
    if not check_rate_limit(api_key, "brief_weekly"):
        raise HTTPException(429, "Rate limit alcanzado")

    data = leer_json("data/ultimo_weekly_brief.json")
    if not data:
        # Buscar en archivos
        archivos = sorted(glob.glob("outputs/weekly_brief_*.txt"), reverse=True)
        if archivos:
            with open(archivos[0], encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
            nombre = os.path.basename(archivos[0]).replace("weekly_brief_","").replace(".txt","")
            if es_pro(api_key):
                return {"fecha": nombre, "brief": contenido}
            return {"fecha": nombre, "resumen": contenido[:300] + "...",
                    "nota": "Brief completo en plan Pro"}
        raise HTTPException(404, "Sin weekly brief disponible")

    if es_pro(api_key):
        return data
    return {"fecha": data.get("fecha"), "nota": "Brief completo en plan Pro"}


@app.post("/analizar/noticia", tags=["Análisis"])
def analizar_noticia(request: NoticiaRequest,
                      api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    Analiza cualquier noticia con IA y determina su impacto en los mercados.
    La IA evalúa qué activos se moverán y en qué dirección.
    """
    if not check_rate_limit(api_key, "analizar_noticia"):
        raise HTTPException(429, "Rate limit alcanzado")

    try:
        from analizador_noticias import analizar_noticia_con_ia
        from contexto_kairos     import obtener_contexto_completo
        ctx      = obtener_contexto_completo()
        analisis = analizar_noticia_con_ia(
            request.titular, request.fuente, ctx
        )
        return {
            "timestamp": datetime.now().isoformat(),
            "titular":   request.titular,
            "analisis":  analisis,
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.post("/analizar/evento", tags=["Análisis"])
def analizar_evento(request: EventoRequest,
                     api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    Analiza un evento fundamental y su impacto por activo.
    Macro, geopolítico, político, energético, corporativo.
    """
    if not check_rate_limit(api_key, "analizar_evento"):
        raise HTTPException(429, "Rate limit alcanzado")

    try:
        from analisis_fundamental import (analizar_evento_fundamental,
                                           detectar_categoria_evento)
        cat, sub = detectar_categoria_evento(request.evento)
        if request.categoria:
            cat = request.categoria
        resultado = analizar_evento_fundamental(request.evento, cat, sub)
        return {
            "timestamp": datetime.now().isoformat(),
            "evento":    request.evento,
            "categoria": cat,
            "subtipo":   sub,
            "analisis":  resultado.get("analisis_ia",{}),
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.get("/precision", tags=["Sistema"])
def precision(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Estadísticas de precisión del sistema KAIROS."""
    if not check_rate_limit(api_key, "precision"):
        raise HTTPException(429, "Rate limit alcanzado")

    data = leer_json("data/feedback_estadisticas.json")
    if not data:
        return {"mensaje": "Sin datos de precisión aún. Sistema en calibración."}

    respuesta = {
        "precision_dir_24h":   data.get("precision_dir_24h",0),
        "precision_rango_24h": data.get("precision_rango_24h",0),
        "total_evaluaciones":  data.get("total_evaluaciones",0),
        "error_target_avg":    data.get("error_target_avg",0),
        "ultima_evaluacion":   data.get("ultima_evaluacion"),
    }

    if es_pro(api_key):
        respuesta["por_activo"] = data.get("por_activo",{})
        respuesta["historial"]  = data.get("historial",[])[-30:]

    return {"timestamp": datetime.now().isoformat(), **respuesta}


@app.get("/historial/alertas", tags=["Sistema"])
def historial_alertas(limite: int = Query(20, ge=1, le=100),
                       api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Últimas alertas enviadas al canal Telegram."""
    if not check_rate_limit(api_key, "historial"):
        raise HTTPException(429, "Rate limit alcanzado")

    if not es_pro(api_key):
        limite = min(limite, 5)

    log_file = "outputs/monitor.log"
    alertas  = []

    if os.path.exists(log_file):
        try:
            with open(log_file, encoding="utf-8", errors="ignore") as f:
                lineas = f.readlines()
            for l in lineas:
                if "Alerta enviada" in l or "score:" in l.lower():
                    alertas.append(l.strip())
            alertas = alertas[-limite:]
        except Exception as e:
            raise HTTPException(500, f"Error leyendo log: {e}")

    return {
        "timestamp": datetime.now().isoformat(),
        "total":     len(alertas),
        "alertas":   alertas,
        "nota":      "Historial completo disponible en plan Pro" if not es_pro(api_key) else None,
    }


# ── Health check ──────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
