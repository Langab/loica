"""Las cadenas: una oferta, muchas sucursales.

El problema que resuelve este módulo se ve solo mirando la página. Banco de
Chile publica el descuento de Dunkin' **una vez por local**, así que la lista
abría con veintiún Dunkin' seguidos y con veintidós Starbucks detrás, y el
banco parecía tener el triple de convenios que los demás. No los tiene: tiene
los mismos convenios y el buen gusto de decir dónde queda cada local.

Y al revés: Santander publica "Melt Pizzas" y punto. No dice ninguna
dirección, así que el descuento no caía en el mapa aunque Melt tenga trece
locales en Santiago. Quien abre la página buscando dónde comer cerca no lo
veía nunca.

Las dos cosas son la misma confusión: **el descuento es del convenio, las
direcciones son de los locales**. Acá se separan.

    expandir()  toma la oferta que el banco publicó sin dirección y la abre en
                una fila por sucursal conocida.
    agrupar()   junta las filas del mismo convenio en una sola oferta con su
                lista de locales, que es lo que se publica.

De dónde salen las sucursales, en orden de confianza:

    1. Otro banco que sí las publica. Banco de Chile lista los 66 Dunkin' con
       calle y comuna; Falabella y Entel publican el mismo Dunkin' sin
       ninguna. Es un dato de banco, declarado, y viaja diciendo de cuál.
    2. OpenStreetMap, del índice local que ya usa el geocodificador
       (`datos/indice_osm.db`, tabla `locales`). Ahí están los McDonald's, los
       Doggis y los Melt de Santiago con sus coordenadas.

La segunda fuente pide cuidado y por eso tiene tres candados. El banco dijo
"hay descuento en Melt Pizzas" sin decir en cuáles, así que mostrar todos los
Melt es leer literalmente lo que publicó; pero mostrar todos los "Sakura"
cuando Sakura es el nombre de un restorán suelto y de otros cuatro homónimos
sería inventar un descuento en cuatro locales que no lo tienen. Los candados:

    · el nombre tiene que calzar EXACTO ya normalizado, nunca por pedazos;
    · OSM tiene que conocer al menos tres locales con ese nombre en la Región
      Metropolitana —tres es lo que separa una cadena de un homónimo—;
    · el nombre tiene que tener cuerpo (cinco caracteres): "Fork" y "TPM"
      calzan con cualquier cosa.

Y lo que igual queda inferido se dice: cada local viaja con `origen`, que es
"" cuando lo publicó el propio banco, el nombre del banco que lo prestó, o
"OpenStreetMap". La ficha lo muestra. La deuda se dice, no se esconde.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from ..geo import COMUNAS as CENTROS_COMUNA
from ..geo import RUTA_INDICE, normalizar_osm
from .modelo import Descuento
from .texto import COMUNAS, COMUNAS_RM, plano

log = logging.getLogger("loica.descuentos")

# Cuántos locales con el mismo nombre tiene que conocer OSM para que eso sea
# una cadena y no una casualidad. Con dos, "Vendetta" y "Jalisco" —que son
# restoranes sueltos con nombre repetido— entraban como si fueran franquicias.
MINIMO_CADENA_OSM = 3

# Nombres demasiado cortos calzan con demasiadas cosas.
LARGO_MINIMO_NOMBRE = 5

# Los `amenity` de OSM que sirven de comer. Sin este filtro, un nombre de
# cadena calza también con la tienda o el gimnasio que se llama igual.
TIPOS_GASTRONOMICOS = {
    "restaurant", "fast_food", "cafe", "bar", "pub", "ice_cream",
    "bakery", "biergarten", "food_court", "confectionery", "pastry",
}

# Dos nodos de OSM a menos de esta distancia son el mismo local mapeado dos
# veces (pasa con el nodo y el polígono del edificio). En grados: ~90 metros.
JUNTOS_GRADOS = 0.0008


def clave(nombre: str) -> str:
    """La huella de la cadena.

    Es `normalizar_osm` y no una normalización propia justamente para que la
    misma llave sirva para buscar en el índice de OSM: si el índice y la
    consulta normalizaran distinto, "Papa John's" no encontraría nunca los
    "papa john s" que OSM tiene guardados.
    """
    return normalizar_osm(nombre)


def _comuna_de(lat: float, lon: float, ciudad: str = "") -> str:
    """La comuna del punto, y de paso el filtro de "esto es Santiago".

    Devuelve "" cuando el punto no cae en ninguna comuna de la Región
    Metropolitana, y esa respuesta vacía es la que descarta la sucursal.

    Empezó siendo una caja de latitud y longitud alrededor de la RM y estaba
    mal: la región se estira hasta Melipilla por el poniente, así que la caja
    que la contenía entera contenía también Viña del Mar y Concón. Los catorce
    Melt Pizzas que salieron a la primera corrida estaban casi todos en la
    Quinta Región —Avenida Libertad, Concón Reñaca, Viana— y para alguien
    parado en Santiago eso es exactamente el dato inútil que el catastro
    promete no publicar.

    Por cercanía al centro de la comuna, con tope de 12 km. OSM deja `ciudad`
    en blanco en más de la mitad de sus locales, así que sin el respaldo por
    distancia la mitad de las sucursales quedaría fuera. Doce kilómetros es
    generoso para el Gran Santiago —donde los centros están a tres o cuatro—
    y sigue dejando Viña, que está a más de setenta del centro más cercano,
    del otro lado.
    """
    limpia = COMUNAS.get(plano(ciudad), (ciudad or "").strip())
    if limpia in COMUNAS_RM:
        return limpia
    # Una ciudad declarada que NO es de la RM es una respuesta, no un vacío:
    # "Viña del Mar" quiere decir que no es acá, y no hay que ir a preguntarle
    # a las coordenadas si por casualidad quedan cerca de Melipilla.
    if limpia and limpia not in COMUNAS_RM and plano(limpia) in COMUNAS:
        return ""

    mejor, mejor_dist = "", 12.0 ** 2
    for comuna, (clat, clon) in CENTROS_COMUNA.items():
        if comuna not in COMUNAS_RM:
            continue
        dist = ((lat - clat) * 111) ** 2 + ((lon - clon) * 92) ** 2
        if dist < mejor_dist:
            mejor, mejor_dist = comuna, dist
    return mejor


class Directorio:
    """Dónde queda cada sucursal de cada cadena.

    Se arma una vez por corrida con lo que ya trajeron los bancos, y consulta
    OSM solo cuando ningún banco publicó nada de esa cadena.
    """

    def __init__(self, descuentos: list[Descuento], ruta_osm: Path = RUTA_INDICE):
        # cadena → sucursales que un banco declaró, con el banco que lo hizo
        self.de_bancos: dict[str, list[dict]] = {}
        for d in descuentos:
            if not (d.direccion and d.comuna) or d.direccion_prestada_de:
                continue
            sedes = self.de_bancos.setdefault(clave(d.comercio), [])
            if any(plano(s["direccion"]) == plano(d.direccion) for s in sedes):
                continue
            sedes.append({"direccion": d.direccion, "comuna": d.comuna,
                          "region": d.region, "lat": d.lat, "lon": d.lon,
                          "telefono": d.telefono, "origen": d.banco})

        self.con = None
        if ruta_osm.exists():
            try:
                self.con = sqlite3.connect(f"file:{ruta_osm}?mode=ro", uri=True)
                self.con.execute("SELECT 1 FROM locales LIMIT 1").fetchone()
            except sqlite3.Error as e:
                log.warning("El índice OSM no sirve para las cadenas (%s); "
                            "sigo solo con lo que publican los bancos", e)
                self.con = None
        self._cache_osm: dict[str, list[dict]] = {}

    def sucursales(self, nombre: str, banco: str = "") -> list[dict]:
        """Las sucursales conocidas de esta cadena, la mejor fuente primero.

        Si el propio banco publica ese local con dirección en otra de sus
        entradas, mandan las suyas. Es su convenio y su dato: ir a buscarle la
        dirección a un tercero teniéndola en casa sería marcar como prestado
        algo que no lo es.
        """
        k = clave(nombre)
        de_bancos = self.de_bancos.get(k) or []
        propias = [s for s in de_bancos if s["origen"] == banco]
        if propias:
            # Del mismo banco: no es un préstamo, así que no se marca como tal.
            return [{**s, "origen": ""} for s in propias]
        if de_bancos:
            return de_bancos
        return self._osm(k)

    def _osm(self, k: str) -> list[dict]:
        if k in self._cache_osm:
            return self._cache_osm[k]
        self._cache_osm[k] = sedes = self._consultar_osm(k)
        return sedes

    def _consultar_osm(self, k: str) -> list[dict]:
        if not self.con or len(k) < LARGO_MINIMO_NOMBRE:
            return []
        try:
            filas = self.con.execute(
                "SELECT tipo, direccion, ciudad, lat, lon FROM locales WHERE nombre=?",
                (k,)).fetchall()
        except sqlite3.Error as e:
            log.warning("El índice OSM falló (%s); sigo sin él en esta corrida", e)
            self.con = None
            return []

        sedes: list[dict] = []
        for tipo, direccion, ciudad, lat, lon in filas:
            if tipo not in TIPOS_GASTRONOMICOS or lat is None or lon is None:
                continue
            comuna = _comuna_de(lat, lon, ciudad)
            if not comuna:            # no es de Santiago, o no se pudo decir
                continue
            # El mismo local mapeado dos veces en OSM son dos pines encima del
            # otro, que en el mapa se lee como dos locales distintos.
            if any(abs(lat - s["lat"]) < JUNTOS_GRADOS
                   and abs(lon - s["lon"]) < JUNTOS_GRADOS for s in sedes):
                continue
            sedes.append({"direccion": " ".join((direccion or "").split()),
                          "comuna": comuna,
                          "region": "Metropolitana", "lat": lat, "lon": lon,
                          "telefono": "", "origen": "OpenStreetMap"})

        if len(sedes) < MINIMO_CADENA_OSM:
            return []
        return sedes


def expandir(descuentos: list[Descuento]) -> tuple[list[Descuento], dict]:
    """La oferta publicada sin dirección se abre en una fila por sucursal.

    Solo se toca lo que no tiene NINGUNA dirección. Cuando el banco dijo dónde
    queda el local, manda él: es su convenio y su dato, y suponerle sucursales
    que no declaró sería agrandarle el descuento.
    """
    directorio = Directorio(descuentos)
    salida: list[Descuento] = []
    cuenta = {"ofertas": 0, "sedes": 0, "de_bancos": 0, "de_osm": 0, "propias": 0}

    for d in descuentos:
        if d.direccion:
            salida.append(d)
            continue
        sedes = directorio.sucursales(d.comercio, d.banco)
        if not sedes:
            salida.append(d)
            continue

        cuenta["ofertas"] += 1
        for sede in sedes:
            copia = Descuento(**{**d.a_campos(),
                                 "direccion": sede["direccion"],
                                 "comuna": sede["comuna"] or d.comuna,
                                 "region": sede["region"] or d.region,
                                 "telefono": d.telefono or sede["telefono"],
                                 "lat": sede["lat"], "lon": sede["lon"],
                                 "direccion_prestada_de": sede["origen"]})
            salida.append(copia)
            cuenta["sedes"] += 1
            if sede["origen"] == "OpenStreetMap":
                cuenta["de_osm"] += 1
            elif sede["origen"]:
                cuenta["de_bancos"] += 1
            else:
                cuenta["propias"] = cuenta.get("propias", 0) + 1

    return salida, cuenta


def agrupar(descuentos: list[Descuento]) -> list[dict]:
    """Junta las filas del mismo convenio en una oferta con sus locales.

    Es la forma que se publica, y cambia dos cosas a la vez:

    En la lista, Dunkin' es UNA fila que dice "66 locales" en vez de sesenta y
    seis Dunkin' seguidos. Eso no es solo prolijidad: con las filas sueltas,
    Banco de Chile ocupaba 334 de las 756 y parecía tener cuatro veces más
    convenios que Santander cuando tiene más o menos los mismos (179 contra
    72). La lista contaba direcciones y la leíamos como si contara descuentos.

    En el archivo, la letra chica del convenio —que son 268 caracteres de
    promedio— se escribe una vez y no sesenta y seis. Ahí está la diferencia
    entre que esto quepa o no: con una fila por sucursal, los mismos siete
    bancos se iban a 1,7 MB desde los 985 KB que pesaban con 756 filas.
    Agrupado son 1,1 MB con Banco Security ya adentro, y con 1.784 pines en
    el mapa en vez de 756.

    El mapa no pierde nada: sigue habiendo un punto por local, solo que ahora
    cuelgan de su oferta.
    """
    from . import _riqueza                      # el mismo criterio de "cuál trae más"

    ofertas: dict[str, dict] = {}
    for d in descuentos:
        oferta = ofertas.get(d.id)
        if oferta is None:
            ofertas[d.id] = oferta = {"mejor": d, "locales": []}
        elif _riqueza(d) > _riqueza(oferta["mejor"]):
            oferta["mejor"] = d

        # Un local sin dirección, sin comuna y sin coordenadas no es un lugar:
        # es la misma oferta otra vez. La oferta igual sale en la lista.
        if not (d.direccion or d.comuna or d.lat):
            continue
        # Sin calle, dos sucursales distintas de la misma comuna tienen la
        # misma llave y una se come a la otra. OSM publica el 45% de sus
        # locales sin `addr:street` —solo el punto— y con la llave por texto
        # los tres Burger King sin calle de La Florida quedaban en uno. Cuando
        # no hay calle manda la coordenada, redondeada a unos 10 metros.
        clave_local = ((plano(" ".join(d.direccion.split())), plano(d.comuna))
                       if d.direccion else
                       ("", plano(d.comuna), round(d.lat or 0, 4), round(d.lon or 0, 4)))
        if any(l["_clave"] == clave_local for l in oferta["locales"]):
            continue
        oferta["locales"].append({
            "_clave": clave_local,
            "direccion": d.direccion,
            "comuna": d.comuna,
            "lat": d.lat,
            "lon": d.lon,
            "precision": d.precision,
            "telefono": d.telefono,
            # "" = lo publicó este mismo banco. Si no, de dónde salió.
            "origen": d.direccion_prestada_de,
        })

    salida = []
    for oferta in ofertas.values():
        datos = oferta["mejor"].a_dict()
        # Los campos de sucursal se van a `locales`: dejarlos también arriba
        # sería tener la dirección en dos lugares, y el día que se corrija uno
        # el otro queda mintiendo.
        for campo in ("direccion", "comuna", "lat", "lon", "precision",
                      "telefono", "direccion_prestada_de"):
            datos.pop(campo, None)
        # Los que traen calle primero: "Avenida Larraín 5862, La Reina" es una
        # dirección y "La Reina" a secas es un punto en el mapa sin más señas.
        # Con el orden alfabético puro, la ficha de Burger King abría con dos
        # comunas sueltas y las direcciones de verdad quedaban abajo.
        locales = sorted(oferta["locales"],
                         key=lambda l: (not l["direccion"], l["comuna"], l["direccion"]))
        for local in locales:
            local.pop("_clave")
        datos["locales"] = locales
        datos["comunas"] = sorted({l["comuna"] for l in locales if l["comuna"]})
        salida.append(datos)

    # Por cuánto rebaja y no por banco: agrupada por banco, la lista abría con
    # las de un solo emisor una tras otra y parecía que era el único.
    return sorted(salida, key=lambda o: (-(o["porcentaje"] or 0),
                                         o["comercio"].lower(), o["banco"]))
