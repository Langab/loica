"""Almacén SQLite: histórico local de eventos, con estado y trazabilidad.

SQLite ahora porque no necesita servidor ni cuesta nada. Cuando el MVP esté en
pie, este mismo esquema se sube a Supabase (las columnas ya calzan).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, date
from pathlib import Path

from .modelo import Evento

RUTA_DB = Path(__file__).resolve().parent.parent / "datos" / "eventos.db"

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
"""


class Almacen:
    def __init__(self, ruta: Path | str = RUTA_DB):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.ruta)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)
        self.con.commit()

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
                """UPDATE eventos SET
                       titulo = ?, categoria = ?, descripcion_corta = ?,
                       inicio = ?, fin = ?, lugar_nombre = ?, lugar_direccion = ?,
                       comuna = ?, lat = COALESCE(?, lat), lon = COALESCE(?, lon),
                       precio_clp = ?, es_gratis = ?, precio_texto = ?,
                       link_entradas = ?, imagen_url = ?,
                       fecha_ultima_verificacion = ?, visto_por_ultima_vez = ?
                   WHERE hash_dedup = ?""",
                (d["titulo"], d["categoria"], d["descripcion_corta"],
                 d["inicio"], d["fin"], d["lugar_nombre"], d["lugar_direccion"],
                 d["comuna"], d["lat"], d["lon"], d["precio_clp"],
                 None if d["es_gratis"] is None else int(d["es_gratis"]),
                 d["precio_texto"], d["link_entradas"], d["imagen_url"],
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
        """Marca como caducados los eventos cuya fecha ya pasó."""
        cursor = self.con.execute(
            "UPDATE eventos SET estado = 'caducado' WHERE inicio < ? AND estado != 'caducado'",
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
            "SELECT * FROM eventos WHERE estado = 'borrador' AND inicio >= ? ORDER BY inicio",
            (date.today().isoformat(),),
        ).fetchall()

    def resumen(self) -> dict:
        fila = self.con.execute(
            """SELECT
                   COUNT(*) AS total,
                   SUM(CASE WHEN estado = 'borrador'  THEN 1 ELSE 0 END) AS borradores,
                   SUM(CASE WHEN estado = 'publicado' THEN 1 ELSE 0 END) AS publicados,
                   SUM(CASE WHEN es_gratis = 1 AND estado != 'caducado' THEN 1 ELSE 0 END) AS gratis,
                   SUM(CASE WHEN inicio >= date('now') THEN 1 ELSE 0 END) AS vigentes
               FROM eventos""",
        ).fetchone()
        return dict(fila)

    def cerrar(self) -> None:
        self.con.close()
