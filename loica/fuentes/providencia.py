"""Adaptador para la agenda de actividades de la Municipalidad de Providencia.

El sitio municipal corre sobre un CMS de gobierno antiguo (rutas del tipo
/provi/site/... y /provi/explora/...) que no ofrece API, sitemap, RSS ni
JSON-LD de eventos. Su agenda visible (/provi/explora/actividades/) responde
200 con el cuerpo vacío —por eso la fuente vivió apagada—, pero lo que esa
página arma con JavaScript sale renderizado en el servidor en un fragmento
aparte: /provi/site/list/port/actividades_mes.html, ~800 KB con las últimas
mil tarjetas.

Cada tarjeta trae lo que hace falta para publicar sin abrir nada más: título,
recinto, link a la ficha, imagen y el día. Los atributos engañan, eso sí:

  - `data_fecha="20260831"` es la fecha de PUBLICACIÓN (coincide con el
    `fechap` de la ficha), no la del evento.
  - El día del evento va en `data_mes` y `data_dia`. Cuando `data_dia` es
    "0", la actividad ocupa el mes entero y el rótulo dice cómo: "Todos los
    Martes del mes", "Todo el mes", "De Lunes a Sábado", "Todos los días.
    Del 5 al 30".
  - La mitad de los slugs termina en DDMMAA (`...-070926`), y esa es la única
    parte de toda la tarjeta que trae el año escrito.

La ficha agrega lo que la tarjeta calla: el horario, el valor y el cuerpo. Se
abre solo para lo vigente y hasta un tope (`tope_detalle`), de lo más próximo
a lo más lejano, porque el runner de la corrida nace sin caché cada día y el
tope es lo único que acota las peticiones. Lo que queda fuera del tope se
publica igual con lo que dice la tarjeta —descubrir el evento ya es la mitad
del trabajo— y toma su hora y su precio el día en que entra en la ventana.

Para lo que dura el mes entero no se expande día por día: vigente es lo que
no ha terminado, así que una sola tarjeta con la primera y la última sesión
del mes basta, y la cadencia va escrita en la descripción para que el export
saque de ahí los `dias_semana`.
"""

from __future__ import annotations

import calendar
import logging
import re
import unicodedata
from datetime import date, datetime, time, timedelta

from bs4 import BeautifulSoup

from ..modelo import Evento
from ..normalizar import (PALABRAS_GRATIS, detectar_comuna, limpiar_html,
                          parsear_fecha, parsear_precio, resumir)
from ..recurrencia import (DIAS_SEMANA, frase_cadencia, parsear_dias, parsear_hora,
                           rango_de_sesiones)
from ..red import ClienteEducado

log = logging.getLogger("loica.providencia")

# El segmento de categoría de la URL (/actividades/<categoria>/<slug>) es una
# pista para el clasificador solo cuando dice algo. "familia" no se traduce a
# propósito: es el cajón donde el municipio mete el 85% de todo —operativos de
# la Tarjeta Vecino, exposiciones, ferias, cueca— y leerlo como "panorama
# familiar" sesgaría al clasificador justo cuando el título no dijo nada.
# "educacion" tampoco: ahí conviven charlas, cursos y ferias laborales.
CATEGORIA_POR_SEGMENTO = {
    "deporte": "deporte",
    "musica": "musica",
    "cine": "cine",
    "teatro": "teatro",
}

# Con nombre y no sacado de `MESES`: ese diccionario trae "setiembre" además
# de "septiembre" para LEER, y al darlo vuelta gana la grafía rara.
NOMBRES_MES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

_FECHA_EN_SLUG = re.compile(r"-(\d{2})(\d{2})(\d{2})$")
_SEGMENTO = re.compile(r"/actividades/([^/]+)/")
_DEL_AL = re.compile(r"\bdel\s+(\d{1,2})\s+al\s+(\d{1,2})\b")
_DE_A = re.compile(r"\bde\s+(lunes|martes|miercoles|jueves|viernes|sabado|domingo)"
                   r"\s+a\s+(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b")
_HORA = re.compile(r"\b([01]?\d|2[0-3])[:.h](\d{2})\b")
# El cuerpo de la ficha termina casi siempre en datos de contacto y en el
# botón de inscripción. Son útiles en la ficha, no en una descripción de 200
# caracteres, y le meten correos al clasificador.
_COLA_DE_CONTACTO = re.compile(r"\s*para mayor informaci[oó]n.*$|\s*INSCRIPCI[OÓ]N\s*$",
                               re.IGNORECASE | re.DOTALL)
_PARECE_DIRECCION = re.compile(r"\d{2,}|\bcon\b|\bav(da)?\.?\b|\bavenida\b|\bcalle\b|\bpasaje\b",
                               re.IGNORECASE)
_METRO_AL_FINAL = re.compile(r",?\s*metro\s+[^,;]+$", re.IGNORECASE)


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    return " ".join("".join(c for c in sin_tildes
                            if unicodedata.category(c) != "Mn").lower().split())


def _fecha_compacta(valor: str | None) -> date | None:
    """"20260831" → date. Es el formato de `data_fecha` y de `fechap`."""
    try:
        return datetime.strptime((valor or "").strip(), "%Y%m%d").date()
    except ValueError:
        return None


# -- el fragmento -----------------------------------------------------------

def _tarjetas(html: str, base: str) -> list[dict]:
    """Lee las tarjetas del fragmento tal como vienen, sin interpretarlas."""
    sopa = BeautifulSoup(html, "html.parser")
    tarjetas: list[dict] = []
    for nodo in sopa.find_all("div", attrs={"data_mes": True, "data_dia": True}):
        enlace = nodo.find("a", href=True)
        nodo_titulo = nodo.find("h4")
        if enlace is None or nodo_titulo is None:
            continue
        href = enlace["href"].strip()
        if href.startswith("/"):
            href = base + href
        elif not href.startswith("http"):
            continue
        titulo = limpiar_html(nodo_titulo.get_text(" ", strip=True))
        if not titulo:
            continue

        rotulo = nodo.select_one(".label-cat")
        recinto = nodo.find("em")
        imagen = nodo.find("img")
        src = (imagen.get("src", "") if imagen else "").strip()
        if src.startswith("/"):
            src = base + src
        segmento = _SEGMENTO.search(href)
        tarjetas.append({
            "url": href,
            "slug": href.rstrip("/").rsplit("/", 1)[-1],
            "titulo": titulo,
            "rotulo": rotulo.get_text(" ", strip=True) if rotulo else "",
            "recinto": limpiar_html(recinto.get_text(" ", strip=True)) if recinto else "",
            "imagen": src,
            "segmento": segmento.group(1) if segmento else "",
            "mes": nodo.get("data_mes", ""),
            "dia": nodo.get("data_dia", ""),
            "publicado": _fecha_compacta(nodo.get("data_fecha")),
        })
    return tarjetas


def _dias_del_rotulo(rotulo: str) -> list[int]:
    """Días de la semana (0=lunes) que nombra el rótulo de un mes entero.

    "Todos los Martes y Jueves del mes" → [1, 3]; "De Lunes a Sábado" → [0..5];
    "Todo el mes" y "Todos los días" → los siete. Lista vacía si no nombra
    ninguno: quien llama decide qué hacer con eso.
    """
    plano = _plano(rotulo)
    # "Sábados" y "domingos" son los únicos días con plural, y parsear_dias
    # busca la palabra entera: sin quitarles la ese, "Todos los Sábados del
    # mes" no encontraba ningún día.
    plano = re.sub(r"\b(sabado|domingo)s\b", r"\1", plano)
    m = _DE_A.search(plano)
    if m:
        desde, hasta = DIAS_SEMANA[m.group(1)], DIAS_SEMANA[m.group(2)]
        if desde <= hasta:
            return list(range(desde, hasta + 1))
        return list(range(desde, 7)) + list(range(0, hasta + 1))
    if re.search(r"\btodos? (el mes|los dias)\b", plano):
        return list(range(7))
    return parsear_dias(plano)


def _tramo_del_mes(anio: int, mes: int, rotulo: str) -> tuple[date, date]:
    """El mes entero, salvo que el rótulo acote: "Todos los días. Del 5 al 30"."""
    primero, ultimo = 1, calendar.monthrange(anio, mes)[1]
    m = _DEL_AL.search(_plano(rotulo))
    if m:
        desde, hasta = int(m.group(1)), int(m.group(2))
        if 1 <= desde <= hasta <= ultimo:
            primero, ultimo = desde, hasta
    return date(anio, mes, primero), date(anio, mes, ultimo)


def _cuando(tarjeta: dict, hoy: date) -> dict | None:
    """Traduce los atributos de la tarjeta a un tramo de fechas.

    Devuelve {"inicio", "fin", "dias", "mes_entero", "tramo"} con fechas (sin
    hora) —`tramo` es el trecho del mes que declara el rótulo, del que `inicio`
    y `fin` son la primera y la última sesión reales—, o None si los atributos
    no se dejan leer. El año sale del slug cuando lo
    trae; si no, de la fecha de publicación: un aviso no anuncia algo que ya
    pasó, así que una fecha más de un mes anterior a la publicación habla del
    año siguiente (los avisos de diciembre sobre enero).
    """
    try:
        mes, dia = int(tarjeta["mes"]), int(tarjeta["dia"])
    except (TypeError, ValueError):
        return None
    if not 1 <= mes <= 12:
        return None

    anio = None
    m = _FECHA_EN_SLUG.search(tarjeta["slug"])
    if m:
        anio = 2000 + int(m.group(3))
    if anio is None:
        referencia = tarjeta["publicado"] or hoy
        anio = referencia.year
        try:
            tentativa = date(anio, mes, max(dia, 1))
        except ValueError:
            return None
        if tentativa < referencia - timedelta(days=30):
            anio += 1

    if dia == 0:
        # Mes entero: la primera y la última sesión reales de ese mes, no el
        # día 1 y el 30. "Todos los martes de septiembre" empieza el primer
        # martes, y el rótulo puede acotar el tramo ("Del 5 al 30").
        try:
            primero, ultimo = _tramo_del_mes(anio, mes, tarjeta["rotulo"])
        except ValueError:
            return None
        dias = _dias_del_rotulo(tarjeta["rotulo"])
        if not dias:
            log.debug("rótulo de mes entero sin días reconocibles: %r (%s)",
                      tarjeta["rotulo"], tarjeta["slug"])
            dias = list(range(7))
        sesiones = rango_de_sesiones(dias, primero, ultimo)
        if sesiones is None:
            return None
        return {"inicio": sesiones[0].date(), "fin": sesiones[1].date(),
                "dias": dias, "mes_entero": True, "tramo": (primero, ultimo)}

    try:
        fecha = date(anio, mes, dia)
    except ValueError:
        return None
    # El rótulo suele decir solo "Sábado": si no calza con la fecha de los
    # atributos, alguien editó una cosa y no la otra. Se anota para saberlo.
    nombre_dia = _plano(tarjeta["rotulo"]).split(" ")[0] if tarjeta["rotulo"] else ""
    if nombre_dia in DIAS_SEMANA and DIAS_SEMANA[nombre_dia] != fecha.weekday():
        log.debug("el rótulo dice %s pero los atributos dan %s (%s)",
                  nombre_dia, fecha, tarjeta["slug"])
    return {"inicio": fecha, "fin": fecha, "dias": [], "mes_entero": False,
            "tramo": (fecha, fecha)}


# -- la ficha ---------------------------------------------------------------

def _leer_ficha(html: str) -> dict:
    """Los campos de la lista "Día / Horario / Valor / Inscripciones" y el cuerpo."""
    sopa = BeautifulSoup(html, "html.parser")
    campos: dict[str, str] = {}
    lista = sopa.find("ul", class_="list-dotted-green")
    if lista is not None:
        for item in lista.find_all("li"):
            etiqueta = item.find("strong")
            if etiqueta is None:
                continue
            nombre = _plano(etiqueta.get_text(" ", strip=True)).strip(": ")
            etiqueta.extract()
            # El "Día:" termina en un "de" colgado: es la etiqueta del año, que
            # el CMS deja vacía.
            valor = re.sub(r"\s+de$", "", item.get_text(" ", strip=True)).strip(" .")
            if nombre and valor:
                campos[nombre] = valor

    cuerpo = ""
    nodo_cuerpo = sopa.find("div", class_="CUERPO")
    if nodo_cuerpo is not None:
        cuerpo = _COLA_DE_CONTACTO.sub("", nodo_cuerpo.get_text(" ", strip=True)).strip()

    publicado = None
    marca = sopa.find("input", id="fechap")
    if marca is not None:
        publicado = _fecha_compacta(marca.get("value"))

    return {"campos": campos, "cuerpo": cuerpo, "publicado": publicado}


def _horas(horario: str) -> tuple[time | None, time | None]:
    """"De 20:00 a 22:00 horas." → (20:00, 22:00); "16:00" → (16:00, None)."""
    encontradas = _HORA.findall(horario or "")
    inicio = parsear_hora(horario)
    fin = None
    if inicio and len(encontradas) > 1:
        try:
            fin = time(int(encontradas[1][0]), int(encontradas[1][1]))
        except ValueError:
            fin = None
    return inicio, fin


def _precio(valor: str, cuerpo: str) -> tuple[int | None, bool | None, str]:
    """El campo "Valor:" manda; si no existe, se lee el cuerpo.

    "Pagada con y sin descuento de Tarjeta Vecino (50%)" dice que cuesta, no
    cuánto: es_gratis=False es un hecho y el monto no, así que el precio queda
    vacío. Inventarle un número rompería el filtro "solo gratis", que es la
    promesa central del producto.

    "Tarjeta vecino activa" o "Contar con tarjeta vecino vigente" en el mismo
    campo NO dicen que cueste: son un requisito para entrar. Ahí el campo no
    opina y se lee el cuerpo, como si no existiera.
    """
    if valor:
        plano = _plano(valor)
        if any(palabra in plano for palabra in PALABRAS_GRATIS):
            return 0, True, valor[:80]
        precio, gratis, texto = parsear_precio(valor)
        if precio is not None:
            return precio, gratis, texto
        if "pagad" in plano:
            return None, False, valor[:80]
    return parsear_precio(cuerpo)


def _lugar(recinto: str) -> tuple[str, str]:
    """"Biblioteca Bellavista, Constitución 85" → (nombre, dirección).

    El municipio escribe el recinto de tres maneras: solo el nombre ("Club
    Providencia"), nombre y dirección separados por coma o punto y coma, o
    la pura dirección ("Los Jesuitas 881, Providencia", "Dinamarca con Av. El
    Bosque"). Cuando el primer trozo ya es una dirección, la dirección es el
    texto completo y no el resto.
    """
    partes = re.split(r"\s*[;,]\s*", recinto.strip(), maxsplit=1)
    nombre = partes[0].strip(" .")
    resto = partes[1].strip(" .") if len(partes) > 1 else ""
    if _PARECE_DIRECCION.search(nombre):
        direccion = recinto.strip(" .")
    else:
        direccion = resto
    # ", Metro Salvador" es una indicación para llegar, no parte de la
    # dirección, y confunde al geocodificador.
    direccion = _METRO_AL_FINAL.sub("", direccion).strip(" .")
    return nombre[:120], direccion[:160]


def _frase_de_mes_entero(dias: list[int], tramo: tuple[date, date], horario: str) -> str:
    """"Todos los martes y jueves de septiembre, 16:00".

    Va a la descripción: es lo que le dice a quien lee que esto se repite, y
    de ahí saca el export los `dias_semana` mientras el modelo no tenga un
    campo propio para la recurrencia.
    """
    primero, ultimo = tramo
    mes = NOMBRES_MES[primero.month - 1]
    if len(dias) == 7:
        cuando = "todos los días"
    else:
        # "De lunes a sábado" se lee mejor, pero el export solo entiende los
        # rangos escritos con abreviaturas ("Lu a Sa") y de la frase larga
        # sacaría lunes y sábado nada más: se nombran todos los días.
        # `frase_cadencia` escribe "todos los sábado"; la ese es solo para los
        # dos días que tienen plural.
        cuando = re.sub(r"\b(sábado|domingo)\b", r"\1s", frase_cadencia(dias))
    mes_completo = primero.day == 1 and ultimo.day == calendar.monthrange(
        ultimo.year, ultimo.month)[1]
    if mes_completo:
        frase = f"{cuando} de {mes}"
    else:
        frase = f"{cuando} del {primero.day} al {ultimo.day} de {mes}"
    if horario:
        frase += f", {horario[0].lower() + horario[1:]}"
    return frase[0].upper() + frase[1:]


# -- el adaptador -----------------------------------------------------------

def extraer_providencia(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    base = fuente["url_base"].rstrip("/")
    url_listado = fuente.get("url_agenda") or (base + fuente.get("endpoint", ""))
    hoy = date.today()
    peticiones = 0

    respuesta = cliente.obtener(url_listado, max_edad_cache_seg=6 * 3600)
    peticiones += 1
    if respuesta is None or not respuesta.ok:
        log.warning("%s: no pude leer el fragmento de actividades", fuente.get("nombre"))
        return []

    tarjetas = _tarjetas(respuesta.text, base)
    if not tarjetas:
        log.warning("%s: el fragmento no trae tarjetas; ¿cambió la maquetación?",
                    fuente.get("nombre"))
        return []

    # Vigente es lo que no ha terminado. Las tarjetas pasadas no se abren ni
    # se emiten: `es_valido` las botaría igual, pero acá se ahorran las
    # peticiones. Las que no se dejan fechar se abren de todos modos, por si
    # la ficha dice lo que la tarjeta no.
    vigentes: list[tuple[dict, dict | None]] = []
    pasadas = 0
    for tarjeta in tarjetas:
        tramo = _cuando(tarjeta, hoy)
        if tramo is not None and tramo["fin"] < hoy:
            pasadas += 1
            continue
        vigentes.append((tarjeta, tramo))

    # De lo más próximo a lo más lejano, y en un mismo día primero lo puntual:
    # la ficha le importa más a la función de hoy que al taller que corre
    # todo el mes. Lo que empezó antes de hoy cuenta como de hoy.
    #
    # El orden también es lo que hace estable la ventana entre corridas: la
    # base pisa hora, precio y descripción con lo que trae cada corrida, así
    # que un evento que hoy tuvo ficha y mañana no la volvería a perder. Con
    # este orden lo único que saca a un evento de la ventana es que se
    # publiquen tarjetas nuevas más cercanas que él; lo que ya pasó solo deja
    # lugar. Por eso el tope conviene holgado: los ~55 talleres de mes entero
    # de Providencia viven todos en "hoy" y se llevan su parte cada día.
    def prioridad(par):
        tarjeta, tramo = par
        if tramo is None:
            return (hoy, 0, tarjeta["titulo"])
        return (max(tramo["inicio"], hoy), int(tramo["mes_entero"]), tarjeta["titulo"])

    vigentes.sort(key=prioridad)
    tope = int(fuente.get("tope_detalle", 80)) if fuente.get("buscar_detalle", True) else 0

    eventos: list[Evento] = []
    fichas_abiertas = 0
    rotulos_raros: set[str] = set()
    for tarjeta, tramo in vigentes:
        ficha = None
        if fichas_abiertas < tope:
            fichas_abiertas += 1
            peticiones += 1
            detalle = cliente.obtener(tarjeta["url"], max_edad_cache_seg=3 * 24 * 3600)
            if detalle is not None and detalle.ok:
                ficha = _leer_ficha(detalle.text)

        campos = ficha["campos"] if ficha else {}
        cuerpo = ficha["cuerpo"] if ficha else ""
        horario = campos.get("horario", "")
        hora, hora_fin = _horas(horario)

        inicio = fin = None
        todo_el_dia = False
        partes_descripcion: list[str] = []
        if tramo is None and ficha:
            # Sin atributos legibles, el "Día:" de la ficha es lo que queda.
            leida = parsear_fecha(campos.get("dia", ""), publicado=(
                datetime.combine(ficha["publicado"], time(0, 0)) if ficha["publicado"] else None))
            if leida is not None:
                tramo = {"inicio": leida.date(), "fin": leida.date(), "dias": [],
                         "mes_entero": False, "tramo": (leida.date(), leida.date())}
        if tramo is not None:
            if tramo["mes_entero"]:
                inicio = datetime.combine(tramo["inicio"], hora or time(0, 0))
                fin = datetime.combine(tramo["fin"], hora_fin or hora or time(0, 0))
                todo_el_dia = hora is None
                partes_descripcion.append(
                    _frase_de_mes_entero(tramo["dias"], tramo["tramo"], horario))
                if len(tramo["dias"]) == 7 and not re.search(
                        r"\btodos? (el mes|los dias)\b", _plano(tarjeta["rotulo"])):
                    rotulos_raros.add(tarjeta["rotulo"])
            else:
                inicio = datetime.combine(tramo["inicio"], hora or time(0, 0))
                if horario:
                    partes_descripcion.append(horario)
        elif tarjeta["rotulo"]:
            partes_descripcion.append(tarjeta["rotulo"])

        if cuerpo:
            partes_descripcion.append(cuerpo)

        precio, gratis, texto_precio = _precio(campos.get("valor", ""), cuerpo)
        lugar, direccion = _lugar(tarjeta["recinto"])

        eventos.append(Evento(
            titulo=tarjeta["titulo"][:160],
            categoria=CATEGORIA_POR_SEGMENTO.get(tarjeta["segmento"], ""),
            descripcion_corta=resumir(". ".join(p for p in partes_descripcion if p), 200),
            inicio=inicio,
            fin=fin,
            todo_el_dia=todo_el_dia,
            lugar_nombre=lugar or fuente.get("nombre", ""),
            lugar_direccion=direccion,
            # La comuna de la fuente manda, como en las tablas municipales: la
            # agenda de un municipio es de su comuna por definición, y el
            # recinto engaña ("Dinamarca con Av. El Bosque" es una esquina de
            # Providencia, no la comuna de El Bosque).
            comuna=fuente.get("comuna") or detectar_comuna(direccion, lugar),
            precio_clp=precio,
            es_gratis=gratis,
            precio_texto=texto_precio,
            fuente_tipo="providencia",
            fuente_nombre=fuente.get("nombre", ""),
            fuente_url=tarjeta["url"],
            imagen_url=tarjeta["imagen"],
            id_externo=tarjeta["slug"],
            fecha_publicacion=(datetime.combine(tarjeta["publicado"], time(0, 0))
                               if tarjeta["publicado"] else None),
        ))

    if rotulos_raros:
        log.info("%s: rótulos de mes entero leídos como todos los días: %s",
                 fuente.get("nombre"), "; ".join(sorted(rotulos_raros)[:10]))
    log.info("%s: %d tarjetas, %d pasadas, %d vigentes, %d fichas abiertas (tope %d), "
             "%d peticiones", fuente.get("nombre"), len(tarjetas), pasadas,
             len(vigentes), fichas_abiertas, tope, peticiones)
    return eventos
