"""Ingesta asistida: eventos que una persona encontró y el pipeline estructura.

No todo se puede rastrear. Hay tres casos permanentes:

  1. Sitios que bloquean el rastreo automático (Passline responde 403 a
     cualquier cliente que no sea un navegador de verdad).
  2. Instagram, donde vive buena parte del circuito de barrio y de las ferias,
     y cuya API no permite leer cuentas ajenas.
  3. El dato que llega por WhatsApp, por un afiche en la calle o porque el
     organizador lo mandó.

En los tres el descubrimiento lo hace una persona navegando normal. Lo que
aporta el pipeline es lo de siempre: normalizar, deduplicar contra lo que ya
existe, geocodificar y dejarlo en revisión con su link de origen.

Se escriben en `datos/manual/*.yaml` y entran como cualquier otra fuente, con
las mismas reglas: sin `fuente_url` no se guarda, porque sin atribución el
proyecto deja de ser un índice y pasa a ser una copia.

    eventos:
      - titulo: Colo-Colo vs Everton
        inicio: 2026-08-30 15:00
        lugar_nombre: Estadio Monumental
        comuna: Macul
        precio_texto: desde $12.000
        fuente_url: https://www.passline.com/eventos/...
        fuente_nombre: Passline
"""

from __future__ import annotations

import csv
import html
import logging
from datetime import date, datetime
from pathlib import Path

import yaml

from ..modelo import Evento
from ..normalizar import detectar_comuna, parsear_precio, resumir
from ..red import ClienteEducado

log = logging.getLogger("loica.manual")

DIR_MANUAL = Path(__file__).resolve().parent.parent.parent / "datos" / "manual"

# Campos que se aceptan tal cual desde el YAML. Cualquier otro se ignora en
# silencio: el archivo lo escribe una persona apurada, no un programa.
CAMPOS_TEXTO = ("titulo", "categoria", "descripcion_corta", "lugar_nombre",
                "lugar_direccion", "comuna", "precio_texto", "fuente_nombre",
                "fuente_url", "link_entradas", "imagen_url", "id_externo")


def _fecha(valor) -> datetime | None:
    """Acepta datetime, date o texto ISO. YAML ya convierte los dos primeros."""
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    if isinstance(valor, str) and valor.strip():
        from ..normalizar import parsear_fecha
        return parsear_fecha(valor)
    return None


# El rectángulo que envuelve a la Región Metropolitana. Es un guardia GRUESO
# y hay que saber qué no hace: como es un rectángulo, no distingue regiones
# vecinas —Valparaíso cae dentro de él— y no puede. De eso se encargan la
# comuna y `requiere_comuna`, que sí saben de límites administrativos.
#
# Lo que sí atrapa es el error bruto: la latitud sin signo (Santiago en el
# hemisferio norte), el par invertido, la coordenada de otro país pegada por
# error. Ese es el error que importa, porque un pin en el lugar equivocado
# engaña más que la ausencia de pin: nadie duda de un mapa.
CAJA_RM = (-34.35, -32.90, -71.75, -69.75)   # lat_min, lat_max, lon_min, lon_max


def _coordenadas(crudo: dict, origen: str, titulo: str) -> tuple[float | None, float | None]:
    """Lee lat/lon si vienen y caen dentro de la Región Metropolitana."""
    bruto_lat, bruto_lon = crudo.get("lat"), crudo.get("lon")
    if bruto_lat in (None, "") or bruto_lon in (None, ""):
        return None, None
    try:
        # Coma decimal: quien copia de una hoja de cálculo en español la trae.
        lat = float(str(bruto_lat).strip().replace(",", "."))
        lon = float(str(bruto_lon).strip().replace(",", "."))
    except (TypeError, ValueError):
        log.warning("%s: '%s' trae coordenadas ilegibles (%r, %r) — se ignoran",
                    origen, titulo[:40], bruto_lat, bruto_lon)
        return None, None
    lat_min, lat_max, lon_min, lon_max = CAJA_RM
    if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
        log.warning("%s: '%s' tiene coordenadas lejos de Santiago (%s, %s) — se ignoran",
                    origen, titulo[:40], lat, lon)
        return None, None
    return lat, lon


def _desde_dict(crudo: dict, fuente: dict, origen: str) -> Evento | None:
    if not isinstance(crudo, dict):
        return None

    datos = {campo: str(crudo.get(campo, "") or "").strip() for campo in CAMPOS_TEXTO}
    if not datos["titulo"]:
        log.warning("%s: una entrada sin título — se omite", origen)
        return None
    if not datos["fuente_url"]:
        log.warning("%s: '%s' no trae fuente_url — se omite (rompe la atribución)",
                    origen, datos["titulo"][:50])
        return None

    # El precio puede venir como número, como "gratis" o como texto libre.
    precio = crudo.get("precio_clp")
    gratis = crudo.get("es_gratis")
    if precio is None and gratis is None and datos["precio_texto"]:
        precio, gratis, _ = parsear_precio(datos["precio_texto"])
    try:
        precio = int(precio) if precio is not None else None
    except (TypeError, ValueError):
        precio = None

    lat, lon = _coordenadas(crudo, origen, datos["titulo"])

    return Evento(
        titulo=datos["titulo"][:200],
        categoria=datos["categoria"],
        descripcion_corta=resumir(datos["descripcion_corta"]),
        inicio=_fecha(crudo.get("inicio")),
        fin=_fecha(crudo.get("fin")),
        lugar_nombre=datos["lugar_nombre"],
        lugar_direccion=datos["lugar_direccion"],
        comuna=detectar_comuna(datos["comuna"], datos["lugar_direccion"],
                               datos["lugar_nombre"], fuente.get("comuna", "")),
        lat=lat,
        lon=lon,
        precio_clp=precio,
        es_gratis=bool(gratis) if gratis is not None else None,
        precio_texto=datos["precio_texto"],
        fuente_tipo="manual",
        # Se conserva de dónde salió (Passline, Instagram, un afiche): el
        # curador tiene que poder juzgar cuán confiable es el dato.
        fuente_nombre=datos["fuente_nombre"] or fuente.get("nombre", "Ingesta manual"),
        fuente_url=datos["fuente_url"],
        link_entradas=datos["link_entradas"],
        imagen_url=datos["imagen_url"],
        id_externo=datos["id_externo"],
    )


# Mapeo por defecto de un CSV exportado desde Passline. Se puede cambiar por
# fuente con `csv_columnas`, para cuando la exportación venga de otro lado.
COLUMNAS_CSV = {
    "titulo": "nombre",
    "categoria": "categoria",
    "inicio": "fecha_inicio",
    "hora_inicio": "hora_inicio",
    "fin": "fecha_termino",
    "lugar_nombre": "lugar",
    # La dirección con número es lo que convierte un pin al centro de la
    # comuna en un pin en la puerta del lugar. El índice local de OSM la
    # resuelve sola; sin ella hay que adivinar por el nombre del recinto.
    "lugar_direccion": "direccion",
    # Y si quien extrajo ya tenía las coordenadas —porque la página las
    # publica o porque las sacó del mapa del propio sitio—, mejor todavía:
    # entran directas y no pasan por el geocodificador.
    "lat": "lat",
    "lon": "lon",
    "comuna": "comuna",
    "precio_clp": "precio_min",
    "fuente_url": "link_evento",
    "imagen_url": "imagen_recorte",
    "id_externo": "id",
    # De qué agenda salió cada fila. No viene en la exportación de Passline
    # —ahí todo el archivo es de Passline y el nombre del archivo alcanza—,
    # pero sí en la extracción asistida semanal, donde un mismo CSV trae
    # eventos de quince municipios distintos. Sin esta columna los quince
    # quedarían atribuidos al nombre del archivo, y la atribución es la regla
    # central del proyecto: cada evento tiene que poder decir de dónde salió.
    "fuente_nombre": "fuente_nombre",
}


def _desde_fila(fila: dict, mapa: dict, fuente: dict, origen: str) -> dict | None:
    """Traduce una fila de CSV al mismo diccionario que se lee de un YAML.

    Así el CSV y el YAML entran por la misma puerta y valen las mismas reglas,
    incluida la de que sin link no se guarda.
    """
    def col(campo: str) -> str:
        nombre = mapa.get(campo)
        return html.unescape(str(fila.get(nombre, "") or "").strip()) if nombre else ""

    titulo = col("titulo")
    if not titulo:
        return None

    # "2026-08-21" + "21:00:00" → una sola fecha con hora. Sin la hora, todos
    # los eventos quedarían a medianoche.
    inicio = col("inicio")
    hora = col("hora_inicio")
    if inicio and hora:
        inicio = f"{inicio} {hora[:5]}"

    # El precio viene como "7000.00": el modelo guarda pesos enteros.
    #
    # El CERO se trata aparte y no es un detalle: en estas exportaciones un 0
    # significa "gratis", que es un HECHO, y no "no sé cuánto cuesta", que es
    # la ausencia del dato. Guardarlo como precio 0 tampoco sirve —el modelo
    # tiene un campo propio para eso— así que se traduce a es_gratis.
    #
    # Antes el 0 caía en el mismo saco que un precio inválido y quedaba en
    # None, y la línea que preguntaba `precio == 0` no podía ser verdadera
    # nunca. El efecto: 30 eventos gratis de Passline publicados sin la marca,
    # invisibles bajo el filtro de gratis, que es de los más usados.
    precio = None
    gratis = None
    crudo = col("precio_clp")
    if crudo:
        try:
            valor = int(float(crudo))
            if valor == 0:
                gratis = True
            elif 0 < valor <= 2_000_000:
                precio = valor
        except ValueError:
            pass

    return {
        "titulo": titulo,
        "categoria": col("categoria"),
        "inicio": inicio,
        "fin": col("fin"),
        "lugar_nombre": col("lugar_nombre"),
        "lugar_direccion": col("lugar_direccion"),
        "lat": col("lat"),
        "lon": col("lon"),
        "comuna": col("comuna"),
        "precio_clp": precio,
        "es_gratis": gratis,
        "fuente_url": col("fuente_url"),
        "link_entradas": col("fuente_url"),
        "imagen_url": col("imagen_url"),
        "id_externo": col("id_externo"),
        # Manda la columna si viene; si no, el nombre del archivo. Así el CSV
        # de Passline sigue funcionando igual que siempre sin tocarlo.
        "fuente_nombre": (col("fuente_nombre") or fuente.get("nombre_csv")
                          or Path(origen).stem.replace("_", " ").title()),
    }


def _leer_csv(ruta: Path, fuente: dict) -> list[dict]:
    mapa = {**COLUMNAS_CSV, **(fuente.get("csv_columnas") or {})}
    try:
        # utf-8-sig porque Excel y varios exportadores dejan BOM al inicio.
        with ruta.open(encoding="utf-8-sig", newline="") as f:
            filas = list(csv.DictReader(f))
    except (OSError, csv.Error) as e:
        log.error("%s: no pude leer el CSV (%s)", ruta.name, e)
        return []

    crudos = [_desde_fila(fila, mapa, fuente, ruta.name) for fila in filas]
    return [c for c in crudos if c]


def extraer_manual(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    """Lee todos los YAML de datos/manual/. No hace ninguna petición de red."""
    carpeta = Path(fuente.get("carpeta") or DIR_MANUAL)
    if not carpeta.exists():
        log.info("%s: todavía no existe %s", fuente.get("nombre"), carpeta)
        return []

    eventos: list[Evento] = []
    archivos = sorted(p for p in carpeta.iterdir()
                      if p.suffix.lower() in (".yaml", ".yml", ".csv")
                      and not p.name.startswith("_"))

    for ruta in archivos:
        if ruta.suffix.lower() == ".csv":
            crudos = _leer_csv(ruta, fuente)
        else:
            try:
                contenido = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                log.error("%s: YAML inválido (%s)", ruta.name, e)
                continue

            crudos = contenido.get("eventos") if isinstance(contenido, dict) else contenido
            if not isinstance(crudos, list):
                # La carpeta la comparten otros catastros (los descuentos de
                # banco, por ejemplo). Un YAML sin 'eventos' no es un error:
                # simplemente no es para nosotros.
                log.debug("%s: sin lista 'eventos' — no es un archivo de eventos",
                          ruta.name)
                continue

        for crudo in crudos:
            evento = _desde_dict(crudo, fuente, ruta.name)
            if evento:
                eventos.append(evento)

    log.info("%s: %d eventos desde %d archivo(s) en %s",
             fuente.get("nombre"), len(eventos), len(archivos), carpeta.name)
    return eventos
