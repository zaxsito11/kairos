import os
import requests
import xml.etree.ElementTree as ET
import re
from bs4 import BeautifulSoup

def limpiar_texto(texto):
    texto = re.sub(r'\s+', ' ', texto).strip()

    marcadores_inicio = [
        "For release at",
        "Information received",
        "Recent indicators",
        "The Committee decided",
        "Staff Review",
        "Developments in Financial Markets",
        "A staff presentation"
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


def obtener_comunicado_fed():

    url = "https://www.federalreserve.gov/feeds/press_monetary.xml"
   # Limpiar cache anterior
    if os.path.exists("data/ultimo_comunicado_fed.txt"):
        os.remove("data/ultimo_comunicado_fed.txt")

    print("📡 Conectando con la FED...")

    respuesta = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    contenido = respuesta.content.decode("utf-8", errors="ignore").strip()

    if not contenido.startswith("<"):
        contenido = contenido[contenido.index("<"):]

    root  = ET.fromstring(contenido)
    canal = root.find("channel")
    items = canal.findall("item")
    item  = items[0]

    titulo = item.find("title").text
    fecha  = item.find("pubDate").text
    link   = item.find("link").text

    print(f"✅ Comunicado: {titulo}")
    print(f"   Fecha    : {fecha}")
    print(f"   Link     : {link}")

    # Construir el link directo al HTML completo
    # El link del feed apunta a la press release
    # El documento completo tiene el mismo nombre base
    base = link.replace(".htm", "")

    # Intentar variantes del link completo
    candidatos = [
        link,
        base + "a.htm",
        base + ".htm",
    ]

    # También buscar en la página el link que dice "HTML"
    print("\n🔍 Buscando documento completo...")
    pagina_inicial = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
    soup_inicial = BeautifulSoup(pagina_inicial.content, "html.parser")

    for a in soup_inicial.find_all("a", href=True):
        href = a["href"]
        texto_link = a.get_text().strip().upper()
        if texto_link == "HTML" and "monetary" in href:
            url_completo = "https://www.federalreserve.gov" + href
            candidatos.insert(0, url_completo)
            print(f"   Encontrado link HTML: {url_completo}")
            break

    # Intentar cada candidato
    texto_limpio = ""
    for candidato in candidatos:
        try:
            print(f"   Intentando: {candidato}")
            r = requests.get(candidato, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer"]):
                    tag.decompose()
                texto_crudo = soup.get_text(separator=" ")
                texto_limpio = limpiar_texto(texto_crudo)
                if len(texto_limpio) > 1000:
                    print(f"   ✅ Documento completo obtenido ({len(texto_limpio)} caracteres)")
                    break
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    if len(texto_limpio) < 500:
        print("⚠️  Solo se obtuvo el resumen. Usando lo disponible.")

    print(f"\n--- PREVIEW (primeros 800 caracteres) ---")
    print(texto_limpio[:800])
    print(f"\n📊 Caracteres totales: {len(texto_limpio)}")

    with open("data/ultimo_comunicado_fed.txt", "w", encoding="utf-8") as f:
        f.write(f"TÍTULO: {titulo}\n")
        f.write(f"FECHA: {fecha}\n")
        f.write(f"LINK: {link}\n\n")
        f.write("=" * 60 + "\n\n")
        f.write(texto_limpio)

    print("💾 Guardado en: data/ultimo_comunicado_fed.txt")

    return {
        "titulo": titulo,
        "fecha" : fecha,
        "link"  : link,
        "texto" : texto_limpio
    }


if __name__ == "__main__":
    comunicado = obtener_comunicado_fed()