#!/usr/bin/env python3
"""Cruza los locales con descuento contra el índice de OSM y propone su ficha.

    python3 scripts/mapear_restoranes.py            # propone y muestra
    python3 scripts/mapear_restoranes.py --escribir # además deja el YAML

Santander publica 83 restaurantes y **ninguna dirección**: su catálogo se
captura a mano y solo trae el nombre. Falabella y Cencosud tampoco dan calle.
Eso son 185 descuentos que no caen en el mapa, y un descuento sin mapa es una
lista de nombres que no dice a dónde ir.

Acá se aprovecha que el índice local de OSM (datos/indice_osm.db) tiene 8.250
locales de comida de la RM con nombre, dirección y comuna. Se cruza el nombre
del comercio contra ese catastro y se propone la ficha completa.

REGLA DE ORO: se propone SOLO cuando el calce es inequívoco.
  - Nombre normalizado idéntico, y
  - un único local con ese nombre en toda la RM, o varios pero todos juntos
    (una cadena con locales dispersos NO se resuelve: "Starbucks" son 80
    direcciones distintas y elegir una es mentir), y
  - si el descuento declara comuna, el local tiene que estar ahí.

Lo que queda ambiguo se lista aparte para resolverlo a mano. El resultado va
a config/correcciones/restoranes.yaml, que el pipeline ya aplica solo.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from loica.geo import COMUNAS, normalizar_osm  # noqa: E402

RUTA_DESCUENTOS = RAIZ / "web" / "descuentos.json"
RUTA_INDICE = RAIZ / "datos" / "indice_osm.db"
RUTA_SALIDA = RAIZ / "datos" / "revision" / "propuesta_restoranes.yaml"

# Tipos del índice que son un local donde se come o se toma algo.
TIPOS_COMIDA = ("restaurant", "fast_food", "cafe", "bar", "pub")

# Nombres demasiado genéricos para calzar por sí solos: aunque el índice
# tenga uno solo, el del banco puede ser otro. Mejor dejarlos a mano.
GENERICOS = {"bar", "cafe", "restaurant", "restaurante", "pub", "sushi",
             "pizza", "buffet", "food", "market", "express", "delivery"}


def comuna_de(lat: float, lon: float, ciudad: str) -> str:
    """La comuna del local: la que declare OSM, si no la más cercana.

    El centroide más cercano se equivoca en los bordes, así que solo se usa
    cuando el punto está a menos de 6 km — más lejos que eso, mejor no decir
    comuna que decir una equivocada.
    """
    if ciudad:
        plano = normalizar_osm(ciudad)
        for nombre in COMUNAS:
            if normalizar_osm(nombre) == plano:
                return nombre
    mejor, mejor_d2 = "", 6 ** 2
    for nombre, (clat, clon) in COMUNAS.items():
        d2 = ((lat - clat) * 111) ** 2 + ((lon - clon) * 92) ** 2
        if d2 < mejor_d2:
            mejor, mejor_d2 = nombre, d2
    return mejor


def buscar(con: sqlite3.Connection, comercio: str, comuna: str) -> tuple[dict | None, str]:
    """Devuelve (ficha, motivo). ficha=None cuando el calce no es inequívoco."""
    clave = normalizar_osm(comercio)
    if not clave or len(clave) < 4:
        return None, "nombre muy corto"
    if clave in GENERICOS:
        return None, "nombre genérico"

    marcadores = ",".join("?" * len(TIPOS_COMIDA))
    filas = con.execute(
        f"""SELECT nombre, tipo, lat, lon, direccion, ciudad FROM locales
            WHERE nombre = ? AND tipo IN ({marcadores}) LIMIT 200""",
        (clave, *TIPOS_COMIDA)).fetchall()
    if not filas:
        return None, "no está en el catastro"

    # LAS CADENAS SE DESCARTAN, y no importa que el descuento declare comuna.
    # La corrección se guarda POR NOMBRE, así que una sola ficha de
    # "Starbucks" mandaría los 135 locales de la ciudad a la misma esquina.
    # Para una cadena, la respuesta honesta es el centro de la comuna que
    # declare cada descuento, no un pin falsamente preciso.
    if len(filas) > 1:
        lats = [f[2] for f in filas]
        lons = [f[3] for f in filas]
        if ((max(lats) - min(lats)) * 111 > 1.5
                or (max(lons) - min(lons)) * 92 > 1.5):
            return None, f"cadena: {len(filas)} locales dispersos en la RM"

    # Si el descuento declara comuna, el único local tiene que estar ahí.
    if comuna and comuna in COMUNAS:
        clat, clon = COMUNAS[comuna]
        if ((filas[0][2] - clat) * 111) ** 2 + ((filas[0][3] - clon) * 92) ** 2 >= 7 ** 2:
            return None, f"el local del catastro no queda en {comuna}"

    nombre, tipo, lat, lon, direccion, ciudad = filas[0]

    # El extracto de OSM se recorta con holgura y alcanza a traer localidades
    # de la región vecina: "Social Bar" calzó con uno de Machalí, a 90 km.
    # Se exige el mismo recuadro que valida config/correcciones/.
    if not (-34.05 <= lat <= -33.00 and -71.30 <= lon <= -70.30):
        return None, "el local del catastro queda fuera de la RM"
    zona = comuna or comuna_de(lat, lon, ciudad)
    if not zona:
        return None, "no se pudo determinar la comuna"

    # Un local que el catastro tiene CON calle y número es un negocio mapeado
    # de verdad; uno con solo un punto puede ser un homónimo que alguien marcó
    # de paso. Los primeros entran solos, los segundos van a revisión.
    return {
        "comercio": comercio,
        "direccion": direccion,
        "comuna": zona,
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "tipo_osm": tipo,
        "confianza": "alta" if direccion else "media",
    }, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--escribir", action="store_true",
                        help="deja la propuesta en datos/revision/")
    parser.add_argument("--banco", help="solo este banco (por id)")
    args = parser.parse_args()

    if not RUTA_INDICE.exists():
        print("Falta el índice. Corré: python3 scripts/construir_indice_osm.py")
        return 1

    datos = json.loads(RUTA_DESCUENTOS.read_text(encoding="utf-8"))
    descuentos = datos["descuentos"]
    if args.banco:
        descuentos = [d for d in descuentos if d["banco_id"] == args.banco]

    # Un local puede aparecer en varios bancos; se resuelve una vez.
    pendientes: dict[str, str] = {}
    for d in descuentos:
        if d.get("precision") in ("fuente", "calle", "correccion"):
            continue
        pendientes.setdefault(d["comercio"], d.get("comuna") or "")

    con = sqlite3.connect(f"file:{RUTA_INDICE}?mode=ro", uri=True)
    resueltos, sin_calce = [], []
    for comercio, comuna in sorted(pendientes.items()):
        ficha, motivo = buscar(con, comercio, comuna)
        (resueltos if ficha else sin_calce).append(ficha or (comercio, motivo))
    con.close()

    altas = [f for f in resueltos if f["confianza"] == "alta"]
    medias = [f for f in resueltos if f["confianza"] == "media"]
    print(f"{len(pendientes)} locales sin ubicación exacta")
    print(f"  con dirección en el catastro (entran solos): {len(altas)}")
    print(f"  solo con coordenada (van a revisión): {len(medias)}")
    print(f"  sin calce, quedan a mano: {len(sin_calce)}")
    print()
    for f in altas:
        print(f"  {f['comercio'][:32]:32s} → {f['direccion'][:34]:34s} "
              f"{f['comuna'][:14]:14s} ({f['tipo_osm']})")

    if resueltos and args.escribir:
        RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
        lineas = [
            "# Propuesta de fichas de restoranes armada por",
            "# scripts/mapear_restoranes.py cruzando los nombres contra el",
            "# catastro local de OSM. Cada entrada tuvo un calce INEQUÍVOCO:",
            "# nombre idéntico y un solo local en la RM (las cadenas se",
            "# descartan: la corrección se guarda por nombre y mandaría los",
            "# 135 Starbucks de la ciudad a la misma esquina).",
            "#",
            "# Revisar y pegar en config/correcciones/restoranes.yaml.",
            "",
            "restoranes:",
        ]
        for f in altas:
            lineas.append(f"  {f['comercio']}:")
            lineas.append(f"    direccion: {f['direccion']}")
            if f["comuna"]:
                lineas.append(f"    comuna: {f['comuna']}")
            lineas.append(f"    lat: {f['lat']}")
            lineas.append(f"    lon: {f['lon']}")
            lineas.append(f"    nota: calce único con dirección en el catastro OSM ({f['tipo_osm']})")
            lineas.append("")
        if medias:
            lineas += [
                "# ---- calce único PERO sin dirección en el catastro ----",
                "# Es solo un punto con ese nombre: puede ser un homónimo que",
                "# alguien marcó de paso. Verificar antes de descomentar.",
                "",
            ]
            for f in medias:
                lineas.append(f"#  {f['comercio']}:")
                lineas.append(f"#    comuna: {f['comuna']}")
                lineas.append(f"#    lat: {f['lat']}")
                lineas.append(f"#    lon: {f['lon']}")
                lineas.append(f"#    nota: punto único en OSM ({f['tipo_osm']}), sin dirección — verificar")
                lineas.append("")
        lineas += ["# ---- sin calce, resolver a mano ----"]
        lineas += [f"#   {c}  ({m})" for c, m in sin_calce]
        RUTA_SALIDA.write_text("\n".join(lineas), encoding="utf-8")
        print(f"\nPropuesta en {RUTA_SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
