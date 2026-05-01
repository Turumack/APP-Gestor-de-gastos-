"""Scraper ligero para auto-rellenar ítems de compra desde una URL.

Soporta principalmente Amazon (varios dominios), pero también funciona con
cualquier página que exponga OpenGraph (`og:title` / `og:image`) — útil
para MercadoLibre, AliExpress, Falabella, etc.

Diseñado para ser tolerante a fallos: devuelve lo que pueda extraer y
nunca lanza excepciones al consumidor (errores quedan en el log).
"""
from __future__ import annotations

import logging
import re
from html import unescape
from typing import TypedDict
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}

_TIMEOUT = 8.0
_MAX_BYTES = 1_500_000  # cap de seguridad: ~1.5 MB de HTML


class ScrapeResult(TypedDict):
    nombre: str
    imagen_url: str
    link: str
    fuente: str  # 'og', 'amazon', 'title', ''
    error: str   # vacío si todo OK


def _meta(html: str, prop_name: str, *, attr: str = "property") -> str:
    """Extrae meta[<attr>=<prop_name>] content del HTML."""
    pattern = (
        rf'<meta[^>]+{attr}=["\']{re.escape(prop_name)}["\'][^>]*'
        rf'content=["\']([^"\']+)["\']'
    )
    m = re.search(pattern, html, flags=re.IGNORECASE)
    if m:
        return unescape(m.group(1)).strip()
    # Variante con content antes que property/name
    pattern2 = (
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*{attr}=["\']{re.escape(prop_name)}["\']'
    )
    m = re.search(pattern2, html, flags=re.IGNORECASE)
    return unescape(m.group(1)).strip() if m else ""


def _title(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, flags=re.IGNORECASE)
    return unescape(m.group(1)).strip() if m else ""


def _amazon_title(html: str) -> str:
    """Amazon a veces no expone og:title; el id 'productTitle' es estable."""
    m = re.search(
        r'id=["\']productTitle["\'][^>]*>\s*([^<]+)',
        html, flags=re.IGNORECASE,
    )
    return unescape(m.group(1)).strip() if m else ""


def _amazon_image(html: str) -> str:
    """Imagen principal Amazon: <img id="landingImage" data-old-hires="..."> o src."""
    m = re.search(
        r'id=["\']landingImage["\'][^>]*data-old-hires=["\']([^"\']+)["\']',
        html, flags=re.IGNORECASE,
    )
    if m:
        return m.group(1)
    m = re.search(
        r'id=["\']landingImage["\'][^>]*src=["\']([^"\']+)["\']',
        html, flags=re.IGNORECASE,
    )
    if m:
        return m.group(1)
    # Fallback: data-a-dynamic-image (JSON con varias resoluciones)
    m = re.search(
        r'data-a-dynamic-image=["\']({[^"\']+})["\']',
        html, flags=re.IGNORECASE,
    )
    if m:
        # primera URL del JSON
        url_match = re.search(r'(https?://[^"\']+\.(?:jpg|jpeg|png|webp))', m.group(1))
        if url_match:
            return url_match.group(1)
    return ""


def _normalizar_titulo_amazon(t: str) -> str:
    """Quita prefijos típicos como 'Amazon.com: ' / 'Amazon.es: '."""
    t = re.sub(r"^Amazon\.[a-z.]+:\s*", "", t, flags=re.IGNORECASE)
    # corta en " : Amazon.com.mx: ..." y similares
    t = re.split(r"\s+:\s+Amazon\.", t, maxsplit=1, flags=re.IGNORECASE)[0]
    return t.strip()


def auto_rellenar_desde_url(url: str) -> ScrapeResult:
    """Descarga la URL y extrae nombre + imagen.

    Nunca lanza: si falla, ``error`` viene poblado y los demás campos vacíos
    (excepto ``link`` que siempre se devuelve aunque sea para que el caller
    lo guarde de todas formas).
    """
    res: ScrapeResult = {
        "nombre": "", "imagen_url": "", "link": url,
        "fuente": "", "error": "",
    }
    url = (url or "").strip()
    if not url:
        res["error"] = "URL vacía."
        return res
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
        res["link"] = url

    parsed = urlparse(url)
    if not parsed.netloc:
        res["error"] = "URL inválida."
        return res

    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, stream=True)
        r.raise_for_status()
        # Lectura limitada
        chunks: list[bytes] = []
        leidos = 0
        for chunk in r.iter_content(chunk_size=32_768):
            if not chunk:
                continue
            chunks.append(chunk)
            leidos += len(chunk)
            if leidos >= _MAX_BYTES:
                break
        html_bytes = b"".join(chunks)
        encoding = r.encoding or "utf-8"
        html = html_bytes.decode(encoding, errors="replace")
    except requests.exceptions.RequestException as e:
        log.warning("scrape: error de red para %s: %s", url, e)
        res["error"] = f"No se pudo abrir la URL ({e.__class__.__name__})."
        return res
    except Exception as e:  # noqa: BLE001
        log.exception("scrape: error inesperado")
        res["error"] = f"Error inesperado: {e}"
        return res

    es_amazon = "amazon." in parsed.netloc.lower()

    nombre = _meta(html, "og:title") or _meta(html, "twitter:title", attr="name")
    imagen = _meta(html, "og:image") or _meta(html, "twitter:image", attr="name")

    if es_amazon:
        # Amazon a veces bloquea OG; intentamos selectores de producto.
        if not nombre:
            nombre = _amazon_title(html)
        if not imagen:
            imagen = _amazon_image(html)
        nombre = _normalizar_titulo_amazon(nombre)
        res["fuente"] = "amazon" if nombre or imagen else ""

    if not nombre:
        nombre = _title(html)
        if nombre:
            res["fuente"] = res["fuente"] or "title"
    elif not res["fuente"]:
        res["fuente"] = "og"

    # Limpieza
    nombre = re.sub(r"\s+", " ", nombre).strip()
    if len(nombre) > 200:
        nombre = nombre[:197] + "…"

    res["nombre"] = nombre
    res["imagen_url"] = imagen.strip()

    if not nombre and not imagen:
        res["error"] = (
            "No se encontraron datos. La página puede requerir login "
            "o estar bloqueando el acceso."
        )
    return res
