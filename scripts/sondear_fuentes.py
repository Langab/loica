#!/usr/bin/env python3
"""Sondeo de red: qué responde cada fuente activa DESDE DONDE CORRE ESTO.

    python3 scripts/sondear_fuentes.py            # todas las fuentes activas
    python3 scripts/sondear_fuentes.py --todas    # también las apagadas

Una petición por fuente (su url_agenda o url_base), sin caché, y una línea
con el código HTTP, el servidor y si Cloudflare puso un desafío. Existe
porque la corrida vive en GitHub Actions, cuya IP es de datacenter, y hay
sitios que a esa IP le cuelgan la conexión o le responden 403/503 mientras
al Mac le responden 200. Los adaptadores no registran el código de la
respuesta, así que cuando una fuente sale en cero desde la nube esto es lo
que dice por qué. Se corre en la nube con:

    gh workflow run corrida.yml -f modo=sondear
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from loica.red import ClienteEducado  # noqa: E402

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "fuentes.yaml"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--todas", action="store_true", help="incluir las fuentes apagadas")
    args = parser.parse_args()

    with open(RUTA_CONFIG, encoding="utf-8") as f:
        fuentes = yaml.safe_load(f)["fuentes"]
    fuentes = [x for x in fuentes if (args.todas or x.get("activa", True))
               and x.get("tipo_adaptador") != "manual"]

    cliente = ClienteEducado(crawl_delay_seg=1, timeout=20, usar_cache=False)
    print(f"{'código':>6}  {'seg':>5}  {'servidor':14} {'cf':9} fuente → url")
    resumen: dict[str, list[str]] = {}
    for fuente in fuentes:
        url = fuente.get("url_agenda") or fuente.get("url_base")
        t0 = time.time()
        try:
            r = cliente.sesion.get(url, timeout=20)
            codigo = str(r.status_code)
            servidor = (r.headers.get("server") or "?")[:14]
            cf = r.headers.get("cf-mitigated") or "-"
        except Exception as e:  # noqa: BLE001 — es un sondeo, se anota y se sigue
            codigo, servidor, cf = type(e).__name__[:14], "-", "-"
        seg = time.time() - t0
        print(f"{codigo:>6}  {seg:5.1f}  {servidor:14} {cf:9} {fuente['nombre'][:45]} → {url}")
        clave = "ok" if codigo == "200" else ("cuelga" if not codigo.isdigit() else codigo)
        resumen.setdefault(clave, []).append(fuente["nombre"])

    print("\nResumen:")
    for clave, nombres in sorted(resumen.items(), key=lambda kv: -len(kv[1])):
        print(f"  {clave:8} {len(nombres):3d}  " + ("" if clave == "ok" else "· ".join(n[:30] for n in nombres)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
