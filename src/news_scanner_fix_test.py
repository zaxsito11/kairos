# Test diagnóstico — por qué las noticias no llegan a Telegram
# Ejecutar: python src/news_scanner_fix_test.py

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("=== DIAGNÓSTICO: NOTICIAS → TELEGRAM ===\n")

# 1. Verificar que news_scanner detecta eventos
print("[1] Probando news_scanner...")
try:
    from news_scanner import escanear_noticias_kairos, SCORE_MINIMO_ALERTA
    estado_visto = []
    eventos = escanear_noticias_kairos(estado_visto)
    print(f"    ✅ Detectados: {len(eventos)} eventos con score≥{SCORE_MINIMO_ALERTA}")
    for e in eventos[:3]:
        print(f"    → [{e.get('score',0)}] {e.get('titular','')[:60]}")
except Exception as ex:
    print(f"    ❌ Error: {ex}")

# 2. Verificar que formatear_alerta_noticia funciona
print("\n[2] Probando formatear_alerta_noticia...")
try:
    from news_scanner import formatear_alerta_noticia
    if eventos:
        msg = formatear_alerta_noticia(eventos[0])
        print(f"    ✅ Mensaje formateado ({len(msg)} chars)")
        print(f"    Preview: {msg[:120]}...")
    else:
        print("    ⚠️ Sin eventos para formatear")
except Exception as ex:
    print(f"    ❌ Error: {ex}")

# 3. Verificar que alertas.py funciona
print("\n[3] Probando alertas.py...")
try:
    from alertas import enviar_alerta_telegram, test_conexion
    ok = test_conexion()
    if ok:
        print("    ✅ Bot conectado")
    else:
        print("    ❌ Bot no conectado")
except Exception as ex:
    print(f"    ❌ Error: {ex}")

# 4. Verificar el flujo monitor → alertas
print("\n[4] Verificando flujo en monitor.py...")
try:
    import inspect
    from monitor import escanear_noticias, procesar_evento
    src = inspect.getsource(procesar_evento)
    if 'enviar_alerta_telegram' in src:
        print("    ✅ procesar_evento llama enviar_alerta_telegram")
    else:
        print("    ❌ procesar_evento NO llama enviar_alerta_telegram")
    if 'formatear_alerta_noticia' in src:
        print("    ✅ procesar_evento usa formatear_alerta_noticia")
    else:
        print("    ❌ procesar_evento NO usa formatear_alerta_noticia")
except Exception as ex:
    print(f"    ❌ Error: {ex}")

# 5. Test envío real
print("\n[5] Enviando noticia de prueba al canal...")
if eventos:
    try:
        from news_scanner import formatear_alerta_noticia
        from alertas import enviar_alerta_telegram
        msg = formatear_alerta_noticia(eventos[0])
        ok  = enviar_alerta_telegram(msg)
        print(f"    {'✅ ENVIADO' if ok else '❌ FALLÓ'}")
    except Exception as ex:
        print(f"    ❌ Error: {ex}")
else:
    print("    ⚠️ Sin eventos disponibles para enviar")

print("\n=== FIN DIAGNÓSTICO ===")
