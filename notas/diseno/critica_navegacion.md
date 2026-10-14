# Crítica de navegación — Loica en celular

**Fecha:** 2026-08-09 · **Alcance:** `index.html`, `calendario.html`, `agrega.html`, `nosotros.html`, `loica.css`, `loica.js`
**Usuario de referencia:** alguien parado en la calle, con una mano, decidiendo qué hacer en los próximos 90 minutos.

---

## Cómo se midió esto

No son estimaciones. Levanté las páginas en un servidor local y medí el DOM real a **375×812** (iPhone SE/13 mini, el piso realista del parque de celulares en Chile). Todos los números de abajo salen de `getBoundingClientRect()` sobre la página renderizada.

Datos del catálogo actual (`eventos.json`, 95 eventos) que condicionan varias conclusiones:

| Dato | Valor | Por qué importa |
|---|---|---|
| Eventos totales | 95 | Los 95 se pintan como pin y como tarjeta al abrir |
| Con imagen | **9 de 95 (9,5%)** | "Evento sin imagen" es el caso normal, no el borde |
| Gratis | 19 de 95 (20%) | El filtro estrella deja 1 de cada 5 |
| Categoría `otros` | **34 de 95 (36%)** | La categoría más grande no significa nada para el usuario |
| Categorías distintas | 10 | Genera 10 chips de filtro |
| Eventos "Hoy" | 4 | "Hoy" ya es casi un estado vacío |
| Eventos "Hoy" + "Gratis" | **2** | Dos toques y quedas casi sin resultados |
| Eventos sin hora (00:00) | 52 de 95 | La ficha muestra fecha sin hora la mitad de las veces |
| Título más largo | 128 caracteres | Rompe la altura de las tarjetas |

---

# (a) Diagnóstico: los 5 problemas más graves

## 1. Tres de los cuatro destinos son literalmente invisibles

**Archivos:** `loica.css:117-118` · `loica.js:156-159`

```css
/* loica.css:117 */
.nav{display:flex;gap:var(--e-1);margin-left:var(--e-4);overflow-x:auto;scrollbar-width:none}
.nav::-webkit-scrollbar{display:none}   /* :118 — se esconde la única pista de scroll */
```

Medición a 375px en `index.html`:

| | |
|---|---|
| Ancho visible de `.nav` | **76 px** |
| Ancho real del contenido | 374 px |
| Contenido fuera de pantalla | **298 px (80%)** |
| Enlaces visibles | **1 de 4** — solo "Mapa" |

"Calendario", "Agrega tu evento" y "Nosotros" **no se ven en ninguna de las cuatro páginas**. Y como `scrollbar-width:none` + `::-webkit-scrollbar{display:none}` eliminan la barra de scroll, tampoco hay señal de que exista algo más a la derecha. El único indicio es que "Mapa" queda pegado al botón de tema, cortado.

Esto no es un problema de comodidad: es una app de 4 páginas donde el celular expone 1. El calendario y el formulario de publicación —o sea, el producto entero salvo el mapa— dependen de que el usuario adivine que ese espacio de 76 px se arrastra.

El problema se agrava porque compiten por el mismo espacio 4 controles que nadie usa parado en la calle: `☀` (34×26) y `ES` `EN` `PT` (32×28 cada uno) ocupan **160 px de los 375** de la barra superior, es decir el doble de ancho que toda la navegación.

## 2. "Gratis", el filtro estrella, está en el peor punto de la pantalla

**Archivos:** `index.html:80` (`<div class="filtros" id="filtros"></div>` dentro de `<header>`) · `index.html:161-162` · `loica.css:138-140`

Posición medida del chip "Gratis": **y = 71 → 107 px**. En una pantalla de 812 px, eso deja el control más usado del producto a **705 px del borde inferior**, en la franja donde el pulgar no llega sin recolocar el teléfono.

La contradicción es explícita en el propio manifiesto del producto (`nosotros.html:125`):

> "Acá el filtro de panoramas gratuitos es el primero de la lista"

Ser el primero de la lista y ser alcanzable son cosas distintas. Hoy es lo primero que se lee y lo último que se puede tocar con una mano. Para un usuario caminando, "Gratis" a 705 px del pulgar es un filtro que no existe.

## 3. 120 px de cabecera permanente y 9 de 13 chips fuera de pantalla

**Archivos:** `index.html:78-81` · `loica.css:138-140` · `index.html:166-172`

```html
<!-- index.html:78-81 -->
<header>
  <div class="barra" id="barra"></div>     <!-- 59 px -->
  <div class="filtros" id="filtros"></div> <!-- 61 px -->
</header>
```

| Medición (375×812, `index.html`) | Valor |
|---|---|
| Alto de la cabecera | **120 px (14,8% de la pantalla), siempre** |
| Chips totales | 13 |
| Chips visibles sin arrastrar | **4** (Gratis, Hoy, Este finde, Aire libre) |
| Ancho de chips fuera de pantalla | **901 px** |
| Mapa sin obstrucción | 812 − 120 − 128 = **564 px (69%)** |

Los 13 chips salen de `index.html:161-172`: 3 fijos más uno por cada categoría presente. Con el catálogo actual eso son 10 chips de categoría, y son de muy mala calidad como filtros:

- **`Otros` filtra 34 de 95 eventos (36%)**. Es una etiqueta de calidad de datos que se filtró a la interfaz. Nadie sale a la calle buscando "otros".
- **`Fiestas` filtra 1 evento. `Aire libre` filtra 1 evento.** Chips que llevan de 95 a 1 resultado: callejones sin salida.
- **`Arte`, `Teatro`, `Cine` y `Charlas` son 4 chips para un mismo concepto visual**: los cuatro usan la misma mascota (chinchilla = cultura) según `loica.js:76-79`. El sistema de diseño ya sabe que son un grupo; el filtro lo ignora y los muestra sueltos.

## 4. El panel deslizable tiene dos estados y ninguno de los dos sirve

**Archivos:** `index.html:29-35` (alturas) · `index.html:248-249` (interacción)

```css
/* index.html:33-35 */
height:128px;max-height:80%;
}
.panel-lista.abierto{height:80%}
```

```js
/* index.html:248-249 — toda la interacción del panel */
document.getElementById("tirador").onclick = () =>
  document.getElementById("panel").classList.toggle("abierto");
```

Medición de los dos estados:

| Estado | Alto panel | Alto lista | Resultado real |
|---|---|---|---|
| Cerrado | 128 px | **68 px** | **0,78 de una tarjeta** (miden 87 px): se ve una tarjeta cortada por la mitad |
| Abierto | 554 px | 494 px | Quedan **138 px de mapa**: el mapa desaparece |

No hay término medio. O ves una tarjeta serruchada, o pierdes el mapa. El estado útil —"veo el mapa **y** tres o cuatro panoramas"— no existe.

**Y el tirador no se arrastra.** `index.html:248` es un `onclick`. Busqué en todo el código: no hay un solo `pointerdown`, `touchstart` ni `pointermove`. La barrita gris de `index.html:37` es una promesa visual de un gesto que no está implementado. El usuario intenta arrastrar, no pasa nada, y concluye que la app está trabada.

## 5. La acción principal de cada evento queda bajo el pliegue, siempre

**Archivos:** `index.html:42-52` (ficha) · `index.html:49` (`.ficha-foto`) · `index.html:236-237` (el CTA)

Medición de la ficha abierta a 375×812, para un evento **sin imagen** (90% del catálogo):

| | |
|---|---|
| Alto visible de la ficha | 596 px (73% de la pantalla) |
| Alto real del contenido | 689 px → **siempre hay scroll** |
| `.ficha-foto` (mascota de relleno) | **150 px** = 25% de la ficha |
| El `<h2>` con el título empieza en | y = 409 px (mitad de la pantalla) |
| Botón "Ver en la fuente original" | **y = 814 px** → 2 px bajo el borde |
| Lo mismo con el título más largo (128 car.) | **y = 939 px** → 127 px bajo el borde |

O sea: **el botón que cumple el propósito entero de la app está fuera de pantalla en el 100% de los eventos.** Y lo que lo empuja hacia abajo es una banda de 150 px que en 86 de 95 casos solo muestra una mascota decorativa, porque `index.html:219-221` cae al placeholder cuando no hay `ev.imagen`.

El botón de cerrar (`index.html:53-57`) mide **34×34** y vive en la esquina superior derecha de la ficha — bajo el mínimo táctil y en la esquina más incómoda para el pulgar izquierdo.

---

# (b) Arquitectura de navegación recomendada

## La decisión

> **Una sola superficie ("Panoramas") que fusiona mapa y calendario, con "Agrega tu evento" y "Nosotros" fuera de la navegación principal.**

Y dentro de esa superficie: **los filtros y el conteo se bajan a la hoja inferior**, pegados al pulgar.

## Por qué no una barra inferior de 4 pestañas

La barra inferior tipo app nativa es la respuesta correcta al problema equivocado. Ordena 4 destinos en la zona del pulgar, sí, pero da por buena la premisa de que hay 4 destinos que valen lo mismo. No los hay:

| Destino | Para quién | Frecuencia real |
|---|---|---|
| Mapa | Todos | Cada sesión |
| Calendario | Todos | Misma data, otra lente temporal |
| Agrega tu evento | **Organizadores**, no consumidores | Una vez en la vida, y llegan por link externo |
| Nosotros | Prensa, curiosos | Casi nunca |

Una barra inferior de 4 cuesta ~56 px más `env(safe-area-inset-bottom)` (~34 px en iPhone) = **~90 px permanentes** de la pantalla más escasa del producto, para servir dos destinos que casi nadie toca. Es cambiar un impuesto arriba (120 px) por otro abajo (90 px), sin reducir la complejidad.

**Antes de elegir el conmutador, hay que reducir los destinos.**

## Por qué fusionar mapa y calendario

No son dos productos. Son **la misma lista con dos lentes de tiempo**, y el código ya lo sabe:

- Los dos leen el mismo `cargarEventos()` (`loica.js:186-190`)
- Los dos pintan con la misma `tarjetaEvento()` (`loica.js:206-229`)
- Los dos tienen una función `visibles()` casi idéntica (`index.html:143-146` vs `calendario.html:131-132`)
- Los dos repiten el bloque `pintarFiltros()` casi copiado (`index.html:148-173` vs `calendario.html:134-153`)

La fusión no es una refactorización arriesgada: es borrar duplicación que ya existe.

Y desde el usuario: **nadie parado en la calle quiere una grilla de mes.** Quiere "ahora", "esta noche", "este finde". La grilla de 42 celdas es un instinto de escritorio. Medido en `calendario.html` a 375px, esa grilla ocupa **376 px (46% de la pantalla)** para entregar puntos de colores, mientras los eventos reales —lo que la persona vino a buscar— reciben 130 px al fondo, cortados.

El calendario no desaparece: se convierte en un **selector de fecha** que se abre desde el control "Cuándo", cuando alguien efectivamente quiere planificar el 15 del mes que viene. Deja de ser un destino de primer nivel y pasa a ser una herramienta dentro de la superficie única.

## El modelo resultante

```
┌─────────────────────────────┐
│  [loica]              [Más] │ ← barra flotante sobre el mapa, no le roba alto
│                             │
│                             │
│         M A P A             │ ← 691 px en vez de 564
│      (pantalla casi         │
│       completa)             │
│                             │
├──── ═══ ────────────────────┤ ← tirador que SÍ se arrastra, 3 estados
│  95 panoramas               │
│  [Gratis] [Hoy] [Finde] [+] │ ← ZONA DEL PULGAR
└─────────────────────────────┘
```

**Qué cambia y por qué:**

| Cambio | Por qué |
|---|---|
| Cabecera flota sobre el mapa | Devuelve 120 px al mapa. El mapa es el producto. |
| `.nav` de 4 enlaces → botón "Más" | 3 destinos invisibles pasan a estar en una hoja inferior tocable |
| Idioma y tema salen de la barra → van a "Más" | Liberan 160 px de los 375 de la barra superior |
| Filtros bajan al panel inferior | "Gratis" pasa de y=71 a y≈700: de inalcanzable a natural |
| Filtros pegados al conteo | Filtro y su consecuencia ("47 panoramas") quedan juntos |
| 13 chips → 3 visibles + "Tipo" | Menos decisiones; los 10 chips de categoría eran de mala calidad |
| Panel: 2 estados → 3, arrastrable | Aparece el estado útil: mapa + 3 tarjetas a la vez |
| Calendario → selector de fecha | Deja de competir con el mapa; la grilla solo aparece si la piden |

## Puesta en marcha por fases

Es mucho cambio para hacerlo de una. Orden sugerido, de mayor rendimiento por esfuerzo a menor:

- **Fase 1 — una tarde, sin tocar la arquitectura.** Bajar `#filtros` al panel, 3 estados de panel con arrastre real, CTA fijo en la ficha, áreas táctiles a 44 px, `env(safe-area-inset-bottom)`. Esto ya resuelve los problemas 2, 4 y 5.
- **Fase 2 — la navegación.** Barra flotante, botón "Más" con hoja inferior, idioma/tema adentro. Resuelve el problema 1.
- **Fase 3 — la fusión.** Calendario como selector de fecha dentro del mapa. Resuelve el problema 3 y borra la duplicación de código.

---

# (c) Cambios concretos

## C1 · Bajar los filtros al pulgar (el cambio de mayor impacto)

**`index.html:78-95`** — sacar `#filtros` de la cabecera y meterlo en el panel:

```html
<!-- ANTES -->
<header>
  <div class="barra" id="barra"></div>
  <div class="filtros" id="filtros"></div>
</header>
<main>
  <div id="mapa"></div>
  <section class="panel-lista" id="panel" aria-label="Lista de eventos">
    <div class="tirador" id="tirador">
      <div class="barra-tirador"></div>
      <div class="conteo"><b id="conteo">0</b> <span id="conteo-txt">eventos</span></div>
    </div>
    <div class="cabecera-lista">…</div>
    <div class="lista" id="lista"></div>
  </section>
```

```html
<!-- DESPUÉS -->
<header>
  <div class="barra" id="barra"></div>
</header>
<main>
  <div id="mapa"></div>
  <section class="panel-lista" id="panel" data-estado="asomo" aria-label="Lista de eventos">
    <div class="tirador" id="tirador">
      <div class="barra-tirador"></div>
      <div class="conteo"><b id="conteo">0</b> <span id="conteo-txt">eventos</span></div>
    </div>
    <div class="filtros" id="filtros"></div>   <!-- ← baja acá, junto al conteo -->
    <div class="cabecera-lista">…</div>
    <div class="lista" id="lista"></div>
  </section>
```

No hay que tocar `pintarFiltros()`: sigue escribiendo en `#filtros`, solo que ahora está abajo.

## C2 · Panel con tres estados y arrastre real

**`index.html:29-37`** — reemplazar el bloque de alturas:

```css
/* ANTES (index.html:29-35) */
.panel-lista{
  position:absolute;left:0;right:0;bottom:0;background:var(--fondo-elevado);
  border-radius:var(--r-xl) var(--r-xl) 0 0;box-shadow:var(--sombra-3);
  display:flex;flex-direction:column;transition:height var(--medio);z-index:4;
  height:128px;max-height:80%;
}
.panel-lista.abierto{height:80%}
```

```css
/* DESPUÉS */
.panel-lista{
  position:absolute;left:0;right:0;bottom:0;background:var(--fondo-elevado);
  border-radius:var(--r-xl) var(--r-xl) 0 0;box-shadow:var(--sombra-3);
  display:flex;flex-direction:column;transition:height var(--medio);z-index:4;
  padding-bottom:env(safe-area-inset-bottom);   /* iPhone con barra de gestos */
}
/* svh y no dvh: la hoja no debe saltar cuando el navegador esconde su barra */
.panel-lista[data-estado="asomo"]{height:calc(126px + env(safe-area-inset-bottom))}
.panel-lista[data-estado="medio"]{height:52svh}
.panel-lista[data-estado="lleno"]{height:88svh}

/* Sin esto el navegador se roba el gesto y el arrastre no funciona */
.tirador{touch-action:none;user-select:none}
```

En `asomo` se ven el conteo y los filtros (126 px), sin tarjeta cortada. El mapa pasa de 564 a **632 px**. En `medio` entran 3 tarjetas completas sin perder el mapa.

**`index.html:248-249`** — reemplazar el `onclick` por arrastre de verdad:

```js
/* ANTES */
document.getElementById("tirador").onclick = () =>
  document.getElementById("panel").classList.toggle("abierto");
```

```js
/* DESPUÉS */
const panel = document.getElementById("panel");
const tirador = document.getElementById("tirador");
const ESTADOS = ["asomo", "medio", "lleno"];
let estado = 0;

const fijarEstado = i => {
  estado = Math.max(0, Math.min(ESTADOS.length - 1, i));
  panel.dataset.estado = ESTADOS[estado];
};

let inicioY = null, altoInicial = 0;

tirador.addEventListener("pointerdown", e => {
  inicioY = e.clientY;
  altoInicial = panel.getBoundingClientRect().height;
  panel.style.transition = "none";          // durante el arrastre manda el dedo
  tirador.setPointerCapture(e.pointerId);
});

tirador.addEventListener("pointermove", e => {
  if(inicioY === null) return;
  const alto = altoInicial + (inicioY - e.clientY);
  panel.style.height = Math.min(Math.max(alto, 120), innerHeight * .9) + "px";
});

tirador.addEventListener("pointerup", e => {
  if(inicioY === null) return;
  const recorrido = inicioY - e.clientY;
  panel.style.transition = "";
  panel.style.height = "";                  // vuelve a mandar el CSS
  // menos de 8px de recorrido fue un toque, no un arrastre
  if(Math.abs(recorrido) < 8) fijarEstado(estado === ESTADOS.length - 1 ? 0 : estado + 1);
  else fijarEstado(estado + (recorrido > 0 ? 1 : -1));
  inicioY = null;
});
```

Sigue funcionando con un toque simple (avanza de estado y vuelve al principio), y ahora también con el dedo.

## C3 · Ficha: CTA siempre visible y sin banda vacía

**`index.html:49-52`** — la foto solo ocupa espacio si hay foto:

```css
/* ANTES */
.ficha-foto{height:150px;background:var(--fondo-hundido);position:relative;
  border-radius:var(--r-xl) var(--r-xl) 0 0;overflow:hidden;display:grid;place-items:center}
.ficha-cuerpo{padding:var(--e-5)}
```

```css
/* DESPUÉS */
.ficha-foto{height:150px;background:var(--fondo-hundido);position:relative;
  border-radius:var(--r-xl) var(--r-xl) 0 0;overflow:hidden;display:grid;place-items:center}
/* 86 de 95 eventos no tienen imagen: no gastes 150px en una mascota decorativa */
.ficha-foto.sin-foto{height:52px;background:transparent}
.ficha-foto.sin-foto svg{display:none}

.ficha-cuerpo{padding:var(--e-5)}

/* El botón que cumple el propósito de la app no puede quedar bajo el pliegue */
.ficha-cta{
  position:sticky;bottom:0;z-index:2;
  margin:var(--e-4) calc(-1 * var(--e-5)) calc(-1 * var(--e-5));
  padding:var(--e-3) var(--e-5) calc(var(--e-3) + env(safe-area-inset-bottom));
  background:var(--fondo-elevado);border-top:1px solid var(--borde);
}
.cerrar{width:44px;height:44px}   /* era 34×34 */
```

**`index.html:217-239`** — dos ajustes dentro de `abrirFicha()`:

```js
// 1. marcar la banda cuando no hay imagen (línea 218)
<div class="ficha-foto${ev.imagen ? "" : " sin-foto"}">

// 2. envolver el CTA para que quede fijo abajo (líneas 236-237)
<div class="ficha-cta">
  <a class="boton bloque" href="${escapar(ev.url)}"
     target="_blank" rel="noopener">${t("ir")} ↗</a>
</div>
```

## C4 · Chips: de 13 a 3 + un agrupador

El sistema de diseño ya define la agrupación correcta en `loica.js:73-85`: la **mascota** es el grupo. El filtro la ignora y muestra las categorías crudas.

**`index.html:166-172`**:

```js
/* ANTES: un chip por categoría cruda → 10 chips, uno de ellos "Otros" con 36% del catálogo */
[...new Set(EVENTOS.map(e => e.categoria))]
  .sort((a,b) => cat(a)[IDIOMA].localeCompare(cat(b)[IDIOMA]))
  .forEach(c => {
    const info = cat(c);
    agregar(`${mascota(info.mascota, filtroCat === c ? "#fff" : info.hex, 19)} ${info[IDIOMA]}`,
            filtroCat === c, () => filtroCat = filtroCat === c ? null : c);
  });
```

```js
/* DESPUÉS: un chip por mascota → 4 grupos con volumen real.
   "loica" (Otros, 34 eventos) queda fuera: nunca se excluye, no se filtra. */
const GRUPOS = {condor:"Música", chinchilla:"Cultura", chincol:"Clases", pudu:"Aire libre"};
[...new Set(EVENTOS.map(e => cat(e.categoria).mascota))]
  .filter(m => GRUPOS[m])
  .forEach(m => {
    const hex = cat(Object.keys(CATEGORIAS).find(c => cat(c).mascota === m)).hex;
    agregar(`${mascota(m, filtroGrupo === m ? "#fff" : hex, 19)} ${GRUPOS[m]}`,
            filtroGrupo === m, () => filtroGrupo = filtroGrupo === m ? null : m);
  });
```

Y en `visibles()` (`index.html:143-146`), cambiar `ev.categoria === filtroCat` por `cat(ev.categoria).mascota === filtroGrupo`.

Resultado: **13 chips → 7** (Gratis, Hoy, Este finde + 4 grupos). Volúmenes: Cultura 38, Música 13 (+1 fiesta), Clases 5, Aire libre 4. Se acabaron los chips que llevan a 1 resultado.

Si además se quiere dejar solo 3 a la vista: los 4 grupos van tras un chip `Tipo ▾` que abre una hoja inferior.

## C5 · Cabecera flotante y navegación en "Más"

**`index.html`, bloque `<style>`** — agregar:

```css
@media (max-width:879px){
  main{position:relative}
  header{
    position:absolute;inset:0 0 auto 0;z-index:6;
    background:transparent;border:0;pointer-events:none;
    padding-top:env(safe-area-inset-top);
  }
  .barra{
    margin:var(--e-2);border-radius:var(--r-full);border:0;pointer-events:auto;
    background:color-mix(in srgb, var(--fondo-elevado) 92%, transparent);
    backdrop-filter:blur(10px);box-shadow:var(--sombra-2);
  }
}
```

**`loica.js:153-183`, dentro de `pintarBarra()`** — la `.nav` horizontal desaparece en celular y su contenido se va a una hoja inferior:

```css
/* loica.css — agregar */
@media (max-width:879px){
  .nav{display:none}
  .barra-fin .idiomas{display:none}   /* ES/EN/PT se van a la hoja "Más" */
  .barra-fin .tema{display:none}
}
.mas{
  min-width:44px;min-height:44px;border-radius:var(--r-full);
  border:1px solid var(--borde);background:var(--fondo-elevado);
  color:var(--tinta);font:750 var(--t-sm)/1 var(--fuente-ui);cursor:pointer;
}
.hoja-mas{
  position:fixed;inset:auto 0 0 0;z-index:20;background:var(--fondo-elevado);
  border-radius:var(--r-xl) var(--r-xl) 0 0;box-shadow:var(--sombra-3);
  padding:var(--e-5) var(--e-4) calc(var(--e-5) + env(safe-area-inset-bottom));
  transform:translateY(101%);transition:transform var(--medio);
}
.hoja-mas.visible{transform:translateY(0)}
.hoja-mas a{
  display:flex;align-items:center;gap:var(--e-3);min-height:52px;
  padding:0 var(--e-3);border-radius:var(--r-md);text-decoration:none;font-weight:700;
}
.hoja-mas a:hover{background:var(--fondo-hundido)}
```

Los enlaces de `loica.js:156-159` se pintan dentro de `.hoja-mas` en vez de `.nav`. Cada uno con 52 px de alto, en la mitad inferior de la pantalla.

## C6 · Áreas táctiles a 44 px

Medidas actuales: **15 de los 16 controles de interfaz están bajo 44×44.**

```css
/* loica.css:119-123 */
.nav a{padding:11px var(--e-3)}          /* 34 → 44 */

/* loica.css:141-147 */
.chip{padding:11px 16px 11px 11px}       /* 36 → 44 */

/* loica.css:129-135 */
.idiomas button,.tema{min-width:44px;min-height:44px}   /* 32×28 y 34×26 */

/* index.html:53 */
.cerrar{width:44px;height:44px}          /* 34×34 */

/* calendario.html:23-27 */
.mes-nav button{width:44px;height:44px}  /* 38×38 */

/* agrega.html:27-31 */
.opcion-cat{padding:11px 15px 11px 11px} /* 40 → 44 */
```

Los controles de zoom de MapLibre (`index.html:119`) miden **29×29** y están arriba a la izquierda, la esquina más lejana del pulgar. En un mapa táctil el pellizco ya hace zoom: **quitarlos**.

```js
/* index.html:119 — ANTES */
mapa.addControl(new maplibregl.NavigationControl({showCompass:false}), "top-left");

/* DESPUÉS: en celular el pellizco basta; el control solo estorba */
if(matchMedia("(min-width:880px)").matches)
  mapa.addControl(new maplibregl.NavigationControl({showCompass:false}), "top-left");
```

## C7 · Continuidad: que el filtro sobreviva al cambio de pantalla

Hoy **no sobrevive**. `index.html:104` y `calendario.html:116` declaran los filtros como variables locales que se reinician en cada carga:

```js
/* index.html:104 */
let EVENTOS = [], filtroCat = null, soloGratis = false, cuando = "todo";
/* calendario.html:116 */
let EVENTOS = [], filtroCat = null, soloGratis = false;
```

Mientras tanto, `loica.js:143` y `loica.js:153` **sí** guardan idioma y tema en `localStorage`. La app conserva las preferencias cosméticas y bota la intención del usuario. Está al revés.

Peor: el calendario **ni siquiera tiene los chips "Hoy" y "Este finde"** (`calendario.html:144-152` solo pinta Gratis + categorías, frente a `index.html:161-164`). Aunque el filtro se transfiriera, el vocabulario no calza.

```js
/* loica.js — agregar junto al manejo de tema */
const FILTROS_CLAVE = "loica-filtros";
function guardarFiltros(f){ sessionStorage.setItem(FILTROS_CLAVE, JSON.stringify(f)); }
function leerFiltros(){
  try{ return JSON.parse(sessionStorage.getItem(FILTROS_CLAVE)) || {}; }
  catch{ return {}; }
}
```

```js
/* index.html:104 — DESPUÉS */
const guardado = leerFiltros();
let EVENTOS = [],
    filtroGrupo = guardado.filtroGrupo ?? null,
    soloGratis  = guardado.soloGratis  ?? false,
    cuando      = guardado.cuando      ?? "todo";
```

Y dentro del `onclick` de `agregar()` (`index.html:156`), añadir `guardarFiltros({filtroGrupo, soloGratis, cuando})`.

**`sessionStorage` y no `localStorage`, a propósito:** un filtro es la intención de *esta salida*, no una preferencia permanente. Si alguien filtra "Gratis" un viernes, el martes siguiente debe abrir la app viendo todo. Dentro de la misma sesión, en cambio, cambiar de pantalla no puede borrarle el trabajo.

## C8 · `env(safe-area-inset-*)`: hoy no existe en ninguna parte

Las cuatro páginas declaran `viewport-fit=cover` (`index.html:5`, `calendario.html:5`, `agrega.html:5`, `nosotros.html:5`) pero **no hay un solo `env(safe-area-inset-*)` en todo el proyecto**. En iPhone con barra de gestos, los últimos ~34 px del panel, de la ficha y de la agenda quedan bajo el indicador de inicio.

```css
/* loica.css — agregar */
.panel-lista,.ficha,.agenda{padding-bottom:env(safe-area-inset-bottom)}
.contenido{padding-bottom:calc(var(--e-12) + env(safe-area-inset-bottom))}
```

## C9 · Calendario: el fondo de la agenda es inalcanzable

**`calendario.html:13,16,70-79`.** Medición a 375×812: `.agenda` termina en **y = 906 px** sobre una pantalla de 812. Como `html,body{overflow:hidden}` (`calendario.html:13`), esos **94 px son irrecuperables**: el final de la lista de eventos del día no se puede ver nunca.

La causa es que `.calendario` es un ítem flex con `min-height:auto` y una grilla de 6 filas que no puede encogerse, así que empuja a `.agenda` fuera de la pantalla.

```css
/* calendario.html:70-79 — ANTES */
@media(max-width:900px){
  main{flex-direction:column}
  .agenda{width:auto;border-left:0;border-top:1px solid var(--borde);max-height:44%}
  …
}
```

```css
/* DESPUÉS */
@media(max-width:900px){
  main{flex-direction:column;min-height:0}
  .calendario{flex:1 1 auto;min-height:0}      /* ← la clave: permite encoger */
  .rejilla{grid-auto-rows:minmax(38px,1fr)}
  .agenda{
    width:auto;border-left:0;border-top:1px solid var(--borde);
    flex:0 0 46%;max-height:none;
    padding-bottom:env(safe-area-inset-bottom);
  }
  …
}
```

**Y un contador que miente.** `calendario.html:205` muestra `+${delDia.length - 3}` asumiendo que las 3 primeras `.marca-ev` están a la vista — pero `calendario.html:74` las esconde (`display:none`) en celular. El día 11 muestra "**+23**" cuando tiene 26 eventos, sin ninguna referencia de a qué se suma ese 23.

```js
/* calendario.html:203-206 — mostrar el total real en celular */
${delDia.length > 3 ? `<span class="mas" data-total="${delDia.length}">+${delDia.length - 3}</span>` : ""}
```
```css
/* calendario.html — en el bloque @media(max-width:900px) */
.mas{font-size:10px}
.mas::before{content:attr(data-total);}   /* el total, no el resto */
.mas{font-size:0}
.mas::before{font-size:10px}
```

## C10 · Estados de error y de vacío

**No hay ninguno.** `mapa.on("click", cerrarFicha)` (`index.html:250`) es el único manejador del mapa: sin `error`, sin `load`. Y `cargarEventos()` (`loica.js:186-190`) no tiene `.catch`.

Lo comprobé sin querer al medir con la red bloqueada: las teselas de OpenStreetMap no cargaron y **la app mostró pines flotando sobre un vacío oscuro, sin un solo mensaje**. Ese es exactamente el escenario objetivo: alguien en la calle con señal mala.

```js
/* index.html — agregar después de la línea 119 */
mapa.on("error", () => {
  document.getElementById("mapa").insertAdjacentHTML("beforeend",
    `<div class="aviso-mapa">No pudimos cargar el mapa. Los panoramas siguen abajo.</div>`);
});

/* loica.js:186-190 — agregar el .catch en quien lo llama (index.html:133) */
cargarEventos()
  .then(evs => { EVENTOS = evs; pintarFiltros(); refrescar(); })
  .catch(() => {
    document.getElementById("lista").innerHTML =
      `<div class="vacio">${mascota("loica","var(--tinta-tenue)",78)}
        <p><b>No pudimos cargar los panoramas</b><br>Revisa tu conexión.</p>
        <button class="boton" onclick="location.reload()">Reintentar</button></div>`;
  });
```

**Y una salida del estado vacío.** Hoy el mensaje dice "Prueba sacando algún filtro" (`loica.js:95`) pero no ofrece el botón para hacerlo. Con "Hoy"+"Gratis" quedan **2 eventos** y con "Fiestas" queda **1**: el callejón sin salida está a dos toques.

```js
/* index.html:201-205 — agregar el botón de escape */
if(!lista.length){
  cont.innerHTML = `<div class="vacio">${mascota("loica","var(--tinta-tenue)",78)}
    <p><b>${t("vacio")}</b><br>${t("vaciopista")}</p>
    <button class="boton" id="limpiar">Ver los 95 panoramas</button></div>`;
  document.getElementById("limpiar").onclick = () => {
    soloGratis = false; filtroGrupo = null; cuando = "todo";
    guardarFiltros({filtroGrupo, soloGratis, cuando}); pintarFiltros(); refrescar();
  };
  return;
}
```

## C11 · Formulario: iOS hace zoom en cada campo

**`loica.css:202-206`.** Los inputs usan `font:var(--t-base)` = **14,5 px**. Safari en iOS hace zoom automático al enfocar cualquier campo bajo 16 px, y el usuario queda con la página ampliada y tiene que pellizcar para volver. Pasa en los 22 campos del formulario.

```css
/* loica.css:202-206 */
.campo input,.campo select,.campo textarea{
  width:100%;padding:11px var(--e-3);border:1.5px solid var(--borde);
  border-radius:var(--r-sm);background:var(--fondo);color:var(--tinta);
  font:16px/1.4 var(--fuente-ui);   /* ← 14.5px hacía que iOS ampliara la página */
  transition:var(--rapido);
}
```

Además, medido a 375×812: la página completa mide **2.386 px (2,9 pantallas)** y **el primer campo del formulario recién aparece en y = 777 px** — casi una pantalla entera de hero (346 px) y promesas (324 px) antes de poder escribir nada. Para quien llega decidido a publicar, eso es fricción pura.

```css
/* agrega.html:13-19 — comprimir la entrada en celular */
@media(max-width:600px){
  .hero{padding:var(--e-5) var(--e-4) var(--e-4)}
  .hero svg{width:48px;height:48px}          /* era 84px */
  .promesas{display:none}                     /* mover al final, después del formulario */
}
```

---

# (d) No tocar — esto ya está bien resuelto

Nada de lo que sigue necesita cambios. Varias son mejores que el promedio de lo que se ve en producción.

**Sistema de diseño (`loica.css:8-51`).** Escalas coherentes de tipografía, espaciado de base 4, sombras y radios con nombres semánticos. Está bien construido y bien comentado. No refactorizar.

**Modo oscuro (`loica.css:54-80`, `loica.js:137-150`).** Respeta `prefers-color-scheme`, permite anular la preferencia del sistema, y persiste la elección. Además redefine las sombras para oscuro, detalle que casi nadie hace. Esto está mejor que en la mayoría de las apps comerciales.

**`tarjetaEvento()` (`loica.js:206-229`).** Un solo componente compartido entre mapa y calendario. Es exactamente por esto que la fusión de la Fase 3 es barata. Mantener y seguir compartiendo.

**El sistema de mascotas por categoría (`loica.js:10-86`).** Señalética independiente del idioma, legible a 19 px en un chip y a 78 px en un estado vacío. Es el mejor activo de diseño del producto. La única corrección es *usarlo más*: agrupar los filtros por mascota (C4).

**Pines verdes para lo gratis (`index.html:27`).** Codificar el filtro estrella en el propio mapa, no solo en un chip. Decisión correcta.

**`escapar()` aplicado consistentemente (`loica.js:193`)** en todos los `innerHTML` con datos externos. Mantener la disciplina.

**`prefers-reduced-motion` (`loica.css:227-229`) y `:focus-visible` (`loica.css:106`).** Accesibilidad de base bien puesta desde el principio.

**El `ResizeObserver` del mapa (`index.html:121-131`).** Resuelve un problema real (el mapa nace sin tamaño final) y el comentario explica *por qué* se compara el tamaño anterior. Buen código.

**`.tarjeta` como `<button>` real (`loica.js:208`)** en vez de un `div` con `onclick`. Teclado y lectores de pantalla funcionan gratis.

**Semana que parte el lunes (`calendario.html:171-173`).** Correcto para Chile, y con comentario que lo explica.

**Aviso de ubicación aproximada (`index.html:231`, `loica.js:96`).** Honestidad sobre los 10 eventos geolocalizados solo a nivel de comuna. Mantener.

**`overscroll-behavior:contain` en `.lista` (`index.html:40`).** Evita que el scroll de la lista arrastre la página. Detalle fino y correcto.

**El tono de los textos** en las tres traducciones, y particularmente `nosotros.html`. La voz del producto está clara y es consistente. No tocarla.

---

# Anexo · Hallazgos menores

- **`alternarTema()` (`loica.js:144-149`) no tiene vuelta atrás.** Alterna claro↔oscuro, pero una vez que el usuario toca el botón nunca puede volver a "seguir al sistema", porque `localStorage` siempre queda con un valor. Un tercer estado "Sistema" en la hoja "Más" lo resuelve.
- **59 pines en pantalla al abrir**, de 95 totales, sin agrupación. Con `otros` en gris representando 36% del catálogo, buena parte del mapa es ruido gris. Vale la pena evaluar *clustering* cuando crezca el catálogo.
- **Tarjetas de altura variable (87 a 140 px)** porque `.tarjeta h3` (`loica.css:174-177`) no limita las líneas. Con títulos de hasta 128 caracteres el ritmo de la lista se rompe. Un `-webkit-line-clamp:2` lo estabiliza.
- **75 elementos interactivos en pantalla al abrir el mapa** (59 pines + ~16 controles). Aplicando C1, C4 y C6, los controles bajan de 16 a 9 y todos quedan sobre 44 px.
- **El formulario envía por `mailto:` (`agrega.html:280`)** y muestra la pantalla de éxito (`agrega.html:283-285`) sin saber si el correo se envió. En celular esto saca al usuario del navegador. Es una decisión consciente y razonable para esta etapa, pero el texto de éxito ya lo reconoce ("Revisa que tu correo se haya enviado") — conviene mantener esa honestidad hasta que haya backend.

---

**Resumen de una línea:** el mapa no necesita más funciones, necesita más pantalla y que los tres controles que importan —Gratis, Hoy, Finde— estén donde está el pulgar.
