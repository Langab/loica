#!/usr/bin/env python3
"""Catastro de salas de cine de la Región Metropolitana → config/cines.yaml.

    python3 scripts/catastro_cines.py            # refresca el catastro
    python3 scripts/catastro_cines.py --seco     # muestra los cambios y no escribe

Una sala de cine no es un evento: es una dirección que va a seguir ahí el año
que viene. Por eso el catastro se guarda en el repositorio y no se vuelve a
pedir en cada corrida — el mapa de la página de cine se dibuja con esto,
incluso el de las cadenas cuya cartelera no se puede leer.

De dónde sale cada dato:

  · **Cinemark**, por su BFF público (bff.cinemark.cl/api/cinema/theaters):
    nombre, slug, dirección y coordenadas como campos propios, incluida la
    sala Portal La Dehesa que su página /cines no lista. Es la fuente más
    precisa que hay y es de ellos mismos.
  · **El índice OSM local** (`datos/indice_osm.db`, el mismo que geocodifica
    todo el pipeline) para las demás salas: Cinépolis, Cineplanet, los cines
    de barrio y las salas de los centros culturales. Overpass daría además el
    mall que contiene cada sala, pero su robots.txt prohíbe `/api/` y el
    proyecto respeta robots.txt aunque el servicio sea programable: los
    nombres de mall que hoy están en el YAML se confirmaron una vez y viven
    ahí como dato revisado a mano.

Lo que una persona escribió en el YAML —el nombre corregido, el circuito, los
alias con que otras fuentes nombran la sala— manda siempre. El script solo
rellena huecos, agrega salas nuevas y avisa de lo que cambió. Una entrada con
`verificado: true` no se pisa nunca.
"""

from __future__ import annotations

import argparse
import math
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from loica.geo import COMUNAS  # noqa: E402
from loica.normalizar import detectar_comuna  # noqa: E402
from loica.red import ClienteEducado  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "config" / "cines.yaml"
INDICE = RAIZ / "datos" / "indice_osm.db"

CINEMARK_CINES = "https://www.cinemark.cl/cines"

# Cómo se llama cada cadena para mostrar y qué circuito es. El circuito no es
# cosmético: es el filtro que separa "las doce salas del mall" de "la sala de
# cien butacas donde dan la película húngara".
CADENAS = {
    "cinemark": ("Cinemark", "comercial"),
    "cineplanet": ("Cineplanet", "comercial"),
    "cinepolis": ("Cinépolis", "comercial"),
}

# El sitio al que lleva el botón cuando la sala no tiene página propia. Una
# ficha sin URL deja el botón muerto, y la promesa de la página de cine es
# justamente dejar a la persona en la boletería del cine: es mejor mandarla a
# la portada de la cadena, donde puede elegir su sala, que a ninguna parte.
SITIO_CADENA = {
    "cineplanet": "https://www.cineplanet.cl/",
    "cinepolis": "https://cinepolis.com/cl",
    "cinemark": "https://www.cinemark.cl/",
}

# Las salas que viven DENTRO de un centro cultural no están etiquetadas como
# cine en OSM —el edificio es un arts_centre— así que se buscan por el nombre
# del edificio. Sin esto la Cineteca Nacional y el cine de Matucana 100 no
# existen para el catastro, y son dos de las mejores salas de la ciudad.
SALAS_EN_CENTROS = {
    "cineteca-nacional": {
        "nombre": "Cineteca Nacional de Chile",
        "edificio": "centro cultural palacio de la moneda",
        "direccion": "Plaza de la Ciudadanía 26",
        "comuna": "Santiago",
        "url": "https://www.cclm.cl/cineteca-nacional/",
        "alias": ["Cineteca Nacional", "Centro Cultural La Moneda", "CCLM"],
    },
    "sala-cine-m100": {
        "nombre": "Sala de Cine Matucana 100",
        "edificio": "centro cultural matucana 100",
        "direccion": "Av. Matucana 100",
        "comuna": "Estación Central",
        "url": "https://www.m100.cl/",
        "alias": ["MATUCANA 100 / CINE", "Matucana 100", "M100"],
    },
    "centro-cine-creacion": {
        "nombre": "Centro de Cine y Creación",
        "edificio": "centro de cine y creacion",
        "direccion": "Raulí 571",
        "comuna": "Santiago",
        "url": "https://centrodecineycreacion.cl/",
        "alias": ["CCC", "Centro de Cine y Creación"],
    },
}


# --- Lo que se verificó una vez, a mano -------------------------------------
#
# OSM tiene las salas de Cinépolis y Cineplanet con el nombre de la cadena
# pelado: veinte pines que dicen "Cinepolis" y ninguno dice en qué mall está,
# que es justo lo único que le sirve a alguien buscando dónde ver la película.
#
# El nombre de cada una salió de cruzar su coordenada con el centro comercial
# que la contiene (`shop=mall` de OSM a menos de 350 m, consultado por
# Overpass el 24-08-2026). Es evidencia, no memoria: la sala de Av. Larraín
# 5862 está a 45 m del polígono de Mall Plaza Egaña. Las que no tenían ningún
# mall cerca quedaron con su comuna y `verificado: false`, que es una pregunta
# abierta para la próxima extracción asistida, no un nombre inventado.
#
# Vive acá y no solo en el YAML para que el catastro se pueda reconstruir de
# cero: se borra config/cines.yaml, se corre el script y vuelve entero.
#
# Los nombres de Cineplanet son los de su propia lista de salas.
CURADOS = {
    # Cinépolis (ex Cinehoyts), por el mall que la contiene
    (-33.34337, -70.54443): ("Cinépolis Paseo Los Trapenses", "Lo Barnechea"),
    (-33.40193, -70.51449): ("Cinépolis Paseo Los Dominicos", "Las Condes"),
    (-33.41507, -70.54122): ("Cinépolis Plaza Los Dominicos", "Las Condes"),
    (-33.50069, -70.75646): ("Cinépolis Terrazas Maipú", "Maipú"),
    (-33.48228, -70.75168): ("Cinépolis Arauco Maipú", "Maipú"),
    (-33.63207, -70.71063): ("Cinépolis Mallplaza Sur", "San Bernardo"),
    (-33.59531, -70.70705): ("Cinépolis Paseo San Bernardo", "San Bernardo"),
    (-33.45294, -70.67837): ("Cinépolis Portal Exposición", "Estación Central"),
    (-33.40206, -70.57796): ("Cinépolis Parque Arauco", "Las Condes"),
    (-33.39840, -70.59908): ("Cinépolis Casacostanera", "Vitacura"),
    (-33.45211, -70.56976): ("Cinépolis Mallplaza Egaña", "La Reina"),
    (-33.36902, -70.72975): ("Cinépolis Arauco Quilicura", "Quilicura"),
    (-33.43956, -70.64855): ("Cinépolis Vivo Imperio", "Santiago"),
    (-33.53509, -70.57102): ("Cinépolis Vivo Outlet La Florida", "La Florida"),
    (-33.68004, -71.18532): ("Cinépolis Melipilla", "Melipilla"),
    # Cineplanet, con los nombres de su propia lista de salas. Ojo: su lista
    # tiene CINCO salas en la RM, no seis — el pin de OSM en Av. La Dehesa 1445
    # que decía "Cineplanet" era una etiqueta vieja: ese cine es el Cinemark
    # Portal La Dehesa (lo confirma el BFF de Cinemark, con 5 salas y su
    # dirección exacta). Ese punto se descarta abajo, en PUNTOS_FALSOS.
    (-33.452882, -70.682639): ("Cineplanet Alameda", "Estación Central"),
    (-33.418240, -70.606685): ("Cineplanet Costanera Center", "Providencia"),
    (-33.509389, -70.608215): ("Cineplanet Florida Center", "La Florida"),
    (-33.424787, -70.654398): ("Cineplanet Mall Barrio Independencia", "Independencia"),
    (-33.487742, -70.576967): ("Cineplanet Quilín", "Peñalolén"),
    # Cines de barrio: acá el nombre de OSM es el bueno, se arregla el calce
    (-33.445308, -70.650245): ("Centro Arte Alameda — Sala CEINA", "Santiago"),
    (-33.438493, -70.640977): ("El Biógrafo", "Santiago"),
    (-33.447383, -70.652052): ("Cine Arte Normandie", "Santiago"),
    (-33.441113, -70.641241): ("Cine UC", "Santiago"),
    (-33.437032, -70.649528): ("Cine Mayo", "Santiago"),
    (-33.486801, -70.627370): ("MUVIX Cinema", "San Joaquín"),
    (-33.429928, -70.634156): ("ZooCine", "Santiago"),
}

# Puntos de OSM que sabemos EQUIVOCADOS: etiquetas viejas que nombran una
# cadena que ya no está (o nunca estuvo) en esa dirección. Se descartan por
# cercanía, con su porqué escrito — borrar un dato sin decir por qué es como
# se pierden las discusiones dentro de seis meses.
PUNTOS_FALSOS = {
    # OSM dice "Cineplanet" en Av. La Dehesa 1445. Cineplanet no tiene sala en
    # Lo Barnechea (su propia lista: 5 salas RM); el cine de ese mall es el
    # Cinemark Portal La Dehesa, que entra por el BFF con dirección propia.
    (-33.3569374, -70.5142459): "etiqueta vieja: ahí está Cinemark Portal La Dehesa",
}

# Sitio oficial y de dónde sale la cartelera de las salas que no son Cinemark.
# La URL es a lo que lleva el botón "comprar": si no la sabemos, la ficha
# muestra la dirección y no un link roto.
FICHAS = {
    "Cine Arte Normandie": {
        "url": "https://normandie.cl/cartelera/", "cartelera": "semanal",
        "alias": ["Cine Arte Normandie", "Normandie", "Cine Normandie"]},
    "El Biógrafo": {
        "url": "https://elbiografo.cl/", "cartelera": "semanal",
        "alias": ["El Biógrafo", "Cine Arte El Biógrafo", "Biógrafo", "El Biografo"]},
    "Centro Arte Alameda — Sala CEINA": {
        "url": "https://centroartealameda.cl/", "cartelera": "agenda",
        "alias": ["Centro Arte Alameda", "Centro Arte Alameda / Sala CEINA",
                  "CENTRO ARTE ALAMEDA", "Sala CEINA", "CEINA",
                  "Cine Arte Alameda", "Arte Alameda"]},
    "MUVIX Cinema": {
        "url": "https://muvix.cl/", "cartelera": "navegador", "circuito": "comercial",
        "alias": ["MUVIX", "Muvix Cinema"]},
    "Cine UC": {"cartelera": "navegador", "alias": ["Cine UC", "Centro de Extensión UC"]},
    "Cine Mayo": {"cartelera": "navegador", "alias": ["Cine Mayo"]},
    "ZooCine": {"cartelera": "navegador", "alias": ["ZooCine", "Zoocine"]},
    "Cineplanet Alameda": {"url": "https://www.cineplanet.cl/"},
    "Cineplanet Costanera Center": {"url": "https://www.cineplanet.cl/"},
    "Cineplanet Florida Center": {"url": "https://www.cineplanet.cl/"},
    "Cineplanet Mall Barrio Independencia": {"url": "https://www.cineplanet.cl/"},
    "Cineplanet Quilín": {"url": "https://www.cineplanet.cl/"},
}


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn").lower()


def _identificador(nombre: str) -> str:
    limpio = re.sub(r"[^a-z0-9]+", "-", _sin_tildes(nombre)).strip("-")
    return limpio or "cine"


def _metros(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia plana. A escala de ciudad el error del plano es despreciable
    y evita arrastrar una dependencia geodésica para comparar 50 puntos."""
    return math.hypot((a[0] - b[0]) * 111_320, (a[1] - b[1]) * 92_600)


def en_rm(lat: float, lon: float) -> bool:
    """A menos de 30 km del centro de alguna comuna de la RM.

    Una caja de coordenadas no sirve: la RM llega hasta el oeste de Melipilla
    y en esa misma longitud, doscientos kilómetros al norte, está Viña del Mar
    — que Cinemark publica en la misma lista. Medir contra los centroides que
    el geocodificador ya conoce deja fuera a Viña y adentro a Melipilla.
    """
    return any(_metros((lat, lon), centro) < 30_000 for centro in COMUNAS.values())


def _comuna(punto: tuple[float, float], *textos: str) -> str:
    """La comuna que dice la dirección y, si no la dice, la del centroide más
    cercano. Cinemark escribe "Gran Avenida José Miguel Carrera 6150": el
    nombre de la avenida no nombra la comuna, pero la coordenada sí."""
    declarada = detectar_comuna(*[t for t in textos if t])
    if declarada:
        return declarada
    cercanas = sorted((_metros(punto, centro), nombre) for nombre, centro in COMUNAS.items())
    return cercanas[0][1] if cercanas and cercanas[0][0] < 8_000 else ""


def _curado(punto: tuple[float, float]) -> tuple[str, str] | None:
    """El nombre verificado de la sala que está en ese punto, si lo hay.

    Se compara por cercanía y no por igualdad: OSM corrige coordenadas cada
    tanto y un desplazamiento de veinte metros no convierte una sala en otra.
    """
    for coordenada, ficha in CURADOS.items():
        if _metros(punto, coordenada) < 200:
            return ficha
    return None


def _marca(nombre: str) -> str:
    plano = _sin_tildes(nombre)
    for clave in CADENAS:
        if clave in plano:
            return clave
    return "independiente"


def cines_de_cinemark(cliente: ClienteEducado) -> list[dict]:
    """La lista oficial, ahora por su BFF (bff.cinemark.cl/api/cinema/theaters).

    Antes se leía del HTML de /cines, desescapando el payload de Next con una
    expresión regular. El BFF entrega lo mismo en JSON limpio y con DOS mejoras
    que el HTML no tenía: coordenadas como campos propios (no adentro de una
    URL de Google Maps) y la sala Portal La Dehesa, que la página /cines no
    lista pero el BFF sí — y existe: 5 salas en Avenida La Dehesa 1445.

    Está abierto: 200 a nuestro user-agent identificado, sin credencial
    (medido el 25-08-2026). Si deja de responder, el catastro conserva lo que
    ya tenía, que es exactamente lo que debe pasar.
    """
    respuesta = cliente.obtener("https://bff.cinemark.cl/api/cinema/theaters",
                                max_edad_cache_seg=24 * 3600)
    if respuesta is None or not respuesta.ok:
        print("  Cinemark: el BFF no respondió — se conserva lo que ya estaba", file=sys.stderr)
        return []
    try:
        teatros = (respuesta.json() or {}).get("data") or []
    except ValueError:
        print("  Cinemark: el BFF no devolvió JSON", file=sys.stderr)
        return []

    salas = []
    for t in teatros:
        try:
            lat, lon = float(t["latitude"]), float(t["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if not t.get("slug") or not t.get("name"):
            continue
        salas.append({
            "slug": t["slug"], "nombre": t["name"],
            "direccion": (t.get("address") or "").strip(),
            "formatos": " | ".join(f.get("shortName", "") for f in t.get("formats") or []
                                   if isinstance(f, dict) and f.get("shortName")),
            "lat": lat, "lon": lon,
        })
    return salas


def cines_del_indice() -> list[dict]:
    if not INDICE.exists():
        print("  Falta datos/indice_osm.db — solo entra Cinemark", file=sys.stderr)
        return []
    con = sqlite3.connect(INDICE)
    filas = con.execute(
        "SELECT nombre, lat, lon, direccion, ciudad FROM locales WHERE tipo = 'cinema'"
    ).fetchall()
    con.close()
    return [{"nombre": f[0], "lat": f[1], "lon": f[2], "direccion": f[3] or "",
             "ciudad": f[4] or ""} for f in filas]


def salas_de_centros() -> list[dict]:
    if not INDICE.exists():
        return []
    con = sqlite3.connect(INDICE)
    salidas = []
    for clave, ficha in SALAS_EN_CENTROS.items():
        fila = con.execute("SELECT lat, lon FROM locales WHERE nombre = ? LIMIT 1",
                           (ficha["edificio"],)).fetchone()
        if not fila:
            print(f"  {ficha['nombre']}: sin coordenada en el índice OSM", file=sys.stderr)
            continue
        salidas.append({
            "id": clave, "nombre": ficha["nombre"], "cadena": "independiente",
            "circuito": "arte", "direccion": ficha["direccion"], "comuna": ficha["comuna"],
            "lat": round(fila[0], 6), "lon": round(fila[1], 6), "url": ficha["url"],
            "formatos": "", "cartelera": "agenda", "fuente_geo": "osm",
            "alias": ficha["alias"], "verificado": True,
        })
    con.close()
    return salidas


def construir() -> list[dict]:
    cliente = ClienteEducado(crawl_delay_seg=2, timeout=60)

    print("Cinemark…")
    cinemark = [s for s in cines_de_cinemark(cliente) if en_rm(s["lat"], s["lon"])]
    print(f"  {len(cinemark)} salas en la RM")

    print("Índice OSM local…")
    indice = [c for c in cines_del_indice() if en_rm(c["lat"], c["lon"])]
    print(f"  {len(indice)} salas en la RM")

    catastro: list[dict] = []
    for sala in cinemark:
        catastro.append({
            "id": sala["slug"],
            "nombre": sala["nombre"],
            "cadena": "cinemark",
            "circuito": "comercial",
            "direccion": sala["direccion"],
            "comuna": _comuna((sala["lat"], sala["lon"]), sala["direccion"]),
            "lat": round(sala["lat"], 6),
            "lon": round(sala["lon"], 6),
            "url": f"https://www.cinemark.cl/cartelera/{sala['slug']}",
            "formatos": sala["formatos"],
            "cartelera": "cinemark",
            "fuente_geo": "cinemark",
            "verificado": True,
        })

    puntos_cinemark = [(s["lat"], s["lon"]) for s in cinemark]
    for sala in indice:
        punto = (sala["lat"], sala["lon"])
        motivo_falso = next((m for p, m in PUNTOS_FALSOS.items()
                             if _metros(punto, p) < 200), None)
        if motivo_falso:
            print(f"  descartado un punto de OSM: {motivo_falso}")
            continue
        cadena = _marca(sala["nombre"])
        # Cinemark ya entró con su dato oficial: el nodo de OSM es el mismo
        # local visto de lejos.
        if cadena == "cinemark" and any(_metros(punto, q) < 500 for q in puntos_cinemark):
            continue
        etiqueta, circuito = CADENAS.get(cadena, (sala["nombre"].title(), "arte"))
        comuna = _comuna(punto, sala["ciudad"], sala["direccion"])
        curado = _curado(punto)
        if curado:
            nombre, comuna = curado[0], curado[1] or comuna
        elif cadena in CADENAS:
            # El índice guarda el nombre en minúsculas y sin el mall, así que
            # "Cinépolis" a secas queda como pregunta abierta para la próxima
            # extracción asistida, no como nombre bueno.
            nombre = f"{etiqueta} {comuna}".strip() if comuna else etiqueta
        else:
            nombre = sala["nombre"].title()

        ficha = {
            "id": _identificador(nombre if curado else f"{nombre} {comuna or sala['direccion']}"),
            "nombre": nombre,
            "cadena": cadena,
            "circuito": circuito,
            "direccion": sala["direccion"],
            "comuna": comuna,
            "lat": round(sala["lat"], 6),
            "lon": round(sala["lon"], 6),
            "url": "",
            "formatos": "",
            "cartelera": "navegador" if cadena in CADENAS else "",
            "fuente_geo": "osm",
            "verificado": bool(curado),
        }
        extra = FICHAS.get(nombre, {})
        ficha.update(extra)
        if not ficha.get("url"):
            ficha["url"] = SITIO_CADENA.get(cadena, "")
        if cadena in CADENAS and "alias" not in ficha:
            # Con el nombre de la sala y el de la cadena a secas alcanza para
            # pegar la función que llega escrita "Cinépolis" y nada más.
            ficha["alias"] = [nombre, etiqueta]
        catastro.append(ficha)

    return _desambiguar(catastro + salas_de_centros())


def _desambiguar(catastro: list[dict]) -> list[dict]:
    """Dos salas no pueden llamarse igual.

    Melipilla tiene dos Cinépolis y Puente Alto otros dos, y como el nombre se
    arma con la comuna cuando no hay mall, salían las cuatro con el mismo
    rótulo. Eso no es un problema estético: `loica/cines.py` pega cada función
    con su sala por nombre, y con dos candidatas idénticas todas las funciones
    de las dos se apilarían en un solo pin. La calle desempata, y la que ya
    tenía nombre confirmado se queda con el suyo.
    """
    from collections import Counter
    repetidos = {n for n, veces in Counter(c["nombre"] for c in catastro).items() if veces > 1}
    for ficha in catastro:
        if ficha["nombre"] not in repetidos or ficha.get("verificado"):
            continue
        calle = (ficha.get("direccion") or "").strip()
        if calle:
            ficha["nombre"] = f"{ficha['nombre']} ({calle})"
            ficha["id"] = _identificador(ficha["nombre"])
    return catastro


def _cerca(ficha: dict, otras: list[dict], metros: float = 250) -> dict | None:
    """La misma sala mapeada con otro id (OSM la movió, cambió el nombre)."""
    punto = (ficha["lat"], ficha["lon"])
    for otra in otras:
        if otra.get("lat") is None:
            continue
        if _metros(punto, (otra["lat"], otra["lon"])) < metros:
            return otra
    return None


# Campos que el script NUNCA pisa: son juicio de una persona, no dato medible.
DE_LA_CASA = ("nombre", "alias", "url", "circuito", "cartelera", "notas", "id_cartelera")


def fusionar(nuevo: list[dict], viejo: list[dict]) -> tuple[list[dict], list[str]]:
    pendientes = list(viejo)
    salida, notas = [], []

    for ficha in nuevo:
        previa = next((v for v in pendientes if v.get("id") == ficha["id"]), None)
        if previa is None:
            # El id se arma con el nombre, así que si alguien renombró la sala
            # en el YAML el id ya no calza: se busca por cercanía antes de
            # declararla nueva y duplicarla en el mapa.
            previa = _cerca(ficha, pendientes)
        if previa is None:
            notas.append(f"+ nueva: {ficha['nombre']}")
            salida.append(ficha)
            continue

        pendientes.remove(previa)
        fusion = dict(ficha)
        fusion["id"] = previa.get("id", ficha["id"])
        for campo in DE_LA_CASA:
            if previa.get(campo) not in (None, "", []):
                fusion[campo] = previa[campo]
        if previa.get("verificado"):
            fusion["verificado"] = True
            for campo, valor in previa.items():
                if valor in (None, "", []):
                    continue
                if campo in ("lat", "lon") and fusion.get(campo) != valor:
                    notas.append(f"~ {previa.get('nombre')}: {campo} {fusion[campo]} → "
                                 f"{valor} (manda el YAML, está verificado)")
                fusion[campo] = valor
        salida.append(fusion)

    for sobrante in pendientes:
        notas.append(f"= se conserva, el catastro no la vio: {sobrante.get('nombre')}")
        salida.append(sobrante)

    salida.sort(key=lambda c: (c.get("circuito") != "arte", c.get("cadena", ""),
                               c.get("nombre", "")))
    return salida, notas


CABECERA = """# Catastro de salas de cine de la Región Metropolitana.
#
# Lo escribe y refresca scripts/catastro_cines.py, y se edita a mano sin miedo:
# los campos de la casa (nombre, alias, url, circuito, cartelera) y cualquier
# entrada con `verificado: true` no los pisa el script.
#
#   cadena      cinemark · cineplanet · cinepolis · independiente
#   circuito    comercial (la sala del mall) · arte (el cine de barrio)
#   cartelera   de dónde salen los horarios de esta sala:
#                 cinemark   el BFF público de Cinemark (semana entera,
#                            sinopsis y tráiler); JSON-LD queda de respaldo
#                 semanal    el cine publica la semana en su sitio (Normandie)
#                 agenda     ya llega por otra fuente del pipeline (CCLM, M100)
#                 navegador  hay que sacarla con la extracción asistida
#                            (datos/manual/_prompt_cine.md)
#                 vacío      no tiene cartelera propia que leer
#   alias       cómo la nombran OTRAS fuentes; es lo que permite pegar una
#               función con su sala aunque la ticketera la escriba distinto
#   verificado  alguien confirmó el nombre mirando el sitio del cine
#
# Las coordenadas son el motivo por el que este archivo existe: se guardan una
# vez y el mapa las usa para siempre, incluso las de las cadenas cuya cartelera
# no se puede leer.

"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seco", action="store_true", help="no escribir, solo mostrar")
    args = parser.parse_args()

    viejo = []
    if SALIDA.exists():
        viejo = (yaml.safe_load(SALIDA.read_text(encoding="utf-8")) or {}).get("cines", [])

    catastro, notas = fusionar(construir(), viejo)
    for nota in notas:
        print(" ", nota)

    sin_verificar = [c["nombre"] for c in catastro if not c.get("verificado")]
    print(f"\n{len(catastro)} salas · {len(sin_verificar)} sin nombre confirmado")
    for nombre in sin_verificar:
        print(f"    ? {nombre}")

    if args.seco:
        return 0

    cuerpo = yaml.safe_dump({"cines": catastro}, allow_unicode=True, sort_keys=False,
                            default_flow_style=False, width=100)
    SALIDA.write_text(CABECERA + cuerpo, encoding="utf-8")
    print(f"\nEscrito {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
