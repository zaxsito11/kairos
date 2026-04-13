# alertas.py — KAIROS
# Envía alertas a Telegram:
#   1. Al canal público KAIROS Markets (todos los suscriptores)
#   2. Al chat personal del admin (tú)

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")   # tu chat personal (admin)
CANAL_ID         = "-1003935530360"                  # canal KAIROS Markets


def enviar_mensaje(chat_id: str, mensaje: str) -> bool:
    """Envía un mensaje a un chat o canal específico."""
    if not TELEGRAM_TOKEN:
        print("⚠️ TELEGRAM_TOKEN no configurado")
        return False

    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id":    chat_id,
            "text":       mensaje,
            "parse_mode": "HTML",
        }
        r = requests.post(url, data=data, timeout=10)

        if r.status_code == 200:
            return True
        else:
            # Intentar sin parse_mode si hay error de formato
            data.pop("parse_mode")
            r2 = requests.post(url, data=data, timeout=10)
            return r2.status_code == 200

    except Exception as e:
        print(f"  Error enviando Telegram a {chat_id}: {e}")
        return False


def enviar_alerta_telegram(mensaje: str, solo_admin: bool = False):
    """
    Función principal de alertas KAIROS.

    Por defecto envía:
    - Al canal público (todos los suscriptores)
    - Al chat personal del admin

    Args:
        mensaje:     Texto de la alerta
        solo_admin:  Si True, solo envía al admin (para mensajes internos)
    """
    if not TELEGRAM_TOKEN:
        print("⚠️ Sin token Telegram — alerta no enviada")
        return

    # ── Enviar al canal público ───────────────────────────────────
    if not solo_admin:
        ok_canal = enviar_mensaje(CANAL_ID, mensaje)
        if ok_canal:
            print("  ✅ Alerta enviada al canal KAIROS Markets")
        else:
            print("  ⚠️ Error enviando al canal")

    # ── Enviar al admin (chat personal) ───────────────────────────
    if TELEGRAM_CHAT_ID:
        ok_admin = enviar_mensaje(TELEGRAM_CHAT_ID, mensaje)
        if ok_admin:
            print("  ✅ Alerta enviada al admin")
        else:
            print("  ⚠️ Error enviando al admin")


def enviar_alerta_admin(mensaje: str):
    """
    Envía solo al admin — para logs internos y errores del sistema.
    Los suscriptores del canal NO lo ven.
    """
    enviar_alerta_telegram(mensaje, solo_admin=True)


def test_conexion():
    """Verifica que el bot puede enviar al canal y al admin."""
    print("\n🧪 Test de conexión Telegram\n" + "="*40)

    msg_test = (
        "🟢 KAIROS — Sistema activo\n"
        "{'='*38}\n"
        "✅ Bot conectado correctamente\n"
        "✅ Canal: KAIROS Markets\n"
        "📊 Monitor iniciado\n\n"
        "kairos-markets.streamlit.app"
    )

    print("Enviando al canal público...")
    ok_canal = enviar_mensaje(CANAL_ID, msg_test)
    print(f"  Canal: {'✅ OK' if ok_canal else '❌ Error'}")

    if TELEGRAM_CHAT_ID:
        print("Enviando al admin...")
        ok_admin = enviar_mensaje(TELEGRAM_CHAT_ID, msg_test)
        print(f"  Admin: {'✅ OK' if ok_admin else '❌ Error'}")

    return ok_canal


if __name__ == "__main__":
    test_conexion()
