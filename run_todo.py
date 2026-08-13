#!/usr/bin/env python3
"""Corrida completa: eventos, descuentos, sitio y publicación. Un solo comando.

El proyecto tenía tres piezas sueltas que nadie encadenaba: `run_diario.py`
dejaba los eventos en la base, `run_descuentos.py` dejaba los descuentos de
banco en su JSON, y `exportar_web.py` armaba el sitio. La corrida programada
llamaba sólo a la primera, así que la base se actualizaba todas las mañanas y
la web se quedaba con los datos del día que alguien exportara a mano.

Peor: los dos catastros comiteaban por separado al mismo repositorio y se
pisaban entre ellos. Acá van en la misma corrida y en el mismo commit.

    python3 run_todo.py                  # todo: eventos, descuentos y publicar
    python3 run_todo.py --sin-publicar   # deja el sitio listo, no toca git
    python3 run_todo.py --solo-publicar  # sin extraer: exporta lo que ya hay
    python3 run_todo.py --sin-descuentos # sólo eventos
    python3 run_todo.py --fuente gam     # una sola fuente (se pasa a run_diario)
    python3 run_todo.py --forzar         # publica aunque caiga el volumen

La corrida completa son seis pasos: extraer eventos, extraer descuentos,
exportar el sitio, revisar la extracción (informe + colas de corrección en
datos/revision/, no bloquea), doble check (verificar_web.py, SÍ bloquea) y
publicar.

Después del push, GitHub Actions publica `web/` en Pages: no hay que hacer
nada más.

REGLA IMPORTANTE — sólo se comitea lo que produce el pipeline
=============================================================
Corre sin nadie mirando a las 11:00, así que NUNCA hace `git add -A`: si en
ese momento hay un archivo a medio editar, un `add -A` se lo llevaría al
repositorio. Se agregan únicamente las rutas de RUTAS_PUBLICABLES.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# Lo único que esta corrida tiene derecho a comitear: su propia salida.
RUTAS_PUBLICABLES = ["web/eventos.json", "web/descuentos.json", "web/e",
                     "datos/manual"]


def _correr(comando: list[str], titulo: str) -> bool:
    """Ejecuta un paso mostrando su salida en vivo. True si terminó bien."""
    print(f"\n{'=' * 62}\n  {titulo}\n{'=' * 62}", flush=True)
    resultado = subprocess.run(comando, cwd=RAIZ)
    if resultado.returncode != 0:
        print(f"\n  ✗ {titulo}: terminó con código {resultado.returncode}")
        return False
    return True


def _git(*args: str, capturar: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=RAIZ, text=True,
                          capture_output=capturar)


def paso_extraer(extra: list[str]) -> bool:
    return _correr([sys.executable, "run_diario.py", *extra], "1/6  Eventos")


def paso_descuentos(extra: list[str]) -> bool:
    """Los descuentos NO abortan la corrida si fallan.

    Son un catastro aparte: que Bci cambie su JSON no es razón para dejar sin
    actualizar la agenda de eventos, que es el corazón del proyecto.
    """
    if not _correr([sys.executable, "run_descuentos.py", *extra], "2/6  Descuentos"):
        print("    Se sigue igual: los eventos no dependen de esto.")
    return True


def paso_exportar() -> bool:
    return _correr([sys.executable, "exportar_web.py"], "3/6  Exportar el sitio")


def paso_revisar() -> bool:
    """La revisión del estado de extracción NO bloquea: es el insumo de
    curaduría (informe + colas de corrección en datos/revision/)."""
    if not _correr([sys.executable, "revisar_extraccion.py"], "4/6  Revisión"):
        print("    Se sigue igual: la revisión informa, no bloquea.")
    return True


def paso_verificar(forzar: bool) -> bool:
    """El doble check SÍ bloquea: si el sitio está roto o vacío, no hay push."""
    extra = ["--forzar"] if forzar else []
    return _correr([sys.executable, "verificar_web.py", *extra],
                   "5/6  Doble check")


def _resolver_generados() -> bool:
    """Resuelve el rebase cuando el choque es sólo en archivos generados.

    `web/eventos.json` y `web/descuentos.json` los regeneran los dos catastros
    todos los días, así que dos corridas seguidas chocan siempre aunque nadie
    haya editado nada. En un archivo derivado no hay nada que fusionar: gana la
    regeneración más nueva, que es la nuestra.

    Sólo se aplica si TODOS los archivos en conflicto son generados. Si el
    choque toca código o configuración, se aborta y decide una persona:
    resolver eso a ciegas sí borraría trabajo de verdad.
    """
    conflictivos = [linea.strip() for linea in
                    _git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
                    if linea.strip()]
    if not conflictivos:
        return False

    generados = {"web/eventos.json", "web/descuentos.json"}
    ajenos = [f for f in conflictivos
              if f not in generados and not f.startswith("web/e/")]
    if ajenos:
        print(f"  El conflicto toca archivos que no son generados: {', '.join(ajenos[:4])}")
        return False

    for archivo in conflictivos:
        # En un rebase, "theirs" es el commit que se está reaplicando: el nuestro.
        _git("checkout", "--theirs", "--", archivo)
        _git("add", "--", archivo)

    seguir = subprocess.run(["git", "rebase", "--continue"], cwd=RAIZ, text=True,
                            capture_output=True, env={"GIT_EDITOR": "true",
                                                      "PATH": "/usr/bin:/bin"})
    if seguir.returncode != 0:
        return False

    print(f"  Regenerados en conflicto, resueltos con la corrida nueva: "
          f"{', '.join(conflictivos)}")
    return True


def paso_publicar() -> bool:
    """Comitea y sube SOLO la salida del pipeline."""
    print(f"\n{'=' * 62}\n  6/6  Publicar\n{'=' * 62}", flush=True)

    existentes = [r for r in RUTAS_PUBLICABLES if (RAIZ / r).exists()]
    if not existentes:
        print("  No hay nada que publicar todavía.")
        return True

    _git("add", "--", *existentes)

    # --cached compara lo que está en el índice: si el export no cambió nada,
    # no se ensucia el historial con un commit vacío.
    if _git("diff", "--cached", "--quiet").returncode == 0:
        print("  El sitio no cambió desde la última publicación — no hay commit.")
        return True

    resumen = _git("diff", "--cached", "--shortstat").stdout.strip()
    mensaje = (f"Corrida del {datetime.now():%d-%m-%Y %H:%M}\n\n"
               f"Actualiza el sitio con la corrida automática. {resumen}\n")
    if _git("commit", "-q", "-m", mensaje).returncode != 0:
        print("  ✗ No pude comitear.")
        return False

    # Otra sesión pudo haber pusheado mientras corríamos: se integra antes de
    # subir, si no el push se rechaza por no ser fast-forward.
    #
    # --autostash es imprescindible acá: esto corre sin nadie mirando y el
    # árbol casi siempre tiene algo a medio editar, y `git rebase` se niega a
    # empezar con cambios sin comitear. Sin esto, cualquier archivo abierto
    # bloqueaba la publicación y el error decía "conflicto", que era mentira.
    _git("fetch", "origin", "--quiet")
    rama = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
    if _git("rev-parse", "--verify", f"origin/{rama}").returncode == 0:
        rebase = _git("rebase", "--autostash", f"origin/{rama}")
        if rebase.returncode != 0 and not _resolver_generados():
            _git("rebase", "--abort")
            print("  ✗ El remoto tiene cambios que chocan con estos.\n"
                  f"    {rebase.stderr.strip()[:200]}\n"
                  "    El commit quedó hecho localmente: resolvé y pusheá a mano.")
            return False

    push = _git("push", "origin", rama)
    if push.returncode != 0:
        print(f"  ✗ Falló el push:\n{push.stderr.strip()}\n"
              "    El commit está local, no se perdió nada.")
        return False

    print(f"  ✓ Publicado. {resumen}")
    print("    GitHub Actions se encarga de dejarlo en Pages.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Corrida completa: extraer, exportar y publicar.")
    parser.add_argument("--sin-publicar", action="store_true",
                        help="deja el sitio listo pero no toca git")
    parser.add_argument("--solo-publicar", action="store_true",
                        help="no extrae: exporta lo que ya está en la base")
    parser.add_argument("--sin-descuentos", action="store_true",
                        help="salta el catastro de descuentos de banco")
    parser.add_argument("--fuente", help="correr solo esta fuente")
    parser.add_argument("--forzar", action="store_true",
                        help="publica aunque el doble check acuse caída de volumen")
    parser.add_argument("--sin-cache", action="store_true")
    parser.add_argument("-v", "--verboso", action="store_true")
    args, _ = parser.parse_known_args()

    inicio = datetime.now()

    if not args.solo_publicar:
        extra = []
        if args.fuente:
            extra += ["--fuente", args.fuente]
        if args.sin_cache:
            extra.append("--sin-cache")
        if args.verboso:
            extra.append("-v")
        # Si TODAS las fuentes fallaron, run_diario devuelve 1. Publicar igual
        # sería pisar un sitio bueno con uno vacío.
        if not paso_extraer(extra):
            print("\n✗ La extracción falló entera — no se publica nada.")
            return 1

        if not args.sin_descuentos and not args.fuente:
            comunes = [a for a in extra if a in ("--sin-cache", "-v")]
            paso_descuentos(comunes)

    if not paso_exportar():
        print("\n✗ El export falló — no se publica nada.")
        return 1

    paso_revisar()

    if not paso_verificar(args.forzar):
        if args.sin_publicar:
            print("\n✗ El doble check falló. Igual no se iba a publicar "
                  "(--sin-publicar); el detalle quedó arriba.")
            return 1
        print("\n✗ El doble check falló — no se publica nada. El sitio "
              "anterior sigue en pie; el detalle quedó arriba.")
        return 1

    if args.sin_publicar:
        print("\n✓ Sitio listo en web/. No se publicó (--sin-publicar).")
        return 0

    if not paso_publicar():
        return 1

    print(f"\n✓ Todo listo en {(datetime.now() - inicio).seconds // 60} min.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
