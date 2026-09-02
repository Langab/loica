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

import csv
import json
import logging
import os
import re
from datetime import date, datetime
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

from .. import asistida
from ..normalizar import limpiar_html
from ..red import ClienteEducado
from .modelo import Descuento
from .texto import (COMUNAS, MESES, REGIONES, datos_bci, dias_en, lugar_en, modalidad_en,
                    oferta_en, plano, porcentaje_en, sucursales_bch, tope_en,
                    url_normal, vigencia_en)


def token_de(banco: dict) -> str:
    """El token de lectura del banco; manda la variable de entorno si existe.

    El que está en `config/bancos.yaml` es el Content Delivery de solo lectura
    que Falabella trae incrustado en su propio bundle de JavaScript: es público
    por diseño, no es un secreto nuestro, y por eso puede vivir versionado.

    Aun así la puerta queda abierta. Un token dentro de un archivo del
    repositorio es una costumbre que se pega sola, y el día que un banco pida
    uno que sí sea secreto conviene que el lugar donde ponerlo ya exista y no
    haya que tocar código con el apuro encima:

        export LOICA_TOKEN_FALABELLA=...
    """
    return os.environ.get(f"LOICA_TOKEN_{banco['id'].upper()}", "") or banco.get("token_lectura", "")


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
def _coord(valor) -> float | None:
    """Coordenada solo si cae dentro de Chile continental.

    Una promoción con la latitud en cero mandaría el pin al golfo de Guinea, y
    un pin en el lugar equivocado es peor que ningún pin: el usuario llega a
    una esquina donde no hay nada.
    """
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if -56.0 < numero < -17.0 or -76.0 < numero < -66.0 else None


def _bci(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    # Desde el 02-09-2026 manda la pasada asistida, si existe. El portal
    # vivirconbeneficios.cl que se leía hasta entonces es un catálogo MUERTO:
    # sus 27 promociones de restaurantes traen `end_date` entre 2018 y 2020 y
    # `updated_at` entre 2017 y 2021, y solo una de ellas sigue en el catálogo
    # vivo de bci.cl (80 restaurantes en la RM al 01-09-2026, 77 con vigencia
    # hasta el 30-09). Como el adaptador no miraba `end_date`, se publicaban
    # 143 descuentos de hace seis años como si corrieran hoy. bci.cl responde
    # 403 a clientes que no son un navegador (WAF), así que su catálogo entra
    # por la pasada con el navegador, igual que Santander, con su fecha de
    # captura a la vista. El portal viejo queda de respaldo y ahora sí filtra
    # por `end_date`, con lo que hoy no devuelve nada vigente: es lo correcto.
    csv_pasada = asistida.archivos("descuentos_bci.csv")
    if csv_pasada:
        return _csv_pasada(banco, csv_pasada[0])

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

                porcentaje, promocion = _descuento_bci(promo, descripcion, condiciones)

                recogidos.append(Descuento(
                    banco_id=banco["id"],
                    banco=banco["nombre"],
                    comercio=_titulo_bci(promo.get("title") or ""),
                    categoria=(promo.get("category") or categoria).split("/")[-1],
                    comuna=comuna,
                    region=region,
                    porcentaje=porcentaje,
                    oferta=promocion or oferta_en(descripcion, condiciones),
                    tope=tope_en(condiciones),
                    # Acá está la diferencia con los otros dos: no hay campo de
                    # día, solo prosa. Buena parte no dice ninguno y queda sin
                    # día, que es lo honesto: mejor vacío que un martes inventado.
                    dias=dias_en(descripcion, condiciones),
                    # `end_date` es un campo del JSON y manda sobre la prosa.
                    # Hasta el 02-09-2026 no se leía, y por eso ninguna de las
                    # promociones de 2018-2020 caía como vencida.
                    vigencia_hasta=(_fecha_iso(promo.get("end_date"))
                                    or vigencia_en(condiciones, descripcion)),
                    tarjetas=[],       # Bci no las publica por promoción
                    modalidad=modalidad_en(descripcion, condiciones),
                    condiciones=condiciones,
                    url=promo.get("url") or "",
                    # `location_street` es la dirección tal como la cargó el
                    # local; la del HTML sale de parsear prosa. Se prefiere el
                    # campo y el HTML queda de respaldo.
                    direccion=(str(promo.get("location_street") or "").strip()
                               or local["direccion"]),
                    telefono=local["telefono"],
                    sitio_web=url_normal(local["sitio_web"]),
                    logo=(promo.get("covers") or [""])[0],
                    # Bci es el único banco que publica coordenadas por
                    # promoción: 97% las trae. Ese local va al mapa exacto,
                    # sin geocodificar ni aproximar por comuna.
                    lat=_coord(promo.get("latitude")),
                    lon=_coord(promo.get("longitude")),
                ))
            pagina += 1

    return recogidos


def _descuento_bci(promo: dict, descripcion: str, condiciones: str) -> tuple[int | None, str]:
    """Cuánto rebaja esta promoción de Bci, y el 1 que no es un uno por ciento.

    `discount` es el porcentaje como número, y leerlo del campo en vez del
    titular en prosa subió de 66 a 147 las promociones con cifra. Pero Bci lo
    usa además como bandera: cuando la promoción no es un porcentaje sino un
    combo a precio fijo, escribe **1**. Los catorce China Wok del catastro
    salían en la página anunciando "1% de descuento" —que es un insulto— sobre
    una promoción que en realidad es *"2 woky pack mongoliana a $6.180"*.

    Un uno por ciento no existe como oferta comercial: nadie arma una campaña
    para rebajar cien pesos en diez mil. Así que por debajo del piso de
    `porcentaje_en` (5%) el número no se lee como porcentaje, se lee como lo
    que es —hay promoción— y la fila lo dice con palabras.

    Devuelve (porcentaje, etiqueta). Solo uno de los dos trae algo.
    """
    crudo = str(promo.get("discount") or "").strip()
    numero = int(crudo) if crudo.isdigit() else None

    if numero is not None and 5 <= numero <= 100:
        return numero, ""

    # Sin cifra utilizable: puede que el titular sí la traiga.
    del_texto = porcentaje_en(promo.get("title"), descripcion, condiciones)
    if del_texto is not None:
        return del_texto, ""

    if numero is None:
        return None, ""

    # La bandera. "2x1" es una etiqueta mejor que "Promoción" y se gana el
    # puesto; para todo lo demás, decir "hay promoción" es lo único cierto.
    etiqueta = oferta_en(promo.get("title"), descripcion, condiciones)
    return None, etiqueta if etiqueta and "x" in etiqueta else "Promoción"


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
            "access_token": token_de(banco),
            # Sin `include`, Contentful manda el logo como un puntero
            # ({"sys": {"linkType": "Asset", "id": "..."}}) en vez del archivo,
            # y los 108 descuentos salían sin imagen. Con include=1 vienen los
            # assets resueltos en la misma respuesta, sin peticiones extra.
            "include": 1,
        })
        if not isinstance(datos, dict) or "items" not in datos:
            log.warning("Falabella: Contentful no devolvió items (skip=%s)", saltar)
            break

        assets = {a["sys"]["id"]: a
                  for a in ((datos.get("includes") or {}).get("Asset") or [])}

        def _logo(campos: dict) -> str:
            enlace = (campos.get("imageApp") or {}).get("sys") or {}
            archivo = ((assets.get(enlace.get("id")) or {})
                       .get("fields", {}).get("file", {}).get("url", ""))
            # Contentful devuelve la URL sin esquema: //images.ctfassets.net/...
            return ("https:" + archivo) if archivo.startswith("//") else archivo

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
                logo=_logo(campos),
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
            "access_token": token_de(banco),
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
    # Desde el 01-09-2026 la pasada del navegador entrega Santander como CSV
    # dentro de su carpeta con fecha, y ese CSV trae lo que el YAML no tenía:
    # dirección, comuna, logo, tope y vigencia por local. Si hay CSV, manda.
    csv_nuevo = asistida.archivos("descuentos_santander.csv")
    if csv_nuevo:
        return _csv_pasada(banco, csv_nuevo[0])

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
            # Vacío y no "restaurantes": Santander NO publica rubro, y poner
            # el valor por defecto acá es afirmar algo que el banco no dijo.
            # Vacío deja que el modelo lo deduzca del nombre del local, que es
            # cómo Burger King entra al filtro de comida rápida en vez de
            # quedar escondido entre los restaurantes.
            categoria=str(fila.get("categoria") or ""),
            # La captura mínima trae solo región, y así el descuento no se
            # puede filtrar por comuna ni ubicar en el mapa: en la página queda
            # como "Metropolitana" a secas. Si la captura incluye dirección,
            # comuna o sitio del local, se usan. Están opcionales a propósito
            # para que una captura vieja siga funcionando sin tocar nada.
            direccion=str(fila.get("direccion") or "").strip(),
            comuna=str(fila.get("comuna") or "").strip(),
            sitio_web=str(fila.get("sitio_web") or "").strip(),
            region=" · ".join(regiones) if len(regiones) <= 3 else "Todo Chile",
            # El logo del local. La ficha de Santander lo muestra grande y es
            # media página de la tentación: un nombre en texto plano no invita
            # a ir a ninguna parte.
            logo=str(fila.get("logo") or "").strip(),
            porcentaje=porcentaje_en(fila.get("monto")),
            # "Descuento máximo por pedido de $40.000" sale en las condiciones
            # de la ficha. Si la captura lo trae aparte se usa tal cual; si no,
            # se busca en el texto como en los otros bancos.
            tope=(int(fila["tope"]) if str(fila.get("tope") or "").isdigit()
                  else tope_en(str(fila.get("condiciones") or fila.get("cuando") or ""))),
            # "Hasta el 31 de agosto de 2026" — el mismo parser que usan los
            # otros bancos para la letra chica.
            vigencia_hasta=vigencia_en(str(fila.get("vigencia") or ""),
                                       str(fila.get("condiciones") or "")),
            dias=dias_en(fila.get("cuando")),
            modalidad=modalidad_en(fila.get("cuando")),
            # "Limited" y "Amex" son tarjetas de gama alta: el descuento no es
            # para cualquier cliente y decirlo importa.
            tarjetas=[tarjeta.lower()] if tarjeta else [],
            segmentado=bool(tarjeta),
            # La ficha del banco lista la letra chica en viñetas ("No acumulable
            # con otras promociones", "Válido en local"). Si la captura las
            # trae, valen más que repetir el "cuándo".
            condiciones=(str(fila.get("condiciones") or "").strip()
                         or str(fila.get("cuando") or "").strip()),
            url=fuente,
            capturado=capturado,
        ))
    log.info("Santander: %d descuentos de la captura del %s", len(recogidos), capturado or "?")
    return recogidos


def _csv_pasada(banco: dict, ruta: Path) -> list[Descuento]:
    """Un banco capturado con el navegador, en el formato de la pasada con fecha.

        banco,comercio,direccion,comuna,lat,lon,logo,dias,monto,tope,vigencia,
        sitio_web,categoria,url

    Lo usan los bancos que le cierran la puerta al robot y se anotan a mano:
    Santander desde el 01-09-2026 y Bci desde el 02-09-2026. Es el mismo
    archivo para los dos, cambia solo el nombre (`descuentos_<id>.csv`).

    Cada fila es UN LOCAL, no un convenio: Santander publica "Holy Moly" dos
    veces porque tiene dos direcciones, y así las dos caen en el mapa. La
    columna `url` es la ficha de esa promoción —Santander le da página propia a
    cada una—, que es mejor atribución que el link único a la parrilla que
    traía el YAML.

    Lo que el CSV NO trae es el tipo de tarjeta, que el YAML sí tenía. Sin esa
    columna no se puede saber si la promoción es solo para Amex o Limited, y
    marcar `segmentado` a ojo sería inventarlo: queda en falso, que es lo que
    el dato publicado permite afirmar.
    """
    try:
        # utf-8-sig porque Excel y varios exportadores dejan BOM al inicio.
        with ruta.open(encoding="utf-8-sig", newline="") as f:
            filas = list(csv.DictReader(f))
    except (OSError, csv.Error) as e:
        log.error("%s: no pude leer %s (%s)", banco["nombre"], ruta.name, e)
        return []

    # La fecha de la carpeta ES la fecha de captura, y sale de la carpeta DE
    # ESTE archivo, no de "la pasada más nueva": si el CSV viniera suelto de la
    # raíz mientras existe una pasada, ponerle la fecha de la pasada sería
    # firmar como fresco algo que no lo es. Viaja hasta la ficha en la página,
    # porque un descuento que dice "capturado hace tres meses" es honesto; uno
    # que se hace pasar por fresco, no.
    fecha = asistida.fecha_de_carpeta(ruta.parent)
    capturado = fecha.isoformat() if fecha else ""

    recogidos = []
    for fila in filas:
        comercio = str(fila.get("comercio") or "").strip()
        if not comercio:
            continue
        monto = str(fila.get("monto") or "").strip()
        recogidos.append(Descuento(
            banco_id=banco["id"],
            banco=banco["nombre"],
            comercio=comercio,
            # Santander no publica rubro. La columna trae lo que dedujo quien
            # capturó, y el modelo lo homologa; vacío deja que lo deduzca del
            # nombre del local.
            categoria=str(fila.get("categoria") or "").strip(),
            direccion=str(fila.get("direccion") or "").strip(),
            comuna=str(fila.get("comuna") or "").strip(),
            lat=_coordenada(fila.get("lat")),
            lon=_coordenada(fila.get("lon")),
            sitio_web=str(fila.get("sitio_web") or "").strip(),
            # Región VACÍA a propósito, igual que en el YAML: Santander no
            # publica región por local. Las 167 filas con comuna ya pasan el
            # filtro de la RM por comuna, y las 13 sin comuna son cadenas
            # (Bar TPM, Vapiano, Kento Sushi) que pasan igual, porque lo que no
            # declara región se deja pasar. Escribir "Metropolitana" acá sería
            # afirmar por el banco algo que el banco no dijo.
            region="",
            logo=str(fila.get("logo") or "").strip(),
            porcentaje=porcentaje_en(monto),
            # "2x1", "Con regalo": lo que no es porcentaje. Un descuento tiene
            # uno u otro, nunca los dos.
            oferta="" if porcentaje_en(monto) else oferta_en(monto),
            tope=int(fila["tope"]) if str(fila.get("tope") or "").strip().isdigit() else None,
            vigencia_hasta=_fecha_iso(fila.get("vigencia")),
            dias=dias_en(str(fila.get("dias") or "").replace(";", " y ")),
            modalidad=modalidad_en(monto),
            # `condiciones` es la letra chica que la ficha muestra al pie. El
            # CSV no trae letra chica, y repetir ahí el "40% dcto." que ya es
            # el titular no informa: lo llena de ruido.
            condiciones="",
            url=str(fila.get("url") or "").strip(),
            capturado=capturado,
        ))

    log.info("%s: %d descuentos de la captura del %s (%s)",
             banco["nombre"], len(recogidos), capturado or "?", ruta.parent.name)
    return recogidos


def _coordenada(valor) -> float | None:
    try:
        return float(str(valor).strip())
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Tarjeta Cencosud Scotiabank
# --------------------------------------------------------------------------
def _cencosud(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    """La landing publica DOS catálogos distintos y hay que leer los dos.

    `window.CardsAPI` es el carrusel de tarjetas del sitio entero —el mismo
    JSON en todas las landings— y ahí viven los convenios de cadena: Burger
    King, PedidosYa, Rappi, Papa Johns. Son un puñado y hasta ahora eran los
    únicos que entraban.

    Los restaurantes no están en ese JSON. Están en el HTML de la propia
    landing, en una grilla de `div.grilla_item` con nombre, mall o comuna,
    día, tope, legal y sitio web, servida ya renderizada. Son 58 fichas que
    el adaptador ignoraba enteras por mirar solo la variable de JavaScript:
    la captura asistida del 01-09-2026 trajo 51 comercios y el adaptador
    veía 8.
    """
    respuesta = cliente.obtener(banco["url_agenda"])
    if respuesta is None or not respuesta.ok:
        log.warning("Cencosud: no respondió")
        return []

    grilla = _grilla_cencosud(banco, respuesta.text)
    tarjetas = _tarjetas_cencosud(banco, respuesta.text)
    log.info("Cencosud: %d de la grilla + %d del carrusel", len(grilla), len(tarjetas))
    return grilla + tarjetas


def _grilla_cencosud(banco: dict, html: str) -> list[Descuento]:
    """Las fichas de restaurante de la landing, una por local.

    Cada `div.grilla_item` es una ficha completa y no hay que abrir nada:

        <div class="grilla_item">
          <a href="https://santabrasa.cl/"><img alt="logo Santa Brasa" src="...">
            <div class="tit">Santa Brasa</div>
            <div class="desc">40% <span>Dcto.</span></div>
            <ul><li>Cenco Costanera</li><li>Jueves</li></ul></a>
          <p class="legal">Promoción válida todos los jueves ... tope de $40.000 ...</p>
        </div>

    Se parsea con BeautifulSoup y no con expresión regular a propósito: la
    página trae otras nueve fichas iguales COMENTADAS —promociones de
    noviembre que todavía no arrancan— y un `re.findall` las levantaría como
    si estuvieran vivas. El parser las descarta solo.
    """
    sopa = BeautifulSoup(html, "html.parser")
    recogidos = []
    for ficha in sopa.select("div.grilla_item"):
        titulo = ficha.select_one(".tit")
        comercio = titulo.get_text(" ", strip=True) if titulo else ""
        if not comercio:
            continue

        etiquetas = [li.get_text(" ", strip=True) for li in ficha.select("ul li")]
        donde = etiquetas[0] if etiquetas else ""
        cuando = " · ".join(etiquetas[1:])
        rebaja = ficha.select_one(".desc")
        rebaja = rebaja.get_text(" ", strip=True) if rebaja else ""
        letra_chica = ficha.select_one("p.legal")
        legal = letra_chica.get_text(" ", strip=True) if letra_chica else ""
        enlace, imagen = ficha.find("a"), ficha.find("img")

        # Manda el <li>, no la letra chica. Se contradicen en una de las 58
        # fichas —La Cocina de Javier dice "de lunes a viernes" arriba y
        # "lunes a jueves" en el legal— y arriba es lo que la persona lee.
        # El legal solo entra cuando el <li> no trae ningún día.
        dias = dias_en(cuando) or dias_en(legal)

        for comuna, direccion, region in _locales_cencosud(donde, _seccion_cencosud(ficha)):
            recogidos.append(Descuento(
                banco_id=banco["id"],
                banco=banco["nombre"],
                comercio=comercio,
                categoria="restaurantes",
                comuna=comuna,
                region=region,
                direccion=direccion,
                sitio_web=url_normal(enlace.get("href") if enlace else ""),
                porcentaje=porcentaje_en(rebaja, legal),
                # Uno u otro, nunca los dos: el "2x1" solo tiene sentido
                # cuando no hay un por ciento que mostrar.
                oferta="" if porcentaje_en(rebaja, legal) else oferta_en(rebaja),
                tope=tope_en(legal),
                dias=dias,
                vigencia_hasta=vigencia_en(legal),
                tarjetas=["cencosud"],
                modalidad=modalidad_en(legal),
                condiciones=legal[:300],
                url=banco["url_agenda"],
                logo=url_normal(imagen.get("src") if imagen else ""),
            ))
    return recogidos


def _seccion_cencosud(ficha) -> str:
    """El título de bloque bajo el que cuelga la ficha: "Santiago", "Regiones".

    Cencosud parte la grilla en bloques con `h4.titulo_region` y ese título es
    la única señal de que un local no es de Santiago cuando la ficha nombra un
    mall en vez de una comuna.
    """
    encabezado = ficha.find_previous("h4", class_="titulo_region")
    return encabezado.get_text(" ", strip=True) if encabezado else ""


def _locales_cencosud(donde: str, seccion: str) -> list[tuple[str, str, str]]:
    """"Providencia, Las Condes y Vitacura" son tres locales, no uno.

    Devuelve (comuna, dirección, región) por cada local. En esa misma línea
    Cencosud mezcla tres cosas que no son lo mismo:

        "Vitacura"              la comuna
        "Cenco Costanera"       el mall, que no dice en qué comuna queda
        "Viña del Mar"          la ciudad, cuando el local no es de Santiago

    Lo que calza con el diccionario de comunas queda como comuna; lo que no,
    es el nombre de un mall y queda como dirección para que lo resuelva la
    geocodificación, que es donde vive ese problema. "Mirador Alto las Condes"
    cae en las dos: es un mall Y dice su comuna, así que se lee de adentro.
    """
    piezas = [p.strip(" .-") for p in re.split(r",| y |/| - |–", donde) if p.strip(" .-")]
    locales: list[tuple[str, str, str]] = []
    for pieza in piezas:
        plana = plano(pieza)
        adentro = _comuna_adentro(pieza)
        if plana in COMUNAS:
            locales.append((COMUNAS[plana], "", ""))
        elif plana in REGIONES:
            locales.append(("", "", REGIONES[plana]))
        elif adentro or not locales or locales[-1][1]:
            locales.append((adentro, pieza, ""))
        else:
            # "Lo Barnechea, Portal La Dehesa" es UN local dicho dos veces: la
            # comuna y después el mall. Sin esto Margó salía con una sucursal
            # de más, la misma contada como comuna y como dirección.
            comuna, _, region = locales[-1]
            locales[-1] = (comuna, pieza, region)

    if not locales:
        locales = [("", "", "")]

    # Un mall de regiones no dice su ciudad ("Mall Marina Arauco" no contiene
    # "Viña"), y sin esto entraría a la lista de Santiago por no declarar
    # nada. El título del bloque es de Cencosud, no nuestro: lo que cuelga de
    # "Regiones" no es de la RM aunque el nombre del local no lo delate.
    if plano(seccion).startswith("regiones"):
        locales = [(comuna, direccion, region or "Regiones")
                   for comuna, direccion, region in locales]
    return locales


# Las comunas de más de una palabra primero: "Las Condes" tiene que ganarle a
# una hipotética "Condes" y "San Pedro de la Paz" a "San Pedro".
_COMUNAS_LARGAS = sorted(COMUNAS, key=len, reverse=True)


def _comuna_adentro(texto: str) -> str:
    """La comuna que el nombre del mall lleva escrita: "Mirador Alto las Condes"."""
    plana = plano(texto)
    for clave in _COMUNAS_LARGAS:
        if re.search(rf"(?<![a-z0-9]){re.escape(clave)}(?![a-z0-9])", plana):
            return COMUNAS[clave]
    return ""


def _tarjetas_cencosud(banco: dict, html: str) -> list[Descuento]:
    """El carrusel de tarjetas del sitio, incrustado como `window.CardsAPI`.

    Es el catálogo del sitio entero —85 beneficios, los mismos en cualquier
    landing— y de ahí solo sirve la categoría "comida", que es la que filtra
    `config/bancos.yaml`. Aporta poco pero es el único lugar donde están los
    convenios de cadena, que no tienen ficha en la grilla.
    """
    bloque = re.search(r"window\.CardsAPI\s*=\s*\{.*?return\s*(\[.*?\]);", html, re.S)
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

        url = str(item.get("url") or "")
        # La tarjeta de "La Ruta del Sabor" es la landing que acabamos de
        # abrir, no un comercio: entraba como un descuento llamado
        # "restaurantes" que era la grilla entera disfrazada de una fila.
        if url.rstrip("/") == banco["url_agenda"].rstrip("/"):
            continue

        titulo = str(item.get("title") or "").strip()
        corta = str(item.get("short_description") or "")
        legal = limpiar_html(item.get("legal_text") or "")
        dias = dias_en(titulo, corta)
        # El monto se mira en el titular Y en la bajada, igual que dos líneas
        # más abajo. Mirando solo el titular se caía Cineplanet, que anuncia
        # "¡Tu nuevo beneficio está imperdible!" y deja el 50% en la bajada.
        if not dias and porcentaje_en(titulo, corta) is None:
            continue        # sin día ni monto no queda nada que mostrar

        recogidos.append(Descuento(
            banco_id=banco["id"],
            banco=banco["nombre"],
            comercio=_comercio_cencosud(titulo, url),
            categoria="restaurantes",
            region="Todo Chile",
            porcentaje=porcentaje_en(titulo, corta),
            oferta=oferta_en(titulo, corta),
            dias=dias,
            vigencia_hasta=vigencia_en(legal),
            tarjetas=["cencosud"],
            modalidad=modalidad_en(titulo, corta),
            condiciones=corta.strip() or legal[:300],
            url=url or banco["url_agenda"],
            logo=url_normal(item.get("logo_card") or ""),
        ))
    return recogidos


# Palabras que en un nombre propio van en minúscula: "Escapadas en Chile".
_MINUSCULAS = {"de", "del", "la", "las", "el", "los", "en", "y", "con", "a"}


def _comercio_cencosud(titulo: str, url: str = "") -> str:
    """El nombre del comercio, que Cencosud no publica como campo.

    Hay dos lugares donde buscarlo y ninguno solo alcanza:

        "40% dcto. en Burger King"          el titular, cortado por el " en "
        ".../landing/burger-king"           el slug de la landing del beneficio

    El titular tiene la ortografía buena ("PedidosYa" pegado) pero la mitad de
    las veces es un eslogan: "¡Platos preparados todos los días!" es Fork y
    "Un beneficio hecho a su medida" es KidZania. El slug siempre nombra al
    comercio pero pierde tildes y mayúsculas.

    Así que manda el titular cuando dice lo mismo que el slug, y el slug
    cuando el titular se fue a vender.
    """
    corte = re.split(r"\s+en\s+", titulo, maxsplit=1)
    nombre = corte[1] if len(corte) > 1 else titulo
    # Se les cuela el día pegado al nombre: "PedidosYa todos los viernes"
    nombre = re.split(r"\s+todos los\s+", nombre, maxsplit=1)[0].strip(" .,¡!")

    slug = url.rstrip("/").rsplit("/", 1)[-1] if "/landing/" in url else ""
    if not slug:
        return nombre
    if plano(nombre).replace(" ", "") == slug.replace("-", ""):
        return nombre           # el titular lo escribe mejor: "PedidosYa"
    return " ".join(p if p in _MINUSCULAS else p.capitalize()
                    for p in slug.split("-"))


def _ripley(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    """Restofans: el catálogo de restaurantes de Banco Ripley.

    Ripley enruta TODO su back por un solo endpoint (`/api/call-sp-api`) y dice
    qué recurso quiere en cabeceras: `x-path-api` lleva la ruta real y
    `x-method-api` el verbo. El cuerpo va en form-urlencoded. Es raro pero es
    público, sin credencial y sin WAF — lo llama su propia web abierta, y
    robots.txt no lo prohíbe.

    Vale la pena el rodeo porque el dato es el más completo del catastro
    después de Banco de Chile: cada local trae nombre, tipo de cocina, día,
    dirección, comuna, vigencia y hasta el horario. La estructura es de un CMS
    propio, con cada campo envuelto en {"nombre": ..., "value": ...}.
    """
    respuesta = cliente.obtener(
        banco["url_base"] + banco["endpoint"],
        form_cuerpo={"idSection": banco.get("seccion", "restofans")},
        cabeceras={"content-Type": "application/x-www-form-urlencoded",
                   "x-path-api": banco["ruta_api"], "x-method-api": "POST"})
    if respuesta is None or not respuesta.ok:
        log.warning("Ripley: no respondió el catálogo de %s",
                    banco.get("seccion", "restofans"))
        return []
    try:
        cajas = respuesta.json().get("data") or []
    except ValueError as e:
        log.warning("Ripley: la respuesta no es JSON (%s)", e)
        return []

    recogidos = []
    for caja in cajas:
        if not (caja.get("config") or {}).get("active", True):
            continue
        for item in caja.get("items") or []:
            if not (item.get("config") or {}).get("active", True):
                continue
            d = _descuento_ripley(banco, item)
            if d is not None:
                recogidos.append(d)
    log.info("Ripley: %d locales en %s", len(recogidos),
             (cajas[0].get("config") or {}).get("nombre", "?") if cajas else "?")
    return recogidos


def _valor(params: dict, clave: str) -> str:
    """Saca el texto de un campo del CMS de Ripley: {"value": "40% dcto"}."""
    campo = params.get(clave)
    if isinstance(campo, dict):
        return str(campo.get("value") or "").strip()
    return str(campo or "").strip()


def _lista(detalles: dict, clave: str) -> list[str]:
    """Los campos de lista de Ripley: {"array": [{"txtItem": {"value": ...}}]}."""
    bloque = detalles.get(clave) or {}
    if not (bloque.get("config") or {}).get("active", True):
        return []
    salidas = []
    for fila in bloque.get("array") or []:
        texto = _valor(fila, "txtItem")
        if texto and texto != ".":
            salidas.append(texto)
    return salidas


def _descuento_ripley(banco: dict, item: dict) -> Descuento | None:
    params = item.get("params") or {}
    comercio = _valor(params, "txtNameComercio")
    if not comercio:
        return None

    detalles = params.get("details") or {}
    direcciones = _lista(detalles, "arrDireccion")
    vigencias = _lista(detalles, "arrVigencia")
    legal = _valor(detalles, "txtLegal")

    # "R.M. (Vitacura)" o "R.M. (La Florida / Ñuñoa / Providencia)". Cuando son
    # varias comunas no se elige una: decir "Ñuñoa" de un local que también
    # está en La Florida manda a la persona al lado equivocado de la ciudad.
    # Se deja la comuna sólo si es una sola, y la dirección cuenta el resto.
    detalle_card = _valor(params, "txtDetalleCard")
    comunas = re.findall(r"\(([^)]*)\)", detalle_card)
    partes = [c.strip() for c in comunas[0].split("/")] if comunas else []
    comuna = partes[0] if len(partes) == 1 else ""

    # El día sale ÚNICAMENTE de `txtValidezBeneficio`, que es el campo que el
    # banco llama "Validez del Beneficio": Jueves, Martes, Miércoles, o "Todos
    # los días".
    #
    # `arrVigencia` NO sirve para esto aunque hable de días, y confundirlos
    # cuesta caro: dice "Todos los sábados de agosto" en 63 de los 73 locales
    # porque es la vigencia de LA CAMPAÑA, no el día de cada restaurante.
    # Leyéndolo, Pastamore —que es de lunes— salía además con sábado, y mandar
    # a alguien un sábado a un local donde va a pagar la cuenta completa es
    # justo lo que un catastro de descuentos no puede permitirse.
    #
    # "Todos los días" no produce ningún día y eso es correcto: en este
    # proyecto la lista vacía significa "sin restricción de día".
    dias = dias_en(_valor(params, "txtValidezBeneficio"))

    # La letra chica que ve la persona. `txtVigenciaDetalle` es lo que el
    # banco declara como vigencia del beneficio ("Hasta el 30 de septiembre")
    # y va primero. De `arrVigencia` —la campaña— entra solo lo que no nombra
    # un mes: Ripley no la rota, y el 02-09-2026 seguía diciendo "Todos los
    # sábados de agosto" en 25 locales con vigencia declarada al 30-09.
    # Publicar ese texto en septiembre es decirle a alguien que llegó tarde.
    vigencia_txt = _valor(params, "txtVigenciaDetalle")
    sin_mes = [v for v in vigencias
               if not re.search(r"\b(" + "|".join(MESES) + r")\b", plano(v))]
    letra_chica = ([vigencia_txt] if vigencia_txt else []) + sin_mes + _lista(detalles, "arrHorarios")

    return Descuento(
        banco_id=banco["id"],
        banco=banco["nombre"],
        comercio=comercio,
        # `txtSubtitulo` es el tipo de cocina puesto por el banco ("Italiana",
        # "Peruana"). Es mejor que deducirlo del nombre, así que manda él y
        # `cocina_de()` sólo actúa cuando viene vacío.
        cocina=_valor(params, "txtSubtitulo"),
        comuna=comuna,
        region="Metropolitana de Santiago" if "R.M." in detalle_card else "",
        direccion=direcciones[0] if direcciones else "",
        sitio_web=url_normal(_valor(params, "linkComercio")),
        porcentaje=porcentaje_en(_valor(params, "txtDescuento")),
        oferta=oferta_en(_valor(params, "txtDescuento")),
        tope=tope_en(legal),
        dias=dias,
        vigencia_hasta=vigencia_en(vigencia_txt, *vigencias, legal),
        tarjetas=["ripley"],
        modalidad=modalidad_en(legal, _valor(params, "txtDetalleCard")),
        condiciones=" · ".join(letra_chica)[:300],
        url=banco.get("url_agenda", ""),
        logo=_valor(params, "imgLogo"),
    )


def _entel(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    """Club Entel: las tarjetas del catálogo van como JSON dentro del HTML.

    Mismo patrón que Cencosud —un GET normal y un JSON incrustado— pero acá el
    CMS es Modyo y no hay una variable global que agarrar: los bloques vienen
    sueltos en el HTML. Se leen por su forma (href + title + text + section),
    que es estable porque la arma el CMS y no una persona.

    Aporta poco en volumen (la sección de comida son unos pocos locales) pero
    el texto trae el día casi siempre: "25% dcto los días miércoles".
    """
    respuesta = cliente.obtener(banco["url_agenda"])
    if respuesta is None or not respuesta.ok:
        log.warning("Entel: no respondió")
        return []

    patron = re.compile(
        r'"href":"(https://www\.entel\.cl/beneficios/descuentos/[a-z0-9-]+)"'
        r'.*?"title":"([^"]*)","text":"([^"]*)".*?"section": "([^"]*)"', re.S)
    secciones = {s.lower() for s in (banco.get("categorias") or [])}

    vistos: dict[str, Descuento] = {}
    for url, titulo, texto, seccion in patron.findall(respuesta.text):
        if url in vistos or (secciones and seccion.lower() not in secciones):
            continue
        # El CMS marca el énfasis con **markdown**: fuera, que no es dato.
        limpio = texto.replace("**", "").replace("&#39;", "'")
        nombre = titulo.replace("&#39;", "'").strip()
        if not nombre:
            continue
        # La vigencia vive en la ficha, no en el catálogo. Entel arrastra
        # beneficios vencidos hace más de un año como si estuvieran activos
        # (la pasada del 01-09-2026 contó 22 de 63), y sin esta petición extra
        # todos entraban a la página con "sin fecha declarada", que se lee
        # como "sirve".
        terminos = _terminos_entel(cliente, url)
        vistos[url] = Descuento(
            banco_id=banco["id"],
            banco=banco["nombre"],
            comercio=nombre,
            region="Todo Chile",
            porcentaje=porcentaje_en(limpio, terminos),
            oferta=oferta_en(limpio),
            dias=dias_en(limpio) or dias_en(terminos),
            tope=tope_en(terminos),
            vigencia_hasta=vigencia_en(terminos),
            tarjetas=["entel"],
            modalidad=modalidad_en(limpio, terminos),
            condiciones=limpio[:300],
            url=url,
        )
    log.info("Entel: %d beneficios en %s (%d con vigencia)", len(vistos),
             ", ".join(banco.get("categorias") or ["todas las secciones"]),
             sum(1 for d in vistos.values() if d.vigencia_hasta))
    return list(vistos.values())


def _terminos_entel(cliente: ClienteEducado, url: str) -> str:
    """Los términos legales de una ficha de Entel, como texto plano.

    La ficha viene renderizada en el servidor (no hace falta navegador) y los
    términos van en uno o más `.modal-text`: ahí está la única fecha de
    término que Entel publica. Se lee SOLO ese bloque y no la página entera:
    el resto trae un carrusel con otros beneficios y sus propias fechas, y la
    primera que apareciera se le colgaría al beneficio equivocado.

    Con caché de un día: son ~30 fichas y los términos no cambian a diario.
    Si la ficha no responde, se devuelve vacío y el beneficio queda sin
    vigencia, que es lo que se sabía hasta ahora.
    """
    respuesta = cliente.obtener(url, max_edad_cache_seg=24 * 3600)
    if respuesta is None or not respuesta.ok:
        return ""
    sopa = BeautifulSoup(respuesta.text, "html.parser")
    bloques = [b.get_text(" ", strip=True) for b in sopa.select(".modal-text")]
    return " · ".join(b for b in bloques if b)


# --------------------------------------------------------------------------
# Banco Security — el catálogo del grupo BICE-Security
# --------------------------------------------------------------------------
# La cabecera que el estándar JSON:API define para negociar el formato. Es lo
# único que hay que mandar: el endpoint no pide token, ni cookie, ni nada más.
_JSONAPI = {"Accept": "application/vnd.api+json"}


def _security(banco: dict, cliente: ClienteEducado) -> list[Descuento]:
    """Banco Security: Drupal 10 con el JSON:API abierto, sin token y sin WAF.

    En calidad de campos es el mejor dato del catastro después de Banco de
    Chile, y en el día de la semana es incluso mejor: los 80 beneficios
    gastronómicos traen el día en una taxonomía propia —80 de 80— y la
    vigencia como fecha ISO de verdad, no como prosa.

    Las dos trampas grandes están en el nombre de un campo y en la forma de
    otro, y cada una se resuelve donde corresponde:

        field_descripcion_vigencia_benef   se llama vigencia y trae EL DÍA
        field_direccion_establecimiento_   puede traer varios locales en uno

    La tercera trampa es de sistema y está en `_paginas_security`: el API
    omite lo no publicado uno por uno y deja páginas vacías en medio.
    """
    url = banco["url_base"] + banco["endpoint"]
    # `include` resuelve las relaciones en la misma respuesta. Sin él habría
    # que pedir aparte cada logo, cada día y cada categoría: más de trescientas
    # peticiones para 175 fichas, contra las once páginas que son con esto.
    params = {"page[limit]": banco.get("por_pagina", 50),
              "include": "field_logo,field_dias_de_aplicacion,field_categorias_beneficio"}
    categorias = [str(c) for c in (banco.get("categorias") or [])]
    hoy = date.today()
    recogidos: list[Descuento] = []
    fichas_vistas = 0

    for fichas, incluidos in _paginas_security(cliente, url, params):
        for ficha in fichas:
            atributos = ficha.get("attributes") or {}
            categoria = _categoria_security(ficha, incluidos, categorias)
            if not categoria:
                continue          # viajes, shopping, farmacias: otro producto

            rango = atributos.get("field_vigencia_beneficio") or {}
            desde = _fecha_iso(rango.get("value"))
            if desde and desde > hoy:
                # Ventana que todavía no empieza. `Al Pesto` (nid 616) declara
                # 2026-11-01 a 2026-11-30 estando hoy en agosto, y el modelo no
                # tiene dónde guardar "desde cuándo": o se deja fuera o se
                # publica un 40% que no existe todavía.
                continue

            detalle = limpiar_html((atributos.get("field_detalle_beneficio") or {}).get("value"))
            porcentaje, oferta = _descuento_security(atributos)
            # "Black One y Black" o "Black One": son los dos únicos valores del
            # campo en los 80 gastronómicos, las dos tarjetas de gama alta del
            # banco. No hay un solo beneficio de comida para la tarjeta de
            # entrada, así que el catálogo entero va marcado como segmentado,
            # igual que Amex y Limited en Santander.
            tarjetas = [t.strip().lower() for t in
                        re.split(r"\s+y\s+", str(atributos.get("field_tipo_de_tarjeta") or ""))
                        if t.strip()]

            base = dict(
                banco_id=banco["id"],
                banco=banco["nombre"],
                comercio=_comercio_security(atributos),
                categoria=categoria,
                porcentaje=porcentaje,
                oferta=oferta,
                # El tope no tiene campo: está en la prosa del detalle ("Tope de
                # dcto. de $10.000"), y ahí lo encuentra el mismo lector que usan
                # los otros bancos en 63 de los 80.
                tope=tope_en(detalle),
                # EL DÍA. `field_dias_de_aplicacion` es una taxonomía —limpia
                # hoy, pero de 27 términos que mezclan días, prosa ("Sabados,
                # domingos y feriados") y hasta un "Descuentos adicionales" que
                # no es un día—, así que el nombre del término no se cree: se
                # parsea igual que la prosa de los otros bancos.
                #
                # `field_descripcion_vigencia_benef` se suma acá y NO en la
                # vigencia, aunque se llame así: lo que trae es "Todos los
                # lunes", "Martes y jueves". Es la trampa de Ripley al revés y
                # en el mismo lugar del modelo —allá un campo de vigencia de
                # campaña se leía como el día del local—, y sale igual de cara:
                # leerlo como vigencia deja los 80 sin día y mete prosa en una
                # fecha.
                dias=dias_en(" · ".join(_terminos(ficha, "field_dias_de_aplicacion", incluidos)),
                             atributos.get("field_descripcion_vigencia_benef")),
                vigencia_hasta=_vigencia_security(rango, atributos),
                tarjetas=tarjetas,
                segmentado=bool(tarjetas),
                modalidad=modalidad_en(detalle,
                                       atributos.get("field_descripcion_caluga_benefic")),
                # El detalle y no la frase legal: la legal son 41 variantes de
                # una misma plantilla en los 175, y sus dos datos útiles —hasta
                # cuándo y con qué tarjeta— ya viajan en `vigencia_hasta` y en
                # `tarjetas`. El detalle es el que trae el tope y el cómo.
                condiciones=detalle,
                url=banco["url_base"] + ((atributos.get("path") or {}).get("alias") or ""),
                sitio_web=url_normal((atributos.get("field_enlace_marca") or {}).get("uri")),
                logo=_logo_security(ficha, incluidos, banco["url_base"]),
            )
            fichas_vistas += 1
            for local in _locales_security(atributos):
                recogidos.append(Descuento(**base, **local))

    log.info("Security: %d locales en %d beneficios gastronómicos",
             len(recogidos), fichas_vistas)
    return recogidos


def _paginas_security(cliente: ClienteEducado, url: str, params: dict, tope: int = 40):
    """Las páginas del JSON:API, siguiendo `links.next` y sin contar registros.

    Drupal omite uno a uno los nodos que no están publicados —335 de los 510
    que tiene el sitio— y no rellena el hueco: quedan páginas con `data: []`
    en medio de la lista, y la primera de todas es una de ellas. Un paginador
    que corte en la primera página vacía se lleva CERO de los 175 beneficios
    publicados; uno que corte al ver menos de 50 registros se lleva la mitad.

    Se corta cuando `links.next` desaparece, que es lo que define el estándar.
    El tope es sólo un seguro contra un `next` que apunte a sí mismo: hoy son
    once páginas y el sitio entero cabría en once más.
    """
    vistas = 0
    while url and vistas < tope:
        datos = cliente.json(url, params=params, cabeceras=_JSONAPI)
        # `next` ya trae el page[offset], el page[limit] y el include en la
        # query: repetir los params encima duplicaría el límite.
        params = None
        vistas += 1
        if not isinstance(datos, dict):
            log.warning("Security: la página %d del JSON:API no devolvió JSON", vistas)
            return
        incluidos = {(x.get("type"), x.get("id")): x for x in datos.get("included") or []}
        yield (datos.get("data") or []), incluidos
        url = ((datos.get("links") or {}).get("next") or {}).get("href") or ""


def _relacionados(ficha: dict, campo: str, incluidos: dict) -> list[dict]:
    """Los recursos de una relación, resueltos contra el `included` de la página.

    JSON:API entrega la relación como puntero ({type, id}) y el recurso aparte.
    Un campo de un solo valor viene como objeto y uno multivaluado como lista
    —`field_logo` es objeto, `field_dias_de_aplicacion` es lista—, así que los
    dos casos se resuelven acá y no en cada llamada.
    """
    dato = ((ficha.get("relationships") or {}).get(campo) or {}).get("data")
    punteros = dato if isinstance(dato, list) else ([dato] if isinstance(dato, dict) else [])
    return [incluidos[(p.get("type"), p.get("id"))]
            for p in punteros if (p.get("type"), p.get("id")) in incluidos]


def _terminos(ficha: dict, campo: str, incluidos: dict) -> list[str]:
    """Los nombres de los términos de taxonomía de una relación."""
    return [str((r.get("attributes") or {}).get("name") or "")
            for r in _relacionados(ficha, campo, incluidos)]


def _categoria_security(ficha: dict, incluidos: dict, categorias: list[str]) -> str:
    """El rubro del beneficio, o "" si no es de comer.

    El filtro es la taxonomía del propio banco y no una lista de palabras:
    Security clasifica sus 175 beneficios en su vocabulario `beneficios`
    (Gourmet, Restaurantes, Comida Rápida, Viajes, Shopping y servicios…) y
    eso es más fiel que adivinar por el nombre. Son 80 de 175.

    Un beneficio puede llevar dos rubros —27 de los 80 son Gourmet Y
    Restaurantes— así que el orden de `categorias` en el YAML es de prioridad:
    manda el primero que calce.
    """
    suyas = {plano(n) for n in _terminos(ficha, "field_categorias_beneficio", incluidos)}
    for candidata in categorias:
        if plano(candidata) in suyas:
            return candidata
    return ""


def _descuento_security(atributos: dict) -> tuple[int | None, str]:
    """Cuánto rebaja el beneficio, y el 0 que no es un cero por ciento.

    `field_porcentaje_descuento` trae 0 en 14 de los 80 gastronómicos, y no es
    que el descuento sea nulo: es un centinela para lo que no cabe en un
    entero. Publicarlo tal cual pondría catorce tarjetas anunciando "0% de
    descuento", que es la misma mentira que el "1% de descuento" de los China
    Wok de Bci —ver `_descuento_bci`— y se resuelve igual: por debajo del piso,
    el número no se lee como porcentaje sino como bandera, y el valor real se
    busca donde el banco sí lo escribió.

    Detrás del 0 hay cuatro cosas distintas y cada una tiene su lugar:

      7  menús a precio fijo   → `field_titulo_caluga` dice "Menú Priceless"
      4  montos por app Copec  → el precio está SÓLO en el título ($3.000)
      1  un 10% escondido      → el título y la caluga lo dicen, el campo no
      2  portadas de cuponera  → no son locales; se excluyen en el YAML

    Devuelve (porcentaje, etiqueta). Solo uno de los dos trae algo.
    """
    crudo = atributos.get("field_porcentaje_descuento")
    numero = crudo if isinstance(crudo, int) else None
    if numero is not None and 5 <= numero <= 100:
        return numero, ""

    titulo = str(atributos.get("title") or "")
    caluga = str(atributos.get("field_titulo_caluga") or "")

    # "Mastercard - Claro Arena 10% de dcto." lleva el 10 en el título y en la
    # caluga, y un 0 en el campo numérico. Se miran esos dos y no el detalle:
    # el detalle es prosa larga y `porcentaje_en` se queda con el número más
    # alto que encuentre, que ahí puede ser el de otra cosa.
    del_texto = porcentaje_en(titulo, caluga)
    if del_texto is not None:
        return del_texto, ""

    # "Mastercard - app Copec - Juan Valdez $3.000": el precio cerrado vive en
    # el título y en ninguna otra parte. Son cuatro (Juan Valdez, SBARRO,
    # Streat Burger y Pronto Copec) y es una oferta, no un porcentaje.
    monto = re.search(r"\$\s?[\d.]+", titulo)
    if monto:
        return None, monto.group(0).replace(" ", "").rstrip(".")

    # La caluga es el titular de la tarjeta del banco. Cuando dice algo
    # distinto del nombre de la marca, ese algo es la oferta —los siete "Menú
    # Priceless"—; cuando repite la marca no dice nada y se deja en blanco.
    marca = str(atributos.get("field_nombre_marca") or "")
    if caluga and plano(caluga) != plano(marca):
        return None, caluga.strip()
    return None, oferta_en(titulo, caluga)


def _vigencia_security(rango: dict, atributos: dict) -> date | None:
    """Hasta cuándo corre: la más restrictiva entre la fecha y la letra chica.

    `field_vigencia_beneficio.end_value` es una fecha ISO de verdad y en 79 de
    los 80 coincide con la que declara `field_frase_legal_beneficio`. El que
    sobra es `Al Pesto`, que dice 2026-11-30 en el campo y "Promoción válida
    hasta el 31/03/2026" en la frase legal, y no lo toca nadie desde marzo:
    filtrando sólo por el campo estructurado entra como vigente y manda a
    alguien a pagar la cuenta completa.

    Quedarse con la menor no le cuesta nada a los otros 79 —tienen la misma
    fecha en los dos lados— y deja fuera al único que se contradice.
    """
    candidatas = [f for f in (_fecha_iso((rango or {}).get("end_value")),
                              vigencia_en(str(atributos.get("field_frase_legal_beneficio") or "")))
                  if f is not None]
    return min(candidatas) if candidatas else None


def _comercio_security(atributos: dict) -> str:
    """El nombre del local, sin la marca de segmento pegada atrás.

    13 de los 175 nombres terminan en "- Mastercard" y 6 en "- Banca Joven":
    eso es a qué cliente apunta la campaña, no cómo se llama el restaurante.
    Sin sacarlo el mismo local aparece dos veces con nombres distintos, y no es
    hipotético: `Capogrossi` está publicado con 40% y `Capogrossi - Mastercard`
    con un menú a precio fijo, los dos en Alonso de Córdova 4225. Con el sufijo
    afuera son una sola ficha y se queda la que tiene más dato.
    """
    nombre = " ".join(str(atributos.get("field_nombre_marca")
                          or atributos.get("title") or "").split())
    nombre = re.sub(r"\s*[-–]\s*(Mastercard|Banca Joven)\s*$", "", nombre, flags=re.I)
    return nombre.strip(" -–")


def _locales_security(atributos: dict) -> list[dict]:
    """Una fila por local: Security mete varios en un campo separados por " | ".

    18 de los 80 gastronómicos traen más de una dirección ahí adentro —la
    Barquillería tiene seis— y son 111 direcciones en total. Sin partirlas, El
    Taller cae en un solo pin y sus otros dos locales desaparecen del mapa: se
    perdían dos tercios de los pines de esta fuente. Es lo mismo que hace
    `_bancochile` con sus sucursales, y además deja que la huella
    banco|comercio|comuna|dirección de `modelo.py` distinga los locales sola.
    """
    crudas = str(atributos.get("field_direccion_establecimiento_") or "").strip()
    if not crudas:
        # `field_ubicacion_caluga` es el texto de la tarjeta y casi siempre es
        # una lista de comunas ("Las Condes, Lo Barnechea y Providencia."), que
        # como dirección no sirve. Sólo se usa cuando trae número de calle: en
        # el catálogo de hoy eso rescata a ZIA Bistró & Café (Avenida El Rodeo
        # 13453, Lo Barnechea) y deja afuera "Rappi app." y "PedidosYa app.".
        caluga = str(atributos.get("field_ubicacion_caluga") or "").strip()
        crudas = caluga if re.search(r"\d", caluga) else ""

    locales = []
    for cruda in crudas.split("|"):
        direccion = _direccion_security(cruda)
        # La comuna NO existe como campo en esta fuente: sale de la dirección o
        # no sale. Lo que no calce con la tabla de comunas del proyecto queda
        # en blanco y lo resuelven después el geocodificador y la memoria de
        # correcciones; inventarla sería peor que no tenerla.
        comuna, region = lugar_en(_trozos_direccion(direccion))
        if not (direccion or comuna):
            continue
        locales.append({"direccion": direccion, "comuna": comuna, "region": region})
    return locales or [{"direccion": "", "comuna": "", "region": ""}]


def _direccion_security(cruda: str) -> str:
    """Una dirección, o vacío cuando lo que hay no es una dirección.

    Los cuatro locales de la plataforma Justo escriben su URL en el campo de
    la dirección: "kobo.cl", "ryge.cl", "streetwrap.cl" y
    "delivery.comidaslapunta.cl/pedir". Publicarlas manda al geocodificador a
    buscar una calle que no existe y deja la ficha diciendo que el local queda
    en kobo.cl. El sitio del local ya viaja en `sitio_web`.
    """
    limpia = " ".join(str(cruda or "").split()).strip(" .,")
    if re.match(r"^(https?://)?[\w-]+(\.[\w-]+)+(/\S*)?$", limpia):
        return ""
    return limpia


def _trozos_direccion(direccion: str) -> list[str]:
    """La dirección partida en los pedazos donde puede estar la comuna.

    `lugar_en` compara etiqueta por etiqueta y no busca dentro del texto, que
    es justo lo que hay que hacer con una dirección chilena: "Av. Las Condes
    1234, Lo Barnechea" es de Lo Barnechea, y una búsqueda por substring la
    mandaría a Las Condes.
    """
    trozos = []
    for parte in re.split(r"[,;]", direccion):
        # El código postal pegado a la comuna: "Av. Vitacura 9275, 7630000
        # Vitacura." es el único caso del catálogo, y sin sacarle el número el
        # trozo no calza con nada y Barbazul se queda sin comuna.
        limpio = re.sub(r"^\s*\d{4,8}\s+", "", parte).strip(" .")
        if limpio:
            trozos.append(limpio)

    # "Santiago" es una comuna Y el nombre de la ciudad entera. En "Av. El
    # Rodeo 13032, Santiago, Lo Barnechea." es lo segundo, y como `lugar_en` se
    # queda con el primer trozo que reconoce, Tanaka salía en la comuna de
    # Santiago —el centro— estando en Lo Barnechea, doce kilómetros más arriba.
    # Cuando la misma dirección nombra otra comuna, manda ella.
    if len([t for t in trozos if plano(t) in COMUNAS]) > 1:
        trozos = [t for t in trozos if plano(t) != "santiago"]
    return trozos


def _logo_security(ficha: dict, incluidos: dict, url_base: str) -> str:
    """El logo del local. Drupal lo entrega como ruta del sitio, sin dominio."""
    for archivo in _relacionados(ficha, "field_logo", incluidos):
        ruta = ((archivo.get("attributes") or {}).get("uri") or {}).get("url") or ""
        if ruta:
            return (url_base + ruta) if ruta.startswith("/") else ruta
    return ""


ADAPTADORES = {
    "bancochile": _bancochile,
    "bci": _bci,
    "falabella": _falabella,
    "santander": _santander,
    "cencosud": _cencosud,
    "ripley": _ripley,
    "entel": _entel,
    "security": _security,
}
