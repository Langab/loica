#!/usr/bin/env python3
"""Construye el índice local de direcciones y locales desde los datos de OSM.

    python3 scripts/construir_indice_osm.py             # descarga si falta y construye
    python3 scripts/construir_indice_osm.py --sin-bajar # usa el .pbf que ya está

Deja `datos/indice_osm.db` (SQLite) con dos tablas:

  direcciones  calle + número → coordenadas, para geocodificar "Guillermo
               Subiabre 1015, Huechuraba" sin preguntarle a nadie.
  locales      nombre → coordenadas, para los bares, salas, teatros y canchas
               que publican eventos ("Bar de René", "Sala Metrónomo").

POR QUÉ ASÍ — la nota ética completa está en loica/geo.py: los robots.txt de
Nominatim, Photon y Overpass prohíben consultarlos en línea y este proyecto no
evade esos controles. La alternativa correcta es trabajar con la COPIA de los
datos: OpenStreetMap distribuye extractos justamente para esto (licencia
ODbL, la misma de los mosaicos que ya usa el mapa). El archivo se baja UNA
vez desde Geofabrik —un servicio cuyo único propósito es repartir estos
extractos; su robots.txt aparta a los crawlers de búsqueda, y su documentación
técnica invita a la descarga automatizada— y la corrida diaria del pipeline
nunca toca esa red: consulta el SQLite local.

El .pbf pesa ~330 MB y queda en datos/cache/ (ignorado por git). El índice
resultante pesa unos pocos MB y se reconstruye cuando se quiera actualizar:
bastan un par de veces al año.

Atribución: los datos son © colaboradores de OpenStreetMap, ODbL.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# La MISMA normalización que usa la consulta (loica/geo.py): si el índice y
# la consulta normalizan distinto, nada calza jamás.
from loica.geo import normalizar_osm as normalizar  # noqa: E402
RUTA_PBF = RAIZ / "datos" / "cache" / "chile-latest.osm.pbf"
RUTA_DB = RAIZ / "datos" / "indice_osm.db"
URL_PBF = "https://download.geofabrik.de/south-america/chile-latest.osm.pbf"

# Región Metropolitana con holgura: lo mismo que valida loica/geo.py.
LAT_MIN, LAT_MAX = -34.30, -32.90
LON_MIN, LON_MAX = -71.80, -70.00

# Qué locales interesan: los tipos de recinto que publican panoramas o tienen
# descuentos. Un nombre sin tipo conocido no sirve para desambiguar.
TIPOS_LOCAL = {
    "amenity": {"bar", "pub", "nightclub", "cafe", "restaurant", "fast_food",
                "theatre", "cinema", "arts_centre", "community_centre",
                "events_venue", "music_venue", "planetarium", "library"},
    "leisure": {"sports_centre", "stadium", "fitness_centre", "swimming_pool",
                "pitch", "sports_hall", "dance"},
    "tourism": {"museum", "gallery", "attraction"},
}


def bajar_pbf() -> None:
    RUTA_PBF.parent.mkdir(parents=True, exist_ok=True)
    print(f"Bajando {URL_PBF}")
    print("  (~330 MB, una sola vez; queda en datos/cache/)")
    peticion = urllib.request.Request(URL_PBF, headers={
        "User-Agent": "LoicaBot/1.0 (+https://langab.github.io/loica; indice local, descarga unica)"})
    with urllib.request.urlopen(peticion) as r, open(RUTA_PBF, "wb") as f:
        total = 0
        while True:
            pedazo = r.read(1 << 20)
            if not pedazo:
                break
            f.write(pedazo)
            total += len(pedazo)
            if total % (50 << 20) < (1 << 20):
                print(f"  … {total >> 20} MB")
    print(f"  Listo: {total >> 20} MB")


def construir() -> None:
    import osmium

    class Recolector(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.direcciones: list[tuple] = []
            self.locales: list[tuple] = []

        def _dentro(self, lat: float, lon: float) -> bool:
            return LAT_MIN < lat < LAT_MAX and LON_MIN < lon < LON_MAX

        def _procesar(self, tags, lat, lon):
            if not self._dentro(lat, lon):
                return
            calle = tags.get("addr:street")
            numero = tags.get("addr:housenumber")
            if calle and numero:
                # "1015-B" o "1015 dpto 3" → 1015. Sin número limpio no sirve.
                m = re.match(r"\d{1,5}", numero)
                if m:
                    self.direcciones.append(
                        (normalizar(calle), int(m.group()),
                         normalizar(tags.get("addr:city", "")), lat, lon))
            nombre = tags.get("name")
            if nombre:
                for llave, valores in TIPOS_LOCAL.items():
                    tipo = tags.get(llave)
                    if tipo in valores:
                        # La calle y la comuna del local, cuando OSM las trae:
                        # es lo que convierte "Naoki" en "Naoki, Isidora
                        # Goyenechea 3000, Las Condes" para la ficha.
                        calle = tags.get("addr:street", "")
                        numero = tags.get("addr:housenumber", "")
                        direccion = f"{calle} {numero}".strip() if calle else ""
                        self.locales.append((normalizar(nombre), tipo, lat, lon,
                                             direccion, tags.get("addr:city", "")))
                        break

        def node(self, n):
            self._procesar(n.tags, n.location.lat, n.location.lon)

        def way(self, w):
            # El centroide burdo del contorno alcanza: es un edificio, no un país.
            try:
                puntos = [(nd.location.lat, nd.location.lon) for nd in w.nodes
                          if nd.location.valid()]
            except osmium.InvalidLocationError:
                return
            if not puntos:
                return
            lat = sum(p[0] for p in puntos) / len(puntos)
            lon = sum(p[1] for p in puntos) / len(puntos)
            self._procesar(w.tags, lat, lon)

    print(f"Leyendo {RUTA_PBF.name} (esto toma unos minutos)…")
    rec = Recolector()
    rec.apply_file(str(RUTA_PBF), locations=True, idx="flex_mem")

    RUTA_DB.unlink(missing_ok=True)
    con = sqlite3.connect(RUTA_DB)
    con.executescript("""
        CREATE TABLE direcciones (calle TEXT, numero INTEGER, ciudad TEXT,
                                  lat REAL, lon REAL);
        CREATE INDEX idx_dir ON direcciones(calle, numero);
        CREATE TABLE locales (nombre TEXT, tipo TEXT, lat REAL, lon REAL,
                              direccion TEXT, ciudad TEXT);
        CREATE INDEX idx_loc ON locales(nombre);
    """)
    con.executemany("INSERT INTO direcciones VALUES (?,?,?,?,?)", rec.direcciones)
    con.executemany("INSERT INTO locales VALUES (?,?,?,?,?,?)", rec.locales)
    con.commit()
    con.close()
    print(f"Índice listo: {RUTA_DB}")
    print(f"  {len(rec.direcciones):,} direcciones y {len(rec.locales):,} locales de la RM")
    print()
    print("La corrida diaria corre en GitHub Actions y baja este archivo del release")
    print("`indice-osm` del repositorio. Para que use el índice nuevo, subirlo:")
    print("    gh release upload indice-osm datos/indice_osm.db --clobber")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-bajar", action="store_true",
                        help="no descargar: usar el .pbf ya presente")
    args = parser.parse_args()

    if not RUTA_PBF.exists():
        if args.sin_bajar:
            print(f"No existe {RUTA_PBF} y se pidió --sin-bajar.")
            return 1
        bajar_pbf()
    construir()
    return 0


if __name__ == "__main__":
    sys.exit(main())
