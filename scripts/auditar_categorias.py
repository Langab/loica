#!/usr/bin/env python3
"""Mide el clasificador contra la auditoría hecha a mano.

    python3 scripts/auditar_categorias.py            # cómo está hoy
    python3 scripts/auditar_categorias.py --comparar # con memoria contra sin memoria
    python3 scripts/auditar_categorias.py --errores  # lista lo que sigue mal
    python3 scripts/auditar_categorias.py --pendientes # esqueleto para eventos.yaml

El problema que resuelve: agregar una regla al clasificador o a la memoria
(`config/correcciones/categorias.yaml`) arregla unos eventos y rompe otros, y
contar solo los que arregla esconde los que rompe. Esa lección ya la dejó
escrita la auditoría de comunas del 16-08-2026: *medir el arreglo en las DOS
direcciones antes de publicarlo*.

Acá esa medición existe. `datos/revision/auditoria_categorias_*.tsv` es el
conjunto etiquetado: 597 eventos revisados uno por uno el 22-08-2026 contra el
catastro publicado ese día, cada uno con la categoría que le corresponde y con
qué confianza se pudo determinar. El script clasifica esos mismos eventos con
el código de hoy y compara.

Los veredictos de confianza MEDIA no cuentan como error: son los casos donde
el auditor no pudo confirmar qué era el evento con el título, el lugar y la
descripción. Se listan aparte para que alguien los mire, pero una regla no se
juzga por ellos.

El conjunto envejece: los eventos caducan y salen de la base. Lo que no
envejece son las reglas que se escribieron mirándolo, y por eso el archivo
queda versionado — el día que alguien toque `clasificar.py` puede saber si
rompió algo que ya estaba bien.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from loica.almacen import SQL_VIGENTE  # noqa: E402
from loica.clasificar import clasificar, clasificar_subcategoria  # noqa: E402
from loica.correcciones import MemoriaCategorias  # noqa: E402
from exportar_web import es_panorama  # noqa: E402
import loica.clasificar as clas  # noqa: E402

DIR_REVISION = RAIZ / "datos" / "revision"
RUTA_DB = RAIZ / "datos" / "eventos.db"


def cargar_veredictos() -> dict[str, dict]:
    """Lee todos los .tsv de auditoría de datos/revision/.

    Son varios archivos a propósito (uno por auditoría, con su fecha en el
    nombre): así una revisión nueva se agrega sin tocar la anterior, y si dos
    auditorías opinan del mismo evento gana la más reciente por orden
    alfabético del nombre.
    """
    veredictos: dict[str, dict] = {}
    archivos = sorted(DIR_REVISION.glob("auditoria_categorias_*.tsv"))
    for ruta in archivos:
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if not linea.strip() or linea.lstrip().startswith("#"):
                continue
            partes = linea.split("\t")
            if len(partes) < 2:
                continue
            id_ev, categoria = partes[0].strip(), partes[1].strip()
            subcategoria = partes[2].strip() if len(partes) > 2 else ""
            confianza = partes[3].strip() if len(partes) > 3 else "alta"
            veredictos[id_ev] = {"categoria": categoria,
                                 "subcategoria": subcategoria,
                                 "confianza": confianza, "origen": ruta.name}
    return veredictos


def cargar_eventos(ids: set[str]) -> dict[str, sqlite3.Row]:
    """Los eventos auditados que siguen en la base. Los que caducaron se van
    quedando fuera solos, y eso es normal: el conjunto envejece."""
    if not RUTA_DB.exists():
        print(f"No existe {RUTA_DB.relative_to(RAIZ)}: no hay contra qué medir.")
        return {}
    con = sqlite3.connect(f"file:{RUTA_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    filas = {f["hash_dedup"]: f for f in con.execute("SELECT * FROM eventos")}
    con.close()
    return {i: filas[i] for i in ids if i in filas}


def clasificar_fila(fila) -> tuple[str, str, str]:
    """Lo mismo que hace el export, en el mismo orden.

    Incluye la puerta de "esto no es un panorama" (es_panorama), porque para
    la auditoría "descartar" es una respuesta más: si el pipeline publica un
    abono de temporada, da lo mismo en qué categoría lo puso.
    """
    titulo, descripcion = fila["titulo"], fila["descripcion_corta"] or ""
    panorama, senal = es_panorama(titulo, descripcion)
    if not panorama:
        return "descartar", "", f"descarte: {senal[:28]}"
    categoria, origen = clasificar(titulo, fila["categoria"] or "",
                                   descripcion,
                                   fila["lugar_nombre"] or "",
                                   fila["fuente_nombre"] or "")
    subcategoria, _ = clasificar_subcategoria(
        categoria, titulo, fila["categoria"] or "", descripcion,
        fila["lugar_nombre"] or "", fila["fuente_nombre"] or "")
    return categoria, subcategoria, origen


def medir(eventos: dict, veredictos: dict) -> dict:
    """Compara y devuelve el detalle. `aciertos` cuenta solo confianza alta."""
    aciertos = errores = dudosos_ok = dudosos_no = 0
    detalle_errores, detalle_dudosos, por_origen = [], [], Counter()
    sub_ok = sub_mal = 0
    for id_ev, fila in eventos.items():
        v = veredictos[id_ev]
        categoria, subcategoria, origen = clasificar_fila(fila)
        # El export descarta el evento; para la auditoría "descartar" es una
        # respuesta más y se compara igual que una categoría.
        calza = categoria == v["categoria"]
        if v["confianza"] == "alta":
            if calza:
                aciertos += 1
                por_origen[origen] += 1
            else:
                errores += 1
                detalle_errores.append((id_ev, fila["titulo"], v["categoria"],
                                        categoria, origen, fila["lugar_nombre"] or "",
                                        fila["fuente_nombre"] or ""))
        else:
            (dudosos_ok := dudosos_ok + 1) if calza else (dudosos_no := dudosos_no + 1)
            if not calza:
                detalle_dudosos.append((id_ev, fila["titulo"], v["categoria"],
                                        categoria, origen))
        if calza and v["subcategoria"]:
            if subcategoria == v["subcategoria"]:
                sub_ok += 1
            else:
                sub_mal += 1
    return {"aciertos": aciertos, "errores": errores, "dudosos_ok": dudosos_ok,
            "dudosos_no": dudosos_no, "detalle": detalle_errores,
            "dudosos": detalle_dudosos, "por_origen": por_origen,
            "sub_ok": sub_ok, "sub_mal": sub_mal}


def _pct(n: int, total: int) -> str:
    return f"{n * 100 / max(total, 1):.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparar", action="store_true",
                        help="mide con y sin la memoria de categorias.yaml")
    parser.add_argument("--errores", action="store_true",
                        help="lista los eventos que siguen mal clasificados")
    parser.add_argument("--dudosos", action="store_true",
                        help="lista las diferencias de confianza media")
    parser.add_argument("--pendientes", action="store_true",
                        help="escribe el esqueleto YAML de lo que sigue mal")
    args = parser.parse_args()

    veredictos = cargar_veredictos()
    if not veredictos:
        print("No encontré ningún datos/revision/auditoria_categorias_*.tsv.")
        return 1
    eventos = cargar_eventos(set(veredictos))
    if not eventos:
        print(f"Ninguno de los {len(veredictos)} eventos auditados sigue en la base.")
        return 1

    caducados = len(veredictos) - len(eventos)
    print(f"Auditoría: {len(veredictos)} eventos revisados a mano, "
          f"{len(eventos)} siguen en la base"
          + (f" ({caducados} ya caducaron)" if caducados else ""))

    ahora = medir(eventos, veredictos)
    total_alta = ahora["aciertos"] + ahora["errores"]

    if args.comparar:
        memoria_real = clas.memoria()
        clas.usar_memoria(MemoriaCategorias(Path("/no-existe.yaml")))
        antes = medir(eventos, veredictos)
        clas.usar_memoria(memoria_real)
        t = antes["aciertos"] + antes["errores"]
        print()
        print("                              sin memoria    con memoria")
        print(f"  Aciertos (confianza alta)   {antes['aciertos']:5d} ({_pct(antes['aciertos'], t):>5})"
              f"   {ahora['aciertos']:5d} ({_pct(ahora['aciertos'], total_alta):>5})")
        print(f"  Errores                     {antes['errores']:5d}          "
              f"{ahora['errores']:5d}")
        print(f"  Subcategoría correcta       {antes['sub_ok']:5d}          "
              f"{ahora['sub_ok']:5d}")
        # Lo que importa de verdad: qué se rompió, no solo qué se arregló.
        antes_mal = {e[0] for e in antes["detalle"]}
        ahora_mal = {e[0] for e in ahora["detalle"]}
        arreglados = antes_mal - ahora_mal
        rotos = ahora_mal - antes_mal
        print(f"\n  Arreglados por la memoria: {len(arreglados)}")
        print(f"  ROTOS por la memoria:      {len(rotos)}"
              + ("  ← revisar antes de publicar" if rotos else ""))
        for id_ev in sorted(rotos):
            fila = eventos[id_ev]
            v = veredictos[id_ev]
            cat, _, origen = clasificar_fila(fila)
            print(f"     · {fila['titulo'][:56]:56s} debía ser {v['categoria']:10s} "
                  f"y quedó {cat} ({origen})")
        return 0

    print(f"\n  Confianza alta: {ahora['aciertos']} de {total_alta} "
          f"({_pct(ahora['aciertos'], total_alta)}) · errores: {ahora['errores']}")
    print(f"  Confianza media (no cuentan): calzan {ahora['dudosos_ok']}, "
          f"difieren {ahora['dudosos_no']}")
    sub_total = ahora["sub_ok"] + ahora["sub_mal"]
    if sub_total:
        print(f"  Subcategoría, de los que la auditoría anotó: "
              f"{ahora['sub_ok']} de {sub_total}")
    print("\n  De dónde salió cada acierto:")
    for origen, n in ahora["por_origen"].most_common():
        print(f"     {origen:12s} {n:4d}")

    if args.errores or args.pendientes:
        print(f"\n  Siguen mal ({ahora['errores']}):")
        for id_ev, titulo, esperada, dio, origen, lugar, fuente in ahora["detalle"]:
            print(f"     {id_ev}  {titulo[:52]:52s} {esperada:10s} ≠ {dio:10s} ({origen})")
            print(f"                       lugar: {lugar[:40]:40s} fuente: {fuente[:30]}")
    if args.dudosos:
        print(f"\n  Diferencias de confianza media ({ahora['dudosos_no']}):")
        for id_ev, titulo, esperada, dio, origen in ahora["dudosos"]:
            print(f"     {id_ev}  {titulo[:52]:52s} {esperada:10s} ≠ {dio:10s} ({origen})")

    if args.pendientes:
        # El bisturí: lo que ninguna regla generalizable alcanzó a arreglar.
        lineas = ["# Lo que la auditoría marcó mal y el clasificador sigue sin",
                  "# resolver. Pegar en config/correcciones/eventos.yaml SOLO lo que",
                  "# no se pueda generalizar: si el error se repite, la regla va en",
                  "# config/correcciones/categorias.yaml o en loica/clasificar.py.",
                  "", "eventos:"]
        for id_ev, titulo, esperada, dio, _, _, _ in ahora["detalle"]:
            lineas.append(f"  # {titulo[:70]}  ({dio} → {esperada})")
            lineas.append(f"  {id_ev}:")
            if esperada == "descartar":
                lineas.append("    descartar: true")
            else:
                lineas.append(f"    categoria: {esperada}")
            lineas.append("    nota: auditoría del 2026-08-22")
            lineas.append("")
        salida = DIR_REVISION / "pendientes_categorias.yaml"
        salida.write_text("\n".join(lineas), encoding="utf-8")
        print(f"\n  Esqueleto en {salida.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
