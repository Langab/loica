"""Lectura del dato que los bancos publican en prosa.

Los tres bancos que sirven entregan JSON, pero solo Falabella trae el día de la
semana como campo. Banco de Chile lo mete en una lista plana de etiquetas
mezclado con la región y la comuna (`["providencia", "martes", "segmentado"]`),
y BCI directamente no lo tiene: hay que sacarlo del HTML de la promoción.

Todo el parseo vive acá y no en los adaptadores, porque el problema es el
mismo tres veces y las reglas del castellano no cambian según el banco.

Se parsea con diccionario y expresión regular, sin modelo de lenguaje: la
corrida diaria no puede costar plata ni depender de una API con token.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

# Orden canónico. Es el que usa la página para ordenar los chips, así que
# lunes va primero y no domingo (que es lo que devolvería `Date.getDay()`).
DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")

_INDICE_DIA = {d: i for i, d in enumerate(DIAS)}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Las regiones vienen con nombre largo o corto según el banco: Falabella dice
# "Región Metropolitana de Santiago" y Banco de Chile "metropolitana de
# santiago". La clave es la forma plana; el valor, cómo se muestra.
REGIONES = {
    "arica y parinacota": "Arica y Parinacota",
    "tarapaca": "Tarapacá",
    "antofagasta": "Antofagasta",
    "atacama": "Atacama",
    "coquimbo": "Coquimbo",
    "valparaiso": "Valparaíso",
    "metropolitana de santiago": "Metropolitana",
    "metropolitana": "Metropolitana",
    "ohiggins": "O'Higgins",
    "o higgins": "O'Higgins",
    "libertador general bernardo ohiggins": "O'Higgins",
    "maule": "Maule",
    "nuble": "Ñuble",
    "biobio": "Biobío",
    "la araucania": "La Araucanía",
    "araucania": "La Araucanía",
    "los rios": "Los Ríos",
    "los lagos": "Los Lagos",
    "aysen": "Aysén",
    "aysen del general carlos ibanez del campo": "Aysén",
    "magallanes": "Magallanes",
    "magallanes y de la antartica chilena": "Magallanes",
}

# Comunas y ciudades donde los bancos efectivamente tienen convenios. No es el
# listado completo de las 346 comunas del país: es el que aparece en los datos,
# más el Gran Santiago entero. Lo que no esté acá queda con la región puesta y
# la comuna vacía, que es preferible a inventarla.
COMUNAS = {
    # Gran Santiago
    "santiago": "Santiago", "providencia": "Providencia", "las condes": "Las Condes",
    "vitacura": "Vitacura", "lo barnechea": "Lo Barnechea", "nunoa": "Ñuñoa",
    "la reina": "La Reina", "macul": "Macul", "penalolen": "Peñalolén",
    "la florida": "La Florida", "puente alto": "Puente Alto", "san joaquin": "San Joaquín",
    "san miguel": "San Miguel", "la cisterna": "La Cisterna", "el bosque": "El Bosque",
    "la granja": "La Granja", "maipu": "Maipú", "estacion central": "Estación Central",
    "quinta normal": "Quinta Normal", "cerrillos": "Cerrillos", "pudahuel": "Pudahuel",
    "renca": "Renca", "quilicura": "Quilicura", "conchali": "Conchalí",
    "huechuraba": "Huechuraba", "recoleta": "Recoleta", "independencia": "Independencia",
    "cerro navia": "Cerro Navia", "lo prado": "Lo Prado", "lo espejo": "Lo Espejo",
    "pedro aguirre cerda": "Pedro Aguirre Cerda", "san ramon": "San Ramón",
    "la pintana": "La Pintana", "san bernardo": "San Bernardo", "colina": "Colina",
    "lampa": "Lampa", "buin": "Buin", "padre hurtado": "Padre Hurtado",
    "pirque": "Pirque", "san jose de maipo": "San José de Maipo", "talagante": "Talagante",
    "melipilla": "Melipilla", "penaflor": "Peñaflor", "calera de tango": "Calera de Tango",
    # Valparaíso
    "vina del mar": "Viña del Mar", "concon": "Concón", "quilpue": "Quilpué",
    "villa alemana": "Villa Alemana", "san antonio": "San Antonio", "quintero": "Quintero",
    "zapallar": "Zapallar", "papudo": "Papudo", "la ligua": "La Ligua",
    "los andes": "Los Andes", "san felipe": "San Felipe", "cachagua": "Cachagua",
    "algarrobo": "Algarrobo", "el quisco": "El Quisco", "cartagena": "Cartagena",
    "olmue": "Olmué", "limache": "Limache", "casablanca": "Casablanca",
    # Norte
    "arica": "Arica", "iquique": "Iquique", "alto hospicio": "Alto Hospicio",
    "calama": "Calama", "san pedro de atacama": "San Pedro de Atacama",
    "copiapo": "Copiapó", "caldera": "Caldera", "vallenar": "Vallenar",
    "la serena": "La Serena", "coquimbo ciudad": "Coquimbo", "ovalle": "Ovalle",
    "vicuna": "Vicuña", "illapel": "Illapel",
    # Centro sur
    "rancagua": "Rancagua", "machali": "Machalí", "santa cruz": "Santa Cruz",
    "pichilemu": "Pichilemu", "san fernando": "San Fernando",
    "talca": "Talca", "curico": "Curicó", "linares": "Linares",
    "constitucion": "Constitución", "chillan": "Chillán", "concepcion": "Concepción",
    "talcahuano": "Talcahuano", "san pedro de la paz": "San Pedro de la Paz",
    "chiguayante": "Chiguayante", "los angeles": "Los Ángeles", "coronel": "Coronel",
    # Sur
    "temuco": "Temuco", "padre las casas": "Padre Las Casas", "villarrica": "Villarrica",
    "pucon": "Pucón", "valdivia": "Valdivia", "osorno": "Osorno",
    "puerto montt": "Puerto Montt", "puerto varas": "Puerto Varas", "frutillar": "Frutillar",
    "castro": "Castro", "ancud": "Ancud", "chiloe": "Chiloé",
    "coyhaique": "Coyhaique", "puerto natales": "Puerto Natales",
    "punta arenas": "Punta Arenas",
}

# Etiquetas de gestión interna del banco que no dicen nada del descuento.
RUIDO = {
    "segmentado", "casa-matriz", "planes", "big5", "todo-chile", "tarjeta-fan",
    "sabores", "restaurant", "restaurante", "restaurantes", "comida", "sucursale",
    "sucursales", "regiones", "canje-dolares-premios", "dolares-premio",
}


def plano(texto: str) -> str:
    """Minúsculas y sin tildes. Los bancos escriben 'sabado' y 'sábado'."""
    sin_tildes = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").lower()


def _tiene(texto: str, palabra: str) -> bool:
    """Con límite de palabra: sin él 'lunes' matchea dentro de otra cosa."""
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(palabra)}(?![a-z0-9])", texto))


def _tiene_dia(texto: str, dia: str) -> bool:
    """Como _tiene, pero acepta el plural del día.

    De los siete días, solo sábado y domingo cambian en plural — lunes a
    viernes son invariables. Por eso el error pasaba desapercibido: "todos los
    martes" se leía bien y "todos los sábados" no, y quedaba con la lista de
    días VACÍA, que en este modelo significa "sin restricción". Un descuento
    de sábado terminaba anunciado como de todos los días.
    """
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(dia)}s?(?![a-z0-9])", texto))


def dias_en(*textos: str) -> list[str]:
    """Días de la semana mencionados, en orden de lunes a domingo.

    Entiende las cuatro formas en que los bancos lo escriben:

        "todos los martes"        → martes
        "lunes y martes"          → lunes, martes
        "de domingo a jueves"     → domingo, lunes, martes, miércoles, jueves
        "todos los días"          → los siete

    El rango envuelve la semana a propósito: "domingo a jueves" es la promoción
    de días de baja, y leerla como un solo día sería perder cinco.
    """
    texto = plano(" · ".join(str(t) for t in textos if t))
    if not texto:
        return []

    if re.search(r"todos los dias|todo los dias|de lunes a domingo|toda la semana", texto):
        return list(DIAS)

    encontrados: set[str] = set()

    # Rangos primero: "de lunes a jueves". El "de" es opcional, y el plural
    # también ("de sábados a lunes" lo escribe más de un banco).
    for desde, hasta in re.findall(
            rf"({'|'.join(DIAS)})s?\s+a\s+({'|'.join(DIAS)})s?", texto):
        i, f = _INDICE_DIA[desde], _INDICE_DIA[hasta]
        largo = (f - i) % 7
        encontrados.update(DIAS[(i + paso) % 7] for paso in range(largo + 1))

    for dia in DIAS:
        if _tiene_dia(texto, dia):
            encontrados.add(dia)

    # En Chile "el finde" es sábado y domingo; el viernes se dice aparte.
    if re.search(r"fin de semana|finde", texto):
        encontrados.update(("sabado", "domingo"))

    return sorted(encontrados, key=_INDICE_DIA.__getitem__)


def porcentaje_en(*textos: str) -> int | None:
    """El descuento anunciado. Se queda con el mayor, que es el del titular.

    "Hasta un 40%" con una condición que menciona un 10% en otra cosa tiene que
    devolver 40: es el número por el que la persona va al restaurante. Sobre 90
    se descarta — a esa altura ya no es un descuento sino un año o un RUT.

    Se acepta "20 dcto" sin símbolo porque Bci lo escribe así seguido (Le Pain
    Quotidien, entre otros) y si no, esas promociones quedan sin número.

    Devuelve None de verdad cuando no hay porcentaje: los 2x1, las bebidas de
    regalo y los combos a precio fijo son descuentos reales que no se expresan
    en por ciento, y ponerles un número inventado sería peor que dejarlos en
    blanco.
    """
    texto = plano(" · ".join(str(t) for t in textos if t))
    valores = [int(n) for n in re.findall(r"(\d{1,2})\s*(?:%|dcto|dto\b)", texto)]
    valores = [v for v in valores if 5 <= v <= 90]
    return max(valores) if valores else None


def oferta_en(*textos: str) -> str:
    """Etiqueta corta para los descuentos que no se expresan en porcentaje.

    La categoría de comida rápida de Bci son 274 promociones y casi ninguna es
    un por ciento: son "2x1 en KFC", "Coca-Cola 2,5 lts gratis", "empanada de
    regalo", combos a precio fijo. Sin esto, esas 274 filas aparecerían con un
    guion en la columna del descuento, que se lee como "acá no hay nada".

    Solo devuelve algo cuando el patrón es inequívoco. Resumir la descripción a
    la fuerza daba títulos como "2x1 Cadena de comida rápida Tadeo Haenke 1706".
    """
    texto = plano(" · ".join(str(t) for t in textos if t))

    nxm = re.search(r"\b(\d)\s*x\s*(\d)\b", texto)
    if nxm and nxm.group(1) > nxm.group(2):
        return f"{nxm.group(1)}x{nxm.group(2)}"
    if re.search(r"\bgratis\b|\bde regalo\b|\bregalo\b", texto):
        return "Con regalo"
    if re.search(r"\bcombo|\bpack\b|\bprecio especial|\bprecio fijo", texto):
        return "Combo"
    return ""


def tope_en(*textos: str) -> int | None:
    """Tope de descuento por compra, en pesos. Sin él el 40% puede ser $2.000."""
    texto = plano(" · ".join(str(t) for t in textos if t))
    hallazgo = re.search(r"tope[^$]{0,60}\$\s*([\d.]{3,12})", texto)
    if not hallazgo:
        return None
    try:
        return int(hallazgo.group(1).replace(".", ""))
    except ValueError:
        return None


# Lo que precede a una fecha de TÉRMINO ("hasta el 30/09", "del 1 al 30 de
# septiembre", "vence el 31") y lo que precede a una de INICIO ("desde el 1 de
# septiembre", "a partir del 02/01/2026"). La diferencia es la que evita dar
# por muerta una promoción el día después de que empezó.
_CIERRE = re.compile(r"(?:hasta|al|vence|vencimiento|termina|finaliza|expira)\s*(?:el|la|dia)?\s*$")
_APERTURA = re.compile(r"(?:desde|a partir de|a partir del|a contar de|a contar del|inicio|comienza|comienzo)\s*(?:el|dia)?\s*$")

# Un mes a secas ("todos los sabados de agosto", "valido durante septiembre",
# "bases de agosto de 2026") solo cuenta como vigencia si aparece en un
# contexto que hable de cuándo corre la promoción. Sin ese freno, "el menú de
# septiembre" o "inaugurado en marzo" pondrían fecha de término a un descuento
# que no la declara, y un descuento que se cae antes de tiempo es un local
# perdido para quien lo busca.
_CONTEXTO_MES = re.compile(
    r"(?:valid[oa]s?|vigen[a-z]*|durante|mes de|promocion|campana|bases|hasta"
    r"|dcto|descuento|beneficio|oferta"
    r"|los (?:lunes|martes|miercoles|jueves|viernes|sabados?|domingos?))"
    r"[^.·;]{0,40}?\b(?:de |del |en |durante )?(" + "|".join(MESES) + r")\b(?:\s+(?:de |del )?(\d{4}))?")


def _anio_para(mes: int, hoy: date) -> int:
    """El año de un mes que llegó sin año.

    Los bancos escriben "hasta el 30 de septiembre" y "válido en agosto" sin
    decir de qué año, porque para ellos es obvio: es la campaña de este mes o
    de los próximos. Se toma como FUTURO solo si cae dentro de los tres meses
    que vienen; cualquier otro mes se lee como el más reciente ya pasado. El
    sesgo es a propósito: leído el 2 de septiembre, "agosto" es el agosto que
    acaba de terminar y no el del año que viene, y ante la duda es mejor dar
    por vencido un descuento que mandar a alguien a pagar la cuenta entera.
    """
    adelante = (mes - hoy.month) % 12
    if adelante <= 3:
        return hoy.year if mes >= hoy.month else hoy.year + 1
    return hoy.year if mes < hoy.month else hoy.year - 1


def _ultimo_dia(anio: int, mes: int) -> date:
    return date(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)


def vigencia_en(*textos: str, hoy: date | None = None) -> date | None:
    """Hasta cuándo sirve. Es el dato que evita mandar a alguien a un local
    con una promoción muerta, que es la forma más rápida de perder la confianza.

    Tres formas de decirlo, de la más precisa a la más vaga:

    1. Una fecha completa: "hasta el 30 de septiembre de 2026", "31/08/2026".
       Si hay varias, manda la primera que venga precedida de "hasta", "al",
       "vence"; si ninguna lo dice, la última del texto. Una fecha precedida
       de "desde" o "a partir de" es el INICIO y nunca se toma como término:
       antes "válido desde el 02/01/2026 hasta el 31/12/2026" devolvía enero y
       la promoción moría a los dos días de publicada.
    2. Día y mes sin año: "hasta el 30 de septiembre". El año lo pone
       `_anio_para`.
    3. Un mes a secas, en contexto de vigencia: "todos los sábados de agosto",
       "válido durante septiembre", "bases de agosto de 2026". Se toma el
       último día de ese mes. Hasta el 02-09-2026 esto no se leía, y Banco
       Ripley seguía publicando en septiembre 25 convenios "de agosto" como si
       corrieran todavía.

    Sin nada de eso devuelve None, que la página muestra como "sin fecha
    declarada" en vez de dar el descuento por bueno.
    """
    texto = plano(" · ".join(str(t) for t in textos if t))
    hoy = hoy or date.today()
    candidatas: list[tuple[int, date, bool, bool]] = []   # (posición, fecha, cierre, apertura)

    def anotar(posicion: int, anio: int, mes: int, dia: int) -> None:
        try:
            fecha = date(anio, mes, dia)
        except ValueError:
            return
        antes = texto[max(0, posicion - 18):posicion]
        candidatas.append((posicion, fecha,
                           bool(_CIERRE.search(antes)), bool(_APERTURA.search(antes))))

    for m in re.finditer(r"(\d{1,2})\s+de\s+([a-z]+)(?:\s+(?:de|del)\s+(\d{4}))?", texto):
        mes = MESES.get(m.group(2))
        if not mes:
            continue
        anio = int(m.group(3)) if m.group(3) else _anio_para(mes, hoy)
        anotar(m.start(), anio, mes, int(m.group(1)))

    for m in re.finditer(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", texto):
        anotar(m.start(), int(m.group(3)), int(m.group(2)), int(m.group(1)))

    if candidatas:
        candidatas.sort()
        cerradas = [c for c in candidatas if c[2]]
        if cerradas:
            return cerradas[0][1]
        abiertas = [c for c in candidatas if not c[3]]
        if abiertas:
            return abiertas[-1][1]
        return None

    mes_solo = _CONTEXTO_MES.search(texto)
    if mes_solo:
        mes = MESES[mes_solo.group(1)]
        anio = int(mes_solo.group(2)) if mes_solo.group(2) else _anio_para(mes, hoy)
        return _ultimo_dia(anio, mes)
    return None


def modalidad_en(*textos: str) -> str:
    """presencial | online | ambas. Importa: un 30% que solo corre por delivery
    no sirve si la persona ya está sentada en la mesa."""
    texto = plano(" · ".join(str(t) for t in textos if t))
    presencial = bool(re.search(r"presencial|en el local|en local", texto))
    online = bool(re.search(r"online|delivery|en linea|pedidos ya|rappi|uber eats", texto))
    if presencial and online:
        return "ambas"
    return "presencial" if presencial else ("online" if online else "")


def lugar_en(etiquetas) -> tuple[str, str]:
    """Separa comuna y región de una lista plana de etiquetas.

    Banco de Chile las publica revueltas y sin prefijo:
    `["metropolitana de santiago", "providencia", "martes", "segmentado"]`.

    Valparaíso, Antofagasta y Coquimbo son región Y ciudad, así que se resuelve
    por posición: la etiqueta que ya se usó como región no se vuelve a usar como
    comuna, salvo que no haya ninguna otra candidata.
    """
    planas = [plano(e) for e in (etiquetas or [])]
    region = comuna = ""
    etiqueta_region = ""

    for etiqueta in planas:
        if not region and etiqueta in REGIONES:
            region, etiqueta_region = REGIONES[etiqueta], etiqueta

    for etiqueta in planas:
        if etiqueta == etiqueta_region or etiqueta in RUIDO:
            continue
        if etiqueta in COMUNAS:
            comuna = COMUNAS[etiqueta]
            break

    # "valparaiso" sola: la promoción es en la ciudad, no en toda la región
    if not comuna and etiqueta_region in COMUNAS:
        comuna = COMUNAS[etiqueta_region]

    return comuna, region


def es_gastronomico(*textos: str) -> bool:
    """Filtro de categoría para las fuentes que mezclan rubros (BCI publica
    gimnasios, hoteles y restaurantes en el mismo endpoint)."""
    texto = plano(" · ".join(str(t) for t in textos if t))
    return bool(re.search(
        r"restaurant|restaurante|sabores|gastronom|cafeteria|cafe|bar\b|pizzer|"
        r"sushi|comida|cocina|antojos|brunch|heladeria|pasteler|panaderia", texto))

# Las 52 comunas de la Región Metropolitana. La app es de Santiago: un 40% en
# Puerto Natales es un dato correcto y completamente inútil para quien la usa.
COMUNAS_RM = {
    "Santiago", "Cerrillos", "Cerro Navia", "Conchalí", "El Bosque",
    "Estación Central", "Huechuraba", "Independencia", "La Cisterna",
    "La Florida", "La Granja", "La Pintana", "La Reina", "Las Condes",
    "Lo Barnechea", "Lo Espejo", "Lo Prado", "Macul", "Maipú", "Ñuñoa",
    "Pedro Aguirre Cerda", "Peñalolén", "Providencia", "Pudahuel", "Quilicura",
    "Quinta Normal", "Recoleta", "Renca", "San Joaquín", "San Miguel",
    "San Ramón", "Vitacura", "Puente Alto", "Pirque", "San José de Maipo",
    "Colina", "Lampa", "Tiltil", "San Bernardo", "Buin", "Calera de Tango",
    "Paine", "Melipilla", "Alhué", "Curacaví", "María Pinto", "San Pedro",
    "Talagante", "El Monte", "Isla de Maipo", "Padre Hurtado", "Peñaflor",
}


def es_metropolitana(comuna: str, region: str) -> bool:
    """¿Este descuento sirve en Santiago?

    Vale por comuna de la RM, o por región metropolitana cuando el banco no
    baja a comuna (las cadenas y el delivery se publican así). Lo que declara
    otra región se descarta; lo que no declara nada se deja pasar, porque son
    en su mayoría cadenas nacionales que sí tienen local en Santiago.
    """
    if comuna:
        return comuna in COMUNAS_RM
    plana = plano(region)
    if not plana:
        return True
    return "metropolitana" in plana or "todo chile" in plana or "santiago" in plana


def sucursales_bch(html: str) -> list[dict]:
    """Banco de Chile publica los locales como campos separados por punto y coma.

        <ul><li>VACIO;IRARRAZAVAL #3313;Región Metropolitana;ÑUÑOA;VACIO</li></ul>
                     └ dirección      └ región            └ comuna

    Es mejor dato que las etiquetas: acá la comuna viene declarada por el
    banco, no deducida de una lista plana donde "valparaiso" puede ser la
    región o la ciudad. Un local por <li>; las cadenas traen varios.

    "VACIO" es literalmente lo que escriben cuando el campo va en blanco.
    """
    locales = []
    for fila in re.findall(r"<li[^>]*>(.*?)</li>", html or "", re.S):
        partes = [p.strip() for p in re.sub(r"<[^>]+>", " ", fila).split(";")]
        partes = ["" if p.upper() == "VACIO" else p for p in partes]
        if len(partes) < 4:
            continue
        direccion, region, comuna = partes[1], partes[2], partes[3]
        if not (direccion or comuna):
            continue
        locales.append({
            "direccion": " ".join(direccion.split()),
            "region": region_normal(region),
            "comuna": COMUNAS.get(plano(comuna), comuna.strip().title()),
        })
    return locales


def region_normal(crudo: str) -> str:
    """Nombre de región canónico a partir de como lo escriba cada banco.

    En los datos reales aparecen "Región Metropolitana", "RM" y
    "Región Metropolotana" —el typo es de ellos— para la misma región. Sin
    unificarlas, la misma comuna sale con tres regiones distintas y el filtro
    de Santiago deja fuera locales que sí están en Santiago.
    """
    limpio = plano(crudo).replace("region de ", "").replace("region del ", "")
    limpio = limpio.replace("region ", "").strip()
    if not limpio:
        return ""
    # El typo y la abreviatura entran por acá, antes del diccionario exacto.
    # El prefijo corta en "metropol" y no en "metropolit" porque el typo real
    # que publica Banco de Chile es "Metropolotana", con o.
    if limpio in ("rm", "r.m.", "r m") or limpio.startswith("metropol"):
        return "Metropolitana"
    return REGIONES.get(limpio, str(crudo).strip())


def datos_bci(html: str) -> dict:
    """Bci entierra dirección, teléfono y sitio del local en el HTML de la promo.

        <li class="direccion"><i></i> Callao 3123<br>Las Condes</li>
        <li class="telefono">+56 2 2757 2000</li>
        <li class="web"><a href="https://...">...</a></li>

    Las clases son estables (están en las 27 de restaurantes sin excepción),
    así que esto es leer un formato, no adivinar. El <br> separa la calle de
    la comuna: es el único lugar donde Bci declara la comuna de verdad.
    """
    salida = {"direccion": "", "comuna": "", "telefono": "", "sitio_web": ""}
    if not html:
        return salida

    bloque = re.search(r'class="direccion"[^>]*>(.*?)</li>', html, re.S)
    if bloque:
        crudo = re.sub(r"<i[^>]*>.*?</i>", " ", bloque.group(1), flags=re.S)
        trozos = [" ".join(t.split()) for t in re.split(r"<br\s*/?>", crudo)]
        trozos = [" ".join(re.sub(r"<[^>]+>", " ", t).split()) for t in trozos if t.strip()]
        if trozos:
            salida["direccion"] = trozos[0]
        # El último trozo suele ser la comuna; solo se acepta si está en la lista
        for t in reversed(trozos[1:]):
            if plano(t) in COMUNAS:
                salida["comuna"] = COMUNAS[plano(t)]
                break

    tel = re.search(r'class="telefono"[^>]*>(.*?)</li>', html, re.S)
    if tel:
        salida["telefono"] = " ".join(re.sub(r"<[^>]+>", " ", tel.group(1)).split())

    web = re.search(r'class="web"[^>]*>\s*<a[^>]*href="([^"]+)"', html, re.S)
    if web:
        salida["sitio_web"] = web.group(1).strip()
    return salida


def url_normal(crudo: str) -> str:
    """Banco de Chile publica el sitio del local como "www.quotidien.cl".

    Sin esquema el navegador lo resuelve relativo al sitio y el link termina
    apuntando a loica.cl/www.quotidien.cl, que es un 404 con nuestra cara.
    """
    limpio = str(crudo or "").strip().strip('"\'')
    if not limpio or limpio.lower() in ("vacio", "n/a", "-"):
        return ""
    if limpio.startswith(("http://", "https://")):
        return limpio
    if limpio.startswith("//"):
        return "https:" + limpio
    if "." not in limpio.split("/")[0]:
        return ""            # no parece un dominio
    return "https://" + limpio
