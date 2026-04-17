# kairos.py — KAIROS
# Punto de entrada único del sistema.
# Ejecuta todos los módulos o solo los que necesites.

import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def banner():
    print("""
╔══════════════════════════════════════════════════╗
║                    K A I R O S                  ║
║       The intelligence between events           ║
║               and markets                       ║
╠══════════════════════════════════════════════════╣
║  Canal:  t.me/+Jk7_RXqqhAxlOGZh                ║
║  App:    kairos-markets.streamlit.app           ║
║  Web:    zaxsito11.github.io/kairos             ║
╚══════════════════════════════════════════════════╝
""")

def cmd_monitor(args):
    from monitor import run_monitor, run_test
    if args.test:
        run_test()
    else:
        run_monitor(args.intervalo)

def cmd_dashboard(args):
    import subprocess
    subprocess.run(["streamlit", "run", "src/dashboard.py"])

def cmd_brief(args):
    tipo = args.tipo.lower()
    if tipo == "morning":
        from morning_brief import generar_y_enviar_brief
        generar_y_enviar_brief(forzar=True)
    elif tipo == "closing":
        from closing_brief import generar_y_enviar_closing
        generar_y_enviar_closing(forzar=True)
    elif tipo == "weekly":
        from weekly_brief import generar_y_enviar_weekly
        generar_y_enviar_weekly(forzar=True)
    elif tipo == "event":
        from event_brief import verificar_y_enviar_event_briefs
        n = verificar_y_enviar_event_briefs()
        print(f"✅ {n} event briefs enviados")
    else:
        print(f"Tipo desconocido: {tipo}. Usa: morning | closing | weekly | event")

def cmd_targets(args):
    from price_targets      import calcular_targets_fusionados, guardar_prediccion
    from news_scanner       import SITUACIONES_ACTIVAS
    sits = [{"nombre":s["nombre"],"tipo":s["tipo"]}
            for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
    targets = calcular_targets_fusionados(
        regimen_macro="NEUTRO",
        tono_fed="HAWKISH LEVE",
        situaciones_activas=sits
    )
    from price_targets import formatear_targets_telegram
    print(formatear_targets_telegram(targets))
    guardar_prediccion(targets)

def cmd_tecnico(args):
    from analisis_tecnico import analizar_todos
    resultados = analizar_todos()
    print(f"\n{'─'*60}")
    print(f"{'Activo':8} {'Precio':>9} {'Señal':>8} {'Conf':>5} "
          f"{'RSI':>6} {'Vol':>6} {'OBV':>12} {'T-24h':>10}")
    print(f"{'─'*60}")
    for nombre, a in resultados.items():
        emoji = "▲" if a["señal"]=="ALCISTA" else "▼" if a["señal"]=="BAJISTA" else "↔"
        vol   = f"{a.get('vol_relativo',1.0):.1f}x"
        obv   = a.get("obv_tendencia","─")[:8]
        print(f"{nombre:8} {a['precio']:>9} {emoji:>8} {a['confianza']:>4}% "
              f"{a['rsi']:>6} {vol:>6} {obv:>12} {a['target_24h']:>10}")

def cmd_feedback(args):
    from feedback_sistema import (ejecutar_feedback_diario,
                                   mostrar_estadisticas_actuales)
    if args.stats:
        mostrar_estadisticas_actuales()
    else:
        ejecutar_feedback_diario(forzar=True)

def cmd_status(args):
    """Muestra el estado completo de KAIROS."""
    import json
    from datetime import datetime

    print("\n📊 KAIROS — Estado del Sistema")
    print("="*50)

    # Estado del monitor
    estado_file = "data/monitor_estado.json"
    if os.path.exists(estado_file):
        with open(estado_file) as f:
            estado = json.load(f)
        print(f"\n🤖 Monitor:")
        print(f"  Alertas enviadas: {estado.get('alertas_enviadas',0)}")
        print(f"  Última revisión:  {estado.get('ultima_revision','nunca')[:19]}")
        print(f"  Noticias vistas:  {len(estado.get('noticias_vistas',[]))}")
    else:
        print("\n⚠️ Monitor no ha corrido aún")

    # Brief de hoy
    brief_file = "data/ultimo_brief.json"
    if os.path.exists(brief_file):
        with open(brief_file) as f:
            brief = json.load(f)
        hoy = datetime.now().strftime("%Y-%m-%d")
        estado_brief = "✅ HOY" if brief.get("fecha")==hoy else f"📅 {brief.get('fecha','?')}"
        print(f"\n📊 Morning Brief: {estado_brief}")
    else:
        print("\n⚠️ Sin Morning Brief generado")

    # Estadísticas de feedback
    fb_file = "data/feedback_estadisticas.json"
    if os.path.exists(fb_file):
        with open(fb_file) as f:
            fb = json.load(f)
        print(f"\n🎯 Precisión del sistema:")
        print(f"  Total evaluaciones: {fb.get('total_evaluaciones',0)}")
        print(f"  Dirección 24h:      {fb.get('precision_dir_24h',0)}%")
        print(f"  Rango 24h:          {fb.get('precision_rango_24h',0)}%")
        print(f"  Error target avg:   {fb.get('error_target_avg',0)}%")
    else:
        print("\n⚠️ Sin datos de feedback aún (se acumula con el tiempo)")

    # Situaciones activas
    try:
        from news_scanner import SITUACIONES_ACTIVAS
        activas = [s for s in SITUACIONES_ACTIVAS if not s["resuelto"]]
        print(f"\n🌍 Situaciones activas: {len(activas)}")
        for s in activas:
            print(f"  🔴 {s['nombre']} (score: {s['score_base']})")
    except Exception:
        pass

    # Próximos eventos
    try:
        from calendario_eco import obtener_eventos_proximos
        eventos = obtener_eventos_proximos(dias=14)
        if eventos:
            print(f"\n📅 Próximos {min(3,len(eventos))} eventos:")
            for ev in eventos[:3]:
                emoji = "🚨" if ev["impacto"]=="CRÍTICO" else "⚠️"
                print(f"  {emoji} {ev['evento']} — {ev['dias_restantes']} días")
    except Exception:
        pass

    print("\n" + "="*50)


if __name__ == "__main__":
    banner()

    parser = argparse.ArgumentParser(
        description="KAIROS — Inteligencia de Mercados",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comandos disponibles:
  monitor   --test           Test de una pasada
  monitor                    Loop continuo (producción)
  dashboard                  Abrir dashboard web
  brief     --tipo morning   Generar Morning Brief
  brief     --tipo closing   Generar Closing Brief
  brief     --tipo weekly    Generar Weekly Brief
  brief     --tipo event     Verificar Event Briefs
  targets                    Calcular targets de precio
  tecnico                    Análisis técnico todos los activos
  feedback  --forzar         Evaluar aciertos
  feedback  --stats          Ver estadísticas
  status                     Estado completo del sistema
        """
    )

    subparsers = parser.add_subparsers(dest="comando")

    # Monitor
    p_mon = subparsers.add_parser("monitor")
    p_mon.add_argument("--test",      action="store_true")
    p_mon.add_argument("--intervalo", type=int, default=300)
    p_mon.set_defaults(func=cmd_monitor)

    # Dashboard
    p_dash = subparsers.add_parser("dashboard")
    p_dash.set_defaults(func=cmd_dashboard)

    # Brief
    p_brief = subparsers.add_parser("brief")
    p_brief.add_argument("--tipo", default="morning",
                         choices=["morning","closing","weekly","event"])
    p_brief.set_defaults(func=cmd_brief)

    # Targets
    p_tgt = subparsers.add_parser("targets")
    p_tgt.set_defaults(func=cmd_targets)

    # Técnico
    p_tec = subparsers.add_parser("tecnico")
    p_tec.set_defaults(func=cmd_tecnico)

    # Feedback
    p_fb = subparsers.add_parser("feedback")
    p_fb.add_argument("--forzar", action="store_true")
    p_fb.add_argument("--stats",  action="store_true")
    p_fb.set_defaults(func=cmd_feedback)

    # Status
    p_st = subparsers.add_parser("status")
    p_st.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        # Sin comando → mostrar status
        cmd_status(args)
