"""Catastro de talleres permanentes: lugares que enseñan todas las semanas.

El pipeline sabe leer agendas: una agenda publica "el sábado 30 toca esto".
Un taller de cerámica no publica agenda porque no tiene nada que anunciar —
su clase de los martes a las 19:00 lleva tres años igual y va a seguir ahí el
mes que viene—. Ese dato no está en ningún feed: está escrito en prosa en la
página "Talleres" del estudio, y por eso el 96% de las clases del catastro
venían de tres corporaciones municipales de deportes mientras la cerámica, el
grabado, el teatro y la danza de Santiago no aparecían por ninguna parte.

Este adaptador lee `config/talleres.yaml` —un catastro que escribe una
persona, con su dirección y su link, igual que `config/cines.yaml`— y emite
una sesión por cada día que el lugar declara. El export las vuelve a juntar en
UNA tarjeta con sus `dias_semana` (ver `colapsar_series`), que es exactamente
lo que la página de talleres sabe filtrar por día.

Tres reglas que hacen que esto no se convierta en un archivo de mentiras:

  1. **Nada se inventa.** Un taller entra con los días y la hora que su sitio
     publica. El que no publica horario queda catastrado con `activo: false` y
     una nota: existe, se sabe dónde está, y alguien puede llamar y completarlo.
  2. **Todo caduca.** Cada entrada trae `verificado` y `vigente_hasta`. Pasada
     esa fecha el lugar deja de emitir sesiones y aparece en el registro de la
     corrida pidiendo revisión. Un horario de hace dos años no es un dato: es
     una promesa que el usuario va a ir a cobrarle al taller.
  3. **La atribución manda.** Sin `url` no se publica, como en toda fuente:
     la tarjeta existe para mandar a la gente al taller, no para reemplazarlo.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from ..modelo import Evento
from ..normalizar import parsear_precio, resumir
from ..recurrencia import (NOMBRES, frase_cadencia, parsear_dias, parsear_hora,
                           sesiones_futuras)
from ..red import ClienteEducado

log = logging.getLogger("loica.talleres")

CATASTRO = Path(__file__).resolve().parent.parent.parent / "config" / "talleres.yaml"

# Cuánto vale una verificación mientras nadie la renueve. Cuatro meses es el
# largo de una temporada de talleres en Chile (marzo-junio, agosto-noviembre):
# más que eso y el horario que se publica ya es de otro semestre.
VIGENCIA_POR_DEFECTO_DIAS = 120


def _fecha(valor) -> date | None:
    """YAML ya convierte `2026-08-24` en date; el texto suelto se tolera."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            return date.fromisoformat(valor.strip()[:10])
        except ValueError:
            return None
    return None


def _vigencia(lugar: dict, taller: dict) -> date | None:
    """Hasta cuándo vale este horario. El taller manda sobre el lugar."""
    explicita = _fecha(taller.get("vigente_hasta")) or _fecha(lugar.get("vigente_hasta"))
    if explicita:
        return explicita
    verificado = _fecha(taller.get("verificado")) or _fecha(lugar.get("verificado"))
    if verificado:
        return verificado + timedelta(days=VIGENCIA_POR_DEFECTO_DIAS)
    # Sin fecha de verificación no hay forma de saber si esto sigue vigente.
    return None


def _precio(taller: dict) -> tuple[int | None, bool | None, str]:
    texto = str(taller.get("precio_texto", "") or "").strip()
    if taller.get("gratis") is True:
        return None, True, texto or "Gratis"
    crudo = taller.get("precio_clp")
    if isinstance(crudo, int):
        return crudo, False, texto or "${:,}".format(crudo).replace(",", ".")
    if texto:
        precio, gratis, _ = parsear_precio(texto)
        return precio, gratis, texto
    return None, None, ""


def _eventos_de(lugar: dict, taller: dict, horizonte: int,
                hoy: date, distinguir_hora: bool = False) -> list[Evento]:
    titulo = str(taller.get("titulo", "") or "").strip()
    enlace = str(taller.get("url") or lugar.get("url") or "").strip()
    if not titulo or not enlace:
        return []

    dias = parsear_dias(*(taller.get("dias") or []))
    if not dias:
        return []

    hora_inicio = parsear_hora(str(taller.get("hora_inicio", "") or ""))
    hora_fin = parsear_hora(str(taller.get("hora_fin", "") or ""))
    hasta = _vigencia(lugar, taller)
    if not hasta or hasta < hoy:
        return []

    # Un ciclo que parte en octubre no tiene clases en septiembre. Sin esto,
    # `sesiones_futuras` arrancaría hoy y anunciaría cuatro sesiones que no
    # existen: el taller que publica su temporada con fecha de inicio la
    # declara acá y las sesiones empiezan cuando empieza de verdad.
    desde = _fecha(taller.get("vigente_desde")) or _fecha(lugar.get("vigente_desde"))
    sesiones = sesiones_futuras(dias, hora_inicio, desde, hasta, horizonte, hoy)
    if not sesiones:
        return []

    precio_clp, gratis, precio_texto = _precio(taller)
    cadencia = frase_cadencia(dias, hora_inicio, hora_fin)

    # El mismo curso dictado en cuatro horarios son CUATRO clases distintas
    # para quien elige a cuál puede ir, y el taller las publica así: "martes
    # 11:00, martes 19:30, miércoles 19:30, sábado 11:00". Río abajo hay dos
    # mecanismos que no las distinguen —la huella de deduplicación es
    # título+día+lugar y no mira la hora, y `colapsar_multidia` fusiona por
    # título+lugar lo que caiga a menos de cuatro días— así que sin esto tres
    # de las cuatro opciones desaparecían en silencio: de 92 sesiones entraban
    # 42, y la que quedaba se dibujaba como una temporada de un mes.
    #
    # El catastro guarda el nombre tal como lo escribe el taller; la etiqueta
    # se agrega acá y solo cuando el mismo nombre se repite en el mismo lugar.
    if distinguir_hora and hora_inicio:
        cuando = f"{NOMBRES[dias[0]]} " if len(dias) == 1 else ""
        titulo = f"{titulo} ({cuando}{hora_inicio.strftime('%H:%M')})"
    descripcion = ". ".join(x for x in (cadencia, str(taller.get("descripcion", "") or "").strip()) if x)

    eventos: list[Evento] = []
    for numero, sesion in enumerate(sesiones):
        eventos.append(Evento(
            titulo=titulo[:200],
            categoria=str(taller.get("categoria", "") or ""),
            descripcion_corta=resumir(descripcion),
            inicio=sesion,
            # `fin` en None a propósito: cada sesión es su propio evento y el
            # rango del taller es su temporada, no una función larga. Con un
            # `fin` puesto, `colapsar_series` deja de juntar las sesiones y la
            # página de talleres pierde el filtro por día.
            fin=None,
            # El nombre del lugar y el de quien dicta no siempre son lo mismo:
            # el Programa Adulto Mayor UC hace sus clases en el Centro de
            # Extensión UC, y es ESE nombre el que el índice de OSM conoce y
            # geocodifica exacto. Cuando el catastro declara `lugar`, manda.
            lugar_nombre=str(lugar.get("lugar") or lugar.get("nombre", "") or ""),
            lugar_direccion=str(lugar.get("direccion", "") or ""),
            comuna=str(lugar.get("comuna", "") or ""),
            precio_clp=precio_clp,
            es_gratis=gratis,
            precio_texto=precio_texto,
            fuente_tipo="talleres",
            fuente_nombre=str(lugar.get("nombre", "") or ""),
            fuente_url=enlace,
            imagen_url=str(lugar.get("imagen_url", "") or ""),
            id_externo=f"{lugar.get('id', '')}:{taller.get('id') or numero}",
        ))
    return eventos


def extraer_talleres(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    """Lee el catastro y emite las próximas sesiones. No pide nada a la red."""
    ruta = Path(fuente.get("catastro") or CATASTRO)
    if not ruta.is_absolute():
        ruta = CATASTRO.parent.parent / ruta
    if not ruta.exists():
        log.warning("%s: no existe el catastro %s", fuente.get("nombre"), ruta)
        return []

    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        log.error("%s: catastro ilegible (%s)", fuente.get("nombre"), e)
        return []

    lugares = datos.get("lugares") or []
    horizonte = int(fuente.get("horizonte_dias", 30))
    hoy = date.today()

    eventos: list[Evento] = []
    publicados = apagados = caducados = sin_horario = 0
    for lugar in lugares:
        if not isinstance(lugar, dict):
            continue
        if lugar.get("activo") is False:
            apagados += 1
            continue

        vencimiento = _vigencia(lugar, {})
        if vencimiento and vencimiento < hoy:
            # No se apaga solo: se avisa. Un taller caducado es trabajo
            # pendiente de una persona, no un error del programa.
            caducados += 1
            log.warning("%s: la verificación de %s venció el %s — hay que "
                        "volver a mirar su página", fuente.get("nombre"),
                        lugar.get("nombre"), vencimiento.isoformat())
            continue

        del_lugar = [t for t in (lugar.get("talleres") or []) if isinstance(t, dict)]
        repetidos = Counter(str(t.get("titulo", "") or "").strip() for t in del_lugar)

        for taller in del_lugar:
            if taller.get("activo") is False or not (taller.get("dias") or []):
                sin_horario += 1
                continue
            titulo = str(taller.get("titulo", "") or "").strip()
            nuevos = _eventos_de(lugar, taller, horizonte, hoy,
                                 distinguir_hora=repetidos[titulo] > 1)
            if nuevos:
                publicados += 1
                eventos.extend(nuevos)
            else:
                sin_horario += 1

    log.info("%s: %d talleres → %d sesiones desde %s (%d lugares apagados, "
             "%d con la verificación vencida, %d sin horario publicado)",
             fuente.get("nombre"), publicados, len(eventos), ruta.name,
             apagados, caducados, sin_horario)
    return eventos
