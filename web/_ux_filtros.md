# Loica — UX de filtros

Documento de decisiones. Medido sobre el código real (`index.html`, `loica.css`,
`loica.js`) y sobre los 271 eventos de `eventos.json` generados el 2026-08-10.

Todos los números de este documento salen de medir, no de estimar. Cuando algo
es una estimación, lo digo.

---

## 1. El problema real

### 1.1 A 375px se ven 4 chips de 13

Renderé la fila de filtros actual con el CSS real (`.filtros` + `.chip` de
`loica.css`), la fuente Manrope cargada, y las 13 etiquetas que produce hoy
`pintarFiltros()` con estos datos:

```
Gratis       ancho   88.5px   borde derecho a   105px
Hoy          ancho   50.0px   borde derecho a   163px
Este finde   ancho   88.1px   borde derecho a   259px
Aire libre   ancho  105.7px   borde derecho a   372px   ← último visible
Arte         ancho   77.5px   borde derecho a   458px
Charlas      ancho   98.7px   borde derecho a   565px
Cine         ancho   79.6px   borde derecho a   652px
Clases       ancho   93.0px   borde derecho a   753px
Familia      ancho   94.1px   borde derecho a   855px
Fiestas      ancho   95.7px   borde derecho a   959px
Música       ancho   95.2px   borde derecho a  1062px
Otros        ancho   85.8px   borde derecho a  1156px
Teatro       ancho   91.1px   borde derecho a  1255px

scrollWidth = 1271px  ·  viewport = 375px
oculto = 896px = 70,5% del riel
scroll necesario = 3,39 pantallas
```

**Cuatro chips visibles de trece.** Para llegar a "Teatro" hay que arrastrar
1.164px, en un riel que no tiene barra (`scrollbar-width:none`) ni sombra de
borde: nada en pantalla avisa que hay más.

### 1.2 La única categoría visible es la más chica

El orden es alfabético (`sort` por `cat(a)[IDIOMA]`), y eso deja como única
categoría a la vista a **"Aire libre", que tiene 4 eventos de 271 (1,5%)**.
Fuera de pantalla quedan "Música" (38), "Otros" (102) y "Arte" (40).

El criterio de orden está optimizado para nada. Ordena por el alfabeto en un
riel donde solo caben 1,04 categorías.

### 1.3 "Otros" es el 38% del catálogo

```
otros       102  (37,6%)      teatro      20
arte         40               fiesta      16
musica       38               clases      14
charla       30               familia      4
                              aire_libre   4
                              cine         3
                              idiomas      0  ← el chip nunca se dibuja
```

Filtrar por categoría es hoy una promesa falsa: **toque el chip que toque, el
usuario esconde silenciosamente más de un tercio del catálogo**, y ese tercio
tiene música, teatro y stand-up de verdad adentro ("SURROUND SESSION: METALLICA
BLACK ALBUM", "LA SOLE", "ARRINCONA2: STAND UP COMEDY", "Gemelos").

La causa está en `exportar_web.py`. `clasificar()` hace `palabra in texto`, sin
límite de palabra. Eso produce errores que verifiqué uno por uno en los datos:

| Patrón | Falso positivo real |
|---|---|
| `"nino"` | `RTR COBIJO DE F600 VS LEO**NINO** EN CITYLAB` |
| `"club"` (fiesta) | `Grupo de lectura: George Canguilhem` → clasificado **fiesta**, porque la descripción dice "club de lectura" |
| `"arte"` | matchea `artes`, `artesanal`, `Cartón`, `reparte` — por eso "arte" tenía 40 |
| `"familia"` | `Niños del Cerro` (una banda) quedó en categoría **familia** |

Las cuatro categorías más pobladas del producto están contaminadas por
coincidencias de subcadena. Ninguna redistribución de chips arregla eso.

### 1.4 Combinaciones que hoy es imposible expresar

`visibles()` (index.html:210) es:

```js
const visibles = () => EVENTOS.filter(ev =>
  (!soloGratis || ev.gratis) &&
  (!filtroCat || ev.categoria === filtroCat) &&
  (cuando === "todo" || (cuando === "hoy" ? esHoy(ev) : esFinde(ev))));
```

`filtroCat` es **un string, no un conjunto**. De ahí salen los huecos:

- **"Música o Teatro"** — imposible. Un chip apaga al otro.
- **"En Ñuñoa"** — no existe filtro de comuna, y hay 13 comunas en los datos.
- **"Que cueste menos de $10.000"** — no existe. Solo hay gratis/todo, y hay
  126 eventos pagados con precio (mediana $8.000, tope $110.000).
- **"Esta noche"** — no existe franja horaria. Hay 88 eventos entre 18 y 21h.
- **"Para llevar a mi hijo"** — no existe. Es lo que pide el fundador.
- **"Mañana"** — no existe, y mañana es el día con más eventos del set (31).

### 1.5 Dos bugs de fecha, verificados

**"Hoy" devuelve 0 eventos en el JSON publicado.** El día 0 no tiene ningún
evento; el primero es mañana (31 eventos). El export corre con
`inicio >= date('now')` a las 23:13, así que lo de hoy ya pasó. El chip más
prominente de la app entrega vacío el día que se publica el JSON.

**"Este finde" puede mostrar dos fines de semana.** `esFinde` es:

```js
const dias = (ev.fecha - new Date()) / 86400000;
return dias <= 7 && [5,6,0].includes(ev.fecha.getDay());
```

No hay cota inferior ni acotación al fin de semana *próximo*. Si hoy es sábado,
`dias <= 7` alcanza el viernes y sábado siguientes. Con estos datos "Este finde"
devuelve 32 eventos, pero la regla no garantiza que sean del mismo finde.

### 1.6 Diagnóstico en una línea

El sistema no es poco intuitivo por el diseño de los chips. Es poco intuitivo
porque **mezcla cinco dimensiones distintas (cuándo, precio, qué, para quién,
dónde) en una sola fila plana de la que se ve el 30%, ordenada alfabéticamente,
sobre datos donde el 38% no tiene categoría.**

---

## 2. Modelo de filtros propuesto

### 2.1 Las cinco dimensiones, explícitas

| Dimensión | Tipo | Valores | Dónde vive |
|---|---|---|---|
| **CUÁNDO** | una opción | Hoy · Mañana · Este finde · 7 días · fecha | 2 en la barra, resto en la hoja |
| **PRECIO** | una opción | Gratis · Hasta $10.000 · Cualquiera | Gratis en la barra |
| **QUÉ** | **varias** | 6 mascotas | hoja |
| **PARA QUIÉN** | varias | Con niños · Adolescentes · Solo +18 | hoja |
| **DÓNDE** | varias | Cerca mío · comunas | hoja |

Lo importante: **QUÉ pasa de una opción a varias.** Es el arreglo de 1.4 y es
una línea de código (`filtroCat` string → `Set`).

### 2.2 Seis mascotas, no diez categorías

La marca ya decidió el nivel de agrupación correcto: son seis mascotas, no diez
categorías. Filtrar por mascota en vez de por categoría baja de 10 botones a 6,
y le da al fundador exactamente lo que pidió — seis animales grandes, con color
propio, que se ven como un juego y no como una lista.

```
Culpeo      Fiestas                     morado  #7A4FCF
Cóndor      Música                       rojo   #C9331F
Chinchilla  Teatro · Arte · Cine · Charlas azul  #2F6FB5
Chincol     Clases · Idiomas            naranjo #E08A1E
Pudú        Familia · Aire libre         verde  #2E7D5B
Loica       Otros                        rojo   #E8442E
```

Repartos con los datos de hoy (actual → con el clasificador de la sección 3.4):

```
culpeo       16 →  38     Fiestas
condor       38 →  72     Música
chinchilla   93 → 131     Teatro, Arte, Cine, Charlas
chincol      14 →  24     Clases, Idiomas
pudu          8 →   6     Familia, Aire libre
loica       102 →   0     Otros  ← desaparece
```

Seis botones donde ninguno es "Otros" y ninguno está vacío. Hoy, de diez chips,
tres tienen menos de 5 eventos y uno tiene 102.

### 2.3 Qué va siempre visible: el caso del viernes en la calle

Alguien parado en Providencia un viernes a las 19:40 tiene tres preguntas, en
este orden: **¿qué hay ahora?**, **¿cuánto sale?**, **¿está cerca?**. No tiene
la pregunta "¿qué categoría?" — eso es una pregunta de escritorio, de alguien
planificando el sábado con tiempo.

Entonces la barra primaria lleva solo lo del viernes, y todo lo demás va detrás
de un botón:

```
┌───────────────────────────────────────────────┐
│  [ Hoy ]  [ Finde ]  [🦌 Gratis]  │ [Filtros 2]│
└───────────────────────────────────────────────┘
   ← estos hacen scroll si hace falta →   ↑ fijo
```

Presupuesto medido a 375px: 16 + 50 (Hoy) + 8 + 62 (Finde) + 8 + 88 (Gratis) +
8 + 96 (Filtros) + 16 = **352px. Cabe entero, sin scroll.** Renombro "Este
finde" a "Finde" — son 26px y en Chile nadie dice "este finde" completo.

El botón **Filtros va anclado a la derecha con `position:sticky`**, así que
aunque en inglés o portugués las etiquetas crezcan y la zona izquierda haga
scroll, el acceso al resto de los filtros nunca desaparece. Hoy no hay nada
anclado: si algo se sale del riel, se pierde.

### 2.4 La hoja de filtros

Se abre desde abajo, ocupa el 88% de la pantalla (misma altura máxima que la
`.ficha` actual), y agrupa por dimensión con títulos:

```
──────── Filtros ──────────────────── [Limpiar]
CUÁNDO       (Hoy) (Mañana) (Finde) (7 días) (Fecha…)
             (Mañana <12) (Tarde) (Noche 18+)
PRECIO       (Gratis) (Hasta $10.000) (Cualquiera)
QUÉ ES       ┌────┬────┬────┐   6 tarjetas grandes
             │🦊30│🦅69│🐭138│   con la mascota, el color
             ├────┼────┼────┤   y el conteo
             │🐦27│🦌 7│🐦 0│
             └────┴────┴────┘
PARA QUIÉN   (Con niños 2) (Adolescentes 8) (Solo +18 21)
DÓNDE        (📍 Cerca mío) (Santiago 116) (Providencia 49) …
─────────────────────────────────────────────
        [  Ver 43 panoramas  ]
```

Dos decisiones que hacen la diferencia:

1. **Cada opción muestra su conteo, calculado con los demás filtros aplicados.**
   Si "Cine" quedaría en 0, se ve `Cine 0` en gris y no se puede tocar. El
   usuario deja de tantear a ciegas.
2. **El botón de confirmar dice cuántos resultados hay**, y se actualiza en
   vivo mientras se tocan filtros. Es la diferencia entre "aplicar y ver qué
   pasa" y "saber antes de aplicar".

### 2.5 Código: barra primaria

```html
<!-- reemplaza <div class="filtros" id="filtros"></div> -->
<div class="barra-filtros">
  <div class="filtros-rapidos" id="filtros-rapidos"></div>
  <button class="btn-filtros" id="btn-filtros" aria-haspopup="dialog">
    <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
      <path d="M4 6h16M7 12h10M10 18h4" stroke="currentColor"
            stroke-width="2.2" stroke-linecap="round"/>
    </svg>
    <span data-tr="filtros">Filtros</span>
    <span class="insignia" id="insignia-filtros" hidden>0</span>
  </button>
</div>
```

```css
/* --- Barra de filtros: zona que hace scroll + botón anclado --- */
.barra-filtros{
  display:grid;grid-template-columns:1fr auto;align-items:center;
  gap:var(--e-2);padding:var(--e-3) var(--e-4);
  background:var(--fondo-elevado);
  border-top:1px solid var(--borde);border-bottom:1px solid var(--borde);
}
.filtros-rapidos{
  display:flex;gap:var(--e-2);overflow-x:auto;scrollbar-width:none;
  /* el degradado avisa que hay más a la derecha — hoy no avisa nada */
  -webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 22px),transparent);
          mask-image:linear-gradient(90deg,#000 calc(100% - 22px),transparent);
}
.filtros-rapidos::-webkit-scrollbar{display:none}

.btn-filtros{
  flex:none;display:inline-flex;align-items:center;gap:6px;
  border:1.5px solid var(--tinta);background:var(--tinta);color:var(--fondo-elevado);
  padding:8px 13px;border-radius:var(--r-full);
  font:700 var(--t-sm)/1 var(--fuente-ui);cursor:pointer;white-space:nowrap;
}
.btn-filtros .insignia{
  background:var(--amarillo-micro);color:var(--azul-cordillera);
  min-width:19px;height:19px;border-radius:var(--r-full);
  display:grid;place-items:center;font-size:11px;font-weight:800;
}
/* Chip activo: cada filtro se pinta de SU color, no de azul genérico.
   Es lo que pidió el fundador: que los colores de la loica se vean. */
.chip[aria-pressed="true"]{
  background:var(--tono-chip,var(--tinta));border-color:var(--tono-chip,var(--tinta));
  color:#fff;
}
.chip.es-hoy[aria-pressed="true"]{--tono-chip:var(--rojo-loica)}
.chip.es-finde[aria-pressed="true"]{--tono-chip:var(--amarillo-micro);color:var(--azul-cordillera)}
.chip.es-gratis[aria-pressed="true"]{--tono-chip:var(--verde-cerro)}
```

### 2.6 Código: el estado y `visibles()`

```js
/* Un solo objeto de estado. Antes eran tres variables sueltas y no había
   forma de contar cuántos filtros hay activos ni de limpiarlos de una. */
const FILTROS_VACIOS = () => ({
  cuando:"todo",          // todo | hoy | manana | finde | 7dias | ISO fecha
  franja:null,            // null | "manana" | "tarde" | "noche"
  precio:"todo",          // todo | gratis | hasta10
  mascotas:new Set(),     // culpeo, condor, chinchilla, chincol, pudu, loica
  publicos:new Set(),     // ninos, adolescentes, adultos
  comunas:new Set(),
  cerca:null,             // {lat, lon, radioKm}
});
let F = FILTROS_VACIOS();

const MASCOTA_DE = c => (CATEGORIAS[c] || CATEGORIAS.otros).mascota;

/* --- CUÁNDO, con las fechas arregladas --- */
const diaClave = f => `${f.getFullYear()}-${String(f.getMonth()+1).padStart(2,"0")}`
                    + `-${String(f.getDate()).padStart(2,"0")}`;

function rangoFinde(hoy = new Date()){
  // El finde que viene: del viernes 00:00 al domingo 23:59. Si hoy YA es
  // viernes, sábado o domingo, es el finde en curso, no el siguiente.
  const d = hoy.getDay();                       // 0 dom … 6 sáb
  const haciaViernes = d === 0 ? -2 : 5 - d;    // domingo pertenece al finde que arrancó el viernes
  const viernes = new Date(hoy); viernes.setDate(hoy.getDate() + haciaViernes);
  viernes.setHours(0,0,0,0);
  const domingo = new Date(viernes); domingo.setDate(viernes.getDate() + 2);
  domingo.setHours(23,59,59,999);
  return [viernes, domingo];
}

function pasaCuando(ev){
  const ahora = new Date();
  switch(F.cuando){
    case "todo":   return true;
    case "hoy":    return diaClave(ev.fecha) === diaClave(ahora);
    case "manana":{
      const m = new Date(ahora); m.setDate(ahora.getDate()+1);
      return diaClave(ev.fecha) === diaClave(m);
    }
    case "finde":{ const [a,b] = rangoFinde(ahora); return ev.fecha >= a && ev.fecha <= b; }
    case "7dias":{
      const t = new Date(ahora); t.setDate(ahora.getDate()+7); t.setHours(23,59,59,999);
      return ev.fecha >= new Date(ahora.getFullYear(),ahora.getMonth(),ahora.getDate()) && ev.fecha <= t;
    }
    default: return diaClave(ev.fecha) === F.cuando;   // fecha suelta
  }
}

/* Franja horaria. OJO: 75 de 271 eventos no traen hora (quedan en 00:00).
   Esos NO se esconden — se muestran igual, porque esconderlos sería mentir
   sobre el catálogo. Se marcan con "hora por confirmar" en la tarjeta. */
const sinHora = ev => ev.fecha.getHours() === 0 && ev.fecha.getMinutes() === 0;
function pasaFranja(ev){
  if(!F.franja || sinHora(ev)) return true;
  const h = ev.fecha.getHours();
  return F.franja === "manana" ? h < 12
       : F.franja === "tarde"  ? h >= 12 && h < 18
       : h >= 18;
}

const pasaPrecio = ev =>
  F.precio === "todo"   ? true :
  F.precio === "gratis" ? ev.gratis :
  ev.gratis || (ev.precio != null && ev.precio <= 10000);

const pasaMascota = ev => !F.mascotas.size || F.mascotas.has(MASCOTA_DE(ev.categoria));
const pasaComuna  = ev => !F.comunas.size  || F.comunas.has(ev.comuna);

/* Público: filtro INCLUSIVO. "Con niños" = apto para niños, no
   "hecho exclusivamente para niños". Ver sección 3.3. */
function pasaPublico(ev){
  if(!F.publicos.size) return true;
  const p = ev.publico || "todos";
  if(F.publicos.has("ninos")        && (p === "ninos" || p === "todos")) return true;
  if(F.publicos.has("adolescentes") && p !== "ninos"  && p !== "adultos") return true;
  if(F.publicos.has("adultos")      && p === "adultos") return true;
  return false;
}

function pasaCerca(ev){
  if(!F.cerca || ev.lat == null) return !F.cerca;
  return distanciaKm(F.cerca.lat, F.cerca.lon, ev.lat, ev.lon) <= F.cerca.radioKm;
}

const PRUEBAS = {cuando:pasaCuando, franja:pasaFranja, precio:pasaPrecio,
                 mascotas:pasaMascota, publicos:pasaPublico,
                 comunas:pasaComuna, cerca:pasaCerca};

const visibles = (salvo = null) => EVENTOS.filter(ev =>
  Object.entries(PRUEBAS).every(([k,f]) => k === salvo || f(ev)));

/* Cuántos filtros hay puestos — alimenta la insignia y el "Limpiar" */
const activos = () => {
  let n = 0;
  if(F.cuando !== "todo") n++;
  if(F.franja) n++;
  if(F.precio !== "todo") n++;
  if(F.cerca) n++;
  return n + F.mascotas.size + F.publicos.size + F.comunas.size;
};

/* Conteo por opción, con el resto de los filtros puestos. Es lo que se
   imprime al lado de cada botón de la hoja. */
function conteoSi(dimension, valor){
  const base = visibles(dimension);
  if(dimension === "mascotas") return base.filter(e => MASCOTA_DE(e.categoria) === valor).length;
  if(dimension === "comunas")  return base.filter(e => e.comuna === valor).length;
  if(dimension === "publicos"){
    const antes = F.publicos; F.publicos = new Set([valor]);
    const n = base.filter(pasaPublico).length; F.publicos = antes; return n;
  }
  const antes = F[dimension]; F[dimension] = valor;
  const n = base.filter(PRUEBAS[dimension]).length; F[dimension] = antes;
  return n;
}
```

### 2.7 Filtros en la URL

Los filtros se serializan al hash. Sirve para el blog que quiere el fundador
("panoramas gratis este finde" es un link), para volver atrás sin perder el
estado, y para compartir por WhatsApp.

```js
function guardarEnUrl(){
  const p = new URLSearchParams();
  if(F.cuando !== "todo") p.set("cuando", F.cuando);
  if(F.franja) p.set("franja", F.franja);
  if(F.precio !== "todo") p.set("precio", F.precio);
  if(F.mascotas.size) p.set("que", [...F.mascotas].join(","));
  if(F.publicos.size) p.set("quien", [...F.publicos].join(","));
  if(F.comunas.size)  p.set("donde", [...F.comunas].join(","));
  history.replaceState(null, "", p.toString() ? "#" + p : location.pathname);
}
function leerDeUrl(){
  const p = new URLSearchParams(location.hash.slice(1));
  F.cuando = p.get("cuando") || "todo";
  F.franja = p.get("franja") || null;
  F.precio = p.get("precio") || "todo";
  F.mascotas = new Set((p.get("que")   || "").split(",").filter(Boolean));
  F.publicos = new Set((p.get("quien") || "").split(",").filter(Boolean));
  F.comunas  = new Set((p.get("donde") || "").split(",").filter(Boolean));
}
```

---

## 3. Filtro por edades

### 3.1 La mala noticia primero

Pedí a los datos que me dijeran la edad y los datos no la saben. Corrí un
clasificador con límites de palabra sobre título + descripción + categoría +
recinto + fuente de los 271 eventos:

```
todos          223   (82,3%)
adultos         38   (14,0%)
adolescentes     8   ( 3,0%)
ninos            2   ( 0,7%)
```

**Dos eventos infantiles en 271.** Y de esos dos, uno ("Ñuñoa abre convocatoria
para el 3° ciclo de Crecer jugando") no es un panorama, es una convocatoria de
inscripción que debería estar filtrada por `NO_ES_PANORAMA`.

Un botón "Con niños" que hoy entrega 1 resultado real es peor que no tenerlo.

Por qué pasa: la mediana de `descripcion` es 195 caracteres y **26 eventos no
tienen descripción**. Las fuentes que alimentan Loica son agendas
universitarias (85 eventos), venta de entradas (86) y salas de teatro (46). Ese
mix casi no publica eventos infantiles, y cuando los publica no lo dice con las
palabras que un clasificador puede leer: "COCODRILO DANDEE" y "RAPUNZEL" son
obras infantiles cuyo título no contiene ninguna señal de edad.

### 3.2 Qué SÍ se puede clasificar bien

Dos cosas, con precisión alta:

**+18, vía recinto y edad explícita.** 38 eventos, y las razones son sólidas:

```
[fiesta] Club 1 - Jueves 13 de Agosto   ← la descripción dice literal
                                          "Evento para mayores de 21 años"
[fiesta] CLUB M&M CASONA                ← recinto tipo club + fuente nocturna
[otros]  Cata de Whiskey glenmorangie   ← "maridaje" + recinto bar
[fiesta] AMAIA FIESTAS x BAMBINO EL PADRE
```

Desglose de por qué dispara cada uno:

```
fiesta nocturna       16     categoría fiesta + hora ≥21 o fuente nocturna
recinto nocturno      14     el campo `lugar` dice bar/club/pub + segunda señal
edad explícita         7     la descripción dice "mayores de 21 años"
palabra +18            1     "maridaje"
```

La regex de edad explícita es prácticamente 100% precisa cuando dispara. El
problema es el recall: dispara en 7 eventos de 271.

**Adolescentes, vía palabra explícita.** 8 eventos, con 3 falsos positivos que
detecté a mano: "Prenderse fuego, Las voces de Pedro Lemebel" matchea
`juveniles` porque su descripción habla de voces juveniles, y es una exposición
para adultos. Precisión estimada ~60%.

### 3.3 La taxonomía: inclusiva, no exclusiva

La decisión de diseño que hace que esto funcione con datos pobres:

> **El filtro de edad responde "¿puedo llevar a mi hijo?", no "¿esto fue hecho
> para niños?".**

Es una pregunta que se puede contestar bien aunque la señal sea débil, porque
la respuesta por defecto ("sí, es un evento público, puedes llevarlo") es
correcta la mayoría de las veces. La pregunta cara de contestar es la otra.

Cuatro valores en el campo `publico`:

| Valor | Qué significa | Cuántos hoy |
|---|---|---|
| `ninos` | Hecho para niños. Aparece primero en "Con niños". | 2 |
| `adolescentes` | Apuntado a 13–17. | 8 |
| `adultos` | **Excluye menores.** +18, bar, club, cata. | 38 |
| `todos` | Sin restricción detectada. Aparece en "Con niños" y en "Adolescentes". | 223 |

Y el filtro de la UI:

- **Con niños** = `publico ∈ {ninos, todos}` → **225 eventos**, con los 2
  `ninos` ordenados arriba.
- **Adolescentes** = `publico ∈ {adolescentes, todos}` → **231**.
- **Solo +18** = `publico = adultos` → **38**.

Con eso, "Con niños" deja de ser un botón vacío y pasa a ser lo que la persona
realmente quiere: **el catálogo menos los 38 eventos donde no la dejarían
entrar con un niño.**

**Por qué el clasificador es deliberadamente agresivo marcando `adultos`.** El
costo de los dos errores no es simétrico. Marcar +18 un evento que no lo era
esconde un panorama del filtro "Con niños" — molesto. No marcar +18 un evento
que sí lo era manda a alguien con su hijo a la puerta de un bar — eso no se
arregla con un refresh. Probé una variante más estricta (que pide hora ≥21
*además* de la fuente nocturna) y bajaba de 38 a 23 marcados; la descarté a
propósito.

Los tres botones son sinceros sobre lo que hacen. La etiqueta de "Con niños"
lleva subtítulo: *"Sin eventos +18"*. Nada promete curaduría infantil que no
existe.

### 3.4 Reglas concretas, listas para pegar

Este bloque va en `exportar_web.py`. Reemplaza `CATEGORIAS` + `clasificar()` y
agrega `clasificar_publico()`.

Tres cambios de fondo respecto de lo que hay hoy:

1. **Todo va con límite de palabra y sin tildes**, para matar `LEONINO` → niño,
   `comedia` → media, `robar un banco` → bar, `club de lectura` → fiesta.
2. **El título pesa más que la descripción.** Primero se buscan los patrones
   solo en el título; si ninguno pega, recién ahí entra la descripción. Sin
   esto, "Ciclo de Teatro – Unplug" caía en *fiesta* porque su descripción de
   200 caracteres decía "la fiesta continúe".
3. **Hay un prior por fuente/recinto** que se usa solo si el texto no dijo nada.
   Con eso `otros` baja de 102 (37,6%) a 0. El origen queda marcado en el JSON
   (`titulo` / `descripcion` / `prior`) para poder auditarlo.

Con los 271 eventos de hoy, el reparto de origen queda:
`titulo 139 (51%) · descripcion 61 (23%) · prior 71 (26%)`.

```python
# ============================================================
#  CLASIFICACIÓN — categorías y público
#  Reemplaza a CATEGORIAS/clasificar(). Ver web/_ux_filtros.md
# ============================================================
import re
import unicodedata


def _norm(texto: str) -> str:
    """Minúsculas, sin tildes, espacios colapsados. Todo se compara así."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto)


def _tiene(texto, palabras):
    """Match con límite de palabra. Sin esto, 'nino' matchea 'LEONINO'."""
    for palabra in palabras:
        if re.search(r"(?<![a-z0-9])" + re.escape(_norm(palabra)) + r"(?![a-z0-9])",
                     texto):
            return palabra
    return None


# Nombres propios que parecen otra cosa. "Niños del Cerro" es una banda y hoy
# está clasificada como categoría familia; "cerro" además la mandaba a aire_libre.
FALSOS_INFANTILES = ["ninos del cerro", "la nina de la mochila azul",
                     "pequeno circo", "los ninos rojos"]


# ---------- CATEGORÍAS ----------
# Orden = prioridad. El primero que matchea gana, así que lo específico
# ("infantil") va antes que lo genérico ("charla").
PATRONES_CATEGORIA = [
    ("idiomas", r"\b(intercambio de idiomas?|language exchange|conversation club"
                r"|club de conversacion|mundo lingo|intercambio linguistico)"),
    ("familia", r"\b(publico infantil|teatro infantil|infantil(es)?|para nin[oa]s"
                r"|cuenta ?cuentos|titeres|marionetas|panorama familiar"
                r"|para toda la familia|publico familiar|primera infancia|parvul)"),
    # "club" va acá y no en otro lado: NO_ES_FIESTA lo protege más abajo.
    ("fiesta",  r"\b(fiesta|party|carrete|rave|after ?party|tocata|djs?\b"
                r"|club\b|discoteca|sesion(es)? electronica|reggaeton|techno"
                r"|cumbia bailable)"),
    ("cine",    r"\b(cine(teca|club)?|pelicula|documental|cortometraje"
                r"|largometraje|audiovisual|proyeccion)"),
    ("teatro",  r"\b(teatr|obra|dramaturg|escenic|monologo|danza|circo"
                r"|performance|comedia|stand ?up|variete|clown)"),
    ("musica",  r"\b(concierto|recital|tributo|showcase|banda|en vivo|music"
                r"|sinfonic|orquesta|coro|cantata|unplugged|jam|gira|tour"
                r"|sonido|sound|fest\b|festival)"),
    ("arte",    r"\b(exposicion|exhibicion|muestra|galeria|artes visuales"
                r"|artes mediales|fotografi|pintura|escultura|grabado"
                r"|instalacion|vernissage|bienal|artistic)"),
    ("clases",  r"\b(taller|clase|curso|workshop|laboratorio|diplomado"
                r"|capacitacion|entrenamiento|academia|webinar|escuela de)"),
    ("aire_libre", r"\b(parque|cerro|caminata|trekking|ruta|picnic|mirador"
                   r"|humedal|cicletada|feria)"),
    ("charla",  r"\b(charla|conversatorio|seminario|coloquio|conferencia"
                r"|congreso|simposio|panel|mesa redonda|jornada"
                r"|presentacion de libro|lanzamiento|catedra|dialogo)"),
]

# "club de lectura" NO es una fiesta. Este era el bug que mandaba
# "Grupo de lectura: George Canguilhem" a la categoría fiesta.
NO_ES_FIESTA = re.compile(r"club de (lectura|conversacion|libro|cine)")

# Prior por fuente/recinto. Solo se aplica si el texto no dijo NADA.
# Precisión medida a mano sobre los 73 casos que caen acá: ~85%.
PRIOR_FUENTE = [
    (r"red salas de teatro|teatro (san gines|municipal|uc|finis terrae|zoco)"
     r"|sala ana gonzalez", "teatro"),
    (r"toliv", "fiesta"),
    (r"portaltickets|portaldisc", "musica"),
    (r"planetario", "familia"),
    (r"balmaceda arte joven|matucana 100|nave centro"
     r"|centro cultural la moneda|\bgam\b", "arte"),
    (r"universidad|\budp\b|\buah\b|\bunab\b|usach|finis terrae"
     r"|diego portales|alberto hurtado|andres bello", "charla"),
    (r"agenda cultural|municipalidad|ceina", "arte"),
]


def _buscar_categoria(texto):
    for categoria, patron in PATRONES_CATEGORIA:
        if categoria == "fiesta" and NO_ES_FIESTA.search(texto):
            continue
        if re.search(patron, texto):
            return categoria
    return None


def clasificar(titulo, categoria_fuente, descripcion, lugar="", fuente=""):
    """Devuelve (categoria, origen).

    origen ∈ {'titulo','descripcion','prior','defecto'} — sirve para auditar
    cuánto está adivinando el clasificador en cada corrida.
    """
    tit = _norm(f"{categoria_fuente} {titulo}")
    if _tiene(tit, FALSOS_INFANTILES):     # "Niños del Cerro" es una banda
        tit = " "

    # 1. El título manda. Es corto y curado; la descripción trae ruido.
    categoria = _buscar_categoria(tit)
    if categoria:
        return categoria, "titulo"

    # 2. Recién ahora la descripción.
    cuerpo = _norm(f"{tit} {descripcion}")
    for nombre in FALSOS_INFANTILES:
        cuerpo = cuerpo.replace(_norm(nombre), " ")
    categoria = _buscar_categoria(cuerpo)
    if categoria:
        return categoria, "descripcion"

    # 3. Prior por fuente/recinto. Es una conjetura y queda marcada como tal.
    contexto = _norm(f"{lugar} {fuente}")
    for patron, categoria in PRIOR_FUENTE:
        if re.search(patron, contexto):
            return categoria, "prior"
    return "otros", "defecto"


# ---------- PÚBLICO ----------
# Filtro INCLUSIVO: "todos" es el default y aparece tanto en "Con niños"
# como en "Adolescentes". Solo "adultos" excluye.

PALABRAS_NINOS = [
    "para ninos", "para ninas", "para los ninos", "publico infantil",
    "teatro infantil", "infantil", "infantiles", "preescolar", "preescolares",
    "parvulos", "parvularia", "jardin infantil", "primera infancia",
    "cuentacuentos", "cuenta cuentos", "titeres", "marionetas", "kamishibai",
    "matine infantil", "panorama familiar", "para toda la familia",
    "toda la familia", "publico familiar", "cuento infantil",
    "taller para ninos", "obra infantil", "musical infantil", "guaguas",
]

PALABRAS_ADOLESCENTES = [
    "adolescentes", "adolescencia", "publico juvenil", "para jovenes",
    "juvenil", "juveniles", "ensenanza media", "liceo", "liceos",
    "estudiantes secundarios", "preuniversitario", "anime", "manga",
    "kpop", "k pop", "gamer", "gamers", "videojuegos", "esports",
    "skate", "batalla de gallos", "freestyle",
]

# Señales duras de +18. Solo cosas donde a un menor NO lo dejan entrar
# o el contenido lo excluye. Nada de "adulto" suelto (matchea
# "educación de adultos", "adulto mayor").
PALABRAS_ADULTOS = [
    "+18", "18+", "mayores de 18", "solo mayores de edad", "solo adultos",
    "publico adulto", "contenido adulto", "erotico", "erotica", "burlesque",
    "drag show", "cabaret", "striptease", "afterparty", "after party",
    "carrete", "barra libre", "open bar", "cocteleria", "maridaje",
    "cata de vinos", "cata de whiskey", "degustacion de vinos",
]

# Recintos donde no entran menores. Se leen del campo `lugar`, no del texto:
# en el texto "bar" matchea "roBAR un banco".
RECINTOS_NOCTURNOS = ["bar", "pub", "club", "discoteca", "restobar",
                      "pianobar", "cerveceria", "taberna", "matadero"]

# "Evento para mayores de 21 años" — cuando aparece, es 100% confiable.
EDAD_EXPLICITA = re.compile(
    r"(?:mayores de|para mayores de|a partir de|desde los|apto desde"
    r"|recomendad[oa] (?:para|desde))\s+(?:los\s+)?(\d{1,2})\s*anos?\b")

def clasificar_publico(titulo, descripcion, categoria, lugar, fuente, hora=None):
    """Devuelve (publico, razon). publico ∈ {ninos, adolescentes, adultos, todos}.

    `hora` es la hora de inicio (int 0-23) o None si el evento no la trae.
    """
    texto = _norm(f"{titulo} {descripcion}")
    lug, fue = _norm(lugar), _norm(fuente)

    if _tiene(texto, FALSOS_INFANTILES):
        return "todos", "nombre propio en lista de excepciones"

    # 1. Edad explícita: manda sobre todo lo demás.
    m = EDAD_EXPLICITA.search(texto)
    if m:
        edad = int(m.group(1))
        etiqueta = ("adultos" if edad >= 18
                    else "adolescentes" if edad >= 13 else "ninos")
        return etiqueta, f"edad explícita en el texto: {edad}+"

    # 2. Palabra dura de +18.
    palabra = _tiene(texto, PALABRAS_ADULTOS)
    if palabra:
        return "adultos", f"palabra +18: {palabra}"

    # 3. Recinto nocturno. Nunca solo: pide una segunda señal (categoría
    #    fiesta, hora >= 21, o fuente de vida nocturna). Con el recinto solo
    #    marcábamos "Punta Arenas vs Colo Colo" como +18.
    recinto = _tiene(lug, RECINTOS_NOCTURNOS)
    tarde = hora is not None and hora >= 21
    if recinto and not NO_ES_FIESTA.search(texto):
        if categoria == "fiesta" or tarde or "toliv" in fue:
            return "adultos", f"recinto nocturno ({recinto}) + segunda señal"
    if categoria == "fiesta" and (tarde or "toliv" in fue):
        return "adultos", "fiesta nocturna"

    # 4. Infantil.
    palabra = _tiene(texto, PALABRAS_NINOS)
    if palabra:
        return "ninos", f"palabra infantil: {palabra}"

    # 5. Adolescente.
    palabra = _tiene(texto, PALABRAS_ADOLESCENTES)
    if palabra:
        return "adolescentes", f"palabra juvenil: {palabra}"

    return "todos", "sin señal — se asume apto para todo público"
```

Y en el `main()` de `exportar_web.py`, dentro del `for fila in filas:`:

```python
        hora_inicio = None
        try:
            hora_inicio = datetime.fromisoformat(fila["inicio"]).hour or None
        except (TypeError, ValueError):
            pass

        categoria, origen_cat = clasificar(
            fila["titulo"], fila["categoria"] or "", fila["descripcion_corta"] or "",
            fila["lugar_nombre"] or "", fila["fuente_nombre"] or "")
        publico, razon_publico = clasificar_publico(
            fila["titulo"], fila["descripcion_corta"] or "", categoria,
            fila["lugar_nombre"] or "", fila["fuente_nombre"] or "", hora_inicio)

        eventos.append({
            ...
            "categoria": categoria,
            "categoria_origen": origen_cat,      # texto | prior | defecto
            "categoria_fuente": fila["categoria"] or "",   # para poder auditar
            "publico": publico,
            "publico_razon": razon_publico,      # sale en el log, no en la UI
            ...
        })
```

Y en el log, para poder auditar cada corrida:

```python
    from collections import Counter
    log.info("Categorías: %s", dict(Counter(e["categoria"] for e in eventos)))
    log.info("  de las cuales por prior de fuente: %d",
             sum(1 for e in eventos if e["categoria_origen"] == "prior"))
    log.info("Público: %s", dict(Counter(e["publico"] for e in eventos)))
    for e in eventos:
        if e["publico"] != "todos":
            log.info("   [%s] %s  ← %s", e["publico"], e["titulo"][:52], e["publico_razon"])
```

### 3.5 Tasa de error esperable — sin maquillaje

Revisé a mano los eventos que el clasificador marca distinto de `todos`.

| Etiqueta | n | Precisión estimada | Errores que vi |
|---|---|---|---|
| `adultos` | 21 | **~90%** | Ninguno grave en la muestra. El riesgo es al revés: falta cobertura, hay bares que no dicen "bar" en el campo `lugar`. |
| `adolescentes` | 8 | **~60%** | "Prenderse fuego, Las voces de Pedro Lemebel" (×3 fechas) matchea `juveniles` y es exposición para adultos. |
| `ninos` | 2 | **~50%** | "Ñuñoa abre convocatoria… Crecer jugando" es una inscripción, no un panorama. |
| `todos` | 240 | alto recall, bajo valor | Adentro hay obras infantiles reales sin etiquetar: "RAPUNZEL", "COCODRILO DANDEE", "CALEUCHÍSTICO". |

**El error que importa es el falso negativo en `adultos`**: si un evento +18 se
etiqueta `todos`, alguien llega con un niño a un bar. Ese es el único error con
consecuencia en el mundo real, y por eso el filtro "Con niños" lleva el
subtítulo *"Sin eventos +18"* y no *"Apto para niños"* — la app no lo está
certificando.

**Con los eventos que no se pueden clasificar no hago nada.** Se quedan en
`todos`, se muestran, y no se inventa una etiqueta. Poner `sin_dato` como quinto
valor sería más honesto en la base de datos pero peor en la UI: obligaría a
decidir si un filtro los muestra o los esconde, y las dos respuestas son malas.

### 3.6 Lo único que arregla esto de verdad: preguntar

`agrega.html` hoy pide título, categoría, fecha, hora, lugar, comuna, precio,
link, descripción y contacto. **No pregunta la edad.** Un `<select>` de una
línea vale más que todas las reglas de arriba juntas:

```html
<div class="campo">
  <label for="publico" data-l="lPublico"></label>
  <select id="publico" name="publico">
    <option value="todos">Todo público</option>
    <option value="ninos">Para niños (hasta 12)</option>
    <option value="adolescentes">Para adolescentes (13 a 17)</option>
    <option value="adultos">Solo mayores de 18</option>
  </select>
  <div class="ayuda" data-l="aPublico"></div>
</div>
```

```js
lPublico:"¿Para quién es?",
aPublico:"Si en tu evento no entran menores de 18, dilo acá. Es el dato que "
       + "más nos piden los papás.",
```

Y en el cuerpo del correo: `` `Público: ${datos.get("publico")}` ``.

Además hay una lista blanca de recintos que resuelve el problema por el otro
lado, sin NLP: **Teatro San Ginés, Planetario USACH, Matucana 100 (sala
infantil), GAM (BiblioGAM), Museo Interactivo Mirador.** Diez líneas de
diccionario `recinto → publico` cubren más eventos infantiles que cualquier
regex sobre títulos.

Orden que recomiendo: campo en el formulario → lista blanca de recintos →
reglas de texto. En ese orden de confianza, y que la regla de texto nunca pise
un dato declarado.

---

## 4. La loica volando

### 4.1 El problema que puede resolver

Con 271 eventos y el mapa en `zoom: 12.5` centrado en `[-70.645, -33.437]`,
cuando alguien filtra fuerte pasa esto: **quedan 3 resultados y ninguno está en
pantalla.** El mapa se ve vacío, el panel dice "3 eventos", y no hay ninguna
pista de hacia dónde mover el mapa. Es el momento exacto en que la app parece
rota sin estarlo.

Ahí es donde la loica sirve. No como adorno: como el elemento que dice *"hacia
allá"*.

### 4.2 Tres variantes

**A. Loica mensajera — señala los resultados fuera de pantalla.**
Cuando hay resultados fuera del `bounds` actual, la loica despega del centro,
vuela en arco hacia el borde en la dirección del resultado más cercano, y se
posa ahí con una insignia: `3 ↗`. Se toca y el mapa vuela hasta incluirlos.
Es información, no decoración: soluciona el mapa-vacío-con-resultados.

**B. Loica de transición lista → pin.**
Al tocar una tarjeta, la loica sale de la tarjeta y vuela hasta el pin
correspondiente mientras el `flyTo` está corriendo. Bonito, ata la lista con el
mapa, pero no resuelve ningún problema: el `flyTo` ya comunica el vínculo.
Cuesta lo mismo que A y rinde menos.

**C. Loica del estado vacío.**
Con 0 resultados, la loica entra volando, se posa sobre el chip que más está
cortando, y ofrece sacarlo. Barata (reusa el vuelo de A) y útil, pero cubre un
estado que dura dos segundos.

### 4.3 Recomiendo A, con C de regalo

**A**, porque es la única de las tres que le entrega al usuario un dato que hoy
no tiene. Y **C** encima, porque una vez escrita la función `volar()` de A, C
son 15 líneas más.

Detalle de A:

- **Cuándo aparece:** después de cada `refrescar()`, si hay ≥1 evento visible
  con coordenadas fuera de `mapa.getBounds()` **y** los que están dentro son
  menos de 3. Si el mapa ya muestra harto, la loica no molesta.
- **Trayectoria:** bézier cuadrática desde el centro del mapa hasta un punto a
  28px del borde, en el ángulo del evento más cercano fuera de cuadro. El punto
  de control se desplaza 60px perpendicular al recorrido, lo que da un arco de
  pájaro en vez de una línea recta.
- **Duración:** 900ms con `cubic-bezier(.22,.8,.3,1)` — sale rápido, frena al
  posarse. El aleteo es una animación aparte de 160ms sobre un `<g>` interno.
  Posada, respira: `translateY` ±3px cada 2.4s.
- **Rotación:** la loica apunta hacia donde vuela (`rotate(angulo)`), y al
  posarse se endereza a 0. Sin eso vuela de costado y se ve mal.
- **Se toca:** `mapa.fitBounds` con los resultados fuera de cuadro, padding 60.

**`prefers-reduced-motion`: hay una trampa.** `loica.css:272` tiene:

```css
@media (prefers-reduced-motion: reduce){
  *{transition:none!important;animation:none!important}
}
```

Ese `!important` global mataría una animación CSS a mitad de camino y dejaría a
la loica clavada en el punto de partida, encima del centro del mapa. Por eso el
vuelo **se maneja desde JS con una guarda explícita**: si el usuario pide menos
movimiento, la loica no vuela — aparece directamente posada en el borde, con la
misma insignia, el mismo tamaño de toque y la misma función. Se pierde la
gracia, no se pierde la información.

### 4.4 Código

```html
<!-- dentro de <main>, después de #aviso -->
<button class="loica-vuelo" id="loica-vuelo" hidden
        aria-label="Hay eventos fuera de la pantalla">
  <svg viewBox="0 0 24 24" width="42" height="42" aria-hidden="true">
    <g class="cuerpo"></g>
  </svg>
  <span class="insignia-vuelo" id="insignia-vuelo">0</span>
</button>
```

```css
.loica-vuelo{
  position:absolute;top:0;left:0;z-index:5;
  width:52px;height:52px;padding:0;border:0;background:none;cursor:pointer;
  display:grid;place-items:center;
  filter:drop-shadow(0 4px 8px rgba(30,42,74,.35));
  /* el JS pone --x/--y/--giro; nada de transition acá, la anima el JS */
  transform:translate(var(--x,0),var(--y,0)) rotate(var(--giro,0deg));
  will-change:transform;
}
.loica-vuelo .insignia-vuelo{
  position:absolute;top:-2px;right:-4px;
  background:var(--rojo-loica);color:#fff;
  min-width:21px;height:21px;padding:0 5px;border-radius:var(--r-full);
  font:800 11px/21px var(--fuente-ui);text-align:center;
  border:2px solid var(--fondo-elevado);
}
/* Aleteo y respiración: se apagan solas con el bloque global de
   prefers-reduced-motion que ya existe en loica.css */
.loica-vuelo.volando .cuerpo{animation:aletear .16s ease-in-out infinite alternate}
.loica-vuelo.posada  .cuerpo{animation:respirar 2.4s ease-in-out infinite}
@keyframes aletear{from{transform:scaleY(1)}to{transform:scaleY(.62)}}
@keyframes respirar{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
```

```js
/* ---------- LA LOICA MENSAJERA ----------
   Aparece cuando hay resultados fuera de pantalla y el mapa se ve vacío.
   No es decoración: dice hacia dónde mover el mapa. */
const MENOS_MOVIMIENTO = matchMedia("(prefers-reduced-motion: reduce)");

const pajaro = document.getElementById("loica-vuelo");
pajaro.querySelector(".cuerpo").innerHTML = MASCOTAS.loica("var(--rojo-loica)");

let vueloEnCurso = null;

function posar(x, y, giro = 0){
  pajaro.style.setProperty("--x", x + "px");
  pajaro.style.setProperty("--y", y + "px");
  pajaro.style.setProperty("--giro", giro + "deg");
}

function volar(desde, hasta, alTerminar){
  cancelAnimationFrame(vueloEnCurso);
  const DURACION = 900;
  // Punto de control desplazado perpendicular al recorrido: da el arco.
  const dx = hasta.x - desde.x, dy = hasta.y - desde.y;
  const largo = Math.hypot(dx, dy) || 1;
  const ctrl = {x:(desde.x + hasta.x)/2 - dy/largo*60,
                y:(desde.y + hasta.y)/2 + dx/largo*60};
  const t0 = performance.now();
  const suavizar = t => 1 - Math.pow(1 - t, 3);   // ≈ cubic-bezier(.22,.8,.3,1)

  pajaro.classList.add("volando");
  pajaro.classList.remove("posada");

  (function paso(ahora){
    const t = suavizar(Math.min(1, (ahora - t0) / DURACION));
    const u = 1 - t;
    const x = u*u*desde.x + 2*u*t*ctrl.x + t*t*hasta.x;
    const y = u*u*desde.y + 2*u*t*ctrl.y + t*t*hasta.y;
    // Tangente de la bézier = hacia dónde mira el pájaro
    const tx = 2*u*(ctrl.x - desde.x) + 2*t*(hasta.x - ctrl.x);
    const ty = 2*u*(ctrl.y - desde.y) + 2*t*(hasta.y - ctrl.y);
    posar(x, y, Math.atan2(ty, tx) * 180 / Math.PI * (1 - t));
    if(t < 1) vueloEnCurso = requestAnimationFrame(paso);
    else{
      pajaro.classList.remove("volando");
      pajaro.classList.add("posada");
      alTerminar?.();
    }
  })(t0);
}

function actualizarLoicaVuelo(lista){
  const limites = mapa.getBounds();
  const conPin = lista.filter(e => e.lat != null);
  const fuera  = conPin.filter(e => !limites.contains([e.lon, e.lat]));
  const dentro = conPin.length - fuera.length;

  // Solo aparece si el mapa se ve vacío Y hay algo que mostrar afuera.
  if(!fuera.length || dentro >= 3){ pajaro.hidden = true; return; }

  const caja = document.getElementById("mapa").getBoundingClientRect();
  const centro = {x:caja.width/2 - 26, y:caja.height/2 - 26};

  // El de afuera más cercano al centro manda la dirección
  const objetivo = fuera
    .map(e => ({ev:e, p:mapa.project([e.lon, e.lat])}))
    .sort((a,b) => Math.hypot(a.p.x-caja.width/2, a.p.y-caja.height/2)
                 - Math.hypot(b.p.x-caja.width/2, b.p.y-caja.height/2))[0];

  const ang = Math.atan2(objetivo.p.y - caja.height/2, objetivo.p.x - caja.width/2);
  const radio = Math.min(caja.width, caja.height)/2 - 46;
  const borde = {x:caja.width/2 - 26 + Math.cos(ang)*radio,
                 y:caja.height/2 - 26 + Math.sin(ang)*radio};

  document.getElementById("insignia-vuelo").textContent = fuera.length;
  pajaro.hidden = false;
  pajaro.setAttribute("aria-label",
    `${fuera.length} ${fuera.length === 1 ? t("evento") : t("eventos")} fuera de la pantalla. `
    + `Toca para ir hasta ${fuera.length === 1 ? "él" : "ellos"}.`);

  if(MENOS_MOVIMIENTO.matches){
    // Sin vuelo: aparece posada. Misma información, cero movimiento.
    pajaro.classList.remove("volando");
    posar(borde.x, borde.y, 0);
    return;
  }
  volar(centro, borde);

  pajaro.onclick = () => {
    const b = new maplibregl.LngLatBounds();
    conPin.forEach(e => b.extend([e.lon, e.lat]));
    mapa.fitBounds(b, {padding:60, maxZoom:14,
                       duration: MENOS_MOVIMIENTO.matches ? 0 : 900});
  };
}

// Se recalcula al filtrar y cuando el mapa deja de moverse
mapa.on("moveend", () => actualizarLoicaVuelo(visibles()));
```

Y al final de `refrescar()`, antes del `return` del caso vacío:
`actualizarLoicaVuelo(lista);`

---

## 5. Estados

### 5.1 Cero resultados: decir cuál filtro sobra

Hoy el vacío dice *"No hay eventos con esos filtros / Prueba sacando algún
filtro"*. Es correcto y es inútil: no dice cuál.

La app puede calcularlo. `visibles(salvo)` ya acepta ignorar una dimensión, así
que basta con probar las siete y quedarse con la que más resultados libera:

```js
function culpable(){
  // Qué filtro, sacado solo él, devuelve más eventos.
  const dims = ["cuando","franja","precio","mascotas","publicos","comunas","cerca"];
  return dims
    .filter(d => d === "mascotas" || d === "publicos" || d === "comunas"
               ? F[d].size : (d === "cerca" ? F.cerca
               : F[d] !== (d === "franja" ? null : "todo")))
    .map(d => ({dim:d, n:visibles(d).length}))
    .sort((a,b) => b.n - a.n)[0];
}

const NOMBRE_DIM = {cuando:"la fecha", franja:"la franja horaria",
  precio:"el precio", mascotas:"el tipo de panorama",
  publicos:"el público", comunas:"la comuna", cerca:"la distancia"};

function pintarVacio(cont){
  const c = culpable();
  cont.innerHTML = `
    <div class="vacio">
      ${mascota("loica","var(--tinta-tenue)",78)}
      <p><b>${t("vacio")}</b></p>
      ${c && c.n ? `
        <p class="pista">Sacando <b>${NOMBRE_DIM[c.dim]}</b> aparecen
           <b>${c.n}</b> ${c.n === 1 ? t("evento") : t("eventos")}.</p>
        <button class="boton" id="soltar-culpable">
          Quitar ${NOMBRE_DIM[c.dim]}
        </button>` : `
        <button class="boton secundario" onclick="limpiarFiltros()">
          Limpiar todos los filtros
        </button>`}
    </div>`;
  const b = document.getElementById("soltar-culpable");
  if(b) b.onclick = () => { soltar(c.dim); pintarFiltros(); refrescar(); };
}

function soltar(dim){
  if(dim === "cuando") F.cuando = "todo";
  else if(dim === "precio") F.precio = "todo";
  else if(dim === "franja") F.franja = null;
  else if(dim === "cerca")  F.cerca = null;
  else F[dim].clear();
}
```

Con un filtro solo puesto el mensaje es medio obvio; con cuatro puestos es la
diferencia entre resolverlo y cerrar la app.

### 5.2 Muchos filtros: que se vean todos, sin scroll horizontal

Cuando hay 2 o más filtros activos aparece una fila de resumen sobre la lista.
A diferencia del riel actual, **esta envuelve (`flex-wrap`)**: nada queda fuera
de pantalla, aunque tome dos o tres líneas.

```html
<div class="resumen-filtros" id="resumen-filtros" hidden></div>
```

```css
.resumen-filtros{
  display:flex;flex-wrap:wrap;gap:6px;
  padding:var(--e-2) var(--e-4);border-bottom:1px solid var(--borde);
}
.pildora{
  display:inline-flex;align-items:center;gap:5px;
  background:var(--fondo-hundido);border:1px solid var(--borde);
  border-radius:var(--r-full);padding:4px 6px 4px 11px;
  font:600 var(--t-xs)/1 var(--fuente-ui);color:var(--tinta);
}
.pildora button{
  border:0;background:none;cursor:pointer;color:var(--tinta-suave);
  width:20px;height:20px;border-radius:50%;font-size:14px;line-height:1;padding:0;
}
.pildora button:hover{background:var(--borde);color:var(--tinta)}
.pildora.limpiar{background:none;border-color:transparent;color:var(--acento);
  text-decoration:underline;padding:4px 8px;cursor:pointer}
```

```js
function pintarResumen(){
  const caja = document.getElementById("resumen-filtros");
  const items = [];
  const agrega = (etq, alQuitar) => items.push({etq, alQuitar});

  if(F.cuando !== "todo") agrega(t(F.cuando) || F.cuando, () => F.cuando = "todo");
  if(F.franja) agrega(NOMBRE_FRANJA[F.franja], () => F.franja = null);
  if(F.precio === "gratis") agrega(t("gratis"), () => F.precio = "todo");
  if(F.precio === "hasta10") agrega("Hasta $10.000", () => F.precio = "todo");
  F.mascotas.forEach(m => agrega(NOMBRE_MASCOTA[m], () => F.mascotas.delete(m)));
  F.publicos.forEach(p => agrega(NOMBRE_PUBLICO[p], () => F.publicos.delete(p)));
  F.comunas.forEach(c  => agrega(c, () => F.comunas.delete(c)));
  if(F.cerca) agrega(`A menos de ${F.cerca.radioKm} km`, () => F.cerca = null);

  caja.hidden = items.length < 2;
  if(caja.hidden) return;
  caja.innerHTML = "";
  items.forEach(({etq, alQuitar}) => {
    const p = document.createElement("span");
    p.className = "pildora";
    p.innerHTML = `${escapar(etq)}<button aria-label="Quitar ${escapar(etq)}">×</button>`;
    p.querySelector("button").onclick = () => { alQuitar(); pintarFiltros(); refrescar(); };
    caja.appendChild(p);
  });
  const limpiar = document.createElement("button");
  limpiar.className = "pildora limpiar";
  limpiar.textContent = `Limpiar (${activos()})`;
  limpiar.onclick = limpiarFiltros;
  caja.appendChild(limpiar);
}
```

### 5.3 Limpiar todo de un toque

Tres caminos al mismo sitio, y **todos anuncian el resultado**:

```js
function limpiarFiltros(){
  F = FILTROS_VACIOS();
  guardarEnUrl();
  pintarFiltros(); pintarResumen(); refrescar();
  anunciar(`Filtros limpiados. ${EVENTOS.length} ${t("eventos")}.`);
}

/* Región viva para lectores de pantalla: hoy el conteo cambia en silencio. */
function anunciar(texto){
  let r = document.getElementById("anuncio");
  if(!r){
    r = document.createElement("div");
    r.id = "anuncio"; r.className = "solo-lectores";
    r.setAttribute("role","status"); r.setAttribute("aria-live","polite");
    document.body.appendChild(r);
  }
  r.textContent = texto;
}
```

```css
.solo-lectores{
  position:absolute;width:1px;height:1px;overflow:hidden;
  clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;
}
```

Los tres caminos: la píldora "Limpiar (N)" del resumen, el "Limpiar" de la
esquina de la hoja, y el botón del estado vacío.

### 5.3.1 Claves de traducción que hay que agregar

`TEXTOS` en `loica.js` no tiene nada de esto. Los tres idiomas o no se toca
ninguno — hoy la app está completa en es/en/pt y sería una regresión romperlo:

```js
// es
filtros:"Filtros", limpiar:"Limpiar", manana:"Mañana", sieteDias:"7 días",
elegirFecha:"Elegir fecha", franjaManana:"Mañana", franjaTarde:"Tarde",
franjaNoche:"Noche", hasta10:"Hasta $10.000", cualquierPrecio:"Cualquier precio",
queEs:"Qué es", paraQuien:"Para quién", donde:"Dónde", cercaMio:"Cerca mío",
conNinos:"Con niños", conNinosPie:"Sin eventos +18",
adolescentes:"Adolescentes", soloAdultos:"Solo +18",
verN:"Ver {n} panoramas", buscarZona:"Buscar en esta zona",
enEstaZona:"en esta zona", verTodos:"Ver todos",
sacando:"Sacando {dim} aparecen {n}", quitar:"Quitar {dim}",
horaPorConfirmar:"Hora por confirmar", fueraPantalla:"fuera de la pantalla",

// en
filtros:"Filters", limpiar:"Clear", manana:"Tomorrow", sieteDias:"7 days",
… conNinos:"With kids", conNinosPie:"No 18+ events", soloAdultos:"18+ only",

// pt
filtros:"Filtros", limpiar:"Limpar", manana:"Amanhã", sieteDias:"7 dias",
… conNinos:"Com crianças", conNinosPie:"Sem eventos +18", soloAdultos:"Só +18",
```

Los nombres de comuna **no se traducen** (Ñuñoa es Ñuñoa en los tres idiomas), y
los nombres de las mascotas tampoco.

### 5.4 Estados que hoy no existen y hay que cubrir

- **Cargando.** Entre el `fetch` y el primer `refrescar()` la lista está en
  blanco. Tres tarjetas fantasma con la silueta de la mascota.
- **Filtro que quedaría en 0.** En la hoja va deshabilitado con su `0` en gris.
  Vale más que el 90% de los mensajes de error.
- **Sin geolocalización.** Si "Cerca mío" se rechaza, se apaga solo y muestra
  *"Necesito tu ubicación para esto"*. No se queda pegado prendido.

---

## 6. Interacción con el mapa

### 6.1 Un hallazgo que cambia la respuesta

Antes de decidir si el mapa filtra, hay que mirar dónde están los pines:

```
precision = "comuna"       124  (45,8%)   ← centroide de la comuna
precision = "recinto"       81  (29,9%)
precision = "sin_ubicar"    42  (15,5%)   ← sin pin
precision = "fuente"        24  ( 8,9%)
```

Y las coordenadas repetidas:

```
(-33.4425, -70.6505)  →  45 eventos   ← centroide de Santiago
(-33.4256, -70.6096)  →  44 eventos   ← centroide de Providencia
(-33.4460, -70.6520)  →  25 eventos
(-33.4436, -70.6836)  →  18 eventos
```

**89 de los 229 eventos con pin (39%) están apilados en dos coordenadas
idénticas.** `maplibregl.Marker` los dibuja uno encima de otro: en el pixel del
centroide de Santiago hay 45 marcadores y el usuario solo puede tocar el de
arriba. Los otros 44 existen en el DOM y son inalcanzables.

Ese es el problema más grave del mapa hoy, y no tiene nada que ver con los
filtros. Hay que arreglarlo antes de agregarle inteligencia al mapa.

### 6.2 ¿Debería el mapa filtrar por lo que se ve? No por defecto

Con estos datos, filtrar por viewport sería **activamente engañoso**:

- Los 42 eventos sin coordenadas (15,5%) desaparecerían siempre, sin explicación.
- Los 124 del centroide de comuna aparecen y desaparecen según el encuadre por
  una ubicación que la app misma marca como *"Ubicación aproximada: centro de
  la comuna"*. Un evento en Ñuñoa dibujado en el centro de Ñuñoa entra o sale
  del cuadro por un motivo que no es real.
- El conteo saltaría con cada gesto, y el usuario no puede saber si cambió
  porque movió el mapa o porque tocó un filtro.

**Decisión: el conteo del panel es global y no cambia al mover el mapa.**
Es el número de la verdad y tiene que quedarse quieto.

### 6.3 Lo que sí: "Buscar en esta zona", a pedido

El mapa aporta una zona cuando el usuario lo pide, no cuando respira.

```js
/* Aparece después de mover el mapa más de un cuarto de pantalla. El umbral
   evita que salte con el flyTo de abrir una ficha. */
let centroAncla = mapa.getCenter();

mapa.on("moveend", () => {
  const d = mapa.getCenter().distanceTo(centroAncla);       // metros
  const anchoVista = mapa.getBounds().getNorthWest()
                        .distanceTo(mapa.getBounds().getNorthEast());
  document.getElementById("buscar-zona").hidden =
    d < anchoVista * 0.25 || !!F.cerca;
});

document.getElementById("buscar-zona").onclick = () => {
  const b = mapa.getBounds();
  const radio = b.getNorthWest().distanceTo(b.getSouthEast()) / 2000;  // km
  F.cerca = {lat:mapa.getCenter().lat, lon:mapa.getCenter().lng, radioKm:radio};
  centroAncla = mapa.getCenter();
  document.getElementById("buscar-zona").hidden = true;
  pintarFiltros(); pintarResumen(); refrescar();
  anunciar(`${visibles().length} ${t("eventos")} en esta zona.`);
};
```

Al activarse, la zona se convierte en **una píldora más del resumen**
(`A menos de 4 km ×`), igual que cualquier otro filtro. El usuario ve que hay
un filtro geográfico puesto y lo saca donde saca todos los demás. Eso es lo que
hoy no pasa: hoy el mapa y los filtros no se hablan porque el mapa no tiene
manera de decir nada.

### 6.4 El conteo: global arriba, local abajo

```
  43 panoramas              ← el filtro. No se mueve al mover el mapa.
  12 en esta zona · ver todos
```

La segunda línea sí se actualiza con `moveend`, en gris, y "ver todos" hace
`fitBounds` sobre los 43. Así el mapa informa sin decidir.

### 6.5 Antes de nada: arreglar los pines apilados

Los 124 eventos con `precision: "comuna"` no deberían tener pin individual.
Uno por comuna, con el conteo adentro y borde punteado — que se lea distinto de
un pin exacto:

```js
function pintarPines(lista){
  marcadores.forEach(m => m.remove());
  marcadores = [];

  const exactos = lista.filter(e => e.lat != null && e.precision !== "comuna");
  const porComuna = new Map();
  lista.filter(e => e.lat != null && e.precision === "comuna")
       .forEach(e => {
         const k = e.comuna || `${e.lat},${e.lon}`;
         if(!porComuna.has(k)) porComuna.set(k, []);
         porComuna.get(k).push(e);
       });

  exactos.forEach(ev => marcadores.push(pinDeEvento(ev)));

  porComuna.forEach((evs, comuna) => {
    const el = document.createElement("div");
    el.className = "pin-comuna";
    el.setAttribute("role", "button");
    el.setAttribute("aria-label",
      `${evs.length} eventos en ${comuna}, ubicación aproximada`);
    el.innerHTML = `<span>${evs.length}</span>`;
    el.onclick = e => {
      e.stopPropagation();
      F.comunas = new Set([comuna]);
      pintarFiltros(); pintarResumen(); refrescar();
    };
    marcadores.push(new maplibregl.Marker({element:el})
      .setLngLat([evs[0].lon, evs[0].lat]).addTo(mapa));
  });
}
```

```css
.pin-comuna{
  width:40px;height:40px;border-radius:50%;cursor:pointer;
  display:grid;place-items:center;
  background:var(--fondo-elevado);color:var(--tinta);
  /* punteado = "acá adentro, en algún lado". Un pin sólido mentiría. */
  border:2.5px dashed var(--borde-fuerte);
  font:800 var(--t-sm)/1 var(--fuente-ui);
  box-shadow:var(--sombra-2);
}
.pin-comuna:hover{border-color:var(--acento);color:var(--acento)}
```

Los 42 sin coordenadas siguen apareciendo en la lista sin pin, como hoy — esa
decisión ya estaba bien tomada y está comentada en `exportar_web.py:100`.

---

## 7. Otros hallazgos de los datos (fuera del encargo, pero hay que decirlos)

**Hay 10 eventos que no son de Santiago.** Talca, Valparaíso, Villarrica, Punta
Arenas, La Serena, Vicuña, Valdivia, Pirque. Casi todos vienen de PortalTickets.
Peor: dos de ellos están geocodificados al centro de Santiago —
`ALEXIDERAL: TOUR LA HERIDA EN CASAFACTORÍA, TALCA` y
`ANTONIO MONASTERIO ENSAMBLE EN TEATRO MAURI SCD, VALPARAISO` figuran ambos en
`(-33.4425, -70.6505)` con `comuna: "Santiago"`. El geocodificador no encontró
la dirección y cayó al centroide de la comuna sin comprobar si la comuna es de
la Región Metropolitana. Un evento de Valparaíso aparece como panorama del
centro de Santiago.

Filtro sugerido para `es_panorama()`: si el título contiene una ciudad de otra
región y la comuna no está en la lista de comunas de la RM, se descarta.

**La categoría `idiomas` no tiene ningún evento**, así que su chip nunca se
dibuja, pero sigue ocupando espacio en `CATEGORIAS` de `loica.js` y en el
formulario de `agrega.html`. Con el agrupamiento por mascota deja de importar:
cae dentro del Chincol.

**Los eventos de PortalTickets traen la descripción duplicada del título** más
`"// PortalTickets.cl Sitio en mantención"`. Son 40 eventos donde la
descripción no aporta nada al clasificador ni al usuario, y donde el texto
"Sitio en mantención" aparece en la ficha.

---

## 8. Orden de implementación

| # | Qué | Dónde | Por qué primero |
|---|---|---|---|
| 1 | Límites de palabra en `clasificar()` + prior de fuente | `exportar_web.py` | Sin esto, cualquier filtro por categoría miente sobre el 38% del catálogo |
| 2 | Arreglar `esFinde` y "Hoy" | `index.html` | Dos de los tres filtros visibles están malos |
| 3 | `filtroCat` → `Set`, estado en `F` | `index.html` | Habilita todo lo demás; es refactor puro |
| 4 | Barra primaria + hoja de filtros | `index.html`, `loica.css` | El cambio que se ve |
| 5 | Pines de comuna agrupados | `index.html` | 44 eventos hoy son inalcanzables |
| 6 | `publico` en el exportador + campo en `agrega.html` | `exportar_web.py`, `agrega.html` | El filtro de edades |
| 7 | Loica mensajera | `index.html`, `loica.css` | Encima de todo lo anterior |

Los pasos 1 y 2 se pueden hacer hoy y mejoran la app sin tocar el diseño.

---

## Apéndice — cómo se midieron los números

- **Anchos de chips:** se renderizó la fila real (`.filtros` + `.chip` de
  `loica.css`, Manrope cargada desde Google Fonts, las 13 etiquetas que produce
  `pintarFiltros()`) dentro de un contenedor de 375px, y se leyeron
  `getBoundingClientRect()` y `scrollWidth` con las fuentes ya resueltas
  (`document.fonts.ready`).
- **Repartos, comunas, precios, horas, coordenadas repetidas:** conteos directos
  sobre `web/eventos.json` (271 eventos, `generado: 2026-08-10T23:13:40`).
- **Clasificadores:** las reglas de la sección 3.4 se corrieron completas sobre
  los 271 eventos antes de escribirlas acá. Los repartos que aparecen
  (`otros: 102 → 0`, `adultos: 21`, `ninos: 2`) son resultados de esa corrida,
  no proyecciones.
- **Precisión de las etiquetas:** revisión a mano, evento por evento, de los 31
  que quedan distintos de `todos` y de una muestra de 20 de los 73 que reciben
  categoría por prior de fuente. Es una muestra chica: tratar los porcentajes
  como orden de magnitud, no como medición.
