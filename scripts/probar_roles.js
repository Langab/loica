#!/usr/bin/env node
/* ============================================================
   Prueba el recomendador poniéndose en el lugar de gente distinta.

   Existe porque probar esto a mano en el navegador es lento y engañoso: uno
   hace tres clics, ve algo razonable y da por bueno el motor. Acá cada perfil
   corre contra eventos.json completo y muestra qué recibiría de verdad, con
   las alarmas encendidas cuando algo no calza — que fue como apareció que a
   una mamá con un niño el chat le mandaba a ver "Obsesión".

     node scripts/probar_roles.js            # todos los perfiles
     node scripts/probar_roles.js cita       # uno solo
     node scripts/probar_roles.js -v         # con puntaje y por qué
   ============================================================ */
const fs = require("fs");
const path = require("path");
const R = require(path.join(__dirname, "..", "web", "recomendador.js"));

const RAIZ = path.join(__dirname, "..", "web");
const eventos = JSON.parse(fs.readFileSync(path.join(RAIZ, "eventos.json"), "utf8")).eventos
  .map(ev => Object.assign({}, ev, {fecha: new Date(ev.inicio)}));
R.marcar(eventos);

const hoy = new Date(); hoy.setHours(0,0,0,0);
const vigentes = eventos.filter(ev => ev.fecha >= hoy);

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

/* Los perfiles son gente, no combinaciones de filtros. Cada uno trae lo que
   NO debería recibir, porque eso es lo que hay que poder detectar solo. */
const PERFILES = [
  {
    nombre:"Cita — viernes en la noche, quiere impresionar",
    compania:"pareja", situacion:"escenario", detalle:"vivo",
    cuando:"finde", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.recurrente, "es un taller semanal, no una cita"],
      [ev => ev.paraNinos, "es infantil"],
    ],
  },
  {
    nombre:"Carrete — cumpleaños con seis amigos",
    compania:"amigos", situacion:"noche", detalle:"tarde",
    cuando:"finde", plata:"igual", sector:"todo",
    malo:[
      [ev => ev.paraNinos, "es infantil"],
      [ev => ev.recurrente, "es un taller semanal"],
      [ev => ev.categoria === "charla", "una charla no es un carrete"],
    ],
  },
  {
    nombre:"Mamá — hijo de 6 años, sábado en la tarde",
    compania:"ninos", situacion:"escenario", detalle:"vivo",
    cuando:"finde", plata:"igual", sector:"todo",
    malo:[
      [ev => !ev.paraNinos, "no hay ninguna señal de que sea para niños"],
      [ev => ev.adulto, "tiene señales de contenido adulto"],
      [ev => ev.precio > 15000, "muy caro para llevar niños"],
    ],
  },
  {
    nombre:"Ejercicio — quiere meterse a algo fijo",
    compania:"solo", situacion:"mover", detalle:"taller",
    cuando:"semana", plata:"gratis", sector:"todo",
    malo:[
      [ev => !["deporte","aire_libre","clases","familia","otros"].includes(ev.categoria),
       "no es una actividad física"],
    ],
  },
  {
    nombre:"Ejercicio — solo quiere probar una vez",
    compania:"solo", situacion:"mover", detalle:"suelto",
    cuando:"semana", plata:"igual", sector:"todo",
    malo:[[ev => ev.recurrente, "pidió algo suelto y esto es un taller fijo"]],
  },
  {
    nombre:"No sabe qué hacer — sábado, solo, sin plata",
    compania:"solo", situacion:"panorama", detalle:"seguro",
    cuando:"finde", plata:"gratis", sector:"todo",
    malo:[
      [ev => !ev.gratis, "pidió gratis"],
      [ev => ev.recurrente, "un taller semanal no responde '¿qué hago hoy?'"],
    ],
  },
  {
    nombre:"Mamá — algo fijo para que el niño se meta",
    compania:"ninos", situacion:"mover", detalle:"taller",
    cuando:"semana", plata:"gratis", sector:"todo",
    malo:[[ev => !ev.paraNinos, "no hay señal de que sea para niños"]],
  },
  {
    nombre:"Cita barata — quieren salir sin gastar",
    compania:"pareja", situacion:"panorama", detalle:"seguro",
    cuando:"semana", plata:"gratis", sector:"todo",
    malo:[
      [ev => !ev.gratis, "pidió gratis"],
      [ev => ev.recurrente, "es un taller semanal, no una cita"],
      [ev => ev.paraNinos, "es infantil"],
    ],
  },
];

const verboso = process.argv.includes("-v");
const filtro = process.argv.slice(2).find(a => !a.startsWith("-"));

let alarmas = 0, vacios = 0;

for(const perfil of PERFILES){
  if(filtro && !perfil.nombre.toLowerCase().includes(filtro.toLowerCase())) continue;

  const sit = R.situacionPorId(perfil.situacion);
  const opcion = (sit.opciones || []).find(o => o.id === perfil.detalle) || {};
  const filtros = {
    compania: perfil.compania,
    soloGratis: perfil.plata === "gratis",
    techoPlata: perfil.plata === "barato" ? 10000 : null,
    sector: perfil.sector,
    ajuste: opcion.efecto || {},
  };

  const pool = vigentes.filter(ev => RANGOS[perfil.cuando](ev.fecha));
  const orden = R.rankear(pool, sit, filtros);

  console.log("\n" + "─".repeat(72));
  console.log(perfil.nombre);
  console.log(`  ${sit.es[0]} · ${opcion.es || "—"} · ${perfil.cuando} · ${perfil.plata}` +
              `   → ${orden.length} candidatos`);
  console.log("─".repeat(72));

  if(!orden.length){ console.log("  ⚠️  NADA. El perfil se va con las manos vacías."); vacios++; continue; }

  orden.slice(0, 5).forEach((ev, i) => {
    const fallas = perfil.malo.filter(([test]) => { try { return test(ev); } catch(e){ return false; } });
    const marca = fallas.length ? "🔴" : "  ";
    const precio = ev.gratis ? "gratis" : ev.precio ? "$" + ev.precio.toLocaleString("es-CL") : "s/precio";
    console.log(`${marca} ${i+1}. ${(ev.titulo || "").slice(0, 52)}`);
    console.log(`      ${ev.categoria} · ${precio} · ${ev.comuna || "sin comuna"}` +
                `${ev.recurrente ? " · TALLER" : ""}${ev.paraNinos ? " · INFANTIL" : ""}` +
                (verboso ? ` · ${R.puntuar(ev, sit, filtros).toFixed(1)} pts` : ""));
    fallas.forEach(([, por]) => { console.log(`      🔴 ${por}`); alarmas++; });
  });
}

console.log("\n" + "═".repeat(72));
console.log(alarmas === 0 && vacios === 0
  ? "✅ Ningún perfil recibió algo que no pidió."
  : `${alarmas} recomendaciones malas · ${vacios} perfiles sin resultados`);
console.log("═".repeat(72));
process.exit(alarmas || vacios ? 1 : 0);
