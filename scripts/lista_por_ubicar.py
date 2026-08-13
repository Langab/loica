#!/usr/bin/env python3
"""Arma la lista única de lo que falta ubicar en el mapa, ordenada por impacto.

    python3 scripts/lista_por_ubicar.py            # muestra
    python3 scripts/lista_por_ubicar.py --escribir # deja el documento auxiliar

Junta en un solo documento los dos catastros —lugares de eventos y locales con
descuento— porque quien va a buscar direcciones a mano no quiere abrir dos
listas: quiere una, ordenada por cuántos pines arregla cada búsqueda.

Se descarta lo que NO es un lugar (ticketeras, agregadores, programas
municipales, "Online"): buscarles dirección es perder el tiempo, porque no
tienen una.

El resultado va a `datos/revision/por_ubicar.md`, que es el documento de
trabajo, y lo que se resuelva se escribe en `config/correcciones/`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

RUTA_EVENTOS = RAIZ / "web" / "eventos.json"
RUTA_DESCUENTOS = RAIZ / "web" / "descuentos.json"
RUTA_SALIDA = RAIZ / "datos" / "revision" / "por_ubicar.md"

# Lo que no es un lugar físico y por lo tanto no tiene dirección que buscar.
NO_SON_LUGARES = re.compile(
    r"portaltickets|portaldisc|passline|puntoticket|ticketmaster|toliv"
    r"|red salas de teatro|deporte vecinal|escuelas abiertas"
    r"|academias deportivas|personas mayores|disfruta santiago"
    r"|^online$|^futbol$|^fútbol$|agregador|por confirmar|a confirmar",
    re.IGNORECASE)


def lugares_de_eventos() -> list[dict]:
    datos = json.loads(RUTA_EVENTOS.read_text(encoding="utf-8"))
    grupos: dict[tuple, dict] = {}
    for e in datos["eventos"]:
        if e.get("precision") not in ("comuna", "sin_ubicar"):
            continue
        nombre = (e.get("lugar") or "").strip()
        if not nombre or NO_SON_LUGARES.search(nombre):
            continue
        clave = (nombre, e.get("comuna") or "")
        g = grupos.setdefault(clave, {"nombre": nombre, "comuna": e.get("comuna") or "",
                                      "n": 0, "pista": "", "tipo": "evento"})
        g["n"] += 1
        if not g["pista"] and e.get("direccion"):
            g["pista"] = e["direccion"]
    return sorted(grupos.values(), key=lambda g: -g["n"])


def locales_de_descuentos() -> list[dict]:
    if not RUTA_DESCUENTOS.exists():
        return []
    datos = json.loads(RUTA_DESCUENTOS.read_text(encoding="utf-8"))
    grupos: dict[str, dict] = {}
    for d in datos["descuentos"]:
        if d.get("precision") in ("fuente", "calle", "correccion"):
            continue
        nombre = (d.get("comercio") or "").strip()
        if not nombre:
            continue
        g = grupos.setdefault(nombre, {"nombre": nombre, "comuna": d.get("comuna") or "",
                                       "n": 0, "pista": d.get("direccion") or "",
                                       "tipo": "descuento", "bancos": set()})
        g["n"] += 1
        g["bancos"].add(d.get("banco") or "")
        if not g["comuna"] and d.get("comuna"):
            g["comuna"] = d["comuna"]
    return sorted(grupos.values(), key=lambda g: -g["n"])


def tabla(titulo: str, filas: list[dict], destino: str) -> list[str]:
    lineas = [f"## {titulo} ({len(filas)})", "",
              f"Lo que se resuelva va a `config/correcciones/{destino}`.", "",
              "| # | Pines | Lugar | Comuna | Pista de la fuente |",
              "|---:|---:|---|---|---|"]
    for i, g in enumerate(filas, 1):
        pista = g["pista"] or ""
        if g.get("bancos"):
            pista = (pista + " · " if pista else "") + ", ".join(sorted(b for b in g["bancos"] if b))
        lineas.append(f"| {i} | {g['n']} | {g['nombre']} | {g['comuna'] or '—'} | {pista[:60] or '—'} |")
    lineas.append("")
    return lineas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--escribir", action="store_true")
    parser.add_argument("--tope", type=int, default=60,
                        help="cuántas filas por tabla (por defecto 60)")
    args = parser.parse_args()

    eventos = lugares_de_eventos()[:args.tope]
    descuentos = locales_de_descuentos()[:args.tope]

    lineas = [
        "# Por ubicar en el mapa",
        "",
        "Documento de trabajo: los lugares que hoy caen al centro de su comuna",
        "o no salen en el mapa, ordenados por cuántos pines arregla cada uno.",
        "",
        "**Cómo se completa.** Se busca la dirección en el sitio del local, su",
        "Instagram o Google Maps, y se anota en el YAML de correcciones con la",
        "fuente en `nota`. Una dirección que no se pueda verificar se deja en",
        "blanco: un pin equivocado manda a alguien a una esquina donde no hay",
        "nada, y eso es peor que no tener pin.",
        "",
        "Los agregadores, ticketeras y programas municipales quedan fuera de",
        "esta lista a propósito: no son lugares y no tienen dirección.",
        "",
    ]
    lineas += tabla("Lugares de eventos", eventos, "lugares.yaml")
    lineas += tabla("Locales con descuento", descuentos, "restoranes.yaml")

    texto = "\n".join(lineas)
    print(f"Lugares de eventos por ubicar: {len(lugares_de_eventos())}")
    print(f"Locales con descuento por ubicar: {len(locales_de_descuentos())}")
    if args.escribir:
        RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
        RUTA_SALIDA.write_text(texto, encoding="utf-8")
        print(f"Documento en {RUTA_SALIDA.relative_to(RAIZ)}")
    else:
        print()
        print(texto[:1800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
