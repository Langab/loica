/* ============================================================
   LOICA — módulo compartido
   Mascotas (SVG), traducciones, datos y utilidades comunes.
   ============================================================ */

/* ---------- MASCOTAS ----------
   Once animales chilenos, dibujados en DOS niveles. Un solo SVG no puede
   servir a 22px en un chip y a 200px en la portada: los detalles de r=".4"
   que se veían lindos grandes, chicos no existen (0,3px). Por eso:

     carita(nombre, color)  → viewBox 24, SOLO cabeza.   Para ≤ 34px
     cuerpo(nombre, color)  → viewBox 48, cuerpo entero.  Para ≥ 38px

   `mascota()` elige sola según el tamaño que le pidas.

   Desde el 22-08-2026 (elenco v2) cada animal lleva además:
     - Un ACCESORIO humano que dice su oficio a 22px sin leer la etiqueta:
       la Chinchilla va de boina al teatro, el Pingüino con birrete y libro
       al seminario, el Guarén con la tarjeta del banco en los dientes. Se
       apaga con {acc:false}: el logo va limpio.
     - PARTES con clase (.p-ojos, .p-oreja, .p-cola, .p-ala, .p-acc…) para que
       loica.css las anime sin JavaScript: parpadeo, cola, boina. Los tics se
       encienden con {anima:true} y las entradas con la clase `entra` en el
       contenedor y --d en cada animal (ver "MASCOTAS: partes y tics" en
       loica.css). Con prefers-reduced-motion no pasa nada.

   Reglas de la carita, que son las que la hacen legible chiquitita: cabeza
   ≥70% del alto, ojo de radio ≥1,6, contorno de tinta de 1,6, máximo tres
   rellenos planos. Si un rasgo mide menos de 1/15 del viewBox, no va.

   El contorno usa `var(--contorno)`, así que en modo oscuro la tinta se
   invierte a crema sola. Cuando el SVG se va a rasterizar a canvas (los
   pines del mapa) hay que pasarle un color concreto en `tinta`. */

const TINTA_VAR = "var(--contorno)";
const OJO = "#1E2A4A", CREMA = "#FAF3E7", ROSA = "#F2778C", AMARILLO = "#F5B52E";
const ROJO = "#E8442E", PIEL = "#E8C3B4";

/* Ojos en un grupo animable: el parpadeo es un scaleY sobre `.p-ojos`. */
const ojos = (x1, x2, y, r = 1.75, pose = "posada") => pose === "durmiendo"
  ? `<g class="p-ojos p-dormido"><path d="M${x1 - r} ${y + r * .3}q${r} -${r * 1.3} ${r * 2} 0M${x2 - r} ${y + r * .3}q${r} -${r * 1.3} ${r * 2} 0"
       fill="none" stroke="${OJO}" stroke-width="1.6" stroke-linecap="round"/></g>`
  : `<g class="p-ojos"><circle cx="${x1}" cy="${y}" r="${r}" fill="${OJO}"/>
     <circle cx="${x2}" cy="${y}" r="${r}" fill="${OJO}"/>
     <circle cx="${x1 + r * .32}" cy="${y - r * .38}" r="${r * .38}" fill="#fff"/>
     <circle cx="${x2 + r * .32}" cy="${y - r * .38}" r="${r * .38}" fill="#fff"/></g>`;

/* ---------- ACCESORIOS (lienzo 24, se dibujan sobre la carita) ----------
   Uno por animal. Cada uno tiene un chiste y un trabajo: decir el oficio
   a 22px. Se pueden apagar con {acc:false} (el logo, por ejemplo). */
const ACC = {
  /* La anfitriona: cintillo con micrófono, como la que atiende en la puerta
     del evento. Es la única que habla, así que es la única con micrófono. */
  loica: k => `<g class="p-acc">
    <path d="M4.2 11.2C4.2 5.6 7.6 2.4 12 2.4s7.8 3.2 7.8 8.8" fill="none" stroke="${k}" stroke-width="2.2" stroke-linecap="round"/>
    <path d="M4.2 11.2C4.2 5.6 7.6 2.4 12 2.4s7.8 3.2 7.8 8.8" fill="none" stroke="${CREMA}" stroke-width=".8" stroke-linecap="round"/>
    <rect x="2.6" y="9.6" width="3.2" height="4" rx="1.3" fill="${CREMA}" stroke="${k}" stroke-width="1.1"/>
    <rect x="18.2" y="9.6" width="3.2" height="4" rx="1.3" fill="${CREMA}" stroke="${k}" stroke-width="1.1"/>
    <path class="p-mic" d="M4.2 13.6c.3 2.3 1.8 3.8 4.2 4.2" fill="none" stroke="${k}" stroke-width="1.3" stroke-linecap="round"/>
    <circle class="p-mic" cx="8.9" cy="18.2" r="1.7" fill="${OJO}" stroke="${CREMA}" stroke-width=".8"/></g>`,

  /* El Cóndor baja a escuchar la prueba de sonido: audífonos sobre la
     cabeza pelada. La cinta pasa por detrás de la cresta. */
  condorCinta: k => `<path d="M7 7.4C7 2.9 9.1 1.3 12 1.3s5 1.6 5 6.1" fill="none" stroke="${k}" stroke-width="2.1" stroke-linecap="round"/>`,
  condor: k => `<g class="p-acc">
    <circle cx="6.7" cy="7.4" r="2.7" fill="${OJO}" stroke="${k}" stroke-width="1.1"/>
    <circle cx="17.3" cy="7.4" r="2.7" fill="${OJO}" stroke="${k}" stroke-width="1.1"/>
    <circle cx="6.7" cy="7.4" r="1" fill="${CREMA}" opacity=".7"/>
    <circle cx="17.3" cy="7.4" r="1" fill="${CREMA}" opacity=".7"/></g>`,

  /* El Culpeo sale de noche y nunca se saca los lentes. Reemplazan a los
     ojos: a 22px se leen como 😎, que es exactamente lo que hay que leer. */
  culpeo: k => `<g class="p-acc p-lentes">
    <rect x="5.3" y="9" width="5.8" height="4.4" rx="2" fill="${OJO}" stroke="${k}" stroke-width="1.1"/>
    <rect x="12.9" y="9" width="5.8" height="4.4" rx="2" fill="${OJO}" stroke="${k}" stroke-width="1.1"/>
    <path d="M11.1 10.9h1.8" stroke="${k}" stroke-width="1.3" stroke-linecap="round"/>
    <g class="p-brillo"><path d="M6.8 12.5l2.4-2.5M14.4 12.5l2.4-2.5" stroke="#fff" stroke-width="1.1" stroke-linecap="round" opacity=".9"/></g></g>`,

  /* La Chinchilla va al teatro de boina, ladeada como corresponde. */
  chinchilla: k => `<g class="p-acc p-boina" transform="rotate(-9 12 6.6)">
    <path d="M5.6 7.8c.6-3.6 3.3-5.5 6.5-5.4 3.2.1 5.6 2.1 6.2 5.4-1.7-1.3-3.8-2-6.3-2s-4.7.7-6.4 2z" fill="${OJO}" stroke="${k}" stroke-width="1.2" stroke-linejoin="round"/>
    <path d="M12.2 2.6v-1.3" stroke="${k}" stroke-width="1.5" stroke-linecap="round"/>
    <circle cx="12.2" cy="1.2" r=".8" fill="${ROJO}"/></g>`,

  /* El Chincol anda con el lápiz del taller detrás de la oreja (que no
     tiene: licencia de dibujo animado). Se dibuja ANTES de la cabeza para
     que asome por detrás. */
  chincolAtras: k => `<g class="p-acc p-lapiz" transform="rotate(-46 19 8)">
    <rect x="17.6" y="3.2" width="2.6" height="10.4" rx=".5" fill="${AMARILLO}" stroke="${k}" stroke-width="1"/>
    <path d="M17.6 3.2h2.6L18.9.6z" fill="${CREMA}" stroke="${k}" stroke-width=".9" stroke-linejoin="round"/>
    <path d="M18.5 1.6l.4-1l.4 1z" fill="${OJO}"/>
    <rect x="17.6" y="12.2" width="2.6" height="1.7" fill="${ROSA}" stroke="${k}" stroke-width=".9"/></g>`,

  /* El Pudú lleva pañuelo de scout: es el de los cerros y las familias. */
  pudu: k => `<g class="p-acc">
    <path d="M5.2 19.3c2 1.4 4.3 2.1 6.8 2.1s4.8-.7 6.8-2.1L12 23.8z" fill="${AMARILLO}" stroke="${k}" stroke-width="1.2" stroke-linejoin="round"/>
    <circle cx="12" cy="21" r="1.5" fill="${AMARILLO}" stroke="${k}" stroke-width="1"/></g>`,

  /* El Degú anota lo que no cuesta nada: etiqueta de precio colgando de
     la oreja, y en la etiqueta un cero. Se balancea. */
  degu: k => `<g class="p-acc p-etiqueta">
    <path d="M19.9 3.4c.5 1 .8 2.1.8 3.3" fill="none" stroke="${k}" stroke-width=".9" stroke-linecap="round"/>
    <g transform="rotate(-16 20.4 9)">
      <rect x="16.8" y="6.6" width="6.8" height="4.8" rx="1" fill="${CREMA}" stroke="${k}" stroke-width="1"/>
      <circle cx="18.1" cy="9" r=".6" fill="${k}"/>
      <ellipse cx="21.1" cy="9" rx="1.3" ry="1.65" fill="none" stroke="${OJO}" stroke-width="1.05"/></g></g>`,

  /* El Guarén no suelta la tarjeta: la lleva en los dientes, como lleva
     todo un guarén. Va dorada porque es "la del banco". */
  guaren: k => `<g class="p-acc p-tarjeta" transform="rotate(-12 12 21.4)">
    <rect x="8.1" y="19.2" width="7.8" height="4.6" rx=".8" fill="${AMARILLO}" stroke="${k}" stroke-width="1"/>
    <rect x="8.1" y="20.2" width="7.8" height="1.15" fill="${OJO}"/>
    <rect x="9.1" y="22" width="2.4" height=".9" fill="${CREMA}" opacity=".95"/></g>`,

  /* El Chungungo entrena: cintillo de toalla y dos gotas de sudor. */
  chungungo: k => `<g class="p-acc">
    <path d="M4.4 8.8c2.2-1.4 4.7-2.1 7.6-2.1s5.4.7 7.6 2.1" fill="none" stroke="${k}" stroke-width="3.6" stroke-linecap="round"/>
    <path d="M4.4 8.8c2.2-1.4 4.7-2.1 7.6-2.1s5.4.7 7.6 2.1" fill="none" stroke="${CREMA}" stroke-width="2" stroke-linecap="round"/>
    <g class="p-sudor"><path d="M2.9 5.2c-.9 1.3-.9 2.2 0 2.5.9-.3.9-1.2 0-2.5z" fill="#7DA5D5"/>
    <path d="M21.1 5.2c-.9 1.3-.9 2.2 0 2.5.9-.3.9-1.2 0-2.5z" fill="#7DA5D5"/></g></g>`,

  /* El Pingüino, que ya nació de terno, se pone el birrete para el
     seminario. La borla cuelga a la derecha y se mece. */
  pinguino: k => `<g class="p-acc p-birrete">
    <path d="M8 5.4v2.3c0 1.3 1.8 2.1 4 2.1s4-.8 4-2.1V5.4" fill="${OJO}" stroke="${k}" stroke-width="1"/>
    <path d="M3.4 4.6 12 1.2l8.6 3.4L12 8z" fill="${OJO}" stroke="${k}" stroke-width="1.1" stroke-linejoin="round"/>
    <g class="p-borla"><path d="M12.2 1.6c2.6.5 4.9 1.7 5.8 3.4v3.1" fill="none" stroke="${AMARILLO}" stroke-width="1" stroke-linecap="round"/>
    <circle cx="18" cy="8.9" r="1.05" fill="${AMARILLO}" stroke="${k}" stroke-width=".7"/></g></g>`,

  /* La Cabra entra con los lentes 3D puestos. Es el accesorio que más
     trabaja del elenco: a 22px nadie distingue una cabra de un pudú, pero
     dos lentes —uno rojo y uno cian— dicen "cine" antes de que se lea la
     etiqueta. Los cristales van translúcidos y por debajo, así que los ojos
     siguen viéndose y siguen parpadeando: con lentes opacos la cara quedaba
     muerta. */
  cabra: k => `<g class="p-acc p-lentes">
    <path d="M3.4 10.9h17.2" stroke="${k}" stroke-width="1.3" stroke-linecap="round"/>
    <rect x="4.6" y="10.1" width="6.2" height="4.6" rx="1.2" fill="${ROJO}" fill-opacity=".5"
          stroke="${k}" stroke-width="1.2"/>
    <rect x="13.2" y="10.1" width="6.2" height="4.6" rx="1.2" fill="#2FBBD1" fill-opacity=".5"
          stroke="${k}" stroke-width="1.2"/>
    <path d="M10.8 11.6h2.4" stroke="${k}" stroke-width="1.2" stroke-linecap="round"/>
    <path d="M4.6 11.4 3 10.4M19.4 11.4 21 10.4" stroke="${k}" stroke-width="1.2"
          stroke-linecap="round"/></g>`,

  /* El Quiltro ya tiene puesta la servilleta: estaba afuera del local
     antes que tú. La lengua le cae encima. */
  quiltro: k => `<g class="p-acc">
    <path d="M5.4 19.2c1.9 1.5 4.1 2.3 6.6 2.3s4.7-.8 6.6-2.3l-1.3 4.8H6.7z" fill="${CREMA}" stroke="${k}" stroke-width="1.1" stroke-linejoin="round"/>
    <path d="M7.4 22.6h9.2" stroke="${ROJO}" stroke-width=".9" opacity=".85"/></g>`,
};

/* ---------- CARITAS (lienzo 24, solo cabeza; para ≤ 34px) ----------
   Las mismas señas de especie de loica.js; cambian las partes con clase
   y el accesorio. `a` = true dibuja el accesorio. */
const cabezaCondor = (k, p, a) => `
  ${a ? ACC.condorCinta(k) : ""}
  <g class="p-cabeza">
  <ellipse cx="12" cy="6.6" rx="4.9" ry="4.3" fill="#C0766B" stroke="${k}" stroke-width="1.5"/>
  <path d="M9 4.6c.4-2.2 1.5-3.3 3-3.3s2.6 1.1 3 3.3c-.9-.7-1.9-1.1-3-1.1s-2.1.4-3 1.1z"
        fill="#C0766B" stroke="${k}" stroke-width="1.2" stroke-linejoin="round"/>
  <path d="M10.5 7.9h3c.9 0 1.5.8 1.3 1.7-.4 1.9-1.3 3.5-2.8 4.5-1.5-1-2.4-2.6-2.8-4.5-.2-.9.4-1.7 1.3-1.7z"
        fill="${CREMA}" stroke="${k}" stroke-width="1.2" stroke-linejoin="round"/>
  <ellipse cx="12" cy="13.3" rx="1.2" ry="1" fill="${OJO}"/>
  ${ojos(9.9, 14.1, 6.2, 1.6, p)}
  ${a ? ACC.condor(k) : ""}</g>`;

const oreja = (lado, svg) => `<g class="p-oreja p-oreja-${lado}">${svg}</g>`;

const CARITAS = {
  loica: (c, k, p, a) => `
    <circle cx="12" cy="12.2" r="8.6" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="16.6" rx="5.6" ry="3.6" fill="${ROJO}" stroke="${k}" stroke-width="1.2"/>
    <path d="M6.3 8.1c1.2-1.2 3-1.5 4.4-.8M17.7 8.1c-1.2-1.2-3-1.5-4.4-.8"
          fill="none" stroke="${CREMA}" stroke-width="1.5" stroke-linecap="round"/>
    <path class="p-pico" d="M10.5 12.1h3L12 20.4z" fill="${k}" stroke="${k}" stroke-width="1" stroke-linejoin="round"/>
    ${ojos(8.7, 15.3, 10.1, 1.8, p)}
    ${a ? ACC.loica(k) : ""}`,

  condor: (c, k, p, a) => `
    <ellipse cx="12" cy="17.2" rx="8.7" ry="5.2" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <path d="M6.6 14.6c-.6-1.8.6-3.4 2.4-3.3.2-1.2 1.4-2 3-2s2.8.8 3 2c1.8-.1 3 1.5 2.4 3.3-.6 1.9-2.7 3-5.4 3s-4.8-1.1-5.4-3z"
          fill="${CREMA}" stroke="${k}" stroke-width="1.3" stroke-linejoin="round"/>
    ${cabezaCondor(k, p, a)}`,

  culpeo: (c, k, p, a) => `
    ${oreja("i", `<path d="M5.6 11 6.6 3.1 11.6 6.9z" fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M7.2 8.8 7.7 5.4 10 7.1z" fill="${ROSA}" opacity=".75"/>`)}
    ${oreja("d", `<path d="M18.4 11 17.4 3.1 12.4 6.9z" fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M16.8 8.8 16.3 5.4 14 7.1z" fill="${ROSA}" opacity=".75"/>`)}
    <path d="M12 5c-4.6 0-7.8 2.6-7.8 6.2 0 2.1.8 3.9 2.2 5.3 1.5 1.6 3.4 3.9 5.6 3.9s4.1-2.3 5.6-3.9c1.4-1.4 2.2-3.2 2.2-5.3 0-3.6-3.2-6.2-7.8-6.2z"
          fill="${c}" stroke="${k}" stroke-width="1.6" stroke-linejoin="round"/>
    <ellipse cx="12" cy="17.8" rx="3" ry="3.4" fill="${CREMA}" stroke="${k}" stroke-width="1.4"/>
    ${a ? ACC.culpeo(k) : ojos(8.7, 15.3, 11.2, 1.7, p)}
    <ellipse cx="12" cy="16.4" rx="1.5" ry="1.2" fill="${OJO}"/>`,

  pudu: (c, k, p, a) => `
    <path d="M9.7 5 8.9 1.7M14.3 5 15.1 1.7" stroke="${k}" stroke-width="2" stroke-linecap="round"/>
    ${oreja("i", `<ellipse cx="7" cy="6.1" rx="3" ry="2.3" transform="rotate(-38 7 6.1)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="6.9" cy="6" rx="1.5" ry="1.05" transform="rotate(-38 6.9 6)" fill="${ROSA}" opacity=".65"/>`)}
    ${oreja("d", `<ellipse cx="17" cy="6.1" rx="3" ry="2.3" transform="rotate(38 17 6.1)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="17.1" cy="6" rx="1.5" ry="1.05" transform="rotate(38 17.1 6)" fill="${ROSA}" opacity=".65"/>`)}
    <circle cx="12" cy="13" r="8" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="17.7" rx="3.3" ry="2.9" fill="${CREMA}"/>
    ${ojos(8.8, 15.2, 12.2, 1.8, p)}
    <ellipse cx="12" cy="16.5" rx="1.7" ry="1.3" fill="${OJO}"/>
    ${a ? ACC.pudu(k) : ""}`,

  chincol: (c, k, p, a) => `
    ${a ? ACC.chincolAtras(k) : ""}
    <path class="p-copete" d="M8.4 7.4 9.4 1.8 12 5.2 14.6 1.8 15.6 7.4z" fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <circle cx="12" cy="12.5" r="8.4" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <path d="M8.6 5.6c-1.7 1.3-2.8 3.1-3.2 5.2M15.4 5.6c1.7 1.3 2.8 3.1 3.2 5.2"
          fill="none" stroke="${k}" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M5.4 14.9c1.5 3.2 3.8 4.9 6.6 4.9s5.1-1.7 6.6-4.9"
          fill="none" stroke="#B0561F" stroke-width="2.8" stroke-linecap="round"/>
    <path d="M10.4 12.9h3.2L12 16.4z" fill="#E8B23A" stroke="${k}" stroke-width="1.1" stroke-linejoin="round"/>
    ${ojos(8.8, 15.2, 10.4, 1.75, p)}`,

  chinchilla: (c, k, p, a) => `
    ${oreja("i", `<circle cx="5.8" cy="7.6" r="3.7" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <circle cx="6" cy="7.9" r="1.8" fill="${ROSA}" opacity=".6"/>`)}
    ${oreja("d", `<circle cx="18.2" cy="7.6" r="3.7" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <circle cx="18" cy="7.9" r="1.8" fill="${ROSA}" opacity=".6"/>`)}
    <circle cx="12" cy="13.2" r="7.8" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="16.9" rx="3.4" ry="2.7" fill="${CREMA}"/>
    ${ojos(9, 15, 12.2, 1.75, p)}
    <ellipse cx="12" cy="15.7" rx="1.25" ry="1" fill="${OJO}"/>
    ${a ? ACC.chinchilla(k) : ""}`,

  degu: (c, k, p, a) => `
    ${oreja("i", `<ellipse cx="6.1" cy="6.2" rx="2.8" ry="3.4" transform="rotate(-24 6.1 6.2)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="6.2" cy="6.4" rx="1.35" ry="1.75" transform="rotate(-24 6.2 6.4)" fill="${ROSA}" opacity=".6"/>`)}
    ${oreja("d", `<ellipse cx="17.9" cy="6.2" rx="2.8" ry="3.4" transform="rotate(24 17.9 6.2)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="17.8" cy="6.4" rx="1.35" ry="1.75" transform="rotate(24 17.8 6.4)" fill="${ROSA}" opacity=".6"/>`)}
    <circle cx="12" cy="13" r="8.1" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <circle cx="8.7" cy="11.7" r="2.95" fill="${CREMA}"/>
    <circle cx="15.3" cy="11.7" r="2.95" fill="${CREMA}"/>
    <ellipse cx="12" cy="17.5" rx="3.7" ry="3" fill="${CREMA}"/>
    ${ojos(8.7, 15.3, 11.7, 1.8, p)}
    <ellipse class="p-nariz" cx="12" cy="15.9" rx="1.6" ry="1.2" fill="${OJO}"/>
    <path d="M10.9 17.4h2.2v1.5a1.1 1.1 0 0 1-2.2 0z" fill="#E8B23A" stroke="${k}" stroke-width="1"/>
    ${a ? ACC.degu(k) : ""}`,

  guaren: (c, k, p, a) => `
    ${oreja("i", `<circle cx="6.8" cy="5.6" r="3.6" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <circle cx="6.9" cy="5.8" r="1.8" fill="${ROSA}" opacity=".7"/>`)}
    ${oreja("d", `<circle cx="17.2" cy="5.6" r="3.6" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <circle cx="17.1" cy="5.8" r="1.8" fill="${ROSA}" opacity=".7"/>`)}
    <path d="M4.1 11.2a7.9 7.9 0 0 1 15.8 0c0 3.2-1.4 5.9-3.3 8-1.7 1.9-3.2 3.4-4.6 3.4s-2.9-1.5-4.6-3.4c-1.9-2.1-3.3-4.8-3.3-8z"
          fill="${c}" stroke="${k}" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M8.5 15.2c1-.5 2.2-.8 3.5-.8s2.5.3 3.5.8c-.5 3.3-1.7 5.9-3.5 7.9-1.8-2-3-4.6-3.5-7.9z" fill="${CREMA}"/>
    ${ojos(8.6, 15.4, 11.6, 1.8, p)}
    <ellipse cx="12" cy="18.5" rx="1.45" ry="1.1" fill="${OJO}"/>
    ${a ? ACC.guaren(k) : ""}
    <path d="M10.9 19.5h2.2v2.2a1.1 1.1 0 0 1-2.2 0z" fill="${CREMA}" stroke="${k}" stroke-width="1.05" stroke-linejoin="round"/>
    <path d="M12 19.8v1.9" stroke="${k}" stroke-width=".85"/>`,

  chungungo: (c, k, p, a) => `
    ${oreja("i", `<circle cx="3.9" cy="9.8" r="1.9" fill="${c}" stroke="${k}" stroke-width="1.4"/>`)}
    ${oreja("d", `<circle cx="20.1" cy="9.8" r="1.9" fill="${c}" stroke="${k}" stroke-width="1.4"/>`)}
    <path d="M12 5.6c-5.4 0-9.4 2.9-9.4 6.9 0 3.8 4 6.7 9.4 6.7s9.4-2.9 9.4-6.7c0-4-4-6.9-9.4-6.9z"
          fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="15.1" rx="5" ry="3.2" fill="${CREMA}"/>
    <path d="M6.7 14.4 4 13.7M6.9 16.2 4.2 16.7M17.3 14.4 20 13.7M17.1 16.2 19.8 16.7"
          fill="none" stroke="${k}" stroke-width="1.5" stroke-linecap="round"/>
    ${ojos(8.5, 15.5, 10.4, 1.7, p)}
    <ellipse cx="12" cy="13.3" rx="1.9" ry="1.4" fill="${OJO}"/>
    ${a ? ACC.chungungo(k) : ""}`,

  quiltro: (c, k, p, a) => `
    ${oreja("i", `<path d="M4.8 12.4 5.4 3.6 11.4 7.8z" fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M6.7 9.8 7.1 5.8 9.7 7.6z" fill="${ROSA}" opacity=".75"/>`)}
    ${oreja("d", `<path d="M17.4 5.2c3-.4 5.2 1.6 5 4.6-.2 3-2.2 5.4-4.6 6-1.8.4-3-.8-2.8-2.8.2-3 1-5.6 2.4-7.8z"
          fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M18.1 7.6c1.6-.2 2.6.8 2.5 2.4-.1 1.6-1.1 2.8-2.4 3.1z" fill="${ROSA}" opacity=".7"/>`)}
    <circle cx="12" cy="12.4" r="8.3" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="16.6" rx="5.4" ry="4" fill="${CREMA}"/>
    ${ojos(8.7, 15.3, 10.8, 1.8, p)}
    <ellipse cx="12" cy="15.4" rx="2" ry="1.5" fill="${OJO}"/>
    ${a ? ACC.quiltro(k) : ""}
    <path class="p-lengua" d="M10.8 18.9h2.4v2.5a1.2 1.2 0 0 1-2.4 0z"
          fill="${ROSA}" stroke="${k}" stroke-width="1.1" stroke-linejoin="round"/>`,

  /* La Cabra: cuernos hacia atrás, orejas caídas al costado y la chivita.
     Los tres rasgos juntos son lo que la separa del Pudú, que es el otro
     herbívoro chico del elenco: el pudú lleva astas rectas y cortas hacia
     ARRIBA y orejas redondas; ésta lleva cuernos curvos hacia ATRÁS, orejas
     largas hacia los lados y barba. La cara va más alta que ancha porque una
     cabra tiene el hocico largo, y eso se nota aunque el dibujo sea chico. */
  cabra: (c, k, p, a) => `
    <path d="M9.3 7.2C8.4 4.4 7.2 2.6 5.6 1.8M14.7 7.2c.9-2.8 2.1-4.6 3.7-5.4"
          fill="none" stroke="${k}" stroke-width="2.4" stroke-linecap="round"/>
    <path d="M9.3 7.2C8.4 4.4 7.2 2.6 5.6 1.8M14.7 7.2c.9-2.8 2.1-4.6 3.7-5.4"
          fill="none" stroke="#C7B9A4" stroke-width="1.1" stroke-linecap="round"/>
    ${oreja("i", `<ellipse cx="4.5" cy="11.6" rx="3.4" ry="1.9" transform="rotate(20 4.5 11.6)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="4.7" cy="11.7" rx="1.7" ry=".85" transform="rotate(20 4.7 11.7)" fill="${ROSA}" opacity=".6"/>`)}
    ${oreja("d", `<ellipse cx="19.5" cy="11.6" rx="3.4" ry="1.9" transform="rotate(-20 19.5 11.6)" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <ellipse cx="19.3" cy="11.7" rx="1.7" ry=".85" transform="rotate(-20 19.3 11.7)" fill="${ROSA}" opacity=".6"/>`)}
    <path d="M12 5.9c-4.2 0-7.1 2.4-7.1 5.9 0 2.4.7 4.5 1.9 6.1C8.1 19.7 9.9 21 12 21s3.9-1.3 5.2-3.1c1.2-1.6 1.9-3.7 1.9-6.1 0-3.5-2.9-5.9-7.1-5.9z"
          fill="${c}" stroke="${k}" stroke-width="1.6" stroke-linejoin="round"/>
    <ellipse cx="12" cy="17.6" rx="3.5" ry="2.9" fill="${CREMA}"/>
    ${ojos(8.8, 15.2, 12.3, 1.75, p)}
    <ellipse cx="12" cy="16.6" rx="1.5" ry="1.05" fill="${OJO}"/>
    <path class="p-chiva" d="M10.4 20.2h3.2l-1.6 3.6z" fill="${CREMA}" stroke="${k}"
          stroke-width="1.1" stroke-linejoin="round"/>
    ${a ? ACC.cabra(k) : ""}`,

  pinguino: (c, k, p, a) => `
    <circle cx="12" cy="12.2" r="8.6" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <path d="M7 6.2c-2 1.9-2.6 4.7-1.9 7.2.8 2.9 3.5 4.9 6.9 4.9s6.1-2 6.9-4.9c.7-2.5.1-5.3-1.9-7.2"
          fill="none" stroke="${CREMA}" stroke-width="1.9" stroke-linecap="round"/>
    <ellipse cx="12" cy="12.3" rx="2.6" ry="1.4" fill="${ROSA}"/>
    <path d="M10.6 12.1h2.8L12 16.3z" fill="${k}" stroke="${k}" stroke-width="1" stroke-linejoin="round"/>
    ${ojos(8.6, 15.4, 10, 1.75, p)}
    ${a ? ACC.pinguino(k) : ""}`,
};

/* ---------- CUERPOS (lienzo 48) ---------- */
const cola = (d, c, k, grosor = 5.4) =>
  `<path d="${d}" fill="none" stroke="${k}" stroke-width="${grosor}" stroke-linecap="round"/>
   <path d="${d}" fill="none" stroke="${c}" stroke-width="${grosor - 2.4}" stroke-linecap="round"/>`;

const AVES = new Set(["loica", "condor", "chincol"]);

/* Las alas van en grupos con clase: en vuelo aletean (dos cuadros, steps).
   El Chincol de cuerpo entero carga la bolsa de feria colgando del ala. */
const PROPS = {
  chincol: k => `<g class="p-prop p-bolsa" transform="translate(31 30)">
    <path d="M-5 1.2 -3.6 12.4h9.4L7.4 1.2z" fill="#2F6FB5" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>
    <path d="M-2.6 3.6l1.6 8.2M1.2 3.6v8.2M5 3.6l-1.6 8.2M-4 6.6h10.6M-3.4 9.6h9.4" stroke="${CREMA}" stroke-width=".9" opacity=".7"/>
    <path d="M-2.4 1.2c0-2.2 1.5-3.6 3.6-3.6s3.6 1.4 3.6 3.6" fill="none" stroke="${k}" stroke-width="1.8"/>
    <path d="M4.4 1.2c.6-3.4 2.4-5.8 4.6-7.2" fill="none" stroke="#2E7D5B" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M8.6-5.6l1.8-3.2M9.2-5.2l2.6-1.4" stroke="#74A68D" stroke-width="2" stroke-linecap="round"/></g>`,
  pudu: k => `<g class="p-prop p-mochila">
    <rect x="30.2" y="19.2" width="8.6" height="8" rx="2.6" fill="${AMARILLO}" stroke="${k}" stroke-width="1.8"/>
    <path d="M32 23.4h5" stroke="${k}" stroke-width="1.4" stroke-linecap="round"/>
    <rect x="32.4" y="18" width="4.2" height="2.2" rx="1" fill="${AMARILLO}" stroke="${k}" stroke-width="1.4"/></g>`,
  chungungo: k => `<g class="p-prop p-dorsal">
    <rect x="22.4" y="28.2" width="9.4" height="7.4" rx="1" fill="${CREMA}" stroke="${k}" stroke-width="1.5"/>
    <path d="M25.2 30.6h3.8l-2.6 3.6" fill="none" stroke="${OJO}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="23.7" cy="29.4" r=".55" fill="${k}"/><circle cx="30.5" cy="29.4" r=".55" fill="${k}"/></g>`,
  /* La caja de cabritas, que es el chiste entero: en Chile a las palomitas
     se les dice cabritas. Va al costado, del tamaño en que se lee a 48px:
     rayas rojas y crema, y los granos asomando arriba. */
  cabra: k => `<g class="p-prop p-cabritas" transform="translate(35.4 28.6) scale(.88)">
    <path d="M-6 3.4 -4.6 15.4h9.2L6 3.4z" fill="${CREMA}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>
    <path d="M-4.4 3.4 -3.4 15.4M-1 3.4v12M2.4 3.4l.6 12" stroke="${ROJO}" stroke-width="1.9" opacity=".9"/>
    <circle cx="-3.4" cy="2.2" r="2.5" fill="${AMARILLO}" stroke="${k}" stroke-width="1.3"/>
    <circle cx=".6" cy=".6" r="2.7" fill="${CREMA}" stroke="${k}" stroke-width="1.3"/>
    <circle cx="4.2" cy="2.4" r="2.3" fill="${AMARILLO}" stroke="${k}" stroke-width="1.3"/></g>`,
  pinguino: k => `<g class="p-prop p-libro" transform="rotate(-8 12 32)">
    <rect x="7.2" y="27.2" width="8.4" height="10.6" rx="1" fill="${OJO}" stroke="${k}" stroke-width="1.5"/>
    <rect x="8.8" y="27.2" width="6.8" height="10.6" fill="${CREMA}" stroke="${k}" stroke-width="1.2"/>
    <path d="M10.6 30.2h3.4M10.6 32.4h3.4M10.6 34.6h2.2" stroke="${OJO}" stroke-width=".9" stroke-linecap="round"/></g>`,
};

const cuerpoAve = (nombre, c, k, p, a) => {
  const alas = p === "volando" || p === "celebrando";
  const condor = nombre === "condor", esLoica = nombre === "loica";
  const alaIzq = condor ? "M24 27 5.8 11.6 3 15 7 17.4 3.4 20.2 8.4 21.2 5.8 24.8 16.4 33z"
                        : "M24 27 5.6 11.4 2.8 25.6 16.4 33z";
  const alaDer = condor ? "M24 27 42.2 11.6 45 15 41 17.4 44.6 20.2 39.6 21.2 42.2 24.8 31.6 33z"
                        : "M24 27 42.4 11.4 45.2 25.6 31.6 33z";
  return `
    ${alas ? `<g class="p-ala p-ala-i"><path d="${alaIzq}" fill="${c}" stroke="${k}" stroke-width="2" stroke-linejoin="round"/></g>
              <g class="p-ala p-ala-d"><path d="${alaDer}" fill="${c}" stroke="${k}" stroke-width="2" stroke-linejoin="round"/></g>` : ""}
    ${p === "volando" ? "" : `<path d="M20.4 39.6v4.8M27.2 39.6v4.8M17.8 44.6h5.2M24.6 44.6h5.2"
        stroke="${k}" stroke-width="2.3" stroke-linecap="round"/>`}
    <g class="p-cola"><path d="${esLoica ? "M17 30.2 2.2 39.4 13 22.4z" : "M16.6 30.6 3 37.2 13.6 22.4z"}"
          fill="${c}" stroke="${k}" stroke-width="2" stroke-linejoin="round"/></g>
    <ellipse cx="24.6" cy="30.2" rx="${condor ? 12.2 : 11.4}" ry="${condor ? 10.4 : 10}"
             fill="${c}" stroke="${k}" stroke-width="2"/>
    ${esLoica ? `<ellipse cx="24.2" cy="25.8" rx="6.4" ry="5.4" fill="${ROJO}"/>` : ""}
    ${alas || condor ? "" : `<g class="p-ala p-ala-plegada"><path d="M27.8 22.6c4.4.8 7.4 4 7.6 8 .1 2.9-1 5.6-3 7.6l-1.1-2.5-1.5 2.3c-1.8-2.1-2.8-4.8-2.8-7.7 0-2.7.3-5.3.8-7.7z"
        fill="${c}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/></g>`}
    ${a && PROPS[nombre] && !alas ? PROPS[nombre](k) : ""}
    ${condor
      ? `<path d="M14.6 19.8c-1-3.2 1-6 4.2-5.8.4-2.2 2.5-3.6 5.8-3.6s5.4 1.4 5.8 3.6c3.2-.2 5.2 2.6 4.2 5.8-1 3.2-4.9 5-10 5s-9-1.8-10-5z"
           fill="${CREMA}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>
         <g transform="translate(11.2 .4) scale(1.12)">${cabezaCondor(k, p, a)}</g>`
      : `<g class="p-cabeza" transform="translate(14.9 1.2) scale(.93)">${CARITAS[nombre](c, k, p, a)}</g>`}`;
};

const COLAS = {
  culpeo:     (c, k) => cola("M37.4 32.4c3.6-1.2 5.9-4.3 6.6-8.8", c, k, 8) +
                        `<circle cx="44" cy="23.6" r="2.7" fill="${OJO}" stroke="${k}" stroke-width="1.4"/>`,
  pudu:       (c, k) => `<path d="M39.6 27.6c1.5-2.7 3.9-3.2 4.9-1.6 1 1.7-.1 3.9-2.3 4.6z"
                          fill="${c}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>`,
  chinchilla: (c, k) => cola("M36.6 30.2c-.9-4.4.7-8.6 4-10.4.8-.5 1.6-.7 2.4-.6", c, k, 7.5),
  degu:       (c, k) => cola("M37.2 30.6c3.4-1.2 5.4-4 5.8-8", c, k, 4.8) +
                        `<ellipse cx="43.6" cy="20.6" rx="2.1" ry="3.3" transform="rotate(14 43.6 20.6)"
                           fill="${OJO}" stroke="${k}" stroke-width="1.4"/>`,
  chungungo:  (c, k) => `<path d="M38.2 29.2c4.2-.2 7.6 2.5 8.8 6.6.3 1-.8 1.9-1.7 1.3-3.3-2-5.9-4.7-7.1-7.9z"
                          fill="${c}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>`,
  guaren:     (c, k) => cola("M37.6 32.6c5.4.4 8.8-2.6 10.2-9", PIEL, k, 4),
  /* La cola de la cabra es corta y parada, no cuelga: es medio centímetro de
     pelo apuntando al cielo y sin eso el cuerpo se lee como un pudú. */
  cabra:      (c, k) => `<path d="M38.4 26.4c.6-2.6 2.4-3.8 3.8-2.8 1.4 1 1.2 3.2-.4 4.6z"
                          fill="${c}" stroke="${k}" stroke-width="1.8" stroke-linejoin="round"/>`,
  quiltro:    (c, k) => cola("M37.6 29c4-1.2 6.4-4.2 6.6-8 .1-2.1-1.3-3.4-3-3-1.6.4-2.5 1.9-2.3 3.6", c, k, 5),
};

const CUADRUPEDOS = {
  culpeo:     {cuerpo:[29.4, 31.2, 12.2, 8.6], grosor:3.4, cabeza:"2.5 3.4",
               patas:"M21.6 38.6v5.6M28 38.8v5.4M34.4 38.4v5.8M39.4 37.6v6.4",
               extra:`<ellipse cx="19.6" cy="27.6" rx="3.4" ry="4.2" fill="${CREMA}"/>`},
  pudu:       {cuerpo:[28.8, 30.8, 11.4, 8.2], grosor:2.7, cabeza:"2.5 3.4",
               patas:"M21.8 38.2v6.4M27.4 38.6v6M33.6 38.4v6.2M38.6 37.4v7.2", extra:""},
  chinchilla: {cuerpo:[28.4, 31.4, 10.8, 9.6], grosor:3.2, cabeza:"4.4 5.2", /* era "2.5 3.4" y dejaba la cabeza despegada del cuerpo: el único    cuadrúpedo de los ocho al que le pasaba. Se nota en todas las    páginas y más desde que el calendario la saca a 92px. */
               patas:"M22.6 39.8v4.4M27.8 40.2v4M33.4 39.8v4.4M37.6 38.8v5.2", extra:""},
  degu:       {cuerpo:[28.6, 31.8, 11.4, 8.4], grosor:3, cabeza:"2.5 3.4",
               patas:"M22.2 39.4v5M27.6 39.8v4.6M33.4 39.4v5M38 38.6v5.6",
               extra:`<ellipse cx="27.4" cy="37.4" rx="5.4" ry="2.3" fill="${CREMA}" opacity=".85"/>`},
  chungungo:  {cuerpo:[28.6, 33, 13.8, 7.4], grosor:3.2, cabeza:"3 8.2",
               patas:"M20.8 39.4v4.8M26.6 39.8v4.4M33.2 39.6v4.6M38.2 38.6v5.4", extra:""},
  guaren:     {cuerpo:[28.4, 31.8, 12, 8], grosor:2.8, cabeza:"3.2 4.6",
               patas:"M21.8 39.2v5.4M27.4 39.6v5M33.4 39.2v5.4M38.2 38.4v6", extra:""},
  cabra:      {cuerpo:[28.6, 31, 11.6, 8.4], grosor:2.9, cabeza:"2.5 3.4",
               patas:"M21.6 38.6v6M27.4 39v5.6M33.6 38.6v6M38.4 37.8v6.8",
               extra:`<ellipse cx="27.4" cy="35" rx="7.4" ry="3.1" fill="${CREMA}" opacity=".92"/>`},
  quiltro:    {cuerpo:[28.4, 31.6, 12.4, 8.8], grosor:3.5, cabeza:"2.5 3.4",
               patas:"M21.8 39.2v5.2M27.6 39.6v4.8M33.8 39.2v5.2M38.4 38.4v6",
               extra:`<ellipse cx="28.4" cy="37.4" rx="8.2" ry="3.4" fill="${CREMA}" opacity=".92"/>`},
};

const BIGOTES_CHINCHILLA = `
  <path d="M9.2 18.6 4.6 17.2M9.4 20.4 4.8 20.8M18.6 18.6 23.2 17.2M18.4 20.4 23 20.8"
        fill="none" stroke-width="1.2" stroke-linecap="round"/>`;

/* Celebrando, el cuadrúpedo se para en dos patas: todo el cuerpo gira
   desde las patas traseras. Antes la pose era idéntica a "posada" y el
   carnet mostraba dos dibujos iguales uno al lado del otro. */
const cuerpoCuadrupedo = (nombre, c, k, p, a) => {
  const q = CUADRUPEDOS[nombre], [bx, by, brx, bry] = q.cuerpo;
  const celebra = p === "celebrando";
  return `${celebra ? `<g transform="rotate(-16 38 44)">` : ""}
  <path class="p-patas" d="${q.patas}" stroke="${k}" stroke-width="${q.grosor}" stroke-linecap="round"/>
  <g class="p-cola">${COLAS[nombre](c, k)}</g>
  <ellipse cx="${bx}" cy="${by}" rx="${brx}" ry="${bry}" fill="${c}" stroke="${k}" stroke-width="2"/>
  ${q.extra}
  ${a && PROPS[nombre] ? PROPS[nombre](k) : ""}
  <g class="p-cabeza" transform="translate(${q.cabeza}) scale(.95)${celebra ? " rotate(10 12 14)" : ""}">${CARITAS[nombre](c, k, p, a)}</g>
  ${nombre === "chinchilla" ? `<g stroke="${k}">${BIGOTES_CHINCHILLA}</g>` : ""}${celebra ? "</g>" : ""}`;
};

const cuerpoPinguino = (c, k, p, a) => {
  const ang = p === "celebrando" ? 150 : p === "volando" ? 95 : 14;
  const aleta = (sx, s, cl) => `<g class="p-aleta ${cl}" transform="translate(${sx} 24.4) rotate(${s * ang})">
      <ellipse cx="0" cy="5.6" rx="2.1" ry="5.8" fill="${c}" stroke="${k}" stroke-width="1.8"/></g>`;
  return `
  ${p === "volando" ? "" : `<path d="M20.4 41.2l-2.1 3.4h4.6zM27.6 41.2l-2.1 3.4h4.6z"
        fill="${ROSA}" stroke="${k}" stroke-width="1.3" stroke-linejoin="round"/>`}
  <ellipse cx="24" cy="30" rx="10.6" ry="12.2" fill="${c}" stroke="${k}" stroke-width="2"/>
  <ellipse cx="24" cy="31.6" rx="6.8" ry="9.2" fill="${CREMA}"/>
  <path d="M17.6 25.6c1.3 3.5 3.5 5.2 6.4 5.2s5.1-1.7 6.4-5.2"
        fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round"/>
  ${a && p === "posada" ? PROPS.pinguino(k) : ""}
  ${aleta(15, -1, "p-aleta-i")}${aleta(33, 1, "p-aleta-d")}
  <g class="p-cabeza" transform="translate(12.8 1.1) scale(.93)">${CARITAS.pinguino(c, k, p, a)}</g>`;
};

/* ---------- API ---------- */
const clases = (nombre, opc) => `masc masc-${nombre}${opc.anima ? " anima" : ""}${opc.clase ? " " + opc.clase : ""}`;

function carita(nombre, color = "currentColor", tamano = 24, opc = {}){
  const dibujo = CARITAS[nombre] || CARITAS.loica;
  return `<svg class="${clases(nombre, opc)}" viewBox="0 0 24 24" width="${tamano}" height="${tamano}"
            aria-hidden="true" focusable="false" data-pose="${opc.pose || "posada"}">
            ${dibujo(color, opc.tinta || TINTA_VAR, opc.pose || "posada", opc.acc !== false)}</svg>`;
}

function cuerpo(nombre, color = "currentColor", tamano = 48, opc = {}){
  const clave = CARITAS[nombre] ? nombre : "loica";
  const k = opc.tinta || TINTA_VAR, p = opc.pose || "posada", a = opc.acc !== false;
  const dibujo = clave === "pinguino" ? cuerpoPinguino(color, k, p, a)
               : AVES.has(clave)      ? cuerpoAve(clave, color, k, p, a)
                                      : cuerpoCuadrupedo(clave, color, k, p, a);
  return `<svg class="${clases(clave, opc)}" viewBox="0 0 48 48" width="${tamano}" height="${tamano}"
            aria-hidden="true" focusable="false" data-pose="${p}">${dibujo}</svg>`;
}

function mascota(nombre, color, tamano = 24, opc = {}){
  return tamano < 38 ? carita(nombre, color, tamano, opc) : cuerpo(nombre, color, tamano, opc);
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
  cine:      {mascota:"cabra",      color:"var(--c-cine)",   tintaVar:"var(--c-cine-tinta)",    hex:"#A51D99", tinta:"#7E1574", es:"Cine",      en:"Film",     pt:"Cinema"},
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

/* ---------- SUBCATEGORÍAS ----------
   El animal responde "¿qué tipo de cosa es?". Adentro de Fiestas eso no basta:
   202 fiestas en un chip son 202 fiestas, y a nadie le da lo mismo un techno
   de las tres de la mañana que una noche ochentera. Lo mismo pasa con Clases
   —cocina no es cerámica— y con Teatro, donde una obra de sala y un stand-up
   en un bar se ven iguales hasta que llegas.

   El valor lo pone el pipeline en `subcategoria` (loica/clasificar.py) y puede
   venir vacío: de muchos eventos el título no dice el género y adivinarlo sería
   peor que callarse. Los que vienen vacíos NO se esconden — aparecen cuando no
   hay subfiltro puesto.

   Acá viven SOLO los nombres para mostrar. Qué subfiltros se dibujan lo decide
   la página mirando los eventos que tiene cargados, así que si el clasificador
   inventa una subcategoría nueva mañana, la interfaz la muestra igual con el
   nombre crudo en vez de quedar en blanco. */
const SUBCATEGORIAS = {
  // Fiestas — el género que suena
  reggaeton:  {es:"Reggaetón",   en:"Reggaeton",    pt:"Reggaeton"},
  electronica:{es:"Electrónica", en:"Electronic",   pt:"Eletrônica"},
  cumbia:     {es:"Cumbia",      en:"Cumbia",       pt:"Cumbia"},
  latina:     {es:"Latina",      en:"Latin",        pt:"Latina"},
  brasilera:  {es:"Brasilera",   en:"Brazilian",    pt:"Brasileira"},
  ochentera:  {es:"Ochentera",   en:"80s & 90s",    pt:"Anos 80"},
  urbano:     {es:"Urbano",      en:"Hip hop",      pt:"Urbano"},
  pop:        {es:"Pop",         en:"Pop",          pt:"Pop"},
  rock:       {es:"Rock",        en:"Rock",         pt:"Rock"},
  metal:      {es:"Metal",       en:"Metal",        pt:"Metal"},
  // Música
  clasica:    {es:"Clásica",     en:"Classical",    pt:"Clássica"},
  jazz:       {es:"Jazz",        en:"Jazz",         pt:"Jazz"},
  folclor:    {es:"Folclor",     en:"Folk",         pt:"Folclore"},
  tributo:    {es:"Tributo",     en:"Tribute",      pt:"Tributo"},
  // Teatro
  obra:       {es:"Obra",        en:"Play",         pt:"Peça"},
  comedia:    {es:"Comedia",     en:"Comedy",       pt:"Comédia"},
  danza:      {es:"Danza",       en:"Dance",        pt:"Dança"},
  circo:      {es:"Circo",       en:"Circus",       pt:"Circo"},
  performance:{es:"Performance", en:"Performance",  pt:"Performance"},
  // Clases y talleres
  cocina:     {es:"Cocina",      en:"Cooking",      pt:"Cozinha"},
  manualidades:{es:"Manualidades",en:"Crafts",      pt:"Artesanato"},
  artes_visuales:{es:"Artes visuales",en:"Visual arts",pt:"Artes visuais"},
  bienestar:  {es:"Bienestar",   en:"Wellbeing",    pt:"Bem-estar"},
  escritura:  {es:"Escritura",   en:"Writing",      pt:"Escrita"},
  tecnologia: {es:"Tecnología",  en:"Technology",   pt:"Tecnologia"},
  idiomas:    {es:"Idiomas",     en:"Languages",    pt:"Idiomas"},
  oficios:    {es:"Oficios",     en:"Trades",       pt:"Ofícios"},
  musica:     {es:"Música",      en:"Music",        pt:"Música"},
  // Deporte
  futbol:     {es:"Fútbol",      en:"Football",     pt:"Futebol"},
  natacion:   {es:"Natación",    en:"Swimming",     pt:"Natação"},
  running:    {es:"Running",     en:"Running",      pt:"Corrida"},
  ciclismo:   {es:"Ciclismo",    en:"Cycling",      pt:"Ciclismo"},
  artes_marciales:{es:"Artes marciales",en:"Martial arts",pt:"Artes marciais"},
  gimnasia:   {es:"Gimnasia",    en:"Gym & fitness",pt:"Ginástica"},
  baile_fitness:{es:"Baile fitness",en:"Dance fitness",pt:"Dança fitness"},
  raqueta:    {es:"Raqueta",     en:"Racket sports",pt:"Raquete"},
  equipo:     {es:"Por equipos", en:"Team sports",  pt:"Por equipes"},
};

/* Si el clasificador devuelve una subcategoría que todavía no tiene nombre
   escrito acá, se muestra la clave con la primera en mayúscula y los guiones
   bajos como espacios. Feo, pero legible — y no deja un chip en blanco. */
const subcat = (clave, idioma = IDIOMA) => SUBCATEGORIAS[clave]?.[idioma]
  || String(clave || "").replace(/_/g, " ").replace(/^./, c => c.toUpperCase());

/* El elenco, en el orden en que se presenta. Lo usan la portada y Nosotros:
   antes cada página repetía la lista a mano y ya iban desincronizadas. */
const ELENCO = [
  {clave:"loica",      hex:"#E8442E", tinta:"#AA2C1B", es:["Loica","La anfitriona","Te recibe, te guía y te avisa cuando hay algo bueno cerca.",
                                                       "Nació con la pechera roja puesta. En su primer día en el Persa Biobío alguien la confundió con la encargada y le preguntó dónde quedaba el baño. Contestó bien. Desde entonces no ha parado de responder preguntas que nadie le hizo formalmente."],
                                                       en:["Loica","The host","She greets you, guides you and tells you what's on nearby.",
                                                       "She was born wearing the red waistcoat. On her first day at the flea market someone mistook her for staff and asked where the toilets were. She got it right. She has been answering questions nobody officially asked her ever since."],
                                                       pt:["Loica","A anfitriã","Ela recebe você, guia e avisa quando tem algo bom por perto.",
                                                       "Nasceu com o peitilho vermelho. No primeiro dia na feira alguém a confundiu com a encarregada e perguntou onde ficava o banheiro. Ela acertou. Desde então não parou de responder perguntas que ninguém fez oficialmente."]},
  {clave:"condor",     hex:"#DE3A1E", tinta:"#A82B12", es:["Cóndor","Música","Lo que se escucha fuerte: conciertos, tocatas, festivales.",
                                                       "Vive a cinco mil metros y desde allá arriba escuchaba las pruebas de sonido de todo el valle. Bajó una vez a reclamar por el volumen, se quedó hasta el bis y ahora baja siempre. Sigue diciendo que viene a reclamar."],
                                                       en:["Condor","Music","The loud stuff: gigs, concerts, festivals.",
                                                       "He lives at five thousand metres and from up there he could hear every soundcheck in the valley. He came down once to complain about the volume, stayed for the encore, and now he comes down every time. He still says he is coming down to complain."],
                                                       pt:["Condor","Música","O que se ouve alto: shows, tocatas, festivais.",
                                                       "Mora a cinco mil metros e lá de cima ouvia a passagem de som do vale inteiro. Desceu uma vez para reclamar do volume, ficou até o bis e agora desce sempre. Continua dizendo que vem reclamar."]},
  {clave:"culpeo",     hex:"#7A3FE0", tinta:"#5B2BAF", es:["Culpeo","Fiestas","Sale de noche. Todo lo que parte cuando el resto se acuesta.",
                                                       "Es nocturno de nacimiento, así que llevaba siglos despierto a las tres de la mañana sin nada que hacer. Cuando Santiago por fin inventó el after, sintió que la ciudad se había puesto a su horario. No se lo agradece a nadie."],
                                                       en:["Culpeo fox","Parties","A night creature. Everything that starts when the city sleeps.",
                                                       "He is nocturnal by birth, so he spent centuries wide awake at three in the morning with nothing to do. When Santiago finally invented the after-party he felt the city had finally adopted his schedule. He thanks no one for it."],
                                                       pt:["Culpeo","Festas","Sai à noite. Tudo o que começa quando o resto vai dormir.",
                                                       "É noturno de nascença, então passou séculos acordado às três da manhã sem nada para fazer. Quando Santiago enfim inventou o after, sentiu que a cidade tinha se ajustado ao horário dele. Não agradece a ninguém."]},
  {clave:"chinchilla", hex:"#1B6FD1", tinta:"#1A5599", es:["Chinchilla","Cultura","Teatro, cine, arte y charlas. Escucha más de lo que habla.",
                                                       "Con esas orejas escuchaba al apuntador desde la última fila. Entró a un teatro solo para confirmar que el actor se estaba equivocando, tenía razón, y no se ha ido más. Aplaude fuerte y tarde, como corresponde."],
                                                       en:["Chinchilla","Culture","Theatre, film, art and talks. Listens more than she speaks.",
                                                       "With those ears she could hear the prompter from the back row. She walked into a theatre just to confirm the actor was getting it wrong, she was right, and she never left. She claps loudly and slightly late, as one should."],
                                                       pt:["Chinchila","Cultura","Teatro, cinema, arte e palestras. Escuta mais do que fala.",
                                                       "Com aquelas orelhas ouvia o ponto desde a última fila. Entrou num teatro só para confirmar que o ator estava errando, tinha razão, e nunca mais saiu. Aplaude forte e atrasada, como manda o figurino."]},
  {clave:"cabra",      hex:"#A51D99", tinta:"#7E1574", es:["Cabra","Cine","Las cabritas son suyas. Sabe qué dan hoy, en qué sala y a qué hora.",
                                                       "En Chile a las palomitas les dicen cabritas, y ella se lo tomó personal. Entró a una función a reclamar por el nombre, se sentó en la última fila y no salió más. Ahora llega veinte minutos antes, se sienta al medio y se queda hasta que terminan los créditos, por si acaso."],
                                                       en:["Goat","Cinema","The popcorn is hers. She knows what's on today, in which screen and at what time.",
                                                       "In Chile popcorn is called cabritas — little goats — and she took it personally. She walked into a screening to complain about the name, sat in the back row and never left. Now she turns up twenty minutes early, takes the middle seat and stays through the credits, just in case."],
                                                       pt:["Cabra","Cinema","A pipoca é dela. Sabe o que está passando hoje, em qual sala e a que horas.",
                                                       "No Chile a pipoca se chama cabritas — cabrinhas — e ela levou para o lado pessoal. Entrou numa sessão para reclamar do nome, sentou na última fila e nunca mais saiu. Agora chega vinte minutos antes, senta no meio e fica até o fim dos créditos, vai que aparece algo."]},
  {clave:"chincol",    hex:"#F08800", tinta:"#8A5000", es:["Chincol","Barrio","Clases, talleres y ferias. El pájaro más de barrio que hay.",
                                                       "Nunca se ha ido del barrio. Ni de vacaciones. Conoce a la señora de la esquina, sabe qué día pasa la feria y una vez tomó un taller de mimbre solo porque era en la sede de la junta de vecinos y había once para todos."],
                                                       en:["Chincol","Neighbourhood","Classes, workshops and markets. The most local bird there is.",
                                                       "He has never left the neighbourhood. Not even on holiday. He knows the lady on the corner, he knows which day the street market comes, and he once took a basket-weaving workshop purely because it was at the community centre and there was free tea for everyone."],
                                                       pt:["Chincol","Bairro","Aulas, oficinas e feiras. O pássaro mais de bairro que existe.",
                                                       "Nunca saiu do bairro. Nem de férias. Conhece a senhora da esquina, sabe que dia passa a feira e uma vez fez uma oficina de cestaria só porque era na associação de moradores e tinha lanche para todo mundo."]},
  {clave:"pudu",       hex:"#0E8757", tinta:"#0A6141", es:["Pudú","Aire libre","El ciervo más chico del mundo. Cerros, parques y todo lo que pasa sin techo.",
                                                       "Mide cuarenta centímetros y vive metido entre los arbustos, así que conoce el cerro por abajo: dónde hay sombra, en qué parte el sendero se pone feo y a qué hora se llena. Bajó al parque un domingo por curiosidad y no se fue más. Dice que adentro de una sala no se ve nada."],
                                                       en:["Pudú","Outdoors","The world's smallest deer. Hills, parks and everything that happens without a roof.",
                                                       "He is forty centimetres tall and lives deep in the undergrowth, so he knows the hill from below: where the shade is, where the path turns bad, and what time it fills up. He came down to the park one Sunday out of curiosity and never left. He says you cannot see anything from inside a room."],
                                                       pt:["Pudu","Ar livre","O menor cervo do mundo. Morros, parques e tudo o que acontece sem teto.",
                                                       "Tem quarenta centímetros e vive enfiado no mato, então conhece o morro por baixo: onde tem sombra, em que parte a trilha piora e a que horas enche. Desceu ao parque num domingo por curiosidade e não foi mais embora. Diz que dentro de uma sala não se vê nada."]},
  {clave:"degu",       hex:"#2E7D5B", tinta:"#1C523B", es:["Degú","Gratis","Vive en el cerro sin pagar arriendo. Se hace cargo de lo que no cuesta nada.",
                                                       "Los degús salen a la superficie a la misma hora todos los días y no le piden permiso a nadie. Este cachó temprano que en Santiago pasan cosas buenas que no cuestan un peso, y que casi nunca están anunciadas donde uno mira. Así que las anota. La lista es lo único que junta."],
                                                       en:["Degu","Free","He lives on the hill and pays no rent. He looks after everything that costs nothing.",
                                                       "Degus come up to the surface at the same hour every day and ask nobody's permission. This one worked out early that good things happen in Santiago for nothing, and that they are almost never announced anywhere people look. So he writes them down. The list is the only thing he hoards."],
                                                       pt:["Degu","Grátis","Mora no morro e não paga aluguel. Cuida de tudo o que não custa nada.",
                                                       "Degus saem à superfície na mesma hora todo dia e não pedem licença a ninguém. Este percebeu cedo que em Santiago acontecem coisas boas que não custam nada, e que quase nunca estão anunciadas onde alguém procura. Então anota. A lista é a única coisa que ele junta."]},
  {clave:"guaren",     hex:"#95521C", tinta:"#6B3813", es:["Guarén","Descuentos","Le dicen rata y lo anotó en el currículum. Sabe qué día conviene salir a comer.",
                                                       "En Chile a alguien le dicen rata cuando cuida la plata más de lo que al resto le parece elegante. Él se lo tomó como cargo. Junta folletos de banco, los ordena por día de la semana y así descubrió que los martes come por la mitad. No ha vuelto a pagar precio de lista y lo cuenta en toda comida."],
                                                       en:["Guarén rat","Discounts","They call him a rat and he put it on his CV. He knows which day is the cheap one to eat out.",
                                                       "In Chile you get called a rat when you look after your money more closely than everyone else finds elegant. He took it as a job title. He hoards bank leaflets, sorts them by day of the week, and that is how he found out Tuesdays are half price. He has not paid full price since, and he brings it up at every meal."],
                                                       pt:["Guarén","Descontos","Chamam ele de rato e ele pôs no currículo. Sabe qual dia compensa sair para comer.",
                                                       "No Chile chamam alguém de rato quando cuida do dinheiro mais do que o resto acha elegante. Ele levou como cargo. Junta folhetos de banco, organiza por dia da semana e foi assim que descobriu que na terça come pela metade. Nunca mais pagou o preço cheio e conta isso em toda refeição."]},
  {clave:"chungungo",  hex:"#0C8B9B", tinta:"#065C66", es:["Chungungo","Deporte","La nutria del Mapocho. Se mueve, se moja y no para nunca.",
                                                       "Entrena en el Mapocho, que no es piscina olímpica pero forma carácter. Empezó nadando para arrancar de un perro y terminó cronometrándose. Ahora corre, nada y pedalea convencido de que tú también deberías. No insiste: solo te mira."],
                                                       en:["Chungungo","Sport","The Mapocho river otter. Always moving, always wet, never still.",
                                                       "He trains in the Mapocho, which is no Olympic pool but it builds character. He started swimming to escape a dog and ended up timing himself. Now he runs, swims and cycles, convinced you should too. He does not push. He just looks at you."],
                                                       pt:["Chungungo","Esporte","A lontra do Mapocho. Se mexe, se molha e não para nunca.",
                                                       "Treina no Mapocho, que não é piscina olímpica mas forma caráter. Começou nadando para fugir de um cachorro e terminou se cronometrando. Agora corre, nada e pedala convencido de que você também deveria. Não insiste: só te olha."]},
  {clave:"pinguino",   hex:"#C42B67", tinta:"#8F1C4A", es:["Pingüino","Charlas","De Humboldt y de punta en blanco. Charlas, seminarios y gente que sabe.",
                                                       "Nació de terno y en Chile eso te abre puertas. Entró a un seminario solo por el café de la mitad, nadie le pidió credencial y terminó sentado en la mesa. No habló, pero asintió en los momentos correctos. Ahora lo invitan."],
                                                       en:["Penguin","Talks","A Humboldt in black tie. Talks, seminars and people who know.",
                                                       "He was born in black tie, and that opens doors. He walked into a seminar purely for the coffee break, nobody asked him for a badge, and he ended up on the panel. He said nothing, but nodded at the right moments. Now they invite him."],
                                                       pt:["Pinguim","Palestras","Um Humboldt de gala. Palestras, seminários e gente que sabe.",
                                                       "Nasceu de terno e isso abre portas. Entrou num seminário só pelo café do intervalo, ninguém pediu credencial e terminou sentado na mesa. Não falou, mas concordou com a cabeça nos momentos certos. Agora o convidam."]},
  {clave:"quiltro",    hex:"#5C7A1E", tinta:"#47600F", es:["Quiltro","Comer","Guatón y de nadie. Ya estaba afuera del local antes que tú.",
                                                       "No estudió. Se paró veinte años en la puerta de los locales y aprendió por el olor: sabe cuál cocina con mantequilla de verdad, cuál recalienta y cuál saca la basura a las once con cosas que todavía sirven. La guata es su currículum."],
                                                       en:["Quiltro","Eating out","A potbellied street mutt. It was outside the place before you got there.",
                                                       "He never studied. He spent twenty years standing outside restaurants and learned it all by smell: which kitchen uses real butter, which one reheats, and which one takes the bins out at eleven with things still worth eating. The belly is the CV."],
                                                       pt:["Vira-lata","Comer","Barrigudo e de ninguém. Já estava na porta antes de você.",
                                                       "Não estudou. Passou vinte anos parado na porta dos restaurantes e aprendeu pelo cheiro: sabe qual cozinha com manteiga de verdade, qual requenta e qual põe o lixo na rua às onze com coisa que ainda serve. A barriga é o currículo."]},
];

/* ---------- TRADUCCIONES ---------- */
const TEXTOS = {
  es:{
    lema:"Santiago está pasando",
    mapa:"Mapa", habla:"Habla", blog:"Blog", cine:"Cine", comer:"Dónde comer", ninos:"Niños", mas18:"+18", calendario:"Calendario", agregar:"Agrega tu evento", nosotros:"Quién hace esto",
    eventos:"eventos", evento:"evento", gratis:"Gratis",
    hoy:"Hoy", manana:"Mañana", semana:"7 días", finde:"Finde",
    cuandoLargo:{hoy:"Hoy", manana:"Mañana", semana:"En estos 7 días", finde:"Este fin de semana", todo:"Todos"},
    filtrosCuando:"Cuándo", filtrosRapidos:"Precio y público", filtrosTipo:"Tipo de panorama",
    buscar:"Busca un local, una fiesta, una banda…", buscarEtiqueta:"Buscar por palabra",
    buscarBorrar:"Borrar la búsqueda", buscarSin:"Nada con esa palabra",
    buscarSinPista:"Prueba con el nombre del local o de la comuna",
    filtrosAfinar:"Afinar", afinarTodo:"Todo", filtrosLimpiar:"Limpiar filtros",
    cuando:"Cuándo", donde:"Dónde", precio:"Precio", sinPrecio:"Precio en la fuente", ir:"Ver en la fuente original",
    vacio:"No hay eventos con esos filtros", vaciopista:"Prueba sacando algún filtro",
    aprox:"Ubicación aproximada: centro de la comuna", sinUbicar:"Dirección por confirmar — revísala en la fuente", fuente:"Información publicada por",
    libre:"Entrada liberada", verMapa:"Ver en el mapa", cerrar:"Cerrar",
    verLista:"Ver la lista", ajustarLista:"Arrastra para ver más o menos de la lista",
    anteriorEv:"Anterior", siguienteEv:"Siguiente", deN:"de",
    verMas:"Ver más panoramas", cargando:"Cargando…",
    meses:["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"],
    dias:["lun","mar","mié","jue","vie","sáb","dom"], mesesCortos:["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"],
    hoyBoton:"Hoy", anterior:"Mes anterior", siguiente:"Mes siguiente",
    /* Portada */
    pTitulo:"¿Qué hacemos hoy", pTituloAcento:"por Santiago?",
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
    pHistoriaT:"Cómo llegó a esto", pHistoriaPista:"Toca a cualquiera y te cuenta su historia",
    pHistoriaCerrar:"Cerrar", pHistoriaVer:"Ver sus panoramas",
    pGratisT:"gratis", pGratisD:"panoramas que no cuestan nada",
    pSelloHoy:"Panoramas revisados hoy a las {h}",
    pSelloAyer:"Panoramas revisados ayer a las {h}",
    pSelloViejo:"Panoramas revisados el {f}", pSelloSin:"Sin fecha de revisión",
    pTotalD:"panoramas vigentes", pFuentesD:"fuentes revisadas cada mañana",
    pCierreT:"¿Organizas algo?", pCierreD:"Si tu evento es abierto y pasa en Santiago, cabe acá. No cobramos por aparecer.",
    pCineT:"Cine", pCineD:"Qué dan hoy y qué sala te queda cerca, del mall al cine arte.",
    pTallerT:"Talleres y clases", pTallerD:"Lo que se toma todas las semanas: natación, yoga, cerámica.",
    pDctoT:"Los descuentos", pDctoD:"Dónde comer más barato hoy, según tu tarjeta.",
    pDctoCifra:"descuentos de banco vigentes",
    pComerT:"Dónde comer", pComerD:"Los locales de siempre, elegidos a dedo y con lo que hay que pedir.",
    /* Talleres */
    talleres:"Talleres",
    tTitulo:"Talleres y clases",
    tBajada:"Lo que se toma todas las semanas: natación, yoga, cerámica, idiomas. Casi todo municipal y de barrio.",
    tCuantos:"talleres", tCuantos1:"taller",
    tTipo:"Tipo", tDia:"Día", tComuna:"Comuna", tTodos:"Todos", tHoyEs:"Hoy es",
    tVacio:"No hay talleres con esos filtros", tVaciopista:"Prueba sacando alguno",
    tOjo:"Los cupos y las inscripciones los maneja cada organizador. Confirma en la fuente antes de ir.",
    tVerFicha:"Ver ficha",
    /* Descuentos */
    descuentos:"Descuentos",
    dTitulo:"¿Dónde como hoy?",
    dBajada:"Descuentos de restaurantes con tarjetas de banco. Los revisa un robot todas las mañanas en la página de cada banco y te deja en ella.",
    dCuantos:"descuentos", dCuantos1:"descuento",
    dBanco:"Banco", dComuna:"Comuna", dDia:"Día", dTodos:"Todos", dLimpiar:"Limpiar",
    dTodosDias:"Todos los días", dHoyEs:"Hoy es",
    dSinFecha:"Sin fecha declarada por el banco", dHasta:"Hasta el",
    dTope:"Tope", dSegmentado:"No es para todos los clientes del banco",
    dLocales:"locales", dOtraComuna:"y otra comuna", dOtrasComunas:"y {n} comunas más",
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
    mapa:"Map", habla:"Talk", blog:"Blog", cine:"Cinema", comer:"Where to eat", ninos:"Kids", mas18:"18+", calendario:"Calendar", agregar:"Add your event", nosotros:"Who makes this",
    eventos:"events", evento:"event", gratis:"Free",
    hoy:"Today", manana:"Tomorrow", semana:"7 days", finde:"Weekend",
    cuandoLargo:{hoy:"Today", manana:"Tomorrow", semana:"Within 7 days", finde:"This weekend", todo:"All"},
    filtrosCuando:"When", filtrosRapidos:"Price and audience", filtrosTipo:"Type of event",
    buscar:"Search a venue, a party, a band…", buscarEtiqueta:"Search by keyword",
    buscarBorrar:"Clear the search", buscarSin:"Nothing matches that word",
    buscarSinPista:"Try the name of the venue or the district",
    filtrosAfinar:"Narrow down", afinarTodo:"All", filtrosLimpiar:"Clear filters",
    cuando:"When", donde:"Where", precio:"Price", sinPrecio:"Price at source", ir:"View original source",
    vacio:"No events match these filters", vaciopista:"Try removing a filter",
    aprox:"Approximate location: district centre", sinUbicar:"Address to be confirmed — check the source", fuente:"Information published by",
    libre:"Free entry", verMapa:"See on the map", cerrar:"Close",
    verLista:"Show the list", ajustarLista:"Drag to show more or less of the list",
    anteriorEv:"Previous", siguienteEv:"Next", deN:"of",
    verMas:"See more events", cargando:"Loading…",
    meses:["January","February","March","April","May","June","July","August","September","October","November","December"],
    dias:["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], mesesCortos:["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"],
    hoyBoton:"Today", anterior:"Previous month", siguiente:"Next month",
    /* Portada */
    pTitulo:"What's on today", pTituloAcento:"around Santiago?",
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
    pHistoriaT:"How it came to this", pHistoriaPista:"Tap any of them and you get the backstory",
    pHistoriaCerrar:"Close", pHistoriaVer:"See what they cover",
    pGratisT:"free", pGratisD:"events that cost nothing",
    pSelloHoy:"Listings checked today at {h}",
    pSelloAyer:"Listings checked yesterday at {h}",
    pSelloViejo:"Listings checked on {f}", pSelloSin:"No check date",
    pTotalD:"events on right now", pFuentesD:"sources checked every morning",
    pCierreT:"Running something?", pCierreD:"If your event is open to the public and happens in Santiago, it belongs here. We don't charge for it.",
    pCineT:"Cinema", pCineD:"What is on today and which screen is near you, from the mall to the arthouse.",
    pTallerT:"Workshops & classes", pTallerD:"The weekly stuff: swimming, yoga, pottery.",
    pDctoT:"The discounts", pDctoD:"Where to eat cheaper today, depending on your card.",
    pDctoCifra:"live bank discounts",
    pComerT:"Where to eat", pComerD:"The regulars, hand-picked, and what to order at each one.",
    /* Talleres */
    talleres:"Classes",
    tTitulo:"Workshops & classes",
    tBajada:"The weekly stuff: swimming, yoga, pottery, languages. Mostly municipal and neighbourhood-run.",
    tCuantos:"classes", tCuantos1:"class",
    tTipo:"Type", tDia:"Day", tComuna:"District", tTodos:"All", tHoyEs:"Today is",
    tVacio:"No classes match these filters", tVaciopista:"Try removing one",
    tOjo:"Spots and sign-ups are handled by each organiser. Check the source before you go.",
    tVerFicha:"View details",
    /* Descuentos */
    descuentos:"Discounts",
    dTitulo:"Where do I eat today?",
    dBajada:"Restaurant discounts with Chilean bank cards. A robot checks each bank's own page every morning and always sends you back to it.",
    dCuantos:"discounts", dCuantos1:"discount",
    dBanco:"Bank", dComuna:"District", dDia:"Day", dTodos:"All", dLimpiar:"Clear",
    dTodosDias:"Every day", dHoyEs:"Today is",
    dSinFecha:"No end date published by the bank", dHasta:"Until",
    dTope:"Cap", dSegmentado:"Not available to every customer of the bank",
    dLocales:"venues", dOtraComuna:"and one more district", dOtrasComunas:"and {n} more districts",
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
    mapa:"Mapa", habla:"Fale", blog:"Blog", cine:"Cinema", comer:"Onde comer", ninos:"Crianças", mas18:"+18", calendario:"Calendário", agregar:"Adicione seu evento", nosotros:"Quem faz isso",
    eventos:"eventos", evento:"evento", gratis:"Grátis",
    hoy:"Hoje", manana:"Amanhã", semana:"7 dias", finde:"Fim de semana",
    cuandoLargo:{hoy:"Hoje", manana:"Amanhã", semana:"Nestes 7 dias", finde:"Neste fim de semana", todo:"Todos"},
    filtrosCuando:"Quando", filtrosRapidos:"Preço e público", filtrosTipo:"Tipo de programa",
    buscar:"Busque um local, uma festa, uma banda…", buscarEtiqueta:"Buscar por palavra",
    buscarBorrar:"Limpar a busca", buscarSin:"Nada com essa palavra",
    buscarSinPista:"Tente o nome do local ou da comuna",
    filtrosAfinar:"Refinar", afinarTodo:"Tudo", filtrosLimpiar:"Limpar filtros",
    cuando:"Quando", donde:"Onde", precio:"Preço", sinPrecio:"Preço na fonte", ir:"Ver na fonte original",
    vacio:"Nenhum evento com esses filtros", vaciopista:"Tente remover algum filtro",
    aprox:"Localização aproximada: centro da comuna", sinUbicar:"Endereço a confirmar — veja na fonte", fuente:"Informação publicada por",
    libre:"Entrada gratuita", verMapa:"Ver no mapa", cerrar:"Fechar",
    verLista:"Ver a lista", ajustarLista:"Arraste para ver mais ou menos da lista",
    anteriorEv:"Anterior", siguienteEv:"Próximo", deN:"de",
    verMas:"Ver mais programas", cargando:"Carregando…",
    meses:["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"],
    dias:["seg","ter","qua","qui","sex","sáb","dom"], mesesCortos:["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"],
    hoyBoton:"Hoje", anterior:"Mês anterior", siguiente:"Próximo mês",
    /* Portada */
    pTitulo:"O que a gente faz hoje", pTituloAcento:"por Santiago?",
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
    pHistoriaT:"Como chegou nisso", pHistoriaPista:"Toque em qualquer um e ele conta a história",
    pHistoriaCerrar:"Fechar", pHistoriaVer:"Ver os programas dele",
    pGratisT:"grátis", pGratisD:"programas que não custam nada",
    pSelloHoy:"Programas revisados hoje às {h}",
    pSelloAyer:"Programas revisados ontem às {h}",
    pSelloViejo:"Programas revisados em {f}", pSelloSin:"Sem data de revisão",
    pTotalD:"programas em cartaz", pFuentesD:"fontes revisadas toda manhã",
    pCierreT:"Organiza algo?", pCierreD:"Se o seu evento é aberto e acontece em Santiago, cabe aqui. Não cobramos para aparecer.",
    pCineT:"Cinema", pCineD:"O que está passando hoje e qual sala fica perto, do shopping ao cine arte.",
    pTallerT:"Oficinas e aulas", pTallerD:"O que se faz toda semana: natação, ioga, cerâmica.",
    pDctoT:"Os descontos", pDctoD:"Onde comer mais barato hoje, conforme o seu cartão.",
    pDctoCifra:"descontos de banco em vigor",
    pComerT:"Onde comer", pComerD:"Os lugares de sempre, escolhidos a dedo e com o que pedir.",
    /* Talleres */
    talleres:"Aulas",
    tTitulo:"Oficinas e aulas",
    tBajada:"O que se faz toda semana: natação, ioga, cerâmica, idiomas. Quase tudo municipal e de bairro.",
    tCuantos:"aulas", tCuantos1:"aula",
    tTipo:"Tipo", tDia:"Dia", tComuna:"Comuna", tTodos:"Todas", tHoyEs:"Hoje é",
    tVacio:"Nenhuma aula com esses filtros", tVaciopista:"Tente tirar algum",
    tOjo:"As vagas e inscrições são de cada organizador. Confirme na fonte antes de ir.",
    tVerFicha:"Ver ficha",
    /* Descuentos */
    descuentos:"Descontos",
    dTitulo:"Onde eu como hoje?",
    dBajada:"Descontos de restaurantes com cartões de bancos chilenos. Um robô revisa a página de cada banco toda manhã e sempre te leva de volta a ela.",
    dCuantos:"descontos", dCuantos1:"desconto",
    dBanco:"Banco", dComuna:"Comuna", dDia:"Dia", dTodos:"Todos", dLimpiar:"Limpar",
    dTodosDias:"Todos os dias", dHoyEs:"Hoje é",
    dSinFecha:"Sem data de término declarada pelo banco", dHasta:"Até",
    dTope:"Limite", dSegmentado:"Não vale para todos os clientes do banco",
    dLocales:"locais", dOtraComuna:"e mais uma comuna", dOtrasComunas:"e mais {n} comunas",
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

/* El idioma sale del aparato, no de un supuesto. El sitio es de Santiago pero
   lo abren turistas y quien llegó hace poco, y arrancar todo en español los
   obligaba a encontrar el selector antes de entender la página.

   Se mira `navigator.languages` completo y no solo `navigator.language`,
   porque un teléfono en francés con español de segunda lengua declara
   ["fr-FR","es"] y ahí el español es la mejor respuesta que tenemos.

   Lo que no está en los tres idiomas cae a INGLÉS y no a español: alguien con
   el aparato en alemán tiene más chance de leer inglés que castellano. */
const IDIOMAS = ["es", "en", "pt"];
function idiomaDelAparato(){
  const declarados = navigator.languages && navigator.languages.length
    ? navigator.languages : [navigator.language || ""];
  for(const etiqueta of declarados){
    const base = String(etiqueta).toLowerCase().split("-")[0];
    if(IDIOMAS.includes(base)) return base;
  }
  return "en";
}
let IDIOMA = localStorage.getItem("loica-idioma") || idiomaDelAparato();
document.documentElement.lang = IDIOMA;
const t = clave => TEXTOS[IDIOMA][clave];

function fijarIdioma(nuevo){
  IDIOMA = nuevo;
  localStorage.setItem("loica-idioma", nuevo);
  document.documentElement.lang = nuevo;
}

/* ---------- TEMA ----------
   El sitio arranca CLARO siempre, tenga el aparato la configuración que tenga.
   Antes seguía al `prefers-color-scheme` del sistema, y en Chile media ciudad
   tiene el teléfono en oscuro por batería: entraban a un mapa nocturno sin
   haberlo pedido y sin saber que existía un interruptor. El oscuro sigue
   siendo de primera clase —la app se usa de noche— pero ahora es una decisión,
   no una herencia.

   Por eso en el CSS ya no hay ningún `@media (prefers-color-scheme: dark)`:
   el oscuro entra solo por `[data-tema="oscuro"]`. Si vuelve a aparecer uno,
   vuelve el problema, y encima con un parpadeo oscuro antes de que corra este
   archivo. */
function temaGuardado(){ return localStorage.getItem("loica-tema"); }
function aplicarTema(tema, guardar = true){
  if(tema) document.documentElement.dataset.tema = tema;
  else delete document.documentElement.dataset.tema;
  if(guardar) localStorage.setItem("loica-tema", tema || "");
}
function alternarTema(){
  const actual = document.documentElement.dataset.tema || "claro";
  aplicarTema(actual === "oscuro" ? "claro" : "oscuro");
  return document.documentElement.dataset.tema;
}
// `false` en el arranque: se pinta claro pero NO se guarda, así que quien
// nunca tocó el interruptor sigue sin preferencia registrada.
aplicarTema(temaGuardado() || "claro", false);

/* ---------- CABECERA COMPARTIDA ---------- */
// Íconos de la navegación inferior. Simples a propósito: compiten con las
// mascotas y a 22px la mascota no se lee.
const ICONOS_NAV = {
  /* Talleres: dos flechas en círculo — la clase que vuelve cada semana. */
  talleres:`<path d="M20 12a8 8 0 1 1-2.9-6.2" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round"/>
        <path d="M17.4 2.6v3.6H21" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="12" cy="12" r="1.6" fill="currentColor"/>`,
  /* Cine: la claqueta. Se eligió sobre el rollo de película y sobre la
     butaca porque a 21px las perforaciones del rollo se cierran y la butaca
     queda igual al globo de "habla". La barra diagonal de arriba es la que
     la hace reconocible aunque el resto se empaste. */
  cine:`<rect x="2.6" y="8.4" width="18.8" height="12.4" rx="2.2" fill="none"
        stroke="currentColor" stroke-width="1.8"/>
        <path d="M2.9 8.4 6.9 3.6l3.6 4.8M9.9 8.4l4-4.8 3.6 4.8" fill="none"
        stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M17.1 8.4 21.1 3.6" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round"/>`,
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
  // Tenedor y cuchillo, sin plato: a 21px el plato es un círculo que se come
  // los cubiertos y deja el ícono igual al del "agrega". Los descuentos ya
  // hablan de comer, pero van con etiqueta de precio: acá el gesto es la mesa.
  comer:`<path d="M6 3v4.8a2.7 2.7 0 0 0 5.4 0V3M8.7 3v4.8M8.7 10.5V21"
        fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M17 3c1.8 1.9 2.7 4.3 2.7 6.7 0 1.9-.9 3.1-2.7 3.5z"
        fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M17 13.2V21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>`,
};
/* index.html es la PORTADA y no está en esta lista a propósito: se llega a
   ella por el logo. Seis destinos no caben en la barra inferior de un
   celular sin que las etiquetas se corten. */
const PAGINAS = [["mapa.html","mapa"],["habla.html","habla"],["calendario.html","calendario"],
                 ["cine.html","cine"], ["talleres.html","talleres"],
                 ["descuentos.html","descuentos"],["comer.html","comer"],["blog.html","blog"],
                 ["agrega.html","agregar"],["nosotros.html","nosotros"]];
// En la barra inferior el espacio manda: con OCHO destinos cada celda baja a
// 47 px en un teléfono de 375, así que las etiquetas son de UNA palabra corta
// y ninguna pasa de seis letras. "Calendario" ya no cabía con seis y pasó a
// "Agenda"; "Descuentos" tampoco cabe y va como "Dctos", que es como se
// escribe en cualquier vitrina de Chile; y "Publicar" —que con siete todavía
// entraba— se cortaba con ocho y pasó a "Subir".
//
// Ocho es el techo de verdad. A 375 px la celda mide 47 y el área táctil
// sigue sobre los 44; en un teléfono de 320 px baja a 40 y queda bajo la
// recomendación, que es el precio conocido de este destino. Un noveno destino
// deja de caber en cualquier teléfono y tendría que vivir en otra parte.
const CORTOS = {
  es:{mapa:"Mapa", habla:"Habla", calendario:"Agenda", cine:"Cine", talleres:"Clases", descuentos:"Dctos", comer:"Comer", blog:"Blog", agregar:"Subir", nosotros:"Quién"},
  en:{mapa:"Map", habla:"Talk", calendario:"Agenda", cine:"Cinema", talleres:"Class", descuentos:"Deals", comer:"Eat", blog:"Blog", agregar:"Post", nosotros:"Who"},
  pt:{mapa:"Mapa", habla:"Fale", calendario:"Agenda", cine:"Cinema", talleres:"Aulas", descuentos:"Dctos", comer:"Comer", blog:"Blog", agregar:"Subir", nosotros:"Quem"},
};

/* `raiz` es el prefijo hacia la raíz del sitio. Las fichas de `e/` viven un
   nivel más abajo y le pasan "../"; sin eso su navegación apuntaba a
   `e/calendario.html` y los cinco enlaces daban 404. */
function pintarBarra(paginaActual, raiz = ""){
  // El color de la página activa (nav superior e inferior) sale de este atributo
  const claveActual = (PAGINAS.find(([url]) => url === paginaActual) || [,"portada"])[1];
  document.documentElement.dataset.pagina = claveActual;
  const logo = `<a class="logo" href="${raiz}index.html" aria-label="Loica">
      ${carita("loica", "var(--acento)", 34, {acc:false})}<b>loica</b></a>`;
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

/* ---------- DATOS ----------

   SIGUE VIGENTE = todavía no ha TERMINADO. Es la misma regla que aplica el
   pipeline en SQL (`SQL_VIGENTE` en loica/almacen.py): manda la fecha de
   término cuando existe, y si no, la de inicio. Una exposición que abrió en
   julio y cierra en septiembre sigue vigente; un concierto de ayer, no.

   Está escrita DOS VECES a propósito, acá y en el SQL, y no es un descuido.
   El pipeline filtra en el momento de generar `eventos.json`, pero ese archivo
   es estático: se reescribe cuando corre la corrida de las 11:00 y no antes.
   Si el Mac quedó apagado, si una fuente hizo fallar la corrida o si alguien
   entra a las 9 de la mañana del día siguiente, el navegador está leyendo el
   catastro de ayer — y sin esta segunda barrera mostraría los panoramas de
   ayer como si todavía se pudieran ir a ver. Con ella, el sitio envejece bien
   solo: cada visita descarta lo que ya pasó aunque el archivo tenga días.

   Lo que NO se descarta es lo de hoy que ya empezó. Un recital de las 19:00
   sigue en la lista a las 22:00, y es a propósito: a esa hora la pregunta
   "¿qué hay hoy?" todavía se hace, media función sigue vendiendo entrada y
   nadie mide el día en horas. La unidad de este catastro es el día. */
const siguesVigente = (ev, hoy = new Date()) => {
  const cuando = ev.fin || ev.inicio;
  // Sin fecha no se bota: se muestra. `new Date(null)` no es una fecha
  // inválida sino el 1 de enero de 1970, así que el vacío hay que atajarlo
  // antes de parsear o el evento se cae por una fecha que nadie escribió.
  if(!cuando) return true;
  const termino = new Date(cuando);
  if(isNaN(termino)) return true;
  const corte = new Date(hoy); corte.setHours(0, 0, 0, 0);
  return termino >= corte;
};

async function cargarEventos(){
  // El `?v=N` de loica.css/js no sirve acá: este archivo lo reescribe el robot
  // todas las mañanas y nadie sube un número por eso. Sin esto, quien ya visitó
  // el sitio sigue viendo la cartelera del día que entró por primera vez.
  const r = await fetch("eventos.json", {cache: "no-cache"});
  const d = await r.json();
  /* La marca de la corrida se guarda al pasar, sin cambiar lo que esta función
     devuelve: la llaman cuatro páginas y ninguna espera un objeto. La portada
     la usa para decir cuándo se revisó el catálogo. Viene en hora de Santiago
     y sin huso escrito —el workflow fija TZ: America/Santiago— así que se
     compara como texto contra el día de Santiago, nunca con new Date(). */
  window.generadoEventos = d.generado || "";
  return d.eventos
    .filter(siguesVigente)
    .map(ev => ({...ev, fecha: new Date(ev.inicio)}));
}

async function cargarTalleres(){
  // Misma barrera que cargarEventos: lo que ya terminó no se muestra aunque
  // el archivo tenga días (ver siguesVigente).
  const r = await fetch("talleres.json", {cache: "no-cache"});
  const d = await r.json();
  return d.talleres
    .filter(siguesVigente)
    .map(ev => ({...ev, fecha: new Date(ev.inicio)}));
}

/* ---------- UTILIDADES ---------- */
const escapar = s => String(s ?? "").replace(/[&<>"']/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

/* `escapar` NO alcanza para un href.
   Casi todos los links que pinta esta app —el del evento, el del banco, el
   sitio del local— vienen de sitios de terceros que raspa el robot. Escapar
   sirve contra un `"` que se sale del atributo, pero `javascript:alert(1)` no
   lleva comillas ni signos raros: pasa intacto por `escapar` y el navegador lo
   ejecuta al primer clic, en el dominio de Loica y con la sesión de quien
   pinchó. La única defensa es mirar el ESQUEMA y aceptar solo los dos que esta
   app necesita.

   Devuelve "" cuando no le gusta lo que ve. Quien la use decide qué hacer con
   el vacío: acá casi siempre significa "no dibujes el botón". */
function urlSegura(u){
  if(!u) return "";
  // Los espacios y tabs DENTRO del esquema los ignora el navegador —
  // `java\tscript:` se ejecuta igual—, así que se limpian antes de mirar.
  const limpia = String(u).replace(/[\u0000-\u0020]/g, "").toLowerCase();
  if(limpia.startsWith("//")) return "";        // hereda el protocolo, pero es otro sitio
  const dosPuntos = limpia.indexOf(":");
  if(dosPuntos === -1) return u;                // relativa: es nuestra, pasa
  // Una barra antes de los dos puntos significa que no era un esquema sino un
  // path con dos puntos adentro ("fotos/a:b.jpg"). También es relativa.
  const barra = limpia.indexOf("/");
  if(barra !== -1 && barra < dosPuntos) return u;
  return ["http:", "https:", "mailto:", "tel:"].includes(limpia.slice(0, dosPuntos + 1)) ? u : "";
}

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

const terminaDia = f => { const d = new Date(f); d.setHours(23,59,59,999); return d; };

/* Cada rango es una VENTANA con principio y fin, no un predicado suelto.
   Antes eran predicados sobre una fecha, y con eso solo se puede contestar
   "¿este evento puntual cae adentro?". Falta la otra pregunta, que apareció
   cuando el catastro empezó a publicar temporadas: "¿esta exposición que corre
   de julio a septiembre toca la ventana en algún momento?". Un predicado sobre
   una sola fecha no la puede contestar; dos fechas contra dos fechas, sí. */
const VENTANAS = {
  hoy:    () => { const d = empiezaDia(new Date()); return [d, terminaDia(d)]; },
  manana: () => { const d = empiezaDia(new Date()); d.setDate(d.getDate() + 1);
                  return [d, terminaDia(d)]; },
  semana: () => { const d = empiezaDia(new Date()), h = new Date(d);
                  h.setDate(d.getDate() + 7); return [d, terminaDia(h)]; },
  finde:  () => ventanaFinde(),
};

const RANGOS = {
  todo:   () => true,
  hoy:    f => { const [d,h] = VENTANAS.hoy();    return f >= d && f <= h; },
  manana: f => { const [d,h] = VENTANAS.manana(); return f >= d && f <= h; },
  semana: f => { const [d,h] = VENTANAS.semana(); return f >= d && f <= h; },
  finde:  f => { const [d,h] = VENTANAS.finde();  return f >= d && f <= h; },
};
const enRango = (fecha, rango) => (RANGOS[rango] || RANGOS.todo)(fecha);

/* Un evento ocupa el calendario de tres formas distintas y el filtro de fecha
   tiene que saber cuál es cuál:

   1. PUNTUAL — un concierto el jueves. Basta con mirar `inicio`.
   2. SERIE — un taller de martes y jueves hasta noviembre, que llega como UNA
      tarjeta con `dias_semana` (0=lunes) y `fin`. No sirve mirar solo `inicio`:
      un taller de sábados tiene que seguir apareciendo en "este fin de semana"
      aunque su próxima sesión sea el martes.
   3. TEMPORADA — una exposición que abrió el 18 de julio y cierra el 27 de
      septiembre: `fin` en el futuro, `inicio` en el pasado y sin `dias_semana`,
      porque está todos los días. Mirando solo `inicio` caía en el caso 1 y
      quedaba fuera de Hoy, Mañana, 7 días y Finde — aparecía únicamente en
      "Todos". Eran 143 eventos, y son justo los que contestan que sí a la
      pregunta que se hace quien abre la app: "¿esto todavía se puede ver?".
      Antes no se notaba porque estos eventos ni siquiera salían del almacén;
      empezaron a salir cuando la vigencia pasó a medirse por fecha de término. */
function sesionEnRango(ev, rango){
  if(rango === "todo") return true;
  const ventana = VENTANAS[rango];
  if(!ventana) return true;
  const [desde, hasta] = ventana();
  const ini = new Date(ev.inicio);

  if(ev.dias_semana && ev.dias_semana.length){
    const prueba = RANGOS[rango];
    const fin = ev.fin ? new Date(ev.fin) : ini;
    /* Se recorren los días entre hoy y el final de la serie, con tope de 60:
       más allá ningún filtro de la página mira (el más largo son 7 días). */
    const d = new Date(); d.setHours(0,0,0,0);
    for(let i = 0; i < 60; i++){
      if(d > fin) break;
      if(d >= empiezaDia(ini) && ev.dias_semana.includes((d.getDay() + 6) % 7)){
        const conHora = new Date(d);
        conHora.setHours(ini.getHours(), ini.getMinutes(), 0, 0);
        if(prueba(conHora)) return true;
      }
      d.setDate(d.getDate() + 1);
    }
    return false;
  }

  // Temporada: se cruzan los dos tramos. Basta con que se toquen.
  if(ev.fin){
    const fin = new Date(ev.fin);
    if(fin > ini) return ini <= hasta && fin >= desde;
  }
  return ini >= desde && ini <= hasta;
}

/* ---------- BÚSQUEDA POR PALABRA ----------
   Los filtros por animal responden "¿qué tipo de cosa quiero hacer?". No
   responden "¿qué hay en el Blondie?" ni "¿dónde toca Los Tres?", que es como
   la gente busca de verdad cuando ya sabe lo que anda trucando: el nombre de
   un local, de una fiesta, de una banda.

   Se busca sobre el título, el lugar, la comuna y la fuente. La descripción
   NO entra: son textos largos de la fuente y meterlos hace que "teatro"
   devuelva media cartelera porque alguien escribió "teatro" en un párrafo.

   Sin tildes de los dos lados. Nadie escribe "Ñuñoa" con la eñe en el
   buscador de un celular, y "cumbia" tiene que encontrar "Cumbión". */
const sinTildes = s => String(s ?? "").normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "").toLowerCase();

/* Varias palabras = todas tienen que estar, en cualquier campo y en cualquier
   orden. "blondie rock" encuentra la tocata de rock en el Blondie; si fuera
   una sola cadena, no encontraría nada porque el título dice "ROCK EN BLONDIE"
   al revés. */
function coincideBusqueda(ev, texto){
  const q = sinTildes(texto).trim();
  if(!q) return true;
  const heno = sinTildes([ev.titulo, ev.lugar, ev.comuna, ev.fuente].join(" "));
  return q.split(/\s+/).every(palabra => heno.includes(palabra));
}

/* "todos los martes y jueves" — lo que la tarjeta muestra en vez de repetirse. */
const NOMBRE_DIA = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"];
function cadencia(ev){
  if(!ev.dias_semana || !ev.dias_semana.length) return "";
  const n = ev.dias_semana.map(i => NOMBRE_DIA[i]);
  const lista = n.length === 1 ? n[0]
    : n.slice(0,-1).join(", ") + " y " + n[n.length-1];
  return (n.length === 1 ? "todos los " : "") + lista;
}
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

/* ---------- AGENDAR EN GOOGLE CALENDAR ----------
   Compartir es para mandárselo a otro; esto es para uno mismo. Alguien que ve
   un panorama el jueves y le interesa el sábado no tiene dónde ponerlo: cierra
   la pestaña y lo olvida.

   Tres decisiones que no son obvias:

   DURACIÓN. Casi ningún evento del catastro declara hora de término, así que
   se asumen dos horas. Es una convención honesta: en el calendario se ve un
   bloque razonable y la hora de inicio —que es la que importa para llegar— es
   la real.

   LAS SERIES Y LAS TEMPORADAS NO SE VUELCAN ENTERAS. Un taller de martes y
   jueves hasta noviembre trae `fin` en noviembre, y una exposición que cierra
   en septiembre también. Usar ese `fin` como término del evento le mete a
   alguien un bloque de tres meses atravesado en el calendario. Se agenda la
   PRÓXIMA fecha con las dos horas de siempre, y la cadencia o la temporada se
   cuentan en la descripción, que es donde sirven de dato y no estorban.

   SIN HORA VA COMO EVENTO DE DÍA COMPLETO. Google acepta `YYYYMMDD/YYYYMMDD`
   y así se evita inventar una hora: un evento a las 00:00 en el calendario
   dice "es a medianoche", que es una afirmación falsa sobre el panorama. */
const _fechaGoogle = (f, soloDia) => soloDia
  ? `${f.getFullYear()}${String(f.getMonth() + 1).padStart(2,"0")}${String(f.getDate()).padStart(2,"0")}`
  : f.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");

function urlCalendario(ev){
  let ini = new Date(ev.inicio);
  if(isNaN(ini)) return "";

  /* Una temporada que YA EMPEZÓ y sigue en cartelera se agenda para hoy, no
     para su estreno. La exposición de mariposas abrió el 24 de abril de 2025 y
     cierra el 30 de agosto: agendar abril del año pasado le deja a alguien una
     entrada en un mes que ya pasó y que no va a mirar nunca. Lo que la persona
     está decidiendo es ir AHORA, así que se agenda hoy como día completo y la
     fecha de cierre se cuenta en la descripción. */
  const cierre = ev.fin ? new Date(ev.fin) : null;
  const arranco = new Date(); arranco.setHours(0,0,0,0);
  const enCurso = ini < arranco && cierre && !isNaN(cierre) && cierre >= arranco
                  && !(ev.dias_semana && ev.dias_semana.length);
  if(enCurso) ini = arranco;

  // Un evento sin hora llega como 00:00. No es "a medianoche": es "ese día".
  const soloDia = enCurso || (!ini.getHours() && !ini.getMinutes());

  let fin;
  if(soloDia){
    fin = new Date(ini);
    fin.setDate(fin.getDate() + 1);          // Google pide el día siguiente
  } else {
    const mismoDia = cierre && !isNaN(cierre)
      && cierre > ini && cierre.toDateString() === ini.toDateString()
      && !(ev.dias_semana && ev.dias_semana.length);
    fin = mismoDia ? cierre : new Date(ini.getTime() + 2 * 3600 * 1000);
  }

  const detalle = [
    ev.descripcion || "",
    cadencia(ev) ? `Se repite ${cadencia(ev)}.` : "",
    // La temporada se cuenta acá justamente porque no se vuelca al bloque.
    (!cadencia(ev) && cierre && !isNaN(cierre) && cierre.toDateString() !== ini.toDateString())
      ? `En cartelera hasta el ${cierre.toLocaleDateString(localeDe(),
          {day:"numeric", month:"long"})}.` : "",
    // textoPrecio devuelve "—" cuando la fuente no publicó precio, y una línea
    // que dice "Precio: —" no informa nada: mejor no ponerla.
    textoPrecio(ev) !== "—" ? `Precio: ${textoPrecio(ev)}` : "",
    `Ficha en Loica: ${urlDeEvento(ev)}`,
    urlSegura(ev.url) ? `Fuente: ${ev.url}` : "",
  ].filter(Boolean).join("\n");

  const p = new URLSearchParams({
    action: "TEMPLATE",
    text: ev.titulo || "",
    dates: `${_fechaGoogle(ini, soloDia)}/${_fechaGoogle(fin, soloDia)}`,
    details: detalle,
    location: [ev.lugar, ev.direccion, ev.comuna].filter(Boolean).join(", "),
  });
  return `https://calendar.google.com/calendar/render?${p}`;
}

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

  /* Agendar va al final y separado del resto: los otros cinco mandan el
     panorama a otra persona y este lo guarda para uno. Sin la línea divisoria
     se lee como "compartir en Google", que es otra cosa. */
  const enlaceAgenda = urlCalendario(ev);
  if(enlaceAgenda){
    const sep = document.createElement("span");
    sep.className = "compartir-corte";
    sep.setAttribute("aria-hidden", "true");
    fila.appendChild(sep);

    const nombreAgenda = {es:"Agendar en Google Calendar",
                          en:"Add to Google Calendar",
                          pt:"Adicionar ao Google Calendar"}[IDIOMA];
    const b = boton("agendar", nombreAgenda, "#4285F4",
      `<rect x="3" y="4.5" width="18" height="16" rx="2.6" fill="none"
             stroke="currentColor" stroke-width="1.9"/>
       <path d="M3 9.5h18M8 2.5v4M16 2.5v4" fill="none" stroke="currentColor"
             stroke-width="1.9" stroke-linecap="round"/>
       <path d="M10 15.4l1.8 1.8 3.4-3.6" fill="none" stroke="currentColor"
             stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>`,
      () => window.open(enlaceAgenda, "_blank", "noopener"));
    // El único botón de la fila que lleva texto: es una acción distinta de las
    // demás y un ícono solo la deja adivinándose.
    b.classList.add("con-texto");
    b.insertAdjacentHTML("beforeend", `<span>${escapar(
      {es:"Agendar", en:"Add to calendar", pt:"Agendar"}[IDIOMA])}</span>`);
  }

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

/* ---------- LA CORDILLERA ----------
   Era un zigzag genérico copiado a mano en tres archivos: servía de decoración
   pero podía ser la sierra de cualquier ciudad del mundo. Esta es Santiago y se
   nota, que es justo lo que pide el sistema (color pleno, contorno, nada
   genérico). De atrás hacia adelante:

     1. Los Andes, con NIEVE en las cumbres altas. La nieve es la mitad de la
        postal: sin ella el filo se lee como un cerro pelado cualquiera.
     2. La precordillera, con el Manquehue — el cono que todo el mundo ubica
        aunque no sepa el nombre.
     3. La ciudad: el San Cristóbal con su cruz, el Santa Lucía y el Costanera.
        Tres siluetas y ya sabes en qué ciudad estás.

   Va acá y no en cada página para que sea LA MISMA en todas. `tono` deja que
   habla.html la tiña con el color del guía de turno; el resto usa el default. */
function cordillera({tono = "var(--c-fiesta)"} = {}){
  // Nieve: parches irregulares colgando de las cuatro cumbres altas. Van en
  // crema FIJA, nunca var(--contorno): la nieve es blanca de día y de noche.
  const nieve = [[190,18],[450,14],[730,22],[1010,28]]
    .map(([x,y]) => `M${x} ${y} L${x-22} ${y+21} L${x-9} ${y+16} L${x+3} ${y+24}
                     L${x+14} ${y+15} L${x+24} ${y+20} Z`).join("");

  return `
  <svg class="cerros" viewBox="0 0 1200 150" preserveAspectRatio="none" aria-hidden="true">
    <!-- 1. Los Andes. Los animales caminan sobre el tercio de abajo, así que
            todo lo que tenga que leerse vive sobre la línea y≈78. -->
    <path fill="var(--c-cultura)" opacity=".3" d="M0 150 L0 78 L70 40 L120 62 L190 18
      L250 50 L310 30 L380 58 L450 14 L520 54 L590 34 L660 66 L730 22 L800 56
      L870 36 L940 70 L1010 28 L1080 60 L1140 42 L1200 68 L1200 150 Z"/>
    <path fill="#FAF3E7" opacity=".62" d="${nieve}"/>

    <!-- 2. La precordillera. El cono de 560 es el Manquehue. -->
    <path fill="${tono}" opacity=".34" style="transition:fill .4s" d="M0 150 L0 104
      L90 84 L170 98 L260 76 L340 92 L420 70 L500 88 L560 58 L620 88 L700 74
      L790 96 L880 72 L960 94 L1050 78 L1130 96 L1200 84 L1200 150 Z"/>

    <!-- 3. La ciudad. Azul cordillera fijo y opaco: lo que está adelante tiene
            que ser MÁS OSCURO que lo de atrás o deja de leerse como silueta.
            Probado con crema y quedaba como neblina, sin cerro ni torre. -->
    <!-- Los hitos van en los HUECOS entre cumbres nevadas (190, 450, 730, 1010):
         pegados a una, la torre y la nieve se fundían en un solo palo claro.
         Y nada que deba verse baja de y≈76, que es la línea del lomo de los
         animales: más abajo queda tapado. -->
    <path fill="var(--azul-cordillera)" opacity=".72" d="M0 150 L0 140 L110 140
      L110 127 L150 127 L150 140 L230 140 Q302 62 375 140 L520 140 L520 121
      L560 121 L560 140 L598 140 L600 46 L622 41 L622 140 L700 140 L700 126
      L740 126 L740 140 L830 140 Q880 74 930 140 L1010 140 L1010 123 L1055 123
      L1055 140 L1200 140 L1200 150 Z"/>
    <!-- La cruz del San Cristóbal: dos trazos que ubican la ciudad entera -->
    <!-- La cruz iba en y=62, que es la COORDENADA DE CONTROL de la Bézier del
         cerro, no su cumbre. Una cuadrática solo llega a la mitad del camino
         hacia su control: con Q302 62 entre dos extremos en y=140 el ápice
         real cae en 0,25·140 + 0,5·62 + 0,25·140 = 101. O sea que la cruz
         flotaba 39 unidades sobre el cerro, como un signo "+" suelto en el
         cielo, en las once páginas que dibujan la cordillera. Mismas
         proporciones, apoyada en la cumbre de verdad. -->
    <path stroke="var(--azul-cordillera)" stroke-width="3" opacity=".72" fill="none"
          d="M302 101 L302 87 M295 92 L309 92"/>
  </svg>`;
}

/* Cuándo es, dicho como lo diría una persona */
/* ¿Es una temporada que YA ESTÁ CORRIENDO? Abrió antes de hoy, cierra hoy o
   después, y no es una serie de sesiones sueltas.

   Importa para lo que se muestra, no para lo que se filtra. Estas entran al
   filtro "Hoy" con toda razón —la muestra de Matta se puede ver hoy— pero la
   tarjeta anunciaba la fecha en que ABRIÓ. Con "Hoy" apretado aparecían
   tarjetas que decían "24 ABR", "10 JUL", "19 AGO 2025": el filtro estaba
   bien y la tarjeta lo desmentía, que es peor que un filtro roto, porque hace
   desconfiar de todo lo demás. En Arte eran 36 de 40. */
const enCartelera = (ev, hoy = new Date()) => {
  if(!ev.fin || (ev.dias_semana && ev.dias_semana.length)) return false;
  const ini = new Date(ev.inicio), fin = new Date(ev.fin);
  if(isNaN(ini) || isNaN(fin)) return false;
  const corte = new Date(hoy); corte.setHours(0, 0, 0, 0);
  return ini < corte && fin >= corte;
};

const hastaCuando = ev => {
  const fin = new Date(ev.fin);
  if(isNaN(fin)) return "";
  const cuando = fin.toLocaleDateString(localeDe(), {day:"numeric", month:"long"});
  return IDIOMA === "en" ? `On until ${cuando}`
       : IDIOMA === "pt" ? `Em cartaz até ${cuando}`
                         : `En cartelera hasta el ${cuando}`;
};

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
/* La próxima sesión de una serie semanal, mirando desde hoy. Una clase de
   martes y jueves cuya temporada partió en marzo no se anuncia por marzo: se
   anuncia por el martes que viene. Devuelve null si la serie ya terminó. */
function proximaSesion(ev){
  if(!ev.dias_semana || !ev.dias_semana.length) return null;
  const ini = new Date(ev.inicio);
  const fin = ev.fin ? new Date(ev.fin) : ini;
  const d = new Date(); d.setHours(ini.getHours(), ini.getMinutes(), 0, 0);
  for(let i = 0; i < 8; i++){
    if(d > fin) return null;
    if(d >= ini && ev.dias_semana.includes((d.getDay() + 6) % 7)) return new Date(d);
    d.setDate(d.getDate() + 1);
  }
  return null;
}

function tarjetaEvento(ev, alPulsar){
  const info = cat(ev.categoria);
  // Una temporada en curso se anuncia por HOY y por hasta cuándo, nunca por
  // el día que abrió: esa fecha ya pasó y no le sirve a nadie. Y una serie
  // semanal se anuncia por su PRÓXIMA sesión, no por la primera de marzo.
  const corre = enCartelera(ev);
  const proxima = proximaSesion(ev);
  const dia = corre
    ? {texto: IDIOMA === "en" ? "TODAY" : IDIOMA === "pt" ? "HOJE" : "HOY", pronto: true}
    : etiquetaDia(proxima && proxima >= new Date(new Date().setHours(0,0,0,0))
                  ? proxima : ev.fecha);
  // Una temporada en curso no tiene "hora": las 03:00 de una exposición son
  // la hora en que el CMS guardó el registro, no una cita. Mostrarla afirmaba
  // "Portafolio – Moda, HOY a las 03:00", que se lee como página rota.
  const hora = (!corre && (ev.fecha.getHours() || ev.fecha.getMinutes()))
    ? horaDe(ev.fecha) : "";
  const precio = ev.gratis ? t("gratis") : (ev.precio ? "$" + ev.precio.toLocaleString("es-CL") : "");

  const boton = document.createElement("button");
  boton.className = "tarjeta" + (ev.gratis ? " tarjeta-gratis" : "");
  boton.type = "button";
  boton.innerHTML = `
    <div class="mini-caja">
      <div class="miniatura">
        ${carita(info.mascota, info.hex, 44)}
        ${urlSegura(ev.imagen) ? `<img src="${escapar(urlSegura(ev.imagen))}" alt="" loading="lazy"
                         onerror="this.remove()">` : ""}
      </div>
      <span class="dia${dia.pronto ? " pronto" : ""}">${dia.texto}</span>
    </div>
    <div class="tarjeta-cuerpo">
      ${hora ? `<div class="hora">${hora}</div>` : ""}
      <h3>${escapar(ev.titulo)}</h3>
      <div class="tarjeta-meta">
        <span>${escapar(ev.lugar)}</span>
        ${ev.comuna ? `<span>· ${escapar(ev.comuna)}</span>` : ""}
      </div>
      ${cadencia(ev) ? `<div class="tarjeta-meta cadencia">↻ ${escapar(cadencia(ev))}</div>` : ""}
      ${corre ? `<div class="tarjeta-meta cadencia">→ ${escapar(hastaCuando(ev))}</div>` : ""}
    </div>
    <div class="precio${ev.gratis ? " libre" : precio ? "" : " sin-dato"}">${precio || escapar(t("sinPrecio"))}</div>`;

  boton.onclick = () => alPulsar(ev);
  return boton;
}

/* Las filas de carga: la forma de la tarjeta, sin datos, latiendo. */
function esqueleto(n = 3){
  return Array.from({length:n}, () => `<div class="esqueleto" aria-hidden="true">
    <i class="e-mini"></i><div class="e-txt"><i></i><i></i><i></i></div><i class="e-precio"></i></div>`).join("");
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
  /* Entel y Ripley faltaban y los dos caían al café del respaldo: 67
     descuentos pintados exactamente del mismo color, indistinguibles entre sí
     en el chip y en el pin. Los tonos salen de la paleta de la casa y no de la
     marca del banco —acá el color es señalética nuestra, no publicidad
     suya— y cada uno trae su tinta oscurecida, que es la única que puede
     tocar texto: el naranjo fuerte sobre crema da 2,4:1. */
  entel:     {color:"#F08800", tinta:"var(--c-clases-tinta)"},
  ripley:    {color:"#A51D99", tinta:"var(--c-cine-tinta)"},
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
  // no-cache igual que eventos.json: sin esto, quien ya visitó la página
  // sigue viendo los descuentos de ayer aunque la corrida diaria publique.
  const r = await fetch("descuentos.json", {cache: "no-cache"});
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

/* Dónde vale el convenio, en una línea. Desde el 25-08-2026 el JSON trae una
   fila por convenio y las sucursales colgando en `locales[]`: antes venía una
   fila por sucursal y el 25% de Dunkin' del Banco de Chile aparecía veintiuna
   veces en la lista, una por local. */
function dondeDescuento(d){
  const locales = d.locales || [];
  if(!locales.length) return {calle:"", donde:""};
  if(locales.length === 1) return {calle: locales[0].direccion || "", donde: locales[0].comuna || ""};
  /* El 40% de Burger King de Cencosud corre en diecisiete comunas: nombrarlas
     todas no cabe en la tarjeta. Se dicen las dos primeras y el resto se
     cuenta, que es lo que necesita saber quien está eligiendo dónde comer. */
  const comunas = d.comunas || [];
  const resto = comunas.length - 2;
  return {
    calle: `${locales.length} ${t("dLocales")}`,
    donde: resto <= 0 ? comunas.join(", ")
      : `${comunas.slice(0, 2).join(", ")} ${
          resto === 1 ? t("dOtraComuna") : t("dOtrasComunas").replace("{n}", resto)}`,
  };
}

function tarjetaDescuento(d, alPulsar){
  const b = banco(d.banco_id);
  const donde = dondeDescuento(d);
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
    <div class="mini-caja">
      <div class="miniatura">${carita("guaren", b.color, 44)}</div>
      <span class="dia${dia.hoy ? " pronto" : ""}">${escapar(dia.texto)}</span>
    </div>
    <div class="tarjeta-cuerpo">
      <div class="hora banco-nombre">${escapar(d.banco)}</div>
      <h3>${escapar(d.comercio)}</h3>
      <div class="tarjeta-meta">
        ${donde.calle ? `<span>${escapar(donde.calle)}</span>` : ""}
        ${donde.donde ? `<span>${donde.calle ? "· " : ""}${escapar(donde.donde)}</span>`
                      : d.region ? `<span>${donde.calle ? "· " : ""}${escapar(d.region)}</span>` : ""}
        ${d.segmentado ? `<span class="aviso" title="${escapar(t("dSegmentado"))}">·&nbsp;${
          IDIOMA === "en" ? "segmented" : "segmentado"}</span>` : ""}
      </div>
    </div>
    <div class="precio${monto ? " dcto" : " sin-dato"}">${escapar(monto) || "—"}</div>`;

  boton.onclick = () => alPulsar(d);
  return boton;
}

/* ---------- LA HOJA INFERIOR: la lista que sube, baja y se va ----------

   Cuatro páginas (mapa, cine, descuentos, talleres) tenían el MISMO arrastre
   copiado y pegado, y por lo tanto el mismo defecto. Medido con toques reales
   —CDP Input.dispatchTouchEvent sobre un iPhone 13, no con un mouse fingido—
   en mapa.html: arrastrar desde el contador movía el panel de 173 px a 173, o
   sea nada; desde la lista, igual; solo enganchaba desde el tirador, que mide
   29 px de alto. Un dedo mide 44 y cae en el contador o en la lista. Eso es lo
   que el dueño reportaba como "no deja subir ni bajar la pestaña": el gesto
   existía, pero en una franja que el pulgar no encuentra.

   Lo que arregla esta función:

   1. TRES ZONAS DE AGARRE en vez de una. El tirador (ahora con 44 px de blanco
      táctil), la cabecera del contador entera —que es donde de verdad cae el
      pulgar— y la lista, pero solo cuando ya está arriba del todo y el dedo va
      hacia abajo. Ese último es el patrón de Google Maps y de Apple Maps: la
      hoja se lleva el gesto únicamente cuando la lista no tiene a dónde
      seguir. En cualquier otro caso la lista scrollea y la hoja no se mete.

      Ojo con la trampa que ya nos costó una vez: `touch-action:none` en el
      PANEL entero cancelaba el scroll de la lista (37.000 px de eventos en una
      caja que no se movía). Por eso el `touch-action` restrictivo va SOLO en
      las zonas de agarre, con la clase `.hoja-agarre` que esta función pone y
      saca, y la lista se queda en `pan-y`.

   2. UN CUARTO TOPE: oculta. El dueño lo pidió con todas sus letras — poder
      esconder la lista para ver el mapa completo, y traerla de vuelta con un
      toque. Vuelve con un botón flotante que además dice cuántos resultados la
      están esperando, así esconderla no se siente como perderlos.

   3. GESTO DE VERDAD. Soltar rápido salta al siguiente tope en esa dirección
      (fling); soltar lento cae en el más cercano; y un arrastre corto pero
      decidido (>24 px) siempre cambia de tope, porque volver al mismo se lee
      como que el gesto no se registró. El `click` sintético que el navegador
      dispara detrás de cada toque se suprime si el dedo se movió: antes la
      guarda era `if(!arrastrando)`, y como `soltar()` apagaba esa bandera
      ANTES de que llegara el click, no protegía nada y cada arrastre
      adelantaba un tope de más.

   4. NO SE ROMPE SI SE PIERDE LA CAPTURA. `setPointerCapture` se pide, pero no
      se confía en él: los `pointermove`/`pointerup` se escuchan en `window`,
      porque en Safari la captura se suelta sola a mitad de gesto y la hoja
      quedaba colgada entre dos topes. `pointercancel` cae siempre en un tope
      válido. Si el navegador no tiene Pointer Events, hay respaldo en Touch.

   Lo que NO hace, y es a propósito: en escritorio y en teléfono acostado la
   lista es una COLUMNA al costado, no una hoja. Ahí esta función queda inerte
   —no toca el alto, no pinta el botón, no escucha el dedo— y se vuelve a
   activar sola si la pantalla rota. Quién manda en esa decisión es la CSS: se
   pregunta si el tirador está visible, y no se comparan anchos a mano, porque
   las cuatro páginas NO tienen los mismos cortes (solo mapa.html tiene el
   layout de acostado). El `matchMedia` está para enterarse del cambio al
   instante; quien decide es el `display` del tirador. */

/* Los tres números del gesto, juntos y con nombre para que se puedan discutir:
   cuánto hay que mover el dedo para que deje de ser un toque, cuánto para que
   el arrastre cuente como decidido, y a qué velocidad (px/ms) deja de ser un
   arrastre y pasa a ser un envión. */
const HOJA_TOQUE = 8, HOJA_DECIDIDO = 24, HOJA_ENVION = .45;
/* Una velocidad medida hace más de 120 ms ya no describe el gesto: es el dedo
   parado antes de soltar, y ahí el envión sería una invención nuestra. */
const HOJA_VELOCIDAD_VIEJA = 120;

/* Los topes van numerados -1..2 y NO 0..3 a propósito: las páginas ya llaman
   `fijarPanel(0)` para el reposo y `fijarPanel(1)` para la altura media desde
   `refrescar()`. Renumerar habría hecho que `fijarPanel(0)` escondiera la hoja
   en el arranque. El tope nuevo se cuelga por abajo. */
const HOJA_OCULTA = -1, HOJA_REPOSO = 0, HOJA_MEDIA = 1, HOJA_ALTA = 2;

function montarHoja(opc = {}){
  const panel = document.querySelector(opc.panel || "#panel");
  if(!panel) return null;
  const marco = panel.parentElement;
  const tirador = panel.querySelector(opc.tirador || ".tirador");
  if(!marco || !tirador) return null;
  const lista = panel.querySelector(opc.lista || ".lista");
  const cabecera = panel.querySelector(opc.conteo || ".conteo");
  const agarres = [tirador, cabecera].filter(Boolean);

  let movil = false, indice = HOJA_REPOSO;
  /* Dos identificadores y no uno: el tirador y el contador se manejan con
     Pointer Events y la lista con Touch Events (ver el cableado), y un mismo
     dedo real llega a los dos con numeraciones distintas —`pointerId` empieza
     en 1 y `Touch.identifier` en 0—. Con una sola variable se confundían y un
     `pointerup` ajeno cortaba el arrastre de la lista. */
  let gesto = null, seMovio = false, esperaLista = null;
  let idPuntero = null, idTacto = null;
  let cuadro = 0, pendiente = null, reMedida = 0;

  /* ---- El CROMO: todo lo que el panel tiene que mostrar sí o sí ----
     Son los hijos del panel que no son la lista —el tirador, la cabecera del
     contador, la fila de afinar, y en descuentos un pie fijo— más los bordes
     propios del panel, que con `box-sizing:border-box` entran en el `height`.
     Se MIDE, no se declara: cada página tiene una cabecera distinta y pedirle
     un número a mano es garantizar que algún día no calce. */
  const cromoDelPanel = () => {
    let alto = panel.offsetHeight - panel.clientHeight;   // los bordes propios
    for(const hijo of panel.children){
      if(hijo === lista || (lista && hijo.contains(lista))) continue;
      alto += hijo.offsetHeight;                          // 0 si está display:none
    }
    return alto;
  };

  /* Cuánta lista tiene que asomar en reposo. Se mide una FILA DE VERDAD en vez
     de clavar un número: una tarjeta de evento, una de descuento y una de
     taller no miden lo mismo.
     La banda de plausibilidad DESCARTA, no recorta, y la diferencia importa:
     la primera cría de la lista no siempre es una fila. Puede ser el esqueleto
     de carga, el cartel de "no hay nada", o —medido— un envoltorio que agrupa
     el día entero: 693 px en cine y 7.566 en descuentos. Recortando esos a un
     tope de 132 el reposo salía inflado (cine al 61 % de la pantalla,
     descuentos al 66 %); descartándolos cae al asomo por defecto, que es lo
     honesto cuando no hay una fila que medir. */
  const HOJA_ASOMO = 90;
  const asomoDeLista = () => {
    const fila = lista && lista.firstElementChild;
    const alto = fila ? fila.offsetHeight : 0;
    const esFila = alto >= 56 && alto <= 132;
    /* El asomo tiene TECHO, y la fila medida solo lo baja. Dejar entrar la
       fila entera parecía lo correcto y no lo es por dos razones: una fila que
       calza exacta con el borde de la hoja se lee como el final de la lista,
       cuando lo que hay que decir es "sigue"; y con filas altas el reposo se
       inflaba —talleres, con filas de 119, se llevaba el 50 % de la pantalla—.
       Con techo, el que asoma es un pedazo de la fila siguiente, que es la
       señal de que hay más abajo, y el mapa conserva su parte. */
    return Math.min(esFila ? alto : HOJA_ASOMO, HOJA_ASOMO);
  };

  /* El reposo tiene un tope arriba (no crece más de 250 px en pantallas
     grandes) y un piso abajo. El piso ERA 132 píxeles pelados y ese fue el
     error: 132 no sabe nada del cromo de cada página. mapa.html funcionaba de
     casualidad —sus 97 px de cabecera caben en 173 y dejan 74 de lista— y las
     otras tres no. Medido en un iPhone 13 con el reposo viejo: cine abría con
     43 px de lista, talleres con 63 y descuentos con CERO, o sea la hoja se
     abría entera de cabecera. Y empeoró cuando el tirador subió de 29 a 44.
     No es teoría: descuentos tenía su propia fórmula (.52 en vez de .34)
     justamente por esto, y el comentario que lo advertía se perdió al portarla
     —decía que su pie fijo se lleva 66 px y que con el reposo de mapa la lista
     abría mostrando una fila y media—.

     Ahora el piso es el cromo medido más un asomo de lista, y el tope de 250
     CEDE ante el piso, no al revés: una hoja que abre sin una sola fila no es
     una lista, es una cabecera con barra de agarre.

     La regla de diseño que sostiene todo esto —en reposo el mapa se queda con
     la mayoría de la pantalla— se sigue cumpliendo donde puede: mapa queda en
     el 37 % del alto y cine y talleres cerca del 42 %. Descuentos se pasa al
     55 %, y es a propósito: esa página ya se daba el 52 % antes de portarse
     porque su pie fijo no deja otra. Apretarle el cromo (el aviso del banco,
     la nota de geo) es una decisión de diseño y no se toma desde acá. */
  let medidaCache = null;
  const medidas = () => {
    /* Durante un arrastre las medidas no cambian, y volver a leerlas en cada
       `touchmove` obliga al navegador a recalcular el layout justo después de
       que le escribimos el alto: es el clásico ida y vuelta que hace que el
       gesto se sienta pegajoso. Se mide una vez al empezar el gesto. */
    if(gesto && medidaCache) return medidaCache;
    const disponible = marco.clientHeight;
    const alta = Math.round(disponible * .88);
    const piso = cromoDelPanel() + asomoDeLista();
    // El reposo nunca puede pasar de la altura alta, y media nunca puede
    // quedar por debajo del reposo: si la escalera se desordena, el tope más
    // cercano deja de significar nada. Pasa de verdad en pantallas muy bajas.
    const reposo = Math.min(alta, Math.round(Math.max(piso, Math.min(250, disponible * .34))));
    return (medidaCache = {disponible, reposo, alta,
                           media: Math.max(reposo, Math.round(disponible * .62))});
  };
  // La escalera en píxeles, en el mismo orden que los índices -1..2.
  const escalera = m => [0, m.reposo, m.media, m.alta];
  const altoDe = (i, m) => escalera(m)[i + 1];

  /* Una sola escritura de estilo por cuadro. Durante el arrastre llegan
     pointermove a 120 Hz y escribir dos custom properties en cada uno es
     pedirle al navegador un recálculo de layout por evento. */
  const escribir = (alto, baja) => {
    panel.style.setProperty("--alto-panel", Math.round(alto) + "px");
    panel.style.setProperty("--baja-hoja", Math.round(baja) + "px");
  };
  const escribirEnCuadro = (alto, baja) => {
    pendiente = [alto, baja];
    if(cuadro) return;
    cuadro = requestAnimationFrame(() => { cuadro = 0; escribir(pendiente[0], pendiente[1]); });
  };
  // Cuando el tope ya se decidió, la escritura es inmediata y el cuadro
  // pendiente sobra: si se dejara, pisaría el destino un instante después.
  const escribirYa = (alto, baja) => {
    if(cuadro){ cancelAnimationFrame(cuadro); cuadro = 0; }
    escribir(alto, baja);
  };

  /* ---- El botón que trae la hoja de vuelta ----
     Lo construye la función y no el HTML: así portar una página no obliga a
     acordarse de un marcado nuevo, y el botón nunca queda huérfano de su
     lógica. El texto lo pone la página —lee su propio contador— y se refresca
     solo, ver `vigilarConteo` más abajo. */
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "volver-hoja";
  boton.id = opc.idBoton || "volver-hoja";
  boton.hidden = true;
  boton.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"
      stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg>
    <span class="volver-hoja-txt"></span>`;
  if(panel.id) boton.setAttribute("aria-controls", panel.id);
  boton.addEventListener("click", () => fijar(HOJA_REPOSO, true));
  marco.appendChild(boton);
  const rotuloTxt = boton.querySelector(".volver-hoja-txt");

  /* El rótulo por defecto sale del contador de la propia página (`#conteo` +
     `#conteo-txt`), que es el dato que ya está pintado y traducido. Una página
     que cuente distinto pasa `opc.rotulo`. */
  const rotuloPorDefecto = () => {
    const n = panel.querySelector("#conteo"), s = panel.querySelector("#conteo-txt");
    return [n && n.textContent.trim(), s && s.textContent.trim()]
      .filter(Boolean).join(" ").trim();
  };
  const rotular = () => {
    const texto = (opc.rotulo ? opc.rotulo() : rotuloPorDefecto()) || t("verLista");
    rotuloTxt.textContent = texto;
    // El texto visible es "128 eventos", que como nombre de un botón no dice
    // qué hace. El lector de pantalla escucha el verbo.
    boton.setAttribute("aria-label", t("verLista") + ", " + texto);
  };

  /* ---- Fijar un tope ---- */
  function fijar(i, conFoco){
    indice = Math.max(HOJA_OCULTA, Math.min(HOJA_ALTA, Math.round(i)));
    if(!movil) return indice;
    const m = medidas();
    const fuera = indice === HOJA_OCULTA;
    panel.classList.toggle("hoja-fuera", fuera);
    // Escondida conserva el alto de reposo: así vuelve creciendo desde donde
    // corresponde y no aparece de golpe con el alto que tenía antes de irse.
    escribirYa(fuera ? m.reposo : altoDe(indice, m), 0);
    // Fuera de pantalla la hoja sigue teniendo tarjetas enfocables con Tab.
    // `inert` la saca del tabulador y del árbol de accesibilidad de una vez.
    if("inert" in panel) panel.inert = fuera;
    tirador.setAttribute("aria-expanded", indice > HOJA_REPOSO ? "true" : "false");
    boton.hidden = !fuera;
    if(fuera) rotular();
    if(conFoco) (fuera ? boton : tirador).focus();
    return indice;
  }

  /* ---- El gesto ---- */
  function empezar(y){
    // Se tira la medida vieja ANTES de abrir el gesto: la de adentro se
    // congela, así que la que se congela tiene que ser fresca.
    medidaCache = null;
    gesto = {y0:y, yUlt:y, tUlt:performance.now(), v:0,
             alto0:panel.clientHeight, i0:indice, alto:panel.clientHeight, baja:0};
    seMovio = false;
    panel.classList.add("arrastrando");
  }

  function mover(y){
    if(!gesto) return;
    const ahora = performance.now(), dt = ahora - gesto.tUlt;
    if(dt > 0){ gesto.v = (y - gesto.yUlt) / dt; gesto.yUlt = y; gesto.tUlt = ahora; }
    /* `hoja-moviendo` marca que esto ya es un ARRASTRE y no un dedo apoyado.
       De ella cuelga el apagado de la selección de texto en la cabecera del
       contador, que tiene que seguir siendo copiable en reposo y con un pulso
       largo (ver loica.css §4b). Por eso no se cuelga de `arrastrando`, que se
       pone en el `pointerdown` y por lo tanto también en un pulso quieto. */
    if(!seMovio && Math.abs(y - gesto.y0) > HOJA_TOQUE){
      seMovio = true;
      panel.classList.add("hoja-moviendo");
    }
    const m = medidas();
    const bruto = gesto.alto0 - (y - gesto.y0);
    /* Dos variables y no una: por arriba del reposo la hoja CRECE (cambia de
       alto), y por debajo ya no puede encoger más —el tirador y el contador
       tienen alto propio— así que se DESLIZA hacia abajo. Estirar el alto por
       debajo de su contenido dejaba la cabecera desbordada fuera de la caja. */
    gesto.alto = Math.min(m.alta, Math.max(m.reposo, bruto));
    gesto.baja = Math.max(0, Math.min(m.reposo, m.reposo - bruto));
    escribirEnCuadro(gesto.alto, gesto.baja);
  }

  function soltar(cancelado){
    if(!gesto) return;
    const g = gesto; gesto = null;
    panel.classList.remove("arrastrando", "hoja-moviendo");
    const m = medidas(), pasos = escalera(m);
    // Lo que el ojo ve: el alto menos lo que se fue por abajo.
    const visible = g.alto - g.baja;
    let cerca = 0;
    pasos.forEach((h, k) => {
      if(Math.abs(h - visible) < Math.abs(pasos[cerca] - visible)) cerca = k;
    });
    let destino = cerca - 1;

    /* Un gesto CANCELADO no es un gesto soltado: el sistema se llevó el dedo
       (una llamada, el gesto de volver de iOS, el navegador que decide que el
       toque era para scrollear). Ahí solo se cae al tope más cercano, sin
       envión y sin la regla del arrastre decidido.
       Esto no es celo: era un error real. Con `pan-y` en la lista, Chromium
       mandaba `pointerdown`, uno o dos `pointermove` y un `pointercancel`; con
       DOS movimientos alcanzaba a guardarse una velocidad de 0,5 px/ms, el
       cancel entraba por la misma puerta que un soltar normal y la hoja se
       iba un tope hacia abajo (448 → 316) por un gesto que el navegador ya
       había dado por muerto. Peor: eso hacía PASAR una prueba que en realidad
       estaba fallando. */
    if(!cancelado){
      const v = (performance.now() - g.tUlt > HOJA_VELOCIDAD_VIEJA) ? 0 : g.v;
      const dy = g.yUlt - g.y0;                       // + hacia abajo
      const rumbo = (v !== 0 ? v : dy) < 0 ? 1 : -1;  // +1 sube, -1 baja
      if(Math.abs(v) >= HOJA_ENVION) destino += rumbo;
      // Un arrastre corto pero decidido tiene que cambiar de tope. Si cae en el
      // mismo del que salió, el usuario lee "no me registró" y repite el gesto.
      else if(Math.abs(dy) > HOJA_DECIDIDO && destino === g.i0) destino = g.i0 + rumbo;
    }
    fijar(destino);
  }

  /* Soltar el dedo limpia SIEMPRE, haya o no arrastre: si la lista se quedó
     esperando (`esperaLista`) o el toque fue limpio, `soltar()` se devuelve
     temprano y sin esto el id del dedo quedaba pegado hasta el toque siguiente. */
  function terminar(cancelado){
    soltar(cancelado);
    esperaLista = null; idPuntero = null; idTacto = null;
  }

  /* ---- La lista: solo se lleva el gesto cuando ya no tiene a dónde bajar ----
     No se decide en el `touchstart` sino en el primer movimiento que pasa el
     umbral de toque: antes de eso no se sabe si el dedo viene a scrollear o a
     bajar la hoja, y adivinar mal rompe una de las dos cosas.
     Tres condiciones para quedárselo, y las tres tienen que darse:
       · el dedo va HACIA ABAJO y más vertical que horizontal;
       · la lista ya está arriba del todo, así que no tiene a dónde bajar;
       · el evento todavía es `cancelable`. Si el navegador ya empezó a
         scrollear, `preventDefault()` no hace nada y quedarse con el gesto
         sería mover la hoja Y scrollear la lista al mismo tiempo. */
  function decidirLista(d, e){
    const dy = d.clientY - esperaLista.y0, dx = d.clientX - esperaLista.x0;
    if(Math.abs(dy) <= HOJA_TOQUE && Math.abs(dx) <= HOJA_TOQUE) return false;
    const nuestro = dy > 0 && Math.abs(dy) > Math.abs(dx) &&
                    lista.scrollTop <= 0 && e.cancelable;
    esperaLista = null;
    // El gesto arranca DESDE AQUÍ, no desde el punto original: si no, la hoja
    // pegaría un salto de los 8 px que el dedo ya llevaba andados.
    if(nuestro) empezar(d.clientY);
    return nuestro;
  }

  /* ---- Cableado: cada zona con la familia de eventos que le sirve ----

     Y no es capricho, es lo único que funciona. El tirador y el contador
     llevan `touch-action:none`, así que ahí no hay ningún scroller peleando
     por el gesto y Pointer Events anda perfecto.

     La LISTA es otra cosa. Lleva `touch-action:pan-y` —tiene que scrollear— y
     eso significa que el gesto vertical es del scroller nativo, no nuestro.
     Medido en Chromium con toques reales: llega `pointerdown`, UNO o dos
     `pointermove`, y `pointercancel`. Se acabó. La lógica de "decido en el
     primer movimiento pasados 8 px" no alcanza a correr, y cuando alcanzaba
     era peor: el `pointercancel` entraba con velocidad guardada y la hoja se
     movía un tope sola. Pointer Events y querer interceptar un gesto vertical
     dentro de un scroller son incompatibles por construcción.

     La salida es la que usan las librerías de bottom sheet: escuchar
     `touchmove` en la lista con `{passive:false}` y llamar `preventDefault()`.
     Eso hace dos cosas a la vez —y por eso es la línea entera del arreglo—:
       1. le avisa al navegador, ANTES del gesto, que acá alguien podría
          cancelarlo, y entonces marca los `touchmove` como `cancelable`. Con
          todos los listeners pasivos llegaban con `cancelable=false` desde el
          primero, y `preventDefault()` no habría hecho nada;
       2. cuando decidimos quedarnos el gesto, frena el scroll de verdad.
     El `{passive:false}` tiene que ir EN EL REGISTRO: después no se cambia. */
  const hayPuntero = typeof window.PointerEvent === "function";
  /* ---- Los controles que viven DENTRO de una zona de agarre ----
     La primera versión se negaba a empezar el gesto si el dedo caía sobre un
     botón. Sonaba prudente y era el error: renunciaba al GESTO cuando solo
     había que renunciar al TOQUE. En cine el conmutador Cines/Películas/Qué
     ver vive dentro del `.conteo` y se lleva 219 de sus 386 px: barriendo el
     ancho con toques reales, la hoja arrancaba en la mitad de los puntos —y
     justo en la página donde el agarre nuevo más falta hacía.

     Ahora es al revés, que es lo que hacen las hojas nativas: el arrastre
     arranca igual encima de un botón, y quien decide es el desenlace. Si el
     dedo se movió, se traga el `click` del botón y manda la hoja; si no se
     movió, el botón recibe su toque como si nada hubiera pasado. La bandera
     que lo resuelve es la misma `seMovio` de 8 px que ya mataba el click
     fantasma: es la misma decisión tomada en el mismo lugar.

     Va en captura y sobre el panel entero, así cubre el conmutador de cine,
     los chips de cualquier cabecera, las tarjetas de la lista y el propio
     tirador, sin tener que enumerar a ninguno. */
  panel.addEventListener("click", e => {
    if(!seMovio) return;
    seMovio = false;
    e.stopPropagation();
    e.preventDefault();
  }, true);

  // El dedo de ESTE gesto entre todos los que cambiaron en el evento.
  const dedoDe = e => idTacto === null ? null
    : Array.prototype.find.call(e.changedTouches, d => d.identifier === idTacto);

  /* Touch Events para una zona. `esLista` distingue las dos maneras de
     empezar: en el tirador el gesto es nuestro desde el toque, y en la lista
     hay que esperar a ver para dónde va el dedo.
     No hacen falta listeners en `window`: a diferencia de los punteros, un
     Touch le pertenece al elemento donde EMPEZÓ durante toda su vida, así que
     el `touchend` llega acá aunque el dedo termine en la otra punta. */
  const cablearTacto = (zona, esLista) => {
    zona.addEventListener("touchstart", e => {
      if(!movil || gesto || esperaLista || idTacto !== null) return;
      const d = e.changedTouches[0];
      idTacto = d.identifier;
      if(esLista) esperaLista = {y0:d.clientY, x0:d.clientX};
      else empezar(d.clientY);
    }, {passive:true});

    zona.addEventListener("touchmove", e => {
      const d = dedoDe(e); if(!d) return;
      if(esperaLista && !decidirLista(d, e)) return;   // es de la lista: que scrollee
      if(!gesto) return;
      mover(d.clientY);
      if(e.cancelable) e.preventDefault();
    }, {passive:false});

    zona.addEventListener("touchend", e => { if(dedoDe(e)) terminar(); }, {passive:true});
    zona.addEventListener("touchcancel", e => { if(dedoDe(e)) terminar(true); }, {passive:true});
  };

  if(lista) cablearTacto(lista, true);

  if(hayPuntero){
    agarres.forEach(zona => zona.addEventListener("pointerdown", e => {
      // El segundo dedo no hereda el gesto: con dos apoyados saltaba de uno a
      // otro y la hoja pegaba tirones.
      if(!movil || gesto || idPuntero !== null || e.button > 0) return;
      idPuntero = e.pointerId;
      // Se pide la captura, pero los `move`/`up` se escuchan en window: si
      // Safari la suelta, el arrastre sigue vivo igual.
      try{ zona.setPointerCapture(e.pointerId); }catch(_){}
      empezar(e.clientY);
    }));
    addEventListener("pointermove", e => {
      if(e.pointerId === idPuntero) mover(e.clientY);
    }, {passive:true});
    addEventListener("pointerup", e => { if(e.pointerId === idPuntero) terminar(); });
    addEventListener("pointercancel", e => { if(e.pointerId === idPuntero) terminar(true); });
  }else{
    // Sin Pointer Events, el tirador y el contador van por Touch como la lista.
    agarres.forEach(zona => cablearTacto(zona, false));
  }

  /* Un toque limpio en el tirador cicla topes. Acá ya no hace falta preguntar
     por `seMovio`: el guardia en captura del panel se traga el click de todo
     arrastre antes de que llegue hasta acá. Si este click existe, es un toque
     de verdad. */
  tirador.addEventListener("click", () => {
    if(movil) fijar(indice >= HOJA_ALTA ? HOJA_REPOSO : indice + 1);
  });
  tirador.addEventListener("keydown", e => {
    if(!movil) return;
    if(e.key === "ArrowUp"){ e.preventDefault(); fijar(indice + 1); }
    else if(e.key === "ArrowDown"){ e.preventDefault(); fijar(indice - 1); }
    else if(e.key === "Enter" || e.key === " "){
      e.preventDefault(); fijar(indice >= HOJA_ALTA ? HOJA_REPOSO : indice + 1);
    }
    // Escape esconde y deja el foco en el botón de volver: la salida del
    // teclado no puede terminar en un foco perdido en el <body>.
    else if(e.key === "Escape"){ e.preventDefault(); fijar(HOJA_OCULTA, true); }
  });
  tirador.setAttribute("role", "button");
  if(!tirador.hasAttribute("tabindex")) tirador.tabIndex = 0;
  if(panel.id) tirador.setAttribute("aria-controls", panel.id);
  // El rótulo de la página manda: cada una nombra lo que lista (eventos,
  // películas, descuentos, talleres). Este es el que se pone si no hay ninguno.
  if(!tirador.hasAttribute("aria-label")) tirador.setAttribute("aria-label", t("ajustarLista"));

  /* ---- Modo: hoja o columna ----
     Lo decide el `display` del tirador, o sea la CSS de cada página, porque
     los cortes NO son los mismos en las cuatro (solo mapa.html manda la lista
     al costado con el teléfono acostado). Escribir los anchos acá otra vez era
     garantizar que algún día dejen de calzar. */
  const enHoja = () => getComputedStyle(tirador).display !== "none";
  function modo(){
    const antes = movil;
    movil = enHoja();
    if(!movil){
      // Inerte: se devuelven las llaves y manda la columna. Si quedaran puestos
      // el alto o el desplazamiento de un gesto a medias, la columna aparecería
      // corrida hacia abajo al rotar.
      terminar(true);
      panel.classList.remove("hoja-fuera", "arrastrando", "hoja-moviendo", "hoja-viva");
      panel.style.removeProperty("--alto-panel");
      panel.style.removeProperty("--baja-hoja");
      agarres.forEach(z => z.classList.remove("hoja-agarre"));
      if("inert" in panel) panel.inert = false;
      tirador.removeAttribute("aria-expanded");
      boton.hidden = true;
      return;
    }
    panel.classList.add("hoja-viva");
    agarres.forEach(z => z.classList.add("hoja-agarre"));
    // Al volver de la columna la hoja NO vuelve escondida: rotar el teléfono
    // no es pedir que la lista desaparezca.
    fijar(!antes && indice === HOJA_OCULTA ? HOJA_REPOSO : indice);
  }
  const volverAMedir = () => {
    // Con el dedo apoyado no se remide nada: las medidas del gesto están
    // congeladas a propósito y recalcular a mitad de arrastre pega un tirón.
    if(reMedida || gesto) return;
    reMedida = requestAnimationFrame(() => { reMedida = 0; modo(); });
  };
  /* `resize` cubre el alto que cambia cuando iOS pliega la barra de
     direcciones; los `matchMedia` avisan del giro al instante, sin esperar a
     que el navegador se decida a emitir el resize. */
  addEventListener("resize", volverAMedir);
  ["(min-width:880px)", "(max-height:460px)"].forEach(consulta => {
    const vigia = matchMedia(consulta);
    if(vigia.addEventListener) vigia.addEventListener("change", volverAMedir);
    else if(vigia.addListener) vigia.addListener(volverAMedir);
  });

  /* La hoja nace ANTES de que la página termine de pintarse, y eso desfasaba
     todas sus cuentas. Medido en talleres: al montarse, el marco decía 565 px
     cuando el definitivo son 492, y el reposo salía en 192 en vez de 167. No
     era nuevo —el arrastre viejo tenía el mismo desfase— pero se arreglaba a
     mano y solo en mapa.html, que volvía a llamar `fijarPanel(0)` después de
     pintar la cabecera. Pedirle eso a cada página es pedirle que se acuerde.

     Un ResizeObserver lo cierra solo y para las cuatro. Mira dos cosas:
       · el MARCO, que encoge cuando la cabecera crece al llegar el JSON;
       · el CROMO del panel, porque la cabecera del contador envuelve a dos
         líneas cuando aparece la nota del catastro, y ahí el piso del reposo
         cambia sin que el marco se haya movido ni un píxel.
     No hay lazo posible: `fijar()` solo escribe el alto del PANEL, y el panel
     no está observado —sus hijos fijos no cambian de alto porque la hoja suba
     o baje; el que absorbe la diferencia es la lista, que tampoco se mira. */
  if(typeof ResizeObserver === "function"){
    const vigia = new ResizeObserver(volverAMedir);
    vigia.observe(marco);
    for(const hijo of panel.children){
      if(hijo === lista || (lista && hijo.contains(lista))) continue;
      vigia.observe(hijo);
    }
  }

  /* El rótulo del botón sigue vivo mientras la hoja está escondida: los
     filtros se pueden tocar igual y "128 eventos" tiene que dejar de mentir.
     Se mira el contador de la página en vez de pedirle que nos avise. */
  if(cabecera && typeof MutationObserver === "function"){
    new MutationObserver(() => { if(!boton.hidden) rotular(); })
      .observe(cabecera, {childList:true, characterData:true, subtree:true});
  }
  addEventListener("loica:idioma", () => { if(!boton.hidden) rotular(); });

  modo();

  /* La API. `fijarPanel` se conserva con la MISMA numeración de siempre
     —0 reposo, 1 media, 2 alta— porque `refrescar()` la llama en las cuatro
     páginas; el tope nuevo es el -1. */
  const api = {
    fijar, ocultar: () => fijar(HOJA_OCULTA), mostrar: () => fijar(HOJA_REPOSO),
    rotular, remedir: modo, get indice(){ return indice; }, get activa(){ return movil; },
    boton, panel,
  };
  window.fijarPanel = i => fijar(i);
  window.hojaLista = api;
  return api;
}

/* Auto-montaje de la cordillera: cualquier página que ponga un #cordillera
   vacío la recibe sin cablear nada. Las que la quieren con opciones (la portada
   y habla, que la tiñe con el guía) la pintan ellas y esto no las pisa. */
function montarCordillera(){
  const caja = document.getElementById("cordillera");
  if(caja && !caja.childElementCount) caja.innerHTML = cordillera();
}
if(document.readyState === "loading")
  document.addEventListener("DOMContentLoaded", montarCordillera);
else montarCordillera();
