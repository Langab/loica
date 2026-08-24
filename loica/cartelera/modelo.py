"""Una función de cine y cómo se agrupan para la página.

Por qué esto no es un `Evento` y no entra a `datos/eventos.db`: una cartelera
son miles de funciones que caducan en tres días. Cuarenta y cuatro salas por
doce películas por cuarenta horarios es más filas por día que todo el resto
del catastro junto, y `datos/eventos.jsonl` —la copia de la base que viaja en
git y se comitea en cada corrida— crecería varios megas diarios para guardar
lo que mañana ya no existe.

El precedente está en la casa: los descuentos de banco también son un catastro
aparte con su propio runner y su propio JSON. La cartelera hace lo mismo.

La otra razón es la huella de deduplicación de `Evento`, que es (título, DÍA,
lugar): las cinco funciones de la misma película el mismo día en la misma sala
colapsarían en una. Acá la unidad es la función y el agrupamiento se hace al
final, para mostrar.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime


def clave_pelicula(titulo: str) -> str:
    """Identificador estable de una película a partir de su título.

    La misma película se escribe distinto en cada cadena —"SPIDER-MAN: UN
    NUEVO DÍA", "Spider-Man: un nuevo dia"— y sin normalizar aparecería dos
    veces en la cartelera, una por cine. Se bajan tildes, mayúsculas y
    puntuación, y se sacan las etiquetas de formato que algunas salas pegan al
    título ("(2D DOB)", "- SUBTITULADA").
    """
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", titulo or "")
                         if unicodedata.category(c) != "Mn").lower()
    sin_formato = re.sub(
        r"\b(2d|3d|4d|xd|dbox|d-box|imax|premier|vip|atmos|screenx|"
        r"dob|dobl|doblada|doblado|sub|subt|subtitulada|subtitulado|esp|cast)\b", " ",
        sin_tildes)
    limpio = re.sub(r"[^a-z0-9]+", "-", sin_formato).strip("-")
    return re.sub(r"-{2,}", "-", limpio)[:80]


# El título llega en mayúsculas de imprenta desde casi todas las cadenas. En
# una lista de doce películas eso GRITA, así que se pasa a mayúscula inicial
# —pero respetando las palabras que van en minúscula en castellano y las
# siglas de verdad, que sí van en mayúscula.
MINUSCULAS = {"de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
              "y", "e", "o", "u", "a", "al", "en", "con", "por", "para", "sin",
              "the", "of", "and", "a", "to", "in"}
SIGLAS = {"3d", "2d", "4d", "xd", "imax", "vip", "dc", "tv", "ii", "iii", "iv",
          "vi", "vii", "viii", "ix", "xi", "xii"}


def titulo_legible(titulo: str) -> str:
    crudo = " ".join((titulo or "").split())
    if not crudo or crudo != crudo.upper():
        return crudo  # ya viene con mayúsculas y minúsculas: no se toca

    palabras, abre = [], True
    for palabra in crudo.lower().split(" "):
        if palabra in SIGLAS:
            palabras.append(palabra.upper())
        elif not abre and palabra in MINUSCULAS:
            palabras.append(palabra)
        else:
            # "spider-man" → "Spider-Man"; "¿qué?" → "¿Qué?"
            palabras.append(re.sub(r"(^|[-/¿¡(])(\w)",
                                   lambda m: m.group(1) + m.group(2).upper(), palabra))
        # Después de dos puntos o de una raya empieza otra frase, y ahí el
        # artículo sí va en mayúscula: "Spider-Man: Un nuevo día", no
        # "Spider-Man: un Nuevo Día".
        abre = palabra.endswith((":", "–", "—", ".", "?", "!"))
    return " ".join(palabras)


# Los idiomas que declara una cartelera chilena, normalizados a dos valores.
# Es EL filtro de una página de cine: quien no quiere doblada no quiere
# doblada, y ninguna cadena lo escribe igual.
def normalizar_idioma(texto: str) -> str:
    plano = "".join(c for c in unicodedata.normalize("NFD", texto or "")
                    if unicodedata.category(c) != "Mn").lower()
    if re.search(r"\b(dob|dobl\w*|espanol|castellano|esp)\b", plano):
        return "doblada"
    if re.search(r"\b(sub\w*|vose|original)\b", plano):
        return "subtitulada"
    return ""


@dataclass
class Funcion:
    """Una película, en una sala, a una hora. La unidad de la cartelera."""

    pelicula: str
    cine_id: str
    inicio: datetime
    formato: str = ""        # 2D, 3D, XD, PREMIER…
    idioma: str = ""         # doblada | subtitulada | ""
    sala: str = ""
    url: str = ""            # dónde se compra: la página oficial del cine
    poster: str = ""
    duracion_min: int | None = None
    clasificacion: str = ""  # TE, TE+7, MA14…
    fuente: str = ""         # qué adaptador la trajo, para el informe

    @property
    def dia(self) -> str:
        return self.inicio.date().isoformat()

    @property
    def clave(self) -> str:
        return clave_pelicula(self.pelicula)


@dataclass
class Cartelera:
    """Lo que devuelve cada adaptador: sus funciones y qué le pasó."""

    funciones: list[Funcion] = field(default_factory=list)
    salas_leidas: int = 0
    salas_fallidas: list[str] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
