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


# Cuántas peticiones seguidas pueden fallar a nivel de conexión (timeout,
# conexión rechazada o cortada) antes de dar el dominio por muerto por el
# resto de la corrida. Un sitio que desde la IP del runner no responde nada
# —ni siquiera un 403— cuesta 72 segundos por URL (20 s de timeout, tres
# intentos y las esperas entre medio), y una fuente con cincuenta fichas
# son sesenta minutos de corrida para cero eventos. Tres bastan para
# saberlo; mañana se vuelve a intentar desde cero.
FALLOS_PARA_CORTAR = 3


class ClienteEducado:
    """Un cliente por dominio, que recuerda cuándo fue su última petición."""

    _ultima_peticion: dict[str, float] = {}
    _robots: dict[str, robotparser.RobotFileParser | None] = {}
    # Fallos de conexión seguidos por dominio. Es de clase a propósito: dos
    # fuentes del mismo dominio comparten el veredicto dentro de una corrida.
    _fallos_seguidos: dict[str, int] = {}
    _cortados: set[str] = set()

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
                reintentos: int = 2, json_cuerpo: dict | None = None,
                form_cuerpo: dict | None = None,
                cabeceras: dict | None = None) -> requests.Response | None:
        """GET respetuoso, o POST si se le pasa `json_cuerpo` o `form_cuerpo`.

        Algunas APIs reciben los filtros en el cuerpo y no en la query
        (Passline pide {"country": "chile"} por POST). Se sigue pasando por
        robots.txt, crawl-delay y caché igual que un GET: el método cambia,
        las reglas de buena ciudadanía no.

        `form_cuerpo` y `cabeceras` existen por Banco Ripley, que enruta todo
        su catálogo por un solo endpoint y dice QUÉ pedir en cabeceras
        (`x-path-api`, `x-method-api`) con el cuerpo en form-urlencoded. Es
        público y sin credencial —lo llama su propia web abierta— pero no
        entra en el molde de GET-con-params ni en el de POST-con-JSON.
        """
        if not self.permitido(url):
            log.warning("robots.txt prohíbe %s — se omite", url)
            return None

        dominio = urlparse(url).netloc
        if dominio in self._cortados:
            log.debug("%s no responde en esta corrida — se omite %s", dominio, url)
            return None

        url_completa = url
        if params:
            pedido = requests.Request("GET", url, params=params).prepare()
            url_completa = pedido.url
        if json_cuerpo is not None:
            # El cuerpo forma parte de la identidad del recurso para la caché:
            # dos POST distintos al mismo endpoint no son la misma respuesta.
            url_completa = f"{url_completa}#{json.dumps(json_cuerpo, sort_keys=True)}"
        if form_cuerpo is not None or cabeceras:
            # Lo mismo, y acá pesa más: en Ripley TODAS las peticiones van a la
            # misma URL y lo único que las distingue es la cabecera x-path-api.
            # Sin esto la caché devolvería el primer catálogo para cualquier
            # pedido posterior.
            firma = json.dumps([form_cuerpo or {}, cabeceras or {}], sort_keys=True)
            url_completa = f"{url_completa}#{firma}"

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

        espera = self.delay_declarado(url)
        transcurrido = time.time() - self._ultima_peticion.get(dominio, 0)
        if transcurrido < espera:
            time.sleep(espera - transcurrido)

        for intento in range(reintentos + 1):
            try:
                if form_cuerpo is not None:
                    respuesta = self.sesion.post(url, params=params, data=form_cuerpo,
                                                 headers=cabeceras, timeout=self.timeout)
                elif json_cuerpo is not None:
                    respuesta = self.sesion.post(url, params=params, json=json_cuerpo,
                                                 headers=cabeceras, timeout=self.timeout)
                else:
                    respuesta = self.sesion.get(url, params=params, headers=cabeceras,
                                                timeout=self.timeout)
                self._ultima_peticion[dominio] = time.time()

                if respuesta.status_code == 429 or respuesta.status_code >= 500:
                    if intento < reintentos:
                        pausa = espera * (2 ** (intento + 1))
                        log.warning("%s devolvió %s — reintento en %.0fs",
                                    dominio, respuesta.status_code, pausa)
                        time.sleep(pausa)
                        continue

                # Respondió, aunque sea un 403: el dominio está vivo.
                self._fallos_seguidos[dominio] = 0
                if respuesta.ok and self.usar_cache:
                    self._guardar_cache(url_completa, respuesta.text, respuesta.status_code)
                return respuesta

            except requests.RequestException as e:
                self._ultima_peticion[dominio] = time.time()
                if intento < reintentos:
                    time.sleep(espera * (2 ** (intento + 1)))
                    continue
                log.error("Falló %s: %s", url, e)
                self._anotar_fallo(dominio)
                return None
        return None

    def _anotar_fallo(self, dominio: str) -> None:
        fallos = self._fallos_seguidos.get(dominio, 0) + 1
        self._fallos_seguidos[dominio] = fallos
        if fallos >= FALLOS_PARA_CORTAR and dominio not in self._cortados:
            self._cortados.add(dominio)
            log.warning("%s no responde (%d peticiones seguidas sin conexión): "
                        "se omite por el resto de la corrida", dominio, fallos)

    def json(self, url: str, params: dict | None = None, **kw) -> list | dict | None:
        respuesta = self.obtener(url, params=params, **kw)
        if respuesta is None or not respuesta.ok:
            return None
        try:
            return respuesta.json()
        except ValueError:
            return None
