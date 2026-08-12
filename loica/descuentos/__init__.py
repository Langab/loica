"""Catastro de descuentos bancarios en restaurantes.

Responde una sola pregunta, que es la que uno se hace parado en la vereda:
*es martes, ando por Providencia, tengo tarjeta del Chile, ¿dónde como?*

Corre con el mismo criterio que el pipeline de eventos: peticiones HTTP
educadas, sin modelo de lenguaje, sin credenciales de usuario, y cada
descuento amarrado al link del banco que lo publica. La app indexa y deriva
tráfico a la fuente; no la reemplaza.

El sondeo de qué banco sirve y cuál no está en
`notas/catastro_descuentos_bancos.md`.
"""

from __future__ import annotations

import logging
from datetime import date

from ..red import ClienteEducado
from .bancos import ADAPTADORES
from .modelo import Descuento

log = logging.getLogger("loica.descuentos")


def recolectar(bancos: list[dict], usar_cache: bool = True) -> tuple[list[Descuento], list[dict]]:
    """Recorre los bancos activos y devuelve (descuentos, estadísticas)."""
    todos: list[Descuento] = []
    estadisticas: list[dict] = []

    for banco in bancos:
        if not banco.get("activo", True):
            continue
        adaptador = ADAPTADORES.get(banco.get("adaptador", ""))
        if adaptador is None:
            log.error("%s: adaptador '%s' desconocido", banco["id"], banco.get("adaptador"))
            continue

        cliente = ClienteEducado(crawl_delay_seg=banco.get("crawl_delay_seg", 2),
                                 usar_cache=usar_cache)
        try:
            crudos = adaptador(banco, cliente)
        except Exception as e:                       # una fuente caída no bota la corrida
            log.error("%s falló: %s", banco["id"], e)
            estadisticas.append({"banco": banco["nombre"], "crudos": 0, "vigentes": 0,
                                 "con_dia": 0, "error": str(e)})
            continue

        vigentes = [d for d in crudos if _sigue_viva(d) and d.comercio]
        todos.extend(vigentes)
        estadisticas.append({
            "banco": banco["nombre"],
            "crudos": len(crudos),
            "vigentes": len(vigentes),
            "con_dia": sum(1 for d in vigentes if d.dias),
            "vencidos": sum(1 for d in crudos if not _sigue_viva(d)),
            "error": "",
        })
        log.info("%-16s %3d vigentes de %3d (%d con día)",
                 banco["nombre"], len(vigentes), len(crudos),
                 sum(1 for d in vigentes if d.dias))

    return _sin_repetidos(todos), estadisticas


def _sigue_viva(descuento: Descuento, hoy: date | None = None) -> bool:
    """Una promoción vencida es peor que ninguna.

    Mandar a alguien a un restaurante con un descuento muerto quema la
    confianza mucho más rápido que un evento pasado en la agenda: allá se
    perdió un panorama, acá se paga la cuenta completa delante de la mesa.

    Las que no declaran vigencia igual pasan —Bci tiene cientos así— pero
    viajan con `vigencia_hasta` en null y la página las muestra como "sin
    fecha declarada" en vez de darlas por buenas.
    """
    if descuento.vigencia_hasta is None:
        return True
    return descuento.vigencia_hasta >= (hoy or date.today())


def _sin_repetidos(descuentos: list[Descuento]) -> list[Descuento]:
    """Mismo comercio, mismo banco, misma comuna = una sola fila.

    Se queda con la que tenga más dato: entre dos entradas del mismo local
    gana la que trae día y porcentaje, porque es la que sirve para filtrar.
    """
    mejores: dict[str, Descuento] = {}
    for d in descuentos:
        previo = mejores.get(d.id)
        if previo is None or _riqueza(d) > _riqueza(previo):
            mejores[d.id] = d
    return sorted(mejores.values(),
                  key=lambda d: (d.banco, -(d.porcentaje or 0), d.comercio.lower()))


def _riqueza(d: Descuento) -> int:
    return ((len(d.dias) > 0) * 4 + (d.porcentaje is not None) * 2
            + bool(d.oferta) + (d.vigencia_hasta is not None))
