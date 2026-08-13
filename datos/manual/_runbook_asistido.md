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
                      ├─→  datos/manual/*.yaml|csv
scrapers automáticos ─┤          │
                      │          ↓
                      └─→  datos/eventos.db   ← LA BASE CONSOLIDADA
                                 │              (SQLite, tabla `eventos`)
                                 ↓
                          web/eventos.json  →  el sitio
```

La base consolidada es **`datos/eventos.db`**. Todo lo que entra —automático o
asistido— pasa por las mismas reglas: se normaliza, se deduplica por
título+fecha+lugar, se geocodifica y queda en estado `borrador`.

Un evento que ya trajo un scraper no se duplica si lo agregás a mano: el
deduplicador lo reconoce.

---

## La rutina semanal

### 1. Passline — la cartelera nacional

**Por qué a mano:** Cloudflare Managed Challenge. Devuelve 403 a Python con
cualquier user-agent, incluso desde la máquina donde corre el pipeline.

**Qué pedirme:** *"abrí passline y sacá la cartelera de la RM"*

**Qué obtengo:** título, fecha, hora, recinto, comuna y el link de cada evento.

**Dónde queda:** `datos/manual/passline.csv`

> El CSV se **reemplaza**, no se acumula. Los eventos que ya pasaron se caducan
> solos, así que un CSV viejo se va vaciando sin rellenarse.

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

**Dónde queda:** `datos/manual/instagram.yaml`

### 3. Santander — los descuentos

**Por qué a mano:** `banco.santander.cl` responde 403 a todo, incluido
`/robots.txt`. Ni siquiera se puede leer qué permite.

**Qué falta hoy:** sus 72 descuentos no tienen dirección, así que no caen en el
mapa ni se filtran por comuna. Salen como "Metropolitana" a secas.

**Qué pedirme:** *"abrí la ficha de cada descuento de Santander y sacá la
dirección"*. La ficha (al hacer clic en el local) tiene **dirección, logo, tope
y vigencia** — los cuatro campos que faltan.

**Dónde queda:** `datos/manual/descuentos_santander.yaml` — el formato completo
está documentado en la cabecera de ese archivo.

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
