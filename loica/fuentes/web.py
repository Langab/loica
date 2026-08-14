"""Adaptadores para RSS/sitemaps y para HTML suelto.

El adaptador HTML es deliberadamente conservador: solo saca hechos (título,
fecha, precio, link). Si el sitio cambia su maquetación, devuelve menos
eventos, pero no inventa ninguno.
"""

from __future__ import annotations

import logging
import re
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from ..modelo import Evento, es_enlace_de_maquina
from ..normalizar import (detectar_comuna, limpiar_html, parsear_fecha,
                          parsear_precio, resumir)
from ..red import ClienteEducado

log = logging.getLogger("loica.web")

# Datos estructurados: muchos sitios ya publican sus eventos en JSON-LD
# (schema.org/Event). Cuando existe, es la mejor fuente posible de un HTML.
def _desde_jsonld(sopa: BeautifulSoup, fuente: dict) -> list[Evento]:
    import json

    eventos: list[Evento] = []
    for etiqueta in sopa.find_all("script", type="application/ld+json"):
        try:
            # strict=False tolera saltos de línea crudos dentro de un string,
            # que el JSON estricto prohíbe. No es un detalle: Ticketplus mete
            # la descripción del evento con sus saltos tal cual, y su bloque
            # schema.org/Event —el único con fecha y lugar— se descartaba
            # entero mientras el bloque Product de al lado sí parseaba.
            datos = json.loads(etiqueta.string or "", strict=False)
        except (ValueError, TypeError):
            continue

        candidatos = datos if isinstance(datos, list) else [datos]
        if isinstance(datos, dict) and "@graph" in datos:
            candidatos = datos["@graph"]

        for item in candidatos:
            if not isinstance(item, dict):
                continue
            tipo = item.get("@type", "")
            tipos = tipo if isinstance(tipo, list) else [tipo]
            if not any("Event" in str(t) for t in tipos):
                continue

            lugar = item.get("location") or {}
            nombre_lugar = ""
            direccion = ""
            if isinstance(lugar, dict):
                nombre_lugar = str(lugar.get("name", ""))
                dir_obj = lugar.get("address")
                if isinstance(dir_obj, dict):
                    partes = [dir_obj.get("streetAddress", ""), dir_obj.get("addressLocality", "")]
                    direccion = ", ".join(p for p in partes if p)
                elif isinstance(dir_obj, str):
                    direccion = dir_obj

            ofertas = item.get("offers") or {}
            if isinstance(ofertas, list):
                ofertas = ofertas[0] if ofertas else {}
            # AggregateOffer (varios tipos de entrada) trae lowPrice en vez de price
            precio_crudo = ""
            if isinstance(ofertas, dict):
                for campo in ("price", "lowPrice"):
                    if ofertas.get(campo) not in (None, ""):
                        precio_crudo = str(ofertas[campo])
                        break
            precio, gratis, texto_precio = parsear_precio(precio_crudo)
            if precio_crudo.strip() in ("0", "0.0", "0.00"):
                precio, gratis = 0, True
            elif precio is None and precio_crudo:
                try:
                    valor = int(float(precio_crudo))
                    if 0 < valor <= 2_000_000:
                        precio, gratis = valor, False
                        texto_precio = f"desde ${valor:,.0f}".replace(",", ".")
                except ValueError:
                    pass

            # Coordenadas: schema.org las pone en location.geo
            lat = lon = None
            geo = lugar.get("geo") if isinstance(lugar, dict) else None
            if isinstance(geo, dict):
                try:
                    lat, lon = float(geo.get("latitude")), float(geo.get("longitude"))
                except (TypeError, ValueError):
                    lat = lon = None

            imagen = item.get("image")
            if isinstance(imagen, list):
                imagen = imagen[0] if imagen else ""

            # El link sale SOLO del JSON-LD, y puede venir relativo. Si el sitio
            # no lo declara (Toliv no lo hace) se deja vacío a propósito: quien
            # llama sabe de qué página salió el evento y pone esa. Rellenar acá
            # con `url_agenda` mandaba a todos los eventos al sitemap.
            enlace = str(item.get("url", "")).strip()
            if enlace.startswith("//"):
                enlace = "https:" + enlace
            elif enlace.startswith("/"):
                enlace = fuente["url_base"].rstrip("/") + enlace

            eventos.append(Evento(
                titulo=limpiar_html(str(item.get("name", ""))),
                descripcion_corta=resumir(str(item.get("description", ""))),
                inicio=parsear_fecha(str(item.get("startDate", ""))),
                fin=parsear_fecha(str(item.get("endDate", ""))),
                lugar_nombre=nombre_lugar or fuente.get("nombre", ""),
                lugar_direccion=direccion,
                comuna=detectar_comuna(direccion, nombre_lugar, fuente.get("comuna", "")),
                lat=lat, lon=lon,
                precio_clp=precio,
                es_gratis=gratis,
                precio_texto=texto_precio,
                fuente_tipo="html",
                fuente_nombre=fuente.get("nombre", ""),
                fuente_url=enlace,
                imagen_url=str(imagen or ""),
            ))
    return eventos


def eventos_desde_html(html: str, fuente: dict, tipo: str = "html") -> list[Evento]:
    """Extrae eventos de un HTML: primero JSON-LD, si no, tarjetas con selectores."""
    sopa = BeautifulSoup(html, "html.parser")

    eventos = _desde_jsonld(sopa, fuente)
    if eventos:
        # Acá el evento se leyó de la agenda misma, así que cuando el JSON-LD no
        # trae link propio, mandar a la agenda es honesto: es una página que la
        # persona puede leer. (No así un sitemap: para eso está el guardia.)
        agenda = fuente.get("url_agenda", "")
        if agenda and not es_enlace_de_maquina(agenda):
            for e in eventos:
                e.fuente_url = e.fuente_url or agenda
        log.info("%s: %d eventos vía JSON-LD", fuente.get("nombre"), len(eventos))
        return eventos

    selectores = fuente.get("selectores") or {}
    selector_tarjeta = selectores.get("tarjeta")
    if not selector_tarjeta:
        # Heurística: contenedores que suelen envolver un evento. `[data-date]`
        # va primero porque cuando existe trae la fecha ya en formato ISO.
        for candidato in ("[data-date]", "article.evento", ".evento", ".event",
                          ".eventon_list_event", "article.event", ".card-evento",
                          ".agenda-item"):
            if sopa.select(candidato):
                selector_tarjeta = candidato
                break
    if not selector_tarjeta:
        log.warning("%s: no encontré tarjetas de evento en el HTML", fuente.get("nombre"))
        return []

    # Atributo del que sacar la fecha (ej. GAM usa data-date="2026-08-01")
    atributo_fecha = selectores.get("atributo_fecha", "data-date")

    base = fuente["url_base"].rstrip("/")
    for tarjeta in sopa.select(selector_tarjeta)[:120]:
        texto = tarjeta.get_text(" ", strip=True)

        nodo_titulo = (tarjeta.select_one(selectores["titulo"]) if selectores.get("titulo")
                       else tarjeta.find(["h1", "h2", "h3", "h4"]))
        titulo = limpiar_html(nodo_titulo.get_text(" ", strip=True)) if nodo_titulo else ""
        if not titulo:
            continue

        enlace = (tarjeta.select_one(selectores["link"]) if selectores.get("link")
                  else tarjeta.find("a", href=True))
        url = enlace.get("href", "") if enlace else ""
        # "//teatromori.com/obra/..." es una URL sin esquema, no una ruta: si se
        # le pega el dominio delante queda https://teatromori.com//teatromori.com/...
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = base + url

        # Fecha: atributo del HTML > selector configurado > texto de la tarjeta
        inicio = None
        fin = None
        valor_atributo = tarjeta.get(atributo_fecha) if atributo_fecha else None
        if valor_atributo:
            inicio = parsear_fecha(str(valor_atributo))
        if inicio is None:
            nodo_fecha = (tarjeta.select_one(selectores["fecha"])
                          if selectores.get("fecha") else None)
            texto_fecha = nodo_fecha.get_text(" ", strip=True) if nodo_fecha else texto
            inicio = parsear_fecha(texto_fecha)
            # "18 Julio, 2026 - 27 Septiembre, 2026": la segunda fecha es el
            # término. Sin ella una exposición que ya abrió no se publica nunca,
            # porque la vigencia se mide por la fecha de término (SQL_VIGENTE).
            # Solo se lee del selector de fecha: en el texto suelto de una
            # tarjeta cualquier número con mes de por medio pasaría por rango.
            if inicio is not None and nodo_fecha:
                tramos = re.split(r"\s*[-–—]\s*|\s+al\s+|\s+hasta\s+", texto_fecha, maxsplit=1)
                if len(tramos) == 2:
                    posible = parsear_fecha(tramos[1])
                    if posible and posible >= inicio:
                        fin = posible
        if inicio is None:
            continue

        categoria = ""
        nodo_categoria = (tarjeta.select_one(selectores["categoria"])
                          if selectores.get("categoria") else tarjeta.find("small"))
        if nodo_categoria:
            categoria = limpiar_html(nodo_categoria.get_text(" ", strip=True))[:40]

        precio, gratis, texto_precio = parsear_precio(texto)

        # Un mismo sitio puede cubrir varias salas y distinguirlas solo por una
        # clase CSS de la tarjeta (Teatro Mori marca sala-1 … sala-5, y la
        # comuna cambia entre Las Condes, Providencia, Vitacura y Recoleta).
        lugar = fuente.get("nombre", "")
        comuna_tarjeta = ""
        mapa_salas = selectores.get("salas_por_clase") or {}
        if mapa_salas:
            for clase in (tarjeta.get("class") or []):
                if clase in mapa_salas:
                    sala = mapa_salas[clase] or {}
                    lugar = sala.get("lugar", lugar)
                    comuna_tarjeta = sala.get("comuna", "")
                    break

        # Otras veces la sede no está en una clase sino escrita en la tarjeta:
        # el MAC pone "MAC Quinta Normal - 6 y 7" o "MAC Parque Forestal - 7 y 8"
        # en un <p>, y sus dos sedes quedan a 4 km. Con el nombre de la sede en
        # `lugar_nombre`, la memoria de correcciones les pone su pin a cada una
        # y detectar_comuna saca la comuna del mismo texto.
        if selectores.get("lugar"):
            nodo_lugar = tarjeta.select_one(selectores["lugar"])
            if nodo_lugar:
                lugar = limpiar_html(nodo_lugar.get_text(" ", strip=True))[:120] or lugar

        eventos.append(Evento(
            titulo=titulo,
            categoria=categoria,
            descripcion_corta=resumir(texto, 150),
            inicio=inicio,
            fin=fin,
            lugar_nombre=lugar,
            comuna=detectar_comuna(comuna_tarjeta, texto, fuente.get("comuna", "")),
            precio_clp=precio,
            es_gratis=gratis,
            precio_texto=texto_precio,
            fuente_tipo=tipo,
            fuente_nombre=fuente.get("nombre", ""),
            fuente_url=url or fuente.get("url_agenda", ""),
        ))

    log.info("%s: %d eventos vía HTML (%s)", fuente.get("nombre"), len(eventos), selector_tarjeta)
    return eventos


def extraer_html(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    url = fuente.get("url_agenda") or (fuente["url_base"].rstrip("/") + fuente.get("endpoint", ""))
    respuesta = cliente.obtener(url)
    if respuesta is None or not respuesta.ok:
        return []
    return eventos_desde_html(respuesta.text, fuente)


def _urls_desde_listado(fuente: dict, cliente: ClienteEducado) -> list[tuple[str, str]]:
    """Saca los links de evento de una página de listado HTML.

    Para sitios que no publican sus eventos en el sitemap (PortalTickets, por
    ejemplo, tiene un sitemap de 6 URLs y toda su cartelera en una sola página).
    """
    base = fuente["url_base"].rstrip("/")
    url = fuente.get("url_agenda") or (base + fuente.get("endpoint", "/"))
    respuesta = cliente.obtener(url, max_edad_cache_seg=3 * 3600)
    if respuesta is None or not respuesta.ok:
        log.warning("%s: no pude leer el listado", fuente.get("nombre"))
        return []

    patron = fuente.get("patron_url", "")
    # Algunos sitios no tienen un prefijo común para sus eventos: Puntoticket
    # publica /cumbre-guachaca-2026 al mismo nivel que /login y /giftcard. Ahí
    # el filtro útil es por descarte, no por patrón.
    excluir = [e.lower() for e in (fuente.get("excluir_url") or [])]

    sopa = BeautifulSoup(respuesta.text, "html.parser")
    vistas: dict[str, str] = {}
    for enlace in sopa.find_all("a", href=True):
        href = enlace["href"]
        if patron and patron not in href:
            continue
        if href.startswith("/"):
            href = base + href
        elif not href.startswith("http"):
            continue
        limpia = href.split("?")[0].rstrip("/")
        if any(trozo in limpia.lower() for trozo in excluir):
            continue
        # Solo fichas: la home y las secciones no son eventos.
        if limpia == base or limpia.count("/") < 3:
            continue
        vistas.setdefault(limpia, "")
    return list(vistas.items())


def extraer_sitemap_fichas(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    """Descubre las URLs de los eventos y saca los datos de cada ficha.

    Es el patrón más común en sitios modernos: el listado (sitemap o página)
    solo entrega links; la fecha, el lugar y el precio están en la ficha,
    a veces como JSON-LD (schema.org/Event) y a veces solo en el texto.

    `origen: listado` en la configuración cambia el sitemap por una página HTML.
    """
    base = fuente["url_base"].rstrip("/")

    if fuente.get("origen") == "rss":
        # El feed entrega los links pero no los datos: la fecha vive en la ficha
        # (Feria Friki es el caso: describe "Fecha / Horario / Dirección" ahí).
        url_feed = fuente.get("url_agenda") or (base + fuente.get("endpoint", "/feed/"))
        respuesta = cliente.obtener(url_feed, max_edad_cache_seg=3 * 3600)
        entradas = []
        if respuesta is not None and respuesta.ok:
            try:
                raiz = ElementTree.fromstring(respuesta.content)
                for item in raiz.findall(".//item"):
                    enlace = item.find("link")
                    fecha = item.find("pubDate")
                    if enlace is not None and enlace.text:
                        entradas.append((enlace.text.strip(),
                                         (fecha.text or "") if fecha is not None else ""))
            except ElementTree.ParseError:
                log.warning("%s: feed ilegible", fuente.get("nombre"))
    elif fuente.get("origen") == "listado":
        entradas = _urls_desde_listado(fuente, cliente)
    else:
        url_mapa = fuente.get("url_agenda") or (base + fuente.get("endpoint", "/sitemap.xml"))
        respuesta = cliente.obtener(url_mapa, max_edad_cache_seg=6 * 3600)
        if respuesta is None or not respuesta.ok:
            log.warning("%s: no pude leer el sitemap", fuente.get("nombre"))
            return []

        try:
            raiz = ElementTree.fromstring(respuesta.content)
        except ElementTree.ParseError:
            log.warning("%s: sitemap ilegible", fuente.get("nombre"))
            return []

        espacios = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        entradas = []
        for nodo in raiz.findall(".//s:url", espacios) or raiz.findall(".//url"):
            loc = nodo.find("s:loc", espacios) if nodo.find("s:loc", espacios) is not None else nodo.find("loc")
            if loc is None or not loc.text:
                continue
            mod = nodo.find("s:lastmod", espacios) if nodo.find("s:lastmod", espacios) is not None else nodo.find("lastmod")
            entradas.append((loc.text.strip(), (mod.text or "") if mod is not None else ""))

        patron = fuente.get("patron_url", "")
        if patron:
            entradas = [e for e in entradas if patron in e[0]]

    # Lo más recientemente modificado primero: son los eventos vivos
    entradas.sort(key=lambda e: e[1], reverse=True)
    tope = int(fuente.get("tope_fichas", 40))
    entradas = entradas[:tope]

    log.info("%s: %d fichas a revisar desde el sitemap", fuente.get("nombre"), len(entradas))

    eventos: list[Evento] = []
    for url, _ in entradas:
        ficha = cliente.obtener(url, max_edad_cache_seg=24 * 3600)
        if ficha is None or not ficha.ok:
            continue

        sopa = BeautifulSoup(ficha.text, "html.parser")
        encontrados = [e for e in _desde_jsonld(sopa, fuente) if e.inicio]
        if encontrados:
            # Muchos sitios no ponen las coordenadas en el JSON-LD pero sí en
            # los datos que usa su propio mapa. Es el único lugar donde están.
            coords = re.search(r'"?latitude\\?"?\s*:\s*\\?"?(-?\d+\.\d{3,})', ficha.text)
            coords_lon = re.search(r'"?longitude\\?"?\s*:\s*\\?"?(-?\d+\.\d{3,})', ficha.text)
            for e in encontrados:
                e.fuente_url = e.fuente_url or url
                e.fuente_tipo = "sitemap"
                if e.lat is None and coords and coords_lon:
                    try:
                        lat, lon = float(coords.group(1)), float(coords_lon.group(1))
                        # Solo si cae dentro de Santiago; si no, mejor sin dato
                        if -33.75 < lat < -33.20 and -70.95 < lon < -70.35:
                            e.lat, e.lon = lat, lon
                    except ValueError:
                        pass
            eventos.extend(encontrados)
            continue

        # Sin datos estructurados: título de la pestaña y fecha del texto
        titulo = ""
        og_titulo = sopa.find("meta", property="og:title")
        if og_titulo:
            titulo = limpiar_html(og_titulo.get("content", ""))
        elif sopa.title:
            titulo = limpiar_html(sopa.title.get_text())
        if not titulo:
            continue

        for basura in sopa.select("nav, header, footer, script, style"):
            basura.decompose()
        texto = sopa.get_text(" ", strip=True)
        inicio = parsear_fecha(texto)
        if inicio is None:
            continue

        precio, gratis, texto_precio = parsear_precio(texto)
        og_imagen = sopa.find("meta", property="og:image")
        eventos.append(Evento(
            titulo=titulo.split("|")[0].split(" - ")[0].strip()[:120],
            descripcion_corta=resumir(texto, 180),
            inicio=inicio,
            lugar_nombre=fuente.get("nombre", ""),
            comuna=detectar_comuna(texto, fuente.get("comuna", "")),
            precio_clp=precio, es_gratis=gratis, precio_texto=texto_precio,
            fuente_tipo="sitemap",
            fuente_nombre=fuente.get("nombre", ""),
            fuente_url=url,
            imagen_url=og_imagen.get("content", "") if og_imagen else "",
        ))

    log.info("%s: %d eventos vía sitemap+fichas", fuente.get("nombre"), len(eventos))
    return eventos


def extraer_rss(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    """RSS o sitemap. Cultura Providencia publica sitemap.rss."""
    url = fuente.get("url_agenda") or (fuente["url_base"].rstrip("/") + fuente.get("endpoint", ""))
    respuesta = cliente.obtener(url)
    if respuesta is None or not respuesta.ok:
        return []

    try:
        raiz = ElementTree.fromstring(respuesta.content)
    except ElementTree.ParseError as e:
        log.warning("%s: RSS ilegible (%s)", fuente.get("nombre"), e)
        return []

    eventos: list[Evento] = []
    espacios = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    items = raiz.findall(".//item") or raiz.findall(".//s:url", espacios)
    for item in items[:80]:
        titulo_nodo = item.find("title") if item.find("title") is not None else None
        link_nodo = item.find("link") if item.find("link") is not None else item.find("s:loc", espacios)

        titulo = limpiar_html(titulo_nodo.text or "") if titulo_nodo is not None else ""
        url_item = (link_nodo.text or "").strip() if link_nodo is not None else ""
        if not titulo or not url_item:
            continue

        desc_nodo = item.find("description")
        descripcion = limpiar_html(desc_nodo.text or "") if desc_nodo is not None else ""

        texto = f"{titulo}. {descripcion}"
        inicio = parsear_fecha(texto)
        if inicio is None:
            continue

        precio, gratis, texto_precio = parsear_precio(texto)
        eventos.append(Evento(
            titulo=titulo,
            descripcion_corta=resumir(descripcion),
            inicio=inicio,
            lugar_nombre=fuente.get("nombre", ""),
            comuna=detectar_comuna(texto, fuente.get("comuna", "")),
            precio_clp=precio,
            es_gratis=gratis,
            precio_texto=texto_precio,
            fuente_tipo="rss",
            fuente_nombre=fuente.get("nombre", ""),
            fuente_url=url_item,
        ))

    log.info("%s: %d eventos vía RSS", fuente.get("nombre"), len(eventos))
    return eventos
