"""Adaptador de dos niveles: índice de locales → cartelera de cada local.

Las ticketeras independientes publican un listado general corto (PortalTickets
muestra 50 eventos) pero enlazan la cartelera completa de cada local. Ahí vive
el circuito que ninguna municipalidad publica: Bar de René, Bar Raíces en
Yungay, Kahuin, Mesón Nerudiano, Sala Master.

Leer solo el listado general deja fuera casi todo: de los 12 eventos que Bar de
René tenía publicados, el listado general mostraba 1.

La ventaja de bajar al local es que su cartelera ya trae la tarjeta completa
—título, fecha y "Local, Comuna"— así que NO hay que abrir la ficha de cada
evento. Una corrida cuesta 1 petición del índice más 1 por local, no 200.

    tipo_adaptador: carteleras
    url_agenda: https://www.portaldisc.com/portaltickets
    patron_indice: /cartelera/    # links del índice que son locales
    patron_url: /evento/          # links de la cartelera que son eventos
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from ..modelo import Evento
from ..normalizar import (detectar_comuna, limpiar_html, parsear_fecha,
                          parsear_precio)
from ..red import ClienteEducado

log = logging.getLogger("loica.carteleras")


def _links(html: str, base: str, patron: str) -> list[str]:
    """Links únicos de la página que contienen `patron`, ya absolutos."""
    sopa = BeautifulSoup(html, "html.parser")
    vistos: dict[str, None] = {}
    for enlace in sopa.find_all("a", href=True):
        href = enlace["href"]
        if patron not in href:
            continue
        if href.startswith("/"):
            href = base + href
        elif not href.startswith("http"):
            continue
        vistos.setdefault(href.split("?")[0].rstrip("/"), None)
    return list(vistos)


def _tarjeta(ancla) -> tuple[str, str, str]:
    """Saca (título, texto de fecha, texto de lugar) de una tarjeta de evento.

    La tarjeta son párrafos en orden dentro del enlace: título, fecha, y
    "Local, Comuna". Si el sitio cambia la maquetación se cae al texto plano,
    que sigue sirviendo para la fecha aunque se pierda la separación.
    """
    parrafos = [limpiar_html(p.get_text(" ", strip=True))
                for p in ancla.find_all(["p", "h2", "h3", "h4", "span", "div"])]
    parrafos = [p for p in parrafos if p]

    if len(parrafos) >= 2:
        titulo = parrafos[0]
        # La fecha es el primer párrafo después del título donde se reconozca
        # una: así da igual si el sitio mete un párrafo de género o de precio.
        resto = parrafos[1:]
        indice_fecha = next((i for i, p in enumerate(resto)
                             if parsear_fecha(p) is not None), None)
        if indice_fecha is not None:
            fecha = resto[indice_fecha]
            lugar = " ".join(resto[indice_fecha + 1:])
            return titulo, fecha, lugar
        return titulo, "", " ".join(resto)

    texto = limpiar_html(ancla.get_text(" ", strip=True))
    return texto, texto, texto


def extraer_carteleras(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    base = fuente["url_base"].rstrip("/")
    url_indice = fuente.get("url_agenda") or (base + fuente.get("endpoint", "/"))

    respuesta = cliente.obtener(url_indice, max_edad_cache_seg=6 * 3600)
    if respuesta is None or not respuesta.ok:
        log.warning("%s: no pude leer el índice de locales", fuente.get("nombre"))
        return []

    patron_indice = fuente.get("patron_indice", "/cartelera/")
    patron_evento = fuente.get("patron_url", "/evento/")
    tope = int(fuente.get("tope_locales", 40))

    locales = _links(respuesta.text, base, patron_indice)[:tope]

    # El índice no lista todos los locales: Teatro Fábrica y Teatro Fiebre
    # tienen cartelera propia y no aparecen ahí. Se agregan por configuración.
    for extra in fuente.get("carteleras_extra") or []:
        url_extra = extra if extra.startswith("http") else f"{base}{patron_indice}{extra}"
        if url_extra.rstrip("/") not in locales:
            locales.append(url_extra.rstrip("/"))

    if not locales:
        log.warning("%s: el índice no enlaza ningún local (patrón %s)",
                    fuente.get("nombre"), patron_indice)
        return []

    log.info("%s: %d locales en el índice", fuente.get("nombre"), len(locales))

    eventos: list[Evento] = []
    vistos: set[str] = set()
    locales_con_datos = 0

    for url_local in locales:
        pagina = cliente.obtener(url_local, max_edad_cache_seg=6 * 3600)
        if pagina is None or not pagina.ok:
            continue

        sopa = BeautifulSoup(pagina.text, "html.parser")

        # PortalDisc responde 200 a CUALQUIER slug, aunque el local no exista:
        # devuelve una página con el título "EVENTOS EN " vacío y un evento
        # genérico de la plataforma. Sin este guardia, un slug mal escrito mete
        # esa preventa de vinilo como si fuera del local.
        titulo_pagina = sopa.title.get_text(" ", strip=True) if sopa.title else ""
        if re.search(r"eventos\s+en\s*$", titulo_pagina, re.IGNORECASE):
            log.warning("%s: %s no tiene local asociado — se omite",
                        fuente.get("nombre"), url_local.rsplit("/", 1)[-1])
            continue

        antes = len(eventos)

        for ancla in sopa.find_all("a", href=True):
            href = ancla["href"]
            if patron_evento not in href:
                continue
            if href.startswith("/"):
                href = base + href
            href = href.split("?")[0]
            if href in vistos:
                continue

            # Cada evento aparece dos veces: una como imagen (sin texto) y otra
            # como tarjeta. Solo la segunda sirve.
            titulo, texto_fecha, texto_lugar = _tarjeta(ancla)
            if not titulo:
                continue

            inicio = parsear_fecha(texto_fecha) or parsear_fecha(titulo)
            if inicio is None:
                continue

            vistos.add(href)

            # "Bar de René, Providencia" — el local antes de la coma, la comuna
            # después. Se le pasa el texto entero a detectar_comuna igual, por
            # si el formato viene al revés.
            lugar = texto_lugar.split(",")[0].strip() if texto_lugar else ""
            precio, gratis, texto_precio = parsear_precio(texto_lugar)

            eventos.append(Evento(
                titulo=titulo[:200],
                inicio=inicio,
                lugar_nombre=lugar or fuente.get("nombre", ""),
                comuna=detectar_comuna(texto_lugar, fuente.get("comuna", "")),
                precio_clp=precio,
                es_gratis=gratis,
                precio_texto=texto_precio,
                fuente_tipo="carteleras",
                fuente_nombre=fuente.get("nombre", ""),
                fuente_url=href,
                link_entradas=href,
            ))

        if len(eventos) > antes:
            locales_con_datos += 1

    # Los eventos que quedan sin comuna NO son un error a corregir: PortalDisc
    # es nacional y esas tarjetas son de locales de regiones (Teatro Mauri en
    # Valparaíso, MagBar en Chillán, Bandera 1001 en Concepción, 12 Lunas en La
    # Serena). `requiere_comuna` los descarta, que es exactamente lo correcto.
    # Se probó abrir la ficha para rescatarles la comuna: recuperó 0 de 59 y
    # costaba una petición por evento descartado.
    sin_comuna = sum(1 for e in eventos if not e.comuna)
    log.info("%s: %d eventos desde %d/%d locales (%d sin comuna, probablemente de regiones)",
             fuente.get("nombre"), len(eventos), locales_con_datos, len(locales), sin_comuna)
    return eventos
