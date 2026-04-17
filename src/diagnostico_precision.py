# diagnostico_precision.py — KAIROS
# Analiza por qué la precisión es baja y qué hay que corregir.
# Ejecutar: python src/diagnostico_precision.py

import os, json
from datetime import datetime

print("\n🔍 KAIROS — DIAGNÓSTICO DE PRECISIÓN")
print("="*55)

# Leer historial de predicciones
targets_file = "data/price_targets_historico.json"
feedback_file = "data/feedback_estadisticas.json"

if os.path.exists(targets_file):
    with open(targets_file) as f:
        historico = json.load(f)
    print(f"\nPredicciones guardadas: {len(historico)}")
    
    evaluadas = [h for h in historico if h.get("evaluado_24h")]
    no_eval   = [h for h in historico if not h.get("evaluado_24h")]
    
    print(f"Evaluadas: {len(evaluadas)}")
    print(f"Pendientes: {len(no_eval)}")
    
    if evaluadas:
        print("\nDetalle de evaluaciones:")
        for e in evaluadas[-5:]:
            fecha = e.get("fecha_prediccion","?")
            res   = e.get("resultados_24h",{})
            aciertos = e.get("aciertos_24h", "?")
            print(f"\n  📅 {fecha} — Precisión: {aciertos}%")
            if res:
                for activo, r in list(res.items())[:4]:
                    ok = "✅" if r.get("acierto_dir") else "❌"
                    print(f"    {ok} {activo}: predicho {r.get('dir_pred','?')} | real {r.get('dir_real','?')} | cambio {r.get('cambio_pct',0):+.2f}%")

if os.path.exists(feedback_file):
    with open(feedback_file) as f:
        fb = json.load(f)
    
    print(f"\n{'='*55}")
    print("ESTADÍSTICAS GLOBALES:")
    print(f"  Precisión dirección: {fb.get('precision_dir_24h',0)}%")
    print(f"  Total evaluaciones:  {fb.get('total_evaluaciones',0)}")
    
    print("\nPor activo:")
    for activo, a in fb.get("por_activo",{}).items():
        if a["total"] > 0:
            pct = round(a["aciertos_dir"]/a["total"]*100,1)
            ok  = "✅" if pct >= 50 else "❌"
            print(f"  {ok} {activo:8}: {pct:5.1f}% ({a['aciertos_dir']}/{a['total']})")

print(f"\n{'='*55}")
print("\n📊 DIAGNÓSTICO:")
print("""
22% de precisión significa que el sistema predice INCORRECTAMENTE
la dirección la mayor parte del tiempo.

Posibles causas:
  1. Los targets/señales usan datos muy viejos de precio_ref hardcodeados
  2. El análisis técnico vs precio real no coincide por timing
  3. El mercado está en un régimen diferente al histórico (conflicto Irán)
  4. Se predicen activos muy correlacionados como independientes

Solución inmediata:
  → El feedback debe usar precios de cierre del DÍA DE LA PREDICCIÓN
    como base, no el precio del día siguiente
  → El activo más difícil de predecir en conflictos: DXY, VIX
  → Los más fáciles: Gold (refugio), WTI (Irán directo)
""")
