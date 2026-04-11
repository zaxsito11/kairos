import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_alerta_telegram(mensaje):
    """Envía un mensaje al chat de Telegram configurado."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram no configurado.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text":    mensaje,
        "parse_mode": "HTML"
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("✅ Alerta enviada a Telegram.")
            return True
        else:
            print(f"❌ Error Telegram: {r.text}")
            return False
    except Exception as e:
        print(f"❌ Error enviando alerta: {e}")
        return False


def construir_mensaje_alerta(comunicado, analisis, regimen):
    """
    Construye el mensaje de alerta para Telegram
    a partir del análisis de KAIROS.
    """

    titulo = comunicado.get("titulo", "Comunicado")
    fecha  = comunicado.get("fecha", "")

    # Extraer tono y score del análisis
    tono  = "N/A"
    score = "N/A"

    lineas = analisis.split('\n')
    for linea in lineas:
        if "Clasificacion:" in linea or "Clasificación:" in linea:
            tono = linea.split(":")[-1].strip()
        if "Score:" in linea and "Confidence" not in linea:
            score = linea.split(":")[-1].strip()

    # Emoji según tono
    emoji_tono = {
        "HAWKISH FUERTE": "🔴🔴",
        "HAWKISH LEVE":   "🔴",
        "NEUTRO":         "🟡",
        "DOVISH LEVE":    "🟢",
        "DOVISH FUERTE":  "🟢🟢"
    }
    emoji = emoji_tono.get(tono, "⚪")

    regimen_actual = regimen.get("regimen", "N/A")

    mensaje = (
        f"<b>📊 KAIROS — ALERTA DE MERCADO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Evento:</b> {titulo}\n"
        f"<b>Fecha:</b> {fecha}\n\n"
        f"<b>Tono FED:</b> {emoji} {tono}\n"
        f"<b>Score:</b> {score}\n"
        f"<b>Régimen macro:</b> {regimen_actual}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Ver análisis completo:\n"
        f"https://kairos-markets.streamlit.app"
    )

    return mensaje


def evaluar_y_alertar(comunicado, analisis, regimen):
    """
    Evalúa si el análisis merece una alerta
    y la envía si es relevante.
    """

    # Extraer score numérico
    score_num = 0
    for linea in analisis.split('\n'):
        if "Score:" in linea and "Confidence" not in linea:
            try:
                val = linea.split(":")[-1].strip()
                val = val.replace("+", "").replace("-", "")
                score_num = abs(int(val))
            except:
                pass

    # Enviar alerta si el score es significativo (>= 2)
    if score_num >= 2:
        print(f"🚨 Evento significativo detectado (score: {score_num}). Enviando alerta...")
        mensaje = construir_mensaje_alerta(comunicado, analisis, regimen)
        enviar_alerta_telegram(mensaje)
    else:
        print(f"ℹ️  Score bajo ({score_num}). No se envía alerta.")


if __name__ == "__main__":
    # Test de conexión con Telegram
    print("Probando conexión con Telegram...")
    enviar_alerta_telegram(
        "<b>🔔 KAIROS conectado</b>\n\n"
        "El sistema de alertas está funcionando correctamente.\n"
        "Recibirás notificaciones cuando haya eventos relevantes.\n\n"
        "🔗 https://kairos-markets.streamlit.app"
    )