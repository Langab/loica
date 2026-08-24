#!/usr/bin/env python3
"""Corrida diaria de la cartelera de cine.

Recorre las salas del catastro que publican horarios legibles, junta las que
llegaron por la agenda cultural y las que dejó la extracción asistida, y deja
`web/cine.json` listo para la página.

Uso:
    python3 run_cine.py                  # corrida completa
    python3 run_cine.py --via jsonld     # una sola vía, para depurar
    python3 run_cine.py --probar         # muestra sin escribir el JSON
    python3 run_cine.py --sin-cache -v   # ignora la caché y da el detalle

Corre DESPUÉS de exportar_web.py: una de sus cuatro vías lee `web/eventos.json`
para recoger las funciones de la Cineteca, de M100 y del Centro Arte Alameda,
que ya llegan por las fuentes de siempre y no hay por qué pedir dos veces.

Igual que el resto del pipeline: es Python puro leyendo HTML y JSON. No llama
a ningún modelo de lenguaje, no consume tokens y puede correr solo todos los
días.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from loica.cartelera import DIAS, para_la_web, recolectar
from loica.cines import catalogo
from loica.red import ClienteEducado

RAIZ = Path(__file__).resolve().parent
RUTA_SALIDA = RAIZ / "web" / "cine.json"

# Piso de publicación. Si una corrida trae menos funciones que esto, algo se
# rompió río arriba —Cinemark cambió su HTML, se cayó la red— y publicar el
# archivo dejaría la página vacía. Es el mismo criterio del doble check de
# verificar_web.py: mejor el dato de ayer que una página en blanco.
#
# Una sola sala de Cinemark trae del orden de cien funciones en tres días, y
# son ocho salas. Cincuenta es "se cayó casi todo" sin ser tan estricto como
# para bloquear un feriado en que las cadenas publican poco.
PISO_FUNCIONES = 50


def main() -> int:
    parser = argparse.ArgumentParser(description="Corrida de la cartelera de cine")
    parser.add_argument("--via", help="solo esta vía: jsonld · semanal · agenda · asistida")
    parser.add_argument("--probar", action="store_true", help="no escribir el JSON")
    parser.add_argument("--sin-cache", action="store_true", help="ignorar la caché local")
    parser.add_argument("--forzar", action="store_true",
                        help="publicar aunque caiga bajo el piso de funciones")
    parser.add_argument("-v", "--verboso", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verboso else logging.WARNING,
                        format="%(message)s")
    log = logging.getLogger("cine")
    log.setLevel(logging.INFO)

    salas = catalogo()
    if not salas:
        print("No hay catastro de cines. Corre antes:")
        print("    python3 scripts/catastro_cines.py")
        return 1

    cliente = ClienteEducado(crawl_delay_seg=2, usar_cache=not args.sin_cache)
    cartelera = recolectar(cliente, solo=args.via)
    salida = para_la_web(cartelera)

    print(f"\n{len(cartelera.funciones)} funciones · "
          f"{len(salida['peliculas'])} películas · "
          f"{sum(1 for c in salida['cines'] if c['funciones'])} de {len(salas)} salas "
          f"con horarios · {DIAS} días")

    por_via = Counter(f.fuente.split(":")[0] for f in cartelera.funciones)
    for via, cuantas in por_via.most_common():
        print(f"    {via or '(sin fuente)':12} {cuantas:5d}")

    if cartelera.salas_fallidas:
        print(f"\n  No dieron cartelera ({len(cartelera.salas_fallidas)}):")
        for fallo in cartelera.salas_fallidas[:12]:
            print(f"    · {fallo}")
    if cartelera.notas:
        print("\n  Notas:")
        for nota in cartelera.notas[:12]:
            print(f"    · {nota}")

    # Las salas sin horarios NO son un error: veinte de ellas son de las dos
    # cadenas que no se pueden leer, y salen igual en el mapa con su link.
    sin_horarios = [c for c in salida["cines"] if not c["funciones"]]
    if sin_horarios:
        print(f"\n  {len(sin_horarios)} salas van al mapa sin horarios "
              f"(cartelera cerrada o sin funciones cargadas)")

    if args.probar:
        print("\n--probar: no se escribió nada.")
        return 0

    if len(cartelera.funciones) < PISO_FUNCIONES and not args.forzar:
        print(f"\n  ✗ Solo {len(cartelera.funciones)} funciones (el piso son "
              f"{PISO_FUNCIONES}). No se escribe web/cine.json: se conserva el de "
              f"la corrida anterior.\n    Para publicar igual: --forzar")
        return 1

    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    RUTA_SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    print(f"\n  Escrito {RUTA_SALIDA.relative_to(RAIZ)} "
          f"({RUTA_SALIDA.stat().st_size / 1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
