/* ============================================================
   LOICA — elenco v2 (prototipo, 2026-08-22)
   Los mismos once animales de loica.js, con tres cosas nuevas:
     1. Un ACCESORIO por animal, humano y reconocible a 22px, que dice de
        qué se hace cargo sin leer la etiqueta (la Chinchilla va de boina
        al teatro, el Pingüino con birrete y libro al seminario...).
     2. PARTES con clase (ojos, orejas, cola, alas, accesorio) para que el
        CSS las anime sin JavaScript: parpadeo, cola que se mueve, boina
        que se ladea.
     3. Una ENTRADA por animal, sacada de su propia historia (el Degú sale
        de la tierra, la Chinchilla llega tarde y aplaude).
   Misma API que loica.js: carita() / cuerpo() / mascota(), más las
   opciones {acc:false} (sin accesorio, para el logo) y {anima:true}.
   Las reglas de dibujo siguen siendo las de _direccion_visual.md §6:
   cabeza ≥70%, ojo ≥1,6, contorno 1,6, nada bajo 1/15 del lienzo.
   ============================================================ */
const V2 = (() => {
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
  quiltro:    (c, k) => cola("M37.6 29c4-1.2 6.4-4.2 6.6-8 .1-2.1-1.3-3.4-3-3-1.6.4-2.5 1.9-2.3 3.6", c, k, 5),
};

const CUADRUPEDOS = {
  culpeo:     {cuerpo:[29.4, 31.2, 12.2, 8.6], grosor:3.4, cabeza:"2.5 3.4",
               patas:"M21.6 38.6v5.6M28 38.8v5.4M34.4 38.4v5.8M39.4 37.6v6.4",
               extra:`<ellipse cx="19.6" cy="27.6" rx="3.4" ry="4.2" fill="${CREMA}"/>`},
  pudu:       {cuerpo:[28.8, 30.8, 11.4, 8.2], grosor:2.7, cabeza:"2.5 3.4",
               patas:"M21.8 38.2v6.4M27.4 38.6v6M33.6 38.4v6.2M38.6 37.4v7.2", extra:""},
  chinchilla: {cuerpo:[28.4, 31.4, 10.8, 9.6], grosor:3.2, cabeza:"2.5 3.4",
               patas:"M22.6 39.8v4.4M27.8 40.2v4M33.4 39.8v4.4M37.6 38.8v5.2", extra:""},
  degu:       {cuerpo:[28.6, 31.8, 11.4, 8.4], grosor:3, cabeza:"2.5 3.4",
               patas:"M22.2 39.4v5M27.6 39.8v4.6M33.4 39.4v5M38 38.6v5.6",
               extra:`<ellipse cx="27.4" cy="37.4" rx="5.4" ry="2.3" fill="${CREMA}" opacity=".85"/>`},
  chungungo:  {cuerpo:[28.6, 33, 13.8, 7.4], grosor:3.2, cabeza:"3 8.2",
               patas:"M20.8 39.4v4.8M26.6 39.8v4.4M33.2 39.6v4.6M38.2 38.6v5.4", extra:""},
  guaren:     {cuerpo:[28.4, 31.8, 12, 8], grosor:2.8, cabeza:"3.2 4.6",
               patas:"M21.8 39.2v5.4M27.4 39.6v5M33.4 39.2v5.4M38.2 38.4v6", extra:""},
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

/* ---------- EL CSS DE LAS PARTES ----------
   Vive junto al dibujo para que el que copie el módulo se lleve las dos
   mitades. Todo es CSS puro sobre grupos con clase; con
   prefers-reduced-motion se apaga entero y los ojos quedan abiertos. */
const CSS = `
.masc{overflow:visible}
.masc [class^="p-"],.masc [class*=" p-"]{transform-box:fill-box;transform-origin:50% 50%}
/* --- Tics de reposo: solo con .anima --- */
.masc.anima .p-ojos{animation:m-parpadeo var(--parp,5.3s) ease-in-out var(--d,0s) infinite}
.masc.anima .p-dormido{animation:none}
@keyframes m-parpadeo{0%,93%,100%{transform:scaleY(1)}96%{transform:scaleY(.08)}}
/* Loica: ladea la cabeza, como quien escucha tu pregunta */
.masc-loica.anima{transform-origin:50% 100%;animation:m-ladear 4.6s ease-in-out var(--d,0s) infinite}
@keyframes m-ladear{0%,100%{transform:rotate(0)}30%{transform:rotate(-4deg)}60%{transform:rotate(3deg)}}
/* Cóndor: asiente al beat, cuatro golpes y descansa */
.masc-condor.anima .p-cabeza{transform-origin:50% 100%;animation:m-beat 3.6s linear var(--d,0s) infinite}
@keyframes m-beat{0%,8%,16%,24%,32%,100%{transform:translateY(0)}4%,12%,20%,28%{transform:translateY(.9px)}}
/* Culpeo: el destello cruza los lentes; una oreja se mueve */
.masc-culpeo.anima .p-brillo{animation:m-destello 5.4s ease-in-out var(--d,0s) infinite}
@keyframes m-destello{0%,80%,100%{transform:translateX(0);opacity:.9}88%{transform:translateX(1.6px);opacity:.2}}
.masc-culpeo.anima .p-oreja-d{transform-origin:50% 100%;animation:m-oreja 5.4s ease-in-out var(--d,0s) infinite}
/* Chinchilla: orejas que escuchan, alternadas */
.masc-chinchilla.anima .p-oreja{transform-origin:50% 100%;animation:m-oreja 3.8s ease-in-out var(--d,0s) infinite}
.masc-chinchilla.anima .p-oreja-d{animation-delay:calc(var(--d,0s) + 1.9s)}
@keyframes m-oreja{0%,86%,100%{transform:rotate(0)}90%{transform:rotate(-9deg)}95%{transform:rotate(6deg)}}
/* Chincol: dos saltitos; los chincoles saltan, no caminan */
.masc-chincol.anima{animation:m-saltos 3.4s ease-in-out var(--d,0s) infinite}
@keyframes m-saltos{0%,24%,100%{transform:translateY(0)}6%,18%{transform:translateY(-7%)}12%{transform:translateY(0)}}
.masc-chincol.anima .p-lapiz{transform-origin:20% 80%;animation:m-lapiz 3.4s ease-in-out var(--d,0s) infinite}
@keyframes m-lapiz{0%,24%,100%{transform:rotate(0)}8%{transform:rotate(-6deg)}}
/* Pudú: sacude una oreja, mira */
.masc-pudu.anima .p-oreja-i{transform-origin:80% 90%;animation:m-oreja 4.4s ease-in-out var(--d,0s) infinite}
/* Degú: la etiqueta cuelga y se mece */
.masc-degu.anima .p-etiqueta{transform-origin:30% 0%;animation:m-pendulo 2.9s ease-in-out var(--d,0s) infinite}
@keyframes m-pendulo{0%,100%{transform:rotate(5deg)}50%{transform:rotate(-7deg)}}
.masc-degu.anima .p-nariz{animation:m-nariz 2.9s ease-in-out var(--d,0s) infinite}
@keyframes m-nariz{0%,70%,100%{transform:scale(1)}78%{transform:scale(1.25,.8)}86%{transform:scale(1)}}
/* Guarén: mordisquea la tarjeta; la cola barre */
.masc-guaren.anima .p-tarjeta{transform-origin:50% 20%;animation:m-mordisco 1.7s ease-in-out var(--d,0s) infinite}
@keyframes m-mordisco{0%,100%{transform:rotate(-12deg)}50%{transform:rotate(-8deg)}}
.masc-guaren.anima .p-cola{transform-origin:0% 80%;animation:m-cola-lenta 3.2s ease-in-out var(--d,0s) infinite}
@keyframes m-cola-lenta{0%,100%{transform:rotate(0)}50%{transform:rotate(8deg)}}
/* Chungungo: trota en el lugar, sudando */
.masc-chungungo.anima{animation:m-trote .36s ease-in-out var(--d,0s) infinite alternate}
@keyframes m-trote{from{transform:translateY(0)}to{transform:translateY(-4%)}}
.masc-chungungo.anima .p-sudor{animation:m-sudor 1.4s ease-out var(--d,0s) infinite}
@keyframes m-sudor{0%{transform:translateY(0);opacity:0}20%{opacity:1}100%{transform:translateY(-3px);opacity:0}}
/* Pingüino: asiente en los momentos correctos; la borla se mece */
.masc-pinguino.anima{transform-origin:50% 100%;animation:m-asentir 5.2s ease-in-out var(--d,0s) infinite}
@keyframes m-asentir{0%,60%,100%{transform:rotate(0)}68%{transform:rotate(6deg)}76%{transform:rotate(0)}84%{transform:rotate(5deg)}}
.masc-pinguino.anima .p-borla{transform-origin:0% 0%;animation:m-pendulo 3.4s ease-in-out var(--d,0s) infinite}
/* Quiltro: cola que no para, lengua que jadea */
.masc-quiltro.anima .p-cola{transform-origin:0% 90%;animation:m-colita .32s ease-in-out var(--d,0s) infinite alternate}
@keyframes m-colita{from{transform:rotate(-10deg)}to{transform:rotate(14deg)}}
.masc-quiltro.anima .p-lengua{transform-origin:50% 0%;animation:m-jadeo .55s ease-in-out var(--d,0s) infinite alternate}
@keyframes m-jadeo{from{transform:scaleY(.78)}to{transform:scaleY(1.08)}}
/* Aves en vuelo: aleteo en dos cuadros, corte seco = dibujado, no interpolado */
.masc.anima[data-pose="volando"] .p-ala,.masc.anima[data-pose="celebrando"] .p-ala{animation:m-aleteo .22s steps(1) var(--d,0s) infinite}
.masc.anima .p-ala-i{transform-origin:100% 100%}.masc.anima .p-ala-d{transform-origin:0% 100%}
@keyframes m-aleteo{0%,49%{transform:rotate(0)}50%,100%{transform:rotate(var(--aleteo,14deg))}}
.masc.anima .p-ala-i{--aleteo:-14deg}
/* --- Entradas: una por animal, sacada de su historia. backwards = arranca escondido --- */
.entra .masc{animation-fill-mode:backwards}
.entra .masc-loica{animation:m-vuelo-llega 1.1s cubic-bezier(.25,0,.35,1) var(--d,0s) backwards}
@keyframes m-vuelo-llega{from{transform:translate(-160px,60px) rotate(-12deg)}to{transform:none}}
.entra .masc-condor{animation:m-planeo 1.2s cubic-bezier(.2,0,.2,1) var(--d,0s) backwards}
@keyframes m-planeo{from{transform:translate(60px,-140px) rotate(-22deg)}70%{transform:translate(4px,-6px) rotate(-4deg)}to{transform:none}}
.entra .masc-culpeo{animation:m-noche .9s ease-out var(--d,0s) backwards}
@keyframes m-noche{from{opacity:0;transform:scale(.86)}60%{opacity:1}to{transform:none}}
.entra .masc-chinchilla{animation:m-tarde .5s cubic-bezier(.34,1.56,.64,1) calc(var(--d,0s) + .9s) backwards}
@keyframes m-tarde{from{transform:scale(0) rotate(-20deg)}to{transform:none}}
.entra .masc-chincol{animation:m-saltos-entra 1s ease-out var(--d,0s) backwards}
@keyframes m-saltos-entra{0%{transform:translate(-110px,0)}17%{transform:translate(-90px,-22px)}34%{transform:translate(-66px,0)}51%{transform:translate(-44px,-18px)}68%{transform:translate(-22px,0)}85%{transform:translate(-8px,-10px)}100%{transform:none}}
.entra .masc-pudu{animation:m-asoma .8s cubic-bezier(.34,1.4,.64,1) var(--d,0s) backwards}
@keyframes m-asoma{from{transform:translateY(60%) scale(.7);opacity:0}40%{opacity:1}to{transform:none}}
.entra .masc-degu{animation:m-tierra .7s cubic-bezier(.34,1.56,.64,1) var(--d,0s) backwards}
@keyframes m-tierra{from{transform:translateY(70%);opacity:0}30%{opacity:1}to{transform:none}}
.entra .masc-guaren{animation:m-muralla .55s cubic-bezier(.2,.7,.2,1) var(--d,0s) backwards}
@keyframes m-muralla{from{transform:translate(180px,6px)}to{transform:none}}
.entra .masc-chungungo{animation:m-trote-entra 1.1s linear var(--d,0s) backwards}
@keyframes m-trote-entra{0%{transform:translate(-220px,0)}10%{transform:translate(-198px,-6px)}20%{transform:translate(-176px,0)}30%{transform:translate(-154px,-6px)}40%{transform:translate(-132px,0)}50%{transform:translate(-110px,-6px)}60%{transform:translate(-88px,0)}70%{transform:translate(-66px,-6px)}80%{transform:translate(-44px,0)}90%{transform:translate(-22px,-6px)}100%{transform:none}}
.entra .masc-pinguino{animation:m-pasitos 1.3s ease-out var(--d,0s) backwards}
@keyframes m-pasitos{0%{transform:translateX(150px) rotate(7deg)}12%{transform:translateX(132px) rotate(-7deg)}24%{transform:translateX(114px) rotate(7deg)}36%{transform:translateX(96px) rotate(-7deg)}48%{transform:translateX(78px) rotate(7deg)}60%{transform:translateX(60px) rotate(-7deg)}72%{transform:translateX(42px) rotate(7deg)}84%{transform:translateX(22px) rotate(-5deg)}100%{transform:none}}
/* El Quiltro no entra: ya estaba. Solo se sacude cuando llegan los demás. */
.entra .masc-quiltro{animation:m-sacudida .6s ease-in-out calc(var(--d,0s) + .2s) backwards}
@keyframes m-sacudida{0%,100%{transform:rotate(0)}25%{transform:rotate(-5deg)}50%{transform:rotate(5deg)}75%{transform:rotate(-3deg)}}
/* Reacciones: celebra (un brinco con rebote) y se duerme (se hunde) */
.masc.celebra{animation:m-celebra .6s cubic-bezier(.34,1.56,.64,1)}
@keyframes m-celebra{0%{transform:none}40%{transform:translateY(-14%) rotate(-6deg)}70%{transform:translateY(0) rotate(4deg)}100%{transform:none}}
@media (prefers-reduced-motion:reduce){
  .masc,.masc *{animation:none!important}
}`;

const NOMBRES = ["loica","condor","culpeo","chinchilla","chincol","pudu","degu","guaren","chungungo","pinguino","quiltro"];
return {carita, cuerpo, mascota, CARITAS, ACC, PROPS, CSS, NOMBRES, OJO, CREMA};
})();
if(typeof module !== "undefined") module.exports = V2;
