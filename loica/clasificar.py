# ============================================================
#  CLASIFICACIÓN — categorías y público
#  Reemplaza a CATEGORIAS/clasificar(). Ver web/_ux_filtros.md
# ============================================================
import re
import unicodedata


def _norm(texto: str) -> str:
    """Minúsculas, sin tildes, espacios colapsados. Todo se compara así."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto)


def _tiene(texto, palabras):
    """Match con límite de palabra. Sin esto, 'nino' matchea 'LEONINO'."""
    for palabra in palabras:
        if re.search(r"(?<![a-z0-9])" + re.escape(_norm(palabra)) + r"(?![a-z0-9])",
                     texto):
            return palabra
    return None


# Nombres propios que parecen otra cosa. "Niños del Cerro" es una banda y hoy
# está clasificada como categoría familia; "cerro" además la mandaba a aire_libre.
FALSOS_INFANTILES = ["ninos del cerro", "la nina de la mochila azul",
                     "pequeno circo", "los ninos rojos"]


# ---------- CATEGORÍAS ----------
# Orden = prioridad. El primero que matchea gana, así que lo específico
# ("infantil") va antes que lo genérico ("charla").
PATRONES_CATEGORIA = [
    ("idiomas", r"\b(intercambio de idiomas?|language exchange|conversation club"
                r"|club de conversacion|mundo lingo|intercambio linguistico)"),
    # Deporte va ANTES que familia a propósito: "Natación para niños" es
    # deporte (la edad ya la captura `publico`), no un panorama familiar
    # genérico. Y antes que música, porque la descripción de un taller de
    # aerobike dice "al ritmo de la música" y mandaba 18 clases de bicicleta
    # estática a conciertos.
    ("deporte", r"\b(futbol\w*|estadio nacional|estadio monumental|colo colo"
                r"|campeonato|torneo anfp|copa chile|basquet\w*|voleibol|voley"
                r"|rugby|hockey|atp|padel|maraton|corrida|running|trail"
                r"|10k|21k|42k|cicletada|ciclorecreovia|ciclismo|atletismo"
                r"|patin\w*|hipodromo|rodeo|zumba|crossfit"
                r"|acondicionamiento fisico|entrenamiento funcional"
                # Talleres municipales de actividad física. La categoría de la
                # fuente suele declararlo ("Actividad Física y Salud") aunque
                # el título sea solo "Aerobike Ma-Ju 08:30", y ese texto entra
                # junto al título en la búsqueda.
                r"|actividad fisica|habilitacion fisica|recuperacion fisica"
                r"|aerobike|aerobox|aerobic\w*|cardio ?box|cardio|fitness"
                r"|calistenia|gap|pilates|yoga|tai ?chi|gimnasia|hidrogimnasia"
                r"|natacion|matronatacion|nado|aquagym|aguas abiertas"
                r"|karate|taekwondo|judo|jiu ?jitsu|kung ?fu|boxeo|kickboxing"
                r"|muay ?thai|defensa personal|esgrima|tenis|ping ?pong"
                r"|badminton|handbol|balonmano|futsal|skate\w*|parkour"
                # "vs" a secas NO va: "JUEVES LATINO VS POP" es una fiesta.
                # Los partidos se pescan por el estadio o la disciplina.
                r"|escalada|halterofilia|powerlifting|estadio municipal"
                r"|estadio bicentenario|estadio santa laura|claro arena"
                r"|fight house|ufc|mma|clasificatorio|mountain ?bike|mtb)\b"),
    ("familia", r"\b(publico infantil|teatro infantil|infantil(es)?|para nin[oa]s"
                r"|cuenta ?cuentos|titeres|marionetas|panorama familiar"
                r"|para toda la familia|publico familiar|primera infancia|parvul)"),
    # "club" va acá y no en otro lado: NO_ES_FIESTA lo protege más abajo.
    ("feria",   r"\b(feria de disen\w*|feria artesanal|feria costumbrista"
                r"|feria navidena|feria del libro|feria vintage"
                r"|feria de emprendedor\w*|feria gastronomica|feria de las pulgas"
                r"|feria itinerante|feria de barrio|mercadillo|mercadito"
                r"|mercado de disen\w*|mercado de pulgas|mercado navideno"
                r"|persa|bazar|garage sale|segunda mano|trueque|expoventa"
                r"|otaku|anime|manga|cosplay|comic con|frikimarket|friki"
                r"|kpop|k-pop|coleccionismo|pokemon|magic the gathering)"),
    ("fiesta",  r"\b(fiesta|party|carrete|rave|after ?party|tocata|djs?\b"
                r"|club\b|discoteca|sesion(es)? electronica|reggaeton|techno"
                r"|cumbia bailable|fonda\w*|ramada\w*|fiestas patrias"
                r"|chilenidad|dieciochera)"),
    ("cine",    r"\b(cine(teca|club)?|pelicula|documental|cortometraje"
                r"|largometraje|audiovisual|proyeccion)"),
    ("teatro",  r"\b(teatr|obra|dramaturg|escenic|monologo|danza|circo"
                r"|performance|comedia|stand ?up|variete|clown)"),
    ("musica",  r"\b(concierto|recital|tributo|showcase|banda|en vivo|music"
                r"|sinfonic|orquesta|coro|cantata|unplugged|jam|gira|tour"
                r"|sonido|sound|fest\b|festival)"),
    ("arte",    r"\b(exposicion|exhibicion|muestra|galeria|artes visuales"
                r"|artes mediales|fotografi|pintura|escultura|grabado"
                r"|instalacion|vernissage|bienal|artistic)"),
    ("clases",  r"\b(taller|clase|curso|workshop|laboratorio|diplomado"
                r"|capacitacion|entrenamiento|academia|webinar|escuela de)"),
    ("aire_libre", r"\b(parque|cerro|caminata|trekking|ruta|picnic|mirador"
                   r"|humedal)"),
    ("charla",  r"\b(charla|conversatorio|seminario|coloquio|conferencia"
                r"|congreso|simposio|panel|mesa redonda|jornada"
                r"|presentacion de libro|lanzamiento|catedra|dialogo)"),
]

# "club de lectura" NO es una fiesta. Este era el bug que mandaba
# "Grupo de lectura: George Canguilhem" a la categoría fiesta.
NO_ES_FIESTA = re.compile(r"club de (lectura|conversacion|libro|cine)")

# Prior por fuente/recinto. Solo se aplica si el texto no dijo NADA.
# Precisión medida a mano sobre los 73 casos que caen acá: ~85%.
PRIOR_FUENTE = [
    # Una corporación de deportes solo publica deporte: si el título no dijo
    # nada ("Nivelación 2 Ma-Ju"), esto evita que caiga a "otros".
    (r"corporaci\w+ (municipal )?de deportes|talleres deportivos", "deporte"),
    (r"red salas de teatro|teatro (san gines|municipal|uc|finis terrae|zoco|mori)"
     r"|sala ana gonzalez", "teatro"),
    (r"toliv", "fiesta"),
    (r"portaltickets|portaldisc", "musica"),
    # Recintos que viven de conciertos: un título sin señal ahí es música.
    (r"movistar arena|teatro caupolican|club chocolate|blondie|club amanda",
     "musica"),
    (r"planetario", "familia"),
    (r"balmaceda arte joven|matucana 100|nave centro"
     r"|centro cultural la moneda|\bgam\b", "arte"),
    (r"universidad|\budp\b|\buah\b|\bunab\b|usach|finis terrae"
     r"|diego portales|alberto hurtado|andres bello", "charla"),
    (r"agenda cultural|municipalidad|ceina", "arte"),
]


def _buscar_categoria(texto):
    for categoria, patron in PATRONES_CATEGORIA:
        if categoria == "fiesta" and NO_ES_FIESTA.search(texto):
            continue
        if re.search(patron, texto):
            return categoria
    return None


def clasificar(titulo, categoria_fuente, descripcion, lugar="", fuente=""):
    """Devuelve (categoria, origen).

    origen ∈ {'titulo','descripcion','prior','defecto'} — sirve para auditar
    cuánto está adivinando el clasificador en cada corrida.
    """
    tit = _norm(f"{categoria_fuente} {titulo}")
    if _tiene(tit, FALSOS_INFANTILES):     # "Niños del Cerro" es una banda
        tit = " "

    # 1. El título manda. Es corto y curado; la descripción trae ruido.
    categoria = _buscar_categoria(tit)
    if categoria:
        return categoria, "titulo"

    # 2. Recién ahora la descripción.
    cuerpo = _norm(f"{tit} {descripcion}")
    for nombre in FALSOS_INFANTILES:
        cuerpo = cuerpo.replace(_norm(nombre), " ")
    categoria = _buscar_categoria(cuerpo)
    if categoria:
        return categoria, "descripcion"

    # 3. Prior por fuente/recinto. Es una conjetura y queda marcada como tal.
    contexto = _norm(f"{lugar} {fuente}")
    for patron, categoria in PRIOR_FUENTE:
        if re.search(patron, contexto):
            return categoria, "prior"
    return "otros", "defecto"


# ---------- PÚBLICO ----------
# Filtro INCLUSIVO: "todos" es el default y aparece tanto en "Con niños"
# como en "Adolescentes". Solo "adultos" excluye.

PALABRAS_NINOS = [
    "para ninos", "para ninas", "para los ninos", "publico infantil",
    "teatro infantil", "infantil", "infantiles", "preescolar", "preescolares",
    "parvulos", "parvularia", "jardin infantil", "primera infancia",
    "cuentacuentos", "cuenta cuentos", "titeres", "marionetas", "kamishibai",
    "matine infantil", "panorama familiar", "para toda la familia",
    "toda la familia", "publico familiar", "cuento infantil",
    "taller para ninos", "obra infantil", "musical infantil", "guaguas",
]

PALABRAS_ADOLESCENTES = [
    "adolescentes", "adolescencia", "publico juvenil", "para jovenes",
    "juvenil", "juveniles", "ensenanza media", "liceo", "liceos",
    "estudiantes secundarios", "preuniversitario", "anime", "manga",
    "kpop", "k pop", "gamer", "gamers", "videojuegos", "esports",
    "skate", "batalla de gallos", "freestyle",
]

# Señales duras de +18. Solo cosas donde a un menor NO lo dejan entrar
# o el contenido lo excluye. Nada de "adulto" suelto (matchea
# "educación de adultos", "adulto mayor").
PALABRAS_ADULTOS = [
    "+18", "18+", "mayores de 18", "solo mayores de edad", "solo adultos",
    "publico adulto", "contenido adulto", "erotico", "erotica", "burlesque",
    "drag show", "cabaret", "striptease", "afterparty", "after party",
    "carrete", "barra libre", "open bar", "cocteleria", "maridaje",
    "cata de vinos", "cata de whiskey", "degustacion de vinos",
]

# Recintos donde no entran menores. Se leen del campo `lugar`, no del texto:
# en el texto "bar" matchea "roBAR un banco".
RECINTOS_NOCTURNOS = ["bar", "pub", "club", "discoteca", "restobar",
                      "pianobar", "cerveceria", "taberna", "matadero"]

# "Evento para mayores de 21 años" — cuando aparece, es 100% confiable.
EDAD_EXPLICITA = re.compile(
    r"(?:mayores de|para mayores de|a partir de|desde los|apto desde"
    r"|recomendad[oa] (?:para|desde))\s+(?:los\s+)?(\d{1,2})\s*anos?\b")

def clasificar_publico(titulo, descripcion, categoria, lugar, fuente, hora=None):
    """Devuelve (publico, razon). publico ∈ {ninos, adolescentes, adultos, todos}.

    `hora` es la hora de inicio (int 0-23) o None si el evento no la trae.
    """
    texto = _norm(f"{titulo} {descripcion}")
    lug, fue = _norm(lugar), _norm(fuente)

    if _tiene(texto, FALSOS_INFANTILES):
        return "todos", "nombre propio en lista de excepciones"

    # 1. Edad explícita: manda sobre todo lo demás.
    m = EDAD_EXPLICITA.search(texto)
    if m:
        edad = int(m.group(1))
        etiqueta = ("adultos" if edad >= 18
                    else "adolescentes" if edad >= 13 else "ninos")
        return etiqueta, f"edad explícita en el texto: {edad}+"

    # 2. Palabra dura de +18.
    palabra = _tiene(texto, PALABRAS_ADULTOS)
    if palabra:
        return "adultos", f"palabra +18: {palabra}"

    # 3. Recinto nocturno. Nunca solo: pide una segunda señal (categoría
    #    fiesta, hora >= 21, o fuente de vida nocturna). Con el recinto solo
    #    marcábamos "Punta Arenas vs Colo Colo" como +18.
    recinto = _tiene(lug, RECINTOS_NOCTURNOS)
    tarde = hora is not None and hora >= 21
    if recinto and not NO_ES_FIESTA.search(texto):
        if categoria == "fiesta" or tarde or "toliv" in fue:
            return "adultos", f"recinto nocturno ({recinto}) + segunda señal"
    if categoria == "fiesta" and (tarde or "toliv" in fue):
        return "adultos", "fiesta nocturna"

    # 4. Infantil.
    palabra = _tiene(texto, PALABRAS_NINOS)
    if palabra:
        return "ninos", f"palabra infantil: {palabra}"

    # 5. Adolescente.
    palabra = _tiene(texto, PALABRAS_ADOLESCENTES)
    if palabra:
        return "adolescentes", f"palabra juvenil: {palabra}"

    return "todos", "sin señal — se asume apto para todo público"
