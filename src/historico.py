import json
import os
from datetime import datetime

# Base de datos de eventos historicos del FOMC
# con sus outcomes reales en mercados
EVENTOS_HISTORICOS = [
    {
        "fecha": "2022-03-16",
        "evento": "FOMC sube tasas 25bps - inicio ciclo restrictivo",
        "tono": "HAWKISH FUERTE",
        "score": 4,
        "contexto": "Primera subida desde 2018. Inflacion en 7.9%. Guerra Ucrania.",
        "outcomes_24h": {
            "SPX": -0.4,
            "NDX": -0.3,
            "Gold": -1.2,
            "DXY": +0.8,
            "UST10Y": +8,
            "VIX": -5.2
        },
        "outcomes_1w": {
            "SPX": +5.8,
            "NDX": +7.1,
            "Gold": -2.1,
            "DXY": +1.2
        },
        "leccion": "Mercado subio post-decision a pesar de hawkishness. 'Buy the news' tras incertidumbre previa."
    },
    {
        "fecha": "2022-06-15",
        "evento": "FOMC sube tasas 75bps - mayor subida desde 1994",
        "tono": "HAWKISH FUERTE",
        "score": 5,
        "contexto": "Inflacion en 8.6%. Sorpresa total - mercado esperaba 50bps.",
        "outcomes_24h": {
            "SPX": +1.5,
            "NDX": +2.5,
            "Gold": -1.8,
            "DXY": +0.9,
            "UST10Y": -5,
            "VIX": -8.1
        },
        "outcomes_1w": {
            "SPX": -5.8,
            "NDX": -6.2,
            "Gold": -2.9,
            "DXY": +1.8
        },
        "leccion": "Rally inicial seguido de caida fuerte. FED detras de la curva, credibilidad cuestionada."
    },
    {
        "fecha": "2022-11-02",
        "evento": "FOMC sube 75bps pero Powell senala posible pausa",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Cuarta subida consecutiva de 75bps. Mercado esperaba señal de pivot.",
        "outcomes_24h": {
            "SPX": -2.5,
            "NDX": -3.1,
            "Gold": +0.8,
            "DXY": +0.6,
            "UST10Y": +10,
            "VIX": +12.3
        },
        "outcomes_1w": {
            "SPX": +5.9,
            "NDX": +7.2,
            "Gold": +3.1,
            "DXY": -2.1
        },
        "leccion": "Caida inicial por decepcion, rally posterior cuando mercado digiere señal de pausa."
    },
    {
        "fecha": "2023-02-01",
        "evento": "FOMC sube 25bps - desaceleracion del ritmo",
        "tono": "HAWKISH LEVE",
        "score": 1,
        "contexto": "Inflacion bajando pero aun elevada. Primer 25bps tras serie de 75bps.",
        "outcomes_24h": {
            "SPX": +1.1,
            "NDX": +2.0,
            "Gold": +1.3,
            "DXY": -0.8,
            "UST10Y": -6,
            "VIX": -6.4
        },
        "outcomes_1w": {
            "SPX": -0.9,
            "NDX": -1.2,
            "Gold": -0.4,
            "DXY": +0.3
        },
        "leccion": "Rally moderado al confirmar desaceleracion de subidas. Mercado ya tenia bastante priced-in."
    },
    {
        "fecha": "2023-07-26",
        "evento": "FOMC sube 25bps - posiblemente ultima subida del ciclo",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Inflacion en 3%. Powell deja puerta abierta a pausa prolongada.",
        "outcomes_24h": {
            "SPX": +0.2,
            "NDX": +0.4,
            "Gold": +0.3,
            "DXY": -0.1,
            "UST10Y": +2,
            "VIX": -2.1
        },
        "outcomes_1w": {
            "SPX": -2.3,
            "NDX": -2.8,
            "Gold": -1.1,
            "DXY": +0.7
        },
        "leccion": "Reaccion minima al evento. Completamente priced-in. Mercado se movio por datos posteriores."
    },
    {
        "fecha": "2023-09-20",
        "evento": "FOMC mantiene tasas - hawkish pause",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Pausa pero dot plot revela posible subida adicional en 2023.",
        "outcomes_24h": {
            "SPX": -0.9,
            "NDX": -1.5,
            "Gold": -1.1,
            "DXY": +0.7,
            "UST10Y": +12,
            "VIX": +8.2
        },
        "outcomes_1w": {
            "SPX": -2.9,
            "NDX": -3.5,
            "Gold": -2.3,
            "DXY": +1.4
        },
        "leccion": "Dot plot mas hawkish de lo esperado causo sell-off en bonos y acciones."
    },
    {
        "fecha": "2024-01-31",
        "evento": "FOMC mantiene tasas - descarta recorte en marzo",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Mercado tenia 70% priced-in de recorte en marzo. Powell lo descarta.",
        "outcomes_24h": {
            "SPX": -1.6,
            "NDX": -2.2,
            "Gold": -0.8,
            "DXY": +0.9,
            "UST10Y": +8,
            "VIX": +9.1
        },
        "outcomes_1w": {
            "SPX": +1.4,
            "NDX": +2.1,
            "Gold": +0.6,
            "DXY": -0.3
        },
        "leccion": "Sorpresa hawkish causo caida inmediata. Recuperacion posterior cuando datos confirmaron desinflacion."
    },
    {
        "fecha": "2024-09-18",
        "evento": "FOMC recorta 50bps - inicio ciclo expansivo",
        "tono": "DOVISH LEVE",
        "score": -2,
        "contexto": "Primer recorte desde 2020. Mercado esperaba 25bps, llego 50bps.",
        "outcomes_24h": {
            "SPX": -0.3,
            "NDX": -0.3,
            "Gold": +1.1,
            "DXY": -0.4,
            "UST10Y": -4,
            "VIX": +5.2
        },
        "outcomes_1w": {
            "SPX": +1.7,
            "NDX": +1.9,
            "Gold": +2.3,
            "DXY": -1.1
        },
        "leccion": "Reaccion inicial negativa - mercado interpreta 50bps como señal de preocupacion. Rally posterior."
    },
    {
        "fecha": "2024-12-18",
        "evento": "FOMC recorta 25bps pero reduce proyeccion de recortes 2025",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Dot plot pasa de 4 a 2 recortes proyectados en 2025. Sorpresa hawkish.",
        "outcomes_24h": {
            "SPX": -2.9,
            "NDX": -3.6,
            "Gold": -1.8,
            "DXY": +1.2,
            "UST10Y": +12,
            "VIX": +25.4
        },
        "outcomes_1w": {
            "SPX": -2.1,
            "NDX": -2.4,
            "Gold": -1.2,
            "DXY": +0.8
        },
        "leccion": "Uno de los mayores sell-offs post-FED del ciclo. Dot plot fue la sorpresa, no la decision."
    },
    {
        "fecha": "2025-01-29",
        "evento": "FOMC pausa - sin cambios en tasas",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Primera reunion de Trump. FED en modo espera. Sin sorpresas.",
        "outcomes_24h": {
            "SPX": +0.5,
            "NDX": +0.7,
            "Gold": +0.4,
            "DXY": -0.2,
            "UST10Y": -2,
            "VIX": -4.1
        },
        "outcomes_1w": {
            "SPX": +1.2,
            "NDX": +1.5,
            "Gold": +0.8,
            "DXY": -0.4
        },
        "leccion": "Evento completamente neutral. Mercado ignoró decision y siguio tendencia previa."
    }
]


def encontrar_similares(tono_actual, score_actual, n=3):
    """
    Encuentra los eventos historicos mas similares
    al evento actual basandose en tono y score.
    """

    candidatos = []

    for evento in EVENTOS_HISTORICOS:
        # Calcular similitud
        diff_score = abs(evento["score"] - score_actual)
        mismo_tono = 1 if evento["tono"] == tono_actual else 0

        # Score de similitud (menor = mas similar)
        similitud = diff_score - (mismo_tono * 0.5)
        candidatos.append((similitud, evento))

    # Ordenar por similitud
    candidatos.sort(key=lambda x: x[0])

    return [e for _, e in candidatos[:n]]


def generar_resumen_historico(eventos_similares):
    """
    Genera un resumen de los eventos historicos similares
    con sus outcomes para incluir en el analisis.
    """

    if not eventos_similares:
        return "No se encontraron precedentes historicos similares."

    resumen = "PRECEDENTES HISTORICOS SIMILARES:\n"
    resumen += "=" * 50 + "\n\n"

    for i, evento in enumerate(eventos_similares, 1):
        resumen += f"{i}. {evento['fecha']} — {evento['evento']}\n"
        resumen += f"   Tono: {evento['tono']} (Score: {evento['score']})\n"
        resumen += f"   Contexto: {evento['contexto']}\n"
        resumen += f"   Outcomes 24h:\n"

        for activo, cambio in evento["outcomes_24h"].items():
            signo = "+" if cambio >= 0 else ""
            resumen += f"     {activo}: {signo}{cambio}%\n"

        resumen += f"   Leccion: {evento['leccion']}\n\n"

    # Calcular promedios
    spx_avg = sum(e["outcomes_24h"]["SPX"] for e in eventos_similares) / len(eventos_similares)
    gold_avg = sum(e["outcomes_24h"]["Gold"] for e in eventos_similares) / len(eventos_similares)
    dxy_avg  = sum(e["outcomes_24h"]["DXY"] for e in eventos_similares) / len(eventos_similares)

    resumen += "PROMEDIO HISTORICO (24h):\n"
    resumen += f"  SPX:  {'+' if spx_avg >= 0 else ''}{round(spx_avg, 1)}%\n"
    resumen += f"  Gold: {'+' if gold_avg >= 0 else ''}{round(gold_avg, 1)}%\n"
    resumen += f"  DXY:  {'+' if dxy_avg >= 0 else ''}{round(dxy_avg, 1)}%\n"

    return resumen


def mostrar_historico(tono, score):
    """Muestra los eventos historicos similares en consola."""

    print(f"\n📚 Buscando precedentes para: {tono} (Score: {score})")
    similares = encontrar_similares(tono, score)
    resumen   = generar_resumen_historico(similares)
    print(resumen)
    return similares


if __name__ == "__main__":
    mostrar_historico("HAWKISH LEVE", 2)