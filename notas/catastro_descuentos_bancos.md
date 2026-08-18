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

## Sondeo dirigido 2026-08-18 — Ripley, Entel, Mercado Pago, BICE, Scotiabank

Se rehizo el sondeo sobre los seis emisores pedidos. **robots.txt de los seis
permite todo lo que se consultó.** El método fue el de siempre: HTTP educado,
y cuando la URL no aparecía, leer el bundle de JavaScript del propio sitio para
ver a qué endpoint le habla. Un navegador se usó sólo para observar peticiones
de páginas públicas, nunca para saltarse un control.

### Banco Ripley — ENCENDIDO. El segundo mejor dato del catastro.

La ruta que fallaba era la adivinada: no es `/beneficios` sino
`/beneficios-y-promociones`, y ésa es una SPA de Angular que no trae el
catálogo en el HTML. El catálogo sale de:

```
POST https://www.bancoripley.cl/api/call-sp-api
     x-path-api: /api/sp/beneficios/get-activeBox-beneficio
     x-method-api: POST
     content-Type: application/x-www-form-urlencoded
     body: idSection=restofans
```

Todo el back pasa por ese único endpoint y el recurso se pide por cabecera.
Sin credencial, sin WAF, sin token. **73 restaurantes ("Restofans"), 40 en la
Región Metropolitana.**

Por local: `txtNameComercio`, `txtSubtitulo` (tipo de cocina, puesto por el
banco), `txtDescuento`, `txtValidezBeneficio` (el día), `arrDireccion` (calle y
número), `txtDetalleCard` (`R.M. (Vitacura)`), `arrHorarios`, `txtLegal` (tope).

**La trampa, y es cara.** `arrVigencia` dice *"Todos los sábados de agosto"* en
63 de los 73 locales: es la vigencia de LA CAMPAÑA, no el día de cada
restaurante. Leerlo como día ponía a los 73 en sábado — Pastamore, que es de
lunes, salía también el sábado. El día sale **sólo** de `txtValidezBeneficio`.

Repartido real: jueves 38, martes 11, "todos los días" 10, miércoles 8, lunes 3,
sábado 3. La campaña es mensual y el nombre de la caja lo dice ("Restofans
Agosto 2026"): si un mes no aparece, se acabó la campaña, no se rompió nada.

### Entel — ENCENDIDO. Poco volumen, día casi siempre.

No es banco sino telco, pero el descuento funciona igual y la pregunta del
usuario no distingue quién lo emite. `entel.cl/beneficios/` trae el catálogo
como JSON incrustado en el HTML (CMS Modyo), igual que Cencosud. La sección
`Beneficios Comida` da **28 beneficios, 19 con día**: Starbucks, Burger King,
Domino's, Dunkin, Doggis, Juan Maestro, Rappi.

Son cadenas nacionales y **no publican dirección ni comuna**. Ahí choca con el
préstamo de direcciones entre bancos: a "Starbucks" le presta la dirección del
Starbucks de San Sebastián 2946 y queda como si el descuento fuera sólo en ése.
Son 9 casos. Ver "pendiente" más abajo.

### Mercado Pago — SIN CATÁLOGO WEB PÚBLICO.

`/beneficios`, `/promociones`, `/descuentos`, `/cuenta/beneficios` y
`/c/promociones-bancarias` responden **200 con la página de "no existe"** (404
disfrazado). robots.txt no lo prohíbe y no hay sitemap (403). No se encontró
catálogo web: en Chile los beneficios de Mercado Pago parecen vivir sólo dentro
de la app. **Queda apagado por falta de fuente, no por bloqueo.**

### BICE — BLOQUEADO POR VERIFICACIÓN DE NAVEGADOR. No se rodea.

`www.bice.cl/beneficios` responde **403 con "Estamos verificando su conexión —
Enable JavaScript and cookies"**. Eso es un desafío anti-bot, no un descuido.
`portal.bice.cl` ni siquiera conecta.

Mismo criterio que Santander, y por la misma razón: rodear eso con un navegador
automatizado sería evadir un control puesto a propósito. **No se hace.** Si el
catálogo se quiere, va por captura a mano como Santander, o pidiéndole acceso a
BICE.

### Scotiabank — EL CATÁLOGO ESTÁ TRAS AUTENTICACIÓN.

Corrige a medias el sondeo anterior: `scotiaclub.cl/scclubfront/categoria/...`
**sí** responde 200 y sin login (405 KB), y existen rutas gastronómicas propias
("Ruta Gourmet", "Ruta Rápida", "Ruta Dulce"). Pero eso es sólo el cascarón: los
`.card` de la página son navegación, no comercios. El catálogo se carga después
y detrás de `/scclubfront/auth`.

Sacarlo usando la sesión iniciada de una persona significaría publicar contenido
autenticado —posiblemente segmentado por cliente— como si fuera público.
**Descartado**, igual que en el sondeo anterior.

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
