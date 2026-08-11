"""Colapsa eventos de varios días en uno solo con rango de fechas.

Los calendarios publican una entrada por cada día que dura una exposición o
una temporada de teatro. Sin esto, el mapa mostraría treinta veces la misma
muestra y el usuario vería basura.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta

from .modelo import Evento, clave_dedup

log = logging.getLogger("loica.agrupar")

# Días de hueco que se toleran dentro de una misma temporada (ej. una obra que
# se da de jueves a domingo tiene saltos de 3 días entre semana).
HUECO_MAXIMO_DIAS = 4


def _clave_serie(evento: Evento) -> str:
    """Identidad del evento sin la fecha: mismo título y mismo lugar."""
    return clave_dedup(evento.titulo, None, evento.lugar_nombre or evento.comuna)


def colapsar_multidia(eventos: list[Evento]) -> list[Evento]:
    """Agrupa repeticiones del mismo evento en uno con inicio y fin."""
    con_fecha = [e for e in eventos if e.inicio is not None]
    sin_fecha = [e for e in eventos if e.inicio is None]

    series: dict[str, list[Evento]] = defaultdict(list)
    for evento in con_fecha:
        series[_clave_serie(evento)].append(evento)

    resultado: list[Evento] = []
    colapsados = 0

    for repeticiones in series.values():
        if len(repeticiones) == 1:
            resultado.append(repeticiones[0])
            continue

        repeticiones.sort(key=lambda e: e.inicio)

        # Se corta la serie cuando hay un hueco grande: son temporadas distintas
        bloque = [repeticiones[0]]
        for anterior, actual in zip(repeticiones, repeticiones[1:]):
            if (actual.inicio.date() - anterior.inicio.date()) <= timedelta(days=HUECO_MAXIMO_DIAS):
                bloque.append(actual)
            else:
                resultado.append(_fusionar(bloque))
                colapsados += len(bloque) - 1
                bloque = [actual]
        resultado.append(_fusionar(bloque))
        colapsados += len(bloque) - 1

    if colapsados:
        log.info("Colapsados %d duplicados de eventos de varios días", colapsados)

    return resultado + sin_fecha


def _fusionar(bloque: list[Evento]) -> Evento:
    """Del bloque se queda el primero, con la fecha de término del último."""
    primero = bloque[0]
    if len(bloque) == 1:
        return primero

    ultimo = bloque[-1]
    primero.fin = ultimo.fin or ultimo.inicio

    # Si ninguna repetición traía hora, es un evento de todo el día (exposición)
    if all(e.inicio.hour == 0 and e.inicio.minute == 0 for e in bloque):
        primero.todo_el_dia = True

    # Se completan los huecos con datos de las otras repeticiones
    for otro in bloque[1:]:
        if not primero.precio_texto and otro.precio_texto:
            primero.precio_texto = otro.precio_texto
        if primero.precio_clp is None and otro.precio_clp is not None:
            primero.precio_clp = otro.precio_clp
            primero.es_gratis = otro.es_gratis
        if not primero.imagen_url and otro.imagen_url:
            primero.imagen_url = otro.imagen_url

    return primero
