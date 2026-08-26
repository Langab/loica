#!/usr/bin/env python3
"""Banco de pruebas de la hoja arrastrable: ¿se puede agarrar con el dedo?

    python3 scripts/verificar_hoja.py --etiqueta antes
    python3 scripts/verificar_hoja.py --etiqueta despues --comparar antes

Cuatro páginas tienen mapa arriba y una hoja de resultados abajo que en celular
sube y baja a tres alturas: mapa.html, cine.html, descuentos.html, talleres.html.
El encargo de este archivo es UNO: que "quedó arreglado" deje de ser una
impresión y pase a ser un número comparable entre dos corridas.

Por qué existe
--------------
El 22-08 el "no funciona en celular" del mapa resultó ser un `touch-action:none`
puesto de más: cancelaba el scroll de la lista y nadie lo notó hasta que un
humano puso el dedo. Un mes después el blanco que arrastra son 29px de tirador
y desde el contador o la lista no pasa nada. Las dos cosas son invisibles para
cualquier prueba que mire el HTML: hay que empujar de verdad y medir el alto.

Cada caso da un veredicto pasa/falla, no una impresión. El código de salida es
distinto de 0 si algo falla real, para que esto sea una puerta antes de
publicar —el mismo patrón de verificar_web.py: si esto falla, no hay push.

Qué es real y qué es simulacro
------------------------------
Esto importa más que el resumen bonito, así que va arriba y también sale
impreso en el informe:

- chromium: toque REAL. Los eventos entran por CDP (`Input.dispatchTouchEvent`),
  que es la misma cañería por donde entra un dedo. El navegador decide de
  verdad si el gesto scrollea la lista o mueve la hoja, y por eso este es el
  único navegador donde el caso 6 —la regresión del touch-action— se prueba
  en serio.
- webkit (el motor de Safari en iPhone, o sea el navegador que más importa):
  Playwright NO tiene arrastre táctil para webkit. Se corre en dos modos:
    · "puntero" — ratón de verdad, entrada real del navegador, pero llega como
      pointerType=mouse. Prueba la lógica; NO prueba la pelea entre el gesto y
      el scroll nativo, que es justo lo que se rompió antes.
    · "toque simulado" — eventos Pointer(touch)+Touch despachados desde la
      página. Mueve los listeners de la app, pero el navegador no participa:
      no hay arbitraje de gesto, no hay scroll nativo, no hay touch-action.
      Sus fallas NO cuentan para el código de salida y salen marcadas.
- firefox: solo el camino de puntero con ratón y consola limpia, que es lo que
  Playwright permite ahí sin inventar.

Ruido de consola, y qué NO mide este banco
------------------------------------------
Dos cosas del entorno ensuciaban el caso 14 y las dos se cortan en la red, no
filtrando texto: el beacon de Cloudflare Insights (que servido desde localhost
se cae por CORS, y que cada motor redacta distinto) se contesta con un 204, y
las fotos remotas de los talleres —S3 de las municipalidades, nunoadeportes,
huechuraba— se contestan con un PNG de 1×1.

Lo segundo es una decisión, no una comodidad: son cientos de idas a internet
por corrida y firefox ya trajo un webp a medio bajar y lo cantó como error de
consola. Un caso que a veces pasa según cómo venga la red no es una puerta, es
un dado.

El precio, dicho de frente: este banco NO prueba que las fotos existan ni que
carguen. Eso lo hace verificar_web.py, que valida las URL. Acá se mide la hoja,
y su alto sale de una fracción del contenedor, no de los bytes de una foto.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_WEB = RAIZ / "web"
DIR_INFORME = RAIZ / "informes" / "hoja-movil-2026-08-25"
BASE = "http://localhost:8777"

PAGINAS = [
    ("mapa", "mapa.html"),
    ("cine", "cine.html"),
    ("dctos", "descuentos.html"),
    ("tall", "talleres.html"),
]

# Los cuatro formatos del encargo. `ambito` dice qué batería corre en cada uno:
# no tiene sentido probar el arrastre en escritorio, donde la hoja es una
# columna al costado y el tirador está escondido a propósito.
FORMATOS = [
    {"clave": "iphone13", "nombre": "iPhone 13 vertical", "ancho": 390, "alto": 664,
     "celular": True, "ambito": "celular"},
    {"clave": "android360", "nombre": "Android chico 360×640", "ancho": 360, "alto": 640,
     "celular": True, "ambito": "celular"},
    {"clave": "acostado", "nombre": "iPhone 13 acostado", "ancho": 844, "alto": 390,
     "celular": True, "ambito": "acostado"},
    {"clave": "escritorio", "nombre": "Escritorio 1280×800", "ancho": 1280, "alto": 800,
     "celular": False, "ambito": "escritorio"},
]

# id, título, ámbito donde aplica. El orden es el del encargo y no se toca:
# comparar dos corridas exige que la fila 6 sea siempre la misma fila 6.
CASOS = [
    (1,  "reposo: el mapa se queda con la mayoría", "celular"),
    (2,  "subir desde el tirador (200px)", "celular"),
    (3,  "bajar desde el tirador (200px)", "celular"),
    (4,  "subir desde .conteo", "celular"),
    (5,  "bajar desde .lista con scrollTop 0", "celular"),
    (6,  "scroll de la lista SIN mover la hoja", "celular"),
    (7,  "arrastre corto (28px) cambia de tope", "celular"),
    (8,  "arrastrar bien abajo la esconde", "celular"),
    (9,  "el botón flotante la trae de vuelta", "celular"),
    (10, "sin salto por click fantasma", "celular"),
    (11, "teclado: flechas cambian tope, Escape esconde", "celular"),
    (12, "escritorio: columna al costado, sin tirador", "escritorio"),
    (13, "acostado: la lista se va al costado", "acostado"),
    (14, "consola sin errores", "*"),
]

# Los casos que dependen de empujar con el dedo. En el modo simulado de webkit
# se corren solo estos: los demás (reposo, teclado, disposición) ya los cubre
# el modo puntero, que sí es entrada real, y repetirlos solo infla la tabla.
CASOS_DE_ARRASTRE = {2, 3, 4, 5, 6, 7, 8, 9, 10}

# Ruido de consola que es del entorno y no del sitio. Se ignora POR LISTA, no
# por patrón amplio: el día que la página tire un error de verdad tiene que
# salir. Cada entrada lleva el porqué al lado.
RUIDO_CONOCIDO = [
    # El beacon de analítica sale del origen loicasantiago.cl; contra localhost
    # el preflight CORS lo rechaza. No es del sitio.
    "cloudflareinsights.com",
    "cdn-cgi/rum",
]

TOLERANCIA = 12      # px de holgura al comparar altos: redondeos y subpíxeles
CAMBIO_MINIMO = 40   # px: menos que esto no es "cambió de tope", es un temblor


# PNG transparente de 1×1, para tapar las fotos remotas sin dejar rota la <img>.
PNG_1PX = __import__("base64").b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


class NoSePuede(Exception):
    """El navegador no da la herramienta para probar este caso.

    No es lo mismo que fallar. Un caso que el motor no deja ejercer se informa
    `na` con el motivo: contarlo como falla ensuciaría el número que decide si
    se publica, y contarlo como aprobado sería vender por probado algo que
    nunca se tocó."""


# --------------------------------------------------------------------------
# Lo que se mide. Todo en una sola ida al navegador: cada evaluate cuesta un
# viaje, y en un banco de 4 páginas × 3 navegadores × 4 formatos los viajes
# son la mitad del reloj.
# --------------------------------------------------------------------------
JS_GEOMETRIA = """() => {
  const panel = document.getElementById('panel') || document.querySelector('.panel-lista');
  if(!panel) return null;
  const lista = document.getElementById('lista') || document.querySelector('.lista');
  const tirador = document.getElementById('tirador') || document.querySelector('.tirador');
  const conteo = document.querySelector('.conteo');
  const caja = panel.getBoundingClientRect();
  const madre = panel.parentElement.getBoundingClientRect();
  /* Lo que se VE de la hoja. Si está corrida fuera de pantalla con un
     translate, el alto sigue siendo el mismo y "está escondida" solo se nota
     mirando cuánto de ella cae dentro del viewport. Esa es la única medida
     que sirve para el caso 8 sin amarrarse al nombre de una clase CSS. */
  const altoDentro = Math.max(0, Math.min(caja.bottom, innerHeight) - Math.max(caja.top, 0));
  const anchoDentro = Math.max(0, Math.min(caja.right, innerWidth) - Math.max(caja.left, 0));
  const centro = e => {
    if(!e) return null;
    const q = e.getBoundingClientRect();
    const est = getComputedStyle(e);
    const seVe = est.display !== 'none' && est.visibility !== 'hidden' && q.height > 0;
    return {x: Math.round(q.x + q.width/2), y: Math.round(q.y + q.height/2),
            arriba: Math.round(q.y), ancho: Math.round(q.width),
            alto: Math.round(q.height), seVe};
  };
  return {
    alto: Math.round(caja.height),
    visible: anchoDentro > 1 ? Math.round(altoDentro) : 0,
    izq: Math.round(caja.left),
    arriba: Math.round(caja.top),
    disponible: Math.round(madre.height),
    anchoMadre: Math.round(madre.width),
    pantalla: innerHeight,
    anchoPantalla: innerWidth,
    lista: lista ? {arriba: Math.round(lista.scrollTop),
                    total: Math.round(lista.scrollHeight),
                    caja: Math.round(lista.clientHeight),
                    accionTactil: getComputedStyle(lista).touchAction,
                    centro: centro(lista)} : null,
    tirador: centro(tirador),
    conteo: centro(conteo),
    hayFijar: typeof window.fijarPanel === 'function'
  };
}"""

# Espera de verdad: no un sleep, sino "el alto dejó de moverse". Pide tres
# muestras iguales seguidas y un mínimo de cuatro cuadros, porque justo después
# de fijar() la transición todavía no arrancó y dos muestras iguales mentirían.
JS_QUIETO = """() => {
  const p = document.getElementById('panel') || document.querySelector('.panel-lista');
  if(!p) return true;
  const c = p.getBoundingClientRect();
  /* Se miran el alto Y el borde de arriba. Esconderla es un `transform`, no un
     cambio de alto: mirando solo el alto, la hoja "ya estaba quieta" desde el
     primer cuadro del deslizamiento y las medidas salían a mitad de camino
     —35 px asomando cuando ya iba saliendo, 170 después de Escape—. Dos casos
     dados por fallados por medir antes de tiempo. */
  const k = Math.round(c.height * 10) + ':' + Math.round(c.top * 10);
  const s = window.__q = window.__q || {n: 0, k: null, t: 0};
  s.t++;
  if(s.k === k) s.n++; else { s.n = 0; s.k = k; }
  return s.t >= 4 && s.n >= 3;
}"""

# La página está lista cuando la lista tiene contenido de sobra para scrollear:
# es exactamente la condición que los casos necesitan, y no depende de cómo se
# llame la tarjeta en cada página (mapa y talleres usan .tarjeta, cine .cine,
# descuentos .dcto dentro de un envoltorio que anima).
JS_LISTA_CARGADA = """() => {
  const l = document.getElementById('lista') || document.querySelector('.lista');
  return !!l && l.scrollHeight > l.clientHeight + 60;
}"""

# Candidatos a "botón que trae la hoja de vuelta": cualquier cosa clickeable,
# visible, con área táctil de verdad, que NO viva dentro de la hoja. No se
# busca por nombre porque el botón todavía no existe y no hay que adivinarle
# la clase al agente que lo va a escribir: se compara el antes y el después de
# esconder la hoja, y lo que apareció es el candidato.
JS_BOTONES_FUERA = """() => {
  const panel = document.getElementById('panel') || document.querySelector('.panel-lista');
  const fuera = [];
  for(const el of document.querySelectorAll('button,[role="button"],a[href]')){
    if(panel && panel.contains(el)) continue;
    const c = el.getBoundingClientRect();
    if(c.width < 24 || c.height < 24) continue;
    const est = getComputedStyle(el);
    if(est.display === 'none' || est.visibility === 'hidden' || +est.opacity < 0.05) continue;
    if(c.bottom < 0 || c.top > innerHeight || c.right < 0 || c.left > innerWidth) continue;
    const txt = (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 40);
    fuera.push({clave: (el.id || '') + '|' + el.className.toString().slice(0,60) + '|' + txt,
                txt, id: el.id, clase: el.className.toString().slice(0, 60),
                x: Math.round(c.x + c.width/2), y: Math.round(c.y + c.height/2),
                flotante: est.position === 'fixed' || est.position === 'absolute'});
  }
  return fuera;
}"""

# Parche SOLO para el modo simulado de webkit. Un PointerEvent fabricado a mano
# trae un pointerId que el navegador no conoce, y setPointerCapture le tira
# NotFoundError encima: el handler de la app moriría en su primera línea y el
# arrastre "fallaría" por culpa del simulacro, no del sitio. Se neutraliza la
# captura para que el simulacro pueda al menos llegar al pointermove. Queda
# dicho en el informe: es una muleta del banco, no un hallazgo.
JS_MULETA_CAPTURA = """() => {
  const orig = Element.prototype.setPointerCapture;
  Element.prototype.setPointerCapture = function(id){
    try { return orig.call(this, id); } catch(e) { /* pointerId inventado */ }
  };
  window.__muletaCaptura = true;
}"""

JS_DEDO_SINTETICO = """([x, y, fase]) => {
  /* El destino se fija en touchstart y NO se recalcula: así funciona un dedo
     de verdad —el target queda capturado en el primer contacto— y así hay que
     imitarlo, o cada paso del arrastre le pegaría a un elemento distinto. */
  if(fase === 'inicio') window.__destino = document.elementFromPoint(x, y) || document.body;
  const el = window.__destino || document.body;
  const comun = {bubbles: true, cancelable: true, composed: true,
                 clientX: x, clientY: y, pageX: x, pageY: y, screenX: x, screenY: y};
  const nombrePunt = {inicio: 'pointerdown', mueve: 'pointermove', suelta: 'pointerup'}[fase];
  el.dispatchEvent(new PointerEvent(nombrePunt, Object.assign({
    pointerId: 7, pointerType: 'touch', isPrimary: true, button: fase === 'mueve' ? -1 : 0,
    buttons: fase === 'suelta' ? 0 : 1, width: 24, height: 24, pressure: fase === 'suelta' ? 0 : 0.5
  }, comun)));
  /* Y además el TouchEvent: si el arreglo escucha touch en vez de pointer,
     este simulacro tiene que moverlo igual. */
  try {
    const t = new Touch(Object.assign({identifier: 7, target: el}, comun));
    const nombreTac = {inicio: 'touchstart', mueve: 'touchmove', suelta: 'touchend'}[fase];
    const vivos = fase === 'suelta' ? [] : [t];
    el.dispatchEvent(new TouchEvent(nombreTac, {bubbles: true, cancelable: true, composed: true,
      touches: vivos, targetTouches: vivos, changedTouches: [t]}));
  } catch(e) { /* si el motor no deja construir Touch, con pointer basta */ }
}"""


# --------------------------------------------------------------------------
# Los tres dedos. Cada uno dice de qué está hecho, porque el informe tiene que
# poder separar "probado" de "despachado con eventos sintéticos".
# --------------------------------------------------------------------------
class Dedo:
    """Un modo de empujar. `realismo` es lo que el informe promete."""
    clave = ""
    nombre = ""
    realismo = ""     # real | parcial | simulado
    gatilla = True    # ¿sus fallas cuentan para el código de salida?

    def __init__(self, page, cdp=None):
        self.page = page
        self.cdp = cdp

    def arrastrar(self, x0, y0, x1, y1, pasos=16, pausa=0.02, pausa_final=0.0):
        """Empuja y devuelve el alto de la hoja LEÍDO ANTES DE SOLTAR.

        Ese número es la clave del caso 10: dice dónde dejó la hoja el dedo, y
        contra él se mide si al soltar la hoja saltó un tope de más.

        `pausa_final` es el tiempo entre el último movimiento y el suelte. No es
        decoración: la hoja distingue soltar rápido de soltar lento —con envión
        salta un tope a propósito, como cualquier hoja nativa— y descarta la
        velocidad si el último movimiento fue hace más de 120 ms. Sin esa pausa,
        el envión legítimo y el click fantasma dejan la hoja en el mismo lugar y
        no hay forma de saber cuál de los dos la movió. Quien quiera aislar el
        click tiene que soltar lento."""
        raise NotImplementedError

    def _alto_vivo(self):
        return self.page.evaluate(
            "() => {const p=document.getElementById('panel')||document.querySelector('.panel-lista');"
            "return p ? Math.round(p.getBoundingClientRect().height) : -1}")


class DedoCDP(Dedo):
    """chromium. Toque real: los eventos entran por la misma cañería que un dedo."""
    clave = "toque"
    nombre = "toque real (CDP)"
    realismo = "real"

    def arrastrar(self, x0, y0, x1, y1, pasos=16, pausa=0.02, pausa_final=0.0):
        self.cdp.send("Input.dispatchTouchEvent",
                      {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0, "id": 1}]})
        for i in range(1, pasos + 1):
            self.cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [
                {"x": x0 + (x1 - x0) * i / pasos, "y": y0 + (y1 - y0) * i / pasos, "id": 1}]})
            time.sleep(pausa)
        if pausa_final:
            time.sleep(pausa_final)
        vivo = self._alto_vivo()
        self.cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        return vivo

    def scrollear_lista(self, x, y, dy):
        """Con toque real el scroll de la lista lo decide el navegador: se
        arrastra dentro de la lista y se mira quién se movió. Ese es el caso 6."""
        self.arrastrar(x, y, x, y - dy, pasos=14)
        return "arrastre táctil"


class DedoPuntero(Dedo):
    """webkit y firefox. Entrada real del navegador, pero pointerType=mouse:
    prueba la lógica del arrastre, no la pelea con el scroll nativo."""
    clave = "puntero"
    nombre = "puntero de ratón (entrada real, no es dedo)"
    realismo = "parcial"

    def arrastrar(self, x0, y0, x1, y1, pasos=16, pausa=0.012, pausa_final=0.0):
        m = self.page.mouse
        m.move(x0, y0)
        m.down()
        for i in range(1, pasos + 1):
            m.move(x0 + (x1 - x0) * i / pasos, y0 + (y1 - y0) * i / pasos)
            time.sleep(pausa)
        if pausa_final:
            time.sleep(pausa_final)
        vivo = self._alto_vivo()
        m.up()
        return vivo

    def scrollear_lista(self, x, y, dy):
        """La rueda es entrada real y mueve la lista de verdad, pero pasa por
        encima de touch-action: prueba que la lista scrollea, NO que el gesto
        del dedo no se lo roba. La diferencia queda dicha en el informe.

        En webkit móvil no hay rueda —Playwright la niega de frente— y tampoco
        hay arrastre táctil. Ahí este caso simplemente no se puede probar, y
        eso se dice: es la limitación honesta de webkit, no una falla del
        sitio ni un aprobado regalado."""
        try:
            self.page.mouse.move(x, y)
            self.page.mouse.wheel(0, dy)
        except Exception as e:
            raise NoSePuede("webkit móvil no da rueda ni arrastre táctil: "
                            "el caso 6 no se puede ejercer en este motor") from e
        return "rueda del ratón (no prueba touch-action)"


class DedoSintetico(Dedo):
    """webkit, plan B. Eventos fabricados desde la página: mueven los listeners
    de la app, pero el navegador no participa. No gatilla el código de salida."""
    clave = "simulado"
    nombre = "toque SIMULADO (eventos fabricados)"
    realismo = "simulado"
    gatilla = False

    def arrastrar(self, x0, y0, x1, y1, pasos=16, pausa=0.012, pausa_final=0.0):
        ev = self.page.evaluate
        ev(JS_DEDO_SINTETICO, [x0, y0, "inicio"])
        for i in range(1, pasos + 1):
            ev(JS_DEDO_SINTETICO, [x0 + (x1 - x0) * i / pasos, y0 + (y1 - y0) * i / pasos, "mueve"])
            time.sleep(pausa)
        if pausa_final:
            time.sleep(pausa_final)
        vivo = self._alto_vivo()
        ev(JS_DEDO_SINTETICO, [x1, y1, "suelta"])
        return vivo

    def scrollear_lista(self, x, y, dy):
        """Un touchmove fabricado NO scrollea nada: el scroll nativo lo hace el
        compositor, no un listener. Acá solo se puede mirar que la hoja no se
        haya movido, y eso es medio caso 6, no el caso 6."""
        self.arrastrar(x, y, x, y - dy, pasos=14)
        return "simulado: el scroll nativo no ocurre"


# --------------------------------------------------------------------------
# Utilidades de la corrida
# --------------------------------------------------------------------------
def hay_servidor(url: str) -> bool:
    host, puerto = url.replace("http://", "").split(":")
    try:
        with socket.create_connection((host, int(puerto)), timeout=2):
            return True
    except OSError:
        return False


def es_ruido(texto: str, ubicacion: str) -> bool:
    campo = f"{texto} {ubicacion}"
    return any(p in campo for p in RUIDO_CONOCIDO)


def esperar_quieto(page, tope_ms=3500):
    """Espera a que la hoja deje de moverse. Condición, no reloj."""
    try:
        page.evaluate("() => { delete window.__q }")
        page.wait_for_function(JS_QUIETO, timeout=tope_ms, polling="raf")
    except Exception:
        pass  # que no se haya quedado quieta también es un dato: lo dirá el alto


def geo(page):
    return page.evaluate(JS_GEOMETRIA)


def descubrir_topes(page, g):
    """Los tres altos a los que la hoja se pega, medidos en vez de adivinados.

    Se sacan por teclado, flecha arriba, porque es la única API que las cuatro
    páginas tienen igual: `window.fijarPanel` solo existe en mapa.html. Sin
    estos números los casos 7 y 10 no se pueden juzgar: "cambió de tope" y
    "saltó un tope de más" exigen saber dónde están los topes.

    Se sube y NUNCA se baja. Bajar desde el reposo lleva al tope escondida, y
    escondida la hoja va `inert`: el tirador deja de ser enfocable y el teclado
    ya no la trae de vuelta, así que el descubrimiento se quedaba encerrado y
    devolvía una lista vacía. Subiendo se recorren los mismos topes sin poder
    caerse por ese borde. (Escondida tampoco sería un tope: es la ausencia de
    hoja, y colarla en la lista haría que el caso 10 midiera el salto contra
    una altura que no existe.)"""
    if not g or not g["tirador"] or not g["tirador"]["seVe"]:
        return []
    vistos = [g["alto"]] if g["visible"] > TOLERANCIA else []
    enfocar_tirador(page)
    for _ in range(3):
        page.keyboard.press("ArrowUp")
        esperar_quieto(page)
        gg = geo(page)
        if gg["visible"] <= TOLERANCIA:
            break
        if gg["alto"] in vistos:
            break          # ya no sube más: se llegó al tope alto
        vistos.append(gg["alto"])
    return sorted(set(vistos))


def enfocar_tirador(page):
    """Foco por DOM y no por locator: en escritorio el tirador es display:none y
    el locator se quedaría esperando una actionability que nunca llega."""
    page.evaluate("() => {const t=document.getElementById('tirador')||"
                  "document.querySelector('.tirador'); t && t.focus()}")


def bajar_a_reposo(page):
    """Flecha abajo de a una, mirando después de cada tecla.

    De a cuatro seguidas se pasaría de largo hasta esconderla, que en el arreglo
    nuevo es un tope más abajo del reposo. Y si se pasa no hay vuelta por
    teclado: escondida la hoja va `inert` y el tirador deja de tomar foco.
    Devuelve None para decir "de acá solo se sale recargando"."""
    for _ in range(4):
        antes = geo(page)
        page.keyboard.press("ArrowDown")
        esperar_quieto(page)
        ahora = geo(page)
        if ahora["visible"] <= TOLERANCIA:      # se pasó: la escondió
            return None
        if abs(ahora["alto"] - antes["alto"]) <= 1:   # ya no baja más
            return ahora
    return geo(page)


def volver_a_reposo(page, url, topes):
    """Deja la hoja donde empieza, sin recargar si se puede evitar.

    Recargar entre casos son ~3s × 11 casos × 16 combinaciones: media hora de
    reloj regalada. Se recarga solo cuando el caso dejó la hoja escondida y no
    hay cómo devolverla."""
    g = geo(page)
    if g and g["visible"] > 20 and g["tirador"] and g["tirador"]["seVe"]:
        enfocar_tirador(page)
        g = bajar_a_reposo(page)
        if g is None:            # quedó escondida e inerte: solo recargando
            return cargar(page, url)
        if topes and abs(g["alto"] - topes[0]) <= TOLERANCIA:
            return g
        if not topes and g["visible"] > 20:
            return g
    if g and g["hayFijar"]:
        page.evaluate("() => fijarPanel(0)")
        esperar_quieto(page)
        g = geo(page)
        if g and g["visible"] > 20:
            return g
    return cargar(page, url)


def cargar(page, url):
    page.goto(url, wait_until="load", timeout=60000)
    page.wait_for_function(JS_LISTA_CARGADA, timeout=45000, polling=200)
    esperar_quieto(page)
    return geo(page)


def mas_cercano(topes, valor):
    return min(topes, key=lambda t: abs(t - valor)) if topes else None


def dentro(v, minimo, maximo):
    return max(minimo, min(maximo, v))


# --------------------------------------------------------------------------
# Los casos. Cada uno devuelve (veredicto, detalle). Veredicto: ok | falla | na
# --------------------------------------------------------------------------
def caso_1_reposo(page, dedo, g, topes):
    """La hoja en reposo tiene que dejarle al mapa la mayoría de la pantalla.

    Se mide contra la pantalla entera (innerHeight) y no contra el hueco del
    mapa, porque la regla del encargo habla de la PANTALLA y porque las cuatro
    páginas eligieron a propósito fracciones distintas del hueco —descuentos
    abre en 52% para que el guarén no se coma la primera fila—. Medir contra el
    hueco convertiría una decisión de diseño en una falla falsa. Los dos
    números quedan igual en el JSON."""
    razon = g["visible"] / g["pantalla"]
    razon_hueco = g["visible"] / g["disponible"] if g["disponible"] else 0
    det = {"alto": g["visible"], "pantalla": g["pantalla"],
           "porcentaje_pantalla": round(razon * 100, 1),
           "porcentaje_hueco_mapa": round(razon_hueco * 100, 1)}
    return ("ok" if razon < 0.5 else "falla"), det


def caso_2_subir_tirador(page, dedo, g, topes):
    t = g["tirador"]
    if not t or not t["seVe"]:
        return "na", {"motivo": "no hay tirador visible"}
    antes = g["alto"]
    dedo.arrastrar(t["x"], t["y"], t["x"], max(4, t["y"] - 200))
    esperar_quieto(page)
    ahora = geo(page)["alto"]
    return ("ok" if ahora - antes >= CAMBIO_MINIMO else "falla"), {"de": antes, "a": ahora}


def caso_3_bajar_tirador(page, dedo, g, topes):
    """Se sube primero —si no, no hay de dónde bajar— y después se baja."""
    t = g["tirador"]
    if not t or not t["seVe"]:
        return "na", {"motivo": "no hay tirador visible"}
    dedo.arrastrar(t["x"], t["y"], t["x"], max(4, t["y"] - 200))
    esperar_quieto(page)
    g2 = geo(page)
    if g2["alto"] - g["alto"] < CAMBIO_MINIMO:
        return "na", {"motivo": "no se pudo subir para después bajar (mira el caso 2)"}
    t2 = g2["tirador"]
    antes = g2["alto"]
    dedo.arrastrar(t2["x"], t2["y"], t2["x"], min(g2["pantalla"] - 4, t2["y"] + 200))
    esperar_quieto(page)
    ahora = geo(page)["alto"]
    return ("ok" if antes - ahora >= CAMBIO_MINIMO else "falla"), {"de": antes, "a": ahora}


def caso_4_subir_conteo(page, dedo, g, topes):
    """El contador es cabecera de la hoja: el dedo que lo agarra está agarrando
    la hoja. Hoy no pasa nada y por eso este caso existe."""
    c = g["conteo"]
    if not c or not c["seVe"]:
        return "na", {"motivo": "no hay .conteo visible"}
    antes = g["alto"]
    dedo.arrastrar(c["x"], c["y"], c["x"], max(4, c["y"] - 200))
    esperar_quieto(page)
    ahora = geo(page)["alto"]
    return ("ok" if ahora - antes >= CAMBIO_MINIMO else "falla"), {"de": antes, "a": ahora}


def caso_5_bajar_lista(page, dedo, g, topes):
    """Con la lista arriba de todo (scrollTop 0) el dedo que la tira hacia abajo
    no quiere scrollear: quiere bajar la hoja. Es el contrato estándar de una
    hoja arrastrable y hoy no está."""
    g2 = _subir_hoja(page, dedo, g)
    if g2 is None:
        return "na", {"motivo": "no se pudo levantar la hoja"}
    page.evaluate("() => {const l=document.getElementById('lista')||document.querySelector('.lista'); if(l) l.scrollTop=0}")
    g2 = geo(page)
    li = g2["lista"]["centro"]
    antes = g2["alto"]
    dedo.arrastrar(li["x"], li["y"], li["x"], min(g2["pantalla"] - 4, li["y"] + 200))
    esperar_quieto(page)
    g3 = geo(page)
    det = {"de": antes, "a": g3["alto"], "scrollTop_al_soltar": g3["lista"]["arriba"]}
    return ("ok" if antes - g3["alto"] >= CAMBIO_MINIMO else "falla"), det


def caso_6_scroll_lista(page, dedo, g, topes):
    """LA regresión. Con la hoja arriba, el dedo que sube DENTRO de la lista
    tiene que scrollear la lista y no mover la hoja. Esto se rompió una vez por
    poner touch-action:none de más y dejó 37.000px de eventos en una caja de
    200px que no se podía mover."""
    g2 = _subir_hoja(page, dedo, g)
    if g2 is None:
        return "na", {"motivo": "no se pudo levantar la hoja"}
    li = g2["lista"]
    if li["total"] <= li["caja"] + 40:
        return "na", {"motivo": "la lista no tiene de dónde scrollear"}
    page.evaluate("() => {const l=document.getElementById('lista')||document.querySelector('.lista'); if(l) l.scrollTop=0}")
    g2 = geo(page)
    alto_antes, scroll_antes = g2["alto"], g2["lista"]["arriba"]
    c = g2["lista"]["centro"]
    como = dedo.scrollear_lista(c["x"], c["y"], 160)
    esperar_quieto(page)
    g3 = geo(page)
    movio_lista = g3["lista"]["arriba"] - scroll_antes
    movio_hoja = abs(g3["alto"] - alto_antes)
    det = {"scrollTop": f"{scroll_antes} → {g3['lista']['arriba']}",
           "alto_hoja": f"{alto_antes} → {g3['alto']}",
           "touch_action": g3["lista"]["accionTactil"], "empujado_con": como}
    if dedo.realismo == "simulado":
        # Un evento fabricado no scrollea: acá solo se puede exigir que la hoja
        # no se haya movido. Media verdad, dicha como media verdad.
        det["ojo"] = "solo se comprueba que la hoja no se movió"
        return ("ok" if movio_hoja <= 8 else "falla"), det
    ok = movio_lista >= 20 and movio_hoja <= 8
    return ("ok" if ok else "falla"), det


def caso_7_arrastre_corto(page, dedo, g, topes):
    """28px es menos de lo que la gente cree que arrastra. Tiene que cambiar de
    tope igual: si vuelve al mismo, el gesto se sintió ignorado."""
    t = g["tirador"]
    if not t or not t["seVe"]:
        return "na", {"motivo": "no hay tirador visible"}
    antes = g["alto"]
    dedo.arrastrar(t["x"], t["y"], t["x"], t["y"] - 28, pasos=7)
    esperar_quieto(page)
    ahora = geo(page)["alto"]
    det = {"de": antes, "a": ahora, "topes": topes}
    if topes:
        det["quedo_en_un_tope"] = any(abs(ahora - x) <= TOLERANCIA for x in topes)
    return ("ok" if abs(ahora - antes) >= CAMBIO_MINIMO else "falla"), det


def caso_8_esconder(page, dedo, g, topes):
    """Arrastrar bien abajo la esconde del todo y el mapa queda entero.

    Se sube primero para tener pista de sobra hacia abajo, y si el arrastre
    lento no la esconde se prueba un envión rápido: muchas hojas se cierran con
    velocidad, no con distancia. Se mide lo que se VE de la hoja, no una clase
    CSS, así el caso no se casa con la implementación que venga."""
    return esconder(page, dedo, g)


def esconder(page, dedo, g):
    """Intenta esconderla arrastrando y devuelve (veredicto, detalle).

    Lo usan el caso 8 y el 9. El 9 no puede dar por hecho el estado que dejó el
    8: entre caso y caso la página se recarga, porque de la hoja escondida no
    se vuelve por teclado. Antes el 9 miraba una hoja recién cargada, la veía
    visible e informaba "no se pudo esconder" sin haber intentado nunca."""
    _subir_hoja(page, dedo, g)
    menor = None   # lo MENOS que llegó a asomar en cualquier intento
    for pasos, pausa, como in ((18, 0.02, "arrastre largo"), (5, 0.004, "envión rápido")):
        gg = geo(page)
        t = gg["tirador"]
        if not t or not t["seVe"]:
            return "na", {"motivo": "no hay tirador visible"}
        dedo.arrastrar(t["x"], t["y"], t["x"], gg["pantalla"] - 3, pasos=pasos, pausa=pausa)
        esperar_quieto(page)
        g3 = geo(page)
        if g3["visible"] <= TOLERANCIA:
            return "ok", {"visible": g3["visible"], "con": como,
                          "mapa_libre": g3["disponible"] - g3["visible"]}
        # El número que se informa es el del intento, no el de después de
        # volver a levantarla para el siguiente: medir tras el re-subir decía
        # "quedó asomada 448px" cuando 448 era el tope alto, no el resultado.
        if menor is None or g3["visible"] < menor["visible"]:
            menor = {"visible": g3["visible"], "con": como, "pantalla": g3["pantalla"]}
        _subir_hoja(page, dedo, g3)
    menor["motivo"] = "quedó asomada: el arrastre tiene piso y no llega a esconderla"
    return "falla", menor


def caso_9_volver(page, dedo, g, topes, botones_antes):
    """Escondida la hoja, algo tiene que traerla de vuelta o la lista se perdió.

    El botón todavía no existe, así que no se busca por nombre: se compara qué
    elementos clickeables aparecieron después de esconderla y se prueba el más
    plausible. Así el caso no le adivina la clase al arreglo que venga."""
    veredicto, det8 = esconder(page, dedo, g)
    g0 = geo(page)
    if g0["visible"] > TOLERANCIA:
        return "falla", {"motivo": "no se pudo esconder la hoja, así que no hay a qué volver",
                         "al_esconder": det8}
    ahora = page.evaluate(JS_BOTONES_FUERA)
    previos = {b["clave"] for b in botones_antes}
    nuevos = [b for b in ahora if b["clave"] not in previos]
    if not nuevos:
        return "falla", {"motivo": "no apareció ningún botón nuevo al esconder la hoja",
                         "clickeables_fuera_de_la_hoja": len(ahora)}

    # El contrato de montarHoja() dice que el botón lo crea la función con id
    # `volver-hoja` y lo cuelga de panel.parentElement. Se prefiere ese, pero no
    # se exige: la búsqueda a ciegas —qué apareció al esconder la hoja— se queda
    # igual, porque una prueba que solo sabe encontrar el botón por su id deja
    # de ser una prueba del comportamiento y pasa a ser un espejo del código.
    def puntaje(b):
        return (4 if b["id"] == "volver-hoja" else 0) \
               + (2 if re.search(r"lista|volver|ver|mostrar|panel|resultado", b["txt"], re.I) else 0) \
               + (1 if b["flotante"] else 0)
    for b in sorted(nuevos, key=puntaje, reverse=True)[:3]:
        page.mouse.click(b["x"], b["y"])
        esperar_quieto(page)
        if geo(page)["visible"] >= 40:
            return "ok", {"boton": b["txt"] or b["id"] or b["clase"]}
    return "falla", {"motivo": "apareció algo pero al clickearlo la hoja no volvió",
                     "candidatos": [b["txt"] or b["id"] or b["clase"] for b in nuevos[:4]]}


def caso_10_click_fantasma(page, dedo, g, topes):
    """Después de un arrastre el navegador manda un `click` de regalo. Si el
    handler del tirador también cicla de tope con ese click, la hoja salta uno
    de más y el gesto se siente descalibrado.

    Se juzga sin mirar el código: donde el dedo soltó la hoja hay un alto vivo;
    el tope correcto es el más cercano A ESE alto. Si la hoja terminó en otro,
    se pasó de largo.

    Se suelta LENTO —300 ms parado antes de levantar el dedo— y ese detalle es
    lo que hace válido el caso. La hoja salta un tope a propósito cuando se
    suelta con envión, como cualquier hoja nativa; con envión, el salto legítimo
    y el del click fantasma dejan la hoja exactamente en el mismo lugar y esta
    prueba estaría acusando al inocente. Parado 300 ms la velocidad ya venció
    (el motor la descarta a los 120 ms), así que lo único que puede correr la
    hoja un tope de más es el click."""
    t = g["tirador"]
    if not t or not t["seVe"]:
        return "na", {"motivo": "no hay tirador visible"}
    if not topes:
        return "na", {"motivo": "no se pudieron descubrir los topes"}
    vivo = dedo.arrastrar(t["x"], t["y"], t["x"], max(4, t["y"] - 200), pausa_final=0.3)
    esperar_quieto(page)
    final = geo(page)["alto"]
    esperado = mas_cercano(topes, vivo)
    det = {"al_soltar": vivo, "tope_que_corresponde": esperado, "quedo_en": final,
           "topes": topes, "suelte": "lento (300ms) para descartar el envión"}
    return ("ok" if abs(final - esperado) <= TOLERANCIA else "falla"), det


def caso_11_teclado(page, dedo, g, topes, url):
    """Con foco en el tirador: flechas cambian tope y Escape esconde.

    Las tres partes van en un veredicto porque el encargo las pide juntas, pero
    el detalle dice cuál se cayó: hoy las flechas andan y Escape no hace nada."""
    t = g["tirador"]
    if not t or not t["seVe"]:
        return "na", {"motivo": "no hay tirador visible"}
    enfocar_tirador(page)
    enfocado = page.evaluate("() => document.activeElement === (document.getElementById('tirador')||document.querySelector('.tirador'))")
    a0 = geo(page)["alto"]
    page.keyboard.press("ArrowUp"); esperar_quieto(page)
    a1 = geo(page)["alto"]
    page.keyboard.press("ArrowDown"); esperar_quieto(page)
    a2 = geo(page)["alto"]
    page.keyboard.press("Escape"); esperar_quieto(page)
    g3 = geo(page)
    arriba_ok = a1 - a0 >= CAMBIO_MINIMO
    # Se pide DIRECCIÓN, no puntería: que la flecha abajo baje un tope. Exigir
    # que vuelva al alto exacto del arranque mezclaba dos cosas —"el teclado
    # mueve la hoja" y "el reposo del arranque es el mismo de siempre"— y
    # reprobaba el teclado, que anda, por una deriva del reposo, que es otra
    # cosa y se informa aparte en `_medidas`.
    abajo_ok = a1 - a2 >= CAMBIO_MINIMO
    escape_ok = g3["visible"] <= TOLERANCIA
    det = {"toma_foco": enfocado, "arriba": f"{a0} → {a1}", "abajo": f"{a1} → {a2}",
           "escape_esconde": escape_ok, "visible_tras_escape": g3["visible"],
           "flechas_ok": arriba_ok and abajo_ok,
           "vuelve_al_reposo_del_arranque": abs(a2 - a0) <= TOLERANCIA}
    return ("ok" if (arriba_ok and abajo_ok and escape_ok) else "falla"), det


def caso_12_escritorio(page, g):
    """En escritorio la hoja no es hoja: es una columna al costado, sin tirador
    y sin alto forzado. Que el arreglo de celular no se derrame para acá."""
    col = g["izq"] > g["anchoPantalla"] * 0.45
    sin_tirador = not (g["tirador"] and g["tirador"]["seVe"])
    llena = g["alto"] >= g["disponible"] * 0.7
    det = {"borde_izq": g["izq"], "ancho_pantalla": g["anchoPantalla"],
           "es_columna_al_costado": col, "tirador_escondido": sin_tirador,
           "alto_no_forzado": llena, "alto": g["alto"], "hueco": g["disponible"]}
    return ("ok" if (col and sin_tirador and llena) else "falla"), det


def caso_13_acostado(page, g):
    """Acostado hay ancho de sobra y falta alto: la lista se va al costado, como
    en escritorio. Si se queda de hoja, el mapa desaparece."""
    col = g["izq"] > g["anchoPantalla"] * 0.4
    llena = g["alto"] >= g["disponible"] * 0.7
    det = {"borde_izq": g["izq"], "ancho_pantalla": g["anchoPantalla"],
           "es_columna_al_costado": col, "ocupa_todo_el_alto": llena,
           "alto": g["alto"], "hueco": g["disponible"],
           "tirador_escondido": not (g["tirador"] and g["tirador"]["seVe"])}
    return ("ok" if (col and llena) else "falla"), det


def _subir_hoja(page, dedo, g):
    """Deja la hoja en un tope alto para los casos que necesitan lista larga.

    Por teclado, que es lo único que las cuatro páginas comparten y lo único
    que no depende de que el arrastre —lo que estamos probando— funcione."""
    t = g["tirador"]
    if not t or not t["seVe"]:
        return None
    enfocar_tirador(page)
    for _ in range(3):
        page.keyboard.press("ArrowUp")
    esperar_quieto(page)
    g2 = geo(page)
    if g2["alto"] - g["alto"] >= CAMBIO_MINIMO:
        return g2
    if g2["hayFijar"]:
        page.evaluate("() => fijarPanel(2)")
        esperar_quieto(page)
        g2 = geo(page)
        if g2["alto"] - g["alto"] >= CAMBIO_MINIMO:
            return g2
    return g2 if g2["alto"] > g["alto"] else None


# --------------------------------------------------------------------------
# La corrida de una página en un navegador, un modo y un formato
# --------------------------------------------------------------------------
def callar_analitica(page):
    """Contesta el beacon de Cloudflare Insights con un 204 y CORS abierto.

    Servido desde localhost el beacon se cae por CORS y ensucia la consola de
    las cuatro páginas. Filtrar el texto del error no sirve: cada motor lo
    redacta distinto —chromium nombra la URL, webkit dice sólo "Origin ... is
    not allowed" sin decir de quién— y una lista de frases o se queda corta o
    se vuelve tan ancha que se traga errores de verdad. Cortarlo en la red lo
    apaga igual en los tres motores y deja el caso 14 diciendo algo: si aparece
    un error, es del sitio."""
    cors = {"Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS"}

    def responder(ruta):
        # El beacon entra de dos formas: el <script> que lo carga y el POST que
        # manda la medición. Al script hay que contestarle con MIME de
        # JavaScript o webkit —que es estricto— tira "'text/plain' is not a
        # valid JavaScript MIME type" y cambiamos un error de consola por otro.
        if ruta.request.resource_type == "script":
            ruta.fulfill(status=200, body="",
                         headers=dict(cors, **{"Content-Type": "application/javascript"}))
        else:
            ruta.fulfill(status=204, body="", headers=cors)

    page.route(re.compile(r"cloudflareinsights\.com|/cdn-cgi/rum"), responder)

    # Las fotos de los talleres viven en S3 de las municipalidades, en
    # talleres.nunoadeportes.cl, en huechuraba.cl. Cada una es una ida a
    # internet en cada carga de cada página de cada navegador de cada formato:
    # segundos regalados y, peor, una lotería —firefox ya trajo un webp a medio
    # bajar y lo cantó como error de consola—. Un caso que a veces pasa según
    # cómo venga la red no es una puerta, es un dado. Se responden todas con un
    # PNG de 1×1 válido.
    #
    # Lo que esto NO prueba, y queda dicho: que las fotos existan y carguen.
    # Eso es trabajo de verificar_web.py, que valida las URL. Acá se mide la
    # hoja, y el alto de la hoja no depende de los bytes de una foto: sale de
    # una fracción del contenedor, no del contenido.
    page.route(
        "**/*",
        lambda ruta: ruta.fulfill(status=200, body=PNG_1PX, headers={"Content-Type": "image/png"})
        if (ruta.request.resource_type == "image"
            and "localhost" not in ruta.request.url) else ruta.fallback())


def correr_pagina(page, dedo, url, formato, casos_pedidos):
    callar_analitica(page)
    errores = []
    page.on("console", lambda m: errores.append({"tipo": m.type, "texto": m.text[:200],
                                                 "donde": (m.location or {}).get("url", "")})
            if m.type == "error" else None)
    page.on("pageerror", lambda e: errores.append({"tipo": "pageerror", "texto": str(e)[:200],
                                                   "donde": ""}))
    salida = {}
    g = cargar(page, url)
    if g is None:
        return {"error": "la página no tiene #panel / .panel-lista"}, errores

    topes = []
    botones_antes = []
    reposo_carga = g["alto"] if g["visible"] > TOLERANCIA else None
    if formato["ambito"] == "celular":
        topes = descubrir_topes(page, g)
        g = volver_a_reposo(page, url, topes)
        botones_antes = page.evaluate(JS_BOTONES_FUERA)

    # Dos reposos, no uno. En mapa.html la hoja abre en 182 px y después de
    # cualquier ida y vuelta se asienta en 211: 29 px de mapa que el usuario
    # pierde para siempre apenas toca la hoja una vez. No reprueba ningún caso
    # —el teclado y el arrastre andan— pero es una diferencia real, así que
    # queda medida en las dos corridas y cualquier cambio salta en el JSON.
    salida["_medidas"] = {"topes": topes, "reposo": g["alto"],
                          "reposo_al_cargar": reposo_carga,
                          "reposo_asentado": g["alto"],
                          "hueco": g["disponible"],
                          "pantalla": g["pantalla"],
                          "tirador_px": g["tirador"]["alto"] if g["tirador"] else None,
                          "touch_action_lista": g["lista"]["accionTactil"] if g["lista"] else None}

    def anota(n, res):
        salida[n] = {"veredicto": res[0], "detalle": res[1]}

    if formato["ambito"] == "celular":
        secuencia = [
            (1, lambda: caso_1_reposo(page, dedo, geo(page), topes)),
            (2, lambda: caso_2_subir_tirador(page, dedo, geo(page), topes)),
            (3, lambda: caso_3_bajar_tirador(page, dedo, geo(page), topes)),
            (4, lambda: caso_4_subir_conteo(page, dedo, geo(page), topes)),
            (5, lambda: caso_5_bajar_lista(page, dedo, geo(page), topes)),
            (6, lambda: caso_6_scroll_lista(page, dedo, geo(page), topes)),
            (7, lambda: caso_7_arrastre_corto(page, dedo, geo(page), topes)),
            (10, lambda: caso_10_click_fantasma(page, dedo, geo(page), topes)),
            (8, lambda: caso_8_esconder(page, dedo, geo(page), topes)),
            (9, lambda: caso_9_volver(page, dedo, geo(page), topes, botones_antes)),
            (11, lambda: caso_11_teclado(page, dedo, geo(page), topes, url)),
        ]
        for n, fn in secuencia:
            if n not in casos_pedidos:
                continue
            try:
                anota(n, fn())
            except NoSePuede as e:
                anota(n, ("na", {"motivo": str(e)}))
            except Exception as e:
                anota(n, ("falla", {"motivo": f"el caso reventó: {type(e).__name__}: {e}"[:180]}))
            # 8, 9 y 11 dejan la hoja escondida: de ahí solo se vuelve recargando.
            if n in (8, 9, 11):
                g = cargar(page, url)
            else:
                g = volver_a_reposo(page, url, topes)
    elif formato["ambito"] == "escritorio" and 12 in casos_pedidos:
        anota(12, caso_12_escritorio(page, g))
    elif formato["ambito"] == "acostado" and 13 in casos_pedidos:
        anota(13, caso_13_acostado(page, g))

    # Caso 14 al final: junta todo lo que la consola escupió en la pasada.
    reales = [e for e in errores if not es_ruido(e["texto"], e["donde"])]
    ruido = len(errores) - len(reales)
    anota(14, ("ok" if not reales else "falla",
               {"errores": reales[:6], "cuantos": len(reales), "ruido_ignorado": ruido}))
    return salida, errores


def main() -> int:
    ap = argparse.ArgumentParser(description="Banco de pruebas de la hoja arrastrable")
    ap.add_argument("--etiqueta", default=datetime.now().strftime("%Y%m%d-%H%M"),
                    help="nombre de la corrida: antes, despues, lo que sea")
    ap.add_argument("--comparar", help="etiqueta de otra corrida para el diff")
    ap.add_argument("--navegadores", default="chromium,webkit,firefox")
    ap.add_argument("--paginas", default=",".join(k for k, _ in PAGINAS))
    ap.add_argument("--formatos", default=",".join(f["clave"] for f in FORMATOS))
    ap.add_argument("--base", default=BASE)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    # El 8777 lo suele servir un python suelto de la sesión de al lado. Si está,
    # se usa y no se toca; si no, lo levanta este guion y lo apaga al terminar.
    propio = None
    if not hay_servidor(args.base):
        propio = subprocess.Popen([sys.executable, "-m", "http.server", "8777"],
                                  cwd=str(DIR_WEB), stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        for _ in range(40):
            if hay_servidor(args.base):
                break
            time.sleep(0.25)

    paginas = [(k, f) for k, f in PAGINAS if k in args.paginas.split(",")]
    formatos = [f for f in FORMATOS if f["clave"] in args.formatos.split(",")]
    navs = [n for n in args.navegadores.split(",") if n]

    # Huella de los archivos de la hoja, al empezar y al terminar. Otro agente
    # puede estar editándolos mientras esto corre: si cambian a mitad de camino,
    # la corrida no es de una sola versión del sitio y hay que decirlo.
    def huella():
        import hashlib
        h = {}
        for f in ["loica.js", "loica.css", "mapa.html", "cine.html",
                  "descuentos.html", "talleres.html"]:
            ruta = DIR_WEB / f
            h[f] = hashlib.sha1(ruta.read_bytes()).hexdigest()[:12] if ruta.exists() else None
        return h

    inicio = time.time()
    res = {"etiqueta": args.etiqueta, "cuando": datetime.now().isoformat(timespec="seconds"),
           "base": args.base, "huella_inicial": huella(), "corridas": {}, "avisos": []}

    try:
        with sync_playwright() as p:
            for nav in navs:
                # webkit va dos veces: puntero real y toque simulado.
                modos = {"chromium": [DedoCDP], "webkit": [DedoPuntero, DedoSintetico],
                         "firefox": [DedoPuntero]}.get(nav, [DedoPuntero])
                try:
                    navegador = getattr(p, nav).launch(headless=True)
                except Exception as e:
                    res["avisos"].append(f"{nav}: no se pudo abrir ({str(e)[:110]}). "
                                         f"Se baja con `python3 -m playwright install {nav}`; "
                                         f"son cientos de MB y no se descarga sin permiso.")
                    print(f"  ⚠ {nav} no está instalado o no abre — se sigue con los otros.")
                    continue
                for Clase in modos:
                    for formato in formatos:
                        casos = CASOS_DE_ARRASTRE | {14} if Clase is DedoSintetico \
                            else {n for n, _, _ in CASOS}
                        if Clase is DedoSintetico and formato["ambito"] != "celular":
                            continue
                        ctx_args = {"viewport": {"width": formato["ancho"], "height": formato["alto"]},
                                    "locale": "es-CL", "timezone_id": "America/Santiago"}
                        if formato["celular"] and nav != "firefox":
                            ctx_args.update({"has_touch": True, "is_mobile": True,
                                             "device_scale_factor": 3,
                                             "user_agent": p.devices["iPhone 13"]["user_agent"]})
                        elif formato["celular"]:
                            aviso = f"firefox · {formato['nombre']}: sin has_touch/is_mobile (no los soporta)"
                            if aviso not in res["avisos"]:
                                res["avisos"].append(aviso)
                        for clave, archivo in paginas:
                            ctx = navegador.new_context(**ctx_args)
                            page = ctx.new_page()
                            cdp = ctx.new_cdp_session(page) if Clase is DedoCDP else None
                            dedo = Clase(page, cdp)
                            if Clase is DedoSintetico:
                                page.add_init_script(f"({JS_MULETA_CAPTURA})()")
                            url = f"{args.base}/{archivo}"
                            t0 = time.time()
                            try:
                                salida, _ = correr_pagina(page, dedo, url, formato, casos)
                            except Exception as e:
                                salida = {"error": f"{type(e).__name__}: {e}"[:200]}
                            salida["_segundos"] = round(time.time() - t0, 1)
                            llave = f"{nav}|{dedo.clave}|{formato['clave']}|{clave}"
                            res["corridas"][llave] = salida
                            print(f"  · {llave}  ({salida['_segundos']}s)", flush=True)
                            ctx.close()
                navegador.close()
    finally:
        if propio:
            propio.terminate()

    res["huella_final"] = huella()
    res["segundos"] = round(time.time() - inicio, 1)
    if res["huella_inicial"] != res["huella_final"]:
        cambiados = [f for f in res["huella_inicial"]
                     if res["huella_inicial"][f] != res["huella_final"][f]]
        res["avisos"].append("OJO: cambiaron a mitad de corrida " + ", ".join(cambiados) +
                             " — esta corrida NO es de una sola versión del sitio.")

    DIR_INFORME.mkdir(parents=True, exist_ok=True)
    destino = DIR_INFORME / f"hoja-{args.etiqueta}.json"
    destino.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    fallas = informar(res, args)
    print(f"\nJSON: {destino}")
    return 1 if fallas else 0


# --------------------------------------------------------------------------
# Informe legible
# --------------------------------------------------------------------------
SIMBOLO = {"ok": "✓", "falla": "✗", "na": "·"}


def celda_de(bloque, n):
    """El caso `n` de un bloque, venga de memoria o de un JSON releído.

    Los casos se guardan con clave entera, pero JSON no tiene claves enteras y
    al releer vuelven como "4". Sin esto, `--comparar` no encontraba nada del
    lado viejo, daba `None`, se saltaba la fila y terminaba informando siempre
    "arreglados: 0, rotos: 0": una comparación que nunca contradice a nadie es
    peor que no tener comparación."""
    if not bloque:
        return None
    return bloque.get(n) if n in bloque else bloque.get(str(n))
NOMBRE_MODO = {"toque": "toque real (CDP) — el dedo de verdad",
               "puntero": "puntero de ratón — entrada real, NO es dedo",
               "simulado": "toque SIMULADO — eventos fabricados, no gatilla"}


def informar(res, args) -> int:
    claves_pag = [k for k, _ in PAGINAS if k in args.paginas.split(",")]
    bloques = {}
    for llave, salida in res["corridas"].items():
        nav, modo, formato, pag = llave.split("|")
        bloques.setdefault((nav, modo, formato), {})[pag] = salida

    fallas_reales, fallas_simuladas = [], []
    print("\n" + "=" * 78)
    print(f"HOJA ARRASTRABLE · etiqueta «{res['etiqueta']}» · {res['segundos']}s")
    print("=" * 78)

    for (nav, modo, formato), porpag in bloques.items():
        nom_fmt = next(f["nombre"] for f in FORMATOS if f["clave"] == formato)
        gatilla = modo != "simulado"
        print(f"\n{nav} · {NOMBRE_MODO.get(modo, modo)} · {nom_fmt}")
        print("  " + " " * 48 + "  ".join(f"{c:>5}" for c in claves_pag))
        for n, titulo, ambito in CASOS:
            fila = []
            hay = False
            for pag in claves_pag:
                celda = celda_de(porpag.get(pag, {}), n)
                if celda is None:
                    fila.append("·")
                else:
                    hay = True
                    v = celda["veredicto"]
                    fila.append(SIMBOLO[v])
                    if v == "falla":
                        reg = (n, titulo, nav, modo, formato, pag, celda["detalle"])
                        (fallas_reales if gatilla else fallas_simuladas).append(reg)
            if not hay:
                continue
            print(f"  {n:>2}  {titulo[:44]:<44}" + "  ".join(f"{s:>5}" for s in fila))

    # Medidas crudas: sirven para discutir sin volver a correr nada.
    print("\nMedidas (chromium · iPhone 13 vertical)")
    for pag in claves_pag:
        m = res["corridas"].get(f"chromium|toque|iphone13|{pag}", {}).get("_medidas")
        if m:
            print(f"  {pag:<6} topes={m['topes']}  reposo={m['reposo']}px  "
                  f"hueco={m['hueco']}px  tirador={m['tirador_px']}px  "
                  f"touch-action lista={m['touch_action_lista']}")

    if fallas_reales:
        print(f"\n✗ FALLAS REALES: {len(fallas_reales)}")
        for n, titulo, nav, modo, fmt, pag, det in fallas_reales:
            resumen = ", ".join(f"{k}={v}" for k, v in list(det.items())[:3])
            print(f"  caso {n:>2} {titulo[:36]:<36} {nav}/{fmt}/{pag}: {resumen[:88]}")
    else:
        print("\n✓ Ninguna falla real.")

    if fallas_simuladas:
        print(f"\n~ Fallas en modo SIMULADO: {len(fallas_simuladas)} "
              "(no cuentan para el código de salida; ver la nota de honestidad)")
        for n, titulo, nav, modo, fmt, pag, det in fallas_simuladas[:12]:
            print(f"  caso {n:>2} {titulo[:36]:<36} {nav}/{fmt}/{pag}")

    for a in res.get("avisos", []):
        print(f"\n  aviso: {a}")

    print("\nQué es real y qué es simulacro")
    print("  chromium/toque   REAL      toques por CDP: el navegador arbitra el gesto.")
    print("                             Es el único donde el caso 6 se prueba en serio.")
    print("  webkit/puntero   PARCIAL   entrada real, pero pointerType=mouse. Prueba la")
    print("                             lógica; no prueba la pelea con el scroll nativo.")
    print("  webkit/simulado  SIMULADO  eventos fabricados desde la página, con")
    print("                             setPointerCapture neutralizado. No gatilla.")
    print("  firefox/puntero  PARCIAL   solo camino de ratón; sin has_touch.")

    if args.comparar:
        comparar(res, args.comparar, claves_pag)
    return len(fallas_reales)


def comparar(res, etiqueta_vieja, claves_pag):
    ruta = DIR_INFORME / f"hoja-{etiqueta_vieja}.json"
    if not ruta.exists():
        print(f"\n  aviso: no está {ruta}, no hay con qué comparar.")
        return
    viejo = json.loads(ruta.read_text(encoding="utf-8"))
    arreglados, rotos = [], []
    for llave, salida in res["corridas"].items():
        antes = viejo["corridas"].get(llave, {})
        for n, _, _ in CASOS:
            va = (celda_de(antes, n) or {}).get("veredicto")
            vb = (celda_de(salida, n) or {}).get("veredicto")
            if va == vb or va is None or vb is None:
                continue
            (arreglados if vb == "ok" else rotos).append((n, llave, va, vb))
    print(f"\nContra «{etiqueta_vieja}» ({viejo.get('segundos')}s → {res['segundos']}s)")
    print(f"  arreglados: {len(arreglados)}   rotos: {len(rotos)}")
    for n, llave, va, vb in rotos[:20]:
        print(f"  ✗ ROTO   caso {n:>2}  {llave}  {va} → {vb}")
    for n, llave, va, vb in arreglados[:20]:
        print(f"  ✓ arregla caso {n:>2}  {llave}  {va} → {vb}")


if __name__ == "__main__":
    sys.exit(main())
