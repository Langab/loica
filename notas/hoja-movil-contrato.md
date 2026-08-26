# La hoja inferior: contrato de `montarHoja()`

*25-08-2026. Escrito para que la persona (o el agente) que porte `cine.html`,
`descuentos.html` y `talleres.html` no tenga que leer `loica.js` entero.*

---

## 1. Qué problema resuelve, para no volver a discutirlo

Las cuatro páginas con mapa tenían el **mismo** arrastre copiado y pegado, y por
lo tanto el mismo defecto. Medido con toques reales (`Input.dispatchTouchEvent`
por CDP, Chromium con perfil de iPhone 13) sobre `mapa.html`, **antes**:

| gesto | alto del panel |
|---|---|
| arrastrar desde `.conteo` (cabecera del contador) | 173 → **173** (nada) |
| arrastrar desde `.lista` | 173 → **173** (nada) |
| arrastrar desde el `#tirador` | 173 → 448 ✔ |
| arrastre corto de 18 px desde el tirador | 173 → **173** (nada) |
| tamaño del `#tirador` | 386 × **29 px** |

O sea: el gesto existía, pero solo en una franja de 29 px. El pulgar mide 44 y
cae en el contador o en la lista, donde no pasaba nada. Eso es lo que el dueño
reportaba como *"no deja subir o bajar la pestaña"*. Y no había forma de
esconder la lista para ver el mapa completo, que también lo pidió.

**Después** (mismo aparato, mismo método):

| gesto | resultado |
|---|---|
| arrastrar desde `.conteo` hacia arriba | 173 → **448** ✔ |
| arrastrar desde `.lista` con `scrollTop 0` hacia abajo | 448 → 316, y siguiendo → **escondida** ✔ |
| arrastrar desde `.lista` ya scrolleada | la lista scrollea (300 → 165), la hoja **no se mueve** ✔ |
| arrastre corto de 30 px desde `.conteo` | 173 → **316** ✔ |
| tamaño del `#tirador` | 386 × **44 px** ✔ |
| botón de vuelta | 136 × 44, rótulo vivo ("1718 eventos" → "254 eventos" al filtrar) ✔ |

---

## 2. Qué expone `montarHoja()`

Vive en `web/loica.js`, sección **"LA HOJA INFERIOR"**. Es una función global
suelta, como todo en ese archivo (no hay módulos).

```js
const hoja = montarHoja({ /* todo opcional */ });
```

### Opciones

| opción | por defecto | para qué |
|---|---|---|
| `panel`   | `"#panel"`  | selector del panel, en el documento |
| `tirador` | `".tirador"`| selector **dentro** del panel |
| `lista`   | `".lista"`  | selector **dentro** del panel; es el scroller |
| `conteo`  | `".conteo"` | selector **dentro** del panel; segunda zona de agarre |
| `rotulo`  | lee `#conteo` + `#conteo-txt` | función que devuelve el texto del botón de vuelta |
| `idBoton` | `"volver-hoja"` | id del botón flotante que la función **crea** |

### Devuelve

```js
{ fijar(i, conFoco), ocultar(), mostrar(), rotular(), remedir(),
  indice /* getter */, activa /* getter: ¿está en modo hoja? */,
  boton, panel }
```

Devuelve `null` —sin romper nada— si no encuentra el panel o el tirador.

### Globales que deja puestas

- **`window.fijarPanel(i)`** — se conserva **con la misma numeración de
  siempre**, porque `refrescar()` la llama en las cuatro páginas:

  | `i` | tope | alto |
  |---|---|---|
  | `-1` | **oculta** (nuevo) | fuera de pantalla |
  | `0` | reposo | `min(alta, max(cromo + asomo, min(250, disponible × .34)))` |
  | `1` | media | `max(reposo, disponible × .62)` |
  | `2` | alta | `disponible × .88` |

  `disponible` = `panel.parentElement.clientHeight`.

  **El reposo SÍ cambia de alto, y en tres de las cuatro páginas.** (Esta línea
  decía antes que el cálculo "no se toca"; era cierto para mapa.html y falso
  para el resto.) Cada página traía su propia fórmula —talleres
  `min(268, max(132, disp × .40))`, descuentos `min(360, max(170, disp × .52))`—
  y la común es otra. Lo que se conserva de la de mapa es el tramo del medio:
  el 34 % con tope de 250.

  Lo que cambió es el PISO. Era `132`, píxeles pelados que no saben nada de la
  cabecera de cada página, y por eso mapa funcionaba de casualidad y las demás
  no: medido en un iPhone 13, cine abría con 43 px de lista, talleres con 63 y
  descuentos con **cero**. Ahora el piso se mide solo:

  - **`cromo`** = los hijos del panel que no son la `.lista` (tirador,
    cabecera del contador, fila de afinar, el pie del banco en descuentos) más
    los bordes propios del panel. No hay que declarar nada.
  - **`asomo`** = cuánta lista tiene que verse. Se mide la primera fila de
    verdad, con techo de 90 px y descartando lo que no parezca fila (fuera de
    56-132 px: el esqueleto de carga, el cartel de "no hay nada", o los
    envoltorios de día que miden 693 px en cine y 7.566 en descuentos).

  Y el tope de 250 **cede ante el piso**, no al revés: una hoja que abre sin
  una sola fila no es una lista, es una cabecera con barra de agarre.

  Alto de reposo que le queda a cada página (iPhone 13 vertical, medido):

  | página | reposo | cromo | lista visible | % de la pantalla |
  |---|---|---|---|---|
  | mapa | 189 | 99 | 90 | 37 % |
  | cine | 217 | 127 | 90 | 51 % |
  | talleres | 219 | 129 | 90 | 45 % |
  | descuentos | 284 | 194 | 90 | 58 % |

  La regla de diseño —en reposo el mapa se queda con la mayoría de la
  pantalla— se cumple en mapa y talleres. Cine y descuentos se pasan de la
  mitad porque su cromo es más alto (descuentos lleva además un pie fijo de
  68 px), y descuentos ya se daba el 52 % a propósito antes de portarse.
  Bajarlos de ahí es apretarles el cromo, o sea diseño, y no se decide desde
  `loica.js`.

- **`window.hojaLista`** — el mismo objeto de arriba, por si hace falta desde la
  consola o desde otro script.

---

## 3. Qué marcado espera

Lo que ya tienen las cuatro páginas. Nada nuevo que agregar:

```html
<main>                                   <!-- position:relative; su clientHeight define los topes -->
  <div id="mapa"></div>
  <section class="panel-lista" id="panel">
    <div class="tirador" id="tirador"><div class="barra-tirador"></div></div>
    <div class="conteo"><b id="conteo">0</b> <span id="conteo-txt">eventos</span></div>
    <div class="lista" id="lista"></div>
  </section>
</main>
```

- El **`id` del panel** se usa para el `aria-controls` del tirador y del botón.
  Sin `id` funciona igual, pero sin esa relación.
- **`#conteo` y `#conteo-txt`** son los que da el rótulo por defecto del botón.
  Si la página cuenta distinto, pasa `rotulo`.
- **El botón flotante NO va en el HTML**: lo crea `montarHoja()` y lo cuelga de
  `panel.parentElement`. Así portar no obliga a acordarse de un marcado nuevo.
- `role="button"`, `tabindex`, `aria-controls` y `aria-expanded` los pone la
  función. El `aria-label` del tirador **solo** se pone si la página no traía
  uno: cada página nombra lo que lista (eventos, películas, descuentos).

---

## 4. Clases y variables CSS

### Clases que pone y saca el JS (no las escribas a mano)

| clase | dónde | cuándo |
|---|---|---|
| `hoja-viva`   | panel | mientras la hoja está activa (modo celular vertical) |
| `hoja-fuera`  | panel | escondida del todo |
| `arrastrando` | panel | mientras el dedo manda (apaga la transición) |
| `hoja-agarre` | tirador y `.conteo` | zonas que arrastran |

`hoja-fuera` **no es** `oculto`. En `mapa.html`, `.panel-lista.oculto` significa
*"hay una ficha encima"* y lo maneja `abrirFicha()`/`cerrarFicha()`. Son dos
estados distintos que dan la vuelta al mismo lugar; no los mezcles.

### Variables que escribe el JS

- `--alto-panel` — el alto del tope, en px. La página la consume en
  `.panel-lista{height:var(--alto-panel, …)}`.
- `--baja-hoja` — cuánto se desliza la hoja hacia abajo durante el arrastre.
  La consume `loica.css`: `.panel-lista{transform:translateY(var(--baja-hoja,0px))}`.
  Por debajo del reposo la hoja ya no puede encoger (el tirador y el contador
  tienen alto propio), así que **se desliza** en vez de achicarse.

Las dos se escriben **una vez por cuadro** dentro de `requestAnimationFrame`.

### Variables que solo lee

`--hueco-nav`, `--medio`, `--rebote`, `--foco`, `--contorno`, `--fondo-elevado`,
`--tinta`, `--r-pill`, `--repisa-2`, `--t-sm`, `--e-3`, `--e-4`, `--fuente-marca`.

### Qué vive en `loica.css` §4b y qué se queda en la página

**En `loica.css` (común, ya está):** el `transform` de `--baja-hoja`, la
transición de `.hoja-viva`, `.arrastrando`, `.hoja-fuera`, `.hoja-agarre`
(`touch-action:none` + `user-select:none`), los 44 px del tirador, el
`touch-action:pan-y` de la lista, el anillo de foco y **todo** el botón
`.volver-hoja`.

**En la página (propio de ella):** la caja del panel (`position`, `bottom`,
`height:var(--alto-panel)`, `max-height:88%`, colores, ancho de escritorio, sus
media queries) y `.barra-tirador`, que **no es igual en las cuatro** (mapa y
descuentos la tienen 52×7 en tinta; cine y talleres 44×4,5 en borde-fuerte).

---

## 5. Los tres pasos para portar una página

### Paso 1 — cambiar el bloque de JS

Busca en el `<script>` el comentario
`/* --- Arrastre del panel: tres alturas, con gesto de verdad --- */` y borra el
IIFE entero (unas 55 líneas, termina en `addEventListener("resize", () => fijar(indice));})();`).
En su lugar:

```js
/* --- La hoja de la lista: cuatro topes, agarre ancho y botón de vuelta ---
   El arrastre vive en montarHoja() (loica.js). Contrato:
   notas/hoja-movil-contrato.md. El rótulo del botón lo pone ESTA página: la
   hoja no sabe si cuenta películas, descuentos o talleres. */
const hoja = montarHoja({
  rotulo: () => `${document.getElementById("conteo").textContent} ` +
                `${document.getElementById("conteo-txt").textContent}`,
});
```

Tiene que quedar **antes** del bloque de ARRANQUE, que es donde la página llama
`fijarPanel(0)`.

> **Solo si la página llama `fijarPanel` desde `refrescar()`** (a hoy lo hace
> únicamente `mapa.html`; cine, descuentos y talleres **no** la llaman nunca):
> ponle la guarda de la hoja escondida. `mapa.html` sube el panel a media
> cuando la lista queda en cero, para que se lea la salida del callejón; si el
> usuario la escondió a propósito, hacerla saltar sería pisarle una decisión.
>
> ```js
> if(hoja && hoja.indice > HOJA_OCULTA) fijarPanel(1);
> ```

### Paso 2 — podar el `<style>` de la página

Borra lo que ahora vive en `loica.css` §4b:

```css
.panel-lista.arrastrando{transition:none}          /* borrar */
.tirador{padding:9px var(--e-4) 6px;cursor:grab;flex:none;touch-action:none}
.tirador:active{cursor:grabbing}                   /* borrar */
```

y deja el tirador en lo mínimo propio de la página:

```css
/* El resto del tirador —44 px de blanco táctil, cursor, touch-action, anillo
   de foco— vive en loica.css §4b. Acá queda solo lo de esta página. */
.tirador{padding:0 var(--e-4);flex:none}
```

**No toques** `.barra-tirador`, `.panel-lista`, `.lista` ni las media queries:
son de la página. **No borres** `.tirador{display:none}` de los cortes de
escritorio (y de acostado, si la página lo tiene): **esa línea es el
interruptor**. `montarHoja()` decide si es hoja o columna preguntándole al
`display` del tirador, no comparando anchos, justamente porque los cortes no
son los mismos en las cuatro páginas (solo `mapa.html` tiene el layout de
teléfono acostado).

### Paso 3 — subir el `?v=`

Las dos líneas de la página, a `v=26` como mínimo:

```html
<link rel="stylesheet" href="loica.css?v=26">
<script src="loica.js?v=26"></script>
```

No es cosmético: a alguien con la `v=25` en caché le llegaría un `loica.js` sin
`montarHoja` y el script de la página se caería en la primera línea.

> **Pendiente aparte, para quien haga el barrido:** las otras seis páginas
> (`index`, `calendario`, `habla`, `comer`, `blog`, `agrega`), las fichas de
> `web/e/` y la plantilla de `exportar_web.py` siguen en `v=25`. No están rotas
> —no usan nada nuevo— pero la convención del sitio es que las diez vayan
> parejas.

---

## 6. Cómo se verifica (no se supone)

Hay un python sirviendo `web/` en `http://localhost:8777`. Los guiones de
referencia están en el scratchpad de la sesión (`hoja.py`, `hoja2.py`,
`humo.py`) y se copian y adaptan cambiando la URL. El mouse fingido **no
sirve**: hay que mandar toques por CDP.

```python
cdp = ctx.new_cdp_session(page)
cdp.send("Input.dispatchTouchEvent", {"type":"touchStart","touchPoints":[{"x":x,"y":y,"id":1}]})
```

Lo que hay que poder mostrar medido, no supuesto:

1. arrastre desde `.conteo` hacia arriba **cambia el alto**;
2. arrastre desde `.lista` con `scrollTop === 0` hacia abajo **baja la hoja**;
3. arrastre desde `.lista` ya scrolleada **scrollea y no mueve la hoja**;
4. se puede **esconder del todo** y el botón la trae de vuelta;
5. el rótulo del botón **cambia** al cambiar un filtro;
6. **escritorio y acostado no cambiaron**: `.tirador` en `display:none`,
   `hoja-viva` ausente, `--alto-panel` sin fijar, botón oculto;
7. **cero errores de JS** en las diez páginas (el CORS de Cloudflare Insights
   en `localhost` es viejo y no cuenta);
8. **la lista se ve en reposo** en las cuatro páginas: panel, cromo y lista
   visible, como la tabla de la sección 2.

### Dos trampas que ya hicieron pasar una prueba que fallaba

Las dos costaron caro, así que van escritas:

- **Medir solo `alto` no distingue reposo de escondida.** Por debajo del reposo
  la hoja no encoge —el tirador y el contador tienen alto propio— sino que se
  **desliza**, así que `getBoundingClientRect().height` dice 189 en las dos.
  Hay que medir **cuánto de la hoja cae dentro de la pantalla**:
  `max(0, min(caja.bottom, innerHeight) - max(caja.top, 0))`. Cero es
  escondida.
- **Un cambio de alto no prueba que el gesto funcionó.** El arrastre desde la
  lista "pasó" durante una tarde entera midiendo 448 → 316, y lo que había
  detrás era un `pointercancel` que entraba con velocidad guardada y flingeaba
  la hoja un tope. El gesto no movía nada. Para no repetirlo: **medir durante
  el gesto, no solo al final** (tres tomas mientras el dedo baja), y **soltar
  lento** —una pausa de ~300 ms antes del `touchEnd`— cuando lo que se quiere
  aislar no es el envión.

---

## 7. Decisiones que parecen raras y no lo son

- **`touch-action:none` va SOLO en las zonas de agarre.** Cuando estuvo en el
  panel entero, el navegador cancelaba el scroll de la lista: 37.000 px de
  eventos en una caja que no se movía con el dedo. La lista se queda en `pan-y`.
- **La lista va por Touch Events y el resto por Pointer Events, y no es
  capricho: es lo único que funciona.** El tirador y el contador llevan
  `touch-action:none`, así que ahí no hay scroller peleando y Pointer Events
  anda perfecto. La lista lleva `pan-y` —tiene que scrollear— y eso significa
  que el gesto vertical es del scroller nativo. Medido en Chromium con toques
  reales: llega `pointerdown`, UNO o dos `pointermove`, y `pointercancel`. Se
  acabó. Pointer Events y querer interceptar un gesto vertical dentro de un
  scroller son incompatibles por construcción, y la primera versión de esta
  función lo intentaba: **el arrastre desde la lista no movía la hoja ni un
  píxel** (448 → 448 medido durante el gesto, no solo al final).

  La salida es la de las librerías de bottom sheet: `touchmove` en la lista con
  `{passive:false}` y `preventDefault()`. Eso hace dos cosas a la vez, y por eso
  es la línea entera del arreglo: le avisa al navegador **antes** del gesto que
  acá alguien podría cancelarlo —y entonces marca los `touchmove` como
  `cancelable`, que con todos los listeners pasivos llegaban en `false` desde el
  primero y `preventDefault()` no habría hecho nada— y frena el scroll de verdad
  cuando decidimos quedarnos el gesto. **El `{passive:false}` tiene que ir en el
  registro: después no se cambia.**
- **La lista se lleva el gesto solo si va hacia abajo, más vertical que
  horizontal, con `scrollTop === 0` y con el evento todavía `cancelable`.** Es
  el patrón de Google Maps y Apple Maps. Y no se decide en el `touchstart` sino
  en el primer movimiento que pasa los 8 px: antes de eso no se sabe si el dedo
  viene a scrollear o a bajar la hoja, y adivinar mal rompe una de las dos
  cosas.
- **La lista no captura el puntero, y de hecho ya no escucha punteros.**
  `setPointerCapture` sobre un scroller mata su propio scroll. En el tirador y
  el contador sí se pide, pero no se confía: los `move`/`up` se escuchan en
  `window`, porque Safari suelta la captura a mitad de gesto y la hoja quedaba
  colgada entre dos topes. En el camino de Touch no hacen falta listeners en
  `window`: un `Touch` le pertenece al elemento donde empezó durante toda su
  vida.
- **Un `pointercancel` no es un `pointerup`.** Cancelar significa que el sistema
  se llevó el dedo, así que se cae al tope más cercano **sin envión y sin la
  regla del arrastre decidido**. Era un error real: con `pan-y` en la lista,
  Chromium mandaba dos `pointermove` antes del cancel, con eso se guardaba una
  velocidad de 0,5 px/ms, el cancel entraba por la misma puerta que un soltar
  normal y la hoja se iba un tope abajo (448 → 316) por un gesto que el
  navegador ya había dado por muerto. Peor todavía: eso hacía **pasar** una
  prueba que en realidad estaba fallando.
- **El click sintético se suprime con `seMovio`, no con `arrastrando`.** El
  `click` llega **después** del `pointerup`, cuando cualquier bandera de "estoy
  arrastrando" ya se apagó. Ésa era la guarda vieja y no protegía nada: cada
  arrastre adelantaba un tope de más.
- **La hoja se remide sola; no hay que llamarla.** Nace antes de que la página
  termine de pintarse, y ahí sus cuentas salen desfasadas: medido en talleres,
  al montarse el marco decía 565 px cuando el definitivo son 492. Un
  `ResizeObserver` mira el marco (que encoge cuando la cabecera crece al llegar
  el JSON) y el cromo del panel (la cabecera del contador envuelve a dos líneas
  cuando aparece la nota del catastro). **Ninguna página necesita llamar
  `remedir()` después de cargar los datos**; `mapa.html` conserva su
  `fijarPanel(0)` post-cabecera porque no molesta, pero ya no hace falta.
- **El gesto arranca AUNQUE el dedo caiga sobre un botón.** La primera versión
  se negaba a empezar si el toque era sobre un control, y eso mataba medio
  agarre justo donde más falta hacía: en cine el conmutador Cines/Películas/Qué
  ver vive dentro del `.conteo` y se lleva 219 de sus 386 px, así que barriendo
  el ancho con toques reales la hoja solo arrancaba en el 50 % de los puntos
  (mapa, sin controles ahí, daba 100 %). Ahora decide el desenlace, como en las
  hojas nativas: un guardia de `click` en captura sobre el panel se traga el
  click cuando el dedo se movió más de 8 px, y lo deja pasar cuando no. Toque
  limpio sobre el conmutador → cambia de vista; arrastre que empieza sobre ese
  mismo botón → mueve la hoja y no conmuta. **Si agregas un control dentro del
  `.conteo`, no hay nada que registrar: ya está cubierto.**
- **La selección de texto se apaga solo mientras se arrastra, y solo fuera del
  tirador.** Al convertir el `.conteo` en zona de agarre se le puso
  `user-select:none`, y eso dejaba sin copiar la nota del catastro que talleres
  y descuentos pintan ahí ("31 no declaran sus días · 195 no publican precio").
  No se notó en mapa porque ahí no hay nada copiable — el riesgo de decidir
  mirando una sola página. Ahora el apagado cuelga de `.hoja-moviendo`, que el
  JS pone recién al pasar el umbral de 8 px: en reposo y con un pulso largo el
  texto se selecciona y se copia como en cualquier parte. El tirador es la
  excepción y lo lleva siempre: es un control, no tiene texto que copiar.
- **El tirador pasó de 29 a 44 px** y eso le quita 15 px de lista al reposo. Es
  el precio y se paga: es lo que mide un pulgar, y además ahora la cabecera del
  contador también arrastra, así que la banda de agarre pasó de 29 px a más de
  90.
- **Escondida, la hoja lleva `inert`.** Fuera de pantalla seguía teniendo
  tarjetas alcanzables con Tab.
- **Acostado, cine y descuentos no tienen arreglo desde `loica.js`.** Medido a
  844×390: el marco útil de cine queda en 152 px y su cromo mide 127, y el de
  descuentos en 218 con 178 de cromo. Aunque la hoja se llevara el marco
  entero, quedarían 25 y 40 px de lista. No es el piso del reposo: es que en
  horizontal esas cabeceras no dejan sitio. `mapa.html` lo resuelve con un
  corte propio —`max-width:879px and max-height:460px` manda la lista a una
  columna al costado— y esas dos páginas no lo tienen. **El arreglo es ese
  corte, en la CSS de cada página, y es una decisión de maquetación, no de la
  mecánica de la hoja.** Talleres, con menos cromo, sí abre con lista (79 px).
- **"Escondida" quiere decir fuera del VIEWPORT, no detrás de la barra de
  abajo.** Con el `translateY(104%)` que usa la ficha quedaban 51 px de hoja
  dentro de la pantalla: invisibles porque la barra inferior es opaca, pero
  ahí. Se baja su propio alto **más `--hueco-nav`**, y así la medida honesta
  —cuánto de la hoja cae dentro de la pantalla— da cero.
- **Soltar rápido salta un tope; soltar lento cae en el más cercano.** Es lo
  pedido y es lo que hace cualquier hoja nativa, pero tiene una consecuencia
  para quien escriba pruebas: **un arrastre rápido y largo NO termina en el
  tope más cercano al punto donde soltó el dedo**, termina uno más allá. Una
  prueba que quiera aislar el *click* fantasma tiene que soltar LENTO —una
  pausa de ~300 ms entre el último `touchMove` y el `touchEnd`— porque si no,
  el envión y el click fantasma producen el mismo síntoma y no se distinguen.
  El umbral está en `HOJA_ENVION` (0,45 px/ms) y la velocidad se descarta si
  el último movimiento fue hace más de `HOJA_VELOCIDAD_VIEJA` (120 ms).
