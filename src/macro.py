import os
from fredapi import Fred
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

fred = Fred(api_key=os.getenv("FRED_API_KEY"))

# Indicadores macro clave con sus codigos en FRED
INDICADORES = {
    "CPI": {
        "codigo": "CPIAUCSL",
        "nombre": "Inflacion CPI (YoY %)",
        "descripcion": "Indice de precios al consumidor"
    },
    "CORE_CPI": {
        "codigo": "CPILFESL",
        "nombre": "Core CPI (YoY %)",
        "descripcion": "CPI sin energia ni alimentos"
    },
    "PCE": {
        "codigo": "PCEPI",
        "nombre": "Inflacion PCE (YoY %)",
        "descripcion": "Indice preferido de la FED"
    },
    "CORE_PCE": {
        "codigo": "PCEPILFE",
        "nombre": "Core PCE (YoY %)",
        "descripcion": "PCE sin energia ni alimentos - objetivo FED"
    },
    "DESEMPLEO": {
        "codigo": "UNRATE",
        "nombre": "Tasa de Desempleo (%)",
        "descripcion": "Desempleo mensual USA"
    },
    "NFP": {
        "codigo": "PAYEMS",
        "nombre": "Nominas No Agricolas (miles)",
        "descripcion": "Creacion de empleo mensual"
    },
    "PIB": {
        "codigo": "GDP",
        "nombre": "PIB Real (QoQ %)",
        "descripcion": "Crecimiento economico trimestral"
    },
    "PMI_MANUFACTURA": {
        "codigo": "MANEMP",
        "nombre": "Empleo Manufactura",
        "descripcion": "Salud del sector manufacturero"
    },
    "TASA_FED": {
        "codigo": "FEDFUNDS",
        "nombre": "Tasa Fondos Federales (%)",
        "descripcion": "Tasa de referencia actual de la FED"
    },
    "RENDIMIENTO_10Y": {
        "codigo": "GS10",
        "nombre": "Bono Tesoro 10Y (%)",
        "descripcion": "Rendimiento bono referencia"
    },
    "RENDIMIENTO_2Y": {
        "codigo": "GS2",
        "nombre": "Bono Tesoro 2Y (%)",
        "descripcion": "Rendimiento corto plazo"
    }
}


def calcular_variacion_anual(serie):
    """Calcula la variacion porcentual anual de una serie."""
    try:
        if len(serie) >= 13:
            valor_actual  = serie.iloc[-1]
            valor_hace_1y = serie.iloc[-13]
            variacion = ((valor_actual - valor_hace_1y) / valor_hace_1y) * 100
            return round(variacion, 2)
        return None
    except:
        return None


def calcular_variacion_mensual(serie):
    """Calcula la variacion porcentual mensual."""
    try:
        if len(serie) >= 2:
            valor_actual   = serie.iloc[-1]
            valor_anterior = serie.iloc[-2]
            variacion = ((valor_actual - valor_anterior) / valor_anterior) * 100
            return round(variacion, 2)
        return None
    except:
        return None


def obtener_datos_macro():
    """
    Descarga los indicadores macro mas importantes desde FRED.
    Retorna un diccionario con valores actuales y variaciones.
    """

    print("📊 Descargando datos macro desde FRED...")

    resultados = {}
    fecha_inicio = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

    for nombre_clave, config in INDICADORES.items():
        try:
            serie = fred.get_series(
                config["codigo"],
                observation_start=fecha_inicio
            )

            if serie is None or len(serie) == 0:
                resultados[nombre_clave] = None
                continue

            valor_actual = round(float(serie.iloc[-1]), 2)
            fecha_dato   = serie.index[-1].strftime("%b %Y")

            # Calcular variaciones segun el indicador
            if nombre_clave in ["CPI", "CORE_CPI", "PCE", "CORE_PCE"]:
                variacion = calcular_variacion_anual(serie)
                tipo_var  = "YoY"
            elif nombre_clave == "NFP":
                variacion = calcular_variacion_mensual(serie)
                tipo_var  = "MoM"
                valor_actual = int(serie.iloc[-1])
            else:
                variacion = calcular_variacion_mensual(serie)
                tipo_var  = "MoM"

            resultados[nombre_clave] = {
                "nombre":      config["nombre"],
                "descripcion": config["descripcion"],
                "valor":       valor_actual,
                "variacion":   variacion,
                "tipo_var":    tipo_var,
                "fecha":       fecha_dato
            }

            print(f"   ✅ {config['nombre']}: {valor_actual} ({fecha_dato})")

        except Exception as e:
            print(f"   ⚠️  Error en {nombre_clave}: {e}")
            resultados[nombre_clave] = None

    return resultados


def evaluar_regimen_macro(datos):
    """
    Evalua el regimen macro actual basado en los datos.
    Determina si el contexto es HAWKISH, DOVISH o NEUTRO.
    """

    señales_hawkish = 0
    señales_dovish  = 0
    resumen = []

    # Evaluar inflacion
    if datos.get("CORE_PCE") and datos["CORE_PCE"]["variacion"]:
        core_pce = datos["CORE_PCE"]["variacion"]
        if core_pce > 3.0:
            señales_hawkish += 2
            resumen.append(f"Core PCE elevado: {core_pce}% (objetivo FED: 2%)")
        elif core_pce > 2.5:
            señales_hawkish += 1
            resumen.append(f"Core PCE sobre objetivo: {core_pce}%")
        elif core_pce < 2.0:
            señales_dovish += 1
            resumen.append(f"Core PCE bajo objetivo: {core_pce}%")

    # Evaluar desempleo
    if datos.get("DESEMPLEO") and datos["DESEMPLEO"]["valor"]:
        desempleo = datos["DESEMPLEO"]["valor"]
        if desempleo < 4.0:
            señales_hawkish += 1
            resumen.append(f"Mercado laboral solido: {desempleo}%")
        elif desempleo > 5.0:
            señales_dovish += 2
            resumen.append(f"Mercado laboral debil: {desempleo}%")

    # Evaluar curva de tasas (2Y vs 10Y)
    if datos.get("RENDIMIENTO_2Y") and datos.get("RENDIMIENTO_10Y"):
        r2y = datos["RENDIMIENTO_2Y"]["valor"]
        r10y = datos["RENDIMIENTO_10Y"]["valor"]
        spread = round(r10y - r2y, 2)
        if spread < 0:
            señales_dovish += 1
            resumen.append(f"Curva invertida: spread {spread}% (señal recesion)")
        else:
            resumen.append(f"Curva normal: spread {spread}%")

    # Determinar regimen
    if señales_hawkish > señales_dovish + 1:
        regimen = "HAWKISH"
        descripcion = "Contexto macro presiona hacia politica restrictiva"
    elif señales_dovish > señales_hawkish + 1:
        regimen = "DOVISH"
        descripcion = "Contexto macro presiona hacia politica expansiva"
    else:
        regimen = "NEUTRO"
        descripcion = "Contexto macro equilibrado, sin presion clara"

    return {
        "regimen":     regimen,
        "descripcion": descripcion,
        "señales":     resumen,
        "score":       señales_hawkish - señales_dovish
    }


def mostrar_macro(datos, regimen):
    """Imprime resumen de datos macro en consola."""

    print(f"\n{'='*60}")
    print(f"  CONTEXTO MACRO — {datetime.now().strftime('%d %b %Y')}")
    print(f"{'='*60}")

    categorias = {
        "INFLACION": ["CPI", "CORE_CPI", "PCE", "CORE_PCE"],
        "EMPLEO":    ["DESEMPLEO", "NFP"],
        "TASAS":     ["TASA_FED", "RENDIMIENTO_2Y", "RENDIMIENTO_10Y"]
    }

    for categoria, claves in categorias.items():
        print(f"\n  {categoria}:")
        for clave in claves:
            if datos.get(clave):
                d = datos[clave]
                print(f"    {d['nombre']:<35} {d['valor']:>8} ({d['fecha']})")

    print(f"\n  REGIMEN MACRO: {regimen['regimen']}")
    print(f"  {regimen['descripcion']}")
    for s in regimen["señales"]:
        print(f"    → {s}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    datos  = obtener_datos_macro()
    regimen = evaluar_regimen_macro(datos)
    mostrar_macro(datos, regimen)