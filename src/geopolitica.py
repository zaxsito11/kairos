from datetime import datetime

# Base de conocimiento: tipos de eventos geopoliticos
# y su impacto historico en mercados
EVENTOS_GEOPOLITICOS = {
    "CONFLICTO_ARMADO": {
        "descripcion": "Guerra, invasion, ataque militar",
        "palabras_clave": [
    "war", "invasion", "military strike", "attack", "conflict",
    "troops", "missile", "bombing", "airstrike", "offensive",
    "military operation", "armed forces", "guerra", "invasion",
    "ataque", "conflicto", "misil", "ofensiva", "operacion militar"
],
              "impacto": {
            "WTI":    {"direccion": "SUBE",  "magnitud": "ALTA",   "razon": "Riesgo de interrupcion de suministro"},
            "Gold":   {"direccion": "SUBE",  "magnitud": "ALTA",   "razon": "Refugio seguro ante incertidumbre"},
            "DXY":    {"direccion": "SUBE",  "magnitud": "MEDIA",  "razon": "Dolar como refugio global"},
            "SPX":    {"direccion": "BAJA",  "magnitud": "MEDIA",  "razon": "Aversion al riesgo"},
            "VIX":    {"direccion": "SUBE",  "magnitud": "ALTA",   "razon": "Volatilidad disparada por incertidumbre"},
            "Defensa":{"direccion": "SUBE",  "magnitud": "ALTA",   "razon": "Aumento de gasto militar esperado"},
            "UST10Y": {"direccion": "BAJA",  "magnitud": "MEDIA",  "razon": "Bonos como refugio seguro"}
        },
        "ejemplos_historicos": [
            "Invasion Rusia a Ucrania Feb 2022: WTI +8%, Gold +3%, SPX -2.5%",
            "Ataque Hamas Oct 2023: Gold +1%, WTI +4%, VIX +30%",
            "Guerra Iraq 2003: WTI +15%, Gold +5%, SPX -5%"
        ]
    },
    "SANCION_ECONOMICA": {
        "descripcion": "Sanciones economicas a paises productores",
        "palabras_clave": [
            "sanctions", "embargo", "ban", "restrict", "freeze assets",
            "sanciones", "embargo", "restricciones", "bloqueo"
        ],
        "impacto": {
            "WTI":    {"direccion": "SUBE",  "magnitud": "ALTA",   "razon": "Restriccion de oferta energetica"},
            "Gold":   {"direccion": "SUBE",  "magnitud": "MEDIA",  "razon": "Incertidumbre economica global"},
            "DXY":    {"direccion": "SUBE",  "magnitud": "MEDIA",  "razon": "Fortaleza USD como moneda de reserva"},
            "SPX":    {"direccion": "BAJA",  "magnitud": "LEVE",   "razon": "Presion en costos de energia"},
            "EURUSD": {"direccion": "BAJA",  "magnitud": "MEDIA",  "razon": "Europa mas expuesta a energia rusa"},
            "VIX":    {"direccion": "SUBE",  "magnitud": "MEDIA",  "razon": "Incertidumbre comercial"}
        },
        "ejemplos_historicos": [
            "Sanciones Rusia Feb 2022: Gas europeo +200%, EUR/USD -8%",
            "Sanciones Iran 2018: WTI +20% en 6 meses"
        ]
    },
    "TENSION_COMERCIAL": {
        "descripcion": "Aranceles, guerras comerciales, disputas trade",
        "palabras_clave": [
            "tariff", "trade war", "import duty", "trade deal",
            "protectionism", "arancel", "guerra comercial",
            "proteccionismo", "acuerdo comercial"
        ],
        "impacto": {
            "SPX":    {"direccion": "BAJA",  "magnitud": "MEDIA",  "razon": "Cadenas de suministro afectadas"},
            "NDX":    {"direccion": "BAJA",  "magnitud": "ALTA",   "razon": "Tech muy expuesta a China"},
            "DXY":    {"direccion": "MIXTO", "magnitud": "MEDIA",  "razon": "Depende de quien impone aranceles"},
            "Gold":   {"direccion": "SUBE",  "magnitud": "LEVE",   "razon": "Refugio ante incertidumbre comercial"},
            "WTI":    {"direccion": "BAJA",  "magnitud": "LEVE",   "razon": "Menor demanda por desaceleracion global"},
            "EURUSD": {"direccion": "MIXTO", "magnitud": "MEDIA",  "razon": "Depende del impacto en exportaciones EU"}
        },
        "ejemplos_historicos": [
            "Aranceles Trump China 2018: SPX -20%, NDX -25%",
            "Acuerdo Phase 1 US-China Ene 2020: SPX +2%, NDX +3%"
        ]
    },
    "CRISIS_ENERGETICA": {
        "descripcion": "Cortes de suministro, decision OPEC, desastre energetico",
        "palabras_clave": [
            "OPEC", "oil cut", "supply cut", "pipeline", "energy crisis",
            "oil embargo", "refinery", "LNG", "natural gas",
            "recorte produccion", "crisis energetica", "gasoducto"
        ],
        "impacto": {
            "WTI":    {"direccion": "SUBE",  "magnitud": "MUY ALTA","razon": "Impacto directo en oferta de crudo"},
            "Gold":   {"direccion": "SUBE",  "magnitud": "MEDIA",   "razon": "Inflacion por energia impulsa oro"},
            "SPX":    {"direccion": "BAJA",  "magnitud": "MEDIA",   "razon": "Mayores costos para empresas"},
            "EURUSD": {"direccion": "BAJA",  "magnitud": "ALTA",    "razon": "Europa mas dependiente de energia"},
            "VIX":    {"direccion": "SUBE",  "magnitud": "MEDIA",   "razon": "Incertidumbre economica"},
            "Energia":{"direccion": "SUBE",  "magnitud": "MUY ALTA","razon": "Sector energia beneficiado directamente"}
        },
        "ejemplos_historicos": [
            "OPEC corte produccion Oct 2022: WTI +10% en semana",
            "Crisis gas Europa 2022: TTF gas +400%, EUR/USD -15%"
        ]
    },
    "INESTABILIDAD_POLITICA": {
        "descripcion": "Golpe de estado, elecciones criticas, crisis institucional",
        "palabras_clave": [
            "coup", "election", "political crisis", "government collapse",
            "default", "debt crisis", "political instability",
            "golpe", "elecciones", "crisis politica", "default"
        ],
        "impacto": {
            "Gold":   {"direccion": "SUBE",  "magnitud": "ALTA",   "razon": "Refugio ante inestabilidad"},
            "DXY":    {"direccion": "SUBE",  "magnitud": "MEDIA",  "razon": "Flujo hacia activos seguros USD"},
            "VIX":    {"direccion": "SUBE",  "magnitud": "ALTA",   "razon": "Incertidumbre politica eleva volatilidad"},
            "SPX":    {"direccion": "BAJA",  "magnitud": "LEVE",   "razon": "Cautela inversora"},
            "EM":     {"direccion": "BAJA",  "magnitud": "ALTA",   "razon": "Emergentes mas vulnerables a crisis politicas"}
        },
        "ejemplos_historicos": [
            "Brexit Jun 2016: GBP -10%, Gold +5%, VIX +50%",
            "Crisis deuda Grecia 2015: EUR/USD -5%, Gold +3%"
        ]
    },
    "ACUERDO_PAZ_COMERCIAL": {
        "descripcion": "Acuerdo de paz, cese al fuego, acuerdo comercial positivo",
        "palabras_clave": [
            "peace deal", "ceasefire", "trade agreement", "diplomatic",
            "resolution", "agreement", "acuerdo de paz", "alto al fuego",
            "acuerdo diplomatico", "normalizacion"
        ],
        "impacto": {
            "SPX":    {"direccion": "SUBE",  "magnitud": "MEDIA",  "razon": "Reduccion de incertidumbre geopolitica"},
            "Gold":   {"direccion": "BAJA",  "magnitud": "MEDIA",  "razon": "Menor demanda de refugio"},
            "WTI":    {"direccion": "BAJA",  "magnitud": "MEDIA",  "razon": "Menor prima de riesgo geopolitico"},
            "VIX":    {"direccion": "BAJA",  "magnitud": "ALTA",   "razon": "Reduccion de incertidumbre"},
            "DXY":    {"direccion": "BAJA",  "magnitud": "LEVE",   "razon": "Menor demanda de refugio en USD"}
        },
        "ejemplos_historicos": [
            "Acuerdo Abraham UAE-Israel 2020: DXY -0.5%, SPX +1%",
            "Phase 1 US-China Ene 2020: SPX +2%, VIX -15%"
        ]
    }
}


def clasificar_evento_geopolitico(texto):
    """
    Analiza un texto y determina el tipo de evento geopolitico.
    Retorna la clasificacion con mayor coincidencia.
    """

    texto_lower = texto.lower()
    scores = {}

    for tipo, config in EVENTOS_GEOPOLITICOS.items():
        score = 0
        palabras_encontradas = []

        for palabra in config["palabras_clave"]:
            if palabra.lower() in texto_lower:
                score += 1
                palabras_encontradas.append(palabra)

        if score > 0:
            scores[tipo] = {
                "score": score,
                "palabras": palabras_encontradas,
                "config": config
            }

    if not scores:
        return None

    # Retornar el tipo con mayor score
    tipo_dominante = max(scores, key=lambda x: scores[x]["score"])

    return {
        "tipo":        tipo_dominante,
        "descripcion": scores[tipo_dominante]["config"]["descripcion"],
        "score":       scores[tipo_dominante]["score"],
        "palabras":    scores[tipo_dominante]["palabras"],
        "impacto":     scores[tipo_dominante]["config"]["impacto"],
        "ejemplos":    scores[tipo_dominante]["config"]["ejemplos_historicos"]
    }


def generar_alerta_geopolitica(evento_clasificado, fuente=""):
    """
    Genera un resumen de alerta para un evento geopolitico detectado.
    """

    if not evento_clasificado:
        return None

    tipo    = evento_clasificado["tipo"]
    impacto = evento_clasificado["impacto"]

    # Separar activos que suben y bajan
    suben = [(a, d) for a, d in impacto.items() if d["direccion"] == "SUBE"]
    bajan = [(a, d) for a, d in impacto.items() if d["direccion"] == "BAJA"]

    resumen = (
        f"EVENTO GEOPOLITICO DETECTADO: {tipo}\n"
        f"Descripcion: {evento_clasificado['descripcion']}\n"
        f"Palabras clave detectadas: {', '.join(evento_clasificado['palabras'])}\n\n"
        f"IMPACTO ESPERADO EN MERCADOS:\n"
    )

    if suben:
        resumen += "SUBEN:\n"
        for activo, datos in suben:
            resumen += f"  + {activo} ({datos['magnitud']}): {datos['razon']}\n"

    if bajan:
        resumen += "BAJAN:\n"
        for activo, datos in bajan:
            resumen += f"  - {activo} ({datos['magnitud']}): {datos['razon']}\n"

    resumen += f"\nPRECEDENTES HISTORICOS:\n"
    for ejemplo in evento_clasificado["ejemplos"]:
        resumen += f"  • {ejemplo}\n"

    return resumen


def analizar_titular_geopolitico(titular):
    """
    Analiza un titular de noticias y produce analisis geopolitico.
    Funcion principal para uso desde el dashboard.
    """

    print(f"\n🌍 Analizando: {titular}")

    clasificacion = clasificar_evento_geopolitico(titular)

    if clasificacion:
        print(f"✅ Tipo detectado: {clasificacion['tipo']}")
        print(f"   Score: {clasificacion['score']} palabras coincidentes")
        alerta = generar_alerta_geopolitica(clasificacion)
        print(alerta)
        return clasificacion
    else:
        print("ℹ️  No se detectaron patrones geopoliticos relevantes.")
        return None


if __name__ == "__main__":
    # Pruebas con titulares reales
    titulares = [
        "US imposes new tariffs on Chinese goods amid trade war escalation",
        "OPEC+ announces surprise production cut of 1 million barrels per day",
        "Russia launches military offensive in eastern Ukraine",
        "US and China reach trade agreement, markets rally"
    ]

    for titular in titulares:
        analizar_titular_geopolitico(titular)
        print("-" * 60)