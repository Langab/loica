"""Adaptador para APIs JSON declaradas en la configuración.

Varias municipalidades ya no publican HTML: montaron una SPA sobre una API
propia (Ñuñoa Deportes sobre API Gateway, y las comunas en Ligup comparten
plataforma). Esos endpoints entregan el mejor dato del pipeline —recinto con
dirección, gratuidad como booleano, recurrencia estructurada— pero cada uno
nombra sus campos distinto.

En vez de un adaptador por municipio, el mapeo vive en `config/fuentes.yaml`
bajo la clave `json`, y aquí solo está la mecánica. Sumar la siguiente comuna
con la misma plataforma es escribir YAML, no código.

    json:
      lista: talleres                 # dónde está el arreglo
      plantilla_url: https://.../{_id}
      paginacion: {parametro: page, limite: 100, campo_total_paginas: totalPages}
      campos:
        titulo: nombre
        lugar_direccion: recinto.direccion
      recurrencia: {bloques: 'horarios[].bloques', dias: dias, hora_inicio: inicio}
"""

from __future__ import annotations

import logging
import re

from ..modelo import Evento
from ..normalizar import detectar_comuna, limpiar_html, parsear_fecha, resumir
from ..recurrencia import (frase_cadencia, parsear_dias, parsear_hora,
                           sesiones_futuras)
from ..red import ClienteEducado

log = logging.getLogger("loica.json")


def _camino(dato, ruta: str):
    """Sigue una ruta con puntos dentro del JSON. `a.b` baja un nivel.

    `a[].b` significa "por cada elemento de la lista a, toma b y aplana": es lo
    que permite leer horarios[].bloques sin escribir un bucle por cada fuente.
    """
    actual = dato
    for tramo in ruta.split("."):
        aplanar = tramo.endswith("[]")
        if aplanar:
            tramo = tramo[:-2]

        if isinstance(actual, list):
            siguiente = []
            for elemento in actual:
                if isinstance(elemento, dict) and tramo in elemento:
                    valor = elemento[tramo]
                    siguiente.extend(valor if isinstance(valor, list) else [valor])
            actual = siguiente
        elif isinstance(actual, dict):
            actual = actual.get(tramo)
        else:
            return None

        if aplanar and not isinstance(actual, list):
            actual = [actual] if actual is not None else []
        if actual is None:
            return None
    return actual


def _texto(dato, ruta: str) -> str:
    valor = _camino(dato, ruta) if ruta else None
    if isinstance(valor, list):
        valor = valor[0] if valor else None
    return limpiar_html(str(valor)) if valor not in (None, "") else ""


def _paginas(fuente: dict, cliente: ClienteEducado, url: str) -> list[dict]:
    """Recorre la API página por página hasta agotarla o llegar al tope."""
    config = fuente.get("json") or {}
    pag = config.get("paginacion") or {}
    ruta_lista = config.get("lista", "")

    parametro = pag.get("parametro", "page")
    primera = int(pag.get("desde", 1))
    limite = int(pag.get("limite", 100))
    max_paginas = int(pag.get("max_paginas", 20))
    campo_total = pag.get("campo_total_paginas", "totalPages")

    extra = dict(fuente.get("parametros") or {})
    recolectados: list[dict] = []
    pagina = primera

    while pagina < primera + max_paginas:
        params = dict(extra)
        if pag:
            params[parametro] = pagina
            if pag.get("parametro_limite"):
                params[pag["parametro_limite"]] = limite

        datos = cliente.json(url, params=params, max_edad_cache_seg=6 * 3600)
        if datos is None:
            break

        lote = _camino(datos, ruta_lista) if ruta_lista else datos
        if not isinstance(lote, list) or not lote:
            break
        recolectados.extend(x for x in lote if isinstance(x, dict))

        if not pag:
            break
        total = _camino(datos, campo_total) if campo_total else None
        try:
            if total is not None and pagina >= int(total) + primera - 1:
                break
        except (TypeError, ValueError):
            pass
        pagina += 1

    return recolectados


def _cumple_filtros(item: dict, filtros: dict) -> bool:
    """Descarta lo que la propia fuente marca como inactivo o cerrado."""
    for ruta, esperado in (filtros or {}).items():
        valor = _camino(item, ruta)
        if isinstance(esperado, list):
            if valor not in esperado:
                return False
        elif isinstance(esperado, bool):
            if bool(valor) is not esperado:
                return False
        elif str(valor).lower() != str(esperado).lower():
            return False
    return True


def _sesiones_del_taller(item: dict, config: dict, horizonte: int) -> tuple:
    """Traduce rango de ciclo + bloques semanales a (sesiones, cadencia).

    Sin recurrencia declarada devuelve la fecha única que traiga la fuente. Con
    recurrencia devuelve una sesión por fecha: `colapsar_multidia` decide
    después si son una temporada o sesiones sueltas (ver `sesiones_futuras`).
    """
    campos = config.get("campos") or {}
    desde = parsear_fecha(_texto(item, campos.get("inicio", "")))
    hasta = parsear_fecha(_texto(item, campos.get("fin", "")))

    rec = config.get("recurrencia") or {}
    if not rec or not desde:
        return ([desde] if desde else []), ""

    bloques = _camino(item, rec.get("bloques", "")) or []
    if not isinstance(bloques, list):
        bloques = [bloques]

    dias: list[int] = []
    hora_inicio = hora_fin = None
    for bloque in bloques:
        if not isinstance(bloque, dict):
            continue
        dias += parsear_dias(*(bloque.get(rec.get("dias", "dias")) or []))
        if hora_inicio is None:
            hora_inicio = parsear_hora(str(bloque.get(rec.get("hora_inicio", "inicio"), "")))
            hora_fin = parsear_hora(str(bloque.get(rec.get("hora_fin", "fin"), "")))

    dias = sorted(set(dias))
    if not dias:
        return ([desde] if desde else []), ""

    sesiones = sesiones_futuras(dias, hora_inicio, desde.date(),
                                hasta.date() if hasta else None, horizonte)
    return sesiones, frase_cadencia(dias, hora_inicio, hora_fin)


def extraer_json(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    config = fuente.get("json") or {}
    if not config:
        log.warning("%s: falta el bloque 'json' en la configuración", fuente.get("nombre"))
        return []

    endpoint = fuente.get("endpoint", "")
    url = endpoint if endpoint.startswith("http") else fuente["url_base"].rstrip("/") + endpoint

    crudos = _paginas(fuente, cliente, url)
    if not crudos:
        log.warning("%s: la API no devolvió elementos", fuente.get("nombre"))
        return []

    campos = config.get("campos") or {}
    filtros = config.get("filtros") or {}
    plantilla = config.get("plantilla_url", "")
    horizonte = int(fuente.get("horizonte_dias", 30))

    eventos: list[Evento] = []
    descartados_filtro = 0
    talleres = 0

    for item in crudos:
        if not _cumple_filtros(item, filtros):
            descartados_filtro += 1
            continue

        titulo = _texto(item, campos.get("titulo", "titulo"))
        if not titulo:
            continue

        sesiones, cadencia = _sesiones_del_taller(item, config, horizonte)
        if not sesiones:
            continue

        # La cadencia va primero: es lo que le dice al usuario que esto se
        # repite. El modelo todavía no tiene campo propio para recurrencia.
        descripcion = _texto(item, campos.get("descripcion_corta", ""))
        if cadencia:
            descripcion = f"{cadencia}. {descripcion}".strip()

        # La URL pública se arma con la plantilla: la API vive en otro dominio
        # y sin link a la ficha se rompe la atribución (y el evento se descarta).
        enlace = ""
        if plantilla:
            enlace = re.sub(r"\{([^}]+)\}",
                            lambda m: _texto(item, m.group(1)) or "", plantilla)
            if enlace.endswith("/") or "{" in enlace:
                enlace = ""
        enlace = enlace or fuente.get("url_agenda", "")

        gratis = None
        if campos.get("es_gratis"):
            crudo = _camino(item, campos["es_gratis"])
            if isinstance(crudo, bool):
                gratis = crudo

        direccion = _texto(item, campos.get("lugar_direccion", ""))
        lugar = _texto(item, campos.get("lugar_nombre", ""))
        comuna = detectar_comuna(_texto(item, campos.get("comuna", "")),
                                 direccion, fuente.get("comuna", ""))
        categoria = _texto(item, campos.get("categoria", ""))
        imagen = _texto(item, campos.get("imagen_url", ""))
        id_externo = _texto(item, campos.get("id_externo", ""))
        resumen = resumir(descripcion)

        talleres += 1
        for sesion in sesiones:
            eventos.append(Evento(
                titulo=titulo,
                categoria=categoria,
                descripcion_corta=resumen,
                inicio=sesion,
                lugar_nombre=lugar or fuente.get("nombre", ""),
                lugar_direccion=direccion,
                comuna=comuna,
                es_gratis=gratis,
                precio_texto="Gratis" if gratis else "",
                fuente_tipo="json",
                fuente_nombre=fuente.get("nombre", ""),
                fuente_url=enlace,
                imagen_url=imagen,
                id_externo=id_externo,
            ))

    log.info("%s: %d talleres → %d sesiones vía API JSON (%d descartados por filtro)",
             fuente.get("nombre"), talleres, len(eventos), descartados_filtro)
    return eventos
