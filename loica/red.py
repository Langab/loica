"""Cliente HTTP educado: robots.txt, crawl-delay, caché y user-agent identificado.

Las reglas de buena ciudadanía del proyecto viven aquí, en el código, no en un
documento. Ningún adaptador habla con internet sin pasar por este módulo.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.robotparser as robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

log = logging.getLogger("loica.red")

CONTACTO = "https://loica.cl/bot"  # cambiar por el dominio real cuando exista
USER_AGENT = f"LoicaBot/0.1 (agenda de eventos de Santiago; +{CONTACTO})"

DIR_CACHE = Path(__file__).resolve().parent.parent / "datos" / "cache"
DIR_CACHE.mkdir(parents=True, exist_ok=True)


class ClienteEducado:
    """Un cliente por dominio, que recuerda cuándo fue su última petición."""

    _ultima_peticion: dict[str, float] = {}
    _robots: dict[str, robotparser.RobotFileParser | None] = {}

    def __init__(self, crawl_delay_seg: float = 2.0, timeout: int = 20, usar_cache: bool = True):
        self.crawl_delay = crawl_delay_seg
        self.timeout = timeout
        self.usar_cache = usar_cache
        self.sesion = requests.Session()
        self.sesion.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "es-CL,es;q=0.9",
        })

    # -- robots.txt ---------------------------------------------------------
    def _robots_de(self, url: str) -> robotparser.RobotFileParser | None:
        dominio = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        if dominio in self._robots:
            return self._robots[dominio]

        parser = robotparser.RobotFileParser()
        try:
            respuesta = self.sesion.get(urljoin(dominio, "/robots.txt"), timeout=self.timeout)
            if respuesta.status_code == 200:
                parser.parse(respuesta.text.splitlines())
            else:
                parser = None  # sin robots.txt no hay prohibición declarada
        except requests.RequestException:
            parser = None

        self._robots[dominio] = parser
        return parser

    def permitido(self, url: str) -> bool:
        parser = self._robots_de(url)
        if parser is None:
            return True
        return parser.can_fetch(USER_AGENT, url)

    def delay_declarado(self, url: str) -> float:
        """Si el sitio declara Crawl-delay, mandan ellos (ej. Las Condes pide 10 s)."""
        parser = self._robots_de(url)
        if parser is None:
            return self.crawl_delay
        try:
            declarado = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*")
        except Exception:
            declarado = None
        return max(float(declarado or 0), self.crawl_delay)

    # -- caché en disco -----------------------------------------------------
    def _ruta_cache(self, url: str) -> Path:
        return DIR_CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")

    def _leer_cache(self, url: str, max_edad_seg: int) -> dict | None:
        ruta = self._ruta_cache(url)
        if not ruta.exists():
            return None
        if time.time() - ruta.stat().st_mtime > max_edad_seg:
            return None
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _guardar_cache(self, url: str, contenido: str, status: int) -> None:
        try:
            self._ruta_cache(url).write_text(
                json.dumps({"url": url, "status": status, "texto": contenido}),
                encoding="utf-8",
            )
        except OSError as e:
            log.debug("No se pudo cachear %s: %s", url, e)

    # -- petición -----------------------------------------------------------
    def obtener(self, url: str, params: dict | None = None,
                max_edad_cache_seg: int = 6 * 3600,
                reintentos: int = 2) -> requests.Response | None:
        """GET respetuoso. Devuelve None si robots lo prohíbe o si falla."""
        if not self.permitido(url):
            log.warning("robots.txt prohíbe %s — se omite", url)
            return None

        url_completa = url
        if params:
            pedido = requests.Request("GET", url, params=params).prepare()
            url_completa = pedido.url

        if self.usar_cache:
            cacheado = self._leer_cache(url_completa, max_edad_cache_seg)
            if cacheado:
                log.debug("caché: %s", url_completa)
                falsa = requests.Response()
                falsa.status_code = cacheado["status"]
                falsa._content = cacheado["texto"].encode("utf-8")
                falsa.url = url_completa
                falsa.encoding = "utf-8"
                return falsa

        dominio = urlparse(url).netloc
        espera = self.delay_declarado(url)
        transcurrido = time.time() - self._ultima_peticion.get(dominio, 0)
        if transcurrido < espera:
            time.sleep(espera - transcurrido)

        for intento in range(reintentos + 1):
            try:
                respuesta = self.sesion.get(url, params=params, timeout=self.timeout)
                self._ultima_peticion[dominio] = time.time()

                if respuesta.status_code == 429 or respuesta.status_code >= 500:
                    if intento < reintentos:
                        pausa = espera * (2 ** (intento + 1))
                        log.warning("%s devolvió %s — reintento en %.0fs",
                                    dominio, respuesta.status_code, pausa)
                        time.sleep(pausa)
                        continue

                if respuesta.ok and self.usar_cache:
                    self._guardar_cache(url_completa, respuesta.text, respuesta.status_code)
                return respuesta

            except requests.RequestException as e:
                self._ultima_peticion[dominio] = time.time()
                if intento < reintentos:
                    time.sleep(espera * (2 ** (intento + 1)))
                    continue
                log.error("Falló %s: %s", url, e)
                return None
        return None

    def json(self, url: str, params: dict | None = None, **kw) -> list | dict | None:
        respuesta = self.obtener(url, params=params, **kw)
        if respuesta is None or not respuesta.ok:
            return None
        try:
            return respuesta.json()
        except ValueError:
            return None
