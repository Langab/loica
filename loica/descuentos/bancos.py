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

import logging
from datetime import date, datetime

from ..normalizar import limpiar_html
from ..red import ClienteEducado
from .modelo import Descuento
from .texto import (dias_en, lugar_en, modalidad_en, oferta_en,
                    porcentaje_en, tope_en, vigencia_en)

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
            comuna, region = lugar_en(etiquetas)
            condiciones = limpiar_html(campos.get("Condiciones Comerciales") or "")
            descripcion = limpiar_html(campos.get("Descripcion") or "")
            extracto = campos.get("Extracto") or ""
            vigencia_txt = campos.get("Vigencia") or ""

            recogidos.append(Descuento(
                banco_id=banco["id"],
                banco=banco["nombre"],
                comercio=(campos.get("Titulo") or meta.get("name") or "").strip(),
                categoria=meta.get("category_slug") or "restaurantes",
                comuna=comuna,
                region=region,
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
                logo=((campos.get("Logo") or {}).get("url") or ""),
            ))
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
                descripcion = limpiar_html(promo.get("description") or "")
                condiciones = limpiar_html((promo.get("options") or {}).get("conditions") or "")
                etiquetas = promo.get("tags") or []
                comuna, region = lugar_en(etiquetas)

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


ADAPTADORES = {
    "bancochile": _bancochile,
    "bci": _bci,
    "falabella": _falabella,
}
