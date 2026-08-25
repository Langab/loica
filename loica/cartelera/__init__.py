"""El catastro de carteleras de cine: junta las cuatro vías y arma la página.

Cuatro maneras de conseguir los horarios, en orden de cuánto cuesta cada una:

  jsonld     Cinemark publica ScreeningEvent en el HTML de cada sala. Gratis,
             estructurado, sin navegador: entra a la corrida diaria y listo.
  semanal    El Normandie y El Biógrafo publican la semana en su página. Se
             lee con un parser por sala; son dos.
  agenda     La Cineteca, M100 y el Centro Arte Alameda ya llegan por las
             fuentes de siempre; acá solo se recogen de web/eventos.json.
  asistida   Cineplanet y Cinépolis cierran su cartelera a todo lo que no sea
             su propia app, así que las mira una persona con el navegador y
             deja un CSV. Ver datos/manual/_prompt_cine.md.

El resultado se agrupa POR PELÍCULA, no por función. Una cartelera son miles
de funciones y nadie las lee así: se lee "qué dan" y después "dónde y a qué
hora". La página necesita las dos vistas y las dos salen de la misma lista.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

from ..cines import catalogo
from ..red import ClienteEducado
from . import agenda, asistida, jsonld, semanal
from .modelo import Cartelera, Funcion, clave_pelicula, sin_coletillas

log = logging.getLogger("loica.cartelera")

# Cuántos días de cartelera se publican.
#
# Siete, porque es lo que alguien quiere preguntarle a una cartelera: "¿qué dan
# el sábado?". Pero hay que saber lo que se está publicando, y esto está
# MEDIDO (24-08-2026, un lunes):
#
#   Cinemark              3 días — hoy, mañana y pasado. No publica más.
#   Normandie             hasta el miércoles: su semana corre de jueves a
#                         miércoles y ese lunes le quedaban 3 días.
#   agenda cultural       6 días, pero con 2, 1 y 1 función en los últimos.
#
# O sea que del cuarto día en adelante la cartelera está casi vacía SIEMPRE, y
# no por una falla nuestra: las cadenas cargan sus horarios con dos o tres días
# de anticipación y los jueves, que es cuando cambian la programación, el
# calendario se llena de golpe. Mostrar los siete días es honesto mientras la
# página diga que ese día todavía no lo publica el cine —y no que sobran
# filtros, que es lo que decía antes—. Esa parte vive en web/cine.html.
#
# Subir este número no cuesta peso: los días extra agregaron 3 funciones a las
# 630 que ya había.
DIAS = 7

VIAS = {
    "jsonld": jsonld.extraer,
    "semanal": semanal.extraer,
    "agenda": agenda.extraer,
    "asistida": asistida.extraer,
}


def recolectar(cliente: ClienteEducado | None = None,
               solo: str | None = None) -> Cartelera:
    cliente = cliente or ClienteEducado(crawl_delay_seg=2)
    total = Cartelera()

    for nombre, extraer in VIAS.items():
        if solo and solo != nombre:
            continue
        log.info("%s…", nombre)
        try:
            parcial = extraer(cliente)
        except Exception as e:  # noqa: BLE001 — una vía caída no bota las otras
            log.warning("  %s falló: %s", nombre, e)
            total.salas_fallidas.append(f"{nombre}: {type(e).__name__} {e}")
            continue
        total.funciones.extend(parcial.funciones)
        total.salas_leidas += parcial.salas_leidas
        total.salas_fallidas.extend(parcial.salas_fallidas)
        total.notas.extend(parcial.notas)

    total.funciones = _limpiar(total.funciones)
    return total


def _limpiar(funciones: list[Funcion]) -> list[Funcion]:
    """Saca lo pasado, lo demasiado lejano y lo repetido.

    Se deduplica por (sala, película, minuto exacto): la misma función puede
    llegar por dos vías —el CSV asistido de la semana pasada y el de hoy— y
    una película no se da dos veces a la misma hora en la misma sala. El
    formato NO entra en la llave a propósito: si una cadena publica la misma
    función como "2D" y como "2D DOB", sigue siendo una sola función.
    """
    ahora = datetime.now()
    limite = datetime.combine(date.today() + timedelta(days=DIAS), datetime.min.time())
    vistas: dict[tuple, Funcion] = {}

    for funcion in funciones:
        if funcion.inicio < ahora.replace(hour=0, minute=0, second=0, microsecond=0):
            continue
        if funcion.inicio >= limite:
            continue
        llave = (funcion.cine_id, funcion.clave, funcion.inicio.isoformat(timespec="minutes"))
        previa = vistas.get(llave)
        # Ante dos copias gana la que trae más datos: el afiche y el link de
        # compra son lo que la página muestra.
        if previa is None or (len(funcion.poster) + len(funcion.url)
                              > len(previa.poster) + len(previa.url)):
            vistas[llave] = funcion
    return sorted(vistas.values(), key=lambda f: (f.inicio, f.cine_id, f.pelicula))


def _mejor(valores: list) -> str:
    """El valor más repetido y no vacío. Las cadenas escriben la duración y la
    clasificación de la misma película distinto; gana la mayoría."""
    conteo: dict = defaultdict(int)
    for valor in valores:
        if valor:
            conteo[valor] += 1
    return max(conteo, key=conteo.get) if conteo else ""


def para_la_web(cartelera: Cartelera) -> dict:
    """La forma que consume web/cine.html.

    Las salas van completas —las 44, incluso las que hoy no tienen horarios—
    porque el mapa es media página: la pregunta "qué cine tengo cerca" se
    contesta con la dirección, no con la función.
    """
    por_pelicula: dict[str, list[Funcion]] = defaultdict(list)
    for funcion in cartelera.funciones:
        por_pelicula[funcion.clave].append(funcion)

    peliculas = []
    for clave, funciones in por_pelicula.items():
        funciones.sort(key=lambda f: f.inicio)
        peliculas.append({
            "clave": clave,
            # El título más largo suele ser el completo ("Spider-Man: Un nuevo
            # día" contra "Spider-Man"), que es el que la gente reconoce. Pero
            # se compara ya SIN la coletilla de sala o de ciclo: desde que esas
            # variantes se agrupan juntas, la más larga es justamente la peor
            # —"La Odisea / Centro Arte Alameda" le ganaba a "La Odisea"— y la
            # ficha quedaba titulada con el nombre de UNA de sus ocho salas.
            "titulo": max((sin_coletillas(f.pelicula) for f in funciones), key=len),
            "poster": _mejor([f.poster for f in funciones]),
            "duracion": next((f.duracion_min for f in funciones if f.duracion_min), None),
            "clasificacion": _mejor([f.clasificacion for f in funciones]),
            "cines": sorted({f.cine_id for f in funciones}),
            "funciones": [{
                "cine": f.cine_id,
                "inicio": f.inicio.isoformat(timespec="minutes"),
                "formato": f.formato,
                "idioma": f.idioma,
                "sala": f.sala,
                "url": f.url,
            } for f in funciones],
        })

    # Primero lo que más se da: una película en veinte salas es el estreno de
    # la semana y es lo que la mayoría viene a buscar.
    peliculas.sort(key=lambda p: (-len(p["funciones"]), p["titulo"]))

    conteo: dict[str, int] = defaultdict(int)
    for funcion in cartelera.funciones:
        conteo[funcion.cine_id] += 1

    cines = []
    for sala in catalogo():
        cines.append({
            "id": sala["id"],
            "nombre": sala["nombre"],
            "cadena": sala.get("cadena", ""),
            "circuito": sala.get("circuito", ""),
            "direccion": sala.get("direccion", ""),
            "comuna": sala.get("comuna", ""),
            "lat": sala.get("lat"),
            "lon": sala.get("lon"),
            "url": sala.get("url", ""),
            "formatos": sala.get("formatos", ""),
            "funciones": conteo.get(sala["id"], 0),
        })
    cines.sort(key=lambda c: (-c["funciones"], c["nombre"]))

    return {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "dias": DIAS,
        "total_funciones": len(cartelera.funciones),
        "cines": cines,
        "peliculas": peliculas,
    }


__all__ = ["recolectar", "para_la_web", "Cartelera", "Funcion", "clave_pelicula",
           "sin_coletillas", "DIAS"]
