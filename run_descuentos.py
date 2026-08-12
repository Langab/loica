#!/usr/bin/env python3
"""Corrida diaria del catastro de descuentos bancarios.

Recorre los portales públicos de beneficios de los bancos, arma la tabla de
"qué restaurante tiene descuento, qué día y con qué tarjeta", y deja
`web/descuentos.json` listo para la página.

Uso:
    python3 run_descuentos.py                    # corrida completa
    python3 run_descuentos.py --banco bancochile # un solo banco, para depurar
    python3 run_descuentos.py --probar           # muestra sin escribir el JSON
    python3 run_descuentos.py --sin-cache -v     # ignora la caché y da el detalle

Igual que `run_diario.py`: no llama a ningún modelo de lenguaje, es Python
puro leyendo JSON. No consume tokens ni cuesta dinero, así que puede correr
todos los días solo.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

from loica.descuentos import recolectar

RAIZ = Path(__file__).resolve().parent
RUTA_CONFIG = RAIZ / "config" / "bancos.yaml"
RUTA_SALIDA = RAIZ / "web" / "descuentos.json"
DIR_INFORMES = RAIZ / "informes"
DIR_LOGS = RAIZ / "datos" / "logs"


def configurar_logs(verboso: bool) -> None:
    DIR_LOGS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verboso else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)-18s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(DIR_LOGS / f"{datetime.now():%Y-%m}.log", encoding="utf-8"),
        ],
    )


def cargar_bancos(solo: str | None = None) -> list[dict]:
    with open(RUTA_CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    bancos = [b for b in config.get("bancos", []) if b.get("activo", True)]
    if solo:
        bancos = [b for b in bancos if b["id"] == solo]
        if not bancos:
            raise SystemExit(f"No hay un banco activo con id '{solo}'")
    return bancos


def escribir_json(descuentos, estadisticas) -> Path:
    """El JSON que lee la página. Trae los índices ya calculados para que el
    navegador no tenga que recorrer la lista entera solo para pintar chips."""
    dias = Counter()
    for d in descuentos:
        dias.update(d.dias)

    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    RUTA_SALIDA.write_text(json.dumps({
        "generado": datetime.now().isoformat(timespec="seconds"),
        "total": len(descuentos),
        "bancos": sorted({(d.banco_id, d.banco) for d in descuentos}),
        "comunas": sorted({d.comuna for d in descuentos if d.comuna}),
        "por_dia": dict(dias),
        "descuentos": [d.a_dict() for d in descuentos],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return RUTA_SALIDA


def escribir_informe(descuentos, estadisticas, duracion: float) -> Path:
    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    hoy = datetime.now()
    ruta = DIR_INFORMES / f"{hoy:%Y-%m-%d}_descuentos.md"

    con_dia = sum(1 for d in descuentos if d.dias)
    sin_vigencia = sum(1 for d in descuentos if d.vigencia_hasta is None)
    # `%B` da "August" en el entorno de GitHub Actions, que corre en inglés
    mes = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre")[hoy.month - 1]
    lineas = [
        f"# Descuentos — {hoy.day} de {mes} de {hoy.year}",
        "",
        f"{len(descuentos)} descuentos vigentes en {duracion:.1f}s. "
        f"{con_dia} traen día de la semana ({con_dia * 100 // max(len(descuentos), 1)}%).",
        "",
        "| Banco | Crudos | Vigentes | Con día | Vencidos |",
        "|---|---:|---:|---:|---:|",
    ]
    for e in estadisticas:
        marca = " ⚠️" if e.get("error") else ""
        lineas.append(f"| {e['banco']}{marca} | {e['crudos']} | {e['vigentes']} "
                      f"| {e['con_dia']} | {e.get('vencidos', 0)} |")

    if sin_vigencia:
        lineas += ["", f"> {sin_vigencia} descuentos no declaran hasta cuándo corren. "
                       "Van marcados en la página como *sin fecha declarada*; no se dan "
                       "por buenos."]

    porcomuna = Counter(d.comuna for d in descuentos if d.comuna)
    if porcomuna:
        lineas += ["", "## Dónde están", ""]
        lineas += [f"- **{c}** — {n}" for c, n in porcomuna.most_common(15)]

    for e in estadisticas:
        if e.get("error"):
            lineas += ["", f"## Falló: {e['banco']}", "", f"```\n{e['error']}\n```"]

    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return ruta


def main() -> int:
    parser = argparse.ArgumentParser(description="Catastro diario de descuentos bancarios")
    parser.add_argument("--banco", help="correr solo este banco (por id)")
    parser.add_argument("--sin-cache", action="store_true", help="ignorar la caché local")
    parser.add_argument("--probar", action="store_true", help="no escribir el JSON")
    parser.add_argument("-v", "--verboso", action="store_true")
    args = parser.parse_args()

    configurar_logs(args.verboso)
    log = logging.getLogger("loica")
    inicio = time.time()

    bancos = cargar_bancos(args.banco)
    log.info("Revisando %d bancos%s", len(bancos), " (modo prueba)" if args.probar else "")

    descuentos, estadisticas = recolectar(bancos, usar_cache=not args.sin_cache)
    duracion = time.time() - inicio

    con_dia = sum(1 for d in descuentos if d.dias)
    log.info("")
    log.info("%d descuentos vigentes · %d con día · %.1fs",
             len(descuentos), con_dia, duracion)

    if args.probar:
        for d in descuentos[:25]:
            log.info("  %-16s %-34s %-14s %s%s",
                     d.banco, d.comercio[:34], d.comuna or "—",
                     f"{d.porcentaje}% " if d.porcentaje else "",
                     ", ".join(d.dias) or "sin día")
        log.info("  … (%d más)", max(len(descuentos) - 25, 0))
        return 0

    salida = escribir_json(descuentos, estadisticas)
    informe = escribir_informe(descuentos, estadisticas, duracion)
    log.info("JSON:    %s", salida.relative_to(RAIZ))
    log.info("Informe: %s", informe.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
