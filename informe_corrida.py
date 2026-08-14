#!/usr/bin/env python3
"""Deja un Excel de diagnóstico de la corrida en `informes/`.

    python3 informe_corrida.py

Es el informe para MIRAR EL PROCESO, no el catastro. El sitio contesta "¿qué
hago hoy?"; esto contesta "¿está funcionando esto y dónde se está rompiendo?".
Por eso vive fuera de `web/` y fuera de git (`informes/` está en .gitignore):
es un cuaderno de trabajo, no un entregable.

Dos hojas, y la división no es decorativa:

  1. Diagnóstico — los números de la corrida y el delta contra la anterior.
     Sirve para ver de un vistazo si algo se cayó: una fuente que pasó de 200
     eventos a 0, la georreferenciación que bajó diez puntos, una corrida que
     se demoró el triple.

  2. Para revisar — la lista de eventos que el pipeline no supo resolver solo.
     Es una cola de trabajo: cada fila es una decisión que una persona puede
     tomar en diez segundos y que después se guarda en `config/correcciones/`
     para que no vuelva a preguntarse.

La comparación con "la corrida anterior" sale de `datos/historial_corridas.json`,
que este script escribe al final. Se usa eso y no `git show HEAD:web/eventos.json`
porque con `--sin-publicar` el HEAD no avanza y entonces todas las corridas del
día se comparaban contra el mismo punto, mostrando altas que ya se habían
mostrado. El historial guarda además una fila por corrida con los agregados,
así que a las pocas semanas el propio archivo muestra la tendencia.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from loica.almacen import RUTA_DB, SQL_VIGENTE
from loica.clasificar import clasificar

RAIZ = Path(__file__).resolve().parent
DIR_INFORMES = RAIZ / "informes"
RUTA_EVENTOS = RAIZ / "web" / "eventos.json"
RUTA_HISTORIAL = RAIZ / "datos" / "historial_corridas.json"

# Las precisiones que significan "el pin está donde de verdad ocurre la cosa".
# `comuna` es el centro de la comuna y `sin_ubicar` es que no hay pin: las dos
# son deuda, y por eso se cuentan aparte.
PRECISIONES_EXACTAS = {"recinto", "fuente", "calle", "correccion"}

# Paleta del informe. Es la del sitio para que se reconozca de qué proyecto es,
# pero apagada: esto se lee en una planilla, no es una vitrina.
TINTA = "1E2A4A"
CREMA = "FAF3E7"
ARENA = "EDE7DE"
ROJO = "C0392B"
AMBAR = "B9770E"
VERDE = "1E7A52"

FUENTE = "Arial"
_borde = Side(style="thin", color="BEB6A9")
BORDE = Border(left=_borde, right=_borde, top=_borde, bottom=_borde)


# ---------------------------------------------------------------- datos

def _cargar_json(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def corrida_de_hoy(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """Las filas de `corridas` de la última tanda, una por fuente.

    Se agrupa por fuente y se toma la más reciente: correr `run_diario.py` dos
    veces el mismo día dejaba dos filas por fuente y los totales salían al
    doble, que es justo el número que uno no quiere dudar en un diagnóstico.
    """
    return con.execute(
        """SELECT c.* FROM corridas c
           JOIN (SELECT fuente, MAX(momento) AS ultimo
                 FROM corridas WHERE date(momento) = date('now','localtime')
                 GROUP BY fuente) u
             ON c.fuente = u.fuente AND c.momento = u.ultimo
           ORDER BY c.fuente""",
    ).fetchall()


def eventos_publicados() -> list[dict]:
    return _cargar_json(RUTA_EVENTOS).get("eventos", [])


def historial() -> dict:
    d = _cargar_json(RUTA_HISTORIAL)
    return {"ultima": d.get("ultima") or {}, "filas": d.get("filas") or []}


def lugares_nuevos(con: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """Lugares que aparecen por primera vez en la base con esta corrida.

    Un lugar nuevo es donde se rompe la georreferenciación: el catastro no lo
    conoce, la memoria de correcciones tampoco, y el pin sale al centro de la
    comuna o no sale. Saber cuáles entraron hoy es saber qué revisar.
    """
    filas = con.execute(
        """SELECT lugar_nombre, comuna, COUNT(*) AS n
           FROM eventos
           WHERE lugar_nombre IS NOT NULL AND TRIM(lugar_nombre) != ''
           GROUP BY lugar_nombre
           HAVING MIN(date(fecha_extraccion)) = date('now','localtime')
           ORDER BY n DESC, lugar_nombre""",
    ).fetchall()
    return [(f["lugar_nombre"], f["comuna"] or "", f["n"]) for f in filas]


def clasificar_con_origen(con: sqlite3.Connection) -> dict[str, str]:
    """Para cada evento vigente, de dónde salió su categoría.

    `exportar_web.py` se queda solo con la categoría y bota el origen, porque
    al sitio no le sirve. Acá sí: una categoría sacada del título es un hecho
    leído y una sacada del recinto es una conjetura del 85%. Son la misma
    palabra en la tarjeta y no son la misma confianza, y esa diferencia es
    justamente lo que hay que poner en la cola de revisión.
    """
    origenes = {}
    for fila in con.execute(
            "SELECT hash_dedup, titulo, categoria, descripcion_corta, "
            "lugar_nombre, fuente_nombre FROM eventos WHERE " + SQL_VIGENTE):
        _, origen = clasificar(fila["titulo"], fila["categoria"] or "",
                               fila["descripcion_corta"] or "",
                               fila["lugar_nombre"] or "",
                               fila["fuente_nombre"] or "")
        origenes[fila["hash_dedup"]] = origen
    return origenes


# ------------------------------------------------------------- escritura

def _titulo(hoja, fila: int, texto: str) -> int:
    c = hoja.cell(row=fila, column=1, value=texto)
    c.font = Font(name=FUENTE, size=12, bold=True, color=TINTA)
    c.fill = PatternFill("solid", fgColor=ARENA)
    for col in range(2, 7):
        hoja.cell(row=fila, column=col).fill = PatternFill("solid", fgColor=ARENA)
    return fila + 1


def _dato(hoja, fila: int, etiqueta: str, valor, nota: str = "",
          color: str | None = None, formato: str | None = None) -> int:
    a = hoja.cell(row=fila, column=1, value=etiqueta)
    a.font = Font(name=FUENTE, size=10, color=TINTA)
    b = hoja.cell(row=fila, column=2, value=valor)
    b.font = Font(name=FUENTE, size=10, bold=True, color=color or TINTA)
    b.alignment = Alignment(horizontal="right")
    if formato:
        b.number_format = formato
    if nota:
        c = hoja.cell(row=fila, column=3, value=nota)
        c.font = Font(name=FUENTE, size=9, italic=True, color="645D51")
    return fila + 1


def _encabezados(hoja, fila: int, titulos: list[str]) -> int:
    for i, t in enumerate(titulos, start=1):
        c = hoja.cell(row=fila, column=i, value=t)
        c.font = Font(name=FUENTE, size=9, bold=True, color=CREMA)
        c.fill = PatternFill("solid", fgColor=TINTA)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDE
    hoja.row_dimensions[fila].height = 26
    return fila + 1


def hoja_diagnostico(wb: Workbook, ctx: dict) -> None:
    h = wb.active
    h.title = "Diagnóstico"
    h.sheet_view.showGridLines = False

    f = 1
    c = h.cell(row=1, column=1, value=f"Corrida del {ctx['momento']:%d-%m-%Y a las %H:%M}")
    c.font = Font(name=FUENTE, size=15, bold=True, color=TINTA)
    f = 3

    # ---- La corrida
    f = _titulo(h, f, "LA CORRIDA")
    f = _dato(h, f, "Duración total", ctx["duracion_min"],
              "minutos de punta a punta", formato="0.0")
    f = _dato(h, f, "Fuentes que corrieron", ctx["fuentes_total"])
    f = _dato(h, f, "Fuentes con error", ctx["fuentes_error"],
              "revísalas en la tabla de abajo" if ctx["fuentes_error"] else "ninguna",
              ROJO if ctx["fuentes_error"] else VERDE)
    f = _dato(h, f, "Fuentes vivas pero sin nada futuro", ctx["fuentes_vacias"],
              "responden bien y no aportan eventos: agenda abandonada o "
              "cambio de formato" if ctx["fuentes_vacias"] else "ninguna",
              AMBAR if ctx["fuentes_vacias"] else VERDE)
    f += 1

    # ---- Qué cambió
    f = _titulo(h, f, "QUÉ CAMBIÓ DESDE LA CORRIDA ANTERIOR")
    fila_hoy, fila_antes = f, f + 1
    f = _dato(h, f, "Publicados ahora", ctx["total_hoy"])
    f = _dato(h, f, "Publicados en la corrida anterior", ctx["total_antes"],
              ctx["cuando_antes"])
    f = _dato(h, f, "Entraron (altas)", ctx["altas"], "no estaban antes", VERDE)
    f = _dato(h, f, "Salieron (bajas)", ctx["bajas"],
              "ya pasaron, caducaron o la fuente los bajó", AMBAR)
    fila_neto = f
    h.cell(row=f, column=1, value="Neto").font = Font(name=FUENTE, size=10, color=TINTA)
    nc = h.cell(row=f, column=2, value=f"=B{fila_hoy}-B{fila_antes}")
    nc.font = Font(name=FUENTE, size=10, bold=True, color=TINTA)
    nc.alignment = Alignment(horizontal="right")
    h.cell(row=f, column=3, value="si es muy negativo sin explicación, mira las "
           "fuentes con error").font = Font(name=FUENTE, size=9, italic=True, color="645D51")
    f += 2

    # ---- Extracción
    f = _titulo(h, f, "LO QUE TRAJO LA EXTRACCIÓN")
    f = _dato(h, f, "Eventos encontrados en las fuentes", ctx["encontrados"])
    f = _dato(h, f, "Nuevos guardados en la base", ctx["nuevos"])
    f = _dato(h, f, "Actualizados", ctx["actualizados"], "ya estaban y cambió algo")
    f = _dato(h, f, "Descartados en la puerta", ctx["descartados"],
              "sin título, sin link, pasados o link de máquina")
    f += 1

    # ---- Georreferenciación
    f = _titulo(h, f, "GEORREFERENCIACIÓN")
    fila_exactos = f
    f = _dato(h, f, "Con pin exacto", ctx["exactos"],
              "recinto, calle, coordenada de la fuente o corrección a mano", VERDE)
    f = _dato(h, f, "Pin aproximado (centro de comuna)", ctx["aprox"],
              "el mapa lo atenúa; están en la hoja 2", AMBAR)
    f = _dato(h, f, "Sin pin", ctx["sin_pin"],
              "salen en la lista pero no en el mapa; están en la hoja 2", ROJO)
    fila_total_geo = f
    f = _dato(h, f, "Total publicado", ctx["total_hoy"])
    pc = h.cell(row=f, column=1, value="% con pin exacto")
    pc.font = Font(name=FUENTE, size=10, color=TINTA)
    pv = h.cell(row=f, column=2, value=f"=IFERROR(B{fila_exactos}/B{fila_total_geo},0)")
    pv.font = Font(name=FUENTE, size=10, bold=True, color=TINTA)
    pv.number_format = "0.0%"
    pv.alignment = Alignment(horizontal="right")
    h.cell(row=f, column=3, value="es la métrica clave del mapa").font = Font(
        name=FUENTE, size=9, italic=True, color="645D51")
    f += 1
    f = _dato(h, f, "De los eventos nuevos de hoy, con pin", ctx["nuevos_con_pin"],
              f"de {ctx['nuevos_publicados']} nuevos que salieron publicados")
    f += 1

    # ---- Clasificación
    f = _titulo(h, f, "CLASIFICACIÓN")
    f = _dato(h, f, "Leída del título o la descripción", ctx["origen_texto"],
              "el clasificador lo leyó, no lo adivinó", VERDE)
    f = _dato(h, f, "Adivinada por el recinto o la fuente", ctx["origen_prior"],
              "conjetura razonable (~85% de acierto); están en la hoja 2", AMBAR)
    f = _dato(h, f, "Sin señal: cayó en «otros»", ctx["origen_defecto"],
              "el clasificador no supo qué es; están en la hoja 2", ROJO)
    f = _dato(h, f, "Con subcategoría", ctx["con_subcat"],
              "género de la fiesta, tipo de obra, oficio del taller")
    f += 1
    f = _encabezados(h, f, ["Categoría", "Eventos", "% del total"])
    fila_cat = f
    for cat, n in ctx["por_categoria"]:
        h.cell(row=f, column=1, value=cat).font = Font(name=FUENTE, size=10)
        h.cell(row=f, column=2, value=n).font = Font(name=FUENTE, size=10)
        p = h.cell(row=f, column=3, value=f"=IFERROR(B{f}/$B${fila_total_geo},0)")
        p.font = Font(name=FUENTE, size=10)
        p.number_format = "0.0%"
        for col in (1, 2, 3):
            h.cell(row=f, column=col).border = BORDE
        f += 1
    tc = h.cell(row=f, column=1, value="Total")
    tc.font = Font(name=FUENTE, size=10, bold=True)
    tv = h.cell(row=f, column=2, value=f"=SUM(B{fila_cat}:B{f - 1})")
    tv.font = Font(name=FUENTE, size=10, bold=True)
    for col in (1, 2, 3):
        h.cell(row=f, column=col).border = BORDE
    f += 2

    # ---- Lugares nuevos
    f = _titulo(h, f, f"LUGARES QUE APARECEN POR PRIMERA VEZ ({len(ctx['lugares'])})")
    h.cell(row=f, column=1, value="Un lugar nuevo es donde se rompe la "
           "georreferenciación: nadie lo ha ubicado todavía.").font = Font(
        name=FUENTE, size=9, italic=True, color="645D51")
    f += 1
    if ctx["lugares"]:
        f = _encabezados(h, f, ["Lugar", "Comuna", "Eventos"])
        for nombre, comuna, n in ctx["lugares"][:60]:
            h.cell(row=f, column=1, value=nombre).font = Font(name=FUENTE, size=10)
            h.cell(row=f, column=2, value=comuna).font = Font(name=FUENTE, size=10)
            h.cell(row=f, column=3, value=n).font = Font(name=FUENTE, size=10)
            for col in (1, 2, 3):
                h.cell(row=f, column=col).border = BORDE
            f += 1
        if len(ctx["lugares"]) > 60:
            h.cell(row=f, column=1,
                   value=f"… y {len(ctx['lugares']) - 60} más").font = Font(
                name=FUENTE, size=9, italic=True, color="645D51")
            f += 1
    else:
        h.cell(row=f, column=1, value="Ninguno: todas las sedes de hoy ya se "
               "conocían.").font = Font(name=FUENTE, size=10, italic=True)
        f += 1
    f += 1

    # ---- Por fuente
    f = _titulo(h, f, "POR FUENTE")
    f = _encabezados(h, f, ["Fuente", "Encontrados", "Nuevos", "Actualizados",
                            "Descartados", "Segundos", "Estado"])
    fila_fuentes = f
    for fila in ctx["fuentes"]:
        estado = "ERROR" if fila["error"] else ("sin nada futuro"
                 if fila["fuente"] in ctx["nombres_vacias"] else "ok")
        color = ROJO if fila["error"] else (AMBAR if estado != "ok" else TINTA)
        valores = [fila["fuente"], fila["encontrados"], fila["nuevos"],
                   fila["actualizados"], fila["descartados"],
                   round(fila["duracion_seg"] or 0, 1), estado]
        for i, v in enumerate(valores, start=1):
            c = h.cell(row=f, column=i, value=v)
            c.font = Font(name=FUENTE, size=10,
                          color=color if i in (1, 7) else TINTA)
            c.border = BORDE
        if fila["error"]:
            h.cell(row=f, column=7).comment = None
            h.cell(row=f, column=7).value = f"ERROR: {str(fila['error'])[:180]}"
        f += 1
    if ctx["fuentes"]:
        h.cell(row=f, column=1, value="Total").font = Font(name=FUENTE, size=10, bold=True)
        for col in range(2, 7):
            L = get_column_letter(col)
            t = h.cell(row=f, column=col,
                       value=f"=SUM({L}{fila_fuentes}:{L}{f - 1})")
            t.font = Font(name=FUENTE, size=10, bold=True)
            t.border = BORDE
        h.cell(row=f, column=1).border = BORDE
        h.cell(row=f, column=7).border = BORDE

    for col, ancho in zip("ABCDEFG", (46, 13, 52, 13, 13, 11, 20)):
        h.column_dimensions[col].width = ancho


def hoja_revisar(wb: Workbook, ctx: dict) -> None:
    h = wb.create_sheet("Para revisar")
    h.sheet_view.showGridLines = False

    c = h.cell(row=1, column=1, value="Lo que el pipeline no supo resolver solo")
    c.font = Font(name=FUENTE, size=15, bold=True, color=TINTA)
    h.cell(row=2, column=1, value=(
        "Cada fila es una decisión de diez segundos. Lo que se arregle acá va a "
        "config/correcciones/ (lugares.yaml para la ubicación, eventos.yaml para "
        "la categoría) y la corrida siguiente lo aplica sola. Si el mismo error "
        "se repite en eventos nuevos, el arreglo va en loica/clasificar.py, no "
        "en la memoria.")).font = Font(name=FUENTE, size=9, italic=True, color="645D51")
    h.merge_cells(start_row=2, start_column=1, end_row=2, end_column=11)
    h.row_dimensions[2].height = 30
    h.cell(row=2, column=1).alignment = Alignment(wrap_text=True, vertical="top")

    columnas = ["Qué revisar", "Título", "Cuándo", "Lugar", "Dirección",
                "Comuna", "Categoría", "De dónde salió", "Subcategoría",
                "Fuente", "Link"]
    f = _encabezados(h, 4, columnas)
    h.freeze_panes = h.cell(row=f, column=1)

    for e in ctx["revisar"]:
        valores = [e["motivo"], e["titulo"], e["cuando"], e["lugar"],
                   e["direccion"], e["comuna"], e["categoria"], e["origen"],
                   e["subcategoria"], e["fuente"], e["url"]]
        for i, v in enumerate(valores, start=1):
            c = h.cell(row=f, column=i, value=v)
            c.font = Font(name=FUENTE, size=10, color=TINTA)
            c.border = BORDE
            c.alignment = Alignment(vertical="top", wrap_text=(i in (2, 4, 5)))
        h.cell(row=f, column=1).font = Font(name=FUENTE, size=10, bold=True,
                                            color=e["color"])
        if e["url"]:
            enlace = h.cell(row=f, column=11)
            enlace.hyperlink = e["url"]
            enlace.value = "abrir"
            enlace.font = Font(name=FUENTE, size=10, color="1B6FD1", underline="single")
        f += 1

    h.auto_filter.ref = f"A4:K{max(f - 1, 5)}"
    for col, ancho in zip("ABCDEFGHIJK", (30, 46, 17, 30, 30, 16, 12, 16, 15, 22, 9)):
        h.column_dimensions[col].width = ancho


# ------------------------------------------------------------------ main

def armar_contexto() -> dict:
    con = sqlite3.connect(RUTA_DB)
    con.row_factory = sqlite3.Row

    fuentes = corrida_de_hoy(con)
    publicados = eventos_publicados()
    hist = historial()
    ids_antes = set(hist["ultima"].get("ids") or [])
    ids_hoy = {e["id"] for e in publicados}
    origenes = clasificar_con_origen(con)

    # Qué eventos entraron hoy a la base: sirve para saber si lo nuevo llegó
    # bien ubicado o si la deuda de georreferenciación la generan los recién
    # llegados.
    nuevos_hoy = {f["hash_dedup"] for f in con.execute(
        "SELECT hash_dedup FROM eventos "
        "WHERE date(fecha_extraccion) = date('now','localtime')")}
    pub_nuevos = [e for e in publicados if e["id"] in nuevos_hoy]

    nombres_vacias = set()
    for fila in fuentes:
        if fila["error"] or not fila["encontrados"]:
            continue
        vig = con.execute("SELECT COUNT(*) FROM eventos WHERE fuente_nombre = ? AND "
                          + SQL_VIGENTE, (fila["fuente"],)).fetchone()[0]
        if not vig:
            nombres_vacias.add(fila["fuente"])

    conteo_origen = Counter(origenes.get(e["id"], "defecto") for e in publicados)

    # ---- La cola de revisión
    ETIQUETAS = {
        "sin_pin": ("1. Sin pin en el mapa", ROJO),
        "sin_categoria": ("2. Sin categoría (otros)", ROJO),
        "categoria_adivinada": ("3. Categoría adivinada por el recinto", AMBAR),
        "pin_aproximado": ("4. Pin al centro de la comuna", AMBAR),
    }
    revisar = []
    for e in publicados:
        origen = origenes.get(e["id"], "")
        if e["precision"] == "sin_ubicar":
            motivo = "sin_pin"
        elif e["categoria"] == "otros":
            motivo = "sin_categoria"
        elif origen == "prior":
            motivo = "categoria_adivinada"
        elif e["precision"] == "comuna":
            motivo = "pin_aproximado"
        else:
            continue
        etiqueta, color = ETIQUETAS[motivo]
        revisar.append({
            "orden": etiqueta, "motivo": etiqueta, "color": color,
            "titulo": e["titulo"],
            "cuando": (e["inicio"] or "")[:16].replace("T", " "),
            "lugar": e["lugar"], "direccion": e["direccion"],
            "comuna": e["comuna"], "categoria": e["categoria"],
            "origen": origen, "subcategoria": e.get("subcategoria") or "",
            "fuente": e["fuente"], "url": e["url"],
        })
    revisar.sort(key=lambda r: (r["orden"], r["cuando"]))

    duracion = sum(f["duracion_seg"] or 0 for f in fuentes)
    exactos = sum(1 for e in publicados if e["precision"] in PRECISIONES_EXACTAS)

    ctx = {
        "momento": datetime.now(),
        "duracion_min": round(duracion / 60, 1),
        "fuentes": fuentes,
        "fuentes_total": len(fuentes),
        "fuentes_error": sum(1 for f in fuentes if f["error"]),
        "fuentes_vacias": len(nombres_vacias),
        "nombres_vacias": nombres_vacias,
        "encontrados": sum(f["encontrados"] or 0 for f in fuentes),
        "nuevos": sum(f["nuevos"] or 0 for f in fuentes),
        "actualizados": sum(f["actualizados"] or 0 for f in fuentes),
        "descartados": sum(f["descartados"] or 0 for f in fuentes),
        "total_hoy": len(publicados),
        "total_antes": hist["ultima"].get("total", 0),
        "cuando_antes": hist["ultima"].get("momento", "primera corrida registrada"),
        "altas": len(ids_hoy - ids_antes) if ids_antes else len(ids_hoy),
        "bajas": len(ids_antes - ids_hoy),
        "exactos": exactos,
        "aprox": sum(1 for e in publicados if e["precision"] == "comuna"),
        "sin_pin": sum(1 for e in publicados if e["precision"] == "sin_ubicar"),
        "nuevos_publicados": len(pub_nuevos),
        "nuevos_con_pin": sum(1 for e in pub_nuevos if e["lat"] is not None),
        "origen_texto": conteo_origen["titulo"] + conteo_origen["descripcion"],
        "origen_prior": conteo_origen["prior"],
        "origen_defecto": conteo_origen["defecto"],
        "con_subcat": sum(1 for e in publicados if e.get("subcategoria")),
        "por_categoria": Counter(e["categoria"] for e in publicados).most_common(),
        "lugares": lugares_nuevos(con),
        "revisar": revisar,
    }
    con.close()
    return ctx, ids_hoy


def guardar_historial(ctx: dict, ids_hoy: set) -> None:
    hist = historial()
    hist["filas"].append({
        "momento": ctx["momento"].isoformat(timespec="seconds"),
        "total": ctx["total_hoy"], "altas": ctx["altas"], "bajas": ctx["bajas"],
        "exactos": ctx["exactos"], "sin_pin": ctx["sin_pin"],
        "otros": dict(ctx["por_categoria"]).get("otros", 0),
        "duracion_min": ctx["duracion_min"],
        "fuentes_error": ctx["fuentes_error"],
    })
    # 400 corridas son más de un año a una por día: pasado eso el archivo
    # crece sin que nadie lo lea.
    hist["filas"] = hist["filas"][-400:]
    hist["ultima"] = {
        "momento": ctx["momento"].strftime("%d-%m-%Y %H:%M"),
        "total": ctx["total_hoy"],
        "ids": sorted(ids_hoy),
    }
    RUTA_HISTORIAL.parent.mkdir(parents=True, exist_ok=True)
    RUTA_HISTORIAL.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    if not RUTA_EVENTOS.exists():
        print("No existe web/eventos.json: corre primero exportar_web.py")
        return 1

    ctx, ids_hoy = armar_contexto()

    wb = Workbook()
    hoja_diagnostico(wb, ctx)
    hoja_revisar(wb, ctx)

    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    ruta = DIR_INFORMES / f"{date.today():%Y-%m-%d}_diagnostico.xlsx"
    wb.save(ruta)
    guardar_historial(ctx, ids_hoy)

    print(f"Diagnóstico: {ruta}")
    print(f"  {ctx['total_hoy']} publicados "
          f"(+{ctx['altas']} / -{ctx['bajas']} desde la corrida anterior)")
    print(f"  {ctx['exactos']} con pin exacto, {ctx['sin_pin']} sin pin")
    print(f"  {len(ctx['revisar'])} eventos en la cola de revisión")
    return 0


if __name__ == "__main__":
    sys.exit(main())
