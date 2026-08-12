#!/usr/bin/env python3
"""Corrida diaria del pipeline de eventos.

Recorre todas las fuentes activas, guarda lo nuevo como BORRADOR y deja un
informe en Markdown para que el curador revise y publique.

Uso:
    python3 run_diario.py                 # corrida normal
    python3 run_diario.py --fuente gam    # una sola fuente (para depurar)
    python3 run_diario.py --sin-cache     # ignora la caché local
    python3 run_diario.py --probar        # no guarda nada, solo muestra

Este script no llama a ningún modelo de lenguaje: es Python puro y no consume
tokens. Puede correr todos los días sin costo.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from loica.agrupar import colapsar_multidia
from loica.almacen import Almacen
from loica.filtros import motivo_de_descarte
from loica.fuentes import ADAPTADORES
from loica.red import ClienteEducado

RAIZ = Path(__file__).resolve().parent
RUTA_CONFIG = RAIZ / "config" / "fuentes.yaml"
DIR_INFORMES = RAIZ / "informes"
DIR_LOGS = RAIZ / "datos" / "logs"


def configurar_logs(verboso: bool) -> None:
    DIR_LOGS.mkdir(parents=True, exist_ok=True)
    formato = "%(asctime)s  %(levelname)-7s %(name)-16s %(message)s"
    logging.basicConfig(
        level=logging.DEBUG if verboso else logging.INFO,
        format=formato,
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(DIR_LOGS / f"{datetime.now():%Y-%m}.log", encoding="utf-8"),
        ],
    )


def cargar_fuentes(solo: str | None = None) -> list[dict]:
    with open(RUTA_CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    fuentes = [f for f in config.get("fuentes", []) if f.get("activa", True)]
    if solo:
        fuentes = [f for f in fuentes if f["id"] == solo]
        if not fuentes:
            raise SystemExit(f"No existe una fuente activa con id '{solo}'")
    return fuentes


def escribir_informe(almacen: Almacen, estadisticas: list[dict], duracion: float) -> Path:
    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    hoy = datetime.now()
    ruta = DIR_INFORMES / f"{hoy:%Y-%m-%d}_corrida.md"

    nuevos = almacen.nuevos_de_hoy()
    resumen = almacen.resumen()

    lineas = [
        f"# Corrida del {hoy:%d-%m-%Y %H:%M}",
        "",
        f"- Duración: {duracion:.0f} s",
        f"- Eventos nuevos para revisar: **{len(nuevos)}**",
        f"- En cartera vigente: {resumen.get('vigentes') or 0} "
        f"({resumen.get('gratis') or 0} gratis)",
        f"- Pendientes de curaduría: {resumen.get('borradores') or 0}",
        "",
        "## Por fuente",
        "",
        "| Fuente | Encontrados | Nuevos | Actualizados | Descartados | Estado |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for e in estadisticas:
        estado = "error" if e["error"] else "ok"
        lineas.append(
            f"| {e['fuente']} | {e['encontrados']} | {e['nuevos']} | "
            f"{e['actualizados']} | {e['descartados']} | {estado} |"
        )

    if any(e["error"] for e in estadisticas):
        lineas += ["", "### Errores", ""]
        for e in estadisticas:
            if e["error"]:
                lineas.append(f"- **{e['fuente']}**: {e['error']}")

    # Salud de las fuentes: una fuente que responde bien pero no aporta ningún
    # evento futuro está viva técnicamente y muerta editorialmente. Conviene
    # saberlo antes de confiar en ella.
    sospechosas = []
    for e in estadisticas:
        if e["error"] or e["encontrados"] == 0:
            continue
        vigentes = almacen.con.execute(
            "SELECT COUNT(*) FROM eventos WHERE fuente_nombre = ? AND inicio >= date('now')",
            (e["fuente"],),
        ).fetchone()[0]
        if vigentes == 0:
            sospechosas.append(e["fuente"])

    if sospechosas:
        lineas += [
            "", "### Fuentes a revisar", "",
            "Respondieron bien pero no tienen **ningún evento futuro**: puede que "
            "su agenda esté abandonada o que cambiaron el formato.", "",
        ]
        lineas += [f"- {nombre}" for nombre in sospechosas]

    lineas += ["", "## Eventos nuevos para revisar", ""]
    if not nuevos:
        lineas.append("_Ninguno hoy._")
    else:
        comuna_actual = None
        for fila in nuevos:
            if fila["comuna"] != comuna_actual:
                comuna_actual = fila["comuna"]
                lineas += ["", f"### {comuna_actual or 'Sin comuna'}", ""]
            fecha = (fila["inicio"] or "")[:16].replace("T", " ")
            precio = "GRATIS" if fila["es_gratis"] else (
                f"${fila['precio_clp']:,}".replace(",", ".") if fila["precio_clp"] else "s/i"
            )
            lineas.append(
                f"- **{fila['titulo']}** — {fecha} · {precio} · "
                f"{fila['lugar_nombre']} · [fuente]({fila['fuente_url']}) "
                f"`{fila['fuente_nombre']}`"
            )

    lineas += [
        "",
        "---",
        "",
        "Todo lo de arriba está en estado **borrador**: no se publica nada sin "
        "que una persona lo revise (regla del proyecto).",
        "",
        "Para publicar un evento revisado:",
        "",
        "```sql",
        "UPDATE eventos SET estado='publicado' WHERE hash_dedup='<hash>';",
        "```",
    ]

    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return ruta


def main() -> int:
    parser = argparse.ArgumentParser(description="Corrida diaria del pipeline de eventos")
    parser.add_argument("--fuente", help="correr solo esta fuente (por id)")
    parser.add_argument("--sin-cache", action="store_true", help="ignorar la caché local")
    parser.add_argument("--probar", action="store_true", help="no guardar, solo mostrar")
    parser.add_argument("-v", "--verboso", action="store_true")
    args = parser.parse_args()

    configurar_logs(args.verboso)
    log = logging.getLogger("loica")
    inicio = time.time()

    fuentes = cargar_fuentes(args.fuente)
    log.info("Corriendo %d fuentes%s", len(fuentes), " (modo prueba)" if args.probar else "")

    almacen = None if args.probar else Almacen()
    estadisticas: list[dict] = []

    for fuente in fuentes:
        t0 = time.time()
        nombre = fuente["nombre"]
        adaptador = ADAPTADORES.get(fuente["tipo_adaptador"])
        conteo = {"fuente": nombre, "encontrados": 0, "nuevos": 0,
                  "actualizados": 0, "descartados": 0, "error": None}

        if adaptador is None:
            conteo["error"] = f"tipo_adaptador desconocido: {fuente['tipo_adaptador']}"
            estadisticas.append(conteo)
            log.error("%s: %s", nombre, conteo["error"])
            continue

        try:
            cliente = ClienteEducado(
                crawl_delay_seg=float(fuente.get("crawl_delay_seg", 2)),
                usar_cache=not args.sin_cache,
            )
            eventos = adaptador(fuente, cliente)
            conteo["encontrados"] = len(eventos)
            # Una exposición de un mes llega como 30 entradas iguales: se unen.
            # Los cines son la excepción: cada función es el dato que importa,
            # y fusionar la del jueves con la del domingo borra los horarios.
            if fuente.get("colapsar", True):
                eventos = colapsar_multidia(eventos)

            # Las ticketeras nacionales traen eventos de todo Chile. Sin comuna
            # de la Región Metropolitana no se puede afirmar que sean de
            # Santiago, y esta app es de Santiago.
            exige_comuna = bool(fuente.get("requiere_comuna"))

            for evento in eventos:
                valido, motivo = evento.es_valido()
                if valido and exige_comuna and not evento.comuna:
                    valido, motivo = False, "sin comuna de Santiago"
                # Las municipalidades publican talleres y ferias mezclados con
                # licitaciones y cuentas públicas: el filtro por palabras es lo
                # que hace usable esa fuente sin un adaptador por comuna.
                if valido:
                    descarte = motivo_de_descarte(evento, fuente)
                    if descarte:
                        valido, motivo = False, descarte
                if not valido:
                    conteo["descartados"] += 1
                    log.debug("descartado (%s): %s", motivo, evento.titulo[:60])
                    continue

                if args.probar:
                    cuando = f"{evento.inicio:%d-%m-%Y %H:%M}" if evento.inicio else "SIN FECHA  "
                    print(f"  · {cuando} | {evento.titulo[:55]:57} | "
                          f"{'GRATIS' if evento.es_gratis else evento.precio_texto or 's/i'}")
                    conteo["nuevos"] += 1
                    continue

                resultado = almacen.guardar(evento)
                conteo["nuevos" if resultado == "nuevo" else "actualizados"] += 1

        except Exception as e:  # una fuente caída no puede tumbar la corrida
            conteo["error"] = f"{type(e).__name__}: {e}"
            log.exception("%s falló", nombre)

        duracion = time.time() - t0
        estadisticas.append(conteo)
        if almacen:
            almacen.registrar_corrida(nombre, conteo["encontrados"], conteo["nuevos"],
                                      conteo["actualizados"], conteo["descartados"],
                                      conteo["error"], duracion)
        log.info("%s → %d encontrados, %d nuevos, %d actualizados, %d descartados (%.1fs)",
                 nombre, conteo["encontrados"], conteo["nuevos"],
                 conteo["actualizados"], conteo["descartados"], duracion)

    total = time.time() - inicio

    if almacen:
        caducados = almacen.caducar_pasados()
        if caducados:
            log.info("Marcados como caducados: %d eventos pasados", caducados)
        ruta = escribir_informe(almacen, estadisticas, total)
        log.info("Informe: %s", ruta)
        almacen.cerrar()

    nuevos_total = sum(e["nuevos"] for e in estadisticas)
    con_error = [e["fuente"] for e in estadisticas if e["error"]]
    log.info("Listo en %.0fs — %d eventos nuevos%s", total, nuevos_total,
             f" · fuentes con error: {', '.join(con_error)}" if con_error else "")

    return 1 if len(con_error) == len(estadisticas) else 0


if __name__ == "__main__":
    sys.exit(main())
