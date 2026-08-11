"""Adaptador para tablas HTML de talleres municipales.

Media docena de municipios publica su oferta deportiva y de talleres como
tablas planas, una por recinto:

    GIMNASIO MUNICIPAL
    Dirección: Guillermo Subiabre #1123, Huechuraba.
    Horario de funcionamiento: Lunes a viernes de 09:00 a 22:00.
    DISCIPLINA        | DÍA(S)                | HORARIO           | EDAD   | INICIO
    Ciclismo Montaña  | Sábado                | 09:00 a 13:00     | 6+     | Marzo
    Escuela de Fútbol | Martes - jueves       | 17:15 a 18:30     | 6 a 10 | Marzo

El nombre del recinto y su dirección viven en las filas de ARRIBA del
encabezado, no en una columna: por eso no sirve un lector de tablas genérico.

La columna INICIO dice "Marzo" porque son programas anuales que ya empezaron y
siguen corriendo. La fecha que le importa al usuario no es cuándo partió el
programa sino cuándo es la próxima sesión, así que se emiten las ocurrencias
futuras (ver `loica/recurrencia.py`).
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from ..modelo import Evento
from ..normalizar import detectar_comuna, limpiar_html, parsear_precio
from ..recurrencia import frase_cadencia, parsear_dias, parsear_hora, sesiones_futuras
from ..red import ClienteEducado

log = logging.getLogger("loica.tablas")

# Con qué encabezado se reconoce cada columna. Los municipios no se ponen de
# acuerdo: "EDAD" en un lado, "CATEGORÍA - EDAD" en otro.
COLUMNAS = {
    "titulo": ("disciplina", "taller", "actividad", "ramo", "curso"),
    "dias": ("dia", "dias", "dia(s)", "jornada"),
    "horario": ("horario", "hora", "bloque"),
    "publico": ("edad", "categoria", "categoria - edad", "nivel"),
    "inicio": ("inicio", "comienzo", "desde"),
    "lugar": ("recinto", "lugar", "sede", "establecimiento"),
    "comuna": ("comuna", "barrio", "sector"),
}

ETIQUETA_DIRECCION = re.compile(r"direcci[oó]n\s*:\s*(.+)", re.IGNORECASE)
# "Horario de funcionamiento" es del recinto, no del taller: si se lee como si
# fuera la hora de una clase, todos los talleres quedan a la misma hora.
FILA_IGNORABLE = re.compile(
    r"horario de funcionamiento|tel[eé]fono|mail|correo|domingos? y festivos",
    re.IGNORECASE)

# Algunas tablas no repiten el nombre de la actividad en cada fila: la actividad
# es el título de la tabla y las filas son solo tramos horarios ("Bloque 1",
# "Bloque 2"). Publicar "Bloque 1" no le dice nada a nadie, así que en ese caso
# el nombre del evento pasa a ser el título de la tabla.
TITULO_GENERICO = re.compile(
    r"^(bloque|grupo|turno|horario|nivel|cupo|secci[oó]n)\s*[nº#]?\s*\d+$",
    re.IGNORECASE)

# Una dirección sin la etiqueta "Dirección:" (pasa en las tablas de una sola
# actividad). Se reconoce por la vía pública o por el número de calle.
PARECE_DIRECCION = re.compile(
    r"\b(av(da?)?\.?|avenida|calle|pasaje|psje\.?|camino|bandej[oó]n)\b|#\s*\d|\d{3,}",
    re.IGNORECASE)


def _normalizar(texto: str) -> str:
    import unicodedata
    plano = unicodedata.normalize("NFD", (texto or "").lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return " ".join(plano.split())


def _mapear_encabezado(celdas: list[str]) -> dict[str, int] | None:
    """Si esta fila es un encabezado, devuelve {campo: índice de columna}."""
    mapa: dict[str, int] = {}
    for indice, celda in enumerate(celdas):
        plano = _normalizar(celda)
        if not plano:
            continue
        for campo, alias in COLUMNAS.items():
            if campo in mapa:
                continue
            if any(plano == a or plano.startswith(a) for a in alias):
                mapa[campo] = indice
                break

    # Sin disciplina y sin días no hay taller que leer: es otra tabla.
    if "titulo" in mapa and "dias" in mapa:
        return mapa
    return None


def _contexto_de_recinto(filas_previas: list[list[str]]) -> tuple[str, str]:
    """Saca (nombre del recinto, dirección) de las filas sobre el encabezado."""
    nombre = direccion = ""
    sueltas: list[str] = []

    for celdas in filas_previas:
        texto = " ".join(c for c in celdas if c).strip()
        if not texto:
            continue

        m = ETIQUETA_DIRECCION.search(texto)
        if m and not direccion:
            direccion = limpiar_html(m.group(1)).strip(" .")
            continue

        # El nombre del recinto es la primera fila de una sola celda que no es
        # un dato de contacto ni un horario de atención.
        if len(celdas) == 1 and not FILA_IGNORABLE.search(texto):
            if not ETIQUETA_DIRECCION.search(texto):
                limpio = limpiar_html(texto)[:120]
                if not nombre:
                    nombre = limpio
                else:
                    sueltas.append(limpio)

    # Tablas de una sola actividad ponen la dirección en la fila siguiente al
    # nombre, sin etiqueta ("Bandejón Av. Pedro Fontova ...").
    if not direccion:
        for candidata in sueltas:
            if PARECE_DIRECCION.search(candidata):
                direccion = candidata
                break

    return nombre, direccion


def _eventos_de_tabla(tabla, fuente: dict, horizonte: int) -> list[Evento]:
    filas = []
    for tr in tabla.find_all("tr"):
        filas.append([c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])])

    mapa = None
    fila_encabezado = -1
    for indice, celdas in enumerate(filas):
        mapa = _mapear_encabezado(celdas)
        if mapa:
            fila_encabezado = indice
            break
    if not mapa:
        return []

    nombre_recinto, direccion = _contexto_de_recinto(filas[:fila_encabezado])
    url = fuente.get("url_agenda") or fuente.get("url_base", "")
    eventos: list[Evento] = []

    def celda(celdas: list[str], campo: str) -> str:
        indice = mapa.get(campo, -1)
        return celdas[indice] if 0 <= indice < len(celdas) else ""

    for celdas in filas[fila_encabezado + 1:]:
        if len(celdas) < 2:
            continue

        titulo = limpiar_html(celda(celdas, "titulo"))
        if not titulo or FILA_IGNORABLE.search(titulo):
            continue

        # "Bloque 3" no es el nombre de nada: la actividad está en el título de
        # la tabla y la fila solo distingue el tramo horario.
        if TITULO_GENERICO.match(titulo):
            if not nombre_recinto:
                continue
            titulo = f"{nombre_recinto.title()} ({titulo})"

        dias = parsear_dias(celda(celdas, "dias"))
        if not dias:
            continue

        horario = celda(celdas, "horario")
        hora = parsear_hora(horario)
        sesiones = sesiones_futuras(dias, hora, horizonte_dias=horizonte)
        if not sesiones:
            continue

        lugar = limpiar_html(celda(celdas, "lugar")) or nombre_recinto
        dir_fila = limpiar_html(celda(celdas, "comuna"))
        cadencia = frase_cadencia(dias, hora)

        detalle = ", ".join(p for p in (
            cadencia,
            f"horario {horario}" if horario and not hora else "",
            celda(celdas, "publico"),
        ) if p)

        # Los talleres municipales suelen ser gratuitos, pero eso NO se asume:
        # si la tabla no lo dice, el precio queda vacío. El filtro "solo gratis"
        # es la promesa central del producto.
        precio, gratis, texto_precio = parsear_precio(" ".join(celdas))

        for sesion in sesiones:
            eventos.append(Evento(
                titulo=titulo,
                categoria=fuente.get("categoria_por_defecto", ""),
                descripcion_corta=detalle[:200],
                inicio=sesion,
                lugar_nombre=lugar or fuente.get("nombre", ""),
                lugar_direccion=direccion,
                # La comuna de la fuente va PRIMERO, al revés que en el resto
                # del pipeline: una página de talleres municipales es por
                # definición de una sola comuna. Al detectarla desde el texto,
                # "JJ. VV. Villa Conchalí" y "Av. Recoleta" mandaban talleres
                # de Huechuraba a Conchalí y Recoleta.
                comuna=detectar_comuna(fuente.get("comuna", ""), dir_fila,
                                       direccion, lugar),
                precio_clp=precio,
                es_gratis=gratis,
                precio_texto=texto_precio,
                fuente_tipo="tabla",
                fuente_nombre=fuente.get("nombre", ""),
                fuente_url=url,
            ))

    return eventos


def extraer_tabla(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    url = fuente.get("url_agenda") or (
        fuente["url_base"].rstrip("/") + fuente.get("endpoint", ""))
    respuesta = cliente.obtener(url, max_edad_cache_seg=24 * 3600)
    if respuesta is None or not respuesta.ok:
        log.warning("%s: no pude leer la página de talleres", fuente.get("nombre"))
        return []

    sopa = BeautifulSoup(respuesta.text, "html.parser")
    horizonte = int(fuente.get("horizonte_dias", 30))

    eventos: list[Evento] = []
    tablas_leidas = 0
    for tabla in sopa.find_all("table"):
        encontrados = _eventos_de_tabla(tabla, fuente, horizonte)
        if encontrados:
            tablas_leidas += 1
            eventos.extend(encontrados)

    log.info("%s: %d sesiones desde %d tablas", fuente.get("nombre"),
             len(eventos), tablas_leidas)
    return eventos
