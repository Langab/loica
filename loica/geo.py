"""Convierte nombres de lugares en coordenadas para poder ponerlos en el mapa.

Estrategia, de más barato a más caro:
  1. Tabla de recintos conocidos de Santiago (instantáneo y exacto).
  2. Caché en disco de lo ya resuelto.
  3. Índice LOCAL de OpenStreetMap (datos/indice_osm.db): direcciones con
     número y locales con nombre de toda la RM, consultados en SQLite sin
     tocar la red. Se construye con scripts/construir_indice_osm.py.
  4. Centro de la comuna como último recurso (aproximado, y la página lo dice).

La geocodificación remota está APAGADA por defecto, y no por pereza: el
robots.txt de Nominatim prohíbe `/search` y el de Photon prohíbe todo, así que
el cliente educado (red.py) no les puede preguntar — la caché quedó con 453
consultas en null porque cada una murió en el robots. Este proyecto respeta
robots.txt sin excepción; por eso la precisión del mapa sale de dos fuentes
que no le preguntan nada a nadie en cada corrida:

  - la memoria de correcciones (config/correcciones/lugares.yaml), curada por
    la revisión diaria, que siempre manda; y
  - el índice local de OSM, una copia de datos distribuida para esto (ODbL,
    la misma licencia de los mosaicos del mapa), que resuelve las direcciones
    con número y los locales con nombre.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
import unicodedata
from pathlib import Path

from .red import ClienteEducado

log = logging.getLogger("loica.geo")

RUTA_CACHE = Path(__file__).resolve().parent.parent / "datos" / "coordenadas.json"
RUTA_INDICE = Path(__file__).resolve().parent.parent / "datos" / "indice_osm.db"

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
    # Arturo Prat 33: verificada contra el índice OSM (estaba 380 m corrida).
    "ceina": (-33.4453, -70.6502),
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
    # Alameda 2879, comuna de Santiago. Estaba anotado 1,1 km al oriente, en
    # pleno centro. Lo confirman tres fuentes que coinciden: el nodo de OSM,
    # la dirección que publica Passline y las coordenadas de Puntoticket.
    "blondie": (-33.4492, -70.6738),
    "corporacion cultural de vitacura": (-33.3899, -70.5817),
    "centro artesanal los dominicos": (-33.4030, -70.5350),
}


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    limpio = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return " ".join(limpio.lower().split())


def normalizar_osm(texto: str) -> str:
    """Normalización compartida entre el índice OSM y sus consultas.

    La usa también scripts/construir_indice_osm.py: si el índice y la consulta
    normalizan distinto, nada calza. Minúsculas, sin tildes, sin puntuación,
    abreviaturas comunes expandidas ("av." → "avenida").
    """
    plano = unicodedata.normalize("NFD", (texto or "").lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    plano = re.sub(r"[^a-z0-9ñ ]", " ", plano)
    palabras = {"av": "avenida", "avda": "avenida", "gral": "general",
                "pje": "pasaje", "sta": "santa", "sto": "santo",
                "pdte": "presidente",
                # Santiago está lleno de calles con fecha, y el catastro las
                # escribe con dígitos mientras las fuentes las escriben con
                # letras: "Diecinueve de Abril" es "19 de abril" en OSM.
                "uno": "1", "dos": "2", "tres": "3", "cuatro": "4",
                "cinco": "5", "seis": "6", "siete": "7", "ocho": "8",
                "nueve": "9", "diez": "10", "once": "11", "doce": "12",
                "trece": "13", "catorce": "14", "quince": "15",
                "dieciseis": "16", "diecisiete": "17", "dieciocho": "18",
                "diecinueve": "19", "veinte": "20", "veintiuno": "21"}
    partes = [palabras.get(p, p) for p in plano.split()]
    return " ".join(partes)


class IndiceLocal:
    """Consulta el índice SQLite construido desde el extracto de OSM.

    Dos preguntas: "¿dónde queda Guillermo Subiabre 1015?" (tabla direcciones)
    y "¿dónde queda el Bar de René?" (tabla locales). Todo local, sin red.
    Si el índice no existe (no se ha corrido scripts/construir_indice_osm.py),
    el geocodificador sigue funcionando sin este escalón.
    """

    def __init__(self, ruta: Path = RUTA_INDICE):
        self.con = None
        if not ruta.exists():
            return
        try:
            self.con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
            # connect() en SQLite es perezoso: no toca el archivo hasta la
            # primera consulta. Se hace una acá para que un índice a medio
            # construir (0 bytes, o un build interrumpido) se descarte ahora
            # y no reviente a mitad del export.
            self.con.execute("SELECT 1 FROM direcciones LIMIT 1").fetchone()
        except sqlite3.Error as e:
            log.warning("El índice OSM no está utilizable (%s); sigo sin él. "
                        "Reconstruilo con scripts/construir_indice_osm.py", e)
            self.con = None

    def _consultar(self, sql: str, args: tuple) -> list:
        """Consulta el índice tolerando que se haya vuelto ilegible.

        El archivo puede desaparecer o corromperse mientras corre el export
        (una reconstrucción en paralelo, por ejemplo). Una falla del índice
        degrada la precisión del pin; no puede botar la corrida diaria.
        """
        if not self.con:
            return []
        try:
            return self.con.execute(sql, args).fetchall()
        except sqlite3.Error as e:
            log.warning("El índice OSM falló (%s); sigo sin él en esta corrida", e)
            self.con = None
            return []

    @staticmethod
    def _distancia_km2(lat1, lon1, lat2, lon2) -> float:
        # Distancia aproximada al cuadrado, suficiente para comparar cercanías
        # dentro de la RM. 111 y 92 km por grado a esta latitud.
        return ((lat1 - lat2) * 111) ** 2 + ((lon1 - lon2) * 92) ** 2

    def _elegir(self, filas: list, comuna: str, radio: float = 8) -> list | None:
        """Entre varios candidatos: el de la comuna pedida; si la fila no trae
        ciudad, el más cercano al centro de esa comuna. Sin comuna, solo se
        acepta si los candidatos están juntos (si no, es un nombre ambiguo y
        un pin equivocado es peor que ninguno).

        `radio` es cuánto se tolera que el candidato se aleje del centro de la
        comuna. Los calces difusos —nombre recortado o número aproximado—
        piden un radio más corto: "19 de Abril 3526" de Ñuñoa calzaba con una
        calle homónima a 7,6 km, dentro del radio ancho pero en otra comuna.
        """
        if not filas:
            return None
        comuna_norm = normalizar_osm(comuna)
        if comuna_norm:
            de_comuna = [f for f in filas if f[0] == comuna_norm]
            if de_comuna:
                return [de_comuna[0][1], de_comuna[0][2]]
            centro = COMUNAS.get(comuna)
            if centro:
                mejor = min(filas, key=lambda f: self._distancia_km2(
                    f[1], f[2], centro[0], centro[1]))
                if self._distancia_km2(mejor[1], mejor[2], *centro) < radio ** 2:
                    return [mejor[1], mejor[2]]
                return None
        lats = [f[1] for f in filas]
        lons = [f[2] for f in filas]
        if (max(lats) - min(lats)) * 111 < 2 and (max(lons) - min(lons)) * 92 < 2:
            return [filas[0][1], filas[0][2]]
        return None

    @staticmethod
    def _candidatos(texto: str) -> list[tuple[str, int]]:
        """Saca los pares (calle, número) plausibles de un texto libre.

        Las fuentes municipales escriben de todo: "Juan Moya 1370", "JJ. VV.
        Simón Bolívar Av. Las Torres # 840" (basura por delante) y
        "Guanaco Norte # 1250 Capilla Santa Inés" (el número al medio y el
        recinto después). En vez de adivinar el formato se proponen todos los
        cortes y decide el índice: el que exista en el catastro y caiga en la
        comuna es el bueno. Primero el número que cierra el texto, que es el
        formato más común; después los del medio, de derecha a izquierda.
        """
        plano = normalizar_osm(texto.split(",")[0])
        plano = re.sub(r"\b(n|no|numero)\s+(\d)", r"\2", plano)
        cortes = []
        for m in re.finditer(r"\b(\d{1,5})\b", plano):
            # El cero inicial NO es decorativo: en Providencia, Ñuñoa y Las
            # Condes "Santa Isabel 0350" es un tramo distinto de la calle que
            # "Santa Isabel 350", y quedan a 900 m. El índice guarda el número
            # como entero, así que esa diferencia se perdió al construirlo:
            # mejor no resolver que resolver a la cuadra equivocada.
            if m.group(1).startswith("0") and len(m.group(1)) > 1:
                continue
            antes = plano[:m.start()].strip()
            if antes:
                cortes.append((antes, int(m.group(1)), m.end() == len(plano)))
        cortes.sort(key=lambda c: (not c[2], -len(c[0])))
        return [(calle, numero) for calle, numero, _ in cortes]

    def direccion(self, direccion: str, comuna: str = "",
                  estricta: bool = False) -> list | None:
        """Resuelve "Calle 1234" contra las direcciones con número de OSM.

        Con `estricta`, solo vale el calce exacto de calle y número: nada de
        números cercanos ni nombres recortados. Se usa cuando el resultado va
        a competir contra un dato ya existente (la tabla de recintos, o las
        coordenadas que publicó la fuente), donde una aproximación no alcanza
        para desbancar a nadie.
        """
        if not self.con or not direccion:
            return None
        # Sin comuna, un nombre de calle repetido en media región se resuelve
        # a ciegas: "Av. Bernardo O'Higgins 2900" apareció a 55 km de donde
        # correspondía. La comuna suele venir en la misma dirección después
        # de la coma, que antes se botaba: se rescata como pista.
        if not comuna:
            resto = normalizar_osm(" ".join(direccion.split(",")[1:]))
            for nombre in COMUNAS:
                if normalizar_osm(nombre) in resto:
                    comuna = nombre
                    break
        for calle, numero in self._candidatos(direccion)[:4]:
            encontrada = self._buscar(calle, numero, comuna, estricta)
            if encontrada:
                return encontrada
        return None

    def _buscar(self, calle: str, numero: int, comuna: str,
                estricta: bool = False) -> list | None:
        """Busca una calle en el índice aflojando de a poco la exigencia.

        El texto trae basura antes de la calle ("JJ. VV. Simón Bolívar
        Av. Las Torres 840"): se prueba desde el nombre completo hacia
        sufijos cada vez más cortos hasta que uno exista en el índice.
        """
        palabras = calle.split()
        for corte in range(len(palabras)):
            candidata = " ".join(palabras[corte:])
            exactas = self._consultar(
                "SELECT ciudad, lat, lon FROM direcciones WHERE calle=? AND numero=?",
                (candidata, numero))
            elegida = self._elegir(exactas, comuna)
            if elegida:
                return elegida
        if estricta:
            return None

        # La fuente suele acortar el nombre de la calle: escribe "Juan Moya
        # 1370" donde el catastro dice "Juan Moya Morales". Se prueba como
        # prefijo, exigiendo que la calle empiece igual para no confundir
        # "Los Alerces" con "Los Alerces Sur" de otra comuna — de eso se
        # encarga _elegir, que descarta candidatos dispersos.
        # Y también lo omite por delante: escribe "Guanaco Norte 1250" donde
        # el catastro dice "Avenida El Guanaco Norte". Los dos lados, porque
        # las fuentes municipales recortan por donde se les ocurre.
        for corte in range(len(palabras)):
            candidata = " ".join(palabras[corte:])
            if len(candidata) < 6:
                break
            # El tercer patrón es el nombre EN MEDIO: el catastro guarda
            # "avenida 10 de julio huamachuco" —con prefijo y con apellido— y
            # la fuente escribe "10 de Julio 760". Sin esto no calzaba por
            # ningún lado, aunque el número exacto estuviera a 1,3 km.
            for patron in (f"{candidata} *", f"* {candidata}", f"* {candidata} *"):
                aproximadas = self._consultar(
                    """SELECT ciudad, lat, lon FROM direcciones
                       WHERE calle GLOB ? AND numero = ? LIMIT 12""",
                    (patron, numero))
                elegida = self._elegir(aproximadas, comuna, radio=4.5)
                if elegida:
                    return elegida

        # Sin el número exacto: el más cercano en la misma calle, si está a
        # menos de ~2 cuadras de numeración. Mejor la cuadra que el centroide.
        # Va con los mismos tres patrones que arriba —nombre exacto, recortado
        # por delante y por detrás—: mirar solo el nombre exacto dejaba fuera
        # "Vicuña Mackenna 7110", que el catastro guarda como "avenida vicuna
        # mackenna" y sin ese número puntual.
        for corte in range(len(palabras)):
            candidata = " ".join(palabras[corte:])
            patrones = [("calle = ?", candidata)]
            if len(candidata) >= 6:
                patrones += [("calle GLOB ?", f"{candidata} *"),
                             ("calle GLOB ?", f"* {candidata}"),
                             ("calle GLOB ?", f"* {candidata} *")]
            for condicion, valor in patrones:
                cercanas = self._consultar(
                    f"""SELECT ciudad, lat, lon FROM direcciones
                        WHERE {condicion} AND ABS(numero - ?) < 250
                        ORDER BY ABS(numero - ?) LIMIT 8""",
                    (valor, numero, numero))
                elegida = self._elegir(cercanas, comuna, radio=4.5)
                if elegida:
                    return elegida
        return None

    def local(self, nombre: str, comuna: str = "") -> list | None:
        """Resuelve un local por su nombre exacto (bares, salas, teatros)."""
        if not self.con:
            return None
        clave = normalizar_osm(nombre)
        # Nombres cortos o de una palabra chocan con homónimos por toda la
        # ciudad ("kafe", "lounge"): se exige algo más de sustancia.
        if len(clave) < 6 or len(clave.split()) < 2:
            return None
        filas = self._consultar(
            "SELECT '' AS ciudad, lat, lon FROM locales WHERE nombre=? LIMIT 12",
            (clave,))
        return self._elegir(filas, comuna)


class Geocodificador:
    def __init__(self, usar_nominatim: bool = False):
        self.usar_nominatim = usar_nominatim
        self.cache: dict[str, list | None] = {}
        if RUTA_CACHE.exists():
            try:
                self.cache = json.loads(RUTA_CACHE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.cache = {}
        # Los null de la caché son consultas que murieron en el robots.txt de
        # Nominatim, no lugares inexistentes. Se purgan al cargar: si algún día
        # la geocodificación remota vuelve (con permiso), que reintente; y
        # mientras tanto no ensucian el archivo.
        nulos = [k for k, v in self.cache.items() if v is None]
        for k in nulos:
            del self.cache[k]
        if nulos:
            log.info("Caché de coordenadas: purgadas %d entradas null heredadas", len(nulos))
        self.cliente = ClienteEducado(crawl_delay_seg=1.1, usar_cache=False)
        self._ultima_consulta = 0.0
        self.indice = IndiceLocal()

    def guardar(self) -> None:
        try:
            RUTA_CACHE.write_text(json.dumps(self.cache, ensure_ascii=False),
                                  encoding="utf-8")
        except OSError as e:
            log.warning("No pude guardar la caché de coordenadas: %s", e)

    def ubicar(self, lugar: str, direccion: str = "",
               comuna: str = "") -> tuple[float | None, float | None, str]:
        """Devuelve (lat, lon, precisión). Precisión: recinto | calle | comuna.

        OJO con el vocabulario: acá se dice "calle" y no "direccion" porque es
        lo que esperan run_descuentos.py, el modelo de descuentos y la página
        — tres lugares contaban pines "calle" que este módulo nunca emitía.
        """
        clave_lugar = _plano(lugar)

        # 0. La dirección que publica la fuente, si calza EXACTO calle+número
        #    en el catastro. Va antes que RECINTOS porque esa tabla se escribe
        #    a mano y envejece: Blondie estaba anotado a 1,1 km de su local de
        #    Alameda 2879, y le ganaba a la dirección correcta que venía en el
        #    evento. Un calce exacto con el catastro es un hecho verificable;
        #    la tabla es una foto de cuando alguien la escribió.
        exacta = self.indice.direccion(direccion, comuna, estricta=True)
        if exacta:
            return exacta[0], exacta[1], "calle"

        # 1. Recintos conocidos, por coincidencia parcial del nombre.
        #    El match es por contención, así que un nombre genérico se lleva
        #    puesto a su homónimo de otra comuna: "Teatro Municipal de La
        #    Florida" calzaba con "teatro municipal" y quedaba a 10 km, en el
        #    Teatro Municipal de Santiago. Si la comuna declarada contradice
        #    al recinto, el recinto no manda.
        centro = COMUNAS.get(comuna)
        for nombre, (lat, lon) in RECINTOS.items():
            if not nombre or not (nombre in clave_lugar or clave_lugar.startswith(nombre)):
                continue
            if centro and ((lat - centro[0]) * 111) ** 2 + ((lon - centro[1]) * 92) ** 2 > 8 ** 2:
                log.debug("Recinto %r descartado: contradice la comuna %s", nombre, comuna)
                continue
            return lat, lon, "recinto"

        # 2. Caché de consultas anteriores
        consulta = ", ".join(p for p in (direccion or lugar, comuna, "Santiago, Chile") if p)
        clave = _plano(consulta)
        if clave in self.cache:
            guardado = self.cache[clave]
            if guardado:
                return guardado[0], guardado[1], "calle"
        elif self.usar_nominatim and (direccion or lugar):
            coords = self._preguntar_nominatim(consulta)
            self.cache[clave] = coords
            if coords:
                return coords[0], coords[1], "calle"

        # 3. Índice local de OSM: primero la dirección con número (lo más
        #    confiable), después el nombre del local. No se cachea: es una
        #    consulta SQLite local y así los rebuilds del índice rigen al tiro.
        coords = self.indice.direccion(direccion, comuna)
        if coords:
            return coords[0], coords[1], "calle"
        # A veces la dirección viene pegada en el nombre del lugar
        # ("JJ. VV. Simón Bolívar Av. Las Torres # 840").
        coords = self.indice.direccion(lugar, comuna)
        if coords:
            return coords[0], coords[1], "calle"
        coords = self.indice.local(lugar, comuna)
        if coords:
            return coords[0], coords[1], "recinto"

        # 4. Centro de la comuna: aproximado, pero mejor que no aparecer
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

        # La Región Metropolitana cabe en este recuadro; fuera de él es un
        # error. El recuadro viejo (-33.75..-33.20 / -70.90..-70.40) era solo
        # el Gran Santiago y rechazaba comunas reales del catálogo: Melipilla,
        # Til Til, Curacaví y San José de Maipo quedaban fuera.
        if not (-34.05 < lat < -33.00 and -71.30 < lon < -70.30):
            log.debug("El geocodificador devolvió algo fuera de la RM para %r", consulta)
            return None
        return [lat, lon]
