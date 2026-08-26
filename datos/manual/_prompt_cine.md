# Prompt de cartelera de cine — extracción con el navegador

Se usa cuando hay tiempo —idealmente un jueves, que es cuando las cadenas
cambian la programación y cargan la semana— y devuelve **un CSV por cadena**,
que se guardan en `datos/manual/` y se suben con git: la corrida en la nube
arranca sola al ver el archivo nuevo y lo publica en la página de cine.

```bash
git add datos/manual/cartelera_*.csv
git commit -m "Cartelera de cine al $(date +%F)"
git push
```

## Un archivo por cadena, y por qué importa

`loica/cartelera/asistida.py` lee **todos** los `datos/manual/cartelera*.csv`,
así que conviven sin pisarse:

| Archivo | Qué trae |
|---|---|
| `cartelera_cineplanet.csv` | Las 5 salas de Cineplanet |
| `cartelera_cinepolis.csv` | Las 20 de Cinépolis |
| `cartelera_independientes.csv` | Cine Mayo, Cine UC, MUVIX, ZooCine |

Cada archivo se **reemplaza entero** cuando se vuelve a extraer esa cadena.
Estaban todas en un solo `cartelera_cines.csv` y eso era una trampa: como el
archivo se reemplaza, una pasada que trajera solo Cinépolis **borraba las 424
funciones de Cineplanet** sin que nadie lo notara hasta ver la página. Con un
archivo por cadena, extraer una no toca a las otras.

Lo que no se refresca se apaga solo: las funciones pasadas se descartan al
publicar, así que un archivo viejo se vacía en unos días en vez de mentir.

## Por qué estas salas y no todas

De las 44 salas del catastro (`config/cines.yaml`), el pipeline lee sola la
cartelera de quince:

| Cómo se lee | Salas | Detalle |
|---|---|---|
| BFF público | 9 | Cinemark sirve su cartelera —la semana entera, con sinopsis y tráiler— en `bff.cinemark.cl`, abierto sin credencial. Pide la cabecera `country: CL`. |
| Página semanal | 2 | El Normandie y El Biógrafo publican la semana en su sitio. Del Normandie se lee además su archivo de películas por la API de su WordPress: sinopsis, tráiler, afiche, duración, calificación y quién la dirigió. |
| Agenda cultural | 4 | La Cineteca Nacional, Matucana 100 y el Centro Arte Alameda ya llegan por las fuentes de siempre. |
| **Navegador** | **29** | **Esto.** |

Las dos cadenas grandes que faltan cierran su cartelera a propósito:

- **Cineplanet** entrega los horarios solo a quien trae la cookie de sesión
  que su propio sitio planta en el navegador (200 con cookie, 403 sin ella).
  Con el navegador abierto en cineplanet.cl, sus tres caches
  —`/v3/api/cache/moviescache`, `/sessioncache`, `/cinemascache`— traen la
  semana completa, con sinopsis, tráiler y géneros.
- **Cinépolis** (ex Cinehoyts) responde `401 Unauthorized access` en su API:
  pide un token. Verificado de nuevo el 25-08-2026, y de paso: `cinepolis.com/cl`
  devuelve 3,7 KB de cáscara vacía y **el sitio que sirve es
  `www.cinepolischile.cl`**, que igual arma la cartelera en el navegador —o
  sea que tampoco se puede leer desde un programa, pero es donde hay que mirar.

Ninguna de las dos se fuerza. Cuando alguna publique un feed o dé permiso,
sale de acá igual que van a salir Ticketplus y Ticketmaster del prompt de
Passline.

---

## El prompt (copiar desde acá)

Necesito la cartelera de cine de Santiago de Chile y me la devuelves como CSV.
Trabajo en Loica, un índice de panoramas de la Región Metropolitana: cada
función se publica con el link donde se compra la entrada, así que el link es
obligatorio y el dato tiene que ser textual, nunca inventado.

### Reglas duras (no se rompen)

1. **Nada inventado.** Si la página no dice el dato, la celda va **vacía**.
   Nunca "N/A", nunca guiones. Una función sin hora no se incluye.
2. **Hasta 7 días desde hoy.** Trae todos los días que el cine tenga
   publicados hasta ese tope; del octavo en adelante no sirve, porque la
   página publica una semana y el resto se descarta al entrar. Si pasas un
   jueves vas a traer mucho más: es el día en que las cadenas cambian la
   programación.
3. **Una fila por función.** Si Spider-Man se da a las 18:30, 20:20 y 22:10
   en la misma sala, son tres filas. No agrupes horarios en una celda.
4. **El nombre de la sala, exactamente como está en la tabla de abajo.**
   Es lo que permite pegar cada función con su pin en el mapa. Si el sitio la
   llama distinto, usa igual el nombre de la tabla y anótalo en el resumen.
5. **Solo Región Metropolitana.** La tabla de abajo ya está filtrada; si el
   sitio ofrece otras regiones, sáltalas.
6. **No rodees bloqueos.** Si una página pide login, muestra captcha o
   "verificando su conexión", anótala como bloqueada en el resumen y sigue.
   No busques rodeos, no toques APIs que el sitio no ofrece públicamente.
7. **El afiche importa.** Copia la URL de la imagen del póster tal como está
   en la página (clic derecho → copiar dirección de imagen, o el `src` de la
   etiqueta). Es lo que la página muestra al lado del título. Si no hay
   póster, deja la celda vacía.

### Convenciones de datos

- `fecha`: `2026-08-27`. `hora`: `19:40` (24 horas).
- `formato`: lo que declare el sitio — `2D`, `3D`, `XD`, `4DX`, `IMAX`,
  `PREMIER`, `MACRO XE`. Vacío si no lo dice.
- `idioma`: **`doblada`** o **`subtitulada`**, en minúscula, traduciendo lo
  que diga el sitio ("DOB", "Español", "Castellano" → doblada; "SUB",
  "Subtitulada", "VOSE" → subtitulada). Vacío si no lo declara. Es el filtro
  más usado de la página.
  **Ojo con el título:** varias salas avisan el idioma ahí y en ninguna otra
  parte —"Mi vecino Totoro (doblada al español)"—, y casi siempre son las de
  niños. Si el título lo dice, la columna se llena.
- `duracion_min`: solo el número (`152`). Vacío si no aparece.
- `clasificacion`: como la escriba el sitio — `TE`, `TE+7`, `TE+14`, `MA14`,
  `+18`, `14 años`.
- `poster`: URL completa de la imagen, empezando en `https://`.
- `link_compra`: la URL a la que lleva apretar ese horario. Si el sitio no
  da una URL por función, usa la de la película en esa sala; y si tampoco,
  la de la cartelera de esa sala. **Sin link no incluyas la fila.**

### Formato de salida

Un CSV por cadena, UTF-8, separador coma, con este encabezado exacto y en
este orden:

```
cine,pelicula,fecha,hora,formato,idioma,duracion_min,clasificacion,poster,link_compra,sinopsis,trailer,generos,credito
```

Las cuatro últimas son de la PELÍCULA y se repiten en cada una de sus
funciones, está bien:

- **`sinopsis`**: el resumen que publica el cine, un párrafo, sin inventar.
- **`trailer`**: la URL de YouTube o Vimeo. Solo esos dos dominios; cualquier
  otro se descarta al entrar.
- **`generos`**: separados por coma (`Acción, Aventura`).
- **`credito`**: quién la dirigió, de dónde y de qué año, en una línea:
  `Jean-Luc Godard · Francia · 1963`. Las cadenas publican género y las salas
  de repertorio publican autor — son dos maneras de contestar "¿esto es para
  mí?" y cada cine contesta con la que tiene. Si el sitio no lo dice, vacío.

Sirven para la vista **"Qué ver"** de la página, donde la Cabra presenta la
cartelera con carátula, descripción y tráiler, sin horarios encima.

Ordena por `cine`, después por `fecha` y después por `hora`. Deduplica por
(cine + pelicula + fecha + hora). Entrega cada archivo `.csv` adjunto **y** el
contenido en un bloque de código.

Ejemplo de dos filas bien hechas:

```
cine,pelicula,fecha,hora,formato,idioma,duracion_min,clasificacion,poster,link_compra,sinopsis,trailer,generos,credito
Cinépolis Mallplaza Egaña,La Odisea,2026-08-27,19:40,2D,subtitulada,172,MA14,https://…/odisea.jpg,https://www.cinepolischile.cl/compra/12345,"Epopeya mitológica que sigue el viaje de Odiseo a casa tras la guerra de Troya.",https://youtu.be/IrdgjWno1VE,"Acción, Aventura",Christopher Nolan · Reino Unido · 2026
Cine UC,El desprecio,2026-08-28,19:00,,subtitulada,123,14 años,,https://extension.uc.cl/cine/el-desprecio,"Un dramaturgo acepta reescribir escenas para una película en Capri.",,,"Jean-Luc Godard · Francia · 1963"
```

Mira las diferencias: la de la cadena trae formato, afiche y género; la de la
sala de repertorio no trae ninguno de los tres y sí trae el crédito. Las dos
están bien — lo que no está bien es rellenar una celda que la página no dijo.

### Además del CSV, quiero un resumen corto

1. **Funciones por sala.**
2. **Salas que no dieron nada**, y por qué (sin cartelera cargada, bloqueada,
   la página no abrió).
3. **Nombres que el sitio escribe distinto** a la tabla de abajo, con los dos
   nombres. Las salas marcadas "confirma el nombre" salieron del cruce de sus
   coordenadas con el mall que las contiene, no del sitio de la cadena: si
   ves cómo se llaman de verdad, dímelo y corrijo el catastro.
4. **Salas que ya no existen** o que aparecen y no están en la tabla.
5. **¿Se puede automatizar alguna?** Si mientras miras ves que el sitio deja
   una puerta abierta —una URL que devuelve JSON al cambiar de día, datos
   `schema.org/ScreeningEvent` en el HTML, un feed— dímelo. Esa cadena sale de
   este prompt para siempre, como salió Cinemark.

### Las salas

#### Cineplanet — 5 salas → `cartelera_cineplanet.csv`

Dónde mirar: https://www.cineplanet.cl/

| Escribe la sala así en el CSV | Comuna | Dirección |
|---|---|---|
| Cineplanet Alameda | Estación Central | Av. Libertador Bernardo O'Higgins |
| Cineplanet Costanera Center | Providencia | Av. Andrés Bello 2461 |
| Cineplanet Florida Center | La Florida | Av. Vicuña Mackenna Oriente 6100 |
| Cineplanet Mall Barrio Independencia | Independencia | Av. Independencia 565 |
| Cineplanet Quilín | Peñalolén | Av. Américo Vespucio 3300 |

Son cinco y no seis: la sala de Av. La Dehesa 1445 que figuraba acá como
"Cineplanet Lo Barnechea" es en realidad el **Cinemark Portal La Dehesa**, que
ya entra solo. Era una etiqueta vieja de OpenStreetMap.

#### Cinépolis — 20 salas → `cartelera_cinepolis.csv`

Dónde mirar: **https://www.cinepolischile.cl/** (elige ciudad y cine en los
dos selectores de arriba). `cinepolis.com/cl` no sirve: devuelve una página
vacía que se arma después.

| Escribe la sala así en el CSV | Comuna | Dirección |
|---|---|---|
| Cinépolis Arauco Maipú | Maipú | Av. Américo Vespucio 399 |
| Cinépolis Arauco Quilicura | Quilicura | Av. Bernardo O'Higgins 581 |
| Cinépolis Casacostanera | Vitacura | Av. Nueva Costanera 3900 |
| Cinépolis La Reina ⟵ **confirma el nombre** | La Reina | Av. Ossa 655 |
| Cinépolis Maipú ⟵ **confirma el nombre** | Maipú | Av. Lo Espejo |
| Cinépolis Mallplaza Egaña | La Reina | Av. Larraín 5862 |
| Cinépolis Mallplaza Sur | San Bernardo | Av. Presidente Jorge Alessandri 20040 |
| Cinépolis Melipilla | Melipilla | Vicuña Mackenna 01372 |
| Cinépolis Melipilla (Serrano 395) ⟵ **confirma el nombre** | Melipilla | Serrano 395 |
| Cinépolis Parque Arauco | Las Condes | Av. Presidente Kennedy 5413 |
| Cinépolis Paseo Los Dominicos | Las Condes | Camino El Alba 11969 |
| Cinépolis Paseo Los Trapenses | Lo Barnechea | Av. Los Trapenses 3515 |
| Cinépolis Paseo San Bernardo | San Bernardo | Eyzaguirre |
| Cinépolis Plaza Los Dominicos | Las Condes | Av. Padre Hurtado Sur 875 |
| Cinépolis Portal Exposición | Estación Central | — |
| Cinépolis Puente Alto ⟵ **confirma el nombre** | Puente Alto | — |
| Cinépolis Puente Alto (Independencia) ⟵ **confirma el nombre** | Puente Alto | Independencia |
| Cinépolis Terrazas Maipú | Maipú | — |
| Cinépolis Vivo Imperio | Santiago | Huérfanos |
| Cinépolis Vivo Outlet La Florida | La Florida | Rojas Magallanes 1856 |

**Las cuatro que se parecen entre sí.** Hay dos en Melipilla y dos en Puente
Alto, y sus nombres se distinguen solo por el paréntesis. Si no estás seguro
de a cuál corresponde una función, **anótalo en el resumen y déjala fuera**:
una función en la sala de al lado es peor que una función que falta. Lo mismo
con las tres de Maipú, que sí tienen nombres distintos (Arauco, Terrazas y
Maipú a secas) pero se confunden fácil.

#### Salas independientes — 4 → `cartelera_independientes.csv`

| Escribe la sala así en el CSV | Comuna | Dónde mirar |
|---|---|---|
| Cine Mayo | Santiago | Sala única; busca su cartelera o su Instagram |
| Cine UC | Santiago | https://extension.uc.cl (Centro de Extensión UC) |
| MUVIX Cinema | San Joaquín | https://muvix.cl/ |
| ZooCine | Santiago | Sala del Parque Metropolitano |

Estas cuatro son las que más ganan con `sinopsis` y `credito`: son de
repertorio y hoy salen en la página sin una línea que leer.

### Lo que NO hay que mirar

Ya entra solo, todos los días, con horarios y con ficha:

**Cinemark** (sus 9 salas, la semana entera con sinopsis y tráiler) ·
**Cine Arte Normandie** (con sinopsis, tráiler, afiche y director) ·
**El Biógrafo** · **Cineteca Nacional** · **Matucana 100** ·
**Centro Arte Alameda**

---

## Qué pasa después

`loica/cartelera/asistida.py` lee los CSV, pega cada fila con su sala del
catastro por nombre o por alias, descarta lo que no calza (y dice cuántas y
por qué), y `run_cine.py` lo junta con lo que sí se pudo leer solo. Una fila
con un link que no sea `http(s)` no se publica: es la misma regla que corre
para todo dato de fuente que termina en un `href`.

Para probar antes de publicar:

```bash
python3 run_cine.py --via asistida --probar -v
```
