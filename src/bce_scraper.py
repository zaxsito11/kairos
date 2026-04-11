import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

def obtener_comunicado_bce():
    """
    Descarga la decision de politica monetaria mas reciente del BCE
    usando su feed RSS oficial.
    """

    print("📡 Conectando con el BCE...")

    # Feed RSS oficial del BCE - comunicados de prensa
    rss_url = "https://www.ecb.europa.eu/rss/press.html"

    respuesta = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})

    soup = BeautifulSoup(respuesta.content, "html.parser")
    items = soup.find_all("item")

    # Buscar el primer item relacionado con politica monetaria
    primer_link   = None
    primer_titulo = None
    primer_fecha  = None

    palabras_clave = [
        "monetary policy",
        "interest rate",
        "key ecb rates",
        "governing council",
        "press conference"
    ]

    for item in items:
        titulo = item.find("title")
        link   = item.find("link")
        fecha  = item.find("pubDate")

        if titulo and link:
            titulo_texto = titulo.get_text().lower()
            link_texto = link.get_text().strip()
            if any(palabra in titulo_texto for palabra in palabras_clave) and not link_texto.endswith(".pdf"):
                primer_titulo = titulo.get_text().strip()
                primer_link   = link_texto
                primer_fecha  = fecha.get_text().strip() if fecha else datetime.now().strftime("%d %B %Y")
                break

    # Si no encontramos nada en RSS, usar pagina de decisiones
    if not primer_link:
        print("   Buscando en pagina de decisiones...")
        url_decisiones = "https://www.ecb.europa.eu/press/govcdec/mopo/2026/html/index.en.html"
        r = requests.get(url_decisiones, headers={"User-Agent": "Mozilla/5.0"})
        soup2 = BeautifulSoup(r.content, "html.parser")

        for a in soup2.find_all("a", href=True):
            href = a["href"]
            if ".en.html" in href and "govcdec" in href:
                primer_titulo = a.get_text().strip()
                primer_link   = "https://www.ecb.europa.eu" + href if not href.startswith("http") else href
                primer_fecha  = datetime.now().strftime("%d %B %Y")
                break

    # Ultimo recurso: link directo a la conferencia mas reciente conocida
    if not primer_link:
        print("   Usando comunicado conocido mas reciente...")
        primer_link   = "https://www.ecb.europa.eu/press/pressconf/2025/html/ecb.is250130~c43a2b7131.en.html"
        primer_titulo = "ECB Monetary Policy Press Conference January 2025"
        primer_fecha  = "30 January 2025"

    print(f"✅ Comunicado: {primer_titulo}")
    print(f"   Fecha     : {primer_fecha}")
    print(f"   Link      : {primer_link}")

    # Descargar texto
    print("\n📄 Descargando texto completo...")
    pagina = requests.get(primer_link, headers={"User-Agent": "Mozilla/5.0"})
    soup3  = BeautifulSoup(pagina.content, "html.parser")

    for tag in soup3(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    texto_crudo  = soup3.get_text(separator=" ")
    texto_limpio = re.sub(r'\s+', ' ', texto_crudo).strip()

    # Encontrar inicio real del contenido
    marcadores_inicio = [
        "The Governing Council",
        "At today",
        "Good afternoon",
        "Monetary policy decisions",
        "The ECB"
    ]

    for marcador in marcadores_inicio:
        if marcador in texto_limpio:
            idx = texto_limpio.index(marcador)
            texto_limpio = texto_limpio[idx:]
            break

    print(f"📊 Caracteres: {len(texto_limpio)}")

    if len(texto_limpio) < 300:
        print("❌ No se pudo obtener contenido suficiente del BCE.")
        return None

    with open("data/ultimo_comunicado_bce.txt", "w", encoding="utf-8") as f:
        f.write(f"TITULO: {primer_titulo}\n")
        f.write(f"FECHA: {primer_fecha}\n")
        f.write(f"LINK: {primer_link}\n\n")
        f.write("=" * 60 + "\n\n")
        f.write(texto_limpio)

    print("💾 Guardado en: data/ultimo_comunicado_bce.txt")
    print(f"\n--- PREVIEW ---")
    print(texto_limpio[:400])

    return {
        "titulo": primer_titulo,
        "fecha":  primer_fecha,
        "link":   primer_link,
        "texto":  texto_limpio,
        "fuente": "BCE"
    }


if __name__ == "__main__":
    obtener_comunicado_bce()