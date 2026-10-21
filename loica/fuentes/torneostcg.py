"""Torneos TCG Chile: los torneos destacados de la Región Metropolitana.

torneostcg.cl es un agregador nacional hecho en Next.js. No tiene JSON-LD ni
API: cada página de juego (/region-metropolitana/torneos/pokemon-tcg) trae sus
datos dentro del payload que Next.js manda en el HTML (`self.__next_f.push`).
Ahí vienen dos cosas distintas:

  - el calendario SEMANAL de cada tienda (lunes 19:00 en tal local…): cientos
    de entradas que se repiten cada semana y que llenarían la categoría con
    ligas de barrio. No se toman.
  - las "Próximas fechas destacadas": regionales, prereleases y torneos
    grandes, con fecha, hora, recinto con dirección y link de inscripción
    (objetos con "kind":"major"). Esos sí son panoramas, y son los que entran.

Se leen solo las páginas de la RM que declara el propio sitemap, así que no
hace falta filtrar regiones después. robots.txt: Allow: / (revisado
2026-10-20).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from ..modelo import Evento
from ..normalizar import detectar_comuna
from ..red import ClienteEducado

log = logging.getLogger("loica.torneostcg")

_PAGINA_RM = re.compile(r"https://www\.torneostcg\.cl/region-metropolitana/torneos/[a-z0-9\-]+$")


def _payload(html: str) -> str:
    """Junta los trozos del payload de Next.js en un solo texto legible."""
    trozos = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    partes = []
    for trozo in trozos:
        try:
            partes.append(json.loads(f'"{trozo}"'))
        except json.JSONDecodeError:
            continue
    return "".join(partes)


def _destacados(payload: str) -> list[dict]:
    """Los objetos {"kind":"major", …} que aparezcan en el payload."""
    decodificador = json.JSONDecoder()
    encontrados = []
    for m in re.finditer(r'\{"kind":"major"', payload):
        try:
            obj, _ = decodificador.raw_decode(payload, m.start())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("title") and obj.get("startsAt"):
            encontrados.append(obj)
    return encontrados


def _fecha(dia: str, hora: str | None) -> datetime | None:
    try:
        base = datetime.strptime(dia[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
    if hora and re.fullmatch(r"\d{1,2}:\d{2}", hora):
        h, m = hora.split(":")
        base = base.replace(hour=int(h), minute=int(m))
    return base


def extraer_torneostcg(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    sitemap = cliente.obtener(fuente["url_base"].rstrip("/") + "/sitemap.xml",
                              max_edad_cache_seg=24 * 3600)
    if sitemap is None or not sitemap.ok:
        log.warning("%s: no respondió el sitemap", fuente.get("nombre"))
        return []
    paginas = sorted({u for u in re.findall(r"<loc>([^<]+)</loc>", sitemap.text)
                      if _PAGINA_RM.match(u.strip())})

    vistos: dict[str, Evento] = {}
    for url in paginas[: int(fuente.get("tope_fichas", 30))]:
        pagina = cliente.obtener(url, max_edad_cache_seg=12 * 3600)
        if pagina is None or not pagina.ok:
            continue
        for item in _destacados(_payload(pagina.text)):
            clave = item.get("id") or f'{item["title"]}|{item["startsAt"]}'
            if clave in vistos:
                continue
            # "$undefined" es como Next.js serializa un campo vacío.
            fin = item.get("endsAt")
            recinto = str(item.get("venue") or "").strip()
            # El recinto viene como "Hotel Gran Palace - Huérfanos 1178":
            # nombre y dirección en el mismo campo.
            nombre, _, direccion = recinto.partition(" - ")
            inscripcion = str(item.get("url") or "")
            vistos[clave] = Evento(
                titulo=str(item["title"]).strip(),
                categoria="Torneo de cartas",
                descripcion_corta=f'Organiza {item["organizer"]}.' if item.get("organizer") else "",
                inicio=_fecha(item["startsAt"], item.get("startTime")),
                fin=_fecha(fin, item.get("endTime")) if isinstance(fin, str) and fin[:1].isdigit() else None,
                lugar_nombre=nombre.strip() or recinto,
                lugar_direccion=direccion.strip(),
                comuna=detectar_comuna(direccion, nombre, item.get("city") or ""),
                fuente_tipo="torneostcg",
                fuente_nombre=fuente.get("nombre", ""),
                fuente_url=url,
                link_entradas=inscripcion if inscripcion.startswith("http") else "",
                id_externo=str(item.get("id") or ""),
            )

    log.info("%s: %d torneos destacados en %d páginas de la RM",
             fuente.get("nombre"), len(vistos), len(paginas))
    return [e for e in vistos.values() if e.inicio is not None]
