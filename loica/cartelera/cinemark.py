"""La cartelera de Cinemark por su BFF público: la semana entera, no tres días.

El JSON-LD de las páginas de sala (ver jsonld.py) fue la primera vía, y tiene
un techo que no es nuestro pero tampoco es el de Cinemark: la página solo
publica la SEMANA DE CINE en curso —que en Chile corre de jueves a miércoles—
así que un lunes trae tres días y un miércoles trae uno. La app de Cinemark
muestra más, y de dónde lo saca es de su BFF (bff.cinemark.cl), que resultó
estar abierto: responde 200 a nuestro user-agent identificado, sin cookie, sin
token y sin API key (medido el 25-08-2026). Es la misma clase de fuente que el
JSON de Bci o el Contentful de Falabella en descuentos: dato público servido
en JSON, leído con permiso implícito y crawl-delay.

Lo que entrega, y por qué vale el cambio de vía:

  /api/cinema/theaters       las 22 salas con id, slug, dirección y COORDENADAS
  /api/cinema/showtimes      todas las funciones cargadas por sala — la semana
                             completa Y las preventas (hoy llega hasta octubre)
  /api/cinema/movies         el catálogo con clasificación y duración
  /api/cinema/movies/slug/·  la ficha: SINOPSIS, TRÁILER, géneros, reparto

Además el showtimes declara el IDIOMA de cada función ("Doblada"/"Subtitulada"),
que en el JSON-LD no existía y había que adivinar desde la ficha — y solo
cuando la película se daba en un idioma único.

La trampa horaria es la misma de siempre: `sessionDateTime` dice
"2026-08-25T12:00:00.000Z" y esa Z es mentira — las 12:00 son las 12:00 de
Chile (la hora de apertura de la sala un día de semana, verificado contra sus
propios horarios publicados). Se leen los primeros 16 caracteres como hora
local y punto.

Si el BFF deja de responder, esta vía cae sola al JSON-LD de las páginas, que
sigue siendo verdad — solo que más corta.
"""

from __future__ import annotations

import logging
from datetime import datetime

from ..cines import por_cartelera
from ..modelo import es_url_publica
from ..red import ClienteEducado
from . import jsonld
from .modelo import Cartelera, Funcion, clave_pelicula, normalizar_idioma, titulo_legible

log = logging.getLogger("loica.cartelera.cinemark")

BFF = "https://bff.cinemark.cl/api/cinema"
# Cinemark opera el mismo BFF para varios países y desde el 25-08-2026 pide que
# se lo digan: sin esta cabecera la ficha de la película responde 500 con
# "Country undefined not implemented". Las salas y los horarios siguen
# contestando sin ella —tenían un valor por omisión que la ficha perdió— pero
# se manda en las cuatro llamadas, que es lo que el sitio de ellos manda y lo
# que evita que el próximo endpoint que endurezcan nos deje sin sinopsis otra
# vez. Como parámetro en la query NO sirve: probado con ?country=CL y sigue en
# 500. Va en la cabecera.
PAIS = {"country": "CL"}
# La cartelera de la SALA: apretar un horario del Alto Las Condes tiene que
# dejar al usuario en la cartelera del Alto Las Condes, no en la página de la
# película con las 22 salas para volver a elegir. La página de /compra-entradas
# redirige justamente a esa página genérica, así que no sirve.
CARTELERA_SALA = "https://www.cinemark.cl/cartelera/{slug}"


def _salas() -> list[dict]:
    # Acepta la marca nueva y la vieja del catastro: durante la transición
    # config/cines.yaml puede decir cualquiera de las dos.
    vistas, salida = set(), []
    for sala in por_cartelera("cinemark") + por_cartelera("jsonld"):
        if sala["id"] not in vistas:
            vistas.add(sala["id"])
            salida.append(sala)
    return salida


def _json(cliente: ClienteEducado, url: str, edad: int) -> dict | list | None:
    respuesta = cliente.obtener(url, max_edad_cache_seg=edad, cabeceras=PAIS)
    if respuesta is None or not respuesta.ok:
        return None
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return None
    return cuerpo.get("data") if isinstance(cuerpo, dict) else cuerpo


def _fecha(crudo: str) -> datetime | None:
    if not crudo or len(crudo) < 16:
        return None
    try:
        return datetime.strptime(crudo[:16], "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


def extraer(cliente: ClienteEducado) -> Cartelera:
    salida = Cartelera()
    salas = _salas()
    if not salas:
        return salida

    # Las 22 salas del BFF, para casar su id numérico con nuestro catastro.
    # El slug del BFF ES el id del catastro (el catastro se construyó desde la
    # lista oficial de Cinemark, que usa los mismos slugs).
    teatros = _json(cliente, f"{BFF}/theaters", 24 * 3600)
    if not isinstance(teatros, list) or not teatros:
        salida.notas.append("Cinemark: el BFF no entregó las salas — caigo al JSON-LD de las páginas")
        return jsonld.extraer(cliente)

    id_bff = {t.get("slug"): str(t.get("id")) for t in teatros if t.get("slug")}

    # El catálogo una vez: clasificación, duración y slug, casados por
    # corporateId, que viaja en cada función.
    catalogo = _json(cliente, f"{BFF}/movies", 6 * 3600)
    por_corporate = {m.get("corporateId"): m for m in catalogo or [] if isinstance(m, dict)}

    corporates_vistos: set[str] = set()
    for sala in salas:
        teatro = id_bff.get(sala["id"])
        if not teatro:
            salida.salas_fallidas.append(f"{sala['nombre']}: sin id en el BFF")
            continue

        funciones = _json(cliente, f"{BFF}/showtimes?theater={teatro}", 6 * 3600)
        if not isinstance(funciones, list):
            salida.salas_fallidas.append(f"{sala['nombre']}: el BFF no respondió showtimes")
            continue

        cuantas = 0
        for f in funciones:
            if not isinstance(f, dict):
                continue
            titulo = (f.get("movieName") or "").strip()
            inicio = _fecha(f.get("sessionDateTime") or "")
            if not titulo or inicio is None:
                continue
            ficha = por_corporate.get(f.get("corporateId")) or {}
            slug = ficha.get("slug") or ""
            corporates_vistos.add(f.get("corporateId"))
            salida.funciones.append(Funcion(
                pelicula=titulo_legible(titulo),
                cine_id=sala["id"],
                inicio=inicio,
                formato=(f.get("sessionFormat") or "").strip(),
                idioma=normalizar_idioma(((f.get("language") or {}).get("name")) or ""),
                sala=str(f.get("theaterRoom") or ""),
                # A la cartelera de ESTA sala; el slug de la sala es el id.
                url=CARTELERA_SALA.format(slug=sala["id"]),
                poster=(ficha.get("posterUrl") or "").strip()
                       if es_url_publica(ficha.get("posterUrl") or "") else "",
                duracion_min=ficha.get("runTime") if isinstance(ficha.get("runTime"), int) else None,
                clasificacion=(ficha.get("rating") or "").strip(),
                fuente="cinemark",
            ))
            cuantas += 1
        if cuantas:
            salida.salas_leidas += 1
            log.info("  %s: %d funciones", sala["nombre"], cuantas)
        else:
            salida.salas_fallidas.append(f"{sala['nombre']}: el BFF respondió sin funciones")

    if not salida.funciones:
        salida.notas.append("Cinemark: el BFF quedó en cero — caigo al JSON-LD de las páginas")
        return jsonld.extraer(cliente)

    _fichas(cliente, salida, corporates_vistos, por_corporate)
    return salida


def _fichas(cliente: ClienteEducado, salida: Cartelera,
            corporates: set, por_corporate: dict) -> None:
    """Sinopsis, tráiler y géneros de cada película en cartelera.

    Una petición por PELÍCULA —unas treinta— contra las miles de funciones que
    describen. Se guardan aparte de las funciones porque son de la película, y
    la página los usa para el presentador: la Cabra no puede contar de qué se
    trata una película si nadie se lo dijo.
    """
    for corporate in corporates:
        ficha = por_corporate.get(corporate) or {}
        slug = ficha.get("slug")
        if not slug:
            continue
        detalle = _json(cliente, f"{BFF}/movies/slug/{slug}", 24 * 3600)
        if not isinstance(detalle, dict):
            continue
        clave = clave_pelicula(detalle.get("title") or ficha.get("title") or "")
        if not clave:
            continue
        trailer = (detalle.get("trailerUrl") or "").strip()
        salida.fichas[clave] = {
            "sinopsis": (detalle.get("synopsis") or "").strip(),
            "trailer": trailer if es_url_publica(trailer) else "",
            "generos": [g.get("name", "") for g in detalle.get("genres") or []
                        if isinstance(g, dict) and g.get("name")],
        }
    log.info("  fichas con sinopsis y tráiler: %d", len(salida.fichas))
