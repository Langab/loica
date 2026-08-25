# Prompt de cartelera de cine — extracción con el navegador

Se usa **una vez al día**, idealmente en la mañana, y devuelve un CSV que se
guarda como `datos/manual/cartelera_cines.csv` (se **reemplaza**, no se
acumula) y se sube con git: la corrida en la nube arranca sola al ver el
archivo nuevo y lo publica en la página de cine.

```bash
git add datos/manual/cartelera_cines.csv
git commit -m "Cartelera de cine al $(date +%F)"
git push
```

## Por qué estas salas y no todas

De las 44 salas del catastro (`config/cines.yaml`), el pipeline lee sola la
cartelera de doce:

| Cómo se lee | Salas | Detalle |
|---|---|---|
| BFF público | 9 | Cinemark sirve su cartelera —la semana entera, con sinopsis y tráiler— en `bff.cinemark.cl`, abierto sin credencial. Entra solo a la corrida. |
| Página semanal | 2 | El Normandie y El Biógrafo publican la semana en su sitio y se leen con un parser propio. |
| Agenda cultural | 4 | La Cineteca Nacional, Matucana 100 y el Centro Arte Alameda ya llegan por las fuentes de siempre. |
| **Navegador** | **30** | **Esto.** |

Las dos cadenas grandes que faltan cierran su cartelera a propósito:

- **Cineplanet** entrega los horarios solo a quien trae la cookie de sesión
  que su propio sitio planta en el navegador (200 con cookie, 403 sin ella).
  Con el navegador abierto en cineplanet.cl, sus tres caches
  —`/v3/api/cache/moviescache`, `/sessioncache`, `/cinemascache`— traen la
  semana completa, con sinopsis, tráiler y géneros. Las 5 salas RM son
  Alameda, Costanera Center, Florida Center, Mall Barrio Independencia y
  Quilín.
- **Cinépolis** (ex Cinehoyts) responde `401 Unauthorized access` en su API:
  pide un token.

Ninguna de las dos se fuerza. Cuando alguna publique un feed o dé permiso,
sale de acá igual que van a salir Ticketplus y Ticketmaster del prompt de
Passline.

---

## El prompt (copiar desde acá)

Necesito la cartelera de cine de Santiago de Chile para **hoy y los próximos
tres días**, y me la devuelves como un CSV. Trabajo en Loica, un índice de
panoramas de la Región Metropolitana: cada función se publica con el link
donde se compra la entrada, así que el link es obligatorio y el dato tiene
que ser textual, nunca inventado.

### Reglas duras (no se rompen)

1. **Nada inventado.** Si la página no dice el dato, la celda va **vacía**.
   Nunca "N/A", nunca guiones. Una función sin hora no se incluye.
2. **Solo hoy y los próximos tres días.** Cuatro días en total. Si el sitio
   ofrece más, no los tomes: las salas todavía no los tienen cargados y
   cambian.
3. **Una fila por función.** Si Spider-Man se da a las 18:30, 20:20 y 22:10
   en la misma sala, son tres filas. No agrupes horarios en una celda.
4. **El nombre de la sala, exactamente como está en la tabla de abajo.**
   Es lo que permite pegar cada función con su pin en el mapa. Si el sitio la
   llama distinto, usa igual el nombre de la tabla y anótalo en el resumen.
5. **Solo Región Metropolitana.** La tabla de abajo ya está filtrada; si el
   sitio ofrece otras regiones, sáltalas.
6. **No rodees bloqueos.** Si una página pide login, muestra captcha o
   "verificando su conexión", anótala como bloqueada en el resumen y sigue.
   No busques rodeos.
7. **El afiche importa.** Copia la URL de la imagen del póster de la película
   tal como está en la página (clic derecho → copiar dirección de imagen, o
   el `src` de la etiqueta). Es lo que la página muestra al lado del título.
   Si no hay póster, deja la celda vacía.

### Convenciones de datos

- `fecha`: `2026-08-25`. `hora`: `19:40` (24 horas).
- `formato`: lo que declare el sitio — `2D`, `3D`, `XD`, `4DX`, `IMAX`,
  `PREMIER`, `MACRO XE`. Vacío si no lo dice.
- `idioma`: **`doblada`** o **`subtitulada`**, en minúscula, traduciendo lo
  que diga el sitio ("DOB", "Español", "Castellano" → doblada; "SUB",
  "Subtitulada", "VOSE" → subtitulada). Vacío si no lo declara. Es el filtro
  más usado de la página: si el sitio lo dice, no lo dejes vacío.
- `duracion_min`: solo el número (`152`). Vacío si no aparece.
- `clasificacion`: como la escriba el sitio — `TE`, `TE+7`, `TE+14`, `MA14`,
  `+18`.
- `poster`: URL completa de la imagen, empezando en `https://`.
- `link_compra`: la URL a la que lleva apretar ese horario. Si el sitio no
  da una URL por función, usa la de la película en esa sala; y si tampoco,
  la de la cartelera de esa sala. **Sin link no incluyas la fila.**

### Formato de salida

Un único CSV, UTF-8, separador coma, con este encabezado exacto y en este
orden:

```
cine,pelicula,fecha,hora,formato,idioma,duracion_min,clasificacion,poster,link_compra,sinopsis,trailer,generos
```

Las tres últimas son de la PELÍCULA (se repiten en cada una de sus funciones,
está bien): **sinopsis** es el resumen que publica el cine —un párrafo, sin
inventar—, **trailer** la URL de YouTube o Vimeo del tráiler, y **generos** los
géneros separados por coma ("Acción, Aventura"). Si el sitio no los trae,
quedan vacías. Sirven para la vista "¿Qué película veo?", donde la Cabra
presenta la cartelera con su descripción.

Ordena por `cine`, después por `fecha` y después por `hora`. Deduplica por
(cine + pelicula + fecha + hora). Entrega el archivo `.csv` adjunto **y** el
contenido en un bloque de código.

Ejemplo de dos filas bien hechas:

```
cine,pelicula,fecha,hora,formato,idioma,duracion_min,clasificacion,poster,link_compra,sinopsis,trailer,generos
Cinépolis Mallplaza Egaña,La odisea,2026-08-25,19:40,2D,subtitulada,152,MA14,https://…/odisea.jpg,https://cinepolis.com/cl/compra/12345,"La saga de Homero llega a IMAX por primera vez.",https://youtu.be/8un_UztYsw0,"Acción, Aventura"
```

### Además del CSV, quiero un resumen corto

1. **Funciones por sala.**
2. **Salas que no dieron nada**, y por qué (sin cartelera cargada, bloqueada,
   la página no abrió).
3. **Nombres que el sitio escribe distinto** a la tabla de abajo, con los dos
   nombres. Las salas marcadas "confirma el nombre" salieron del cruce de sus
   coordenadas con el mall que las contiene, no del sitio de la cadena: si
   ves cómo se llaman de verdad, dímelo y corrijo el catastro.
4. **Salas que ya no existen** o que aparecen y no están en la tabla.

### Las salas


### Cineplanet — 6 salas

Dónde mirar: https://www.cineplanet.cl/

| Escribe la sala así en el CSV | Comuna | Dirección |
|---|---|---|
| Cineplanet Alameda | Estación Central | Avenida Libertador Bernardo O'Higgins |
| Cineplanet Costanera Center | Providencia | Avenida Andrés Bello 2461 |
| Cineplanet Florida Center | La Florida | Avenida Vicuña Mackenna Oriente 6100 |
| Cineplanet Lo Barnechea ⟵ **confirma el nombre** | Lo Barnechea | Avenida La Dehesa 1445 |
| Cineplanet Mall Barrio Independencia | Independencia | Avenida Independencia 565 |
| Cineplanet Quilín | Peñalolén | Avenida Américo Vespucio 3300 |

### Cinépolis — 20 salas

Dónde mirar: https://cinepolis.com/cl

| Escribe la sala así en el CSV | Comuna | Dirección |
|---|---|---|
| Cinépolis Arauco Maipú | Maipú | Avenida Américo Vespucio 399 |
| Cinépolis Arauco Quilicura | Quilicura | Avenida Bernardo O'Higgins 581 |
| Cinépolis Casacostanera | Vitacura | Avenida Nueva Costanera 3900 |
| Cinépolis La Reina ⟵ **confirma el nombre** | La Reina | Avenida Ossa 655 |
| Cinépolis Maipú ⟵ **confirma el nombre** | Maipú | Avenida Lo Espejo |
| Cinépolis Mallplaza Egaña | La Reina | Avenida Larraín 5862 |
| Cinépolis Mallplaza Sur | San Bernardo | Avenida Presidente Jorge Alessandri Rodríguez 20040 |
| Cinépolis Melipilla | Melipilla | Vicuña Mackenna 01372 |
| Cinépolis Melipilla (Serrano 395) ⟵ **confirma el nombre** | Melipilla | Serrano 395 |
| Cinépolis Parque Arauco | Las Condes | Avenida Presidente Kennedy 5413 |
| Cinépolis Paseo Los Dominicos | Las Condes | Camino El Alba 11969 |
| Cinépolis Paseo Los Trapenses | Lo Barnechea | Avenida Los Trapenses 3515 |
| Cinépolis Paseo San Bernardo | San Bernardo | Eyzaguirre |
| Cinépolis Plaza Los Dominicos | Las Condes | Avenida Padre Hurtado Sur 875 |
| Cinépolis Portal Exposición | Estación Central | — |
| Cinépolis Puente Alto ⟵ **confirma el nombre** | Puente Alto | — |
| Cinépolis Puente Alto (Independencia) ⟵ **confirma el nombre** | Puente Alto | Independencia |
| Cinépolis Terrazas Maipú | Maipú | — |
| Cinépolis Vivo Imperio | Santiago | Huérfanos |
| Cinépolis Vivo Outlet La Florida | La Florida | Rojas Magallanes 1856 |

### Salas independientes chicas — 4 salas

Dónde mirar: (cada una en su sitio o su Instagram)

| Escribe la sala así en el CSV | Comuna | Dirección |
|---|---|---|
| Cine Mayo | Santiago | — |
| Cine UC | Santiago | — |
| MUVIX Cinema | San Joaquín | Avenida Alcalde Carlos Valdovinos 200 |
| ZooCine | Santiago | — |

---

## Qué pasa después

`loica/cartelera/asistida.py` lee el CSV, pega cada fila con su sala del
catastro por nombre o por alias, descarta lo que no calza (y dice cuántas y
por qué), y `run_cine.py` lo junta con lo que sí se pudo leer solo. Una fila
con un link que no sea `http(s)` no se publica: es la misma regla que corre
para todo dato de fuente que termina en un `href`.
