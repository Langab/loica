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
RUTA_ESTADO = RAIZ / "datos" / "ultima_corrida_descuentos.json"
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


def ubicar(descuentos) -> tuple[list, Counter, dict]:
    """Le pone coordenadas a cada descuento para que caiga en el mapa.

    Tres precisiones, y la página las distingue porque no son lo mismo:
      fuente   → el banco publicó latitud y longitud (Bci, en el 91% de los suyos)
      calle    → se resolvió desde la dirección
      comuna   → solo se sabe la comuna, así que el pin es el centro de ella
    Un pin aproximado se muestra atenuado: mandar a alguien a una esquina donde
    no hay nada es peor que decirle "está en Ñuñoa, mira la dirección".
    """
    log = logging.getLogger("loica")

    # Primero la memoria de arreglos (config/correcciones/restoranes.yaml):
    # cocina, rubro, dirección o coordenadas que la revisión ya corrigió una
    # vez. Va ANTES de abrir las cadenas a propósito: una dirección corregida
    # a mano también sirve de sucursal para los otros bancos que publican el
    # mismo local.
    from loica.correcciones import Correcciones
    corr = Correcciones()
    corregidos = sum(1 for d in descuentos if corr.aplicar_a_descuento(d))
    if corregidos:
        log.info("%d descuentos con correcciones de la memoria", corregidos)

    # Y ahora las cadenas: la oferta que el banco publicó sin ninguna
    # dirección —"Melt Pizzas", a secas— se abre en una fila por sucursal
    # conocida, para que caiga en el mapa entera y no se quede solo en la
    # lista. Ver loica/descuentos/cadenas.py.
    from loica.descuentos.cadenas import _comuna_de, expandir
    descuentos, cuenta = expandir(descuentos)
    if cuenta["ofertas"]:
        log.info("%d ofertas de cadena abiertas en %d sucursales "
                 "(%d del mismo banco, %d de otros bancos, %d de OpenStreetMap)",
                 cuenta["ofertas"], cuenta["sedes"], cuenta["propias"],
                 cuenta["de_bancos"], cuenta["de_osm"])

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

    # Último filtro, y va DESPUÉS de geocodificar porque antes no había con
    # qué. `es_metropolitana` deja pasar lo que no declara ni comuna ni
    # región, y tiene razón en hacerlo: la mayoría de esos son cadenas
    # nacionales que sí tienen local en Santiago. Pero algunos no lo son, y
    # cuando la dirección se resuelve queda un pin en Chiloé, en Huasco, en
    # Quillota o en Reñaca dentro del mapa de Santiago. Son cinco hoy y
    # estaban desde antes de las cadenas: el pin se veía correcto porque lo
    # era —el local existe y queda ahí—, solo que a seiscientos kilómetros de
    # quien abre la página.
    fuera = [d for d in descuentos
             if d.lat is not None and not _comuna_de(d.lat, d.lon, d.comuna)]
    if fuera:
        log.info("%d locales quedan fuera del mapa por estar fuera de la RM: %s",
                 len(fuera), ", ".join(f"{d.comercio} ({d.direccion})" for d in fuera[:6]))
        descartados = {id(d) for d in fuera}
        descuentos = [d for d in descuentos if id(d) not in descartados]

    return descuentos, precisiones, cuenta


def escribir_json(ofertas: list[dict], estadisticas) -> Path:
    """El JSON que lee la página. Trae los índices ya calculados para que el
    navegador no tenga que recorrer la lista entera solo para pintar chips.

    Lo que se publica son OFERTAS, no filas: un convenio del banco con su
    lista de locales adentro. `total` cuenta convenios —que es lo que la
    página muestra como "N descuentos"— y `locales` cuenta los lugares donde
    usarlos, que es lo que se ve en el mapa. Los dos números son distintos y
    los dos importan: Banco de Chile tiene un convenio con Dunkin' y sesenta y
    seis lugares donde comerse la dona.
    """
    dias = Counter()
    for o in ofertas:
        dias.update(o["dias"])

    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    RUTA_SALIDA.write_text(json.dumps({
        "generado": datetime.now().isoformat(timespec="seconds"),
        "total": len(ofertas),
        "locales": sum(len(o["locales"]) for o in ofertas),
        "bancos": sorted({(o["banco_id"], o["banco"]) for o in ofertas}),
        "comunas": sorted({c for o in ofertas for c in o["comunas"]}),
        "por_dia": dict(dias),
        "descuentos": ofertas,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return RUTA_SALIDA


def guardar_estado(bancos, estadisticas, duracion: float) -> Path:
    """Deja por escrito qué banco corrió, cómo y con qué resultado.

    Los eventos registran cada corrida en la tabla `corridas` de la base, así
    que el diagnóstico puede reconstruir después qué pasó con cada fuente. Los
    descuentos no tenían dónde: sus estadísticas vivían en memoria, se
    imprimían en el informe en Markdown y se perdían. El resultado era que la
    hoja de fuentes del Excel podía decir el estado de las 127 fuentes de
    eventos y no el de los cinco bancos, que son fuentes web igual que las
    otras y se rompen igual que las otras.

    Va a `datos/` y no a `web/` porque es diagnóstico del proceso, no catastro:
    a la página no le sirve saber que Cencosud demoró once segundos.
    """
    por_nombre = {e["banco"]: e for e in estadisticas}
    filas = []
    for banco in bancos:
        e = por_nombre.get(banco["nombre"], {})
        filas.append({
            "id": banco["id"],
            "banco": banco["nombre"],
            "adaptador": banco.get("adaptador", ""),
            # Un banco activo que no aparece en las estadísticas es uno cuyo
            # adaptador no existe: `recolectar` lo saltó sin dejar rastro.
            "corrio": banco["nombre"] in por_nombre,
            "crudos": e.get("crudos", 0),
            "vigentes": e.get("vigentes", 0),
            "con_dia": e.get("con_dia", 0),
            "vencidos": e.get("vencidos", 0),
            "fuera_rm": e.get("fuera_rm", 0),
            "error": e.get("error", "") or (
                "" if banco["nombre"] in por_nombre
                else f"adaptador desconocido: {banco.get('adaptador', '')}"),
        })

    RUTA_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    RUTA_ESTADO.write_text(json.dumps({
        "momento": datetime.now().isoformat(timespec="seconds"),
        "duracion_seg": round(duracion, 1),
        "bancos": filas,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return RUTA_ESTADO


def escribir_informe(ofertas: list[dict], estadisticas, duracion: float,
                    cadenas: dict | None = None) -> Path:
    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    hoy = datetime.now()
    ruta = DIR_INFORMES / f"{hoy:%Y-%m-%d}_descuentos.md"

    con_dia = sum(1 for o in ofertas if o["dias"])
    sin_vigencia = sum(1 for o in ofertas if o["vigencia_hasta"] is None)
    locales = sum(len(o["locales"]) for o in ofertas)
    # `%B` da "August" en el entorno de GitHub Actions, que corre en inglés
    mes = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre")[hoy.month - 1]
    lineas = [
        f"# Descuentos — {hoy.day} de {mes} de {hoy.year}",
        "",
        f"{len(ofertas)} descuentos vigentes en {locales} locales, en "
        f"{duracion:.1f}s. {con_dia} traen día de la semana "
        f"({con_dia * 100 // max(len(ofertas), 1)}%).",
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

    if cadenas and cadenas.get("ofertas"):
        partes = []
        if cadenas.get("propias"):
            partes.append(f"{cadenas['propias']} las publica el mismo banco en otra entrada")
        if cadenas.get("de_bancos"):
            partes.append(f"{cadenas['de_bancos']} las publica otro banco")
        if cadenas.get("de_osm"):
            partes.append(f"{cadenas['de_osm']} salen de OpenStreetMap")
        lineas += ["", f"> {cadenas['ofertas']} ofertas venían sin ninguna dirección y se "
                       f"abrieron en {cadenas['sedes']} sucursales: {', '.join(partes)}. "
                       "Cada local dice de dónde salió."]

    porcomuna = Counter(l["comuna"] for o in ofertas for l in o["locales"] if l["comuna"])
    if porcomuna:
        lineas += ["", "## Dónde están", ""]
        lineas += [f"- **{c}** — {n}" for c, n in porcomuna.most_common(15)]

    cadenones = sorted(((len(o["locales"]), o["comercio"], o["banco"]) for o in ofertas),
                       reverse=True)[:10]
    if cadenones and cadenones[0][0] > 1:
        lineas += ["", "## Las cadenas más largas", ""]
        lineas += [f"- **{com}** ({banco}) — {n} locales"
                   for n, com, banco in cadenones if n > 1]

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

    descuentos, precisiones, cadenas = ubicar(descuentos)
    con_pin = sum(n for p, n in precisiones.items() if p != "sin_ubicar")
    log.info("%d con pin en el mapa (%d exactos) · %d solo en la lista",
             con_pin, precisiones.get("fuente", 0) + precisiones.get("calle", 0)
             + precisiones.get("correccion", 0),
             precisiones.get("sin_ubicar", 0))

    # Las sucursales se juntan de vuelta en su convenio: una fila por oferta
    # con su lista de locales adentro. Es lo que se publica.
    from loica.descuentos.cadenas import agrupar
    ofertas = agrupar(descuentos)
    log.info("%d convenios en %d locales", len(ofertas),
             sum(len(o["locales"]) for o in ofertas))

    salida = escribir_json(ofertas, estadisticas)
    informe = escribir_informe(ofertas, estadisticas, duracion, cadenas)
    guardar_estado(bancos, estadisticas, duracion)
    log.info("JSON:    %s", salida.relative_to(RAIZ))
    log.info("Informe: %s", informe.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
