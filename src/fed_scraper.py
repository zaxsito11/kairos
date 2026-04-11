import requests
import xml.etree.ElementTree as ET
import re
import os
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
from datetime import datetime

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
            idx = texto.index(marcador)
            texto = texto[idx:]
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
            idx = texto.index(marcador)
            texto = texto[:idx]
            break

    return texto.strip()


def obtener_todos_los_items():
    """Obtiene todos los items de los feeds de la FED."""

    feeds = [
        "https://www.federalreserve.gov/feeds/press_monetary.xml",
    ]

    items_totales = []

    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            contenido = r.content.decode("utf-8", errors="ignore").strip()
            if not contenido.startswith("<"):
                contenido = contenido[contenido.index("<"):]
            root  = ET.fromstring(contenido)
            canal = root.find("channel")
            if canal:
                items_totales.extend(canal.findall("item"))
        except Exception as e:
            print(f"   Error en feed: {e}")
            continue

    return items_totales


def obtener_comunicado_fed():
    """
    Descarga el comunicado más reciente de la FED.
    Prioriza statements de decisión sobre minutas.
    """

    # Limpiar cache anterior
    if os.path.exists("data/ultimo_comunicado_fed.txt"):
        os.remove("data/ultimo_comunicado_fed.txt")

    print("📡 Conectando con la FED...")

    items = obtener_todos_los_items()

    if not items:
        print("❌ No se pudieron obtener items del feed.")
        return None

    # Ordenar por fecha (más reciente primero)
    def obtener_fecha(item):
        try:
            pub = item.find("pubDate").text
            return parsedate_to_datetime(pub)
        except:
            return datetime.min

    items.sort(key=obtener_fecha, reverse=True)

    # Prioridad 1: Statement de decisión de tasas (mismo día)
    # Prioridad 2: Minutas del FOMC
    # Prioridad 3: Cualquier comunicado monetario

  # Tomar siempre el documento más reciente
    # Las minutas tienen más contenido que los statements
    item_seleccionado = items[0] if items else None

    titulo = item_seleccionado.find("title").text
    fecha  = item_seleccionado.find("pubDate").text
    link   = item_seleccionado.find("link").text

    print(f"✅ Comunicado: {titulo}")
    print(f"   Fecha    : {fecha}")
    print(f"   Link     : {link}")

    # Descargar texto completo
    print("\n📄 Descargando texto completo...")

    pagina = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
    soup   = BeautifulSoup(pagina.content, "html.parser")

    # Buscar link al HTML completo dentro de la página
    link_completo = None
    for a in soup.find_all("a", href=True):
        href       = a["href"]
        texto_link = a.get_text().strip().upper()
        if texto_link == "HTML" and "monetary" in href.lower():
            link_completo = "https://www.federalreserve.gov" + href
            print(f"   Documento completo: {link_completo}")
            break

    if link_completo:
        pagina = requests.get(link_completo, headers={"User-Agent": "Mozilla/5.0"})
        soup   = BeautifulSoup(pagina.content, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    texto_crudo  = soup.get_text(separator=" ")
    texto_limpio = limpiar_texto(texto_crudo)

    print(f"📊 Caracteres: {len(texto_limpio)}")
    print(f"\n--- PREVIEW ---")
    print(texto_limpio[:400])

    with open("data/ultimo_comunicado_fed.txt", "w", encoding="utf-8") as f:
        f.write(f"TÍTULO: {titulo}\n")
        f.write(f"FECHA: {fecha}\n")
        f.write(f"LINK: {link}\n\n")
        f.write("=" * 60 + "\n\n")
        f.write(texto_limpio)

    print(f"\n💾 Guardado en: data/ultimo_comunicado_fed.txt")

    return {
        "titulo": titulo,
        "fecha" : fecha,
        "link"  : link,
        "texto" : texto_limpio
    }


if __name__ == "__main__":
    obtener_comunicado_fed()