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

from loica.almacen import Almacen
from loica.geo import Geocodificador
from loica.modelo import es_enlace_de_maquina

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

# Lo que NO es un panorama aunque aparezca en una agenda cultural.
NO_ES_PANORAMA = [
    "buscamos practicante", "buscamos pasante", "práctica profesional",
    "practica profesional", "oferta laboral", "postula a ", "postulaciones",
    "convocatoria laboral", "llamado a concurso", "concurso público",
    "concurso publico", "se busca ", "vacante", "bases del concurso",
    "requisitos de postulación", "cartas de apoyo", "fondos de cultura",
    "matrícula", "matricula ", "proceso de admisión", "calendario académico",
    "feria laboral", "feria vocacional", "feria de proyectos",
    "feria de empleo", "feria de postgrados", "feria de universidades",
    "feria científica", "feria cientifica",
]


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
<link rel="stylesheet" href="../loica.css?v=11">
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

  <a class="boton bloque" href="{url_fuente}" target="_blank" rel="noopener">
    Ver en la fuente original ↗</a>

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
<script src="../loica.js?v=11"></script>
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
    return (str(texto or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


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
        if ev["imagen"]:
            jsonld["image"] = ev["imagen"]
        if ev["gratis"] or ev["precio"]:
            jsonld["offers"] = {"@type": "Offer", "price": ev["precio"] or 0,
                                "priceCurrency": "CLP", "url": ev["url"]}

        html = PLANTILLA_FICHA.format(
            titulo_html=_escapar(ev["titulo"]),
            descripcion_meta=_escapar(resumen[:180]),
            url_ficha=f"{SITIO}/e/{ev['id']}.html",
            og_imagen=(f'<meta property="og:image" content="{_escapar(ev["imagen"])}">'
                       if ev["imagen"] else
                       f'<meta property="og:image" content="{SITIO}/og-default.png">'),
            tipo_tarjeta="summary_large_image",
            jsonld=json.dumps(jsonld, ensure_ascii=False),
            # Las fotos son del organizador y se enlazan, no se copian. Algunos
            # servidores las bloquean desde otro dominio: si eso pasa, entra la
            # mascota de la categoría en vez de quedar un hueco roto.
            foto=(f'<img src="{_escapar(ev["imagen"])}" alt="" '
                  f'onerror="this.remove();document.getElementById(\'foto\')'
                  f'.classList.add(\'sin-foto\')">' if ev["imagen"] else ""),
            url_fuente=_escapar(ev["url"]),
            cuando=_escapar(cuando), donde=_escapar(donde),
            precio=_escapar(precio),
            clase_precio=" libre" if ev["gratis"] else "",
            bloque_descripcion=(f'<div class="dato"><span class="et"></span>'
                                f'<span>{_escapar(ev["descripcion"])}</span></div>'
                                if ev["descripcion"] else ""),
            id_evento=ev["id"], fuente_html=_escapar(ev["fuente"]),
            evento_json=json.dumps(ev, ensure_ascii=False),
        )
        (DIR_FICHAS / f"{ev['id']}.html").write_text(html, encoding="utf-8")

    return len(eventos)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("exportar")

    almacen = Almacen()
    filas = almacen.con.execute(
        """SELECT * FROM eventos
           WHERE inicio >= date('now') AND estado != 'descartado'
           ORDER BY inicio""",
    ).fetchall()

    geo = Geocodificador()
    eventos = []
    sin_ubicar = 0
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

        # Si la fuente ya entregó coordenadas, mandan ellas
        categoria, _ = _clasificar(fila["titulo"], fila["categoria"] or "",
                                   fila["descripcion_corta"] or "",
                                   fila["lugar_nombre"] or "", fila["fuente_nombre"] or "")
        publico, _ = clasificar_publico(fila["titulo"], fila["descripcion_corta"] or "",
                                        categoria, fila["lugar_nombre"] or "",
                                        fila["fuente_nombre"] or "")

        lat, lon, precision = fila["lat"], fila["lon"], "fuente"
        if lat is None:
            lat, lon, precision = geo.ubicar(
                fila["lugar_nombre"] or "", fila["lugar_direccion"] or "", fila["comuna"] or "")
        if lat is None:
            # No se descarta: sale en la lista sin pin. Botar 42 eventos reales
            # (entre ellos 20 obras de teatro) es peor que mostrarlos sin mapa.
            sin_ubicar += 1
            precision = "sin_ubicar"

        eventos.append({
            "id": fila["hash_dedup"],
            "titulo": fila["titulo"],
            "inicio": fila["inicio"],
            "fin": fila["fin"],
            "lugar": fila["lugar_nombre"] or fila["fuente_nombre"],
            "direccion": fila["lugar_direccion"] or "",
            "comuna": fila["comuna"] or "",
            "lat": lat,
            "lon": lon,
            "precision": precision,
            "gratis": bool(fila["es_gratis"]),
            "precio": fila["precio_clp"],
            "precio_texto": fila["precio_texto"] or "",
            "categoria": categoria,
            "publico": publico,
            "descripcion": fila["descripcion_corta"] or "",
            "imagen": fila["imagen_url"] or "",
            "fuente": fila["fuente_nombre"],
            "url": fila["fuente_url"],
        })

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
    exactos += sum(1 for e in eventos if e["precision"] == "fuente")
    log.info("Exportados %d eventos (%d gratis, %d con ubicación exacta, %d con imagen)",
             len(eventos), gratis, exactos, con_imagen)
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
