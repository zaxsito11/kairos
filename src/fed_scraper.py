# fed_scraper.py — KAIROS
# Descarga el comunicado más reciente de la FED.
#
# CONFIABILIDAD:
# - Verifica el RSS primero (ligero) antes de re-descargar
# - Solo descarga el documento completo si hay algo genuinamente nuevo
# - Cache de 6 horas para no saturar los servidores de la FED
# - Nunca borra el cache sin verificar primero

import requests
import xml.etree.ElementTree as ET
import re
import os
import json
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime

CACHE_FILE      = "data/ultimo_comunicado_fed.txt"
CACHE_META_FILE = "data/fed_cache_meta.json"
CACHE_HORAS     = 6   # horas antes de re-verificar el RSS


# ── Limpieza de texto ─────────────────────────────────────────────
def limpiar_texto(texto):
    texto = re.sub(r'\s+', ' ', texto).strip()

    marcadores_inicio = [
        "For release at",
        "Information received",
        "Recent indicators",
        "The Committee decided",
        "Staff Review",
        "Developments in Financial Markets",
        "A staff presentation",
        "The Federal Reserve"
    ]
    for marcador in marcadores_inicio:
        if marcador in texto:
            texto = texto[texto.index(marcador):]
            break

    marcadores_fin = [
        "Last Update:",
        "Please enable JavaScript",
        "Back to Top",
        "Subscribe to RSS",
        "Notation Vote"
    ]
    for marcador in marcadores_fin:
        if marcador in texto:
            texto = texto[:texto.index(marcador)]
            break

    return texto.strip()


# ── Metadata del cache ────────────────────────────────────────────
def cargar_meta() -> dict:
    """Carga metadata del último comunicado cacheado."""
    if os.path.exists(CACHE_META_FILE):
        try:
            with open(CACHE_META_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ultima_verificacion": None, "link_actual": None, "titulo_actual": None}


def guardar_meta(meta: dict):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_META_FILE, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def cache_es_valido(meta: dict) -> bool:
    """
    El cache es válido si fue verificado hace menos de CACHE_HORAS horas.
    Esto evita re-descargar en cada ciclo del monitor.
    """
    ultima = meta.get("ultima_verificacion")
    if not ultima:
        return False
    try:
        dt = datetime.fromisoformat(ultima)
        return datetime.now() - dt < timedelta(hours=CACHE_HORAS)
    except Exception:
        return False


# ── Obtener items del RSS de la FED ──────────────────────────────
def obtener_items_rss() -> list:
    """Lee el RSS de la FED (ligero, ~5KB) para ver si hay algo nuevo."""
    feeds = ["https://www.federalreserve.gov/feeds/press_monetary.xml"]
    items = []
    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            contenido = r.content.decode("utf-8", errors="ignore").strip()
            if not contenido.startswith("<"):
                contenido = contenido[contenido.index("<"):]
            root  = ET.fromstring(contenido)
            canal = root.find("channel")
            if canal:
                items.extend(canal.findall("item"))
        except Exception as e:
            print(f"   Error en RSS FED: {e}")
    return items


# ── Descargar documento completo ──────────────────────────────────
def descargar_documento(link: str, titulo: str, fecha: str) -> dict | None:
    """
    Descarga el texto completo del comunicado desde el link del RSS.
    Solo se llama cuando hay un documento genuinamente nuevo.
    """
    print(f"\n📄 Descargando documento completo...")
    try:
        pagina = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup   = BeautifulSoup(pagina.content, "html.parser")

        # Buscar link al HTML completo (minutas tienen enlace separado)
        link_completo = None
        for a in soup.find_all("a", href=True):
            href       = a["href"]
            texto_link = a.get_text().strip().upper()
            if texto_link == "HTML" and "monetary" in href.lower():
                link_completo = "https://www.federalreserve.gov" + href
                print(f"   Documento completo: {link_completo}")
                break

        if link_completo:
            pagina = requests.get(link_completo, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup   = BeautifulSoup(pagina.content, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        texto_limpio = limpiar_texto(soup.get_text(separator=" "))
        print(f"📊 Caracteres: {len(texto_limpio)}")
        print(f"\n--- PREVIEW ---")
        print(texto_limpio[:400])

        # Guardar en cache
        os.makedirs("data", exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(f"TÍTULO: {titulo}\n")
            f.write(f"FECHA: {fecha}\n")
            f.write(f"LINK: {link}\n\n")
            f.write("=" * 60 + "\n\n")
            f.write(texto_limpio)

        print(f"\n💾 Guardado en: {CACHE_FILE}")

        return {
            "titulo":    titulo,
            "fecha":     fecha,
            "link":      link,
            "contenido": texto_limpio,
        }

    except Exception as e:
        print(f"❌ Error descargando documento: {e}")
        return None


# ── Función principal ─────────────────────────────────────────────
def obtener_comunicado_fed(forzar: bool = False) -> dict | None:
    """
    Obtiene el comunicado más reciente de la FED.

    LÓGICA:
    1. Si el cache es válido (< 6h) y no se fuerza → devuelve cache
    2. Si no → verifica RSS (ligero) para ver si hay documento nuevo
    3. Si hay documento nuevo → descarga completo y actualiza cache
    4. Si no hay nuevo → devuelve cache existente

    Args:
        forzar: si True, ignora el cache y re-descarga siempre
    """
    os.makedirs("data", exist_ok=True)
    meta = cargar_meta()

    # ── Caso 1: cache válido y no se fuerza
    if not forzar and cache_es_valido(meta) and os.path.exists(CACHE_FILE):
        print(f"📋 Usando cache FED (válido por {CACHE_HORAS}h) — {meta.get('titulo_actual','')[:60]}")
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            contenido = f.read()
        # Extraer campos del cache
        lineas = contenido.split('\n')
        titulo = lineas[0].replace("TÍTULO: ", "").strip() if lineas else ""
        fecha  = lineas[1].replace("FECHA: ", "").strip()  if len(lineas) > 1 else ""
        link   = lineas[2].replace("LINK: ", "").strip()   if len(lineas) > 2 else ""
        texto  = '\n'.join(lineas[5:]) if len(lineas) > 5 else contenido
        return {"titulo": titulo, "fecha": fecha, "link": link, "contenido": texto}

    # ── Caso 2: verificar RSS
    print("📡 Verificando RSS de la FED...")
    items = obtener_items_rss()

    if not items:
        # Si falla el RSS pero hay cache, devolver cache
        if os.path.exists(CACHE_FILE):
            print("⚠️ RSS no disponible. Usando cache anterior.")
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                contenido = f.read()
            lineas = contenido.split('\n')
            titulo = lineas[0].replace("TÍTULO: ", "").strip() if lineas else ""
            fecha  = lineas[1].replace("FECHA: ", "").strip()  if len(lineas) > 1 else ""
            link   = lineas[2].replace("LINK: ", "").strip()   if len(lineas) > 2 else ""
            texto  = '\n'.join(lineas[5:]) if len(lineas) > 5 else contenido
            return {"titulo": titulo, "fecha": fecha, "link": link, "contenido": texto}
        print("❌ Sin RSS y sin cache. No se puede obtener comunicado FED.")
        return None

    # Ordenar por fecha más reciente
    def obtener_fecha(item):
        try:
            return parsedate_to_datetime(item.find("pubDate").text)
        except Exception:
            return datetime.min

    items.sort(key=obtener_fecha, reverse=True)
    item_reciente = items[0]

    titulo = item_reciente.find("title").text
    fecha  = item_reciente.find("pubDate").text
    link   = item_reciente.find("link").text

    print(f"✅ Comunicado más reciente: {titulo}")
    print(f"   Fecha: {fecha}")

    # ── Caso 3: ¿Es genuinamente nuevo vs cache?
    if not forzar and meta.get("link_actual") == link and os.path.exists(CACHE_FILE):
        print(f"✓ Mismo documento que antes — usando cache existente")
        # Actualizar timestamp de verificación
        meta["ultima_verificacion"] = datetime.now().isoformat()
        guardar_meta(meta)
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            contenido = f.read()
        lineas = contenido.split('\n')
        texto  = '\n'.join(lineas[5:]) if len(lineas) > 5 else contenido
        return {"titulo": titulo, "fecha": fecha, "link": link, "contenido": texto}

    # ── Caso 4: documento nuevo — descargar completo
    print(f"🔴 NUEVO DOCUMENTO DETECTADO — descargando...")
    resultado = descargar_documento(link, titulo, fecha)

    if resultado:
        meta["ultima_verificacion"] = datetime.now().isoformat()
        meta["link_actual"]         = link
        meta["titulo_actual"]       = titulo
        guardar_meta(meta)

    return resultado


# ── Ejecución directa ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    forzar = "--forzar" in sys.argv
    if forzar:
        print("⚡ Modo forzar: ignorando cache\n")
    resultado = obtener_comunicado_fed(forzar=forzar)
    if resultado:
        print(f"\n✅ Comunicado obtenido: {resultado['titulo']}")
        print(f"   Caracteres: {len(resultado.get('contenido',''))}")
