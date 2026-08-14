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

Tres archivos, del más general al más quirúrgico:

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
import unicodedata
from pathlib import Path

import yaml

log = logging.getLogger("loica.correcciones")

RUTA_CORRECCIONES = Path(__file__).resolve().parent.parent / "config" / "correcciones"

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


class Correcciones:
    """Carga los tres YAML una vez y responde consultas baratas."""

    def __init__(self, ruta: Path | str = RUTA_CORRECCIONES):
        ruta = Path(ruta)
        self.lugares = _cargar(ruta / "lugares.yaml", "lugares", CAMPOS_LUGAR)
        self.eventos = _cargar(ruta / "eventos.yaml", "eventos", CAMPOS_EVENTO)
        self.restoranes = _cargar(ruta / "restoranes.yaml", "restoranes",
                                  CAMPOS_RESTORAN)
        if self.lugares or self.eventos or self.restoranes:
            log.info("Correcciones cargadas: %d lugares, %d eventos, %d restoranes",
                     len(self.lugares), len(self.eventos), len(self.restoranes))

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
