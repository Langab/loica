# Auditoría de la extracción diaria — 22 de agosto de 2026

Pregunta de Benjamín: "siento que estamos pegados en el bucle de depender de
la extensión de Claude para Chrome; ¿hay forma de correr la actualización
diaria sin que mi computador esté encendido?". Esto es lo que se midió, lo
que se cambió y lo que queda en sus manos.

## En una línea

El 92 % del trabajo manual semanal es Passline y Ticketplus; Ticketplus se
puede automatizar con un adaptador que ya existe, Ticketmaster con una key
gratis, y el recorrido por dieciséis municipios rendía dieciocho eventos a la
semana. Lo único que de verdad necesita un navegador es Passline. Y la
corrida diaria ya no necesita el Mac: corre en GitHub Actions con la base
viajando en git.

## 1. De qué dependía cada cosa

| Pieza | Antes | Ahora |
|---|---|---|
| Corrida diaria de eventos (`run_todo.py`) | launchd en el Mac a las 11:00; Mac apagado = no hay corrida; Mac durmiendo = corrida de 11 horas (la del 21-08) | GitHub Actions, `.github/workflows/corrida.yml` |
| Descuentos bancarios | GitHub Actions a las 07:15 (ya estaba) | Igual; ver el hallazgo de Pages más abajo |
| Base consolidada (`datos/eventos.db`) | Solo en el Mac, fuera de git | Copia en git (`datos/eventos.jsonl`), la base se rearma sola desde ahí |
| Índice OSM (24 MB) | Solo en el Mac | Release `indice-osm` del repositorio, el workflow lo baja |
| Extracción asistida | Una sesión semanal de Claude en Chrome con dieciséis fuentes + tres ticketeras, visitando ficha por ficha (~640 fichas) | Una sesión semanal solo con Passline (~350 fichas) mientras Passline no ofrezca feed; el CSV se sube con git y dispara la corrida solo |

## 2. El CSV asistido, medido

`datos/manual/asistida.csv` al 21-08-2026: 700 filas.

| Fuente | Filas | % | Se puede automatizar |
|---|---:|---:|---|
| Passline | 354 | 51 % | **No.** Cloudflare Managed Challenge: `robots.txt` responde 200 y es permisivo (solo veda carro y tickets), pero `sitemap.xml` y todo lo demás devuelven 403 `cf-mitigated: challenge`. Rodearlo está fuera de las reglas del proyecto. |
| Ticketplus | 292 | 42 % | **Sí, con lo que ya hay.** Su `robots.txt` permite `/events/*` y `/companies/*`; `sitemap.xml` publica 396 fichas de eventos con `lastmod`; el adaptador `sitemap` ya lo lee para Club Subterráneo. La fuente `ticketplus` está apagada por una "decisión estratégica" cuya nota quedó truncada en el YAML (termina en "y publica si"), así que la razón no está escrita en ninguna parte, y mientras tanto se extraía a mano cada semana. |
| Ticketmaster | 20 | 3 % | **Sí, con una key gratis** (developer.ticketmaster.com). El adaptador está escrito. La key va como secreto `TICKETMASTER_API_KEY` del repositorio. |
| 16 municipios y museos | 34 | 5 % | Nueve de las dieciséis no dieron ni una fila. De las 34, MUT (11), MAVI (2), Vicuña Mackenna (2) y Museo de la Educación (1) ya entran solas por el pipeline. Lo que de verdad aportaba el recorrido: Peñalolén 9, Vitacura 7, Independencia 2. |

En la base, lo vigente que depende del CSV: Passline 622, Ticketplus 250 (+25
de Club Subterráneo, que sí es automático), Ticketmaster 19.

## 3. Qué se hizo con cada una

- **Passline**: se queda a mano, pero sola. `_prompt_chrome_semanal.md` es ahora
  un prompt de una sola fuente, y subir el CSV con git dispara la corrida en la
  nube. La puerta lateral sigue abierta: Club Chocolate publica sus eventos con
  el link de Passline en un campo estructurado. Lo que falta es de Benjamín:
  pedirle a Passline un feed o acceso de "productor"; crear cuentas no es algo
  que Claude haga.
- **Ticketplus**: la entrada `ticketplus` de `config/fuentes.yaml` queda lista
  para encender (`activa: true`), con el sondeo de hoy anotado. Es una decisión
  de Benjamín porque revierte una suya; el dato es que ya la estaba extrayendo
  a mano.
- **Ticketmaster**: key → secreto del repositorio → `activa: true`. Cinco
  minutos, una vez.
- **Municipios**: salen del prompt semanal. Las nueve que no dan nada ni con
  una persona mirando (Recoleta, Renca, Lo Espejo, Macul, Colina, Conchalí,
  Corporación de Estación Central, Deportes Padre Hurtado, Parquemet) son
  candidatas a apagar: el diagnóstico las marca "sin nada futuro" todos los
  días y Conchalí sola cuesta 5 minutos de corrida por cero eventos. No se
  apagaron hoy: son agendas municipales y pueden despertar en marzo.

## 4. La corrida en la nube

Lo que hacía falta para sacarla del Mac no era el workflow, era la memoria:
un runner nace vacío. Decisiones:

- La base SQLite sigue fuera de git (binaria, cambia entera). Viaja su copia,
  `datos/eventos.jsonl`, una línea por evento ordenada por hash: el diff diario
  muestra solo lo que cambió y pesa lo que pesa un día de `web/e/`.
  `Almacen` la restaura cuando la base está vacía o cuando el archivo cambió
  por debajo (por huella, no por fecha); `run_diario.py` la vuelca al terminar.
  En el Mac, `git pull` deja la base al día.
- El índice OSM (24 MB, se reconstruye un par de veces al año) va como asset
  del release `indice-osm`; `scripts/construir_indice_osm.py` avisa cómo subirlo.
- Caché de coordenadas, historial del diagnóstico y colas de revisión entran
  a git y a `RUTAS_PUBLICABLES`.
- `TZ=America/Santiago` en el workflow: el runner está en UTC y sin eso "hoy"
  cambiaba a las 20:00 de Chile.
- Los informes quedan como artefacto (30 días) y el del día en el resumen de
  la corrida.
- Primera corrida (`sin-publicar`, 22-08-2026): [pendiente — se completa con
  el resultado: duración, fuentes que bloquean IPs de datacenter, diferencias
  contra la corrida del Mac].

## 5. Hallazgos de paso

- **Los descuentos de la mañana no llegaban al sitio.** Un push hecho con el
  token de Actions no dispara otros workflows (regla de GitHub contra bucles),
  así que `pages.yml` nunca corrió para un commit "Descuentos al...": cero de
  todos los que hay en el historial. El JSON esperaba a que el Mac publicara.
  `corrida.yml` le avisa a Pages con `gh workflow run`; `descuentos.yml` no
  se tocó porque tenía ediciones ajenas sin comitear, pero le falta la misma
  línea.
- **Las 11 horas del 21-08 no fueron la extracción**: el log tiene saltos de
  266, 96 y 82 minutos entre línea y línea. Era el Mac durmiendo. Una corrida
  normal dura 41–45 minutos (17-08 y 20-08).
- `_resolver_generados` no contaba `web/talleres.json` como archivo generado:
  un choque ahí habría abortado la publicación. Corregido.
- `openpyxl` no estaba en `requirements.txt`; el diagnóstico lo necesita.
  Corregido.
- El comentario de `descuentos.yml` tiene las estaciones al revés (Chile está
  en UTC-4 en invierno y UTC-3 en verano). No cambia nada: corren los dos
  crons y uno coincide.
- Las ediciones sin comitear en `descuentos.yml` y `pages.yml` (acciones
  fijadas por SHA) son correctas: `11d5960a` es `actions/checkout` v4.4.0.
  Ninguna de las sesiones abiertas las reclama.

## 6. Lo que queda en manos de Benjamín

1. Encender Ticketplus (`activa: true` en `config/fuentes.yaml`) o escribir la
   razón para no hacerlo donde la nota truncada la perdió.
2. Sacar la key de Ticketmaster y guardarla como secreto del repositorio.
3. Escribirle a Passline pidiendo un feed o acceso de productor.
4. Decidir si las nueve fuentes municipales sin agenda se apagan.
5. Agregar a `descuentos.yml` el aviso a Pages (o dejar que la corrida de las
   11:00 lo publique, que es lo que pasa hoy).
