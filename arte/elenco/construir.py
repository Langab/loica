#!/usr/bin/env python3
"""Arma el elenco v3 (los retratos) desde arte/elenco/svg/.

    python3 arte/elenco/construir.py                 # valida y arma hoja.html
    python3 arte/elenco/construir.py --png           # + captura hoja.png (Chrome sin ventana)
    python3 arte/elenco/construir.py --solo pudu,cabra --png   # solo esos, en grande
    python3 arte/elenco/construir.py --web           # además los escribe en web/loica.js y web/loica.css

Sin --web no toca el sitio: sirve para iterar un dibujo mirando la hoja.
Las reglas que valida están en LEEME.md.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
WEB_JS = RAIZ / "web" / "loica.js"
WEB_CSS = RAIZ / "web" / "loica.css"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TINTA = "#1E2A4A"

INI_JS, FIN_JS = "/* RETRATOS:INICIO", "/* RETRATOS:FIN */"
INI_CSS, FIN_CSS = "/* RETRATOS-CSS:INICIO", "/* RETRATOS-CSS:FIN */"


def fichas() -> list[dict]:
    return json.loads((AQUI / "fichas.json").read_text(encoding="utf-8"))


def validar(clave: str, interior: str) -> list[str]:
    errores = []
    if re.search(r"<(style|script|image|text|foreignObject)\b|href=|on\w+=", interior, re.I):
        errores.append("contenido no permitido (style/script/image/text/href/on*)")
    if "`" in interior or "${" in interior:
        errores.append("caracteres que rompen el template de JS (` o ${)")
    if "'" in interior:
        errores.append("comillas simples: usar dobles")
    for m in re.finditer(r'\sid="([^"]+)"', interior):
        if not m.group(1).startswith(clave + "-"):
            errores.append(f'id sin prefijo "{clave}-": {m.group(1)}')
    if not re.match(r'\s*<g class="an-cuerpo', interior):
        errores.append('el dibujo debe partir con <g class="an-cuerpo"> que lo envuelve todo')
    n_parp = len(re.findall(r'class="[^"]*\ban-parpado\b', interior))
    if n_parp != 2:
        errores.append(f"se esperan 2 an-parpado y hay {n_parp}")
    if not re.search(r'class="[^"]*\ban-brazo\b', interior):
        errores.append("falta an-brazo")
    return errores


def comprimir(interior: str) -> str:
    s = re.sub(r"<!--[\s\S]*?-->", "", interior)
    s = re.sub(r"\s*\n\s*", " ", s)
    s = re.sub(r">\s+<", "><", s).strip()
    s = re.sub(r"(\.\d*?[1-9])0+(?=\D)", r"\1", s)   # 2.500 → 2.5
    s = re.sub(r"(\d)\.0+(?=\D)", r"\1", s)           # 3.0 → 3
    return s


def svg_completo(f: dict, interior: str, tam: int, clases: str = "") -> str:
    return (f'<svg class="retrato {clases}" viewBox="-20 0 240 240" width="{tam}" height="{tam}" '
            f'role="img" aria-label="{html.escape(f["aria"])}" fill="none" stroke="{TINTA}" '
            f'stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round">{interior}</svg>')


def cargar(solo: set[str] | None) -> tuple[list[tuple[dict, str]], bool]:
    lista, ok = [], True
    for f in fichas():
        if solo and f["clave"] not in solo:
            continue
        ruta = AQUI / "svg" / f"{f['clave']}.svg"
        if not ruta.exists():
            print(f"  · {f['clave']}: sin dibujo todavía")
            lista.append((f, None))
            continue
        interior = ruta.read_text(encoding="utf-8")
        errores = validar(f["clave"], interior)
        if errores:
            ok = False
            print(f"  ✗ {f['clave']}:")
            for e in errores:
                print(f"      {e}")
        else:
            print(f"  ✓ {f['clave']} ({len(comprimir(interior))} bytes)")
        lista.append((f, comprimir(interior)))
    return lista, ok


def hoja(lista: list[tuple[dict, str]], grande: bool) -> str:
    css = (AQUI / "retrato.css").read_text(encoding="utf-8")
    t = 300 if grande else 170

    def celda(f, interior, tam, clases="", fondo="#FAF3E7", tinta="#1E2A4A"):
        dib = (svg_completo(f, interior, tam, clases) if interior
               else f'<div style="width:{tam}px;height:{tam}px;display:grid;place-items:center;border:3px dashed #bbb;border-radius:50%">{f["clave"]}</div>')
        return f'<figure style="background:{fondo};color:{tinta}">{dib}<figcaption>{f["nombre"]}</figcaption></figure>'

    filas = []
    filas.append("<h2>Sobre crema, tamaño de portada</h2><div class=fila>" +
                 "".join(celda(f, i, t) for f, i in lista) + "</div>")
    if not grande:
        filas.append("<h2>En su color (ficha del animal)</h2><div class=fila>" +
                     "".join(celda(f, i, 120, fondo=f["color"], tinta="#fff") for f, i in lista) + "</div>")
        filas.append("<h2>Modo oscuro · 96 px</h2><div class=fila>" +
                     "".join(celda(f, i, 96, fondo="#161B2E", tinta="#FAF3E7") for f, i in lista) + "</div>")
        filas.append("<h2>Chicos: 56 px (lo mínimo para un retrato)</h2><div class=fila>" +
                     "".join(celda(f, i, 56) for f, i in lista) + "</div>")
        filas.append("<h2>Durmiendo (estados vacíos) · silueta (marca de agua)</h2><div class=fila>" +
                     "".join(celda(f, i, 96, "rt-dormido") for f, i in lista[:6]) +
                     "".join(celda(f, i, 96, "rt-silueta", fondo=f["color"]) for f, i in lista[6:]) + "</div>")
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Elenco v3 · hoja de prueba</title>
<style>
body{{margin:0;padding:24px;background:#FFFBF5;color:#1E2A4A;font:15px/1.4 system-ui,sans-serif}}
h1{{margin:0 0 4px}} h2{{font-size:15px;margin:28px 0 10px;opacity:.75}}
.fila{{display:flex;flex-wrap:wrap;gap:12px}}
figure{{margin:0;padding:10px 10px 8px;border-radius:16px;border:3px solid #1E2A4A;box-shadow:4px 4px 0 #1E2A4A;display:flex;flex-direction:column;align-items:center}}
figcaption{{font-weight:700;font-size:13px;margin-top:4px}}
{css}
</style></head><body>
<h1>Elenco v3 · los retratos</h1>
<p>Generada por arte/elenco/construir.py. Abrir con #anima para ver los tics.</p>
{''.join(filas)}
<script>if(location.hash==="#anima")document.querySelectorAll(".retrato").forEach((s,i)=>{{s.classList.add("anima");s.style.setProperty("--d",(-i*.7)+"s")}})</script>
</body></html>"""


def reemplazar_bloque(texto: str, ini: str, fin: str, nuevo: str, archivo: str) -> str:
    a = texto.find(ini)
    b = texto.find(fin)
    if a < 0 or b < 0:
        sys.exit(f"Faltan los marcadores {ini} … {fin} en {archivo}")
    return texto[:a] + nuevo + texto[b + len(fin):]


def escribir_web(lista: list[tuple[dict, str]]) -> None:
    faltan = [f["clave"] for f, i in lista if i is None]
    if faltan:
        sys.exit(f"No se publica: faltan dibujos de {', '.join(faltan)}")
    lineas = [INI_JS + " — generado por arte/elenco/construir.py, no editar a mano. */",
              "const RETRATOS = {"]
    for f, i in lista:
        lineas.append(f"  {f['clave']}: {{aria:{json.dumps(f['aria'], ensure_ascii=False)}, svg:'{i}'}},")
    lineas += ["};", FIN_JS]
    js = WEB_JS.read_text(encoding="utf-8")
    WEB_JS.write_text(reemplazar_bloque(js, INI_JS, FIN_JS, "\n".join(lineas), "loica.js"), encoding="utf-8")
    css = WEB_CSS.read_text(encoding="utf-8")
    bloque = (INI_CSS + " — copia de arte/elenco/retrato.css (construir.py --web). */\n" +
              (AQUI / "retrato.css").read_text(encoding="utf-8").strip() + "\n" + FIN_CSS)
    WEB_CSS.write_text(reemplazar_bloque(css, INI_CSS, FIN_CSS, bloque, "loica.css"), encoding="utf-8")
    print(f"  → web/loica.js y web/loica.css actualizados ({len(lista)} retratos)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solo", help="claves separadas por coma")
    ap.add_argument("--png", action="store_true", help="captura la hoja con Chrome sin ventana")
    ap.add_argument("--web", action="store_true", help="escribe los retratos en web/loica.js y web/loica.css")
    a = ap.parse_args()
    solo = set(a.solo.split(",")) if a.solo else None
    lista, ok = cargar(solo)
    nombre = "hoja" if not solo else "hoja_" + "_".join(sorted(solo))
    ruta = AQUI / f"{nombre}.html"
    ruta.write_text(hoja(lista, grande=bool(solo)), encoding="utf-8")
    print(f"  hoja: {ruta.relative_to(RAIZ)}")
    if a.png:
        alto = 900 if solo else 1900
        ancho = max(700, 340 * len(lista)) if solo else 1500
        png = ruta.with_suffix(".png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size={ancho},{alto}", f"--screenshot={png}", ruta.as_uri()],
                       check=False, capture_output=True, timeout=90)
        print(f"  captura: {png.relative_to(RAIZ)}" if png.exists() else "  ✗ no salió la captura")
    if not ok:
        print("Hay errores: corrígelos antes de --web.")
        return 1
    if a.web:
        escribir_web(lista)
    return 0


if __name__ == "__main__":
    sys.exit(main())
