import os
from fredapi import Fred
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
fred = Fred(api_key=os.getenv("FRED_API_KEY"))

# RECORDATORIO: Actualizar consenso antes de cada publicación importante
CONSENSO_ACTUAL = {
    "NFP": {
        "nombre": "Nominas No Agricolas",
        "consenso": 140,
        "unidad": "miles",
        "fecha_publicacion": "2026-05-02",
        "periodo": "Abril 2026"
    },
    "CPI_YOY": {
        "nombre": "Inflacion CPI (YoY)",
        "consenso": 2.6,
        "unidad": "%",
        "fecha_publicacion": "2026-05-13",
        "periodo": "Abril 2026"
    },
    "CORE_CPI_MOM": {
        "nombre": "Core CPI (MoM)",
        "consenso": 0.3,
        "unidad": "%",
        "fecha_publicacion": "2026-05-13",
        "periodo": "Abril 2026"
    },
    "PCE_YOY": {
        "nombre": "Inflacion PCE (YoY)",
        "consenso": 2.5,
        "unidad": "%",
        "fecha_publicacion": "2026-05-30",
        "periodo": "Abril 2026"
    },
    "DESEMPLEO": {
        "nombre": "Tasa de Desempleo",
        "consenso": 4.2,
        "unidad": "%",
        "fecha_publicacion": "2026-05-02",
        "periodo": "Abril 2026"
    }
}

CODIGOS_FRED = {
    "NFP":          "PAYEMS",
    "CPI_YOY":      "CPIAUCSL",
    "CORE_CPI_MOM": "CPILFESL",
    "PCE_YOY":      "PCEPI",
    "DESEMPLEO":    "UNRATE",
}

IMPACTO_SORPRESA = {
    "NFP": {
        "hawkish": {"razon": "Empleo fuerte → FED menos urgente en recortar → USD y acciones suben"},
        "dovish":  {"razon": "Empleo debil → FED mas urgente en recortar → bonos y oro suben"}
    },
    "CPI_YOY": {
        "hawkish": {"razon": "Inflacion alta → FED hawkish → tasas suben, acciones presionadas"},
        "dovish":  {"razon": "Inflacion baja → FED dovish → recortes mas probables"}
    },
    "CORE_CPI_MOM": {
        "hawkish": {"razon": "Core CPI alto → presion inflacionaria persistente → FED hawkish"},
        "dovish":  {"razon": "Core CPI bajo → desinflacion confirmada → recortes mas cerca"}
    },
    "DESEMPLEO": {
        "hawkish": {"razon": "Desempleo bajo → mercado laboral solido → FED no necesita recortar"},
        "dovish":  {"razon": "Desempleo alto → deterioro economico → FED necesita recortar"}
    }
}


def obtener_ultimo_dato_fred(indicador):
    """Obtiene el ultimo dato publicado de FRED y calcula la variacion correcta."""

    codigo = CODIGOS_FRED.get(indicador)
    if not codigo:
        return None

    try:
        # Para YoY necesitamos mas de 13 meses de historia
        fecha_inicio = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        serie = fred.get_series(codigo, observation_start=fecha_inicio)

        if serie is None or len(serie) == 0:
            return None

        fecha = serie.index[-1].strftime("%d %b %Y")
        val_actual = float(serie.iloc[-1])

        if indicador == "NFP":
            # PAYEMS viene en miles de personas
            valor = round(val_actual / 1000, 1)

        elif indicador == "DESEMPLEO":
            # UNRATE ya viene como porcentaje
            valor = round(val_actual, 1)

        elif indicador in ["CPI_YOY", "PCE_YOY"]:
            # Calcular variacion anual del indice
            if len(serie) >= 13:
                val_hace_1y = float(serie.iloc[-13])
                valor = round(((val_actual - val_hace_1y) / val_hace_1y) * 100, 2)
            else:
                valor = round(val_actual, 2)

        elif indicador == "CORE_CPI_MOM":
            # Calcular variacion mensual
            if len(serie) >= 2:
                val_anterior = float(serie.iloc[-2])
                valor = round(((val_actual - val_anterior) / val_anterior) * 100, 2)
            else:
                valor = round(val_actual, 2)

        else:
            valor = round(val_actual, 2)

        return {"valor": valor, "fecha": fecha}

    except Exception as e:
        print(f"   Error obteniendo {indicador}: {e}")
        return None


def calcular_sorpresa_dato(indicador, valor_real):
    """Calcula la sorpresa de un dato macro vs su consenso."""

    if indicador not in CONSENSO_ACTUAL:
        return None

    config   = CONSENSO_ACTUAL[indicador]
    consenso = config["consenso"]

    diferencia     = valor_real - consenso
    diferencia_pct = (diferencia / abs(consenso)) * 100 if consenso != 0 else 0

    # Para desempleo: mas alto = mas dovish
    if indicador == "DESEMPLEO":
        diferencia     = -diferencia
        diferencia_pct = -diferencia_pct

    abs_pct = abs(diferencia_pct)

    if abs_pct > 15:
        nivel = "SORPRESA ALTA"
        emoji = "🚨"
    elif abs_pct > 7:
        nivel = "SORPRESA MODERADA"
        emoji = "⚠️"
    elif abs_pct > 3:
        nivel = "SORPRESA LEVE"
        emoji = "📊"
    else:
        nivel = "EN LINEA CON CONSENSO"
        emoji = "✅"

    direccion = "HAWKISH" if diferencia > 0 else "DOVISH"

    return {
        "indicador":      indicador,
        "nombre":         config["nombre"],
        "consenso":       consenso,
        "real":           valor_real,
        "diferencia":     round(diferencia, 2),
        "diferencia_pct": round(diferencia_pct, 1),
        "nivel":          nivel,
        "emoji":          emoji,
        "direccion":      direccion,
        "unidad":         config["unidad"],
        "periodo":        config["periodo"],
        "impacto":        IMPACTO_SORPRESA.get(indicador, {}).get(
                              direccion.lower(), {}
                          )
    }


def analizar_sorpresas_recientes():
    """Analiza las sorpresas de los datos macro mas recientes."""

    print("📊 Analizando sorpresas de datos macro...")
    print("⚠️  RECORDATORIO: Actualizar CONSENSO_ACTUAL antes de cada publicacion")
    print()

    resultados = []

    for indicador in ["NFP", "DESEMPLEO", "CPI_YOY", "CORE_CPI_MOM"]:
        dato = obtener_ultimo_dato_fred(indicador)

        if dato:
            sorpresa = calcular_sorpresa_dato(indicador, dato["valor"])
            if sorpresa:
                sorpresa["fecha_dato"] = dato["fecha"]
                resultados.append(sorpresa)

                print(f"{sorpresa['emoji']} {sorpresa['nombre']}")
                print(f"   Consenso : {sorpresa['consenso']} {sorpresa['unidad']}")
                print(f"   Real     : {sorpresa['real']} {sorpresa['unidad']} ({dato['fecha']})")
                signo = "+" if sorpresa["diferencia"] > 0 else ""
                print(f"   Sorpresa : {signo}{sorpresa['diferencia']} → {sorpresa['nivel']} {sorpresa['direccion']}")
                if sorpresa["impacto"]:
                    print(f"   Impacto  : {sorpresa['impacto'].get('razon', '')}")
                print()

    return resultados


def generar_resumen_macro_sorpresas(resultados):
    """Genera resumen del sesgo de sorpresas macro."""

    if not resultados:
        return "Sin datos disponibles."

    hawkish = sum(1 for r in resultados if r["direccion"] == "HAWKISH")
    dovish  = sum(1 for r in resultados if r["direccion"] == "DOVISH")

    if hawkish > dovish:
        sesgo = "HAWKISH"
        desc  = "Datos sorprenden al alza, apoyando FED menos dovish"
    elif dovish > hawkish:
        sesgo = "DOVISH"
        desc  = "Datos sorprenden a la baja, apoyando recortes de tasas"
    else:
        sesgo = "MIXTO"
        desc  = "Datos mixtos sin sesgo claro"

    resumen  = f"Sesgo macro: {sesgo} — {desc}\n"
    resumen += f"Hawkish: {hawkish} | Dovish: {dovish}\n\n"

    for r in resultados:
        signo = "+" if r["diferencia"] > 0 else ""
        resumen += f"{r['emoji']} {r['nombre']}: {r['real']} vs {r['consenso']} → {r['nivel']} {r['direccion']}\n"

    return resumen


if __name__ == "__main__":
    resultados = analizar_sorpresas_recientes()
    print("=" * 60)
    print(generar_resumen_macro_sorpresas(resultados))