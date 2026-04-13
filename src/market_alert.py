# market_alert.py — KAIROS
#
# CONCEPTO:
# No es suficiente detectar que el VIX subió 15%.
# KAIROS necesita explicar POR QUÉ subió y qué significa
# para los próximos movimientos del mercado.
#
# Este módulo detecta movimientos anómalos Y los conecta
# con el contexto macro y geopolítico actual para dar
# una alerta accionable, no solo un número.

import os
import sys
import json
from datetime import datetime, timedelta
import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))

# ── Configuración de umbrales ─────────────────────────────────────
# Movimiento diario que dispara alerta
UMBRALES = {
    "VIX":   {"subida": 15.0,  "bajada": -15.0, "unidad": "puntos %"},
    "SPX":   {"subida":  1.5,  "bajada":  -1.5, "unidad": "%"},
    "NDX":   {"subida":  2.0,  "bajada":  -2.0, "unidad": "%"},
    "DXY":   {"subida":  0.7,  "bajada":  -0.7, "unidad": "%"},
    "Gold":  {"subida":  1.2,  "bajada":  -1.2, "unidad": "%"},
    "WTI":   {"subida":  2.5,  "bajada":  -2.5, "unidad": "%"},
    "UST10Y":{"subida":  0.08, "bajada": -0.08, "unidad": "bps"},
}

# Niveles técnicos clave a vigilar
NIVELES_CLAVE = {
    "VIX":    [20, 25, 30, 40],      # niveles de pánico histórico
    "SPX":    [5000, 5200, 5500],    # soportes/resistencias clave
    "DXY":    [100, 102, 105],       # niveles de dólar
    "Gold":   [2800, 3000, 3200],    # niveles de oro
    "UST10Y": [4.0, 4.25, 4.5, 5.0],# yields clave
}

# Interpretación contextual por activo y dirección
INTERPRETACION = {
    "VIX_SUBE": {
        "nombre":   "VIX SPIKE — Miedo al mercado",
        "contexto": "El mercado está comprando protección. Señal clásica de risk-off.",
        "implicaciones": [
            "Salida de activos de riesgo (SPX, NDX) probable",
            "Flujo hacia refugios: Gold, DXY, UST",
            "Ampliación de spreads de crédito posible",
            "Revisar eventos macro en calendario próximo",
        ],
        "precedentes": {
            "SPX_24h":  "-1.8% promedio cuando VIX sube >15%",
            "Gold_24h": "+1.2% promedio cuando VIX sube >15%",
            "DXY_24h":  "+0.5% promedio cuando VIX sube >15%",
        }
    },
    "VIX_BAJA": {
        "nombre":   "VIX COMPRESIÓN — Calma de mercado",
        "contexto": "Reducción de incertidumbre. Señal de risk-on.",
        "implicaciones": [
            "Favorece activos de riesgo (SPX, NDX)",
            "Presión bajista en refugios (Gold, DXY)",
            "Ambiente favorable para carry trades",
        ],
        "precedentes": {
            "SPX_24h":  "+0.8% promedio cuando VIX baja >15%",
            "Gold_24h": "-0.6% promedio cuando VIX baja >15%",
        }
    },
    "SPX_BAJA": {
        "nombre":   "SPX CAÍDA — Presión vendedora",
        "contexto": "Salida de renta variable estadounidense.",
        "implicaciones": [
            "Verificar si hay catalizador específico (macro, geopolítica)",
            "NDX probablemente amplifica el movimiento",
            "Gold y UST como refugio probable",
            "Revisar si VIX confirma el movimiento",
        ],
        "precedentes": {
            "NDX_24h":  "-1.3x el movimiento de SPX históricamente",
            "Gold_24h": "+0.6% promedio cuando SPX cae >1.5%",
            "VIX_24h":  "+12% promedio cuando SPX cae >1.5%",
        }
    },
    "SPX_SUBE": {
        "nombre":   "SPX RALLY — Momentum alcista",
        "contexto": "Flujo positivo hacia renta variable.",
        "implicaciones": [
            "Risk-on activo — revisar catalizador",
            "NDX suele amplificar en rallies",
            "Posible presión en refugios (Gold, DXY)",
        ],
        "precedentes": {
            "NDX_24h":  "+1.3x el movimiento de SPX históricamente",
            "Gold_24h": "-0.4% promedio cuando SPX sube >1.5%",
        }
    },
    "DXY_SUBE": {
        "nombre":   "DXY FORTALEZA — Dólar al alza",
        "contexto": "Fortaleza del dólar. Presión sobre emergentes y commodities.",
        "implicaciones": [
            "Presión bajista en commodities (Gold, WTI)",
            "EURUSD y GBPUSD bajo presión",
            "Emergentes con mayor estrés de financiamiento",
            "Posible señal hawkish de la FED o risk-off global",
        ],
        "precedentes": {
            "Gold_24h":  "-0.7% promedio cuando DXY sube >0.7%",
            "EURUSD_24h":"-0.6% promedio cuando DXY sube >0.7%",
            "WTI_24h":   "-1.2% promedio cuando DXY sube >0.7%",
        }
    },
    "DXY_BAJA": {
        "nombre":   "DXY DEBILIDAD — Dólar a la baja",
        "contexto": "Debilidad del dólar. Favorable para commodities.",
        "implicaciones": [
            "Impulso alcista en Gold y commodities",
            "EURUSD y divisas emergentes se benefician",
            "Posible señal dovish FED o risk-on global",
        ],
        "precedentes": {
            "Gold_24h": "+0.8% promedio cuando DXY baja >0.7%",
            "WTI_24h":  "+1.0% promedio cuando DXY baja >0.7%",
        }
    },
    "Gold_SUBE": {
        "nombre":   "GOLD RALLY — Demanda de refugio",
        "contexto": "El oro sube. Señal de incertidumbre o inflación.",
        "implicaciones": [
            "Risk-off activo o expectativas inflacionarias al alza",
            "Revisar si hay catalizador geopolítico",
            "DXY puede estar débil — verificar",
            "Bonos del tesoro también suelen subir en este escenario",
        ],
        "precedentes": {
            "SPX_24h":  "-0.8% promedio cuando Gold sube >1.2%",
            "DXY_24h":  "-0.4% promedio cuando Gold sube >1.2%",
        }
    },
    "WTI_SUBE": {
        "nombre":   "WTI RALLY — Petróleo al alza",
        "contexto": "Precio del petróleo subiendo. Impacto inflacionario.",
        "implicaciones": [
            "Presión inflacionaria — hawkish para FED y BCE",
            "Sectores energéticos se benefician",
            "Consumo y transporte bajo presión",
            "Revisar si hay catalizador OPEC o geopolítico",
        ],
        "precedentes": {
            "Gold_24h":  "+0.5% promedio cuando WTI sube >2.5%",
            "SPX_24h":   "Mixto — depende del contexto macro",
        }
    },
    "UST10Y_SUBE": {
        "nombre":   "YIELD 10Y SUBE — Tasas al alza",
        "contexto": "Yields subiendo. Presión sobre valoraciones y renta variable.",
        "implicaciones": [
            "Encarecimiento del crédito y hipotecas",
            "Presión sobre valoraciones de growth (NDX especialmente)",
            "DXY suele fortalecerse",
            "Señal de expectativas hawkish o mayor oferta de bonos",
        ],
        "precedentes": {
            "NDX_24h":  "-1.5% promedio cuando 10Y sube >8bps",
            "DXY_24h":  "+0.4% promedio cuando 10Y sube >8bps",
            "Gold_24h": "-0.5% promedio cuando 10Y sube >8bps",
        }
    },
}


# ── Funciones de datos ────────────────────────────────────────────
def obtener_datos_mercado() -> dict:
    """
    Obtiene datos actuales de todos los activos monitoreados.
    Retorna precio actual, cambio diario y si rompió nivel clave.
    """
    tickers = {
        "VIX":    "^VIX",
        "SPX":    "^GSPC",
        "NDX":    "^NDX",
        "DXY":    "DX-Y.NYB",
        "Gold":   "GC=F",
        "WTI":    "CL=F",
        "UST10Y": "^TNX",
    }

    datos = {}
    for nombre, ticker in tickers.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue

            hoy   = float(hist["Close"].iloc[-1])
            ayer  = float(hist["Close"].iloc[-2])
            pct   = ((hoy - ayer) / ayer) * 100

            # Verificar si rompió nivel clave
            nivel_roto = None
            for nivel in NIVELES_CLAVE.get(nombre, []):
                if ayer < nivel <= hoy:
                    nivel_roto = {"tipo": "RUPTURA_ALCISTA", "nivel": nivel}
                elif ayer > nivel >= hoy:
                    nivel_roto = {"tipo": "RUPTURA_BAJISTA", "nivel": nivel}

            datos[nombre] = {
                "precio":       round(hoy, 2),
                "precio_ayer":  round(ayer, 2),
                "cambio_pct":   round(pct, 2),
                "nivel_roto":   nivel_roto,
                "timestamp":    datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"   Error obteniendo {nombre}: {e}")

    return datos


def detectar_alertas(datos: dict) -> list:
    """
    Analiza los datos de mercado y genera alertas cuando
    hay movimientos significativos o ruptura de niveles clave.
    """
    alertas = []

    for nombre, info in datos.items():
        pct    = info["cambio_pct"]
        precio = info["precio"]
        umbral = UMBRALES.get(nombre, {})

        if not umbral:
            continue

        alerta_tipo = None

        # ── Umbral de movimiento
        if pct >= umbral.get("subida", 999):
            alerta_tipo = f"{nombre}_SUBE"
        elif pct <= umbral.get("bajada", -999):
            alerta_tipo = f"{nombre}_BAJA"

        # ── Ruptura de nivel clave (siempre alerta aunque no supere umbral)
        nivel_roto = info.get("nivel_roto")
        if nivel_roto and not alerta_tipo:
            dir_ = "SUBE" if nivel_roto["tipo"] == "RUPTURA_ALCISTA" else "BAJA"
            alerta_tipo = f"{nombre}_{dir_}"

        if alerta_tipo:
            interpretacion = INTERPRETACION.get(alerta_tipo, {})
            alertas.append({
                "activo":         nombre,
                "precio":         precio,
                "cambio_pct":     pct,
                "tipo":           alerta_tipo,
                "nivel_roto":     nivel_roto,
                "nombre":         interpretacion.get("nombre", alerta_tipo),
                "contexto":       interpretacion.get("contexto", ""),
                "implicaciones":  interpretacion.get("implicaciones", []),
                "precedentes":    interpretacion.get("precedentes", {}),
                "timestamp":      datetime.now().isoformat(),
            })

    # Ordenar por magnitud de movimiento
    alertas.sort(key=lambda x: abs(x["cambio_pct"]), reverse=True)
    return alertas


def generar_mensaje_alerta(alerta: dict, regimen: dict = None) -> str:
    """
    Genera mensaje completo para Telegram.
    Incluye movimiento, contexto, implicaciones y precedentes.
    """
    activo    = alerta["activo"]
    precio    = alerta["precio"]
    pct       = alerta["cambio_pct"]
    nombre    = alerta["nombre"]
    contexto  = alerta["contexto"]
    impl      = alerta["implicaciones"]
    prec      = alerta["precedentes"]
    nivel     = alerta.get("nivel_roto")

    signo     = "+" if pct > 0 else ""
    emoji_dir = "📈" if pct > 0 else "📉"

    # Urgencia por magnitud
    abs_pct = abs(pct)
    if abs_pct >= 3 or (activo == "VIX" and abs_pct >= 25):
        urgencia = "🚨 CRÍTICO"
    elif abs_pct >= 1.5 or (activo == "VIX" and abs_pct >= 15):
        urgencia = "⚠️ ALTO"
    else:
        urgencia = "📡 MEDIO"

    lineas = [
        f"{urgencia} — KAIROS ALERT MERCADO",
        f"{'='*38}",
        f"{emoji_dir} {nombre}",
        f"",
        f"📊 {activo}: {precio} ({signo}{pct}%)",
    ]

    if nivel:
        tipo_ruptura = "🔼 RUPTURA ALCISTA" if nivel["tipo"] == "RUPTURA_ALCISTA" else "🔽 RUPTURA BAJISTA"
        lineas.append(f"⚡ {tipo_ruptura} del nivel {nivel['nivel']}")

    lineas += [
        f"",
        f"🧠 {contexto}",
    ]

    if regimen:
        lineas.append(f"📊 Régimen macro: {regimen.get('regimen','?')}")

    if impl:
        lineas += ["", "📋 IMPLICACIONES:"]
        for i in impl[:3]:
            lineas.append(f"  → {i}")

    if prec:
        lineas += ["", "📚 HISTÓRICO:"]
        for k, v in list(prec.items())[:3]:
            lineas.append(f"  • {v}")

    lineas += ["", "kairos-markets.streamlit.app"]
    return "\n".join(lineas)


def analizar_correlaciones(alertas: list, datos: dict) -> str:
    """
    Si hay múltiples alertas simultáneas, detecta el patrón
    macro subyacente — eso es más valioso que alertas individuales.
    """
    if len(alertas) < 2:
        return ""

    activos_alerta = {a["activo"]: a["cambio_pct"] for a in alertas}

    # Patrón RISK-OFF clásico
    if (activos_alerta.get("VIX", 0) > 0 and
            activos_alerta.get("SPX", 0) < 0 and
            activos_alerta.get("Gold", 0) > 0):
        return (
            "🔴 PATRÓN RISK-OFF DETECTADO\n"
            "VIX sube + SPX baja + Gold sube = salida clásica de riesgo.\n"
            "Buscar catalizador: macro, geopolítica o evento sistémico."
        )

    # Patrón RISK-ON
    if (activos_alerta.get("VIX", 0) < 0 and
            activos_alerta.get("SPX", 0) > 0):
        return (
            "🟢 PATRÓN RISK-ON DETECTADO\n"
            "VIX baja + SPX sube = entrada de capital a riesgo.\n"
            "Ambiente favorable para activos de mayor beta."
        )

    # Patrón INFLACIONARIO
    if (activos_alerta.get("WTI", 0) > 0 and
            activos_alerta.get("Gold", 0) > 0 and
            activos_alerta.get("DXY", 0) < 0):
        return (
            "🟡 PATRÓN INFLACIONARIO DETECTADO\n"
            "WTI sube + Gold sube + DXY baja = presiones inflacionarias.\n"
            "Hawkish para FED y BCE. Bonos bajo presión."
        )

    # Patrón HAWKISH (dólar + yields suben)
    if (activos_alerta.get("DXY", 0) > 0 and
            activos_alerta.get("UST10Y", 0) > 0):
        return (
            "🔴 PATRÓN HAWKISH DETECTADO\n"
            "DXY sube + Yields suben = expectativas de política restrictiva.\n"
            "Presión sobre renta variable y commodities."
        )

    return ""


# ── Función principal para el monitor ────────────────────────────
def ejecutar_market_alert(regimen: dict = None) -> list:
    """
    Función principal que ejecuta el análisis completo de mercado.
    Retorna lista de alertas con mensajes listos para Telegram.
    """
    print("  Obteniendo datos de mercado...")
    datos   = obtener_datos_mercado()
    alertas = detectar_alertas(datos)

    # Detectar patrón macro si hay múltiples alertas
    patron = analizar_correlaciones(alertas, datos)

    mensajes = []

    # Si hay patrón macro, es el mensaje más importante — va primero
    if patron and len(alertas) >= 2:
        msg_patron = (
            f"{'='*38}\n"
            f"{patron}\n\n"
            f"Activos en movimiento: "
            f"{', '.join([a['activo'] for a in alertas])}\n\n"
            f"kairos-markets.streamlit.app"
        )
        mensajes.append({"tipo": "PATRON_MACRO", "mensaje": msg_patron})

    # Alertas individuales (máximo 3 para no saturar)
    for alerta in alertas[:3]:
        mensaje = generar_mensaje_alerta(alerta, regimen)
        mensajes.append({
            "tipo":    "ALERTA_MERCADO",
            "activo":  alerta["activo"],
            "mensaje": mensaje,
            "alerta":  alerta,
        })

    return mensajes


# ── Snapshot del mercado (para dashboard) ─────────────────────────
def obtener_snapshot() -> dict:
    """
    Retorna un snapshot completo del estado actual del mercado
    para mostrar en el dashboard.
    """
    datos   = obtener_datos_mercado()
    alertas = detectar_alertas(datos)
    patron  = analizar_correlaciones(alertas, datos)

    # Determinar régimen de mercado actual
    vix_pct = datos.get("VIX", {}).get("cambio_pct", 0)
    spx_pct = datos.get("SPX", {}).get("cambio_pct", 0)

    if vix_pct > 10 and spx_pct < -1:
        regimen_mercado = "RISK-OFF 🔴"
    elif vix_pct < -10 and spx_pct > 1:
        regimen_mercado = "RISK-ON 🟢"
    elif abs(vix_pct) < 5 and abs(spx_pct) < 0.5:
        regimen_mercado = "NEUTRAL 🟡"
    else:
        regimen_mercado = "MIXTO ⚪"

    return {
        "datos":           datos,
        "alertas":         alertas,
        "patron":          patron,
        "regimen_mercado": regimen_mercado,
        "timestamp":       datetime.now().isoformat(),
        "n_alertas":       len(alertas),
    }


# ── Test directo ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n⚠️ KAIROS MARKET ALERT — TEST\n" + "="*50)

    snapshot = obtener_snapshot()

    print(f"\n📊 Régimen de mercado: {snapshot['regimen_mercado']}")
    print(f"   Alertas activas: {snapshot['n_alertas']}")

    print("\n📈 Datos actuales:")
    for nombre, info in snapshot["datos"].items():
        pct   = info["cambio_pct"]
        signo = "+" if pct > 0 else ""
        flag  = " ⚠️" if abs(pct) >= UMBRALES.get(nombre, {}).get("subida", 999) else ""
        nivel = f" 🔔 NIVEL {info['nivel_roto']['nivel']}" if info.get("nivel_roto") else ""
        print(f"   {nombre:8} {info['precio']:>10}  {signo}{pct}%{flag}{nivel}")

    if snapshot["patron"]:
        print(f"\n{snapshot['patron']}")

    if snapshot["alertas"]:
        print(f"\n{'='*50}")
        print("ALERTAS GENERADAS:")
        for alerta in snapshot["alertas"]:
            print(f"\n{generar_mensaje_alerta(alerta)}")
    else:
        print("\n✓ Sin alertas — mercados dentro de rangos normales")
