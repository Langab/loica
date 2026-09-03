"""Fichas de talleres con el horario escrito en prosa: "LU-MI-VI (9:30-10:30)".

La Corporación de Deportes de Peñalolén no publica calendario: publica una
página por disciplina (/talleres-ligup/<slug>/) con un bloque por clase —el
recinto, a veces con la dirección entre paréntesis; los días y la hora; y
cuánto cuestan la matrícula y la mensualidad—. Su API REST responde 403
(robots.txt no la prohíbe, pero un 403 se respeta igual: no se rodea) y el
índice /talleres-ligup/ no enlaza las fichas. La puerta abierta es el sitemap
de páginas más el HTML de cada ficha.

Es el mismo modelo que `tabla`: un taller que se repite se traduce a sus
próximas sesiones (loica/recurrencia.py) y el export las vuelve a juntar en
una tarjeta con sus días. Lo que cambia es de dónde se lee —bloques de texto
en vez de una tabla— y que la misma corporación arma sus fichas de cinco
maneras distintas (revisadas una por una el 02-09-2026):

  · el encabezado del bloque es el recinto, con la dirección entre paréntesis
    ("CHIMKOWE (Av. Grecia 8787)") o pegada ("CHIMKOWE Av. Grecia 8787");
  · el encabezado es el grupo ("5 a 8 años", "Categoría Sub 7", "NIVEL 1") y
    el recinto está en un encabezado de sección más arriba, o en la única
    pestaña de recintos de la página, o no está;
  · la página entera es de un recinto ("Talleres Deportivos (Complejo La
    Foresta)") y los encabezados son las disciplinas;
  · el recinto viene al final del texto, después del precio;
  · un mismo bloque trae varios tramos ("LU-MI (17:00-18:30) MA (16:30-18:00)").

Tres reglas:
  · Sin días y hora legibles no hay sesión: el bloque se ignora. Un horario
    inventado manda a una persona a una puerta cerrada. Y un recinto que la
    ficha no dice queda en blanco (la tarjeta lleva el nombre de la
    corporación), no se adivina desde el mapa.
  · "Mensualidad:" y "Matrícula:" se leen por separado. Un taller con
    matrícula de $20.000 y mensualidad gratis no es gratis, y el filtro de
    gratis es la promesa central del sitio.
  · La misma disciplina en el mismo recinto y los mismos días a otra hora
    son clases distintas; cuando el título se repite se le agrega la hora,
    igual que hace el catastro de talleres (loica/fuentes/talleres.py). Sin
    eso la deduplicación —título+día+lugar— se comería todas menos una.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from datetime import time
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from ..modelo import Evento
from ..normalizar import detectar_comuna, limpiar_html, resumir
from ..recurrencia import DIAS_SEMANA, ABREVIATURAS, frase_cadencia, parsear_dias, parsear_hora, sesiones_futuras
from ..red import ClienteEducado

log = logging.getLogger("loica.horarios")

ENCABEZADOS = ["h1", "h2", "h3", "h4", "h5", "h6"]
BASURA = ("nav", "header", "footer", "script", "style", "noscript")

# "(9:30-10:30)", "(20:30 a 21:30)", "(8:00-09:00 hrs)": el tramo horario
# entre paréntesis es lo que marca una clase. Los días van justo antes.
RANGO_HORA = re.compile(
    r"\(\s*([01]?\d|2[0-3])[:.](\d{2})\s*(?:-|–|—|a|hasta)?\s*(?:([01]?\d|2[0-3])[:.](\d{2}))?"
    r"\s*(?:hrs?\.?|h\.?)?\s*\)", re.IGNORECASE)

_DIA = r"(?:lu|ma|mi|ju|vi|sa|do|lunes|martes|miercoles|jueves|viernes|sabado|domingo)"
# Días sueltos en un encabezado ("NIVEL 1 Mayores 15 años LU-MI"): se sacan
# del nombre. Con límite de palabra a los dos lados: "RAMA" termina en "MA"
# y no es martes.
_DIAS_SUELTOS = re.compile(rf"\b{_DIA}\b(?:\s*(?:-|/|,|\by\b|\ba\b)\s*{_DIA}\b)*", re.IGNORECASE)
_RANGO_DIAS = re.compile(rf"\b({_DIA})\s+a\s+({_DIA})\b", re.IGNORECASE)

# Una dirección: vía pública, o una palabra seguida de número de tres cifras
# o más, o una esquina. "Mayores de 18 años" no pasa, "Altiplano 1830" sí.
_DIRECCION = re.compile(
    r"\b(?:av(?:da)?\.?|avenida|calle|pasaje|psje\.?|camino)\b|\besq\b|\bs/n\b|\b\d[\d.]{2,}\b",
    re.IGNORECASE)
# Dónde empieza la dirección cuando viene pegada al nombre del recinto:
# "CHIMKOWE Av. Grecia 8787, Peñalolén", "POLIDEPORTIVO X Altiplano 1830".
_INICIO_DIRECCION = re.compile(
    r"\s+((?:av(?:da)?\.?|avenida|calle|pasaje|psje\.?|camino)\b.*|\S+\s+\d[\d.]{2,}\b.*)$",
    re.IGNORECASE)

# Dos o más palabras en mayúsculas al inicio, y después el resto.
_MAYUSCULAS_Y_RESTO = re.compile(r"^((?:[A-ZÁÉÍÓÚÑ0-9(][A-ZÁÉÍÓÚÑ0-9.\-()]*\s+){2,})(.+)$")

# Palabras que nombran un recinto deportivo o comunitario. Sirven para
# distinguir un encabezado que es un lugar de uno que es un grupo de edad.
_LUGAR = re.compile(
    r"\b(?:polideportivo|polidep\.?|pol\.|complejo|comp\.|multicancha|gimnasio|estadio"
    r"|centro c[íi]vico|centro (?:de )?atenci[óo]n|centro cultural|centro deportivo|cancha"
    r"|box|capilla|sede|club|parque|colegio|liceo|piscina|plaza|casa de|junta de vecinos)\b",
    re.IGNORECASE)

# A quién va dirigido: se conserva en la descripción, no en el nombre del lugar.
_PUBLICO = re.compile(
    r"(?:\bedad\s*:?\s*)?\b(?:mayores|menores)\s+(?:de\s+)?\d+\s*\+?\s*a[ñn]os\b"
    r"|(?:\bedad\s*:?\s*)?\b(?:de\s+)?\d+\s*(?:a|-)\s*\d+\s+a[ñn]os\b"
    r"|\b\d+\s*\+\s*a[ñn]os\b|\bdesde\s+(?:los\s+)?\d+\s+a[ñn]os\b|\btodo\s+p[úu]blico\b"
    r"|\badultos?\s+mayores\b|\bni[ñn][oa]s(?:\s*\(as\))?\b|\bj[óo]venes\b"
    r"|\bhombres(?:\s*(?:y|-)\s*mujeres)?\b|\bmujeres\b",
    re.IGNORECASE)


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    solo_ascii = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return " ".join(solo_ascii.lower().split())


def _limpio(texto: str) -> str:
    return " ".join((texto or "").split())


def _legible(nombre: str) -> str:
    """"POLIDEP. S. LIVINGSTONE" → "Polidep. S. Livingstone"; lo demás, tal cual."""
    nombre = _limpio(nombre).strip(" ,.:;-–")
    return nombre.title() if nombre.isupper() else nombre


# -- descubrimiento ----------------------------------------------------------

def _urls_del_sitemap(fuente: dict, cliente: ClienteEducado) -> list[str]:
    """Las fichas que calzan con `patron_url`, desde un sitemap o un índice."""
    base = fuente["url_base"].rstrip("/")
    url = fuente.get("url_agenda") or (base + fuente.get("endpoint", "/sitemap.xml"))
    patron = fuente.get("patron_url", "")
    excluir = [e.lower() for e in (fuente.get("excluir_url") or [])]

    def locs(url_mapa: str) -> tuple[str, list[str]]:
        respuesta = cliente.obtener(url_mapa, max_edad_cache_seg=6 * 3600)
        if respuesta is None or not respuesta.ok:
            log.warning("%s: no pude leer el sitemap %s", fuente.get("nombre"), url_mapa)
            return "", []
        try:
            # strip(): los sitemaps de WordPress traen un salto de línea antes
            # de <?xml?> y el parser exige que la declaración sea lo primero.
            raiz = ElementTree.fromstring(respuesta.content.strip())
        except ElementTree.ParseError:
            log.warning("%s: sitemap ilegible %s", fuente.get("nombre"), url_mapa)
            return "", []
        encontradas = [n.text.strip() for n in raiz.iter() if n.tag.endswith("loc") and n.text]
        return raiz.tag, encontradas

    etiqueta, urls = locs(url)
    if etiqueta.endswith("sitemapindex"):
        # Yoast reparte por tipo: se abren solo los mapas que interesan
        # (por defecto el de páginas, que es donde viven las fichas).
        hijo = fuente.get("sitemap_hijo", "page")
        urls = [u for mapa in urls if hijo in mapa for u in locs(mapa)[1]]

    indice = (base + patron).rstrip("/")
    fichas: dict[str, str] = {}
    for u in urls:
        # La URL se pide tal como la publica el sitemap, con su barra final:
        # sin ella WordPress responde 301 y cada ficha cuesta dos peticiones.
        limpia = u.split("?")[0]
        clave = limpia.rstrip("/")
        if patron and patron not in u:
            continue
        if clave == indice or any(trozo in clave.lower() for trozo in excluir):
            continue
        fichas.setdefault(clave, limpia)
    return list(fichas.values())


# -- lectura de una ficha ----------------------------------------------------

def _titulo(sopa: BeautifulSoup) -> str:
    og = sopa.find("meta", property="og:title")
    titulo = (og.get("content") or "") if og else ""
    if not titulo:
        h1 = sopa.find("h1")
        titulo = h1.get_text(" ", strip=True) if h1 else (sopa.title.get_text() if sopa.title else "")
    return limpiar_html(titulo).split(" | ")[0].strip()[:200]


def _bloques(sopa: BeautifulSoup) -> list:
    """Los contenedores más chicos con un tramo horario, subidos hasta su título.

    Se parte del elemento mínimo que contiene "(9:30-10:30)" y se sube por
    los ancestros hasta encontrar un encabezado (el nombre del recinto o del
    grupo), sin cruzar a un contenedor que también envuelva OTRO horario: dos
    clases en columnas vecinas no pueden compartir bloque.
    """
    minimos = []
    for elemento in sopa.find_all(True):
        if elemento.name in BASURA:
            continue
        if not RANGO_HORA.search(elemento.get_text(" ", strip=True)):
            continue
        if any(RANGO_HORA.search(hijo.get_text(" ", strip=True))
               for hijo in elemento.find_all(True)):
            continue
        minimos.append(elemento)

    bloques = []
    for elemento in minimos:
        contenedor = elemento
        for _ in range(6):
            padre = contenedor.parent
            if padre is None or padre.name in ("body", "html"):
                break
            if any(otro is not elemento and padre in otro.parents for otro in minimos):
                break
            contenedor = padre
            if contenedor.find(ENCABEZADOS) is not None:
                break
        bloques.append((contenedor, elemento))
    return bloques


def _sin_horarios(texto: str) -> str:
    texto = RANGO_HORA.sub(" ", texto)
    return _limpio(_DIAS_SUELTOS.sub(" ", texto))


def _dias(trozo: str) -> list[int]:
    """"LU-MI-VI" → [0, 2, 4]; "LU a VI" es un rango, no lunes y viernes."""
    m = _RANGO_DIAS.search(_plano(trozo))
    if m:
        desde = DIAS_SEMANA.get(m.group(1)) if m.group(1) in DIAS_SEMANA else ABREVIATURAS.get(m.group(1))
        hasta = DIAS_SEMANA.get(m.group(2)) if m.group(2) in DIAS_SEMANA else ABREVIATURAS.get(m.group(2))
        if desde is not None and hasta is not None and desde <= hasta:
            return list(range(desde, hasta + 1))
    return parsear_dias(trozo)


def _horarios(texto: str) -> list[tuple[list[int], time, time | None]]:
    """Todos los pares días+tramo de un bloque, en orden.

    Los días de cada tramo son lo escrito justo antes de su paréntesis y
    después del tramo anterior (o del último paréntesis cerrado, que sería
    una dirección): "(Av. Grecia 8787) MA-JU (8:00-9:00) VI (16:30-17:30)".
    """
    encontrados = []
    fin_anterior = 0
    for m in RANGO_HORA.finditer(texto):
        trozo = texto[fin_anterior:m.start()]
        if ")" in trozo:
            trozo = trozo.rsplit(")", 1)[1]
        fin_anterior = m.end()
        dias = _dias(trozo[-60:])
        hora = parsear_hora(f"{m.group(1)}:{m.group(2)}")
        if not dias or hora is None:
            continue
        hora_fin = parsear_hora(f"{m.group(3)}:{m.group(4)}") if m.group(3) else None
        encontrados.append((dias, hora, hora_fin))
    return encontrados


def _es_lugar(texto: str, pestanas: list[str]) -> bool:
    """¿Este encabezado nombra un recinto y no un grupo de edad o un nivel?"""
    if _DIRECCION.search(texto) or _LUGAR.search(texto):
        return True
    plano = _plano(texto)
    for pestana in pestanas:
        palabras = [p for p in _plano(pestana).replace("–", " ").split() if len(p) >= 4]
        if palabras and all(p in plano for p in palabras):
            return True
    return False


def _separar_recinto(texto: str) -> tuple[str, str, str]:
    """"CHIMKOWE (Av. Grecia 8787) Mayores de 18 años" → (recinto, dirección, público)."""
    texto = _limpio(texto)
    direccion = ""
    m = re.search(r"\(([^()]{4,})\)", texto)
    if m and _DIRECCION.search(m.group(1)):
        direccion = m.group(1).strip()
        texto = _limpio(texto[:m.start()] + " " + texto[m.end():])
    else:
        # "COMPLEJO LA FORESTA Sánchez Fontecilla 13.760": el recinto va en
        # MAYÚSCULAS y la dirección en minúsculas, y ese corte es más fiable
        # que adivinar cuántas palabras tiene la calle.
        m = _MAYUSCULAS_Y_RESTO.match(texto)
        if m and _DIRECCION.search(m.group(2)) and not _PUBLICO.search(m.group(2)):
            texto, direccion = m.group(1).strip(), m.group(2).strip()
        else:
            m = _INICIO_DIRECCION.search(texto)
            if m and not _PUBLICO.search(m.group(1)):
                direccion = m.group(1).strip()
                texto = _limpio(texto[:m.start()])

    publico = " ".join(p.group(0) for p in _PUBLICO.finditer(texto))
    nombre = _PUBLICO.sub(" ", texto)
    return _legible(nombre), direccion.strip(" ,.;"), _limpio(publico)


def _recinto_del_titulo(titulo: str) -> tuple[str, str]:
    """"Talleres Deportivos en Peñalolén (Complejo La Foresta)" → (recinto, título)."""
    m = re.search(r"\(([^()]{4,})\)\s*$", titulo)
    if m and _es_lugar(m.group(1), []):
        return _legible(m.group(1)), _limpio(titulo[:m.start()])
    return "", titulo


def _interpretar(encabezado: str, cuerpo: str, elemento, titulo_pagina: str,
                 titulo_base: str, recinto_pagina: str, pestanas: list[str]) -> dict:
    """Decide qué es el encabezado del bloque y de dónde sale el recinto."""
    titulo = titulo_base
    recinto = direccion = grupo = ""
    limpio = _sin_horarios(encabezado)

    if limpio:
        if _plano(limpio) in _plano(titulo_pagina):
            pass  # repite la disciplina de la página: no dice nada nuevo
        elif recinto_pagina:
            titulo = _legible(limpio)  # página de un recinto: los bloques son disciplinas
        elif _es_lugar(limpio, pestanas):
            recinto, direccion, grupo = _separar_recinto(limpio)
        else:
            grupo = _legible(limpio)  # "5 a 8 años", "Categoría Sub 7", "NIVEL 1"

    if not recinto:
        # El recinto después del precio: "Mensualidad: $18.000 La Foresta
        # (Sánchez Fontecilla 13770)".
        m = re.search(r"([^()$\d]{3,60}?)\s*\(([^()]{4,})\)\s*$", cuerpo)
        if m and _DIRECCION.search(m.group(2)):
            recinto, direccion = _legible(m.group(1)), m.group(2).strip(" ,.;")
    if not recinto and recinto_pagina:
        recinto = recinto_pagina
    if not recinto:
        # Un encabezado de sección más arriba que nombre un lugar (vóleibol
        # agrupa los niveles bajo "POLIDEPORTIVO SERGIO LIVINGSTONE Altiplano
        # 1830"). Una pregunta o un llamado ("¡Inscríbete…!") es el fin de la
        # sección: de ahí para arriba ya es otra cosa.
        previo = elemento.find_previous(["h2", "h3"])
        while previo is not None:
            texto = _limpio(previo.get_text(" ", strip=True))
            if any(c in texto for c in "?¿!¡"):
                break
            if texto and len(texto) <= 80 and _es_lugar(texto, pestanas):
                recinto, direccion, _ = _separar_recinto(texto)
                break
            previo = previo.find_previous(["h2", "h3"])
    if not recinto and len(pestanas) == 1:
        # La página dice "revisa las pestañas para ver dónde": si hay una
        # sola pestaña de recinto, ahí es.
        recinto = _legible(pestanas[0])

    if recinto and _plano(recinto) == _plano(titulo):
        recinto = ""
    return {"titulo": titulo, "recinto": recinto, "direccion": direccion, "grupo": grupo}


def _precio(texto: str) -> tuple[int | None, bool | None, str]:
    """Mensualidad y matrícula por separado; gratis solo si nada cuesta."""
    plano = _plano(texto)

    def valor(etiqueta: str) -> str:
        m = re.search(rf"{etiqueta}\s*:?\s*((?:entre|desde)?\s*\$?\s*\d[\d.]*|gratis|gratuit\w*|no tiene|sin costo|liberad\w*)",
                      plano)
        return m.group(1).strip() if m else ""

    def monto(crudo: str) -> int | None:
        m = re.search(r"\d[\d.]*", crudo)
        if not m:
            return None
        try:
            return int(m.group(0).replace(".", "")) or None
        except ValueError:
            return None

    def pesos(n: int) -> str:
        return "${:,}".format(n).replace(",", ".")

    mensual, matricula = valor("mensualidad"), valor(r"matr[i]cula")
    monto_mensual, monto_matricula = monto(mensual), monto(matricula)
    sin_costo = lambda crudo: bool(crudo) and monto(crudo) is None  # "gratis", "no tiene"

    if monto_mensual:
        prefijo = "Mensualidad desde" if mensual.startswith(("entre", "desde")) else "Mensualidad"
        texto_precio = f"{prefijo} {pesos(monto_mensual)}"
        if monto_matricula:
            texto_precio += f", matrícula {pesos(monto_matricula)}"
        return monto_mensual, False, texto_precio
    if monto_matricula:
        texto_precio = f"Matrícula {pesos(monto_matricula)}"
        if sin_costo(mensual):
            texto_precio += ", sin mensualidad"
        return monto_matricula, False, texto_precio
    if sin_costo(mensual) or sin_costo(matricula):
        return 0, True, "Gratis"

    # Sin rótulos: "GRATIS" a secas, o "Desde $14.000".
    m = re.search(r"\b(desde|entre)\s*\$?\s*(\d[\d.]*)", plano)
    if m and monto(m.group(2)):
        return monto(m.group(2)), False, f"Desde {pesos(monto(m.group(2)))}"
    if re.search(r"\bgratis\b|\bgratuit", plano):
        return 0, True, "Gratis"
    return None, None, ""


def _eventos_de_ficha(url: str, html: str, fuente: dict, horizonte: int) -> list[Evento]:
    sopa = BeautifulSoup(html, "html.parser")
    titulo_pagina = _titulo(sopa)
    if not titulo_pagina:
        return []
    for basura in sopa.find_all(BASURA):
        basura.decompose()

    recinto_pagina, titulo_base = _recinto_del_titulo(titulo_pagina)
    # Las pestañas de recintos al pie de la ficha (Kadence las marca como
    # role=tab). No dicen qué clase va en cuál, pero si hay una sola, es esa.
    pestanas = [_limpio(t.get_text(" ", strip=True))
                for t in sopa.select('[role="tab"], li.kt-title-item')]
    pestanas = [p for p in dict.fromkeys(pestanas) if p]

    clases: list[dict] = []
    vistas: set = set()
    for contenedor, elemento in _bloques(sopa):
        texto = _limpio(contenedor.get_text(" ", strip=True))
        encabezado = contenedor.find(ENCABEZADOS)
        texto_encabezado = _limpio(encabezado.get_text(" ", strip=True)) if encabezado else ""
        cuerpo = _limpio(texto.replace(texto_encabezado, " ", 1)) if texto_encabezado else texto

        datos = _interpretar(texto_encabezado, cuerpo, elemento, titulo_pagina,
                             titulo_base, recinto_pagina, pestanas)
        precio, gratis, texto_precio = _precio(texto)
        for dias, hora, hora_fin in _horarios(texto):
            # El mismo tramo repetido en la ficha (una caja de "oferta" que
            # duplica la de al lado) es una sola clase.
            clave = (datos["recinto"], datos["grupo"], tuple(dias), hora)
            if clave in vistas:
                continue
            vistas.add(clave)
            clases.append({**datos, "dias": dias, "hora": hora, "hora_fin": hora_fin,
                           "precio": precio, "gratis": gratis, "texto_precio": texto_precio})

    repetidos = Counter((c["titulo"], c["recinto"], tuple(c["dias"])) for c in clases)
    eventos: list[Evento] = []
    for clase in clases:
        sesiones = sesiones_futuras(clase["dias"], clase["hora"], horizonte_dias=horizonte)
        if not sesiones:
            continue
        nombre = clase["titulo"]
        # Mismo taller, mismo recinto, mismos días, otra hora (u otro grupo):
        # son clases distintas para quien elige a cuál puede ir.
        if repetidos[(clase["titulo"], clase["recinto"], tuple(clase["dias"]))] > 1:
            nombre = f"{clase['titulo']} ({clase['hora'].strftime('%H:%M')})"
        cadencia = frase_cadencia(clase["dias"], clase["hora"], clase["hora_fin"])
        descripcion = ", ".join(p for p in (cadencia, clase["grupo"]) if p)
        lugar = clase["recinto"] or fuente.get("nombre", "")
        for sesion in sesiones:
            eventos.append(Evento(
                titulo=nombre[:200],
                categoria=fuente.get("categoria_por_defecto", ""),
                descripcion_corta=resumir(descripcion),
                inicio=sesion,
                fin=None,  # cada sesión es su propio evento (ver talleres.py)
                lugar_nombre=lugar,
                lugar_direccion=clase["direccion"],
                # La comuna de la fuente va primero, como en `tabla`: una
                # corporación municipal dicta en su comuna, y "Av. Grecia"
                # sola podría mandar la clase a Ñuñoa.
                comuna=detectar_comuna(fuente.get("comuna", ""), clase["direccion"], lugar),
                precio_clp=clase["precio"],
                es_gratis=clase["gratis"],
                precio_texto=clase["texto_precio"],
                fuente_tipo="horarios",
                fuente_nombre=fuente.get("nombre", ""),
                fuente_url=url,
                id_externo=f"{url.rstrip('/').rsplit('/', 1)[-1]}:{_plano(lugar)[:30]}:"
                           f"{_plano(clase['grupo'])[:20]}:{clase['hora']:%H%M}",
            ))
    return eventos


def extraer_horarios(fuente: dict, cliente: ClienteEducado) -> list[Evento]:
    fichas = _urls_del_sitemap(fuente, cliente)
    tope = int(fuente.get("tope_fichas", 40))
    fichas = fichas[:tope]
    horizonte = int(fuente.get("horizonte_dias", 30))
    log.info("%s: %d fichas de talleres en el sitemap", fuente.get("nombre"), len(fichas))

    eventos: list[Evento] = []
    con_horario = 0
    for url in fichas:
        ficha = cliente.obtener(url, max_edad_cache_seg=24 * 3600)
        if ficha is None or not ficha.ok:
            continue
        nuevos = _eventos_de_ficha(url, ficha.text, fuente, horizonte)
        if nuevos:
            con_horario += 1
            eventos.extend(nuevos)
        else:
            log.debug("%s: sin horarios legibles en %s", fuente.get("nombre"), url)

    log.info("%s: %d sesiones desde %d de %d fichas", fuente.get("nombre"),
             len(eventos), con_horario, len(fichas))
    return eventos
