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
from .texto import es_metropolitana

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

        excluidos = {str(x).strip().lower() for x in (banco.get("excluir_comercios") or [])}
        vigentes = [d for d in crudos
                    if _sigue_viva(d) and d.comercio
                    and d.comercio.strip().lower() not in excluidos]
        # Loica es de Santiago. Un 40% en Puerto Natales es un dato correcto y
        # completamente inútil para quien abre la página, y además ensucia el
        # filtro de comuna con noventa nombres que nadie va a elegir.
        santiago = [d for d in vigentes if es_metropolitana(d.comuna, d.region)]
        todos.extend(santiago)
        estadisticas.append({
            "banco": banco["nombre"],
            "crudos": len(crudos),
            "vigentes": len(santiago),
            "con_dia": sum(1 for d in santiago if d.dias),
            "vencidos": sum(1 for d in crudos if not _sigue_viva(d)),
            "fuera_rm": len(vigentes) - len(santiago),
            "error": "",
        })
        _avisar_si_vieja(banco, santiago)
        log.info("%-26s %3d en la RM de %3d (%d con día)",
                 banco["nombre"], len(santiago), len(crudos),
                 sum(1 for d in santiago if d.dias))

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
    """Mismo comercio, mismo banco y MISMA DIRECCIÓN = una sola fila.

    Se queda con la que tenga más dato: entre dos entradas del mismo local
    gana la que trae día y porcentaje, porque es la que sirve para filtrar.

    Antes la llave era la comuna y no la dirección, y eso borraba sucursales
    de verdad: los tres Starbucks de Las Condes quedaban en uno solo, sin
    aviso y sin que se notara, porque el que sobrevivía se veía bien. La lista
    no se alarga por esto —las sucursales se agrupan de nuevo al publicar, en
    cadenas.py— pero el mapa gana los pines que faltaban.
    """
    mejores: dict[str, Descuento] = {}
    for d in descuentos:
        previo = mejores.get(d.huella)
        if previo is None or _riqueza(d) > _riqueza(previo):
            mejores[d.huella] = d
    # Por valor y no por banco. Agrupada por banco, la lista abría con las
    # 137 de Falabella una tras otra y parecía que ese era el único banco;
    # ordenada por cuánto rebaja, arriba queda lo que conviene y los tres
    # bancos se mezclan solos.
    return sorted(mejores.values(),
                  key=lambda d: (-(d.porcentaje or 0), d.comercio.lower(), d.banco))


def _riqueza(d: Descuento) -> int:
    return ((len(d.dias) > 0) * 4 + (d.porcentaje is not None) * 2
            + bool(d.oferta) + (d.vigencia_hasta is not None))


def _avisar_si_vieja(banco: dict, descuentos: list[Descuento]) -> None:
    """Las fuentes de captura manual envejecen en silencio si nadie mira.

    Este aviso es el único mecanismo que tiene Santander para no volverse una
    mentira: nada lo refresca solo, así que la corrida tiene que gritarlo.
    """
    limite = banco.get("avisar_dias")
    if not limite or not descuentos:
        return
    capturado = descuentos[0].capturado
    if not capturado:
        return
    try:
        dias = (date.today() - date.fromisoformat(capturado)).days
    except ValueError:
        return
    if dias > int(limite):
        # `rehacer` dice DÓNDE se rehace. Antes decía `archivo`, que desde que
        # Santander llega en la pasada con fecha es el respaldo viejo: el aviso
        # mandaba a editar un YAML que ya no se lee.
        log.warning("%s: la captura es del %s (%d días). Toca rehacerla: %s",
                    banco["nombre"], capturado, dias,
                    banco.get("rehacer") or banco.get("archivo", ""))
