#!/usr/bin/env python3
"""Revisión del estado de extracción: qué está bien, qué hay que corregir.

    python3 revisar_extraccion.py

Corre después del export y produce dos cosas:

1. Un informe en `informes/AAAA-MM-DD_revision.md` con la foto de calidad de
   la base consolidada: cuántos eventos tienen ubicación exacta, cuántos caen
   al centro de comuna, cuántos quedaron en "otros", qué fuentes están
   degradadas y cómo vienen los descuentos.

2. Las COLAS DE CORRECCIÓN en `datos/revision/`: archivos YAML con esqueleto
   listo para completar y copiar a `config/correcciones/`. Ahí está el ciclo
   que pide el proceso: cada corrección hecha una vez queda en la memoria
   (config/correcciones/) y arregla sola todas las extracciones futuras.

Este paso NO bloquea la publicación (eso lo hace verificar_web.py): es el
insumo de trabajo para la persona —o la sesión de Claude— que cura el dato.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
RUTA_EVENTOS = RAIZ / "web" / "eventos.json"
RUTA_DESCUENTOS = RAIZ / "web" / "descuentos.json"
RUTA_DB = RAIZ / "datos" / "eventos.db"
DIR_INFORMES = RAIZ / "informes"
DIR_PENDIENTES = RAIZ / "datos" / "revision"

# Cuántas entradas mostrar en cada cola. Las colas son para trabajarlas, no
# para admirarlas: más de esto y nadie las abre.
TOPE_COLA = 30


def _cargar_json(ruta: Path) -> dict | None:
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def cola_lugares(eventos: list[dict]) -> list[dict]:
    """Los lugares que concentran más eventos sin ubicación exacta.

    Se ordena por cuántos eventos arregla cada corrección: anotar las
    coordenadas del lugar número uno puede mover cientos de pines de una vez.
    """
    grupos: dict[tuple, dict] = {}
    for e in eventos:
        if e.get("precision") not in ("comuna", "sin_ubicar"):
            continue
        clave = (e.get("lugar") or "", e.get("comuna") or "")
        g = grupos.setdefault(clave, {"lugar": clave[0], "comuna": clave[1],
                                      "eventos": 0, "direccion": ""})
        g["eventos"] += 1
        if not g["direccion"] and e.get("direccion"):
            g["direccion"] = e["direccion"]
    return sorted(grupos.values(), key=lambda g: -g["eventos"])


def cola_categorias(eventos: list[dict]) -> list[dict]:
    """Eventos que quedaron en 'otros': el clasificador no supo qué son."""
    pendientes = [e for e in eventos if e.get("categoria") == "otros"]
    pendientes.sort(key=lambda e: e.get("inicio") or "9999")
    return pendientes


def cola_restoranes(descuentos: list[dict]) -> tuple[list[dict], list[dict]]:
    """Convenios sin ubicación exacta y sin tipo de cocina.

    "Sin ubicar" quiere decir otra cosa desde que cada fila es un convenio con
    sus sucursales adentro. Una oferta con locales prestados —de otro banco que
    sí publicó la calle, o del índice de OSM— ya está en el mapa: mandarla a la
    cola sería pedir que alguien busque a mano una dirección que ya se sabe.
    Falta ubicar la oferta que no tiene NINGÚN local, y la que los tiene todos
    en el centro de la comuna.
    """
    sin_pin: dict[str, dict] = {}
    sin_cocina: dict[str, dict] = {}
    for d in descuentos:
        nombre = d.get("comercio") or ""
        locales = d.get("locales") or []
        if not locales or all(l.get("precision") == "comuna" for l in locales):
            g = sin_pin.setdefault(nombre, {"comercio": nombre, "n": 0,
                                            "comuna": "", "direccion": "",
                                            "bancos": set()})
            g["n"] += 1
            g["bancos"].add(d.get("banco") or "")
            # La pista sale del primer local que traiga algo. Cuando la oferta
            # cayó al centro de la comuna es porque el banco dijo una dirección
            # que el geocodificador no supo resolver, y esa dirección a medias
            # es por donde empieza la búsqueda a mano.
            for local in locales:
                g["comuna"] = g["comuna"] or (local.get("comuna") or "")
                g["direccion"] = g["direccion"] or (local.get("direccion") or "")
        if not d.get("cocina"):
            g = sin_cocina.setdefault(nombre, {"comercio": nombre, "n": 0,
                                               "categoria": d.get("categoria") or ""})
            g["n"] += 1
    orden_pin = sorted(sin_pin.values(), key=lambda g: -g["n"])
    orden_cocina = sorted(sin_cocina.values(), key=lambda g: -g["n"])
    return orden_pin, orden_cocina


def nombres_activos() -> set[str] | None:
    """Nombres de las fuentes que hoy están activas en la configuración.

    Devuelve None si el archivo no se puede leer: ante la duda se informa de
    más y no de menos.
    """
    try:
        import yaml
        with open(RAIZ / "config" / "fuentes.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return {x["nombre"] for x in config.get("fuentes", []) if x.get("activa", True)}
    except Exception:
        return None


def fuentes_degradadas(con: sqlite3.Connection) -> list[dict]:
    """Fuentes ACTIVAS cuyas últimas 3 corridas vienen en error o en cero.

    Una fuente que respondió bien durante meses y lleva tres días en cero no
    es "una fuente tranquila": o el sitio cambió y el adaptador quedó ciego,
    o de verdad no hay agenda. Las dos cosas se miran, no se adivinan.

    Las apagadas no cuentan: sus corridas viejas quedan para siempre en la
    tabla, así que sin este filtro una fuente que uno apagó justamente porque
    no servía seguía apareciendo en la lista todos los días, al lado de las
    que sí se rompieron, y la lista dejaba de leerse. Ticketmaster fue el caso.
    """
    activas = nombres_activos()
    filas = con.execute(
        """SELECT fuente, encontrados, error, momento FROM corridas
           ORDER BY momento DESC""").fetchall()
    if activas is not None:
        filas = [f for f in filas if f["fuente"] in activas]
    ultimas: dict[str, list] = defaultdict(list)
    for f in filas:
        if len(ultimas[f["fuente"]]) < 3:
            ultimas[f["fuente"]].append(f)

    degradadas = []
    for fuente, corridas in ultimas.items():
        if len(corridas) < 3:
            continue
        malas = all((c["error"] or (c["encontrados"] or 0) == 0) for c in corridas)
        if malas:
            degradadas.append({
                "fuente": fuente,
                "ultimo_error": next((c["error"] for c in corridas if c["error"]), ""),
                "desde": corridas[-1]["momento"][:10],
            })
    return sorted(degradadas, key=lambda d: d["fuente"])


def sin_fecha(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(
        """SELECT hash_dedup, titulo, fuente_nombre, fuente_url FROM eventos
           WHERE estado = 'revisar_fecha' ORDER BY fecha_extraccion DESC""").fetchall()


def escribir_pendientes(lugares, otros, rest_pin, rest_cocina) -> None:
    """Esqueletos YAML listos para completar y copiar a config/correcciones/.

    Se escriben a mano y no con yaml.dump a propósito: el valor de estos
    archivos son los comentarios (contexto de cada entrada) y el orden por
    impacto, y un dump alfabético pierde las dos cosas.
    """
    DIR_PENDIENTES.mkdir(parents=True, exist_ok=True)
    hoy = datetime.now().strftime("%Y-%m-%d")

    lineas = [
        f"# Cola de LUGARES sin ubicación exacta — revisión del {hoy}.",
        "# Completa lat/lon (Google Maps: click derecho → copiar coordenadas),",
        "# borra las entradas que no puedas verificar, y pega las listas en",
        "# config/correcciones/lugares.yaml bajo la clave `lugares:`.",
        "# Ordenadas por impacto: la primera arregla más eventos que ninguna.",
        "",
        "lugares:",
    ]
    for g in lugares[:TOPE_COLA]:
        lineas.append(f"  # {g['eventos']} eventos sin pin exacto")
        lineas.append(f"  {g['lugar']}:")
        lineas.append(f"    direccion: {g['direccion'] or '# COMPLETAR'}")
        lineas.append(f"    comuna: {g['comuna'] or '# COMPLETAR'}")
        lineas.append("    lat: # COMPLETAR")
        lineas.append("    lon: # COMPLETAR")
        lineas.append(f"    nota: verificada el {hoy} por # COMPLETAR")
        lineas.append("")
    (DIR_PENDIENTES / "pendientes_lugares.yaml").write_text(
        "\n".join(lineas), encoding="utf-8")

    lineas = [
        f"# Cola de EVENTOS en categoría 'otros' — revisión del {hoy}.",
        "# Ponles la categoría que corresponda (idiomas, familia, feria, deporte,",
        "# fiesta, cine, teatro, musica, arte, clases, aire_libre, charla) o",
        "# descartar: true si no son un panorama, y pégalos en",
        "# config/correcciones/eventos.yaml bajo `eventos:`.",
        "# OJO: si el error se repite (misma palabra, mismo tipo de evento), el",
        "# arreglo de verdad va en loica/clasificar.py, no acá.",
        "",
        "eventos:",
    ]
    for e in otros[:TOPE_COLA]:
        lineas.append(f"  # {e['titulo'][:70]} | {e.get('fuente', '')[:30]} | {(e.get('inicio') or '')[:10]}")
        lineas.append(f"  {e['id']}:")
        lineas.append("    categoria: # COMPLETAR")
        lineas.append(f"    nota: revisado el {hoy}")
        lineas.append("")
    (DIR_PENDIENTES / "pendientes_eventos.yaml").write_text(
        "\n".join(lineas), encoding="utf-8")

    lineas = [
        f"# Cola de RESTORANES con descuento — revisión del {hoy}.",
        "# Arriba los sin ubicación (completar direccion/comuna/lat/lon), abajo",
        "# los sin tipo de cocina (completar cocina). Pegar en",
        "# config/correcciones/restoranes.yaml bajo `restoranes:`.",
        "# El match es EXACTO por nombre: 'Sushi Home' no corrige a",
        "# 'Sushi Home Ñuñoa'.",
        "",
        "restoranes:",
    ]
    for g in rest_pin[:TOPE_COLA]:
        bancos = ", ".join(sorted(b for b in g["bancos"] if b))
        lineas.append(f"  # {g['n']} descuentos sin pin exacto ({bancos})")
        lineas.append(f"  {g['comercio']}:")
        lineas.append(f"    direccion: {g['direccion'] or '# COMPLETAR'}")
        lineas.append(f"    comuna: {g['comuna'] or '# COMPLETAR'}")
        lineas.append("    lat: # COMPLETAR")
        lineas.append("    lon: # COMPLETAR")
        lineas.append(f"    nota: verificada el {hoy} por # COMPLETAR")
        lineas.append("")
    lineas.append("  # ---- sin tipo de cocina ----")
    for g in rest_cocina[:TOPE_COLA]:
        lineas.append(f"  {g['comercio']}:")
        lineas.append("    cocina: # COMPLETAR (japonesa, peruana, italiana, parrilla, cafe, bar, chilena...)")
        lineas.append("")
    (DIR_PENDIENTES / "pendientes_restoranes.yaml").write_text(
        "\n".join(lineas), encoding="utf-8")


def main() -> int:
    hoy = datetime.now()
    datos_ev = _cargar_json(RUTA_EVENTOS)
    datos_dc = _cargar_json(RUTA_DESCUENTOS)

    if not datos_ev:
        print("No hay web/eventos.json que revisar. Corre exportar_web.py primero.")
        return 1

    eventos = datos_ev.get("eventos", [])
    descuentos = (datos_dc or {}).get("descuentos", [])

    precision = Counter(e.get("precision") or "sin_ubicar" for e in eventos)
    categorias = Counter(e.get("categoria") for e in eventos)
    exactos = sum(precision[p] for p in ("recinto", "fuente", "calle", "correccion"))

    lugares = cola_lugares(eventos)
    otros = cola_categorias(eventos)
    rest_pin, rest_cocina = cola_restoranes(descuentos)

    # sqlite3.connect CREA el archivo si no existe: apuntar a una base
    # ausente dejaría un eventos.db vacío de 0 bytes que la corrida siguiente
    # tomaría por buena. Mejor revisar sin esta parte.
    degradadas: list[dict] = []
    sinfecha: list = []
    if RUTA_DB.exists():
        try:
            con = sqlite3.connect(f"file:{RUTA_DB}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            degradadas = fuentes_degradadas(con)
            sinfecha = sin_fecha(con)
            con.close()
        except sqlite3.Error as e:
            print(f"  (no pude leer la base: {e} — el resto de la revisión sigue)")
    else:
        print(f"  (no existe {RUTA_DB.name}: la revisión va sin la parte de la base)")

    escribir_pendientes(lugares, otros, rest_pin, rest_cocina)

    # ---------- el informe ----------
    total = len(eventos)
    pct = lambda n: f"{n * 100 // max(total, 1)}%"
    mes = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre")[hoy.month - 1]

    lineas = [
        f"# Revisión de la extracción — {hoy.day} de {mes} de {hoy.year}",
        "",
        f"**{total} eventos** en el consolidado y **{len(descuentos)} descuentos**.",
        "",
        "## Georreferenciación",
        "",
        "| Precisión | Eventos | |",
        "|---|---:|---|",
        f"| Exacta (recinto/fuente/calle/corrección) | {exactos} | {pct(exactos)} |",
        f"| Centro de comuna (aproximada) | {precision.get('comuna', 0)} | {pct(precision.get('comuna', 0))} |",
        f"| Sin pin | {precision.get('sin_ubicar', 0)} | {pct(precision.get('sin_ubicar', 0))} |",
        "",
        f"Cola de lugares por corregir: **{len(lugares)}** "
        f"(los {min(TOPE_COLA, len(lugares))} de más impacto quedaron en "
        f"`datos/revision/pendientes_lugares.yaml`). Las direcciones que se "
        f"investiguen se anotan con su URL en "
        f"`datos/revision/investigacion_lugares_AAAA-MM-DD.yaml` y pasan por el "
        f"doble check contra OpenStreetMap: `python3 scripts/verificar_lugares.py`.",
        "",
        "## Categorías",
        "",
        "| Categoría | Eventos |", "|---|---:|",
    ]
    lineas += [f"| {c} | {n} |" for c, n in categorias.most_common()]
    lineas += [
        "",
        f"En 'otros' quedaron **{categorias.get('otros', 0)}** ({pct(categorias.get('otros', 0))}): "
        "la cola está en `datos/revision/pendientes_eventos.yaml`. Si un error se "
        "repite, la regla va en `config/correcciones/categorias.yaml` (la memoria "
        "del clasificador) y si pide lógica, en `loica/clasificar.py`. Para saber "
        "si la regla nueva rompió algo que ya estaba bien: "
        "`python3 scripts/auditar_categorias.py --comparar`.",
        "",
        "## Sin fecha (estado revisar_fecha)",
        "",
        f"{len(sinfecha)} eventos descubiertos sin fecha legible. Los descubrió "
        "la extracción, falta que alguien abra la ficha y complete el dato:",
        "",
    ]
    lineas += [f"- {f['titulo'][:60]} — {f['fuente_nombre']} — {f['fuente_url']}"
               for f in sinfecha[:15]]
    if len(sinfecha) > 15:
        lineas.append(f"- … y {len(sinfecha) - 15} más")

    if degradadas:
        lineas += ["", "## Fuentes degradadas (3 corridas seguidas en error o en cero)", ""]
        lineas += [f"- **{d['fuente']}** — desde {d['desde']}"
                   + (f" — `{d['ultimo_error'][:80]}`" if d["ultimo_error"] else "")
                   for d in degradadas]

    if descuentos:
        # La precisión es de cada sucursal y no del convenio: Dunkin' es una
        # sola oferta con veintiún pines, y contarla una vez escondería veinte.
        locales = [l for d in descuentos for l in (d.get("locales") or [])]
        dc_precision = Counter(l.get("precision") or "sin_ubicar" for l in locales)
        dc_exactos = sum(dc_precision[p] for p in ("fuente", "calle", "correccion"))
        prestados = sum(1 for l in locales if l.get("origen"))
        sin_local = sum(1 for d in descuentos if not (d.get("locales") or []))
        sin_cocina_n = sum(1 for d in descuentos if not d.get("cocina"))
        lineas += [
            "", "## Descuentos", "",
            f"- {len(descuentos)} convenios con {len(locales)} locales en el mapa",
            f"- Con pin exacto: {dc_exactos} de {len(locales)}",
            f"- Al centro de comuna: {dc_precision.get('comuna', 0)}",
            f"- Sin pin: {dc_precision.get('sin_ubicar', 0)}",
            f"- Sucursales prestadas (las dijo otro banco o OSM, no el que "
            f"publica el convenio): {prestados}",
            f"- Convenios sin ningún local, que salen en la lista pero no en el "
            f"mapa: {sin_local}",
            f"- Sin tipo de cocina: {sin_cocina_n}",
            "",
            f"Por ubicar a mano quedan **{len(rest_pin)}** comercios: los que no "
            "tienen ningún local y los que caen todos al centro de su comuna. "
            "Lo prestado ya está ubicado y no entra a la cola. Cola en "
            "`datos/revision/pendientes_restoranes.yaml`.",
        ]

    lineas += [
        "", "## Cómo se corrige", "",
        "1. Abrir la cola en `datos/revision/pendientes_*.yaml`.",
        "2. Completar los datos verificados, anotando de dónde salió cada uno.",
        "3. Pasarlos por el doble check (`scripts/verificar_lugares.py` para "
        "direcciones, `scripts/auditar_categorias.py --comparar` para categorías): "
        "una corrección que rompe otra cosa no es una corrección.",
        "4. Pegar las entradas en `config/correcciones/*.yaml` y comitear.",
        "5. La próxima corrida las aplica sola — la memoria no se olvida.",
    ]

    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    ruta = DIR_INFORMES / f"{hoy:%Y-%m-%d}_revision.md"
    ruta.write_text("\n".join(lineas), encoding="utf-8")

    print(f"Revisión lista: {ruta.relative_to(RAIZ)}")
    print(f"  Ubicación exacta: {exactos}/{total} ({pct(exactos)}) · "
          f"comuna: {precision.get('comuna', 0)} · sin pin: {precision.get('sin_ubicar', 0)}")
    print(f"  En 'otros': {categorias.get('otros', 0)} · sin fecha: {len(sinfecha)} · "
          f"fuentes degradadas: {len(degradadas)}")
    print(f"  Colas de corrección en {DIR_PENDIENTES.relative_to(RAIZ)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
