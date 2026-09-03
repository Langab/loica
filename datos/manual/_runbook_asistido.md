# Runbook de extracción asistida

Lo que **no** se puede automatizar, pero sí se puede hacer contigo presente,
con la extensión de Claude en tu Chrome. Diez minutos, una vez por semana.

## Por qué existe este archivo

El pipeline automático cubre ~50 fuentes y corre solo a las 11:00. Lo que queda
fuera son sitios que mantienen un desafío activo contra clientes automatizados
(Passline, Itaú, Centro Arte Alameda) o que exigen sesión (Instagram).

Esos sitios **sí** cargan en un navegador de verdad. La diferencia no es
técnica sino de naturaleza:

- **Vos pidiéndomelo, puntual, en tu navegador** → es navegar con ayuda. Se hace.
- **Un cron a las 11:00 haciendo lo mismo solo** → es un bot desatendido
  entrando donde el sitio puso un control para impedirlo. No se hace.

Por eso esto es un runbook y no un script.

---

## Dónde termina todo

```
extracción asistida  ─┐
                      ├─→  datos/manual/loica_asistida_AAAAMMDD/
scrapers automáticos ─┤          │
                      │          ↓
                      └─→  datos/eventos.db   ← LA BASE CONSOLIDADA
                                 │              (SQLite, tabla `eventos`)
                                 ↓
                          web/eventos.json  →  el sitio
```

### Una carpeta con fecha por pasada

Desde el **01-09-2026** la sesión entrega una CARPETA, no archivos sueltos:

    datos/manual/loica_asistida_20260901/
      asistida.csv                  los eventos
      cartelera_cinepolis.csv       el cine
      cartelera_cineplanet.csv
      cartelera_independientes.csv
      descuentos_santander.csv      los descuentos que no se pueden rastrear
      RESUMEN_2026-09-01.md          los hallazgos que no caben en un CSV

Manda la carpeta con la fecha más nueva, y manda **por nombre de archivo**: lo
que la carpeta trae tapa a la copia suelta de la raíz; lo que no trae
(`blondie.yaml`, `fondas_2026.yaml`) se sigue leyendo de la raíz.

Dos cosas que esto arregla y conviene no perder:

1. **La pasada es una foto completa, no un parche.** Sobre todo en el cine: una
   función es de un día concreto, y mezclar la pasada de la semana pasada con
   la de hoy no suma salas, publica horarios que ya pasaron.
2. **Comparar dos pasadas es un `diff` entre dos carpetas.** Ya no hace falta
   guardar una copia aparte en `notas/asistida/`.

La base consolidada es **`datos/eventos.db`**. Todo lo que entra —automático o
asistido— pasa por las mismas reglas: se normaliza, se deduplica por
título+fecha+lugar, se geocodifica y queda en estado `borrador`.

Un evento que ya trajo un scraper no se duplica si lo agregás a mano: el
deduplicador lo reconoce.

---

## La rutina semanal

### 1. Passline y Ticketplus — las dos ticketeras

**Ticketplus** entra sola desde el 03-09-2026 (fuente `ticketplus`, sitemap +
JSON-LD, 120 fichas por corrida) y además va en la pasada, que cubre el
catálogo entero: el bloque 1 de `_prompt_asistido.md` dice cómo. Lo que sigue
es Passline, que solo se puede mirar con el navegador.

**Por qué a mano:** Cloudflare Managed Challenge. Devuelve 403 a Python con
cualquier user-agent, incluso desde la máquina donde corre el pipeline.

**Qué pedirme:** *"abrí passline y sacá la cartelera de la RM"*

**Qué obtengo:** título, fecha, hora, recinto, comuna y el link de cada evento.

**Dónde queda:** `asistida.csv` dentro de la carpeta de la pasada.

> La carpeta **reemplaza** a la anterior, no se acumula con ella. Los eventos
> que ya pasaron se caducan solos, así que una pasada vieja se va vaciando sin
> rellenarse.

### 2. Instagram — el circuito sin ticketera

**Por qué a mano:** la API no lee cuentas ajenas, y la vista pública muestra el
perfil pero esconde el pie de foto tras un muro de login.

**IMPORTANTE:** esto requiere que **vos** estés logueado y copies los pies de
foto. Yo no me logueo con tu cuenta: actividad automatizada sobre una cuenta
personal de Instagram es la forma más rápida de que te la restrinjan.

**Qué pedirme:** pegame el texto crudo de los posts. Yo interpreto el afiche
desordenado —"🔥ESTE VIERNES DIRTY PERREO @ Coco, 23hrs, +18"— y lo dejo
estructurado.

**Cuentas a vigilar:** ver `_instagram.md`

**Dónde queda:** `instagram.yaml` dentro de la carpeta de la pasada.

### 3. Santander y Bci — los descuentos

**Por qué a mano:** `banco.santander.cl` responde 403 a todo, incluido
`/robots.txt`. Ni siquiera se puede leer qué permite. Y `bci.cl/beneficios`
hace lo mismo (WAF): el portal abierto que se leía en su lugar,
`vivirconbeneficios.cl`, es un catálogo muerto desde 2021 —sus promociones
traen `end_date` de 2018 a 2020— y desde el 02-09-2026 ya no se publica. El
catálogo vivo de Bci entra por acá, como `descuentos_bci.csv`, con el mismo
formato que Santander.

**Cuándo:** el primer día hábil de cada mes. Los dos bancos rotan la parrilla
por mes y la mayoría vence el día 30: el 01-09-2026, 173 de 180 filas de
Santander y 77 de 80 de Bci vencían el 30-09. La corrida avisa sola cuando la
captura pasa de 45 días (`avisar_dias` en `config/bancos.yaml`).

**Qué falta hoy:** de las 180 filas del 01-09-2026, 64 traen calle y número.
Las otras 116 caen en el centroide de su comuna, no en la puerta del local.

**Qué pedirme:** *"abrí la ficha de cada descuento de Santander y sacá la
dirección"*. La ficha (al hacer clic en el local) tiene **dirección, logo, tope
y vigencia**.

**Dónde queda:** `descuentos_santander.csv` dentro de la carpeta de la pasada,
con estas columnas:

    banco,comercio,direccion,comuna,lat,lon,logo,dias,monto,tope,vigencia,
    sitio_web,categoria,url

Una fila por **local**, no por convenio: 1213 va dos veces porque tiene dos
direcciones, y así las dos caen en el mapa. `dias` separa con `;`, `vigencia`
es ISO (`2026-09-30`) y `url` es la ficha de esa promoción, que Santander
publica con página propia.

Ojo con la vigencia: **el pie legal del sitio no rota** —el 01-09-2026 todavía
decía "válidos durante el mes de marzo de 2026"— así que hay que leerla en la
ficha de cada promoción.

---

## Después de cada sesión asistida

```bash
python3 run_todo.py
```

Levanta lo que dejamos en `datos/manual/`, corre las 50 fuentes automáticas,
arma el sitio y lo publica. GitHub Actions lo deja en Pages solo.

Para revisar antes de publicar:

```bash
python3 run_todo.py --sin-publicar
```

---

## La regla que no cambia

Todo evento necesita `fuente_url`. Sin link no se guarda, venga de donde venga.
Es lo que mantiene a Loica como índice que deriva tráfico al organizador, y no
como copia. La imagen se enlaza, nunca se descarga.
