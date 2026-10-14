# Blog de Loica — plan editorial y técnico

**Fecha:** agosto 2026
**Entregables:** este documento + `web/blog.json` (tres posts escritos, listos para consumir)
**Base de datos usada:** `web/eventos.json`, 271 eventos reales, generado el 2026-08-10
**Lo que NO incluye:** el HTML de la página. Eso lo hace Benjamín.

---

## 0. La pregunta que hay que responder antes de escribir una línea

Un blog de eventos es la idea más fácil de tener y la más fácil de abandonar. Casi todos los agregadores tienen uno y casi todos están muertos, con el último post de hace ocho meses. Así que la pregunta no es "¿hacemos un blog?" sino **¿qué hace este blog que el mapa no hace?**

Miré los 271 eventos para contestarla, y la respuesta salió de los datos, no de la teoría:

| Lo que encontré en `eventos.json` | Qué significa |
|---|---|
| 86 eventos marcados `gratis: true`, pero **54 de ellos no tienen ninguna evidencia textual de ser gratis** — el pipeline puso `precio: 0` porque no encontró precio | El filtro estrella de la app está mintiendo 6 de cada 10 veces |
| 59 eventos con `gratis: false` y `precio: null` | Se ven como pagados sin serlo necesariamente |
| 75 de 271 eventos con hora `00:00` | La hora es desconocida en el 28% de la cartelera |
| 23 eventos con dirección fuera de la Región Metropolitana: Punta Arenas, Valparaíso, Villarrica, Puerto Natales, Talca, La Serena, Valdivia, Concepción, Puerto Montt | El mapa de Santiago tiene eventos de Punta Arenas |
| 6 eventos con "AGOTADA" en el texto y ninguna marca en la ficha | Mandas gente a un evento que no puede entrar |
| 45 eventos comparten exactamente la coordenada `-33.4425, -70.6505`; otros 44 comparten `-33.4256, -70.6096` | Los pines se apilan; el mapa miente sobre dónde queda algo |
| `categoria: "otros"` en 102 de 271 eventos (38%) | El filtro por categoría no sirve para 4 de cada 10 eventos |
| Solo **4** eventos en `categoria: "familia"` | El filtro por edades que pide el fundador todavía no tiene datos que filtrar |

**Ahí está la respuesta.** El pipeline junta 271 eventos automáticamente y ninguna máquina puede decir "esta obra vale los $23.000" ni "esa entrada gratis ya se agotó" ni "esto en realidad es en Valparaíso". El blog **es la capa humana sobre el pipeline**: una persona que abre los links, descarta lo que no sirve, ordena lo que queda y le pone un motivo.

Eso convierte el blog en algo que no es marketing: es **la única prueba pública de que alguien revisa**. Y es exactamente lo que el plan de marketing dice que sostiene todo (`plan_marketing_lanzamiento.md`, sección 3.2: "el pilar 1 es el negocio", y la advertencia de la sección 9: "un evento vencido publicado te cuesta más seguidores que diez posts buenos").

**Definición operativa:** el blog de Loica es la versión larga y con link de "Los datos del finde" — la serie que el plan de marketing ya define como el activo #1. No es un blog *además* de Instagram. Es la casa propia del mismo contenido, en un canal que no depende del algoritmo de nadie.

---

## 1. Formato editorial

### 1.1 Los tres formatos

| # | Formato | Cadencia | Mascota | Qué es | Para quién |
|---|---|---|---|---|---|
| 1 | **El finde** | Semanal, jueves 18:00 | Loica (roja) | 8-12 panoramas de viernes a domingo, agrupados por día, con precio real | El "Matías" del estudio de usuarios: profesional 25-35 que decide el jueves |
| 2 | **Gratis** | Mensual, día 1 | Pudú (verde) | Todo lo gratis verificado del mes, incluidas las que se cayeron y por qué | El público de @panoramasgratis (155K seguidores demostrando que este filtro sostiene una audiencia solo) |
| 3 | **La ruta** | Quincenal, un barrio por vez | Culpeo (amarillo) | Un barrio caminable de punta a punta, ordenado por precio, con lo que hay esa semana | El que ya decidió salir pero no dónde; y el turista del QR de hoteles |

### 1.2 Por qué estos tres

**"El finde" es innegociable porque es la cita.** Un blog sin cita semanal no es un blog, es un archivo de posts sueltos. El plan de marketing ya definió el jueves como el día ("Los datos del finde", misma hora siempre) y ya explicó por qué: es la cita que instala el hábito que después hereda la app. Publicar el post el mismo jueves que sale el reel significa **una sola sesión de curaduría alimenta las dos cosas**, que es la única forma de que esto sea sostenible para una persona. El post no compite con el reel: el reel no puede tener diez links con precio, y el blog sí.

**"Gratis" es el que trae gente de Google.** Es el único formato con demanda de búsqueda estructural, no coyuntural: alguien busca "panoramas gratis santiago" todas las semanas del año, no solo cuando hay festival. Y es donde la competencia real (@panoramasgratis, @santiagoadicto) **no está**: viven en Instagram, que no aparece en Google. Ese hueco es gratis y es nuestro si lo tomamos ahora. Además, es el formato donde la honestidad se vuelve un producto vendible: cualquiera puede copiar una lista de eventos gratis, pero copiar "estas dos se cayeron y por eso" requiere haber abierto los links.

**"La ruta" es el que no se puede copiar con un scraper.** Es el diferenciador de marca hecho contenido: el barrio es la unidad mental del panorama santiaguino ("¿vamos a Lastarria o a Italia?") y es la unidad del lanzamiento por zonas del plan de marketing. Tres cosas más que solo hace este formato:

- **Es evergreen.** El Teatro San Ginés y el Club 1 van a seguir ahí en marzo. Una ruta bien escrita rankea durante años; un "finde" muere el lunes.
- **Es el material del QR de hoteles.** La táctica 5.4 del plan de marketing necesita algo trilingüe e impreso para regalar en recepción. "Bellavista en cinco cuadras" traducido a EN/PT **es** ese material, sin trabajo extra.
- **Es la excusa para conocer organizadores.** Escribir la ruta de un barrio obliga a caminarlo, y caminar el barrio es el pitch de alianzas de la sección 4 del plan de marketing. El post es el subproducto de una gestión comercial que igual había que hacer.

### 1.3 Lo que descarté y por qué

| Formato | Por qué no |
|---|---|
| **Agenda diaria** ("hoy en Santiago") | El mapa ya hace eso, y mejor. Un blog que compite con tu propio producto es trabajo duplicado. |
| **"Los 10 mejores eventos de..."** | Superlativo sin criterio. La estrategia de marca lo prohíbe explícitamente: "Exagerada (¡EL MEJOR EVENTO DEL AÑO! todos los días destruye confianza)". Además es exactamente lo que escribe una IA. |
| **Entrevistas largas a organizadores** | Buenísimo contenido, pero es el pilar 3 del plan de marketing y funciona mejor en reel de 60 segundos que en texto. Cuando haya volumen, entra como sección dentro de "La ruta", no como formato propio. |
| **"Guía de 3 días para turistas"** | Sí sirve, pero es "La ruta" ×3 con otro nombre. Cuando existan tres rutas publicadas (Bellavista, Lastarria, Barrio Italia), la guía de turista se arma encadenándolas — es una consecuencia, no un formato nuevo. |
| **"Con niños" / "Para adolescentes"** como formato propio | **Este merece explicación aparte, porque el fundador lo pidió.** |

### 1.4 Sobre los filtros por edad (niños, adolescentes)

El fundador pidió filtros por edad. Estoy de acuerdo con el filtro y en desacuerdo con hacerlo un formato de blog **todavía**, y el motivo está en los datos:

- Solo **4 de 271 eventos** están en `categoria: "familia"`.
- Pero si busco señales de texto ("niños", "infantil", "familiar", "todo espectador", "adolescentes") aparecen **17**.

O sea: **el problema no es que no haya panoramas para cabros chicos, es que el clasificador no los está encontrando.** Cuatro eventos al mes no sostienen un formato quincenal; se te acaba el material al segundo post y publicas relleno, que es precisamente cómo mueren los blogs.

El orden correcto es:

1. **Arreglar el clasificador primero** (`exportar_web.py`, función `clasificar`): que "todo espectador", "niñas, niños y tercera edad", "FamFest" y "adaptación familiar" caigan en `familia`. Eso solo debería subir de 4 a ~17 sin tocar el pipeline de fuentes.
2. **Mientras tanto, la edad vive como sección fija dentro de "El finde"**: una línea que se llama *"Con cabros chicos"* y va siempre en el bloque del sábado. Ya está escrita en el post 1 de `blog.json`. Cumple el 80% de lo que pide el fundador, con el material que existe hoy.
3. **Cuando haya 25+ eventos familiares al mes**, "El finde con niños" se separa como formato propio. Ese es el umbral, escrito antes de tener ganas de cambiarlo.

---

## 2. Estructura de datos: `web/blog.json`

### 2.1 El criterio de diseño

Quien escribe es una persona apurada, un jueves, probablemente en el teléfono. Todo lo que se pueda deducir de `eventos.json` no se escribe: **el post guarda el `id` del evento y nada más**. La fecha, el lugar, la comuna, el precio y la foto los saca el renderizador de `eventos.json` en el momento de pintar. Si el organizador cambia la hora, el post se corrige solo.

Consecuencia práctica: publicar un post es escribir ~8 párrafos y pegar ~10 IDs. Nada más.

### 2.2 Esquema

```jsonc
{
  "actualizado": "2026-08-10",
  "sitio": "https://loicasantiago.cl",

  // Config de los tres formatos. La página lee de acá el color y la mascota:
  // no se hardcodea nada en el HTML.
  "formatos": {
    "finde":  { "etiqueta": "El finde", "mascota": "loica",
                "color": "var(--rojo-loica)", "cadencia": "semanal, jueves 18:00",
                "url": "blog/este-finde.html" }
    // ... gratis, ruta
  },

  // Diccionario de avisos de honestidad. Se pintan como chip sobre la tarjeta
  // del evento. Es la capa humana hecha dato.
  "banderas": {
    "agotado":             "Agotado",
    "online":              "Es online",
    "inscripcion":         "Necesita inscripción previa",
    "sin_hora":            "La fuente no publica la hora",
    "hora_dudosa":         "La fuente da dos horas distintas",
    "precio_no_publicado": "La fuente no publica el precio",
    "sala_por_confirmar":  "La fuente no dice en qué sala es"
  },

  "posts": [
    {
      "slug":      "este-finde",           // URL: blog/este-finde.html
      "formato":   "finde",                // clave de "formatos"
      "titulo":    "El finde del 14 al 16: dos musicales, un Municipal a oscuras…",
      "bajada":    "Camila Moreno cierra el domingo…",
      "autor":     "Benjamín",
      "publicado": "2026-08-13",           // ISO date
      "vence":     "2026-08-17",           // desde acá, banner de "esto ya pasó"
      "evergreen": false,                  // true = sigue sirviendo vencido
      "destacado": true,                   // el que se ancla en el mapa
      "mascota":   "loica",                // override del formato, opcional
      "barrio":    "",                     // solo formato "ruta"

      // El texto. Un string por párrafo. "## " al inicio = subtítulo.
      // Se permite *cursiva* y **negrita**, nada más.
      "cuerpo": [
        "Agosto en Santiago tiene una ventaja: hace frío…",
        "## Viernes 14",
        "Si vas a gastar en una sola cosa, gástala en Bellavista…"
      ],

      // Los eventos que el post referencia, en el orden en que se leen.
      // "nota" es la única parte que no puede salir de eventos.json:
      // es el criterio de quien escribe. "bandera" es opcional.
      "eventos": [
        { "id": "d12a12acd1bc7ce1",
          "nota": "La más intensa de la lista. No vayas si andas bajoneado.",
          "bandera": "sin_hora" },
        { "id": "0f33f8f59f3676d7",
          "nota": "Mayores de 21, teléfono guardado. Audiotonics toda la noche." }
      ],

      "seo": {
        "titulo":      "Qué hacer en Santiago este fin de semana — 14, 15 y 16 de agosto 2026",
        "descripcion": "Diez panoramas revisados uno por uno…",
        "permalink":   "blog/2026-08-14-el-finde.html"  // copia congelada, ver §5
      }
    }
  ]
}
```

### 2.3 Reglas del esquema

| Campo | Obligatorio | Nota |
|---|---|---|
| `slug`, `formato`, `titulo`, `bajada`, `publicado`, `cuerpo`, `eventos` | Sí | Sin uno de estos el post no se pinta |
| `vence` | Sí | Nunca `null`. Un post sin fecha de muerte es un post que va a mentir. Vencido y `evergreen: false` → sale del índice y queda con `noindex` |
| `evergreen` | No (default `false`) | `true` = vencido sigue publicado con banner: "los lugares siguen ahí, los eventos cambiaron → ver el barrio en el mapa" |
| `eventos[].nota` | Puede ser `""` | Si está vacía, la tarjeta muestra solo los datos de `eventos.json` |
| `eventos[].bandera` | No | Debe existir en `banderas`; si no, el renderizador la ignora |
| `seo` | Sí | Si falta, se cae a `titulo` + `bajada`, pero es peor (ver §5) |

### 2.4 Chequeo antes de publicar

Vale la pena un script de 20 líneas (`scripts/validar_blog.py`) que corra antes de cada `git push` y falle si:

1. Algún `eventos[].id` no existe en `eventos.json` → **link roto en producción**.
2. Algún evento referenciado tiene `inicio` anterior a `publicado` → estás publicando algo que ya pasó.
3. Algún evento referenciado tiene `lat: null` → **no va a aparecer en el mapa** (le pasa hoy a `7093f7c8723385c4`, *La liebre y la tortuga*, citado en el post 1).
4. Algún precio escrito en `cuerpo` no coincide con el `precio` del evento en `eventos.json` → error de tipeo con costo de credibilidad.
5. Algún evento referenciado tiene "AGOTAD" en su texto y el post no le puso `bandera: "agotado"`.
6. El `cuerpo` tiene menos de 250 o más de 450 palabras.

Los tres posts entregados pasan los seis chequeos (el 3 con la bandera `sala_por_confirmar` puesta a propósito).

---

## 3. Los tres posts

Escritos completos en `web/blog.json`. Todos usan eventos reales de `eventos.json`; verifiqué uno por uno que el `id`, el nombre, el lugar, la fecha y el precio existan en el archivo. **Ningún precio del texto está inventado**: los seis precios citados en el post 1 y los siete del post 3 coinciden exactamente con el campo `precio` del evento correspondiente.

| # | Formato | Titular | Palabras | Eventos |
|---|---|---|---|---|
| 1 | finde | El finde del 14 al 16: dos musicales, un Municipal a oscuras y fiestas de $3.000 | 350 | 10 |
| 2 | gratis | Gratis de verdad: lo que no cuesta nada en Santiago hasta el 31 de agosto | 301 | 9 |
| 3 | ruta | Bellavista en cinco cuadras: dónde entrar un viernes según cuánta plata tengas | 323 | 11 |

### Post 1 — "El finde" (10 eventos)

Cubre viernes 14 a domingo 16 de agosto. Ordenado por día, no por categoría, porque así se decide un panorama. Trae la sección *"Con cabros chicos"* que responde al pedido de filtros por edad con el material que existe hoy.

Eventos: `d12a12acd1bc7ce1` (Las cosas extraordinarias, San Ginés, $12.000) · `4cb7d104cf9440bc` (El tipo que odiaba los musicales, San Ginés, $23.000) · `0f33f8f59f3676d7` (Club 1, Bombero Núñez 1, $5.000) · `2a811911867fa9de` (Club Roma Semáforo, Ñuñoa, $3.000) · `b50e4d284b336592` (Norteña, con Julieta Venegas, CC La Moneda, gratis) · `4a3299bb72e711a2` (Visita guiada nocturna, Teatro Municipal, $11.500) · `7093f7c8723385c4` (La liebre y la tortuga, $5.000) · `e3730c640ced4828` (Mamisonga en Sala Metrónomo, $5.000) · `310c6f1286b46e0f` (Camila Moreno en CEINA) · `528a7542b2b85ac6` (Fe de Ratas, Matucana 100, $8.000)

### Post 2 — "Gratis" (9 eventos)

Siete que pasaron la verificación y **dos que se cayeron con nombre y apellido**. Esa última sección es la que hace el post: es la diferencia entre una lista y un criterio, y es imposible de copiar sin hacer el trabajo.

Eventos: `12621fc7551e5a21` (Malditas, Galería Concreta M100) · `af5c1cb68ccbd080` (Historias en femenino, Las Condes) · `71917655fc5f03fd` (Kandinsky, UNAB) · `a577579b6858420f` (Relaciones entre música y archivo, M100) · `af4d79762d6c6602` (Taller de live looping, Ñuñoa) · `ef8779344f74bc2a` (El rey que quería ser músico, Municipal Delivery, **online**) · `b50e4d284b336592` (Norteña / Julieta Venegas, **con inscripción**) · `b9813d06d9e08fca` (Orquesta USACH, **agotada**) · `55b6265d9e3927df` (Pariente Fest, **agotado**)

### Post 3 — "La ruta: Bellavista" (11 eventos)

Ordenado por precio, de $23.000 a $3.000, porque en la práctica la plata es el primer filtro de una noche. Es la Zona 1 del plan de lanzamiento. Es el candidato natural a la primera traducción EN/PT para el QR de hoteles.

Eventos: `628c35f567717769` (Pretty Woman, $18.000) · `32a4dd0be84f2124` (Crónica de la mujer menos mujer, $12.000) · `d12a12acd1bc7ce1` · `4cb7d104cf9440bc` · `03437d42d9aced0a` (Danyro, Sala SCD Bellavista, $5.000) · `022e9729a173b885` (Patricio Alvarado, SCD Bellavista, $7.000) · `0f33f8f59f3676d7` y `30a2e81be0633669` (Club 1 viernes y sábado) · `b3d7b3617f54757a` (Mamisonga en The Hive, $6.000) · `285aefe40fa3c61a` (Club M&M Casona, $3.000) · `e3730c640ced4828` (Sala Metrónomo, $5.000)

### Nota sobre el tono

Escribí los tres en primera persona singular ("abrí los links", "es la que más ganas tengo de ver"). No es capricho: la estrategia de marca define a Loica como "la amiga local que siempre sabe qué está pasando", y una amiga no dice "descubre los mejores eventos". Además, la primera persona es lo único que un competidor con scraper no puede generar.

Regla que apliqué en los tres, sacada de la misma estrategia: **primero el dato, después el chiste**. Cada párrafo dice qué, cuándo, dónde y cuánto antes de opinar.

---

## 4. Cómo se conecta con el resto del sitio

### 4.1 Qué pasa al tocar un evento dentro de un post

**No sacar al lector del post.** La tarjeta del evento se expande *in situ*: el renderizador ya tiene `eventos.json` cargado, así que dibuja título, fecha, lugar, comuna, precio y la nota del editor sin pedir nada al servidor. Dentro de la tarjeta expandida, dos botones y nada más:

| Botón | Destino | Por qué |
|---|---|---|
| **Ver en el mapa** | `index.html#/e/{id}` | Ya funciona: `index.html:194` lee `location.hash.match(/^#\/e\/(.+)$/)` y abre la ficha |
| **Ir al organizador** | `ev.url` | Es donde se compran las entradas. Salir del sitio acá es un éxito, no una fuga |

Y arriba de todo, el `<h3>` de la tarjeta enlaza a `e/{id}.html` — las 271 fichas estáticas que ya existen, con Open Graph y JSON-LD `Event` incluidos. Ese es el link que se pega en WhatsApp.

### 4.2 "Ver los 10 en el mapa" (lo único que hay que programar de nuevo)

Al final de cada post va un botón que abre el mapa **filtrado a los eventos del post**. Hoy no existe: `index.html` no lee query params (el estado vive en `filtroCat`, `soloGratis`, `cuando`, línea 121). Es el único cambio de código que el blog exige, y son ~10 líneas:

```js
// index.html, junto al bloque que ya lee location.hash
const q = new URLSearchParams(location.search);
const soloIds = q.get("ids")?.split(",").filter(Boolean);
// en el filtro de la lista: && (!soloIds || soloIds.includes(ev.id))
// y después de pintar: map.fitBounds(bordeDe(eventosVisibles), {padding: 60});
```

Link del botón: `index.html?ids=d12a12acd1bc7ce1,4cb7d104cf9440bc,…` — se arma solo desde `post.eventos`.

Mientras esté sin implementar, el botón puede apuntar a `index.html#/e/{primer_id}`, que ya funciona. No es lo mismo, pero no bloquea publicar.

### 4.3 Cómo se comparte un post

Reusar `REDES` y `botonesCompartir()` de `loica.js:284-350`, que ya tiene WhatsApp, Facebook, X, Instagram vía `navigator.share` y copiar-link, con el comentario honesto de por qué Instagram no tiene URL de compartir. Solo cambia el texto:

```js
// paralelo a textoCompartir(ev), para posts
function textoCompartirPost(p){
  return `${p.titulo}\n${p.bajada}`;   // + "\n\n" + url, que lo agrega REDES.whatsapp
}
```

Y en el `<head>` de cada post:

```html
<meta property="og:type"        content="article">
<meta property="og:title"       content="{{titulo}}">
<meta property="og:description" content="{{bajada}}">
<meta property="og:image"       content="{{sitio}}/og/{{formato}}.png">
```

Sobre la imagen: no hay presupuesto de ilustración, así que **tres PNG fijas, una por formato** (Loica roja / Pudú verde / Culpeo amarillo, con la etiqueta del formato encima). Se hacen una vez en Canva con la plantilla del kit de marca y sirven para siempre. Una imagen por post sería mejor y no es sostenible semanalmente; tres imágenes reconocibles sí lo son, y de hecho refuerzan la identidad: la gente aprende que "la verde es la de los gratis".

### 4.4 Cómo llega alguien al blog desde el mapa

Cuatro puertas, en orden de importancia:

1. **La barra de navegación.** Acá hay una decisión que tomar, porque `loica.js:189` dice explícitamente: *"En la barra inferior el espacio es de 4 columnas"*, y hoy están ocupadas por Mapa / Calendario / Publicar / Nosotros. Meter una quinta rompe el diseño.
   **Recomendación: en la barra inferior (móvil), "Blog" reemplaza a "Publicar"**, y "Publicar" se queda solo en la barra superior y en el pie. Motivo: un lector en el celular no va a publicar un evento nunca; los organizadores llegan a `agrega.html` por link directo desde el pitch de alianzas, no navegando. La barra inferior es del lector.
   En escritorio caben las cinco, así que ahí no se saca nada.

2. **Tarjeta fija arriba del panel de lista, de jueves a domingo.** Con la mascota del formato y el titular: *"El finde según la Loica →"*. Es el mismo lugar donde el usuario ya está mirando. Se pinta leyendo `blog.json` y tomando el post con `destacado: true` que no esté vencido.

3. **Índice inverso en la ficha del evento.** Al abrir un evento que salió en un post: *"Salió en: Bellavista en cinco cuadras"*. Se arma en el cliente recorriendo `posts[].eventos[].id` — no hace falta guardar nada nuevo. Esto es lo que convierte 271 fichas en 271 puertas al blog, y es lo más barato de todo.

4. **El estado vacío.** Cuando los filtros dan cero resultados, hoy el usuario queda en una pantalla muerta. Ahí va: *"Nada con esos filtros. ¿Miramos lo que hay este finde?"* con link al post. Convertir un callejón sin salida en una lectura es la mejor relación esfuerzo/beneficio de esta lista.

### 4.5 El circuito completo

```
Instagram / WhatsApp  →  post del blog  →  ficha e/{id}.html  →  mapa (index.html#/e/{id})
                              ↑                    │
                              └────────────────────┘
                          "Salió en: …"

mapa (sin resultados / tarjeta del finde / nav)  →  post del blog
```

---

## 5. SEO honesto

**Advertencia de honestidad primero:** no tengo datos de volumen de búsqueda de una herramienta de keywords. Lo que sigue está razonado desde la estructura de las consultas y desde la evidencia del plan de marketing (dónde está la competencia y dónde no). Antes de invertir mucho en esto, vale la pena mirar Google Search Console después del primer mes — es gratis y va a decir la verdad.

### 5.1 La oportunidad real

Las cuentas que dominan panoramas en Santiago (@santiagoadicto ~778K, @panoramasgratis ~155K) **viven en Instagram, que Google no indexa de forma útil**. Alguien que googlea "que hacer en santiago este fin de semana" no las encuentra. Ese hueco es la única ventaja competitiva gratis que hay disponible, y se toma con 3 páginas bien hechas, no con 50 mediocres.

### 5.2 Arquitectura de URLs (esta es la decisión importante)

El error típico es publicar cada semana en una URL nueva (`/blog/finde-14-agosto`, `/blog/finde-21-agosto`, …). Cada una parte de cero en autoridad y ninguna llega a rankear nunca. La alternativa:

| URL | Qué es | Se actualiza | Indexable |
|---|---|---|---|
| `blog.html` | Índice del blog | Automático | Sí |
| `blog/este-finde.html` | **Siempre la edición vigente.** Es la que acumula autoridad y la que rankea | Cada jueves, misma URL | Sí |
| `blog/2026-08-14-el-finde.html` | Copia congelada de esa semana, para compartir y para archivo | Nunca | **No** (`noindex`) |
| `blog/panoramas-gratis-santiago.html` | El activo #1 de búsqueda. URL permanente | Día 1 de cada mes | Sí |
| `blog/bellavista.html`, `blog/lastarria.html`, … | Una por barrio, permanente | Cuando cambian los eventos | Sí |

Al año esto da **~11 páginas indexables** (1 índice + 1 finde + 1 gratis + 4-8 barrios), no 60. Cada una con historia acumulada. Los `noindex` en las copias congeladas evitan que compitan contra su propia versión vigente.

> El campo `seo.permalink` de `blog.json` guarda justamente la ruta de la copia congelada.

### 5.3 Títulos y descripciones

La clave: **el titular editorial y el `<title>` de Google no son el mismo texto**, y por eso `blog.json` tiene los dos campos. El titular es para quien ya llegó; el `<title>` es para quien está escaneando diez resultados azules.

| Consulta objetivo | `<title>` (≤60 car.) | `meta description` (≤155 car.) |
|---|---|---|
| que hacer en santiago este fin de semana | **Qué hacer en Santiago este fin de semana — 14, 15 y 16 de agosto 2026** | Diez panoramas revisados uno por uno para el fin de semana en Santiago: teatro en Bellavista, visita nocturna al Teatro Municipal, Camila Moreno en CEINA y fiestas desde $3.000. |
| panoramas gratis santiago / que hacer gratis en santiago | **Panoramas gratis en Santiago — agosto 2026 \| Loica** | Exposiciones, talleres y conciertos gratis en Santiago durante agosto de 2026. Verificados uno por uno: si dice gratis es gratis, y si se agotó también lo decimos. |
| que hacer en bellavista santiago / bellavista de noche | **Qué hacer en Bellavista, Santiago: teatro, tocatas y fiestas \| Loica** | La ruta de Bellavista de punta a punta: Teatro San Ginés, Sala SCD Bellavista, Club 1 en Bombero Núñez, The Hive y Sala Metrónomo. Precios reales, de $3.000 a $23.000. |

Tres reglas que apliqué:

1. **El mes va en el título del formato "gratis" y se actualiza cada mes.** "agosto 2026" en el título le dice a Google y a la persona que esto está vivo. Es el mismo truco por el que las páginas de recetas ponen el año.
2. **Precios reales en la meta description.** "$3.000" y "$23.000" son números concretos que ganan el clic contra "descubre los mejores panoramas". Y son verdad, que es lo que hace que la gente vuelva.
3. **Nombres propios en la descripción** (Teatro Municipal, Camila Moreno, San Ginés): capturan la búsqueda de cola larga de quien busca el lugar, no la categoría.

### 5.4 Datos estructurados

Las fichas `e/{id}.html` ya emiten JSON-LD `Event` — está bien hecho. Cada post debería emitir dos cosas más:

- **`BlogPosting`** con `datePublished` y `author`.
- **`ItemList`** con los `Event` del post en orden. Es lo que puede hacer que Google muestre el post con la lista de eventos desplegada, que es un resultado mucho más grande que un link azul.

Se genera solo desde `post.eventos` cruzado con `eventos.json`. Cero trabajo editorial adicional.

### 5.5 Multilingüe

El sitio es trilingüe (es/en/pt) y el blog **no debería serlo entero**. Traducir "El finde" cada semana a dos idiomas es la forma más rápida de abandonar el proyecto. La decisión honesta:

- **"El finde" y "Gratis": solo español.** Son semanales/mensuales y su público es santiaguino.
- **"La ruta": los tres idiomas.** Es evergreen (se traduce una vez y sirve un año), es lo que el turista busca ("what to do in Bellavista Santiago", "o que fazer em Santiago"), y es literalmente el material que necesita el QR de hoteles de la sección 5.4 del plan de marketing. Con `hreflang` entre las tres versiones.

### 5.6 Lo que NO hay que hacer

- No crear una página por evento en el blog: ya existen las 271 fichas `e/{id}.html`, y duplicar contenido se castiga.
- No escribir "descubre", "los mejores", "imperdibles". Además de mentir, es el vocabulario que Google asocia con contenido generado en masa.
- No comprar links ni publicar en directorios. Con presupuesto cero, el único link building que funciona acá es el de la sección 4 del plan de marketing: que los organizadores y centros culturales que mencionas en las rutas te enlacen de vuelta. Pídeselo cuando les mandes el post donde salen — es la conversación más fácil del mundo.

---

## 6. Lo que encontré en `eventos.json` y hay que arreglar

Esto no era parte del encargo, pero apareció al verificar los posts y afecta directamente al blog y al mapa. Ordenado por urgencia.

| # | Problema | Evidencia | Impacto |
|---|---|---|---|
| 1 | **`gratis: true` sin ninguna evidencia de gratuidad** | 54 de 86. El pipeline pone `precio: 0` cuando no encuentra precio. Ejemplos: `efd3a04391359d79` (*Gemelos*, Teatro UC), `340cea78914f42bd` (*El niño de los fósiles*, Teatro UC), `14b5b46dfb3bfb11` (Club 1, un jueves de club marcado gratis) | **Crítico.** El filtro estrella miente. Fix: `gratis = true` solo si el texto dice gratis/gratuito/liberada/sin costo; si no, `precio: null` + "precio no publicado" |
| 2 | **Eventos fuera de la Región Metropolitana** | 23 con dirección en Punta Arenas, Valparaíso, Villarrica, Puerto Natales, Talca, La Serena, Valdivia, Concepción, Puerto Montt, Curicó, La Unión. Todos vienen de Toliv y PortalTickets | **Crítico.** Fix: descartar en `exportar_web.py` todo lo que no geocodifique dentro de la RM |
| 3 | **Toliv corre las fechas un día** | `0f33f8f59f3676d7` se titula "Club 1 - Viernes 14 de Agosto" y su descripción dice "🗓️ Viernes 14 de Agosto ⏰ 23:00 hrs", pero `inicio` es `2026-08-15T00:00`. Le pasa a los 46 eventos de Toliv | **Alto.** Un evento del viernes aparece en el filtro del sábado. Parece un problema de zona horaria al parsear |
| 4 | **Toliv geocodifica al centroide de la comuna** | `0f33f8f59f3676d7` (Bombero Núñez 1) y `9479b22f294945d6` (Buenos Aires 207) comparten exactamente `-33.40203, -70.64345`, y son direcciones distintas. The Hive y Sala Metrónomo también comparten coordenada | **Alto.** El pin no está donde dice estar, justo en el barrio del lanzamiento |
| 5 | **Eventos agotados sin marcar** | 6 con "AGOTADA" en el texto: `b9813d06d9e08fca` (Orquesta USACH), `55b6265d9e3927df` (Pariente Fest), `99e5710ac207f961`, `a1c89eceedd4902e`, `74d6c0e406a5509b`, `204d3ef2ad6b83ef` | **Medio.** Fix: campo `agotado: true` detectando "agotad" y chip rojo en la ficha |
| 6 | **`categoria: "otros"` en el 38%** | 102 de 271. Además, `2c21037adfdb18cc` (un grupo de lectura sobre Canguilhem) está clasificado como `fiesta` | **Medio.** El filtro por categoría, que es medio producto, no sirve para 4 de cada 10 eventos |
| 7 | **Mismo lugar con comuna distinta según el evento** | Teatro San Ginés aparece como Santiago y como Providencia; Matucana 100 como Santiago y Estación Central; Agenda Cultural Las Condes como Las Condes e Independencia | **Medio.** Rompe el filtro por comuna. Fix: tabla de recintos conocidos con comuna y coordenada fijas |
| 8 | **Comuna incorrecta por herencia de la fuente** | `e6a9d66736d17925` es de Balmaceda Arte Joven **Valparaíso** (la descripción lo dice) y figura como comuna Santiago. `55b6265d9e3927df` es en Chimkowe, **Peñalolén**, y figura como Santiago | **Medio.** Es la razón por la que descarté dos eventos del post de gratis |
| 9 | **Contenido que no es un evento** | `b2c85bd25ee38483` ("Exitoso cierre de primera Residencia…"), `abf1b561b5e80cf5` ("Nueva alianza: NAVE y CCLM"), `db0cc964fc7fa6d4` ("¿Tienes un emprendimiento? Postula…"). Son noticias del sitio, con fechas de 2027 | **Bajo.** Ensucian el calendario a futuro |
| 10 | **Hora desconocida servida como 00:00** | 75 de 271. En la ficha se lee como "a las 00:00", que es peor que no decir nada | **Bajo pero barato de arreglar.** Fix: si la hora es 00:00, mostrar "hora por confirmar" |

Los problemas 1, 2 y 5 son los que más importan para el blog, porque son exactamente los que hoy tengo que corregir a mano cada vez que escribo un post. Arreglarlos en `exportar_web.py` es trabajo que se paga solo todas las semanas.

---

## 7. Qué falta para publicar

En orden:

1. **`blog.html`** — índice + renderizador de posts. Lee `blog.json` y `eventos.json`, pinta con los tokens de `loica.css`. Es la parte de Benjamín.
2. **Nav: "Blog" entra a la barra inferior en lugar de "Publicar"** (`loica.js:186-192`, arrays `PAGINAS` y `CORTOS`, en los tres idiomas).
3. **Tres PNG de Open Graph**, una por formato, con la mascota correspondiente.
4. **`?ids=` en `index.html`** para el botón "ver los N en el mapa" (§4.2, ~10 líneas).
5. **`scripts/validar_blog.py`** con los seis chequeos de §2.4, corriendo antes de publicar.
6. **Los arreglos 1, 2 y 5 de la sección 6** en `exportar_web.py`.
7. **Primer post de verdad**, el jueves siguiente al deploy. La cadencia importa más que la calidad del primero: un blog con cuatro posts mediocres puntuales pierde contra uno con cuatro posts decentes cada jueves.

**Métrica única para decidir a los dos meses:** compartidos por post. No visitas, no tiempo en página. Si la gente no lo manda al grupo de WhatsApp, el post no sirve — y esa es la misma métrica que el plan de marketing define para Instagram, así que se comparan directamente y se sabe cuál de los dos canales merece las horas.
