"""Adaptadores para sitios WordPress, que son la mayoría de las agendas chilenas.

Estrategia en cascada, de mejor a peor dato:
  1. API de The Events Calendar (/wp-json/tribe/events/v1/events) — trae fecha,
     lugar y precio ya estructurados. Es el mejor caso posible.
  2. Tipos de post de calendario (tribe_events, ajde_events, mec-events).
  3. Posts normales, interpretando fecha y precio desde el texto.
"""

from __future__ import annotations

import logging
from datetime import datetime

from ..modelo import Evento
from ..normalizar import (detectar_comuna, limpiar_html, parsear_fecha,
                          parsear_precio, resumir)
from ..red import ClienteEducado

log = logging.getLogger("loica.wordpress")

# Tipos de post que suelen contener eventos. Los tres primeros son plugins
# conocidos; el resto son nombres que usan los sitios chilenos a medida
# (CEINA, por ejemplo, publica en 'cartelera' y 'taller').
TIPOS_DE_POST_CALENDARIO = (
    "tribe_events", "ajde_events", "mec-events",
    "cartelera", "eventos", "evento", "taller", "talleres",
    "actividades", "actividad", "agenda", "programacion", "proximamente",
)

# Pistas para autodescubrir tipos de post propios en /wp-json/wp/v2/types
PISTAS_TIPO_EVENTO = ("event", "evento", "cartelera", "agenda", "taller",
                      "actividad", "programa", "funcion", "obra")


def _texto(campo) -> str:
    """Los campos de WP vienen como {'rendered': '<p>...'} o como string pelado."""
    if isinstance(campo, dict):
        return limpiar_html(campo.get("rendered", ""))
    return limpiar_html(str(campo or ""))


def _desde_tribe(item: dict, fuente: dict) -> Evento | None:
    """The Events Calendar: el formato más rico que nos vamos a encontrar."""
    titulo = limpiar_html(item.get("title", ""))
    if not titulo:
        return None

    inicio = parsear_fecha(item.get("start_date") or "")
    fin = parsear_fecha(item.get("end_date") or "")

    lugar = item.get("venue") or {}
    nombre_lugar = limpiar_html(lugar.get("venue", "")) if isinstance(lugar, dict) else ""
    direccion = ""
    if isinstance(lugar, dict):
        partes = [lugar.get("address", ""), lugar.get("city", "")]
        direccion = ", ".join(p for p in partes if p)

    costo = item.get("cost") or ""
    precio, gratis, texto_precio = parsear_precio(costo or item.get("description", ""))
    if not costo and item.get("cost_details", {}).get("values") == []:
        precio, gratis = 0, True

    categorias = item.get("categories") or []
    categoria = categorias[0].get("name", "") if categorias and isinstance(categorias[0], dict) else ""

    imagen = item.get("image") or {}
    imagen_url = imagen.get("url", "") if isinstance(imagen, dict) else ""

    return Evento(
        titulo=titulo,
        categoria=categoria,
        descripcion_corta=resumir(item.get("description", "")),
        inicio=inicio,
        fin=fin,
        todo_el_dia=bool(item.get("all_day")),
        lugar_nombre=nombre_lugar or fuente.get("nombre", ""),
        lugar_direccion=direccion,
        comuna=detectar_comuna(direccion, nombre_lugar, fuente.get("comuna", "")),
        precio_clp=precio,
        es_gratis=gratis,
        precio_texto=texto_precio or costo,
        fuente_tipo="wordpress",
        fuente_nombre=fuente.get("nombre", ""),
        fuente_url=item.get("url", "") or item.get("link", ""),
        link_entradas=item.get("website", ""),
        imagen_url=imagen_url,
        id_externo=str(item.get("id", "")),
    )


def _imagen_de(item: dict) -> str:
    """Saca la URL de la imagen destacada de un post de WordPress.

    Se enlaza, nunca se descarga: la foto es del organizador (ver la regla de
    derecho de autor en esquema_extraccion_datos.md).
    """
    if item.get("jetpack_featured_media_url"):
        return item["jetpack_featured_media_url"]

    incrustado = (item.get("_embedded") or {}).get("wp:featuredmedia") or []
    if incrustado and isinstance(incrustado[0], dict):
        medio = incrustado[0]
        tamanos = ((medio.get("media_details") or {}).get("sizes") or {})
        for nombre in ("medium_large", "large", "medium", "full"):
            if tamanos.get(nombre, {}).get("source_url"):
                return tamanos[nombre]["source_url"]
        if medio.get("source_url"):
            return medio["source_url"]
    return ""


def _desde_meta(item: dict, fuente: dict) -> tuple[datetime | None, str]:
    """Lee fecha y link desde los campos meta que declare la configuración.

    Algunos sitios (Club Chocolate) publican la fecha como timestamp Unix y el
    link de la ticketera en `meta`, no en el cuerpo. Es dato estructurado y
    fiable: mejor que adivinar del HTML.
    """
    campos = fuente.get("campos_meta") or {}
    meta = item.get("meta") or {}
    if not isinstance(meta, dict):
        return None, ""

    fecha = None
    clave_fecha = campos.get("fecha")
    if clave_fecha and meta.get(clave_fecha):
        crudo = meta[clave_fecha]
        try:
            fecha = datetime.fromtimestamp(int(crudo))
        except (TypeError, ValueError, OSError):
            fecha = parsear_fecha(str(crudo))

    enlace = ""
    clave_link = campos.get("link")
    if clave_link and isinstance(meta.get(clave_link), str):
        enlace = meta[clave_link].strip()
    return fecha, enlace


def _desde_post(item: dict, fuente: dict) -> Evento | None:
    """Post genérico de WordPress: hay que deducir la fecha del evento del texto."""
    titulo = _texto(item.get("title"))
    if not titulo:
        return None

    cuerpo = _texto(item.get("content")) or _texto(item.get("excerpt"))
    texto_completo = f"{titulo}. {cuerpo}"

    # La fecha del evento se busca en el texto, tomando como referencia cuándo
    # se publicó el aviso (así "5 de julio" en un post de julio no se va al año
    # siguiente). Si no aparece, el evento igual se guarda marcado para que el
    # curador le ponga la fecha a mano.
    publicado = parsear_fecha(item.get("date") or "")
    # Los campos meta mandan sobre el texto: son dato estructurado del sitio.
    fecha_meta, link_meta = _desde_meta(item, fuente)
    inicio = fecha_meta or parsear_fecha(texto_completo, publicado=publicado)

    precio, gratis, texto_precio = parsear_precio(texto_completo)

    return Evento(
        titulo=titulo,
        descripcion_corta=resumir(cuerpo),
        inicio=inicio,
        lugar_nombre=fuente.get("nombre", ""),
        comuna=detectar_comuna(texto_completo, fuente.get("comuna", "")),
        precio_clp=precio,
        es_gratis=gratis,
        precio_texto=texto_precio,
        fuente_tipo="wordpress",
        fuente_nombre=fuente.get("nombre", ""),
        fuente_url=item.get("link", ""),
        link_entradas=link_meta,
        imagen_url=_imagen_de(item),
        id_externo=str(item.get("id", "")),
        fecha_publicacion=publicado,
    )


def _completar_desde_ficha(evento: Evento, cliente: ClienteEducado) -> bool:
    """Abre la ficha del evento para buscar la fecha que la API no entregó.

    Muchos sitios guardan la fecha en campos propios que la API REST no expone,
    pero la muestran en la página. Devuelve True si encontró fecha.
    """
    respuesta = cliente.obtener(evento.fuente_url, max_edad_cache_seg=3 * 24 * 3600)
    if respuesta is None or not respuesta.ok:
        return False

    from bs4 import BeautifulSoup
    sopa = BeautifulSoup(respuesta.text, "html.parser")

    # De paso, la imagen para compartir (og:image) casi siempre es el afiche
    if not evento.imagen_url:
        og = sopa.find("meta", property="og:image")
        if og and og.get("content", "").startswith("http"):
            evento.imagen_url = og["content"]

    # 1. Datos estructurados: si el sitio publica schema.org/Event, ahí está
    #    todo bien puesto y no hay que adivinar nada.
    from .web import _desde_jsonld
    estructurados = [e for e in _desde_jsonld(sopa, {"nombre": evento.fuente_nombre})
                     if e.inicio is not None]
    if estructurados:
        mejor = estructurados[0]
        evento.inicio = mejor.inicio
        evento.fin = evento.fin or mejor.fin
        evento.lugar_nombre = evento.lugar_nombre or mejor.lugar_nombre
        evento.lugar_direccion = evento.lugar_direccion or mejor.lugar_direccion
        if evento.precio_clp is None and evento.es_gratis is None:
            evento.precio_clp, evento.es_gratis = mejor.precio_clp, mejor.es_gratis
        return True

    # 2. Si no, se lee el texto. El menú y el pie ensucian la búsqueda de fechas.
    for basura in sopa.select("nav, header, footer, script, style"):
        basura.decompose()

    texto = sopa.get_text(" ", strip=True)
    # La referencia para deducir el año es cuándo se publicó el aviso, NO hoy:
    # si no, un evento de junio pasado se convierte en uno de junio del próximo año.
    fecha = parsear_fecha(texto, publicado=evento.fecha_publicacion)
    if fecha is None:
        return False

    evento.inicio = fecha
    if evento.precio_clp is None and evento.es_gratis is None:
        evento.precio_clp, evento.es_gratis, evento.precio_texto = parsear_precio(texto)
    return True


def _tipos_disponibles(base: str, cliente: ClienteEducado) -> list[str]:
    """Pregunta al sitio qué tipos de contenido publica y elige los que suenan a evento.

    Esto es lo que permite descubrir que CEINA usa 'cartelera' y 'taller' sin
    que nadie lo escriba a mano en la configuración.
    """
    datos = cliente.json(f"{base}/wp-json/wp/v2/types", max_edad_cache_seg=7 * 24 * 3600)
    if not isinstance(datos, dict):
        return []

    candidatos = []
    for nombre, info in datos.items():
        if nombre.startswith("wp_") or nombre in ("attachment", "nav_menu_item", "page"):
            continue
        rest_base = (info or {}).get("rest_base") or nombre
        if any(pista in nombre.lower() for pista in PISTAS_TIPO_EVENTO):
            candidatos.append(rest_base)
    return candidatos


def extraer(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    base = fuente["url_base"].rstrip("/")
    eventos: list[Evento] = []

    # 1. The Events Calendar: el mejor dato posible cuando el sitio lo usa
    datos = cliente.json(f"{base}/wp-json/tribe/events/v1/events", params={"per_page": 50})
    if isinstance(datos, dict) and datos.get("events"):
        for item in datos["events"]:
            evento = _desde_tribe(item, fuente)
            if evento:
                eventos.append(evento)
        log.info("%s: %d eventos vía The Events Calendar", fuente["nombre"], len(eventos))
        return eventos

    # Las municipalidades publican las actividades mezcladas con miles de
    # noticias. Traer los 50 posts más recientes y filtrar después no sirve:
    # los últimos 50 de Recoleta son licitaciones y cuentas públicas, y los
    # talleres quedan enterrados entre 2.532 registros. Con `buscar_terminos`
    # se le pregunta al sitio por cada palabra (?search=taller), que es lo que
    # recorre el archivo completo en vez de la portada.
    terminos = list(fuente.get("buscar_terminos") or [])
    vistos: set[str] = set()

    def cosechar(endpoint: str) -> list[Evento]:
        # _embed trae la imagen destacada en la misma petición: sin esto
        # WordPress solo entrega el id de la imagen y no su URL.
        base_params = {"per_page": 50, "orderby": "date",
                       "_embed": "wp:featuredmedia"}
        consultas = ([{**base_params, "search": t} for t in terminos]
                     if terminos else [base_params])

        encontrados: list[Evento] = []
        for params in consultas:
            datos = cliente.json(f"{base}{endpoint}", params=params)
            if not isinstance(datos, list) or not datos:
                continue
            for item in datos:
                clave = f"{endpoint}:{item.get('id')}"
                if clave in vistos:
                    continue
                vistos.add(clave)
                evento = _desde_post(item, fuente)
                if evento:
                    encontrados.append(evento)

        if encontrados:
            log.info("%s: %d eventos vía %s%s", fuente["nombre"], len(encontrados),
                     endpoint, f" ({len(terminos)} búsquedas)" if terminos else "")
        return encontrados

    # 2. Tipos propios del sitio: los de la configuración más los que el propio
    #    sitio declara. Se recorren TODOS, porque un sitio a medida reparte sus
    #    eventos en varios tipos a la vez (CEINA: cartelera + taller).
    tipos = list(fuente.get("tipos_post") or []) + _tipos_disponibles(base, cliente)
    endpoints = [f"/wp-json/wp/v2/{t}" for t in dict.fromkeys(tipos)]
    if fuente.get("endpoint"):
        endpoints.append(fuente["endpoint"])

    for endpoint in dict.fromkeys(endpoints):
        eventos.extend(cosechar(endpoint))

    # 3. Último recurso: nombres habituales, hasta el primero que dé resultado.
    if not eventos:
        for tipo in TIPOS_DE_POST_CALENDARIO:
            eventos = cosechar(f"/wp-json/wp/v2/{tipo}")
            if eventos:
                break

    if not eventos:
        log.warning("%s: la API REST no devolvió eventos utilizables", fuente["nombre"])
        return eventos

    # 4. Segunda pasada: a los que quedaron sin fecha se les abre la ficha.
    #    Cuesta una petición por evento, así que se limita y solo se hace si la
    #    fuente lo pide en la configuración.
    if fuente.get("buscar_detalle"):
        tope = int(fuente.get("tope_detalle", 40))
        # El filtro por palabras se aplica ANTES de abrir fichas: en una fuente
        # municipal la mayoría de los posts son licitaciones y cuentas públicas,
        # y abrirles la ficha para buscarles fecha es gastar la cuota del sitio
        # en cosas que se van a descartar igual.
        from ..filtros import motivo_de_descarte
        candidatos = [e for e in eventos
                      if e.necesita_fecha and not motivo_de_descarte(e, fuente)]
        pendientes = candidatos[:tope]
        recuperados = sum(1 for e in pendientes if _completar_desde_ficha(e, cliente))
        if pendientes:
            log.info("%s: %d/%d fechas recuperadas abriendo la ficha",
                     fuente["nombre"], recuperados, len(pendientes))

    return eventos


def extraer_eventon(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    """Plugin EventON (lo usa Santiago Cultura): responde por admin-ajax.php.

    Su robots.txt permite explícitamente admin-ajax. Si el formato del JSON
    cambia, esta función devuelve vacío sin romper la corrida completa.
    """
    base = fuente["url_base"].rstrip("/")
    respuesta = cliente.obtener(
        f"{base}/wp-admin/admin-ajax.php",
        params={"action": "the_ajax_hook", "direction": "none", "shortcode[event_count]": "50"},
    )
    if respuesta is None or not respuesta.ok:
        log.warning("%s: EventON no respondió", fuente["nombre"])
        return []

    try:
        datos = respuesta.json()
    except ValueError:
        log.warning("%s: EventON devolvió algo que no es JSON", fuente["nombre"])
        return []

    html = datos.get("content", "") if isinstance(datos, dict) else ""
    if not html:
        return []

    from .web import eventos_desde_html  # import local para evitar ciclo
    return eventos_desde_html(html, fuente, tipo="eventon")
