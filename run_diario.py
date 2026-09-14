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
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from statistics import median
from urllib.parse import urlparse

import yaml

from loica.agrupar import colapsar_multidia
from loica.almacen import SQL_VIGENTE, Almacen
from loica.filtros import motivo_de_descarte
from loica.fuentes import ADAPTADORES
from loica.red import ClienteEducado
from loica import asistida

RAIZ = Path(__file__).resolve().parent
RUTA_CONFIG = RAIZ / "config" / "fuentes.yaml"
DIR_INFORMES = RAIZ / "informes"
DIR_LOGS = RAIZ / "datos" / "logs"
RUTA_HISTORIAL_FUENTES = RAIZ / "datos" / "historial_fuentes.json"
MAX_HISTORIAL_FUENTES = 60


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
        "| Fuente | Encontrados | Nuevos | Actualizados | Descartados | Red | Estado |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for e in estadisticas:
        estado = "error" if e["error"] else ("alerta: " + e["alertas"][0]
                                                if e.get("alertas") else "ok")
        lineas.append(
            f"| {e['fuente']} | {e['encontrados']} | {e['nuevos']} | "
            f"{e['actualizados']} | {e['descartados']} | {_resumen_red(e.get('red'))} | {estado} |"
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
            "SELECT COUNT(*) FROM eventos WHERE fuente_nombre = ? AND " + SQL_VIGENTE,
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


def _resumen_red(red: dict | None) -> str:
    """Una celda legible del diagnóstico HTTP de una fuente."""
    if not red:
        return "—"
    codigos = red.get("codigos") or {}
    partes = [f"{codigo}×{n}" for codigo, n in codigos.items()]
    if red.get("robots"):
        partes.append(f"robots×{red['robots']}")
    if red.get("errores"):
        partes.append(f"red×{red['errores']}")
    return ", ".join(partes) or "—"


def _dominio(fuente: dict) -> str:
    """Dominio de una fuente para no correr dos extractores del mismo host a la vez."""
    url = fuente.get("url_base") or fuente.get("url_agenda") or fuente["id"]
    return urlparse(url).netloc or fuente["id"]


def _extraer_fuente(fuente: dict, sin_cache: bool) -> dict:
    """Parte de red de una fuente; no toca SQLite y por eso puede ir en paralelo."""
    t0 = time.time()
    conteo = {"fuente": fuente["nombre"], "encontrados": 0, "nuevos": 0,
              "actualizados": 0, "descartados": 0, "error": None, "alertas": []}
    adaptador = ADAPTADORES.get(fuente["tipo_adaptador"])
    eventos = []
    cliente = None
    if adaptador is None:
        conteo["error"] = f"tipo_adaptador desconocido: {fuente['tipo_adaptador']}"
        return {"fuente": fuente, "conteo": conteo, "eventos": eventos,
                "duracion": time.time() - t0}
    try:
        cliente = ClienteEducado(crawl_delay_seg=float(fuente.get("crawl_delay_seg", 2)),
                                 usar_cache=not sin_cache)
        eventos = adaptador(fuente, cliente)
        conteo["encontrados"] = len(eventos)
        if fuente.get("tipo_adaptador") == "manual":
            pasada = asistida.ultima_pasada(Path(fuente["carpeta"])
                                             if fuente.get("carpeta") else None)
            if pasada and not asistida.manifest(Path(fuente["carpeta"])
                                                 if fuente.get("carpeta") else None):
                conteo["alertas"].append("pasada asistida sin manifest")
            if pasada and fuente.get("max_edad_dias") is not None:
                edad = (datetime.now().date() - pasada[0]).days
                if edad > int(fuente["max_edad_dias"]):
                    conteo["alertas"].append(
                        f"pasada asistida vencida ({edad} días; máximo {fuente['max_edad_dias']})")
    except Exception as e:  # una fuente caída no puede tumbar la corrida
        conteo["error"] = f"{type(e).__name__}: {e}"
        logging.getLogger("loica").exception("%s falló", fuente["nombre"])
    conteo["red"] = cliente.resumen_red() if cliente else {}
    return {"fuente": fuente, "conteo": conteo, "eventos": eventos,
            "duracion": time.time() - t0}


def _extraer_en_paralelo(fuentes: list[dict], sin_cache: bool, concurrencia: int) -> list[dict]:
    """Extrae hosts distintos en paralelo, serializando siempre un mismo dominio.

    El crawl-delay vive en ClienteEducado y sigue aplicando a cada petición.
    Agrupar antes de enviar al pool evita que dos fuentes del mismo host se
    salten ese intervalo por una carrera entre hilos.
    """
    grupos: dict[str, list[tuple[int, dict]]] = {}
    for indice, fuente in enumerate(fuentes):
        grupos.setdefault(_dominio(fuente), []).append((indice, fuente))

    resultados: list[dict | None] = [None] * len(fuentes)

    def correr_grupo(items: list[tuple[int, dict]]) -> list[tuple[int, dict]]:
        return [(indice, _extraer_fuente(fuente, sin_cache)) for indice, fuente in items]

    trabajadores = min(max(1, concurrencia), len(grupos))
    if trabajadores == 1:
        for items in grupos.values():
            for indice, resultado in correr_grupo(items):
                resultados[indice] = resultado
    else:
        with ThreadPoolExecutor(max_workers=trabajadores, thread_name_prefix="loica") as pool:
            futuros = [pool.submit(correr_grupo, items) for items in grupos.values()]
            for futuro in as_completed(futuros):
                for indice, resultado in futuro.result():
                    resultados[indice] = resultado
    return [r for r in resultados if r is not None]


def _cargar_historial_fuentes() -> dict[str, list[dict]]:
    try:
        datos = json.loads(RUTA_HISTORIAL_FUENTES.read_text(encoding="utf-8"))
        fuentes = datos.get("fuentes", {})
        return fuentes if isinstance(fuentes, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _anotar_salud(estadisticas: list[dict]) -> None:
    """Compara cada fuente con su propia línea base y guarda el último tramo.

    La base SQLite de Actions nace de cero todos los días, así que esta memoria
    versionada es la que permite detectar un parser que pasó de 40 a 0 aunque
    la corrida actual técnicamente no haya lanzado una excepción.
    """
    historial = _cargar_historial_fuentes()
    ahora = datetime.now().isoformat(timespec="seconds")
    for e in estadisticas:
        previas = historial.get(e["fuente"], [])[-7:]
        hallazgos = [p.get("encontrados", 0) for p in previas
                     if not p.get("error") and p.get("encontrados", 0) > 0]
        if e["error"]:
            e["alertas"].append("error de extracción")
        red = e.get("red") or {}
        codigos = red.get("codigos") or {}
        if e["encontrados"] == 0 and (codigos.get("403") or codigos.get("429")):
            e["alertas"].append("acceso bloqueado (HTTP 403/429)")
        if e["encontrados"] == 0 and red.get("robots"):
            e["alertas"].append("robots.txt impidió la extracción")
        if red.get("cortadas"):
            e["alertas"].append(
                f"dominio omitido tras fallos ({red['cortadas']} peticiones evitadas)")
        elif len(hallazgos) >= 3:
            base = median(hallazgos)
            if e["encontrados"] == 0 and base >= 5:
                e["alertas"].append(f"cero inesperado (mediana reciente: {base:.0f})")
            elif e["encontrados"] < base * 0.2:
                e["alertas"].append(f"volumen -80% (mediana reciente: {base:.0f})")
        if e["duracion_seg"] > 300:
            e["alertas"].append(f"lenta ({e['duracion_seg'] / 60:.1f} min)")

        fila = {"momento": ahora, "encontrados": e["encontrados"],
                "nuevos": e["nuevos"], "actualizados": e["actualizados"],
                "descartados": e["descartados"], "error": e["error"],
                "duracion_seg": e["duracion_seg"], "red": e.get("red", {}),
                "alertas": e["alertas"]}
        historial.setdefault(e["fuente"], []).append(fila)
        historial[e["fuente"]] = historial[e["fuente"]][-MAX_HISTORIAL_FUENTES:]

    RUTA_HISTORIAL_FUENTES.write_text(
        json.dumps({"version": 1, "fuentes": historial}, ensure_ascii=False,
                   indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Corrida diaria del pipeline de eventos")
    parser.add_argument("--fuente", help="correr solo esta fuente (por id)")
    parser.add_argument("--sin-cache", action="store_true", help="ignorar la caché local")
    parser.add_argument("--concurrencia", type=int, default=6,
                        help="hosts distintos en paralelo (por defecto: 6)")
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

    for resultado in _extraer_en_paralelo(fuentes, args.sin_cache, args.concurrencia):
        fuente = resultado["fuente"]
        conteo = resultado["conteo"]
        eventos = resultado["eventos"]
        if not conteo["error"]:
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

                estado_guardado = almacen.guardar(evento)
                conteo["nuevos" if estado_guardado == "nuevo" else "actualizados"] += 1

        duracion = resultado["duracion"]
        conteo["duracion_seg"] = round(duracion, 1)
        estadisticas.append(conteo)
        if almacen:
            almacen.registrar_corrida(conteo["fuente"], conteo["encontrados"], conteo["nuevos"],
                                      conteo["actualizados"], conteo["descartados"],
                                      conteo["error"], duracion)
        log.info("%s → %d encontrados, %d nuevos, %d actualizados, %d descartados (%.1fs)",
                 conteo["fuente"], conteo["encontrados"], conteo["nuevos"],
                 conteo["actualizados"], conteo["descartados"], duracion)

    total = time.time() - inicio

    if almacen:
        _anotar_salud(estadisticas)
        for e in estadisticas:
            for alerta in e["alertas"]:
                log.warning("%s: %s", e["fuente"], alerta)
        revividos = almacen.revivir_vigentes()
        if revividos:
            log.info("Rescatados %d eventos que seguían en cartelera y estaban "
                     "caducados por la regla vieja (se medía por inicio, no por fin)",
                     revividos)
        caducados = almacen.caducar_pasados()
        if caducados:
            log.info("Marcados como caducados: %d eventos pasados", caducados)
        ruta = escribir_informe(almacen, estadisticas, total)
        log.info("Informe: %s", ruta)
        # La base es local; lo que viaja en git (y lo que la nube necesita
        # mañana) es esta copia. Se vuelca al final de cada corrida.
        log.info("Estado volcado a %s", almacen.volcar())
        almacen.cerrar()

    nuevos_total = sum(e["nuevos"] for e in estadisticas)
    con_error = [e["fuente"] for e in estadisticas if e["error"]]
    log.info("Listo en %.0fs — %d eventos nuevos%s", total, nuevos_total,
             f" · fuentes con error: {', '.join(con_error)}" if con_error else "")

    return 1 if len(con_error) == len(estadisticas) else 0


if __name__ == "__main__":
    sys.exit(main())
