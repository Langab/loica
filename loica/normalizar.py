"""Interpretación de fechas, precios y comunas escritos como los escriben los humanos.

Las agendas culturales chilenas publican "Sábado 15 de marzo, 19:30 hrs" o
"Entrada liberada", no ISO 8601. Este módulo traduce eso a datos.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from html import unescape

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
    "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}

PALABRAS_GRATIS = (
    "gratis", "gratuito", "gratuita", "liberada", "liberado", "sin costo",
    "entrada libre", "acceso libre", "free", "adhesion voluntaria",
)

COMUNAS_RM = (
    "Santiago", "Providencia", "Las Condes", "Vitacura", "Lo Barnechea", "Ñuñoa",
    "La Reina", "Macul", "Peñalolén", "La Florida", "Puente Alto", "San Joaquín",
    "San Miguel", "La Cisterna", "El Bosque", "La Granja", "Maipú", "Estación Central",
    "Quinta Normal", "Cerrillos", "Pudahuel", "Renca", "Quilicura", "Conchalí",
    "Huechuraba", "Recoleta", "Independencia", "Cerro Navia", "Lo Prado",
    "Pedro Aguirre Cerda", "Lo Espejo", "San Ramón", "La Pintana", "San Bernardo",
)


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").lower()


# Shortcodes de WordPress que el tema deja sin renderizar en el contenido que
# devuelve la API REST: [vc_row], [/vc_column_text], [vc_column width="1/1"].
# No son texto, son maquetación, y además ENVENENAN la lectura de fechas: el
# `width="1/1"` de WPBakery calza con el patrón dd/mm y Artequin publicaba
# todos sus talleres el 1 de enero. Los temas Uncode/Visual Composer son
# comunes en los sitios culturales chilenos, así que esto no es un parche
# para una fuente. Solo se sacan los de nombre en minúscula, que es la
# convención de WordPress: "[13 de septiembre]" o "[Ver más]" no se tocan.
_SHORTCODE = re.compile(r"\[/?[a-z][a-z0-9_]*(?=[\s\]/])[^\]]*\]")


def limpiar_html(texto: str) -> str:
    """Quita etiquetas, shortcodes y decodifica entidades (&#038; → &)."""
    if not texto:
        return ""
    sin_tags = re.sub(r"<[^>]+>", " ", texto)
    return " ".join(unescape(_SHORTCODE.sub(" ", sin_tags)).split())


def parsear_fecha(texto: str, anio_por_defecto: int | None = None,
                  publicado: datetime | None = None) -> datetime | None:
    """Extrae la primera fecha reconocible de un texto libre en español.

    Reconoce: ISO, dd/mm/aaaa, "15 de marzo", "15 de marzo de 2027",
    "sábado 15 de marzo", rangos "del 3 al 28 de febrero", con hora opcional
    ("19:30", "19.30 hrs", "a las 19").

    `publicado` es la fecha en que la fuente publicó el aviso. Sirve para no
    inventar eventos futuros: si un post de julio de 2026 dice "5 de julio",
    se entiende que habla de 2026, no del año que viene.
    """
    if not texto:
        return None

    plano = _plano(texto)
    hoy = datetime.now()
    anio_defecto = anio_por_defecto or (publicado.year if publicado else hoy.year)
    fecha = None

    # Se recorren TODAS las coincidencias de cada patrón, no solo la primera:
    # en una página larga la primera suele ser basura (un horario, un teléfono)
    # y la fecha de verdad viene después.

    posicion = 0  # dónde apareció la fecha, para buscar la hora al lado

    # ISO compacto: 20270315, sin separadores. Lo usan los campos ACF de
    # WordPress —el CEP publica así la fecha de sus seminarios— y sin esto la
    # fecha se leía como un número cualquiera y el evento quedaba sin cuándo.
    # Va primero porque el patrón con guiones no lo reconoce, y se exige año
    # plausible para no confundirlo con un teléfono o un monto.
    for m in re.finditer(r"(?<!\d)(20[2-9]\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)",
                         plano):
        try:
            fecha = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            posicion = m.end()
            break
        except ValueError:
            continue

    # ISO: 2027-03-15 (con o sin hora). La T va en minúscula además de
    # mayúscula porque el texto ya pasó por _plano(), que lo bajó todo: con
    # solo [T ] la hora NUNCA calzaba y todo evento con JSON-LD quedaba a las
    # 00:00. Para un club eso no es un detalle, es el dato.
    for m in re.finditer(r"(\d{4})-(\d{2})-(\d{2})(?:[Tt ](\d{1,2}):(\d{2}))?", plano):
        try:
            fecha = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                             int(m.group(4) or 0), int(m.group(5) or 0))
            posicion = m.end()
            break
        except ValueError:
            continue

    # dd/mm/aaaa o dd-mm-aaaa
    if fecha is None:
        for m in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", plano):
            dia, mes = int(m.group(1)), int(m.group(2))
            anio = int(m.group(3)) if m.group(3) else anio_defecto
            if anio < 100:
                anio += 2000
            try:
                fecha = datetime(anio, mes, dia)
                posicion = m.end()
                break
            except ValueError:
                continue

    patron_meses = "|".join(sorted(MESES, key=len, reverse=True))

    # Fin de un rango que cruza de mes. Sirve para no mandar al año siguiente
    # una temporada que está EN CURSO: "del 2 de julio al 5 de septiembre",
    # leído un 11 de agosto, empieza el 2 de julio de ESTE año, no del próximo.
    fin_del_rango = None

    # Rango entre meses distintos: "del 2 de julio al 5 de septiembre"
    if fecha is None:
        m = re.search(rf"\b(?:del?\s+|desde\s+el\s+)?(\d{{1,2}})\s*(?:de\s+)?({patron_meses})"
                      rf"\s+al?\s+(\d{{1,2}})\s*(?:de\s+)?({patron_meses})\b"
                      rf"(?:\s*,?\s*(?:de|del)?\s*(\d{{4}}))?", plano)
        if m:
            anio = int(m.group(5)) if m.group(5) else anio_defecto
            try:
                fecha = datetime(anio, MESES[m.group(2)], int(m.group(1)))
                fin = datetime(anio, MESES[m.group(4)], int(m.group(3)))
                # Una temporada que termina antes de empezar cruza el año nuevo
                fin_del_rango = fin if fin >= fecha else fin.replace(year=anio + 1)
                posicion = m.end()
            except ValueError:
                fecha = fin_del_rango = None

    # Rango "del 3 al 28 de febrero": interesa el DÍA DE INICIO, no el final
    if fecha is None:
        m = re.search(rf"\b(?:del\s+|desde\s+el\s+)?(\d{{1,2}})\s+al\s+\d{{1,2}}"
                      rf"\s*(?:de\s+)?({patron_meses})\b(?:\s*,?\s*(?:de|del)?\s*(\d{{4}}))?", plano)
        if m:
            try:
                fecha = datetime(int(m.group(3)) if m.group(3) else anio_defecto,
                                 MESES[m.group(2)], int(m.group(1)))
                posicion = m.end()
            except ValueError:
                fecha = None

    # "15 de marzo" / "15 de marzo de 2027" / "15 marzo" / "15 Marzo, 2027"
    # La coma antes del año no es un adorno: el MAC escribe "11 Julio, 2026" y
    # sin tolerarla el año se descartaba, la fecha quedaba "sin año" y la regla
    # de más abajo la mandaba al año siguiente. Seis exposiciones en curso
    # aparecían programadas para 2027.
    if fecha is None:
        for m in re.finditer(rf"\b(\d{{1,2}})\s*(?:de\s+)?({patron_meses})\b"
                             rf"(?:\s*,?\s*(?:de|del)?\s*(\d{{4}}))?", plano):
            dia = int(m.group(1))
            mes = MESES[m.group(2)]
            anio = int(m.group(3)) if m.group(3) else anio_defecto
            try:
                fecha = datetime(anio, mes, dia)
                posicion = m.end()
                break
            except ValueError:
                continue

    # Sin año explícito hay que decidir de qué año habla el aviso.
    if fecha is not None and not re.search(r"\b(19|20)\d{2}\b", plano[:posicion or 200]):
        referencia = publicado or hoy
        # Una temporada en curso no se manda al año siguiente: si el rango
        # TERMINA en el futuro, la obra se está dando ahora aunque haya
        # empezado hace meses. Sin esto, "del 2 de julio al 5 de septiembre"
        # leído en agosto quedaba como julio del año que viene.
        en_curso = fin_del_rango is not None and fin_del_rango.date() >= hoy.date()
        # Un aviso no anuncia algo que ya pasó: si la fecha quedó antes de la
        # publicación, habla del año siguiente (posts de diciembre sobre enero).
        if not en_curso and fecha.date() < referencia.date() - timedelta(days=30):
            fecha = fecha.replace(year=fecha.year + 1)

    if fecha is None:
        return None

    # Hora: se busca JUNTO a la fecha, no en toda la página. Si no, en un sitio
    # de teatro se termina tomando el horario de atención de la boletería.
    if fecha.hour == 0 and fecha.minute == 0:
        ventana = plano[posicion:posicion + 120] if posicion else plano[:200]
        mh = re.search(r"\b(?:a\s+las\s+)?([01]?\d|2[0-3])[:.h](\d{2})\b", ventana)
        if mh:
            fecha = fecha.replace(hour=int(mh.group(1)), minute=int(mh.group(2)))
        else:
            mh = re.search(r"\b(?:a\s+las\s+)([01]?\d|2[0-3])\s*(?:hrs?|horas)?\b", ventana)
            if mh:
                fecha = fecha.replace(hour=int(mh.group(1)))

    return fecha


def parsear_precio(texto: str) -> tuple[int | None, bool | None, str]:
    """Devuelve (precio_clp, es_gratis, texto_original_resumido).

    Ante la duda devuelve (None, None, texto): mejor un dato vacío que uno falso,
    porque el filtro "solo gratis" es la promesa central del producto.
    """
    if not texto:
        return None, None, ""

    plano = _plano(texto)

    def contexto(pos: int, largo: int = 60) -> str:
        """Solo el trozo donde apareció el precio, no el texto entero."""
        inicio = max(0, pos - 20)
        return " ".join(texto[inicio:inicio + largo].split())

    for palabra in PALABRAS_GRATIS:
        pos = plano.find(palabra)
        if pos >= 0:
            # "gratis hasta agotar cupos" sigue siendo gratis
            return 0, True, contexto(pos)

    # $5.000 / $ 5000 / 5.000 pesos / CLP 5000
    m = re.search(r"\$\s*(\d{1,3}(?:[.\s]\d{3})+|\d{3,6})", plano)
    if not m:
        m = re.search(r"\b(\d{1,3}(?:[.\s]\d{3})+|\d{4,6})\s*(?:pesos|clp)\b", plano)
    if m:
        try:
            valor = int(re.sub(r"[.\s]", "", m.group(1)))
            if 0 < valor <= 2_000_000:
                return valor, False, contexto(m.start())
        except ValueError:
            pass

    # Sin señales de precio no se inventa nada: el filtro "solo gratis" es la
    # promesa central del producto y un falso positivo la rompe.
    return None, None, ""


# La comuna se busca como palabra entera. Media lista son palabras corrientes
# del castellano que viven dentro de otras: "Inmaculado Corazón de María"
# contiene "Macul" y "la danza del oso" contiene "el bosque". Como abajo gana
# la mención más tardía, y estos accidentes aparecen en medio de la prosa, sin
# la frontera un concierto en la Basílica quedaba en Macul.
_COMUNA_RE = {c: re.compile(rf"(?<![0-9a-z]){re.escape(_plano(c))}(?![0-9a-z])")
              for c in COMUNAS_RM}


def detectar_comuna(*textos: str) -> str:
    """Busca una comuna del Gran Santiago en los textos entregados, por orden.

    Los textos se miran en el orden en que llegan y el primero que diga algo
    manda: los adaptadores pasan primero la dirección, después el nombre del
    lugar y al final la comuna por defecto de la fuente.

    DENTRO de un mismo texto gana la primera de `COMUNAS_RM`, y como esa lista
    parte por "Santiago", en la práctica Santiago le gana a cualquier comuna
    que la acompañe. Eso etiqueta mal direcciones como "Providencia, Barrio
    Bellavista, Teatro San Ginés"... y NO se arregla dando vuelta la
    preferencia. Se intentó el 16-08-2026 y salió empatado:

      · "Que gane la comuna que no sea Santiago" arregla el San Ginés, la
        Corporación Cultural de La Reina y un par de Las Condes —14 eventos—,
        pero rompe otros 15: el MAC y el Museo Nacional de Historia Natural
        están en el PARQUE Quinta Normal, que es un parque de la comuna de
        SANTIAGO con el nombre de otra comuna. El índice OSM local lo zanja:
        Matucana 464 → ciudad "santiago".

    El texto solo no alcanza, porque "Quinta Normal" puede ser el parque o la
    comuna y la dirección no dice cuál. Quien sí puede zanjarlo es la posición
    —`datos/indice_osm.db` guarda la ciudad de cada dirección—, y mientras esa
    resolución no exista, los casos puntuales se arreglan donde corresponde:
    `config/correcciones/lugares.yaml`, que manda sobre todo esto y se
    verifica lugar por lugar.
    """
    for texto in textos:
        if not texto:
            continue
        plano = _plano(texto)
        for comuna, patron in _COMUNA_RE.items():
            if patron.search(plano):
                return comuna
    return ""


def resumir(texto: str, largo: int = 200) -> str:
    """Recorta a un resumen corto: guardamos hechos, no obras ajenas."""
    limpio = limpiar_html(texto)
    if len(limpio) <= largo:
        return limpio
    corte = limpio[:largo].rsplit(" ", 1)[0]
    return corte + "…"
