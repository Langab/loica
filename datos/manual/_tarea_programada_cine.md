# La cartelera de cine como tarea programada del escritorio

Lo que hoy es una sesión a mano con Claude en el navegador (Brave con la
extensión de Claude en Chrome) puede correr sola **en este Mac**, no en la
nube: GitHub Actions no tiene navegador ni extensión, y las dos cadenas que
faltan —Cinépolis (API con token) y Cineplanet (cookie de sesión; sus JSON
responden 403 a un cliente identificado)— solo se leen desde un navegador de
verdad. La aplicación de escritorio de Claude tiene "tareas programadas": un
prompt que corre a una hora fija **mientras la aplicación esté abierta** (si
está cerrada, corre al abrirla) y que puede usar la extensión del navegador.

## Antes de encenderla, la decisión que es del dueño

`_runbook_asistido.md` dice por qué existe la extracción asistida: *una
persona pidiéndolo, puntual, en su navegador, es navegar con ayuda; un cron
haciendo lo mismo solo es un bot desatendido entrando donde el sitio puso un
control para impedirlo*. Esa línea sigue en pie para Passline y Santander
(Cloudflare y WAF: controles contra clientes automáticos). Los cines son otro
caso: Cinemark ya entra solo, Cinépolis y Cineplanet no tienen desafío contra
bots sino puertas (token, cookie) que su propia página abre para cualquier
navegador. Programar esta tarea es decidir que leer esas páginas todos los
días con un navegador es mirar y no rodear. Es una decisión, no un detalle
técnico, y por eso no viene encendida.

## Cómo se enciende

En una sesión de Claude Code (escritorio), pedir literalmente:

> Creá una tarea programada `cartelera-cine` que corra todos los jueves a las
> 07:30 con el prompt de `datos/manual/_tarea_programada_cine.md`.

(Los jueves cambia la programación; una segunda corrida los lunes cubre el
fin de semana largo de las salas que publican de a dos días.)

## El prompt de la tarea

```
Sos el extractor de la cartelera de cine de Loica. Trabajás en
/Users/langa/dev/loica-pipeline con la extensión de Claude en Chrome del
navegador local (Brave). Seguí al pie de la letra la sección "CSV 2 —
Cartelera de cine" de datos/manual/_prompt_asistido.md: las 20 salas de
Cinépolis (una sala a la vez, borrando el chip antes de navegar y verificando
el nombre de la sala en pantalla antes de extraer), Cineplanet por sus tres
JSON públicos desde una pestaña parada en cineplanet.cl, y MUVIX. Hasta 7
días desde hoy. No hagas clic en ningún horario (abre la compra). Si un sitio
pide login, muestra captcha o "verificando su conexión", anotalo y seguí: no
rodees nada.

Escribí los CSV con csv.writer de Python, con el encabezado exacto del
prompt, en una carpeta nueva datos/manual/loica_asistida_<AAAAMMDD>/ (fecha
de hoy). Copiá a esa carpeta los archivos de la carpeta con fecha anterior
que NO hayas regenerado (asistida.csv, descuentos_*.csv, RESUMEN_*.md), para
que la pasada siga siendo una foto completa: loica/asistida.py manda la
carpeta más nueva y lo que ella no trae se pierde.

Antes de guardar, corré el chequeo del prompt (encabezado, fechas
AAAA-MM-DD, horas HH:MM, sala contra config/cines.yaml, promedio de funciones
por sala y día ~24; si da ~100 hay conteo doble). Después:

  git pull --rebase --autostash
  git add datos/manual/loica_asistida_<AAAAMMDD>/
  git commit -m "Cartelera de cine al <AAAA-MM-DD>"
  git push

Ese push dispara la corrida en la nube, que publica sola. Dejá un resumen de
dos líneas por cadena (salas con funciones, salas en cero y por qué) en
datos/manual/loica_asistida_<AAAAMMDD>/RESUMEN_cine_<AAAA-MM-DD>.md. Si algo
falló, decilo ahí y no subas CSV a medias: una cadena entera o nada.
```

## Lo que hay que saber

- Corre en la cuenta de la aplicación de escritorio, con Brave abierto y la
  extensión conectada. Si el Mac está apagado, no corre; corre al abrir.
- Cinépolis tarda ~60 minutos con tres agentes en paralelo; una sola sesión
  secuencial puede tardar dos horas. Programarla temprano.
- Cada corrida comitea y pushea sola. Si se prefiere revisar antes, sacar las
  tres líneas de git del prompt y subir a mano.
