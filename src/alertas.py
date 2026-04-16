# alertas.py — KAIROS
# Sistema centralizado de envío de alertas via Telegram.
# Canal público: -1003935530360
# Admin (usuario): 1121938640

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
CANAL_ID         = os.getenv("CANAL_ID", "-1003935530360")
ADMIN_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "1121938640")

# Control de duplicados en memoria
_alertas_enviadas_sesion = set()


def enviar_mensaje(chat_id: str, texto: str) -> bool:
    """Envía un mensaje a un chat específico de Telegram."""
    if not TELEGRAM_TOKEN:
        print(f"⚠️ TELEGRAM_TOKEN no configurado")
        return False
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id":    chat_id,
            "text":       texto,
            "parse_mode": "Markdown",
        }
        r = requests.post(url, data=data, timeout=15)
        if r.status_code == 200:
            return True
        else:
            # Reintentar sin Markdown si falla el formato
            data["parse_mode"] = ""
            r2 = requests.post(url, data=data, timeout=15)
            return r2.status_code == 200
    except Exception as e:
        print(f"  Error Telegram: {e}")
        return False


def enviar_alerta_telegram(mensaje: str, canal: bool = True,
                            admin: bool = True) -> bool:
    """
    Envía alerta al canal público y/o al admin.
    Por defecto envía a ambos.
    """
    # Limitar a 4096 chars por mensaje de Telegram
    if len(mensaje) > 4096:
        mensaje = mensaje[:4090] + "..."

    exito = False
    if canal and CANAL_ID:
        ok = enviar_mensaje(CANAL_ID, mensaje)
        if ok:
            print(f"   ✅ Alerta enviada al canal KAIROS Markets")
            exito = True

    if admin and ADMIN_CHAT_ID:
        ok = enviar_mensaje(ADMIN_CHAT_ID, mensaje)
        if ok:
            print(f"   ✅ Alerta enviada al admin")

    return exito


def enviar_solo_admin(mensaje: str) -> bool:
    """Envía mensaje solo al admin (errores, debug, estado)."""
    return enviar_mensaje(ADMIN_CHAT_ID, mensaje)


def ya_enviado(clave: str) -> bool:
    """Verifica si ya se envió una alerta con esta clave en la sesión."""
    return clave in _alertas_enviadas_sesion


def marcar_enviado(clave: str):
    """Marca una alerta como enviada para no repetirla."""
    _alertas_enviadas_sesion.add(clave)
    # Limpiar si hay demasiadas claves
    if len(_alertas_enviadas_sesion) > 500:
        _alertas_enviadas_sesion.clear()


def evaluar_y_alertar(evento: dict, score: int, umbral: int = 70,
                       datos_macro: dict = None, regimen: dict = None) -> bool:
    """
    Evalúa si un evento merece alerta y la envía.

    Args:
        evento:      dict con 'titular', 'fuente', 'link', 'geo'
        score:       score de impacto del evento (0-100)
        umbral:      score mínimo para alertar (default 70)
        datos_macro: contexto macro actual
        regimen:     régimen macro actual

    Returns:
        True si se envió alerta, False si se descartó
    """
    if score < umbral:
        return False

    titular = evento.get("titular", "")
    fuente  = evento.get("fuente", "")
    link    = evento.get("link", "")
    geo     = evento.get("geo", {})

    # No repetir alertas
    clave = f"{titular[:50]}_{score}"
    if ya_enviado(clave):
        return False

    # Construir mensaje según tipo de evento
    if geo and geo.get("tipo") not in (None, "NO_CLASIFICADO"):
        impacto = geo.get("impacto", {})
        suben   = [a for a, d in impacto.items() if d["direccion"] == "SUBE"]
        bajan   = [a for a, d in impacto.items() if d["direccion"] == "BAJA"]
        tipo_geo= geo["tipo"].replace("_", " ")

        urgencia = "🚨 URGENTE" if score >= 90 else "⚠️ RELEVANTE"
        mensaje  = (
            f"{urgencia} — KAIROS ALERTA\n{'='*38}\n"
            f"📰 {titular}\n"
            f"📡 {fuente}\n"
            f"🔗 {link}\n\n"
            f"🏷️ {tipo_geo} | Score: {score}/100\n"
            f"🟢 Suben: {', '.join(suben) or 'ninguno'}\n"
            f"🔴 Bajan: {', '.join(bajan) or 'ninguno'}\n\n"
            f"kairos-markets.streamlit.app"
        )
    else:
        urgencia = "🚨" if score >= 90 else "📡"
        mensaje  = (
            f"{urgencia} KAIROS — NOTICIA RELEVANTE\n{'='*38}\n"
            f"📰 {titular}\n"
            f"📡 {fuente}\n"
            f"🔗 {link}\n"
            f"📊 Score: {score}/100\n\n"
            f"kairos-markets.streamlit.app"
        )

    # Agregar contexto macro si disponible
    if regimen:
        reg_txt = regimen.get("regimen", "")
        if reg_txt:
            mensaje += f"\n📈 Régimen actual: {reg_txt}"

    enviado = enviar_alerta_telegram(mensaje)
    if enviado:
        marcar_enviado(clave)

    return enviado


def test_conexion() -> bool:
    """Verifica que el bot de Telegram funciona."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
        r   = requests.get(url, timeout=10)
        if r.status_code == 200:
            bot = r.json()["result"]
            print(f"✅ Bot conectado: @{bot['username']}")
            return True
    except Exception as e:
        print(f"❌ Error conexión: {e}")
    return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true",
                        help="Enviar mensaje de prueba al canal")
    args = parser.parse_args()

    if test_conexion():
        if args.test:
            mensaje_test = (
                f"🧪 KAIROS — TEST DE CONEXIÓN\n"
                f"{'='*38}\n"
                f"✅ Sistema funcionando correctamente\n"
                f"📅 {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                f"kairos-markets.streamlit.app"
            )
            enviar_alerta_telegram(mensaje_test)
            print("✅ Mensaje de prueba enviado")
