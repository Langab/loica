"""Homologa el rubro entre bancos y deduce el tipo de cocina del local.

Cada banco nombra lo mismo distinto. Banco de Chile dice `restaurantes-y-bares`,
Bci dice `restaurantes`, Falabella dice `Restaurantes` y Cencosud dice `comida`.
Peor: Bci escribe `cafeteria` en singular y Banco de Chile `cafeterias` en
plural, así que el filtro de la página mostraba "Cafeterías" DOS VECES —dos
slugs distintos con la misma etiqueta— y ninguna de las dos traía todo.

Acá se define el vocabulario único y se traduce el de cada banco.

Aparte del rubro, la pregunta que de verdad se hace la gente es "¿qué como?",
no "¿en qué rubro lo clasificó el banco?". Por eso se deduce también el tipo de
cocina del nombre del local: los mismos restaurantes se repiten entre bancos, y
`Boka Sushi` es japonesa la publique Falabella bajo "Antojos" o Bci bajo
"Restaurantes".
"""

from __future__ import annotations

import re
import unicodedata

# ---------- RUBRO ----------
# El vocabulario único. Lo que la página muestra como filtro.
RUBROS = ("restaurantes", "cafeterias", "gourmet", "comida_rapida")

# De cómo lo dice cada banco a cómo lo decimos nosotros.
EQUIVALENCIAS = {
    "restaurantes": "restaurantes",
    "restaurantes-y-bares": "restaurantes",
    "restaurant": "restaurantes",
    "comida": "restaurantes",
    # No es un rubro sino una promoción de Banco de Chile, pero adentro hay
    # restaurantes de verdad (Boga, Ari Nikkei, Barrica 94). El porcentaje ya
    # viaja en su propio campo, así que como rubro es "restaurantes".
    "40-de-descuento-visa": "restaurantes",
    "cafeteria": "cafeterias",
    "cafeterias": "cafeterias",
    "cafe": "cafeterias",
    "sabores-gourmet": "gourmet",
    "gourmet-y-delicatessen": "gourmet",
    "gourmet": "gourmet",
    "delicatessen": "gourmet",
    "comida-rapida": "comida_rapida",
    "comida_rapida": "comida_rapida",
    "antojos": "comida_rapida",
    "fast-food": "comida_rapida",
}


def _norm(texto: str) -> str:
    plano = unicodedata.normalize("NFD", (texto or "").lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", plano).strip()


def homologar(categoria: str) -> str:
    """Traduce el rubro de un banco al vocabulario único.

    Si aparece uno que no conocemos se devuelve normalizado en vez de forzarlo
    a "restaurantes": un rubro nuevo tiene que verse en la página para que
    alguien lo agregue acá, no esconderse dentro del cajón más grande.
    """
    plano = _norm(categoria).replace(" ", "-")
    if not plano:
        return "restaurantes"
    # Los bancos mandan la ruta completa: "beneficios/sabores/cafeterias"
    plano = plano.split("/")[-1]
    return EQUIVALENCIAS.get(plano, plano)


# ---------- TIPO DE COCINA ----------
# Orden = prioridad: lo específico antes que lo genérico. "Sushi Blue" es
# japonesa aunque también diga "bar", y una "Pizzería Napolitana" es italiana
# aunque pizza también sea comida rápida.
PATRONES_COCINA = [
    ("japonesa", r"\b(sushi|sushie|nikkei|ramen|izakaya|teriyaki|yakiniku|sake"
                 r"|tempura|wasabi|sakura|tokyo|osaka|kyoto|niu|maki|donburi"
                 r"|japon\w*|nippon|samurai|katana|hanzo|ichiban)\b"),
    ("peruana", r"\b(ceviche|cebiche|cevicheria|peruan\w*|lima|inka|inca"
                r"|anticucho|causa|pisco sour|chifa|astrid|gaston)\b"),
    ("italiana", r"\b(pizz\w*|pasta|paste|trattoria|ristorante|osteria"
                 r"|napol\w*|italian\w*|gnocchi|risotto|focaccia|lasagna"
                 r"|spaghetti|capric\w*|bella|dolce|vitto|mamma)\b"),
    ("mexicana", r"\b(taco|tacos|taqueria|mexican\w*|burrito|cantina|guacamole"
                 r"|azteca|maya|jalapeno|nachos|tequila)\b"),
    ("parrilla", r"\b(parrilla|parrillada|grill|asado|steak|steakhouse|carnes"
                 r"|angus|wagyu|brasas|braseria|churrasq\w*)\b"),
    ("mariscos", r"\b(marisco\w*|pescado\w*|ostras|seafood|caleta|pescader\w*"
                 r"|langosta|camaron\w*|congrio|mar\b)\b"),
    ("asiatica", r"\b(wok|china|chino|thai|tailand\w*|asian|asiatic\w*|dim sum"
                 r"|pad thai|korean|coreana|kimchi|bao|noodle\w*|india|hindu"
                 r"|curry|tandoori)\b"),
    ("hamburguesas", r"\b(burger|burgers|hamburgues\w*|wendy\w*|mcdonald\w*"
                     r"|doggis|completo\w*|hot ?dog|streetburger|juicy)\b"),
    ("pollo", r"\b(pollo\w*|chick.?en|kfc|rostiser\w*|alitas|wings)\b"),
    ("vegetariana", r"\b(vegan\w*|vegetarian\w*|veggie|plant based|verde"
                    r"|ensalad\w*|salad)\b"),
    ("panaderia", r"\b(panader\w*|pasteler\w*|bakery|bread|pan\b|masas|kuchen"
                  r"|reposter\w*|dulcer\w*|heladeria|helados|gelato|postres)\b"),
    ("cafe", r"\b(cafe|cafeteria|coffee|espresso|barista|starbucks|juan valdez"
             r"|tostador\w*|te\b|tea)\b"),
    ("bar", r"\b(bar\b|pub|cerveceria|brewery|taproom|cocteler\w*|gin\b|whisky"
            r"|vinoteca|wine|bodega)\b"),
    ("chilena", r"\b(chilena|chileno|picada|empanada\w*|cazuela|pastel de choclo"
                r"|curanto|criolla|fuente de soda|schop)\b"),
]

# Nombres propios que caen en un patrón sin ser de esa cocina. "Bar Mar" no es
# de mariscos por decir "mar", y "La Pica del Wagyu" sí es parrilla.
FALSOS = {
    "mar": ("mariscos", r"\b(mar del plata|mar y sol club|bar\s?mar)\b"),
    "verde": ("vegetariana", r"\b(monte verde|valle verde|casa verde)\b"),
}


def cocina_de(comercio: str, categoria: str = "") -> str:
    """Deduce el tipo de cocina desde el nombre del local.

    Devuelve "" cuando no hay señal, no un valor inventado: en la página es
    preferible que un local no tenga tipo de cocina a que diga uno equivocado.
    El nombre es corto y curado, así que da pocos falsos positivos; la
    categoría del banco solo se usa como desempate al final.
    """
    texto = _norm(comercio)
    if not texto:
        return ""

    for cocina, patron in PATRONES_COCINA:
        if not re.search(patron, texto):
            continue
        excepcion = FALSOS.get(cocina)
        if excepcion and re.search(excepcion[1], texto):
            continue
        return cocina

    # Sin señal en el nombre, el rubro del banco alcanza para los dos casos
    # donde el rubro YA es un tipo de comida.
    rubro = homologar(categoria)
    if rubro == "cafeterias":
        return "cafe"
    if rubro == "comida_rapida":
        return "comida_rapida"
    return ""
