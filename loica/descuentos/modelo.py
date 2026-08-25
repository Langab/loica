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
    # Rubro homologado entre bancos. Cada uno lo nombra distinto y acá se
    # traduce a un vocabulario único (ver categorias.py): restaurantes,
    # cafeterias, gourmet o comida_rapida. La traducción ocurre sola en
    # __post_init__, así que ningún adaptador puede colar un slug crudo.
    categoria: str = "restaurantes"
    # Tipo de cocina deducido del nombre del local: japonesa, italiana,
    # peruana, parrilla... Vacío cuando no hay señal, nunca inventado.
    cocina: str = ""
    comuna: str = ""
    region: str = ""
    # La calle y el número. Es el dato que convierte "hay 40% en Boga" en
    # "puedo ir caminando": sin dirección hay que salir de la página a buscarla.
    direccion: str = ""
    telefono: str = ""
    # Coordenadas del local. Bci las publica por promoción, así que ese local
    # cae en el mapa sin geocodificar nada. Los demás bancos dan la dirección
    # y las coordenadas se buscan después.
    lat: float | None = None
    lon: float | None = None
    # fuente | calle | comuna | sin_ubicar. La página atenúa el pin cuando es
    # aproximado: no es lo mismo "en esta esquina" que "en algún lugar de Maipú".
    precision: str = ""
    # Cuando la dirección vino de OTRO banco que publica el mismo local. Se
    # guarda de cuál: es un dato prestado y la ficha tiene que poder decirlo.
    direccion_prestada_de: str = ""
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

    def __post_init__(self) -> None:
        """Homologa el rubro y deduce la cocina apenas se crea el descuento.

        Va acá y no en cada adaptador a propósito: son cinco bancos y cada uno
        nombra los rubros a su manera. Si la traducción viviera en el adaptador,
        el sexto banco entraría con su vocabulario propio y la página volvería
        a mostrar dos filtros que dicen lo mismo.
        """
        from .categorias import cocina_de, homologar, rubro_desde_cocina
        cruda = self.categoria
        self.categoria = homologar(cruda)
        if not self.cocina:
            self.cocina = cocina_de(self.comercio, cruda)

        # "restaurantes" es el cajón grande: es lo que queda cuando el banco no
        # declara rubro (Santander) o cuando declara uno tan genérico como
        # "comida" (Cencosud). Ninguna de las dos cosas es una afirmación sobre
        # el local. Si el nombre ya delató una cocina que implica rubro sin
        # ambigüedad —una hamburguesería es comida rápida y una pastelería es
        # cafetería, la liste quien la liste— manda ella. Sin esto Burger King
        # quedaba escondido entre los restaurantes y fuera de su filtro.
        if self.categoria == "restaurantes":
            self.categoria = rubro_desde_cocina(self.cocina) or self.categoria

        # Media coordenada no es una coordenada. Bci publicó "China Wok
        # Arauco Maipú" con latitud y sin longitud, y esa mitad viajaba hasta
        # el JSON como si fuera un pin bueno. Se descarta acá para que el
        # local caiga en la geocodificación normal y salga con su dirección.
        if (self.lat is None) != (self.lon is None):
            self.lat = self.lon = None

    @property
    def id(self) -> str:
        """La huella del CONVENIO: un banco y un comercio, una sola oferta.

        Adentro del pipeline cada fila es una sucursal, pero el descuento no
        es de la sucursal: Banco de Chile publica el mismo 25% de Dunkin'
        sesenta y seis veces, una por local, y es un solo convenio con
        sesenta y seis lugares donde usarlo. Este id es el de ese convenio,
        y es el que la página usa para abrir la ficha.
        """
        crudo = f"{self.banco_id}|{self.comercio.lower().strip()}"
        return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:12]

    @property
    def huella(self) -> str:
        """La de la SUCURSAL, que es la que decide si dos filas son la misma.

        Lleva la dirección y no solo la comuna. Con la comuna sola, los 34
        Starbucks de Las Condes eran uno: el primero se quedaba y los otros
        33 desaparecían del mapa sin que nadie lo notara, porque el que
        quedaba se veía perfectamente bien. Banco de Chile publica 112
        Starbucks en Santiago y el catastro mostraba 22, uno por comuna.
        """
        crudo = (f"{self.banco_id}|{self.comercio.lower().strip()}"
                 f"|{self.comuna.lower()}|{' '.join(self.direccion.lower().split())}")
        return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:12]

    def a_campos(self) -> dict:
        """Los campos tal cual, para clonar la fila cambiándole la sucursal.

        `asdict` y no `vars` porque hay que copiar las listas: dos sucursales
        clonadas de la misma oferta compartirían la lista `dias` y corregir el
        día de una cambiaría el de la otra.
        """
        return asdict(self)

    def a_dict(self) -> dict:
        datos = asdict(self)
        datos["id"] = self.id
        datos["vigencia_hasta"] = self.vigencia_hasta.isoformat() if self.vigencia_hasta else None
        return datos
