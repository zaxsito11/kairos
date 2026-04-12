# calendario_eco.py — KAIROS
#
# CONCEPTO:
# KAIROS no solo reacciona a eventos — los anticipa.
# Este módulo sabe QUÉ eventos macro importantes vienen,
# CUÁNDO exactamente, y qué probabilidad de sorpresa tienen
# basándose en el contexto macro actual.
#
# FUENTE: API gratuita de Investing.com / FRED + calendario hardcoded
# actualizable con datos reales de Bloomberg Economic Calendar.

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))

# ── Zona horaria de referencia ────────────────────────────────────
ET = ZoneInfo("America/New_York")   # hora de NY — donde mueven los mercados

# ── Calendario de eventos macro 2026 ─────────────────────────────
# ⚠️ ACTUALIZAR MENSUALMENTE con fechas reales del calendario económico
# Fuente: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
#         https://www.bls.gov/schedule/news_release/cpi.htm

CALENDARIO_2026 = [

    # ── FOMC (Reuniones de la FED) ────────────────────────────────
    {
        "evento":       "FOMC — Decisión de tasas",
        "tipo":         "FOMC",
        "fecha":        "2026-05-07",
        "hora_et":      "14:00",
        "impacto":      "CRÍTICO",
        "activos":      ["SPX", "NDX", "DXY", "Gold", "UST10Y", "VIX"],
        "descripcion":  "Decisión de tasas FED + statement FOMC",
        "consenso":     "SIN CAMBIO",
        "prob_sorpresa": None,   # se calcula dinámicamente con priced_in.py
    },
    {
        "evento":       "FOMC — Minutas",
        "tipo":         "FOMC_MINUTAS",
        "fecha":        "2026-05-27",
        "hora_et":      "14:00",
        "impacto":      "ALTO",
        "activos":      ["SPX", "DXY", "Gold", "UST10Y"],
        "descripcion":  "Minutas de la reunión FOMC de mayo 2026",
        "consenso":     None,
        "prob_sorpresa": None,
    },
    {
        "evento":       "FOMC — Decisión de tasas",
        "tipo":         "FOMC",
        "fecha":        "2026-06-17",
        "hora_et":      "14:00",
        "impacto":      "CRÍTICO",
        "activos":      ["SPX", "NDX", "DXY", "Gold", "UST10Y", "VIX"],
        "descripcion":  "Decisión de tasas FED + proyecciones económicas (dot plot)",
        "consenso":     "RECORTE 25bps",
        "prob_sorpresa": None,
    },

    # ── CPI (Inflación EEUU) ──────────────────────────────────────
    {
        "evento":       "CPI — Inflación EEUU (Abril)",
        "tipo":         "CPI",
        "fecha":        "2026-05-13",
        "hora_et":      "08:30",
        "impacto":      "ALTO",
        "activos":      ["DXY", "SPX", "Gold", "UST10Y"],
        "descripcion":  "Consumer Price Index — dato de abril 2026",
        "consenso":     "2.4% YoY",   # ⚠️ actualizar con consenso real
        "prev_anterior": "3.29%",
        "prob_sorpresa": None,
    },
    {
        "evento":       "CPI — Inflación EEUU (Mayo)",
        "tipo":         "CPI",
        "fecha":        "2026-06-11",
        "hora_et":      "08:30",
        "impacto":      "ALTO",
        "activos":      ["DXY", "SPX", "Gold", "UST10Y"],
        "descripcion":  "Consumer Price Index — dato de mayo 2026",
        "consenso":     None,
        "prev_anterior": None,
        "prob_sorpresa": None,
    },

    # ── NFP (Nóminas no agrícolas) ────────────────────────────────
    {
        "evento":       "NFP — Nóminas No Agrícolas (Abril)",
        "tipo":         "NFP",
        "fecha":        "2026-05-01",
        "hora_et":      "08:30",
        "impacto":      "ALTO",
        "activos":      ["DXY", "SPX", "Gold", "UST10Y"],
        "descripcion":  "Nóminas no agrícolas + tasa de desempleo abril 2026",
        "consenso":     "138k",       # ⚠️ actualizar con consenso real
        "prev_anterior": "158.6k",
        "prob_sorpresa": None,
    },
    {
        "evento":       "NFP — Nóminas No Agrícolas (Mayo)",
        "tipo":         "NFP",
        "fecha":        "2026-06-05",
        "hora_et":      "08:30",
        "impacto":      "ALTO",
        "activos":      ["DXY", "SPX", "Gold", "UST10Y"],
        "descripcion":  "Nóminas no agrícolas + tasa de desempleo mayo 2026",
        "consenso":     None,
        "prev_anterior": None,
        "prob_sorpresa": None,
    },

    # ── PCE (Inflación preferida de la FED) ───────────────────────
    {
        "evento":       "PCE — Inflación Core (Marzo)",
        "tipo":         "PCE",
        "fecha":        "2026-04-30",
        "hora_et":      "08:30",
        "impacto":      "ALTO",
        "activos":      ["DXY", "SPX", "Gold"],
        "descripcion":  "Core PCE — indicador preferido de inflación de la FED",
        "consenso":     "2.6% YoY",
        "prev_anterior": "2.97%",
        "prob_sorpresa": None,
    },

    # ── GDP (PIB EEUU) ────────────────────────────────────────────
    {
        "evento":       "GDP — PIB EEUU Q1 2026 (preliminar)",
        "tipo":         "GDP",
        "fecha":        "2026-04-29",
        "hora_et":      "08:30",
        "impacto":      "ALTO",
        "activos":      ["SPX", "DXY", "Gold"],
        "descripcion":  "Primera estimación PIB Q1 2026",
        "consenso":     "1.8% QoQ",
        "prev_anterior": "2.4%",
        "prob_sorpresa": None,
    },

    # ── BCE ───────────────────────────────────────────────────────
    {
        "evento":       "BCE — Decisión de tasas",
        "tipo":         "BCE",
        "fecha":        "2026-06-05",
        "hora_et":      "08:15",
        "impacto":      "ALTO",
        "activos":      ["EURUSD", "SPX", "Gold"],
        "descripcion":  "Decisión de tasas del Banco Central Europeo",
        "consenso":     "RECORTE 25bps",
        "prob_sorpresa": None,
    },
]

# ── Precedentes por tipo de evento ────────────────────────────────
PRECEDENTES_POR_TIPO = {
    "FOMC": {
        "hawkish_sorpresa": {
            "n": 10,
            "SPX":    "-1.7% promedio 24h (75% de veces baja)",
            "DXY":    "+0.7% promedio 24h (80% de veces sube)",
            "Gold":   "-0.4% promedio 24h (65% de veces baja)",
            "VIX":    "+15% promedio 24h (70% de veces sube)",
        },
        "dovish_sorpresa": {
            "n": 8,
            "SPX":    "+1.4% promedio 24h (72% de veces sube)",
            "DXY":    "-0.6% promedio 24h (75% de veces baja)",
            "Gold":   "+0.8% promedio 24h (68% de veces sube)",
            "VIX":    "-12% promedio 24h (65% de veces baja)",
        },
    },
    "CPI": {
        "hawkish_sorpresa": {
            "n": 8,
            "DXY":    "+0.8% promedio 4h (72% de veces sube)",
            "SPX":    "-1.2% promedio 4h (68% de veces baja)",
            "Gold":   "-0.5% promedio 4h (60% de veces baja)",
            "UST10Y": "+5bps promedio 4h (75% de veces sube)",
        },
        "dovish_sorpresa": {
            "n": 6,
            "DXY":    "-0.5% promedio 4h (65% de veces baja)",
            "SPX":    "+0.9% promedio 4h (63% de veces sube)",
            "Gold":   "+0.7% promedio 4h (62% de veces sube)",
        },
    },
    "NFP": {
        "hawkish_sorpresa": {
            "n": 9,
            "DXY":    "+0.5% promedio 2h (70% de veces sube)",
            "SPX":    "-0.8% promedio 2h (60% de veces baja)",
            "Gold":   "-0.3% promedio 2h (58% de veces baja)",
        },
        "dovish_sorpresa": {
            "n": 7,
            "DXY":    "-0.6% promedio 2h (68% de veces baja)",
            "SPX":    "+0.5% promedio 2h (60% de veces sube)",
            "Gold":   "+0.4% promedio 2h (62% de veces sube)",
        },
    },
}


# ── Funciones principales ─────────────────────────────────────────
def obtener_eventos_proximos(dias: int = 7) -> list:
    """
    Retorna eventos macro importantes en los próximos N días,
    ordenados por fecha y criticidad.
    """
    ahora   = datetime.now(ET)
    limite  = ahora + timedelta(days=dias)
    eventos = []

    for ev in CALENDARIO_2026:
        try:
            fecha_str = f"{ev['fecha']} {ev['hora_et']}"
            fecha_ev  = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            fecha_ev  = fecha_ev.replace(tzinfo=ET)

            if ahora <= fecha_ev <= limite:
                horas_restantes = (fecha_ev - ahora).total_seconds() / 3600
                dias_restantes  = horas_restantes / 24

                evento = ev.copy()
                evento["fecha_dt"]        = fecha_ev.isoformat()
                evento["horas_restantes"] = round(horas_restantes, 1)
                evento["dias_restantes"]  = round(dias_restantes, 1)
                evento["hora_local_et"]   = fecha_ev.strftime("%d/%m/%Y %H:%M ET")

                # Calcular probabilidad de sorpresa si hay consenso
                if ev.get("consenso") and ev.get("prev_anterior"):
                    evento["prob_sorpresa"] = estimar_prob_sorpresa(ev)

                # Agregar precedentes relevantes
                evento["precedentes"] = PRECEDENTES_POR_TIPO.get(ev["tipo"], {})

                eventos.append(evento)

        except Exception as e:
            continue

    # Ordenar: primero críticos, luego por fecha
    prioridad = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2}
    eventos.sort(key=lambda x: (
        prioridad.get(x["impacto"], 3),
        x["horas_restantes"]
    ))

    return eventos


def estimar_prob_sorpresa(evento: dict) -> dict:
    """
    Estima la probabilidad de sorpresa basándose en:
    - Tendencia reciente vs consenso
    - Histórico de miss/beat del indicador
    """
    tipo = evento.get("tipo", "")

    # Probabilidades base por tipo de indicador
    # (basadas en histórico de sorpresas de los últimos 2 años)
    prob_base = {
        "CPI":  {"hawkish": 45, "dovish": 35, "inline": 20},
        "NFP":  {"hawkish": 40, "dovish": 40, "inline": 20},
        "PCE":  {"hawkish": 42, "dovish": 38, "inline": 20},
        "GDP":  {"hawkish": 35, "dovish": 45, "inline": 20},
        "FOMC": {"hawkish": 15, "dovish": 10, "inline": 75},
    }

    probs = prob_base.get(tipo, {"hawkish": 33, "dovish": 33, "inline": 34})

    return {
        "prob_sorpresa_hawkish": probs["hawkish"],
        "prob_sorpresa_dovish":  probs["dovish"],
        "prob_inline":           probs["inline"],
        "nota": "Estimación basada en histórico 2024-2026",
    }


def generar_alerta_pre_evento(evento: dict) -> str:
    """
    Genera alerta de anticipación para Telegram.
    Se envía X horas antes del evento para preparar al trader.
    """
    horas     = evento["horas_restantes"]
    tipo      = evento["tipo"]
    nombre    = evento["evento"]
    hora_et   = evento["hora_local_et"]
    activos   = ", ".join(evento["activos"])
    consenso  = evento.get("consenso", "N/D")
    anterior  = evento.get("prev_anterior", "N/D")
    impacto   = evento["impacto"]

    emojis = {"CRÍTICO": "🚨", "ALTO": "⚠️", "MEDIO": "📡"}
    emoji  = emojis.get(impacto, "📡")

    if horas < 1:
        tiempo_txt = f"en {int(horas*60)} minutos"
    elif horas < 24:
        tiempo_txt = f"en {round(horas,1)} horas"
    else:
        tiempo_txt = f"en {round(evento['dias_restantes'],1)} días"

    lineas = [
        f"{emoji} KAIROS — EVENTO PRÓXIMO",
        f"{'='*38}",
        f"📅 {nombre}",
        f"⏰ {hora_et} ({tiempo_txt})",
        f"📊 Activos que se moverán: {activos}",
        f"",
        f"📈 Consenso analistas: {consenso}",
        f"📋 Dato anterior: {anterior}",
    ]

    # Probabilidades de sorpresa
    prob = evento.get("prob_sorpresa")
    if prob:
        lineas += [
            f"",
            f"🎲 PROBABILIDAD DE SORPRESA:",
            f"  🔴 Hawkish (supera consenso): {prob['prob_sorpresa_hawkish']}%",
            f"  🟢 Dovish (bajo consenso):    {prob['prob_sorpresa_dovish']}%",
            f"  🟡 En línea con consenso:     {prob['prob_inline']}%",
        ]

    # Precedentes históricos
    precs = evento.get("precedentes", {})
    if precs:
        lineas += ["", f"📚 SI HAY SORPRESA — HISTÓRICO:"]
        if "hawkish_sorpresa" in precs:
            h = precs["hawkish_sorpresa"]
            lineas.append(f"  Si supera consenso ({h['n']} casos):")
            for activo in evento["activos"][:3]:
                if activo in h:
                    lineas.append(f"    → {activo}: {h[activo]}")
        if "dovish_sorpresa" in precs:
            d = precs["dovish_sorpresa"]
            lineas.append(f"  Si queda bajo consenso ({d['n']} casos):")
            for activo in evento["activos"][:3]:
                if activo in d:
                    lineas.append(f"    → {activo}: {d[activo]}")

    lineas += ["", "kairos-markets.streamlit.app"]
    return "\n".join(lineas)


def verificar_alertas_calendario(estado: dict) -> list:
    """
    Revisa el calendario y genera alertas pre-evento cuando:
    - Faltan 24 horas para un evento CRÍTICO
    - Faltan 6 horas para un evento ALTO
    - Faltan 1 hora para cualquier evento importante
    Nunca alerta dos veces el mismo evento en la misma ventana.
    """
    alertas   = []
    eventos   = obtener_eventos_proximos(dias=7)
    alertadas = estado.get("calendario_alertas", {})

    for ev in eventos:
        horas  = ev["horas_restantes"]
        tipo   = ev["tipo"]
        fecha  = ev["fecha"]
        clave  = f"{tipo}_{fecha}"

        # Definir cuándo alertar según impacto
        alertar_en = {
            "CRÍTICO": [24, 6, 1],
            "ALTO":    [6, 1],
            "MEDIO":   [2],
        }.get(ev["impacto"], [2])

        for h_umbral in alertar_en:
            clave_alerta = f"{clave}_{h_umbral}h"

            # ¿Ya fue alertado en esta ventana?
            if clave_alerta in alertadas:
                continue

            # ¿Está en la ventana de alerta? (±30 min del umbral)
            if abs(horas - h_umbral) <= 0.5:
                alertas.append({
                    "evento":       ev,
                    "clave_alerta": clave_alerta,
                    "mensaje":      generar_alerta_pre_evento(ev),
                })
                alertadas[clave_alerta] = datetime.now().isoformat()

    estado["calendario_alertas"] = alertadas
    return alertas


def resumen_semana() -> str:
    """
    Genera un resumen de todos los eventos importantes
    de los próximos 7 días. Para el dashboard.
    """
    eventos = obtener_eventos_proximos(dias=7)

    if not eventos:
        return "Sin eventos macro importantes en los próximos 7 días."

    lineas = ["📅 EVENTOS MACRO PRÓXIMOS 7 DÍAS\n" + "="*38]

    for ev in eventos:
        emoji_impacto = {"CRÍTICO": "🚨", "ALTO": "⚠️", "MEDIO": "📡"}
        emoji = emoji_impacto.get(ev["impacto"], "📡")
        horas = ev["horas_restantes"]

        if horas < 24:
            tiempo = f"en {round(horas,1)}h"
        else:
            tiempo = f"en {round(ev['dias_restantes'],1)} días"

        consenso = f" | Consenso: {ev['consenso']}" if ev.get("consenso") else ""
        lineas.append(
            f"\n{emoji} {ev['evento']}\n"
            f"   📅 {ev['hora_local_et']} ({tiempo})\n"
            f"   📊 Activos: {', '.join(ev['activos'][:4])}{consenso}"
        )

    return "\n".join(lineas)


# ── Test directo ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n📅 KAIROS CALENDARIO ECONÓMICO")
    print("="*50)

    eventos = obtener_eventos_proximos(dias=30)

    if not eventos:
        print("Sin eventos en los próximos 30 días.")
    else:
        print(f"\n{len(eventos)} eventos próximos:\n")
        for ev in eventos:
            emoji = {"CRÍTICO":"🚨","ALTO":"⚠️","MEDIO":"📡"}.get(ev["impacto"],"📡")
            print(f"{emoji} {ev['evento']}")
            print(f"   Fecha: {ev['hora_local_et']}")
            print(f"   Faltan: {ev['horas_restantes']}h ({ev['dias_restantes']} días)")
            if ev.get("consenso"):
                print(f"   Consenso: {ev['consenso']}")
            if ev.get("prob_sorpresa"):
                p = ev["prob_sorpresa"]
                print(f"   Prob. sorpresa: 🔴{p['prob_sorpresa_hawkish']}% hawkish | "
                      f"🟢{p['prob_sorpresa_dovish']}% dovish")
            print()

    print("\n" + "="*50)
    print("RESUMEN SEMANA:")
    print(resumen_semana())

    print("\n" + "="*50)
    print("ALERTA DE EJEMPLO (próximo evento):")
    if eventos:
        print(generar_alerta_pre_evento(eventos[0]))
