"""APIs oficiales. Hoy: Ticketmaster Discovery (la única con permiso explícito
y cobertura de Chile). Límites: 2 peticiones/segundo, 5.000 al día.

La API key se lee de la variable de entorno TICKETMASTER_API_KEY. Si no está,
la fuente se salta sin romper la corrida.
"""

from __future__ import annotations

import logging
import os

from ..modelo import Evento
from ..normalizar import detectar_comuna, parsear_fecha, resumir
from ..red import ClienteEducado

log = logging.getLogger("loica.apis")

URL_DISCOVERY = "https://app.ticketmaster.com/discovery/v2/events.json"


def extraer_ticketmaster(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    api_key = os.environ.get("TICKETMASTER_API_KEY", "").strip()
    if not api_key:
        log.warning("Ticketmaster: falta TICKETMASTER_API_KEY — fuente omitida")
        return []

    eventos: list[Evento] = []
    pagina = 0

    while pagina < 5:  # 5 páginas x 100 = 500 eventos, de sobra para Santiago
        datos = cliente.json(URL_DISCOVERY, params={
            "apikey": api_key,
            "countryCode": "CL",
            "city": fuente.get("ciudad", "Santiago"),
            "size": 100,
            "page": pagina,
            "sort": "date,asc",
        }, max_edad_cache_seg=6 * 3600)

        if not isinstance(datos, dict):
            break

        lote = (datos.get("_embedded") or {}).get("events") or []
        if not lote:
            break

        for item in lote:
            evento = _desde_ticketmaster(item, fuente)
            if evento:
                eventos.append(evento)

        info_pag = datos.get("page") or {}
        if pagina >= info_pag.get("totalPages", 1) - 1:
            break
        pagina += 1

    log.info("Ticketmaster: %d eventos", len(eventos))
    return eventos


def _desde_ticketmaster(item: dict, fuente: dict) -> Evento | None:
    titulo = (item.get("name") or "").strip()
    if not titulo:
        return None

    fechas = (item.get("dates") or {}).get("start") or {}
    inicio = parsear_fecha(fechas.get("dateTime") or fechas.get("localDate") or "")
    if inicio is None:
        return None
    if fechas.get("localTime") and inicio.hour == 0:
        hora = parsear_fecha(f"{fechas.get('localDate')} {fechas.get('localTime')}")
        inicio = hora or inicio

    recintos = (item.get("_embedded") or {}).get("venues") or []
    recinto = recintos[0] if recintos else {}
    nombre_lugar = recinto.get("name", "")
    direccion = ((recinto.get("address") or {}).get("line1") or "")
    ciudad = ((recinto.get("city") or {}).get("name") or "")

    # Precio: Ticketmaster entrega rangos; guardamos el mínimo como referencia
    precio = None
    rangos = item.get("priceRanges") or []
    if rangos:
        try:
            precio = int(float(rangos[0].get("min", 0)))
        except (TypeError, ValueError):
            precio = None

    clasificaciones = item.get("classifications") or []
    categoria = ""
    if clasificaciones:
        segmento = (clasificaciones[0].get("segment") or {}).get("name", "")
        genero = (clasificaciones[0].get("genre") or {}).get("name", "")
        categoria = " / ".join(p for p in (segmento, genero) if p)

    imagenes = item.get("images") or []
    imagen_url = ""
    if imagenes:
        anchas = [i for i in imagenes if i.get("width", 0) >= 640]
        imagen_url = (anchas or imagenes)[0].get("url", "")

    return Evento(
        titulo=titulo,
        categoria=categoria,
        descripcion_corta=resumir(item.get("info") or item.get("pleaseNote") or ""),
        inicio=inicio,
        lugar_nombre=nombre_lugar,
        lugar_direccion=", ".join(p for p in (direccion, ciudad) if p),
        comuna=detectar_comuna(ciudad, direccion, nombre_lugar),
        precio_clp=precio,
        es_gratis=(precio == 0) if precio is not None else None,
        precio_texto=f"desde ${precio:,.0f}".replace(",", ".") if precio else "",
        fuente_tipo="api",
        fuente_nombre="Ticketmaster",
        fuente_url=item.get("url", ""),
        link_entradas=item.get("url", ""),
        imagen_url=imagen_url,
        id_externo=item.get("id", ""),
    )
