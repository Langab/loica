# Crítica de diseño — Loica web

**Fecha:** 9 de agosto de 2026
**Archivos revisados:** `loica.css`, `loica.js`, `index.html`, `calendario.html`, `agrega.html`, `nosotros.html`
**Método:** lectura de código + render real en navegador a 1280×800 y 390×844, en modo claro y oscuro, con los 95 eventos reales de `eventos.json`. Todos los números de contraste, alturas y píxeles de este informe están medidos, no estimados.
**Veredicto:** **HOLD.** El sistema está bien construido por debajo; lo que falla es la capa de decisiones visibles. Hoy la app se puede leer como "plantilla bien ejecutada" y no como "producto diseñado para Santiago".

---

## 0. El lente de producto (contra esto juzgo todo lo demás)

El usuario es el santiaguino de 18 a 44 que tiene dos minutos para decidir su viernes, y el turista que no lee español. La pregunta que abre la app es siempre la misma: **"¿qué hay hoy, dónde, y cuánto sale?"** El objeto de primera lectura debería ser *un panorama concreto con su hora*. La acción primaria es *ir a la fuente del evento*.

Dato que cambia todo: de los 95 eventos, **solo 9 tienen imagen** y **51 no tienen precio**. Es decir, la tarjeta vacía **es** la tarjeta normal. Cualquier diseño que asuma foto y precio está diseñando el caso raro.

---

## A. Las 3 cosas que más delatan que no lo diseñó un profesional

### A1 — La escala tipográfica no tiene saltos: cuatro tamaños dentro de 4,5 px hacen el 95% de la interfaz

**Archivo:** `loica.css`, líneas **35-36** y **174-181**.

```css
/* loica.css:35-36 — ACTUAL */
--t-xs:11.5px; --t-sm:13px; --t-base:14.5px; --t-md:16px;
--t-lg:20px; --t-xl:26px; --t-2xl:34px; --t-3xl:46px;
```

Los saltos reales son: 11,5 → 13 (×1,13) → 14,5 (×1,115) → 16 (×1,10). Y después, de golpe, ×1,25 / ×1,30 / ×1,31 / ×1,35. O sea: **la escala es plana justo donde trabaja** y se abre solo en los títulos grandes que casi no se usan. Medido en la tarjeta de evento:

| Elemento | Tamaño | Peso |
|---|---|---|
| `.tarjeta h3` (el nombre del panorama) | 14,5 px | 720 |
| `.tarjeta-meta` (lugar, precio) | 13,0 px | 400 |

**1,5 px de diferencia entre el título de un evento y su letra chica.** El ojo no distingue eso. Toda la jerarquía de la lista está sostenida por el peso, no por el tamaño, y por eso la lista se lee como un bloque gris parejo.

Además hay dos huellas dactilares del código generado:

1. **`font-weight:720`** (`loica.css:175`). Manrope se carga en `wght@400;500;650;750;800` (`index.html:10`). Verifiqué en el navegador: solo hay instancias en 400, 650, 750 y 800. **720 renderiza exactamente igual que 750.** Es precisión inventada: se ve "afinado" en el código y no cambia ni un píxel en pantalla.
2. **Los medios píxeles**: 11,5 / 14,5 / 10,5 (`loica.css:171`). Nadie diseña una escala en medios píxeles; eso sale de ir empujando valores hasta que "se vea bien".

**Reemplazo concreto:**

```css
/* loica.css:35-36 — PROPUESTO */
--t-xs:11px; --t-sm:13px; --t-base:15px; --t-md:17px;
--t-lg:21px; --t-xl:28px; --t-2xl:38px; --t-3xl:52px;
```

```css
/* loica.css:174-177 — PROPUESTO */
.tarjeta h3{
  font-family:var(--fuente-ui);
  font-size:var(--t-md);          /* 14,5 -> 17: el salto que faltaba */
  font-weight:700;                /* 720 -> 700: un peso que existe de verdad */
  line-height:1.26;
  letter-spacing:-.012em;         /* óptica: a 17px el texto pide cerrarse un pelo */
  margin-bottom:5px;              /* 3 -> 5: separa el título de su metadata */
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}
```

Y en `index.html:10`, `calendario.html:10`, `agrega.html:10`, `nosotros.html:10`, pasar a rango variable para que cualquier peso sea real:

```html
<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600..800&family=Manrope:wght@400..800&display=swap" rel="stylesheet">
```

**Por qué:** con 17/700 contra 13/400 la razón título:metadata sube de **1,115 a 1,31**. Ese es el rango donde el ojo *sabe* qué leer primero sin pensarlo. Y el `line-clamp:2` arregla de paso el ritmo: medí las 14 primeras tarjetas y miden **87, 103, 87, 87, 122, 103, 103, 103, 122, 140, 122, 122, 140, 103 px**. Un 60% de variación porque hay 27 títulos de más de 60 caracteres y 16 de más de 80. Con el clamp quedan en dos alturas.

---

### A2 — La tarjeta de evento dice la categoría tres veces y la hora ninguna

**Archivos:** `loica.js`, líneas **206-229** (`tarjetaEvento`) y **198-201** (`textoPrecio`).

Lo que hoy muestra una tarjeta, en orden de peso visual:

1. Una miniatura de 62×62 con la mascota (86 de 95 veces es eso, no una foto).
2. El título.
3. La mascota **otra vez**, a 15 px, junto al nombre de la categoría **escrito**.
4. El lugar.
5. El precio — que en **51 de 95 casos es un guion: `—`**.

Y una franja negra de 10,5 px con "9 ago" pegada abajo de la miniatura.

O sea: la categoría aparece **tres veces** (miniatura + ícono inline + texto) y la **hora no aparece nunca**, cuando 43 de los 95 eventos tienen hora real. Para un producto cuyo caso de uso declarado es "es viernes 19:00, estoy en Providencia, ¿qué hay?", eso es el error de jerarquía más caro del proyecto. Las dos cosas que deciden si voy o no —**a qué hora** y **cuánto sale**— son los dos elementos más chicos y débiles de la tarjeta.

Y `—` no es honestidad, es un campo roto. La propia estrategia de marca dice: *"Honesta: dice el precio real, avisa si un dato no está verificado"*.

**Reemplazo concreto** — `loica.js:198-201`:

```js
function textoPrecio(ev){
  if(ev.gratis) return t("gratis");
  if(ev.precio) return "$" + ev.precio.toLocaleString("es-CL");
  return t("sinPrecio");     // añadir a TEXTOS: es "Precio en la fuente" / en "Price at source" / pt "Preço na fonte"
}
const horaCorta = ev => (ev.fecha.getHours() || ev.fecha.getMinutes())
  ? ev.fecha.toLocaleTimeString(localeDe(),{hour:"2-digit",minute:"2-digit",hour12:false})
  : "";
const etiquetaDia = f => {
  const hoy = new Date(), man = new Date(Date.now()+864e5);
  if(mismaFecha(f,hoy)) return t("hoy").toUpperCase();
  if(mismaFecha(f,man)) return t("manana").toUpperCase();
  return `${t("dias")[(f.getDay()+6)%7]} ${f.getDate()}`;
};
```

`loica.js:211-226` — nuevo cuerpo de la tarjeta:

```js
boton.innerHTML = `
  <div class="miniatura">
    ${ev.imagen ? `<img src="${escapar(ev.imagen)}" alt="" loading="lazy">`
                : mascota(info.mascota, info.hex, 34)}
    <span class="dia">${etiquetaDia(ev.fecha)}</span>
  </div>
  <div class="tarjeta-cuerpo">
    <h3>${escapar(ev.titulo)}</h3>
    <div class="tarjeta-meta">
      ${horaCorta(ev) ? `<time class="hora">${horaCorta(ev)}</time>` : ""}
      <span class="lugar">${escapar(ev.lugar)}</span>
    </div>
  </div>
  <div class="tarjeta-precio">
    <span class="precio${ev.gratis ? " libre" : ""}">${textoPrecio(ev)}</span>
  </div>`;
```

`loica.css:154-183` — la tarjeta pasa de flex a grilla de tres columnas, con el precio anclado a la derecha:

```css
.tarjeta{
  display:grid;grid-template-columns:56px minmax(0,1fr) auto;
  gap:var(--e-3);align-items:start;
  padding:var(--e-4);border-bottom:1px solid var(--borde);cursor:pointer;
  background:var(--fondo-elevado);text-align:left;width:100%;border-left:0;border-right:0;border-top:0;
  font-family:inherit;color:inherit;transition:background var(--rapido);
}
.miniatura{width:56px;height:56px}
.miniatura .dia{
  font:800 9.5px/1.4 var(--fuente-ui);letter-spacing:.06em;
  font-variant-numeric:tabular-nums;text-transform:uppercase;
}
.tarjeta-meta{
  display:flex;flex-wrap:wrap;gap:2px var(--e-2);align-items:baseline;
  font-size:var(--t-sm);color:var(--tinta-suave);
}
.hora{
  font-weight:750;color:var(--tinta);
  font-variant-numeric:tabular-nums;letter-spacing:-.01em;
}
.hora::after{content:"·";margin-left:var(--e-2);color:var(--tinta-tenue);font-weight:400}
.tarjeta-precio{padding-top:2px;text-align:right}
.precio{
  font-size:var(--t-sm);font-weight:800;color:var(--tinta);
  font-variant-numeric:tabular-nums;letter-spacing:-.02em;white-space:nowrap;
}
.precio.libre{
  color:var(--gratis);font-size:var(--t-xs);
  text-transform:uppercase;letter-spacing:.07em;
}
```

Y **borrar** el `<span class="mascota-nombre">` de `loica.js:222`. La mascota ya está en la miniatura y el color de la gota ya dice la categoría en el mapa; repetirla tres veces no es identidad, es ruido.

**Por qué:** el precio pasa a ser una columna alineada a la derecha con cifras tabulares — se escanea verticalmente, que es como uno compara precios. La hora entra en negrita al principio de la línea de metadata, que es donde el ojo cae después del título. Y "HOY" / "MAÑANA" en la miniatura convierte un dato neutro (9 ago) en una señal de urgencia, que es literalmente el diferenciador #1 del producto contra Instagram.

---

### A3 — El mapa es OpenStreetMap crudo, y el modo oscuro no lo toca

**Archivo:** `index.html`, líneas **111-118**.

```js
style:{version:8,
  sources:{osm:{type:"raster",
    tiles:["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", ...
```

La pantalla insignia del producto —la que la estrategia de marca define como *"la decisión donde marca y producto se funden"*— usa el estilo por defecto de OpenStreetMap. En la captura a 390 px conté **más de 25 íconos POI propios de OSM contra 3 pines de Loica**. Las calles amarillas y naranjas, los parques verdes fuertes y las etiquetas azules de OSM tienen más saturación que los datos de Loica. **El producto pierde contra su propio fondo.**

Y esto es lo grave: **en modo oscuro el mapa sigue siendo diurno**. Cambia la barra, cambian los chips, cambia el panel — y el 60% de la pantalla se queda blanco brillante. La estrategia de marca dice, textual, que *"modo oscuro es obligatorio y de primera clase — la app se usa de noche, buscando carrete"*. Hoy el modo oscuro es maquillaje sobre el cromo.

Encima, el color de categoría más frecuente es el más invisible: **34 de los 95 eventos son `otros`** y `--c-otros:#8C93A8` (`loica.css:89`) tiene **2,43:1 contra el gris del mapa OSM** — por debajo del 3:1 mínimo para elementos gráficos. El pin más común de la app es el que menos se ve.

**Reemplazo concreto** — `index.html:109-118`:

```js
const TESELAS = {
  claro : ["https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
           "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
           "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png"],
  oscuro: ["https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
           "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
           "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png"]
};
const temaActivo = () => document.documentElement.dataset.tema
  || (matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro");

const mapa = new maplibregl.Map({
  container:"mapa",
  style:{version:8,
    sources:{base:{type:"raster",tiles:TESELAS[temaActivo()],tileSize:256,
      attribution:'© OpenStreetMap © CARTO'}},
    layers:[{id:"base",type:"raster",source:"base"}]},
  center:[-70.645,-33.437], zoom:12.5, attributionControl:{compact:true}
});
// al alternar tema, cambiar las teselas
window.addEventListener("loica:tema", () =>
  mapa.getSource("base").setTiles(TESELAS[temaActivo()]));
```

(y en `loica.js:144-149`, que `alternarTema()` dispare `window.dispatchEvent(new CustomEvent("loica:tema"))`, igual que ya hace `fijarIdioma` con `loica:idioma`).

Encima, en `index.html:18`, teñir el basemap a crema papel para que sea de Loica y no de CARTO — el filtro toca solo el canvas, no los pines (que son DOM):

```css
#mapa .maplibregl-canvas{filter:sepia(.20) saturate(.68) brightness(1.03)}
:root[data-tema="oscuro"] #mapa .maplibregl-canvas{filter:saturate(.7) brightness(.95)}
```

Y los dos colores de categoría que no llegan a 3:1 — `loica.css:82-90`:

```css
:root{
  --c-fiesta:#7A4FCF;      /* Culpeo   — 4,84:1 sobre basemap claro ✓ */
  --c-musica:#1E2A4A;      /* Cóndor   — azul cordillera: lo masivo, el cielo alto. 12,5:1 */
  --c-cultura:#2F6FB5;     /* Chinchilla — 4,59:1 ✓ */
  --c-clases:#B8690B;      /* Chincol  — era #E08A1E: 2,38:1. Ahora 3,68:1 */
  --c-libre:#2E7D5B;       /* Pudú     — 4,43:1 ✓ */
  --c-otros:#E8442E;       /* Loica    — su mascota ES la loica y su pecho rojo ES el pin
                              (estrategia_marca §5). Era gris a 2,43:1; ahora 3,52:1 */
}
```

**Por qué:** con esto el mapa se vuelve el papel y los pines la tinta — que es la única razón por la que un mapa existe en este producto. Y la categoría más común deja de ser la invisible.

> **Nota de producto, no de diseño:** 34 de 95 eventos en `otros` y 38 en cultura significa que dos mascotas cargan el 76% de los pines, y **el Culpeo aparece en exactamente 1 pin de 95**. El sistema de seis mascotas está diseñado para una distribución de categorías que los datos no tienen. Esto se arregla en el clasificador del pipeline, no en el CSS, pero mientras no se arregle, la promesa de "reconoces la categoría antes de leer una palabra" (`nosotros.html:134`) no se cumple.

---

## B. 12 mejoras puntuales, ordenadas por impacto visual

### B1 — La ficha de evento esconde el botón principal 147 px bajo el borde

**Archivo:** `index.html`, líneas **42-52** y **217-239**.

Medido en 1280×800 con la ficha abierta: `scrollHeight 747 px` dentro de `clientHeight 517 px`. El `<a class="boton bloque">` con "Ver en la fuente original" queda en `top: 905 px` en una ventana de 800. **La acción primaria del producto no se ve.** Y arriba de todo hay 150 px de `.ficha-foto` (el 29% de la ficha visible) que para 86 de 95 eventos es un rectángulo beige con un dibujo.

```css
/* index.html:49-52 — PROPUESTO */
.ficha-foto{height:132px;background:var(--fondo-hundido);position:relative;
  border-radius:var(--r-xl) var(--r-xl) 0 0;overflow:hidden}
.ficha-foto:empty{display:none}          /* sin imagen, sin caja vacía */
.ficha-cuerpo{padding:var(--e-5) var(--e-5) 0}
.ficha-cta{
  position:sticky;bottom:0;z-index:2;
  background:var(--fondo-elevado);
  padding:var(--e-3) var(--e-5) var(--e-5);
  box-shadow:0 -1px 0 var(--borde), 0 -10px 16px -12px rgba(30,42,74,.25);
}
```

```js
// index.html:218-223 — la foto solo existe si hay foto
${ev.imagen ? `<div class="ficha-foto"><img src="${escapar(ev.imagen)}" alt=""
     onerror="this.closest('.ficha-foto').remove()"></div>` : ""}
// index.html:236-238 — el CTA se envuelve y se ancla
<div class="ficha-cta">
  <a class="boton bloque" href="${escapar(ev.url)}" target="_blank" rel="noopener">${t("ir")} ↗</a>
  <div class="fuente-pie">${t("fuente")} <b>${escapar(ev.fuente)}</b></div>
</div>
```

Sin foto, la ficha abre directo en **categoría → título → cuándo → dónde → cuánto**, y el botón queda siempre pegado abajo. Eso es una ficha de evento; lo de hoy es una tarjeta de blog.

---

### B2 — El botón de cerrar la ficha tiene 1,08:1 de contraste

**Archivo:** `index.html`, líneas **53-57**.

`background:rgba(250,243,231,.94)` (crema) sobre `.ficha-foto{background:var(--fondo-hundido)}` (#F2E9D9, crema hundido). Contraste medido: **1,08:1**. Es un botón invisible. Lo irónico es que en modo oscuro sí se ve perfecto, porque el crema queda sobre navy — está exactamente al revés.

```css
/* index.html:53-57 — PROPUESTO */
.cerrar{
  position:absolute;top:10px;right:10px;
  background:var(--fondo-elevado);color:var(--tinta);
  border:1px solid var(--borde-fuerte);
  width:36px;height:36px;border-radius:50%;font-size:19px;cursor:pointer;
  line-height:1;box-shadow:var(--sombra-1);
}
.cerrar:hover{background:var(--fondo-hundido)}
```

---

### B3 — En celular, el 75% de la navegación está escondida tras un scroll invisible

**Archivo:** `loica.css`, líneas **117-118**.

Medido a 390 px: `.nav` tiene **374 px de contenido en una ventana de 93 px → 281 px ocultos**. Se ven "Mapa" y media palabra de "Cal…". Calendario, Agrega tu evento y Nosotros son inalcanzables salvo que descubras que la barra se arrastra — y la barra de scroll está deliberadamente escondida (`scrollbar-width:none`, `::-webkit-scrollbar{display:none}`).

Encima, el selector de idioma (tres botones de 32×28 px) ocupa esquina superior derecha, más prominente que la mitad de la navegación.

En celular la navegación va abajo, al alcance del pulgar. Eso es literalmente lo que pidió el fundador ("que sirva para celulares sin perder la comodidad"):

```css
/* loica.css, añadir al final de §3 */
@media(max-width:879px){
  .barra .nav{
    position:fixed;left:0;right:0;bottom:0;z-index:20;margin:0;overflow:visible;
    display:grid;grid-template-columns:repeat(4,1fr);gap:0;
    background:var(--fondo-elevado);border-top:1px solid var(--borde);
    padding-bottom:env(safe-area-inset-bottom);
  }
  .barra .nav a{
    border-radius:0;min-height:52px;padding:8px 4px;
    display:flex;align-items:center;justify-content:center;
    font-size:var(--t-xs);text-align:center;
  }
  .barra .nav a[aria-current="page"]{
    background:transparent;color:var(--acento);
    box-shadow:inset 0 2px 0 var(--acento);
  }
  /* el idioma deja de gritar: solo el activo, con menú */
  .idiomas button[aria-pressed="false"]{display:none}
  .idiomas.abierto button{display:inline-block}
}
```

Y en `index.html:29-34`, subir el panel para que no quede bajo la barra:
`.panel-lista{bottom:52px}` y `.ficha{bottom:52px}` dentro del mismo media query.

---

### B4 — Todos los controles táctiles están bajo los 44 px

Medido a 390 px:

| Control | Alto real | Mínimo |
|---|---|---|
| `.nav a` (`loica.css:119-123`) | 34 px | 44 |
| `.idiomas button` (`loica.css:129-133`) | 28 px | 44 |
| `.tema` (`loica.css:135`) | 26 px | 44 |
| `.chip` (`loica.css:141-147`) | 36 px | 44 |
| `.boton` (`loica.css:186-192`) | 42 px | 44 |

```css
/* loica.css:141-147 */
.chip{
  flex:none;display:inline-flex;align-items:center;gap:7px;min-height:44px;
  border:1.5px solid var(--borde);background:var(--fondo-elevado);color:var(--tinta);
  padding:0 16px 0 11px;border-radius:var(--r-full);
  font:650 var(--t-sm)/1 var(--fuente-ui);cursor:pointer;white-space:nowrap;
  transition:background var(--rapido),border-color var(--rapido);
}
/* loica.css:129-133 */
.idiomas button,.tema{min-height:36px;min-width:38px;padding:8px 10px; /* ...resto igual */ }
/* loica.css:186-192 */
.boton{padding:15px var(--e-6);min-height:48px; /* ...resto igual */ }
```

---

### B5 — Trece chips idénticos: los dos filtros que importan pesan igual que "Teatro"

**Archivos:** `loica.css:138-152`, `index.html:148-173`.

En la barra de filtros hay 13 chips exactamente iguales: mismo alto (36 px), mismo radio (999 px), mismo peso (650), mismo tamaño (13 px). "Gratis", "Hoy" y "Este finde" —los tres que responden la pregunta real del usuario— están mezclados con diez categorías. A 390 px se ven cuatro; los otros nueve están tras un scroll sin pista visual (`filtros.scrollWidth 1276` contra `clientWidth 390`).

```css
/* loica.css:138-140 — PROPUESTO */
.filtros{
  display:flex;gap:var(--e-2);overflow-x:auto;padding:var(--e-3) var(--e-4);
  scrollbar-width:none;background:var(--fondo-elevado);border-bottom:1px solid var(--borde);
  -webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 32px),transparent);
  mask-image:linear-gradient(90deg,#000 calc(100% - 32px),transparent);
}
.filtros .sep{
  flex:none;width:1px;align-self:stretch;margin:4px var(--e-2);background:var(--borde);
}
.chip.primario{border-color:var(--borde-fuerte);font-weight:750}
```

```js
/* index.html:164, después del chip "Este finde" */
cont.insertAdjacentHTML("beforeend",'<span class="sep" aria-hidden="true"></span>');
```

Y añadir `"primario"` a la clase de los tres primeros chips (`index.html:161-164`). Un separador de 1 px hace más por la jerarquía que cualquier gradiente.

---

### B6 — El calendario es Google Calendar: los días vacíos pesan lo mismo que los llenos, y el sábado se ve igual que el martes

**Archivo:** `calendario.html`, líneas **41-59** y **194-206**.

En agosto 2026 hay **17 celdas de 31 sin ningún evento**, y cada una es una caja blanca de borde 1,5 px del mismo tamaño que un día con 26 eventos. Más de la mitad de la pantalla es vacío con peso completo. Y `LUN MAR MIÉ JUE VIE SÁB DOM` están todos en el mismo gris al mismo peso — en una app de panoramas, el fin de semana es la única distinción que el usuario realmente busca.

```css
/* calendario.html:36-39 */
.encabezado-dias span:nth-child(6),
.encabezado-dias span:nth-child(7){color:var(--acento)}

/* calendario.html:41-45 — los días sin nada dejan de competir */
.dia.sin-eventos{background:transparent;border-style:dashed;border-color:var(--borde)}
.dia.sin-eventos .dia-num{color:var(--tinta-tenue);font-weight:650}

/* fin de semana con papel distinto */
.rejilla .dia:nth-child(7n-1),
.rejilla .dia:nth-child(7n){background:var(--fondo)}

/* el dato que sí sirve: cuántos hay */
.dia-total{
  margin-top:auto;align-self:flex-end;
  font-size:var(--t-xs);font-weight:800;color:var(--tinta-suave);
  font-variant-numeric:tabular-nums;
}
```

```js
/* calendario.html:187 */
celda.className = "dia"
  + (delDia.length ? "" : " sin-eventos")
  + (dia.getMonth() !== mesVisible.getMonth() ? " fuera" : "")
  /* ...resto igual */;
/* calendario.html:203-206 — el total reemplaza al "+N" */
celda.innerHTML = `<span class="dia-num">${dia.getDate()}</span>
  ${marcas}
  <span class="puntos">${puntos}</span>
  ${delDia.length ? `<span class="dia-total">${delDia.length}</span>` : ""}`;
```

Bonus: los tres títulos truncados por celda (`.marca-ev`, 10,5 px con `text-overflow:ellipsis`) se cortan a unos 18 caracteres — "Prenderse fuego, 1", "Entrenamiento pa". En Google Calendar eso funciona porque son *tus* eventos y los reconoces; acá el usuario no conoce ninguno, así que un título cortado no informa nada. Si hay que elegir, el número de eventos y el punto verde de "hay algo gratis" valen más que tres fragmentos ilegibles.

---

### B7 — El `+23` fantasma en el calendario móvil

**Archivo:** `calendario.html`, línea **74**.

`@media(max-width:900px){ .marca-ev{display:none} }` esconde las etiquetas de eventos pero **no esconde `.mas`**. Resultado real en pantalla: el día 11 muestra `11`, después `+23`, después cuatro puntitos. El "+23" era "hay 23 más además de los 3 que ves" — pero los 3 ya no están. Es un residuo del layout de escritorio, visible en el primer scroll de cualquiera que abra el calendario en el celular.

```css
/* calendario.html:74 */
.marca-ev,.mas{display:none}
```

---

### B8 — Hoy no hay ni estado de carga ni estado de error, y el mensaje de error ya está escrito en la estrategia de marca

**Archivos:** `index.html:133`, `calendario.html:121-126`.

```js
cargarEventos().then(evs => { EVENTOS = evs; pintarFiltros(); refrescar(); });
```

Sin `.catch` en ningún archivo (lo verifiqué con grep: cero coincidencias en todo el proyecto). Si `eventos.json` (73 KB) tarda o falla, el usuario ve **"0 eventos"** y un mapa pelado — o sea, la app de "Santiago está pasando" le dice que en Santiago no pasa nada. Es el peor primer contacto posible y es silencioso.

```js
/* index.html:133 — PROPUESTO */
pintarEsqueleto();      // 6 tarjetas placeholder antes del fetch
cargarEventos()
  .then(evs => { EVENTOS = evs; pintarFiltros(); refrescar(); })
  .catch(() => {
    document.getElementById("lista").innerHTML = `
      <div class="vacio">
        ${mascota("loica","var(--tinta-suave)",64)}
        <p class="vacio-tit">${t("errorTit")}</p>
        <button class="boton secundario" onclick="location.reload()">${t("errorAccion")}</button>
      </div>`;
  });
```

```js
/* loica.js:90-101 — el copy YA existe en estrategia_marca §3, solo hay que usarlo */
errorTit:"Se nos enredó el mapa",  errorAccion:"Dale de nuevo",
```

```css
/* loica.css — esqueleto de carga */
.tarjeta.cargando{pointer-events:none}
.tarjeta.cargando .miniatura,
.tarjeta.cargando h3,
.tarjeta.cargando .tarjeta-meta{
  background:var(--fondo-hundido);color:transparent;border-radius:var(--r-sm);
  animation:latir 1.4s ease-in-out infinite;
}
@keyframes latir{0%,100%{opacity:1}50%{opacity:.45}}
```

---

### B9 — El estado vacío es un callejón sin salida, con la mascota a `opacity:.5`

**Archivos:** `index.html:201-205`, `loica.css:218-219`.

Filtré "Gratis + Fiestas" (combinación que da 0 de 95) y la pantalla queda así: el mapa sin un solo pin y un panel de 396×750 px con un pajarito desvaído al 50% flotando en el vacío, dos líneas de texto y **ningún botón**. Para salir hay que acordarse de cuáles chips uno prendió.

Tres cosas:

1. `opacity:.5` (`loica.css:219`) es el atajo del generador para decir "esto es sutil". Hace que la mascota parezca deshabilitada, no diseñada. Se reemplaza por un color real.
2. El copy es la versión genérica. La estrategia de marca §3 ya trae la buena: *"Nada con esos filtros por acá. Prueba soltando el filtro de precio o mirando otro barrio"*.
3. Falta la salida.

```css
/* loica.css:218-219 — PROPUESTO */
.vacio{padding:var(--e-10) var(--e-5);text-align:center;color:var(--tinta-suave)}
.vacio svg{width:64px;height:64px;margin:0 auto var(--e-4)}   /* fuera el opacity */
.vacio-tit{font-family:var(--fuente-marca);font-size:var(--t-lg);font-weight:800;
  color:var(--tinta);margin:0 0 var(--e-1)}
.vacio-pista{font-size:var(--t-sm);margin:0 0 var(--e-5)}
```

```js
/* index.html:201-205 */
cont.innerHTML = `<div class="vacio">
  ${mascota("pudu","var(--tinta-suave)",64)}
  <p class="vacio-tit">${t("vacio")}</p>
  <p class="vacio-pista">${t("vaciopista")}</p>
  <button class="boton secundario" onclick="limpiarFiltros()">${t("limpiar")}</button>
</div>`;
```

```js
/* loica.js:95 — copy con voz, el que ya está escrito en la estrategia */
vacio:"Nada con esos filtros por acá",
vaciopista:"Prueba soltando el filtro de precio o mirando otro barrio",
limpiar:"Quitar filtros",
```

Y usar al **Pudú** (la mascota de lo gratis) en vez de la Loica: si el filtro de precio es el que suele dejar la lista en cero, la mascota del vacío debería ser la que te sugiere soltarlo. Eso es un detalle de sistema, no de decoración.

---

### B10 — El lema de la marca está escrito en el código y no aparece en ninguna pantalla

**Archivo:** `loica.js`, líneas **91 / 103 / 115**.

```js
lema:"Santiago está pasando",
```

Está definido en los tres idiomas y **nunca se renderiza**. Lo comprobé con grep: `lema` solo aparece en su propia definición. El tagline principal de la marca es código muerto, y la pantalla insignia no dice absolutamente nada de la marca más allá del logo. Lo primero que se lee en el panel es **"95 eventos"**.

Ese es el "momento memorable" que falta. Cuesta cinco líneas:

```html
<!-- index.html:91-93 -->
<div class="cabecera-lista">
  <p class="lema" data-tr="lema"></p>
  <div class="conteo"><b id="conteo2">0</b> <span id="conteo-txt2">eventos</span></div>
</div>
```

```css
/* index.html, dentro del @media(min-width:880px) */
.lema{
  font-family:var(--fuente-marca);font-size:var(--t-lg);font-weight:800;
  letter-spacing:-.025em;color:var(--tinta);margin:0 0 2px;
}
.conteo b{font-variant-numeric:tabular-nums}   /* falta: es un número que cambia */
```

Que el panel abra con **"Santiago está pasando" / "95 panoramas"** en vez de "95 eventos" cambia por completo de qué se trata la pantalla, y no cuesta un píxel de layout.

---

### B11 — `--tinta-tenue` no llega a contraste legible, y está usado justo en las etiquetas de los datos que importan

**Archivo:** `loica.css`, líneas **24** y **74**.

Medido: `#8C93A8` sobre `#FFFDF9` = **3,02:1**; sobre el crema `#FAF3E7` = **2,78:1**. El mínimo AA para texto es 4,5:1. Y ese token pinta: `.mascota-nombre` (11,5 px), `.dato .et` — que son las etiquetas **Cuándo / Dónde / Precio** de la ficha —, `.ayuda`, `.aprox`, `.fuente-pie` y `.mas`.

```css
/* loica.css:24 */
--tinta-tenue:#6E7690;    /* 4,44:1 sobre elevado, 4,09:1 sobre crema */
/* loica.css:74 (modo oscuro) */
--tinta-tenue:#8C96B0;    /* era #7B849E a 3,79:1; ahora 4,78:1 */
```

En la misma pasada, el botón primario: blanco sobre `--rojo-loica #E8442E` da **3,96:1**, y en modo oscuro blanco sobre `#FF5C44` da **3,06:1**. Un botón de 17 px en negrita no califica como "texto grande", así que ambos fallan.

```css
/* loica.css:186-192 — el botón usa el rojo profundo, el pin se queda con el brillante */
.boton{background:var(--rojo-hover);/* #C9331F → 5,28:1 */ ...}
.boton:hover{background:#B22C1A}
/* y en modo oscuro, línea 75: */
--acento:#FF5C44;            /* se queda para pines y bordes */
--acento-boton:#D93A24;      /* 4,58:1 con blanco */
```

Y en el calendario, `.marca-ev` de "Clases" tiene **2,33:1** a 10,5 px (naranjo `#E08A1E` sobre su propio fondo al 12%). Con `--c-clases:#B8690B` (B/A3) sube a 4,89:1 sin tocar nada más.

---

### B12 — El mismo bloque "tres tarjetas centradas" aparece cuatro veces, y las mascotas —lo más propio que tiene el proyecto— están dentro de una grilla de tarjetas

**Archivos:** `agrega.html:16-23` (`.promesas`), `nosotros.html:29-35` (`.creencias`), `nosotros.html:37-45` (`.pasos`), `nosotros.html:47-56` (`.elenco`).

Cuatro veces el mismo patrón: `grid-template-columns:repeat(auto-fit,minmax(XXXpx,1fr))`, tarjeta con `background:var(--fondo-elevado)`, `border:1px solid var(--borde)`, `border-radius:var(--r-lg)`, texto centrado. Sumado al héroe centrado, al gradiente de `nosotros.html:16`, a los tres círculos numerados 1-2-3 de `.pasos` y a la banda oscura de CTA al final, `nosotros.html` es el esqueleto por defecto de una landing generada, de arriba a abajo.

El censo lo confirma: en el mapa hay **97 elementos con `border-radius:12px`** y **17 con pill**. Dos radios hacen todo. Y `.chip:hover`, `.boton:hover` y `.bicho:hover` usan **el mismo `translateY(-1/-3px)` + sombra** — el mismo gesto para un interruptor de filtro, un botón de acción y una tarjeta informativa. Un chip no se "levanta"; se prende.

Dos cambios que rompen el patrón sin rediseñar nada:

**a) `agrega.html:20-23` — sacar la caja de las promesas.** Son tres tranquilizadores antes de un formulario, no tres features:

```css
.promesas{
  display:flex;flex-wrap:wrap;justify-content:center;gap:var(--e-4) var(--e-8);
  max-width:760px;margin:0 auto var(--e-8);padding:0 var(--e-5);
}
.promesa{
  flex:1 1 190px;background:none;border:0;border-top:3px solid var(--acento);
  border-radius:0;padding:var(--e-3) 0 0;
}
.promesa b{display:block;font-size:var(--t-base);margin-bottom:4px}   /* era 13px = igual que el cuerpo */
.promesa span{font-size:var(--t-sm);color:var(--tinta-suave)}
```

(De paso: hoy `.promesa b` y `.promesa span` son **ambos 13 px** — la tarjeta no tiene ninguna jerarquía interna, solo peso y color.)

**b) `nosotros.html:47-56` — el elenco deja de ser una grilla y pasa a ser una lista editorial con pieza principal.** Las seis mascotas son el activo más diferenciador del proyecto y hoy están en la misma grilla que las promesas de un formulario:

```css
.elenco{display:grid;gap:0}
.bicho{
  display:grid;grid-template-columns:72px 1fr;gap:var(--e-4);align-items:start;
  background:none;border:0;border-top:1px solid var(--borde);border-radius:0;
  padding:var(--e-5) 0;text-align:left;transition:none;
}
.bicho:first-child{
  grid-template-columns:124px 1fr;border-top:0;
  padding-top:0;padding-bottom:var(--e-6);
}
.bicho:first-child svg{width:124px;height:124px}
.bicho:hover{transform:none;box-shadow:none}
.bicho svg{margin:0}
.bicho b{display:block;font-family:var(--fuente-marca);font-size:var(--t-lg)}
.bicho .rol{
  font-size:var(--t-xs);font-weight:800;color:var(--tono);
  text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;
}
.bicho span{font-size:var(--t-base);color:var(--tinta-suave);line-height:1.6}
```

La Loica arriba, grande, con su rol de guía; las otras cinco debajo, en lista. Eso se lee como una decisión; seis tarjetas iguales se leen como un componente.

Y el hover genérico, en `loica.css:148`:

```css
.chip:hover{border-color:var(--borde-fuerte);background:var(--fondo-hundido)}  /* fuera el translateY */
```

---

### Menciones cortas (no bloquean, pero suman)

- **`nosotros.html:16`** — `linear-gradient(170deg,var(--fondo-hundido) 0%,var(--fondo) 62%)` es un degradado de crema a crema: no se nota y por eso está de más. La silueta de cerros de la línea 74-79 sí funciona; súbanla a `opacity:.28/.38` y estírenla a `height:180px` y ya tienen la portada resuelta sin degradado.
- **`loica.js:214-215`** — el `onerror` de la miniatura construye un `div` con `innerHTML` y `.replace(/'/g,"")` sobre el SVG. Funciona, pero es frágil y difícil de mantener; con solo 9 imágenes en 95 eventos conviene decidir en JS antes de renderizar.
- **`index.html:214-215`** — `hour:"2-digit"` en `es-CL` produce **"06:00 p. m."**. En Chile los eventos se anuncian "18:00". Añadir `hour12:false` y quedará `18:00`.
- **`font-variant-numeric:tabular-nums` está solo en 2 lugares** (`loica.css:182`, `calendario.html:50`). Falta en `.conteo b`, en `.miniatura .dia`, en la hora de la ficha y en `.dia-total`. Si van a usar cifras tabulares, que sea en todas las cifras.
- **Las mascotas no responden al tema.** `loica.js:13-61` tiene `#FAF3E7`, `#1E2A4A`, `#F5B52E` y `#F2778C` incrustados en los `path`. En modo oscuro los ojos azul cordillera de la chinchilla y el pudú caen sobre fondos oscuros. Cambiar los estructurales por variables (`var(--mascota-clara)` / `var(--mascota-oscura)`, redefinidas en `:root[data-tema="oscuro"]`) y dejar incrustado solo el `#E8442E` del pecho de la loica, que sí es identidad.
- **`calendario.html:48-49`** — `.dia.hoy` y `.dia.elegido` tienen la misma especificidad y `.elegido` va después, así que **el día de hoy pierde su borde rojo apenas está seleccionado** — que es el estado por defecto al cargar. Subir a `.dia.hoy.elegido{border-color:var(--acento)}`.
- **`agrega.html:280-285`** — el formulario dispara un `mailto:` y **acto seguido muestra "¡Gracias!" sin saber si el correo se envió**. El propio copy lo admite ("Revisa que tu correo se haya enviado"). Para una marca cuyo rasgo declarado es "Honesta", el estado de éxito no puede mentir. Mientras no haya backend: mostrar el cuerpo del correo en pantalla con un botón "Copiar" además del `mailto:`, y titular "Casi listo: envía el correo que se abrió" en vez de "¡Gracias!".
- **`index.html:139-142`** — `esFinde` no tiene cota inferior (`dias <= 7` acepta valores negativos), así que un evento del viernes pasado calificaría como "este finde". Con los datos actuales no se nota; con datos históricos sí.

---

## C. Lo que está bien y NO hay que tocar

1. **La arquitectura de tokens de `loica.css` §1 (líneas 8-90).** Colores de marca separados de colores semánticos, semánticos redefinidos en oscuro, y modo oscuro implementado con `prefers-color-scheme` **más** override manual `[data-tema]`. Eso está mejor resuelto que en la mayoría de los productos comerciales. Los valores hay que corregirlos (B11), la estructura no.

2. **La barra verde de "gratis": `loica.css:161`.**
   ```css
   .tarjeta-gratis{box-shadow:inset 3px 0 0 var(--gratis)}
   ```
   Es la mejor micro-decisión del proyecto: 3 px, cero costo de layout, escanea la lista completa de un vistazo, y cumple literalmente la promesa de marca "lo gratis no es lo de segunda". No la toquen. Al contrario: extiéndanla al calendario y a la ficha.

3. **El pin como gota con el disco crema y la mascota adentro** (`index.html:189-193`). La construcción es correcta: el disco `#FAF3E7` garantiza que la mascota se lea sobre cualquier fondo, y la gota lleva el color de categoría. Solo hay que arreglar los dos colores que no contrastan (A3) — la pieza en sí está bien pensada.

4. **`tarjetaEvento()` compartida entre mapa y calendario** (`loica.js:206`). Una sola tarjeta, dos pantallas. Eso es sistema de diseño de verdad, no una carpeta de componentes.

5. **El copy de `nosotros.html`.** "Una ciudad se usa o se pierde" y "Somos el índice de la ciudad, no su intermediario" son frases con autor. El texto del manifiesto es lo más humano del proyecto — el problema es la caja en que está metido (B12), no el contenido. Lo mismo con "Gratis siempre / Lo revisa una persona / Te mandamos gente" en `agrega.html`: es específico, honesto y no suena a IA.

6. **La base de accesibilidad estructural.** `:focus-visible` global con outline de 2,5 px (`loica.css:106`), `prefers-reduced-motion` (227-229), `aria-pressed` en todos los chips, `aria-current="page"` en la nav, `aria-label` en cada pin, botones reales (`<button>`) en vez de `div` clicables. Eso casi nunca está y acá está.

7. **Tres idiomas desde el día uno** (`loica.js:89-126`) con el idioma persistido y re-render por evento (`loica:idioma`). Es exactamente lo que pedía la estrategia: "bilingüe ahora es barato, después es caro".

8. **`calendario.html:124`** — arrancar en el mes del primer evento en vez de en un mes vacío. Es un detalle chico que solo se le ocurre a alguien que pensó en el usuario.

9. **`index.html:123-131`** — el `ResizeObserver` con comparación de tamaño previo para evitar el bucle de `resize()`. Ingeniería correcta y comentada en español. Igual que el comentario de `desplazamiento` en `calendario.html:171`. El código está bien escrito; el problema es visual, no técnico.

10. **La estructura de navegación en celular como bottom sheet arrastrable** (`.panel-lista` + `.tirador`). El patrón es el correcto para mapa + lista. Lo que hay que arreglar es el estado colapsado (128 px muestra el conteo y **media tarjeta cortada**; que muestre una tarjeta completa o solo el resumen), no el patrón.

---

## D. Criterios de PASS

Para levantar el HOLD tienen que cumplirse las siete condiciones, verificadas en pantalla:

1. **La hora y el precio se leen en la tarjeta** sin abrir la ficha, y ningún precio dice `—`. Verificar en la lista del mapa a 1280 y a 390.
2. **La razón título:metadata en la tarjeta es ≥ 1,25** y ningún `font-weight` del CSS está fuera de los pesos que la fuente carga. Verificar con `getComputedStyle` en `.tarjeta h3` y `.tarjeta-meta`.
3. **El mapa cambia con el tema** y ningún color de categoría baja de 3:1 contra el basemap. Verificar `index.html` en claro y oscuro, con el filtro "Otros" activo.
4. **El botón "Ver en la fuente original" es visible sin scroll** al abrir cualquier ficha en 1280×800 y en 390×844.
5. **Las cuatro secciones de la nav son alcanzables en 390 px** sin scroll horizontal, y ningún control táctil mide menos de 44 px de alto.
6. **Existen los tres estados que hoy no existen**: cargando (esqueleto), error (con el copy "Se nos enredó el mapa"), y vacío con botón de salida. Verificar cortando la red y con el filtro Gratis+Fiestas.
7. **Ningún texto por debajo de 4,5:1** en claro y en oscuro. Verificar `--tinta-tenue`, el texto del botón primario y `.marca-ev` de "Clases".

Cuando eso esté, la pregunta "¿esto lo hizo una IA?" deja de tener respuesta obvia — porque el producto va a estar tomando decisiones que solo tienen sentido para una app de panoramas de Santiago, y ninguna otra.
