# ============================================================
#  CLASIFICACIÓN — categorías y público
#  Reemplaza a CATEGORIAS/clasificar(). Ver web/_ux_filtros.md
# ============================================================
# El `from __future__` no es decorativo: el runner de la corrida usa Python
# 3.11 pero el Mac trae el 3.9 de las Command Line Tools, y ahí un
# `X | None` en una anotación de módulo revienta al importar.
from __future__ import annotations

import re
import unicodedata

from .correcciones import MemoriaCategorias


def _norm(texto: str) -> str:
    """Minúsculas, sin tildes, espacios colapsados. Todo se compara así."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto)


# ---------- LA MEMORIA ----------
# config/correcciones/categorias.yaml: palabras en contexto → categoría, escritas
# por la revisión y no por el código. Se consulta ANTES que los patrones de
# abajo, porque es lo curado: cuando la auditoría encontró que "maratón" al
# lado de "película" es cine, eso vale más que el patrón genérico de deporte.
# Los patrones del código siguen siendo la base —la memoria parte vacía y el
# clasificador funciona igual—; la memoria es la capa que aprende sin tocar
# código. Si una regla de la memoria se repite mucho o pide lógica (un orden,
# una excepción de recinto), ahí sí se baja al código.
#
# Se carga una vez por proceso y perezosamente: los scripts que solo importan
# `es_taller` o `clasificar_escala` no leen el YAML.
_MEMORIA: MemoriaCategorias | None = None


def memoria() -> MemoriaCategorias:
    global _MEMORIA
    if _MEMORIA is None:
        _MEMORIA = MemoriaCategorias()
    return _MEMORIA


def usar_memoria(nueva: MemoriaCategorias | None) -> None:
    """Cambia la memoria en uso (la auditoría clasifica con y sin ella)."""
    global _MEMORIA
    _MEMORIA = nueva


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

# En un museo de arte, "obra" es una pieza colgada en la pared; en cualquier
# otra parte es una función de teatro. El clasificador leía el título antes que
# el recinto, así que "Obras extraordinarias" del MAC salía como teatro. Se
# neutraliza la palabra SOLO cuando el recinto es un museo de arte: es una
# desambiguación de sentido, no una excepción para una fuente.
MUSEOS_DE_ARTE = re.compile(
    r"museo de arte|museo nacional de bellas artes|museo de artes visuales"
    r"|\bmavi\b|\bmac (quinta normal|parque forestal)\b|precolombino")
SENTIDO_DE_OBRA = re.compile(r"\bobras?\b")

# "Obra" dentro de una frase hecha que no tiene nada que ver con el teatro.
# La banda se llama MANO DE OBRA y su fecha en la Sala RBX salía como una
# función de teatro; "obras extraordinarias" ya tenía su guarda para los
# museos, pero esto pasa en cualquier parte y por eso se limpia siempre.
FRASES_CON_OBRA = re.compile(
    r"\bmano de obra\b|\bobras? (publicas?|viales?|sanitarias?|de mejoramiento)\b"
    r"|\bobra gruesa\b|\bmaestro de obra\b|\bvida y obra\b|\bla obra de\b")


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
    # El nombre de un estadio dice DÓNDE, no QUÉ, y por eso ya no está en esta
    # lista. Estaba —"estadio nacional", "estadio monumental", "claro arena"—
    # y mandaba a deporte los cuatro conciertos más grandes del catastro:
    # Karol G en el Nacional, Maná en el Monumental, Jamiroquai en el Claro
    # Arena y Gondwana en el Bicentenario. El Movistar Arena nunca estuvo acá
    # y por eso sus quince conciertos siempre estuvieron bien: el recinto se
    # resuelve en PRIOR_FUENTE, que es la capa que opina cuando el texto calló.
    # Los partidos que se publican solo con el nombre de los equipos los pesca
    # PARTIDO, más abajo.
    ("deporte", r"\b(futbol\w*|colo colo"
                r"|campeonato|torneo anfp|copa chile|basquet\w*|voleibol|voley"
                r"|rugby|hockey|atp|padel|maraton|corrida|running|trail"
                r"|10k|21k|42k|cicletada|ciclorecreovia|ciclismo|atletismo"
                # "Deportes" en plural es la categoría con que Passline etiqueta
                # las veladas de boxeo y las liguillas de barrio, y ese texto
                # entra junto al título. En SINGULAR no va: "deporte" es la
                # categoría de las municipalidades y arrastraba "Motricidad
                # Infantil" (familia) y "Senderismo" (aire libre) con ella.
                r"|deportes|liguilla"
                # `hipodromo` estaba acá y era un bug: los tres eventos del
                # Hipódromo Chile en el catastro son conciertos —Santiago
                # Rocks, A Perfect Circle, Primavera Fest— y ninguno una
                # carrera. El recinto ahora vive en PRIOR_FUENTE, donde solo
                # opina cuando el título no dijo nada.
                r"|patin\w*|rodeo|zumba|crossfit"
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
                # Los partidos se pescan por la disciplina, por el nombre del
                # club, o por PARTIDO cuando el título no trae ninguno.
                r"|escalada|halterofilia|powerlifting"
                r"|fight house|ufc|mma|clasificatorio|mountain ?bike|mtb)\b"),
    ("familia", r"\b(publico infantil|teatro infantil|infantil(es)?|para nin[oa]s"
                r"|cuenta ?cuentos|titeres|marionetas|panorama familiar"
                # "Magia Sobre Hielo Melipilla" no dice en ninguna parte que sea
                # para niños, pero un show sobre patines es exactamente eso.
                r"|sobre hielo|on ice"
                r"|para toda la familia|publico familiar|primera infancia|parvul)"),
    # "club" va acá y no en otro lado: NO_ES_FIESTA lo protege más abajo.
    ("feria",   r"\b(feria de disen\w*|feria artesanal|feria costumbrista"
                r"|feria navidena|feria del libro|feria vintage"
                r"|feria de emprendedor\w*|feria gastronomica|feria de las pulgas"
                r"|feria itinerante|feria de barrio|mercadillo|mercadito"
                r"|mercado de disen\w*|mercado de pulgas|mercado navideno"
                r"|persa|bazar|garage sale|segunda mano|trueque|expoventa"
                r"|otaku|anime|manga|cosplay|comic con|frikimarket|friki"
                # "Expo" a secas es en Chile una feria de rubro —Expo Renta
                # Corta, Expo Tuning Buin, Expo Vizcachas Racing—, no una
                # muestra de arte. No colisiona con "exposición": el límite
                # de palabra las separa.
                r"|\bexpo\b|feriafriki"
                # Los torneos de cartas llenan un centro cultural entero y
                # caían en "otros": el One Piece Card Game y el mundial de
                # TAAT son ferias de comunidad, no campeonatos deportivos.
                # Va "world championship" y no "championship" a secas para no
                # robarle a deporte un mundial de verdad.
                r"|card game|trading card|world championship|\btcg\b"
                # Una batalla de tatuadores es una convención con stands.
                r"|tattoo|tatuaje"
                # La "3D Printer Party" es una convención de makers con puestos
                # y abono de dos días. Se llamaba fiesta por decir "party" y
                # cuatro entradas de una feria de impresión 3D aparecían en el
                # filtro de los carretes.
                r"|3d printer|impresion 3d"
                r"|kpop|k-pop|coleccionismo|pokemon|magic the gathering)"),
    # "tocata" NO va acá y estuvo: una tocata es un grupo tocando en vivo, o
    # sea música, y la palabra mandaba a fiesta desde "Tocata Jamás" hasta
    # "Floresalegría + Gomitas Ácidas: una tocata documental". Que sea de
    # noche y en un bar no la convierte en carrete; la fiesta es la que pone
    # un DJ. Vive ahora en el patrón de música, donde siempre debió estar.
    ("fiesta",  r"\b(fiesta|party|carrete|rave|after ?party|djs?\b"
                r"|club\b|discoteca|sesion(es)? electronica|reggaeton|techno"
                # "Sunset" es un formato de carrete, no un atardecer: los
                # Sunset Andes Winter de El Colorado y el Sky Sunset de la
                # Costanera son tardeo con DJ.
                r"|sunset|baile do|baile funk|line ?up"
                # Las noches con fecha propia. "The Vibe - Año Nuevo 2027" y
                # "Open Blondie: Noche de Brujas" no dicen fiesta en ninguna
                # parte, y "hallowe+n" lleva la e de más porque la fuente
                # escribió "Circdomingo HALLOWEN".
                r"|hallowe+n|noche de brujas|ano nuevo"
                r"|cumbia bailable|fonda\w*|ramada\w*|fiestas patrias"
                # La Cumbre Guachaca es la fonda grande de agosto: cueca,
                # cumbia y vino en jarro. Va con chilenidad, no en "otros".
                r"|chilenidad|dieciochera|guachaca)"),
    ("cine",    r"\b(cine(teca|club)?|pelicula|documental|cortometraje"
                r"|largometraje|audiovisual|proyeccion)"),
    ("teatro",  r"\b(teatr|obra|dramaturg|escenic|monologo|danza|circo"
                # "Cirque" del Soleil no es "circo", y "comedy" tampoco es
                # "comedia": dos shows por temporada quedaban en "otros" por
                # estar escritos en otro idioma.
                r"|cirque|comedy|humor"
                # "Probar el quesito" es como los comediantes chilenos llaman
                # a estrenar material en un bar. Tres funciones de Demian The
                # Rat en el Palermo caían en "otros" por eso.
                r"|quesito|micro(fono)? abierto|open mic|impro\b|improvisad"
                r"|performance|comedia|stand ?up|variete|clown)"),
    ("musica",  r"\b(concierto|recital|tributo|showcase|banda|en vivo|music"
                r"|tocata|tocatas"
                r"|sinfonic|orquesta|coro|cantata|unplugged|jam|gira|tour"
                # Los géneros. Passline publica el nombre de la banda y nada
                # más —"Hellripper", "Old Mans Child"— pero cuando el género
                # aparece en el título es la señal más limpia que hay, y
                # "David Bowie Starman Tribute" se perdía por estar en inglés.
                r"|rock|metal|punk|hardcore|blues|reggae|\brap\b|hip ?hop"
                r"|cumbia|sonora|salsa|bolero|ranchera|cueca|folclor|folklor"
                # "Homenaje A" y no "homenaje" pelado: la obra «Infinita» se
                # describe como "un homenaje visual a Gabriela Mistral" y se
                # iba de teatro a música por esa palabra suelta.
                r"|tribute|homenaje a"
                # Formaciones. Passline titula "Cuarteto de Nos" y nada más;
                # la palabra que delata que es una banda es el formato.
                r"|cuarteto|quinteto|sexteto|\btrio\b|big ?band"
                r"|sonido|sound|fest\b|festival)"),
    ("arte",    r"\b(exposicion|exhibicion|muestra|galeria|artes visuales"
                r"|artes mediales|fotografi|pintura|escultura|grabado"
                r"|instalacion|vernissage|bienal|artistic)"),
    ("clases",  r"\b(taller|clase|curso|workshop|laboratorio|diplomado"
                # "Masterclass de Stop Motion" es una clase, no una charla:
                # con la palabra en inglés no matcheaba ninguna de las dos.
                r"|masterclass|master class"
                r"|capacitacion|entrenamiento|academia|webinar|escuela de)"),
    # "ruta" a secas no va: los seminarios hablan de "rutas del narcotráfico"
    # y "rutas y puertos", y quedaban clasificados como panorama al aire libre.
    # Las rutas que sí lo son vienen acompañadas.
    ("aire_libre", r"\b(parque|cerro|caminata|trekking|picnic|mirador|humedal"
                   r"|ruta (patrimonial|escenica|del vino|de senderismo)"
                   r"|senderismo|excursion)"),
    ("charla",  r"\b(charla|conversatorio|seminario|coloquio|conferencia"
                r"|congreso|simposio|panel|mesa redonda|jornada"
                # "Cómo emprender y no morir en el intento" es una charla en
                # un restobar; ni el formato ni el recinto lo decían. Va la
                # frase completa y no "emprend": la obra «Infinita» dice
                # "Gabriela emprende su última travesía" y se iba a charla.
                r"|como emprender|emprendimiento|emprendedor|networking"
                r"|presentacion de libro|lanzamiento|catedra|dialogo)"),
]

# "club de lectura" NO es una fiesta. Este era el bug que mandaba
# "Grupo de lectura: George Canguilhem" a la categoría fiesta.
NO_ES_FIESTA = re.compile(r"club de (lectura|conversacion|libro|cine)")

# Un partido publicado solo con los nombres de los equipos. "Universidad
# Católica vs. Estudiantes de La Plata en Claro Arena" no trae ni una palabra
# de fútbol, y sacar los estadios del patrón de deporte lo dejaba sin señal.
#
# La regla es COMPUESTA a propósito, y ahí está toda la gracia: "vs" solo no
# sirve —"JUEVES LATINO VS POP" es una fiesta y "La gran Magia Tropical vs
# Forest" es una cumbia—, y el nombre de un recinto solo tampoco —Karol G
# canta en el Estadio Nacional—. Las dos cosas juntas y en la misma frase (60
# caracteres, sin saltar de línea) sí: nadie titula así una fiesta.
PARTIDO = re.compile(
    r"\bvs\b\.?.{0,60}?\b(estadio|arena|coliseo|gimnasio|polideportivo|cancha)\b"
    r"|\b(estadio|arena|coliseo|gimnasio|polideportivo|cancha)\b.{0,60}?\bvs\b")

# Un taller de pintura es una CLASE, no una exposición. El patrón de arte
# nombra los medios (pintura, grabado, escultura, fotografía) y va antes que
# el de clases, así que "Taller de pintura al óleo" caía en arte mientras
# "Taller de cerámica" caía en clases: el mismo taller en dos animales
# distintos según el oficio que enseñe. Cuando el título dice que se aprende
# algo, eso manda sobre el medio.
#
# Vale igual para música desde que el patrón nombra géneros: los nueve
# "TALLER GENERAL — SALSA FOOTWORK ON2" del congreso Dare Dance y las
# "Clases de Cueca" de la UNAB se iban a conciertos por decir el baile que
# enseñan.
SE_APRENDE = re.compile(
    r"\b(taller(es)?|curso|clase|clases|workshop|aprende|iniciacion"
    r"|nivel (inicial|basico|intermedio|avanzado)|para principiantes"
    r"|escuela de|academia|capacitacion|diplomado)\b")

# Prior por fuente/recinto. Solo se aplica si el texto no dijo NADA.
# Precisión medida a mano sobre los 73 casos que caen acá: ~85%.
PRIOR_FUENTE = [
    # Una corporación de deportes solo publica deporte: si el título no dijo
    # nada ("Nivelación 2 Ma-Ju"), esto evita que caiga a "otros".
    # `\bestadio\b` NO va acá aunque suene obvio: en el catastro los estadios
    # grandes reparten mitad y mitad —cinco partidos y cuatro conciertos—, así
    # que como prior es una moneda al aire, y las veces que acertaba el texto
    # ya lo había resuelto igual ("liguilla", "Deportes", "Colo-Colo").
    # Polideportivo y complejo deportivo sí: ahí no se hacen conciertos.
    (r"corporaci\w+ (municipal )?de deportes|talleres deportivos"
     r"|polideportivo|complejo deportivo", "deporte"),
    # Sala K es la cartelera de cine de Maipú, pero arrienda una sala DENTRO
    # del campus de la Universidad Mayor, así que el prior de universidades le
    # ganaba y mandaba 13 películas —Robocop, Blood Simple, La Cosa— a charla.
    # Va antes que ese prior a propósito.
    (r"sala k\b|centro arte alameda|cine arte normandie|cineteca", "cine"),
    (r"red salas de teatro|teatro (san gines|municipal|uc|finis terrae|zoco|mori"
     r"|alicia|cau?si[nñ]o|cousino|camilo henriquez|ex mundo magico)"
     # "Teatro Fiebre" NO va en esta lista aunque se llame teatro: de sus 13
     # eventos, 3 son conciertos y 4 exposiciones, y meterlo acá le robaba
     # "PABLO HERRERA ÍNTIMO DE INVIERNO EN FIEBRE BAR" a música.
     r"|municipal de santiago|palermo teatro|teatro palermo|\bcirco\b"
     r"|sala ana gonzalez", "teatro"),
    (r"toliv"
     # Discotecas y clubes de carrete. Sus títulos son puro nombre de noche
     # —"VIERNES SÚPER ILLU", "Papi", "ÁNIMA SABADO 22 AGOSTO"— y ninguno dice
     # que sea una fiesta. El centro de ski entra acá por los Sunset Andes.
     r"|illuminati|hangar bellavista|\bbardot\b|\bclimax\b|spot secreto"
     r"|terraza arrayan|cabaret pirana|centro de ski|el colorado", "fiesta"),
    # Las ticketeras. Puntoticket se llama a sí misma "deportes, musica y
    # familia" y es cierto, pero lo que le queda SIN clasificar después del
    # texto es siempre lo mismo: el show grande en un recinto grande. Sus
    # partidos ya los agarró PARTIDO y sus obras dicen "teatro" en el título.
    (r"portaltickets|portaldisc|puntoticket", "musica"),
    # Recintos que viven de conciertos: un título sin señal ahí es música.
    # Las salas del circuito under se agregaron midiendo el catastro: en Sala
    # RBX 34 de 42 eventos ya eran música, en Metrónomo 23 de 30 y en el
    # Cariola 14 de 24. Lo que quedaba en "otros" era el nombre pelado de una
    # banda de metal —"Hellripper", "Old Mans Child", "The Haunted"—, que es
    # justo lo que el prior tiene que resolver. El Hipódromo Chile va acá y no
    # en deporte: sus tres eventos del catastro son festivales.
    (r"movistar arena|teatro caupolican|club chocolate|blondie|club amanda"
     r"|sala rbx|sala metrono|teatro cariola|bar oxido|ruta 78"
     r"|peluqueria francesa|discoteca la fama|club subterraneo"
     r"|chancho con chaleco|hipodromo|espacio riesco", "musica"),
    # Mercados y estaciones que arriendan el galpón: lo que pasa ahí es un
    # encuentro con stands —Pan Comido junta 50 panaderías, Puro Pisco 30
    # pisqueras— aunque el título solo diga un nombre de fantasía.
    (r"mercado urbano tobalaba|\bmut\b|estacion mapocho|feria friki", "feria"),
    (r"planetario", "familia"),
    (r"balmaceda arte joven|matucana 100|nave centro"
     r"|centro cultural la moneda|\bgam\b"
     # El MAC titula sus muestras como se titula el arte contemporáneo —"RAMA
     # TORCIDA", "POÉTICA DE LAS AGUAS", "De la luz a los datos"— y ninguna de
     # esas palabras dice qué es. Nueve de sus exposiciones caían en "otros".
     # Los museos del Patrimonio no necesitan estar acá: su API declara
     # field_tipo_evento ("exposicion"), y el MAC no tiene ese campo porque su
     # cartelera se lee del HTML. Se escribe el nombre entero y no "mac" a
     # secas: tres letras sueltas le pegan a "hamaca" y a "estomacal".
     r"|museo de arte contemporaneo|\bmac (quinta normal|parque forestal)\b", "arte"),
    (r"universidad|\budp\b|\buah\b|\bunab\b|usach|finis terrae"
     r"|diego portales|alberto hurtado|andres bello", "charla"),
    # Los centros de estudio publican el TEMA como título —"Territorios sin
    # control", "Rutas y puertos"— y nunca el formato, así que 29 de los 42
    # seminarios del CEP caían en "otros". Lo que hacen es siempre lo mismo:
    # seminarios, conversatorios y lanzamientos de libro abiertos al público.
    (r"centro de estudios|estudios publicos|\bcep\b|libertad y desarrollo"
     r"|cieplan|espacio publico|fundacion sol|horizontal|chile 21"
     r"|instituto de estudios|think tank|politicas publicas", "charla"),
    (r"agenda cultural|municipalidad|ceina", "arte"),
]


# Etiquetas de fuente que no dicen nada. La etiqueta de la fuente se pega
# delante del título y entra a la búsqueda como si fuera texto del evento, y
# eso es bueno cuando la etiqueta es honesta ("Actividad Física y Salud",
# "Cine"). Pero "Exposiciones y Conferencias" es el cajón de sastre de
# Passline: la auditoría del 22-08-2026 encontró que 11 de los 12 eventos con
# esa etiqueta no eran exposiciones —un perreo en Club Berlín, un congreso
# veterinario, una expo de yoga— y la palabra "exposiciones" los mandaba a
# arte a todos. Se borra la etiqueta y decide el título; si el título calla,
# el recinto.
ETIQUETAS_RUIDO = {"exposiciones y conferencias", "otro", "otros",
                   "evento-especial", "evento especial"}


def _etiqueta_util(categoria_fuente: str) -> str:
    return "" if _norm(categoria_fuente).strip() in ETIQUETAS_RUIDO else categoria_fuente


# El nombre del recinto suele venir DENTRO del título, y ahí no dice qué es el
# evento sino dónde pasa: "ORQUESTA USACH ... EN TEATRO AULA MAGNA USACH" es un
# concierto, "BLACKDALI ★ VIERNES 16 OCTUBRE ★ Club Subterráneo" es una banda.
# El clasificador leía esas dos palabras —"teatro", "club"— como si fueran el
# formato del evento y mandaba conciertos a teatro y a fiesta. Se borran del
# título antes de buscar: el recinto ya tiene su propia capa (el prior), que
# opina después y solo si el texto calló.
#
# Se borra el LUGAR declarado y también las formas "en el Teatro X" / "en Sala
# Y" que aparecen aunque el campo `lugar` diga otra cosa (PortalTickets pone su
# propio nombre ahí y deja el recinto en el título).
_TIPOS_DE_RECINTO = (r"teatro|sala|club|centro cultural|centro de eventos|gimnasio"
                     r"|estadio|arena|auditorio|anfiteatro|casona|galpon|bar")
_RECINTO_EN_TITULO = re.compile(
    rf"\ben (el |la |los |las )?({_TIPOS_DE_RECINTO})\b[^,.\-–—|]*", re.IGNORECASE)


def _sin_nombre_del_lugar(titulo_plano: str, lugar: str) -> str:
    """Saca del título el nombre del recinto, que dice dónde y no qué."""
    lug = _norm(lugar).strip()
    if len(lug) >= 6:
        # El campo `lugar` a veces trae la dirección pegada ("Club Hell Bar
        # Rojas Magallanes 51"): se prueba también con las primeras palabras.
        palabras = lug.split()
        for corte in range(len(palabras), 1, -1):
            trozo = " ".join(palabras[:corte])
            if len(trozo) >= 6 and trozo in titulo_plano:
                titulo_plano = titulo_plano.replace(trozo, " ")
                break
    return _RECINTO_EN_TITULO.sub(" ", titulo_plano)


def _titulo_para_clasificar(titulo, categoria_fuente, lugar, fuente) -> str:
    """El título normalizado y limpio de lo que no habla del evento."""
    tit = _norm(f"{_etiqueta_util(categoria_fuente)} {titulo}")
    if _tiene(tit, FALSOS_INFANTILES):     # "Niños del Cerro" es una banda
        return " "
    tit = FRASES_CON_OBRA.sub(" ", tit)    # "MANO DE OBRA" es una banda
    # "Obras extraordinarias" en el MAC es una muestra, no una función.
    if MUSEOS_DE_ARTE.search(_norm(f"{lugar} {fuente}")):
        tit = SENTIDO_DE_OBRA.sub(" ", tit)
    return _sin_nombre_del_lugar(tit, lugar)


def _buscar_categoria(texto):
    for categoria, patron in PATRONES_CATEGORIA:
        # Va en el lugar de deporte en la lista, no antes: si el título ya dijo
        # que es una fonda o una obra, eso manda sobre un "vs" cualquiera.
        if categoria == "deporte" and PARTIDO.search(texto):
            return "deporte"
        if categoria == "fiesta" and NO_ES_FIESTA.search(texto):
            continue
        # El medio no define la categoría cuando el título dice que se enseña:
        # "Taller de grabado" es clases, "Bienal de grabado" es arte; y
        # "Taller de cueca" es clases, "Peña con cuecas" es música. Teatro y
        # cine entraron el 22-08-2026: "Taller de Impro" y "Taller de Clown"
        # salían como funciones por "impro" y "clown". Deporte NO entra: una
        # clase de natación es deporte por regla de la casa.
        if categoria in ("arte", "musica", "teatro", "cine") and SE_APRENDE.search(texto):
            continue
        if re.search(patron, texto):
            return categoria
    return None


def clasificar(titulo, categoria_fuente, descripcion, lugar="", fuente="",
               con_memoria=True):
    """Devuelve (categoria, origen).

    origen ∈ {'memoria','titulo','descripcion','prior','defecto'} — sirve para
    auditar cuánto está adivinando el clasificador en cada corrida. 'memoria'
    es una regla de categorias.yaml leída en el texto; una regla de recinto de
    la memoria sale como 'prior', porque eso es: una conjeta por el lugar,
    solo que curada.

    `con_memoria=False` clasifica solo con los patrones del código; lo usa la
    auditoría para medir qué cambia cada regla.
    """
    tit = _titulo_para_clasificar(titulo, categoria_fuente, lugar, fuente)
    cuerpo = _norm(f"{tit} {descripcion}")
    for nombre in FALSOS_INFANTILES:
        cuerpo = cuerpo.replace(_norm(nombre), " ")
    mem = memoria() if con_memoria else None

    # 0. La memoria curada, primero sobre el título y después sobre el texto
    #    completo. Va antes que los patrones del código a propósito: es lo que
    #    alguien ya revisó, y si contradice a un patrón es porque el patrón se
    #    equivocaba en ese contexto.
    if mem:
        calce = mem.buscar(tit, "titulo") or mem.buscar(cuerpo, "texto")
        if calce:
            return calce[0].categoria, "memoria"

    # 1. El título manda. Es corto y curado; la descripción trae ruido.
    #    Primero el título PELADO y recién después con la etiqueta de la
    #    fuente pegada adelante: la etiqueta es lo que el organizador eligió
    #    de un menú, y en Ticketplus "Teatro y Musicales" viste a "Concierto
    #    Orquesta Toki Rapa Nui" y a "Tributo BTS". Como el patrón de teatro
    #    va antes que el de música, la etiqueta le ganaba al título. Ahora la
    #    etiqueta solo opina cuando el título no dijo nada.
    titulo_pelado = _titulo_para_clasificar(titulo, "", lugar, fuente)
    if tit.strip():
        categoria = _buscar_categoria(titulo_pelado)
        if categoria:
            return categoria, "titulo"
        categoria = _buscar_categoria(tit)
        if categoria:
            return categoria, "etiqueta"

    # 2. Recién ahora la descripción.
    categoria = _buscar_categoria(cuerpo)
    if categoria:
        return categoria, "descripcion"

    # 3. Prior por fuente/recinto. Es una conjetura y queda marcada como tal.
    #    Primero el de la memoria (un recinto que la revisión ya caracterizó),
    #    después el del código.
    contexto = _norm(f"{lugar} {fuente}")
    if mem:
        calce = mem.buscar(contexto, "lugar")
        if calce:
            return calce[0].categoria, "prior"
    for patron, categoria in PRIOR_FUENTE:
        if re.search(patron, contexto):
            return categoria, "prior"
    return "otros", "defecto"


def explicar(titulo, categoria_fuente, descripcion, lugar="", fuente=""):
    """Qué dijo cada capa sobre un evento. Para la auditoría, no para el export.

    Devuelve una lista de (capa, categoria, detalle) en el orden en que
    `clasificar` las consulta; la primera con categoría es la que manda.
    """
    tit = _titulo_para_clasificar(titulo, categoria_fuente, lugar, fuente)
    cuerpo = _norm(f"{tit} {descripcion}")
    contexto = _norm(f"{lugar} {fuente}")
    mem = memoria()
    pasos = []
    for nombre, texto in (("memoria:titulo", tit), ("memoria:texto", cuerpo)):
        calce = mem.buscar(texto, nombre.split(":")[1])
        pasos.append((nombre, calce[0].categoria if calce else "",
                      f"{calce[0].nombre} ← «{calce[1]}»" if calce else ""))
    for nombre, texto in (("codigo:titulo", tit), ("codigo:descripcion", cuerpo)):
        cat = _buscar_categoria(texto)
        palabra = ""
        if cat:
            if cat == "deporte" and PARTIDO.search(texto):
                palabra = "PARTIDO"
            else:
                m = next((re.search(p, texto) for c, p in PATRONES_CATEGORIA
                          if c == cat and re.search(p, texto)), None)
                palabra = m.group(0) if m else ""
        pasos.append((nombre, cat or "", f"«{palabra}»" if palabra else ""))
    calce = mem.buscar(contexto, "lugar")
    pasos.append(("memoria:lugar", calce[0].categoria if calce else "",
                  f"{calce[0].nombre} ← «{calce[1]}»" if calce else ""))
    prior = next(((c, p) for p, c in PRIOR_FUENTE if re.search(p, contexto)), None)
    pasos.append(("codigo:prior", prior[0] if prior else "",
                  prior[1][:50] if prior else ""))
    return pasos


# ---------- SUBCATEGORÍA ----------
# El segundo nivel: qué clase de fiesta, de obra o de taller es. Vive dentro de
# una categoría —la misma palabra "danza" es una compañía en teatro y una clase
# de baile entretenido en deporte—, así que cada categoría trae su propia lista
# y ninguna se consulta fuera de la suya.
#
# Cada lista va en orden de prioridad y lo específico manda: "tributo" antes
# que "rock" porque un tributo a AC/DC es las dos cosas y el dueño pidió
# distinguir los tributos; "metal" antes que "rock" porque el metal es rock;
# "aerobike" antes que "ciclismo" porque una bicicleta estática no es salir a
# pedalear —ese error ya mandó 18 clases a la categoría equivocada una vez—.
#
# Devolver "" es una respuesta legítima y frecuente: una fonda no es ninguno de
# los géneros de fiesta y "Fleabag" no dice si es comedia o drama. Mejor vacío
# que inventado; el dueño encontró un "aerobike" clasificado en Música y con
# razón lo consideró inaceptable.
SUBCATEGORIAS = {
    "fiesta": [
        ("reggaeton", ["reggaeton", "reguetón", "reguetonero", "perreo",
                       "perreito", "dembow"]),
        # El urbano va antes que el pop: "TRAP CITY" es trap, no una noche pop.
        ("urbano", ["trap", "hip hop", "hiphop", "rap", "freestyle", "urbano",
                    "batalla de gallos", "gallos", "drill"]),
        ("brasilera", ["funk carioca", "baile funk", "baile do", "samba",
                       "pagode", "forro", "brasil", "brasilera", "brasilero",
                       "brazil", "favela"]),
        ("cumbia", ["cumbia", "cumbias", "guaracha", "sonora", "chicha",
                    "cumbianchera", "tropical"]),
        # "Ultrabailable" es una palabra de la casa: así se anuncian en Chile
        # las noches de mezcla tropical y reggaetón, y el Club Subterráneo la
        # usa en el título de sus tres fiestas semanales.
        ("latina", ["salsa", "bachata", "merengue", "timba", "son cubano",
                    "latino", "latina", "afrocaribe", "parranda", "mambo",
                    "rumba", "reggaetonero", "ultrabailable"]),
        # Las fondas son el bloque más grande de la categoría —una de cada
        # ocho fiestas del catastro— y no eran ninguno de los géneros que pidió
        # el dueño. Pero una fonda tiene género y es este: cueca, tonada y
        # cumbia chilena. Va después de cumbia para que "Fiebre de Cumbia la
        # Fonda", que lo dice en el título, se quede con lo que dice.
        ("folclor", ["fonda", "fondas", "ramada", "ramadas", "fiestas patrias",
                     "dieciochera", "dieciochero", "chilenidad", "guachaca",
                     "cueca", "cuecas", "pena", "folclor", "folclorica",
                     "payador", "criolla"]),
        # Las noches ochenteras se anuncian por la década, no por el género:
        # "FIESTA FOREVER 80' 90'", "La Gran Fiesta 80s 90s", "Roxbury".
        ("ochentera", ["80", "80s", "80's", "90", "90s", "90's", "2000",
                       "ochentera", "ochenteros", "noventera", "noventeros",
                       "retro", "disco", "clasicos", "classics", "old school"]),
        ("electronica", ["techno", "technobus", "house", "tech house",
                         "deep house", "trance", "rave", "electronica",
                         "electronic", "edm", "progressive", "hardtechno",
                         "creamfields", "afterhours"]),
        ("rock", ["rock", "rockers", "indie", "punk", "metal", "grunge",
                  "hardcore", "britpop"]),
        ("pop", ["pop", "hits", "hitz", "kpop", "k pop", "mtv"]),
    ],
    "teatro": [
        ("circo", ["circo", "circense", "cirque", "circdomingo", "malabar",
                   "malabarismo", "acrobacia", "trapecio", "payaso", "payasos",
                   "clown"]),
        ("danza", ["danza", "danzas", "ballet", "coreografia", "coreografias",
                   "coreografico", "coreograficos", "bailarines", "flamenco",
                   "folclore", "folklore", "tap", "breaking"]),
        ("comedia", ["comedia", "comedy", "stand up", "standup", "stand-up",
                     "humor", "humorista", "improvisacion", "improvisadas",
                     "impro", "risa", "reir", "quesito", "monologo"]),
        # Cabaret, drag y kiki ball son formatos de performance, no obras de
        # sala: el "TECITO CON PIERNAS KIKI BALL" no tiene libreto.
        ("performance", ["performance", "perfomance", "cabaret", "drag",
                         "dragfest", "kiki ball", "vogue", "burlesque",
                         "instalacion escenica", "apertura de proceso"]),
        ("obra", ["obra", "obras", "montaje", "dramaturgia", "teatral",
                  "puesta en escena", "pieza teatral", "unipersonal",
                  "tragedia", "comedia dramatica", "sitcom"]),
    ],
    "clases": [
        ("idiomas", ["ingles", "frances", "aleman", "portugues", "italiano",
                     "chino", "mandarin", "japones", "coreano", "idioma",
                     "idiomas", "lengua de senas", "lsch", "conversacion"]),
        ("cocina", ["cocina", "cocteleria", "coctel", "reposteria",
                    "pasteleria", "panaderia", "barista", "sushi", "vino",
                    "vinos", "cata", "degustacion", "gastronomia",
                    "gastronomica", "chocolateria", "cerveza"]),
        ("bienestar", ["yoga", "meditacion", "mindfulness", "respiracion",
                       "reiki", "autocuidado", "bienestar", "aromaterapia",
                       "constelaciones"]),
        ("escritura", ["escritura", "narrativa", "poesia", "cuento", "guion",
                       "literaria", "literario", "creacion literaria",
                       "cronica", "periodismo"]),
        ("tecnologia", ["programacion", "python", "javascript", "robotica",
                        "impresion 3d", "inteligencia artificial", "excel",
                        "computacion", "digital", "ciberseguridad", "datos",
                        "web"]),
        # "arte" a secas NO va: "taller de arte marcial" cae en la lista y un
        # jiu-jitsu terminaba en artes visuales.
        ("artes_visuales", ["pintura", "dibujo", "grabado", "fotografia",
                            "acuarela", "oleo", "ilustracion", "comic",
                            "stop motion", "animacion", "serigrafia", "mural",
                            "muralismo", "artes visuales", "historia del arte",
                            "arte contemporaneo", "collage", "escultura"]),
        ("manualidades", ["ceramica", "telar", "mimbre", "tejido", "tejer",
                          "orfebreria", "cesteria", "macrame", "bordado",
                          "costura", "joyeria", "origami", "encuadernacion",
                          "velas", "jabones", "perfumeria", "manualidades"]),
        # Danza ANTES que música: Passline etiqueta los talleres del congreso
        # Dare Dance con su categoría "Música", y ese texto viaja pegado al
        # título, así que un "TALLER GENERAL – BACHATA FLOW" se iba a clases
        # de instrumento. El baile que dice el título manda sobre la etiqueta
        # de la fuente.
        ("danza", ["danza", "baile", "salsa", "bachata", "cueca", "tango",
                   "flamenco", "ballet", "timba", "afro", "footwork",
                   "partnerwork"]),
        ("musica", ["guitarra", "canto", "piano", "bateria", "ukelele",
                    "violin", "percusion", "coro", "musica", "musical",
                    "produccion musical", "charango", "cajon"]),
        ("oficios", ["carpinteria", "gasfiteria", "electricidad", "soldadura",
                     "peluqueria", "barberia", "mecanica", "jardineria",
                     "huerto", "apicultura", "oficio", "oficios", "cuero",
                     "zapateria"]),
    ],
    "musica": [
        # Un tributo se anuncia como tributo y el público lo busca así; el
        # género de la banda homenajeada queda en segundo plano.
        ("tributo", ["tributo", "tributos", "tribute", "homenaje", "cover",
                     "covers", "sesiones"]),
        ("folclor", ["folclor", "folclore", "folclorica", "folklor", "folklore",
                     "folklorica", "cueca", "cuecas", "pena", "penas",
                     "andina", "latinoamericana", "tonada", "payador",
                     "canto nuevo", "criolla", "criollo", "guachaca"]),
        ("cumbia", ["cumbia", "cumbias", "sonora", "guaracha", "chicha",
                    "tropical"]),
        ("clasica", ["sinfonica", "sinfonico", "orquesta", "opera", "coro",
                     "coral", "camara", "camerata", "cantata", "barroca",
                     "clasica", "lirica", "tenor", "soprano", "filarmonica",
                     "cuarteto de cuerdas", "recital lirico"]),
        ("jazz", ["jazz", "blues", "swing", "bebop", "big band", "big-band",
                  "ska", "skajazz"]),
        ("urbano", ["rap", "hip hop", "hiphop", "trap", "freestyle", "urbano",
                    "reggaeton", "batalla de gallos", "beatmaker"]),
        ("electronica", ["electronica", "techno", "house", "trance", "rave",
                         "edm", "sintetizador", "synth"]),
        # El metal vive acá dentro y no como subcategoría propia. Lo tuvo por
        # un rato y era un corte arbitrario: el prior de recinto ya manda Sala
        # RBX, Metrónomo y Cariola completos a "rock", así que "metal" solo
        # saltaba cuando el título decía la palabra —cuatro eventos— y partía
        # en dos la misma escena, la misma sala y la misma noche.
        ("rock", ["rock", "indie", "punk", "hardcore", "grunge", "garage",
                  "psicodelia", "stoner", "emo", "shoegaze",
                  "metal", "death", "black metal", "thrash", "doom",
                  "grindcore", "metalero", "heavy"]),
        ("pop", ["pop", "balada", "baladas", "romantica", "romanticas"]),
    ],
    "deporte": [
        # El aerobike es una bicicleta clavada al suelo con música fuerte: va
        # con la zumba, no con el ciclismo, y menos con los conciertos.
        ("baile_fitness", ["zumba", "aerobox", "aerobike", "aerobic",
                           "aerobica", "baile entretenido", "ritmos latinos",
                           "cardio dance", "danza", "baile"]),
        ("natacion", ["natacion", "nado", "matronatacion", "aquagym",
                      "hidrogimnasia", "aguas abiertas", "waterpolo",
                      "polo acuatico", "piscina"]),
        ("futbol", ["futbol", "futbolito", "futsal", "baby futbol",
                    "babyfutbol", "liguilla"]),
        ("running", ["running", "corrida", "corridas", "trail", "maraton",
                     "10k", "21k", "42k", "atletismo", "cross country",
                     "trote"]),
        ("ciclismo", ["ciclismo", "cicletada", "ciclorecreovia",
                      "mountain bike", "mtb", "bicicleta", "bicicletada"]),
        ("artes_marciales", ["karate", "taekwondo", "judo", "jiu jitsu",
                             "jiujitsu", "jiu-jitsu", "kung fu", "boxeo",
                             "box", "kickboxing", "muay thai", "muaythai",
                             "defensa personal", "esgrima", "mma", "ufc",
                             "aikido", "capoeira", "lucha libre"]),
        ("raqueta", ["tenis", "padel", "ping pong", "pingpong", "tenis de mesa",
                     "badminton", "squash"]),
        ("equipo", ["basquet", "basquetbol", "basketball", "voleibol", "voley",
                    "volleyball", "handbol", "balonmano", "rugby", "hockey",
                    "beisbol", "softbol"]),
        ("gimnasia", ["gimnasia", "pilates", "yoga", "gap", "acondicionamiento",
                      "entrenamiento funcional", "funcional", "crossfit",
                      "hiit", "calistenia", "tai chi", "taichi", "chikung",
                      "elongacion", "sala de maquinas", "musculacion",
                      "fitness", "actividad fisica", "habilitacion fisica",
                      "recuperacion fisica", "motricidad"]),
    ],
}


# El recinto como última pista, y con lista escrita a mano en vez de buscar
# las mismas palabras dentro del nombre del lugar. Eso último se probó y es una
# trampa: "MUT — Mercado Urbano Tobalaba" convertía una fonda en fiesta urbana
# y la dirección "Antonia López de Bello 80" hacía ochentera una fiesta de 2026.
# Acá cada entrada es un local que programa siempre lo mismo, contado en el
# catastro: en la Sala RBX (42 eventos), el Metrónomo (28) y el Cariola (23)
# lo que suena es rock y metal salvo dos boleros; La Fama es la disco de la
# cumbia peruana.
RECINTO_SUBCATEGORIA = [
    (r"\bcirco\b|carpa de circo", "teatro", "circo"),
    (r"centro coreografico|escuela de danza|academia de ballet", "teatro", "danza"),
    (r"sala rbx|sala metrono|teatro cariola|bar oxido|club hell"
     r"|house of rock|rock ?star|espacio rock and roll", "musica", "rock"),
    (r"discoteca la fama|chancho con chaleco", "musica", "cumbia"),
    # Los clubes de carrete con género propio. La lista es CORTA a propósito:
    # se revisaron los 29 recintos con dos o más fiestas en el catastro y casi
    # ninguno programa lo mismo dos noches seguidas. El Club Subterráneo hace
    # ultrabailable el jueves, jazz el miércoles y un fest de grunge el sábado;
    # el Chocolate tuvo funk carioca, reggaetón y salsa cubana en cuatro
    # fiestas; en Blondie conviven Dua Lipa y Swallow The Sun. Todos esos se
    # quedan vacíos, que es la respuesta correcta.
    # Entran los dos que sí son de un solo género y se puede demostrar sin
    # salir de la base: La Feria trae a John Digweed, Mariano Mellino y
    # Francisco Allendes —siete de siete, house y progresivo—, y el Club 1
    # publica su cartelera como "Lineup: ... (all night long)", que es la
    # forma de anunciar una noche de techno y no una banda.
    (r"\bla feria\b|\bclub 1\b", "fiesta", "electronica"),
    (r"tom house|club fist", "fiesta", "electronica"),
    (r"discoteca la fama", "fiesta", "cumbia"),
]


def clasificar_subcategoria(categoria, titulo, categoria_fuente, descripcion,
                            lugar="", fuente=""):
    """Devuelve (subcategoria, origen) dentro de `categoria`, o ("", "defecto").

    origen ∈ {'titulo','descripcion','lugar','defecto'} — igual que en
    `clasificar`, sirve para saber cuánto está adivinando.

    Solo cinco categorías tienen segundo nivel (fiesta, teatro, clases, musica,
    deporte). Para el resto la respuesta correcta es "": una exposición o una
    charla no se subdividen todavía y una etiqueta inventada es peor que nada.
    """
    listas = SUBCATEGORIAS.get(categoria)
    if not listas:
        return "", "defecto"

    tit = _titulo_para_clasificar(titulo, categoria_fuente, lugar, fuente)
    cuerpo = _norm(f"{tit} {descripcion}")
    contexto = _norm(f"{lugar} {fuente}")

    # 0. La memoria: una regla de categorias.yaml que trae subcategoría y es
    #    de esta misma categoría. Misma razón que en `clasificar`: el prior
    #    de la Sala RBX manda "rock" a todo lo que pasa por ahí, y la regla
    #    "mixtape/freestyle → urbano" que alguien ya revisó tiene que ganarle.
    mem = memoria()
    calce = mem.buscar(tit, "titulo", categoria) or mem.buscar(cuerpo, "texto", categoria)
    if calce:
        return calce[0].subcategoria, "memoria"

    # Mismo orden de confianza que en `clasificar`: el título es corto y
    # curado, la descripción trae ruido.
    for plano, origen in ((tit, "titulo"), (_norm(descripcion), "descripcion")):
        if not plano.strip():
            continue
        for subcategoria, palabras in listas:
            if _tiene(plano, palabras):
                return subcategoria, origen

    # Y al final el recinto, que es una conjetura y queda marcada como tal.
    calce = mem.buscar(contexto, "lugar", categoria)
    if calce:
        return calce[0].subcategoria, "lugar"
    for patron, cat_recinto, subcategoria in RECINTO_SUBCATEGORIA:
        if cat_recinto == categoria and re.search(patron, contexto):
            return subcategoria, "lugar"
    return "", "defecto"


# ---------- ESCALA ----------
# Separar el panorama multitudinario del panorama de barrio. La señal fuerte es
# el RECINTO y no el título: "Fiesta de aniversario" es la misma frase en el
# Movistar Arena y en la sede de la junta de vecinos, y lo único que cambia —lo
# único que le importa a quien elige— es si van 15.000 personas o 60.

# Recintos donde no cabe un panorama chico. Salieron de contar el catastro: el
# Estadio Nacional (31 eventos), el Movistar Arena (14), el Teatro Municipal de
# Santiago (9) y la Estación Mapocho (9) son los que de verdad aparecen; el
# resto queda anotado para cuando lleguen.
RECINTOS_MASIVOS = [
    "movistar arena", "estadio nacional", "estadio monumental", "claro arena",
    "estadio santa laura", "estadio bicentenario", "teatro caupolican",
    "teatro municipal de santiago", "espacio riesco", "arena santiago",
    "teatro coliseo", "blanco arena", "velodromo", "parque ohiggins",
    "parque o higgins", "cupula parque o higgins", "parque bicentenario",
    "parque padre hurtado", "parque la araucana", "club hipico", "hipodromo",
    "estacion mapocho", "teatro nescafe", "arena monticello",
    "centro parque", "espacio broadway", "teatro teleton",
]

# El otro extremo: la sala chica, el bar con tocatas y la sede vecinal. Blondie,
# Chocolate, Cariola y Subterráneo entran acá aunque llenen mil personas — son
# el circuito de bandas que el dueño quiere poder aislar, no un estadio. La
# duda honesta se resuelve dejando el evento sin escala, no forzándolo a una.
RECINTOS_UNDER = [
    "jjvv", "jj vv", "junta de vecinos", "sede social", "sede vecinal",
    "centro comunitario", "casa de la cultura", "centro cultural comunitario",
    "sala master", "sala rbx", "sala metronomo", "sala metrono", "sala scd",
    "club subterraneo", "blondie", "club chocolate",
    "club amanda", "teatro cariola", "bar oxido", "mibar", "bar de rene",
    "bar victoria", "la casa en el aire", "el meson nerudiano", "kahuin",
    "peluqueria francesa", "club 1", "epicentro", "la puerta amarilla",
    "casa en el aire", "bar teatro fiebre", "teatro fiebre", "palermo teatro",
    "club hell bar", "sala ana gonzalez", "espacio 56", "sala de las artes",
    "discoteca la fama", "chancho con chaleco", "restobar", "resto bar",
]

# Palabras del LUGAR que delatan un panorama de barrio aunque el recinto no
# tenga nombre propio. La municipalidad publica la sede como dirección
# ("JJ. VV. Simón Bolívar Av. Las Torres # 840") y ahí no cabe un evento
# masivo ni queriendo.
LUGARES_DE_BARRIO = ["sede", "jjvv", "junta de vecinos", "centro comunitario",
                     "casa de la cultura", "multicancha", "capilla",
                     "club deportivo", "sede comunitaria", "villa"]

# Fuentes que solo publican talleres municipales: todo lo que sale de ahí pasa
# en una sede, un polideportivo o una plaza de la comuna.
FUENTES_DE_BARRIO = re.compile(
    r"talleres deportivos|actividades y talleres|corporaci\w+ (municipal )?de "
    r"deportes|talleres municipales|circuito under|eventos under")

# "Festival", "expo" y "arena" en el título: no alcanzan solos para llamarlo
# masivo, pero cuando el recinto no dijo nada son lo único que hay. Solo el
# TÍTULO: en la descripción la palabra aparece de pasada —"Prenderse fuego"
# cuenta que Lemebel leyó en un festival— y eso no dice nada del tamaño de hoy.
TITULO_MASIVO = re.compile(r"\b(festival|expo|arena|estadio|cumbre)\b")

# Sobre esto ya no es una entrada de bar. Es la señal más débil de todas y va
# al final: en el Teatro Cariola una entrada de metal cuesta $46.000 y ahí caben
# mil personas, así que solo opina cuando nadie más opinó.
PRECIO_MASIVO = 40000


def clasificar_escala(titulo, lugar, fuente, precio_clp=None, descripcion=""):
    """Devuelve (escala, razon). escala ∈ {'masivo', 'under', ''}.

    "" no es un fallo: es lo que corresponde cuando el recinto no dice nada y
    el título tampoco. Preferimos no saber antes que mandar una tocata de bar
    al filtro de los estadios.
    """
    lug = _norm(lugar)
    contexto = _norm(f"{lugar} {fuente}")

    # 1. La fuente, y va primero a propósito. La corporación de deportes de
    #    Ñuñoa arrienda la pista del Estadio Nacional para su taller de
    #    running: 31 clases municipales de veinte personas quedaban marcadas
    #    como panorama masivo por el nombre del recinto. Un taller municipal
    #    no es multitudinario aunque se haga en el Nacional.
    if FUENTES_DE_BARRIO.search(_norm(fuente)):
        return "under", "fuente de talleres municipales o circuito under"

    # 2. El recinto con nombre propio. Es la única señal fuerte que existe.
    #    Se busca también en el texto porque hay fuentes —Disfruta Santiago—
    #    que ponen su propio nombre en el campo `lugar` y dejan el recinto de
    #    verdad en el título: "Cuarteto de Nos ... en el Movistar Arena".
    recinto = _tiene(_norm(f"{lugar} {titulo} {descripcion}"), RECINTOS_MASIVOS)
    if recinto:
        return "masivo", f"recinto masivo: {recinto}"
    recinto = _tiene(contexto, RECINTOS_UNDER)
    if recinto:
        return "under", f"recinto del circuito chico: {recinto}"

    # 3. El lugar sin nombre propio: una sede, una multicancha, una capilla.
    barrio = _tiene(lug, LUGARES_DE_BARRIO)
    if barrio:
        return "under", f"lugar de barrio: {barrio}"

    # 4. Recién acá las señales flojas, y solo si nada de lo anterior habló.
    #    El precio bajo NO dice nada: hay festivales gratuitos con 50.000
    #    personas, así que la señal es de un solo lado.
    palabra = TITULO_MASIVO.search(_norm(titulo))
    if palabra:
        return "masivo", f"palabra de evento grande en el título: {palabra.group()}"
    # Un taller caro sigue siendo un taller: la "Certificación en felicidad"
    # de $540.000 y el taller de perfumería de $45.000 son para veinte
    # personas, y el precio los mandaba al filtro de los estadios.
    if (precio_clp and precio_clp > PRECIO_MASIVO
            and not SE_APRENDE.search(_norm(titulo))):
        return "masivo", f"entrada sobre ${PRECIO_MASIVO:,} (señal débil)"

    return "", "sin señal de tamaño — no se inventa"


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


# ---------- FORMATO: taller contra panorama ----------
# Un panorama se asiste UNA vez: una maratón, un concierto, una obra. Un
# taller se toma TODAS las semanas: la clase de natación de los martes, el
# aerobike de las 08:30, el curso de cerámica. En el mapa convivían los dos y
# los talleres eran el 55% del catastro: la clase de nado de las 06:00
# enterraba a los conciertos, que es exactamente la pregunta contraria a la
# que responde un mapa de panoramas. Ahora cada formato tiene su página.

# Las fuentes que SOLO publican clases. Se midió antes de confiar: 1.594
# eventos de estas tres fuentes y ni uno solo es una corrida, un campeonato ni
# una fecha puntual. La corporación existe para dictar talleres.
FUENTES_DE_TALLERES = re.compile(
    r"corporaci\w+ (municipal )?de deportes|talleres deportivos"
    r"|talleres municipales|actividades y talleres")

# Un evento puntual de deporte se reconoce por el título: es una cita con
# fecha, no una rutina. Va como excepción DENTRO de la fuente municipal por si
# el día de mañana una corporación publica su corrida familiar — hoy no pasa,
# pero la regla queda protegida contra el día en que pase.
_EVENTO_PUNTUAL = re.compile(
    r"\b(corrida|maraton|campeonato|torneo|copa|liguilla|cicletada"
    r"|10k|21k|42k|vs\.?|final)\b")


def es_taller(titulo, categoria, fuente, dias_semana=None):
    """Devuelve (bool, razon). ¿Esto se toma semanalmente o se asiste una vez?

    `dias_semana` viene del export (la serie semanal ya colapsada) y es la
    señal más directa: si algo se repite todos los martes, es un taller por
    definición, sea yoga o sea un club de lectura.
    """
    tit = _norm(titulo)
    if _EVENTO_PUNTUAL.search(tit):
        return False, "evento puntual en el título"
    if dias_semana:
        return True, "serie semanal"
    if categoria in ("clases", "idiomas"):
        return True, "categoría de clases"
    if categoria == "deporte" and FUENTES_DE_TALLERES.search(_norm(fuente)):
        return True, "fuente municipal de talleres"
    # "Escuela de fútbol", "Taller de defensa personal": deporte que se enseña.
    if categoria == "deporte" and SE_APRENDE.search(tit):
        return True, "deporte que se enseña"
    return False, ""
