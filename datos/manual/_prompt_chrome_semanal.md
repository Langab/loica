# Prompt semanal para Claude en Chrome

Copiar el bloque de abajo completo y pegarlo en Claude en el navegador, una vez
por semana. Devuelve un CSV que se guarda en `datos/manual/asistida.csv` y lo
levanta la corrida siguiente sin tocar nada más.

La lista de fuentes se saca de la hoja **Fuentes** del Excel de diagnóstico
(`informes/AAAA-MM-DD_diagnostico.xlsx`), filtrando por estado distinto de
`extrajo`. La de abajo es la del 19-08-2026 y conviene refrescarla cada mes.

---

Necesito que revises unas agendas culturales de Santiago de Chile y me armes un
CSV. Trabajo en Loica, un índice de panoramas de la Región Metropolitana: cada
evento se publica con su link a la fuente original, así que el link es
obligatorio y el dato tiene que ser textual, nunca inventado.

Estas quince páginas cargan bien pero mi extractor automático no logra leerles
la fecha, así que necesito que las mires vos y me digas qué hay realmente.

**Reglas que no se rompen:**

1. **Nada inventado.** Si un evento no dice la fecha, no lo incluyas. Si no
   dice la hora, dejá la hora vacía. Prefiero diez eventos ciertos a cuarenta
   con datos rellenados.
2. **Solo eventos futuros**, de hoy en adelante. Lo que ya pasó no sirve.
3. **Solo Región Metropolitana.** Si una agenda tiene eventos de regiones,
   descartalos.
4. **El link es obligatorio.** Tiene que ser la URL de la ficha del evento, la
   página que abriría una persona. Si un evento no tiene página propia, usá la
   URL de la agenda donde aparece. Sin link, no lo incluyas.
5. **No te saltes ningún bloqueo.** Si una página pide iniciar sesión, muestra
   un captcha o un "verificando su conexión", no intentes rodearlo: anotá esa
   fuente como bloqueada en el resumen final y seguí con la siguiente.
6. **No copies descripciones largas.** Solo los hechos: qué, cuándo, dónde,
   cuánto.

**Las páginas, con su nombre exacto** (el nombre va tal cual en la columna
`fuente_nombre`, no lo cambies ni lo abrevies):

| # | fuente_nombre | Dónde mirar | Comuna |
|---|---|---|---|
| 1 | `Municipalidad de Recoleta` | https://www.recoleta.cl | Recoleta |
| 2 | `Ilustre Municipalidad de Renca` | https://www.renca.cl | Renca |
| 3 | `Municipalidad de Independencia` | https://www.independencia.cl | Independencia |
| 4 | `Municipalidad de Lo Espejo` | https://www.loespejo.cl | Lo Espejo |
| 5 | `Municipalidad de Penalolen` | https://www.penalolen.cl | Peñalolén |
| 6 | `Municipalidad de Macul` | https://www.munimacul.cl | Macul |
| 7 | `Municipalidad de Colina` | https://www.colina.cl | Colina |
| 8 | `Municipalidad de Conchali` | https://www.conchali.cl | Conchalí |
| 9 | `Corporacion Cultural de Estacion Central` | https://www.ecentral.cl | Estación Central |
| 10 | `Corporacion Cultural de Vitacura` | https://vitacuracultura.cl | Vitacura |
| 11 | `Corporacion Municipal de Deportes de Padre Hurtado` | https://www.cmdpadrehurtado.cl | Padre Hurtado |
| 12 | `Parquemet (Cerro San Cristobal y parques urbanos)` | https://parquemet.cl | Varias |
| 13 | `MUT — Mercado Urbano Tobalaba` | https://mut.cl/eventos/ | Providencia |
| 14 | `MAVI UC (Museo de Artes Visuales)` | https://mavi.uc.cl | Santiago |
| 15 | `Museo Benjamin Vicuna Mackenna` | https://www.museovicunamackenna.gob.cl | Providencia |
| 16 | `Museo de la Educacion Gabriela Mistral` | https://www.museodelaeducacion.gob.cl | Santiago |

En los municipios la agenda casi nunca está en la portada: buscá en el menú
algo como "Cultura", "Actividades", "Agenda", "Cartelera" o "Noticias". Si el
municipio no tiene agenda de eventos y solo publica noticias administrativas
(licitaciones, cuentas públicas, ofertas de empleo), decímelo en el resumen y
no fuerces nada: esa es información útil, significa que hay que apagar esa
fuente.

**Formato del CSV.** Estas columnas exactas, en este orden, con encabezado.
Separador coma, comillas dobles donde haga falta, codificación UTF-8:

```
fuente_nombre,nombre,categoria,fecha_inicio,hora_inicio,fecha_termino,lugar,comuna,precio_min,link_evento
```

| Columna | Qué va | Formato |
|---|---|---|
| `fuente_nombre` | El nombre de la tabla de arriba, textual | texto |
| `nombre` | Título del evento | texto |
| `categoria` | Lo que diga la página: música, teatro, taller, feria, cine, exposición, deporte, familiar. Vacío si no dice | texto o vacío |
| `fecha_inicio` | Día en que empieza | `2026-09-14` |
| `hora_inicio` | Hora de inicio, vacío si no la dice | `19:30:00` |
| `fecha_termino` | Solo si dura varios días; si es de un día, vacío | `2026-09-20` |
| `lugar` | Nombre del recinto: "Teatro Municipal de Recoleta" | texto |
| `comuna` | Comuna del evento | texto |
| `precio_min` | Precio en pesos, sin puntos ni símbolo. **`0` si es gratis.** Vacío si no dice | `5000` |
| `link_evento` | URL de la ficha del evento | `https://...` |

**Ejemplo de dos filas bien hechas:**

```csv
fuente_nombre,nombre,categoria,fecha_inicio,hora_inicio,fecha_termino,lugar,comuna,precio_min,link_evento
Municipalidad de Recoleta,Feria de las Pulgas,feria,2026-09-14,10:00:00,,Plaza de Armas de Recoleta,Recoleta,0,https://www.recoleta.cl/feria-pulgas-septiembre
MAVI UC (Museo de Artes Visuales),Retrospectiva Matta,exposición,2026-09-01,,2026-11-30,MAVI UC,Santiago,3000,https://mavi.uc.cl/exposiciones/matta
```

Fijate en el ejemplo: la feria es de un día, así que `fecha_termino` va vacío y
tiene hora; la exposición dura tres meses, así que lleva `fecha_termino` y no
lleva hora. Los dos campos vacíos se dejan vacíos, no se rellenan con guiones
ni con "N/A".

**Qué quiero de vuelta:**

1. El CSV completo, en un bloque de código, listo para copiar.
2. Un resumen corto: cuántos eventos sacaste de cada fuente, cuáles no tenían
   agenda, cuáles estaban caídas y cuáles te bloquearon el paso.

Empezá por la 1 y andá en orden. Si una página tarda o no carga, pasá a la
siguiente y anotala en el resumen.

---

## Qué hago yo con el resultado

1. Guardar el CSV como `datos/manual/asistida.csv` (se **reemplaza**, no se
   acumula: lo pasado se caduca solo).
2. La corrida siguiente lo levanta sola — `datos/manual/` es parte de
   `RUTAS_PUBLICABLES` y el adaptador `manual` lee todos los `.csv` de ahí.
3. Para probarlo antes de publicar:
   `python3 run_diario.py --fuente ingesta_manual`

Los eventos entran como **borrador**, se deduplican contra lo que ya está
—si un scraper ya lo trajo no se duplica— y se geocodifican como cualquier
otro. La columna `fuente_nombre` es la que hace que cada evento quede
atribuido a su municipio y no al archivo.
