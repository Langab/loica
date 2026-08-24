"""APIs oficiales. Hoy: Ticketmaster Discovery (la única con permiso explícito
y cobertura de Chile). Límites: 5 peticiones/segundo, 5.000 al día.

La API key se lee de la variable de entorno TICKETMASTER_API_KEY. Si no está,
la fuente falla fuerte y queda anotada como error en la tabla `corridas`:
devolver cero en silencio la hacía verse igual que una fuente sana en un día
sin agenda, y así estuvo meses. `run_diario` atrapa la excepción por fuente,
así que la corrida no se cae por esto.

En la corrida diaria la key llega desde los secretos del repositorio, que el
workflow inyecta en el entorno. No está escrita en ningún archivo.
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
        # Antes esto devolvía [] con un warning en el log. El resultado era una
        # fuente activa que entregaba cero todos los días sin registrar error:
        # en el informe se veía igual que una fuente sana en un día sin agenda,
        # y así estuvo meses. Reventar acá la deja anotada como error en la
        # tabla `corridas`, que es lo que mira fuentes_degradadas(). run_diario
        # atrapa la excepción por fuente, así que la corrida no se cae.
        raise RuntimeError(
            "falta TICKETMASTER_API_KEY en el entorno "
            "(se saca gratis en developer.ticketmaster.com)")

    eventos: list[Evento] = []
    pagina = 0

    ciudad = fuente.get("ciudad", "Santiago")

    while pagina < 5:  # 5 páginas x 100 = 500 eventos, de sobra para Santiago
        respuesta = cliente.obtener(URL_DISCOVERY, params={
            "apikey": api_key,
            "countryCode": "CL",
            "city": ciudad,
            "size": 100,
            "page": pagina,
            "sort": "date,asc",
        }, max_edad_cache_seg=6 * 3600)

        # Acá se miraba sólo si la respuesta era un diccionario, y cualquier
        # otra cosa cortaba el bucle en silencio. El efecto: una key inválida
        # (401) o la cuota agotada (429) daban EXACTAMENTE el mismo resultado
        # que una ciudad sin eventos —cero, sin error—, que es el patrón que
        # ya nos costó meses con Passline. Ahora cada caso dice lo suyo.
        #
        # El código de estado va solo en el mensaje: la URL completa lleva la
        # key en la query y no puede terminar en un log.
        if respuesta is None:
            raise RuntimeError("la API de Ticketmaster no respondió "
                               "(sin conexión o robots.txt)")
        if respuesta.status_code == 401:
            raise RuntimeError(
                "la API rechazó la credencial (HTTP 401): revisar el secreto "
                "TICKETMASTER_API_KEY — tiene que ser el Consumer Key")
        if respuesta.status_code == 429:
            raise RuntimeError("cuota de Ticketmaster agotada (HTTP 429): "
                               "son 5.000 llamadas al día")
        if not respuesta.ok:
            raise RuntimeError(f"la API devolvió HTTP {respuesta.status_code}")

        try:
            datos = respuesta.json()
        except ValueError:
            raise RuntimeError("la API respondió algo que no es JSON")
        if not isinstance(datos, dict):
            raise RuntimeError("la API respondió un JSON con forma inesperada")

        lote = (datos.get("_embedded") or {}).get("events") or []
        if not lote:
            # Respondió bien y no trae nada: es un hecho sobre el catálogo de
            # Ticketmaster, no una falla nuestra. Se dice y no se revienta.
            if pagina == 0:
                log.info("Ticketmaster: la API respondió 200 pero no tiene "
                         "ningún evento para %s, Chile", ciudad)
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
