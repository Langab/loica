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
DIR_FICHAS = RAIZ / "web" / "e"

# Dominio público: es lo que viaja en los links compartidos por WhatsApp.
SITIO = "https://langab.github.io/loica"

# Taxonomía provisional: mapea lo que dicen las fuentes a las categorías del
# producto. La definitiva está en definicion_producto_mvp.md.
# La clasificación (categorías + público/edad) vive en loica/clasificar.py,
# generado desde web/_ux_filtros.md. Devuelven (valor, motivo).
from loica.clasificar import clasificar as _clasificar
from loica.clasificar import clasificar_publico
# Segundo nivel: qué género de fiesta y qué tamaño de panorama. Salen del
# mismo archivo y con la misma regla —vacío antes que inventado—, así que la
# interfaz tiene que estar preparada para recibir "".
from loica.clasificar import clasificar_subcategoria, clasificar_escala

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
    texto = f"{titulo} {descripcion}".lower()
    for senal in NO_ES_PANORAMA:
        if senal in texto:
            return False, senal
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
     GitHub Pages no deja poner cabeceras. -->
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; upgrade-insecure-requests">
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
<link rel="stylesheet" href="../loica.css?v=16">
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
  <a class="volver" href="../mapa.html">← Ver todos los panoramas de Santiago</a>
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
    <a class="boton secundario bloque" href="../mapa.html#/e/{id_evento}">Ver en el mapa</a></p>

  <div class="pie-fuente">Información publicada por <b>{fuente_html}</b>.<br>
    Loica solo la indexa y te manda a la fuente.</div>
</article>

<nav class="nav-inferior" id="nav-inferior" aria-label="Navegación principal"></nav>
<script src="../loica.js?v=16"></script>
<script>
  pintarBarra("mapa.html", "../");
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


def escribir_fichas(eventos: list[dict]) -> int:
    """Una página HTML por evento.

    Es lo que permite que un link compartido por WhatsApp muestre foto, título
    y fecha en vez de un link pelado — y que el tráfico vuelva a Loica en vez de
    irse directo a la fuente. Todo el plan de marketing depende de esto.
    """
    DIR_FICHAS.mkdir(parents=True, exist_ok=True)
    for viejo in DIR_FICHAS.glob("*.html"):
        viejo.unlink()

    for ev in eventos:
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
        )
        (DIR_FICHAS / f"{ev['id']}.html").write_text(html, encoding="utf-8")

    return len(eventos)


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

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({
        "generado": datetime.now().isoformat(timespec="seconds"),
        "total": len(eventos),
        "eventos": eventos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    gratis = sum(1 for e in eventos if e["gratis"])
    exactos = sum(1 for e in eventos if e["precision"] == "recinto")
    fichas = escribir_fichas(eventos)
    log.info("Fichas individuales para compartir: %d en web/e/", fichas)

    con_imagen = sum(1 for e in eventos if e["imagen"])
    exactos += sum(1 for e in eventos if e["precision"] in ("fuente", "correccion", "calle"))
    log.info("Exportados %d eventos (%d gratis, %d con ubicación exacta, %d con imagen)",
             len(eventos), gratis, exactos, con_imagen)
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
    log.info("Archivo: %s", SALIDA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
