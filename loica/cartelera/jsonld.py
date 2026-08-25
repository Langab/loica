"""Carteleras publicadas como dato estructurado (schema.org ScreeningEvent).

Cinemark deja en el HTML de cada sala un bloque JSON-LD `MovieTheater` con un
`ScreeningEvent` por función: la película, la hora, el formato, el afiche y el
link donde se compra. No es un raspado: es el dato que ellos mismos publican
para que las máquinas lo lean, con su propio vocabulario estándar.

Que sea dato estructurado tiene una consecuencia práctica que decidió media
arquitectura de esta página: se lee con `requests` y punto. Sin navegador, sin
huella de sesión, sin nada que no pueda correr en el runner de GitHub Actions
a las once de la mañana.

El bloque viaja escapado dentro del payload de Next (`self.__next_f.push`), no
en un `<script type="application/ld+json">` normal, así que hay que
desescaparlo antes de buscarlo. Se acepta cualquiera de las dos formas: si
mañana Cinemark lo pone en una etiqueta como corresponde, esto sigue
funcionando.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from ..cines import por_cartelera
from ..modelo import es_url_publica
from ..red import ClienteEducado
from .modelo import Cartelera, Funcion, normalizar_idioma, titulo_legible

log = logging.getLogger("loica.cartelera.jsonld")

# "PT2H24M" → 144 minutos.
DURACION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?")


def _minutos(duracion: str) -> int | None:
    m = DURACION.fullmatch((duracion or "").strip())
    if not m or not any(m.groups()):
        return None
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)


def _fecha(crudo: str) -> datetime | None:
    """La hora local de la función.

    Cinemark escribe `2026-08-24T17:50:00.000Z-05:00`, que no es una fecha
    ISO válida: lleva la Z de UTC Y un desfase horario, dos cosas que se
    contradicen. Los primeros 19 caracteres sí son la hora local de Chile —la
    misma que muestran en pantalla— y es la única lectura que no corre las
    funciones tres horas. Interpretarla como UTC dejaría la última función del
    día publicada al día siguiente.
    """
    if not crudo or len(crudo) < 19:
        return None
    try:
        return datetime.strptime(crudo[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _bloques_jsonld(html: str) -> list[dict]:
    """Todos los objetos JSON-LD del HTML, vengan como vengan.

    Sin deduplicar salen triplicados: Next manda el mismo payload en la
    respuesta del servidor y otra vez en el flight de hidratación, así que el
    bloque aparece tres veces y las funciones se contaban por tres. La copia
    posterior se descarta por su texto normalizado, no por identidad.
    """
    bloques: list[dict] = []
    vistos: set[str] = set()

    def agregar(objeto) -> None:
        if not isinstance(objeto, dict):
            return
        huella = json.dumps(objeto, sort_keys=True, ensure_ascii=False)
        if huella in vistos:
            return
        vistos.add(huella)
        bloques.append(objeto)

    for crudo in re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.S | re.I):
        try:
            agregar(json.loads(crudo))
        except ValueError:
            continue

    # El de Next viene escapado dentro de un string de JavaScript. Se
    # desescapa el HTML entero una vez y se recorta el objeto contando llaves,
    # ignorando las que estén dentro de un string (un título con "{" existe).
    plano = html.replace('\\"', '"').replace("\\u003c", "<").replace("\\n", " ")
    for inicio in [m.start() for m in re.finditer(r'\{"@context"', plano)]:
        profundidad = 0
        dentro = escapado = False
        for i, letra in enumerate(plano[inicio:inicio + 400_000]):
            if escapado:
                escapado = False
                continue
            if letra == "\\":
                escapado = True
                continue
            if letra == '"':
                dentro = not dentro
                continue
            if dentro:
                continue
            if letra == "{":
                profundidad += 1
            elif letra == "}":
                profundidad -= 1
                if profundidad == 0:
                    try:
                        agregar(json.loads(plano[inicio:inicio + i + 1]))
                    except ValueError:
                        pass
                    break
    return bloques


def _funciones_del_bloque(bloque: dict, cine: dict) -> list[Funcion]:
    if not isinstance(bloque, dict) or bloque.get("@type") != "MovieTheater":
        return []

    funciones = []
    for evento in bloque.get("event") or []:
        if not isinstance(evento, dict) or evento.get("@type") != "ScreeningEvent":
            continue
        pelicula = (evento.get("workPresented") or {})
        titulo = (pelicula.get("name") or "").strip()
        inicio = _fecha(evento.get("startDate") or "")
        if not titulo or inicio is None:
            continue

        compra = ((evento.get("offers") or {}).get("url") or "").strip()
        # Regla de la casa: nada que no sea http(s) llega a un href. El link
        # de compra es el que va a apretar una persona.
        if not es_url_publica(compra):
            compra = cine.get("url", "")

        afiche = (pelicula.get("image") or "").strip()
        if not es_url_publica(afiche):
            afiche = ""

        # "Cinemark Alto Las Condes - 4": el número de sala es lo único que
        # aporta, el resto ya lo sabemos por el catastro.
        sala = ((evento.get("location") or {}).get("name") or "")
        sala = sala.split(" - ")[-1].strip() if " - " in sala else ""

        formato = (evento.get("videoFormat") or "").strip()
        funciones.append(Funcion(
            pelicula=titulo_legible(titulo),
            cine_id=cine["id"],
            inicio=inicio,
            formato=formato,
            # El JSON-LD no declara el idioma; en la cadena que lo publica el
            # dato vive solo en la pantalla. Vacío es la respuesta honesta.
            idioma=normalizar_idioma(formato),
            sala=sala,
            url=compra,
            poster=afiche,
            duracion_min=_minutos(pelicula.get("duration") or ""),
            clasificacion=(pelicula.get("contentRating") or "").strip(),
            fuente=cine.get("cadena", ""),
        ))
    return funciones


# La ficha de la película trae dos datos que el JSON-LD de la cartelera no
# tiene y que en una página de cine son filtros, no adorno: la clasificación
# ("TE", "TE+7", "MA14") y en qué idiomas se está dando. Viven en el payload
# de Next de /pelicula/<slug> como JSON plano.
FICHA_CATEGORIA = re.compile(r'"category":"([^"]{1,12})"')
FICHA_IDIOMAS = re.compile(r'"languages":\[(.*?)\]', re.S)
FICHA_ETIQUETA = re.compile(r'"label":"([^"]{1,24})"')


def _ficha_de_pelicula(cliente: ClienteEducado, url_compra: str) -> tuple[str, str]:
    """(clasificación, idioma) de la película, o dos vacíos.

    El idioma solo se devuelve cuando la película se está dando en UNO solo:
    si está en doblada Y subtitulada, cuál es cada función es algo que esta
    página no sabe, y adivinarlo sería mandar a alguien a la versión que no
    quería. Vacío es la respuesta honesta.
    """
    # ".../pelicula/spider-man-un-nuevo-dia/compra-entradas/entradas" → la ficha
    ficha = re.sub(r"/compra-entradas/.*$", "", url_compra or "")
    if "/pelicula/" not in ficha:
        return "", ""

    respuesta = cliente.obtener(ficha, max_edad_cache_seg=24 * 3600)
    if respuesta is None or not respuesta.ok:
        return "", ""

    plano = respuesta.text.replace('\\"', '"')
    categoria = FICHA_CATEGORIA.search(plano)
    idiomas = FICHA_IDIOMAS.search(plano)
    etiquetas = FICHA_ETIQUETA.findall(idiomas.group(1)) if idiomas else []
    unico = normalizar_idioma(etiquetas[0]) if len(etiquetas) == 1 else ""
    return (categoria.group(1) if categoria else ""), unico


def extraer(cliente: ClienteEducado) -> Cartelera:
    salida = Cartelera()
    # Acepta la marca nueva y la vieja: desde que el BFF es la vía primaria,
    # el catastro dice "cinemark" y este módulo queda de respaldo.
    salas = {c["id"]: c for c in por_cartelera("jsonld") + por_cartelera("cinemark")}
    for cine in salas.values():
        url = cine.get("url") or ""
        if not url:
            salida.salas_fallidas.append(f"{cine['nombre']}: sin url en el catastro")
            continue

        # Seis horas: la cartelera del día no cambia, pero los estrenos de los
        # jueves sí, y una corrida de la tarde no puede quedarse con la caché
        # de la mañana.
        respuesta = cliente.obtener(url, max_edad_cache_seg=6 * 3600)
        if respuesta is None or not respuesta.ok:
            codigo = respuesta.status_code if respuesta is not None else "sin respuesta"
            salida.salas_fallidas.append(f"{cine['nombre']}: {codigo}")
            continue

        funciones = []
        for bloque in _bloques_jsonld(respuesta.text):
            funciones.extend(_funciones_del_bloque(bloque, cine))

        if not funciones:
            salida.salas_fallidas.append(f"{cine['nombre']}: sin ScreeningEvent en la página")
            continue

        salida.salas_leidas += 1
        salida.funciones.extend(funciones)
        log.info("  %s: %d funciones", cine["nombre"], len(funciones))

    _enriquecer(cliente, salida)
    return salida


def _enriquecer(cliente: ClienteEducado, salida: Cartelera) -> None:
    """Una petición por PELÍCULA, no por función.

    Son unas treinta fichas contra las seiscientas funciones que hay en
    cartelera: se pide una vez por película y el resultado se reparte. Si la
    ficha no responde, la función se publica igual sin clasificación — el
    horario es el dato que importa y no se pierde por un adorno.
    """
    cache: dict[str, tuple[str, str]] = {}
    for funcion in salida.funciones:
        if funcion.clasificacion and funcion.idioma:
            continue
        llave = re.sub(r"/compra-entradas/.*$", "", funcion.url or "")
        if llave not in cache:
            cache[llave] = _ficha_de_pelicula(cliente, funcion.url)
        clasificacion, idioma = cache[llave]
        funcion.clasificacion = funcion.clasificacion or clasificacion
        funcion.idioma = funcion.idioma or idioma
    con_datos = sum(1 for f in salida.funciones if f.clasificacion)
    log.info("  fichas de película: %d consultadas, %d funciones con clasificación",
             len(cache), con_datos)
