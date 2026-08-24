"""Los cines que publican LA SEMANA, no la función.

El Normandie y El Biógrafo no tienen sistema de ticketera con API: tienen una
página que alguien actualiza los jueves con la programación de los siete días.
Son dos maneras distintas de decir lo mismo:

    Normandie   una sección por día, con las funciones sueltas adentro
                <section class="jueves"><h5>Jueves 20</h5> 15:00 hrs. <b>Título</b>

    El Biógrafo una grilla de películas y un rótulo con el rango de la semana
                <div class="week-badge">13 – al 19 de Ago · 2026</div>
                <div class="movie-card"> .movie-time .movie-title .poster-img

La trampa que comparten es la fecha: ninguno de los dos escribe el año, y el
Normandie tampoco escribe el mes en la sección del día. En vez de armar el
rompecabezas se busca la única fecha cercana a hoy que calce con ese día de la
semana Y ese número; la combinación se repite recién en meses distintos, así
que dentro de una ventana de dos semanas es inequívoca, y cruza sola el fin de
mes y el fin de año.

La segunda trampa es más peligrosa y por eso hay una regla dura acá: **una
semana que ya terminó no se publica**. El Biógrafo estaba mostrando la semana
del 13 al 19 de agosto el día 24 —se actualiza los jueves y a veces se
atrasa—, y publicar eso significa mandar a alguien a una función que pasó hace
cinco días. Cuando la semana declarada quedó atrás, el adaptador devuelve cero
y lo dice en las notas, que es lo que hay que arreglar hablando con el cine,
no adivinando.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timedelta

from bs4 import BeautifulSoup

from ..cines import por_cartelera
from ..modelo import es_url_publica
from ..normalizar import limpiar_html
from ..recurrencia import DIAS_SEMANA
from ..red import ClienteEducado
from .modelo import Cartelera, Funcion, normalizar_idioma, titulo_legible

log = logging.getLogger("loica.cartelera.semanal")

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
         "noviembre": 11, "diciembre": 12,
         "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
         "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12}

# "15:00 hrs. Título" — la hora abre y el título sigue hasta la próxima hora.
# Sin el look-ahead el primer título se come la sección entera.
FUNCION = re.compile(
    r"(\d{1,2})[:.](\d{2})\s*(?:hrs?\.?|horas?)?\s*(.+?)"
    r"(?=\s*\d{1,2}[:.]\d{2}\s*(?:hrs?\.?|horas?)|$)", re.IGNORECASE)


def fecha_cercana(dia_semana: int, numero: int, hoy: date, ventana: int = 12) -> date | None:
    """La fecha cerca de hoy que cae en ese día de la semana y ese número."""
    for delta in range(-ventana, ventana + 1):
        candidata = hoy + timedelta(days=delta)
        if candidata.weekday() == dia_semana and candidata.day == numero:
            return candidata
    return None


def _rango_de_semana(texto: str, hoy: date) -> tuple[date, date] | None:
    """"13 – al 19 de Ago · 2026" → (13-08-2026, 19-08-2026)."""
    plano = " ".join((texto or "").lower().split())
    numeros = re.findall(r"\b(\d{1,2})\b(?!\s*:)", plano)
    mes = next((MESES[m] for m in MESES if re.search(rf"\b{m}\b", plano)), None)
    anio = next((int(a) for a in re.findall(r"\b(20\d{2})\b", plano)), hoy.year)
    if len(numeros) < 2 or mes is None:
        return None
    try:
        desde = date(anio, mes, int(numeros[0]))
        hasta = date(anio, mes, int(numeros[1]))
    except ValueError:
        return None
    if hasta < desde:  # la semana cruza de mes: "30 de ago al 5 de sep"
        hasta = (desde + timedelta(days=6))
    return desde, hasta


def _normandie(sopa: BeautifulSoup, cine: dict, hoy: date) -> tuple[list[Funcion], list[str]]:
    funciones: list[Funcion] = []
    notas: list[str] = []

    for nombre_dia, indice in DIAS_SEMANA.items():
        for seccion in sopa.select(f"section.{nombre_dia}, div.{nombre_dia}"):
            encabezado = seccion.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            if encabezado is None:
                continue
            numero = re.search(r"(\d{1,2})", encabezado.get_text(" ", strip=True))
            if not numero:
                continue
            dia = fecha_cercana(indice, int(numero.group(1)), hoy)
            if dia is None or dia < hoy:
                continue

            # Los links de compra, en el orden en que aparecen: el cine pone
            # uno por función y es el que hay que seguir para comprar.
            enlaces = [a.get("href", "") for a in seccion.select("a[href]")]

            # El encabezado se saca ANTES de leer las horas: si no, su número
            # ("Jueves 20") se confunde con una hora.
            encabezado.decompose()
            texto = seccion.get_text(" ", strip=True)

            for i, funcion in enumerate(FUNCION.finditer(texto)):
                hora, minuto = int(funcion.group(1)), int(funcion.group(2))
                titulo = limpiar_html(funcion.group(3)).strip(" .-–—")
                if not titulo or hora > 23 or minuto > 59:
                    continue
                compra = enlaces[i] if i < len(enlaces) else ""
                funciones.append(Funcion(
                    pelicula=titulo_legible(titulo[:160]),
                    cine_id=cine["id"],
                    inicio=datetime.combine(dia, time(hora, minuto)),
                    idioma="subtitulada",   # la sala programa siempre en VOSE
                    url=compra if es_url_publica(compra) else cine.get("url", ""),
                    fuente="normandie",
                ))

    if not funciones:
        notas.append(f"{cine['nombre']}: la cartelera no trajo funciones futuras")
    return funciones, notas


def _biografo(sopa: BeautifulSoup, cine: dict, hoy: date) -> tuple[list[Funcion], list[str]]:
    funciones: list[Funcion] = []
    notas: list[str] = []

    rotulo = sopa.select_one(".week-badge")
    rango = _rango_de_semana(rotulo.get_text(" ", strip=True) if rotulo else "", hoy)
    if rango is None:
        notas.append(f"{cine['nombre']}: no pude leer el rango de la semana")
        return funciones, notas

    desde, hasta = rango
    if hasta < hoy:
        # La regla dura: no se manda a nadie a una función que ya pasó.
        notas.append(f"{cine['nombre']}: la cartelera publicada es la semana del "
                     f"{desde:%d-%m} al {hasta:%d-%m} y ya terminó — no se publica")
        return funciones, notas

    for tarjeta in sopa.select(".movie-card"):
        titulo_nodo = tarjeta.select_one(".movie-title")
        hora_nodo = tarjeta.select_one(".movie-time")
        if titulo_nodo is None or hora_nodo is None:
            continue
        reloj = re.search(r"(\d{1,2})[:.](\d{2})", hora_nodo.get_text(" ", strip=True))
        if not reloj:
            continue
        hora, minuto = int(reloj.group(1)), int(reloj.group(2))
        if hora > 23 or minuto > 59:
            continue

        titulo = limpiar_html(titulo_nodo.get_text(" ", strip=True))
        afiche = (tarjeta.select_one(".poster-img") or {}).get("src", "") \
            if tarjeta.select_one(".poster-img") else ""
        version = tarjeta.select_one(".movie-version")
        edad = tarjeta.select_one(".movie-rating")
        meta = tarjeta.select_one(".movie-meta-bar")
        minutos = None
        if meta:
            m = re.search(r"(\d{2,3})\s*min", meta.get_text(" ", strip=True))
            minutos = int(m.group(1)) if m else None

        # La misma función se da todos los días de la semana publicada; solo
        # se emiten los días que todavía no pasaron.
        dia = max(desde, hoy)
        while dia <= hasta:
            funciones.append(Funcion(
                pelicula=titulo_legible(titulo[:160]),
                cine_id=cine["id"],
                inicio=datetime.combine(dia, time(hora, minuto)),
                idioma=normalizar_idioma(version.get_text(strip=True) if version else ""),
                url=cine.get("url", ""),
                poster=afiche if es_url_publica(afiche) else "",
                duracion_min=minutos,
                clasificacion=(edad.get_text(strip=True) if edad else ""),
                fuente="biografo",
            ))
            dia += timedelta(days=1)

    return funciones, notas


# Qué sala se lee con qué parser. El id sale del catastro.
PARSERS = {
    "cine-arte-normandie": _normandie,
    "el-biografo": _biografo,
}


def extraer(cliente: ClienteEducado) -> Cartelera:
    salida = Cartelera()
    hoy = date.today()

    for cine in por_cartelera("semanal"):
        parser = PARSERS.get(cine["id"])
        if parser is None:
            salida.notas.append(f"{cine['nombre']}: marcado 'semanal' pero sin parser")
            continue

        url = cine.get("url") or ""
        respuesta = cliente.obtener(url, max_edad_cache_seg=6 * 3600)
        if respuesta is None or not respuesta.ok:
            codigo = respuesta.status_code if respuesta is not None else "sin respuesta"
            salida.salas_fallidas.append(f"{cine['nombre']}: {codigo}")
            continue

        sopa = BeautifulSoup(respuesta.text, "html.parser")
        for basura in sopa.select("nav, header, footer, script, style"):
            basura.decompose()

        funciones, notas = parser(sopa, cine, hoy)
        salida.notas.extend(notas)
        if funciones:
            salida.salas_leidas += 1
            salida.funciones.extend(funciones)
            log.info("  %s: %d funciones", cine["nombre"], len(funciones))
        else:
            salida.salas_fallidas.append(f"{cine['nombre']}: sin funciones futuras")

    return salida
