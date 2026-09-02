# Prompt semanal para Claude en Chrome — solo Passline

Copiar el bloque de abajo completo y pegarlo en Claude en el navegador, una vez
por semana. Devuelve un CSV que se guarda como `asistida.csv` **dentro de la
carpeta con fecha de la pasada** —`datos/manual/loica_asistida_AAAAMMDD/`— y se
sube con git: la corrida en la nube arranca sola al ver la carpeta nueva y la
publica.

```bash
git add datos/manual/loica_asistida_$(date +%Y%m%d)/
git commit -m "Passline al $(date +%F)"
git push
```

Manda la carpeta con la fecha más nueva. La anterior queda ahí al lado como
historia: comparar dos pasadas es un `diff` entre dos carpetas.

## Por qué solo Passline

La auditoría del 22-08-2026 (`notas/_auditoria_extraccion_2026-08-22.md`)
midió el CSV asistido: 700 filas, de las cuales 354 eran Passline, 292
Ticketplus, 20 Ticketmaster y 34 de los dieciséis municipios y museos del
recorrido anterior. De esas 34, la mitad ya las traía el pipeline solo (MUT,
MAVI, Vicuña Mackenna, Museo de la Educación), y nueve de las dieciséis páginas
no dieron ni una fila. El recorrido municipal costaba una hora de navegador
por unos dieciocho eventos a la semana.

Ticketplus se puede leer con el adaptador de sitemap que ya usa Club
Subterráneo (su robots.txt lo permite) y Ticketmaster tiene API con key
gratis: esas dos salen del prompt en cuanto se enciendan en
`config/fuentes.yaml`. Passline es la única que de verdad necesita un
navegador: está tras un Cloudflare Managed Challenge y el proyecto no lo
rodea. Hasta que Passline ofrezca un feed, esto es lo que queda a mano.

---

Necesito que revises la cartelera de Passline para Santiago de Chile y me
armes un CSV. Trabajo en Loica, un índice de panoramas de la Región
Metropolitana: cada evento se publica con su link a la fuente original, así
que el link es obligatorio y el dato tiene que ser textual, nunca inventado.

**Dónde mirar:** https://www.passline.com/ con el filtro de región en
**Región Metropolitana**. Cargá toda la paginación ("ver más eventos") antes de
extraer: quiero la lista completa, no una muestra. Después entrá a la ficha de
cada evento para sacar la comuna y el precio, que no vienen en el listado.

**Reglas que no se rompen:**

1. **Nada inventado.** Si la página no dice el dato, la celda va vacía. Nunca
   "N/A", nunca guiones. Si un evento no tiene día calendario explícito, no lo
   incluyas. Prefiero diez eventos ciertos a cuarenta con datos rellenados.
2. **Solo eventos vigentes o futuros**, tomando como referencia la fecha de
   hoy.
3. **Solo Región Metropolitana.** Ojo con recintos trampa: Gran Arena
   Monticello es Mostazal (O'Higgins), no RM.
4. **El link es obligatorio:** la URL de la ficha en Passline
   (`https://www.passline.com/eventos/...`). Sin link, no lo incluyas.
5. **No rodees bloqueos.** Si una página pide iniciar sesión, muestra un captcha
   o un "verificando su conexión", no intentes rodearlo: anotalo en el resumen
   y seguí con la siguiente.
6. **No copies descripciones.** Solo los hechos: qué, cuándo, dónde, cuánto.

**Formato del CSV.** Estas columnas exactas, en este orden, con encabezado.
Separador coma, comillas dobles donde haga falta, codificación UTF-8:

```
fuente_nombre,nombre,categoria,fecha_inicio,hora_inicio,fecha_termino,lugar,comuna,precio_min,link_evento
```

| Columna | Qué va | Formato |
|---|---|---|
| `fuente_nombre` | Siempre `Passline`, textual | texto |
| `nombre` | Título del evento | texto |
| `categoria` | La que diga Passline (música, teatro, fiesta, deporte, familiar...). Vacío si no dice | texto o vacío |
| `fecha_inicio` | Día en que empieza | `2026-09-14` |
| `hora_inicio` | Hora de inicio, vacío si no la dice | `19:30:00` |
| `fecha_termino` | Solo si dura varios días; si es de un día, vacío | `2026-09-20` |
| `lugar` | Nombre del recinto tal como aparece, con dirección si la ficha la trae | texto |
| `comuna` | Comuna del evento, solo si la ficha o la dirección la indican | texto |
| `precio_min` | Precio mínimo comprable en pesos, sin puntos ni símbolo. **`0` si es gratis / entrada liberada.** Vacío si no dice. Si la preventa barata está agotada, usá el siguiente tramo | `5000` |
| `link_evento` | URL de la ficha en Passline | `https://...` |

**Funciones en fechas sueltas** (una obra los sábados 22, 23, 29 y 30): una fila
por función, mismo link. **Temporada corrida** (del 26 al 29): una sola fila con
`fecha_inicio` y `fecha_termino`.

**Ejemplo de dos filas bien hechas:**

```csv
fuente_nombre,nombre,categoria,fecha_inicio,hora_inicio,fecha_termino,lugar,comuna,precio_min,link_evento
Passline,Moonchilds tributo a Iron Maiden,música,2026-08-29,18:00:00,,Club Hell Bar Rojas Magallanes 51,La Florida,3000,https://www.passline.com/eventos/moonchilds-tributo-a-iron-maiden-en-club-hell-bar
Passline,Gran Final Miss Grand Chile 2026,,2026-08-29,20:00:00,,Gran Espacio Parque Walker Martínez 2295,La Florida,39900,https://www.passline.com/eventos/gran-final-miss-grand-chile-2026
```

**Qué quiero de vuelta:**

1. El CSV completo, en un bloque de código, listo para copiar, ordenado por
   `fecha_inicio` y sin filas repetidas (mismo link y misma fecha).
2. Un resumen corto: cuántos eventos sacaste, cuántas fichas no pudiste abrir
   y si algo te bloqueó el paso.

---

## Qué hago yo con el resultado

1. Guardar el CSV como `asistida.csv` dentro de
   `datos/manual/loica_asistida_AAAAMMDD/` (la carpeta reemplaza a la pasada
   anterior; lo pasado se caduca solo).
2. `git add datos/manual/loica_asistida_$(date +%Y%m%d)/ && git commit -m "Passline al $(date +%F)" && git push`.
   La corrida en la nube arranca sola con ese push y publica en ~1 hora.
3. Para probarlo antes, en el Mac: `python3 run_diario.py --fuente ingesta_manual --probar`.

Los eventos entran como **borrador**, se deduplican contra lo que ya está —si
otra fuente ya lo trajo, no se duplica— y se geocodifican como cualquier otro.
