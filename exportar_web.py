#!/usr/bin/env python3
"""Geocodifica los eventos vigentes y los exporta para el prototipo del mapa.

    python3 exportar_web.py

Deja web/eventos.json con los eventos futuros listos para dibujar.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from loica.almacen import Almacen
from loica.geo import Geocodificador

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "web" / "eventos.json"

# Taxonomía provisional: mapea lo que dicen las fuentes a las categorías del
# producto. La definitiva está en definicion_producto_mvp.md.
CATEGORIAS = {
    "idiomas": ["intercambio de idioma", "language exchange", "conversation club",
                "club de conversación", "mundo lingo", "intercambio linguístico"],
    "musica": ["música", "musica", "concierto", "tocata", "recital", "banda"],
    "teatro": ["teatro", "obra", "dramaturgia", "títeres", "titeres"],
    "arte": ["exposición", "exposicion", "muestra", "galería", "galeria", "arte",
             "fotografía", "fotografia", "pintura"],
    "clases": ["taller", "clase", "curso", "workshop", "entrenamiento", "laboratorio"],
    "fiesta": ["fiesta", "party", "club", "dj", "carrete"],
    "cine": ["cine", "película", "pelicula", "documental", "cineteca"],
    "familia": ["familia", "niños", "ninos", "infantil", "criaturas"],
    "charla": ["charla", "conversatorio", "seminario", "lanzamiento", "coloquio",
               "conferencia", "encuentro"],
    "aire_libre": ["parque", "cerro", "caminata", "ruta", "naturaleza", "bosque"],
}


# Lo que NO es un panorama aunque aparezca en una agenda cultural: ofertas de
# trabajo, prácticas, concursos y trámites. Se colaron en la primera corrida
# (una práctica de administración con "$100.000" quedó como si fuera el precio).
NO_ES_PANORAMA = [
    "buscamos practicante", "buscamos pasante", "práctica profesional",
    "practica profesional", "oferta laboral", "postula a ", "postulaciones",
    "convocatoria laboral", "llamado a concurso", "concurso público",
    "concurso publico", "se busca ", "vacante", "bases del concurso",
    "requisitos de postulación", "cartas de apoyo", "fondos de cultura",
    "matrícula", "matricula ", "proceso de admisión", "calendario académico",
]


def es_panorama(titulo: str, descripcion: str) -> tuple[bool, str]:
    """Filtra lo que claramente no es un evento al que alguien pueda ir."""
    texto = f"{titulo} {descripcion}".lower()
    for senal in NO_ES_PANORAMA:
        if senal in texto:
            return False, senal
    return True, ""


def clasificar(titulo: str, categoria_fuente: str, descripcion: str) -> str:
    texto = f"{categoria_fuente} {titulo} {descripcion}".lower()
    for categoria, palabras in CATEGORIAS.items():
        if any(palabra in texto for palabra in palabras):
            return categoria
    return "otros"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("exportar")

    almacen = Almacen()
    filas = almacen.con.execute(
        """SELECT * FROM eventos
           WHERE inicio >= date('now') AND estado != 'descartado'
           ORDER BY inicio""",
    ).fetchall()

    geo = Geocodificador()
    eventos = []
    sin_ubicar = 0
    descartados = []

    for fila in filas:
        panorama, senal = es_panorama(fila["titulo"], fila["descripcion_corta"] or "")
        if not panorama:
            descartados.append(f'{fila["titulo"][:52]} (por "{senal}")')
            continue

        # Si la fuente ya entregó coordenadas, mandan ellas
        lat, lon, precision = fila["lat"], fila["lon"], "fuente"
        if lat is None:
            lat, lon, precision = geo.ubicar(
                fila["lugar_nombre"] or "", fila["lugar_direccion"] or "", fila["comuna"] or "")
        if lat is None:
            # No se descarta: sale en la lista sin pin. Botar 42 eventos reales
            # (entre ellos 20 obras de teatro) es peor que mostrarlos sin mapa.
            sin_ubicar += 1
            precision = "sin_ubicar"

        eventos.append({
            "id": fila["hash_dedup"],
            "titulo": fila["titulo"],
            "inicio": fila["inicio"],
            "fin": fila["fin"],
            "lugar": fila["lugar_nombre"] or fila["fuente_nombre"],
            "direccion": fila["lugar_direccion"] or "",
            "comuna": fila["comuna"] or "",
            "lat": lat,
            "lon": lon,
            "precision": precision,
            "gratis": bool(fila["es_gratis"]),
            "precio": fila["precio_clp"],
            "precio_texto": fila["precio_texto"] or "",
            "categoria": clasificar(fila["titulo"], fila["categoria"] or "",
                                    fila["descripcion_corta"] or ""),
            "descripcion": fila["descripcion_corta"] or "",
            "imagen": fila["imagen_url"] or "",
            "fuente": fila["fuente_nombre"],
            "url": fila["fuente_url"],
        })

    geo.guardar()
    almacen.cerrar()

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({
        "generado": datetime.now().isoformat(timespec="seconds"),
        "total": len(eventos),
        "eventos": eventos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    gratis = sum(1 for e in eventos if e["gratis"])
    exactos = sum(1 for e in eventos if e["precision"] == "recinto")
    con_imagen = sum(1 for e in eventos if e["imagen"])
    exactos += sum(1 for e in eventos if e["precision"] == "fuente")
    log.info("Exportados %d eventos (%d gratis, %d con ubicación exacta, %d con imagen)",
             len(eventos), gratis, exactos, con_imagen)
    if sin_ubicar:
        log.info("Sin pin en el mapa (salen solo en la lista): %d", sin_ubicar)
    if descartados:
        log.info("Descartados por no ser panoramas (%d):", len(descartados))
        for d in descartados:
            log.info("   · %s", d)
    log.info("Archivo: %s", SALIDA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
