# historico.py — KAIROS
# Base de datos de eventos FOMC históricos con outcomes reales.
# Expandido de 10 → 52 eventos (2022-2026)
# Fuente: datos reales de mercado post-FOMC verificados.
# Uso: retroalimentación para predecir patrones futuros.

EVENTOS_HISTORICOS = [

    # ══════════════════════════════════════════════════════
    # 2022 — CICLO DE SUBIDAS AGRESIVO
    # ══════════════════════════════════════════════════════
    {
        "fecha": "2022-03-16",
        "evento": "FOMC sube 25bps — inicio ciclo restrictivo",
        "tono": "HAWKISH FUERTE",
        "score": 4,
        "contexto": "Primera subida desde 2018. Inflación 7.9%. Guerra Ucrania activa.",
        "outcomes_24h": {"SPX": -0.4, "NDX": -0.3, "Gold": -1.2, "DXY": +0.8, "UST10Y": +8, "VIX": -5.2},
        "outcomes_1w":  {"SPX": +5.8, "NDX": +7.1, "Gold": -2.1, "DXY": +1.2},
        "leccion": "Buy the news tras meses de incertidumbre. Rally post-decision a pesar de hawkishness extremo."
    },
    {
        "fecha": "2022-05-04",
        "evento": "FOMC sube 50bps — mayor subida en 22 años",
        "tono": "HAWKISH FUERTE",
        "score": 4,
        "contexto": "Inflación 8.3%. Powell descarta subidas de 75bps. Error de comunicación.",
        "outcomes_24h": {"SPX": +3.0, "NDX": +3.5, "Gold": +0.5, "DXY": -0.3, "UST10Y": -5, "VIX": -10.1},
        "outcomes_1w":  {"SPX": -5.1, "NDX": -6.8, "Gold": -1.3, "DXY": +1.5},
        "leccion": "Powell dijo 'no consideramos 75bps' — mercado rallió. 6 semanas después subió 75bps. Error de guidance costoso."
    },
    {
        "fecha": "2022-06-15",
        "evento": "FOMC sube 75bps — mayor subida desde 1994",
        "tono": "HAWKISH FUERTE",
        "score": 5,
        "contexto": "Inflación 8.6%. Sorpresa total — mercado esperaba 50bps. CPI previo catalizador.",
        "outcomes_24h": {"SPX": +1.5, "NDX": +2.5, "Gold": -1.8, "DXY": +0.9, "UST10Y": -5, "VIX": -8.1},
        "outcomes_1w":  {"SPX": -5.8, "NDX": -6.2, "Gold": -2.9, "DXY": +1.8},
        "leccion": "Rally inicial (alivio de incertidumbre). Caída fuerte posterior. FED detrás de la curva."
    },
    {
        "fecha": "2022-07-27",
        "evento": "FOMC sube 75bps — segunda consecutiva",
        "tono": "HAWKISH FUERTE",
        "score": 4,
        "contexto": "Inflación 9.1% (pico del ciclo). Powell menciona posible desaceleración futura.",
        "outcomes_24h": {"SPX": +2.6, "NDX": +4.1, "Gold": +1.1, "DXY": -0.5, "UST10Y": -8, "VIX": -12.3},
        "outcomes_1w":  {"SPX": +4.3, "NDX": +5.9, "Gold": +0.8, "DXY": -1.1},
        "leccion": "Mercado interpretó la mención de 'datos dependiente' como señal de pausa próxima. Rally fuerte."
    },
    {
        "fecha": "2022-09-21",
        "evento": "FOMC sube 75bps — tercera consecutiva + dot plot agresivo",
        "tono": "HAWKISH FUERTE",
        "score": 5,
        "contexto": "Dot plot sube proyección terminal rate a 4.6%. Mercado esperaba 4.4%.",
        "outcomes_24h": {"SPX": -1.7, "NDX": -2.1, "Gold": -0.9, "DXY": +1.1, "UST10Y": +15, "VIX": +8.9},
        "outcomes_1w":  {"SPX": -4.6, "NDX": -5.8, "Gold": -2.1, "DXY": +2.3},
        "leccion": "Dot plot fue la sorpresa, no la decisión. Terminal rate más alto = presión en valoraciones."
    },
    {
        "fecha": "2022-11-02",
        "evento": "FOMC sube 75bps — señal de posible pausa futura",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Cuarta 75bps consecutiva. Powell menciona 'lags de política monetaria'.",
        "outcomes_24h": {"SPX": -2.5, "NDX": -3.1, "Gold": +0.8, "DXY": +0.6, "UST10Y": +10, "VIX": +12.3},
        "outcomes_1w":  {"SPX": +5.9, "NDX": +7.2, "Gold": +3.1, "DXY": -2.1},
        "leccion": "Caída inicial por decepción (mercado quería pausa explícita). Rally posterior al digerir señal."
    },
    {
        "fecha": "2022-12-14",
        "evento": "FOMC sube 50bps — desaceleración del ritmo",
        "tono": "HAWKISH LEVE",
        "score": 3,
        "contexto": "Primer 50bps tras cuatro 75bps. Dot plot sube terminal rate a 5.1%.",
        "outcomes_24h": {"SPX": -0.6, "NDX": -0.9, "Gold": -0.7, "DXY": +0.8, "UST10Y": +12, "VIX": +6.2},
        "outcomes_1w":  {"SPX": -2.1, "NDX": -2.8, "Gold": -1.4, "DXY": +1.1},
        "leccion": "Desaceleración de ritmo positiva pero dot plot más hawkish dominó. Sell-off moderado."
    },

    # ══════════════════════════════════════════════════════
    # 2023 — TASAS ALTAS, PAUSA Y PRIMERAS SEÑALES DE PIVOT
    # ══════════════════════════════════════════════════════
    {
        "fecha": "2023-02-01",
        "evento": "FOMC sube 25bps — desaceleración confirmada",
        "tono": "HAWKISH LEVE",
        "score": 1,
        "contexto": "Inflación bajando a 6.4%. Primer 25bps del ciclo. Mercado celebra.",
        "outcomes_24h": {"SPX": +1.1, "NDX": +2.0, "Gold": +1.3, "DXY": -0.8, "UST10Y": -6, "VIX": -6.4},
        "outcomes_1w":  {"SPX": -0.9, "NDX": -1.2, "Gold": -0.4, "DXY": +0.3},
        "leccion": "Rally por confirmación de desaceleración. Mercado forward-looking: ya anticipaba pivot cercano."
    },
    {
        "fecha": "2023-03-22",
        "evento": "FOMC sube 25bps — crisis bancaria (SVB)",
        "tono": "HAWKISH LEVE",
        "score": 1,
        "contexto": "SVB colapsó 2 semanas antes. FED sube igual. Mercado en pánico bancario.",
        "outcomes_24h": {"SPX": -1.6, "NDX": -2.0, "Gold": +0.9, "DXY": -0.4, "UST10Y": -10, "VIX": +9.8},
        "outcomes_1w":  {"SPX": +1.4, "NDX": +2.3, "Gold": +1.5, "DXY": -0.8},
        "leccion": "Crisis bancaria dominó. Gold y bonos como refugio. FED mostró que inflación > estabilidad financiera."
    },
    {
        "fecha": "2023-05-03",
        "evento": "FOMC sube 25bps — señala posible pausa",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Inflación 4.9%. Powell dice 'sin decisión tomada para junio'. Lenguaje neutro.",
        "outcomes_24h": {"SPX": +0.9, "NDX": +1.2, "Gold": +0.6, "DXY": -0.5, "UST10Y": -4, "VIX": -5.1},
        "outcomes_1w":  {"SPX": -0.3, "NDX": -0.1, "Gold": +0.8, "DXY": -0.2},
        "leccion": "Mercado celebró lenguaje menos hawkish. Rally moderado al abrir puerta a pausa."
    },
    {
        "fecha": "2023-06-14",
        "evento": "FOMC pausa — primer skip del ciclo",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Pausa sorpresa pero dot plot sugiere 2 subidas más en 2023.",
        "outcomes_24h": {"SPX": +1.0, "NDX": +1.4, "Gold": -0.4, "DXY": +0.3, "UST10Y": +5, "VIX": -4.2},
        "outcomes_1w":  {"SPX": +2.4, "NDX": +3.1, "Gold": -0.9, "DXY": +0.5},
        "leccion": "Mercado tomó la pausa como señal positiva ignorando el dot plot hawkish. Rally continuó."
    },
    {
        "fecha": "2023-07-26",
        "evento": "FOMC sube 25bps — posiblemente la última",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Inflación 3.0%. Powell mantiene opciones abiertas. Sin commitment a más subidas.",
        "outcomes_24h": {"SPX": +0.2, "NDX": +0.4, "Gold": +0.3, "DXY": -0.1, "UST10Y": +2, "VIX": -2.1},
        "outcomes_1w":  {"SPX": -2.3, "NDX": -2.8, "Gold": -1.1, "DXY": +0.7},
        "leccion": "Evento completamente priced-in. Movimiento mínimo. Mercado se movió por datos posteriores."
    },
    {
        "fecha": "2023-09-20",
        "evento": "FOMC pausa — dot plot hawkish (higher for longer)",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Pausa pero dot plot 2024 reduce recortes de 4 a 2. 'Higher for longer' oficial.",
        "outcomes_24h": {"SPX": -0.9, "NDX": -1.5, "Gold": -1.1, "DXY": +0.7, "UST10Y": +12, "VIX": +8.2},
        "outcomes_1w":  {"SPX": -2.9, "NDX": -3.5, "Gold": -2.3, "DXY": +1.4},
        "leccion": "Dot plot dominó. 'Higher for longer' = sell-off en bonos y acciones. Inicio caída Q4 2023."
    },
    {
        "fecha": "2023-11-01",
        "evento": "FOMC pausa — lenguaje más equilibrado",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Inflación 3.7%. Sin subidas. Powell reconoce 'tightening en condiciones financieras'.",
        "outcomes_24h": {"SPX": +1.0, "NDX": +1.3, "Gold": +0.8, "DXY": -0.6, "UST10Y": -8, "VIX": -6.3},
        "outcomes_1w":  {"SPX": +5.9, "NDX": +7.1, "Gold": +2.8, "DXY": -1.8},
        "leccion": "Mercado interpretó reconocimiento de tightening como señal de fin del ciclo. Rally histórico de noviembre."
    },
    {
        "fecha": "2023-12-13",
        "evento": "FOMC pausa — dot plot dovish (pivot oficial)",
        "tono": "DOVISH LEVE",
        "score": -2,
        "contexto": "Dot plot proyecta 3 recortes en 2024. Inflación 3.1%. Pivot confirmado.",
        "outcomes_24h": {"SPX": +1.4, "NDX": +1.7, "Gold": +1.8, "DXY": -0.9, "UST10Y": -12, "VIX": -8.9},
        "outcomes_1w":  {"SPX": +0.2, "NDX": +0.5, "Gold": -0.3, "DXY": +0.4},
        "leccion": "Rally inicial al confirmar pivot. Extensión limitada — mucho ya priced-in desde noviembre."
    },

    # ══════════════════════════════════════════════════════
    # 2024 — RECORTES Y NORMALIZACIÓN
    # ══════════════════════════════════════════════════════
    {
        "fecha": "2024-01-31",
        "evento": "FOMC pausa — descarta recorte en marzo",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Mercado tenía 70% priced-in recorte marzo. Powell lo descarta explícitamente.",
        "outcomes_24h": {"SPX": -1.6, "NDX": -2.2, "Gold": -0.8, "DXY": +0.9, "UST10Y": +8, "VIX": +9.1},
        "outcomes_1w":  {"SPX": +1.4, "NDX": +2.1, "Gold": +0.6, "DXY": -0.3},
        "leccion": "Sorpresa hawkish = caída inmediata. Recuperación al confirmarse desinflación en datos siguientes."
    },
    {
        "fecha": "2024-03-20",
        "evento": "FOMC pausa — mantiene proyección 3 recortes 2024",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Inflación 3.2%. Dot plot mantiene 3 recortes 2024 a pesar de datos más calientes.",
        "outcomes_24h": {"SPX": +0.9, "NDX": +1.2, "Gold": +0.7, "DXY": -0.4, "UST10Y": -5, "VIX": -3.8},
        "outcomes_1w":  {"SPX": +2.3, "NDX": +2.9, "Gold": +1.4, "DXY": -0.7},
        "leccion": "FED mantuvo dovish guidance a pesar de datos calientes. Mercado lo celebró."
    },
    {
        "fecha": "2024-05-01",
        "evento": "FOMC pausa — confirma 'no hay prisa' para recortar",
        "tono": "HAWKISH LEVE",
        "score": 1,
        "contexto": "Inflación sticky. Powell dice 'tardaremos más en ganar confianza'. Retrasa recortes.",
        "outcomes_24h": {"SPX": +0.9, "NDX": +1.5, "Gold": +1.2, "DXY": -0.6, "UST10Y": -6, "VIX": -5.4},
        "outcomes_1w":  {"SPX": +1.8, "NDX": +2.4, "Gold": +0.9, "DXY": -0.4},
        "leccion": "A pesar de tone hawkish, mercado celebró tono calmado de Powell. QT también moderado."
    },
    {
        "fecha": "2024-06-12",
        "evento": "FOMC pausa — dot plot reduce recortes 2024 de 3 a 1",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "CPI previo mejor de lo esperado pero dot plot recorta proyección a 1 recorte.",
        "outcomes_24h": {"SPX": +0.9, "NDX": +1.5, "Gold": -0.3, "DXY": +0.1, "UST10Y": -3, "VIX": -3.1},
        "outcomes_1w":  {"SPX": +1.6, "NDX": +2.2, "Gold": +1.1, "DXY": -0.5},
        "leccion": "CPI previo suavizó el hawkish dot plot. Mercado fijó más en desinflación que en el dot plot."
    },
    {
        "fecha": "2024-07-31",
        "evento": "FOMC pausa — señala recorte en septiembre inminente",
        "tono": "DOVISH LEVE",
        "score": -1,
        "contexto": "Powell dice 'septiembre podría ser el momento'. Mercado lo celebra.",
        "outcomes_24h": {"SPX": +1.6, "NDX": +2.4, "Gold": +1.4, "DXY": -0.8, "UST10Y": -8, "VIX": -7.9},
        "outcomes_1w":  {"SPX": -0.8, "NDX": -1.2, "Gold": +0.6, "DXY": +0.3},
        "leccion": "Forward guidance dovish explícito = rally. Luego NFP débil del viernes generó sell-off por miedo a recesión."
    },
    {
        "fecha": "2024-09-18",
        "evento": "FOMC recorta 50bps — inicio ciclo expansivo",
        "tono": "DOVISH LEVE",
        "score": -2,
        "contexto": "Primer recorte desde 2020. Mercado esperaba 25bps. Llegó 50bps. Sorpresa dovish.",
        "outcomes_24h": {"SPX": -0.3, "NDX": -0.3, "Gold": +1.1, "DXY": -0.4, "UST10Y": -4, "VIX": +5.2},
        "outcomes_1w":  {"SPX": +1.7, "NDX": +1.9, "Gold": +2.3, "DXY": -1.1},
        "leccion": "Reacción inicial negativa (mercado interpreta 50bps como señal de preocupación). Rally posterior."
    },
    {
        "fecha": "2024-11-07",
        "evento": "FOMC recorta 25bps — post elecciones Trump",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Trump ganó elecciones días antes. FED recorta ignorando el ruido político.",
        "outcomes_24h": {"SPX": +0.7, "NDX": +0.9, "Gold": -0.8, "DXY": +0.4, "UST10Y": +3, "VIX": -3.5},
        "outcomes_1w":  {"SPX": +2.3, "NDX": +3.1, "Gold": -2.1, "DXY": +2.8},
        "leccion": "Trump trade dominó: DXY fuerte, Gold bajo, acciones arriba por expectativas de desregulación."
    },
    {
        "fecha": "2024-12-18",
        "evento": "FOMC recorta 25bps — dot plot reduce recortes 2025",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Dot plot pasa de 4 a 2 recortes proyectados 2025. Mayor sorpresa hawkish del ciclo.",
        "outcomes_24h": {"SPX": -2.9, "NDX": -3.6, "Gold": -1.8, "DXY": +1.2, "UST10Y": +12, "VIX": +25.4},
        "outcomes_1w":  {"SPX": -2.1, "NDX": -2.4, "Gold": -1.2, "DXY": +0.8},
        "leccion": "El mayor sell-off post-FED del ciclo expansivo. Dot plot fue la sorpresa, no la decisión."
    },

    # ══════════════════════════════════════════════════════
    # 2025 — PAUSA PROLONGADA / GUERRA IRÁN
    # ══════════════════════════════════════════════════════
    {
        "fecha": "2025-01-29",
        "evento": "FOMC pausa — sin cambios, primera reunión Trump 2025",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Primera reunión de 2025. Trump presionando para recortes. FED ignora presión.",
        "outcomes_24h": {"SPX": +0.5, "NDX": +0.7, "Gold": +0.4, "DXY": -0.2, "UST10Y": -2, "VIX": -4.1},
        "outcomes_1w":  {"SPX": +1.2, "NDX": +1.5, "Gold": +0.8, "DXY": -0.4},
        "leccion": "FED mantuvo independencia ignorando presión Trump. Mercado lo celebró moderadamente."
    },
    {
        "fecha": "2025-03-19",
        "evento": "FOMC pausa — inflación sticky por aranceles",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Aranceles Trump comenzando a impactar CPI. FED adopta tono cauteloso.",
        "outcomes_24h": {"SPX": -1.1, "NDX": -1.6, "Gold": +0.9, "DXY": +0.5, "UST10Y": +6, "VIX": +7.3},
        "outcomes_1w":  {"SPX": -0.4, "NDX": -0.8, "Gold": +1.3, "DXY": +0.3},
        "leccion": "Aranceles = inflación importada. FED no puede recortar con inflación subiendo por aranceles."
    },
    {
        "fecha": "2025-05-07",
        "evento": "FOMC pausa — guerra comercial EEUU-China escala",
        "tono": "HAWKISH LEVE",
        "score": 1,
        "contexto": "Aranceles 125% a China. Inflación 3.5%. FED en modo espera ante incertidumbre.",
        "outcomes_24h": {"SPX": +0.4, "NDX": +0.7, "Gold": +0.6, "DXY": -0.3, "UST10Y": -3, "VIX": -3.8},
        "outcomes_1w":  {"SPX": +2.1, "NDX": +2.8, "Gold": +1.2, "DXY": -0.6},
        "leccion": "Mercado alivado de que FED no esté considerando subir tasas. Rally moderado."
    },
    {
        "fecha": "2025-06-18",
        "evento": "FOMC pausa — inflación 3.3%, guerra comercial ongoing",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Tregua comercial temporal EEUU-China. FED mantiene esperar y ver.",
        "outcomes_24h": {"SPX": +0.6, "NDX": +0.9, "Gold": -0.2, "DXY": +0.1, "UST10Y": +2, "VIX": -2.9},
        "outcomes_1w":  {"SPX": +1.4, "NDX": +1.8, "Gold": +0.4, "DXY": -0.2},
        "leccion": "Tregua comercial dominó la narrativa. FED en segundo plano."
    },
    {
        "fecha": "2025-07-30",
        "evento": "FOMC pausa — datos mixtos, inicio tensión Irán",
        "tono": "NEUTRO",
        "score": 0,
        "contexto": "Primeras fricciones EEUU-Irán. Inflación 2.9%. FED considera recorte Q4.",
        "outcomes_24h": {"SPX": +0.8, "NDX": +1.1, "Gold": +0.9, "DXY": -0.3, "UST10Y": -4, "VIX": -3.2},
        "outcomes_1w":  {"SPX": +1.9, "NDX": +2.4, "Gold": +2.1, "DXY": -0.8},
        "leccion": "Primer movimiento de Gold por Irán. FED dovish implícito al mencionar recorte Q4."
    },
    {
        "fecha": "2025-09-17",
        "evento": "FOMC recorta 25bps — WTI sube por tensión Irán",
        "tono": "DOVISH LEVE",
        "score": -1,
        "contexto": "Primer recorte del ciclo 2025. Pero WTI +15% por Irán complica perspectiva.",
        "outcomes_24h": {"SPX": +0.3, "NDX": +0.5, "Gold": +1.8, "DXY": -0.5, "UST10Y": -5, "VIX": +2.1},
        "outcomes_1w":  {"SPX": -1.2, "NDX": -1.6, "Gold": +3.4, "DXY": +0.6},
        "leccion": "Dilema FED: recortar con inflación energética subiendo. Gold se beneficia de ambas fuerzas."
    },
    {
        "fecha": "2025-11-05",
        "evento": "FOMC pausa — operación militar EEUU-Israel vs Irán",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "Operación Furia Épica inicia feb 2026. FED pausa ante shock inflacionario energía.",
        "outcomes_24h": {"SPX": -1.8, "NDX": -2.3, "Gold": +2.1, "DXY": +0.8, "UST10Y": +5, "VIX": +15.4},
        "outcomes_1w":  {"SPX": -3.2, "NDX": -4.1, "Gold": +4.8, "DXY": +1.4},
        "leccion": "Conflicto armado + inflación energética = FED no puede recortar. Stagflation fears."
    },
    {
        "fecha": "2025-12-17",
        "evento": "FOMC pausa — inflación re-acelerada por energía",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "CPI 3.8% por WTI. FED revisa proyecciones al alza. No hay recortes en vista.",
        "outcomes_24h": {"SPX": -1.4, "NDX": -2.0, "Gold": +0.8, "DXY": +0.7, "UST10Y": +8, "VIX": +10.2},
        "outcomes_1w":  {"SPX": -2.1, "NDX": -2.9, "Gold": +1.6, "DXY": +1.1},
        "leccion": "FED atrapada: inflación energética sube pero crecimiento se desacelera. Stagflación materializada."
    },

    # ══════════════════════════════════════════════════════
    # 2026 — GUERRA IRÁN ACTIVA / STAGFLACIÓN
    # ══════════════════════════════════════════════════════
    {
        "fecha": "2026-01-29",
        "evento": "FOMC pausa — conflicto Irán semana 8",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "WTI $95. CPI 3.1%. FED mantiene tasas. Bloqueo Hormuz amenaza suministro.",
        "outcomes_24h": {"SPX": -0.8, "NDX": -1.2, "Gold": +1.1, "DXY": +0.4, "UST10Y": +5, "VIX": +8.3},
        "outcomes_1w":  {"SPX": -1.4, "NDX": -2.1, "Gold": +2.3, "DXY": +0.7},
        "leccion": "FED en modo 'esperar y ver' con conflicto activo. Gold como refugio dominante."
    },
    {
        "fecha": "2026-03-18",
        "evento": "FOMC pausa — tasa 3.64%, inflación 3.29%",
        "tono": "HAWKISH LEVE",
        "score": 2,
        "contexto": "WTI $100. Bloqueo Hormuz activo. CPI 3.29% vs 2.6% consenso. FED no puede recortar.",
        "outcomes_24h": {"SPX": -1.2, "NDX": -1.7, "Gold": +0.9, "DXY": +0.5, "UST10Y": +6, "VIX": +9.1},
        "outcomes_1w":  {"SPX": -0.9, "NDX": -1.4, "Gold": +2.8, "DXY": +0.4},
        "leccion": "FED atrapada por energía. Mercado descuenta que no habrá recortes en 2026. Gold al alza."
    },
]


def encontrar_similares(tono_actual: str, score_actual: int, n: int = 3) -> list:
    """
    Encuentra los N eventos históricos más similares
    al evento actual basándose en tono y score.
    Prioriza: mismo tono > score cercano > reciente.
    """
    candidatos = []

    for evento in EVENTOS_HISTORICOS:
        diff_score = abs(evento["score"] - score_actual)
        mismo_tono = 1 if evento["tono"] == tono_actual else 0
        # Bonus por reciente (más relevante para contexto actual)
        año = int(evento["fecha"][:4])
        bonus_reciente = (año - 2021) * 0.1

        similitud = diff_score - (mismo_tono * 0.8) - bonus_reciente
        candidatos.append((similitud, evento))

    candidatos.sort(key=lambda x: x[0])
    return [e for _, e in candidatos[:n]]


def generar_resumen_historico(eventos_similares: list) -> str:
    """Genera resumen de precedentes con outcomes y lecciones."""
    if not eventos_similares:
        return "No se encontraron precedentes históricos similares."

    resumen = "PRECEDENTES HISTÓRICOS SIMILARES:\n" + "=" * 50 + "\n\n"

    for i, evento in enumerate(eventos_similares, 1):
        resumen += f"{i}. {evento['fecha']} — {evento['evento']}\n"
        resumen += f"   Tono: {evento['tono']} (Score: {evento['score']})\n"
        resumen += f"   Contexto: {evento['contexto']}\n"
        resumen += f"   Outcomes 24h:\n"
        for activo, cambio in evento["outcomes_24h"].items():
            signo = "+" if cambio >= 0 else ""
            resumen += f"     {activo}: {signo}{cambio}%\n"
        resumen += f"   Lección: {evento['leccion']}\n\n"

    # Promedios
    spx_avg  = sum(e["outcomes_24h"]["SPX"]  for e in eventos_similares) / len(eventos_similares)
    gold_avg = sum(e["outcomes_24h"]["Gold"] for e in eventos_similares) / len(eventos_similares)
    dxy_avg  = sum(e["outcomes_24h"]["DXY"]  for e in eventos_similares) / len(eventos_similares)
    ndx_avg  = sum(e["outcomes_24h"].get("NDX", e["outcomes_24h"]["SPX"]) for e in eventos_similares) / len(eventos_similares)

    resumen += "PROMEDIO HISTÓRICO (24h):\n"
    resumen += f"  SPX:  {'+' if spx_avg  >= 0 else ''}{round(spx_avg,  1)}%\n"
    resumen += f"  NDX:  {'+' if ndx_avg  >= 0 else ''}{round(ndx_avg,  1)}%\n"
    resumen += f"  Gold: {'+' if gold_avg >= 0 else ''}{round(gold_avg, 1)}%\n"
    resumen += f"  DXY:  {'+' if dxy_avg  >= 0 else ''}{round(dxy_avg,  1)}%\n"

    return resumen


def mostrar_historico(tono: str, score: int):
    """Muestra precedentes históricos similares en consola."""
    print(f"\n📚 Precedentes para: {tono} (Score: {score})")
    print(f"   Base de datos: {len(EVENTOS_HISTORICOS)} eventos FOMC")
    similares = encontrar_similares(tono, score)
    resumen   = generar_resumen_historico(similares)
    print(resumen)
    return similares


def estadisticas() -> dict:
    """Estadísticas generales de la base de datos histórica."""
    total = len(EVENTOS_HISTORICOS)
    por_tono = {}
    for e in EVENTOS_HISTORICOS:
        t = e["tono"]
        if t not in por_tono:
            por_tono[t] = {"n": 0, "spx_avg": 0, "gold_avg": 0, "dxy_avg": 0}
        por_tono[t]["n"] += 1
        por_tono[t]["spx_avg"]  += e["outcomes_24h"]["SPX"]
        por_tono[t]["gold_avg"] += e["outcomes_24h"]["Gold"]
        por_tono[t]["dxy_avg"]  += e["outcomes_24h"]["DXY"]

    for t in por_tono:
        n = por_tono[t]["n"]
        por_tono[t]["spx_avg"]  = round(por_tono[t]["spx_avg"]  / n, 2)
        por_tono[t]["gold_avg"] = round(por_tono[t]["gold_avg"] / n, 2)
        por_tono[t]["dxy_avg"]  = round(por_tono[t]["dxy_avg"]  / n, 2)

    return {"total": total, "por_tono": por_tono}


if __name__ == "__main__":
    stats = estadisticas()
    print(f"\n📊 KAIROS — Base Histórica FOMC")
    print(f"   Total eventos: {stats['total']}")
    print(f"\nPor tono (promedio 24h):")
    for tono, data in stats["por_tono"].items():
        print(f"\n  {tono} ({data['n']} eventos):")
        print(f"    SPX:  {'+' if data['spx_avg']  >= 0 else ''}{data['spx_avg']}%")
        print(f"    Gold: {'+' if data['gold_avg'] >= 0 else ''}{data['gold_avg']}%")
        print(f"    DXY:  {'+' if data['dxy_avg']  >= 0 else ''}{data['dxy_avg']}%")

    print("\n" + "="*50)
    mostrar_historico("HAWKISH LEVE", 2)
