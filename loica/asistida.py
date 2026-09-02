"""Dónde vive la extracción asistida de hoy.

Hasta el 01-09-2026 la pasada con el navegador dejaba sus archivos sueltos en
`datos/manual/`: `asistida.csv`, `cartelera_*.csv`, el YAML de Santander. Cada
pasada pisaba a la anterior y la única forma de ver la de la semana pasada era
ir al historial de git o a la copia archivada en `notas/asistida/`.

Desde entonces cada pasada llega como una CARPETA CON FECHA:

    datos/manual/
      _prompt_cine.md              plantillas y prompts (los que empiezan con _)
      blondie.yaml                 catastros sueltos escritos a mano
      dyzgo.yaml
      loica_asistida_20260825/     ← pasada del 25-08
      loica_asistida_20260901/     ← pasada del 01-09, la que manda hoy
        asistida.csv
        cartelera_cinepolis.csv
        descuentos_santander.csv
        RESUMEN_2026-09-01.md

Manda la carpeta con la fecha más nueva, y manda POR NOMBRE DE ARCHIVO: si la
pasada trae `asistida.csv`, la copia suelta de la raíz queda tapada. Lo que la
pasada NO trae —`blondie.yaml`, `fondas_2026.yaml`, catastros escritos a mano
que no dependen de la sesión con el navegador— se sigue leyendo de la raíz.

Esa regla es la que hace que la carpeta sea una FOTO COMPLETA y no un parche:
subir la carpeta reemplaza la pasada anterior entera, sin que quede la mitad
vieja mezclada con la mitad nueva. Y como la carpeta anterior queda ahí al
lado, comparar dos pasadas es `diff` entre dos carpetas.

La fecha viaja con los datos: es lo que deja que un descuento capturado a mano
diga en la ficha cuándo se capturó, en vez de hacerse pasar por fresco.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

log = logging.getLogger("loica.asistida")

DIR_MANUAL = Path(__file__).resolve().parent.parent / "datos" / "manual"

# loica_asistida_20260901. El prefijo lo pone quien arma la pasada; acá se
# acepta cualquier carpeta que termine en ocho dígitos de fecha para no atarse
# a un nombre exacto que después haya que cambiar en dos lugares.
PATRON_CARPETA = re.compile(r"^(.*_)?(\d{4})(\d{2})(\d{2})$")


def _fecha_de(nombre: str) -> date | None:
    m = PATRON_CARPETA.match(nombre)
    if not m:
        return None
    try:
        return date(int(m.group(2)), int(m.group(3)), int(m.group(4)))
    except ValueError:              # 20261332 no es una fecha
        return None


def pasadas(raiz: Path | None = None) -> list[tuple[date, Path]]:
    """Todas las pasadas con fecha, de la más nueva a la más vieja."""
    base = raiz or DIR_MANUAL
    if not base.exists():
        return []
    encontradas = []
    for hijo in base.iterdir():
        if not hijo.is_dir():
            continue
        fecha = _fecha_de(hijo.name)
        if fecha:
            encontradas.append((fecha, hijo))
    return sorted(encontradas, key=lambda par: par[0], reverse=True)


def ultima_pasada(raiz: Path | None = None) -> tuple[date, Path] | None:
    """La carpeta con fecha más nueva, o None si todavía no hay ninguna."""
    todas = pasadas(raiz)
    return todas[0] if todas else None


def fecha_captura(raiz: Path | None = None) -> date | None:
    """Cuándo se hizo la pasada más nueva."""
    ultima = ultima_pasada(raiz)
    return ultima[0] if ultima else None


def fecha_de_carpeta(carpeta: Path) -> date | None:
    """La fecha que declara el nombre de ESTA carpeta, o None si no declara.

    Sirve para fechar un archivo por dónde está y no por cuál es la pasada más
    nueva. La diferencia importa cuando un archivo viene suelto de la raíz
    mientras existe una pasada: ahí `fecha_captura` mentiría.
    """
    return _fecha_de(carpeta.name)


def archivos(patron: str, raiz: Path | None = None) -> list[Path]:
    """Los archivos que calzan con `patron`, con la pasada tapando a la raíz.

    Devuelve una lista ordenada por nombre. Un archivo de la raíz que tenga el
    mismo nombre que uno de la pasada NO entra: la pasada es la versión nueva
    del mismo dato, y leer las dos sería publicar la cartelera de la semana
    pasada junto a la de esta.

    Los que empiezan con `_` nunca entran: son plantillas y prompts para la
    persona que hace la pasada, no datos.
    """
    base = raiz or DIR_MANUAL
    elegidos: dict[str, Path] = {}

    ultima = ultima_pasada(base)
    if ultima:
        for ruta in sorted(ultima[1].glob(patron)):
            if not ruta.name.startswith("_"):
                elegidos[ruta.name] = ruta

    if base.exists():
        for ruta in sorted(base.glob(patron)):
            if ruta.is_dir() or ruta.name.startswith("_"):
                continue
            elegidos.setdefault(ruta.name, ruta)

    return [elegidos[nombre] for nombre in sorted(elegidos)]


def describir(raiz: Path | None = None) -> str:
    """Una línea para el log: qué pasada se está usando."""
    ultima = ultima_pasada(raiz)
    if not ultima:
        return f"sin carpeta con fecha; se leen los archivos sueltos de {(raiz or DIR_MANUAL).name}/"
    fecha, carpeta = ultima
    return f"pasada {carpeta.name} (capturada el {fecha:%d-%m-%Y})"
