"""El catastro de salas de cine: quién lo lee y cómo se le pega una función.

`config/cines.yaml` guarda las 44 salas de la Región Metropolitana con su
coordenada. Existe porque una sala no es un evento: es una dirección que va a
seguir ahí el año que viene, y el mapa de la página de cine se dibuja con
esto aunque ese día no se haya podido leer ninguna cartelera.

Lo que este módulo aporta al pipeline es el CALCE: una función llega diciendo
que es en "CINEMARK PORTAL ÑUÑOA", en "Cineplanet Costanera Center" o
simplemente en "Cinepolis", y hay que decidir a qué pin del mapa corresponde.
Se resuelve por NOMBRE, y la coordenada confirma:

  1. **Por nombre exacto o alias**, sin tildes ni mayúsculas. Los alias son
     justamente el campo donde se anota "así la escribe Passline".
  2. **Por contención**: el nombre de la sala metido en un texto más largo
     ("Cine Arte Normandie - Sala 1").
  3. Si el nombre calza con VARIAS —"Cinépolis" a secas es alias de las veinte
     salas de la cadena— desempata la comuna, y si no alcanza, la coordenada
     elige entre esas veinte. Sin esa condición, la primera se llevaría todas
     las funciones de la cadena, que es el error que el mapa muestra como
     veinte funciones apiladas en un pin que no es.
  4. Recién si nadie calzó por nombre entra la coordenada sola, y con dos
     radios distintos según haya nombre o no. El porqué está escrito arriba de
     `RADIO_M`, y no es teórico: la coordenada primero le regalaba al Cinépolis
     del centro una función de la Biblioteca Nacional que estaba a 284 metros.
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


# Hasta dónde alcanza la cercanía cuando hay que decidir con ella.
#
#   RADIO    la sala está a menos de esto y NADIE dijo dónde era: se acepta.
#   PEGADO   el lugar tiene nombre y ese nombre no calza con ninguna sala.
#            Ahí la cercanía solo manda si es la misma puerta.
#
# La diferencia entre los dos números la decidió un caso real (25-08-2026): el
# documental "El fotógrafo de La 40" ocurre en la BIBLIOTECA NACIONAL, que en
# el centro de Santiago queda a 284 metros del Cinépolis Vivo Imperio. Con un
# radio único de 300 m, esa función aparecía publicada en la cartelera del
# Cinépolis — una sala que no publica horarios y que por culpa de esa única
# función mentía dos veces: decía tener cartelera y decía "sin funciones para
# este día" en vez de "esta cadena no publica sus horarios".
#
# Y la distancia sola NO alcanza para separar los casos: el Cine Arte
# Independencia dentro del Cineplanet Mall Barrio Independencia está a 277 m
# de su pin y es verdad. 277 buena contra 284 mala. Lo único que las separa es
# el NOMBRE, y por eso el nombre manda.
RADIO_M = 300
PEGADO_M = 60


def buscar(nombre: str = "", comuna: str = "",
           lat: float | None = None, lon: float | None = None) -> dict | None:
    """La sala del catastro a la que corresponde este lugar, o None.

    Manda el NOMBRE y la cercanía confirma, nunca al revés. Antes era al
    revés y el resultado era predecible en una ciudad densa: en cuatro
    cuadras del centro caben la Biblioteca Nacional, dos teatros y un
    multisala, y el primero que pasaba a menos de 300 metros se llevaba la
    función del vecino.
    """
    salas = catalogo()
    if not salas:
        return None

    clave = _plano(nombre)
    clave_comuna = _plano(comuna)

    def _cercana(entre: tuple | list | None = None, radio: float = RADIO_M) -> dict | None:
        if lat is None or lon is None:
            return None
        cercanas = sorted(
            ((_metros(lat, lon, s["lat"], s["lon"]), s) for s in (entre or salas)
             if s.get("lat") is not None), key=lambda p: p[0])
        return cercanas[0][1] if cercanas and cercanas[0][0] < radio else None

    def _unica(candidatas: list[dict]) -> dict | None:
        """Una candidata es una respuesta; varias es una pregunta.

        "Cinépolis" a secas calza con las veinte salas de la cadena, porque el
        nombre de la cadena es alias de todas. Devolver la primera apilaría
        las funciones de las veinte en un pin que no es. Con más de una
        candidata manda la comuna; si tampoco alcanza, la cercanía elige entre
        ESAS —que ya se sabe que son de la cadena nombrada— y si no hay
        coordenadas se devuelve None: una función sin sala se descarta con su
        motivo, que es honesto, mientras que una función en la sala equivocada
        es una mentira con pin.
        """
        if len(candidatas) == 1:
            return candidatas[0]
        if len(candidatas) > 1:
            if clave_comuna:
                por_comuna = [s for s in candidatas if s["_comuna"] == clave_comuna]
                if len(por_comuna) == 1:
                    return por_comuna[0]
            return _cercana(candidatas)
        return None

    if clave:
        # Primero el nombre completo; después el nombre de la sala metido
        # dentro de un texto más largo ("Cine Arte Normandie - Sala 1",
        # "Función en El Biógrafo"). Se exige que la clave sea larga: "cine uc"
        # dentro de cualquier frase sería ruido.
        for candidatas in ([s for s in salas if clave in s["_claves"]],
                           [s for s in salas
                            if any(k and len(k) > 8 and k in clave for k in s["_claves"])]):
            elegida = _unica(candidatas)
            if elegida:
                return elegida

    # Nadie calzó por nombre. Si el lugar no tiene nombre, la cercanía es todo
    # lo que hay y se le cree hasta el radio completo. Si SÍ tiene nombre y ese
    # nombre no es ninguna de las salas, el lugar se llama de otra manera y
    # solo se acepta pegado a la puerta: a esa distancia es el mismo edificio
    # escrito distinto ("Sala CEINA" por Centro Arte Alameda), y más allá es
    # el vecino.
    return _cercana(radio=RADIO_M if not clave else PEGADO_M)


def es_sala_de_cine(nombre: str = "", comuna: str = "",
                    lat: float | None = None, lon: float | None = None) -> bool:
    return buscar(nombre, comuna, lat, lon) is not None
