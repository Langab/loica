"""El catastro de salas de cine: quién lo lee y cómo se le pega una función.

`config/cines.yaml` guarda las 44 salas de la Región Metropolitana con su
coordenada. Existe porque una sala no es un evento: es una dirección que va a
seguir ahí el año que viene, y el mapa de la página de cine se dibuja con
esto aunque ese día no se haya podido leer ninguna cartelera.

Lo que este módulo aporta al pipeline es el CALCE: una función llega diciendo
que es en "CINEMARK PORTAL ÑUÑOA", en "Cineplanet Costanera Center" o
simplemente en "Cinepolis", y hay que decidir a qué pin del mapa corresponde.
Se resuelve en tres pasadas, de la más segura a la más floja:

  1. **Por coordenada** (a menos de 300 m). Es la única que no depende de cómo
     alguien escribió el nombre, así que va primero.
  2. **Por nombre exacto o alias**, sin tildes ni mayúsculas. Los alias son
     justamente el campo donde se anota "así la escribe Passline".
  3. **Por contención con comuna**: "Cinépolis" a secas solo calza si además
     coincide la comuna. Sin esa condición, la primera de las veinte salas de
     Cinépolis se llevaría todas las funciones de la cadena — que es
     exactamente el error que el mapa muestra como veinte funciones apiladas
     en un pin que no es.
"""

from __future__ import annotations

import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

RUTA = Path(__file__).resolve().parent.parent / "config" / "cines.yaml"


def _plano(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", str(texto or ""))
                         if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", sin_tildes.lower()).split())


def _metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return math.hypot((lat1 - lat2) * 111_320, (lon1 - lon2) * 92_600)


@lru_cache(maxsize=1)
def catalogo() -> tuple[dict, ...]:
    """Las salas del catastro. Inmutable y cacheada: la lee todo el pipeline."""
    if not RUTA.exists():
        return ()
    datos = yaml.safe_load(RUTA.read_text(encoding="utf-8")) or {}
    salas = []
    for sala in datos.get("cines") or []:
        if not isinstance(sala, dict) or not sala.get("nombre"):
            continue
        ficha = dict(sala)
        nombres = [ficha["nombre"], *(ficha.get("alias") or [])]
        ficha["_claves"] = tuple(sorted({_plano(n) for n in nombres if n}))
        ficha["_comuna"] = _plano(ficha.get("comuna", ""))
        salas.append(ficha)
    return tuple(salas)


def por_cartelera(modo: str) -> list[dict]:
    """Las salas cuya cartelera se lee de una manera determinada."""
    return [c for c in catalogo() if (c.get("cartelera") or "") == modo]


def buscar(nombre: str = "", comuna: str = "",
           lat: float | None = None, lon: float | None = None) -> dict | None:
    """La sala del catastro a la que corresponde este lugar, o None."""
    salas = catalogo()
    if not salas:
        return None

    if lat is not None and lon is not None:
        cercanas = sorted(
            ((_metros(lat, lon, s["lat"], s["lon"]), s) for s in salas
             if s.get("lat") is not None), key=lambda p: p[0])
        if cercanas and cercanas[0][0] < 300:
            return cercanas[0][1]

    clave = _plano(nombre)
    if not clave:
        return None
    clave_comuna = _plano(comuna)

    def _unica(candidatas: list[dict]) -> dict | None:
        """Una candidata es una respuesta; varias es una pregunta.

        "Cinépolis" a secas calza con las veinte salas de la cadena, porque el
        nombre de la cadena es alias de todas. Devolver la primera apilaría
        las funciones de las veinte en un pin que no es. Con más de una
        candidata manda la comuna, y si tampoco alcanza se devuelve None: una
        función sin sala se descarta con su motivo, que es honesto, mientras
        que una función en la sala equivocada es una mentira con pin.
        """
        if len(candidatas) == 1:
            return candidatas[0]
        if len(candidatas) > 1 and clave_comuna:
            por_comuna = [s for s in candidatas if s["_comuna"] == clave_comuna]
            if len(por_comuna) == 1:
                return por_comuna[0]
        return None

    exactas = _unica([s for s in salas if clave in s["_claves"]])
    if exactas:
        return exactas

    # El nombre de la sala metido dentro de un texto más largo
    # ("Cine Arte Normandie - Sala 1", "Función en El Biógrafo"). Se exige que
    # la clave sea larga: "cine uc" dentro de cualquier frase sería ruido.
    return _unica([s for s in salas
                   if any(k and len(k) > 8 and k in clave for k in s["_claves"])])


def es_sala_de_cine(nombre: str = "", comuna: str = "",
                    lat: float | None = None, lon: float | None = None) -> bool:
    return buscar(nombre, comuna, lat, lon) is not None
