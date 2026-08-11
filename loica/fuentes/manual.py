"""Ingesta asistida: eventos que una persona encontró y el pipeline estructura.

No todo se puede rastrear. Hay tres casos permanentes:

  1. Sitios que bloquean el rastreo automático (Passline responde 403 a
     cualquier cliente que no sea un navegador de verdad).
  2. Instagram, donde vive buena parte del circuito de barrio y de las ferias,
     y cuya API no permite leer cuentas ajenas.
  3. El dato que llega por WhatsApp, por un afiche en la calle o porque el
     organizador lo mandó.

En los tres el descubrimiento lo hace una persona navegando normal. Lo que
aporta el pipeline es lo de siempre: normalizar, deduplicar contra lo que ya
existe, geocodificar y dejarlo en revisión con su link de origen.

Se escriben en `datos/manual/*.yaml` y entran como cualquier otra fuente, con
las mismas reglas: sin `fuente_url` no se guarda, porque sin atribución el
proyecto deja de ser un índice y pasa a ser una copia.

    eventos:
      - titulo: Colo-Colo vs Everton
        inicio: 2026-08-30 15:00
        lugar_nombre: Estadio Monumental
        comuna: Macul
        precio_texto: desde $12.000
        fuente_url: https://www.passline.com/eventos/...
        fuente_nombre: Passline
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

import yaml

from ..modelo import Evento
from ..normalizar import detectar_comuna, parsear_precio, resumir
from ..red import ClienteEducado

log = logging.getLogger("loica.manual")

DIR_MANUAL = Path(__file__).resolve().parent.parent.parent / "datos" / "manual"

# Campos que se aceptan tal cual desde el YAML. Cualquier otro se ignora en
# silencio: el archivo lo escribe una persona apurada, no un programa.
CAMPOS_TEXTO = ("titulo", "categoria", "descripcion_corta", "lugar_nombre",
                "lugar_direccion", "comuna", "precio_texto", "fuente_nombre",
                "fuente_url", "link_entradas", "imagen_url", "id_externo")


def _fecha(valor) -> datetime | None:
    """Acepta datetime, date o texto ISO. YAML ya convierte los dos primeros."""
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    if isinstance(valor, str) and valor.strip():
        from ..normalizar import parsear_fecha
        return parsear_fecha(valor)
    return None


def _desde_dict(crudo: dict, fuente: dict, origen: str) -> Evento | None:
    if not isinstance(crudo, dict):
        return None

    datos = {campo: str(crudo.get(campo, "") or "").strip() for campo in CAMPOS_TEXTO}
    if not datos["titulo"]:
        log.warning("%s: una entrada sin título — se omite", origen)
        return None
    if not datos["fuente_url"]:
        log.warning("%s: '%s' no trae fuente_url — se omite (rompe la atribución)",
                    origen, datos["titulo"][:50])
        return None

    # El precio puede venir como número, como "gratis" o como texto libre.
    precio = crudo.get("precio_clp")
    gratis = crudo.get("es_gratis")
    if precio is None and gratis is None and datos["precio_texto"]:
        precio, gratis, _ = parsear_precio(datos["precio_texto"])
    try:
        precio = int(precio) if precio is not None else None
    except (TypeError, ValueError):
        precio = None

    return Evento(
        titulo=datos["titulo"][:200],
        categoria=datos["categoria"],
        descripcion_corta=resumir(datos["descripcion_corta"]),
        inicio=_fecha(crudo.get("inicio")),
        fin=_fecha(crudo.get("fin")),
        lugar_nombre=datos["lugar_nombre"],
        lugar_direccion=datos["lugar_direccion"],
        comuna=detectar_comuna(datos["comuna"], datos["lugar_direccion"],
                               datos["lugar_nombre"], fuente.get("comuna", "")),
        precio_clp=precio,
        es_gratis=bool(gratis) if gratis is not None else None,
        precio_texto=datos["precio_texto"],
        fuente_tipo="manual",
        # Se conserva de dónde salió (Passline, Instagram, un afiche): el
        # curador tiene que poder juzgar cuán confiable es el dato.
        fuente_nombre=datos["fuente_nombre"] or fuente.get("nombre", "Ingesta manual"),
        fuente_url=datos["fuente_url"],
        link_entradas=datos["link_entradas"],
        imagen_url=datos["imagen_url"],
        id_externo=datos["id_externo"],
    )


def extraer_manual(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    """Lee todos los YAML de datos/manual/. No hace ninguna petición de red."""
    carpeta = Path(fuente.get("carpeta") or DIR_MANUAL)
    if not carpeta.exists():
        log.info("%s: todavía no existe %s", fuente.get("nombre"), carpeta)
        return []

    eventos: list[Evento] = []
    archivos = sorted(p for p in carpeta.glob("*.yaml") if not p.name.startswith("_"))

    for ruta in archivos:
        try:
            contenido = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            log.error("%s: YAML inválido (%s)", ruta.name, e)
            continue

        crudos = contenido.get("eventos") if isinstance(contenido, dict) else contenido
        if not isinstance(crudos, list):
            log.warning("%s: se esperaba una lista bajo 'eventos'", ruta.name)
            continue

        for crudo in crudos:
            evento = _desde_dict(crudo, fuente, ruta.name)
            if evento:
                eventos.append(evento)

    log.info("%s: %d eventos desde %d archivo(s) en %s",
             fuente.get("nombre"), len(eventos), len(archivos), carpeta.name)
    return eventos
