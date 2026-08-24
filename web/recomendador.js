/* ============================================================
   LOICA — el recomendador
   El motor que decide qué panorama sale. Vive aparte de la página a
   propósito: así se puede correr contra eventos.json y talleres.json sin
   navegador y probar de verdad cada perfil de usuario
   (scripts/probar_roles.js). Sin DOM, sin fetch, sin idioma de interfaz:
   entra data, sale un orden.

   LO QUE HAY QUE SABER DEL CATÁLOGO, porque el diseño sale de ahí:

   1. `publico` no sirve para filtrar. 1.518 de 1.740 panoramas dicen "todos",
      y el cine SIN EXCEPCIÓN — incluidos "Possession", "La posada maldita" y
      "Teenage Sex and Death at Camp Miasma". Confiar en ese campo es como
      mandar a un niño de cinco años a cualquiera de esos tres.

   2. Desde el 15-08-2026 el catálogo son DOS archivos. `eventos.json` trae
      los panoramas puntuales (1.740) y `talleres.json` las clases semanales
      (1.694: 1.614 de deporte, casi todas de Ñuñoa y Huechuraba). Para
      "quiero meterme a natación" el taller ES la respuesta; para "qué hago
      el sábado" es ruido. El que carga los dos archivos marca los talleres
      con `esTaller`, y acá cada repregunta decide si los quiere.

   3. Las subcategorías existen pero vienen vacías en 7 de cada 10 eventos:
      el clasificador dice "rock" cuando el título lo dice, y se calla cuando
      no. Por eso una repregunta como "¿qué suena?" no FILTRA por
      subcategoría —se perdería el 70%— sino que pone PRIMERO lo que calza
      fuerte (subcategoría o palabra en el título) y deja el resto detrás.

   4. Casi no hay panoramas infantiles puntuales: 59 en todo el catálogo, y
      133 talleres. Eso no se arregla puntuando mejor, se arregla diciéndolo.

   5. Una temporada —la muestra de Matta que abrió en julio y cierra en
      septiembre— tiene `inicio` en el pasado y `fin` en el futuro. Son 159.
      El que arma el pool de candidatos tiene que mirar `fin` y `dias_semana`,
      no solo `inicio`; acá eso ya viene resuelto en `ev.fecha` (la fecha en
      que IRÍAS, no la del primer día).
   ============================================================ */
(function (raiz) {
"use strict";

/* ---------- Talleres recurrentes ----------
   La señal no está en ningún campo, está en el título, y son dos cruzadas:
   el título normalizado se repite (hay que sacarle días y horas, porque el
   mismo taller viene como "Yoga Lu-Mi 09:00" y "Yoga Ma-Ju 19:30"), o el
   título trae el patrón de días — "Hapkido Lu-Mi-Vi 20:00" aparece UNA vez
   en todo el catálogo y la repetición sola nunca lo iba a pillar.
   Los de talleres.json además llegan con `esTaller`, que manda sobre todo. */
const PATRON_DIAS = /\b(lu|ma|mi|ju|vi|sa|do)(-(lu|ma|mi|ju|vi|sa|do))+\b/i;
const claveTitulo = t => (t || "").toLowerCase().replace(/\s+/g, " ").trim();
const tituloBase = t => claveTitulo(t)
  .replace(PATRON_DIAS, "")
  .replace(/\d{1,2}[:.]\d{2}\s*(h|hrs?|horas?)?\.?/g, "")
  .replace(/[\s\-–—]+/g, " ")
  .replace(/^[\s.\-]+|[\s.\-]+$/g, "");

/* ---------- Señales de texto ----------
   Cuando los campos no alcanzan, el título es el único dato que queda. No es
   elegante; es lo que hay, y es mejor que recomendar a ciegas. */
const SENAL_NINOS = /\b(infantil(es)?|niñ[oa]s?|nino|cuentacuentos|t[ií]teres|marionetas|familiar|preescolar|kinder|escolar|guagua|beb[eé]s?|matin[eé]|para toda la familia|p[úu]blico familiar)\b/i;
/* Lo que jamás va con niños aunque venga sin marcar: la mitad del cine del
   catálogo es terror, giallo y trasnoche de cineclub. */
const SENAL_ADULTA = new RegExp([
  // Géneros que el cine del catálogo trae sin marcar
  "terror","horror","gore","slasher","trasnoche","giallo","zombis?","zombies?",
  "malditas?","posesi[óo]n","obsesi[óo]n","thriller","suspenso","psicol[óo]gic\\w*",
  "er[óo]tic\\w*","sexual\\w*","masacre","asesinat\\w*",
  // Edad declarada
  "mayores de 18","solo adultos","estrictamente adultos","18\\+",
  // Trago: si el evento se vende por la barra, no es un panorama con niños
  "barra libre","open bar","c[óo]ctel\\w*","coctel\\w*","cervez\\w*","cervecer\\w*",
  "vermut","pisco","whisky","mixolog\\w*","destilad\\w*",
].map(x => "\\b" + x + "\\b").join("|"), "i");
const SENAL_PAREJA = /\b(cena|romantic|rom[áa]ntic|jazz|bolero|tango|vino|degustaci[óo]n|concierto[s]? [íi]ntim|acústic|acustic|serenata|cabaret|clásica|clasica|c[áa]mara|ballet|[óo]pera|opera)\b/i;
const SENAL_GRUPO = /\b(fiesta|carrete|tocata|festival|karaoke|torneo|campeonato|pichanga|cumbia|reggaet[óo]n|electr[óo]nic|techno|house|dj|banda|rock|metal|punk|trivia|juegos|competencia)\b/i;
/* `aire_libre` es la categoría más contaminada del catálogo: tiene trekkings
   y también "No te va gustar en Cúpula Parque O'Higgins" a $51.750, que es un
   concierto. Para "hacer ejercicio" no basta la categoría, hay que ver que el
   evento hable de moverse. */
const SENAL_DEPORTE = new RegExp([
  "deporte","deportiv\\w*","ejercicio","entrenamiento","entrena\\w*","gimnasi\\w*",
  "running","trote","trotar","maratón","maraton","corrida","atletismo","caminata",
  "trekking","senderismo","cicletada","ciclismo","bicicleta","nataci[óo]n","nado",
  "yoga","pilates","zumba","aer[óo]bic\\w*","spinning","crossfit","funcional",
  "f[úu]tbol","futsal","b[áa]squetbol","basquetbol","v[óo]leibol","voleibol","tenis",
  "b[áa]dminton","badminton","handbol","hockey","rugby","escalada","boxeo","karate",
  "taekwondo","judo","hapkido","defensa personal","artes marciales","baile entretenido",
  "acondicionamiento","motricidad","chikung","tai chi","taichi","kayak","remo","surf",
  "patinaje","p[áa]del","padel","escuela de",
].map(x => "\\b" + x + "\\b").join("|"), "i");
/* Lo que usa la palabra "maratón" sin mover un músculo: la maratón de El
   Señor de los Anillos es una función de cine de nueve horas. */
const SENAL_FALSO_DEPORTE = /\b(marat[óo]n\s+(de\s+)?(fotograf|cine|pel[íi]cul|lectura|series?|el se[ñn]or|harry|star)|tattoo|tatuaje|exposici[óo]n|expo\b|abonad\w*|abono\b|membres[íi]a)/i;

/* Lo que tiene fecha, precio y ficha pero NO es un panorama: el abono de la
   temporada del club, la membresía anual de la sala, la campaña de socios.
   Se descarta en todas las situaciones, y se mira SOLO el título: en una
   descripción "socios" aparece de sobra hablando de un descuento. */
const NO_ES_PANORAMA = /\b(abonad\w*|abonos?|membres[ií]as?|suscripci[oó]n\w*|convocatorias?|postulaci[oó]n\w*|gift ?card|tarjetas? de regalo)\b/i;

/* Formato "alguien te cuenta": sirve para separar hacer de escuchar. */
const FORMATO_CHARLA = /\b(webinar|conversatorio|charla|seminario|coloquio|panel|foro|conferencia|mesa redonda|clase magistral|masterclass|lanzamiento de libro|presentaci[óo]n del libro)\b/i;

const texto = ev => ((ev.titulo || "") + " " + (ev.descripcion || ""));
const esParaNinos = ev =>
  !SENAL_ADULTA.test(texto(ev)) &&
  (ev.publico === "ninos" || SENAL_NINOS.test(texto(ev)));

/* Marca cada evento una vez, al cargar. `recurrente` y `paraNinos` se
   consultan en cada puntaje, así que se calculan una sola vez. Un taller
   (talleres.json) es recurrente por definición: es UNA tarjeta por una serie
   de sesiones, y contar repeticiones de título no lo iba a encontrar. */
function marcar(eventos){
  const cuenta = new Map();
  eventos.forEach(e => {
    const k = tituloBase(e.titulo);
    cuenta.set(k, (cuenta.get(k) || 0) + 1);
  });
  eventos.forEach(e => {
    e.recurrente = !!e.esTaller
      || (e.dias_semana && e.dias_semana.length > 0)
      || (cuenta.get(tituloBase(e.titulo)) || 0) > 3
      || PATRON_DIAS.test(e.titulo || "");
    e.paraNinos = esParaNinos(e);
    e.adulto = SENAL_ADULTA.test(texto(e)) || e.publico === "adultos";
  });
  return eventos;
}

/* ---------- Sectores ----------
   Agrupan las comunas que el pipeline realmente entrega. Un evento sin
   comuna no entra en ninguno: no se puede prometer un sector que no se sabe. */
const SECTORES = {
  centro: ["Santiago","Estación Central","Recoleta","Independencia","Quinta Normal","Cerrillos","Pedro Aguirre Cerda"],
  oriente:["Providencia","Ñuñoa","Las Condes","Vitacura","Lo Barnechea","La Reina","Peñalolén","Macul"],
  norte:  ["Huechuraba","Conchalí","Quilicura","Renca","Colina","Lampa","Cerro Navia"],
  sur:    ["La Florida","Puente Alto","Maipú","La Pintana","San Miguel","La Granja","El Bosque","Pudahuel","San Bernardo","Lo Espejo","San Joaquín","La Cisterna","Lo Prado","San Ramón","Buin","Padre Hurtado","Peñaflor","Talagante","Paine","Pirque"],
};
const enSector = (ev, s) => s === "todo" || (SECTORES[s] || []).includes(ev.comuna);
const sectorDeComuna = c => Object.keys(SECTORES).find(s => SECTORES[s].includes(c)) || "todo";

/* ============================================================
   CON QUIÉN VAS
   El eje que más cambia una recomendación. "Teatro" no significa lo mismo
   para alguien que va en pareja un viernes que para una mamá con un niño de
   cinco: es la misma categoría y son dos panoramas distintos.

   Desde la v2 NO es una pregunta obligatoria: se deduce de lo que escribes
   ("con amigos", "en pareja") o se ofrece después del resultado, para afinar.
   Sin dato, la compañía es neutra y manda la situación.

   `exige` es una allowlist: si está, el evento tiene que pasarla o queda
   fuera, pase lo que pase con el resto del puntaje.
   ============================================================ */
const COMPANIAS = {
  solo: {
    es:["Voy solo","A mi ritmo"], en:["On my own","At my own pace"], pt:["Vou sozinho","No meu ritmo"],
    dicho:{es:"solo", en:"on your own", pt:"sozinho"},
    pista:/\b(solo|sola|alone|on my own|by myself|sozinh[oa])\b/,
    pesos:{charla:4, arte:3, cine:3, clases:3, fiesta:-2},
    recurrente:1,
  },
  pareja: {
    es:["En pareja","Una cita"], en:["As a couple","A date"], pt:["A dois","Um encontro"],
    dicho:{es:"en pareja", en:"as a couple", pt:"a dois"},
    pista:/\b(pareja|cita|polol[oa]|novi[oa]|romantic[oa]?|date|couple|namorad[oa]|a dois|mi senora|mi marido|esposa?)\b/,
    pesos:{teatro:5, cine:5, musica:4, arte:3, charla:-2, clases:-4, deporte:-4, familia:-6},
    /* Una cita no es un taller de natación de los miércoles. */
    recurrente:-9,
    horaIdeal:[17,2],
    senalBuena:SENAL_PAREJA, bonoSenal:5,
    evitarNinos:true,
  },
  amigos: {
    es:["Con amigos","En grupo"], en:["With friends","In a group"], pt:["Com amigos","Em grupo"],
    dicho:{es:"con amigos", en:"with friends", pt:"com amigos"},
    pista:/\b(amig[oa]s|grupo|friends|galera|cumplea[ñn]os|junta|compadres|la gente|los cabros)\b/,
    pesos:{fiesta:6, musica:5, deporte:3, feria:2, charla:-3, arte:-2},
    recurrente:-5,
    horaIdeal:[16,3],
    senalBuena:SENAL_GRUPO, bonoSenal:4,
    evitarNinos:true,
  },
  ninos: {
    es:["Con niños","Van cabros chicos"], en:["With kids","Children coming"], pt:["Com crianças","Vão crianças"],
    dicho:{es:"con niños", en:"with kids", pt:"com crianças"},
    pista:/\b(ni[ñn][oa]s?|nin[oa]s?|hij[oa]s?|familia|familiar|cabr[oa]s chic[oa]s|guagua|beb[eé]|kids?|children|crian[çc]as?|infantil|sobrin[oa]s?|nietos?)\b/,
    /* ALLOWLIST. Es la única compañía que exige evidencia positiva, y es
       deliberado: el costo de equivocarse acá no es un panorama fome, es una
       mamá con un niño de cinco años en una función de terror. Si el evento
       no dice en ninguna parte que es para niños, no se recomienda para
       niños. Prefiero quedarme corto de opciones y decirlo. */
    exige: ev => ev.paraNinos,
    pesos:{familia:6, teatro:4, feria:4, aire_libre:4, cine:2, deporte:3, clases:3},
    horaIdeal:[9,19],
    techoPrecio:15000,
  },
};
const ORDEN_COMPANIAS = ["solo","pareja","amigos","ninos"];

/* ============================================================
   LAS SITUACIONES
   El usuario elige una situación de su vida, no una categoría, y cada
   situación reparte puntaje entre varias. "Ferias y barrio" no es
   `categoria == feria` — son 37 en todo el catálogo — es feria + aire libre
   + familia ordenados por qué tan bien calzan.

   Cada situación tiene UNA repregunta, la de su animal, y cada opción de esa
   repregunta es un `efecto` sobre el puntaje:

     pesos        suma o resta por categoría encima de los de la situación.
     subcats      subcategorías que calzan FUERTE (rock, comedia, natación).
     senal        palabras del título que también calzan fuerte.
     catsFuertes  categorías enteras que calzan fuerte cuando vienen sin
                  subcategoría (cine, arte).
     soloTalleres / soloEventos   de qué archivo salen los candidatos.
     recurrente   cuánto suma o resta un taller semanal; >0 levanta el veto
                  de `soloPuntual`.

   Lo que calza fuerte va primero con +10; lo que no, queda detrás pero no
   se bota: si de jazz hay dos, el tercero es otro concierto y se dice.

   `pista` es la regla del intérprete de texto libre: si escribes "jazz el
   sábado" la situación es música y la opción es "clásica y jazz" sin pasar
   por ninguna pregunta. Van en minúsculas y sin tildes porque el texto se
   normaliza antes de mirarlo.

   `soloPuntual` marca las situaciones donde un taller semanal no es una
   respuesta: nadie pide "algo para el sábado" y quiere un curso de los
   miércoles.
   ============================================================ */
const SITUACIONES = [
  {
    id:"panorama", guia:"loica",
    es:["Sorpréndeme","Lo mejor que haya"],
    en:["Surprise me","The best there is"],
    pt:["Me surpreenda","O melhor que tiver"],
    dicho:{es:"", en:"", pt:""},
    saludo:{es:"Entonces me quedo yo, que para eso soy la anfitriona. Te muestro lo mejor que haya.",
            en:"Then I'll stay on — that's what being the host is for. I'll show you the best there is.",
            pt:"Então eu fico, que para isso sou a anfitriã. Te mostro o melhor que tiver."},
    pregunta:{es:"¿Te llevo a lo seguro o a algo raro?", en:"Shall I play it safe or take you somewhere odd?", pt:"Te levo no seguro ou em algo estranho?"},
    pista:/\b(sorprendeme|sorprende|lo que sea|cualquier cosa|algo que hacer|que hago|que hacer|panorama|panoramas|plan|planes|surprise|anything|something to do|qualquer coisa|me surpreenda)\b/,
    opciones:[
      {id:"seguro", es:"A lo seguro", en:"Play it safe", pt:"No seguro",
       pista:/\b(seguro|clasico|safe)\b/,
       efecto:{pesos:{musica:4, teatro:4, cine:3, feria:3}}},
      {id:"raro", es:"Algo distinto", en:"Something different", pt:"Algo diferente",
       pista:/\b(raro|distinto|diferente|rara|extrano|odd|different|weird|diferente)\b/,
       efecto:{pesos:{otros:6, charla:4, arte:3, musica:-2}}},
    ],
    porDefecto:"seguro",
    pesos:{}, base:6, bonoGratis:4, variedad:true, soloPuntual:true,
  },
  {
    id:"musica", guia:"condor",
    es:["Música en vivo","Tocatas y conciertos"],
    en:["Live music","Gigs and concerts"],
    pt:["Música ao vivo","Shows e concertos"],
    dicho:{es:"con música en vivo", en:"with live music", pt:"com música ao vivo"},
    saludo:{es:"Cóndor. Yo cargo con lo que suena fuerte.",
            en:"Condor. I carry the loud stuff.",
            pt:"Condor. Eu carrego o que soa alto."},
    pregunta:{es:"¿Qué suena?", en:"What's playing?", pt:"O que toca?"},
    pista:/\b(musica|conciertos?|tocatas?|recital(es)?|festival(es)?|bandas?|show|gig|concerts?|live music|rock|metal|punk|jazz|blues|folclor(e|ico)?|cueca|clasica|sinfonic[ao]|orquesta|opera|tributo|cumbia|pop|indie|rap|hip ?hop|trap|cantante|cantautora?|coro|music|musica ao vivo|cantar)\b/,
    opciones:[
      {id:"rock", es:"Rock y metal", en:"Rock and metal", pt:"Rock e metal",
       pista:/\b(rock|metal|punk|indie|hardcore|grunge|rockero)\b/,
       efecto:{subcats:["rock","metal","punk"], senal:/\b(rock|metal|punk|hardcore|grunge|indie|heavy)\b/i, pesos:{musica:4, fiesta:-2}}},
      {id:"folclor", es:"Folclor y cumbia", en:"Folk and cumbia", pt:"Folclore e cumbia",
       pista:/\b(folclor(e|ico)?|cueca|cumbia|salsa|latin[ao]?|andin[ao]|trova|pena|tropical|bolero|tango)\b/,
       efecto:{subcats:["folclor","cumbia","latina"], senal:/\b(folcl[oó]r\w*|cueca|tonada|trova|cumbia|salsa|bolero|tango|andin\w*|latino\w*|pe[ñn]a|sonora)\b/i, pesos:{musica:4, fiesta:2}}},
      {id:"clasica", es:"Clásica y jazz", en:"Classical and jazz", pt:"Clássica e jazz",
       pista:/\b(jazz|blues|clasica|sinfonic[ao]|orquesta|opera|piano|coro|camara|docta)\b/,
       efecto:{subcats:["clasica","jazz"], senal:/\b(cl[aá]sic[ao]|sinf[oó]nic\w*|orquesta|c[aá]mara|coro|coral|piano|[oó]pera|jazz|blues|cuarteto|soprano|tenor)\b/i, pesos:{musica:4, fiesta:-9}, horaIdeal:[17,23]}},
      {id:"tributo", es:"Tributos y pop", en:"Tributes and pop", pt:"Tributos e pop",
       pista:/\b(tributo|homenaje|cover|pop|ochenter[ao]|noventer[ao]|rap|hip ?hop|trap|urban[ao]?|reggaeton|reguet[oó]n)\b/,
       efecto:{subcats:["tributo","pop","ochentera","urbano","reggaeton"], senal:/\b(tributo|homenaje|cover|pop|ochenter\w*|noventer\w*|80s|90s|urbano|trap|hip ?hop|rap|reggaet[oó]n)\b/i, pesos:{musica:4, fiesta:2}}},
      {id:"cualquiera", es:"Lo que suene", en:"Whatever's on", pt:"O que tocar",
       pista:/\b(lo que sea|lo que suene|cualquiera|whatever|qualquer)\b/,
       efecto:{pesos:{musica:3}}},
    ],
    pesos:{musica:12, fiesta:5}, horaIdeal:[18,2], bonoGratis:1, soloPuntual:true,
  },
  {
    id:"escenario", guia:"chinchilla",
    es:["Teatro, cine o arte","Sentarse a mirar algo"],
    en:["Theatre, film or art","Sit down and watch"],
    pt:["Teatro, cinema ou arte","Sentar e ver algo"],
    dicho:{es:"de escenario", en:"on a stage or screen", pt:"de palco"},
    saludo:{es:"Chinchilla. Escucho más de lo que hablo, así que voy a ser breve.",
            en:"Chinchilla. I listen more than I talk, so I'll be brief.",
            pt:"Chinchila. Escuto mais do que falo, então vou ser breve."},
    pregunta:{es:"¿Qué vamos a ver?", en:"What are we watching?", pt:"O que vamos ver?"},
    pista:/\b(teatro|obras?|cine|peliculas?|films?|movies?|documental(es)?|stand ?up|comedia|humor|monologos?|comediantes?|danza|ballet|circo|expo|exposicion(es)?|museos?|galerias?|arte|muestra|theatre|theater|exhibition|exhibit|art|peca|cinema|actuacion|dramaturgia|pintura|fotografia|escultura)\b/,
    opciones:[
      {id:"obra", es:"Una obra", en:"A play", pt:"Uma peça",
       pista:/\b(teatro|obras?|theatre|theater|peca|actuacion|dramaturgia|drama)\b/,
       efecto:{subcats:["obra","performance"], catsFuertes:["teatro"], senal:/\b(obra|dramaturg\w*|montaje|teatral)\b/i, pesos:{teatro:8, cine:-6, arte:-4}}},
      {id:"comedia", es:"Reírme un rato", en:"A good laugh", pt:"Dar risada",
       pista:/\b(stand ?up|standup|comedia|humor|monologos?|comediantes?|comedy|risa|reir(me)?|chistes?)\b/,
       efecto:{subcats:["comedia"], senal:/\b(stand ?up|comedia|humor\w*|c[oó]mic\w*|mon[oó]log\w*|improvisaci[oó]n|impro\b|chistes?)\b/i, pesos:{teatro:8, cine:-4, arte:-6}}},
      {id:"cine", es:"Cine", en:"Film", pt:"Cinema",
       pista:/\b(cine|peliculas?|films?|movies?|documental(es)?|cinema|cortos?|cortometrajes?)\b/,
       efecto:{catsFuertes:["cine"], senal:/\b(pel[ií]cula|film\w*|documental|cortometraje|proyecci[oó]n|cineclub|cine)\b/i, pesos:{cine:8, teatro:-5, arte:-3}}},
      {id:"danza", es:"Danza o circo", en:"Dance or circus", pt:"Dança ou circo",
       pista:/\b(danza|ballet|circo|dance|acrobacias?|malabar(es|ismo)?)\b/,
       efecto:{subcats:["danza","circo"], senal:/\b(danza|ballet|circo|acrob\w*|malabar\w*|coreograf\w*)\b/i, pesos:{teatro:8, cine:-6, arte:-4}}},
      {id:"expo", es:"Una expo, a mi ritmo", en:"An exhibition, at my pace", pt:"Uma expo, no meu ritmo",
       pista:/\b(expo|exposicion(es)?|museos?|galerias?|arte|muestra|exhibition|exhibit|art|pintura|fotografia|escultura)\b/,
       efecto:{catsFuertes:["arte"], senal:/\b(expo\w*|muestra|galer[ií]a|museo|pintura|fotograf[ií]a|escultura|instalaci[oó]n)\b/i, pesos:{arte:8, cine:-4, teatro:-4}}},
    ],
    pesos:{teatro:11, cine:10, arte:9}, evitar:["fiesta"], horaIdeal:[11,23],
    bonoGratis:2, soloPuntual:true,
  },
  {
    id:"noche", guia:"culpeo",
    es:["Salir de noche","Carrete, tragos, baile"],
    en:["A night out","Party, drinks, dancing"],
    pt:["Sair à noite","Balada, drinks, dança"],
    dicho:{es:"de noche", en:"for a night out", pt:"à noite"},
    saludo:{es:"Yo salgo cuando el resto se acuesta. La noche la manejo yo.",
            en:"I come out when everyone else goes to bed. The night is mine.",
            pt:"Eu saio quando o resto vai dormir. A noite é comigo."},
    pregunta:{es:"¿Qué se baila?", en:"What are we dancing to?", pt:"O que se dança?"},
    pista:/\b(carrete|carretear|carretes|fiestas?|bailar|discoteca|disco|club|after|party|balada|dancar|tragos?|copete|salir de noche|night out|festa|boliche|techno|reggaeton|reguet[oó]n|perreo)\b/,
    opciones:[
      {id:"electronica", es:"Electrónica", en:"Electronic", pt:"Eletrônica",
       pista:/\b(techno|house|electronic[ao]?|electro|dj|djs|rave|minimal|drum|trance)\b/,
       efecto:{subcats:["electronica"], senal:/\b(techno|house|electr[oó]nic\w*|dj\b|djs|rave|after|minimal|drum|trance)\b/i, pesos:{fiesta:6}, horaIdeal:[22,5]}},
      {id:"cumbia", es:"Cumbia y latina", en:"Cumbia and Latin", pt:"Cumbia e latina",
       pista:/\b(cumbia|salsa|bachata|latin[ao]?|tropical|pena|sonidera)\b/,
       efecto:{subcats:["cumbia","latina","folclor"], senal:/\b(cumbia|salsa|bachata|latin\w*|sonider\w*|tropical|pe[ñn]a|fiesta chilena)\b/i, pesos:{fiesta:6, musica:2}}},
      {id:"reggaeton", es:"Reggaetón y urbano", en:"Reggaeton and urban", pt:"Reggaeton e urbano",
       pista:/\b(reggaeton|reguet[oó]n|perreo|urban[ao]?|trap|dembow)\b/,
       efecto:{subcats:["reggaeton","urbano"], senal:/\b(reggaet[oó]n|perreo|urbano|trap|dembow|guaracha)\b/i, pesos:{fiesta:6}}},
      {id:"ochentera", es:"Ochentera y pop", en:"80s and pop", pt:"Anos 80 e pop",
       pista:/\b(ochenter[ao]|noventer[ao]|80s|90s|2000s|retro|karaoke|pop|indie)\b/,
       efecto:{subcats:["ochentera","pop","rock"], senal:/\b(ochenter\w*|noventer\w*|80s|90s|2000s|retro|pop|rock|indie|karaoke|disco)\b/i, pesos:{fiesta:6, musica:2}}},
      {id:"cualquiera", es:"Donde sea, pero salir", en:"Anywhere, just out", pt:"Qualquer lugar, mas sair",
       pista:/\b(donde sea|cualquiera|lo que sea|whatever|qualquer)\b/,
       efecto:{pesos:{fiesta:4}}},
    ],
    pesos:{fiesta:12, musica:7}, horaIdeal:[21,4], bonoGratis:0,
    soloPuntual:true, soloAdultos:true,
  },
  {
    id:"mover", guia:"chungungo",
    es:["Hacer deporte","Una vez o todas las semanas"],
    en:["Get moving","Once or every week"],
    pt:["Fazer esporte","Uma vez ou toda semana"],
    dicho:{es:"para moverte", en:"to get moving", pt:"para se mexer"},
    saludo:{es:"Chungungo, la nutria del Mapocho. Me muevo, me mojo y no paro nunca.",
            en:"Chungungo, the Mapocho river otter. Always moving, always wet, never still.",
            pt:"Chungungo, a lontra do Mapocho. Me mexo, me molho e não paro nunca."},
    /* Acá la repregunta separa dos cosas distintas de verdad: 1.614 talleres
       municipales con cupo contra 30 actividades sueltas. Y dentro del taller,
       natación no es fútbol: son dos preguntas en una lista. */
    pregunta:{es:"¿Qué quieres mover?", en:"What do you want to move?", pt:"O que você quer mexer?"},
    pista:/\b(deportes?|deportiv[ao]s?|ejercicio|entrenar|entrenamiento|gimnasio|gym|yoga|pilates|zumba|natacion|nadar|piscina|correr|running|trote|trotar|bici|bicicleta|cicletada|ciclismo|trekking|caminata|senderismo|futbol|futsal|basquetbol|basket|voleibol|voley|tenis|padel|boxeo|karate|judo|taekwondo|artes marciales|baile entretenido|fitness|funcional|crossfit|sports?|exercise|workout|swim(ming)?|esporte|natacao|escalada|patinaje|maraton|corrida|moverme|mover)\b/,
    opciones:[
      {id:"suelto", es:"Una vez, a probar", en:"Just once, to try", pt:"Uma vez, para provar",
       pista:/\b(correr|running|trote|trotar|cicletada|trekking|caminata|senderismo|carrera|maraton|corrida|escalada|patinaje|una vez|probar|suelto|torneo|campeonato|partido)\b/,
       efecto:{soloEventos:true, recurrente:-8, pesos:{aire_libre:6, deporte:3, familia:2}}},
      {id:"natacion", es:"Natación", en:"Swimming", pt:"Natação",
       pista:/\b(natacion|nadar|piscina|swim(ming)?|natacao|acuatic[ao]s?|aquagym|hidrogimnasia)\b/,
       efecto:{soloTalleres:true, recurrente:6, subcats:["natacion"], senal:/\b(nataci[oó]n|nado|acu[aá]tic\w*|piscina|aquagym|hidro\w*)\b/i, pesos:{deporte:5}}},
      {id:"equipo", es:"Fútbol y de equipo", en:"Football and team sports", pt:"Futebol e de equipe",
       pista:/\b(futbol|futsal|basquetbol|basket|voleibol|voley|handbol|rugby|hockey|equipo|team|baby)\b/,
       efecto:{soloTalleres:true, recurrente:6, subcats:["futbol","equipo"], senal:/\b(f[uú]tbol|futsal|b[aá]squet\w*|v[oó]leibol|voley|handbol|rugby|hockey|baby)\b/i, pesos:{deporte:5}}},
      {id:"gimnasia", es:"Gimnasia y funcional", en:"Gym and functional", pt:"Ginástica e funcional",
       pista:/\b(gimnasi[ao]|gym|yoga|pilates|funcional|crossfit|pesas|spinning|fitness|workout|maquinas|acondicionamiento|stretching|elongacion|tai ?chi|chikung)\b/,
       efecto:{soloTalleres:true, recurrente:6, subcats:["gimnasia","running","ciclismo"], senal:/\b(gimnasi\w*|funcional|crossfit|m[aá]quinas|pesas|spinning|running|trote|acondicionamiento|pilates|yoga|stretching|elongaci[oó]n|tai ?chi|chikung|aer[oó]bic\w*|localizada)\b/i, pesos:{deporte:5}}},
      {id:"baile", es:"Baile", en:"Dance", pt:"Dança",
       pista:/\b(zumba|baile entretenido|ritmos|bailoterapia|baile|danza)\b/,
       efecto:{soloTalleres:true, recurrente:6, subcats:["baile_fitness","danza"], senal:/\b(baile|zumba|danza|ritmos|bachata|salsa|folcl[oó]r\w*)\b/i, pesos:{deporte:5, clases:3}}},
      {id:"marciales", es:"Artes marciales", en:"Martial arts", pt:"Artes marciais",
       pista:/\b(boxeo|karate|judo|taekwondo|marcial(es)?|kick ?boxing|muay|jiu|hapkido|defensa personal|esgrima|kung ?fu)\b/,
       efecto:{soloTalleres:true, recurrente:6, subcats:["artes_marciales"], senal:/\b(karate|judo|taekwondo|boxeo|kick ?boxing|hapkido|jiu|muay|defensa personal|artes marciales|esgrima|kung ?fu)\b/i, pesos:{deporte:5}}},
      {id:"raqueta", es:"Tenis y raqueta", en:"Tennis and racket", pt:"Tênis e raquete",
       pista:/\b(tenis|padel|badminton|ping ?pong|squash|raqueta)\b/,
       efecto:{soloTalleres:true, recurrente:6, subcats:["raqueta"], senal:/\b(tenis|p[aá]del|padel|b[aá]dminton|ping ?pong|tenis de mesa|squash)\b/i, pesos:{deporte:5}}},
      {id:"taller", es:"Cualquier taller fijo", en:"Any regular class", pt:"Qualquer oficina fixa",
       pista:/\b(taller(es)?|clases?|cursos?|semanal|todas las semanas|class(es)?|weekly|aulas?|fijo)\b/,
       efecto:{soloTalleres:true, recurrente:6, pesos:{deporte:5, clases:4}}},
    ],
    pesos:{deporte:12, aire_libre:11, clases:5, familia:4, otros:3},
    horaIdeal:[7,21], bonoGratis:3,
    exigeSenal:SENAL_DEPORTE, categoriaSegura:"deporte", noCharlas:true,
    evitaSenal:SENAL_FALSO_DEPORTE,
  },
  {
    id:"aprender", guia:"pinguino",
    es:["Aprender algo","Charlas y talleres"],
    en:["Learn something","Talks and workshops"],
    pt:["Aprender algo","Palestras e oficinas"],
    dicho:{es:"para aprender algo", en:"to learn something", pt:"para aprender algo"},
    saludo:{es:"Pingüino, de Humboldt y de punta en blanco. Las charlas y los seminarios son mi departamento.",
            en:"Penguin, Humboldt and in black tie. Talks and seminars are my department.",
            pt:"Pinguim, de Humboldt e de gala. Palestras e seminários são o meu departamento."},
    pregunta:{es:"¿Que te cuenten, o meter las manos?", en:"Be told, or get hands on?", pt:"Que te contem ou meter a mão?"},
    pista:/\b(aprender|charlas?|conversatorios?|seminarios?|webinar|conferencias?|taller(es)?|cursos?|clases?|workshops?|talks?|lectures?|class(es)?|courses?|idiomas?|ingles|frances|portugues|cocina|ceramica|escritura|manualidades|carpinteria|costura|tejido|huerto|aulas?|palestras?|learn|libro|lanzamiento)\b/,
    opciones:[
      {id:"escuchar", es:"Que me cuenten", en:"Just listen", pt:"Que me contem",
       pista:/\b(charlas?|conversatorios?|seminarios?|webinar|conferencias?|talks?|lectures?|palestras?|que me cuenten|escuchar|libro|lanzamiento)\b/,
       efecto:{soloEventos:true, pesos:{charla:8, clases:-5}, recurrente:-6}},
      {id:"hacer", es:"Meter las manos", en:"Hands on", pt:"Meter a mão",
       pista:/\b(taller(es)?|cursos?|clases?|workshops?|class(es)?|courses?|idiomas?|ingles|frances|portugues|cocina|ceramica|escritura|manualidades|carpinteria|costura|tejido|huerto|aulas?|hacer|manos)\b/,
       efecto:{pesos:{clases:8, idiomas:5, charla:-5}, recurrente:4}},
    ],
    pesos:{charla:12, clases:10, idiomas:9, arte:3}, horaIdeal:[9,21], bonoGratis:2,
  },
  {
    id:"barrio", guia:"chincol",
    es:["Ferias y barrio","Puestos, plaza, aire libre"],
    en:["Markets and local stuff","Stalls, the square, outdoors"],
    pt:["Feiras e bairro","Barracas, praça, ar livre"],
    dicho:{es:"de barrio", en:"local", pt:"de bairro"},
    saludo:{es:"Chincol, el pájaro más de barrio que hay. Ferias, plaza y aire libre lo conozco de memoria.",
            en:"Chincol, the most local bird there is. Markets, the square and the outdoors I know by heart.",
            pt:"Chincol, o pássaro mais de bairro que existe. Feiras, praça e ar livre conheço de cor."},
    pregunta:{es:"¿Vas a comprar o a pasear?", en:"Are you buying or just wandering?", pt:"Vai comprar ou passear?"},
    pista:/\b(ferias?|mercados?|bazar|persa|pulgas|plazas?|parques?|picnic|paseo|pasear|aire libre|cerro|markets?|outdoors?|park|hike|feira|barrio|vecinos|artesania)\b/,
    opciones:[
      {id:"comprar", es:"A comprar", en:"Buying", pt:"Comprar",
       pista:/\b(ferias?|mercados?|bazar|persa|pulgas|markets?|feira|comprar|compras|artesania)\b/,
       efecto:{soloEventos:true, catsFuertes:["feria"], senal:/\b(feria|bazar|mercado|persa|tienda|dise[ñn]o|artesan\w*)\b/i, pesos:{feria:8, aire_libre:-3}}},
      {id:"pasear", es:"Solo a pasear", en:"Just wandering", pt:"Só passear",
       pista:/\b(plazas?|parques?|picnic|paseo|pasear|aire libre|cerro|park|outdoors?|hike|caminar)\b/,
       efecto:{soloEventos:true, catsFuertes:["aire_libre"], senal:/\b(parque|plaza|cerro|aire libre|paseo|picnic|jard[ií]n)\b/i, pesos:{aire_libre:8, familia:3}}},
    ],
    pesos:{feria:12, aire_libre:11, familia:4, musica:2, otros:2}, horaIdeal:[10,20],
    bonoGratis:4, soloPuntual:true,
  },
  {
    id:"ninos", guia:"pudu",
    es:["Con niños","Panoramas y talleres para ellos"],
    en:["With kids","Plans and classes for them"],
    pt:["Com crianças","Programas e oficinas para elas"],
    dicho:{es:"con niños", en:"with kids", pt:"com crianças"},
    saludo:{es:"Pudú. Mido cuarenta centímetros, así que veo Santiago a la altura de los cabros chicos. De esto hay poco y te lo voy a decir derecho.",
            en:"Pudú. I'm forty centimetres tall, so I see Santiago at kid height. There isn't much of this, and I'll say so plainly.",
            pt:"Pudu. Tenho quarenta centímetros, então vejo Santiago na altura das crianças. Disso tem pouco e vou te dizer na lata."},
    pregunta:{es:"¿Un panorama o un taller para que se metan?", en:"An outing, or a class they can join?", pt:"Um programa ou uma oficina para entrarem?"},
    opciones:[
      {id:"panorama", es:"Un panorama", en:"An outing", pt:"Um programa",
       pista:/\b(panorama|salir|funcion|obra|cine|feria|parque|plaza|paseo)\b/,
       efecto:{soloEventos:true, pesos:{familia:4, teatro:2, feria:2}}},
      {id:"taller", es:"Un taller fijo", en:"A regular class", pt:"Uma oficina fixa",
       pista:/\b(taller(es)?|clases?|cursos?|natacion|futbol|deporte|escuela|class(es)?|aulas?)\b/,
       efecto:{soloTalleres:true, recurrente:6, pesos:{deporte:6, clases:4}}},
    ],
    /* Misma allowlist que la compañía "con niños": sin señal positiva no sale.
       Y sin `soloPuntual`, porque el taller es la mitad de la respuesta. */
    exige: ev => ev.paraNinos,
    pesos:{familia:12, teatro:8, feria:8, aire_libre:8, deporte:8, clases:6, musica:6, cine:5, arte:5, charla:3, otros:3},
    horaIdeal:[9,19], bonoGratis:3, techoPrecio:15000,
  },
  {
    id:"gratis", guia:"degu",
    es:["Sin gastar un peso","Solo lo liberado"],
    en:["Without spending a peso","Free entry only"],
    pt:["Sem gastar nada","Só o gratuito"],
    dicho:{es:"sin gastar un peso", en:"without spending a peso", pt:"sem gastar nada"},
    saludo:{es:"Degú. Vivo en el cerro sin pagar arriendo y anoto todo lo que no cuesta nada. Acá lo gratis va primero.",
            en:"Degu. I live on the hill rent-free and I write down everything that costs nothing. Free comes first here.",
            pt:"Degu. Moro no morro sem pagar aluguel e anoto tudo o que não custa nada. Aqui o grátis vem primeiro."},
    pregunta:{es:"¿De qué tipo?", en:"What kind of thing?", pt:"De que tipo?"},
    pista:/\b(gratis|gratuit[oa]s?|liberad[oa]s?|sin pagar|sin plata|cero peso|free|gratis)\b/,
    opciones:[
      {id:"musica", es:"Música y fiesta", en:"Music and parties", pt:"Música e festa",
       pista:/\b(musica|concierto|tocata|fiesta|carrete|bailar)\b/,
       efecto:{soloEventos:true, pesos:{musica:8, fiesta:8}}},
      {id:"escenario", es:"Teatro, cine y arte", en:"Theatre, film and art", pt:"Teatro, cinema e arte",
       pista:/\b(teatro|cine|arte|expo|museo|obra)\b/,
       efecto:{soloEventos:true, pesos:{teatro:8, cine:8, arte:8}}},
      {id:"charla", es:"Charlas", en:"Talks", pt:"Palestras",
       pista:/\b(charla|conversatorio|seminario|conferencia)\b/,
       efecto:{soloEventos:true, pesos:{charla:8}}},
      {id:"afuera", es:"Afuera y de barrio", en:"Outdoors and local", pt:"Ao ar livre e de bairro",
       pista:/\b(feria|parque|plaza|aire libre|afuera|barrio|cerro)\b/,
       efecto:{soloEventos:true, pesos:{feria:8, aire_libre:8, familia:6}}},
      {id:"taller", es:"Un taller gratis", en:"A free class", pt:"Uma oficina grátis",
       pista:/\b(taller(es)?|clases?|cursos?|deporte|natacion|yoga)\b/,
       efecto:{soloTalleres:true, recurrente:6, pesos:{deporte:6, clases:6}}},
      {id:"cualquiera", es:"Lo que sea, pero gratis", en:"Anything, as long as it's free", pt:"Qualquer coisa, mas grátis",
       pista:/\b(lo que sea|cualquier|whatever|qualquer)\b/,
       efecto:{soloEventos:true, pesos:{}}},
    ],
    pesos:{}, base:6, bonoGratis:0, soloGratis:true, variedad:true,
  },
  {
    id:"comer", guia:"guaren", dominio:"descuentos",
    es:["Salir a comer","Con descuento de banco"],
    en:["Eating out","With a bank discount"],
    pt:["Sair para comer","Com desconto de banco"],
    dicho:{es:"para comer", en:"to eat out", pt:"para comer"},
    saludo:{es:"Guarén. Acá te dicen rata por cuidar la plata; yo me lo tomé como cargo y me sé de memoria qué día conviene salir a comer.",
            en:"Guarén rat. Here they call you a rat for looking after your money; I took it as a job title, and I know by heart which day is worth eating out.",
            pt:"Guarén. No Chile chamam de rato quem cuida do dinheiro; eu levei como cargo e sei de cor que dia compensa sair para comer."},
    pregunta:{es:"¿Qué se te antoja comer?", en:"What do you feel like eating?", pt:"O que você quer comer?"},
    pista:/\b(comer|almorzar|almuerzo|cenar|cena|restaurantes?|restoran(es)?|cafes?|cafeterias?|sushi|pizza|hamburguesas?|descuentos?|banco|tarjeta|eat(ing)?|dinner|lunch|brunch|comida|jantar|almoco|dcto|dctos)\b/,
    opciones:[
      {id:"restaurante", es:"Un restaurante", en:"A restaurant", pt:"Um restaurante",
       pista:/\b(restaurantes?|restoran(es)?|almorzar|almuerzo|cenar|cena|dinner|lunch|jantar|almoco|sushi|pizza|parrilla|peruan[ao]|chin[ao]|italian[ao])\b/,
       cats:["restaurantes","restaurantes-y-bares"]},
      {id:"cafe", es:"Un café", en:"A café", pt:"Um café",
       pista:/\b(cafes?|cafeterias?|coffee|brunch|pasteleria|once|onces)\b/,
       cats:["cafeterias","cafeteria"]},
      {id:"rapida", es:"Algo rápido", en:"Something quick", pt:"Algo rápido",
       pista:/\b(rapid[oa]|hamburguesas?|completos?|sandwich|fast|lanche|al paso)\b/,
       cats:["comida_rapida","comida-rapida","antojos"]},
      {id:"gourmet", es:"Algo gourmet", en:"Something fancy", pt:"Algo gourmet",
       pista:/\b(gourmet|fancy|elegante|fin[oa]|lujo|delicatessen)\b/,
       cats:["gourmet","sabores-gourmet","gourmet-y-delicatessen","40-de-descuento-visa"]},
    ],
  },
];
const situacionPorId = id => SITUACIONES.find(s => s.id === id);
const situacionPorGuia = g => SITUACIONES.find(s => s.guia === g);

/* Qué situaciones tienen sentido con cada compañía. No es cosmético: ofrecer
   "salir de noche" a alguien que anda con un niño de cinco es ofrecerle algo
   que no le vamos a poder cumplir. */
const VETOS = {ninos:["noche"], pareja:[], amigos:[], solo:[]};
const situacionesDe = comp => SITUACIONES.filter(s =>
  !(VETOS[comp] || []).includes(s.id));

/* ¿Este evento calza FUERTE con la repregunta? Es lo que manda el +10 del
   puntaje y lo que se cuenta en la opción ("Rock y metal · 118"): una
   subcategoría del clasificador, una categoría entera sin subcategoría que
   la contradiga, o una palabra del título. */
function esFuerte(ev, aj){
  if(!aj || (!aj.subcats && !aj.senal && !aj.catsFuertes)) return false;
  if(aj.subcats && ev.subcategoria && aj.subcats.includes(ev.subcategoria)) return true;
  if(aj.catsFuertes && aj.catsFuertes.includes(ev.categoria) && !ev.subcategoria) return true;
  if(aj.senal && aj.senal.test(texto(ev))) return true;
  return false;
}
const defineFuerte = aj => !!(aj && (aj.subcats || aj.senal || aj.catsFuertes));

/* ============================================================
   EL PUNTAJE
   Legible a propósito: si mañana hay que explicar por qué salió tal evento,
   se lee esta función y se entiende.
   ============================================================ */
function puntuar(ev, sit, f){
  const comp = COMPANIAS[f.compania] || {};
  const aj = f.ajuste || {};

  /* --- Descartes duros --- */
  if(aj.soloTalleres && !ev.esTaller) return -1;
  if(aj.soloEventos && ev.esTaller) return -1;
  if(comp.exige && !comp.exige(ev)) return -1;
  if(sit.exige && !sit.exige(ev)) return -1;
  if(comp.evitarNinos && ev.paraNinos && !ev.adulto) return -1;
  if(sit.soloAdultos && ev.paraNinos) return -1;
  if((f.soloGratis || sit.soloGratis) && !ev.gratis) return -1;
  if(f.techoPlata && !ev.gratis && ev.precio && ev.precio > f.techoPlata) return -1;
  if(sit.evitar && sit.evitar.includes(ev.categoria)) return -1;
  if(f.comuna && (ev.comuna || "") !== f.comuna) return -1;
  if(f.sector && f.sector !== "todo" && !enSector(ev, f.sector)) return -1;
  if(sit.evitaSenal && sit.evitaSenal.test(texto(ev))) return -1;
  if(NO_ES_PANORAMA.test(ev.titulo || "")) return -1;

  /* Los pesos de la situación mandan; la compañía y la repregunta suman o
     restan encima, nunca reemplazan.

     `abre` decide si una tabla puede INVENTAR categorías que la situación no
     contempla. La compañía no puede: "voy solo" sube las charlas, y sin este
     candado eso metía conversatorios de Wikipedia dentro de "hacer ejercicio",
     porque la situación no tenía `charla` y la compañía se la agregaba desde
     cero. La repregunta sí puede, porque es parte de la situación. */
  const pesos = Object.assign({}, sit.pesos);
  const suma = (tabla, abre) => { for(const k in (tabla || {})){
    if(pesos[k] === undefined && !abre && sit.base === undefined) continue;
    pesos[k] = (pesos[k] !== undefined ? pesos[k] : (sit.base !== undefined ? sit.base : 0)) + tabla[k];
  }};
  suma(comp.pesos, false);
  suma(aj.pesos, true);

  /* Categorías ambiguas: para "hacer ejercicio" la categoría sola no alcanza
     fuera de `deporte`, hay que ver que el evento hable de moverse. */
  if(sit.exigeSenal && ev.categoria !== sit.categoriaSegura
     && !sit.exigeSenal.test(texto(ev))) return -1;
  /* Y hablar DE algo no es hacerlo: "Webinar: Ejercicio como regulador
     metabólico" pasa cualquier filtro de señal deportiva y no es deporte. */
  if(sit.noCharlas && FORMATO_CHARLA.test(ev.titulo || "")) return -1;

  /* Un taller semanal no es respuesta a "qué hago el sábado". Donde la
     situación es de panorama puntual se descarta, no se penaliza: penalizarlo
     lo hundía en el ranking pero igual asomaba cuando había pocos candidatos,
     que es justo cuando más se nota. La repregunta puede levantar el veto
     (el Chungungo lo hace cuando le piden taller fijo). */
  if(sit.soloPuntual && ev.recurrente && !(aj.recurrente > 0)) return -1;

  /* Piso de pertinencia. Los bonos de abajo suman hasta ~22 puntos, así que
     sin este corte un evento que NO calza se cuela por estar bien presentado
     — así apareció un taller de audiciones de $40.000 recomendado para niños. */
  const peso = pesos[ev.categoria] !== undefined ? pesos[ev.categoria] : sit.base;
  if(peso === undefined || peso <= 0) return -1;
  let p = peso;

  /* --- La repregunta: lo que calza fuerte va adelante --- */
  if(esFuerte(ev, aj)) p += (aj.bonoFuerte !== undefined ? aj.bonoFuerte : 10);

  /* --- Taller vs panorama ---
     Manda la repregunta si la hay; si no, la compañía; si no, la situación. */
  if(ev.recurrente){
    const r = aj.recurrente !== undefined ? aj.recurrente
            : comp.recurrente !== undefined ? comp.recurrente
            : sit.soloPuntual ? -9 : -2;
    p += r;
  }

  /* --- Lo gratis va primero: es la promesa del proyecto, no un detalle --- */
  if(ev.gratis) p += (sit.bonoGratis !== undefined ? sit.bonoGratis : 2);
  const techo = comp.techoPrecio || sit.techoPrecio;
  if(techo && ev.precio > techo) p -= 6;

  /* --- Señales de texto --- */
  const t = texto(ev);
  if(comp.senalBuena && comp.senalBuena.test(t)) p += (comp.bonoSenal || 3);
  if(f.compania !== "ninos" && sit.id !== "ninos" && ev.paraNinos && f.compania !== "solo") p -= 3;

  /* --- Horario. Muchos eventos vienen a las 00:00 porque la fuente no
     publicó hora: a esos no se les premia ni castiga, quedan neutros. --- */
  const h = ev.fecha.getHours();
  const tieneHora = h !== 0 || ev.fecha.getMinutes() !== 0;
  const franja = aj.horaIdeal || comp.horaIdeal || sit.horaIdeal;
  if(tieneHora && franja){
    const [d, a] = franja;
    p += (d <= a ? (h >= d && h <= a) : (h >= d || h <= a)) ? 3 : -2;
  }

  /* --- Qué tan recomendable es la ficha en sí --- */
  if(ev.imagen) p += 2;
  if((ev.descripcion || "").length > 60) p += 1;
  if(ev.precision === "sin_ubicar") p -= 2;
  else if(ev.precision === "recinto") p += 1;

  /* A igualdad de puntaje, primero lo que ocurre antes. El techo importa
     tanto como el piso: sin él, una temporada que abrió hace un año y medio
     —`fecha` en el pasado— sumaba 60 puntos y la muestra de Matta salía
     primera en TODAS las listas, incluida "quiero reírme un rato". */
  p += Math.min(3, Math.max(0, 3 - ((ev.fecha - Date.now()) / 86400000) * 0.12));
  return p;
}

/* Ordena y evita que las tres recomendaciones salgan del mismo lugar o sean
   el mismo taller repetido: tres funciones del mismo teatro no son tres
   panoramas, son uno. */
function rankear(eventos, sit, filtros){
  const aj = filtros.ajuste || {};
  const hayFuerte = defineFuerte(aj);
  /* Dos criterios de orden y en este orden: primero si calza con lo que
     pediste, después el puntaje. Sin el primero, la repregunta se convertía
     en una mentira: de natación había 217 y en los tres primeros salían dos,
     porque el tercero lo desplazaba el reparto por fuente de más abajo. */
  const puntuados = eventos
    .map(ev => ({ev, p: puntuar(ev, sit, filtros), f: hayFuerte && esFuerte(ev, aj) ? 1 : 0}))
    .filter(x => x.p > 0)
    .sort((a, z) => (z.f - a.f) || (z.p - a.p));

  const fuentes = new Set(), familias = new Set(), titulos = new Set();
  const primera = [], resto = [];
  for(const {ev} of puntuados){
    /* Repartir por fuente evita tres funciones del mismo teatro. Los talleres
       NO se reparten: su fuente es el municipio —1.127 de Ñuñoa— y su recinto
       es el polideportivo, donde boxeo, taekwondo y natación son tres talleres
       distintos y no tres repeticiones del mismo. Ahí basta el reparto por
       título. Repartiéndolos por recinto, "artes marciales en el norte"
       mostraba dos de los once que hay: los otros nueve estaban en los mismos
       dos gimnasios municipales. */
    const fuente = ev.esTaller ? null : (ev.fuente || ev.lugar || ev.id);
    if((fuente && fuentes.has(fuente)) || titulos.has(tituloBase(ev.titulo))
       || (sit.variedad && familias.has(ev.categoria))){ resto.push(ev); continue; }
    if(fuente) fuentes.add(fuente);
    familias.add(ev.categoria); titulos.add(tituloBase(ev.titulo));
    primera.push(ev);
  }
  // Los descartados por repetición no se botan: van al final, para "ver más".
  return primera.concat(resto);
}

/* ============================================================
   BÚSQUEDA POR PALABRA
   Para lo que no es una situación: "blondie", "los tres", "matucana".
   Título, lugar, comuna y fuente, sin tildes, todas las palabras. Es la
   misma regla de `coincideBusqueda` del mapa, repetida acá para que el
   motor siga corriendo sin navegador.
   ============================================================ */
const sinTildes = s => String(s ?? "").normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "").toLowerCase();
function coincidePalabras(ev, palabras){
  if(!palabras || !palabras.length) return true;
  const pajar = sinTildes([ev.titulo, ev.lugar, ev.comuna, ev.fuente].join(" "));
  return palabras.every(p => pajar.includes(sinTildes(p)));
}

/* ============================================================
   EL INTÉRPRETE DE TEXTO LIBRE
   "jazz el sábado en ñuñoa con mi polola" tiene que salir de acá como
   {situacion:"musica", opcion:"clasica", cuando:"dia", dia:6,
    comuna:"Ñuñoa", compania:"pareja"}. Sin modelo de lenguaje: listas de
   palabras en tres idiomas, en orden de especificidad. No entiende todo,
   y cuando no entiende lo dice — que es mejor que adivinar.

   Lo que no se reconoció como nada queda en `palabras`, para buscar por
   título: el nombre de un local, de una banda, de una fiesta.
   ============================================================ */
const DIAS_PISTA = [
  [0, /\b(domingo|sunday|sun)\b/], [1, /\b(lunes|monday|mon|segunda)\b/],
  [2, /\b(martes|tuesday|tue|terca)\b/], [3, /\b(miercoles|wednesday|wed|quarta)\b/],
  [4, /\b(jueves|thursday|thu|quinta)\b/], [5, /\b(viernes|friday|fri|sexta)\b/],
  [6, /\b(sabado|saturday|sat)\b/],
];
const CUANDO_PISTA = [
  ["noche",  /\b(esta noche|tonight|hoje a noite|a noite|de noche|en la noche|en la nochecita)\b/],
  ["finde",  /\b(finde|fin de semana|fds|weekend|fim de semana|este finde)\b/],
  ["hoy",    /\b(hoy|hoy dia|today|hoje|ahora|now|agora)\b/],
  ["manana", /\b(manana|tomorrow|amanha)\b/],
  ["semana", /\b(esta semana|this week|estos dias|proximos dias|la semana|semana|week|nestes dias)\b/],
  ["todo",   /\b(cuando sea|cualquier dia|cualquier fecha|any ?time|whenever|quando for|qualquer dia|sin fecha)\b/],
];
const PLATA_PISTA = [
  ["gratis", /\b(gratis|gratuit[oa]s?|liberad[oa]s?|sin pagar|sin plata|cero peso|free|de gratis)\b/],
  ["barato", /\b(barat[oa]s?|baratito|cheap|economic[oa]s?|poca plata|barato)\b/],
];
const SECTOR_PISTA = [
  ["centro",  /\b(el centro|centro de santiago|santiago centro|downtown|centro)\b/],
  ["oriente", /\b(oriente|el oriente|sector oriente|east|zona leste)\b/],
  ["norte",   /\b(el norte|sector norte|norte|north)\b/],
  ["sur",     /\b(el sur|sector sur|sur|poniente|el poniente|south|west)\b/],
];
const COMUNAS = [].concat(...Object.values(SECTORES)).filter(c => c !== "Santiago");
const STOP = new Set(("de del la el los las un una unos unas y o u e en a al con para por que quiero busco " +
  "algo hay me te se ver ir donde cerca tengo ganas dame muestrame muestra recomienda recomiendame " +
  "quisiera quiere queremos vamos voy este esta esto eso ese esa mi mis tu tus su sus lo le les " +
  "the an to for in on with i want some something show find get go at of is it my we " +
  "um uma com para quero algo tem mostra me ver o a os as do da dos das no na nos nas e " +
  "bueno buena bonito lindo cool mas menos muy bien ok dale ya porfa por favor please " +
  "panorama panoramas plan planes cosa cosas evento eventos actividad actividades " +
  "taller talleres clase clases curso cursos hacer salir meterme meter buscar probar tomar algun alguna " +
  "want wanna like looking").split(/\s+/));

function interpretar(entrada){
  const crudo = String(entrada || "");
  let resto = " " + sinTildes(crudo).replace(/[¿?¡!.,;:()"'«»]/g, " ").replace(/\s+/g, " ") + " ";
  const r = {palabras:[], entendio:[]};
  const toma = re => {
    const m = resto.match(re);
    if(!m) return null;
    resto = resto.replace(new RegExp(re.source, "g"), " ");
    return m;
  };

  /* Comandos enteros: "más", "otra cosa", "mapa". */
  if(/^\s*(mas|more|mais|otros|otras|tres mas|ver mas|show more|dame mas|sigue|siguiente|next|outros)\s*$/.test(resto))
    return {comando:"mas"};
  if(/\b(otra cosa|de nuevo|empezar|empecemos|reiniciar|volver a empezar|start over|restart|outra coisa|de novo|recomenzar)\b/.test(resto))
    return {comando:"otra"};
  if(/^\s*(mapa|map|ver (el )?mapa|el mapa)\s*$/.test(resto))
    return {comando:"mapa"};

  /* Cuándo: primero los días con nombre ("el viernes"), después las frases. */
  for(const [dia, re] of DIAS_PISTA){ if(toma(re)){ r.cuando = "dia"; r.dia = dia; break; } }
  for(const [id, re] of CUANDO_PISTA){
    const m = toma(re);
    if(m && !r.cuando) r.cuando = id;
    /* "esta noche" es hoy CON preferencia nocturna, pero si además dijiste un
       día ("el viernes en la noche"), el día manda y la noche queda de ajuste. */
    if(m && id === "noche") r.deNoche = true;
  }

  for(const [id, re] of PLATA_PISTA){ if(toma(re)){ r.plata = id; break; } }

  /* Comuna antes que sector: "ñuñoa" también dice "oriente", y la comuna es
     el dato más fino. "Santiago" no cuenta como comuna: es la ciudad. */
  for(const c of COMUNAS){
    const re = new RegExp("\\b" + sinTildes(c).replace(/\s+/g, "\\s+") + "\\b");
    if(toma(re)){ r.comuna = c; r.sector = sectorDeComuna(c); break; }
  }
  if(!r.comuna) for(const [id, re] of SECTOR_PISTA){ if(toma(re)){ r.sector = id; break; } }

  /* Situación y opción. El orden importa: "taller de yoga" es deporte aunque
     diga taller, "charla de cine" es aprender aunque diga cine. Las palabras
     de taller/curso/clase mandan a aprender antes que a escenario o música
     ("taller de fotografía", "clase de canto"), salvo que el deporte ya haya
     reclamado el texto. */
  const hablaDeTaller = /\b(taller(es)?|cursos?|clases?|workshops?|class(es)?|courses?|aulas?|charlas?|conversatorios?|seminarios?|conferencias?|webinar|talks?|lectures?|palestras?)\b/.test(resto);
  const orden = ["comer","mover"].concat(hablaDeTaller ? ["aprender"] : [])
    .concat(["noche","escenario","musica","aprender","barrio","gratis","panorama"]);
  for(const id of orden){
    const sit = situacionPorId(id);
    if(!sit.pista || !sit.pista.test(resto)) continue;
    r.situacion = id;
    /* La opción se busca en el texto ENTERO antes de borrar la pista de la
       situación: "rock" es pista de música Y de su opción "rock y metal". */
    const opcion = (sit.opciones || []).find(o => o.pista && o.pista.test(resto));
    if(opcion) r.opcion = opcion.id;
    resto = resto.replace(new RegExp(sit.pista.source, "g"), " ");
    if(opcion) resto = resto.replace(new RegExp(opcion.pista.source, "g"), " ");
    break;
  }

  /* Con quién. Va después de la situación porque "con niños" es compañía,
     pero también decide la situación cuando no hay otra. */
  for(const id of ORDEN_COMPANIAS){
    if(toma(COMPANIAS[id].pista)){ r.compania = id; break; }
  }
  if(!r.situacion && r.compania === "ninos"){ r.situacion = "ninos"; }
  if(!r.situacion && r.plata === "gratis"){ r.situacion = "gratis"; }

  /* "noche" suelta, sin carrete: es la hora, no la situación. */
  if(toma(/\b(noche|night|nocturno|nocturna|tarde en la noche)\b/) && !r.cuando){ r.cuando = "noche"; r.deNoche = true; }
  if(toma(/\b(en la tarde|tarde|afternoon|a tarde)\b/)) r.deTarde = true;

  /* Lo que sobra es búsqueda por palabra: nombres de locales, bandas, fiestas. */
  r.palabras = resto.split(" ")
    .map(p => p.trim())
    .filter(p => p.length >= 3 && !STOP.has(p) && !/^\d+$/.test(p))
    .slice(0, 4);

  r.vacio = !r.situacion && !r.cuando && !r.plata && !r.comuna && !r.sector
    && !r.compania && !r.palabras.length;
  return r;
}

const API = {PATRON_DIAS, tituloBase, marcar, esParaNinos, SECTORES, enSector, sectorDeComuna,
             COMUNAS, COMPANIAS, ORDEN_COMPANIAS, SITUACIONES, situacionPorId, situacionPorGuia,
             situacionesDe, VETOS, puntuar, rankear, esFuerte, defineFuerte,
             coincidePalabras, interpretar, sinTildes,
             SENAL_NINOS, SENAL_ADULTA, SENAL_PAREJA, SENAL_GRUPO,
             SENAL_DEPORTE, SENAL_FALSO_DEPORTE, FORMATO_CHARLA, NO_ES_PANORAMA};

if(typeof module === "object" && module.exports) module.exports = API;
else Object.assign(raiz, API);

})(typeof globalThis !== "undefined" ? globalThis : this);
