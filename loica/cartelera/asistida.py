"""Las carteleras que hay que sacar con el navegador, ya en CSV.

Cineplanet y Cinépolis no se pueden leer desde un programa, y no por
casualidad: Cineplanet entrega su cartelera solo a quien trae la cookie de
sesión que su propio sitio planta en el navegador —la misma petición da 200
con cookie y 403 sin ella— y la API de Cinépolis responde 401 "Unauthorized
access" porque pide un token. Las dos son puertas cerradas a propósito, y el
proyecto no las fuerza: se pide el dato como lo pediría una persona, mirando
la página.

Ese recorrido lo hace alguien con el navegador siguiendo
`datos/manual/_prompt_cine.md`, que devuelve un CSV. Acá entra ese CSV y se
convierte en funciones iguales a las que trae cualquier otro adaptador. Es la
misma puerta que ya usa Passline para los eventos, con el mismo trato: sin
link no se guarda, porque sin atribución esto deja de ser un índice.

    cine,pelicula,fecha,hora,formato,idioma,duracion_min,clasificacion,poster,link_compra
    Cinépolis Mallplaza Egaña,La odisea,2026-08-25,19:40,2D,subtitulada,152,MA14,https://…jpg,https://…

El nombre del cine se pega contra el catastro por nombre o por alias. Si no
calza con ninguna sala, la fila se descarta con su motivo: una función sin
sala no tiene dónde ir en el mapa, y ponerla en la sala equivocada es peor que
no ponerla.
"""

from __future__ import annotations

import csv
import logging
import re
from datetime import date, datetime
from pathlib import Path

from ..cines import buscar
from ..modelo import es_url_publica
from .modelo import (Cartelera, Funcion, clave_pelicula, normalizar_idioma,
                     titulo_legible)

log = logging.getLogger("loica.cartelera.asistida")

DIR_MANUAL = Path(__file__).resolve().parent.parent.parent / "datos" / "manual"
PATRON = "cartelera*.csv"

COLUMNAS = ("cine", "pelicula", "fecha", "hora", "formato", "idioma",
            "duracion_min", "clasificacion", "poster", "link_compra",
            # Opcionales: la ficha de la película, para el presentador. El
            # prompt del navegador ahora las trae de Cineplanet, pero un CSV
            # viejo sin estas columnas sigue entrando igual —`.get` las deja
            # vacías— así que agregarlas no rompe nada de lo anterior.
            "sinopsis", "trailer", "generos")


# El tráiler es lo único que va a un <iframe>/<a> apuntando a un sitio de
# video. Se restringe a los dos incrustadores conocidos: cualquier otro dominio
# en ese campo es más probable que sea un error del CSV que un tráiler.
_VIDEO = re.compile(r"^https://(www\.|m\.)?(youtube\.com|youtu\.be|player\.vimeo\.com|vimeo\.com)/", re.I)


def _es_video(url: str) -> bool:
    return bool(_VIDEO.match(url or ""))


def _entero(texto: str) -> int | None:
    try:
        valor = int(float(texto))
    except (TypeError, ValueError):
        return None
    return valor if 0 < valor < 600 else None


def _momento(fecha: str, hora: str) -> datetime | None:
    fecha, hora = (fecha or "").strip(), (hora or "").strip()
    if not fecha:
        return None
    for formato in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M",
                    "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(f"{fecha} {hora[:8] or '00:00'}", formato)
        except ValueError:
            continue
    return None


def _de_fila(fila: dict, archivo: str) -> tuple[Funcion | None, str, dict | None]:
    datos = {c: str(fila.get(c, "") or "").strip() for c in COLUMNAS}
    if not datos["pelicula"]:
        return None, "fila sin película", None

    sala = buscar(datos["cine"])
    if sala is None:
        return None, f'"{datos["cine"][:40]}" no calza con ninguna sala del catastro', None

    inicio = _momento(datos["fecha"], datos["hora"])
    if inicio is None:
        return None, f'{datos["pelicula"][:40]}: fecha ilegible ("{datos["fecha"]}")', None
    if inicio.date() < date.today():
        return None, f'{datos["pelicula"][:40]}: función pasada ({inicio:%d-%m})', None

    compra = datos["link_compra"]
    poster = datos["poster"]
    # La ficha va aparte de la función: es de la PELÍCULA, y la clave la
    # agrupa. El tráiler solo se acepta de YouTube/Vimeo —la página lo
    # incrusta— y pasa por es_url_publica igual que cualquier href.
    trailer = datos["trailer"]
    ficha = None
    if datos["sinopsis"] or trailer or datos["generos"]:
        ficha = {
            "clave": clave_pelicula(datos["pelicula"]),
            "sinopsis": datos["sinopsis"][:900],
            "trailer": trailer if (es_url_publica(trailer)
                       and _es_video(trailer)) else "",
            "generos": [g.strip() for g in datos["generos"].split(",") if g.strip()],
        }
    return Funcion(
        pelicula=titulo_legible(datos["pelicula"][:160]),
        cine_id=sala["id"],
        inicio=inicio,
        formato=datos["formato"][:24],
        idioma=normalizar_idioma(datos["idioma"]),
        url=compra if es_url_publica(compra) else sala.get("url", ""),
        poster=poster if es_url_publica(poster) else "",
        duracion_min=_entero(datos["duracion_min"]),
        clasificacion=datos["clasificacion"][:12],
        fuente=f"asistida:{archivo}",
    ), "", ficha


def extraer(_cliente=None) -> Cartelera:
    """No hace ninguna petición de red: lee datos/manual/cartelera*.csv."""
    salida = Cartelera()
    if not DIR_MANUAL.exists():
        return salida

    for ruta in sorted(DIR_MANUAL.glob(PATRON)):
        try:
            # utf-8-sig porque Excel y varios exportadores dejan BOM al inicio.
            with ruta.open(encoding="utf-8-sig", newline="") as f:
                filas = list(csv.DictReader(f))
        except (OSError, csv.Error) as e:
            salida.salas_fallidas.append(f"{ruta.name}: no pude leerlo ({e})")
            continue

        descartes: dict[str, int] = {}
        antes = len(salida.funciones)
        for fila in filas:
            funcion, motivo, ficha = _de_fila(fila, ruta.name)
            if funcion is None:
                descartes[motivo] = descartes.get(motivo, 0) + 1
                continue
            salida.funciones.append(funcion)
            # La primera ficha no vacía de cada película gana; las repetidas
            # (una por función) traen lo mismo.
            if ficha and ficha["clave"] not in salida.fichas:
                salida.fichas[ficha["clave"]] = {k: ficha[k] for k in
                                                 ("sinopsis", "trailer", "generos")}

        leidas = len(salida.funciones) - antes
        salas = {f.cine_id for f in salida.funciones[antes:]}
        salida.salas_leidas += len(salas)
        log.info("  %s: %d funciones en %d salas", ruta.name, leidas, len(salas))
        for motivo, veces in sorted(descartes.items(), key=lambda kv: -kv[1])[:8]:
            salida.notas.append(f"{ruta.name}: {veces}× {motivo}")

    return salida
