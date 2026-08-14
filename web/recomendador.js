/* ============================================================
   LOICA — el recomendador
   El motor que decide qué panorama sale. Vive aparte de la página a
   propósito: así se puede correr contra eventos.json sin navegador y
   probar de verdad cada perfil de usuario (scripts/probar_roles.js).
   Sin DOM, sin fetch, sin idioma: entra data, sale un orden.

   LO QUE HAY QUE SABER DEL CATÁLOGO, porque el diseño sale de ahí:

   1. `publico` no sirve para filtrar. 2.301 de 2.533 eventos dicen "todos",
      y los 59 de cine SIN EXCEPCIÓN — incluidos "Possession", "La posada
      maldita" y "Teenage Sex and Death at Camp Miasma". Confiar en ese campo
      es como mandar a un niño de cinco años a cualquiera de esos tres.

   2. La mitad del catálogo son talleres municipales que se repiten toda la
      semana (1.224 de 2.533). Para "quiero hacer ejercicio" son justo lo que
      se busca; para "qué hago el sábado" son ruido.

   3. Casi no hay panoramas infantiles puntuales: `familia` tiene 66 eventos y
      57 son talleres. Quedan NUEVE. Eso no se arregla puntuando mejor, se
      arregla diciéndolo.
   ============================================================ */
(function (raiz) {
"use strict";

/* ---------- Talleres recurrentes ----------
   La señal no está en ningún campo, está en el título, y son dos cruzadas:
   el título normalizado se repite (hay que sacarle días y horas, porque el
   mismo taller viene como "Yoga Lu-Mi 09:00" y "Yoga Ma-Ju 19:30"), o el
   título trae el patrón de días — "Hapkido Lu-Mi-Vi 20:00" aparece UNA vez
   en todo el catálogo y la repetición sola nunca lo iba a pillar. */
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
].map(x => "\\b" + x + "\\b").join("|"), "i");

/* Formato "alguien te cuenta": sirve para separar hacer de escuchar. */
const FORMATO_CHARLA = /\b(webinar|conversatorio|charla|seminario|coloquio|panel|foro|conferencia|mesa redonda|clase magistral|masterclass|lanzamiento de libro|presentaci[óo]n del libro)\b/i;

const texto = ev => ((ev.titulo || "") + " " + (ev.descripcion || ""));
const esParaNinos = ev =>
  !SENAL_ADULTA.test(texto(ev)) &&
  (ev.publico === "ninos" || SENAL_NINOS.test(texto(ev)));

/* Marca cada evento una vez, al cargar. `recurrente` y `paraNinos` se
   consultan en cada puntaje, así que se calculan una sola vez. */
function marcar(eventos){
  const cuenta = new Map();
  eventos.forEach(e => {
    const k = tituloBase(e.titulo);
    cuenta.set(k, (cuenta.get(k) || 0) + 1);
  });
  eventos.forEach(e => {
    e.recurrente = (cuenta.get(tituloBase(e.titulo)) || 0) > 3
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
  sur:    ["La Florida","Puente Alto","Maipú","La Pintana","San Miguel","La Granja","El Bosque","Pudahuel","San Bernardo","Lo Espejo","San Joaquín"],
};
const enSector = (ev, s) => s === "todo" || (SECTORES[s] || []).includes(ev.comuna);

/* ============================================================
   CON QUIÉN VAS
   El eje que faltaba, y el que más cambia una recomendación. "Teatro" no
   significa lo mismo para alguien que va en pareja un viernes que para una
   mamá con un niño de cinco: es la misma categoría y son dos panoramas
   distintos. Antes esto no se preguntaba y por eso una película de terror
   podía salir como plan infantil.

   `exige` es una allowlist: si está, el evento tiene que pasarla o queda
   fuera, pase lo que pase con el resto del puntaje.
   ============================================================ */
const COMPANIAS = {
  solo: {
    es:["Voy solo","A mi ritmo"], en:["On my own","At my own pace"], pt:["Vou sozinho","No meu ritmo"],
    dicho:{es:"solo", en:"on your own", pt:"sozinho"},
    pesos:{charla:4, arte:3, cine:3, clases:3, fiesta:-2},
    recurrente:1,
  },
  pareja: {
    es:["En pareja","Una cita"], en:["As a couple","A date"], pt:["A dois","Um encontro"],
    dicho:{es:"en pareja", en:"as a couple", pt:"a dois"},
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
    pesos:{fiesta:6, musica:5, deporte:3, feria:2, charla:-3, arte:-2},
    recurrente:-5,
    horaIdeal:[16,3],
    senalBuena:SENAL_GRUPO, bonoSenal:4,
    evitarNinos:true,
  },
  ninos: {
    es:["Con niños","Van cabros chicos"], en:["With kids","Children coming"], pt:["Com crianças","Vão crianças"],
    dicho:{es:"con niños", en:"with kids", pt:"com crianças"},
    /* ALLOWLIST. Es la única compañía que exige evidencia positiva, y es
       deliberado: el costo de equivocarse acá no es un panorama fome, es una
       mamá con un niño de cinco años en una función de terror. Si el evento
       no dice en ninguna parte que es para niños, no se recomienda para
       niños. Prefiero quedarme corto de opciones y decirlo. */
    exige: ev => ev.paraNinos,
    pesos:{familia:6, teatro:4, feria:4, aire_libre:4, cine:2},
    horaIdeal:[9,19],
    techoPrecio:15000,
  },
};

/* ============================================================
   LAS SITUACIONES
   El usuario elige una situación de su vida, no una categoría, y cada
   situación reparte puntaje entre varias. "Ferias y barrio" no es
   `categoria == feria` — son 14 en todo el catálogo — es feria + aire libre
   + clases + familia ordenados por qué tan bien calzan.

   `soloPuntual` marca las situaciones donde un taller semanal no es una
   respuesta: nadie pide "algo para el sábado" y quiere un curso de los
   miércoles. `soloTaller` es el caso inverso, donde el taller ES la
   respuesta.
   ============================================================ */
const SITUACIONES = [
  {
    id:"panorama", guia:"loica",
    es:["Algo que hacer","Sorpréndeme con lo mejor"],
    en:["Something to do","Surprise me with the best"],
    pt:["Algo para fazer","Me surpreenda com o melhor"],
    dicho:{es:"", en:"", pt:""},
    saludo:{es:"Entonces me quedo yo, que para eso soy la anfitriona. Te muestro lo mejor que haya.",
            en:"Then I'll stay on — that's what being the host is for. I'll show you the best there is.",
            pt:"Então eu fico, que para isso sou a anfitriã. Te mostro o melhor que tiver."},
    pregunta:{es:"¿Te llevo a lo seguro o a algo raro?", en:"Shall I play it safe or take you somewhere odd?", pt:"Te levo no seguro ou em algo estranho?"},
    opciones:[
      {id:"seguro", es:"A lo seguro", en:"Play it safe", pt:"No seguro",
       efecto:{pesos:{musica:4, teatro:4, cine:3, feria:3}}},
      {id:"raro", es:"Algo distinto", en:"Something different", pt:"Algo diferente",
       efecto:{pesos:{otros:6, charla:4, arte:3, musica:-2}}},
    ],
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
    pregunta:{es:"¿Qué tan fuerte?", en:"How loud?", pt:"Quão alto?"},
    opciones:[
      {id:"suave", es:"Algo suave", en:"Something gentle", pt:"Algo suave",
       efecto:{pesos:{musica:5, teatro:4, fiesta:-9}, horaIdeal:[17,23]}},
      {id:"fuerte", es:"Que suene fuerte", en:"Loud", pt:"Bem alto",
       efecto:{pesos:{musica:6, fiesta:6}, horaIdeal:[19,3]}},
    ],
    pesos:{musica:12, fiesta:6}, horaIdeal:[18,2], bonoGratis:1, soloPuntual:true,
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
    pregunta:{es:"¿Sala oscura o algo en vivo?", en:"Dark room, or live?", pt:"Sala escura ou ao vivo?"},
    opciones:[
      {id:"cine", es:"Cine", en:"Film", pt:"Cinema",
       efecto:{pesos:{cine:8, teatro:-5, arte:-3}}},
      {id:"vivo", es:"Con gente en escena", en:"People on stage", pt:"Com gente no palco",
       efecto:{pesos:{teatro:8, cine:-6}}},
      {id:"mirar", es:"Una expo, a mi ritmo", en:"An exhibition, at my pace", pt:"Uma expo, no meu ritmo",
       efecto:{pesos:{arte:8, cine:-4, teatro:-4}}},
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
    pregunta:{es:"¿Hasta qué hora estás dispuesto?", en:"How late are you willing to go?", pt:"Até que horas você aguenta?"},
    opciones:[
      {id:"temprano", es:"Después de comida no más", en:"Just after dinner", pt:"Só depois do jantar",
       efecto:{horaIdeal:[19,23], pesos:{musica:4, teatro:3}}},
      {id:"tarde", es:"Hasta que cierren", en:"Until they close", pt:"Até fecharem",
       efecto:{horaIdeal:[21,4], pesos:{fiesta:6}}},
    ],
    pesos:{fiesta:12, musica:8}, horaIdeal:[20,3], bonoGratis:0,
    soloPuntual:true, soloAdultos:true,
  },
  {
    id:"mover", guia:"chungungo",
    es:["Hacer ejercicio","Deporte y aire libre"],
    en:["Exercise","Sport and the outdoors"],
    pt:["Fazer exercício","Esporte e ar livre"],
    dicho:{es:"para moverte", en:"to get moving", pt:"para se mexer"},
    saludo:{es:"Chungungo, la nutria del Mapocho. Me muevo, me mojo y no paro nunca.",
            en:"Chungungo, the Mapocho river otter. Always moving, always wet, never still.",
            pt:"Chungungo, a lontra do Mapocho. Me mexo, me molho e não paro nunca."},
    /* Acá la repregunta SÍ separa dos cosas distintas de verdad: 451 de los
       494 eventos de deporte son talleres municipales con cupo, y 43 son
       actividades sueltas. Son dos respuestas a dos preguntas distintas. */
    pregunta:{es:"¿Algo suelto o para meterse todas las semanas?",
              en:"A one-off, or something weekly?",
              pt:"Algo solto ou para toda semana?"},
    opciones:[
      {id:"suelto", es:"Una vez, a probar", en:"Just once, to try", pt:"Uma vez, para provar",
       efecto:{recurrente:-8, pesos:{aire_libre:6, deporte:3}}},
      {id:"taller", es:"Un taller fijo", en:"A regular class", pt:"Uma oficina fixa",
       efecto:{recurrente:6, pesos:{deporte:5, clases:4}}},
    ],
    pesos:{deporte:12, aire_libre:11, clases:5, familia:4, otros:3},
    horaIdeal:[7,21], bonoGratis:3,
    exigeSenal:SENAL_DEPORTE, categoriaSegura:"deporte", noCharlas:true,
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
    opciones:[
      {id:"escuchar", es:"Que me cuenten", en:"Just listen", pt:"Que me contem",
       efecto:{pesos:{charla:8, clases:-5}, recurrente:-6}},
      {id:"hacer", es:"Meter las manos", en:"Hands on", pt:"Meter a mão",
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
    opciones:[
      {id:"comprar", es:"A comprar", en:"Buying", pt:"Comprar",
       efecto:{pesos:{feria:8, aire_libre:-3}}},
      {id:"pasear", es:"Solo a pasear", en:"Just wandering", pt:"Só passear",
       efecto:{pesos:{aire_libre:8, familia:3}}},
    ],
    pesos:{feria:12, aire_libre:11, familia:4, musica:2}, horaIdeal:[10,20],
    bonoGratis:4, soloPuntual:true,
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
    opciones:[
      {id:"restaurante", es:"Un restaurante", en:"A restaurant", pt:"Um restaurante",
       cats:["restaurantes","restaurantes-y-bares"]},
      {id:"cafe", es:"Un café", en:"A café", pt:"Um café", cats:["cafeterias","cafeteria"]},
      {id:"rapida", es:"Algo rápido", en:"Something quick", pt:"Algo rápido",
       cats:["comida-rapida","antojos"]},
      {id:"gourmet", es:"Algo gourmet", en:"Something fancy", pt:"Algo gourmet",
       cats:["sabores-gourmet","gourmet-y-delicatessen","40-de-descuento-visa"]},
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

/* ============================================================
   EL PUNTAJE
   Legible a propósito: si mañana hay que explicar por qué salió tal evento,
   se lee esta función y se entiende.
   ============================================================ */
function puntuar(ev, sit, f){
  const comp = COMPANIAS[f.compania] || {};

  /* --- Descartes duros --- */
  if(comp.exige && !comp.exige(ev)) return -1;
  if(comp.evitarNinos && ev.paraNinos && !ev.adulto) return -1;
  if(sit.soloAdultos && ev.paraNinos) return -1;
  if(f.soloGratis && !ev.gratis) return -1;
  if(f.techoPlata && !ev.gratis && ev.precio && ev.precio > f.techoPlata) return -1;
  if(sit.evitar && sit.evitar.includes(ev.categoria)) return -1;
  if(f.sector && f.sector !== "todo" && !enSector(ev, f.sector)) return -1;

  const aj = f.ajuste || {};
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

  /* Piso de pertinencia. Los bonos de abajo suman hasta ~12 puntos, así que
     sin este corte un evento que NO calza se cuela por estar bien presentado
     — así apareció un taller de audiciones de $40.000 recomendado para niños. */
  const peso = pesos[ev.categoria] !== undefined ? pesos[ev.categoria] : sit.base;
  if(peso === undefined || peso <= 0) return -1;
  let p = peso;

  /* --- Taller vs panorama ---
     El eje más informativo del catálogo: 1.224 talleres contra 1.309
     panoramas puntuales. Manda la repregunta si la hay; si no, la compañía;
     si no, la situación. */
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
  if(f.compania !== "ninos" && ev.paraNinos && f.compania !== "solo") p -= 3;

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

  // A igualdad de puntaje, primero lo que ocurre antes.
  p += Math.max(0, 3 - ((ev.fecha - Date.now()) / 86400000) * 0.12);
  return p;
}

/* Ordena y evita que las tres recomendaciones salgan del mismo lugar o sean
   el mismo taller repetido: tres funciones del mismo teatro no son tres
   panoramas, son uno. */
function rankear(eventos, sit, filtros){
  const puntuados = eventos
    .map(ev => ({ev, p: puntuar(ev, sit, filtros)}))
    .filter(x => x.p > 0)
    .sort((a, z) => z.p - a.p);

  const fuentes = new Set(), familias = new Set(), titulos = new Set();
  const primera = [], resto = [];
  for(const {ev} of puntuados){
    const fuente = ev.fuente || ev.lugar || ev.id;
    if(fuentes.has(fuente) || titulos.has(tituloBase(ev.titulo))
       || (sit.variedad && familias.has(ev.categoria))){ resto.push(ev); continue; }
    fuentes.add(fuente); familias.add(ev.categoria); titulos.add(tituloBase(ev.titulo));
    primera.push(ev);
  }
  // Los descartados por repetición no se botan: van al final, para "ver más".
  return primera.concat(resto);
}

const API = {PATRON_DIAS, tituloBase, marcar, esParaNinos, SECTORES, enSector,
             COMPANIAS, SITUACIONES, situacionPorId, situacionPorGuia,
             situacionesDe, VETOS, puntuar, rankear,
             SENAL_NINOS, SENAL_ADULTA, SENAL_PAREJA, SENAL_GRUPO,
             SENAL_DEPORTE, FORMATO_CHARLA};

if(typeof module === "object" && module.exports) module.exports = API;
else Object.assign(raiz, API);

})(typeof globalThis !== "undefined" ? globalThis : this);
