#!/usr/bin/env python3
"""Doble check de las direcciones investigadas antes de que lleguen al mapa.

    python3 scripts/verificar_lugares.py            # contrasta y muestra
    python3 scripts/verificar_lugares.py --escribir # deja el YAML aprobado

El circuito completo de la georreferenciación tiene tres pasos y este es el
del medio:

  1. `revisar_extraccion.py` deja la cola de lugares sin pin exacto, ordenada
     por cuántos eventos arregla cada uno.
  2. Alguien —una persona o una sesión de Claude— los busca en internet y
     anota la dirección CON la URL de donde salió, en
     `datos/revision/investigacion_lugares_AAAA-MM-DD.yaml`.
  3. Esto: cada dirección investigada se resuelve contra el catastro local de
     OpenStreetMap (`datos/indice_osm.db`), que es una fuente independiente de
     la que la encontró. Solo lo que las dos vías confirman entra a
     `config/correcciones/lugares.yaml`.

Por qué el doble check y no confiar en la búsqueda: una dirección sacada de un
sitio web puede estar vieja, mal tipeada o ser de otra ciudad, y un pin
equivocado manda a una persona a una esquina donde no hay nada — eso es peor
que no tener pin. El catastro OSM no sabe qué buscó nadie: si dice que
"Merced 349" existe en Santiago y cae donde el sitio del teatro dice que cae,
son dos testigos que no se hablaron entre ellos.

Los cuatro veredictos que emite:

  confirmado   la dirección existe en el catastro y cae en la comuna
               declarada. Entra con coordenadas y `precision: correccion`.
  discrepa     el catastro la ubica lejos de donde dijo la investigación
               (más de TOPE_KM). NO entra el pin: queda anotado para mirar.
  sin_catastro el catastro no conoce esa calle o ese número. Entra igual
               pero SOLO con dirección y comuna, sin coordenadas: el
               geocodificador reintentará con ellas en cada corrida, y una
               dirección corregida ya es mejor que ninguna.
  descartado   la investigación misma dijo que no hay dato (no encontrado,
               ambiguo, no es un lugar, o fuera de la Región Metropolitana).

Lo que este script NO hace: inventar. Si la investigación no trajo dirección,
acá no aparece ninguna.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from loica.geo import COMUNAS, IndiceLocal  # noqa: E402
from loica.correcciones import Correcciones, normalizar_clave  # noqa: E402

DIR_REVISION = RAIZ / "datos" / "revision"
RUTA_SALIDA = DIR_REVISION / "propuesta_lugares.yaml"

# Cuánto se tolera que el catastro y la investigación no coincidan. Un edificio
# grande, un parque o una esquina se estiran unos cientos de metros; más allá
# de eso ya no están hablando del mismo lugar. Se eligió 1 km por lo mismo que
# en exportar_web: es más ancho que cualquier cuadra y más angosto que un error
# de geocodificación de verdad (los que se han visto van de 1,1 a 2,7 km).
TOPE_KM = 1.0

# Lo que la investigación misma marcó como "no hay dato". Se listan aparte en
# vez de ignorarlos en silencio: saber que un lugar NO tiene dirección
# publicada es un resultado, y evita que la próxima revisión lo busque de nuevo.
SIN_DATO = {"no_encontrado", "ambiguo", "no_es_lugar"}


def _km(lat1, lon1, lat2, lon2) -> float:
    """Distancia aproximada en km, suficiente dentro de la RM."""
    return (((lat1 - lat2) * 111) ** 2 + ((lon1 - lon2) * 92) ** 2) ** 0.5


def cargar_investigaciones() -> list[dict]:
    """Todos los investigacion_lugares_*.yaml, en orden de fecha."""
    lugares: list[dict] = []
    for ruta in sorted(DIR_REVISION.glob("investigacion_lugares_*.yaml")):
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        entradas = datos.get("lugares") if isinstance(datos, dict) else datos
        for entrada in entradas or []:
            if isinstance(entrada, dict) and entrada.get("lugar"):
                lugares.append({**entrada, "_archivo": ruta.name})
    return lugares


def verificar(entrada: dict, indice: IndiceLocal) -> dict:
    """Contrasta una dirección investigada contra el catastro OSM."""
    lugar = entrada["lugar"]
    resultado = entrada.get("resultado", "encontrado")
    direccion = (entrada.get("direccion") or "").strip()
    comuna = (entrada.get("comuna") or "").strip()

    if resultado in SIN_DATO or not direccion:
        return {"lugar": lugar, "veredicto": "descartado",
                "motivo": entrada.get("nota") or f"la investigación dijo: {resultado}"}

    # Fuera de la Región Metropolitana no se pone pin aunque la dirección sea
    # perfecta: el catálogo es de Santiago, y un evento de Valdivia con pin
    # exacto sigue siendo un evento que no corresponde publicar.
    if comuna and comuna not in COMUNAS:
        return {"lugar": lugar, "veredicto": "descartado",
                "motivo": f"comuna fuera de la RM: {comuna}"}

    del_catastro = indice.direccion(direccion, comuna)
    de_la_web = None
    if entrada.get("lat") is not None and entrada.get("lon") is not None:
        de_la_web = (float(entrada["lat"]), float(entrada["lon"]))

    ficha = {"lugar": lugar, "direccion": direccion, "comuna": comuna,
             "fuente_url": entrada.get("fuente_url", ""),
             "confianza": entrada.get("confianza", ""),
             "nota_investigacion": entrada.get("nota", "")}

    if del_catastro and de_la_web:
        distancia = _km(de_la_web[0], de_la_web[1], del_catastro[0], del_catastro[1])
        if distancia > TOPE_KM:
            return {**ficha, "veredicto": "discrepa",
                    "motivo": f"la web dice {de_la_web[0]:.5f},{de_la_web[1]:.5f} y el "
                              f"catastro {del_catastro[0]:.5f},{del_catastro[1]:.5f} "
                              f"({distancia:.1f} km)"}
        # Se queda con la del catastro: es la que se puede volver a verificar
        # mañana corriendo esto mismo, sin depender de que el sitio siga vivo.
        return {**ficha, "veredicto": "confirmado", "lat": del_catastro[0],
                "lon": del_catastro[1],
                "motivo": f"web y catastro coinciden dentro de {distancia * 1000:.0f} m"}

    if del_catastro:
        return {**ficha, "veredicto": "confirmado", "lat": del_catastro[0],
                "lon": del_catastro[1],
                "motivo": "la dirección existe en el catastro OSM y cae en su comuna"}

    if de_la_web:
        # Sin segundo testigo. Se aceptan las coordenadas solo si la propia
        # página las publicó Y la investigación quedó con confianza alta; si
        # no, entra la dirección sola y que la resuelva el geocodificador.
        if entrada.get("confianza") == "alta":
            return {**ficha, "veredicto": "confirmado", "lat": de_la_web[0],
                    "lon": de_la_web[1],
                    "motivo": "coordenadas publicadas por la propia fuente "
                              "(el catastro no conoce la dirección)"}
        return {**ficha, "veredicto": "sin_catastro",
                "motivo": "la fuente dio coordenadas pero con confianza "
                          f"{entrada.get('confianza')}: entra sin pin"}

    return {**ficha, "veredicto": "sin_catastro",
            "motivo": "el catastro OSM no conoce esa calle o ese número: "
                      "entra la dirección, el pin lo resolverá la corrida"}


def _escalar(texto: str) -> str:
    """Un valor YAML de una sola línea, sin importar qué traiga adentro.

    Las notas llevan URLs y dos puntos, que en YAML abren un mapa; y si se
    dejan cortar en varias líneas hay que indentar la continuación o el
    archivo deja de parsear. Se emiten entre comillas simples y en una línea:
    feo de leer en el editor, pero un YAML roto en config/correcciones/ se
    lleva TODAS las correcciones del archivo, no solo la entrada mala.
    """
    return "'" + " ".join(texto.split()).replace("'", "''") + "'"


def escribir_propuesta(fichas: list[dict], ya_estan: set[str]) -> Path:
    """El YAML listo para pegar en config/correcciones/lugares.yaml."""
    hoy = max((f.get("_fecha") or "") for f in fichas) or ""
    lineas = [
        "# Propuesta de correcciones de LUGAR verificadas por doble vía:",
        "# investigación web (con URL) + catastro local de OpenStreetMap.",
        "# La armó scripts/verificar_lugares.py; revisar y pegar en",
        "# config/correcciones/lugares.yaml bajo la clave `lugares:`.",
        "#",
        "# Las entradas SIN lat/lon son las que el catastro no pudo confirmar:",
        "# igual sirven, porque una dirección corregida hace que la corrida",
        "# siguiente geocodifique bien lo que hoy cae al centro de la comuna.",
        "",
        "lugares:",
    ]
    for f in fichas:
        if normalizar_clave(f["lugar"]) in ya_estan:
            continue
        # La clave se escapa igual que los valores: media docena de sedes
        # municipales traen "#" en el nombre ("JJ. VV. Simón Bolívar Av. Las
        # Torres # 840") y en YAML ese numeral abre un comentario, se come
        # el resto de la línea y deja el archivo sin parsear.
        lineas.append(f"  {_escalar(f['lugar'])}:")
        lineas.append(f"    direccion: {_escalar(f['direccion'])}")
        if f.get("comuna"):
            lineas.append(f"    comuna: {_escalar(f['comuna'])}")
        if f.get("lat") is not None:
            lineas.append(f"    lat: {f['lat']:.5f}")
            lineas.append(f"    lon: {f['lon']:.5f}")
        partes = [f["motivo"]]
        if f.get("nota_investigacion"):
            partes.append(f["nota_investigacion"])
        if f.get("fuente_url"):
            partes.append(f"fuente: {f['fuente_url']}")
        lineas.append(f"    nota: {_escalar(' · '.join(partes))}")
        lineas.append("")
    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    RUTA_SALIDA.write_text("\n".join(lineas), encoding="utf-8")
    return RUTA_SALIDA


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--escribir", action="store_true",
                        help="deja la propuesta en datos/revision/propuesta_lugares.yaml")
    parser.add_argument("--detalle", action="store_true",
                        help="muestra el veredicto de cada lugar")
    args = parser.parse_args()

    investigados = cargar_investigaciones()
    if not investigados:
        print("No encontré ningún datos/revision/investigacion_lugares_*.yaml.")
        return 1

    indice = IndiceLocal()
    if not indice.con:
        print("Sin datos/indice_osm.db no hay con qué contrastar. Bájalo con:")
        print("  gh release download indice-osm --pattern indice_osm.db --dir datos")
        return 1

    fichas = [verificar(e, indice) for e in investigados]
    por_veredicto: dict[str, list[dict]] = {}
    for f in fichas:
        por_veredicto.setdefault(f["veredicto"], []).append(f)

    ya_estan = set(Correcciones().lugares)
    aprobados = [f for f in fichas if f["veredicto"] in ("confirmado", "sin_catastro")]
    nuevos = [f for f in aprobados if normalizar_clave(f["lugar"]) not in ya_estan]

    print(f"Investigados: {len(investigados)} lugares")
    for veredicto in ("confirmado", "sin_catastro", "discrepa", "descartado"):
        cuantos = len(por_veredicto.get(veredicto, []))
        if cuantos:
            print(f"  {veredicto:13s} {cuantos:4d}")
    print(f"\n  Aprobados para la memoria: {len(aprobados)} "
          f"({len(nuevos)} que no estaban)")

    if por_veredicto.get("discrepa"):
        print("\n  ⚠ Discrepan las dos vías — no se les pone pin:")
        for f in por_veredicto["discrepa"]:
            print(f"     · {f['lugar'][:50]:50s} {f['motivo']}")

    if args.detalle:
        for veredicto in ("confirmado", "sin_catastro", "descartado"):
            print(f"\n  --- {veredicto} ---")
            for f in por_veredicto.get(veredicto, []):
                print(f"     {f['lugar'][:48]:48s} {f.get('motivo','')[:70]}")

    if args.escribir:
        ruta = escribir_propuesta(aprobados, ya_estan)
        print(f"\n  Propuesta en {ruta.relative_to(RAIZ)} "
              f"({len(nuevos)} entradas nuevas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
