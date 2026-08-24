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
| 4 | **Consolidación** | todo converge a `datos/eventos.db` deduplicado por título+fecha+lugar; el export arma `web/eventos.json` (panoramas) y `web/talleres.json` (clases semanales) |
| 5 | **Revisión + memoria de correcciones** | `revisar_extraccion.py` produce el informe y las colas; los arreglos viven en `config/correcciones/` y se aplican solos en cada corrida (ver abajo) |
| 6 | **Diagnóstico de la corrida** | `informe_corrida.py` deja un Excel en `informes/` para mirar el proceso, no el catastro (ver abajo) |
| 7 | **Doble check** | `verificar_web.py`: si el sitio quedó roto, vacío o cayó a la mitad, **no hay push** |
| 8 | **Publicación** | `run_todo.py` comitea solo su salida y pushea; GitHub Actions deja `web/` en Pages |
| 9 | **Corrida diaria a las 06:00** | GitHub Actions (`.github/workflows/corrida.yml`): no depende de ningún computador prendido. El Mac queda para probar (`--sin-publicar`) |

Un solo comando encadena los pasos 3 a 8:

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

- `config/correcciones/categorias.yaml` — **palabras en contexto → categoría**.
  Es la memoria del clasificador: "Magallanes" al lado de "vs" es un partido,
  "maratón" al lado de "película" es cine, "Edo Caroe" es stand-up aunque lo
  vendan en una sala de conciertos. Vale para los eventos de hoy y para los que
  lleguen mañana con las mismas palabras. Una regla puede además decir
  `categoria: descartar`: esto no es un panorama y no se publica.
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

### Cómo se sabe que una corrección arregla más de lo que rompe

Escribir una regla nueva es fácil; saber si se llevó puesto algo que ya estaba
bien, no. Contar solo los eventos que arregla esconde los que quiebra, y esa
lección costó cara una vez: una heurística de comunas que arreglaba 14 eventos
y rompía 15 estuvo a punto de publicarse porque nadie contó el otro lado.

Por eso las dos mitades de la calidad tienen su medición, y las dos usan el
mismo principio: **una segunda fuente que no habló con la primera.**

```bash
python3 scripts/auditar_categorias.py --comparar   # categorías
python3 scripts/verificar_lugares.py               # georreferenciación
```

**Categorías.** `datos/revision/auditoria_categorias_2026-08-22.tsv` es un
conjunto etiquetado a mano: 597 eventos del catastro revisados uno por uno,
cada uno con la categoría que le corresponde y con qué confianza se pudo
determinar (los `media` no cuentan como error — son los casos donde el título,
el lugar y la descripción no alcanzaban). `auditar_categorias.py` clasifica
esos mismos eventos con el código de hoy y dice cuántos calzan, cuántos no, y
—lo importante— **cuáles se rompieron** respecto de la corrida anterior. El
archivo viaja en git justamente para eso: el día que alguien toque
`clasificar.py` puede saber en un comando si retrocedió.

**Georreferenciación.** Una dirección sacada de internet puede estar vieja, mal
tipeada o ser de otra ciudad, y un pin equivocado manda a alguien a una esquina
donde no hay nada — peor que no tener pin. Así que cada dirección investigada
pasa por `verificar_lugares.py`, que la resuelve contra el catastro local de
OpenStreetMap. El catastro no sabe qué buscó nadie: si dice que "Merced 349"
existe en Santiago y cae donde el sitio del teatro dice que cae, son dos
testigos independientes. Sus cuatro veredictos:

| veredicto | qué pasa |
|---|---|
| `confirmado` | las dos vías coinciden (menos de 1 km). Entra con pin exacto. |
| `discrepa` | el catastro lo ubica lejos. **No entra el pin**, queda anotado. |
| `sin_catastro` | el catastro no conoce la calle (pasajes de población, sedes vecinales). Entra la dirección **sin coordenadas**: mejora la búsqueda de la corrida siguiente sin inventar un punto. |
| `descartado` | la investigación no encontró dato, o el lugar está fuera de la RM. |

El circuito de tres pasos: `revisar_extraccion.py` deja la cola ordenada por
impacto → alguien busca las direcciones y las anota **con la URL** en
`datos/revision/investigacion_lugares_AAAA-MM-DD.yaml` → `verificar_lugares.py`
contrasta y deja en `datos/revision/propuesta_lugares.yaml` solo lo aprobado,
listo para pegar en `lugares.yaml`.

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

## El diagnóstico de la corrida (paso 6)

`informe_corrida.py` deja `informes/AAAA-MM-DD_diagnostico.xlsx` en cada
corrida. **No es el catastro, es el proceso**: el sitio contesta "¿qué hago
hoy?" y esto contesta "¿está funcionando y dónde se está rompiendo?". Por eso
vive fuera de `web/` y fuera de git — `informes/` está en `.gitignore`.

Dos hojas:

- **Diagnóstico** — duración, fuentes con error, fuentes vivas que no aportan
  ningún evento futuro, altas y bajas contra la corrida anterior, reparto de la
  georreferenciación con el % de pines exactos, de dónde salió cada categoría
  (leída del texto contra adivinada por el recinto), lugares que aparecen por
  primera vez, y una fila por fuente.
- **Para revisar** — la cola de trabajo: eventos sin pin, sin categoría, con
  categoría adivinada o con el pin al centro de la comuna. Cada fila trae el
  link a la fuente para resolverla en diez segundos.

La comparación con "la corrida anterior" sale de `datos/historial_corridas.json`,
que el propio script escribe. Se usa eso y no `git show HEAD:web/eventos.json`
porque con `--sin-publicar` el HEAD no avanza y todas las corridas del día se
comparaban contra el mismo punto. El historial guarda además una fila de
agregados por corrida, así que a las pocas semanas muestra la tendencia.

No bloquea la publicación: informa. Y va **antes** del doble check a propósito,
porque cuando el doble check corta la publicación es justo cuando uno quiere
abrir el diagnóstico a ver qué se cayó.

## Dos cosas que `run_todo.py` hace a propósito

**Comitea sólo su propia salida.** Corre sin nadie mirando, así que nunca hace
`git add -A`: si en ese momento hay un archivo a medio editar, un `add -A` se
lo llevaría al repositorio. Agrega únicamente lo que produce: el sitio
(`web/eventos.json`, `web/talleres.json`, `web/descuentos.json`, `web/e/`), la
ingesta asistida (`datos/manual/`) y el estado que la corrida de mañana
necesita (`datos/eventos.jsonl`, `datos/coordenadas.json`,
`datos/historial_corridas.json`, `datos/revision/pendientes_*.yaml`).

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

## Cómo corre solo (GitHub Actions)

La corrida completa vive en `.github/workflows/corrida.yml` y corre todos los
días a las **06:00 de Chile** en un runner de GitHub: dura unos 105 minutos, así
que el sitio queda actualizado antes de las 08:00 y nadie abre Loica con la
agenda de ayer. **No depende de ningún
computador prendido.** Sigue siendo Python puro —no llama a ningún modelo, no
consume tokens— y en un repositorio público los minutos de Actions no cuestan.

Un runner nace vacío cada día, así que todo lo que la corrida necesita
recordar viaja en git:

| Archivo | Qué es |
|---|---|
| `datos/eventos.jsonl` | La copia de la base. `datos/eventos.db` sigue fuera de git (es binaria y cambia entera cada día); esto es la misma tabla, una línea por evento ordenada por hash, para que el diff de cada corrida muestre solo lo que cambió |
| `datos/coordenadas.json` | La caché de geocodificación |
| `datos/historial_corridas.json` | Contra qué compara el diagnóstico ("la corrida anterior") |
| `datos/revision/pendientes_*.yaml` | Las colas de corrección del día, listas para trabajarlas después de un `git pull` |

`Almacen` restaura la base desde `datos/eventos.jsonl` cuando está vacía o
cuando la copia cambió por debajo —lo decide por la huella del archivo, no por
su fecha, porque `git pull` le pone al archivo la hora del pull— y
`run_diario.py` la vuelca al terminar. En el Mac eso quiere decir que **`git
pull` deja la base local al día**. Para rearmarla de cero: `rm datos/eventos.db`
y la siguiente corrida la levanta desde la copia.

El índice de OpenStreetMap (24 MB) no va en git: vive en el release
[`indice-osm`](https://github.com/Langab/loica/releases/tag/indice-osm) del
repositorio y el workflow lo baja en cada corrida. Cuando se reconstruye, se
sube con `gh release upload indice-osm datos/indice_osm.db --clobber`.

**Cómo mirarla.** Pestaña *Actions* → *Corrida diaria de eventos*. Cada corrida
deja el informe del día en su resumen y un artefacto (30 días) con el Excel de
diagnóstico, los informes y el sitio tal como se publicó. Si falla, GitHub avisa
por correo y el sitio anterior sigue en pie.

**Cómo correrla a mano.** *Run workflow* en esa pestaña, o desde la terminal:

```bash
gh workflow run corrida.yml -f modo=completo       # extrae y publica
gh workflow run corrida.yml -f modo=sin-publicar   # deja sitio e informes como artefacto
gh workflow run corrida.yml -f modo=probar         # solo lista lo que traería cada fuente
```

Subir un CSV o YAML nuevo a `datos/manual/` también la dispara: la extracción
asistida entra al sitio sin esperar a mañana y sin prender ningún Mac.

**En el Mac** queda la corrida a mano, para probar:

```bash
git pull                              # trae la base de la nube
python3 run_todo.py --sin-publicar    # corre todo, no toca git
```

**Lo que la nube no alcanza.** La IP del runner es de datacenter y hay sitios
que la tratan distinto que a un computador de casa. Cuatro le responden 403
siempre: Recoleta, Cultura Providencia, Teatro Oriente y el CEP (medido el
22-08-2026). Otros la bloquean por volumen o según la IP que le toque ese
día —Quilicura, Artequin, Parquemet, Corporación de Estación Central, Feria
Friki, Club Chocolate, Teatro UC— y el cliente corta un dominio que cuelga a
la tercera URL para que no se coma la corrida. Sus eventos ya guardados siguen
vigentes hasta su fecha; lo nuevo de esas fuentes entra cuando alguien las
corre desde el Mac:

```bash
git pull && python3 run_todo.py --fuente cep    # una fuente, y publica
```

`python3 scripts/sondear_fuentes.py` (o `gh workflow run corrida.yml -f
modo=sondear` para verlo desde la nube) dice qué código HTTP responde cada
fuente desde donde se corre: es la forma de revisar esa lista cuando cambie.

`scripts/instalar_agenda.sh` (la corrida con launchd) sigue en el repositorio,
pero ya no es la corrida oficial y no conviene tenerla instalada a la vez: dos
corridas publicando el mismo día se pisan la base. Se desinstala con
`bash scripts/instalar_agenda.sh --quitar`.

> Los descuentos corren además en `descuentos.yml` a las 03:00, tres horas antes
> a propósito: la corrida grande regenera ese mismo JSON en su paso 2/7, y si se
> cruzaran habría dos workflows empujando `web/descuentos.json` a la vez. Queda
> de red de seguridad: si la corrida falla, los descuentos igual se actualizaron.
> Un commit hecho desde Actions no dispara `pages.yml` (es la regla de GitHub
> contra los bucles), así que ese JSON recién llega al sitio con la corrida de
> las 06:00, que sí le avisa a Pages.

## El dominio

El sitio vive en **https://loicasantiago.cl** (comprado en NIC Chile el
2026-08-24 a nombre de Benjamín, vence 2027-08-24). Sigue alojado en GitHub
Pages: el dominio solo cambia la dirección, no el hosting.

`SITIO` en `exportar_web.py` es el **único interruptor**. De ahí salen las
canónicas, los `og:url`, el `og:image`, el JSON-LD de cada ficha, el
`sitemap.xml` y el `robots.txt`. Los links internos son relativos, así que no
dependen de él.

La configuración que no vive en el repositorio:

| Dónde | Qué |
|---|---|
| NIC Chile | Los nameservers del dominio apuntan a Cloudflare |
| Cloudflare (DNS) | `A` del ápex a las cuatro IP de Pages, `AAAA` a las cuatro `2606:50c0:800x::153`, y `CNAME www → langab.github.io`. Todo en gris (sin proxy): con el proxy naranja, Pages no puede emitir el certificado |
| GitHub → Settings → Pages | Custom domain = `loicasantiago.cl` + Enforce HTTPS |

**El orden importa.** Poner el dominio personalizado en GitHub *antes* de que
los DNS resuelvan deja el sitio caído en las dos direcciones: apenas se
configura, `langab.github.io/loica` empieza a redirigir al dominio nuevo. Se
configuran los DNS primero, se espera a que `dig loicasantiago.cl` conteste las
IP de Pages, y recién ahí se toca GitHub.

Como se publica desde un workflow y no desde una rama, **no va un archivo
`CNAME` en `web/`**: GitHub lo ignora. El dominio se guarda en la configuración
del repositorio.

### La analítica

El sitio mide visitas con **Cloudflare Web Analytics**: sin cookies y sin huella
digital, así que no lleva banner de consentimiento —lo que importa porque la
Ley 21.719 rige desde diciembre de 2026—. A cambio no mide campañas UTM ni
eventos; si algún día hacen falta, el reemplazo natural es Umami.

Va en modo **manual (JS snippet)** y no en el automático: el automático inyecta
el script desde el proxy de Cloudflare, y los registros están en gris a
propósito.

El token es **público**: viaja en el HTML de todas las páginas, no es una
credencial y no va en los secretos del repositorio. Está repetido en las diez
páginas fijas y en la plantilla de `exportar_web.py`, igual que el `?v=` de los
estilos; si se cambia, se cambia en todas:

```bash
# cambia el token del beacon en todo el sitio de una vez
sed -i '' 's/TOKEN_VIEJO/TOKEN_NUEVO/g' web/*.html web/e/*.html exportar_web.py
```

La CSP de cada página tiene que dejar pasar dos cosas o la medición sale en
cero, sin avisar: `https://static.cloudflareinsights.com` en `script-src` (de
ahí baja el beacon) y `https://cloudflareinsights.com` en `connect-src` (ahí
reporta, en `/cdn-cgi/rum`).

`web/sitemap.xml` y `web/robots.txt` los genera `exportar_web.py` en cada
corrida (`escribir_sitemap` y `escribir_robots`). El sitemap lleva las diez
páginas fijas más una línea por ficha; sin él, Google descubre una ficha solo
si alguien la enlaza, y a un panorama que dura tres días no lo enlaza nadie a
tiempo.

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
| `web/talleres.html` | Los **talleres y clases** semanales (natación, yoga, cerámica, grabado, teatro, danza, cursos para personas mayores), con filtro por día, tipo y comuna y su propio mapa. Salen de `web/talleres.json`, separados de los panoramas por `es_taller()` en el export: una maratón es un panorama, la clase de natación de los martes es un taller. Lo que no es municipal entra por `config/talleres.yaml` (ver el adaptador `talleres`) |
| `web/descuentos.html` | Los **descuentos** de restaurante por banco, día y comuna |
| `web/blog.html` | Las ediciones del blog |
| `web/agrega.html` | Formulario para publicar |
| `web/nosotros.html` | Quién hace esto y el elenco explicado |
| `web/e/<id>.html` | Una ficha por evento, para que el link compartido tenga vista previa |

Todas comparten `loica.css` (tokens y componentes) y `loica.js` (los once
animales guía en SVG, categorías y subcategorías, traducciones es/en/pt y
utilidades). Los enlaces
a esos dos archivos llevan `?v=N`: el sitio es estático y sin build, así que
ese número es lo único que obliga al navegador a soltar la versión vieja
después de un cambio de estilos. **Si tocas `loica.css` o `loica.js`, sube el
número en las nueve páginas y en la plantilla de `exportar_web.py`.** Van todos
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
| `talleres` | Catastro de talleres permanentes (`config/talleres.yaml`): lugares que enseñan todas las semanas y no publican agenda. No hace peticiones. |
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

### El catastro de talleres que no son municipales: `talleres`

El 24-08-2026 la página de talleres tenía 1.879 clases y el **96% venía de tres
corporaciones municipales de deportes**: Ñuñoa (1.247), Huechuraba (384) y
Santiago (190). La cerámica, el grabado, el teatro, la danza y los cursos para
personas mayores de la ciudad no aparecían por ninguna parte, y no es que no
existan: es que **un taller de barrio no publica agenda**. Su clase de los
martes a las 19:00 lleva años igual y no tiene nada que anunciar, así que no
hay feed, ni JSON, ni calendario — hay una página que dice "Martes de 11:00 a
13:30 hrs" en prosa. Sondear treinta estudios lo confirmó: casi todos son
WordPress con la API REST cerrada, Wix o Squarespace, y el horario está escrito
a mano en una página suelta.

Eso se cataloga UNA vez, como las salas de cine: `config/talleres.yaml` guarda
el lugar (nombre, dirección, comuna, link) y sus talleres (días, hora, precio),
y `loica/fuentes/talleres.py` emite una sesión por cada día declarado. De ahí
en adelante es una fuente más: se deduplica, se geocodifica y el export la
junta en una tarjeta con sus `dias_semana`, que es lo que la página filtra.

Las reglas que evitan que el archivo se llene de mentiras:

- **Nada se inventa.** Un taller entra con los días y la hora que su sitio
  publica. El que no los publica queda con `activo: false` y una nota: existe,
  su dirección ya está verificada, y completarlo es una llamada de teléfono.
  De los 24 lugares catastrados hoy, 7 publican horario y 17 esperan ese dato.
- **Todo caduca.** `verificado` + `vigente_hasta` (por defecto, cuatro meses:
  el largo de una temporada) sacan al lugar del sitio cuando la verificación
  vence, y la corrida lo avisa en su registro.
- **El año se revisa.** Centro Cerámica publica "los domingos 5, 12, 19 y 26 de
  octubre", pero en 2026 el 5 de octubre cae lunes: ese ciclo es de 2025 y la
  página nunca caducó sola. Por eso está apagado.
- **Sin `url` no se publica**, como en toda fuente.

Dos detalles del adaptador que costaron una medición:

- El mismo curso en cuatro horarios son **cuatro clases distintas** para quien
  elige a cuál puede ir, pero la huella de deduplicación es título+día+lugar y
  `colapsar_multidia` fusiona lo que caiga a menos de cuatro días: de 92
  sesiones entraban 42 y la sobreviviente se dibujaba como una temporada de un
  mes. El catastro guarda el nombre tal como lo escribe el taller y el
  adaptador le agrega el día y la hora **solo cuando el nombre se repite**.
- `vigente_desde` existe para las temporadas que empiezan después: un ciclo que
  parte en octubre no tiene clases en septiembre.

### Los museos: una sola puerta para ocho instituciones

Todos los museos y bibliotecas del **Servicio Nacional del Patrimonio Cultural**
corren el mismo Drupal, y ese Drupal tiene **JSON:API abierto** en `/jsonapi`.
Es el mejor dato estructurado del catálogo y se configura una vez: para sumar
el siguiente museo del Patrimonio se copia la entrada y se cambia el dominio.

```yaml
  endpoint: /jsonapi/node/evento
  parametros: {page[limit]: 50, sort: -field_fechas.end_value}
  json:
    lista: data
    plantilla_url: https://www.mnba.gob.cl{attributes.path.alias}
    campos:
      inicio: attributes.field_fechas.value
      fin: attributes.field_fechas.end_value
      hora_inicio_segundos: attributes.field_horario.from
      categoria: attributes.field_tipo_evento
```

Tres detalles que valen la pena:

- **`sort=-field_fechas.end_value`** ordena por fecha de término descendente,
  así la primera página son justamente las muestras que siguen abiertas. Es la
  forma de pedir "lo vigente" sin poder escribir la fecha de hoy en un YAML
  estático.
- **`hora_inicio_segundos`** existe porque este Drupal guarda el horario como
  segundos desde medianoche (`{"from": 61200}` son las 17:00). No es una hora
  que `parsear_hora` pueda leer: es un formato de campo, y se declara aparte.
- El tipo de contenido se llama `evento` pero cubre **exposiciones, talleres,
  visitas guiadas y charlas**, distinguidas en `field_tipo_evento`. Eso alimenta
  al clasificador sin adivinar.

Con eso entran MNBA, MNHN, Museo Histórico Nacional, Museo Benjamín Vicuña
Mackenna, Museo de la Educación, Archivo Nacional, Biblioteca Nacional y
Biblioteca de Santiago.

**Los que no son del Patrimonio van uno por uno.** El MAC no expone sus muestras
por API —solo posts de prensa— pero publica el HTML más limpio del catálogo, con
el rango de fechas y la sede en la misma tarjeta. Sus **dos sedes quedan a 4 km**
(Parque Forestal y Quinta Normal), así que el adaptador HTML aprendió a leer el
nombre del recinto de un selector (`selectores.lugar`): sin eso las dos caen en
el mismo pin. Museo Violeta Parra tiene un tipo de contenido propio (`agenda`) y
Artequin publica sus talleres como posts normales.

**Los que quedaron apagados, con el motivo escrito en `notas`:** el MIM y el
Precolombino son SPAs que arman la cartelera con JavaScript, el Museo de la
Memoria tiene `/cartelera` pero servida igual por JavaScript, y el Museo
Ferroviario responde 500 en todo lo que no sea su home. Las cuatro direcciones
sí quedaron verificadas en `correcciones/lugares.yaml`, listas para cuando
entren por `datos/manual/`.

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
5. **Caduca** solo los eventos que ya **terminaron**.

### Vigente es lo que no ha terminado, no lo que no ha empezado

Durante meses la vigencia se midió por `inicio`, en cuatro lugares distintos:
el filtro de entrada (`Evento.es_valido`), el caducador, el resumen y la
consulta del export. Con esa regla, **una exposición que abre el 18 de julio y
cierra el 27 de septiembre desaparecía del sitio el 19 de julio**, y una
temporada de teatro desaparecía al día siguiente del estreno. Eran 189 eventos
invisibles en el mapa, y es la forma normal de publicar de un museo: casi toda
su cartelera es un rango, no un día. Medido sobre la misma base, la regla nueva
**suma 189 y no pierde ninguno**.

La regla vive ahora en un solo lugar, `almacen.SQL_VIGENTE`:

```sql
COALESCE(NULLIF(fin, ''), inicio) >= date('now', 'localtime')
```

Sin `fin` manda `inicio`, como siempre. `almacen.revivir_vigentes()` devuelve a
borrador lo que la regla vieja había caducado antes de tiempo — sin eso,
arreglar la regla no recuperaba nada de lo ya enterrado.

Dos consecuencias para quien toque el sitio: un evento vigente **puede tener
`inicio` en el pasado**, y cualquier filtro de fecha del front tiene que cruzar
el tramo `[inicio, fin]` con la ventana del filtro en vez de mirar solo
`inicio` (eso vive en `sesionEnRango()` de `web/loica.js`).

## Estado (corrida del 14 de agosto de 2026)

**2.420 eventos publicados de 65 fuentes activas, 368 gratis, 1.888 (78%) con
ubicación exacta en el mapa.**

El catálogo tiene 114 fuentes catastradas; 65 están activas y el resto quedó en
`config/fuentes.yaml` con `activa: false` **y el motivo escrito en `notas`**,
para no volver a investigar lo mismo.

Lo que movió esta corrida:

| | Antes | Ahora |
|---|---:|---:|
| Eventos publicados | 2.414 | 2.420 |
| Ubicación exacta | 61% | **78%** |
| Museos y bibliotecas | 8 eventos (solo MAVI) | **55** |
| Correcciones de lugar | 86 | 118 |

Los museos entraron con **pin exacto desde el primer día**: los 55 eventos salen
con precisión `correccion`, porque la dirección de cada museo se verificó contra
el catastro OSM local o contra las coordenadas que publica el propio museo antes
de encender la fuente.

Dos errores de coordenadas que encontró la auditoría y quedaron arreglados en la
tabla `RECINTOS` de `loica/geo.py`: el **Movistar Arena** estaba 1,7 km al
norponiente, en plena Alameda en vez de dentro del Parque O'Higgins (14 eventos),
y la **Biblioteca Nacional**, 290 m al oriente.

Los museos y bibliotecas que se encendieron en esta corrida:

| Fuente | Nuevos | Puerta | Nota |
|---|---:|---|---|
| Museo Violeta Parra | 36 | WordPress, post type `agenda` | La fecha sale de la ficha |
| MAC (U. de Chile) | 15 | HTML | Dos sedes, dos pines |
| Museo Nacional de Historia Natural | 9 | JSON:API | Quinta Normal |
| Biblioteca de Santiago | 9 | JSON:API | La más rica en actividades familiares gratuitas |
| Museo Nacional de Bellas Artes | 8 | JSON:API | |
| Biblioteca Nacional | 6 | JSON:API | |
| Museo Histórico Nacional | 3 | JSON:API | |
| Museo Artequin | 4 | WordPress | Quinta Normal |
| Archivo Nacional | 1 | JSON:API | |

Fuentes que responden bien pero **no aportan eventos futuros hoy**: Santiago
Cultura (su agenda está detenida desde julio de 2026), Parquemet y Estación
Central (publican *programas* permanentes con inscripción, no eventos con
fecha), y del lado de los museos, el **Museo de la Educación** y el **Museo
Vicuña Mackenna**, que tienen la API abierta y la cartelera vacía. El informe
diario las marca solo, y quedan encendidas: el día que publiquen, entran.

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

## El tercer catastro: la cartelera de cine

Un pipeline aparte, como el de descuentos y por la misma razón: una cartelera
son **miles de funciones que caducan en tres días**. Meterlas a
`datos/eventos.jsonl` —la copia de la base que viaja en git y se comitea en
cada corrida— habría hecho crecer el repositorio varios megas diarios para
guardar lo que mañana ya no existe. Y la huella de deduplicación de un evento
es (título, DÍA, lugar), así que las cinco funciones de la misma película el
mismo día en la misma sala habrían colapsado en una.

```bash
python3 run_cine.py                  # corrida completa
python3 run_cine.py --via jsonld     # una sola vía, para depurar
python3 run_cine.py --probar         # muestra sin escribir el JSON
python3 scripts/catastro_cines.py    # refresca el catastro de salas
```

Deja `web/cine.json`, que alimenta `web/cine.html` (mapa de salas + cartelera).
Corre dentro de `run_todo.py` como paso 4, **después de exportar**, porque una
de sus cuatro vías lee `web/eventos.json`.

### Las cuatro vías, y por qué son cuatro

| Vía | Salas | Cómo |
|---|---|---|
| `jsonld` | 8 | Cinemark publica `ScreeningEvent` de schema.org en el HTML de cada sala. Es el dato que ellos mismos publican para las máquinas: se lee con `requests` y punto. Una petición extra por película trae la clasificación y el idioma, que el JSON-LD no incluye. |
| `semanal` | 2 | El Normandie y El Biógrafo publican **la semana**, no la función. Un parser por sala. |
| `agenda` | 4 | La Cineteca Nacional, Matucana 100, el Centro Arte Alameda y el CCC ya llegan por las fuentes de siempre: se recogen de `web/eventos.json` y no se piden dos veces. |
| `asistida` | 30 | Cineplanet y Cinépolis cierran su cartelera. Las mira una persona con el navegador siguiendo `datos/manual/_prompt_cine.md` y deja `datos/manual/cartelera_cines.csv`, que dispara la corrida al subirse. |

**Por qué esas dos cadenas no se leen solas**, medido el 24-08-2026:
Cineplanet entrega la cartelera solo a quien trae la cookie de sesión que su
propio sitio planta en el navegador (la misma petición da 200 con cookie y 403
sin ella, con cualquier user-agent), y la API de Cinépolis responde
`401 Unauthorized access` porque pide un token. Las dos son puertas cerradas a
propósito y el proyecto no las fuerza — la misma regla que con Passline. Sus
30 salas igual salen **en el mapa con su dirección y el link a su cartelera
oficial**, y la página lo dice con todas sus letras en vez de esconderlo.

### El catastro de salas

`config/cines.yaml` guarda las 44 salas de la Región Metropolitana con su
coordenada, y ese archivo es el motivo por el que la página tiene mapa aunque
ese día no se haya podido leer ninguna cartelera: una sala no es un evento,
es una dirección que va a seguir ahí el año que viene.

Lo arma `scripts/catastro_cines.py` con la lista oficial de Cinemark (que trae
las coordenadas dentro del `googleMapsUrl`) y el índice OSM local, el mismo que
geocodifica todo el pipeline. OSM tiene las salas de Cinépolis con el nombre de
la cadena pelado —veinte pines que dicen "Cinepolis" y ninguno dice en qué mall
está—, así que el nombre de cada una salió de cruzar su coordenada con el
centro comercial que la contiene. Las seis que no tenían ningún mall a menos de
350 m quedaron con `verificado: false`: es una pregunta abierta para la próxima
extracción asistida, no un nombre inventado.

Lo escrito a mano manda: el script rellena huecos y avisa de lo que cambió,
pero no pisa una entrada con `verificado: true`.

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
  cines.py       El catastro de salas de cine y cómo se le pega una función
  cartelera/     Las cuatro vías de la cartelera: jsonld, semanal, agenda, asistida
run_diario.py    Punto de entrada de los eventos
run_descuentos.py Punto de entrada de los descuentos
run_cine.py      Punto de entrada de la cartelera de cine
config/          Registro de fuentes, de bancos y de salas de cine (esto es lo que se edita)
datos/           Base, caché y logs (fuera de git) + el estado que sí viaja: eventos.jsonl, coordenadas.json, historial_corridas.json, revision/, manual/
informes/        Un informe por corrida
```

## Pendientes conocidos

- Cultura Providencia necesita otro adaptador (su RSS no trae fechas).
- Falta la API key de Ticketmaster: se guarda como secreto `TICKETMASTER_API_KEY`
  en el repositorio (Settings → Secrets and variables → Actions) y se enciende
  la fuente en `config/fuentes.yaml`.
- El registro tiene ~7 pares de fuentes duplicadas de la misma institución
  (`recoleta`/`recoleta_municipio`, etc.), todas inactivas: depurar antes de
  encenderlas.
- La subida a Supabase todavía no está: hoy el destino es SQLite local.
- El JSON-LD de Cinemark no declara el idioma de cada función: la ficha de la
  película sí dice en qué idiomas se está dando, y de ahí se rescata solo
  cuando la película se da en UNO —si está en doblada y subtitulada, cuál es
  cada función no se sabe y la celda queda vacía a propósito.
- El Biógrafo se actualiza los jueves y a veces se atrasa. Cuando la semana
  publicada ya terminó, el adaptador devuelve cero y lo dice: no se manda a
  nadie a una función de hace cinco días. Eso se arregla hablando con el cine.
