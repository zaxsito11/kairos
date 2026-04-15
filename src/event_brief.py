# event_brief.py — KAIROS
# Event Brief: alerta especial 30 min antes de cada evento crítico.
#
# CONCEPTO:
# El Morning Brief da el contexto del día.
# El Event Brief da el análisis específico del evento que viene.
#
# Se dispara automáticamente cuando un evento CRÍTICO o ALTO
# está a menos de 30 minutos. Es corto, preciso y accionable.
#
# ESTRUCTURA:
#   🎯 Qué evento es y cuándo exactamente
#   📊 Consenso del mercado vs dato anterior
#   🔮 Qué pasaría si supera / decepciona el consenso
#   📈 Activos más afectados con dirección y magnitud
#   ⚡ Qué vigilar en los primeros 5 minutos post-dato

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

client    = Groq(api_key=os.getenv("GROQ_API_KEY"))
LOG_FILE  = "outputs/event_brief.log"
SENT_FILE = "data/event_briefs_enviados.json"

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
log = logging.getLogger("KAIROS.event_brief")


# ── Ventanas de alerta ────────────────────────────────────────────
# Cuántos minutos antes de cada tipo de evento enviamos el brief
VENTANAS_MINUTOS = {
    "CRÍTICO": 30,   # FOMC, CPI, NFP — 30 min antes
    "ALTO":    20,   # PCE, GDP, discursos FED — 20 min antes
}

# ── Contexto específico por tipo de evento ────────────────────────
CONTEXTO_EVENTOS = {
    "FOMC": {
        "descripcion": "Decisión de tasas de la Reserva Federal",
        "que_vigilar": [
            "Cambio en el statement (lenguaje nuevo vs anterior)",
            "Dot plot actualizado — proyección de tasas 2026-2027",
            "Tono de Powell en la conferencia de prensa",
            "Votos disidentes en el comité",
        ],
        "activos_primarios":  ["DXY", "UST10Y", "SPX", "Gold"],
        "activos_secundarios":["NDX", "VIX", "Silver", "BTC"],
        "tiempo_reaccion":    "0-5 min en statement, 30 min en conferencia",
    },
    "CPI": {
        "descripcion": "Índice de Precios al Consumidor EEUU",
        "que_vigilar": [
            "Core CPI vs consenso (el más importante)",
            "Componente de vivienda (shelter) — 30% del índice",
            "Servicios ex-energía — preferido de la FED",
            "Revisión del mes anterior",
        ],
        "activos_primarios":  ["DXY", "UST10Y", "Gold"],
        "activos_secundarios":["SPX", "NDX", "Silver"],
        "tiempo_reaccion":    "0-2 min post publicación",
    },
    "NFP": {
        "descripcion": "Nóminas No Agrícolas — Reporte de Empleo EEUU",
        "que_vigilar": [
            "NFP vs consenso — número principal",
            "Tasa de desempleo (U3)",
            "Salarios por hora — presión inflacionaria",
            "Revisión de meses anteriores",
        ],
        "activos_primarios":  ["DXY", "UST10Y", "Gold"],
        "activos_secundarios":["SPX", "VIX", "BTC"],
        "tiempo_reaccion":    "0-3 min post publicación",
    },
    "PCE": {
        "descripcion": "Gasto en Consumo Personal — indicador preferido de la FED",
        "que_vigilar": [
            "Core PCE YoY vs consenso y objetivo 2%",
            "PCE mensual (MoM) para tendencia inmediata",
            "Diferencia con CPI — divergencia es señal",
        ],
        "activos_primarios":  ["DXY", "UST10Y", "SPX"],
        "activos_secundarios":["Gold", "NDX"],
        "tiempo_reaccion":    "0-5 min post publicación",
    },
    "GDP": {
        "descripcion": "Producto Interno Bruto EEUU (preliminar/final)",
        "que_vigilar": [
            "Crecimiento QoQ annualizado vs consenso",
            "Deflactor del GDP — inflación implícita",
            "Consumo personal — motor principal del GDP",
            "Inversión empresarial — señal forward",
        ],
        "activos_primarios":  ["SPX", "DXY", "UST10Y"],
        "activos_secundarios":["NDX", "Gold", "BTC"],
        "tiempo_reaccion":    "0-10 min post publicación",
    },
    "BCE": {
        "descripcion": "Decisión de tasas del Banco Central Europeo",
        "que_vigilar": [
            "Decisión de tasas vs expectativa",
            "Tono del statement (hawkish/dovish/neutro)",
            "Proyecciones de inflación y crecimiento",
            "Forward guidance — próximas reuniones",
        ],
        "activos_primarios":  ["EURUSD", "Bund", "EuroStoxx"],
        "activos_secundarios":["DXY", "Gold", "SPX"],
        "tiempo_reaccion":    "0-5 min en decisión, 30 min en conferencia Lagarde",
    },
    "DEFAULT": {
        "descripcion": "Evento macro de alto impacto",
        "que_vigilar": [
            "Dato real vs consenso de analistas",
            "Revisión de dato anterior",
            "Contexto macro actual",
        ],
        "activos_primarios":  ["SPX", "DXY", "Gold"],
        "activos_secundarios":["VIX", "UST10Y"],
        "tiempo_reaccion":    "0-5 min post publicación",
    },
}


# ── Estado: evitar duplicados ─────────────────────────────────────
def cargar_enviados() -> dict:
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def guardar_enviado(clave: str):
    enviados = cargar_enviados()
    enviados[clave] = datetime.now().isoformat()
    # Limpiar entradas de más de 7 días
    hace_7d = datetime.now() - timedelta(days=7)
    enviados = {k: v for k, v in enviados.items()
                if datetime.fromisoformat(v) > hace_7d}
    with open(SENT_FILE, "w") as f:
        json.dump(enviados, f, indent=2)


def ya_enviado(clave: str) -> bool:
    enviados = cargar_enviados()
    if clave not in enviados:
        return False
    ultima = datetime.fromisoformat(enviados[clave])
    # No reenviar si ya se envió en las últimas 2 horas
    return datetime.now() - ultima < timedelta(hours=2)


# ── Generador del brief con IA ────────────────────────────────────
def generar_event_brief_ia(evento: dict, contexto_extra: dict) -> str:
    """
    Genera el Event Brief para un evento específico usando IA.
    """
    nombre_evento = evento["evento"]
    hora_et       = evento["hora_local_et"]
    impacto       = evento["impacto"]
    consenso      = evento.get("consenso", "No disponible")
    activos       = evento.get("activos", [])
    minutos_rest  = int(evento["horas_restantes"] * 60)

    # Detectar tipo de evento
    tipo = "DEFAULT"
    for clave in CONTEXTO_EVENTOS:
        if clave in nombre_evento.upper():
            tipo = clave
            break

    ctx = CONTEXTO_EVENTOS[tipo]

    # Obtener priced-in si es FOMC
    priced_in_str = ""
    if tipo == "FOMC":
        try:
            from priced_in import obtener_probabilidades_cme
            exp = obtener_probabilidades_cme()
            if exp:
                probs = exp[0]["probabilidades"]
                priced_in_str = "\n".join([f"  {k}: {v}%" for k, v in probs.items()])
        except Exception:
            pass

    # Sorpresa macro si hay dato anterior
    sorpresa_str = ""
    try:
        from sorpresa_macro import analizar_sorpresas_recientes
        sorpresas = analizar_sorpresas_recientes()
        for s in sorpresas:
            if any(x in nombre_evento.upper() for x in
                   [s["nombre"][:3].upper(), "CPI", "NFP", "PCE"]):
                sorpresa_str = (
                    f"Dato anterior: {s['real']} {s['unidad']} "
                    f"(vs consenso {s['consenso']}) — {s['nivel']}"
                )
                break
    except Exception:
        pass

    # Régimen macro actual
    regimen_str = contexto_extra.get("regimen", "NEUTRO")
    tasa_fed    = contexto_extra.get("tasa_fed", "3.64%")

    separador = chr(10)
    que_vigilar = separador.join(["  - " + q for q in ctx["que_vigilar"]])
    activos_pri = ", ".join(ctx["activos_primarios"])
    activos_sec = ", ".join(ctx["activos_secundarios"])

    prompt = f"""Eres el analista de eventos en tiempo real de KAIROS Markets.
Escribes Event Briefs: alertas cortas y precisas que se envían 30 minutos
antes de eventos de alto impacto. Tu análisis es directo y accionable.

EVENTO INMINENTE:
  Nombre:        {nombre_evento}
  Hora ET:       {hora_et}
  Tiempo:        En {minutos_rest} minutos
  Impacto:       {impacto}
  Consenso:      {consenso}
  Activos afect: {", ".join(activos[:6])}

CONTEXTO DEL EVENTO:
  Tipo:          {ctx["descripcion"]}
  Régimen macro: {regimen_str}
  Tasa FED:      {tasa_fed}
{f"  Dato anterior: {sorpresa_str}" if sorpresa_str else ""}
{"  Priced-in FOMC:" + chr(10) + priced_in_str if priced_in_str else ""}

QUÉ VIGILAR:
{que_vigilar}

ACTIVOS PRIMARIOS: {activos_pri}
ACTIVOS SECUNDARIOS: {activos_sec}
Tiempo de reacción: {ctx["tiempo_reaccion"]}

Escribe el Event Brief con EXACTAMENTE esta estructura.
Máximo 350 palabras. Sé ultra-directo.

⚡ KAIROS EVENT BRIEF — {nombre_evento.upper()}
══════════════════════════════════════

🕐 En {minutos_rest} minutos | {hora_et} ET

📊 CONSENSO: {consenso}
[Una línea sobre qué espera el mercado y por qué importa ahora]

🎯 ESCENARIO HAWKISH (dato supera consenso)
[Qué pasaría activo por activo — máximo 4 activos con dirección y magnitud]

🎯 ESCENARIO DOVISH (dato decepciona consenso)
[Qué pasaría activo por activo — máximo 4 activos con dirección y magnitud]

📈 ACTIVOS MÁS SENSIBLES HOY
[Los 3 activos que más reaccionarán y por qué — con niveles a vigilar]

⚡ PRIMEROS 5 MINUTOS POST-DATO
[Qué observar exactamente en los primeros minutos para confirmar la dirección]

⚠️ RIESGO: [BAJO/MEDIO/ALTO/CRÍTICO] — [una línea de razón]

---
KAIROS Markets | kairos-markets.streamlit.app
⚠️ Análisis informativo — no es recomendación de inversión

Responde SOLO con el Event Brief. Sin comentarios extra."""

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres el analista de eventos en tiempo real de KAIROS. "
                    "Escribes event briefs ultra-cortos y accionables. "
                    "Nunca inventas datos. Siempre indicas la incertidumbre. "
                    "Tu estilo: directo, preciso, sin palabras de relleno."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1000
    )

    return respuesta.choices[0].message.content


# ── Función principal ─────────────────────────────────────────────
def verificar_y_enviar_event_briefs() -> int:
    """
    Verifica el calendario y envía Event Briefs
    para eventos que están dentro de la ventana de alerta.

    Returns:
        Número de briefs enviados.
    """
    try:
        from calendario_eco import obtener_eventos_proximos
        from alertas        import enviar_alerta_telegram
        from macro          import obtener_datos_macro, evaluar_regimen_macro
    except Exception as e:
        log.error(f"Error importando módulos: {e}")
        return 0

    eventos = obtener_eventos_proximos(dias=2)
    enviados = 0

    # Contexto macro para la IA
    contexto_extra = {}
    try:
        datos_macro = obtener_datos_macro()
        regimen     = evaluar_regimen_macro(datos_macro)
        contexto_extra = {
            "regimen":  regimen.get("regimen", "NEUTRO"),
            "tasa_fed": str(datos_macro.get("TASA_FED", {}).get("valor", "3.64")) + "%",
        }
    except Exception:
        pass

    for evento in eventos:
        impacto       = evento.get("impacto", "MEDIO")
        ventana_min   = VENTANAS_MINUTOS.get(impacto)
        if not ventana_min:
            continue

        horas_rest    = evento.get("horas_restantes", 999)
        minutos_rest  = horas_rest * 60

        # ¿Estamos dentro de la ventana?
        if not (0 < minutos_rest <= ventana_min):
            continue

        # Clave única para este evento — fecha + nombre
        clave = f"{evento['evento']}_{evento.get('hora_local_et','')}"

        if ya_enviado(clave):
            log.info(f"  Event Brief ya enviado: {clave}")
            continue

        log.info(f"\n⚡ GENERANDO EVENT BRIEF: {evento['evento']}")
        log.info(f"   Tiempo restante: {int(minutos_rest)} min")

        try:
            brief = generar_event_brief_ia(evento, contexto_extra)

            # Enviar al canal
            enviar_alerta_telegram(brief)
            guardar_enviado(clave)
            enviados += 1

            # Guardar en disco
            fecha_str = datetime.now().strftime("%Y-%m-%d_%H%M")
            nombre_ev = evento["evento"].replace(" ", "_")[:30]
            with open(f"outputs/event_brief_{fecha_str}_{nombre_ev}.txt",
                      "w", encoding="utf-8") as f:
                f.write(brief)

            log.info(f"  ✅ Event Brief enviado: {evento['evento']}")

        except Exception as e:
            log.error(f"  Error generando Event Brief: {e}")

    return enviados


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KAIROS Event Brief")
    parser.add_argument("--forzar", type=str, default="",
                        help="Nombre del evento para forzar el brief (ej: CPI)")
    args = parser.parse_args()

    if args.forzar:
        print(f"\n⚡ Forzando Event Brief para: {args.forzar}")

        # Crear evento de prueba
        evento_test = {
            "evento":          args.forzar,
            "hora_local_et":   "08:30 AM ET",
            "impacto":         "CRÍTICO",
            "consenso":        "Ver calendario",
            "activos":         ["SPX", "DXY", "Gold", "UST10Y"],
            "horas_restantes": 0.4,
            "dias_restantes":  0,
        }

        try:
            from macro import obtener_datos_macro, evaluar_regimen_macro
            datos_macro = obtener_datos_macro()
            regimen     = evaluar_regimen_macro(datos_macro)
            contexto_extra = {
                "regimen":  regimen.get("regimen", "NEUTRO"),
                "tasa_fed": str(datos_macro.get("TASA_FED",{}).get("valor","3.64")) + "%",
            }
        except Exception:
            contexto_extra = {"regimen": "NEUTRO", "tasa_fed": "3.64%"}

        brief = generar_event_brief_ia(evento_test, contexto_extra)
        print("\n" + "="*60)
        print(brief)
        print("="*60)

        enviar = input("\n¿Enviar al canal Telegram? (s/n): ").strip().lower()
        if enviar == "s":
            from alertas import enviar_alerta_telegram
            enviar_alerta_telegram(brief)
            print("✅ Enviado al canal")

    else:
        print("\n⚡ KAIROS EVENT BRIEF — Verificando calendario...")
        n = verificar_y_enviar_event_briefs()
        if n > 0:
            print(f"✅ {n} Event Briefs enviados")
        else:
            print("✓ Sin eventos en ventana de alerta ahora")
            print("\nPróximos eventos críticos:")
            try:
                from calendario_eco import obtener_eventos_proximos
                eventos = obtener_eventos_proximos(dias=7)
                for ev in eventos[:5]:
                    minutos = int(ev["horas_restantes"] * 60)
                    ventana = VENTANAS_MINUTOS.get(ev["impacto"], 0)
                    print(f"  {'🚨' if ev['impacto']=='CRÍTICO' else '⚠️'} "
                          f"{ev['evento']} — en {ev['dias_restantes']} días "
                          f"(brief en {int(ev['dias_restantes']*24*60) - ventana} min)")
            except Exception as e:
                print(f"  Error: {e}")
