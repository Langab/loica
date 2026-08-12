"""Modelo de un descuento bancario.

Un descuento NO es un evento y por eso no reusa `Evento`. Un evento pasa una
vez y tiene fecha; un descuento se repite todas las semanas y lo que tiene es
vigencia. La pregunta que responde tampoco es la misma: no es "¿qué hago el
sábado?" sino "es martes, ando por Providencia y tengo tarjeta del Chile,
¿dónde como?".

Misma regla de atribución que los eventos: guardamos HECHOS (comercio, día,
porcentaje, comuna, tarjetas) y el link a la página del banco. Las reseñas y
las fotos del banco se enlazan, no se copian.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import date


@dataclass
class Descuento:
    # Quién da el descuento
    banco_id: str
    banco: str

    # Dónde se usa
    comercio: str
    categoria: str = "restaurantes"     # restaurantes | cafeterias | gourmet
    comuna: str = ""
    region: str = ""
    # La calle y el número. Es el dato que convierte "hay 40% en Boga" en
    # "puedo ir caminando": sin dirección hay que salir de la página a buscarla.
    direccion: str = ""
    telefono: str = ""
    # OJO: son dos links distintos y los dos importan.
    #   url        → la ficha del banco. Es la fuente y la que manda si hay
    #                discusión sobre las condiciones.
    #   sitio_web  → la página del local. Es donde se reserva o se pide.
    sitio_web: str = ""

    # Qué tan bueno es
    porcentaje: int | None = None
    # Etiqueta para lo que no es porcentaje: "2x1", "Con regalo", "Combo".
    # Un descuento tiene uno u otro, nunca los dos.
    oferta: str = ""
    tope: int | None = None

    # Cuándo sirve.
    # Lista VACÍA significa "sin restricción de día", no "no supimos leerlo".
    # Los tres bancos coinciden en eso: Banco de Chile declara el día en 353 de
    # sus 354 promociones, y las de Bci son convenios permanentes de 10-25% que
    # corren cualquier día. Por eso la página muestra la lista vacía como
    # "todos los días" y esas promociones sí aparecen bajo el filtro de Hoy.
    dias: list[str] = field(default_factory=list)   # ["martes", "jueves"]
    vigencia_hasta: date | None = None

    # Con qué se paga
    tarjetas: list[str] = field(default_factory=list)
    modalidad: str = ""                 # presencial | online | ambas

    # Letra chica y atribución
    segmentado: bool = False            # no es para todos los clientes del banco
    condiciones: str = ""
    url: str = ""
    logo: str = ""
    # Fecha de captura, solo para las fuentes que no se pueden automatizar.
    # Vacío = lo trajo la corrida de hoy.
    capturado: str = ""

    @property
    def id(self) -> str:
        """Huella estable: el mismo comercio del mismo banco no se duplica.

        Va la comuna porque una cadena con veinte locales publica veinte
        entradas distintas y todas son descuentos reales, no repetidos.
        """
        crudo = f"{self.banco_id}|{self.comercio.lower().strip()}|{self.comuna.lower()}"
        return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:12]

    def a_dict(self) -> dict:
        datos = asdict(self)
        datos["id"] = self.id
        datos["vigencia_hasta"] = self.vigencia_hasta.isoformat() if self.vigencia_hasta else None
        return datos
