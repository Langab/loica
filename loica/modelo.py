"""Modelo de datos de un evento, alineado con el esquema de atribución del proyecto.

Regla del proyecto: solo guardamos HECHOS (título, cuándo, dónde, precio) y el
link a la fuente original. Las descripciones largas y las fotos se enlazan, no
se copian.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, date

ESTADOS = ("borrador", "publicado", "descartado", "caducado")


def _sin_tildes(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


# Los endpoints por donde el pipeline descubre eventos (sitemaps, feeds, APIs)
# NO son links para una persona: quien los abre ve un XML crudo, no el evento.
# Como la promesa del proyecto es dejar al usuario en la fuente original, un
# enlace así vale lo mismo que no tener enlace.
_ENDPOINTS_DE_MAQUINA = re.compile(
    r"(sitemap[^/]*\.xml|\.xml$|\.rss$|/feed/?$|/wp-json/|/admin-ajax\.php|"
    r"/api/|\.json($|\?)|[?&](f|format|formato)=json)",
    re.IGNORECASE,
)


def es_enlace_de_maquina(url: str) -> bool:
    """¿Este link lleva a datos para un programa en vez de a una página?"""
    return bool(url) and bool(_ENDPOINTS_DE_MAQUINA.search(url))


def clave_dedup(titulo: str, inicio: date | datetime | None, lugar: str) -> str:
    """Huella para detectar el mismo evento llegando por varias fuentes.

    Se normaliza agresivamente porque el mismo evento aparece como
    "Yoga en el Parque" en la muni y "YOGA EN EL PARQUE 🧘" en Instagram.
    """
    base_titulo = _sin_tildes(titulo or "").lower()
    base_titulo = re.sub(r"[^a-z0-9 ]", " ", base_titulo)
    base_titulo = " ".join(base_titulo.split())[:60]

    base_lugar = _sin_tildes(lugar or "").lower()
    base_lugar = re.sub(r"[^a-z0-9 ]", " ", base_lugar)
    base_lugar = " ".join(base_lugar.split())[:40]

    dia = ""
    if isinstance(inicio, datetime):
        dia = inicio.date().isoformat()
    elif isinstance(inicio, date):
        dia = inicio.isoformat()

    crudo = f"{base_titulo}|{dia}|{base_lugar}"
    return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:16]


@dataclass
class Evento:
    # Qué
    titulo: str
    categoria: str = ""
    descripcion_corta: str = ""

    # Cuándo
    inicio: datetime | None = None
    fin: datetime | None = None
    todo_el_dia: bool = False

    # Dónde
    lugar_nombre: str = ""
    lugar_direccion: str = ""
    comuna: str = ""
    lat: float | None = None
    lon: float | None = None

    # Cuánto
    precio_clp: int | None = None
    es_gratis: bool | None = None
    precio_texto: str = ""

    # Atribución: el corazón del modelo "índice con atribución"
    fuente_tipo: str = ""      # api | wordpress | eventon | rss | html | manual | formulario
    fuente_nombre: str = ""    # "Matucana 100"
    fuente_url: str = ""       # link al evento en su sitio original
    link_entradas: str = ""    # ticketera, si la fuente la declara
    imagen_url: str = ""       # se enlaza, no se descarga
    id_externo: str = ""       # id del evento en la fuente

    # Trazabilidad
    fecha_publicacion: datetime | None = None  # cuándo la fuente publicó el aviso
    fecha_extraccion: datetime = field(default_factory=datetime.now)
    fecha_ultima_verificacion: datetime = field(default_factory=datetime.now)
    estado: str = "borrador"   # NADA se publica sin revisión humana

    @property
    def hash_dedup(self) -> str:
        return clave_dedup(self.titulo, self.inicio, self.lugar_nombre or self.comuna)

    @property
    def necesita_fecha(self) -> bool:
        """El sitio anunció algo pero no pudimos leer cuándo es.

        No se descarta: se le muestra al curador para que ponga la fecha a mano.
        Descubrir el evento ya es la mitad del trabajo.
        """
        return self.inicio is None

    def es_valido(self) -> tuple[bool, str]:
        """Filtro mínimo antes de guardar. Devuelve (válido, motivo)."""
        if not self.titulo or len(self.titulo.strip()) < 3:
            return False, "sin título"
        if not self.fuente_url:
            return False, "sin link a la fuente (rompe la atribución)"
        if es_enlace_de_maquina(self.fuente_url):
            return False, f"el link es un endpoint, no una página: {self.fuente_url}"
        if self.inicio is not None and self.inicio.date() < date.today():
            return False, "evento pasado"
        return True, ""

    def como_dict(self) -> dict:
        d = asdict(self)
        for campo in ("inicio", "fin", "fecha_extraccion", "fecha_ultima_verificacion"):
            valor = d.get(campo)
            d[campo] = valor.isoformat() if isinstance(valor, (datetime, date)) else None
        d["hash_dedup"] = self.hash_dedup
        return d
