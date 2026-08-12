"""Convierte nombres de lugares en coordenadas para poder ponerlos en el mapa.

Estrategia en tres pasos, de más barato a más caro:
  1. Tabla de recintos conocidos de Santiago (instantáneo y exacto).
  2. Caché en disco de lo ya consultado.
  3. Nominatim de OpenStreetMap (gratis, 1 consulta por segundo como máximo).
"""

from __future__ import annotations

import json
import logging
import time
import unicodedata
from pathlib import Path

from .red import ClienteEducado

log = logging.getLogger("loica.geo")

RUTA_CACHE = Path(__file__).resolve().parent.parent / "datos" / "coordenadas.json"

# Centro aproximado de cada comuna, como último recurso: es mejor mostrar el
# evento en su comuna que no mostrarlo. En la app se marca como "ubicación
# aproximada" para no mentirle al usuario.
COMUNAS = {
    "Santiago": (-33.4425, -70.6505),
    "Providencia": (-33.4256, -70.6096),
    "Las Condes": (-33.4088, -70.5673),
    "Vitacura": (-33.3899, -70.5817),
    "Lo Barnechea": (-33.3512, -70.5180),
    "Ñuñoa": (-33.4569, -70.5975),
    "La Reina": (-33.4437, -70.5405),
    "Macul": (-33.4890, -70.5980),
    "Peñalolén": (-33.4849, -70.5423),
    "La Florida": (-33.5225, -70.5990),
    "Estación Central": (-33.4610, -70.6790),
    "Quinta Normal": (-33.4400, -70.7000),
    "Recoleta": (-33.4100, -70.6400),
    "Independencia": (-33.4150, -70.6650),
    "San Miguel": (-33.4960, -70.6520),
    "Maipú": (-33.5110, -70.7580),
    "La Granja": (-33.5400, -70.6250),
    "San Joaquín": (-33.4950, -70.6270),
    "Puente Alto": (-33.6110, -70.5760),
    # El diccionario tenía 19 de las 52 comunas de la Región Metropolitana, y
    # una comuna que falta acá no es un pin aproximado sino NINGÚN pin: el
    # evento sale solo en la lista. Eran 441 eventos y 53 descuentos, y 411 de
    # esos eventos son los talleres deportivos de Huechuraba.
    "Huechuraba": (-33.3706, -70.6408),
    "Conchalí": (-33.3830, -70.6750),
    "Renca": (-33.4040, -70.7290),
    "Quilicura": (-33.3670, -70.7290),
    "Cerro Navia": (-33.4230, -70.7400),
    "Lo Prado": (-33.4450, -70.7250),
    "Pudahuel": (-33.4406, -70.7530),
    "Cerrillos": (-33.4967, -70.7161),
    "Pedro Aguirre Cerda": (-33.4870, -70.6720),
    "Lo Espejo": (-33.5230, -70.6890),
    "San Ramón": (-33.5390, -70.6440),
    "La Cisterna": (-33.5378, -70.6636),
    "El Bosque": (-33.5620, -70.6750),
    "La Pintana": (-33.5830, -70.6330),
    "San Bernardo": (-33.5921, -70.6994),
    # Provincias vecinas: aparecen poco pero aparecen, y sin ellas el evento
    # de Colina o de Buin no cae en ninguna parte.
    "Colina": (-33.2019, -70.6747),
    "Lampa": (-33.2833, -70.8778),
    "Til Til": (-33.0870, -70.9280),
    "Buin": (-33.7333, -70.7417),
    "Paine": (-33.8083, -70.7411),
    "Pirque": (-33.6403, -70.5544),
    "San José de Maipo": (-33.6400, -70.3520),
    "Talagante": (-33.6640, -70.9280),
    "Peñaflor": (-33.6090, -70.8770),
    "Padre Hurtado": (-33.5730, -70.8130),
    "El Monte": (-33.6790, -71.0130),
    "Isla de Maipo": (-33.7500, -70.8990),
    "Curacaví": (-33.4033, -71.1447),
    "Melipilla": (-33.6880, -71.2150),
    "Calera de Tango": (-33.6280, -70.7810),
}

# Recintos culturales de Santiago con coordenadas verificadas. Cubrir los
# grandes a mano evita cientos de consultas y errores de geocodificación.
RECINTOS = {
    "gam": (-33.4372, -70.6403),
    "centro cultural gabriela mistral": (-33.4372, -70.6403),
    "matucana 100": (-33.4436, -70.6836),
    "m100": (-33.4436, -70.6836),
    "ceina": (-33.4487, -70.6497),
    "centro cultural la moneda": (-33.4429, -70.6539),
    "cclm": (-33.4429, -70.6539),
    "teatro municipal de santiago": (-33.4407, -70.6480),
    "teatro municipal": (-33.4407, -70.6480),
    "teatro uc": (-33.4372, -70.6222),
    "museo nacional de bellas artes": (-33.4353, -70.6437),
    "mavi": (-33.4383, -70.6403),
    "museo de artes visuales": (-33.4383, -70.6403),
    "museo de la memoria": (-33.4372, -70.6790),
    "planetario usach": (-33.4490, -70.6850),
    "parque metropolitano": (-33.4270, -70.6320),
    "parquemet": (-33.4270, -70.6320),
    "cerro san cristobal": (-33.4258, -70.6320),
    "balmaceda arte joven": (-33.4330, -70.6800),
    "nave": (-33.4390, -70.6690),
    "universidad diego portales": (-33.4460, -70.6520),
    "udp": (-33.4460, -70.6520),
    "biblioteca de santiago": (-33.4400, -70.6830),
    "biblioteca nacional": (-33.4419, -70.6448),
    "estadio nacional": (-33.4644, -70.6106),
    "movistar arena": (-33.4470, -70.6650),
    "teatro caupolican": (-33.4560, -70.6540),
    "club chocolate": (-33.4330, -70.6350),
    "blondie": (-33.4470, -70.6620),
    "corporacion cultural de vitacura": (-33.3899, -70.5817),
    "centro artesanal los dominicos": (-33.4030, -70.5350),
}


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    limpio = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return " ".join(limpio.lower().split())


class Geocodificador:
    def __init__(self, usar_nominatim: bool = True):
        self.usar_nominatim = usar_nominatim
        self.cache: dict[str, list | None] = {}
        if RUTA_CACHE.exists():
            try:
                self.cache = json.loads(RUTA_CACHE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.cache = {}
        self.cliente = ClienteEducado(crawl_delay_seg=1.1, usar_cache=False)
        self._ultima_consulta = 0.0

    def guardar(self) -> None:
        try:
            RUTA_CACHE.write_text(json.dumps(self.cache, ensure_ascii=False),
                                  encoding="utf-8")
        except OSError as e:
            log.warning("No pude guardar la caché de coordenadas: %s", e)

    def ubicar(self, lugar: str, direccion: str = "",
               comuna: str = "") -> tuple[float | None, float | None, str]:
        """Devuelve (lat, lon, precisión). Precisión: recinto | direccion | comuna."""
        clave_lugar = _plano(lugar)

        # 1. Recintos conocidos, por coincidencia parcial del nombre
        for nombre, (lat, lon) in RECINTOS.items():
            if nombre and (nombre in clave_lugar or clave_lugar.startswith(nombre)):
                return lat, lon, "recinto"

        # 2. Caché de consultas anteriores
        consulta = ", ".join(p for p in (direccion or lugar, comuna, "Santiago, Chile") if p)
        clave = _plano(consulta)
        if clave in self.cache:
            guardado = self.cache[clave]
            if guardado:
                return guardado[0], guardado[1], "direccion"
        elif self.usar_nominatim and (direccion or lugar):
            coords = self._preguntar_nominatim(consulta)
            self.cache[clave] = coords
            if coords:
                return coords[0], coords[1], "direccion"

        # 3. Centro de la comuna: aproximado, pero mejor que no aparecer
        if comuna in COMUNAS:
            lat, lon = COMUNAS[comuna]
            return lat, lon, "comuna"

        return None, None, ""

    def _preguntar_nominatim(self, consulta: str) -> list | None:
        """Nominatim pide máximo 1 consulta por segundo y un user-agent real."""
        espera = 1.1 - (time.time() - self._ultima_consulta)
        if espera > 0:
            time.sleep(espera)
        self._ultima_consulta = time.time()

        datos = self.cliente.json(
            "https://nominatim.openstreetmap.org/search",
            params={"q": consulta, "format": "json", "limit": 1,
                    "countrycodes": "cl", "accept-language": "es"},
        )
        if not isinstance(datos, list) or not datos:
            return None
        try:
            lat, lon = float(datos[0]["lat"]), float(datos[0]["lon"])
        except (KeyError, TypeError, ValueError):
            return None

        # Santiago cabe holgadamente en este recuadro; fuera de él es un error
        if not (-33.75 < lat < -33.20 and -70.90 < lon < -70.40):
            log.debug("Nominatim devolvió algo fuera de Santiago para %r", consulta)
            return None
        return [lat, lon]
