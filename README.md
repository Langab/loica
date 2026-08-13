# Pipeline de eventos — Loica (Santiago de Chile)

Extractor automático de eventos desde sitios públicos. Corre solo todos los
días, **no usa modelos de lenguaje**, así que no consume tokens ni cuesta
dinero: es Python puro haciendo peticiones HTTP.

Cada evento queda amarrado a su **fuente original con link**. La app no
reemplaza a la fuente: la indexa y deriva el tráfico hacia ella. Eso es lo que
mantiene el rol de "tablón de anuncios" descrito en `04_negocio_y_legal/legal_chile.md`
del proyecto.

## El proceso, de punta a punta

El pipeline implementa este circuito, y cada paso tiene su comando:

| # | Paso | Dónde vive |
|---|---|---|
| 1 | **Identificación de fuentes** | `config/fuentes.yaml` (100 fuentes catastradas, ~50 activas) y `config/bancos.yaml` |
| 2 | **Metodología según la fuente** | `tipo_adaptador` por fuente: API (wordpress/eventon/json/ticketmaster), scraping educado (html/rss/sitemap/carteleras/cine/tabla) o captura asistida (`manual`, para lo que bloquea bots) |
| 3 | **Extracción** | `run_diario.py` (eventos → SQLite) y `run_descuentos.py` (bancos → JSON) |
| 4 | **Consolidación** | todo converge a `datos/eventos.db` deduplicado por título+fecha+lugar; el export arma `web/eventos.json` |
| 5 | **Revisión + memoria de correcciones** | `revisar_extraccion.py` produce el informe y las colas; los arreglos viven en `config/correcciones/` y se aplican solos en cada corrida (ver abajo) |
| 6 | **Doble check** | `verificar_web.py`: si el sitio quedó roto, vacío o cayó a la mitad, **no hay push** |
| 7 | **Publicación** | `run_todo.py` comitea solo su salida y pushea; GitHub Actions deja `web/` en Pages |
| 8 | **Corrida diaria a las 11:00** | launchd (`scripts/instalar_agenda.sh`); el Mac tiene que estar prendido o durmiendo |

Un solo comando encadena los pasos 3 a 7:

```bash
python3 run_todo.py                  # todo, de punta a punta
python3 run_todo.py --sin-publicar   # deja el sitio listo, no toca git
python3 run_todo.py --solo-publicar  # sin extraer: exporta lo que ya hay
python3 run_todo.py --sin-descuentos # sólo eventos
python3 run_todo.py --forzar         # publica aunque el volumen haya caído
```

Después del push, GitHub Actions publica `web/` en Pages solo.

## La memoria de correcciones (paso 5, el corazón de la calidad)

La extracción se equivoca siempre en los mismos lugares: un lugar que ningún
geocodificador encuentra, un taller de aerobike que cae en "música", un
restaurante sin comuna. La regla acá es que **cada error se corrige UNA vez**
y queda en la memoria:

- `config/correcciones/lugares.yaml` — un lugar → dirección, comuna y
  coordenadas. Arregla todos sus eventos, presentes y futuros.
- `config/correcciones/eventos.yaml` — un evento puntual (por id) → categoría,
  ubicación o `descartar: true`. Es el bisturí.
- `config/correcciones/restoranes.yaml` — un local con descuento → cocina,
  rubro y ubicación. Aplica en todos los bancos que lo publiquen.

El ciclo diario: `revisar_extraccion.py` deja el informe en
`informes/AAAA-MM-DD_revision.md` y las **colas priorizadas** en
`datos/revision/pendientes_*.yaml` (esqueleto listo para completar). Una
persona —o una sesión de Claude— verifica los datos, los pega en
`config/correcciones/` y comitea. La corrida siguiente los aplica sola.
Si el mismo error se repite en eventos nuevos, el arreglo va en el código
(`loica/clasificar.py`), no en la memoria.

### El índice local de OSM

Los robots.txt de Nominatim, Photon y Overpass prohíben consultarlos con un
cliente automático, y este proyecto no evade esos controles. En su lugar, la
georreferenciación usa una **copia local de OpenStreetMap**: 

```bash
python3 scripts/construir_indice_osm.py   # baja el extracto de Chile UNA vez
```

Eso deja `datos/indice_osm.db` (301.472 direcciones con número y 11.900
locales con nombre de toda la RM), y `loica/geo.py` lo consulta en SQLite sin
tocar la red. Datos © colaboradores de OpenStreetMap (ODbL), la misma licencia
de los mosaicos del mapa. Se reconstruye un par de veces al año.

El buscador de direcciones está hecho para lo que de verdad escriben las
fuentes municipales, no para direcciones limpias: acepta el número al final o
al medio del texto (`Guanaco Norte # 1250 Capilla Santa Inés`), ignora la
basura anterior a la calle (`JJ. VV. Simón Bolívar Av. Las Torres 840`),
tolera que el nombre venga recortado por cualquiera de los dos lados
(`Juan Moya` por *Juan Moya Morales*, `Guanaco Norte` por *Avenida El Guanaco
Norte*) y, si no hay comuna, la rescata del propio texto después de la coma.
Todo candidato tiene que caer cerca de la comuna declarada: cuando el mismo
nombre de calle existe en media región, se prefiere no poner pin antes que
ponerlo mal. Con eso la ubicación exacta pasó de 31% a 61% de los eventos.

Los pasos sueltos siguen sirviendo para depurar:

```bash
python3 run_diario.py --fuente gam     # una sola fuente
python3 run_diario.py --probar         # muestra lo que encontraría, sin guardar
python3 run_diario.py --sin-cache -v   # ignora la caché y muestra el detalle
python3 run_descuentos.py --banco bci  # un solo banco
```

### Dos cosas que `run_todo.py` hace a propósito

**Comitea sólo su propia salida.** Corre a las 11:00 sin nadie mirando, así que
nunca hace `git add -A`: si a esa hora hay un archivo a medio editar, un
`add -A` se lo llevaría al repositorio. Agrega únicamente `web/eventos.json`,
`web/descuentos.json`, `web/e/` y `datos/manual/`.

**Resuelve solo los choques en archivos generados.** Los dos catastros
regeneran su JSON todos los días, así que dos corridas seguidas chocan siempre
aunque nadie haya editado nada. En un archivo derivado no hay nada que
fusionar: gana la regeneración más nueva. Si el choque toca código o
configuración, aborta y decide una persona.

Si la extracción de eventos falla entera, no se publica nada: mejor un sitio
con datos de ayer que uno vacío. Los descuentos, en cambio, no abortan la
corrida — que Bci cambie su JSON no es razón para dejar sin actualizar la
agenda, que es el corazón del proyecto.

Después de cada corrida queda un informe en `informes/AAAA-MM-DD_corrida.md`
con los eventos nuevos agrupados por comuna, listos para revisar.

## Cómo dejarlo corriendo solo

```bash
bash scripts/instalar_agenda.sh
```

Queda programado **a las 11:00** con launchd (el equivalente a cron en macOS).
Para cambiar el horario: `HORA=22 MINUTO=30 bash scripts/instalar_agenda.sh`.
Para desinstalarlo: `bash scripts/instalar_agenda.sh --quitar`.

**Qué necesita el Mac para que la corrida de las 11:00 salga:**

- **Prendido o durmiendo.** Si a las 11:00 está durmiendo, launchd corre la
  corrida apenas despierte: el día no se pierde, solo sale más tarde.
- **Apagado no corre nada**, y esa corrida no se recupera al encenderlo (la
  del día siguiente sí sale normal).
- Sesión iniciada (es un agente de usuario, no un demonio del sistema).
- Red, y credenciales de git que no pidan clave: el push es desatendido.
- Para que despierte solo justo antes (opcional, pide contraseña de admin):
  `sudo pmset repeat wakeorpoweron MTWRFSU 10:55:00`.

Se puede verificar con `launchctl list | grep cl.loica.pipeline` y probar al
tiro con `launchctl kickstart gui/$(id -u)/cl.loica.pipeline`.

> Los descuentos además corren solos en GitHub Actions (~07:15), así que esa
> parte no depende del Mac. La corrida de eventos sí: varias fuentes bloquean
> IPs de datacenter, por eso vive en esta máquina y no en la nube.

## El prototipo del mapa

```bash
cd ~/dev/loica-pipeline
python3 exportar_web.py                          # geocodifica y exporta
python3 -m http.server 8777 --directory web      # abre http://localhost:8777
```

`exportar_web.py` toma los eventos vigentes, les pone coordenadas y deja
`web/eventos.json`.

Las páginas son:

| Archivo | Qué es |
|---|---|
| `web/index.html` | La **portada**: hero con el elenco de animales, panoramas de hoy y los cuatro destinos |
| `web/mapa.html` | El **mapa**: un pin-animal por evento (sin agrupar, a propósito), filtros de fecha (Hoy / Mañana / 7 días / Finde), precio, público y categoría, lista lateral y ficha con anterior/siguiente |
| `web/habla.html` | **Habla con la Loica**: el elenco recomienda por turnos, sin tokens ni servidor |
| `web/calendario.html` | Mes a mes |
| `web/descuentos.html` | Los **descuentos** de restaurante por banco, día y comuna |
| `web/blog.html` | Las ediciones del blog |
| `web/agrega.html` | Formulario para publicar |
| `web/nosotros.html` | Quién hace esto y el elenco explicado |
| `web/e/<id>.html` | Una ficha por evento, para que el link compartido tenga vista previa |

Todas comparten `loica.css` (tokens y componentes) y `loica.js` (las ocho
mascotas en SVG, categorías, traducciones es/en/pt y utilidades). Los enlaces
a esos dos archivos llevan `?v=N`: el sitio es estático y sin build, así que
ese número es lo único que obliga al navegador a soltar la versión vieja
después de un cambio de estilos. **Si tocas `loica.css` o `loica.js`, sube el
número en las ocho páginas y en la plantilla de `exportar_web.py`.** Van todos
juntos: la plantilla se había quedado en `v=5` mientras el resto iba en `v=9`,
y las 2.486 fichas servían CSS viejo a quien ya hubiera entrado antes.

```bash
# sube el cache-buster en todo el sitio de una vez
sed -i '' 's/?v=10/?v=11/g' web/*.html exportar_web.py && python3 exportar_web.py
```

### El alto de la barra inferior es un token

`--alto-nav` en `loica.css` define cuánto mide la barra de destinos del
celular, y `--hueco-nav` es ese alto más el notch. **Ese hueco se reserva con
la variable, nunca con un número escrito a mano.** El sitio tenía `52px`
copiado en cinco archivos mientras la barra medía 65 —el ícono de la página
activa lleva pastilla y estiraba la fila—, así que la última línea de cada
página vivía debajo de la barra: en las fichas de evento, la que dice de qué
fuente salió el panorama. En escritorio la barra no existe y `--hueco-nav`
vale cero solo.

Es un **prototipo para ver la idea funcionando**, no la app de producción: usa
MapLibre con mosaicos de OpenStreetMap (sin API key) y lee un archivo JSON en
vez de Supabase. La decisión de stack para el MVP real sigue siendo la de
`arquitectura_tecnica.md` (Next.js + Supabase + MapLibre), y este prototipo
migra a eso sin rehacer nada: el modelo de datos y los adaptadores ya sirven.

## Cómo agregar una fuente nueva

Se edita `config/fuentes.yaml` — **no hay que tocar código**:

```yaml
  - id: mi_fuente
    nombre: Centro Cultural X
    url_base: https://ejemplo.cl
    url_agenda: https://ejemplo.cl/agenda/
    tipo_adaptador: wordpress   # wordpress | eventon | rss | html | api
    comuna: Providencia
    crawl_delay_seg: 2
    buscar_detalle: true        # abre cada ficha si falta la fecha
    activa: true
```

Conviene probarla sola antes de sumarla a la corrida diaria:
`python3 run_diario.py --probar --fuente mi_fuente`

## Los tipos de fuente

| Tipo | Cuándo se usa |
|---|---|
| `wordpress` | El sitio es WordPress y tiene la API REST abierta. Prueba The Events Calendar, después los tipos de contenido propios del sitio (los descubre solo). |
| `eventon` | Calendario EventON servido por `admin-ajax.php`. |
| `rss` | El sitio publica RSS o `sitemap.rss`. |
| `html` | Hay que leer el HTML. Intenta primero JSON-LD (`schema.org/Event`) y si no, usa los selectores CSS de la configuración. |
| `sitemap` | El listado solo entrega links y los datos viven en cada ficha. |
| `carteleras` | Dos niveles: índice de locales → cartelera de cada local. |
| `cine` | Cartelera semanal de cine: una sección por día, funciones con hora. |
| `tabla` | Tablas de talleres municipales, con el recinto y su dirección en las filas sobre el encabezado. |
| `json` | API JSON propia, con el mapeo de campos declarado en el YAML. |
| `ticketmaster` | Ticketmaster Discovery (API oficial con permiso explícito). |
| `manual` | Ingesta asistida desde `datos/manual/*.yaml` y `*.csv`. No hace peticiones. |

### El circuito under: `carteleras`

Las ticketeras independientes publican un listado general corto pero enlazan la
cartelera completa de cada local. Leer solo el listado general deja fuera casi
todo: de los 17 eventos publicados de Bar de René, el listado general de
PortalTickets mostraba **uno**.

El adaptador baja un nivel y recorre cada local. La tarjeta de la cartelera ya
trae título, fecha y "Local, Comuna", así que no hay que abrir la ficha de cada
evento: una corrida son 1 + 23 peticiones, no 200.

Ahí vive el circuito de tocatas que ninguna municipalidad publica: Bar de René,
Bar Raíces en Yungay, Kahuin, Mesón Nerudiano, Sala Master, Sala SCD Egaña.

Los eventos que quedan sin comuna **no son un error**: PortalDisc es nacional y
esas tarjetas son de regiones (Teatro Mauri en Valparaíso, MagBar en Chillán,
Bandera 1001 en Concepción). `requiere_comuna` los descarta, que es lo correcto.

### Cine: `cine` y la excepción a colapsar

Los cines de barrio no publican eventos, publican la semana: una sección por
día con las funciones y su hora. La fecha completa no está escrita en ninguna
parte —la sección dice "Jueves 13" y el mes vive en otro titular—, así que el
adaptador busca la única fecha cercana a hoy que calce con ese día de la semana
Y ese número. Cruza fin de mes y fin de año solo.

Los cines son además la única fuente que se salta `colapsar_multidia`, con
`colapsar: false`. Para una exposición, fusionar 30 días idénticos es correcto;
para un cine, fusionar la función del jueves con la del domingo borra los
horarios, que son justamente el dato que la gente busca.

### Lo que no se puede rastrear: `manual`

Passline responde 403 a cualquier cliente automático —probado con user-agent
vacío, de Chrome y neutro—, así que no es el filtro por la palabra "bot" que
tiene chilecultura sino bloqueo por IP o huella TLS. Instagram, por su parte,
no permite leer cuentas ajenas por API.

En esos casos el descubrimiento lo hace una persona navegando normal, y el
pipeline aporta lo de siempre: normaliza, deduplica contra lo ya guardado,
geocodifica y lo deja en revisión con su link de origen. Se escriben en
`datos/manual/` y entran con las mismas reglas que el resto — sin `fuente_url`
no se guarda.

Acepta dos formatos:

- **`.yaml`** escrito a mano (ver `_plantilla.yaml`), para el dato suelto.
- **`.csv`** exportado, para volúmenes. El mapeo de columnas por defecto es el
  de una exportación de Passline y se cambia con `csv_columnas`. El nombre del
  archivo pasa a ser la fuente: `passline.csv` → "Passline".

El CSV es la vía que hoy trae Passline: su API está tras un Cloudflare Managed
Challenge que responde 403 a cualquier cliente automático —probado con nuestro
user-agent, con `Mozilla/5.0` y con uno que dice "bot"—, incluso desde la
máquina donde corre el pipeline. No es el filtro por la palabra "bot" que tiene
chilecultura: es puntaje de IP y huella TLS, y un navegador de verdad sí pasa.
Así que la extracción la hace una persona con su navegador y el CSV entra acá.

> El tipo `api` ya no existe. Antes apuntaba fijo a Ticketmaster, así que
> cualquier otra fuente declarada como `api` consultaba Ticketmaster en
> silencio. Ahora cada API tiene su nombre y un tipo desconocido falla fuerte.

### Talleres municipales: `tabla` y `json`

Las municipalidades casi no publican eventos con fecha. Publican **talleres que
se repiten**: "lunes, miércoles y viernes de 19:00 a 20:30, desde marzo". Los
dos adaptadores traducen eso a las próximas sesiones (`loica/recurrencia.py`),
porque la fecha que le sirve al usuario no es cuándo empezó el programa en
marzo sino cuándo es la próxima clase.

Después `colapsar_multidia` hace lo correcto con cada caso sin configuración:

- Un taller de **lunes, miércoles y viernes** tiene huecos de 1 a 3 días, bajo
  el máximo tolerado, así que se fusiona en una tarjeta con rango de fechas.
- Un taller de **solo los sábados** tiene huecos de 7 días, sobre el máximo, y
  sobrevive como sesiones sueltas — que es lo que hace que aparezca en "este
  fin de semana", justo donde se lo busca.

**Limitación conocida:** `Evento` todavía no tiene campo de recurrencia. La
cadencia se guarda como texto en la descripción ("todos los martes y jueves a
las 19:00"). Alcanza para el mapa y para el filtro de gratis, pero un taller
semanal ocupa varias filas en vez de una.

### Fuentes ruidosas: `buscar_terminos` y `filtro_palabras`

Lo que mantenía apagadas a casi todas las municipalidades no era técnico: sus
APIs están abiertas. El problema es que publican las actividades mezcladas con
noticias municipales, y Recoleta tiene 2.532 posts.

```yaml
  buscar_terminos: [taller, feria, festival]   # ?search= contra el archivo completo
  filtro_palabras: [taller, feria, concierto]  # tiene que aparecer una
  descartar_palabras: [licitacion, ordenanza]  # si aparece, se descarta
```

`buscar_terminos` es el que importa: sin él se traen los 50 posts más recientes
—que en un municipio son licitaciones y cortes de agua— y se filtra sobre eso.
Con él se le pregunta al sitio por cada palabra y se recorre todo el archivo.

`filtro_palabras` se aplica en un solo lugar (`run_diario.py`), así que sirve
para cualquier tipo de fuente, y también antes de abrir fichas en `wordpress`,
para no gastar la cuota del sitio en posts que se van a descartar igual.

## Reglas de buena ciudadanía (están en el código, no en un papel)

Viven en `loica/red.py` y se aplican a todas las fuentes sin excepción:

- Se respeta `robots.txt`; si prohíbe una URL, no se pide.
- Se respeta el `Crawl-delay` que declare el sitio (Las Condes pide 10 segundos).
- El user-agent identifica al bot y lleva una URL de contacto.
- Todo se cachea en disco para no repetir peticiones.
- Reintentos con espera creciente ante error 429 o 5xx.
- Solo se copian **hechos** (título, fecha, lugar, precio, link). Las
  descripciones se recortan y las imágenes se enlazan, nunca se descargan.

## Qué hace con lo que encuentra

1. **Valida**: sin título o sin link a la fuente, se descarta. Sin fecha, no se
   descarta: queda en estado `revisar_fecha` para completarla a mano —
   descubrir el evento ya es la mitad del trabajo.
2. **Colapsa** las series de varios días. Una exposición de un mes llega como
   30 entradas idénticas y se guarda como una sola con fecha de inicio y fin.
3. **Deduplica** por título + fecha + lugar normalizados, así el mismo evento
   que llega por dos fuentes no se duplica.
4. **Publica con red de seguridad, no con curador previo.** El sitio se arma
   solo todos los días; lo que protege la calidad es el trío de filtros del
   export (no-panoramas, links de máquina, correcciones con `descartar`), el
   doble check que frena publicaciones rotas, y la revisión diaria que
   alimenta la memoria de correcciones. Revisar 2.500 borradores a mano cada
   día no era verdad ayer ni va a serlo mañana.
5. **Caduca** solo los eventos cuya fecha ya pasó.

## Estado (corrida del 9 de agosto de 2026)

**252 eventos de 16 fuentes activas, 97 con fecha futura confirmada, 22 gratis.**

El catálogo tiene 43 fuentes verificadas; 20 están activas y el resto quedó en
`config/fuentes.yaml` con `activa: false`, listas para encender de a poco.

| Fuente | Eventos futuros | Nota |
|---|---:|---|
| Universidad Diego Portales | 26 | Charlas y lanzamientos, casi todos gratis |
| Matucana 100 | 19 | Con precio y hora exacta |
| Teatro Municipal | 10 | |
| CEINA | 10 | La fecha sale de la ficha, no de la API |
| GAM | 8 | De 83 filas de calendario colapsadas |
| Balmaceda Arte Joven | 7 | Gratis |
| Agenda Cultural Las Condes | 5 | Muchas entradas son lugares permanentes |
| Teatro UC | 3 | **Mejor calidad de dato**: The Events Calendar nativo |
| Planetario USACH, NAVE, Ñuñoa | 7 | |
| Centro Cultural La Moneda | 2 | 28 eventos, la mayoría sin fecha legible |

Fuentes que responden bien pero **no aportan eventos futuros hoy**: Santiago
Cultura (su agenda está detenida desde julio de 2026), Parquemet y Estación
Central (publican *programas* permanentes con inscripción, no eventos con
fecha), MAVI y Vitacura. El informe diario las marca solo.

Ticketmaster sigue apagado: falta `TICKETMASTER_API_KEY` (gratis en
developer.ticketmaster.com).

## El otro catastro: descuentos bancarios

Un segundo pipeline, independiente del de eventos, que arma la tabla de
"qué restaurante tiene descuento, qué día y con qué tarjeta".

```bash
python3 run_descuentos.py                    # corrida completa
python3 run_descuentos.py --banco bancochile # un solo banco, para depurar
python3 run_descuentos.py --probar           # muestra sin escribir el JSON
```

Deja `web/descuentos.json` y un informe en `informes/AAAA-MM-DD_descuentos.md`.
Igual que el de eventos: **no llama a ningún modelo de lenguaje**, es Python
leyendo JSON público, y ninguna de las tres fuentes pide credencial de usuario.

Corre solo todos los días con GitHub Actions
(`.github/workflows/descuentos.yml`), así que no depende de que el Mac esté
despierto. Si un banco se cae y el catastro baja de 100 descuentos, el workflow
falla a propósito en vez de publicar una página vacía.

| Banco | Cómo se lee | Día | Dirección | Link al local |
|---|---|---|---|---|
| **Banco de Chile** (+ Edwards) | CMS propio, API abierta | ✅ 99% | ✅ 94% | ✅ 51% |
| **Bci** | `vivirconbeneficios.cl`, JSON de Rails | ❌ convenios permanentes | ✅ 100% | ✅ 99% |
| **Banco Falabella** | Contentful, token público de lectura | ✅ 100% | ❌ solo región | ✅ 100% |
| **Santander** | ⚠️ **captura manual**, ver abajo | ✅ 88% | ❌ solo región | ❌ |
| **Cencosud Scotiabank** | JSON incrustado en la landing | ✅ 55% | ❌ | ❌ |

De Banco de Chile sale **una fila por sucursal**: un restaurante con local en
Ñuñoa y otro en Concepción son dos datos distintos, y aplastarlos en uno obliga
a elegir una dirección y mentir en la otra.

Cada descuento lleva **dos links y no uno**, porque no son lo mismo: `url` es la
ficha del banco —la fuente, y la que manda si hay discusión sobre las
condiciones— y `sitio_web` es la página del local, que es donde se reserva.

### Santander no se rastrea, se anota a mano

`banco.santander.cl` responde 403 a cualquier petición que no venga de un
navegador, y bloquea **incluso `/robots.txt`**: no se puede leer ni siquiera qué
permite y qué no. Con cabeceras completas de navegador devuelve un desafío de
4 KB en vez del contenido. Eso es mitigación de bots activa, y rodearla sería
evadir un control que el banco puso a propósito. Este proyecto pide permiso
antes de leer (`loica/red.py`); no va a hacer la excepción justo acá.

Así que su catálogo —83 restaurantes, el mejor del mercado— se anota a mano en
[`datos/manual/descuentos_santander.yaml`](datos/manual/descuentos_santander.yaml),
igual que los eventos que no se pueden rastrear. Como es una foto y no un flujo,
**envejece**: la corrida avisa a los 45 días y cada ficha muestra en la página
la fecha en que se anotó. Para actualizar, se abre la fuente y se rehace la lista.

Scotiabank (tras login), Itaú, BancoEstado, BICE, Security, Ripley, Consorcio,
Coopeuch y Tenpo quedaron fuera por ahora. El sondeo de los quince emisores está
en [`notas/catastro_descuentos_bancos.md`](notas/catastro_descuentos_bancos.md).

### Solo Región Metropolitana

Loica es de Santiago, así que la corrida descarta lo que declara otra región:
un 40% en Puerto Natales es un dato correcto y completamente inútil para quien
abre la página, y además llenaba el filtro de comuna con noventa nombres que
nadie iba a elegir. De 1.075 descuentos vigentes en todo Chile quedan 652 en la
RM, repartidos en 32 comunas. Lo que no declara comuna ni región se deja pasar:
son en su mayoría cadenas nacionales que sí tienen local en Santiago.

**Dos cosas que hay que saber para leer el dato:**

*La lista de días vacía significa "sin restricción", no "no se pudo leer".* Los
convenios de Bci son de 10-25% cualquier día, y dejarlos fuera del filtro de Hoy
sería esconder 229 descuentos que hoy sirven.

*La frescura es el riesgo real.* Bci todavía publica promociones sin tocar desde
2021. Todo lo que declara vigencia vencida se descarta en la corrida; lo que no
declara ninguna pasa, pero va marcado en la página como "sin fecha declarada" en
vez de darse por bueno. Mandar a alguien a un restaurante con un descuento
muerto quema la confianza mucho más rápido que un evento pasado en la agenda:
allá se perdió un panorama, acá se paga la cuenta completa delante de la mesa.

Para agregar un banco se edita `config/bancos.yaml`, pero a diferencia de las
fuentes de eventos **sí hay que escribir un adaptador**: los tres publican
formas distintas del mismo hecho y esa diferencia no se puede esconder en YAML.

## Estructura

```
loica/
  modelo.py      Qué es un evento y cómo se identifica
  red.py         Cliente HTTP educado (robots, delays, caché)
  normalizar.py  Fechas y precios en español chileno → datos
  agrupar.py     Colapsa eventos de varios días
  almacen.py     Base SQLite y estados de curaduría
  fuentes/       Un adaptador por tipo de fuente
  descuentos/    El catastro bancario: modelo, parseo y un adaptador por banco
run_diario.py    Punto de entrada de los eventos
run_descuentos.py Punto de entrada de los descuentos
config/          Registro de fuentes y de bancos (esto es lo que se edita)
datos/           Base de datos, caché y logs (no se versiona)
informes/        Un informe por corrida
```

## Pendientes conocidos

- Cultura Providencia necesita otro adaptador (su RSS no trae fechas).
- Falta la API key de Ticketmaster (y exportarla antes de correr
  `instalar_agenda.sh` para que quede en el plist).
- El registro tiene ~7 pares de fuentes duplicadas de la misma institución
  (`recoleta`/`recoleta_municipio`, etc.), todas inactivas: depurar antes de
  encenderlas.
- La subida a Supabase todavía no está: hoy el destino es SQLite local.
