# analizador_noticias.py — KAIROS
# Analiza automáticamente CUALQUIER noticia con IA.
# No usa patrones hardcodeados — la IA lee la noticia y decide.
#
# FLUJO:
#   1. Noticia llega con score≥70
#   2. IA analiza: ¿puede mover el mercado? ¿en qué dirección? ¿cuánto?
#   3. Si el impacto es significativo → actualiza predicciones
#   4. Envía al canal con análisis específico

import os, sys, json, logging
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

client   = Groq(api_key=os.getenv("GROQ_API_KEY"))
LOG_FILE = "outputs/analizador_noticias.log"
CACHE_FILE = "data/noticias_analizadas.json"

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
log = logging.getLogger("KAIROS.analizador_noticias")


def ya_analizada(titular: str) -> bool:
    """Evita analizar la misma noticia dos veces."""
    if not os.path.exists(CACHE_FILE):
        return False
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        # Comparar por primeros 60 chars del titular
        clave = titular[:60].lower()
        return clave in cache.get("titulares", [])
    except Exception:
        return False


def marcar_analizada(titular: str):
    cache = {"titulares": []}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
        except Exception:
            pass
    cache.setdefault("titulares", [])
    cache["titulares"].append(titular[:60].lower())
    cache["titulares"] = cache["titulares"][-200:]
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=True)


def analizar_noticia_con_ia(titular: str, fuente: str = "",
                              contexto_actual: dict = None) -> dict:
    """
    La IA analiza la noticia y determina:
    - ¿Puede mover el mercado significativamente?
    - ¿Qué activos afecta y en qué dirección?
    - ¿Cambia el contexto actual de predicciones?
    - ¿Qué tan urgente es actuar?
    """
    ctx = contexto_actual or {}
    reg = ctx.get("regimen",{}).get("regimen","NEUTRO")
    sit = ctx.get("situaciones",[])
    sits_str = "\n".join([f"  - {s['nombre']}: {s['nota']}" for s in sit]) or "Ninguna"

    prompt = f"""Eres el analista de noticias de KAIROS Markets.
Tu trabajo: analizar una noticia y determinar su impacto real en los mercados financieros.

NOTICIA: {titular}
FUENTE: {fuente}

CONTEXTO ACTUAL DEL MERCADO:
  Régimen macro: {reg}
  Situaciones activas:
{sits_str}

Analiza esta noticia y responde SOLO con este JSON:
{{
  "mueve_mercado": true/false,
  "urgencia": "CRITICA/ALTA/MEDIA/BAJA",
  "tipo_evento": "GEOPOLITICA/BANCO_CENTRAL/COMERCIO/MACRO_DATO/ENERGIA/CORPORATIVO/POLITICO/OTRO",
  "impacto_por_activo": {{
    "SPX":    {{"dir": "SUBE/BAJA/NEUTRO", "confianza": 0-100, "razon": "max 20 palabras"}},
    "NDX":    {{"dir": "SUBE/BAJA/NEUTRO", "confianza": 0-100, "razon": "max 20 palabras"}},
    "Gold":   {{"dir": "SUBE/BAJA/NEUTRO", "confianza": 0-100, "razon": "max 20 palabras"}},
    "Silver": {{"dir": "SUBE/BAJA/NEUTRO", "confianza": 0-100, "razon": "max 20 palabras"}},
    "WTI":    {{"dir": "SUBE/BAJA/NEUTRO", "confianza": 0-100, "razon": "max 20 palabras"}},
    "BTC":    {{"dir": "SUBE/BAJA/NEUTRO", "confianza": 0-100, "razon": "max 20 palabras"}},
    "DXY":    {{"dir": "SUBE/BAJA/NEUTRO", "confianza": 0-100, "razon": "max 20 palabras"}},
    "VIX":    {{"dir": "SUBE/BAJA/NEUTRO", "confianza": 0-100, "razon": "max 20 palabras"}}
  }},
  "cambia_contexto": true/false,
  "nuevo_contexto": "descripcion breve de qué cambió",
  "ventana_minutos": 30-480,
  "resumen_impacto": "1 oración: qué pasó y qué mueve",
  "activo_mas_afectado": "el activo con mayor impacto directo"
}}

Criterios para mueve_mercado=true:
  - Evento geopolítico que afecta suministro de energía o seguridad
  - Decisión de banco central inesperada
  - Dato macro que sorprende el consenso >0.3%
  - Acuerdo/ruptura comercial entre potencias
  - Decisión presidencial con impacto económico directo
  - Evento corporativo que mueve índices >0.5%

Responde SOLO con el JSON. Sin texto adicional."""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system",
                 "content": "Eres analista de mercados. Respondes solo en JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=600
        )
        texto = resp.choices[0].message.content.strip()
        if "```" in texto:
            texto = texto.split("```")[1].replace("json","").strip()
        return json.loads(texto)

    except Exception as e:
        log.error(f"  Error IA: {e}")
        return {"mueve_mercado": False, "urgencia": "BAJA"}


def formatear_alerta_noticia_ia(titular: str, fuente: str,
                                  link: str, analisis: dict) -> str:
    """Formatea la alerta con el análisis IA incluido."""
    urgencia   = analisis.get("urgencia","MEDIA")
    tipo       = analisis.get("tipo_evento","OTRO")
    resumen    = analisis.get("resumen_impacto","")
    activo_key = analisis.get("activo_mas_afectado","")
    ventana    = analisis.get("ventana_minutos",60)
    impacto    = analisis.get("impacto_por_activo",{})

    emoji_urg  = {"CRITICA":"🚨","ALTA":"⚠️","MEDIA":"📡","BAJA":"📋"}.get(urgencia,"📡")

    lineas = [
        f"{emoji_urg} KAIROS — {urgencia}",
        f"{'='*38}",
        f"📰 {titular}",
        f"📡 {fuente}",
    ]
    if link:
        lineas.append(f"🔗 {link}")
    lineas += [
        f"",
        f"🏷️ {tipo}",
        f"💡 {resumen}",
        f"⏱️ Ventana: ~{ventana} min",
        f"",
    ]

    # Activos más afectados (solo los no neutros)
    activos_movidos = {k:v for k,v in impacto.items()
                       if v.get("dir","NEUTRO") != "NEUTRO"
                       and v.get("confianza",0) >= 60}

    if activos_movidos:
        lineas.append("📊 Impacto esperado:")
        for activo, info in sorted(activos_movidos.items(),
                                    key=lambda x: x[1].get("confianza",0),
                                    reverse=True)[:4]:
            dir_  = info["dir"]
            conf  = info.get("confianza",0)
            razon = info.get("razon","")
            emoji = "📈" if dir_=="SUBE" else "📉"
            lineas.append(f"  {emoji} {activo}: {dir_} ({conf}%) — {razon[:40]}")

    lineas += ["", "kairos-markets.streamlit.app"]
    return "\n".join(lineas)


def procesar_noticia(evento: dict, contexto_actual: dict = None) -> bool:
    """
    Función principal — llamar desde monitor.py para cada noticia.

    Args:
        evento: dict con 'titular', 'score', 'fuente', 'link'
        contexto_actual: contexto del sistema (regimen, situaciones)

    Returns:
        True si se procesó y envió alerta
    """
    titular = evento.get("titular","")
    score   = evento.get("score", 0)
    fuente  = evento.get("fuente","")
    link    = evento.get("link","")

    if ya_analizada(titular):
        return False

    log.info(f"\n  Analizando con IA: [{score}] {titular[:60]}...")

    # Cargar contexto si no se pasó
    if not contexto_actual:
        try:
            from contexto_kairos import obtener_contexto_completo
            contexto_actual = obtener_contexto_completo()
        except Exception:
            contexto_actual = {}

    # Analizar con IA
    analisis = analizar_noticia_con_ia(titular, fuente, contexto_actual)
    marcar_analizada(titular)

    if not analisis.get("mueve_mercado", False):
        log.info(f"  → No mueve mercado ({analisis.get('urgencia','?')})")
        return False

    urgencia = analisis.get("urgencia","MEDIA")
    log.info(f"  → MUEVE MERCADO | {urgencia} | {analisis.get('activo_mas_afectado','?')}")

    # Enviar alerta con análisis
    try:
        from alertas import enviar_alerta_telegram
        mensaje = formatear_alerta_noticia_ia(titular, fuente, link, analisis)
        enviar_alerta_telegram(mensaje)
        log.info(f"  ✅ Alerta enviada")
    except Exception as e:
        log.error(f"  Error alerta: {e}")

    # Si cambia el contexto → actualizar predicciones
    if analisis.get("cambia_contexto", False):
        try:
            from predicciones_adaptativas import regenerar_predicciones
            cambio = {
                "titular":           titular,
                "score":             score,
                "nuevo_contexto":    analisis.get("nuevo_contexto",""),
                "descripcion":       analisis.get("resumen_impacto",""),
                "activos_afectados": {
                    k: v["dir"] for k,v in analisis.get("impacto_por_activo",{}).items()
                    if v.get("dir") != "NEUTRO" and v.get("confianza",0) >= 65
                },
            }
            regenerar_predicciones(cambio)
            log.info(f"  ⚡ Predicciones actualizadas")
        except Exception as e:
            log.error(f"  Error adaptativo: {e}")

    return True


if __name__ == "__main__":
    print("\n📰 KAIROS — Test analizador de noticias con IA\n")

    noticias_test = [
        {
            "titular": "Trump Says Iran Deal 'Looking Very Good' Amid Ceasefire Talks",
            "score":   99,
            "fuente":  "Reuters",
            "link":    "https://reuters.com",
        },
        {
            "titular": "Fed Powell: Inflation Still Too High, No Rate Cuts This Year",
            "score":   95,
            "fuente":  "Bloomberg",
            "link":    "",
        },
        {
            "titular": "OPEC+ Announces Surprise Production Cut of 1 Million Barrels",
            "score":   92,
            "fuente":  "Reuters",
            "link":    "",
        },
    ]

    try:
        from contexto_kairos import obtener_contexto_completo
        ctx = obtener_contexto_completo()
    except Exception:
        ctx = {}

    for noticia in noticias_test:
        print(f"\nNoticia: {noticia['titular'][:60]}...")
        print(f"Score:   {noticia['score']}")

        analisis = analizar_noticia_con_ia(
            noticia["titular"], noticia["fuente"], ctx
        )

        mueve   = analisis.get("mueve_mercado", False)
        urgencia= analisis.get("urgencia","?")
        tipo    = analisis.get("tipo_evento","?")
        resumen = analisis.get("resumen_impacto","")
        cambia  = analisis.get("cambia_contexto", False)

        print(f"Mueve mercado: {'✅ SÍ' if mueve else '⚫ NO'} | {urgencia} | {tipo}")
        if mueve:
            print(f"Resumen: {resumen}")
            impacto = analisis.get("impacto_por_activo",{})
            for activo, info in sorted(impacto.items(),
                                       key=lambda x: x[1].get("confianza",0),
                                       reverse=True)[:4]:
                if info.get("dir","NEUTRO") != "NEUTRO":
                    dir_  = info["dir"]
                    conf  = info.get("confianza",0)
                    razon = info.get("razon","")
                    emoji = "📈" if dir_=="SUBE" else "📉"
                    print(f"  {emoji} {activo}: {dir_} ({conf}%) — {razon[:45]}")
            if cambia:
                print(f"  ⚡ Cambia contexto: {analisis.get('nuevo_contexto','')}")
        print()
