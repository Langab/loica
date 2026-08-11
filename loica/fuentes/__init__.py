"""Registro de adaptadores: el archivo de configuración elige cuál usar.

Para sumar una fuente nueva no se toca código: se agrega una entrada en
config/fuentes.yaml con su tipo_adaptador.
"""

from .apis import extraer_ticketmaster
from .web import extraer_html, extraer_rss, extraer_sitemap_fichas
from .wordpress import extraer as extraer_wordpress
from .wordpress import extraer_eventon

ADAPTADORES = {
    "wordpress": extraer_wordpress,
    "eventon": extraer_eventon,
    "rss": extraer_rss,
    "html": extraer_html,
    "sitemap": extraer_sitemap_fichas,
    "api": extraer_ticketmaster,
}

__all__ = ["ADAPTADORES"]
