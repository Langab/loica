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
import re
import sys
import time
import unicodedata
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


def prestar_direcciones(descuentos) -> int:
    """El mismo restaurante en dos bancos: el que sabe dónde queda se lo dice al otro.

    Banco de Chile y Bci publican la dirección de casi todos sus locales;
    Santander, Falabella y Cencosud no publican ninguna. Pero son en buena
    medida los mismos restaurantes: Pescados Capitales está en los dos lados,
    y en uno de ellos con calle y comuna.

    Se copia la dirección SOLO cuando el nombre normalizado calza exacto. Un
    match parcial pondría a "Sushi Home" en la dirección de "Sushi Home Ñuñoa",
    que es otro local, y un pin equivocado es peor que ninguno.
    """
    def clave(nombre: str) -> str:
        plano = unicodedata.normalize("NFD", (nombre or "").lower())
        plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
        return " ".join(re.sub(r"[^a-z0-9 ]", " ", plano).split())

    conocidas: dict[str, object] = {}
    for d in descuentos:
        if d.direccion and d.comuna:
            conocidas.setdefault(clave(d.comercio), d)

    prestadas = 0
    for d in descuentos:
        if d.direccion:
            continue
        origen = conocidas.get(clave(d.comercio))
        if origen is None:
            continue
        d.direccion, d.comuna = origen.direccion, origen.comuna
        if d.lat is None:
            d.lat, d.lon = origen.lat, origen.lon
        # Queda dicho de dónde salió: es un dato de otro banco, no del suyo.
        d.direccion_prestada_de = origen.banco
        prestadas += 1
    return prestadas


def ubicar(descuentos) -> Counter:
    """Le pone coordenadas a cada descuento para que caiga en el mapa.

    Tres precisiones, y la página las distingue porque no son lo mismo:
      fuente   → el banco publicó latitud y longitud (Bci, en el 91% de los suyos)
      calle    → se resolvió desde la dirección
      comuna   → solo se sabe la comuna, así que el pin es el centro de ella
    Un pin aproximado se muestra atenuado: mandar a alguien a una esquina donde
    no hay nada es peor que decirle "está en Ñuñoa, mira la dirección".
    """
    # Primero la memoria de arreglos (config/correcciones/restoranes.yaml):
    # cocina, rubro, dirección o coordenadas que la revisión ya corrigió una
    # vez. Va ANTES del préstamo entre bancos a propósito: una dirección
    # corregida a mano también se les presta a los otros bancos que publican
    # el mismo local.
    from loica.correcciones import Correcciones
    corr = Correcciones()
    corregidos = sum(1 for d in descuentos if corr.aplicar_a_descuento(d))
    if corregidos:
        logging.getLogger("loica").info(
            "%d descuentos con correcciones de la memoria", corregidos)

    prestadas = prestar_direcciones(descuentos)
    if prestadas:
        logging.getLogger("loica").info(
            "%d direcciones prestadas entre bancos", prestadas)

    from loica.geo import Geocodificador
    # Se reusa la misma caché de coordenadas que los eventos: muchos de estos
    # restaurantes ya están resueltos de otra corrida y no se vuelve a
    # preguntar. Nominatim queda apagado acá porque su robots.txt lo prohíbe;
    # la caché y los centros de comuna alcanzan.
    geocodificador = Geocodificador(usar_nominatim=False)
    precisiones = Counter()

    for d in descuentos:
        if d.precision == "correccion":
            # Coordenadas puestas a mano en la memoria: mandan ellas.
            precisiones["correccion"] += 1
            continue
        if d.lat is not None and d.lon is not None:
            d.precision = "fuente"
            precisiones["fuente"] += 1
            continue
        lat, lon, precision = geocodificador.ubicar("", d.direccion or "", d.comuna or "")
        d.lat, d.lon = lat, lon
        d.precision = precision if lat is not None else "sin_ubicar"
        precisiones[d.precision] += 1

    geocodificador.guardar()
    return precisiones


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

    # `--banco` es para depurar UN banco, así que lo que trae no es el catastro
    # completo: escribir el JSON con eso borraría a los otros cuatro. Pasó de
    # verdad — una corrida con --banco falabella dejó el sitio con 108
    # descuentos en vez de 652, y el archivo se publica sin que nadie lo mire.
    if args.probar or args.banco:
        for d in descuentos[:25]:
            log.info("  %-16s %-34s %-14s %s%s",
                     d.banco, d.comercio[:34], d.comuna or "—",
                     f"{d.porcentaje}% " if d.porcentaje else "",
                     ", ".join(d.dias) or "sin día")
        log.info("  … (%d más)", max(len(descuentos) - 25, 0))
        if args.banco and not args.probar:
            log.warning("Con --banco NO se escribe %s: tendría sólo este banco. "
                        "Corré sin --banco para actualizar el sitio.",
                        RUTA_SALIDA.relative_to(RAIZ))
        return 0

    precisiones = ubicar(descuentos)
    con_pin = sum(n for p, n in precisiones.items() if p != "sin_ubicar")
    log.info("%d con pin en el mapa (%d exactos) · %d solo en la lista",
             con_pin, precisiones.get("fuente", 0) + precisiones.get("calle", 0)
             + precisiones.get("correccion", 0),
             precisiones.get("sin_ubicar", 0))

    salida = escribir_json(descuentos, estadisticas)
    informe = escribir_informe(descuentos, estadisticas, duracion)
    log.info("JSON:    %s", salida.relative_to(RAIZ))
    log.info("Informe: %s", informe.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
