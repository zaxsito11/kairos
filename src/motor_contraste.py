# motor_contraste.py — KAIROS
# Contrasta análisis técnico vs análisis fundamental.
# Da un veredicto final con probabilidad real.
#
# LÓGICA:
#   TÉCNICO ALCISTA + FUNDAMENTAL ALCISTA → SEÑAL FUERTE (ambos confirman)
#   TÉCNICO ALCISTA + FUNDAMENTAL BAJISTA → CONFLICTO (explicar cuál domina y por qué)
#   CONFLICTO → no es silencio, es una señal en sí misma con narrativa

import os, sys, json
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

# ── Veredictos posibles ───────────────────────────────────────────
VEREDICTOS = {
    "FUERTE_ALCISTA":   {"emoji":"🟢🟢", "accionable": True,  "umbral_confianza": 75},
    "MODERADO_ALCISTA": {"emoji":"🟢",   "accionable": True,  "umbral_confianza": 60},
    "FUERTE_BAJISTA":   {"emoji":"🔴🔴", "accionable": True,  "umbral_confianza": 75},
    "MODERADO_BAJISTA": {"emoji":"🔴",   "accionable": True,  "umbral_confianza": 60},
    "CONFLICTO_FUNDAMENTAL_DOMINA": {"emoji":"⚡", "accionable": True,  "umbral_confianza": 55},
    "CONFLICTO_TECNICO_DOMINA":     {"emoji":"📊", "accionable": True,  "umbral_confianza": 55},
    "NEUTRO":           {"emoji":"↔️",  "accionable": False, "umbral_confianza": 0},
}


def contrastar(activo: str,
               señal_tecnica: dict,
               sesgo_fundamental: dict) -> dict:
    """
    Contrasta análisis técnico vs fundamental para un activo.

    Args:
        señal_tecnica:     Output de analisis_tecnico.analizar_activo()
        sesgo_fundamental: Output de analisis_fundamental sesgo_global[activo]

    Returns:
        Veredicto con dirección, confianza, narrativa y tipo de señal
    """
    # Extraer datos técnicos
    dir_tec  = señal_tecnica.get("señal", "NEUTRAL")
    conf_tec = señal_tecnica.get("confianza", 50)
    rsi      = señal_tecnica.get("rsi", 50)
    macd     = señal_tecnica.get("macd_cruce", "NEUTRAL")
    vol      = señal_tecnica.get("vol_relativo", 1.0)
    obv      = señal_tecnica.get("obv_tendencia", "NEUTRAL")

    # Normalizar dirección técnica
    dir_tec_norm = "ALCISTA" if dir_tec == "ALCISTA" else \
                   "BAJISTA" if dir_tec == "BAJISTA" else "NEUTRO"

    # Extraer datos fundamentales
    dir_fund  = sesgo_fundamental.get("direccion", "NEUTRO")
    conf_fund = sesgo_fundamental.get("confianza", 0)
    razones   = sesgo_fundamental.get("razones", [])

    # ── Determinar convergencia ───────────────────────────────────
    ambos_alcanzan   = dir_tec_norm == "ALCISTA" and dir_fund == "ALCISTA"
    ambos_bajan      = dir_tec_norm == "BAJISTA" and dir_fund == "BAJISTA"
    conflicto        = (dir_tec_norm != "NEUTRO" and dir_fund != "NEUTRO"
                        and dir_tec_norm != dir_fund)
    solo_tecnico     = dir_tec_norm != "NEUTRO" and dir_fund == "NEUTRO"
    solo_fundamental = dir_fund != "NEUTRO" and dir_tec_norm == "NEUTRO"

    # ── Calcular confianza combinada ──────────────────────────────
    if ambos_alcanzan or ambos_bajan:
        # Convergencia → amplificar confianza
        conf_combinada = min(round((conf_tec * 0.45 + conf_fund * 0.55) + 15), 92)
        direccion      = "ALCISTA" if ambos_alcanzan else "BAJISTA"
        tipo           = "FUERTE_ALCISTA" if conf_combinada >= 75 else "MODERADO_ALCISTA" \
                         if ambos_alcanzan else \
                         "FUERTE_BAJISTA" if conf_combinada >= 75 else "MODERADO_BAJISTA"

    elif conflicto:
        # Conflicto → determinar cuál domina
        # Fundamental domina cuando hay eventos de alta confianza activos
        # Técnico domina cuando el precio ya se está moviendo (vol alto, OBV claro)
        peso_fundamental = conf_fund
        peso_tecnico     = conf_tec
        # Volumen alto le da más peso al técnico
        if vol >= 1.5 and obv != "NEUTRAL":
            peso_tecnico += 15
        # Eventos geopolíticos activos le dan más peso al fundamental
        if conf_fund >= 70:
            peso_fundamental += 10

        if peso_fundamental >= peso_tecnico:
            direccion      = dir_fund
            conf_combinada = round(conf_fund * 0.7)
            tipo           = "CONFLICTO_FUNDAMENTAL_DOMINA"
        else:
            direccion      = dir_tec_norm
            conf_combinada = round(conf_tec * 0.65)
            tipo           = "CONFLICTO_TECNICO_DOMINA"

    elif solo_fundamental:
        direccion      = dir_fund
        conf_combinada = round(conf_fund * 0.75)
        tipo           = "MODERADO_ALCISTA" if dir_fund == "ALCISTA" else "MODERADO_BAJISTA"

    elif solo_tecnico:
        direccion      = dir_tec_norm
        conf_combinada = round(conf_tec * 0.70)
        tipo           = "MODERADO_ALCISTA" if dir_tec_norm == "ALCISTA" else "MODERADO_BAJISTA"

    else:
        return {
            "activo":         activo,
            "veredicto":      "NEUTRO",
            "direccion":      "NEUTRO",
            "confianza":      0,
            "accionable":     False,
            "dir_tecnica":    dir_tec_norm,
            "conf_tecnica":   conf_tec,
            "dir_fundamental":dir_fund,
            "conf_fundamental":conf_fund,
            "tipo":           "NEUTRO",
            "emoji":          "↔️",
        }

    veredicto_cfg = VEREDICTOS.get(tipo, VEREDICTOS["NEUTRO"])
    accionable    = (veredicto_cfg["accionable"] and
                     conf_combinada >= veredicto_cfg["umbral_confianza"])

    return {
        "activo":           activo,
        "veredicto":        tipo,
        "direccion":        direccion,
        "confianza":        conf_combinada,
        "accionable":       accionable,
        "emoji":            veredicto_cfg["emoji"],

        # Desglose
        "dir_tecnica":      dir_tec_norm,
        "conf_tecnica":     conf_tec,
        "dir_fundamental":  dir_fund,
        "conf_fundamental": conf_fund,
        "convergencia":     ambos_alcanzan or ambos_bajan,
        "conflicto":        conflicto,

        # Indicadores técnicos clave
        "rsi":              rsi,
        "macd":             macd,
        "vol_relativo":     vol,
        "obv":              obv,

        # Razones fundamentales
        "razones_fundamental": razones,
        "timestamp":        datetime.now().isoformat(),
    }


def analisis_completo_mercado() -> dict:
    """
    Ejecuta análisis técnico + fundamental separados
    y los contrasta para todos los activos.
    """
    print("\n🔬 KAIROS — Análisis Completo (Técnico + Fundamental)")
    print("="*55)

    # 1. Análisis técnico
    print("\n[1/3] Análisis técnico...")
    from analisis_tecnico import analizar_todos
    tecnico = analizar_todos()

    # 2. Análisis fundamental
    print("\n[2/3] Análisis fundamental...")
    from analisis_fundamental import analizar_contexto_fundamental_completo
    fundamental = analizar_contexto_fundamental_completo()
    sesgo_global = fundamental.get("sesgo_global", {})

    # 3. Contraste
    print("\n[3/3] Contrastando señales...")
    resultados   = {}
    accionables  = []

    activos = ["SPX","NDX","Gold","Silver","WTI","BTC","DXY","VIX","UST10Y"]
    for activo in activos:
        tec  = tecnico.get(activo, {})
        fund = sesgo_global.get(activo, {"direccion":"NEUTRO","confianza":0})
        resultado = contrastar(activo, tec, fund)

        # Agregar precio y target técnico
        resultado["precio"]     = tec.get("precio", 0)
        resultado["target_24h"] = tec.get("target_24h", 0)
        resultado["target_7d"]  = tec.get("target_7d", 0)

        resultados[activo] = resultado
        if resultado.get("accionable"):
            accionables.append(activo)

    return {
        "timestamp":     datetime.now().isoformat(),
        "n_accionables": len(accionables),
        "accionables":   accionables,
        "resultados":    resultados,
        "fundamental":   fundamental,
    }


def formatear_para_telegram(analisis: dict) -> str:
    """Formatea el análisis completo para Telegram."""
    if not analisis.get("accionables"):
        return ""

    fecha  = datetime.now().strftime("%d %B %Y %H:%M")
    lineas = [
        "🎯 KAIROS — ANÁLISIS COMPLETO",
        "Técnico + Fundamental contrastados",
        "="*38,
        f"📅 {fecha}",
        "",
    ]

    for activo in analisis["accionables"]:
        r     = analisis["resultados"][activo]
        emoji = r.get("emoji","")
        dir_  = r.get("direccion","")
        conf  = r.get("confianza",0)
        t24h  = r.get("target_24h",0)
        prec  = r.get("precio",0)

        # Indicar convergencia o conflicto
        if r.get("convergencia"):
            tipo_txt = "CONVERGENCIA"
        elif r.get("conflicto"):
            dom = "FUNDAMENTAL" if "FUNDAMENTAL" in r.get("veredicto","") else "TÉCNICO"
            tipo_txt = f"CONFLICTO → {dom} domina"
        else:
            tipo_txt = "señal única"

        lineas.append(f"{emoji} {activo} {dir_} — {conf}%")
        lineas.append(f"   [{tipo_txt}]")
        lineas.append(f"   Técnico: {r['dir_tecnica']} ({r['conf_tecnica']}%)")
        lineas.append(f"   Fundamental: {r['dir_fundamental']} ({r['conf_fundamental']}%)")
        if t24h and prec:
            lineas.append(f"   Precio: {prec} → T24h: {t24h}")
        for razon in r.get("razones_fundamental",[])[:1]:
            if razon:
                lineas.append(f"   {razon[:60]}")
        lineas.append("")

    lineas += ["kairos-markets.streamlit.app",
               "Análisis informativo — no es recomendación"]
    return "\n".join(lineas)


if __name__ == "__main__":
    resultado = analisis_completo_mercado()

    print(f"\n{'='*55}")
    print(f"VEREDICTO FINAL — {resultado['n_accionables']} señales accionables")
    print(f"{'='*55}\n")

    for activo, r in resultado["resultados"].items():
        emoji  = r.get("emoji","")
        dir_   = r.get("direccion","NEUTRO")
        conf   = r.get("confianza",0)
        conv   = "✓ CONVERGENCIA" if r.get("convergencia") else \
                 "⚡ CONFLICTO" if r.get("conflicto") else "señal única"
        acc    = "✅" if r.get("accionable") else "⚫"
        print(f"{acc} {emoji} {activo:8} {dir_:8} {conf:3}%  [{conv}]")
        if r.get("accionable"):
            print(f"     Tec: {r['dir_tecnica']:8} {r['conf_tecnica']}% | "
                  f"Fund: {r['dir_fundamental']:8} {r['conf_fundamental']}%")
