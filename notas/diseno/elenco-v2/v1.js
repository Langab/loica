/* v1 = copia literal de web/loica.js líneas 25-397 (2026-08-22) para comparar antes/después */
const V1 = (() => {
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

  /* El Guarén: la rata de Santiago, y en Chile "rata" es el que cuida la
     plata. Por eso se hace cargo de los descuentos y por eso desplazó al Degú
     de esa página: el chiste lo entiende cualquiera y no hay que explicarlo.

     El elenco ya tiene tres roedores (chinchilla, degú, guarén) y un perro,
     así que las señas están elegidas contra ELLOS, no contra un manual de
     fauna. La cabeza es una CUÑA que se afina hasta la nariz —los otros tres
     tienen cara redonda—, las orejas son dos círculos pelados ARRIBA de la
     cabeza (las de la chinchilla son igual de grandes pero van a los lados, a
     la altura de los ojos), y abajo asoman los dos incisivos, que van CREMA
     porque los del degú son anaranjados y a 22px el color del diente es lo
     único que los separa.

     El hocico claro no es maquillaje: el guarén de verdad es oscuro arriba y
     pálido abajo, y de paso resuelve el mismo problema que el degú tuvo con
     su anillo. Los ojos son azul tinta y sobre el café de descuentos dan
     2,4:1 — desaparecen. Puestos sobre la cuña crema pasan de sobra. */
  guaren: (c, k, p) => `
    <circle cx="6.8" cy="5.6" r="3.6" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <circle cx="17.2" cy="5.6" r="3.6" fill="${c}" stroke="${k}" stroke-width="1.5"/>
    <circle cx="6.9" cy="5.8" r="1.8" fill="#F2778C" opacity=".7"/>
    <circle cx="17.1" cy="5.8" r="1.8" fill="#F2778C" opacity=".7"/>
    <path d="M4.1 11.2a7.9 7.9 0 0 1 15.8 0c0 3.2-1.4 5.9-3.3 8-1.7 1.9-3.2 3.4-4.6 3.4s-2.9-1.5-4.6-3.4c-1.9-2.1-3.3-4.8-3.3-8z"
          fill="${c}" stroke="${k}" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M8.5 15.2c1-.5 2.2-.8 3.5-.8s2.5.3 3.5.8c-.5 3.3-1.7 5.9-3.5 7.9-1.8-2-3-4.6-3.5-7.9z"
          fill="#FAF3E7"/>
    ${ojos(8.6, 15.4, 11.6, 1.8, p)}
    <ellipse cx="12" cy="18.5" rx="1.45" ry="1.1" fill="${OJO}"/>
    <path d="M10.9 19.5h2.2v2.2a1.1 1.1 0 0 1-2.2 0z"
          fill="#FAF3E7" stroke="${k}" stroke-width="1.05" stroke-linejoin="round"/>
    <path d="M12 19.8v1.9" stroke="${k}" stroke-width=".85"/>`,

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

  /* El Quiltro: el perro callejero chileno, y guatón, que es como se le dice
     al que anda bien comido. Es el animal que ya está afuera de la fuente de
     soda antes que uno, así que le tocaba esta página y no otra.

     Tres señas y ninguna es de raza, porque el quiltro justamente no tiene.
     UNA OREJA PARADA Y LA OTRA CAÍDA, que es lo que lo separa del culpeo —el
     otro cánido del elenco— que lleva las dos en punta y simétricas. El hocico
     corto y ancho con la nariz grande, contra el hocico afilado del zorro. Y
     LA LENGUA AFUERA: ningún otro de los diez saca la lengua, así que a 22px
     esa mancha rosada bajo la cara solo puede ser un perro. */
  quiltro: (c, k, p) => `
    <path d="M4.8 12.4 5.4 3.6 11.4 7.8z" fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M6.7 9.8 7.1 5.8 9.7 7.6z" fill="#F2778C" opacity=".75"/>
    <path d="M17.4 5.2c3-.4 5.2 1.6 5 4.6-.2 3-2.2 5.4-4.6 6-1.8.4-3-.8-2.8-2.8.2-3 1-5.6 2.4-7.8z"
          fill="${c}" stroke="${k}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M18.1 7.6c1.6-.2 2.6.8 2.5 2.4-.1 1.6-1.1 2.8-2.4 3.1z" fill="#F2778C" opacity=".7"/>
    <circle cx="12" cy="12.4" r="8.3" fill="${c}" stroke="${k}" stroke-width="1.6"/>
    <ellipse cx="12" cy="16.6" rx="5.4" ry="4" fill="#FAF3E7"/>
    ${ojos(8.7, 15.3, 10.8, 1.8, p)}
    <ellipse cx="12" cy="15.4" rx="2" ry="1.5" fill="${OJO}"/>
    <path d="M10.8 18.9h2.4v2.5a1.2 1.2 0 0 1-2.4 0z"
          fill="#F2778C" stroke="${k}" stroke-width="1.1" stroke-linejoin="round"/>`,

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
  /* La del guarén es la seña que lo delata de lejos, y es la única del elenco
     que NO va del color del animal: es PELADA. Larga, delgada y color carne.
     La del degú también es delgada pero va del color del cuerpo y termina en
     un pincel oscuro; la de la chinchilla es tupida entera. Esta es la única
     que se ve piel, y es más larga que cualquier otra: llega hasta el borde.

     Sin anillos a propósito. Medirían 2 de las 48 unidades del lienzo y la
     regla del 1/15 los deja fuera: a 22px no serían un dato del animal, serían
     tierra en la pantalla. */
  guaren:     (c, k) => cola("M37.6 32.6c5.4.4 8.8-2.6 10.2-9", "#E8C3B4", k, 4),
  /* La del quiltro sube y se ENROSCA hacia adelante, que es como la lleva un
     perro contento y es media silueta del animal. La de la chinchilla también
     sube pero se queda en arco; esta cierra el gancho arriba. */
  quiltro:    (c, k) => cola("M37.6 29c4-1.2 6.4-4.2 6.6-8 .1-2.1-1.3-3.4-3-3-1.6.4-2.5 1.9-2.3 3.6", c, k, 5),
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
  /* Más largo y más bajo que el degú, y las patas más finas: el guarén corre
     pegado a la muralla, no salta. La cabeza va 1,2 más abajo que la del resto
     porque termina en punta: con el desplazamiento de todos, el hocico apenas
     tocaba el lomo y el animal quedaba partido en dos piezas sueltas. */
  guaren:     {cuerpo:[28.4, 31.8, 12, 8], grosor:2.8, cabeza:"3.2 4.6",
               patas:"M21.8 39.2v5.4M27.4 39.6v5M33.4 39.2v5.4M38.2 38.4v6", extra:""},
  /* Guatón, literal: el cuerpo es el más ancho de los cinco cuadrúpedos y las
     patas las más cortas. La panza clara que cuelga es mitad chiste y mitad
     anatomía de perro de barrio bien alimentado por todo el pasaje. */
  quiltro:    {cuerpo:[28.4, 31.6, 12.4, 8.8], grosor:3.5, cabeza:"2.5 3.4",
               patas:"M21.8 39.2v5.2M27.6 39.6v4.8M33.8 39.2v5.2M38.4 38.4v6",
               extra:`<ellipse cx="28.4" cy="37.4" rx="8.2" ry="3.4" fill="#FAF3E7" opacity=".92"/>`},
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

return {carita, cuerpo, mascota, CARITAS, ojos, OJO, TINTA_VAR};
})();
