#!/usr/bin/env python3
"""Convierte una tabla pegada en YAML de ingesta asistida.

Para lo que no se puede rastrear (Passline, Instagram, un afiche): la persona
copia la tabla desde donde la tenga y esto la deja en el formato que lee el
adaptador `manual`, con las fechas ya interpretadas.

    python3 scripts/importar_tabla.py tabla.tsv --fuente Passline \\
        --salida datos/manual/passline.yaml

Acepta columnas separadas por tabulaciones o por | (tabla Markdown), en este
orden: fecha, hora, evento, lugar, [estado]. El orden se puede cambiar con
--columnas.

IMPORTANTE — el link es obligatorio: el pipeline descarta cualquier evento sin
`fuente_url`, porque sin atribución el proyecto deja de ser un índice y pasa a
ser una copia. Si la tabla no trae una columna de link, este script igual
escribe el YAML pero deja `fuente_url` vacío y avisa cuántos quedaron así, para
que se completen antes de la corrida.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from loica.normalizar import parsear_fecha

# Estados que publica la ticketera y que no son parte del nombre del evento.
ESTADOS = {"sold out", "agotado", "promo", "funciones disponibles", "cancelado"}


def _filas(texto: str) -> list[list[str]]:
    filas = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        separador = "\t" if "\t" in linea else ("|" if "|" in linea else None)
        if separador is None:
            continue
        celdas = [c.strip() for c in linea.split(separador)]
        celdas = [c for c in celdas if c != ""]
        if len(celdas) >= 3:
            filas.append(celdas)
    return filas


def _sin_encabezado(filas: list[list[str]]) -> list[list[str]]:
    """Descarta la fila de títulos y los separadores de tabla Markdown."""
    limpias = []
    for celdas in filas:
        plano = " ".join(celdas).lower()
        if set(plano) <= set("-: |"):
            continue
        if plano.startswith("fecha") and "evento" in plano:
            continue
        limpias.append(celdas)
    return limpias


def convertir(texto: str, fuente: str, orden: list[str]) -> tuple[list[dict], int]:
    eventos, sin_fecha = [], 0

    for celdas in _sin_encabezado(_filas(texto)):
        fila = dict(zip(orden, celdas))

        fecha_txt = fila.get("fecha", "")
        hora_txt = fila.get("hora", "")
        # "13 Ago 2026" + "21:00". La hora se pega a la fecha porque
        # parsear_fecha busca la hora al lado de la fecha, no en toda la línea.
        if hora_txt and ":" in hora_txt:
            fecha_txt = f"{fecha_txt} {hora_txt}"
        inicio = parsear_fecha(fecha_txt)
        if inicio is None:
            sin_fecha += 1
            continue

        titulo = fila.get("evento", "").strip()
        if not titulo:
            continue
        # "El Gran Viaje / Centro Arte Alameda" — la ticketera repite el
        # recinto en el título; sobra, ya va en lugar_nombre.
        lugar = fila.get("lugar", "").strip()
        if lugar and titulo.endswith(f"/ {lugar}"):
            titulo = titulo[: -len(f"/ {lugar}")].strip()

        estado = fila.get("estado", "").strip()
        entrada = {
            "titulo": titulo,
            "inicio": inicio.strftime("%Y-%m-%d %H:%M"),
            "lugar_nombre": lugar,
            "fuente_nombre": fuente,
            "fuente_url": fila.get("link", "").strip(),
        }
        if estado and estado.lower() in ESTADOS:
            entrada["descripcion_corta"] = estado
        eventos.append(entrada)

    return eventos, sin_fecha


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archivo", help="tabla en .tsv, .txt o Markdown")
    parser.add_argument("--fuente", default="Ingesta manual",
                        help="de dónde salió el dato (Passline, Instagram...)")
    parser.add_argument("--salida", default="datos/manual/importado.yaml")
    parser.add_argument("--columnas", default="fecha,hora,evento,lugar,estado",
                        help="orden de las columnas; usa 'link' si la tabla lo trae")
    args = parser.parse_args()

    texto = Path(args.archivo).read_text(encoding="utf-8")
    orden = [c.strip() for c in args.columnas.split(",")]
    eventos, sin_fecha = convertir(texto, args.fuente, orden)

    if not eventos:
        print("No se pudo leer ninguna fila. ¿Están separadas por tabulaciones o |?")
        return 1

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        yaml.safe_dump({"eventos": eventos}, allow_unicode=True, sort_keys=False,
                       default_flow_style=False),
        encoding="utf-8")

    sin_link = sum(1 for e in eventos if not e["fuente_url"])
    print(f"{len(eventos)} eventos escritos en {salida}")
    if sin_fecha:
        print(f"{sin_fecha} filas sin fecha reconocible, omitidas")
    if sin_link:
        print(f"\n  ATENCIÓN: {sin_link} eventos sin fuente_url.")
        print("  El pipeline los va a DESCARTAR: sin link no hay atribución.")
        print("  Volvé a extraer la tabla incluyendo el link de cada evento y")
        print("  corré esto con --columnas fecha,hora,evento,lugar,estado,link")
    return 0


if __name__ == "__main__":
    sys.exit(main())
