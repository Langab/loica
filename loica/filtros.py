"""Filtro por palabras, declarado en la configuración de cada fuente.

El muro que mantiene apagadas a casi todas las municipalidades no es técnico:
sus APIs están abiertas y responden bien. El problema es que publican las
actividades MEZCLADAS con las noticias del municipio. Recoleta tiene 2.532
posts, Independencia 1.786: entre ellos hay talleres y ferias, pero también
licitaciones, cuentas públicas y cortes de agua.

Sin una forma de decir "de esta fuente solo me interesan los posts que hablen
de talleres o ferias", encender esas fuentes significaría inundar la curaduría
de ruido. Con eso, se vuelven usables sin escribir un adaptador por comuna.

    filtro_palabras: [taller, feria, festival]   # tiene que aparecer una
    descartar_palabras: [licitacion, ordenanza]  # si aparece, se descarta

El filtro se aplica en un solo lugar (run_diario.py), así que sirve para
cualquier tipo de fuente: WordPress, RSS, HTML o JSON.
"""

from __future__ import annotations

import re
import unicodedata


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").lower()


def _menciona(texto: str, palabras) -> str:
    """Primera palabra de la lista que aparece en el texto, con límite de palabra.

    El límite importa: sin él "feria" matchea "conFERIAr" y "arte" matchea
    "reparte". Es el mismo criterio que usa el clasificador.
    """
    for palabra in palabras or []:
        patron = re.escape(_plano(str(palabra)))
        if re.search(rf"(?<![a-z0-9]){patron}(?![a-z0-9])", texto):
            return str(palabra)
    return ""


def motivo_de_descarte(evento, fuente: dict) -> str:
    """Devuelve el motivo por el que la fuente descarta este evento, o "".

    Se mira el título, la descripción y la categoría: en las noticias
    municipales el título rara vez dice "taller", pero el cuerpo sí.
    """
    incluir = fuente.get("filtro_palabras") or []
    excluir = fuente.get("descartar_palabras") or []
    if not incluir and not excluir:
        return ""

    texto = _plano(" ".join(str(p) for p in (
        evento.titulo, evento.descripcion_corta, evento.categoria) if p))

    prohibida = _menciona(texto, excluir)
    if prohibida:
        return f"palabra excluida: {prohibida}"

    if incluir and not _menciona(texto, incluir):
        return "no menciona ninguna palabra del filtro"

    return ""
