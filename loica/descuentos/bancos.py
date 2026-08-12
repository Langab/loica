"""Un adaptador por banco. La mecánica compartida vive en `texto.py`.

Son tres y no uno solo porque los tres publican formas distintas del mismo
hecho, y esa diferencia no se puede esconder en configuración:

    Banco de Chile  CMS propio. El día viene en una lista plana de etiquetas
                    revuelto con la región y la comuna.
    Bci             Rails con JSON. El día no existe como dato: hay que leerlo
                    del HTML de la promoción.
    Falabella       Contentful. El día es un campo y la vigencia es fecha ISO.

Lo que sí está en `config/bancos.yaml` es qué categorías mirar, cuánto esperar
entre peticiones y con qué URL se arma el link de vuelta a la fuente.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path

import yaml

from ..normalizar import limpiar_html
from ..red import ClienteEducado
from .modelo import Descuento
from .texto import (datos_bci, dias_en, lugar_en, modalidad_en, oferta_en,
                    porcentaje_en, sucursales_bch, tope_en, url_normal, vigencia_en)

log = logging.getLogger("loica.descuentos")


# --------------------------------------------------------------------------
# Banco de Chile
# --------------------------------------------------------------------------
def _bancochile(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    url = banco["url_base"] + banco["endpoint"]
    categorias = set(banco.get("categorias") or [])
    plantilla = banco["url_detalle"]
    recogidos: list[Descuento] = []

    pagina, total_paginas = 1, 1
    while pagina <= total_paginas:
        datos = cliente.json(url, params={"per_page": banco.get("por_pagina", 100),
                                          "page": pagina})
        if not isinstance(datos, dict):
            log.warning("Banco de Chile: la página %s no devolvió JSON", pagina)
            break

        total_paginas = (datos.get("meta") or {}).get("total_pages", 1)
        for entrada in datos.get("entries") or []:
            meta, campos = entrada.get("meta") or {}, entrada.get("fields") or {}
            if categorias and meta.get("category") not in categorias:
                continue

            etiquetas = meta.get("tags") or []
            condiciones = limpiar_html(campos.get("Condiciones Comerciales") or "")
            descripcion = limpiar_html(campos.get("Descripcion") or "")
            extracto = campos.get("Extracto") or ""
            vigencia_txt = campos.get("Vigencia") or ""

            # Una fila por sucursal. Un restaurante con local en Ñuñoa y otro en
            # Concepción son dos datos distintos, y aplastarlos en uno obliga a
            # elegir una dirección y mentir en la otra. Además así el filtro de
            # Región Metropolitana trabaja sobre la dirección declarada por el
            # banco y no sobre una etiqueta deducida.
            locales = sucursales_bch(campos.get("Sucursales") or "")
            if not locales:
                comuna, region = lugar_en(etiquetas)
                locales = [{"direccion": "", "comuna": comuna, "region": region}]

            base = dict(
                banco_id=banco["id"],
                banco=banco["nombre"],
                comercio=(campos.get("Titulo") or meta.get("name") or "").strip(),
                categoria=meta.get("category_slug") or "restaurantes",
                # El % no tiene campo propio: sale del titular y de la letra chica
                porcentaje=porcentaje_en(campos.get("Titulo"), descripcion, condiciones),
                oferta=oferta_en(extracto, condiciones),
                tope=tope_en(condiciones),
                # El día está en las etiquetas y, cuando no, en el extracto
                # ("todos los martes", "domingo a jueves")
                dias=dias_en(" ".join(etiquetas), extracto),
                vigencia_hasta=vigencia_en(vigencia_txt, condiciones),
                tarjetas=campos.get("Tarjetas Permitidas") or [],
                modalidad=modalidad_en(extracto, condiciones),
                segmentado="segmentado" in [str(e).lower() for e in etiquetas],
                condiciones=condiciones,
                url=plantilla.format(slug=meta.get("slug", "")),
                sitio_web=url_normal(campos.get("Sitio web")),
                telefono=(campos.get("Telefono") or "").strip(),
                logo=((campos.get("Logo") or {}).get("url") or ""),
            )
            for local in locales:
                recogidos.append(Descuento(**base, **local))
        pagina += 1

    return recogidos


# --------------------------------------------------------------------------
# Bci
# --------------------------------------------------------------------------
def _bci(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    recogidos: list[Descuento] = []

    for categoria in banco.get("categorias") or []:
        url = banco["url_base"] + banco["endpoint"].format(categoria=categoria)
        pagina, total_paginas = 1, 1

        while pagina <= total_paginas:
            datos = cliente.json(url, params={"per_page": banco.get("por_pagina", 100),
                                              "page": pagina})
            if not isinstance(datos, dict):
                log.warning("Bci: %s no devolvió JSON", categoria)
                break

            total_paginas = (datos.get("meta") or {}).get("total_pages", 1)
            for promo in datos.get("promotions") or []:
                # El HTML de la promoción trae el titular ("Hasta un 40% dcto"),
                # la dirección y el teléfono. Se limpia y se lee como texto.
                bruto = promo.get("description") or ""
                descripcion = limpiar_html(bruto)
                condiciones = limpiar_html((promo.get("options") or {}).get("conditions") or "")
                etiquetas = promo.get("tags") or []
                comuna, region = lugar_en(etiquetas)
                # La comuna del HTML manda sobre la de las etiquetas: viene de
                # la dirección del local, no de una lista de palabras sueltas.
                local = datos_bci(bruto)
                comuna = local["comuna"] or comuna

                recogidos.append(Descuento(
                    banco_id=banco["id"],
                    banco=banco["nombre"],
                    comercio=_titulo_bci(promo.get("title") or ""),
                    categoria=(promo.get("category") or categoria).split("/")[-1],
                    comuna=comuna,
                    region=region,
                    porcentaje=porcentaje_en(promo.get("title"), descripcion, condiciones),
                    oferta=oferta_en(descripcion, condiciones),
                    tope=tope_en(condiciones),
                    # Acá está la diferencia con los otros dos: no hay campo de
                    # día, solo prosa. Buena parte no dice ninguno y queda sin
                    # día, que es lo honesto: mejor vacío que un martes inventado.
                    dias=dias_en(descripcion, condiciones),
                    vigencia_hasta=vigencia_en(condiciones, descripcion),
                    tarjetas=[],       # Bci no las publica por promoción
                    modalidad=modalidad_en(descripcion, condiciones),
                    condiciones=condiciones,
                    url=promo.get("url") or "",
                    direccion=local["direccion"],
                    telefono=local["telefono"],
                    sitio_web=url_normal(local["sitio_web"]),
                    logo=(promo.get("covers") or [""])[0],
                ))
            pagina += 1

    return recogidos


def _titulo_bci(titulo: str) -> str:
    """Bci corta el nombre a media frase: "Gimnasios Pacific - Hasta un".

    El pedazo colgando después del guion es el titular del descuento truncado
    por el largo del campo, no parte del nombre del local.
    """
    limpio = titulo.strip()
    for corte in (" - Hasta un", " - Hasta", " – Hasta un", " - hasta un"):
        if limpio.endswith(corte):
            limpio = limpio[: -len(corte)]
    return limpio.strip(" -–")


# --------------------------------------------------------------------------
# Banco Falabella
# --------------------------------------------------------------------------
def _falabella(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    url = (f"{banco['url_base']}/spaces/{banco['espacio']}"
           f"/environments/{banco['entorno']}/entries")
    categorias = set(banco.get("categorias") or [])
    plantilla = banco["url_detalle"]
    por_pagina = banco.get("por_pagina", 100)
    recogidos: list[Descuento] = []

    # El monto del descuento NO está en `descuentos`: vive en `newBenefits`,
    # que es lo que pinta la tarjeta del sitio. Se cruzan por `permalink`.
    # Sin esto, las 137 promociones de Falabella salían con día y región pero
    # sin decir de cuánto es el descuento, que es lo único que importa.
    montos = _montos_falabella(banco, cliente, url)

    saltar, total = 0, None
    while total is None or saltar < total:
        datos = cliente.json(url, params={
            "content_type": banco["tipo_contenido"],
            "limit": por_pagina,
            "skip": saltar,
            "access_token": banco["token_lectura"],
        })
        if not isinstance(datos, dict) or "items" not in datos:
            log.warning("Falabella: Contentful no devolvió items (skip=%s)", saltar)
            break

        total = datos.get("total", 0)
        for item in datos["items"]:
            campos = item.get("fields") or {}
            suyas = set(campos.get("categoriaV2") or [])
            if categorias and not (categorias & suyas):
                continue

            regiones = campos.get("region") or []
            # Contentful entrega la vigencia como fecha real, así que acá no
            # hay que adivinar nada
            vigencia = _fecha_iso(campos.get("fechaTerminoV2"))
            monto = montos.get(campos.get("permalink", ""), "")
            texto = " · ".join(str(campos.get(c) or "") for c in
                               ("subtituloCajaV2", "descripcionCortaApp", "nombreBeneficio"))

            recogidos.append(Descuento(
                banco_id=banco["id"],
                banco=banco["nombre"],
                comercio=(campos.get("empresaBeneficioV2")
                          or campos.get("nombreBeneficio") or "").strip(),
                categoria="restaurantes" if "Restaurantes" in suyas else "antojos",
                comuna="",     # el tipo `descuentos` solo llega hasta la región
                region=_region_falabella(regiones),
                porcentaje=porcentaje_en(monto, campos.get("nombreBeneficio"), texto),
                # Cuando el monto no es un por ciento es un precio cerrado o un
                # número de cuotas ("$29.900", "12 cuotas"): eso se muestra tal cual.
                oferta=(monto if monto and "%" not in monto else oferta_en(texto)),
                tope=tope_en(texto),
                # Contentful entrega los días en el orden en que los tipeó
                # quien cargó la promo ("jueves, sábado, miércoles"). Pasan por
                # el mismo parser que los otros dos para salir de lunes a domingo.
                dias=dias_en(" ".join(campos.get("diasDescuento") or [])),
                vigencia_hasta=vigencia,
                # `paymentMethodBenefit` dice si corre con CMR, con débito o
                # con ambas. Es el único de los tres bancos que lo separa así.
                tarjetas=[str(m).lower() for m in (campos.get("paymentMethodBenefit") or [])],
                modalidad=modalidad_en(texto),
                condiciones=texto.strip(" ·"),
                sitio_web=url_normal(campos.get("urlV2")),
                url=plantilla.format(slug=campos.get("permalink", "")),
                logo="",
            ))
        saltar += por_pagina

    return recogidos


def _montos_falabella(banco: dict, cliente: ClienteEducado, url: str) -> dict[str, str]:
    """{permalink: "40%"} sacado de `newBenefits`, el tipo que pinta las tarjetas.

    `centerDiscountText` es el número grande de la tarjeta y es el dato que el
    banco muestra al cliente: "40%", "$29.900", "12 cuotas". El campo `discount`
    del mismo tipo NO sirve — es un entero de ordenamiento que marca 40 tanto
    para un 40% como para un 50%.
    """
    montos: dict[str, str] = {}
    saltar, total = 0, None
    while total is None or saltar < total:
        datos = cliente.json(url, params={
            "content_type": "newBenefits",
            "limit": 100,
            "skip": saltar,
            "access_token": banco["token_lectura"],
        })
        if not isinstance(datos, dict) or "items" not in datos:
            break
        total = datos.get("total", 0)
        for item in datos["items"]:
            campos = item.get("fields") or {}
            centro = str(campos.get("centerDiscountText") or "").strip()
            if campos.get("permalink") and centro:
                montos[campos["permalink"]] = centro
        saltar += 100
    return montos


def _fecha_iso(valor) -> date | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _region_falabella(regiones: list) -> str:
    """Falabella lista todas las regiones donde corre la promo. Si son muchas,
    decir una sola sería mentir; se dice que es nacional."""
    if not regiones:
        return ""
    if len(regiones) > 3:
        return "Todo Chile"
    limpias = [str(r).replace("Región de ", "").replace("Región del ", "")
                     .replace("Región ", "").replace(" de Santiago", "").strip()
               for r in regiones]
    return " · ".join(limpias)


# --------------------------------------------------------------------------
# Santander — captura manual
# --------------------------------------------------------------------------
def _santander(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    """Lee la foto que hay en datos/manual/, no la web del banco.

    Santander tiene el mejor catálogo del mercado —83 restaurantes, casi todos
    con día declarado— y es el único que no se puede automatizar: su WAF
    bloquea todo lo que no sea un navegador, incluido /robots.txt. Rodearlo
    sería evadir un control puesto a propósito, así que el archivo se llena a
    mano y acá solo se lee.

    El precio de eso es que envejece, y por eso cada fila viaja con la fecha
    de captura hasta la ficha en la página. Un descuento que dice "capturado
    hace tres meses" es honesto; uno que se hace pasar por fresco, no.
    """
    ruta = Path(__file__).resolve().parents[2] / banco["archivo"]
    if not ruta.exists():
        log.warning("Santander: falta %s — se omite", ruta)
        return []

    doc = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    capturado = str(doc.get("capturado") or "")
    fuente = doc.get("fuente") or ""
    recogidos = []

    for fila in doc.get("descuentos") or []:
        comercio = str(fila.get("comercio") or "").strip()
        if not comercio:
            continue
        regiones = [r.strip() for r in str(fila.get("region") or "").split(",") if r.strip()]
        tarjeta = str(fila.get("tarjeta") or "").strip()
        recogidos.append(Descuento(
            banco_id=banco["id"],
            banco=banco["nombre"],
            comercio=comercio,
            categoria=str(fila.get("categoria") or "restaurantes"),
            # La captura mínima trae solo región, y así el descuento no se
            # puede filtrar por comuna ni ubicar en el mapa: en la página queda
            # como "Metropolitana" a secas. Si la captura incluye dirección,
            # comuna o sitio del local, se usan. Están opcionales a propósito
            # para que una captura vieja siga funcionando sin tocar nada.
            direccion=str(fila.get("direccion") or "").strip(),
            comuna=str(fila.get("comuna") or "").strip(),
            sitio_web=str(fila.get("sitio_web") or "").strip(),
            region=" · ".join(regiones) if len(regiones) <= 3 else "Todo Chile",
            porcentaje=porcentaje_en(fila.get("monto")),
            dias=dias_en(fila.get("cuando")),
            modalidad=modalidad_en(fila.get("cuando")),
            # "Limited" y "Amex" son tarjetas de gama alta: el descuento no es
            # para cualquier cliente y decirlo importa.
            tarjetas=[tarjeta.lower()] if tarjeta else [],
            segmentado=bool(tarjeta),
            condiciones=str(fila.get("cuando") or "").strip(),
            url=fuente,
            capturado=capturado,
        ))
    log.info("Santander: %d descuentos de la captura del %s", len(recogidos), capturado or "?")
    return recogidos


# --------------------------------------------------------------------------
# Tarjeta Cencosud Scotiabank
# --------------------------------------------------------------------------
def _cencosud(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    """El catálogo va incrustado en la página como `window.CardsAPI`.

    No hay endpoint aparte: es un GET normal a la landing y un JSON adentro de
    una etiqueta <script>. Aporta poco —de 83 beneficios solo la categoría
    "comida" sirve, y ahí adentro hay cine y viajes— pero es otro emisor, es
    abierto y sale barato.

    El nombre del local está dentro del título ("40% dcto. en Burger King"),
    así que se corta por el " en ".
    """
    respuesta = cliente.obtener(banco["url_agenda"])
    if respuesta is None or not respuesta.ok:
        log.warning("Cencosud: no respondió")
        return []

    bloque = re.search(r"window\.CardsAPI\s*=\s*\{.*?return\s*(\[.*?\]);",
                       respuesta.text, re.S)
    if not bloque:
        log.warning("Cencosud: no encontré window.CardsAPI (¿cambiaron la página?)")
        return []
    try:
        tarjetas = json.loads(bloque.group(1))
    except ValueError as e:
        log.warning("Cencosud: el JSON incrustado no parsea (%s)", e)
        return []

    categorias = {c.lower() for c in (banco.get("categorias") or [])}
    recogidos = []
    for item in tarjetas:
        if not item.get("is_active", True):
            continue
        suyas = {str(c).lower() for c in (item.get("categories") or [])}
        if categorias and not (categorias & suyas):
            continue

        titulo = str(item.get("title") or "").strip()
        corta = str(item.get("short_description") or "")
        legal = limpiar_html(item.get("legal_text") or "")
        dias = dias_en(titulo, corta)
        if not dias and not porcentaje_en(titulo):
            continue        # sin día ni monto no queda nada que mostrar

        recogidos.append(Descuento(
            banco_id=banco["id"],
            banco=banco["nombre"],
            comercio=_comercio_cencosud(titulo),
            categoria="restaurantes",
            region="Todo Chile",
            porcentaje=porcentaje_en(titulo, corta),
            oferta=oferta_en(titulo, corta),
            dias=dias,
            vigencia_hasta=vigencia_en(legal),
            tarjetas=["cencosud"],
            modalidad=modalidad_en(titulo, corta),
            condiciones=corta.strip() or legal[:300],
            url=str(item.get("url") or banco["url_agenda"]),
        ))
    return recogidos


def _comercio_cencosud(titulo: str) -> str:
    """"40% dcto. en Burger King" → "Burger King"."""
    corte = re.split(r"\s+en\s+", titulo, maxsplit=1)
    nombre = corte[1] if len(corte) > 1 else titulo
    # Se les cuela el día pegado al nombre: "PedidosYa todos los viernes"
    nombre = re.split(r"\s+todos los\s+", nombre, maxsplit=1)[0]
    return nombre.strip(" .,")


ADAPTADORES = {
    "bancochile": _bancochile,
    "bci": _bci,
    "falabella": _falabella,
    "santander": _santander,
    "cencosud": _cencosud,
}
