# Loica — Dirección visual ejecutable

**Fecha:** agosto 2026
**Para:** quien implementa (Benjamín)
**Reemplaza a:** la sección 5 de `estrategia_marca.md` (la amplía, no la contradice)

Esto no es un moodboard. Son decisiones tomadas. Donde hay una opción, elegí una y digo por qué. Todo el CSS de acá está listo para pegar.

---

## 0. La decisión en una frase

> **Loica se ve como una serigrafía chilena que cobró vida: tinta gruesa alrededor de todo, colores planos y alegres, sombra dura desplazada y esquinas muy redondeadas. Sin degradados, sin vidrio, sin negro puro.**

Le pongo nombre para poder discutirlo: **"Tinta y bulto"**. Contorno de tinta (define) + sombra dura (levanta). Dos propiedades CSS por componente. Eso es todo el sistema.

No elegí esto porque esté de moda. Lo elegí porque **es además el arreglo de accesibilidad que la app necesita hoy** (sección 1) y porque es lo más barato de renderizar sobre un mapa WebGL en movimiento. Los tres argumentos apuntan al mismo lugar, así que ahí vamos.

---

## 1. Lo que encontré en el código (esto justifica todo lo demás)

Antes de proponer, medí. Calculé los contrastes WCAG reales de los tokens que están en producción hoy. Hay cosas rotas:

| Qué | Valor actual | Contraste | Veredicto |
|---|---|---|---|
| Texto del botón principal (`--acento-contraste` sobre `--acento`) | `#FFFFFF` sobre `#E8442E` | **3,96:1** | **Falla AA.** El botón es 17px/700; "texto grande" empieza en 18,66px bold, así que no se salva por ahí |
| `--tinta-tenue` sobre `--fondo-elevado` | `#8C93A8` sobre `#FFFDF9` | **3,02:1** | **Falla AA.** Lo usan `.ayuda`, `.aprox`, `.fuente-pie`, `.mascota-nombre`, `.precio.sin-dato` y las etiquetas inactivas de la nav inferior |
| `--tinta-tenue` sobre `--fondo` | `#8C93A8` sobre `#FAF3E7` | **2,78:1** | **Falla AA** |
| `--borde` contra superficie | `#E7DCC8` sobre `#FFFDF9` | **1,34:1** | El chip depende de ese borde para leerse como control |

Y el problema grande, el que importa de verdad: **de noche, cuatro de los seis colores de pin no se distinguen del mapa.**

| Color de pin | vs. teselas claras | vs. teselas oscuras |
|---|---|---|
| `--c-fiesta` `#7A4FCF` | 4,85:1 ✓ | **2,79:1 ✗** |
| `--c-musica` `#C9331F` | 4,69:1 ✓ | **2,89:1 ✗** |
| `--c-cultura` `#2F6FB5` | 4,59:1 ✓ | **2,95:1 ✗** |
| `--c-clases` `#E08A1E` | **2,38:1 ✗** | 5,68:1 ✓ |
| `--c-libre` `#2E7D5B` | 4,44:1 ✓ | 3,05:1 ✓ |
| `--c-otros` `#E8442E` | 3,52:1 ✓ | 3,84:1 ✓ |

Ningún color puede pasar en los dos modos, porque el fondo cambia de blanco a casi negro. **Perseguir el color correcto es una pelea que no se gana.**

Un contorno de tinta sí la gana, y por goleada:

| Contorno | vs. teselas claras | vs. teselas oscuras |
|---|---|---|
| Azul Cordillera `#1E2A4A` | **12,55:1** | — |
| Crema `#EDE7DE` | — | **12,40:1** |

Con contorno, el relleno del pin deja de cargar con la legibilidad y **queda libre para ser todo lo alegre que el fundador quiere.** Ese es el truco central de esta dirección: el contorno compra la libertad de color.

Otras dos cosas que salieron de medir el código:

**Áreas táctiles bajo el mínimo.** El mínimo es 44px:

- `.chip` → `7 + 13 + 7 + 3` = **30px**
- `.tema` → **26px**
- `.idiomas button` → **24px**
- `.nav a` (barra superior) → **27px**

**Las mascotas son invisibles a los tamaños en que se usan.** El ojo de la loica es `<circle r=".4">` en un viewBox de 24. A los 19px del chip eso son **0,32px de radio** — sub-píxel. Literalmente no se dibuja. Lo mismo los brillos del pudú. Hoy las mascotas se leen como manchitas de color, no como animales. Por eso la app no se siente caricaturesca: **no es que falte estilo, es que falta resolución.**

**Y un dato de contenido que manda sobre el color:** de los 271 eventos, **102 son `otros`** (37,6%) y esa categoría está pintada de `#E8442E`, el mismo rojo del CTA. O sea: 4 de cada 10 pines del mapa son del color reservado para "esto se toca". Eso apaga el rojo y aplana el mapa.

---

## 2. Referencias investigadas

Seis, con la técnica concreta y qué se roba.

### 2.1 Duolingo — el estándar de "producto serio que parece juego"
Tokens reales: verde `#58CC02`, azul `#1CB0F6`, tinta `#000437`, radio **12px** en todo (links, botones, nav), display 64/700, cuerpo 17px/500, nav 15px/700, escala de espacio 8/12/16/24/32/40/48/64.

- **Técnica clave:** el botón con "repisa" — `box-shadow: 0 Npx 0` sin blur, y al `:active` el botón baja `translateY(Npx)` y la sombra se colapsa a 0. Se siente físico. Es la microinteracción más rentable que existe: dos líneas de CSS.
- **Segunda técnica:** borde de 2px en los botones incluso los rellenos, y CTA en mayúsculas.
- **Aplicable al mapa:** la repisa va en el botón "Ver en la fuente", en los chips y en el pin seleccionado. No animar `box-shadow` (es caro): animar `transform` y colapsar la sombra en el mismo tick.

### 2.2 Mailchimp (rebrand COLLINS) — playfulness sin infantilizar
Cooper Light como cara de marca + amarillo Cavendish + ilustración "surrealista, fuera de eje".

- **Técnica clave:** el sistema mantiene **tipografía, logo y paleta rígidos**, y toda la libertad se descarga en la ilustración. Por eso puede ser rarísimo sin verse desordenado.
- **Aplicable:** es exactamente nuestra regla. Los tokens de esta dirección son estrictos y aburridos a propósito; **la diversión vive en las mascotas y en el color de categoría, no en inventar componentes nuevos por página.**

### 2.3 Headspace (rebrand Italic Studio) — mascota con rango emocional
La cara naranja pasó de un smiley a un sistema de emociones (estrés, tristeza, calma). Paleta: `#FF7300`, `#FFA500`, `#FFCE00`, más acentos `#FFA1CC`, `#3B197F`, `#27455C`.

- **Técnica clave:** personajes sin aristas, formas curvas y libres, y **una misma cara con muchos estados** en vez de muchos personajes.
- **Aplicable directo:** las 6 mascotas ya existen; lo que falta son **poses**. Más barato y más memorable dibujar 4 poses de la Loica que un séptimo animal.

### 2.4 Neobrutalismo (lectura crítica: NN/g)
Definición técnica: borde sólido 2-3px, sombra dura desplazada ~4px sin blur, colores planos saturados, tipografía grande.

- **Las advertencias de NN/g que sí aplico:** limitar a 2-3 colores por pantalla, verificar contraste (amarillo/cian falla), tipografía rara **solo en titulares**, padding generoso de 24-32px.
- **Lo que rechazo del estilo puro:** bordes negros y esquinas rectas. En una paleta crema el negro puro se ve sucio y violento. **Uso Azul Cordillera como tinta y radios grandes.** El resultado es cartoon, no brutalismo — que es lo que pidió el fundador.
- Bonus: el estilo está de moda en 2026 justamente porque "no parece generado por IA". Eso también resuelve el pedido de que Nosotros no parezca escrita por una IA — el look ayuda.

### 2.5 Elementor (la referencia del fundador)
Miré el sitio. Honestamente: Elementor **no** es un sistema visual fuerte, es un constructor. Su sitio es neutro a propósito porque vende flexibilidad.

- **Qué se rescata, que es lo que el fundador realmente está viendo:** escala. Titulares enormes, imágenes grandes, secciones con mucho aire, movimiento al hacer scroll, y una promesa clara arriba de todo.
- **Traducción honesta del pedido:** cuando dice "impactante y moderno como Elementor", quiere decir **tamaño y confianza**, no ese estilo particular. Nuestra respuesta a "impactante" es tipografía gigante + color plano + mascotas grandes, no gradientes ni parallax.

### 2.6 Google Fonts 2026 — el campo tipográfico
Revisé qué se está usando: Hanken Grotesk y Plus Jakarta Sans son las "bouba grotesk" del momento (redondeadas pero técnicas); Fredoka y Baloo 2 siguen siendo las redondeadas con carácter. Ambas se sirven en el rango de pesos que necesitamos (Baloo 2 400-800, Fredoka 300-700).

- **Conclusión:** ver sección 5. Spoiler: no cambio las fuentes, cambio dónde se usan.

---

## 3. Paleta ampliada

Nueve rampas de 10 pasos. Las generé en **OKLCH** (no en HSL) interpolando desde un tinte casi blanco hasta una sombra profunda, manteniendo el tono e **inyectando los 6 colores de marca exactos** en el paso que les corresponde por luminosidad. Por eso las rampas se sienten parejas y los anclas siguen siendo los anclas:

| Ancla | Hex | Paso donde cae |
|---|---|---|
| Rojo Loica | `#E8442E` | `--rojo-500` |
| Amarillo Micro | `#F5B52E` | `--amarillo-300` |
| Verde Cerro | `#2E7D5B` | `--verde-700` |
| Rosado Atardecer | `#F2778C` | `--rosado-400` |
| Azul Cordillera | `#1E2A4A` | `--azul-900` |
| Crema Papel | `#FAF3E7` | `--arena-100` |

Ojo con esto porque es contraintuitivo y te va a morder si no lo tienes presente: **el Amarillo Micro es `--amarillo-300`, no el 500.** Es un color claro. El Verde Cerro es `--verde-700`. Confía en la rampa, no en el número redondo.

### 3.1 Tokens primitivos (pegar al inicio de `loica.css`)

```css
/* ============================================================
   LOICA — PRIMITIVOS
   Rampas OKLCH ancladas en los 6 colores de marca.
   NO usar estos tokens directo en componentes: usar los
   semánticos de 3.2. Estos son la despensa, no la receta.
   ============================================================ */
:root{
  /* Rojo Loica — acción, marca, selección. Ancla en 500. */
  --rojo-50:#FFF4F1;  --rojo-100:#FFE5DF; --rojo-200:#FFC9BE; --rojo-300:#FEA493;
  --rojo-400:#F47662; --rojo-500:#E8442E; --rojo-600:#D13B27; --rojo-700:#AA2C1B;
  --rojo-800:#801B0E; --rojo-900:#590B03;

  /* Amarillo Micro — destacados, foco, categoría Otros. Ancla en 300. */
  --amarillo-50:#FEF6E8;  --amarillo-100:#FDEACA; --amarillo-200:#FAD391;
  --amarillo-300:#F5B52E; --amarillo-400:#D89E1E; --amarillo-500:#BA8608;
  --amarillo-600:#9D7000; --amarillo-700:#7E5900; --amarillo-800:#5D4100;
  --amarillo-900:#3E2A00;

  /* Verde Cerro — gratis, éxito, aire libre. Ancla en 700. */
  --verde-50:#F1F9F5;  --verde-100:#E5F1EB; --verde-200:#CFE3D8; --verde-300:#B4D0C1;
  --verde-400:#93BBA6; --verde-500:#74A68D; --verde-600:#549274; --verde-700:#2E7D5B;
  --verde-800:#1C523B; --verde-900:#113626;

  /* Rosado Atardecer — celebración, familia, momentos. Ancla en 400. */
  --rosado-50:#FFF3F4;  --rosado-100:#FFE4E7; --rosado-200:#FFC8CE; --rosado-300:#FBA4B0;
  --rosado-400:#F2778C; --rosado-500:#D8687B; --rosado-600:#B75566; --rosado-700:#954150;
  --rosado-800:#712C39; --rosado-900:#4E1824;

  /* Azul Cordillera — tinta, contorno, superficies oscuras. Ancla en 900. */
  --azul-50:#F5F7FB;  --azul-100:#EAEDF3; --azul-200:#D6DAE4; --azul-300:#BEC3D0;
  --azul-400:#A1A8B9; --azul-500:#878FA4; --azul-600:#6D778F; --azul-700:#535E79;
  --azul-800:#384461; --azul-900:#1E2A4A;
  --azul-950:#141A2B; --azul-975:#0B0F1C;   /* extensiones para modo oscuro */

  /* Morado Culpeo — fiestas y noche */
  --morado-50:#F7F5FF;  --morado-100:#EDE8FF; --morado-200:#DAD2FB; --morado-300:#C3B5F2;
  --morado-400:#A893E7; --morado-500:#9072DB; --morado-600:#7A4FCF; --morado-700:#6A44B5;
  --morado-800:#4E3187; --morado-900:#331F5B;

  /* Lápis Chinchilla — cultura */
  --lapis-50:#F1F7FF;  --lapis-100:#E1EDFB; --lapis-200:#C7DAF1; --lapis-300:#A5C2E5;
  --lapis-400:#7DA5D5; --lapis-500:#578AC5; --lapis-600:#2F6FB5; --lapis-700:#2962A0;
  --lapis-800:#1C4777; --lapis-900:#102F50;

  /* Naranjo Chincol — clases y talleres */
  --naranjo-50:#FFF4EA;  --naranjo-100:#FDE7D4; --naranjo-200:#F6CFAB; --naranjo-300:#EDB175;
  --naranjo-400:#E08A1E; --naranjo-500:#CB7B14; --naranjo-600:#AB6604; --naranjo-700:#8A5100;
  --naranjo-800:#663A00; --naranjo-900:#452500;

  /* Arena — neutro CÁLIDO. Nunca uses gris frío en Loica. Ancla en 100. */
  --arena-50:#FFFBF5;  --arena-100:#FAF3E7; --arena-200:#EDE7DE; --arena-300:#DAD3C8;
  --arena-400:#BEB6A9; --arena-500:#A29A8C; --arena-600:#847C6E; --arena-700:#645D51;
  --arena-800:#454037; --arena-900:#292621;
}
```

### 3.2 Tokens semánticos + modo oscuro

```css
/* ---------- SEMÁNTICOS — CLARO ---------- */
:root{
  --fondo:var(--arena-100);
  --fondo-elevado:var(--arena-50);
  --fondo-hundido:var(--arena-200);

  --tinta:var(--azul-900);            /* 12,82:1 sobre crema */
  --tinta-suave:var(--azul-700);      /*  5,87:1 — AA */
  --tinta-tenue:var(--arena-700);     /*  5,90:1 — AA. Reemplaza al #8C93A8 roto */

  /* EL token de esta dirección. Todo lleva contorno de tinta. */
  --contorno:var(--azul-900);
  --contorno-suave:var(--azul-800);

  --acento:var(--rojo-500);           /* superficie/relleno decorativo */
  --acento-solido:var(--rojo-600);    /* SIEMPRE que lleve texto blanco encima */
  --acento-hover:var(--rojo-700);
  --acento-contraste:#FFFFFF;         /* 4,81:1 sobre --acento-solido */

  --gratis:var(--verde-700);
  --gratis-fondo:var(--verde-100);
  --gratis-contraste:#FFFFFF;         /* 5,00:1 */

  --destacado:var(--amarillo-300);
  --destacado-tinta:var(--azul-900);  /* 7,76:1 */

  --foco:var(--amarillo-300);
}

/* ---------- SEMÁNTICOS — OSCURO ----------
   La app se usa de noche en la calle: esto es primera clase, no un extra.
   Regla dura: en oscuro la TINTA SE INVIERTE. El contorno pasa de azul a
   crema. Si no, los contornos desaparecen (#454037 sobre el fondo da 1,44:1). */
@media (prefers-color-scheme: dark){
  :root:not([data-tema="claro"]){ /* ...mismos valores del bloque de abajo... */ }
}
:root[data-tema="oscuro"],
:root:not([data-tema="claro"]){
  --fondo:var(--azul-950);            /* #141A2B */
  --fondo-elevado:#1E2740;
  --fondo-hundido:var(--azul-975);

  --tinta:var(--arena-100);           /* 15,70:1 sobre el fondo */
  --tinta-suave:var(--arena-300);     /*  9,96:1 */
  --tinta-tenue:var(--arena-400);     /*  7,36:1 */

  --contorno:var(--arena-200);        /* 12,04:1 — el contorno se invierte */
  --contorno-suave:var(--arena-300);

  --acento:var(--rojo-400);
  --acento-solido:var(--rojo-400);
  --acento-hover:var(--rojo-300);
  --acento-contraste:var(--azul-900); /* 5,13:1 — tinta OSCURA sobre rojo claro */

  --gratis:var(--verde-300);          /* 10,50:1 como texto */
  --gratis-fondo:var(--verde-900);
  --gratis-contraste:var(--azul-900); /* 8,57:1 */

  --destacado:var(--amarillo-300);    /* 9,51:1 */
  --destacado-tinta:var(--azul-900);

  --foco:var(--amarillo-300);
}
```

> ⚠️ Al pegar el bloque oscuro, expande el `@media` con los mismos valores del selector `[data-tema="oscuro"]`. Está escrito colapsado acá para no repetir 20 líneas en el documento.

### 3.3 Colores de categoría (redefinidos)

```css
:root{
  --c-fiesta:var(--morado-600);     /* Culpeo */
  --c-musica:var(--rojo-600);       /* Cóndor */
  --c-cultura:var(--lapis-600);     /* Chinchilla */
  --c-clases:var(--naranjo-400);    /* Chincol */
  --c-libre:var(--verde-700);       /* Pudú */
  --c-otros:var(--amarillo-300);    /* Loica — CAMBIO, ver abajo */
}
/* Versiones claras para fondos de pastilla, con tinta azul encima */
:root{
  --c-fiesta-suave:var(--morado-200);   /* tinta 9,82:1 */
  --c-musica-suave:var(--rojo-200);     /* tinta 9,66:1 */
  --c-cultura-suave:var(--lapis-200);   /* tinta 9,92:1 */
  --c-clases-suave:var(--naranjo-200);
  --c-libre-suave:var(--verde-200);     /* tinta 10,52:1 */
  --c-otros-suave:var(--amarillo-200);  /* tinta 9,96:1 */
}
```

**El cambio que hay que discutir: `otros` deja de ser rojo y pasa a Amarillo Micro.**

Razones, en orden de peso:

1. **Datos.** 102 de 271 eventos (37,6%) son `otros`. Con el rojo actual, casi 4 de cada 10 pines usan el color que la marca reserva para "esto se toca". El rojo deja de significar algo.
2. **El rojo vuelve a su trabajo:** CTA, pin seleccionado, marca. Un solo significado.
3. **La metáfora de marca no se pierde.** El pecho rojo de la Loica está *dentro* del SVG y no cambia nunca. Sobre una gota amarilla se ve mejor que sobre una roja — hoy el pecho rojo desaparece contra su propio pin. Sigue siendo cierto que "el pecho rojo es el pin"; ahora además se ve.
4. **El amarillo antes no era usable como pin** (2,16:1 contra crema). Con contorno de tinta, sí. Es el primer dividendo concreto de la dirección.

**Pero además, y esto es más importante que el color:** que el 37,6% de tus eventos caiga en "Otros" es un problema de taxonomía, no de diseño. Ningún sistema de color salva un mapa donde la categoría más grande se llama "otros". Vale la pena revisar el clasificador del pipeline. El amarillo es el parche visual mientras tanto.

### 3.4 Tabla de contrastes de los pares críticos

Todos calculados, ninguno estimado. AA = 4,5:1 texto / 3:1 UI.

**Modo claro**

| Par | Contraste | |
|---|---|---|
| `--tinta` sobre `--fondo` | 12,82:1 | ✓ AAA |
| `--tinta-suave` sobre `--fondo` | 5,87:1 | ✓ AA |
| `--tinta-tenue` sobre `--fondo` | 5,90:1 | ✓ AA |
| Blanco sobre `--acento-solido` (botón) | 4,81:1 | ✓ AA |
| Blanco sobre `--acento-hover` | 6,81:1 | ✓ AA |
| Blanco sobre `--gratis` | 5,00:1 | ✓ AA |
| `--tinta` sobre `--destacado` | 7,76:1 | ✓ AA |
| `--tinta` sobre `--c-*-suave` (las 6) | 9,66 – 10,52:1 | ✓ AAA |
| Crema sobre `--tinta` (chip activo) | 12,82:1 | ✓ AAA |
| `--contorno` contra el mapa claro | 12,55:1 | ✓ |

**Modo oscuro**

| Par | Contraste | |
|---|---|---|
| `--tinta` sobre `--fondo` | 15,70:1 | ✓ AAA |
| `--tinta` sobre `--fondo-elevado` | 13,41:1 | ✓ AAA |
| `--tinta-suave` sobre `--fondo-elevado` | 9,96:1 | ✓ AAA |
| `--tinta-tenue` sobre `--fondo-elevado` | 7,36:1 | ✓ AAA |
| `--acento-contraste` sobre `--acento-solido` | 5,13:1 | ✓ AA |
| `--acento-contraste` sobre `--gratis` | 8,57:1 | ✓ AA |
| `--gratis` como texto sobre `--fondo` | 10,50:1 | ✓ AAA |
| `--destacado` sobre `--fondo` | 9,51:1 | ✓ AAA |
| `--contorno` contra `--fondo-elevado` | 12,04:1 | ✓ |
| `--contorno` contra el mapa oscuro | 12,40:1 | ✓ |

**Lo que NO pasa y por eso no está en el sistema.** Lo dejo escrito para que no reaparezca:

- Blanco sobre `#E8442E` (rojo-500): **3,96:1**. Nunca texto blanco sobre rojo-500. Usa `--acento-solido` (rojo-600).
- Blanco sobre morado-500: **3,74:1**. Por eso Culpeo usa morado-600.
- `#8C93A8` sobre cualquier fondo claro: **2,78-3,02:1**. Bórralo del archivo.
- Amarillo-300 solo, como anillo de foco sobre crema: **1,65:1**. Por eso el foco es de dos anillos (sección 7.6).
- Cualquier borde oscuro en modo oscuro (`#454037` → 1,44:1, `#3A4463` → 1,54:1). En oscuro el contorno se invierte a crema. Sin excepciones.

---

## 4. Lenguaje de forma

Qué hace que algo "se vea Loica". Cinco reglas. Si un componente cumple las cinco, es Loica; si le falta una, no lo es.

### 4.1 Contorno de tinta en todo lo que se toca

**Todo control y toda superficie flotante lleva contorno.** Color `--contorno`, nunca negro puro (`#000` sobre crema se ve sucio y agresivo; Azul Cordillera se ve dibujado).

| Elemento | Grosor |
|---|---|
| Chips, pastillas, campos de formulario | **2px** |
| Tarjetas, miniaturas, paneles | **2,5px** |
| Botón principal, pin del mapa, mascota grande | **3px** |

Nada de `1px`. Un contorno de 1px se lee como "borde de tabla"; a partir de 2px se lee como "dibujo".

### 4.2 Sombra dura desplazada, cero blur

```css
--repisa-1:0 3px 0 var(--contorno);   /* chips, pastillas */
--repisa-2:0 4px 0 var(--contorno);   /* tarjetas, botón secundario */
--repisa-3:0 5px 0 var(--contorno);   /* botón principal */
--repisa-4:0 6px 0 var(--contorno);   /* panel, ficha, modales */
```

Siempre hacia abajo, sin desplazamiento lateral (el offset diagonal del neobrutalismo puro se ve descuidado en una lista de datos; el vertical se lee como "botón físico"). **Cero blur** es innegociable: es lo que distingue "dibujo" de "material design".

**En modo oscuro la repisa casi no se ve** (negro sobre `#141A2B` da 1,21:1) y está bien: ahí el contorno crema es el que define la forma (12,04:1). La repisa pasa a ser decorativa. Para elementos de color en oscuro puedes usar una repisa del propio tono oscuro: bajo el botón `--rojo-400`, una repisa `--rojo-800` da 3,66:1 contra el botón — se lee como profundidad de verdad.

### 4.3 Radios grandes y consistentes

```css
--r-sm:10px;    /* campos, pastillas cuadradas */
--r-md:16px;    /* miniaturas, botones secundarios */
--r-lg:22px;    /* tarjetas */
--r-xl:28px;    /* paneles, hojas inferiores */
--r-2xl:36px;   /* bloques de marketing, hero */
--r-pill:999px; /* chips, botón principal, pastillas */
```

Nunca `0` ni `4px` en algo visible. **El radio es la mitad de la personalidad**: es lo que impide que "tinta gruesa + color plano" caiga en brutalismo áspero. Cartoon = redondo. Regla práctica: el radio interior de un elemento anidado = radio exterior − padding.

### 4.4 Ángulos: sí, pero acotados

Rotaciones sutiles de **−2° a +2°**, y solo en:

- Ilustraciones y mascotas grandes
- Tarjetas de blog y bloques de marketing (Nosotros, hero)
- Pastillas decorativas tipo "¡Gratis!"

**Nunca** en: filas de lista, texto de datos, chips de filtro, pines, la ficha del evento. Máximo **dos elementos rotados por pantalla**. Un solo elemento fuera de eje se lee como intención; cuatro se leen como error de CSS.

### 4.5 Color plano, siempre

Cero degradados en superficies. Cero `backdrop-filter`. Cero sombras difusas. Si necesitas jerarquía, la das con **contorno + repisa + color**, que es como funciona una serigrafía: capas de tinta plana.

Única excepción permitida: un degradado en la ilustración del cielo del hero (Rosado Atardecer → Amarillo Micro), que es una imagen, no una superficie de UI.

### 4.6 Por qué esta dirección y no otra

Voy a defenderla porque el brief pide una decisión, no un menú.

- **Contra "sombras suaves modernas" (el estilo actual):** ya lo tenemos y es exactamente lo que el fundador llama "correcto pero olvidable". Además las sombras difusas dependen del fondo; sobre un mapa que cambia de color no dan separación garantizada.
- **Contra glassmorphism:** `backdrop-filter` sobre un canvas WebGL en movimiento tira el framerate en Android de gama media, y el contraste del texto pasa a depender de qué tesela quedó debajo — impredecible por definición.
- **Contra neobrutalismo puro (negro, esquinas rectas):** se ve frío, europeo y agresivo. Loica es cálida y chilena.
- **A favor:** (a) es el arreglo de accesibilidad de la sección 1, (b) coincide con la inspiración ya declarada en `estrategia_marca.md` — "afiches de Larrea, la lota tipográfica de las ferias, los colores de los quioscos" es literalmente serigrafía de tinta plana con contorno, (c) es más barato de renderizar: hoy `index.html:23` aplica `filter: drop-shadow()` a hasta 229 marcadores DOM sobre el mapa; un `stroke` en el SVG cuesta una fracción de eso.

---

## 5. Tipografía

### 5.1 La decisión: no cambio las fuentes, cambio dónde se usan

Baloo 2 + Manrope son buenas. **El problema no es la elección, es la distribución.** Hoy la fuente de marca aparece en `h1,h2,h3` y en `.conteo b`, y nada más. En la pantalla del mapa —que es *la* pantalla del producto— casi todo lo que ves es Manrope: el título de la tarjeta, el precio, los chips, el botón. La voz de la marca no está donde el usuario mira.

Cambiar a Fredoka costaría una carga de fuente nueva y resolvería un 10% del problema. Redistribuir cuesta cero y resuelve el 90%.

**La regla, y es una sola frase:**

> **Baloo 2 para lo que se toca y lo que grita. Manrope para lo que se lee como dato.**

| Baloo 2 (800) | Manrope |
|---|---|
| `h1`, `h2`, `h3` | Título de la tarjeta de evento |
| Texto de botones | Precio, hora, dirección, comuna |
| Texto de chips de filtro | Descripción, texto corrido |
| El contador ("43 eventos") | Etiquetas de formulario y ayudas |
| Badge de día ("HOY", "MAÑANA") | Pie de fuente, metadatos |
| Estados vacíos y globos de la Loica | Todo lo que sea número comparable |

Por qué el precio y la hora se quedan en Manrope: son números que se comparan entre filas, necesitan `font-variant-numeric: tabular-nums` y máxima legibilidad a 13px. Una redondeada gruesa a 13px con números tabulares se empasta. **El dato es sagrado** — eso ya está en la estrategia de marca y sigue mandando.

Por qué los botones y chips sí cambian a Baloo 2: son palabras cortas ("Gratis", "Hoy", "Música", "Ver en la fuente"), en tamaños de 14-17px, donde la redondeada se luce y **es lo que más se toca**. Es el mayor cambio de percepción por el menor riesgo.

### 5.2 Escala completa

Amplío hacia arriba porque "impactante" en el sentido de Elementor = titulares grandes.

```css
:root{
  --fuente-marca:"Baloo 2","Nunito",system-ui,sans-serif;
  --fuente-ui:"Manrope",-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;

  --t-xs:12px;    /* metadatos, pie de fuente */
  --t-sm:13px;    /* precio, hora, meta de tarjeta */
  --t-base:15px;  /* cuerpo */
  --t-md:17px;    /* título de tarjeta, botón */
  --t-lg:21px;    /* h3, contador */
  --t-xl:27px;    /* h2 */
  --t-2xl:35px;   /* h1 de página interior */
  --t-3xl:46px;   /* h1 de mapa/hero móvil */
  --t-4xl:60px;   /* hero escritorio */
  --t-5xl:78px;   /* hero de marketing, cifras gigantes */
}
```

Reglas de composición:

```css
h1,h2,h3,.display{
  font-family:var(--fuente-marca);
  font-weight:800;
  letter-spacing:-.02em;   /* Baloo 2 en 800 abre mucho: apretar */
  line-height:1.08;        /* en --t-3xl y arriba */
  margin:0;
}
h1{font-size:var(--t-2xl);line-height:1.1}
h2{font-size:var(--t-xl);line-height:1.15}
h3{font-size:var(--t-lg);line-height:1.2}

/* Titulares gigantes: apretar más y quitar el interlineado de párrafo */
.display-xl{font-size:var(--t-4xl);letter-spacing:-.035em;line-height:1}
@media(min-width:880px){ .display-xl{font-size:var(--t-5xl)} }

/* Cualquier número que se compare entre filas */
.precio,.hora,.conteo b,.dato time{
  font-family:var(--fuente-ui);
  font-variant-numeric:tabular-nums;
  font-feature-settings:"tnum" 1;
}
```

Y la carga de fuentes en el `<head>` de cada página — un peso menos que hoy en Manrope (400 no se usa en ningún lado donde importe) y el rango completo de Baloo 2:

```html
<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700;800&family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
```

---

## 6. Cómo se usan las mascotas

Acá está el corazón del pedido del fundador, y es donde el código de hoy queda más corto.

### 6.1 El diagnóstico

`MASCOTAS` en `loica.js` dibuja seis animales en un viewBox de 24 con detalles de `r=".4"`. A los 19px del chip eso es **0,32px** — no existe. Las mascotas están dibujadas para verse a 100px y se usan a 19-34px. Por eso la app no se siente caricaturesca.

### 6.2 Sistema de dos niveles

Hay que separar en dos funciones distintas. Una sola no puede servir a 19px y a 200px.

```js
// carita(nombre, color)  -> viewBox 24, SOLO cabeza. Para <= 32px.
// mascota(nombre, color) -> viewBox 48, cuerpo entero. Para >= 40px.
```

**Reglas de dibujo de `carita()`** (viewBox 24, y esto no es negociable si quieres que se lea):

| Rasgo | Regla | Hoy |
|---|---|---|
| Cabeza | ≥ 70% del alto del viewBox | ~50% |
| Ojo (radio) | **≥ 1,6 unidades** (→ ≥1,3px a 20px) | 0,4 |
| Brillo del ojo | ≥ 0,6 unidades, o se omite | 0,4 |
| Contorno de tinta | `stroke-width:1.6`, `stroke:currentColor` heredado de `--contorno` | no hay |
| Rellenos | máximo 3 planos + la tinta | 5-7 |
| Detalles finos | **eliminados** (bigotes, plumas sueltas, patas) | presentes |

Y una regla que resume todo: **si un rasgo mide menos de 1/15 del viewBox, no va en `carita()`.**

**`mascota()`** (viewBox 48) sí lleva cuerpo, patas, cola y los detalles finos. Ahí el `r=".4"` original escalado a 48 se ve perfecto.

### 6.3 Escala de tamaños

| Tamaño | Función | Dónde |
|---|---|---|
| **22px** | `carita()` | Chip de filtro, nav inferior, etiqueta de categoría |
| **28px** | `carita()` | Dentro del pin del mapa |
| **44px** | `carita()` | Miniatura de la tarjeta cuando no hay foto |
| **72px** | `mascota()` | Estados vacíos, error de carga |
| **120px** | `mascota()` | Onboarding, encabezado de sección, tarjeta de blog |
| **200px+** | `mascota()` | Hero de Nosotros, ilustración de portada |

Subir el chip de 19 → 22px y la miniatura de 34 → 44px ya cambia la sensación de la app **antes** de redibujar nada.

### 6.4 Poses

Cuatro poses de la Loica, dos del resto. Es la lección de Headspace: más estados de un personaje rinde más que más personajes.

| Pose | Cuándo aparece |
|---|---|
| **Posada** (neutra) | Reposo. Es la de defecto |
| **Volando** (alas extendidas) | Transiciones, carga, la loica del mapa |
| **Celebrando** (alas arriba) | Filtro que arroja muchos resultados, evento gratis, envío de formulario |
| **Durmiendo** (ojos `^ ^`, cabeza gacha) | Estado vacío: "no hay eventos con esos filtros" |

Culpeo, Pudú, Chincol, Cóndor y Chinchilla: **posada** y **celebrando**, nada más. Y se mantiene la regla de la estrategia de marca: **solo la Loica habla.** Los demás son señalética con cara.

### 6.5 Presencia por página

Hoy las mascotas solo son íconos. Que tengan presencia significa aparecer grandes en algún lugar de cada pantalla:

- **Mapa:** la Loica volando (sección 6.6) + caritas en pines y chips.
- **Calendario:** la mascota dominante del mes a 120px, atrás y al 12% de opacidad, detrás de la grilla.
- **Agrega tu evento:** el Chincol a 120px al lado del formulario; cambia a "celebrando" al enviar.
- **Nosotros:** las seis a 200px, en fila, con su nombre y su función. Es la página donde el mascotario se explica. También es lo que hace que no parezca escrita por una IA: nadie le pide a una IA que dibuje un chincol.
- **Estados vacíos:** siempre 72px, siempre con pose acorde.

### 6.6 "La loica volando por el mapa"

El fundador lo pidió textual. Definido para que no termine siendo un adorno que estorba.

**Concepto: la Loica es una guía, no un adorno.** Nunca vuela porque sí. Vuela cuando tiene algo que decirte, y **siempre llega antes que el mapa** — va adelante de la cámara, como quien te dice "por acá".

**Los cuatro únicos disparadores:**

1. **Primera visita.** Entra volando desde fuera de pantalla, se posa en el tirador del panel y dice el saludo de onboarding ("Soy la Loica. ¿Qué te tinca hoy?"). Se queda posada 4s y se va.
2. **Al filtrar.** Vuela desde el chip que tocaste hasta el contador y "suelta" el número nuevo, que hace pop. ~400ms. Es lo que hace que filtrar se sienta un juego.
3. **Al abrir una ficha.** El mapa hace `flyTo` (~900ms). La Loica sale disparada hacia el pin destino y llega a los 600ms, antes que la cámara. Guía el ojo hacia dónde vas.
4. **Estado vacío.** Aparece posada y durmiendo sobre el texto. No vuela.

**Cómo se implementa** — con `offset-path`, sin JS de física:

```css
#loica-vuelo{
  position:absolute; top:0; left:0;
  width:56px; height:56px;
  z-index:5;                 /* sobre el mapa, bajo el panel */
  pointer-events:none;       /* JAMÁS bloquea un toque */
  opacity:0;
  offset-rotate:auto;        /* se inclina hacia donde va */
  offset-distance:0%;
  will-change:offset-distance,opacity;
}
#loica-vuelo.vuela{
  animation:loica-vuela var(--dur-vuelo,700ms) cubic-bezier(.3,0,.25,1) forwards;
}
@keyframes loica-vuela{
  0%   {opacity:0;  offset-distance:0%}
  12%  {opacity:1}
  88%  {opacity:1}
  100% {opacity:0;  offset-distance:100%}
}

/* Aleteo: dos grupos en el SVG que se alternan. steps(1) = corte seco,
   que es lo que hace que se lea dibujado y no interpolado. */
.ala-arriba,.ala-abajo{animation:aletear .18s steps(1) infinite}
.ala-abajo{animation-delay:.09s}
@keyframes aletear{0%,49%{opacity:1}50%,100%{opacity:0}}
```

Y en JS la trayectoria se arma con la curva entre dos puntos de pantalla, **siempre arqueando hacia arriba** para que no pase por encima de otros pines:

```js
function volarLoica(desde, hasta, ms = 700){
  if(matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const el = document.getElementById("loica-vuelo");
  const cx = (desde.x + hasta.x) / 2;
  const cy = Math.min(desde.y, hasta.y) - 90;   // el arco sube: esquiva pines
  el.style.offsetPath = `path("M ${desde.x} ${desde.y} Q ${cx} ${cy} ${hasta.x} ${hasta.y}")`;
  el.style.setProperty("--dur-vuelo", ms + "ms");
  el.classList.remove("vuela");
  void el.offsetWidth;                          // reinicia la animación
  el.classList.add("vuela");
}
```

**Las reglas que la salvan de ser molesta.** Sin esto, a la tercera vez el usuario la odia:

- Nunca más de **una** Loica en pantalla. Un vuelo nuevo cancela el anterior.
- `pointer-events:none` siempre. No puede robarse un toque.
- No aparece si el usuario movió el mapa en los últimos 400ms (está explorando, no la molestes).
- El vuelo del onboarding ocurre **una vez** — se guarda en `localStorage`.
- El arco siempre sube: no pasa por encima de los pines.
- Con `prefers-reduced-motion`, **no vuela**: aparece posada en el destino, sin animación. La función retorna temprano (arriba en el código).
- Nunca tapa un dato: `z-index:5`, siempre bajo el panel y bajo la ficha.

---

## 7. Componentes rediseñados

CSS real. Reemplaza las secciones equivalentes de `loica.css`.

### 7.1 Chip de filtro

Además del look, arregla el área táctil (30px → 44px) y sube la carita de 19 a 22px.

```css
.filtros{
  display:flex; gap:var(--e-2); overflow-x:auto;
  padding:var(--e-3) var(--e-4) calc(var(--e-3) + 4px);  /* +4 para la repisa */
  scrollbar-width:none; background:var(--fondo-elevado);
  border-bottom:2.5px solid var(--contorno);
}
.filtros::-webkit-scrollbar{display:none}

.chip{
  flex:none; display:inline-flex; align-items:center; gap:7px;
  min-height:44px;                        /* era 30px */
  padding:0 16px 0 10px;
  border:2px solid var(--contorno);
  border-radius:var(--r-pill);
  background:var(--fondo-elevado);
  color:var(--tinta);
  font:700 var(--t-md)/1 var(--fuente-marca);   /* Baloo 2: lo que se toca */
  box-shadow:var(--repisa-1);
  cursor:pointer; white-space:nowrap;
  transition:transform var(--rapido), box-shadow var(--rapido),
             background-color var(--rapido);
}
.chip svg{width:22px; height:22px; flex:none}   /* era 19px */

.chip:hover{ transform:translateY(-1px); box-shadow:0 4px 0 var(--contorno) }
.chip:active{ transform:translateY(3px); box-shadow:0 0 0 var(--contorno) }

/* Activo: se hunde y queda pintado. Se ve "apretado", no solo "distinto". */
.chip[aria-pressed="true"]{
  background:var(--tinta); color:var(--fondo-elevado);
  transform:translateY(3px); box-shadow:0 0 0 var(--contorno);
}
.chip.es-gratis[aria-pressed="true"]{
  background:var(--gratis); color:var(--gratis-contraste);
}

/* Filtros por edad: MISMO color, OTRA forma.
   La forma codifica la dimensión del filtro; el color codifica la categoría.
   Así se agregan niños/adolescentes sin inflar la paleta. */
.chip.edad{ border-radius:var(--r-sm) }
```

Ese último bloque es la respuesta al pedido de "filtros por edades": **no inventes colores nuevos, inventa una forma nueva.** La paleta ya tiene seis categorías; una séptima y octava familia de color haría el mapa ilegible. Chips redondos = "qué y cuándo". Chips de esquina cuadrada = "para quién". El usuario lo aprende en un uso.

### 7.2 Tarjeta de evento

Dos variantes, y esto es una decisión de fondo: **la lista NO se convierte en tarjetas flotantes.** Con 271 eventos, convertir cada fila en una tarjeta con contorno y repisa mata la densidad y obliga a scrollear el triple. El error clásico de "hacerlo más divertido".

La fila se queda fila y gana identidad por el **lomo de color** y por la miniatura contorneada. Las tarjetas flotantes se reservan para calendario, blog y destacados.

```css
/* --- Variante A: FILA (lista del mapa). Densidad primero. --- */
.tarjeta{
  display:grid; grid-template-columns:56px 1fr auto;
  gap:var(--e-3); align-items:start;
  padding:var(--e-3) var(--e-4) var(--e-3) calc(var(--e-4) - 6px);
  background:var(--fondo-elevado);
  border:0; border-bottom:2px solid var(--fondo-hundido);
  border-left:6px solid var(--tono-cat, var(--c-otros));  /* EL LOMO */
  cursor:pointer; text-align:left; width:100%;
  font-family:inherit; color:inherit;
  transition:background-color var(--rapido), border-left-width var(--rapido);
}
.tarjeta:hover{ background:var(--fondo-hundido); border-left-width:10px }
.tarjeta:active{ background:var(--fondo-hundido) }
.tarjeta-gratis{ border-left-color:var(--gratis) }

/* Miniatura: cuadrado contorneado. Con foto o con carita, siempre el mismo bulto. */
.miniatura{
  width:56px; height:56px; border-radius:var(--r-md);
  border:2.5px solid var(--contorno);
  background:var(--c-suave, var(--fondo-hundido));
  overflow:hidden; display:grid; place-items:center;
  position:relative; box-shadow:var(--repisa-1);
}
.miniatura img{width:100%;height:100%;object-fit:cover;position:absolute;inset:0}
.miniatura > svg{width:44px;height:44px}         /* era 34px */

/* Badge de día: pastilla contorneada, encima y afuera. Se lee siempre. */
.miniatura .dia{
  position:absolute; inset:auto -4px -4px auto;
  background:var(--tinta); color:var(--fondo-elevado);
  font:800 10px/1 var(--fuente-marca);
  padding:4px 6px; border-radius:var(--r-pill);
  border:2px solid var(--contorno); letter-spacing:.02em;
}
.miniatura .dia.pronto{ background:var(--acento-solido); color:#fff }

.tarjeta h3{
  font-family:var(--fuente-ui);          /* dato denso: Manrope se queda */
  font-size:var(--t-md); font-weight:700; line-height:1.24;
  letter-spacing:-.01em; margin:3px 0 4px;
  display:-webkit-box; -webkit-line-clamp:2;
  -webkit-box-orient:vertical; overflow:hidden;
}
.precio{
  font:800 var(--t-sm)/1 var(--fuente-ui);
  font-variant-numeric:tabular-nums;
  color:var(--tinta); white-space:nowrap; text-align:right; padding-top:2px;
}
.precio.libre{
  color:var(--gratis-contraste); background:var(--gratis);
  padding:5px 9px; border-radius:var(--r-pill);
  border:2px solid var(--contorno);
}
.precio.sin-dato{ color:var(--tinta-tenue); font-weight:600 }

/* --- Variante B: TARJETA FLOTANTE (calendario, blog, destacados) --- */
.tarjeta-flotante{
  background:var(--fondo-elevado);
  border:2.5px solid var(--contorno);
  border-radius:var(--r-lg);
  box-shadow:var(--repisa-2);
  padding:var(--e-4);
  transition:transform var(--rapido), box-shadow var(--rapido);
}
.tarjeta-flotante:hover{ transform:translateY(-2px); box-shadow:0 6px 0 var(--contorno) }
.tarjeta-flotante:active{ transform:translateY(4px); box-shadow:0 0 0 var(--contorno) }
/* Solo en blog/marketing, nunca en listas de datos */
.tarjeta-flotante.torcida:nth-child(odd){ transform:rotate(-1.2deg) }
.tarjeta-flotante.torcida:nth-child(even){ transform:rotate(1deg) }
```

`--tono-cat` y `--c-suave` se setean por evento desde JS, igual que hoy se hace con `--tono` en el pin.

### 7.3 Pin del mapa

El cambio más importante del documento. Elimina el `filter: drop-shadow()` (caro, hasta 229 marcadores) y lo reemplaza por una segunda gota desplazada dentro del SVG: la repisa dura, gratis.

```css
.pin{
  width:38px; height:46px; cursor:pointer;
  transition:transform var(--rapido);
  /* SIN filter: drop-shadow. La repisa va dentro del SVG. */
}
.pin .gota{ fill:var(--tono); stroke:var(--contorno); stroke-width:2.5 }
.pin .repisa{ fill:var(--contorno) }
.pin .casco{ fill:var(--arena-50) }            /* el disco claro tras la carita */
.pin.gratis .gota{ fill:var(--gratis) }

.pin:hover{ transform:scale(1.12) translateY(-2px); z-index:9 }
.pin.activo{ transform:scale(1.28) translateY(-4px); z-index:10 }
.pin.activo .gota{ stroke:var(--acento-solido); stroke-width:3.5 }
```

```html
<!-- El SVG. La <path class="repisa"> es la MISMA gota, 3px más abajo. -->
<svg viewBox="0 0 38 46" width="38" height="46">
  <path class="repisa" transform="translate(0,3)"
        d="M19 1.5C10.4 1.5 3.5 8.4 3.5 17c0 10.9 13.1 24 14.6 25.4a1.3 1.3 0 0 0 1.8 0C21.4 41 34.5 27.9 34.5 17 34.5 8.4 27.6 1.5 19 1.5z"/>
  <path class="gota"
        d="M19 1.5C10.4 1.5 3.5 8.4 3.5 17c0 10.9 13.1 24 14.6 25.4a1.3 1.3 0 0 0 1.8 0C21.4 41 34.5 27.9 34.5 17 34.5 8.4 27.6 1.5 19 1.5z"/>
  <circle class="casco" cx="19" cy="16.8" r="11.2"/>
  <g transform="translate(5,2.8)"><!-- carita(nombre) a 28px --></g>
</svg>
```

Por qué el casco crema se queda: garantiza que la carita se lea sobre cualquier relleno de gota, en cualquier modo. Es la misma lógica del contorno, un nivel más adentro.

### 7.4 Botón principal

El botón Duolingo, con el rojo corregido a `--acento-solido` (4,81:1 en vez de los 3,96:1 rotos de hoy).

```css
.boton{
  display:inline-flex; align-items:center; justify-content:center; gap:var(--e-2);
  min-height:52px; padding:0 var(--e-6);
  background:var(--acento-solido); color:var(--acento-contraste);
  border:2.5px solid var(--contorno); border-radius:var(--r-pill);
  font:800 var(--t-md)/1 var(--fuente-marca);     /* Baloo 2 */
  letter-spacing:.01em; cursor:pointer; text-decoration:none;
  box-shadow:var(--repisa-3);
  /* Solo transform: animar box-shadow cuesta caro. La sombra se colapsa
     en el mismo tick, no se interpola. */
  transition:transform var(--rapido), box-shadow var(--rapido), background-color var(--rapido);
}
.boton:hover{ background:var(--acento-hover); transform:translateY(-1px);
              box-shadow:0 6px 0 var(--contorno) }
.boton:active{ transform:translateY(5px); box-shadow:0 0 0 var(--contorno) }

.boton.secundario{
  background:var(--fondo-elevado); color:var(--tinta);
  box-shadow:var(--repisa-2);
}
.boton.secundario:active{ transform:translateY(4px); box-shadow:0 0 0 var(--contorno) }
.boton.bloque{ width:100%; }
```

### 7.5 Panel inferior y ficha

```css
.panel-lista, .ficha{
  background:var(--fondo-elevado);
  border:2.5px solid var(--contorno);
  border-bottom:0;
  border-radius:var(--r-xl) var(--r-xl) 0 0;
  /* Sombra hacia ARRIBA: separa del mapa sin blur */
  box-shadow:0 -4px 0 var(--contorno);
}

/* Cinta de marca: el borde superior lleva los colores de la Loica.
   Responde directo al pedido de "que la navegación muestre los colores". */
.panel-lista::before, .barra::after{
  content:""; display:block; height:5px;
  background:linear-gradient(90deg,
    var(--c-musica) 0 20%, var(--c-clases) 20% 40%, var(--c-libre) 40% 60%,
    var(--c-cultura) 60% 80%, var(--c-fiesta) 80% 100%);
}
.panel-lista::before{ border-radius:var(--r-xl) var(--r-xl) 0 0; margin:-2.5px -2.5px 0 }

/* Tirador: pastilla gruesa contorneada, no una rayita gris */
.tirador{ padding:11px var(--e-4) 8px; cursor:grab; flex:none; touch-action:none }
.barra-tirador{
  width:52px; height:7px; margin:0 auto;
  background:var(--tinta); border-radius:var(--r-pill);
}

/* Contador: la cifra en Baloo 2 grande. Es el "score" de la pantalla. */
.conteo{ display:flex; align-items:baseline; gap:8px;
  font:600 var(--t-sm)/1 var(--fuente-ui); color:var(--tinta-suave);
  padding:0 var(--e-4) var(--e-2) }
.conteo b{ font-family:var(--fuente-marca); font-weight:800;
  font-size:var(--t-2xl); color:var(--tinta); font-variant-numeric:tabular-nums }

/* Botón cerrar de la ficha: pastilla contorneada, 44px reales */
.cerrar{
  position:absolute; top:12px; right:12px;
  width:44px; height:44px; border-radius:50%;
  background:var(--fondo-elevado); color:var(--tinta);
  border:2.5px solid var(--contorno); box-shadow:var(--repisa-1);
  font-size:20px; line-height:1; cursor:pointer; z-index:2;
}
.cerrar:active{ transform:translateY(3px); box-shadow:0 0 0 var(--contorno) }
```

### 7.6 Navegación (el pedido explícito del fundador)

Cada destino tiene su color. Es el cambio que más "muestra los colores de la Loica" por el menor esfuerzo.

```css
.barra{
  display:flex; align-items:center; gap:var(--e-3);
  padding:var(--e-3) var(--e-4);
  background:var(--fondo-elevado);
  border-bottom:2.5px solid var(--contorno);
  position:relative;
}
.nav a{
  display:inline-flex; align-items:center; min-height:44px;  /* era 27px */
  padding:0 var(--e-4); border-radius:var(--r-pill);
  font:700 var(--t-base)/1 var(--fuente-marca); color:var(--tinta-suave);
  text-decoration:none; white-space:nowrap; transition:var(--rapido);
}
.nav a:hover{ background:var(--fondo-hundido); color:var(--tinta) }
.nav a[aria-current="page"]{
  background:var(--nav-color, var(--tinta));
  color:var(--nav-tinta, var(--arena-50));   /* ver la nota de contraste abajo */
  border:2px solid var(--contorno); box-shadow:var(--repisa-1);
}

/* Nav inferior: la pastilla de color viaja con la página activa */
@media(max-width:879px){
  .nav-inferior{
    display:flex; position:fixed; inset:auto 0 0 0; z-index:20;
    background:var(--fondo-elevado);
    border-top:2.5px solid var(--contorno);
    padding-bottom:env(safe-area-inset-bottom);
  }
  .nav-inferior a{
    flex:1; display:flex; flex-direction:column; align-items:center; gap:3px;
    padding:8px 4px 7px; min-height:56px; justify-content:center;
    text-decoration:none; color:var(--tinta-tenue);
    font:700 10.5px/1 var(--fuente-marca);
  }
  .nav-inferior a svg{ width:24px; height:24px }
  .nav-inferior a[aria-current="page"]{ color:var(--tinta) }
  /* La pastilla de color tras el ícono: ESTO es "los colores de la loica" */
  .nav-inferior a[aria-current="page"] svg{
    background:var(--nav-color); border:2px solid var(--contorno);
    border-radius:var(--r-pill); padding:4px 14px;
    width:auto; height:26px; box-sizing:content-box;
  }
}

/* Un color por destino. OJO: cada color viaja con su tinta.
   El naranjo es claro — texto crema encima da 2,60:1 y FALLA. Lleva tinta oscura. */
[data-pagina="mapa"]       { --nav-color:var(--c-musica);  --nav-tinta:var(--arena-50) } /* 4,67:1 */
[data-pagina="calendario"] { --nav-color:var(--c-cultura); --nav-tinta:var(--arena-50) } /* 5,01:1 */
[data-pagina="agregar"]    { --nav-color:var(--c-clases);  --nav-tinta:var(--azul-900) } /* 5,27:1 */
[data-pagina="nosotros"]   { --nav-color:var(--c-libre);   --nav-tinta:var(--arena-50) } /* 4,85:1 */
```

**Regla general para cualquier pastilla de color** (nav, badge, chip activo), porque este error se repite solo: los seis colores de categoría **no** aceptan el mismo color de texto. Los oscuros llevan crema, los claros llevan tinta.

| Fondo | Texto | Contraste |
|---|---|---|
| `--c-musica` (rojo-600) | crema | 4,67:1 ✓ |
| `--c-cultura` (lapis-600) | crema | 5,01:1 ✓ |
| `--c-libre` (verde-700) | crema | 4,85:1 ✓ |
| `--c-fiesta` (morado-600) | crema | 5,30:1 ✓ |
| `--c-clases` (naranjo-400) | crema | **2,60:1 ✗** → usa tinta: **5,27:1 ✓** |
| `--c-otros` (amarillo-300) | crema | **1,77:1 ✗** → usa tinta: **7,76:1 ✓** |

### 7.7 Foco (accesibilidad, y no es opcional)

Amarillo solo sobre crema da 1,65:1 — falla. Por eso el anillo es **doble**: amarillo adentro, tinta afuera. El anillo de tinta contra el fondo da 12,82:1 en claro y 12,04:1 en oscuro, así que **siempre** hay un anillo que se ve, en cualquier modo y sobre cualquier fondo — incluido el mapa.

```css
:focus-visible{
  outline:none;
  box-shadow:0 0 0 3px var(--foco), 0 0 0 6px var(--contorno);
  border-radius:inherit;
}
/* En elementos con repisa, el foco la reemplaza para que no se sumen */
.boton:focus-visible, .chip:focus-visible{
  box-shadow:0 0 0 3px var(--foco), 0 0 0 6px var(--contorno);
}
```

---

## 8. Movimiento

### 8.1 Tokens

```css
:root{
  --rapido:.12s cubic-bezier(.4,0,.2,1);        /* presión, hover, chips */
  --medio:.22s cubic-bezier(.2,0,0,1);          /* paneles, hojas, ficha */
  --lento:.4s  cubic-bezier(.2,0,0,1);          /* entradas de página */
  --rebote:.34s cubic-bezier(.34,1.56,.64,1);   /* el sobreimpulso cartoon */
}
```

`--rebote` sobrepasa y vuelve. Es lo que hace que algo se sienta "de juguete". Se usa **solo en apariciones**, nunca en desapariciones (una salida con rebote se lee como bug).

### 8.2 Qué se anima

| Elemento | Qué | Duración | Curva |
|---|---|---|---|
| Botón / chip al presionar | `transform: translateY` + colapso de repisa | `--rapido` | estándar |
| Chip al activarse | color de fondo | `--rapido` | estándar |
| Pin al aparecer | `scale 0 → 1` | `--rebote` | rebote |
| Pin seleccionado | `scale 1 → 1.28` | `--rapido` | estándar |
| Panel inferior | `height` | `--medio` | salida suave |
| Ficha del evento | `transform: translateY` | `--medio` | salida suave |
| Contador al cambiar | `scale 1 → 1.15 → 1` | `--rebote` | rebote |
| Loica volando | `offset-distance` | 400-900ms | ver 6.6 |
| Mascota al celebrar | rotación ±6° | `--rebote` | rebote |

### 8.3 Qué NO se anima, nunca

- **Nada mientras la lista scrollea.** Ni un `transition` activo sobre una fila.
- **La posición de los pines.** Los pines se reposicionan con el mapa: animarlos produce desincronización visible.
- **El color de un dato.** El precio nunca hace fade entre colores.
- **Reflujo de texto.** Nada que mueva la línea base de un título.
- **`box-shadow` interpolado.** Es caro. Se colapsa en el mismo tick que el `transform`.
- **Nada de `filter` ni `backdrop-filter` sobre el mapa.**

### 8.4 La regla del stagger

Aparecer 229 pines escalonados es un desastre de rendimiento y de percepción. Regla:

> Escalona solo los **primeros 12** elementos, con **20ms** entre uno y otro. Total máximo **240ms**. Del 13 en adelante, aparecen todos juntos.

```css
.pin{ animation:pin-entra var(--rebote) backwards }
.pin:nth-child(-n+12){ animation-delay:calc((var(--i,0)) * 20ms) }
@keyframes pin-entra{ from{transform:scale(0)} to{transform:scale(1)} }
```

### 8.5 `prefers-reduced-motion` — la regla explícita

La regla actual (`*{transition:none!important;animation:none!important}`) es un martillazo que además rompe cosas: mata el `transition` de `height` del panel y deja el arrastre a saltos.

La correcta preserva la orientación pero elimina el movimiento gratuito:

```css
@media (prefers-reduced-motion: reduce){
  /* 1. Fuera todo lo decorativo */
  *,*::before,*::after{
    animation-duration:.01ms !important;
    animation-iteration-count:1 !important;
    transition-duration:.01ms !important;
    scroll-behavior:auto !important;
  }
  /* 2. Los cambios de opacidad SÍ se conservan: orientan sin mover */
  .ficha,.panel-lista,.aviso{ transition:opacity .15s linear !important }
  /* 3. La ficha aparece, no sube */
  .ficha{ transform:none !important }
  .ficha:not(.visible){ opacity:0; pointer-events:none }
  .ficha.visible{ opacity:1 }
  /* 4. La Loica no vuela: aparece posada (además volarLoica() sale temprano) */
  #loica-vuelo{ animation:none !important; offset-distance:100% !important }
  /* 5. Nada de aleteo */
  .ala-arriba,.ala-abajo{ animation:none !important }
  .ala-abajo{ opacity:0 }
  /* 6. La presión conserva el feedback: es información, no adorno */
  .boton:active,.chip:active{ transition:none; transform:translateY(4px) }
}
```

Además, en el mapa: `mapa.flyTo({..., essential: false})` para que MapLibre respete la preferencia, o cambiar a `jumpTo()` cuando la media query da true.

---

## 9. Qué NO hacer

Los errores típicos de "hagámoslo más divertido" que arruinarían un mapa que se usa en la calle, de noche, con una mano, con 20% de batería.

1. **No bajes el contraste para que "se vea suave".** Ya pasó: `--tinta-tenue` está en 2,78:1 y se usa para la dirección aproximada y el pie de fuente. Piso duro: 4,5:1 para texto, 3:1 para UI. Sin excepciones "porque se ve mejor".

2. **No degradados en superficies de UI.** Al sol se lavan, en OLED de noche hacen bandas, y el texto encima tiene contraste variable según dónde caiga. Color plano.

3. **No `backdrop-filter` ni vidrio esmerilado sobre el mapa.** Tira el framerate en Android de gama media y hace que el contraste del texto dependa de qué tesela quedó abajo — o sea, impredecible por definición. El panel es opaco.

4. **No pintes datos con el color de su categoría.** El precio en morado, la hora en naranjo. Morado-500 sobre crema da 3,39:1 y el naranjo 2,98:1. La categoría se dice con la carita y con el lomo; el dato se dice en tinta.

5. **No animes los pines en cada `refrescar()`.** Son hasta 229 elementos DOM sobre un canvas WebGL. Ver la regla de stagger (8.4).

6. **No uses negro puro** (`#000`) para contornos ni sombras. Sobre crema se ve sucio y agresivo. La tinta es `--azul-900`.

7. **No más de dos elementos rotados por pantalla, y nunca en datos.** Un chip torcido es simpático; una lista torcida es un bug.

8. **No confíes solo en el color para la categoría.** Daltonismo + pantalla de noche + brillo al mínimo. Siempre **carita + color + etiqueta de texto**. Los tres, siempre.

9. **No achiques el área táctil para que los chips se vean "cute".** El mínimo es 44px. Hoy los chips están en 30px, los botones de idioma en 24px y los de tema en 26px. Se toca caminando.

10. **No pongas la mascota encima del dato.** La Loica puede volar sobre el mapa; no puede pasar sobre el precio ni sobre la hora. `z-index:5`, siempre bajo el panel.

11. **No uses emojis como sistema de íconos.** Se ven distinto en cada dispositivo, no toman el color del tema y son exactamente lo que hace que algo parezca hecho rápido. Tenemos seis animales propios: ese es el activo.

12. **No confetti ni sonido en cada interacción.** La celebración se gasta. Reserva la pose "celebrando" para: encontrar un evento gratis y enviar el formulario. Nada más.

13. **No conviertas la lista en tarjetas flotantes.** Con 271 eventos triplica el scroll. La fila con lomo de color es igual de expresiva y mantiene la densidad.

14. **No agregues colores para los filtros de edad.** Seis familias ya es el techo de un mapa. Los filtros nuevos se distinguen por **forma** (7.1), no por color.

---

## 10. Orden de implementación

De mayor impacto por menor esfuerzo. Cada paso deja la app funcionando.

| # | Qué | Esfuerzo | Impacto |
|---|---|---|---|
| 1 | Pegar los tokens de 3.1-3.3 en `loica.css` | 30 min | Base de todo |
| 2 | Arreglar los contrastes rotos: `--acento-solido` en el botón, `--tinta-tenue` a `--arena-700` | 15 min | Accesibilidad, y ya |
| 3 | Contorno + repisa en chip, botón, miniatura, panel (7.1, 7.4, 7.5) | 2 h | **Acá se ve el cambio** |
| 4 | Áreas táctiles a 44px + Baloo 2 en chips y botones (5.1) | 1 h | Se siente otra app |
| 5 | Pin nuevo con contorno, sin `drop-shadow` (7.3) | 1 h | Legible de noche + más rápido |
| 6 | Nav con color por destino y cinta de marca (7.6) | 1 h | El pedido literal del fundador |
| 7 | `carita()` a viewBox 24 con las reglas de 6.2 | 3-4 h | Las mascotas por fin se ven |
| 8 | `--tono-cat` y lomo de color en la tarjeta (7.2) | 45 min | Categoría legible sin leer |
| 9 | `otros` → amarillo, y revisar el clasificador del pipeline | 30 min + investigación | El mapa deja de ser rojo |
| 10 | Movimiento: repisa que colapsa, stagger, reduced-motion (8) | 2 h | El "se siente juego" |
| 11 | La Loica volando (6.6) | 3-4 h | El wow del fundador |
| 12 | `mascota()` a viewBox 48 con 4 poses | 1-2 días | Nosotros, blog, onboarding |

Los pasos 1 a 6 son un día de trabajo y ya cambian la percepción por completo. Yo partiría ahí, lo publicaría, y recién después metería mano a los SVG.

---

## Fuentes consultadas

- [Duolingo design system — tokens (Refero)](https://styles.refero.design/style/7088d695-362b-4e09-b325-fa8136d4f350)
- [Neobrutalism: Definition and Best Practices — NN/g](https://www.nngroup.com/articles/neobrutalism/)
- [Mailchimp brand system por COLLINS — It's Nice That](https://www.itsnicethat.com/news/mailchimp-collins-brand-system-graphic-design-270918)
- [Headspace, rebrand de identidad visual — It's Nice That](https://www.itsnicethat.com/articles/italic-studio-headspace-graphic-design-project-250424)
- [Headspace design system — colores y tokens](https://oh-my-design.kr/design-systems/headspace)
- [Replicating Duolingo's button in pure CSS](https://medium.com/@lilskyjuicebytes/clone-the-ui-1-replicating-duolingos-button-in-pure-css-bd37a97edb7e)
- [Building a Magical 3D Button — Josh W. Comeau](https://www.joshwcomeau.com/animation/3d-button/)
- [15 Web Design Trends for 2026 — DesignRush](https://www.designrush.com/agency/website-design-development/trends/web-design-trends)
- [Best New Google Fonts 2026 — Made Good Designs](https://madegooddesigns.com/best-new-google-fonts-2026/)
- [Elementor](https://elementor.com) (referencia dada por el fundador)

Los contrastes de este documento están calculados con la fórmula WCAG 2.1 sobre los hex exactos, no estimados a ojo.
