"""Almacén SQLite: histórico local de eventos, con estado y trazabilidad.

SQLite ahora porque no necesita servidor ni cuesta nada. Cuando el MVP esté en
pie, este mismo esquema se sube a Supabase (las columnas ya calzan).
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, date
from pathlib import Path

from .modelo import Evento

log = logging.getLogger("loica.almacen")

RUTA_DB = Path(__file__).resolve().parent.parent / "datos" / "eventos.db"

# La copia de la base que viaja en git. La SQLite es local y no se versiona
# (es binaria y cambia entera cada día); esto es la misma tabla `eventos`, una
# línea JSON por evento, ordenada por hash para que el diff de cada corrida
# muestre solo lo que cambió. Es lo que permite que la corrida viva en GitHub
# Actions, donde cada día se parte de un runner vacío: se restaura desde acá,
# se trabaja en SQLite y al final se vuelve a volcar. En el Mac cumple el rol
# inverso: después de `git pull`, la base local se pone al día sola.
RUTA_ESTADO = Path(__file__).resolve().parent.parent / "datos" / "eventos.jsonl"

# Un evento sigue vigente mientras no haya TERMINADO. La vigencia se medía por
# `inicio`, y con eso una exposición que abrió el 18 de julio y cierra el 27 de
# septiembre desaparecía del sitio el 19 de julio: la pregunta del usuario es
# "¿esto todavía se puede ver?", y esa la contesta la fecha de término. Eran 144
# eventos ya guardados —temporadas de teatro y muestras en curso— invisibles en
# el mapa, y es la forma normal de publicar de un museo.
#
# `fin` lo ponen colapsar_multidia (una serie de días seguidos) y las fuentes
# que declaran temporada. Sin `fin`, manda `inicio` como siempre.
SQL_VIGENTE = "COALESCE(NULLIF(fin, ''), inicio) >= date('now', 'localtime')"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS eventos (
    hash_dedup                TEXT PRIMARY KEY,
    titulo                    TEXT NOT NULL,
    categoria                 TEXT,
    descripcion_corta         TEXT,
    inicio                    TEXT,
    fin                       TEXT,
    todo_el_dia               INTEGER DEFAULT 0,
    lugar_nombre              TEXT,
    lugar_direccion           TEXT,
    comuna                    TEXT,
    lat                       REAL,
    lon                       REAL,
    precio_clp                INTEGER,
    es_gratis                 INTEGER,
    precio_texto              TEXT,
    fuente_tipo               TEXT,
    fuente_nombre             TEXT,
    fuente_url                TEXT NOT NULL,
    link_entradas             TEXT,
    imagen_url                TEXT,
    id_externo                TEXT,
    fecha_extraccion          TEXT,
    fecha_ultima_verificacion TEXT,
    visto_por_ultima_vez      TEXT,
    estado                    TEXT DEFAULT 'borrador'
);
CREATE INDEX IF NOT EXISTS idx_eventos_inicio ON eventos(inicio);
CREATE INDEX IF NOT EXISTS idx_eventos_estado ON eventos(estado);
CREATE INDEX IF NOT EXISTS idx_eventos_comuna ON eventos(comuna);

CREATE TABLE IF NOT EXISTS corridas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    momento         TEXT,
    fuente          TEXT,
    encontrados     INTEGER,
    nuevos          INTEGER,
    actualizados    INTEGER,
    descartados     INTEGER,
    error           TEXT,
    duracion_seg    REAL
);

-- Qué copia de datos/eventos.jsonl tiene cargada esta base (ver volcar).
CREATE TABLE IF NOT EXISTS meta (
    clave   TEXT PRIMARY KEY,
    valor   TEXT
);
"""


class Almacen:
    def __init__(self, ruta: Path | str = RUTA_DB,
                 ruta_estado: Path | str = RUTA_ESTADO):
        self.ruta = Path(ruta)
        self.ruta_estado = Path(ruta_estado)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.ruta)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)
        self.con.commit()
        self._restaurar_si_hace_falta()

    # -- la copia que viaja en git ------------------------------------------
    def _huella_estado(self) -> str | None:
        if not self.ruta_estado.exists():
            return None
        return hashlib.sha1(self.ruta_estado.read_bytes()).hexdigest()

    def _meta(self, clave: str) -> str | None:
        fila = self.con.execute("SELECT valor FROM meta WHERE clave = ?", (clave,)).fetchone()
        return fila[0] if fila else None

    def _poner_meta(self, clave: str, valor: str) -> None:
        self.con.execute("INSERT OR REPLACE INTO meta (clave, valor) VALUES (?, ?)",
                         (clave, valor))

    def _restaurar_si_hace_falta(self) -> None:
        """Carga datos/eventos.jsonl cuando la base no lo tiene todavía.

        Se decide por la huella del archivo y no por su fecha: `git pull` le
        pone al archivo la hora del pull, no la del dato. Si la huella es la
        misma que se guardó al volcar, la base ya tiene exactamente esto y no
        se toca. Se recarga entera en dos casos: la base está vacía (un runner
        recién clonado, o alguien borró datos/eventos.db para ponerse al día)
        o el archivo cambió por debajo (un pull trajo la corrida de la nube).
        """
        huella = self._huella_estado()
        if huella is None:
            return
        cuantos = self.con.execute("SELECT COUNT(*) FROM eventos").fetchone()[0]
        if cuantos and huella == self._meta("huella_estado"):
            return
        cargados = self.restaurar()
        if cargados:
            self._poner_meta("huella_estado", huella)
            self.con.commit()
            log.info("Base restaurada desde %s: %d eventos (%s)", self.ruta_estado.name,
                     cargados, "la base estaba vacía" if not cuantos
                     else "la copia en git cambió")

    def restaurar(self) -> int:
        """Reemplaza la tabla `eventos` con lo que hay en datos/eventos.jsonl."""
        filas = []
        with self.ruta_estado.open(encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    filas.append(json.loads(linea))
        if not filas:
            # Un archivo vacío no es una base vacía: no se borra nada por él.
            return 0
        columnas = [c[1] for c in self.con.execute("PRAGMA table_info(eventos)")]
        # Solo las columnas que la base conoce: si el archivo viene de una
        # versión con una columna de más, se ignora en vez de reventar.
        nombres = [c for c in columnas if c in filas[0]]
        marcadores = ",".join("?" * len(nombres))
        self.con.execute("DELETE FROM eventos")
        self.con.executemany(
            f"INSERT OR REPLACE INTO eventos ({','.join(nombres)}) VALUES ({marcadores})",
            ([fila.get(c) for c in nombres] for fila in filas),
        )
        self.con.commit()
        return len(filas)

    def volcar(self) -> Path:
        """Escribe datos/eventos.jsonl con la tabla completa, ordenada por hash.

        Lo llaman run_diario.py al terminar y run_todo.py antes de publicar.
        La tabla `corridas` no viaja: es el registro de cada corrida y solo la
        lee el diagnóstico del mismo día.
        """
        self.ruta_estado.parent.mkdir(parents=True, exist_ok=True)
        filas = self.con.execute("SELECT * FROM eventos ORDER BY hash_dedup").fetchall()
        with self.ruta_estado.open("w", encoding="utf-8") as f:
            for fila in filas:
                f.write(json.dumps(dict(fila), ensure_ascii=False, sort_keys=True) + "\n")
        self._poner_meta("huella_estado", self._huella_estado() or "")
        self.con.commit()
        return self.ruta_estado

    def guardar(self, evento: Evento) -> str:
        """Inserta o actualiza. Devuelve 'nuevo' | 'actualizado'.

        Nunca pisa el estado de curaduría: si el curador ya publicó o descartó
        un evento, una corrida posterior no lo devuelve a borrador.
        """
        d = evento.como_dict()
        ahora = datetime.now().isoformat()
        existente = self.con.execute(
            "SELECT hash_dedup, estado FROM eventos WHERE hash_dedup = ?",
            (d["hash_dedup"],),
        ).fetchone()

        if existente:
            self.con.execute(
                # COALESCE en lat/lon: si la corrida nueva no trae coordenadas,
                # no se borran las que ya teníamos.
                #
                # fuente_url SÍ se refresca: es el link que sostiene la
                # atribución, y cuando un adaptador se arregla (o el sitio
                # cambia de rutas) el link viejo tiene que corregirse solo en la
                # siguiente corrida. Lo que llega acá ya pasó `es_valido()`.
                """UPDATE eventos SET
                       titulo = ?, categoria = ?, descripcion_corta = ?,
                       inicio = ?, fin = ?, lugar_nombre = ?, lugar_direccion = ?,
                       comuna = ?, lat = COALESCE(?, lat), lon = COALESCE(?, lon),
                       precio_clp = ?, es_gratis = ?, precio_texto = ?,
                       fuente_url = ?, link_entradas = ?, imagen_url = ?,
                       fecha_ultima_verificacion = ?, visto_por_ultima_vez = ?
                   WHERE hash_dedup = ?""",
                (d["titulo"], d["categoria"], d["descripcion_corta"],
                 d["inicio"], d["fin"], d["lugar_nombre"], d["lugar_direccion"],
                 d["comuna"], d["lat"], d["lon"], d["precio_clp"],
                 None if d["es_gratis"] is None else int(d["es_gratis"]),
                 d["precio_texto"], d["fuente_url"], d["link_entradas"], d["imagen_url"],
                 ahora, ahora, d["hash_dedup"]),
            )
            self.con.commit()
            return "actualizado"

        self.con.execute(
            """INSERT INTO eventos (
                   hash_dedup, titulo, categoria, descripcion_corta, inicio, fin,
                   todo_el_dia, lugar_nombre, lugar_direccion, comuna, lat, lon,
                   precio_clp, es_gratis, precio_texto, fuente_tipo, fuente_nombre,
                   fuente_url, link_entradas, imagen_url, id_externo,
                   fecha_extraccion, fecha_ultima_verificacion,
                   visto_por_ultima_vez, estado
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d["hash_dedup"], d["titulo"], d["categoria"], d["descripcion_corta"],
             d["inicio"], d["fin"], int(d["todo_el_dia"]), d["lugar_nombre"],
             d["lugar_direccion"], d["comuna"], d["lat"], d["lon"], d["precio_clp"],
             None if d["es_gratis"] is None else int(d["es_gratis"]),
             d["precio_texto"], d["fuente_tipo"], d["fuente_nombre"], d["fuente_url"],
             d["link_entradas"], d["imagen_url"], d["id_externo"],
             d["fecha_extraccion"], d["fecha_ultima_verificacion"], ahora,
             "revisar_fecha" if evento.necesita_fecha else "borrador"),
        )
        self.con.commit()
        return "nuevo"

    def registrar_corrida(self, fuente: str, encontrados: int, nuevos: int,
                          actualizados: int, descartados: int,
                          error: str | None, duracion: float) -> None:
        self.con.execute(
            """INSERT INTO corridas (momento, fuente, encontrados, nuevos,
                                     actualizados, descartados, error, duracion_seg)
               VALUES (?,?,?,?,?,?,?,?)""",
            (datetime.now().isoformat(), fuente, encontrados, nuevos,
             actualizados, descartados, error, round(duracion, 1)),
        )
        self.con.commit()

    def caducar_pasados(self) -> int:
        """Marca como caducados los eventos que ya terminaron (ver SQL_VIGENTE)."""
        cursor = self.con.execute(
            "UPDATE eventos SET estado = 'caducado' "
            "WHERE COALESCE(NULLIF(fin, ''), inicio) < ? AND estado != 'caducado'",
            (date.today().isoformat(),),
        )
        self.con.commit()
        return cursor.rowcount

    def revivir_vigentes(self) -> int:
        """Devuelve a borrador lo que se caducó antes de tiempo.

        La regla vieja caducaba por `inicio`, así que la base quedó con
        temporadas y exposiciones marcadas 'caducado' que en realidad siguen
        en cartelera. Sin esto, arreglar la regla no las recupera: quedan
        enterradas hasta que la fuente las vuelva a publicar.
        """
        cursor = self.con.execute(
            "UPDATE eventos SET estado = 'borrador' "
            "WHERE estado = 'caducado' AND COALESCE(NULLIF(fin, ''), inicio) >= ?",
            (date.today().isoformat(),),
        )
        self.con.commit()
        return cursor.rowcount

    def nuevos_de_hoy(self) -> list[sqlite3.Row]:
        return self.con.execute(
            """SELECT * FROM eventos
               WHERE date(fecha_extraccion) = date('now', 'localtime')
                 AND estado = 'borrador'
               ORDER BY comuna, inicio""",
        ).fetchall()

    def pendientes_de_revision(self) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM eventos WHERE estado = 'borrador' "
            "AND COALESCE(NULLIF(fin, ''), inicio) >= ? ORDER BY inicio",
            (date.today().isoformat(),),
        ).fetchall()

    def resumen(self) -> dict:
        fila = self.con.execute(
            """SELECT
                   COUNT(*) AS total,
                   SUM(CASE WHEN estado = 'borrador'  THEN 1 ELSE 0 END) AS borradores,
                   SUM(CASE WHEN estado = 'publicado' THEN 1 ELSE 0 END) AS publicados,
                   SUM(CASE WHEN es_gratis = 1 AND estado != 'caducado' THEN 1 ELSE 0 END) AS gratis,
                   SUM(CASE WHEN """ + SQL_VIGENTE + """ THEN 1 ELSE 0 END) AS vigentes
               FROM eventos""",
        ).fetchone()
        return dict(fila)

    def cerrar(self) -> None:
        self.con.close()
