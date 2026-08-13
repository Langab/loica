#!/usr/bin/env python3
"""Doble check del sitio ANTES de publicar. Si esto falla, no hay push.

    python3 verificar_web.py            # valida web/eventos.json y descuentos.json
    python3 verificar_web.py --forzar   # degrada la caída de volumen a aviso

La corrida de las 11:00 publica sin que nadie mire. Este es el par de ojos
que falta: valida que lo que está por subirse no rompa la página ni la deje
vacía. Dos niveles:

- ERROR   → se aborta la publicación. Cosas que botan la página (un descuento
            sin lista `dias` revienta descuentos.html), la dejan vacía o
            delatan una extracción rota (el catastro cayó a la mitad).
- AVISO   → se publica igual, pero queda dicho. Cosas feas que no rompen nada.

La caída de volumen contra la última versión publicada se salta con --forzar,
porque a veces la caída es legítima (se apagó una fuente a propósito).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
RUTA_EVENTOS = RAIZ / "web" / "eventos.json"
RUTA_DESCUENTOS = RAIZ / "web" / "descuentos.json"
DIR_FICHAS = RAIZ / "web" / "e"

# Umbrales. La base hoy ronda los 2.500 eventos y 650 descuentos; estos pisos
# no miden éxito, detectan catástrofe: un sitio con menos que esto es señal de
# extracción rota, no de semana tranquila.
MIN_EVENTOS = 100
MIN_DESCUENTOS = 100          # el mismo piso que usa .github/workflows/descuentos.yml
MAX_CAIDA = 0.5               # publicar menos de la mitad que ayer requiere --forzar
MIN_PROPORCION_PIN = 0.6      # al menos 60% de los eventos con pin en el mapa
FRESCURA_HORAS = 24

CATEGORIAS = {"idiomas", "familia", "feria", "deporte", "fiesta", "cine",
              "teatro", "musica", "arte", "clases", "aire_libre", "charla",
              "otros"}
PRECISIONES = {"recinto", "fuente", "calle", "comuna", "correccion",
               "sin_ubicar", ""}


def _total_publicado(ruta_relativa: str) -> int | None:
    """Cuántos registros tiene la versión ya publicada (comiteada) del JSON."""
    salida = subprocess.run(["git", "show", f"HEAD:{ruta_relativa}"],
                            cwd=RAIZ, capture_output=True, text=True)
    if salida.returncode != 0:
        return None
    try:
        return json.loads(salida.stdout).get("total")
    except json.JSONDecodeError:
        return None


def verificar_eventos(errores: list[str], avisos: list[str],
                      forzar: bool) -> None:
    if not RUTA_EVENTOS.exists():
        errores.append("No existe web/eventos.json")
        return
    try:
        datos = json.loads(RUTA_EVENTOS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errores.append(f"web/eventos.json no es JSON válido: {e}")
        return

    eventos = datos.get("eventos", [])
    if len(eventos) < MIN_EVENTOS:
        errores.append(f"Solo {len(eventos)} eventos (mínimo {MIN_EVENTOS}): "
                       "la extracción vino rota, no se pisa el sitio bueno.")

    generado = datos.get("generado") or ""
    try:
        edad = datetime.now() - datetime.fromisoformat(generado)
        if edad > timedelta(hours=FRESCURA_HORAS):
            errores.append(f"web/eventos.json se generó hace {edad.days}d "
                           f"{edad.seconds // 3600}h: no es la corrida de hoy.")
    except (ValueError, TypeError):
        errores.append(f"Campo 'generado' ilegible: {generado!r}")

    ids = set()
    con_pin = 0
    for i, e in enumerate(eventos):
        donde = f"evento {i} ({str(e.get('titulo'))[:40]!r})"
        for campo in ("id", "titulo", "url"):
            if not e.get(campo):
                errores.append(f"{donde}: sin {campo}")
        identificador = e.get("id")
        if identificador and identificador in ids:
            errores.append(f"{donde}: id duplicado {identificador}")
        ids.add(identificador)

        inicio = e.get("inicio")
        if inicio:
            try:
                datetime.fromisoformat(inicio)
            except ValueError:
                errores.append(f"{donde}: inicio no es fecha ISO: {inicio!r}")

        lat, lon = e.get("lat"), e.get("lon")
        if (lat is None) != (lon is None):
            errores.append(f"{donde}: lat/lon a medias ({lat}, {lon})")
        if lat is not None:
            con_pin += 1
            if not (-34.3 < lat < -32.9 and -71.8 < lon < -70.0):
                errores.append(f"{donde}: coordenadas fuera de la RM ({lat}, {lon})")

        if e.get("categoria") not in CATEGORIAS:
            avisos.append(f"{donde}: categoría desconocida {e.get('categoria')!r}")
        if e.get("precision") not in PRECISIONES:
            avisos.append(f"{donde}: precisión desconocida {e.get('precision')!r}")

    if eventos and con_pin / len(eventos) < MIN_PROPORCION_PIN:
        errores.append(f"Solo {con_pin}/{len(eventos)} eventos con pin "
                       f"({con_pin * 100 // len(eventos)}%): la georreferenciación "
                       "se cayó entera.")

    # Caída de volumen contra lo ya publicado: la señal clásica de que media
    # extracción falló en silencio y estamos por pisar un sitio bueno.
    anterior = _total_publicado("web/eventos.json")
    if anterior and len(eventos) < anterior * MAX_CAIDA:
        mensaje = (f"El catastro cayó de {anterior} a {len(eventos)} eventos "
                   f"(menos del {int(MAX_CAIDA * 100)}%).")
        if forzar:
            avisos.append(mensaje + " Se publica igual por --forzar.")
        else:
            errores.append(mensaje + " Si la caída es legítima: --forzar.")

    # Las fichas compartibles tienen que calzar con el JSON: una ficha huérfana
    # es un link muerto en WhatsApp, y una que falta es un evento incompartible.
    if DIR_FICHAS.exists():
        fichas = {f.stem for f in DIR_FICHAS.glob("*.html")}
        sin_ficha = ids - fichas - {None}
        if sin_ficha:
            errores.append(f"{len(sin_ficha)} eventos sin su ficha en web/e/ "
                           f"(ej: {sorted(sin_ficha)[:3]})")
    else:
        avisos.append("No existe web/e/: no hay fichas para compartir.")


def verificar_descuentos(errores: list[str], avisos: list[str]) -> None:
    if not RUTA_DESCUENTOS.exists():
        avisos.append("No existe web/descuentos.json (¿corrida --sin-descuentos?)")
        return
    try:
        datos = json.loads(RUTA_DESCUENTOS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errores.append(f"web/descuentos.json no es JSON válido: {e}")
        return

    descuentos = datos.get("descuentos", [])
    if len(descuentos) < MIN_DESCUENTOS:
        errores.append(f"Solo {len(descuentos)} descuentos (mínimo {MIN_DESCUENTOS}).")

    # Un descuento sin días declarados se muestra como "todos los días" y entra
    # al filtro de Hoy cualquier día. Eso es correcto para los convenios
    # permanentes de Bci, y es MENTIRA cuando la fuente sí dijo un día y no
    # supimos leerlo. Pasó de verdad: "Holy Moly, todos los sábados" salió
    # publicado como todos los días porque el lector no reconocía el plural, y
    # alguien fue un día que no era y pagó la cuenta completa.
    #
    # Acá se cierra el agujero: si el texto de la fuente nombra un día de la
    # semana y la lista quedó vacía, es un fallo de lectura, no un convenio
    # sin restricción. Y un dato así no se publica.
    dia_en_texto = re.compile(
        r"\b(lunes|martes|mi[eé]rcoles|jueves|viernes|s[áa]bados?|domingos?"
        r"|fin de semana|finde)\b", re.IGNORECASE)

    for i, d in enumerate(descuentos):
        donde = f"descuento {i} ({str(d.get('comercio'))[:40]!r})"
        # `dias` que no sea lista revienta descuentos.html con TypeError: la
        # página hace .includes() sobre él sin mirar el tipo.
        if not isinstance(d.get("dias"), list):
            errores.append(f"{donde}: 'dias' no es una lista: {d.get('dias')!r}")
        elif not d["dias"]:
            texto = " ".join(str(d.get(c) or "") for c in
                             ("condiciones", "oferta", "descripcion"))
            hallado = dia_en_texto.search(texto)
            if hallado:
                errores.append(
                    f"{donde}: la fuente dice {hallado.group(0)!r} pero quedó sin "
                    "días, así que se publicaría como 'todos los días'. Es un "
                    "fallo de lectura en loica/descuentos/texto.py, no un "
                    "convenio sin restricción.")
        for campo in ("comercio", "banco", "id"):
            if not d.get(campo):
                errores.append(f"{donde}: sin {campo}")
        lat, lon = d.get("lat"), d.get("lon")
        if (lat is None) != (lon is None):
            errores.append(f"{donde}: lat/lon a medias ({lat}, {lon})")


def verificar_correcciones(errores: list[str]) -> None:
    """La memoria de correcciones tiene que parsear.

    Un YAML roto no bota la corrida —`loica/correcciones.py` avisa y sigue—
    pero deja el sitio sin NINGUNA corrección, y eso es invisible: los pines
    vuelven al centro de la comuna sin que nada falle. Pasó con una clave que
    llevaba `#` en el nombre, porque en YAML ese carácter abre un comentario.
    """
    import yaml
    directorio = RAIZ / "config" / "correcciones"
    for ruta in sorted(directorio.glob("*.yaml")):
        try:
            crudo = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError, OSError) as e:
            errores.append(f"config/correcciones/{ruta.name} no parsea "
                           f"({str(e).splitlines()[0]}): el sitio saldría sin "
                           "esas correcciones y nadie se enteraría.")
            continue
        if not isinstance(crudo, dict) or not crudo:
            errores.append(f"config/correcciones/{ruta.name}: falta la clave raíz.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Doble check antes del push")
    parser.add_argument("--forzar", action="store_true",
                        help="publica aunque el volumen haya caído a menos de la mitad")
    args = parser.parse_args()

    errores: list[str] = []
    avisos: list[str] = []
    verificar_correcciones(errores)
    verificar_eventos(errores, avisos, args.forzar)
    verificar_descuentos(errores, avisos)

    for a in avisos[:20]:
        print(f"  aviso: {a}")
    if len(avisos) > 20:
        print(f"  … y {len(avisos) - 20} avisos más")

    if errores:
        print(f"\n✗ Doble check FALLÓ con {len(errores)} errores — no se publica:")
        for e in errores[:30]:
            print(f"  ERROR: {e}")
        if len(errores) > 30:
            print(f"  … y {len(errores) - 30} más")
        return 1

    print(f"✓ Doble check OK: el sitio está entero"
          + (f" ({len(avisos)} avisos)" if avisos else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
