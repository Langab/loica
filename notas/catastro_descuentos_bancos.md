# Catastro: descuentos bancarios en restaurantes (Chile)

Sondeo hecho el 2026-08-11 sobre los portales públicos de beneficios de los
principales emisores de tarjetas del país. El objetivo era responder una
pregunta concreta: **¿de cuáles se puede sacar el dato estructurado (comercio,
día de la semana, tarjeta, comuna) sin scrapear HTML a mano?**

La respuesta corta: de tres se puede muy bien, y uno de ellos —Banco de Chile—
entrega exactamente el modelo que necesita la app. El resto está detrás de WAF,
de login, o simplemente no publica el dato en forma legible.

Mismo criterio legal que los eventos: esto **indexa y deriva tráfico a la
fuente**, no la reemplaza. Cada descuento queda amarrado al link del banco.

---

## Resumen

| Banco | Portal | Acceso | Dato estructurado | Día de semana | Veredicto |
|---|---|---|---|---|---|
| **Banco de Chile** (+ Edwards) | sitiospublicos.bancochile.cl | API abierta, sin token | ★★★ | ✅ en tags | **Encender ya** |
| **Banco Falabella / CMR** | Contentful | Token público en bundle JS | ★★★ | ✅ campo propio | **Encender ya** |
| **BCI** | vivirconbeneficios.cl | API abierta, sin token | ★★ | ❌ hay que parsear | **Encender, con parseo** |
| Santander | banco.santander.cl | WAF 403 | PDF mensual | ✅ pero en PDF | Difícil |
| Scotiabank | scotiarewards.cl | Tras login | — | — | Descartado |
| Itaú | itau.cl | SPA vacía / no resuelve | — | — | Pendiente |
| BancoEstado | bancoestado.cl | Shell de 2 KB | — | — | Pendiente |
| MACH | machbank.cl | Contentful (7,4 MB) | ? | ? | Pendiente |
| Coopeuch | coopeuch.cl | HTML | ? | ? | Pendiente |
| Ripley / BICE / Security / Cencosud / Tenpo | varios | 404 en rutas probadas | — | — | Falta encontrar ruta |

---

## Tier 1 — listos para el pipeline

### 1. Banco de Chile — el mejor dataset por lejos

```
https://sitiospublicos.bancochile.cl/api/content/spaces/personas/types/beneficios/entries?per_page=100&page=N
```

Sin token, sin cabeceras especiales, sin WAF. Es un CMS headless (mismo motor
que ya sabemos leer con `json_api`). **829 beneficios en 9 páginas.**

Reparto por categoría:

| n | categoría |
|---|---|
| 250 | `beneficios/sabores/restaurantes-y-bares` |
| 216 | `beneficios/beneficios-y-descuentos` |
| 79 | `beneficios/bienestar/salud` |
| 62 | `beneficios/sabores/40-de-descuento-visa` |
| 39 | `beneficios/bienestar/belleza` |
| 30 | `beneficios/sabores/sabores-gourmet` |
| 24 | `beneficios/panoramas/entretencion` |
| 19 | `beneficios/sabores/dolares-premio` |
| 13 | `beneficios/sabores/cafeterias` |

**De los 250 restaurantes y bares, 247 traen el día de la semana en los tags.**
Eso es el 98,8%: el filtro "¿dónde como hoy?" sale prácticamente gratis.

Los tags mezclan tres dimensiones en una sola lista plana, sin prefijo:

```json
"tags": ["metropolitana de santiago", "providencia", "martes", "segmentado"]
"tags": ["valparaíso", "concón", "martes", "jueves", "segmentado"]
"tags": ["sabado", "los lagos", "osorno", "segmentado"]
```

Hay que clasificarlos por diccionario (día / región / comuna), igual que hace
`clasificar.py` con las categorías de eventos. Ojo con la inconsistencia de
tildes: aparece `sabado` y `miercoles` sin tilde, pero `valparaíso` con tilde.
`normalizar._plano()` ya resuelve eso.

Campos útiles de `fields`:

| Campo | Ejemplo |
|---|---|
| `Titulo` | `SKY BAR` |
| `Extracto` | `lunes y martes presencial` |
| `Descripcion` | HTML con la reseña y el `20%` |
| `Condiciones Comerciales` | tope, exclusiones, si aplica online o presencial |
| `Vigencia` | `Promoción válida hasta el 31 de marzo de 2027.` |
| `Tarjetas Permitidas` | lista de slugs, ver abajo |
| `Logo`, `Portada` | imágenes en assets.bancochile.cl |
| `Telefono`, `Sitio web`, `Sucursales` | contacto |

`Tarjetas Permitidas` viene como slugs limpios, ideal para chips de filtro:

```
visa-credito-infinite, visa-credito-signature, visa-credito-platinum,
visa-fan-credito, mastercard-credito-black, mastercard-credito-platinum,
visa-debito-infinite, visa-debito-signature, ...
```

El `%` no tiene campo propio — hay que sacarlo con regex de `Descripcion` +
`Condiciones Comerciales`. En la muestra salió limpio (20%, 30%).

El tag `segmentado` marca los beneficios que no son para todos los clientes.
Conviene mostrarlo como advertencia, no filtrarlo.

### 2. Banco Falabella / CMR — Contentful, día y región en campos propios

Space `p6eyia4djstu`, token de lectura público incrustado en el bundle de Next:

```
https://cdn.contentful.com/spaces/p6eyia4djstu/environments/master/entries?content_type=descuentos&limit=100&access_token=560c0ddde9630e43122ef3e7879d69013844ee3d48c566d4ba93125924f080dd
```

(Es un Content Delivery token, de solo lectura y pensado para ser público. Aun
así conviene crawl delay y no martillar.)

**526 entradas en `descuentos`**, y esta vez el día es un campo propio, no un tag:

```json
{
  "nombreBeneficio": "CMR Days Farmacias Ahumada Agosto",
  "categoriaV2": ["Regiones", "Salud", "Belleza"],
  "diasDescuento": ["Miércoles", "Jueves", "Viernes", "Martes"],
  "fechaTerminoV2": "2026-08-14T23:59",
  "region": ["Región de Arica y Parinacota", "Región de Tarapacá", ...]
}
```

Campos: `nombreBeneficio`, `permalink`, `categoriaV2`, `diasDescuento`,
`region`, `fechaIngresoV2`, `fechaTerminoV2`, `tipoBeneficio`,
`empresaBeneficioV2`, `subtituloCajaV2`, `descripcionCortaApp`.

La categoría gastronómica se llama **`Antojos`**.

`fechaTerminoV2` es fecha real ISO, así que la vigencia se puede filtrar sin
parsear prosa. Mejor que Banco de Chile en eso.

Otros content types del mismo space:
- `locationsBenefits` (14): `locationName`, `region`, `comuna`, `address`, `days` — sucursales con día.
- `beneficiosRestaurant` (8): **desactualizado**, las vigencias dicen 2021. No usar.
- `newBenefits`, `cardBenefits`: material de marketing, poco dato duro.

### 3. BCI — mucho volumen, pero el día hay que parsearlo

BCI tiene dos caras. `bci.cl/beneficios` responde **403** (WAF), pero el portal
real de contenidos es abierto:

```
https://www.vivirconbeneficios.cl/descuentos/promotions.json?per_page=100&page=N
```

**2.296 promociones en 23 páginas.** Además se puede filtrar por categoría
usando la ruta, lo que ahorra bajar todo:

```
https://www.vivirconbeneficios.cl/descuentos/sabores/restaurantes/promotions.json?per_page=100   → 27
https://www.vivirconbeneficios.cl/descuentos/sabores/comida-rapida/promotions.json
https://www.vivirconbeneficios.cl/descuentos/communes/grouped_communes.json                      → comunas
```

Estructura: `{promotions: [...], meta: {total_entries, per_page, current_page, total_pages}}`.
Es un Rails clásico, la paginación es estándar.

Campos por promoción: `id`, `uuid`, `url`, `title`, `slug`, `description`,
`covers`, `tags`, `category`, `options.conditions`, `created_at`, `updated_at`.

**El problema:** ni el día de la semana ni el porcentaje son campos. Todo viene
enterrado en HTML dentro de `description` y `options.conditions`:

```html
<h3>Hasta un 67% dcto</h3><p>...</p>
<li class="direccion"><i class="icon-map-marker"></i> Av. Vitacura 8745<br>Vitacura</li>
<li class="telefono">222 428 088</li>
```

Lo bueno: ese HTML es **regular** —usa clases `direccion`, `telefono`, `web`—
así que se saca dirección y teléfono con selectores estables, no con adivinanza.
El día sí hay que buscarlo por palabra en el texto de `conditions`.

Los `tags` traen comuna y tipo de cocina (`valparaiso`, `restaurant`, `café`,
`costa`), útiles para categorizar aunque estén sucios.

`updated_at` revela un problema de frescura: varias promociones no se tocan
desde 2021. Hay que cruzar con la vigencia declarada en `conditions` y no
confiar en que "está publicado" signifique "está vigente".

---

## Tier 2 — bloqueados, pendientes o sin dato

**Santander.** Todo `banco.santander.cl` responde 403 con página "Internet
Connection Error", incluso con User-Agent y cabeceras de navegador. Es WAF.
Publican un PDF mensual con el calendario de Sabores:

```
banco.santander.cl/uploads/000/057/921/<uuid>/original/SABORES_ENERO_2026_1_.pdf
```

Tope declarado $40.000. El problema es que la URL lleva un UUID que cambia cada
mes, así que ni siquiera se puede armar por plantilla. Habría que descubrir el
link desde una página que también está tras el WAF. **Es el catálogo más rico
del mercado y el más difícil de automatizar.** Queda para después.

**Scotiabank.** El portal de beneficios vive en
`scotiarewards.cl/scclubfront/` y las rutas de descuentos están tras
`/scclubfront/auth`. La página pública (423 KB) no trae el catálogo. Descartado
mientras no haya acceso legítimo.

**Itaú.** `beneficios.itau.cl` no resolvió (timeout, código 000). `itau.cl/beneficios`
devuelve un shell de 12 KB. Hay que buscar la ruta real del portal.

**BancoEstado.** `bancoestado.cl/beneficios` devuelve 2,5 KB — es un redirect o
shell. Falta encontrar dónde vive el contenido.

**MACH.** `machbank.cl/beneficios` devuelve **7,4 MB** de HTML y usa Contentful.
Prometedor (tienen cupones tipo `MACHBANK30` de 30% en restaurantes) pero hay
que extraer space y token del bundle, igual que con Falabella.

**Coopeuch.** 280 KB de HTML. El `/api/8774324/api_dynamic` que aparece es
Dynatrace (monitoreo), no beneficios. Falta buscar el endpoint real.

**Ripley, BICE, Security, Cencosud, Tenpo.** Las rutas que probé dieron 404 o
no resolvieron. No significa que no exista portal — significa que adiviné mal
la URL. Pendiente de sondeo dirigido.

---

## Lo que esto implica para la app

Con solo los tres del Tier 1 hay del orden de **800 descuentos gastronómicos
con día de la semana**, cubriendo Santiago y regiones. Suficiente para lanzar.

### El modelo de datos es distinto al de eventos

Un evento pasa una vez y tiene fecha. Un descuento **se repite todas las
semanas** y tiene vigencia. Es más parecido al `recurrencia.py` que ya existe
que a un evento suelto:

```
comercio, categoria, banco, porcentaje, dias[], tarjetas[],
comuna, region, tope, vigencia_hasta, presencial/online, url_fuente
```

### Los filtros, en la lógica del elenco de animales

El chip que importa es **"Hoy"**. La pregunta real del usuario no es "muéstrame
descuentos", es *"es martes, estoy en Providencia, tengo tarjeta BCI, ¿dónde
como?"*. Ese cruce —día × comuna × banco— es todo el producto.

Filtros propuestos, en dos filas como el calendario y el mapa:

- **Fila 1 (cuándo/dónde):** Hoy · Este finde · día suelto · comuna
- **Fila 2 (con qué):** banco · tipo de tarjeta (crédito/débito) · categoría · % mínimo

El elenco de `_bichos.html` se traduce directo: en vez de una carita por animal,
un logo o color por banco, con el mismo sistema de chips y pines. Banco de Chile
y Falabella ya entregan logo en la API, así que ni siquiera hay que dibujarlos.

### Riesgo principal: la frescura

Es el punto débil de todo esto. BCI tiene promociones sin tocar desde 2021
todavía publicadas. Una app de descuentos que manda a alguien a un restaurante
con un descuento vencido pierde la confianza de inmediato — mucho más rápido que
una agenda con un evento pasado.

Mitigación: filtrar por `fechaTerminoV2` (Falabella) y por la fecha parseada de
`Vigencia` (Banco de Chile), y marcar como "verificar" todo lo que no declare
vigencia o cuyo `updated_at` tenga más de un año.

### Siguiente paso concreto

Los tres del Tier 1 caben en `json_api` con mapeo declarativo en
`config/fuentes.yaml`, sin escribir un adaptador nuevo — que es exactamente el
caso de uso para el que se construyó. Lo que sí hay que agregar es:

1. Un modelo `Descuento` en `modelo.py` (o un flag en `Evento`).
2. Un clasificador de tags → (día / comuna / región), estilo `clasificar.py`.
3. Extracción del `%` por regex, con revisión manual de los que no matcheen.
