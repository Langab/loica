"""Las fichas de las películas del Normandie, desde su propio WordPress.

La cartelera del Normandie —la que lee `semanal.py`— es una lista de horas con
un título y un link de compra, y nada más: ni afiche, ni duración, ni de qué se
trata. Pero el cine SÍ escribe todo eso; lo escribe en otra parte de su sitio,
un post por película con dirección, país, año, calificación, duración, sinopsis
y el tráiler embebido.

Ese sitio es WordPress y tiene su API REST abierta (`/wp-json/wp/v2/posts`):
dato público servido en JSON, la misma clase de fuente que el BFF de Cinemark o
el Contentful de Falabella en descuentos. Se lee por ahí y no raspando el HTML
de cada página porque es más barato para el cine —un JSON de 60 KB contra doce
páginas completas— y más estable para nosotros. Su robots.txt solo cierra
/wp-admin/ (verificado el 25-08-2026).

Por qué esto no es adorno: la vista "Qué ver" de la página muestra carátula y
sinopsis, y hasta acá el circuito de barrio salía en blanco mientras las
cadenas salían completas. Un cine que aparece sin nada que leer no se elige, y
la razón no era que el Normandie no publicara: era que nosotros no lo
habíamos ido a buscar.

Lo que se puede y lo que no, MEDIDO sobre la cartelera del 25-08-2026 (27
títulos distintos en dos semanas):

  16 tienen post con ficha completa.
  11 son clásicos de repertorio —Taxi Driver, 2046, El exorcista, Batman— que
     el cine programa sin escribirles nada. Ésos quedan sin ficha, y eso es
     una respuesta: el hueco es del cine, no del índice.

La regla dura del calce está acá y vale la pena escribirla: **el título se
calza EXACTO, normalizado**. Nada de parecidos. En el archivo hay un post
"The Batman" (2022) y la cartelera de esta semana da "Batman" (1989): un calce
por contención le pondría a Tim Burton la sinopsis de Matt Reeves, que es
exactamente la clase de error que nadie revisa porque la ficha se ve bien. La
única relajación permitida es sacarle al título una coletilla de VERSIÓN
("– Versión extendida", "(Corte del director)"), que no cambia de película.
"""

from __future__ import annotations

import logging
import re

from ..modelo import es_url_publica
from ..normalizar import limpiar_html
from ..red import ClienteEducado
from .modelo import Cartelera, clave_pelicula

log = logging.getLogger("loica.cartelera.normandie")

API = "https://normandie.cl/wp-json/wp/v2"
CINE = "cine-arte-normandie"

# El índice se pide entero una vez al día: son 1166 posts en 12 páginas de
# 100, pero pidiendo solo el id y el título son unos 70 KB en total. Filtrar
# por la categoría "peliculas" ahorraría tres páginas y costaría tres
# películas: "Possession" y "The Rocky horror picture show" viven solo en
# "re-estreno" y "La guerra de los últimos" solo en "próximamente".
#
# El tope existe para que un sitio que crezca no nos tenga pidiendo páginas
# para siempre, y cuando se alcance lo que se pierde son los posts MÁS VIEJOS
# —la API entrega del más nuevo al más antiguo—, que es exactamente el orden
# en que hay que perderlos.
PAGINAS_INDICE = 14

# Un post de película se reconoce por su ficha, no por su categoría: las tres
# categorías que las guardan se mezclan con noticias y críticas, y un post de
# noticias titulado igual que una película le pegaría una ficha que no es. Si
# no dice quién la dirigió, no es una ficha de película.
FICHA = re.compile(r"direcci[oó]n\s*:", re.I)

# Las etiquetas de la ficha, para saber qué línea es dato y cuál es sinopsis.
# El cine escribió sus posts de dos maneras a lo largo de catorce años: los
# nuevos meten los cinco campos en un párrafo separados por <br>, y los viejos
# ponen un párrafo por campo y agregan reparto y GÉNERO, que los nuevos ya no
# traen. Las dos formas se leen igual una vez que el texto conserva sus saltos.
ETIQUETAS = re.compile(
    r"^(direcci[oó]n|pa[ií]s|a[nñ]o|calificaci[oó]n|duraci[oó]n|g[eé]nero|"
    r"actores(\s+principales)?|reparto|gui[oó]n|fotograf[ií]a|m[uú]sica|montaje|"
    r"productora|estreno|t[ií]tulo\s+original|idioma|origen)\s*:", re.I)


def _lineas(html: str) -> str:
    """El texto del post CON sus saltos de línea.

    `limpiar_html` no sirve para esto y ése fue el bicho: colapsa todos los
    blancos, saltos incluidos, y los cinco datos de la ficha viajan en un solo
    párrafo con <br> entre medio. Sin los saltos, un campo vacío —"Calificación:"
    a secas, que el cine deja así seguido— se come la línea siguiente: la
    clasificación de Calle Málaga quedaba en "Duración: 11" y la duración de La
    Odisea en 10 minutos, robados de un "viaje de 10 años" de la sinopsis.
    """
    # Solo etiquetas COMPLETAS y de cierre: partir en `<figure` —que era lo
    # que hacía— corta la etiqueta por la mitad, el limpiador ya no la
    # reconoce como etiqueta y sus atributos terminan de texto adentro de la
    # sinopsis ("…tras la guerra de Troya. class=\"wp-block-embed-youtube\"").
    con_saltos = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</figure>", "\n", html or "")
    return "\n".join(limpiar_html(linea) for linea in con_saltos.split("\n"))


def _campo(texto: str, etiqueta: str) -> str:
    """El valor de un campo de la ficha, hasta el final de SU línea.

    El `[^\S\n]*` de después de los dos puntos es a propósito: con `\s*` el
    espacio en blanco incluye el salto de línea y un campo vacío se lleva el
    valor del que sigue.
    """
    m = re.search(rf"{etiqueta}\s*:[^\S\n]*([^\n]*)", texto, re.I)
    # El punto NO se saca: es parte de "T.E." y de "U.K.", que son el valor.
    return m.group(1).strip(" ·-–—") if m else ""


def _sinopsis(lineas: str) -> str:
    """Lo que queda del post cuando se le sacan los datos y los letreros."""
    prosa = []
    for linea in lineas.split("\n"):
        if not linea or ETIQUETAS.match(linea):
            continue
        if ">>" in linea or linea.upper().startswith("CARTELERA"):
            continue
        # Un letrero, no una sinopsis: "REESTRENO – VERSIÓN REMATERIZADA".
        # Corto y a gritos; ninguna sinopsis de verdad viene en mayúsculas.
        if len(linea) < 60 and linea == linea.upper():
            continue
        prosa.append(linea)
    return " ".join(prosa)[:900]


# El tráiler viene embebido; lo que se guarda es la dirección para MIRARLO,
# que es a donde manda la página. Se aceptan los dos incrustadores conocidos y
# ningún otro, igual que en el CSV asistido.
_YOUTUBE = re.compile(r"youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{6,20})")
_VIMEO = re.compile(r"player\.vimeo\.com/video/(\d{6,12})")

# Coletillas de versión: no cambian de película, así que se pueden sacar para
# volver a buscar. Cualquier otra cola se respeta — "Backrooms" y "Backrooms 2"
# no son la misma.
_VERSION = re.compile(
    r"\b(versi[oó]n\s+\w+|corte\s+del\s+director|director'?s\s+cut|"
    r"remasterizada|rematerizada|restaurada|extendida|final\s+cut|"
    r"doblada(\s+al\s+espa[nñ]ol)?|subtitulada|\d{1,2}k)\b", re.I)


def _trailer(html: str) -> str:
    m = _YOUTUBE.search(html or "")
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    m = _VIMEO.search(html or "")
    return f"https://vimeo.com/{m.group(1)}" if m else ""


def _sin_version(titulo: str) -> str:
    """"Backrooms – Versión extendida" → "backrooms", o "" si no había cola."""
    for separador in (" – ", " — ", " - ", ":"):
        if separador in (titulo or ""):
            cabeza, cola = titulo.split(separador, 1)
            if _VERSION.search(cola) and cabeza.strip():
                return clave_pelicula(cabeza)
    return ""


def _indice(cliente: ClienteEducado) -> dict[str, int]:
    """{clave de película: id del post} con todo lo que el cine ha publicado."""
    indice: dict[str, int] = {}
    for pagina in range(1, PAGINAS_INDICE + 1):
        respuesta = cliente.obtener(
            f"{API}/posts?per_page=100&page={pagina}&_fields=id,title",
            max_edad_cache_seg=24 * 3600)
        if respuesta is None or not respuesta.ok:
            break
        try:
            posts = respuesta.json()
        except ValueError:
            break
        if not posts:
            break
        for post in posts:
            titulo = limpiar_html(((post.get("title") or {}).get("rendered") or ""))
            clave = clave_pelicula(titulo)
            # El primero gana: la API devuelve del más nuevo al más viejo y la
            # reposición de un clásico trae la ficha reescrita.
            if clave and clave not in indice:
                indice[clave] = post.get("id")
    return indice


def _detalles(cliente: ClienteEducado, ids: set[int]) -> dict[int, dict]:
    """El cuerpo de los posts que interesan, en una petición."""
    if not ids:
        return {}
    lista = ",".join(str(i) for i in sorted(ids))
    respuesta = cliente.obtener(
        f"{API}/posts?include={lista}&per_page=100"
        f"&_fields=id,title,link,content,featured_media",
        max_edad_cache_seg=12 * 3600)
    if respuesta is None or not respuesta.ok:
        return {}
    try:
        posts = respuesta.json()
    except ValueError:
        return {}
    return {p.get("id"): p for p in posts if isinstance(p, dict)}


def _afiches(cliente: ClienteEducado, ids: set[int]) -> dict[int, str]:
    """La imagen destacada de cada post.

    Son fotogramas apaisados (593×390), no afiches verticales: el Normandie no
    publica el afiche. Sirven igual —la tarjeta los recorta al centro, que en
    un fotograma es donde está lo que importa— y una imagen de la película es
    muchísimo más que la claqueta genérica que iba antes.
    """
    ids = {i for i in ids if i}
    if not ids:
        return {}
    lista = ",".join(str(i) for i in sorted(ids))
    respuesta = cliente.obtener(
        f"{API}/media?include={lista}&per_page=100&_fields=id,source_url",
        max_edad_cache_seg=24 * 3600)
    if respuesta is None or not respuesta.ok:
        return {}
    try:
        medios = respuesta.json()
    except ValueError:
        return {}
    return {m.get("id"): (m.get("source_url") or "") for m in medios
            if isinstance(m, dict)}


def _minutos(texto: str) -> int | None:
    m = re.search(r"(\d{2,3})", texto or "")
    if not m:
        return None
    valor = int(m.group(1))
    return valor if 0 < valor < 600 else None


def _ficha(post: dict, afiche: str) -> dict:
    """Lo que se puede leer de un post: la ficha de la película."""
    crudo = (post.get("content") or {}).get("rendered") or ""
    plano = _lineas(crudo)

    director = _campo(plano, "direcci[oó]n")
    pais = _campo(plano, "pa[ií]s")
    anio = _campo(plano, "a[nñ]o")
    # El género solo lo traen los posts viejos, y cuando está es exactamente lo
    # que la tarjeta muestra como pastillas.
    generos = [g.strip() for g in _campo(plano, "g[eé]nero").split(",") if g.strip()]
    return {
        "sinopsis": _sinopsis(plano),
        "trailer": _trailer(crudo),
        "generos": generos[:3],
        # El crédito reemplaza al género, que este cine no publica y que
        # tampoco es lo que hace elegir acá: en una sala de repertorio quién
        # la dirigió y de qué país y año es JUSTAMENTE el dato que decide.
        "credito": " · ".join(x for x in (director, pais, anio) if x)[:120],
        "duracion_min": _minutos(_campo(plano, "duraci[oó]n")),
        "clasificacion": _campo(plano, "calificaci[oó]n")[:12],
        "poster": afiche if es_url_publica(afiche) else "",
    }


def enriquecer(cliente: ClienteEducado, cartelera: Cartelera) -> None:
    """Le pone ficha a las funciones del Normandie, en su sitio.

    Modifica la cartelera recibida: las funciones ganan afiche, duración y
    calificación, y `cartelera.fichas` gana la sinopsis, el tráiler y el
    crédito. Si la API no responde, no pasa nada malo — las funciones se
    publican como salieron, que es el dato que de verdad importa.
    """
    funciones = [f for f in cartelera.funciones if f.cine_id == CINE]
    if not funciones:
        return

    indice = _indice(cliente)
    if not indice:
        cartelera.notas.append("Normandie: no pude leer su archivo de películas")
        return

    # Qué post le toca a cada película de la cartelera. Una vez por película,
    # no por función: las cuatro funciones de Totoro comparten ficha.
    post_de: dict[str, int] = {}
    for funcion in funciones:
        clave = funcion.clave
        if clave in post_de:
            continue
        identificador = indice.get(clave) or indice.get(_sin_version(funcion.pelicula))
        if identificador:
            post_de[clave] = identificador

    detalles = _detalles(cliente, set(post_de.values()))
    afiches = _afiches(cliente, {(detalles.get(i) or {}).get("featured_media")
                                 for i in post_de.values()})

    fichas: dict[str, dict] = {}
    for clave, identificador in post_de.items():
        post = detalles.get(identificador)
        if post is None:
            continue
        crudo = (post.get("content") or {}).get("rendered") or ""
        if not FICHA.search(_lineas(crudo)):
            # Calzó el título pero el post no es una ficha de película: una
            # noticia, una crítica, el aviso de un ciclo. Se descarta entero.
            continue
        fichas[clave] = _ficha(post, afiches.get(post.get("featured_media"), ""))

    for funcion in funciones:
        ficha = fichas.get(funcion.clave)
        if not ficha:
            continue
        funcion.poster = funcion.poster or ficha["poster"]
        funcion.duracion_min = funcion.duracion_min or ficha["duracion_min"]
        funcion.clasificacion = funcion.clasificacion or ficha["clasificacion"]

    for clave, ficha in fichas.items():
        if clave not in cartelera.fichas:
            cartelera.fichas[clave] = {k: ficha[k] for k in
                                       ("sinopsis", "trailer", "generos", "credito")}

    con_sinopsis = sum(1 for f in fichas.values() if f["sinopsis"])
    peliculas = len({f.clave for f in funciones})
    log.info("  Normandie: %d de %d películas con ficha (%d con sinopsis)",
             len(fichas), peliculas, con_sinopsis)
    if peliculas > len(fichas):
        cartelera.notas.append(
            f"Normandie: {peliculas - len(fichas)} de {peliculas} películas sin ficha "
            "— son repertorio y el cine no les escribe página")
