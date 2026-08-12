/* ============================================================
   LOICA — módulo compartido
   Mascotas (SVG), traducciones, datos y utilidades comunes.
   ============================================================ */

/* ---------- MASCOTAS ----------
   Nueve animales chilenos, dibujados en DOS niveles. Un solo SVG no puede
   servir a 22px en un chip y a 200px en la portada: los detalles de r=".4"
   que se veían lindos grandes, chicos no existen (0,3px). Por eso:

     carita(nombre, color)  → viewBox 24, SOLO cabeza.   Para ≤ 34px
     cuerpo(nombre, color)  → viewBox 48, cuerpo entero.  Para ≥ 38px

   `mascota()` elige sola según el tamaño que le pidas, así que todas las
   llamadas de antes siguen andando y de paso se ven mejor.

   Reglas de la carita, que son las que la hacen legible chiquitita: cabeza
   ≥70% del alto, ojo de radio ≥1,6, contorno de tinta de 1,6, máximo tres
   rellenos planos. Si un rasgo mide menos de 1/15 del viewBox, no va.

   El contorno usa `var(--contorno)`, así que en modo oscuro la tinta se
   invierte a crema sola. Cuando el SVG se va a rasterizar a canvas (los
   pines del mapa) hay que pasarle un color concreto en `tinta`. */

const TINTA_VAR = "var(--contorno)";
const OJO = "#1E2A4A";   // los ojos van sobre color saturado: siempre azul tinta

/* Los ojos son el rasgo que más pesa en que la cosa se lea "viva".
   Van grandes a propósito y con brillo. Durmiendo se vuelven dos arcos. */
const ojos = (x1, x2, y, r = 1.75, pose = "posada") => pose === "durmiendo"
  ? `<path d="M${x1 - r} ${y + r * .3}q${r} -${r * 1.3} ${r * 2} 0M${x2 - r} ${y + r * .3}q${r} -${r * 1.3} ${r * 2} 0"
       fill="none" stroke="${OJO}" stroke-width="1.6" stroke-linecap="round"/>`
  : `<circle cx="${x1}" cy="${y}" r="${r}" fill="${OJO}"/>
     <circle cx="${x2}" cy="${y}" r="${r}" fill="${OJO}"/>
     <circle cx="${x1 + r * .32}" cy="${y - r * .38}" r="${r * .38}" fill="#fff"/>
     <circle cx="${x2 + r * .32}" cy="${y - r * .38}" r="${r * .38}" fill="#fff"/>`;

/* La cabeza del cóndor (pelada, con cresta y pico ganchudo) se dibuja igual
   en la carita y en el cuerpo grande, así que vive aparte: en la carita va
   sobre la gola chica y en cuerpoAve() sobre la gola grande, sin duplicar
   el cuerpo de la carita encima del cuerpo de verdad. */
const cabezaCondor = (k, p) => `
  <ellipse cx="12" cy="6.6" rx="4.9" ry="4.3" fill="#C0766B" stroke="${k}" stroke-width="1.5"/>
  <path d="M9 4.6c.4-2.2 1.5-3.3 3-3.3s2.6 1.1 3 3.3c-.9-.7-1.9-1.1-3-1.1s-2.1.4-3 1.1z"
        fill="#C0766B" stroke="${k}" stroke-width="1.2" stroke-linejoin="round"/>
  <path d="M10.5 7.9h3c.9 0 1.5.8 1.3 1.7-.4 1.9-1.3 3.5-2.8 4.5-1.5-1-2.4-2.6-2.8-4.5-.2-.9.4-1.7 1.3-1.7z"
        fill="#FAF3E7" stroke="${k}" stroke-width="1.2" stroke-linejoin="round"/>
  <ellipse cx="12" cy="13.3" rx="1.2" ry="1" fill="${OJO}"/>
  ${ojos(9.9, 14.1, 6.2, 1.6, p)}`;

const CARITAS = {
  /* La Loica (Leistes loyca): el pico LARGO, recto y oscuro es lo que la hace
     loica y no gorrión — más la pechera roja de la garganta al pecho, que es
     la marca y no cambia nunca (va contorneada para leerse incluso sobre un
     cuerpo rojo), y la ceja clara sobre el ojo. */
  loica: (c, k, p) => `
    <circle cx="12" cy="12.2" r="8.6" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="16.6" rx="5.6" ry="3.6" fill="#E8442E" stroke="${k}" stroke-width="1.2"/>
    <path d="M6.3 8.1c1.2-1.2 3-1.5 4.4-.8M17.7 8.1c-1.2-1.2-3-1.5-4.4-.8"
          fill="none" stroke="#FAF3E7" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M10.5 12.1h3L12 20.4z" fill="${k}" stroke="${k}" stroke-width="1" stroke-linejoin="round"/>
    ${ojos(8.7, 15.3, 10.1, 1.8, p)}`,

  /* El Cóndor: cabeza chica y PELADA color piel con la cresta carnosa encima,
     pico ganchudo claro con punta oscura, y la gola blanca esponjosa que
     separa esa cabecita del cuerpo grande. El color de categoría va al cuerpo. */
  condor: (c, k, p) => `
    <ellipse cx="12" cy="17.2" rx="8.7" ry="5.2" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <path d="M6.6 14.6c-.6-1.8.6-3.4 2.4-3.3.2-1.2 1.4-2 3-2s2.8.8 3 2c1.8-.1 3 1.5 2.4 3.3-.6 1.9-2.7 3-5.4 3s-4.8-1.1-5.4-3z"
          fill="#FAF3E7" stroke="${k}" stroke-width="1.3" stroke-linejoin="round"/>
    ${cabezaCondor(k, p)}`,

  /* El Culpeo: zorro de verdad — orejas triangulares grandes, cabeza que se
     afina hacia abajo y el hocico crema ALARGADO que asoma bajo el mentón,
     con la nariz negra grande. */
  culpeo: (c, k, p) => `
    <path d="M5.6 11 6.6 3.1 11.6 6.9z" fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M18.4 11 17.4 3.1 12.4 6.9z" fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M7.2 8.8 7.7 5.4 10 7.1z" fill="#F2778C" opacity=".75"/>
    <path d="M16.8 8.8 16.3 5.4 14 7.1z" fill="#F2778C" opacity=".75"/>
    <path d="M12 5c-4.6 0-7.8 2.6-7.8 6.2 0 2.1.8 3.9 2.2 5.3 1.5 1.6 3.4 3.9 5.6 3.9s4.1-2.3 5.6-3.9c1.4-1.4 2.2-3.2 2.2-5.3 0-3.6-3.2-6.2-7.8-6.2z"
          fill="${c}" stroke="${k}" stroke-width="1.6" stroke-linejoin="round"/>
    <ellipse cx="12" cy="17.8" rx="3" ry="3.4" fill="#FAF3E7" stroke="${k}" stroke-width="1.4"/>
    ${ojos(8.7, 15.3, 11.2, 1.7, p)}
    <ellipse cx="12" cy="16.4" rx="1.5" ry="1.2" fill="${OJO}"/>`,

  /* El Pudú: el ciervo más chico del mundo. Orejas chicas y redondeadas
     ARRIBA (nada de orejas de vaca a los lados), dos cachitos rectos, cara
     oval dulce y la nariz negra grande. */
  pudu: (c, k, p) => `
    <path d="M9.7 5 8.9 1.7M14.3 5 15.1 1.7" stroke="${k}" stroke-width="2" stroke-linecap="round"/>
    <ellipse cx="7" cy="6.1" rx="3" ry="2.3" transform="rotate(-38 7 6.1)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="17" cy="6.1" rx="3" ry="2.3" transform="rotate(38 17 6.1)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="6.9" cy="6" rx="1.5" ry="1.05" transform="rotate(-38 6.9 6)" fill="#F2778C" opacity=".65"/>
    <ellipse cx="17.1" cy="6" rx="1.5" ry="1.05" transform="rotate(38 17.1 6)" fill="#F2778C" opacity=".65"/>
    <circle cx="12" cy="13" r="8" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="17.7" rx="3.3" ry="2.9" fill="#FAF3E7"/>
    ${ojos(8.8, 15.2, 12.2, 1.8, p)}
    <ellipse cx="12" cy="16.5" rx="1.7" ry="1.3" fill="${OJO}"/>`,

  /* El Chincol: el copete puntudo parado, las franjas de la corona y el
     collar castaño en la nuca, que es fijo como la pechera de la loica. */
  chincol: (c, k, p) => `
    <path d="M8.4 7.4 9.4 1.8 12 5.2 14.6 1.8 15.6 7.4z" fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <circle cx="12" cy="12.5" r="8.4" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <path d="M8.6 5.6c-1.7 1.3-2.8 3.1-3.2 5.2M15.4 5.6c1.7 1.3 2.8 3.1 3.2 5.2"
          fill="none" stroke="${k}" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M5.4 14.9c1.5 3.2 3.8 4.9 6.6 4.9s5.1-1.7 6.6-4.9"
          fill="none" stroke="#B0561F" stroke-width="2.8" stroke-linecap="round"/>
    <path d="M10.4 12.9h3.2L12 16.4z" fill="#E8B23A" stroke="${k}" stroke-width="1.1" stroke-linejoin="round"/>
    ${ojos(8.8, 15.2, 10.4, 1.75, p)}`,

  /* La Chinchilla: orejas redondas enormes y cara muy redonda. Los bigotes
     van solo en el cuerpo grande; acá violarían el 1/15. */
  chinchilla: (c, k, p) => `
    <circle cx="5.8" cy="7.6" r="3.7" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <circle cx="18.2" cy="7.6" r="3.7" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <circle cx="6" cy="7.9" r="1.8" fill="#F2778C" opacity=".6"/>
    <circle cx="18" cy="7.9" r="1.8" fill="#F2778C" opacity=".6"/>
    <circle cx="12" cy="13.2" r="7.8" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="16.9" rx="3.4" ry="2.7" fill="#FAF3E7"/>
    ${ojos(9, 15, 12.2, 1.75, p)}
    <ellipse cx="12" cy="15.7" rx="1.25" ry="1" fill="${OJO}"/>`,

  /* El Degú: el roedor del matorral de Santiago, el que uno ve en el San
     Cristóbal. Es el que más se parece a la chinchilla, así que las tres señas
     que lo separan van todas puestas: orejas OVALADAS y medianas (las de la
     chinchilla son círculos enormes), el anillo claro alrededor del ojo, y los
     dientes anaranjados asomando bajo la nariz.

     El anillo no es adorno: el degú va en café oscuro y los ojos son azul
     tinta, que sobre café da 1,9:1 y desaparece. Puestos sobre el anillo crema
     pasan de sobra. La seña real del animal es también la que lo hace legible
     a 22px, que es cuando algo del sistema está bien resuelto. */
  degu: (c, k, p) => `
    <ellipse cx="6.1" cy="6.2" rx="2.8" ry="3.4" transform="rotate(-24 6.1 6.2)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="17.9" cy="6.2" rx="2.8" ry="3.4" transform="rotate(24 17.9 6.2)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="6.2" cy="6.4" rx="1.35" ry="1.75" transform="rotate(-24 6.2 6.4)" fill="#F2778C" opacity=".6"/>
    <ellipse cx="17.8" cy="6.4" rx="1.35" ry="1.75" transform="rotate(24 17.8 6.4)" fill="#F2778C" opacity=".6"/>
    <circle cx="12" cy="13" r="8.1" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <circle cx="8.7" cy="11.7" r="2.95" fill="#FAF3E7"/>
    <circle cx="15.3" cy="11.7" r="2.95" fill="#FAF3E7"/>
    <ellipse cx="12" cy="17.5" rx="3.7" ry="3" fill="#FAF3E7"/>
    ${ojos(8.7, 15.3, 11.7, 1.8, p)}
    <ellipse cx="12" cy="15.9" rx="1.6" ry="1.2" fill="${OJO}"/>
    <path d="M10.9 17.4h2.2v1.5a1.1 1.1 0 0 1-2.2 0z" fill="#E8B23A" stroke="${k}" stroke-width="1"/>`,

  /* El Chungungo: nutria. Cabeza ANCHA y plana (más ancha que alta), orejas
     mínimas, hocico claro grande con nariz grande y bigotes gruesos — los
     bigotes y la cabeza chata son lo que lo separa de la chinchilla. */
  chungungo: (c, k, p) => `
    <circle cx="3.9" cy="9.8" r="1.9" fill="${c}" stroke="${k}" stroke-width="1.4"/>
    <circle cx="20.1" cy="9.8" r="1.9" fill="${c}" stroke="${k}" stroke-width="1.4"/>
    <path d="M12 5.6c-5.4 0-9.4 2.9-9.4 6.9 0 3.8 4 6.7 9.4 6.7s9.4-2.9 9.4-6.7c0-4-4-6.9-9.4-6.9z"
          fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="15.1" rx="5" ry="3.2" fill="#FAF3E7"/>
    <path d="M6.7 14.4 4 13.7M6.9 16.2 4.2 16.7M17.3 14.4 20 13.7M17.1 16.2 19.8 16.7"
          fill="none" stroke="${k}" stroke-width="1.5" stroke-linecap="round"/>
    ${ojos(8.5, 15.5, 10.4, 1.7, p)}
    <ellipse cx="12" cy="13.3" rx="1.9" ry="1.4" fill="${OJO}"/>`,

  /* El Pingüino de Humboldt: la herradura BLANCA que parte sobre cada ojo y
     rodea las mejillas hasta juntarse bajo el mentón, y la base ROSADA
     carnosa del pico — las dos señas del Humboldt. Va de terno a las
     charlas; en Chile "pingüino" es también el escolar de uniforme. */
  pinguino: (c, k, p) => `
    <circle cx="12" cy="12.2" r="8.6" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <path d="M7 6.2c-2 1.9-2.6 4.7-1.9 7.2.8 2.9 3.5 4.9 6.9 4.9s6.1-2 6.9-4.9c.7-2.5.1-5.3-1.9-7.2"
          fill="none" stroke="#FAF3E7" stroke-width="1.9" stroke-linecap="round"/>
    <ellipse cx="12" cy="12.3" rx="2.6" ry="1.4" fill="#F2778C"/>
    <path d="M10.6 12.1h2.8L12 16.3z" fill="${k}" stroke="${k}" stroke-width="1" stroke-linejoin="round"/>
    ${ojos(8.6, 15.4, 10, 1.75, p)}`,
};

/* ---------- CUERPOS (viewBox 48) ----------
   La cabeza es la misma carita escalada; abajo va el cuerpo. Así los ocho
   animales se ven de la misma familia sin dibujar dieciséis SVG distintos. */

// Truco de la cola: se traza dos veces, primero gruesa en tinta y encima
// delgada en color. Sale una cola con contorno sin dibujar el contorno.
const cola = (d, c, k, grosor = 5.4) =>
  `<path d="${d}" fill="none" stroke="${k}" stroke-width="${grosor}" stroke-linecap="round"/>
   <path d="${d}" fill="none" stroke="${c}" stroke-width="${grosor - 2.4}" stroke-linecap="round"/>`;

const AVES = new Set(["loica", "condor", "chincol"]);

/* Mismo esqueleto para las tres aves (cola, cuerpo, ala, patas, cabeza) pero
   con la silueta de cada una: la loica lleva la cola larga de bailarina de
   pastizal y la pechera roja siguiendo hasta el pecho; el cóndor es más
   macizo y en vuelo abre las primarias como dedos. */
const cuerpoAve = (nombre, c, k, p) => {
  const alas = p === "volando" || p === "celebrando";
  const condor = nombre === "condor", esLoica = nombre === "loica";
  const alaIzq = condor ? "M24 27 5.8 11.6 3 15 7 17.4 3.4 20.2 8.4 21.2 5.8 24.8 16.4 33z"
                        : "M24 27 5.6 11.4 2.8 25.6 16.4 33z";
  const alaDer = condor ? "M24 27 42.2 11.6 45 15 41 17.4 44.6 20.2 39.6 21.2 42.2 24.8 31.6 33z"
                        : "M24 27 42.4 11.4 45.2 25.6 31.6 33z";
  return `
    ${alas ? `<path d="${alaIzq}" fill="${c}" stroke="${k}" stroke-width="2" stroke-linejoin="round"/>
              <path d="${alaDer}" fill="${c}" stroke="${k}" stroke-width="2" stroke-linejoin="round"/>` : ""}
    ${p === "volando" ? "" : `<path d="M20.4 39.6v4.8M27.2 39.6v4.8M17.8 44.6h5.2M24.6 44.6h5.2"
        stroke="${k}" stroke-width="2.3" stroke-linecap="round"/>`}
    <path d="${esLoica ? "M17 30.2 2.2 39.4 13 22.4z" : "M16.6 30.6 3 37.2 13.6 22.4z"}"
          fill="${c}" stroke="${k}" stroke-width="2" stroke-linejoin="round"/>
    <ellipse cx="24.6" cy="30.2" rx="${condor ? 12.2 : 11.4}" ry="${condor ? 10.4 : 10}"
             fill="${c}" stroke="${k}" stroke-width="2"/>
    ${esLoica ? `<ellipse cx="24.2" cy="25.8" rx="6.4" ry="5.4" fill="#E8442E"/>` : ""}
    ${alas || condor ? "" : `<path d="M27.8 22.6c4.4.8 7.4 4 7.6 8 .1 2.9-1 5.6-3 7.6l-1.1-2.5-1.5 2.3c-1.8-2.1-2.8-4.8-2.8-7.7 0-2.7.3-5.3.8-7.7z"
        fill="${c}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>`}
    ${condor
      ? `<path d="M14.6 19.8c-1-3.2 1-6 4.2-5.8.4-2.2 2.5-3.6 5.8-3.6s5.4 1.4 5.8 3.6c3.2-.2 5.2 2.6 4.2 5.8-1 3.2-4.9 5-10 5s-9-1.8-10-5z"
           fill="#FAF3E7" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>
         <g transform="translate(11.2 .4) scale(1.12)">${cabezaCondor(k, p)}</g>`
      : `<g transform="translate(14.9 1.2) scale(.93)">${CARITAS[nombre](c, k, p)}</g>`}`;
};

/* Las colas son lo que distingue a los cuatro cuadrúpedos de lejos, y cada
   una es un dato de la especie: la del culpeo es gorda y SIEMPRE termina en
   negro, la del pudú casi no existe, la de la chinchilla es tupida y se
   enrosca hacia arriba como ardilla, y la del chungungo es de nutria: gruesa
   en la base y afinándose hasta la punta. */
const COLAS = {
  culpeo:     (c, k) => cola("M37.4 32.4c3.6-1.2 5.9-4.3 6.6-8.8", c, k, 8) +
                        `<circle cx="44" cy="23.6" r="2.7" fill="${OJO}" stroke="${k}" stroke-width="1.4"/>`,
  pudu:       (c, k) => `<path d="M39.6 27.6c1.5-2.7 3.9-3.2 4.9-1.6 1 1.7-.1 3.9-2.3 4.6z"
                          fill="${c}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>`,
  chinchilla: (c, k) => cola("M36.6 30.2c-.9-4.4.7-8.6 4-10.4.8-.5 1.6-.7 2.4-.6", c, k, 7.5),
  /* La del degú es delgada y termina en un PINCEL oscuro. Es la seña que lo
     separa de la chinchilla vista de lejos: la de ella es tupida entera. */
  degu:       (c, k) => cola("M37.2 30.6c3.4-1.2 5.4-4 5.8-8", c, k, 4.8) +
                        `<ellipse cx="43.6" cy="20.6" rx="2.1" ry="3.3" transform="rotate(14 43.6 20.6)"
                           fill="${OJO}" stroke="${k}" stroke-width="1.4"/>`,
  chungungo:  (c, k) => `<path d="M38.2 29.2c4.2-.2 7.6 2.5 8.8 6.6.3 1-.8 1.9-1.7 1.3-3.3-2-5.9-4.7-7.1-7.9z"
                          fill="${c}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>`,
};

/* Silueta por especie: cuerpo (cx, cy, rx, ry), patas con su grosor, algún
   parche fijo bajo la cabeza y dónde se apoya la cabeza. El chungungo va más
   abajo que el resto: nutria = cuerpo largo, bajo y pegado al suelo. */
const CUADRUPEDOS = {
  culpeo:     {cuerpo:[29.4, 31.2, 12.2, 8.6], grosor:3.4, cabeza:"2.5 3.4",
               patas:"M21.6 38.6v5.6M28 38.8v5.4M34.4 38.4v5.8M39.4 37.6v6.4",
               extra:`<ellipse cx="19.6" cy="27.6" rx="3.4" ry="4.2" fill="#FAF3E7"/>`},
  pudu:       {cuerpo:[28.8, 30.8, 11.4, 8.2], grosor:2.7, cabeza:"2.5 3.4",
               patas:"M21.8 38.2v6.4M27.4 38.6v6M33.6 38.4v6.2M38.6 37.4v7.2", extra:""},
  chinchilla: {cuerpo:[28.4, 31.4, 10.8, 9.6], grosor:3.2, cabeza:"2.5 3.4",
               patas:"M22.6 39.8v4.4M27.8 40.2v4M33.4 39.8v4.4M37.6 38.8v5.2", extra:""},
  /* Más largo y más bajo que la chinchilla: el degú trota, no salta. */
  degu:       {cuerpo:[28.6, 31.8, 11.4, 8.4], grosor:3, cabeza:"2.5 3.4",
               patas:"M22.2 39.4v5M27.6 39.8v4.6M33.4 39.4v5M38 38.6v5.6",
               extra:`<ellipse cx="27.4" cy="37.4" rx="5.4" ry="2.3" fill="#FAF3E7" opacity=".85"/>`},
  chungungo:  {cuerpo:[28.6, 33, 13.8, 7.4], grosor:3.2, cabeza:"3 8.2",
               patas:"M20.8 39.4v4.8M26.6 39.8v4.4M33.2 39.6v4.6M38.2 38.6v5.4", extra:""},
};

/* Los bigotes de la chinchilla van acá y no en la carita (regla del 1/15). */
const BIGOTES_CHINCHILLA = `
  <path d="M9.2 18.6 4.6 17.2M9.4 20.4 4.8 20.8M18.6 18.6 23.2 17.2M18.4 20.4 23 20.8"
        fill="none" stroke-width="1.2" stroke-linecap="round"/>`;

const cuerpoCuadrupedo = (nombre, c, k, p) => {
  const q = CUADRUPEDOS[nombre], [bx, by, brx, bry] = q.cuerpo;
  return `
  <path d="${q.patas}" stroke="${k}" stroke-width="${q.grosor}" stroke-linecap="round"/>
  ${COLAS[nombre](c, k)}
  <ellipse cx="${bx}" cy="${by}" rx="${brx}" ry="${bry}" fill="${c}" stroke="${k}" stroke-width="2"/>
  ${q.extra}
  <g transform="translate(${q.cabeza}) scale(.95)">${CARITAS[nombre](c, k, p)}</g>
  ${nombre === "chinchilla" ? `<g stroke="${k}">${BIGOTES_CHINCHILLA}</g>` : ""}`;
};

/* El pingüino no vuela ni trota: cuerpo propio, parado y guatón. La panza
   crema con la banda oscura en herradura cruzando el pecho es la segunda
   seña del Humboldt (la primera va en la carita). Las aletas son elipses
   pegadas al cuerpo que rotan según la pose: "volando" acá es el saltito
   de nado con las aletas abiertas y las patas recogidas. */
const cuerpoPinguino = (c, k, p) => {
  const ang = p === "celebrando" ? 150 : p === "volando" ? 95 : 14;
  const aleta = (sx, s) => `<g transform="translate(${sx} 24.4) rotate(${s * ang})">
      <ellipse cx="0" cy="5.6" rx="2.1" ry="5.8" fill="${c}" stroke="${k}" stroke-width="1.8"/></g>`;
  return `
  ${p === "volando" ? "" : `<path d="M20.4 41.2l-2.1 3.4h4.6zM27.6 41.2l-2.1 3.4h4.6z"
        fill="#F2778C" stroke="${k}" stroke-width="1.3" stroke-linejoin="round"/>`}
  <ellipse cx="24" cy="30" rx="10.6" ry="12.2" fill="${c}" stroke="${k}" stroke-width="2"/>
  <ellipse cx="24" cy="31.6" rx="6.8" ry="9.2" fill="#FAF3E7"/>
  <path d="M17.6 25.6c1.3 3.5 3.5 5.2 6.4 5.2s5.1-1.7 6.4-5.2"
        fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round"/>
  ${aleta(15, -1)}${aleta(33, 1)}
  <g transform="translate(12.8 1.1) scale(.93)">${CARITAS.pinguino(c, k, p)}</g>`;
};

/* ---------- API PÚBLICA ---------- */
function carita(nombre, color = "currentColor", tamano = 24, opc = {}){
  const dibujo = CARITAS[nombre] || CARITAS.loica;
  return `<svg viewBox="0 0 24 24" width="${tamano}" height="${tamano}"
            aria-hidden="true" focusable="false">
            ${dibujo(color, opc.tinta || TINTA_VAR, opc.pose || "posada")}</svg>`;
}

function cuerpo(nombre, color = "currentColor", tamano = 48, opc = {}){
  const clave = CARITAS[nombre] ? nombre : "loica";
  const k = opc.tinta || TINTA_VAR, p = opc.pose || "posada";
  const dibujo = clave === "pinguino" ? cuerpoPinguino(color, k, p)
               : AVES.has(clave)      ? cuerpoAve(clave, color, k, p)
                                      : cuerpoCuadrupedo(clave, color, k, p);
  return `<svg viewBox="0 0 48 48" width="${tamano}" height="${tamano}"
            aria-hidden="true" focusable="false">${dibujo}</svg>`;
}

/* El punto de corte son 38px: bajo eso el cuerpo entero es una mancha y la
   carita gana; sobre eso la carita sola se ve como una cabeza cortada. */
function mascota(nombre, color, tamano = 24, opc = {}){
  return tamano < 38 ? carita(nombre, color, tamano, opc)
                     : cuerpo(nombre, color, tamano, opc);
}

/* ---------- CATEGORÍAS ----------
   Cada categoría tiene su mascota, su color y su nombre en 3 idiomas.
   Sale de estrategia_marca.md: la mascota ES la señalética de la categoría.

   Dos colores por familia y no es capricho:
     hex   → relleno (pin, pastilla). Va fuerte, siempre con contorno de tinta.
     tinta → el MISMO color pero oscurecido hasta pasar 4,5:1 sobre crema.
             Es el único que puede tocar texto. El naranjo y el amarillo
             fuertes sobre crema dan 2,4:1: como texto son ilegibles.

   El Chungungo estrena familia propia (deporte). Antes el deporte usaba el
   cóndor rojo de música, que decía "concierto" a alguien que busca una
   pichanga. */
const CATEGORIAS = {
  fiesta:    {mascota:"culpeo",     color:"var(--c-fiesta)", tintaVar:"var(--c-fiesta-tinta)",  hex:"#7A3FE0", tinta:"#5B2BAF", es:"Fiestas",   en:"Parties",  pt:"Festas"},
  musica:    {mascota:"condor",     color:"var(--c-musica)", tintaVar:"var(--c-musica-tinta)",  hex:"#DE3A1E", tinta:"#A82B12", es:"Música",    en:"Music",    pt:"Música"},
  teatro:    {mascota:"chinchilla", color:"var(--c-cultura)", tintaVar:"var(--c-cultura-tinta)", hex:"#1B6FD1", tinta:"#1A5599", es:"Teatro",    en:"Theatre",  pt:"Teatro"},
  arte:      {mascota:"chinchilla", color:"var(--c-cultura)", tintaVar:"var(--c-cultura-tinta)", hex:"#1B6FD1", tinta:"#1A5599", es:"Arte",      en:"Art",      pt:"Arte"},
  cine:      {mascota:"chinchilla", color:"var(--c-cultura)", tintaVar:"var(--c-cultura-tinta)", hex:"#1B6FD1", tinta:"#1A5599", es:"Cine",      en:"Film",     pt:"Cinema"},
  charla:    {mascota:"pinguino",   color:"var(--c-charla)",  tintaVar:"var(--c-charla-tinta)",  hex:"#C42B67", tinta:"#8F1C4A", es:"Charlas",   en:"Talks",    pt:"Palestras"},
  clases:    {mascota:"chincol",    color:"var(--c-clases)", tintaVar:"var(--c-clases-tinta)",  hex:"#F08800", tinta:"#8A5000", es:"Clases",    en:"Classes",  pt:"Aulas"},
  feria:     {mascota:"chincol",    color:"var(--c-clases)", tintaVar:"var(--c-clases-tinta)",  hex:"#F08800", tinta:"#8A5000", es:"Ferias",    en:"Markets",  pt:"Feiras"},
  idiomas:   {mascota:"chincol",    color:"var(--c-clases)", tintaVar:"var(--c-clases-tinta)",  hex:"#F08800", tinta:"#8A5000", es:"Idiomas",   en:"Languages",pt:"Idiomas"},
  deporte:   {mascota:"chungungo",  color:"var(--c-deporte)", tintaVar:"var(--c-deporte-tinta)", hex:"#0C8B9B", tinta:"#065C66", es:"Deporte",   en:"Sports",   pt:"Esporte"},
  familia:   {mascota:"pudu",       color:"var(--c-libre)", tintaVar:"var(--c-libre-tinta)",   hex:"#0E8757", tinta:"#0A6141", es:"Familia",   en:"Family",   pt:"Família"},
  aire_libre:{mascota:"pudu",       color:"var(--c-libre)", tintaVar:"var(--c-libre-tinta)",   hex:"#0E8757", tinta:"#0A6141", es:"Aire libre",en:"Outdoors", pt:"Ar livre"},
  otros:     {mascota:"loica",      color:"var(--c-otros)", tintaVar:"var(--c-otros-tinta)",   hex:"#FFB61F", tinta:"#7E5900", es:"Otros",     en:"Other",    pt:"Outros"},
};
const cat = c => CATEGORIAS[c] || CATEGORIAS.otros;

/* El elenco, en el orden en que se presenta. Lo usan la portada y Nosotros:
   antes cada página repetía la lista a mano y ya iban desincronizadas. */
const ELENCO = [
  {clave:"loica",      hex:"#E8442E", tinta:"#AA2C1B", es:["Loica","La anfitriona","Te recibe, te guía y te avisa cuando hay algo bueno cerca."],
                                                       en:["Loica","The host","She greets you, guides you and tells you what's on nearby."],
                                                       pt:["Loica","A anfitriã","Ela recebe você, guia e avisa quando tem algo bom por perto."]},
  {clave:"condor",     hex:"#DE3A1E", tinta:"#A82B12", es:["Cóndor","Música","Lo que se escucha fuerte: conciertos, tocatas, festivales."],
                                                       en:["Condor","Music","The loud stuff: gigs, concerts, festivals."],
                                                       pt:["Condor","Música","O que se ouve alto: shows, tocatas, festivais."]},
  {clave:"culpeo",     hex:"#7A3FE0", tinta:"#5B2BAF", es:["Culpeo","Fiestas","Sale de noche. Todo lo que parte cuando el resto se acuesta."],
                                                       en:["Culpeo fox","Parties","A night creature. Everything that starts when the city sleeps."],
                                                       pt:["Culpeo","Festas","Sai à noite. Tudo o que começa quando o resto vai dormir."]},
  {clave:"chinchilla", hex:"#1B6FD1", tinta:"#1A5599", es:["Chinchilla","Cultura","Teatro, cine, arte y charlas. Escucha más de lo que habla."],
                                                       en:["Chinchilla","Culture","Theatre, film, art and talks. Listens more than she speaks."],
                                                       pt:["Chinchila","Cultura","Teatro, cinema, arte e palestras. Escuta mais do que fala."]},
  {clave:"chincol",    hex:"#F08800", tinta:"#8A5000", es:["Chincol","Barrio","Clases, talleres y ferias. El pájaro más de barrio que hay."],
                                                       en:["Chincol","Neighbourhood","Classes, workshops and markets. The most local bird there is."],
                                                       pt:["Chincol","Bairro","Aulas, oficinas e feiras. O pássaro mais de bairro que existe."]},
  {clave:"pudu",       hex:"#0E8757", tinta:"#0A6141", es:["Pudú","Gratis","El ciervo más chico del mundo cuida lo que no cuesta nada."],
                                                       en:["Pudú","Free","The world's smallest deer looks after everything that costs nothing."],
                                                       pt:["Pudu","Grátis","O menor cervo do mundo cuida do que não custa nada."]},
  {clave:"degu",       hex:"#95521C", tinta:"#6B3813", es:["Degú","Descuentos","Junta, guarda y se sabe de memoria qué día conviene salir a comer."],
                                                       en:["Degu","Discounts","Hoards, saves, and knows by heart which day is the cheap one to eat out."],
                                                       pt:["Degu","Descontos","Junta, guarda e sabe de cor qual dia compensa sair para comer."]},
  {clave:"chungungo",  hex:"#0C8B9B", tinta:"#065C66", es:["Chungungo","Deporte","La nutria del Mapocho. Se mueve, se moja y no para nunca."],
                                                       en:["Chungungo","Sport","The Mapocho river otter. Always moving, always wet, never still."],
                                                       pt:["Chungungo","Esporte","A lontra do Mapocho. Se mexe, se molha e não para nunca."]},
  {clave:"pinguino",   hex:"#C42B67", tinta:"#8F1C4A", es:["Pingüino","Charlas","De Humboldt y de punta en blanco. Charlas, seminarios y gente que sabe."],
                                                       en:["Penguin","Talks","A Humboldt in black tie. Talks, seminars and people who know."],
                                                       pt:["Pinguim","Palestras","Um Humboldt de gala. Palestras, seminários e gente que sabe."]},
];

/* ---------- TRADUCCIONES ---------- */
const TEXTOS = {
  es:{
    lema:"Santiago está pasando",
    mapa:"Mapa", habla:"Habla con la Loica", blog:"Blog", ninos:"Niños", mas18:"+18", calendario:"Calendario", agregar:"Agrega tu evento", nosotros:"Quién hace esto",
    eventos:"eventos", evento:"evento", gratis:"Gratis",
    hoy:"Hoy", manana:"Mañana", semana:"7 días", finde:"Finde",
    cuandoLargo:{hoy:"Hoy", manana:"Mañana", semana:"En estos 7 días", finde:"Este fin de semana", todo:"Todos"},
    filtrosCuando:"Cuándo", filtrosRapidos:"Precio y público", filtrosTipo:"Tipo de panorama",
    cuando:"Cuándo", donde:"Dónde", precio:"Precio", ir:"Ver en la fuente original",
    vacio:"No hay eventos con esos filtros", vaciopista:"Prueba sacando algún filtro",
    aprox:"Ubicación aproximada: centro de la comuna", sinUbicar:"Dirección por confirmar — revísala en la fuente", fuente:"Información publicada por",
    libre:"Entrada liberada", verMapa:"Ver en el mapa", cerrar:"Cerrar",
    anteriorEv:"Anterior", siguienteEv:"Siguiente", deN:"de",
    verMas:"Ver más panoramas", cargando:"Cargando…",
    meses:["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"],
    dias:["lun","mar","mié","jue","vie","sáb","dom"], mesesCortos:["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"],
    hoyBoton:"Hoy", anterior:"Mes anterior", siguiente:"Mes siguiente",
    /* Portada */
    pTitulo:"¿Qué hacemos hoy?",
    pBajada:"Todo lo que está pasando en Santiago, en un solo lugar. Lo junta un robot todas las mañanas y siempre te deja en la fuente original.",
    pSaludo:"¡Hola! Soy la Loica. ¿Te muestro Santiago?",
    pVerMapa:"Ver el mapa", pVerHoy:"Panoramas de hoy",
    pHoyTitulo:"Hoy en Santiago", pHoyVer:"Ver los", pHoyVacio:"Hoy está tranquilo. Mira lo que viene.",
    pDondeIr:"¿Por dónde partimos?",
    pMapaT:"El mapa", pMapaD:"Qué hay cerca tuyo, ahora mismo.",
    pCalT:"El calendario", pCalD:"Para planificar el finde con tiempo.",
    pBlogT:"El blog", pBlogD:"Rutas y recomendaciones escritas a mano.",
    pQuienT:"Quién hace esto", pQuienD:"Una persona, en Santiago, después de la pega.",
    pElencoT:"Los que te acompañan",
    pElencoD:"Nueve animales chilenos hacen de señalética: cada uno se hace cargo de un tipo de panorama en el mapa y el calendario, y el Degú de los descuentos.",
    pGratisT:"gratis", pGratisD:"panoramas que no cuestan nada",
    pTotalD:"panoramas vigentes", pFuentesD:"fuentes revisadas cada mañana",
    pCierreT:"¿Organizas algo?", pCierreD:"Si tu evento es abierto y pasa en Santiago, cabe acá. No cobramos por aparecer.",
    pDctoT:"Los descuentos", pDctoD:"Dónde comer más barato hoy, según tu tarjeta.",
    pDctoCifra:"descuentos de banco vigentes",
    /* Descuentos */
    descuentos:"Descuentos",
    dTitulo:"¿Dónde como hoy?",
    dBajada:"Descuentos de restaurantes con tarjetas de banco. Los revisa un robot todas las mañanas en la página de cada banco y te deja en ella.",
    dCuantos:"descuentos", dCuantos1:"descuento",
    dBanco:"Banco", dComuna:"Comuna", dDia:"Día", dTodos:"Todos", dLimpiar:"Limpiar",
    dTodosDias:"Todos los días", dHoyEs:"Hoy es",
    dSinFecha:"Sin fecha declarada por el banco", dHasta:"Hasta el",
    dTope:"Tope", dSegmentado:"No es para todos los clientes del banco",
    dSoloOnline:"Solo online", dSoloPresencial:"Solo presencial",
    dVerBanco:"Ver en la página del banco",
    dVacio:"No hay descuentos con esos filtros", dVaciopista:"Prueba sacando alguno",
    dOjo:"El descuento lo pone el banco, no Loica. Confirma la vigencia antes de ir.",
    dVerLocal:"Ir al sitio del local",
    dCapturado:"Anotado a mano el",
    dCapturadoPista:"Santander bloquea la lectura automática, así que esta ficha no se actualiza sola: revísala en el banco.",
    diasLargos:["lunes","martes","miércoles","jueves","viernes","sábado","domingo"],
  },
  en:{
    lema:"Santiago is happening",
    mapa:"Map", habla:"Talk to the Loica", blog:"Blog", ninos:"Kids", mas18:"18+", calendario:"Calendar", agregar:"Add your event", nosotros:"Who makes this",
    eventos:"events", evento:"event", gratis:"Free",
    hoy:"Today", manana:"Tomorrow", semana:"7 days", finde:"Weekend",
    cuandoLargo:{hoy:"Today", manana:"Tomorrow", semana:"Within 7 days", finde:"This weekend", todo:"All"},
    filtrosCuando:"When", filtrosRapidos:"Price and audience", filtrosTipo:"Type of event",
    cuando:"When", donde:"Where", precio:"Price", ir:"View original source",
    vacio:"No events match these filters", vaciopista:"Try removing a filter",
    aprox:"Approximate location: district centre", sinUbicar:"Address to be confirmed — check the source", fuente:"Information published by",
    libre:"Free entry", verMapa:"See on the map", cerrar:"Close",
    anteriorEv:"Previous", siguienteEv:"Next", deN:"of",
    verMas:"See more events", cargando:"Loading…",
    meses:["January","February","March","April","May","June","July","August","September","October","November","December"],
    dias:["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], mesesCortos:["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"],
    hoyBoton:"Today", anterior:"Previous month", siguiente:"Next month",
    /* Portada */
    pTitulo:"What are we doing today?",
    pBajada:"Everything happening in Santiago, in one place. A robot gathers it every morning and always sends you to the original source.",
    pSaludo:"Hi! I'm the Loica. Shall I show you Santiago?",
    pVerMapa:"Open the map", pVerHoy:"What's on today",
    pHoyTitulo:"Today in Santiago", pHoyVer:"See all", pHoyVacio:"Quiet today. Have a look at what's coming.",
    pDondeIr:"Where do we start?",
    pMapaT:"The map", pMapaD:"What's near you, right now.",
    pCalT:"The calendar", pCalD:"To plan the weekend ahead of time.",
    pBlogT:"The blog", pBlogD:"Routes and picks written by hand.",
    pQuienT:"Who makes this", pQuienD:"One person, in Santiago, after work.",
    pElencoT:"Your guides",
    pElencoD:"Nine Chilean animals work as signage: each one looks after a type of event on the map and the calendar, and the Degu looks after the discounts.",
    pGratisT:"free", pGratisD:"events that cost nothing",
    pTotalD:"events on right now", pFuentesD:"sources checked every morning",
    pCierreT:"Running something?", pCierreD:"If your event is open to the public and happens in Santiago, it belongs here. We don't charge for it.",
    pDctoT:"The discounts", pDctoD:"Where to eat cheaper today, depending on your card.",
    pDctoCifra:"live bank discounts",
    /* Descuentos */
    descuentos:"Discounts",
    dTitulo:"Where do I eat today?",
    dBajada:"Restaurant discounts with Chilean bank cards. A robot checks each bank's own page every morning and always sends you back to it.",
    dCuantos:"discounts", dCuantos1:"discount",
    dBanco:"Bank", dComuna:"District", dDia:"Day", dTodos:"All", dLimpiar:"Clear",
    dTodosDias:"Every day", dHoyEs:"Today is",
    dSinFecha:"No end date published by the bank", dHasta:"Until",
    dTope:"Cap", dSegmentado:"Not available to every customer of the bank",
    dSoloOnline:"Online only", dSoloPresencial:"In person only",
    dVerBanco:"See it on the bank's page",
    dVacio:"No discounts match these filters", dVaciopista:"Try removing one",
    dOjo:"The discount is the bank's, not Loica's. Check it is still live before you go.",
    dVerLocal:"Go to the venue's site",
    dCapturado:"Written down by hand on",
    dCapturadoPista:"Santander blocks automated reading, so this one does not refresh on its own: check it with the bank.",
    diasLargos:["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
  },
  pt:{
    lema:"Santiago está acontecendo",
    mapa:"Mapa", habla:"Fale com a Loica", blog:"Blog", ninos:"Crianças", mas18:"+18", calendario:"Calendário", agregar:"Adicione seu evento", nosotros:"Quem faz isso",
    eventos:"eventos", evento:"evento", gratis:"Grátis",
    hoy:"Hoje", manana:"Amanhã", semana:"7 dias", finde:"Fim de semana",
    cuandoLargo:{hoy:"Hoje", manana:"Amanhã", semana:"Nestes 7 dias", finde:"Neste fim de semana", todo:"Todos"},
    filtrosCuando:"Quando", filtrosRapidos:"Preço e público", filtrosTipo:"Tipo de programa",
    cuando:"Quando", donde:"Onde", precio:"Preço", ir:"Ver na fonte original",
    vacio:"Nenhum evento com esses filtros", vaciopista:"Tente remover algum filtro",
    aprox:"Localização aproximada: centro da comuna", sinUbicar:"Endereço a confirmar — veja na fonte", fuente:"Informação publicada por",
    libre:"Entrada gratuita", verMapa:"Ver no mapa", cerrar:"Fechar",
    anteriorEv:"Anterior", siguienteEv:"Próximo", deN:"de",
    verMas:"Ver mais programas", cargando:"Carregando…",
    meses:["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"],
    dias:["seg","ter","qua","qui","sex","sáb","dom"], mesesCortos:["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"],
    hoyBoton:"Hoje", anterior:"Mês anterior", siguiente:"Próximo mês",
    /* Portada */
    pTitulo:"O que a gente faz hoje?",
    pBajada:"Tudo o que está acontecendo em Santiago, num só lugar. Um robô junta tudo toda manhã e sempre te leva à fonte original.",
    pSaludo:"Oi! Eu sou a Loica. Te mostro Santiago?",
    pVerMapa:"Abrir o mapa", pVerHoy:"Programas de hoje",
    pHoyTitulo:"Hoje em Santiago", pHoyVer:"Ver os", pHoyVacio:"Hoje está calmo. Veja o que vem por aí.",
    pDondeIr:"Por onde começamos?",
    pMapaT:"O mapa", pMapaD:"O que tem perto de você, agora.",
    pCalT:"O calendário", pCalD:"Para planejar o fim de semana com calma.",
    pBlogT:"O blog", pBlogD:"Roteiros e recomendações escritos à mão.",
    pQuienT:"Quem faz isso", pQuienD:"Uma pessoa, em Santiago, depois do trabalho.",
    pElencoT:"Quem te acompanha",
    pElencoD:"Nove animais chilenos servem de sinalização: cada um cuida de um tipo de programa no mapa e no calendário, e o Degu cuida dos descontos.",
    pGratisT:"grátis", pGratisD:"programas que não custam nada",
    pTotalD:"programas em cartaz", pFuentesD:"fontes revisadas toda manhã",
    pCierreT:"Organiza algo?", pCierreD:"Se o seu evento é aberto e acontece em Santiago, cabe aqui. Não cobramos para aparecer.",
    pDctoT:"Os descontos", pDctoD:"Onde comer mais barato hoje, conforme o seu cartão.",
    pDctoCifra:"descontos de banco em vigor",
    /* Descuentos */
    descuentos:"Descontos",
    dTitulo:"Onde eu como hoje?",
    dBajada:"Descontos de restaurantes com cartões de bancos chilenos. Um robô revisa a página de cada banco toda manhã e sempre te leva de volta a ela.",
    dCuantos:"descontos", dCuantos1:"desconto",
    dBanco:"Banco", dComuna:"Comuna", dDia:"Dia", dTodos:"Todos", dLimpiar:"Limpar",
    dTodosDias:"Todos os dias", dHoyEs:"Hoje é",
    dSinFecha:"Sem data de término declarada pelo banco", dHasta:"Até",
    dTope:"Limite", dSegmentado:"Não vale para todos os clientes do banco",
    dSoloOnline:"Só online", dSoloPresencial:"Só presencial",
    dVerBanco:"Ver na página do banco",
    dVacio:"Nenhum desconto com esses filtros", dVaciopista:"Tente tirar algum",
    dOjo:"O desconto é do banco, não da Loica. Confirme se está em vigor antes de ir.",
    dVerLocal:"Ir ao site do local",
    dCapturado:"Anotado à mão em",
    dCapturadoPista:"O Santander bloqueia a leitura automática, então esta ficha não se atualiza sozinha: confira no banco.",
    diasLargos:["segunda","terça","quarta","quinta","sexta","sábado","domingo"],
  },
};

let IDIOMA = localStorage.getItem("loica-idioma") || "es";
const t = clave => TEXTOS[IDIOMA][clave];

function fijarIdioma(nuevo){
  IDIOMA = nuevo;
  localStorage.setItem("loica-idioma", nuevo);
  document.documentElement.lang = nuevo;
}

/* ---------- TEMA ---------- */
function temaGuardado(){ return localStorage.getItem("loica-tema"); }
function aplicarTema(tema){
  if(tema) document.documentElement.dataset.tema = tema;
  else delete document.documentElement.dataset.tema;
  localStorage.setItem("loica-tema", tema || "");
}
function alternarTema(){
  const actual = document.documentElement.dataset.tema
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro");
  aplicarTema(actual === "oscuro" ? "claro" : "oscuro");
  return document.documentElement.dataset.tema;
}
aplicarTema(temaGuardado() || null);

/* ---------- CABECERA COMPARTIDA ---------- */
// Íconos de la navegación inferior. Simples a propósito: compiten con las
// mascotas y a 22px la mascota no se lee.
const ICONOS_NAV = {
  mapa:`<path d="M9 3 3 5.4v15.1l6-2.4 6 2.4 6-2.4V2.9l-6 2.4L9 3z" fill="none"
        stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M9 3v15.1M15 5.4v15.1" stroke="currentColor" stroke-width="1.8"/>`,
  calendario:`<rect x="3" y="4.8" width="18" height="16.2" rx="2.6" fill="none"
        stroke="currentColor" stroke-width="1.8"/>
        <path d="M3 9.6h18M8 3v3.6M16 3v3.6" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round"/><circle cx="8.4" cy="14" r="1.2" fill="currentColor"/>
        <circle cx="12.6" cy="14" r="1.2" fill="currentColor"/>`,
  agregar:`<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/>
        <path d="M12 8.2v7.6M8.2 12h7.6" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round"/>`,
  blog:`<path d="M5 19.5c4-1 9.2-3.4 12.2-6.4 2.4-2.4 3.3-5.8 3.3-8.6-2.8 0-6.2.9-8.6 3.3-3 3-5.4 8.2-6.4 12.2z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M4.5 20c1.5-4.5 4-8 7-10.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>`,
  nosotros:`<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/>
        <path d="M12 10.8v5.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="12" cy="7.9" r="1.15" fill="currentColor"/>`,
  // Globo de diálogo con la colita abajo a la izquierda: es el único ícono
  // que promete conversación y no navegación.
  habla:`<path d="M4 5.6h16a1.6 1.6 0 0 1 1.6 1.6v8.4a1.6 1.6 0 0 1-1.6 1.6H9.6L5.4 20.6v-3.4H4a1.6 1.6 0 0 1-1.6-1.6V7.2A1.6 1.6 0 0 1 4 5.6z"
        fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <circle cx="8.6" cy="11.4" r="1.15" fill="currentColor"/>
        <circle cx="12" cy="11.4" r="1.15" fill="currentColor"/>
        <circle cx="15.4" cy="11.4" r="1.15" fill="currentColor"/>`,
  // Etiqueta de precio con su ojal. Se eligió por descarte: una tarjeta de
  // crédito es otro rectángulo con una línea adentro, y a 23px se confundía
  // con el calendario, que ya es un rectángulo con una línea adentro.
  descuentos:`<path d="M20.4 12.6 12.6 20.4a2.4 2.4 0 0 1-3.4 0l-6-6A2.4 2.4 0 0 1 3 12.7V5.4A2.4 2.4 0 0 1 5.4 3h7.3c.6 0 1.2.3 1.7.7l6 6c.9 1 .9 2.5 0 3.4z"
        fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <circle cx="8.2" cy="8.2" r="1.5" fill="currentColor"/>`,
};
/* index.html es la PORTADA y no está en esta lista a propósito: se llega a
   ella por el logo. Seis destinos no caben en la barra inferior de un
   celular sin que las etiquetas se corten. */
const PAGINAS = [["mapa.html","mapa"],["habla.html","habla"],["calendario.html","calendario"],
                 ["descuentos.html","descuentos"],["blog.html","blog"],
                 ["agrega.html","agregar"],["nosotros.html","nosotros"]];
// En la barra inferior el espacio manda: con SIETE destinos cada celda baja a
// 53 px en un teléfono de 375, así que las etiquetas son de UNA palabra corta
// y ninguna pasa de seis letras. "Calendario" ya no cabía con seis y pasó a
// "Agenda"; "Descuentos" tampoco cabe y va como "Dctos", que es como se
// escribe en cualquier vitrina de Chile. Siete es el techo: un destino más no
// entra sin bajar de los 44 px de área táctil.
const CORTOS = {
  es:{mapa:"Mapa", habla:"Habla", calendario:"Agenda", descuentos:"Dctos", blog:"Blog", agregar:"Publicar", nosotros:"Quién"},
  en:{mapa:"Map", habla:"Talk", calendario:"Agenda", descuentos:"Deals", blog:"Blog", agregar:"Post", nosotros:"Who"},
  pt:{mapa:"Mapa", habla:"Fale", calendario:"Agenda", descuentos:"Dctos", blog:"Blog", agregar:"Publicar", nosotros:"Quem"},
};

/* `raiz` es el prefijo hacia la raíz del sitio. Las fichas de `e/` viven un
   nivel más abajo y le pasan "../"; sin eso su navegación apuntaba a
   `e/calendario.html` y los cinco enlaces daban 404. */
function pintarBarra(paginaActual, raiz = ""){
  // El color de la página activa (nav superior e inferior) sale de este atributo
  const claveActual = (PAGINAS.find(([url]) => url === paginaActual) || [,"portada"])[1];
  document.documentElement.dataset.pagina = claveActual;
  const logo = `<a class="logo" href="${raiz}index.html" aria-label="Loica">
      ${carita("loica", "var(--acento)", 34)}<b>loica</b></a>`;
  const enlaces = PAGINAS
    .map(([url,clave]) => `<a href="${raiz}${url}" data-tr="${clave}"
        ${url===paginaActual?'aria-current="page"':""}>${t(clave)}</a>`).join("");

  // Barra inferior: en celular es la navegación de verdad
  const inferior = document.getElementById("nav-inferior");
  if(inferior){
    inferior.innerHTML = PAGINAS.map(([url,clave]) =>
      `<a href="${raiz}${url}" ${url===paginaActual?'aria-current="page"':""}>
         <svg viewBox="0 0 24 24" aria-hidden="true">${ICONOS_NAV[clave]}</svg>
         <span data-corto="${clave}">${CORTOS[IDIOMA][clave]}</span></a>`).join("");
  }
  const oscuro = document.documentElement.dataset.tema === "oscuro"
    || (!document.documentElement.dataset.tema && matchMedia("(prefers-color-scheme: dark)").matches);

  document.getElementById("barra").innerHTML = `${logo}
    <nav class="nav">${enlaces}</nav>
    <div class="barra-fin">
      <button class="tema" id="btn-tema" aria-label="Cambiar tema">${oscuro ? "☀" : "☾"}</button>
      <div class="idiomas" role="group" aria-label="Idioma">
        ${["es","en","pt"].map(i => `<button data-idioma="${i}"
            aria-pressed="${i===IDIOMA}">${i.toUpperCase()}</button>`).join("")}
      </div>
    </div>`;

  document.getElementById("btn-tema").onclick = e => {
    e.currentTarget.textContent = alternarTema() === "oscuro" ? "☀" : "☾";
  };
  document.querySelectorAll(".idiomas button").forEach(b => b.onclick = () => {
    fijarIdioma(b.dataset.idioma);
    document.querySelectorAll(".idiomas button").forEach(o =>
      o.setAttribute("aria-pressed", o === b));
    document.querySelectorAll("[data-tr]").forEach(el => el.textContent = t(el.dataset.tr));
    document.querySelectorAll("[data-corto]").forEach(el =>
      el.textContent = CORTOS[IDIOMA][el.dataset.corto]);
    window.dispatchEvent(new CustomEvent("loica:idioma"));
  });
}

/* ---------- DATOS ---------- */
async function cargarEventos(){
  // El `?v=N` de loica.css/js no sirve acá: este archivo lo reescribe el robot
  // todas las mañanas y nadie sube un número por eso. Sin esto, quien ya visitó
  // el sitio sigue viendo la cartelera del día que entró por primera vez.
  const r = await fetch("eventos.json", {cache: "no-cache"});
  const d = await r.json();
  return d.eventos.map(ev => ({...ev, fecha: new Date(ev.inicio)}));
}

/* ---------- UTILIDADES ---------- */
const escapar = s => String(s ?? "").replace(/[&<>"]/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

const localeDe = () => IDIOMA === "es" ? "es-CL" : IDIOMA === "pt" ? "pt-BR" : "en-GB";

/* En Chile las horas se leen 19:30, no 07:30 p. m. — y es-CL por defecto
   entrega el formato de 12 horas. */
const horaDe = fecha => fecha.toLocaleTimeString(localeDe(),
  {hour:"2-digit", minute:"2-digit", hour12:false});

function textoPrecio(ev){
  if(ev.gratis) return t("gratis");
  return ev.precio ? "$" + ev.precio.toLocaleString("es-CL") : "—";
}
const mismaFecha = (a,b) => a.toDateString() === b.toDateString();

/* ---------- RANGOS DE FECHA ----------
   "Hoy" y "este finde" no alcanzaban: un martes, "este finde" son cuatro días
   más y "hoy" ya se está acabando. Entre medio no había nada que responder a
   "¿y mañana?", que es la pregunta que uno se hace en el metro de vuelta.

   El fin de semana es el viernes, sábado y domingo que vienen. Si hoy ya es
   viernes, sábado o domingo, es ESTE — no el de la otra semana. */
const empiezaDia = f => { const d = new Date(f); d.setHours(0,0,0,0); return d; };

function ventanaFinde(hoy = new Date()){
  const dia = hoy.getDay();                       // 0 domingo … 6 sábado
  const desde = empiezaDia(hoy);
  // Días hasta el viernes; si ya estamos en vie/sáb/dom la ventana parte hoy
  if(![5,6,0].includes(dia)) desde.setDate(desde.getDate() + (5 - dia));
  const hasta = new Date(desde);
  // Del viernes al domingo hay dos días; desde el sábado o el domingo, menos
  hasta.setDate(desde.getDate() + (desde.getDay() === 5 ? 2 : desde.getDay() === 6 ? 1 : 0));
  hasta.setHours(23,59,59,999);
  return [desde, hasta];
}

const RANGOS = {
  todo:   () => true,
  hoy:    f => mismaFecha(f, new Date()),
  manana: f => { const m = new Date(); m.setDate(m.getDate() + 1); return mismaFecha(f, m); },
  semana: f => { const d = empiezaDia(new Date()), h = new Date(d);
                 h.setDate(d.getDate() + 7); h.setHours(23,59,59,999);
                 return f >= d && f <= h; },
  finde:  f => { const [d,h] = ventanaFinde(); return f >= d && f <= h; },
};
const enRango = (fecha, rango) => (RANGOS[rango] || RANGOS.todo)(fecha);
const claveDia = f => `${f.getFullYear()}-${String(f.getMonth()+1).padStart(2,"0")}-${String(f.getDate()).padStart(2,"0")}`;

/* ---------- COMPARTIR ----------
   El link que viaja SIEMPRE apunta a la ficha del evento en Loica, no a la
   fuente. Así el que recibe el mensaje por WhatsApp llega acá, ve la foto y la
   fecha en la vista previa, y desde acá decide ir a comprar. Es la única forma
   de que el tráfico compartido vuelva al proyecto. */
const SITIO = location.origin + location.pathname.replace(/\/(e\/)?[^/]*$/, "");

function urlDeEvento(ev){
  return `${SITIO}/e/${ev.id}.html`;
}

function textoCompartir(ev){
  const f = new Date(ev.inicio);
  const dia = f.toLocaleDateString(localeDe(), {weekday:"long", day:"numeric", month:"long"});
  const hora = (f.getHours() || f.getMinutes())
    ? " a las " + f.toLocaleTimeString(localeDe(), {hour:"2-digit", minute:"2-digit", hour12:false})
    : "";
  const precio = ev.gratis ? " · Gratis" : (ev.precio ? ` · $${ev.precio.toLocaleString("es-CL")}` : "");
  return `${ev.titulo}\n${dia}${hora} · ${ev.lugar}${precio}`;
}

const REDES = {
  whatsapp:{
    nombre:"WhatsApp", color:"#25D366",
    icono:`<path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38c1.45.79 3.08 1.21 4.79 1.21h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0012.04 2zm5.8 14.1c-.24.68-1.42 1.31-1.95 1.36-.5.05-1.13.07-1.82-.11-.42-.13-.96-.31-1.65-.61-2.9-1.25-4.8-4.17-4.94-4.36-.15-.19-1.19-1.58-1.19-3.02s.76-2.14 1.03-2.44c.27-.29.58-.37.78-.37h.56c.18 0 .42-.07.66.5.24.59.83 2.03.9 2.18.07.15.12.32.02.51-.1.19-.15.31-.3.48l-.44.51c-.15.15-.3.31-.13.61.17.29.76 1.25 1.63 2.03 1.12 1 2.06 1.31 2.35 1.46.29.15.46.12.63-.07.17-.2.73-.85.92-1.14.19-.29.39-.24.66-.15.27.1 1.7.8 1.99.95.29.15.49.22.56.34.07.12.07.71-.17 1.39z" fill="currentColor"/>`,
    url:(u,t)=>`https://wa.me/?text=${encodeURIComponent(t + "\n\n" + u)}`,
  },
  facebook:{
    nombre:"Facebook", color:"#1877F2",
    icono:`<path d="M22 12.06C22 6.5 17.52 2 12 2S2 6.5 2 12.06c0 5.02 3.66 9.18 8.44 9.94v-7.03H7.9v-2.9h2.54V9.85c0-2.52 1.5-3.91 3.77-3.91 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.78-1.63 1.57v1.89h2.78l-.44 2.9h-2.34V22c4.78-.76 8.44-4.92 8.44-9.94z" fill="currentColor"/>`,
    url:(u)=>`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(u)}`,
  },
  x:{
    nombre:"X", color:"#111",
    icono:`<path d="M17.53 3h3.02l-6.6 7.54L21.75 21h-6.08l-4.76-6.22L5.46 21H2.44l7.06-8.07L2.25 3h6.23l4.3 5.69L17.53 3zm-1.06 16.2h1.67L7.6 4.7H5.81l10.66 14.5z" fill="currentColor"/>`,
    url:(u,t)=>`https://twitter.com/intent/tweet?text=${encodeURIComponent(t)}&url=${encodeURIComponent(u)}`,
  },
};

function botonesCompartir(ev){
  const url = urlDeEvento(ev);
  const texto = textoCompartir(ev);
  const caja = document.createElement("div");
  caja.className = "compartir";

  const etiqueta = {es:"Compartir", en:"Share", pt:"Compartilhar"}[IDIOMA];
  caja.innerHTML = `<span class="compartir-titulo">${etiqueta}</span><div class="compartir-botones"></div>`;
  const fila = caja.querySelector(".compartir-botones");

  const boton = (clase, nombre, color, icono, alPulsar) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "red " + clase;
    b.style.setProperty("--red", color);
    b.setAttribute("aria-label", `${etiqueta} — ${nombre}`);
    b.title = nombre;
    b.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">${icono}</svg>`;
    b.onclick = alPulsar;
    fila.appendChild(b);
    return b;
  };

  for(const [clave, red] of Object.entries(REDES)){
    boton(clave, red.nombre, red.color, red.icono,
          () => window.open(red.url(url, texto), "_blank", "noopener,width=620,height=560"));
  }

  // Instagram no permite compartir un link desde la web: no existe una URL de
  // "compartir en Instagram". Lo honesto es abrir el menú del teléfono, que sí
  // lo incluye; y si el navegador no lo tiene, copiar el link.
  const iconoIg = `<rect x="3" y="3" width="18" height="18" rx="5.4" fill="none" stroke="currentColor" stroke-width="1.9"/>
    <circle cx="12" cy="12" r="4.1" fill="none" stroke="currentColor" stroke-width="1.9"/>
    <circle cx="17.2" cy="6.8" r="1.25" fill="currentColor"/>`;
  if(navigator.share){
    boton("instagram", "Instagram / " + etiqueta, "#E1306C", iconoIg,
          () => navigator.share({title: ev.titulo, text: texto, url}).catch(() => {}));
  } else {
    boton("instagram", "Instagram — " + {es:"copiar link", en:"copy link", pt:"copiar link"}[IDIOMA],
          "#E1306C", iconoIg, e => copiarLink(url, e.currentTarget));
  }

  boton("copiar", {es:"Copiar link", en:"Copy link", pt:"Copiar link"}[IDIOMA],
        "var(--tinta-suave)",
        `<path d="M9.5 14.5l5-5M8 12l-2 2a3.5 3.5 0 105 5l2-2M16 12l2-2a3.5 3.5 0 10-5-5l-2 2"
          fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>`,
        e => copiarLink(url, e.currentTarget));

  return caja;
}

function copiarLink(url, boton){
  const listo = () => {
    boton.classList.add("copiado");
    const antes = boton.title;
    boton.title = {es:"¡Copiado!", en:"Copied!", pt:"Copiado!"}[IDIOMA];
    setTimeout(() => { boton.classList.remove("copiado"); boton.title = antes; }, 1800);
  };
  if(navigator.clipboard) navigator.clipboard.writeText(url).then(listo).catch(() => {});
  else {
    const campo = document.createElement("textarea");
    campo.value = url; document.body.appendChild(campo);
    campo.select(); document.execCommand("copy"); campo.remove(); listo();
  }
}

/* Cuándo es, dicho como lo diría una persona */
function etiquetaDia(fecha){
  const hoy = new Date();
  const manana = new Date(hoy); manana.setDate(hoy.getDate() + 1);
  if(mismaFecha(fecha, hoy))
    return {texto: IDIOMA === "en" ? "TODAY" : IDIOMA === "pt" ? "HOJE" : "HOY", pronto: true};
  if(mismaFecha(fecha, manana))
    return {texto: IDIOMA === "en" ? "TOMORROW" : IDIOMA === "pt" ? "AMANHÃ" : "MAÑANA", pronto: true};
  return {texto: `${fecha.getDate()} ${t("mesesCortos")[fecha.getMonth()]}`, pronto: false};
}

/* Tarjeta de evento reutilizada por el mapa y el calendario */
function tarjetaEvento(ev, alPulsar){
  const info = cat(ev.categoria);
  const dia = etiquetaDia(ev.fecha);
  const hora = (ev.fecha.getHours() || ev.fecha.getMinutes()) ? horaDe(ev.fecha) : "";
  const precio = ev.gratis ? t("gratis") : (ev.precio ? "$" + ev.precio.toLocaleString("es-CL") : "");

  const boton = document.createElement("button");
  boton.className = "tarjeta" + (ev.gratis ? " tarjeta-gratis" : "");
  boton.type = "button";
  boton.innerHTML = `
    <div class="miniatura">
      ${carita(info.mascota, info.hex, 44)}
      ${ev.imagen ? `<img src="${escapar(ev.imagen)}" alt="" loading="lazy"
                       onerror="this.remove()">` : ""}
      <span class="dia${dia.pronto ? " pronto" : ""}">${dia.texto}</span>
    </div>
    <div class="tarjeta-cuerpo">
      ${hora ? `<div class="hora">${hora}</div>` : ""}
      <h3>${escapar(ev.titulo)}</h3>
      <div class="tarjeta-meta">
        <span>${escapar(ev.lugar)}</span>
        ${ev.comuna ? `<span>· ${escapar(ev.comuna)}</span>` : ""}
      </div>
    </div>
    <div class="precio${ev.gratis ? " libre" : precio ? "" : " sin-dato"}">${precio || "—"}</div>`;

  boton.onclick = () => alPulsar(ev);
  return boton;
}

/* ---------- DESCUENTOS DE BANCO ----------
   Otro tipo de dato y por eso otra tarjeta. Un evento pasa una vez y lo que
   manda es la fecha; un descuento se repite todas las semanas y lo que manda
   es el DÍA y el banco. La rejilla es la misma que la de eventos (58px, 1fr,
   auto) para que las dos listas se lean como el mismo sistema, pero lo que va
   en cada celda cambia: donde el evento pone la hora, el descuento pone el
   banco, y donde el evento pone el precio, el descuento pone cuánto rebaja. */

/* Un color por banco. No son los colores corporativos a propósito: Loica no
   es el banco y no conviene que lo parezca. Son tres tonos del sistema, bien
   separados entre sí, y el nombre del banco va escrito en la tarjeta igual —
   el color ayuda a barrer la lista, no es el único dato. */
const BANCOS = {
  bancochile:{color:"#1B6FD1", tinta:"var(--c-cultura-tinta)"},
  bci:       {color:"#7A3FE0", tinta:"var(--c-fiesta-tinta)"},
  falabella: {color:"#0E8757", tinta:"var(--c-libre-tinta)"},
  santander: {color:"#C42B67", tinta:"var(--c-charla-tinta)"},
  cencosud:  {color:"#0C8B9B", tinta:"var(--c-deporte-tinta)"},
};
const banco = id => BANCOS[id] || {color:"#95521C", tinta:"var(--c-descuento-tinta)"};

/* El pipeline numera los días de lunes a domingo; getDay() de domingo a
   sábado. Este es el único lugar donde se cruzan las dos escalas. */
const DIAS_CLAVE = ["lunes","martes","miercoles","jueves","viernes","sabado","domingo"];
const hoyClave = () => DIAS_CLAVE[(new Date().getDay() + 6) % 7];

/* Lista de días VACÍA significa "sin restricción", no "no se pudo leer" —
   está explicado en loica/descuentos/modelo.py. Los convenios permanentes de
   Bci son así, y dejarlos fuera del filtro de Hoy sería esconder 229
   descuentos que hoy sirven. */
const correHoy = d => !d.dias.length || d.dias.includes(hoyClave());

const montoDescuento = d => d.porcentaje ? d.porcentaje + "%" : (d.oferta || "");

async function cargarDescuentos(){
  const r = await fetch("descuentos.json");
  return await r.json();
}

/* La cinta del día sobre la miniatura. Es el dato por el que se entra a esta
   página, así que va donde la tarjeta de evento pone la fecha. */
function cintaDia(d){
  const hoy = !d.dias.length || d.dias.includes(hoyClave());
  if(!d.dias.length) return {texto: {es:"TODOS", en:"EVERY DAY", pt:"TODOS"}[IDIOMA], hoy};
  if(d.dias.length > 2) return {texto: `${d.dias.length} ${{es:"DÍAS", en:"DAYS", pt:"DIAS"}[IDIOMA]}`, hoy};
  return {texto: d.dias.map(x => t("dias")[DIAS_CLAVE.indexOf(x)].toUpperCase()).join(" "), hoy};
}

function tarjetaDescuento(d, alPulsar){
  const b = banco(d.banco_id);
  const dia = cintaDia(d);
  const monto = montoDescuento(d);

  const boton = document.createElement("button");
  boton.className = "tarjeta tarjeta-dcto";
  boton.type = "button";
  boton.style.setProperty("--banco", b.color);
  /* Sin el logo del comercio, a diferencia de la tarjeta de evento. No es un
     olvido: los logos viven en el CDN del banco y una lista son ochenta
     imágenes pedidas a assets.bancochile.cl cada vez que alguien hace scroll.
     Este proyecto respeta crawl-delay y robots.txt para leer; gastarle el
     ancho de banda al mismo servidor para decorar sería incoherente. El logo
     sí va en la ficha, que es UNA imagen y solo cuando alguien la pide. */
  boton.innerHTML = `
    <div class="miniatura">
      ${carita("degu", b.color, 44)}
      <span class="dia${dia.hoy ? " pronto" : ""}">${escapar(dia.texto)}</span>
    </div>
    <div class="tarjeta-cuerpo">
      <div class="hora banco-nombre">${escapar(d.banco)}</div>
      <h3>${escapar(d.comercio)}</h3>
      <div class="tarjeta-meta">
        ${d.direccion ? `<span>${escapar(d.direccion)}</span>` : ""}
        ${d.comuna ? `<span>${d.direccion ? "· " : ""}${escapar(d.comuna)}</span>`
                   : d.region ? `<span>${escapar(d.region)}</span>` : ""}
        ${d.segmentado ? `<span class="aviso" title="${escapar(t("dSegmentado"))}">·&nbsp;${
          IDIOMA === "en" ? "segmented" : "segmentado"}</span>` : ""}
      </div>
    </div>
    <div class="precio${monto ? " dcto" : " sin-dato"}">${escapar(monto) || "—"}</div>`;

  boton.onclick = () => alPulsar(d);
  return boton;
}
