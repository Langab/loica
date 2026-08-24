#!/usr/bin/env node
/* ============================================================
   Prueba el recomendador poniéndose en el lugar de gente distinta.

   Existe porque probar esto a mano en el navegador es lento y engañoso: uno
   hace tres clics, ve algo razonable y da por bueno el motor. Acá cada perfil
   corre contra el catálogo completo —los dos archivos, panoramas y talleres—
   y muestra qué recibiría de verdad, con las alarmas encendidas cuando algo
   no calza. Así apareció que a una mamá con un niño el chat le mandaba a ver
   "Obsesión".

     node scripts/probar_roles.js            # perfiles + frases
     node scripts/probar_roles.js cita       # un perfil
     node scripts/probar_roles.js -v         # con puntaje y por qué
     node scripts/probar_roles.js --frases   # solo el intérprete de texto
   ============================================================ */
const fs = require("fs");
const path = require("path");
const R = require(path.join(__dirname, "..", "web", "recomendador.js"));

const RAIZ = path.join(__dirname, "..", "web");
const leer = (archivo, clave, extra) =>
  JSON.parse(fs.readFileSync(path.join(RAIZ, archivo), "utf8"))[clave]
    .map(ev => Object.assign({}, ev, extra, {fecha: new Date(ev.inicio)}));

/* El catálogo son DOS archivos desde el 15-08-2026 y el motor los mira
   juntos: la mitad de las respuestas de "hacer deporte" son talleres. */
const eventos = leer("eventos.json", "eventos", {});
const talleres = leer("talleres.json", "talleres", {esTaller: true});
const catalogo = R.marcar(eventos.concat(talleres));

const hoy = new Date(); hoy.setHours(0,0,0,0);

/* La misma ventana que usa la página, simplificada: acá basta la fecha de
   inicio porque lo que se prueba es el puntaje, no el calendario. */
const RANGOS = {
  hoy:    f => f.toDateString() === new Date().toDateString(),
  finde:  f => { const d = new Date(); const dow = d.getDay();
                 const desde = new Date(d); desde.setHours(0,0,0,0);
                 if(![5,6,0].includes(dow)) desde.setDate(desde.getDate() + (5 - dow));
                 const hasta = new Date(desde);
                 hasta.setDate(desde.getDate() + (desde.getDay() === 5 ? 2 : desde.getDay() === 6 ? 1 : 0));
                 hasta.setHours(23,59,59,999);
                 return f >= desde && f <= hasta; },
  semana: f => { const d = new Date(hoy), h = new Date(d);
                 h.setDate(d.getDate() + 7); h.setHours(23,59,59,999);
                 return f >= d && f <= h; },
  todo:   () => true,
};
/* Un taller y una temporada valen para cualquier ventana: su tarjeta es una
   serie, no una fecha. Filtrarlos por `inicio` los botaba a todos. */
const vigente = ev => (ev.fin ? new Date(ev.fin) : ev.fecha) >= hoy;
const enVentana = (ev, rango) =>
  ev.esTaller || (ev.fin && new Date(ev.fin) > ev.fecha) || RANGOS[rango](ev.fecha);
const vigentes = catalogo.filter(vigente);

/* Los perfiles son gente, no combinaciones de filtros. Cada uno trae lo que
   NO debería recibir, porque eso es lo que hay que poder detectar solo. */
const PERFILES = [
  {
    nombre:"Cita — viernes en la noche, quiere impresionar",
    compania:"pareja", situacion:"escenario", opcion:"obra",
    cuando:"finde", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.recurrente, "es un taller semanal, no una cita"],
      [ev => ev.paraNinos, "es infantil"],
      [ev => ev.categoria === "cine", "pidió gente en escena"],
    ],
  },
  {
    nombre:"Cita — quiere reírse",
    compania:"pareja", situacion:"escenario", opcion:"comedia",
    cuando:"semana", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.recurrente, "es un taller semanal"],
      [ev => ev.paraNinos, "es infantil"],
    ],
  },
  {
    nombre:"Carrete — cumpleaños con seis amigos, electrónica",
    compania:"amigos", situacion:"noche", opcion:"electronica",
    cuando:"finde", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.paraNinos, "es infantil"],
      [ev => ev.recurrente, "es un taller semanal"],
      [ev => ev.categoria === "charla", "una charla no es un carrete"],
    ],
  },
  {
    nombre:"Rock — quiere que suene fuerte",
    compania:"amigos", situacion:"musica", opcion:"rock",
    cuando:"semana", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.recurrente, "es un taller semanal"],
      [ev => !["musica","fiesta"].includes(ev.categoria), "no es música"],
    ],
  },
  {
    nombre:"Jazz y clásica — algo tranquilo",
    compania:"pareja", situacion:"musica", opcion:"clasica",
    cuando:"todo", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.categoria === "fiesta", "pidió algo tranquilo"],
      [ev => ev.recurrente, "es un taller semanal"],
    ],
  },
  {
    nombre:"Mamá — hijo de 6 años, sábado en la tarde",
    compania:"ninos", situacion:"ninos", opcion:"panorama",
    cuando:"finde", plata:"igual", sector:"todo",
    malo:[
      [ev => !ev.paraNinos, "no hay ninguna señal de que sea para niños"],
      [ev => ev.adulto, "tiene señales de contenido adulto"],
      [ev => ev.precio > 15000, "muy caro para llevar niños"],
      [ev => ev.esTaller, "pidió un panorama, no un taller"],
    ],
  },
  {
    nombre:"Mamá — quiere meter al niño a natación",
    compania:"ninos", situacion:"ninos", opcion:"taller",
    cuando:"semana", plata:"igual", sector:"todo",
    malo:[
      [ev => !ev.paraNinos, "no hay señal de que sea para niños"],
      [ev => !ev.esTaller, "pidió un taller fijo"],
    ],
  },
  {
    nombre:"Natación — quiere meterse a la piscina",
    situacion:"mover", opcion:"natacion",
    cuando:"semana", plata:"igual", sector:"todo",
    malo:[
      [ev => !ev.esTaller, "pidió un taller fijo"],
      [ev => !/nataci|nado|acuátic|acuatic|piscina|aquagym|hidro/i.test(ev.titulo + " " + ev.descripcion),
       "no habla de natación"],
    ],
  },
  {
    nombre:"Artes marciales — cerca de la casa",
    situacion:"mover", opcion:"marciales",
    cuando:"semana", plata:"igual", sector:"norte",
    malo:[
      [ev => !ev.esTaller, "pidió un taller fijo"],
      [ev => !R.enSector(ev, "norte"), "no queda en el norte"],
    ],
  },
  {
    nombre:"Deporte — solo quiere probar una vez",
    situacion:"mover", opcion:"suelto",
    cuando:"todo", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.recurrente, "pidió algo suelto y esto es un taller fijo"],
      [ev => R.SENAL_FALSO_DEPORTE.test(ev.titulo + " " + ev.descripcion),
       "no es deporte: usa la palabra para otra cosa"],
    ],
  },
  {
    nombre:"No sabe qué hacer — sábado, solo, sin plata",
    compania:"solo", situacion:"panorama", opcion:"seguro",
    cuando:"finde", plata:"gratis", sector:"todo",
    malo:[
      [ev => !ev.gratis, "pidió gratis"],
      [ev => ev.recurrente, "un taller semanal no responde '¿qué hago hoy?'"],
    ],
  },
  {
    nombre:"Cero peso — el camino del Degú",
    situacion:"gratis", opcion:"cualquiera",
    cuando:"semana", plata:"igual", sector:"todo",
    malo:[
      [ev => !ev.gratis, "el Degú solo muestra lo liberado"],
      [ev => ev.esTaller, "pidió un panorama"],
    ],
  },
  {
    nombre:"Cita barata — quieren salir sin gastar",
    compania:"pareja", situacion:"panorama", opcion:"seguro",
    cuando:"semana", plata:"gratis", sector:"todo",
    malo:[
      [ev => !ev.gratis, "pidió gratis"],
      [ev => ev.recurrente, "es un taller semanal, no una cita"],
      [ev => ev.paraNinos, "es infantil"],
    ],
  },
  {
    nombre:"Aprender — que le cuenten algo",
    compania:"solo", situacion:"aprender", opcion:"escuchar",
    cuando:"semana", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.esTaller, "pidió una charla, no un taller"],
      [ev => !["charla","clases","idiomas","arte"].includes(ev.categoria), "no es una charla"],
    ],
  },
  {
    nombre:"Barrio — feria el domingo",
    situacion:"barrio", opcion:"comprar",
    cuando:"todo", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.recurrente, "es un taller semanal"],
      [ev => ev.categoria === "fiesta", "una fiesta no es una feria"],
    ],
  },
];

/* Frases de verdad, como las escribiría alguien en el cuadro de texto. Lo
   que se prueba acá no es el puntaje sino el intérprete: qué entendió y qué
   dejó pasar. `espera` son los campos que TIENEN que salir. */
const FRASES = [
  ["jazz el sábado en ñuñoa con mi polola", {situacion:"musica", opcion:"clasica", cuando:"dia", dia:6, comuna:"Ñuñoa", compania:"pareja"}],
  ["algo gratis con niños este finde",      {situacion:"ninos", cuando:"finde", plata:"gratis", compania:"ninos"}],
  ["carrete electrónico esta noche",        {situacion:"noche", opcion:"electronica", cuando:"noche"}],
  ["quiero meterme a natación en huechuraba", {situacion:"mover", opcion:"natacion", comuna:"Huechuraba"}],
  ["stand up mañana",                       {situacion:"escenario", opcion:"comedia", cuando:"manana"}],
  ["una obra de teatro barata",             {situacion:"escenario", opcion:"obra", plata:"barato"}],
  ["feria de diseño",                       {situacion:"barrio", opcion:"comprar"}],
  ["salir a comer sushi hoy",               {situacion:"comer", opcion:"restaurante", cuando:"hoy"}],
  ["charla de historia",                    {situacion:"aprender", opcion:"escuchar"}],
  ["taller de cerámica",                    {situacion:"aprender", opcion:"hacer"}],
  ["correr el domingo",                     {situacion:"mover", opcion:"suelto", cuando:"dia", dia:0}],
  ["cine en pareja",                        {situacion:"escenario", opcion:"cine", compania:"pareja"}],
  ["algo en providencia hoy",               {comuna:"Providencia", cuando:"hoy"}],
  ["que hago hoy",                          {situacion:"panorama", cuando:"hoy"}],
  ["live music tonight",                    {situacion:"musica", cuando:"noche"}],
  ["kids theatre saturday",                 {situacion:"escenario", cuando:"dia", dia:6, compania:"ninos"}],
  ["mais",                                  {comando:"mas"}],
  ["otra cosa",                             {comando:"otra"}],
  ["matucana 100",                          {palabras:["matucana"]}],
  ["asdfgh",                                {palabras:["asdfgh"]}],
];

const verboso = process.argv.includes("-v");
const soloFrases = process.argv.includes("--frases");
const filtro = process.argv.slice(2).find(a => !a.startsWith("-"));

let alarmas = 0, vacios = 0, fallos = 0;

if(!soloFrases) for(const perfil of PERFILES){
  if(filtro && !perfil.nombre.toLowerCase().includes(filtro.toLowerCase())) continue;

  const sit = R.situacionPorId(perfil.situacion);
  const opcion = (sit.opciones || []).find(o => o.id === perfil.opcion) || {};
  const filtros = {
    compania: perfil.compania || "cualquiera",
    soloGratis: perfil.plata === "gratis",
    techoPlata: perfil.plata === "barato" ? 10000 : null,
    sector: perfil.sector,
    ajuste: opcion.efecto || {},
  };

  const pool = vigentes.filter(ev => enVentana(ev, perfil.cuando));
  const orden = R.rankear(pool, sit, filtros);

  console.log("\n" + "─".repeat(72));
  console.log(perfil.nombre);
  console.log(`  ${sit.es[0]} · ${opcion.es || "—"} · ${perfil.cuando} · ${perfil.plata || "—"}` +
              `   → ${orden.length} candidatos`);

  if(!orden.length){ vacios++; console.log("  ⚠ SIN RESULTADOS"); continue; }

  /* Cuántos de los tres primeros calzan FUERTE con la repregunta. Es la
     promesa que hace la página cuando dice "de jazz tengo 12". */
  if(R.defineFuerte(opcion.efecto)){
    const fuertes = orden.filter(ev => R.esFuerte(ev, opcion.efecto)).length;
    const enTres = orden.slice(0,3).filter(ev => R.esFuerte(ev, opcion.efecto)).length;
    console.log(`  calce fuerte: ${fuertes} en total, ${enTres}/3 arriba`);
    if(fuertes >= 3 && enTres < 3){
      fallos++;
      console.log(`  ⚠ hay ${fuertes} que calzan fuerte y solo ${enTres} salieron en los tres primeros`);
    }
  }

  for(const ev of orden.slice(0, 3)){
    const p = R.puntuar(ev, sit, filtros);
    const donde = [ev.lugar, ev.comuna].filter(Boolean).join(", ");
    const precio = ev.gratis ? "gratis" : ev.precio ? "$" + ev.precio.toLocaleString("es-CL") : "s/precio";
    console.log(`   • ${ev.titulo.slice(0, 62)}`);
    console.log(`     ${ev.categoria}${ev.subcategoria ? "/" + ev.subcategoria : ""} · ${donde || "sin lugar"} · ${precio}` +
                (ev.esTaller ? " · taller" : "") + (verboso ? `   [${p.toFixed(1)}]` : ""));
    for(const [prueba, porque] of perfil.malo){
      if(prueba(ev)){ alarmas++; console.log(`     ⚠ ALARMA: ${porque}`); }
    }
  }
}

if(!filtro || soloFrases){
  console.log("\n" + "═".repeat(72));
  console.log("EL INTÉRPRETE DE TEXTO");
  for(const [frase, espera] of FRASES){
    const r = R.interpretar(frase);
    const malos = Object.entries(espera).filter(([k, v]) =>
      Array.isArray(v) ? JSON.stringify(r[k]) !== JSON.stringify(v) : r[k] !== v);
    const marca = malos.length ? "⚠" : "·";
    if(malos.length) fallos++;
    console.log(` ${marca} ${JSON.stringify(frase).padEnd(44)} ${JSON.stringify(
      Object.fromEntries(Object.entries(r).filter(([k, v]) =>
        k !== "vacio" && k !== "entendio" && !(k === "palabras" && !v.length))))}`);
    for(const [k, v] of malos) console.log(`     esperaba ${k}=${JSON.stringify(v)}, salió ${JSON.stringify(r[k])}`);
  }
}

console.log("\n" + "═".repeat(72));
console.log(`Catálogo: ${eventos.length} panoramas + ${talleres.length} talleres` +
            ` · ${vigentes.length} vigentes · ${vigentes.filter(e => e.paraNinos).length} para niños`);
console.log(`${alarmas} alarmas · ${vacios} perfiles sin resultados · ${fallos} fallos de calce`);
process.exit(alarmas + vacios + fallos ? 1 : 0);
