"""Adaptador para carteleras de cine semanales.

Los cines de barrio no publican eventos: publican la semana. El Normandie
arma una sección por día con las funciones sueltas dentro:

    <section class="jueves">
      <h5>Jueves 13</h5>
      15:00 hrs. <strong>La posada maldita</strong>
      17:10 hrs. <strong>La invitación</strong>
    </section>

Cada función es un evento con su hora, que es justo lo que sirve para
"¿qué hay hoy?" y para el filtro de fin de semana.

La fecha completa no está escrita en ninguna parte: la sección dice el día de
la semana y el número, y el mes vive en un titular aparte. En vez de armar el
rompecabezas, se busca la única fecha cercana a hoy que calce con ese día de
la semana Y ese número. Es inequívoco y cruza fin de mes y fin de año solo.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

from ..modelo import Evento
from ..normalizar import detectar_comuna, limpiar_html, parsear_precio
from ..recurrencia import DIAS_SEMANA
from ..red import ClienteEducado

log = logging.getLogger("loica.cine")

# "15:00 hrs. La posada maldita" — la hora abre y el título sigue hasta la
# próxima hora. Sin el look-ahead, el primer título se come toda la sección.
FUNCION = re.compile(
    r"(\d{1,2})[:.](\d{2})\s*(?:hrs?\.?|horas?)?\s*(.+?)"
    r"(?=\s*\d{1,2}[:.]\d{2}\s*(?:hrs?\.?|horas?)|$)",
    re.IGNORECASE)


def _fecha_de(dia_semana: int, numero: int, hoy: date, ventana: int = 12) -> date | None:
    """La fecha cercana a hoy que cae en ese día de la semana y ese número.

    La combinación (jueves, 13) se repite recién en meses distintos, así que
    dentro de una ventana de dos semanas es única. Resuelve solo el cambio de
    mes y de año sin tener que leer el titular de la semana.
    """
    for delta in range(-ventana, ventana + 1):
        candidata = hoy + timedelta(days=delta)
        if candidata.weekday() == dia_semana and candidata.day == numero:
            return candidata
    return None


def extraer_cine(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    url = fuente.get("url_agenda") or (
        fuente["url_base"].rstrip("/") + fuente.get("endpoint", "/cartelera/"))
    respuesta = cliente.obtener(url, max_edad_cache_seg=12 * 3600)
    if respuesta is None or not respuesta.ok:
        log.warning("%s: no pude leer la cartelera", fuente.get("nombre"))
        return []

    sopa = BeautifulSoup(respuesta.text, "html.parser")
    for basura in sopa.select("nav, header, footer, script, style"):
        basura.decompose()

    hoy = date.today()
    eventos: list[Evento] = []
    dias_leidos = 0

    # Una sección por día de la semana: section.jueves, section.viernes...
    for nombre_dia, indice in DIAS_SEMANA.items():
        for seccion in sopa.select(f"section.{nombre_dia}, div.{nombre_dia}"):
            encabezado = seccion.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            if encabezado is None:
                continue

            m = re.search(r"(\d{1,2})", encabezado.get_text(" ", strip=True))
            if not m:
                continue
            fecha = _fecha_de(indice, int(m.group(1)), hoy)
            if fecha is None:
                continue

            # El encabezado se saca antes de leer las funciones: si no, su
            # número se confunde con una hora.
            encabezado.decompose()
            texto = seccion.get_text(" ", strip=True)
            dias_leidos += 1

            for funcion in FUNCION.finditer(texto):
                hora, minuto = int(funcion.group(1)), int(funcion.group(2))
                titulo = limpiar_html(funcion.group(3)).strip(" .-–—")
                if not titulo or hora > 23 or minuto > 59:
                    continue

                precio, gratis, texto_precio = parsear_precio(titulo)
                eventos.append(Evento(
                    titulo=titulo[:200],
                    categoria=fuente.get("categoria_por_defecto", "cine"),
                    inicio=datetime.combine(fecha, datetime.min.time()).replace(
                        hour=hora, minute=minuto),
                    lugar_nombre=fuente.get("nombre", ""),
                    lugar_direccion=fuente.get("direccion", ""),
                    comuna=detectar_comuna(fuente.get("comuna", ""),
                                           fuente.get("direccion", "")),
                    precio_clp=precio,
                    es_gratis=gratis,
                    precio_texto=texto_precio,
                    fuente_tipo="cine",
                    fuente_nombre=fuente.get("nombre", ""),
                    fuente_url=url,
                ))

    log.info("%s: %d funciones en %d días", fuente.get("nombre"),
             len(eventos), dias_leidos)
    return eventos
