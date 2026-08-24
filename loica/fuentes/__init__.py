"""Registro de adaptadores: el archivo de configuración elige cuál usar.

Para sumar una fuente nueva no se toca código: se agrega una entrada en
config/fuentes.yaml con su tipo_adaptador.

OJO con `api`: antes ese nombre apuntaba fijo a Ticketmaster, así que cualquier
otra fuente declarada como `api` terminaba consultando Ticketmaster en silencio.
Ahora cada API tiene su nombre propio (`ticketmaster`) y las APIs JSON genéricas
usan `json`, que se configura por YAML. Un tipo_adaptador desconocido falla
fuerte en run_diario.py, que es lo que uno quiere: mejor una fuente caída que
una fuente trayendo los datos de otra.
"""

from .apis import extraer_ticketmaster
from .carteleras import extraer_carteleras
from .cine import extraer_cine
from .json_api import extraer_json
from .manual import extraer_manual
from .tablas import extraer_tabla
from .talleres import extraer_talleres
from .web import extraer_html, extraer_rss, extraer_sitemap_fichas
from .wordpress import extraer as extraer_wordpress
from .wordpress import extraer_eventon

ADAPTADORES = {
    "wordpress": extraer_wordpress,
    "eventon": extraer_eventon,
    "rss": extraer_rss,
    "html": extraer_html,
    "sitemap": extraer_sitemap_fichas,
    "carteleras": extraer_carteleras,
    "cine": extraer_cine,
    "tabla": extraer_tabla,
    "talleres": extraer_talleres,
    "json": extraer_json,
    "manual": extraer_manual,
    "ticketmaster": extraer_ticketmaster,
}

__all__ = ["ADAPTADORES"]
