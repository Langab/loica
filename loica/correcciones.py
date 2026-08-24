"""Repositorio de correcciones: la memoria de arreglos del pipeline.

El problema que resuelve: la extracción se equivoca siempre en los mismos
lugares. Nominatim no encuentra "Sala Master", el clasificador manda un ciclo
de cine a "charla", y un restaurante con descuento queda sin comuna. Antes
cada arreglo vivía hardcodeado en el código (RECINTOS en geo.py, FALSOS en
clasificar.py) o se perdía: se corregía el dato de hoy y la corrida de mañana
volvía a traer el error.

Acá el arreglo se escribe UNA vez en un YAML de `config/correcciones/` y se
aplica solo en todas las corridas futuras. La revisión diaria
(`revisar_extraccion.py`) propone qué corregir; una persona o una sesión de
Claude completa el dato; y desde ahí queda en la memoria.

Cuatro archivos, del más general al más quirúrgico:

  categorias.yaml  Palabras en contexto → categoría. Es la memoria del
                   clasificador: "Magallanes" junto a "vs" es un partido,
                   "maratón" junto a "película" es cine. Vale para los eventos
                   de hoy y para los que lleguen mañana con las mismas
                   palabras; el clasificador la consulta ANTES que sus propios
                   patrones (ver MemoriaCategorias, más abajo).
  lugares.yaml     Un lugar → dirección, comuna y coordenadas. Sirve para
                   TODOS los eventos que pasen por ese lugar, hoy y siempre.
                   Es la extensión editable de RECINTOS (geo.py) sin tocar código.
  restoranes.yaml  Un local con descuento → cocina, rubro, dirección, comuna
                   y coordenadas. Aplica a todos los bancos que lo publiquen.
  eventos.yaml     Un evento puntual (por su id) → categoría, comuna,
                   coordenadas o descarte. Para el caso que no se puede
                   generalizar.

Las claves de lugares y restoranes se normalizan igual que en geo.py
(minúsculas, sin tildes): "Sala Máster" y "sala master" son la misma clave.
Los lugares matchean por contención (como RECINTOS: "sala master" le pega a
"Sala Master — Radio Universidad de Chile"); los restoranes SOLO por
coincidencia exacta, porque "Sushi Home" no es "Sushi Home Ñuñoa" y un pin
equivocado es peor que ninguno.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger("loica.correcciones")

RUTA_CORRECCIONES = Path(__file__).resolve().parent.parent / "config" / "correcciones"

# Las categorías que existen en el sitio (cada una es un animal guía) más
# "descartar", que no es una categoría sino la decisión de que el evento no es
# un panorama. Una regla con otra cosa es un error de tipeo y se avisa fuerte.
CATEGORIAS = {"idiomas", "familia", "feria", "deporte", "fiesta", "cine",
              "teatro", "musica", "arte", "clases", "aire_libre", "charla",
              "otros"}
# Dónde se busca la regla. `titulo` es la etiqueta de la fuente más el título
# (corto y curado, la señal más limpia); `texto` agrega la descripción (trae
# ruido: una regla acá tiene que ser específica); `lugar` es el nombre del
# recinto más el de la fuente, y SOLO opina cuando el texto no dijo nada —es
# el prior por recinto, escrito como dato en vez de como código.
DONDES = {"titulo", "texto", "lugar"}
CAMPOS_REGLA = {"nombre", "palabras", "contexto", "sin", "donde", "categoria",
                "subcategoria", "nota"}

# Campos que una corrección de evento puede tocar. Cualquier otra clave en el
# YAML es un error de tipeo y se avisa fuerte en vez de ignorarla en silencio.
CAMPOS_EVENTO = {"categoria", "subcategoria", "escala", "publico", "lugar",
                 "direccion", "comuna", "lat", "lon", "descartar", "nota"}
# La escala también se corrige por LUGAR, y ahí es donde de verdad sirve: el
# tamaño es del recinto, no del evento, así que arreglar "Teatro X es under"
# una vez arregla todas sus funciones de aquí en adelante.
CAMPOS_LUGAR = {"direccion", "comuna", "lat", "lon", "escala", "nota"}
CAMPOS_RESTORAN = {"cocina", "categoria", "direccion", "comuna",
                   "lat", "lon", "sitio_web", "nota"}


def normalizar_clave(texto: str) -> str:
    """Misma normalización que geo.py: minúsculas, sin tildes, espacios simples."""
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    limpio = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return " ".join(limpio.lower().split())


def _coordenada(valor, minimo: float, maximo: float) -> float | None:
    """Convierte lat/lon a float validando el rango, o None si no sirve.

    Acá entra lo que alguien escribió a mano: comillas, coma decimal chilena
    ("-33,4327"), o el número de otra ciudad. Un string colado en lat viaja
    hasta eventos.json y bota el doble check, así que se valida en la puerta.
    """
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if minimo <= numero <= maximo else None


def _cargar(ruta: Path, raiz: str, campos_validos: set[str]) -> dict[str, dict]:
    """Lee un YAML de correcciones y valida sus claves.

    Un archivo que no existe es normal (la memoria parte vacía). Un archivo
    ilegible, mal armado o con campos desconocidos NO bota la corrida: se
    avisa y se ignora, porque el pipeline corre solo a las 11:00 y un typo en
    una corrección no puede dejar el sitio sin actualizar.
    """
    if not ruta.exists():
        return {}
    try:
        crudo = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, UnicodeDecodeError, OSError) as e:
        log.error("No pude leer %s (%s): se sigue sin esas correcciones", ruta.name, e)
        return {}

    # Si alguien pegó las entradas sin la clave raíz, esto llega como lista o
    # como texto suelto. Es el error de tipeo más probable de todos.
    if not isinstance(crudo, dict):
        log.error("%s: el archivo no es un mapa; falta la clave raíz '%s:'",
                  ruta.name, raiz)
        return {}

    entradas = crudo.get(raiz) or {}
    if not isinstance(entradas, dict):
        log.error("%s: se esperaba un mapa bajo '%s'", ruta.name, raiz)
        return {}

    limpias: dict[str, dict] = {}
    for clave, datos in entradas.items():
        if not isinstance(datos, dict):
            log.warning("%s: la entrada %r no es un mapa, se ignora", ruta.name, clave)
            continue
        desconocidos = set(datos) - campos_validos
        if desconocidos:
            log.warning("%s: %r trae campos desconocidos %s — se ignoran esos campos",
                        ruta.name, clave, sorted(desconocidos))
            datos = {k: v for k, v in datos.items() if k in campos_validos}

        # Las coordenadas se normalizan acá y no al aplicarlas: si una está
        # mal escrita o cae fuera de la RM, la entrada conserva el resto
        # (dirección, comuna, categoría) y solo pierde el pin.
        if "lat" in datos or "lon" in datos:
            lat = _coordenada(datos.get("lat"), -34.05, -33.00)
            lon = _coordenada(datos.get("lon"), -71.30, -70.30)
            if lat is None or lon is None:
                log.warning("%s: %r tiene coordenadas inválidas o fuera de la RM "
                            "(%r, %r) — se ignora el pin",
                            ruta.name, clave, datos.get("lat"), datos.get("lon"))
                datos = {k: v for k, v in datos.items() if k not in ("lat", "lon")}
            else:
                datos = {**datos, "lat": lat, "lon": lon}

        # PyYAML resuelve las claves que parecen número, y un hash_dedup de
        # puros dígitos (0-7 con cero inicial) lo lee como OCTAL: la clave
        # deja de calzar con el hash real y la corrección se pierde en
        # silencio, con el curador creyendo que corrigió. No se puede
        # revertir la conversión, así que se avisa fuerte.
        if not isinstance(clave, str):
            log.warning("%s: la clave %r se leyó como número, no como texto — "
                        "enciérrala en comillas ('%s:') o la corrección no aplica",
                        ruta.name, clave, clave)
        limpias[normalizar_clave(str(clave))] = datos
    return limpias


def _normalizar_texto(texto: str) -> str:
    """La normalización con que el clasificador compara: minúsculas, sin
    tildes, espacios colapsados. La puntuación se queda, y por eso el límite
    de palabra de abajo es "no letra ni dígito": "vs" calza en "vs." y en
    "(vs)", y "nino" NO calza dentro de "leonino"."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto)


def _compilar_frases(frases: list[str]) -> re.Pattern | None:
    """Una alternancia de frases con límite de palabra, ya normalizadas."""
    limpias = [re.escape(_normalizar_texto(f).strip()) for f in frases
               if isinstance(f, str) and f.strip()]
    if not limpias:
        return None
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(limpias) + r")(?![a-z0-9])")


@dataclass
class Regla:
    """Una entrada de categorias.yaml, ya compilada.

    Dispara cuando alguna de `palabras` aparece en el texto del ámbito
    (`donde`), NINGUNA de `sin` aparece, y —si hay `contexto`— alguna de esas
    también aparece. El contexto es lo que vuelve segura a una palabra que
    sola sería ambigua: "magallanes" es un club, una región y una calle;
    "magallanes" al lado de "vs" es un partido.
    """
    nombre: str
    categoria: str
    donde: str = "titulo"
    subcategoria: str = ""
    nota: str = ""
    palabras: list[str] = field(default_factory=list)
    contexto: list[str] = field(default_factory=list)
    sin: list[str] = field(default_factory=list)
    _palabras: re.Pattern | None = None
    _contexto: re.Pattern | None = None
    _sin: re.Pattern | None = None

    def __post_init__(self):
        self._palabras = _compilar_frases(self.palabras)
        self._contexto = _compilar_frases(self.contexto)
        self._sin = _compilar_frases(self.sin)

    def calza(self, texto_normalizado: str) -> str | None:
        """La palabra que disparó, o None. El texto ya viene normalizado."""
        if not self._palabras:
            return None
        m = self._palabras.search(texto_normalizado)
        if not m:
            return None
        if self._sin and self._sin.search(texto_normalizado):
            return None
        if self._contexto and not self._contexto.search(texto_normalizado):
            return None
        return m.group(0)


class MemoriaCategorias:
    """Las reglas de categorias.yaml, en el orden del archivo.

    Se consulta por ámbito: `buscar(texto, "titulo")` mira solo las reglas
    escritas para el título, etc. La primera que calza gana, así que dentro
    del archivo lo específico va antes que lo general. Una memoria vacía (el
    archivo no existe) es válida: el clasificador sigue con sus patrones.
    """

    def __init__(self, ruta: Path | str | None = None):
        if ruta is None:
            ruta = RUTA_CORRECCIONES / "categorias.yaml"
        self.ruta = Path(ruta)
        self.reglas: list[Regla] = []
        self.problemas: list[str] = []   # lo que no se pudo cargar, para avisar
        self._cargar()
        self._por_donde = {d: [r for r in self.reglas if r.donde == d]
                           for d in DONDES}

    def _cargar(self) -> None:
        if not self.ruta.exists():
            return
        try:
            crudo = yaml.safe_load(self.ruta.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, UnicodeDecodeError, OSError) as e:
            self.problemas.append(f"no se pudo leer: {e}")
            log.error("No pude leer %s (%s): el clasificador sigue sin memoria",
                      self.ruta.name, e)
            return
        entradas = crudo.get("reglas") if isinstance(crudo, dict) else None
        if not isinstance(entradas, list):
            self.problemas.append("falta la lista raíz 'reglas:'")
            log.error("%s: se esperaba una lista bajo 'reglas:'", self.ruta.name)
            return
        for i, datos in enumerate(entradas, 1):
            regla = self._regla(i, datos)
            if regla:
                self.reglas.append(regla)
        if self.reglas:
            log.info("Memoria de categorías: %d reglas", len(self.reglas))

    def _regla(self, i: int, datos) -> Regla | None:
        """Valida una entrada; la que está mal se avisa y se salta, no bota la
        corrida (esto corre solo a las 11:00)."""
        if not isinstance(datos, dict):
            self._avisar(f"regla #{i} no es un mapa")
            return None
        nombre = str(datos.get("nombre") or f"regla #{i}")
        desconocidos = set(datos) - CAMPOS_REGLA
        if desconocidos:
            self._avisar(f"{nombre}: campos desconocidos {sorted(desconocidos)} (se ignoran)")
        categoria = str(datos.get("categoria") or "").strip()
        if categoria not in CATEGORIAS and categoria != "descartar":
            self._avisar(f"{nombre}: categoría {categoria!r} no existe — se salta")
            return None
        donde = str(datos.get("donde") or "titulo").strip()
        if donde not in DONDES:
            self._avisar(f"{nombre}: donde={donde!r} no existe (titulo|texto|lugar) — se salta")
            return None
        palabras = self._lista(datos.get("palabras"))
        if not palabras:
            self._avisar(f"{nombre}: sin 'palabras' — se salta")
            return None
        # Una palabra muy corta sin contexto calza en todas partes: "dj" tiene
        # límite de palabra y pasa, pero "a" o "el" no dicen nada.
        cortas = [p for p in palabras if len(_normalizar_texto(p).strip()) < 3]
        if cortas and not datos.get("contexto"):
            self._avisar(f"{nombre}: palabras de menos de 3 letras sin contexto {cortas} — se salta")
            return None
        return Regla(nombre=nombre, categoria=categoria, donde=donde,
                     subcategoria=str(datos.get("subcategoria") or "").strip(),
                     nota=str(datos.get("nota") or ""), palabras=palabras,
                     contexto=self._lista(datos.get("contexto")),
                     sin=self._lista(datos.get("sin")))

    @staticmethod
    def _lista(valor) -> list[str]:
        if valor is None:
            return []
        if isinstance(valor, str):
            return [valor]
        if isinstance(valor, list):
            return [str(v) for v in valor if v is not None and str(v).strip()]
        return []

    def _avisar(self, mensaje: str) -> None:
        self.problemas.append(mensaje)
        log.warning("%s: %s", self.ruta.name, mensaje)

    # ---------- consultas ----------

    def buscar(self, texto_normalizado: str, donde: str,
               categoria: str | None = None) -> tuple[Regla, str] | None:
        """La primera regla del ámbito `donde` que calza, y la palabra que la
        disparó. Con `categoria`, solo las reglas de esa categoría que traen
        subcategoría (es la consulta del segundo nivel). Las reglas de
        descarte no se devuelven acá: las pregunta `descartar`."""
        if not texto_normalizado:
            return None
        for regla in self._por_donde.get(donde, ()):
            if regla.categoria == "descartar":
                continue
            if categoria is not None and (regla.categoria != categoria
                                          or not regla.subcategoria):
                continue
            palabra = regla.calza(texto_normalizado)
            if palabra:
                return regla, palabra
        return None

    def descartar(self, titulo_normalizado: str,
                  texto_normalizado: str = "") -> tuple[Regla, str] | None:
        """¿Alguna regla dice que esto NO es un panorama? (abonos, membresías,
        campañas de socios…). Las de ámbito `titulo` miran el título; las de
        `texto`, título y descripción."""
        for regla in self.reglas:
            if regla.categoria != "descartar":
                continue
            texto = titulo_normalizado if regla.donde == "titulo" else texto_normalizado
            palabra = regla.calza(texto) if texto else None
            if palabra:
                return regla, palabra
        return None

    def __len__(self) -> int:
        return len(self.reglas)

    def __bool__(self) -> bool:
        return True   # una memoria vacía sigue siendo una memoria


class Correcciones:
    """Carga los cuatro YAML una vez y responde consultas baratas."""

    def __init__(self, ruta: Path | str = RUTA_CORRECCIONES):
        ruta = Path(ruta)
        self.lugares = _cargar(ruta / "lugares.yaml", "lugares", CAMPOS_LUGAR)
        self.eventos = _cargar(ruta / "eventos.yaml", "eventos", CAMPOS_EVENTO)
        self.restoranes = _cargar(ruta / "restoranes.yaml", "restoranes",
                                  CAMPOS_RESTORAN)
        self.categorias = MemoriaCategorias(ruta / "categorias.yaml")
        if self.lugares or self.eventos or self.restoranes or len(self.categorias):
            log.info("Correcciones cargadas: %d lugares, %d eventos, %d restoranes, "
                     "%d reglas de categoría",
                     len(self.lugares), len(self.eventos), len(self.restoranes),
                     len(self.categorias))

    # ---------- consultas ----------

    def evento(self, hash_dedup: str) -> dict:
        """Corrección quirúrgica de un evento puntual, por su id. {} si no hay."""
        return self.eventos.get(normalizar_clave(hash_dedup), {})

    def lugar(self, lugar_nombre: str) -> dict:
        """Corrección de un lugar, por contención del nombre (como RECINTOS)."""
        clave = normalizar_clave(lugar_nombre)
        if not clave:
            return {}
        exacta = self.lugares.get(clave)
        if exacta:
            return exacta
        for nombre, datos in self.lugares.items():
            if nombre and (nombre in clave or clave.startswith(nombre)):
                return datos
        return {}

    def restoran(self, comercio: str) -> dict:
        """Corrección de un local con descuento. SOLO match exacto."""
        return self.restoranes.get(normalizar_clave(comercio), {})

    # ---------- aplicación ----------

    def aplicar_a_evento(self, ev: dict) -> list[str]:
        """Corrige un evento ya armado para exportar. Devuelve qué campos tocó.

        Orden a propósito: primero el lugar (general), encima el evento
        puntual (quirúrgico) — si los dos dicen comuna, gana el puntual.
        Cuando una corrección trae coordenadas se marca precision='correccion':
        en el mapa se dibuja como pin exacto (solo 'comuna' y 'sin_ubicar' se
        atenúan) y en la revisión se distingue de lo geocodificado.
        """
        tocados: list[str] = []

        arreglo_lugar = self.lugar(ev.get("lugar") or "")
        arreglo_evento = self.evento(ev.get("id") or "")

        for origen in (arreglo_lugar, arreglo_evento):
            if not origen:
                continue
            # OJO con el `and origen[campo]`: una corrección solo puede
            # cambiar un valor por OTRO, nunca vaciarlo. Para subcategoria y
            # escala eso significa que "" no se puede imponer a mano —si el
            # clasificador se pasó de listo, el arreglo va en clasificar.py,
            # que además es la regla de la casa cuando el error se repite.
            for campo in ("lugar", "direccion", "comuna", "categoria",
                          "subcategoria", "escala", "publico"):
                if campo in origen and origen[campo] and ev.get(campo) != origen[campo]:
                    ev[campo] = origen[campo]
                    tocados.append(campo)
            if origen.get("lat") is not None and origen.get("lon") is not None:
                if (ev.get("lat"), ev.get("lon")) != (origen["lat"], origen["lon"]):
                    ev["lat"], ev["lon"] = origen["lat"], origen["lon"]
                    ev["precision"] = "correccion"
                    tocados.append("coordenadas")

        if arreglo_evento.get("descartar"):
            ev["descartar"] = True
            tocados.append("descartar")
        return tocados

    def aplicar_a_descuento(self, d) -> list[str]:
        """Corrige un Descuento (objeto, no dict) antes de geocodificar.

        La corrección RELLENA lo que falta; no pisa la dirección que el banco
        sí publicó. La distinción importa porque estas fichas se guardan por
        nombre y hay locales con varias sucursales: Holy Moly tiene una en
        Hernando de Aguirre y otra en Merced, y al sobrescribir las dos con la
        misma ficha quedaban como un descuento duplicado en la misma esquina.
        Cuando el banco da la dirección, ella manda y se geocodifica sola.
        """
        arreglo = self.restoran(d.comercio)
        if not arreglo:
            return []
        tocados: list[str] = []

        # La cocina y el rubro sí se corrigen siempre: son una clasificación
        # nuestra, no un dato del banco. El sitio del local se rellena cuando
        # falta —Santander no publica ninguno— y no se pisa si el banco lo dio.
        for campo in ("cocina", "categoria"):
            valor = arreglo.get(campo)
            if valor and getattr(d, campo) != valor:
                setattr(d, campo, valor)
                tocados.append(campo)
        if arreglo.get("sitio_web") and not d.sitio_web:
            d.sitio_web = arreglo["sitio_web"]
            tocados.append("sitio_web")

        if d.direccion:
            return tocados

        for campo in ("direccion", "comuna"):
            valor = arreglo.get(campo)
            if valor and getattr(d, campo) != valor:
                setattr(d, campo, valor)
                tocados.append(campo)
        if arreglo.get("lat") is not None and arreglo.get("lon") is not None:
            if (d.lat, d.lon) != (arreglo["lat"], arreglo["lon"]):
                d.lat, d.lon = arreglo["lat"], arreglo["lon"]
                d.precision = "correccion"
                tocados.append("coordenadas")
        return tocados
