"""Las funciones que ya venían llegando por la agenda general.

La Cineteca Nacional, la sala de cine de Matucana 100 y el Centro Arte Alameda
no tienen "cartelera": tienen programación cultural, y el pipeline ya la trae
todos los días por las fuentes de siempre (la API de WordPress del Centro
Cultural La Moneda, la de M100, la de CEINA). Volver a pedirla acá sería
raspar dos veces lo mismo.

Así que este adaptador no sale a la red: lee `web/eventos.json` —el archivo
que acaba de escribir `exportar_web.py`, con todo ya clasificado, deduplicado
y geocodificado— y saca de ahí los eventos que ocurren en una sala del
catastro. Es la razón por la que `run_cine.py` corre DESPUÉS de exportar.

Un evento entra si pasa las dos puertas: ocurre en una sala de cine del
catastro **y** el clasificador lo llamó cine. La primera sola no basta —el
Centro Arte Alameda también programa conciertos y la Cineteca hace charlas—,
y la segunda sola tampoco: "Cine bajo las estrellas" en una plaza es un
panorama al aire libre, no una sala a la que uno pueda llegar a las nueve.

Estas funciones siguen apareciendo además en el mapa general, y está bien:
una función de la Cineteca es un panorama de verdad. Lo que no puede pasar es
lo contrario —que las mil funciones de los malls entren al mapa general—, y
por eso las cadenas nunca tocan `web/eventos.json`.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path

from ..cines import buscar
from ..modelo import es_url_publica
from .modelo import Cartelera, Funcion, titulo_legible

log = logging.getLogger("loica.cartelera.agenda")

RUTA_EVENTOS = Path(__file__).resolve().parent.parent.parent / "web" / "eventos.json"


def extraer(_cliente=None, ruta: Path = RUTA_EVENTOS) -> Cartelera:
    salida = Cartelera()
    if not ruta.exists():
        salida.notas.append("web/eventos.json todavía no existe — corre exportar_web.py antes")
        return salida

    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        salida.salas_fallidas.append(f"web/eventos.json ilegible ({e})")
        return salida

    hoy = date.today()
    salas = set()
    for evento in datos.get("eventos") or []:
        if (evento.get("categoria") or "") != "cine":
            continue
        sala = buscar(evento.get("lugar") or "", evento.get("comuna") or "",
                      evento.get("lat"), evento.get("lon"))
        if sala is None:
            continue

        try:
            inicio = datetime.fromisoformat((evento.get("inicio") or "")[:19])
        except ValueError:
            continue
        if inicio.date() < hoy:
            continue

        url = evento.get("url") or ""
        poster = evento.get("imagen") or ""
        salas.add(sala["id"])
        salida.funciones.append(Funcion(
            pelicula=titulo_legible((evento.get("titulo") or "")[:160]),
            cine_id=sala["id"],
            inicio=inicio,
            url=url if es_url_publica(url) else sala.get("url", ""),
            poster=poster if es_url_publica(poster) else "",
            fuente="agenda",
        ))

    salida.salas_leidas = len(salas)
    log.info("  agenda cultural: %d funciones en %d salas",
             len(salida.funciones), len(salas))
    return salida
