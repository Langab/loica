#!/usr/bin/env python3
"""Geocodifica los eventos vigentes y los exporta para el prototipo del mapa.

    python3 exportar_web.py

Deja web/eventos.json con los eventos futuros listos para dibujar.
"""

from __future__ import annotations

import json
import re
import logging
import sys
from datetime import datetime
from pathlib import Path

from loica.almacen import SQL_VIGENTE, Almacen
from loica.correcciones import Correcciones
from loica.geo import Geocodificador
from loica.modelo import es_enlace_de_maquina, es_url_publica

log_urls = logging.getLogger("exportar.urls")

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "web" / "eventos.json"
SALIDA_TALLERES = RAIZ / "web" / "talleres.json"
DIR_FICHAS = RAIZ / "web" / "e"

# Dominio público: es lo que viaja en los links compartidos por WhatsApp.
# Es el único interruptor del dominio: de acá salen las canónicas, los og:url,
# el JSON-LD de cada ficha, el sitemap y el robots.txt. Cambiarlo y volver a
# correr basta para mudar el sitio entero de dirección.
SITIO = "https://loicasantiago.cl"

# Taxonomía provisional: mapea lo que dicen las fuentes a las categorías del
# producto. La definitiva está en definicion_producto_mvp.md.
# La clasificación (categorías + público/edad) vive en loica/clasificar.py,
# generado desde web/_ux_filtros.md. Devuelven (valor, motivo).
from loica.clasificar import clasificar as _clasificar
from loica.clasificar import clasificar_publico
from loica.clasificar import memoria as memoria_categorias, _norm as _norm_clasificador
# Segundo nivel: qué género de fiesta y qué tamaño de panorama. Salen del
# mismo archivo y con la misma regla —vacío antes que inventado—, así que la
# interfaz tiene que estar preparada para recibir "".
from loica.clasificar import clasificar_subcategoria, clasificar_escala
# Tercer eje: qué se asiste una vez (panorama) y qué se toma todas las semanas
# (taller). Cada formato tiene su página y su archivo.
from loica.clasificar import es_taller

# Lo que NO es un panorama aunque aparezca en una agenda cultural.
NO_ES_PANORAMA = [
    "buscamos practicante", "buscamos pasante", "práctica profesional",
    "practica profesional", "oferta laboral", "postula a ", "postulaciones",
    "convocatoria laboral", "llamado a concurso", "concurso público",
    "concurso publico", "se busca ", "vacante", "bases del concurso",
    "postula para",
    "requisitos de postulación", "cartas de apoyo", "fondos de cultura",
    "matrícula", "matricula ", "proceso de admisión", "calendario académico",
    "feria laboral", "feria vocacional", "feria de proyectos",
    "feria de empleo", "feria de postgrados", "feria de universidades",
    "feria científica", "feria cientifica",
]

# Lo que el organizador dejó publicado sin querer. Los sistemas de ticketera y
# los CMS municipales se prueban EN PRODUCCIÓN —se crea un evento falso, se
# emite un ticket, se comprueba que la boletería imprime— y esos eventos quedan
# publicados con nombres que gritan que no son reales. Tres "DEMO -NO REGISTRAR"
# de una corporación municipal llegaron a la portada del sitio.
#
# Va aparte de NO_ES_PANORAMA y con límite de palabra porque estas señales son
# cortas y peligrosas por contención: "demo" está dentro de "demolición" y de
# "Demonios", "test" dentro de "testimonio", y "prueba" dentro de "a prueba de
# balas", que es un nombre de fiesta perfectamente posible.
NO_ES_REAL = re.compile(
    r"(?<![a-záéíóúñ])(demo|test|testing|dummy|borrar|no registrar"
    r"|no publicar|evento de prueba|prueba de evento|sin uso|xxx+)"
    r"(?![a-záéíóúñ])", re.IGNORECASE)


# Nombres de PROGRAMA que las municipalidades ponen donde va el lugar.
# "Deporte Vecinal" no es una dirección: es un programa que ocurre en la sede
# de cada junta de vecinos, y el pipeline apilaba 224 eventos en un solo pin
# con ese nombre. La sede de verdad viene en el título después de la barra
# ("Yoga Ma-Ju 09:45 h. / JJVV Villa Frei"), así que se rescata de ahí.
PROGRAMAS_NO_SON_LUGAR = {
    "deporte vecinal", "futbol", "fútbol", "escuelas abiertas",
    "academias deportivas", "personas mayores", "actividad fisica y salud",
    "talleres deportivos", "deportes",
}


def sede_del_titulo(titulo: str, lugar: str) -> str:
    """Devuelve la sede real si el lugar es un programa y el título la trae."""
    if _plano_simple(lugar) not in PROGRAMAS_NO_SON_LUGAR or " / " not in titulo:
        return ""
    sede = titulo.split(" / ")[-1].strip().rstrip(". ")
    # Una sede tiene nombre; un resto de horario ("Sa 09:00") no sirve.
    if len(sede) < 4 or re.match(r"^[LMXJVSD][auiaeo]?[- ]", sede):
        return ""
    return sede


def _plano_simple(texto: str) -> str:
    import unicodedata
    plano = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in plano if unicodedata.category(c) != "Mn").strip()


# "Nado Libre Ma-Ju 06:00 h." — la municipalidad mete el horario en el nombre
# porque es su única forma de distinguir una clase de otra en una planilla.
# En una tarjeta que ya muestra los días y la hora aparte, ese código sobra y
# hace la lista ilegible.
_CODIGO_HORARIO = re.compile(
    r"\s*[/·-]?\s*\b(?:lu|ma|mi|ju|vi|sa|do)\b(?:\s*[-y/]\s*\b(?:lu|ma|mi|ju|vi|sa|do)\b)*"
    r"\.?\s*\d{1,2}[:.]\d{2}\s*(?:h|hrs?)?\.?", re.IGNORECASE)


# Los días de la semana leídos del título municipal. La corporación publica
# "Nado Libre Lu-Mi-Vi 06:00 h." como UNA temporada con fecha de término, no
# como sesiones sueltas, así que `colapsar_series` nunca le calcula
# `dias_semana` — y sin días, el filtro "¿qué clase puedo tomar el martes?"
# no puede responder y el filtro "Hoy" muestra la clase de Lu-Mi-Vi un sábado.
# El dato está escrito en el título, en el mismo código de horario que ya
# reconoce _CODIGO_HORARIO: acá solo se traduce a números (0=lunes).
_DIA_TOKEN = {
    "lu": 0, "lunes": 0, "ma": 1, "martes": 1, "mi": 2, "miercoles": 2,
    "ju": 3, "jueves": 3, "vi": 4, "viernes": 4,
    "sa": 5, "sabado": 5, "sabados": 5, "do": 6, "domingo": 6, "domingos": 6,
}
_DIAS_EN_TITULO = re.compile(
    r"\b(lunes|martes|miercoles|jueves|viernes|sabados?|domingos?"
    r"|lu|ma|mi|ju|vi|sa|do)\b")
_RANGO_DIAS = re.compile(r"\b(lu|ma|mi|ju|vi|sa|do)\s+a\s+(lu|ma|mi|ju|vi|sa|do)\b")


def dias_del_titulo(titulo: str) -> list[int]:
    """Los días (0=lunes) que el título declara; [] si no declara ninguno.

    Solo se usa para talleres: en un título de concierto "vi" o "do" serían
    ruido, pero en el catálogo municipal el código de horario es la norma.
    """
    plano = _plano_simple(titulo)
    dias: set[int] = set()
    rango = _RANGO_DIAS.search(plano)
    if rango:
        desde, hasta = _DIA_TOKEN[rango.group(1)], _DIA_TOKEN[rango.group(2)]
        if desde <= hasta:
            dias.update(range(desde, hasta + 1))
    for token in _DIAS_EN_TITULO.findall(plano):
        dias.add(_DIA_TOKEN[token])
    return sorted(dias)


def _titulo_sin_horario(titulo: str) -> str:
    """Saca el código de horario del título; deja el nombre de la actividad."""
    limpio = _CODIGO_HORARIO.sub(" ", titulo)
    limpio = re.sub(r"\s*[/·]\s*$", "", " ".join(limpio.split())).strip(" .-/·")
    # Si al sacar el código no queda nombre, se devuelve el original: vale más
    # un título feo que una tarjeta sin título.
    return limpio if len(limpio) >= 3 else titulo


def colapsar_series(eventos: list[dict]) -> tuple[list[dict], int]:
    """Junta las sesiones repetidas de un mismo taller en UNA tarjeta.

    Un yoga de martes y jueves que corre tres meses llegaba como veinte
    tarjetas idénticas en el mismo punto: la mitad del catastro eran sesiones
    repetidas de 320 talleres, y en el mapa se veían como pilas de cuatrocientos
    pines encima del mismo polideportivo. Para quien abre la app a preguntar
    "¿qué hago hoy?", eso entierra los conciertos y las obras.

    La tarjeta que queda dice cuándo es la próxima sesión y en qué días se
    repite. Los días van en `dias_semana` (0=lunes) y hasta cuándo en `fin`,
    para que los filtros de fecha sigan encontrándola: un taller de sábados
    tiene que seguir apareciendo en "este fin de semana" aunque su próxima
    sesión sea dentro de dos días.

    Solo se colapsa lo que de verdad es una serie: mismo título, mismo lugar y
    misma hora, tres sesiones o más. Dos funciones de una obra no son un
    taller, y fusionarlas escondería una.
    """
    grupos: dict[tuple, list[dict]] = {}
    for ev in eventos:
        if not ev.get("inicio"):
            grupos.setdefault(("sin-fecha", id(ev)), []).append(ev)
            continue
        hora = ev["inicio"][11:16]
        # Se agrupa por el título YA limpio de su código de horario: la fuente
        # escribe la misma clase como "Fútbol 5 Ju 16:45 h. / Villa Olímpica"
        # y "Fútbol 5 Ju 16:45 h. / Villa Olímpica." —con punto y sin punto— y
        # agrupando por el texto crudo quedaban dos tarjetas gemelas.
        clave = _titulo_sin_horario(ev["titulo"]).strip().lower()
        grupos.setdefault((clave, ev["lugar"], hora), []).append(ev)

    salida: list[dict] = []
    colapsados = 0
    for sesiones in grupos.values():
        if len(sesiones) < 3:
            salida.extend(sesiones)
            continue
        sesiones.sort(key=lambda e: e["inicio"])
        # Si ya trae `fin`, es una temporada continua (una exposición de un
        # mes), no una serie de sesiones sueltas: eso ya lo colapsó agrupar.py.
        if any(s.get("fin") for s in sesiones):
            salida.extend(sesiones)
            continue
        dias = sorted({datetime.fromisoformat(s["inicio"]).weekday()
                       for s in sesiones})
        tarjeta = dict(sesiones[0])
        tarjeta["fin"] = sesiones[-1]["inicio"]
        tarjeta["dias_semana"] = dias
        tarjeta["sesiones"] = len(sesiones)
        tarjeta["titulo"] = _titulo_sin_horario(tarjeta["titulo"])
        salida.append(tarjeta)
        colapsados += len(sesiones) - 1

    salida.sort(key=lambda e: e.get("inicio") or "9999")
    return salida, colapsados


def _lejos(lat1, lon1, lat2, lon2, km: float) -> bool:
    """True si los dos puntos están a más de `km` de distancia."""
    return ((lat1 - lat2) * 111) ** 2 + ((lon1 - lon2) * 92) ** 2 > km ** 2


def es_panorama(titulo: str, descripcion: str) -> tuple[bool, str]:
    # El evento de prueba se busca SOLO en el título. En una descripción larga
    # "demo" o "test" aparecen de sobra hablando de otra cosa —una demo de un
    # grupo, un test de sonido— y ahí la palabra no dice nada del evento; en el
    # título sí, porque el título es lo que el organizador escribió para
    # nombrarlo.
    prueba = NO_ES_REAL.search(titulo or "")
    if prueba:
        return False, f"evento de prueba: {prueba.group(0)}"
    texto = f"{titulo} {descripcion}".lower()
    for senal in NO_ES_PANORAMA:
        if senal in texto:
            return False, senal
    # La memoria de categorías también sabe decir "esto no es un panorama":
    # abonos, membresías, campañas de socios, convocatorias. Son reglas con
    # `categoria: descartar` en config/correcciones/categorias.yaml, y viven
    # ahí y no en la lista de arriba para que la revisión las agregue sin
    # tocar código.
    calce = memoria_categorias().descartar(_norm_clasificador(titulo),
                                           _norm_clasificador(texto))
    if calce:
        return False, f"memoria: {calce[0].nombre} («{calce[1]}»)"
    return True, ""


PLANTILLA_FICHA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">

<!-- Red de seguridad, no la seguridad. Lo que de verdad impide una inyección
     es que el título y el link ya vengan escapados y filtrados desde Python;
     esto es lo que queda en pie si algún día se escapa uno. `img-src https:`
     va abierto a propósito: las fotos son de los organizadores y viven en
     cientos de dominios que no se pueden listar. Ojo con `frame-ancestors`:
     en un <meta> el navegador lo ignora, solo sirve como cabecera HTTP, y
     GitHub Pages no deja poner cabeceras. Y `upgrade-insecure-requests` no
     va: en Pages no hace nada y abierto por LAN desde el celular dejaba la
     ficha en blanco (el detalle está en mapa.html). -->
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://cloudflareinsights.com; object-src 'none'; base-uri 'none'; form-action 'self'">
<meta name="referrer" content="strict-origin-when-cross-origin">

<title>{titulo_html} — Loica</title>
<meta name="description" content="{descripcion_meta}">
<link rel="canonical" href="{url_ficha}">

<!-- Open Graph: esto es lo que se ve al pegar el link en WhatsApp -->
<meta property="og:type" content="article">
<meta property="og:site_name" content="Loica">
<meta property="og:locale" content="es_CL">
<meta property="og:title" content="{titulo_html}">
<meta property="og:description" content="{descripcion_meta}">
<meta property="og:url" content="{url_ficha}">
{og_imagen}
<meta name="twitter:card" content="{tipo_tarjeta}">
<meta name="twitter:title" content="{titulo_html}">
<meta name="twitter:description" content="{descripcion_meta}">

<script type="application/ld+json">{jsonld}</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;800&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../loica.css?v=29">
<style>
  body{{min-height:100vh;min-height:100dvh}}
  .ficha-sola{{max-width:620px;margin:0 auto;padding:var(--e-4) var(--e-4) var(--e-12)}}
  .foto{{border-radius:var(--r-lg);overflow:hidden;background:var(--fondo-hundido);
    aspect-ratio:16/9;display:grid;place-items:center;margin-bottom:var(--e-5)}}
  .foto:empty,.foto.sin-foto{{aspect-ratio:2.6/1}}
  .foto img{{width:100%;height:100%;object-fit:cover}}
  .foto svg{{width:78px;height:78px;opacity:.75}}
  .dato{{display:flex;gap:var(--e-3);padding:11px 0;border-top:1px solid var(--borde)}}
  .dato .et{{color:var(--tinta-tenue);width:86px;flex:none;font-size:var(--t-sm);font-weight:600}}
  /* Era un enlace de 20px de alto y es el único camino de vuelta desde una
     ficha compartida por WhatsApp: se le da área de dedo. */
  .volver{{display:inline-flex;align-items:center;gap:7px;text-decoration:none;
    color:var(--tinta-suave);font-weight:600;font-size:var(--t-sm);
    min-height:44px;margin-bottom:var(--e-1)}}
  .pie-fuente{{margin-top:var(--e-5);font-size:var(--t-xs);color:var(--tinta-tenue);text-align:center}}
</style>
</head>
<!-- con-nav-inferior reserva el alto de la barra de abajo. Sin esto la línea
     que dice de qué fuente salió el evento —que es el motivo de existir de la
     ficha— queda debajo de la barra y no se lee. -->
<body class="con-nav-inferior">
<div class="barra" id="barra"></div>

<article class="ficha-sola">
  <a class="volver" href="../{pagina_madre}">← {volver_texto}</a>
  <div class="foto" id="foto">{foto}</div>
  <span class="mascota-nombre" id="etiqueta-cat"></span>
  <h1 style="margin:var(--e-2) 0 var(--e-4)">{titulo_html}</h1>

  {bloque_fuente}

  <div id="compartir" style="margin-top:var(--e-4)"></div>

  <div class="dato" style="margin-top:var(--e-4)">
    <span class="et">Cuándo</span><span>{cuando}</span></div>
  <div class="dato"><span class="et">Dónde</span><span>{donde}</span></div>
  <div class="dato"><span class="et">Precio</span>
    <span class="precio{clase_precio}">{precio}</span></div>
  {bloque_descripcion}

  <p style="margin-top:var(--e-5)">
    <a class="boton secundario bloque" href="../{pagina_madre}#/e/{id_evento}">{ver_todos_texto}</a></p>

  <div class="pie-fuente">Información publicada por <b>{fuente_html}</b>.<br>
    Loica solo la indexa y te manda a la fuente.</div>
</article>

<nav class="nav-inferior" id="nav-inferior" aria-label="Navegación principal"></nav>
<script src="../loica.js?v=29"></script>
<script>
  pintarBarra("{pagina_madre}", "../");
  const EV = {evento_json};
  document.getElementById("etiqueta-cat").innerHTML =
    carita(cat(EV.categoria).mascota, cat(EV.categoria).hex, 20) + " " + cat(EV.categoria)[IDIOMA];
  document.getElementById("compartir").appendChild(botonesCompartir(EV));
  const caja = document.getElementById("foto");
  const ponerMascota = () => {{
    if(!caja.querySelector("img") && !caja.querySelector("svg"))
      caja.innerHTML = cuerpo(cat(EV.categoria).mascota, cat(EV.categoria).hex, 96);
  }};
  ponerMascota();
  new MutationObserver(ponerMascota).observe(caja, {{childList:true}});
</script>
<!-- Cloudflare Web Analytics: cuenta visitas sin cookies y sin huella
     digital, así que el sitio no necesita banner de consentimiento (la Ley
     21.719 rige desde diciembre de 2026). El token es público a propósito:
     viaja en el HTML de todas las páginas, no es una credencial. Si se toca,
     hay que tocarlo en las diez páginas Y en la plantilla de exportar_web.py,
     igual que el ?v= de los estilos. -->
<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "05b8b07df9224b248d539904774ba661"}}'></script>
</body>
</html>
"""


def _escapar(texto: str) -> str:
    # La comilla simple también: hoy todos los atributos de la plantilla usan
    # comillas dobles, pero basta que alguien escriba un atributo con simples
    # para que un título con apóstrofo —"Rock 'n' Roll"— se salga del atributo.
    return (str(texto or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def _json_en_script(dato) -> str:
    """Serializa un dato para incrustarlo DENTRO de una etiqueta <script>.

    `json.dumps` a secas no sirve acá. El parser de HTML no entiende de JSON:
    apenas ve la secuencia `</script` cierra el bloque, sin importar que vaya
    dentro de un string. Un evento cuyo título sea

        Concierto </script><img src=x onerror=...> gratis

    —y los títulos los escriben terceros, no nosotros— parte la etiqueta en dos
    y lo que sigue se interpreta como HTML en el dominio de Loica. Escapando
    `<` y `>` como \\u003c y \\u003e el JSON sigue siendo el mismo string (los
    lee JSON.parse y el motor de JS igual), pero deja de existir la secuencia
    que el parser de HTML reconoce.

    U+2028 y U+2029 van por otro motivo: son saltos de línea legales en JSON
    pero ilegales dentro de un literal de JavaScript, y rompen el script entero
    con un error de sintaxis.
    """
    crudo = json.dumps(dato, ensure_ascii=False)
    return (crudo.replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _url_publicable(url: str) -> str:
    """La URL si se puede publicar; string vacío si no.

    Segunda barrera. La primera está en `Evento.es_valido()`, en la puerta de
    entrada, pero la base ya tiene filas guardadas antes de que esa validación
    existiera y este archivo lee de la base, no del extractor. Un `href` es el
    último lugar donde conviene confiar.
    """
    if not es_url_publica(url or ""):
        if url:
            log_urls.warning("URL descartada por esquema no publicable: %.80s", url)
        return ""
    return url


# La página a la que vuelve una ficha, con sus dos textos de vuelta. Un taller
# vuelve a la de talleres; un panorama de una categoría con pestaña propia
# (fiestas, teatro, música, charlas, desde el 02-09-2026) vuelve a su pestaña;
# el resto, al mapa general. Es el espejo de CATEGORIA_DE_PAGINA en loica.js:
# si se agrega una pestaña allá, se agrega acá.
PAGINA_DE_CATEGORIA = {
    "fiesta": ("fiestas.html", "Ver todas las fiestas", "Ver en el mapa de fiestas"),
    "teatro": ("teatro.html", "Ver todo el teatro", "Ver en el mapa de teatro"),
    "musica": ("musica.html", "Ver toda la música", "Ver en el mapa de música"),
    "charla": ("charlas.html", "Ver todas las charlas", "Ver en el mapa de charlas"),
}


def pagina_madre(ev: dict) -> tuple[str, str, str]:
    """(página, texto del link de volver, texto del botón de abajo)."""
    if ev.get("formato") == "taller":
        return ("talleres.html", "Ver todos los talleres y clases",
                "Ver en la página de talleres")
    return PAGINA_DE_CATEGORIA.get(ev.get("categoria") or "", (
        "mapa.html", "Ver todos los panoramas de Santiago", "Ver en el mapa"))


def escribir_fichas(eventos: list[dict]) -> int:
    """Una página HTML por evento — panoramas Y talleres.

    Es lo que permite que un link compartido por WhatsApp muestre foto, título
    y fecha en vez de un link pelado — y que el tráfico vuelva a Loica en vez de
    irse directo a la fuente. Todo el plan de marketing depende de esto.

    La ficha de un taller vuelve a la página de talleres, no al mapa: el botón
    "Ver en el mapa" de una clase de natación llevaba a un mapa donde la clase
    ya no existe, que es un link que promete y no cumple. Por la misma razón
    una fiesta vuelve a fiestas.html y no al mapa general (ver pagina_madre).
    """
    DIR_FICHAS.mkdir(parents=True, exist_ok=True)
    for viejo in DIR_FICHAS.glob("*.html"):
        viejo.unlink()

    for ev in eventos:
        madre, volver_texto, ver_todos_texto = pagina_madre(ev)
        inicio = datetime.fromisoformat(ev["inicio"]) if ev["inicio"] else None
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                 "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        cuando = "—"
        if inicio:
            cuando = f"{dias[inicio.weekday()]} {inicio.day} de {meses[inicio.month - 1]}"
            if inicio.hour or inicio.minute:
                cuando += f", {inicio.hour:02d}:{inicio.minute:02d}"

        precio = ("Entrada liberada" if ev["gratis"]
                  else (f"${ev['precio']:,}".replace(",", ".") if ev["precio"] else "Sin información"))
        donde = ev["lugar"] + (f", {ev['comuna']}" if ev["comuna"] else "")

        resumen = f"{cuando} · {donde} · {precio}"
        if ev["descripcion"]:
            resumen += f" — {ev['descripcion'][:110]}"

        # Las dos URLs que salen del pipeline y terminan en un atributo del
        # navegador. Se filtran acá, una sola vez, y de acá en adelante se usan
        # las versiones limpias — incluida la copia que viaja en el JSON de la
        # página, que el JS de compartir vuelve a leer.
        url_fuente = _url_publicable(ev["url"])
        imagen = _url_publicable(ev["imagen"])
        ev = {**ev, "url": url_fuente, "imagen": imagen}

        jsonld = {
            "@context": "https://schema.org", "@type": "Event",
            "name": ev["titulo"], "startDate": ev["inicio"],
            "eventStatus": "https://schema.org/EventScheduled",
            "location": {"@type": "Place", "name": ev["lugar"],
                         "address": {"@type": "PostalAddress",
                                     "addressLocality": ev["comuna"] or "Santiago",
                                     "addressCountry": "CL"}},
            "url": f"{SITIO}/e/{ev['id']}.html",
        }
        if imagen:
            jsonld["image"] = imagen
        if ev["gratis"] or ev["precio"]:
            jsonld["offers"] = {"@type": "Offer", "price": ev["precio"] or 0,
                                "priceCurrency": "CLP", "url": url_fuente}

        html = PLANTILLA_FICHA.format(
            titulo_html=_escapar(ev["titulo"]),
            descripcion_meta=_escapar(resumen[:180]),
            url_ficha=f"{SITIO}/e/{ev['id']}.html",
            og_imagen=(f'<meta property="og:image" content="{_escapar(imagen)}">'
                       if imagen else
                       f'<meta property="og:image" content="{SITIO}/og-default.png">'),
            tipo_tarjeta="summary_large_image",
            jsonld=_json_en_script(jsonld),
            # Las fotos son del organizador y se enlazan, no se copian. Algunos
            # servidores las bloquean desde otro dominio: si eso pasa, entra la
            # mascota de la categoría en vez de quedar un hueco roto.
            foto=(f'<img src="{_escapar(imagen)}" alt="" '
                  f'onerror="this.remove();document.getElementById(\'foto\')'
                  f'.classList.add(\'sin-foto\')">' if imagen else ""),
            # Sin link publicable no se dibuja el botón. Un href vacío recarga
            # la ficha, que es peor que no ofrecer el botón: promete llevarte a
            # la fuente y no te lleva a ninguna parte.
            bloque_fuente=(f'<a class="boton bloque" href="{_escapar(url_fuente)}" '
                           f'target="_blank" rel="noopener nofollow">\n'
                           f'    Ver en la fuente original ↗</a>' if url_fuente else ""),
            cuando=_escapar(cuando), donde=_escapar(donde),
            precio=_escapar(precio),
            clase_precio=" libre" if ev["gratis"] else "",
            bloque_descripcion=(f'<div class="dato"><span class="et"></span>'
                                f'<span>{_escapar(ev["descripcion"])}</span></div>'
                                if ev["descripcion"] else ""),
            id_evento=_escapar(ev["id"]), fuente_html=_escapar(ev["fuente"]),
            evento_json=_json_en_script(ev),
            pagina_madre=madre, volver_texto=volver_texto,
            ver_todos_texto=ver_todos_texto,
        )
        (DIR_FICHAS / f"{ev['id']}.html").write_text(html, encoding="utf-8")

    return len(eventos)


# Las páginas fijas del sitio. El sitemap descubre solo las fichas de web/e/
# porque se generan acá; estas hay que nombrarlas.
# Habla, comer y blog no están a propósito: desde el 02-09-2026 quedaron
# ocultas —existen y abren por URL, pero no se enlazan ni se indexan—.
PAGINAS_FIJAS = [
    "", "mapa.html", "fiestas.html", "teatro.html", "musica.html", "charlas.html",
    "cine.html", "talleres.html", "descuentos.html", "calendario.html",
    "agrega.html", "nosotros.html",
]

# Los ids de ficha son hashes hexadecimales. Al sitemap solo entra lo que
# calza con eso: es el mismo criterio de la casa de no dejar que un dato de
# fuente llegue crudo a un archivo que otro sistema va a leer.
ID_FICHA = re.compile(r"^[0-9a-f]{8,32}$")


def escribir_sitemap(ids: list[str], dia: str) -> int:
    """El índice que leen los buscadores. Sin esto, Google descubre las fichas
    solo si alguien las enlaza, y a las de un panorama que dura tres días no
    las enlaza nadie a tiempo."""
    urls = [f"{SITIO}/{pagina}" for pagina in PAGINAS_FIJAS]
    urls += [f"{SITIO}/e/{i}.html" for i in ids if ID_FICHA.match(i)]
    cuerpo = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{dia}</lastmod></url>" for u in urls)
    (RAIZ / "web" / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{cuerpo}\n</urlset>\n", encoding="utf-8")
    return len(urls)


def escribir_robots() -> None:
    """Se genera en vez de escribirse a mano para que el dominio salga de
    SITIO y no quede una dirección vieja apuntando a un sitemap que no existe."""
    (RAIZ / "web" / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITIO}/sitemap.xml\n", encoding="utf-8")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("exportar")

    almacen = Almacen()
    filas = almacen.con.execute(
        """SELECT * FROM eventos
           -- SQL_VIGENTE mira la fecha de TÉRMINO cuando existe: una muestra
           -- que abrió hace un mes y cierra en septiembre sigue estando.
           -- 'localtime' dentro de él NO es decorativo: SQLite responde en
           -- UTC, que a las 20:00 de Chile ya es el día siguiente. Sin eso,
           -- cualquier corrida de la tarde publicaba el sitio SIN los
           -- panoramas que quedaban de hoy —308 eventos en la corrida donde
           -- se detectó—, justo a la hora en que alguien abre la app a
           -- preguntar qué hacer.
           WHERE """ + SQL_VIGENTE + """ AND estado != 'descartado'
           ORDER BY inicio""",
    ).fetchall()

    geo = Geocodificador()
    # La memoria de arreglos (config/correcciones/): lo que la revisión ya
    # corrigió una vez se aplica solo acá, en cada corrida, ANTES de
    # geocodificar — una dirección corregida mejora la búsqueda y unas
    # coordenadas corregidas se la ahorran completa.
    corr = Correcciones()
    eventos = []
    sin_ubicar = 0
    corregidos = 0
    discrepantes = 0
    descartados = []

    for fila in filas:
        panorama, senal = es_panorama(fila["titulo"], fila["descripcion_corta"] or "")
        if not panorama:
            descartados.append(f'{fila["titulo"][:52]} (por "{senal}")')
            continue

        # Puerta de publicación: la app promete dejarte en la fuente original.
        # Un link a un sitemap o a una API deja al usuario mirando XML crudo, así
        # que ese evento no sale al sitio. La fila queda en la base para el
        # curador; lo que se cierra es la puerta de salida, no el dato.
        if es_enlace_de_maquina(fila["fuente_url"] or ""):
            descartados.append(f'{fila["titulo"][:52]} (link roto: {fila["fuente_url"]})')
            continue

        categoria, _ = _clasificar(fila["titulo"], fila["categoria"] or "",
                                   fila["descripcion_corta"] or "",
                                   fila["lugar_nombre"] or "", fila["fuente_nombre"] or "")
        publico, _ = clasificar_publico(fila["titulo"], fila["descripcion_corta"] or "",
                                        categoria, fila["lugar_nombre"] or "",
                                        fila["fuente_nombre"] or "")
        # La subcategoría cuelga de la categoría —el género de la fiesta, el
        # tipo de obra—, así que se calcula DESPUÉS y con la categoría ya
        # resuelta. La escala no depende de ella: se lee del recinto.
        subcategoria, _ = clasificar_subcategoria(
            categoria, fila["titulo"], fila["categoria"] or "",
            fila["descripcion_corta"] or "", fila["lugar_nombre"] or "",
            fila["fuente_nombre"] or "")
        escala, _ = clasificar_escala(
            fila["titulo"], fila["lugar_nombre"] or "",
            fila["fuente_nombre"] or "", fila["precio_clp"],
            fila["descripcion_corta"] or "")

        # Si la fuente ya entregó coordenadas, mandan ellas
        ev = {
            "id": fila["hash_dedup"],
            "titulo": fila["titulo"],
            "inicio": fila["inicio"],
            "fin": fila["fin"],
            "lugar": (sede_del_titulo(fila["titulo"], fila["lugar_nombre"] or "")
                      or fila["lugar_nombre"] or fila["fuente_nombre"]),
            "direccion": fila["lugar_direccion"] or "",
            "comuna": fila["comuna"] or "",
            "lat": fila["lat"],
            "lon": fila["lon"],
            "precision": "fuente" if fila["lat"] is not None else "",
            "gratis": bool(fila["es_gratis"]),
            "precio": fila["precio_clp"],
            "precio_texto": fila["precio_texto"] or "",
            "categoria": categoria,
            # Ambos pueden venir vacíos y eso es una respuesta, no un error:
            # una fonda no tiene género y una tocata sin recinto conocido no
            # tiene tamaño. El filtro que los use tiene que contar con eso.
            "subcategoria": subcategoria,
            "escala": escala,
            "publico": publico,
            "descripcion": fila["descripcion_corta"] or "",
            "imagen": fila["imagen_url"] or "",
            "fuente": fila["fuente_nombre"],
            "url": fila["fuente_url"],
        }

        # La memoria de arreglos pisa lo extraído: si la revisión ya dijo que
        # este lugar queda en otra parte o que este evento es de otra
        # categoría, eso vale más que lo que dijo la fuente o el clasificador.
        tocados = corr.aplicar_a_evento(ev)
        if ev.pop("descartar", False):
            descartados.append(f'{ev["titulo"][:52]} (corrección: descartado)')
            continue
        if tocados:
            corregidos += 1

        # Las coordenadas de la fuente no son sagradas. Toliv publicaba Club 1
        # en (-33.402, -70.643), norte de Recoleta, mientras su propia ficha
        # decía "Bombero Núñez #1" — que está en Bellavista, 2,7 km al sur. Es
        # una ticketera geocodificando a la rápida. Cuando la dirección
        # publicada calza EXACTO en el catastro y contradice a las coordenadas
        # por más de 700 m, gana la dirección: es el dato que una persona
        # puede leer y verificar.
        # Se resuelve en modo flexible: el catastro no siempre tiene el número
        # exacto (de Bombero Núñez conoce el 22 y el 98, no el 1) y exigirlo
        # dejaba pasar el error. La red de seguridad es doble: la dirección
        # resuelta tiene que caer cerca de la comuna declarada —de eso se
        # encarga _elegir— y la contradicción tiene que superar 1 km, más que
        # el ancho de una cuadra.
        if ev["lat"] is not None and ev["direccion"]:
            real = geo.indice.direccion(ev["direccion"], ev["comuna"])
            if real and _lejos(ev["lat"], ev["lon"], real[0], real[1], 1.0):
                log.info("  %s: la fuente decía %.4f,%.4f pero su dirección (%s) "
                         "está en %.4f,%.4f — gana la dirección",
                         ev["lugar"][:34], ev["lat"], ev["lon"],
                         ev["direccion"][:40], real[0], real[1])
                ev["lat"], ev["lon"] = real[0], real[1]
                ev["precision"] = "calle"
                discrepantes += 1

        if ev["lat"] is None:
            lat, lon, precision = geo.ubicar(ev["lugar"], ev["direccion"], ev["comuna"])
            ev["lat"], ev["lon"] = lat, lon
            ev["precision"] = precision
            if lat is None:
                # No se descarta: sale en la lista sin pin. Botar 42 eventos
                # reales (entre ellos 20 obras de teatro) es peor que
                # mostrarlos sin mapa.
                sin_ubicar += 1
                ev["precision"] = "sin_ubicar"

        eventos.append(ev)

    # Una coordenada que comparten VARIOS lugares distintos no es la ubicación
    # de ninguno: es el punto al que la ticketera manda lo que no supo
    # geocodificar. Toliv usa el centro de la comuna para todo lo que no
    # reconoce, y el mapa lo dibujaba como pin exacto. Se degrada a
    # aproximado, que es lo que de verdad es: la página lo atenúa y el lugar
    # entra a la cola de corrección en vez de mentir con precisión.
    eventos, sesiones_juntadas = colapsar_series(eventos)

    por_punto: dict[tuple, set] = {}
    for ev in eventos:
        if ev["precision"] == "fuente" and ev["lat"] is not None:
            por_punto.setdefault((round(ev["lat"], 4), round(ev["lon"], 4)),
                                 set()).add(ev["lugar"])
    compartidos = {p for p, lugares in por_punto.items() if len(lugares) > 1}
    degradados = 0
    for ev in eventos:
        if (ev["precision"] == "fuente" and ev["lat"] is not None
                and (round(ev["lat"], 4), round(ev["lon"], 4)) in compartidos):
            ev["precision"] = "comuna"
            degradados += 1

    geo.guardar()
    almacen.cerrar()

    # ---- El corte entre panoramas y talleres ----
    # Un panorama se asiste una vez; un taller se toma todas las semanas. En el
    # mapa convivían los dos y las clases eran el 55% del catastro: el nado
    # libre de las 06:00 enterraba a los conciertos. Cada formato va a su
    # archivo y a su página. Se corta DESPUÉS de colapsar series, porque
    # `dias_semana` —la serie semanal— es la señal más directa de taller.
    talleres = []
    panoramas = []
    for ev in eventos:
        if ev.get("fin") and ev.get("inicio") and ev["fin"] < ev["inicio"]:
            # "hasta el 15 de agosto" se interpreta a las 00:00 y queda antes
            # de la función de las 15:00 del mismo día: fin < inicio no
            # significa nada y rompe los cálculos de duración río abajo.
            ev["fin"] = None
        de_taller, _ = es_taller(ev["titulo"], ev["categoria"], ev["fuente"],
                                 ev.get("dias_semana"))
        ev["formato"] = "taller" if de_taller else "panorama"
        if de_taller and not ev.get("dias_semana"):
            # Primero el título ("Nado Libre Lu-Mi-Vi") y si calla, la
            # descripción: Huechuraba y Santiago escriben los días AHÍ
            # ("todos los lunes, miércoles y viernes a las 08:20"). Sin esta
            # segunda lectura, 457 clases quedaban sin días y el filtro "Hoy"
            # las mostraba TODOS los días — la clase de Lu-Mi-Vi apareciendo
            # un sábado fue el reclamo que destapó esto. Con ella, 429 de las
            # 457 recuperan sus días.
            del_texto = (dias_del_titulo(ev["titulo"])
                         or dias_del_titulo(ev["descripcion"] or ""))
            if del_texto:
                ev["dias_semana"] = del_texto
        (talleres if de_taller else panoramas).append(ev)

    ahora = datetime.now().isoformat(timespec="seconds")
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({
        "generado": ahora,
        "total": len(panoramas),
        "eventos": panoramas,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    SALIDA_TALLERES.write_text(json.dumps({
        "generado": ahora,
        "total": len(talleres),
        "talleres": talleres,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    gratis = sum(1 for e in panoramas if e["gratis"])
    exactos = sum(1 for e in panoramas if e["precision"] == "recinto")
    fichas = escribir_fichas(panoramas + talleres)
    log.info("Fichas individuales para compartir: %d en web/e/", fichas)
    direcciones = escribir_sitemap([e["id"] for e in panoramas + talleres],
                                   ahora[:10])
    escribir_robots()
    log.info("Sitemap con %d direcciones y robots.txt para los buscadores",
             direcciones)

    con_imagen = sum(1 for e in panoramas if e["imagen"])
    exactos += sum(1 for e in panoramas if e["precision"] in ("fuente", "correccion", "calle"))
    log.info("Exportados %d panoramas (%d gratis, %d con ubicación exacta, "
             "%d con imagen) y %d talleres y clases",
             len(panoramas), gratis, exactos, con_imagen, len(talleres))
    eventos = panoramas  # los resúmenes de abajo hablan del mapa
    if corregidos:
        log.info("Con correcciones de la memoria aplicadas: %d", corregidos)
    if discrepantes:
        log.info("Coordenadas de la fuente descartadas por contradecir su "
                 "propia dirección: %d", discrepantes)
    if degradados:
        log.info("Pines degradados a aproximados por compartir coordenada "
                 "entre lugares distintos: %d", degradados)
    if sesiones_juntadas:
        log.info("Sesiones repetidas juntadas en su taller: %d", sesiones_juntadas)
    if sin_ubicar:
        log.info("Sin pin en el mapa (salen solo en la lista): %d", sin_ubicar)
    if descartados:
        log.info("Descartados por no ser panoramas (%d):", len(descartados))
        for d in descartados:
            log.info("   · %s", d)
    log.info("Archivos: %s y %s", SALIDA, SALIDA_TALLERES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
