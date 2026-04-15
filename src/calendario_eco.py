# calendario_eco.py — KAIROS
# Calendario de eventos macro con capacidad de mover mercados.
# Genera alertas pre-evento y alimenta el Morning/Event Brief.
#
# ⚠️ ACTUALIZAR consensos antes de cada publicación importante.

import os
import json
from datetime import datetime, timedelta, timezone

# ══════════════════════════════════════════════════════════════════
# EVENTOS MACRO 2026 — ordenados por fecha
# ⚠️ Actualizar consenso 24h antes de cada publicación
# ══════════════════════════════════════════════════════════════════

EVENTOS_MACRO = [

    # ── ABRIL 2026 ────────────────────────────────────────────────
    {
        "evento":       "GDP EEUU Q1 2026 (preliminar)",
        "fecha":        "2026-04-29",
        "hora_et":      "08:30",
        "impacto":      "CRÍTICO",
        "consenso":     "+1.8% QoQ anualizado",
        "anterior":     "+2.3% QoQ",
        "activos":      ["SPX", "NDX", "DXY", "Gold", "UST10Y"],
        "descripcion":  "Primera estimación del PIB Q1. Alta sensibilidad — recesión o resiliencia.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 35,
            "prob_sorpresa_dovish":  40,
        },
    },
    {
        "evento":       "PCE Inflación (Marzo)",
        "fecha":        "2026-04-30",
        "hora_et":      "08:30",
        "impacto":      "CRÍTICO",
        "consenso":     "2.6% YoY | Core 2.7%",
        "anterior":     "2.5% YoY | Core 2.6%",
        "activos":      ["DXY", "UST10Y", "Gold", "SPX"],
        "descripcion":  "Indicador de inflación preferido de la FED. Crítico para FOMC Mayo.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 45,
            "prob_sorpresa_dovish":  30,
        },
    },

    # ── MAYO 2026 ─────────────────────────────────────────────────
    {
        "evento":       "NFP Nóminas No Agrícolas (Abril)",
        "fecha":        "2026-05-02",
        "hora_et":      "08:30",
        "impacto":      "CRÍTICO",
        "consenso":     "138k empleos | Desempleo 4.3%",
        "anterior":     "158.6k | 4.3%",
        "activos":      ["DXY", "SPX", "Gold", "UST10Y", "VIX"],
        "descripcion":  "Reporte de empleo de abril. Desaceleración esperada post-conflicto Irán.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 40,
            "prob_sorpresa_dovish":  45,
        },
    },
    {
        "evento":       "FOMC — Decisión de tasas (Mayo)",
        "fecha":        "2026-05-07",
        "hora_et":      "14:00",
        "impacto":      "CRÍTICO",
        "consenso":     "SIN CAMBIO 78.4% | Recorte 19.8%",
        "anterior":     "Pausa — tasa 3.64%",
        "activos":      ["SPX", "NDX", "DXY", "Gold", "UST10Y", "VIX", "BTC"],
        "descripcion":  "Reunión FOMC Mayo. FED atrapada entre inflación energética y desaceleración.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 25,
            "prob_sorpresa_dovish":  15,
        },
    },
    {
        "evento":       "CPI Inflación EEUU (Abril)",
        "fecha":        "2026-05-13",
        "hora_et":      "08:30",
        "impacto":      "CRÍTICO",
        "consenso":     "3.1% YoY | Core 2.6%",
        "anterior":     "3.29% YoY | Core 3.17%",
        "activos":      ["DXY", "UST10Y", "Gold", "SPX", "Silver"],
        "descripcion":  "CPI Abril. Se espera moderación vs marzo. Clave para outlook FED junio.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 40,
            "prob_sorpresa_dovish":  35,
        },
    },
    {
        "evento":       "Minutas FOMC (Mayo)",
        "fecha":        "2026-05-27",
        "hora_et":      "14:00",
        "impacto":      "ALTO",
        "consenso":     "Tono hawkish leve esperado",
        "anterior":     "Minutas marzo — hawkish por energía",
        "activos":      ["DXY", "UST10Y", "SPX", "Gold"],
        "descripcion":  "Minutas de la reunión de mayo. Revelan debate interno sobre próximos pasos.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 35,
            "prob_sorpresa_dovish":  25,
        },
    },

    # ── JUNIO 2026 ────────────────────────────────────────────────
    {
        "evento":       "NFP Nóminas No Agrícolas (Mayo)",
        "fecha":        "2026-06-06",
        "hora_et":      "08:30",
        "impacto":      "CRÍTICO",
        "consenso":     "Por confirmar — actualizar mayo",
        "anterior":     "138k (estimado abril)",
        "activos":      ["DXY", "SPX", "Gold", "UST10Y"],
        "descripcion":  "Reporte de empleo de mayo. Precede al FOMC de junio.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 40,
            "prob_sorpresa_dovish":  40,
        },
    },
    {
        "evento":       "BCE — Decisión de tasas (Junio)",
        "fecha":        "2026-06-05",
        "hora_et":      "08:15",
        "impacto":      "CRÍTICO",
        "consenso":     "Subida 25bps 60% | Pausa 40%",
        "anterior":     "Pausa — tasa depósito 1.93%",
        "activos":      ["EURUSD", "Gold", "SPX", "Bund", "Silver"],
        "descripcion":  "Reunión BCE junio. Presión hawkish por inflación energética guerra Irán.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 40,
            "prob_sorpresa_dovish":  20,
        },
    },
    {
        "evento":       "CPI Inflación EEUU (Mayo)",
        "fecha":        "2026-06-11",
        "hora_et":      "08:30",
        "impacto":      "CRÍTICO",
        "consenso":     "Por confirmar — actualizar junio",
        "anterior":     "3.1% (estimado abril)",
        "activos":      ["DXY", "UST10Y", "Gold", "SPX"],
        "descripcion":  "CPI Mayo. Previo al FOMC de junio — máxima relevancia.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 40,
            "prob_sorpresa_dovish":  35,
        },
    },
    {
        "evento":       "FOMC — Decisión de tasas (Junio)",
        "fecha":        "2026-06-17",
        "hora_et":      "14:00",
        "impacto":      "CRÍTICO",
        "consenso":     "Recorte 25bps 48% | Pausa 45%",
        "anterior":     "Pausa mayo — tasa 3.64%",
        "activos":      ["SPX", "NDX", "DXY", "Gold", "UST10Y", "VIX", "BTC"],
        "descripcion":  "FOMC Junio. Alta incertidumbre — depende de datos de mayo.",
        "prob_sorpresa": {
            "prob_sorpresa_hawkish": 30,
            "prob_sorpresa_dovish":  30,
        },
    },
]

# ── Estado de alertas enviadas ────────────────────────────────────
def _cargar_alertas_enviadas(estado: dict) -> dict:
    return estado.get("calendario_alertas", {})


def _guardar_alerta_enviada(estado: dict, clave: str):
    if "calendario_alertas" not in estado:
        estado["calendario_alertas"] = {}
    estado["calendario_alertas"][clave] = datetime.now().isoformat()


# ── Calcular tiempo restante ──────────────────────────────────────
def _calcular_tiempos(evento: dict) -> dict:
    """Calcula horas y días restantes hasta el evento."""
    ahora = datetime.now()
    fecha_str = evento["fecha"] + " " + evento["hora_et"]
    try:
        fecha_ev = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
    except Exception:
        fecha_ev = datetime.strptime(evento["fecha"], "%Y-%m-%d")

    diff          = fecha_ev - ahora
    horas_rest    = diff.total_seconds() / 3600
    dias_rest     = diff.days

    # Formato amigable de hora ET
    try:
        hora_dt   = datetime.strptime(evento["hora_et"], "%H:%M")
        hora_fmt  = hora_dt.strftime("%I:%M %p ET").lstrip("0")
    except Exception:
        hora_fmt  = evento.get("hora_et", "TBD")

    return {
        "horas_restantes": round(horas_rest, 1),
        "dias_restantes":  max(0, dias_rest),
        "hora_local_et":   hora_fmt,
        "es_futuro":       horas_rest > 0,
    }


# ── Función principal ─────────────────────────────────────────────
def obtener_eventos_proximos(dias: int = 30) -> list:
    """
    Retorna eventos próximos ordenados por fecha.
    Solo incluye eventos futuros dentro de los próximos N días.
    """
    ahora = datetime.now()
    limite = ahora + timedelta(days=dias)

    eventos_activos = []
    for ev in EVENTOS_MACRO:
        try:
            fecha_ev = datetime.strptime(ev["fecha"], "%Y-%m-%d")
        except Exception:
            continue

        if fecha_ev < ahora - timedelta(hours=4):
            continue
        if fecha_ev > limite:
            continue

        tiempos = _calcular_tiempos(ev)
        if not tiempos["es_futuro"]:
            continue

        eventos_activos.append({
            **ev,
            **tiempos,
        })

    eventos_activos.sort(key=lambda x: x["horas_restantes"])
    return eventos_activos


def verificar_alertas_calendario(estado: dict) -> list:
    """
    Verifica si hay eventos próximos que requieren alerta.
    Ventanas: CRÍTICO = 24h antes | ALTO = 6h antes | 1h antes siempre.
    No reenvía si ya se envió una alerta para ese evento.
    """
    alertas_enviadas = _cargar_alertas_enviadas(estado)
    eventos          = obtener_eventos_proximos(dias=2)
    nuevas_alertas   = []

    for ev in eventos:
        horas = ev["horas_restantes"]
        imp   = ev["impacto"]

        # Ventanas de alerta según importancia
        ventanas = []
        if imp == "CRÍTICO":
            ventanas = [24, 6, 1]
        elif imp == "ALTO":
            ventanas = [6, 1]
        else:
            ventanas = [1]

        for ventana in ventanas:
            if horas > ventana or horas <= 0:
                continue

            clave = f"{ev['evento']}_{ventana}h"
            if clave in alertas_enviadas:
                continue

            emoji    = "🚨" if imp == "CRÍTICO" else "⚠️"
            tiempo_t = f"{int(horas*60)} min" if horas < 1 else f"{round(horas,1)}h"

            mensaje = (
                f"{emoji} KAIROS — EVENTO MACRO EN {tiempo_t.upper()}\n"
                f"{'='*38}\n"
                f"📅 {ev['evento']}\n"
                f"🕐 {ev['hora_local_et']}\n"
                f"📊 Consenso: {ev['consenso']}\n"
                f"📈 Anterior: {ev['anterior']}\n"
                f"🎯 Activos: {', '.join(ev['activos'][:5])}\n\n"
                f"📋 {ev['descripcion']}\n\n"
                f"⚡ Event Brief llegará 30 min antes del dato\n\n"
                f"kairos-markets.streamlit.app"
            )

            nuevas_alertas.append({
                "tipo":         "CALENDARIO",
                "clave_alerta": clave,
                "evento":       ev["evento"],
                "mensaje":      mensaje,
                "horas":        horas,
            })
            _guardar_alerta_enviada(estado, clave)

    return nuevas_alertas


def resumen_semana() -> str:
    """Genera resumen de eventos de la semana para el mensaje de inicio."""
    eventos = obtener_eventos_proximos(dias=7)
    if not eventos:
        return "Sin eventos críticos esta semana."

    lineas = ["📅 EVENTOS ESTA SEMANA:"]
    for ev in eventos[:5]:
        emoji = {"CRÍTICO": "🚨", "ALTO": "⚠️"}.get(ev["impacto"], "📡")
        lineas.append(
            f"{emoji} {ev['evento']} — {ev['dias_restantes']} días | {ev['hora_local_et']}"
        )
    return "\n".join(lineas)


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n📅 KAIROS — Calendario Económico 2026")
    print("="*55)

    eventos = obtener_eventos_proximos(dias=90)
    print(f"\nEventos próximos (90 días): {len(eventos)}\n")

    for ev in eventos:
        emoji = {"CRÍTICO":"🚨","ALTO":"⚠️","MEDIO":"📡"}.get(ev["impacto"],"📡")
        dias  = ev["dias_restantes"]
        print(f"{emoji} {ev['evento']}")
        print(f"   📅 {ev['fecha']} {ev['hora_local_et']} | en {dias} días")
        print(f"   Consenso: {ev['consenso']}")
        if ev.get("prob_sorpresa"):
            h = ev["prob_sorpresa"]["prob_sorpresa_hawkish"]
            d = ev["prob_sorpresa"]["prob_sorpresa_dovish"]
            print(f"   🔴 Hawkish {h}% | 🟢 Dovish {d}%")
        print()
