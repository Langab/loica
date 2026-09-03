"""Listado HTML que solo enlaza, y fichas donde vive el dato.

Es el patrón de dos agendas que hasta el 02-09-2026 se extraían a mano con
un navegador:

  · La UAI publica /eventos renderizado en servidor (Next.js) con 45
    tarjetas que enlazan a fichas con JSON-LD `Event` completo. Lo que el
    JSON-LD NO dice es dónde queda "Pdte. Errázuriz": la universidad tiene
    tres sedes en tres comunas, y la mayoría de sus eventos no es del campus
    que el catastro suponía.
  · Vitacura tiene la API REST cerrada (401) y un listado /actividades/
    paginado con ?pagina=N; la fecha, la hora, el lugar y la entrada están
    en la ficha, cada uno en su clase CSS, y no hay JSON-LD.

El adaptador `sitemap` con `origen: listado` ya sabe abrir fichas, pero no
pagina, solo lee JSON-LD o texto suelto, y hereda la comuna por defecto de la
fuente cuando el lugar no la dice. Acá se agregan las tres cosas que faltan,
todas por configuración:

    paginacion: "?pagina={n}"      # se sigue hasta que una página no aporte
                                   # fichas nuevas (Vitacura repite la última
                                   # para cualquier N mayor)
    ficha:                         # campos de la ficha, por selector CSS o
      fecha: .actividad-detalle-fecha   # por etiqueta: "etiqueta:Fecha"
      hora: "etiqueta:Hora de inicio"   # busca el rótulo y lee lo que sigue
      lugar: "etiqueta:Ubicación"
    sedes:                         # el lugar dice "Errázuriz"; la dirección
      - clave: Errázuriz           # y la comuna las pone esto, nunca la
        lugar: UAI Sede Presidente Errázuriz     # comuna por defecto
        direccion: Av. Presidente Errázuriz 3485
        comuna: Las Condes
    lugares_sin_comuna: [Online]   # "Online" no queda en ninguna comuna; sin
                                   # esto heredaría la de la fuente
    descartar_tarjeta: [Online]    # ni siquiera se abre la ficha: son la
                                   # mitad de las tarjetas de la UAI

Como en todo adaptador: solo hechos. Si el sitio cambia la maqueta se
devuelven menos eventos, nunca inventados; y sin fecha legible la ficha se
omite, porque el único motivo de abrirla era leer cuándo es.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from bs4 import BeautifulSoup

from ..modelo import Evento
from ..normalizar import (detectar_comuna, limpiar_html, parsear_fecha,
                          parsear_precio, resumir)
from ..recurrencia import parsear_hora
from ..red import ClienteEducado
from .web import _desde_jsonld

log = logging.getLogger("loica.fichas")

# Lo que se puede leer de una ficha con `ficha: {campo: selector}`.
CAMPOS = ("titulo", "fecha", "fin", "hora", "lugar", "precio", "descripcion",
          "categoria")


# Una ubicación que es solo una dirección: vía pública seguida de número, o
# un número de tres cifras o más ("San Félix 1318", "Av. Kennedy 9350").
_PARECE_DIRECCION = re.compile(
    r"\b(?:av(?:da)?\.?|avenida|calle|pasaje|psje\.?|camino)\b.*\d|\bn[º°]\s*\d|\b\d{3,5}\b",
    re.IGNORECASE)


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    solo_ascii = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return " ".join(solo_ascii.lower().split())


def _absoluta(href: str, base: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return base + href
    return href


# -- listado -----------------------------------------------------------------

def _fichas_del_listado(fuente: dict, cliente: ClienteEducado) -> list[tuple[str, str]]:
    """(url de la ficha, texto de su tarjeta), en el orden del listado.

    El texto de la tarjeta sirve para descartar sin abrir la ficha: en la UAI
    la tarjeta ya dice "Online", y abrir esas 18 fichas es gastar la cuota
    del sitio en eventos que no quedan en ninguna comuna.
    """
    base = fuente["url_base"].rstrip("/")
    listado = fuente.get("url_agenda") or (base + fuente.get("endpoint", "/"))
    patron = fuente.get("patron_url", "")
    excluir = [e.lower() for e in (fuente.get("excluir_url") or [])]
    paginacion = fuente.get("paginacion", "")
    tope_paginas = int(fuente.get("tope_paginas", 10)) if paginacion else 1

    vistas: dict[str, str] = {}
    for numero in range(1, tope_paginas + 1):
        url = listado if numero == 1 else listado + paginacion.format(n=numero)
        respuesta = cliente.obtener(url, max_edad_cache_seg=3 * 3600)
        if respuesta is None or not respuesta.ok:
            if numero == 1:
                log.warning("%s: no pude leer el listado", fuente.get("nombre"))
            break

        sopa = BeautifulSoup(respuesta.text, "html.parser")
        nuevas = 0
        for enlace in sopa.find_all("a", href=True):
            href = _absoluta(enlace["href"].strip(), base)
            if not href.startswith("http") or (patron and patron not in href):
                continue
            limpia = href.split("?")[0].split("#")[0]
            clave = limpia.rstrip("/")
            if clave == base or any(trozo in clave.lower() for trozo in excluir):
                continue
            texto = enlace.get_text(" ", strip=True)
            if clave not in vistas:
                # Se guarda la URL tal como la publica el sitio, con su barra
                # final: sin ella WordPress responde 301 y cada ficha cuesta
                # dos peticiones en vez de una (Vitacura: 84 por 44).
                vistas[clave] = (limpia, texto)
                nuevas += 1
            elif texto and texto not in vistas[clave][1]:
                # La misma ficha enlazada desde la foto y desde el título:
                # se junta todo lo que digan sus tarjetas.
                vistas[clave] = (limpia, f"{vistas[clave][1]} {texto}".strip())

        # Una página que no aporta fichas nuevas es el fin del listado, o la
        # última página repetida, que es cómo Vitacura responde a ?pagina=99.
        if nuevas == 0:
            break

    return list(vistas.values())


# -- ficha -------------------------------------------------------------------

def _por_etiqueta(sopa: BeautifulSoup, etiqueta: str) -> str:
    """Lee el valor que sigue a un rótulo: <span>Fecha:</span><span>2 de …</span>.

    Sitios armados con utilidades CSS (Tailwind) no tienen una clase que
    nombre el dato, pero sí el rótulo escrito al lado. Se busca el nodo de
    texto que sea exactamente la etiqueta (con o sin dos puntos) y se toma
    el hermano siguiente; si no hay, lo que queda del padre sin el rótulo.
    """
    patron = re.compile(rf"^\s*{re.escape(etiqueta)}\s*:?\s*$", re.IGNORECASE)
    for nodo in sopa.find_all(string=patron):
        elemento = nodo.parent
        if elemento is None:
            continue
        siguiente = elemento.find_next_sibling()
        if siguiente is not None:
            texto = siguiente.get_text(" ", strip=True)
            if texto:
                return texto
        padre = elemento.parent
        if padre is not None:
            resto = padre.get_text(" ", strip=True)
            resto = re.sub(rf"^\s*{re.escape(etiqueta)}\s*:?\s*", "", resto,
                           flags=re.IGNORECASE).strip()
            if resto:
                return resto
    return ""


def _texto_campo(sopa: BeautifulSoup, selector: str) -> str:
    selector = (selector or "").strip()
    if not selector:
        return ""
    if selector.lower().startswith("etiqueta:"):
        return _por_etiqueta(sopa, selector.split(":", 1)[1].strip())
    nodo = sopa.select_one(selector)
    return nodo.get_text(" ", strip=True) if nodo else ""


def _meta(sopa: BeautifulSoup, propiedad: str) -> str:
    nodo = sopa.find("meta", property=propiedad) or sopa.find("meta", attrs={"name": propiedad})
    return (nodo.get("content") or "").strip() if nodo else ""


def _separar_lugar(texto: str) -> tuple[str, str, str]:
    """"Sala Entel // Pdte. Errázuriz" → (sala, dirección, sede).

    Tres formas de escribir el lugar en una ficha, y qué se saca de cada una:
      · "Hotel Radisson Blu Las Condes, (Manquehue Norte 656)" → la dirección
        va entre paréntesis.
      · "Biblioteca, Av. San Josemaría Escrivá de Balaguer 6420" → después de
        la coma, si lo que sigue parece dirección (tiene número o "esq.").
      · "Sala Entel // Pdte. Errázuriz" → la doble barra separa la sala de la
        sede, y la sede es lo que se cruza con el mapa de `sedes`.
    """
    texto = " ".join((texto or "").split())
    sede = ""
    if "//" in texto:
        texto, sede = (p.strip() for p in texto.split("//", 1))

    m = re.search(r"\(([^()]{4,})\)", texto)
    if m:
        nombre = (texto[:m.start()] + " " + texto[m.end():]).strip(" ,;-")
        return " ".join(nombre.split()), m.group(1).strip(), sede

    if "," in texto:
        nombre, resto = texto.split(",", 1)
        if re.search(r"\d|\bs/n\b|\besq", resto):
            return nombre.strip(), resto.strip(" ."), sede

    return texto, "", sede


def _sede_de(fuente: dict, texto: str) -> dict | None:
    plano = _plano(texto)
    if not plano:
        return None
    for sede in fuente.get("sedes") or []:
        clave = _plano(str(sede.get("clave", "")))
        if clave and clave in plano:
            return sede
    return None


def _evento_de_ficha(url: str, html: str, fuente: dict) -> Evento | None:
    sopa = BeautifulSoup(html, "html.parser")
    campos = fuente.get("ficha") or {}
    leido = {campo: _texto_campo(sopa, campos.get(campo, "")) for campo in CAMPOS}

    # El JSON-LD, cuando existe y trae fecha, es el mejor dato posible. Lo
    # configurado en `ficha` manda sobre él campo por campo: es lo que una
    # persona miró y declaró.
    base = next((e for e in _desde_jsonld(sopa, fuente) if e.inicio is not None), None)

    titulo = leido["titulo"] or (base.titulo if base else "") or _meta(sopa, "og:title")
    if not titulo:
        h1 = sopa.find("h1")
        titulo = h1.get_text(" ", strip=True) if h1 else (sopa.title.get_text() if sopa.title else "")
    titulo = limpiar_html(titulo).split(" | ")[0].strip()[:200]
    if not titulo:
        return None

    inicio = parsear_fecha(leido["fecha"]) if leido["fecha"] else None
    if inicio is None and base:
        inicio = base.inicio
    if inicio is None:
        return None

    # La hora suele venir en su propio elemento ("17:00 a 18:00"), separada
    # de la fecha; parsear_fecha solo la busca al lado de la fecha.
    hora_fin = None
    if leido["hora"]:
        horas = re.findall(r"\b([01]?\d|2[0-3])[:.h](\d{2})\b", leido["hora"])
        if horas and inicio.hour == 0 and inicio.minute == 0:
            inicio = inicio.replace(hour=int(horas[0][0]), minute=int(horas[0][1]))
        if len(horas) > 1:
            hora_fin = parsear_hora(f"{horas[1][0]}:{horas[1][1]}")

    fin = parsear_fecha(leido["fin"]) if leido["fin"] else None
    if fin is None and leido["fecha"]:
        # "Desde 05/09/2026 Hasta 27/09/2026": la segunda fecha es el término,
        # y es la que mide la vigencia de una muestra que ya abrió.
        tramos = re.split(r"\s+hasta\s+|\s+al\s+|\s*[-–—]\s*", leido["fecha"],
                          maxsplit=1, flags=re.IGNORECASE)
        if len(tramos) == 2:
            fin = parsear_fecha(tramos[1])
    if fin is None and base:
        fin = base.fin
    if fin is not None:
        if fin.date() == inicio.date() or fin < inicio:
            fin = None  # un solo día: el rango no dice nada
        elif hora_fin and fin.hour == 0 and fin.minute == 0:
            fin = fin.replace(hour=hora_fin.hour, minute=hora_fin.minute)

    # -- dónde -------------------------------------------------------------
    nombre_lugar = direccion = sede_texto = ""
    if leido["lugar"]:
        nombre_lugar, direccion, sede_texto = _separar_lugar(leido["lugar"])
    elif base:
        nombre_lugar, direccion = base.lugar_nombre, base.lugar_direccion
        if not re.search(r"\d", direccion):
            # "Otro" o "Pdte. Errázuriz" en streetAddress no son direcciones:
            # son la sede. La dirección de verdad, si está, va en el nombre.
            sede_texto, direccion = direccion, ""
            nombre_lugar, direccion, sede_en_nombre = _separar_lugar(nombre_lugar)
            sede_texto = sede_texto or sede_en_nombre
    if nombre_lugar == fuente.get("nombre", ""):
        nombre_lugar = ""
    if nombre_lugar and not direccion and _PARECE_DIRECCION.search(nombre_lugar):
        # "San Félix 1318" a secas: la ficha dio una dirección y ningún
        # nombre. Va también como dirección, que es lo que el índice OSM
        # sabe convertir en un pin exacto; como nombre solo sería un texto.
        direccion = nombre_lugar

    # La sede se cruza SOLO con el texto de sede ("Pdte. Errázuriz"), no con
    # el nombre del recinto: un evento en un hotel de Vitacura no es un
    # evento en la sede Vitacura de la universidad. Si la ficha no separa
    # sede de recinto, se mira todo.
    sede = _sede_de(fuente, sede_texto or f"{nombre_lugar} {direccion}")
    sala = ""
    if sede:
        if nombre_lugar and _plano(str(sede.get("clave", ""))) not in _plano(nombre_lugar):
            sala = nombre_lugar  # "Sala Entel": se conserva en la descripción
        nombre_lugar = str(sede.get("lugar") or nombre_lugar)
        direccion = str(sede.get("direccion") or direccion)
        comuna = str(sede.get("comuna") or "")
    else:
        comuna = detectar_comuna(direccion, nombre_lugar, sede_texto,
                                 fuente.get("comuna", ""))
        todo_lugar = _plano(f"{nombre_lugar} {direccion} {sede_texto}")
        if any(_plano(str(p)) in todo_lugar for p in (fuente.get("lugares_sin_comuna") or [])):
            comuna = ""

    # -- cuánto ------------------------------------------------------------
    if leido["precio"]:
        precio, gratis, texto_precio = parsear_precio(leido["precio"])
        texto_precio = texto_precio or leido["precio"][:60]
    elif base:
        precio, gratis, texto_precio = base.precio_clp, base.es_gratis, base.precio_texto
    else:
        precio, gratis, texto_precio = None, None, ""

    descripcion = (leido["descripcion"] or (base.descripcion_corta if base else "")
                   or _meta(sopa, "og:description") or _meta(sopa, "description"))
    if sala:
        descripcion = f"{sala} · {descripcion}" if descripcion else sala

    imagen = (base.imagen_url if base else "") or _meta(sopa, "og:image")
    if not imagen.startswith("http"):
        imagen = ""

    return Evento(
        titulo=titulo,
        categoria=limpiar_html(leido["categoria"])[:40],
        descripcion_corta=resumir(descripcion),
        inicio=inicio,
        fin=fin,
        todo_el_dia=(inicio.hour == 0 and inicio.minute == 0),
        lugar_nombre=nombre_lugar or fuente.get("nombre", ""),
        lugar_direccion=direccion,
        comuna=comuna,
        precio_clp=precio,
        es_gratis=gratis,
        precio_texto=texto_precio,
        fuente_tipo="fichas",
        fuente_nombre=fuente.get("nombre", ""),
        fuente_url=url,
        imagen_url=imagen,
    )


def extraer_fichas(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    entradas = _fichas_del_listado(fuente, cliente)

    descartar = [_plano(str(p)) for p in (fuente.get("descartar_tarjeta") or [])]
    if descartar:
        antes = len(entradas)
        entradas = [(url, texto) for url, texto in entradas
                    if not any(palabra in _plano(texto) for palabra in descartar)]
        if antes - len(entradas):
            log.info("%s: %d tarjetas descartadas sin abrir (%s)", fuente.get("nombre"),
                     antes - len(entradas), ", ".join(fuente.get("descartar_tarjeta")))

    tope = int(fuente.get("tope_fichas", 60))
    entradas = entradas[:tope]
    log.info("%s: %d fichas a abrir desde el listado", fuente.get("nombre"), len(entradas))

    eventos: list[Evento] = []
    sin_fecha = 0
    for url, _texto in entradas:
        ficha = cliente.obtener(url, max_edad_cache_seg=24 * 3600)
        if ficha is None or not ficha.ok:
            continue
        evento = _evento_de_ficha(url, ficha.text, fuente)
        if evento is None:
            sin_fecha += 1
            log.debug("%s: ficha sin fecha legible — %s", fuente.get("nombre"), url)
            continue
        eventos.append(evento)

    log.info("%s: %d eventos desde %d fichas%s", fuente.get("nombre"), len(eventos),
             len(entradas), f" ({sin_fecha} sin fecha legible)" if sin_fecha else "")
    return eventos
