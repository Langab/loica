# Pipeline de eventos — Loica (Santiago de Chile)

Extractor automático de eventos desde sitios públicos. Corre solo todos los
días, **no usa modelos de lenguaje**, así que no consume tokens ni cuesta
dinero: es Python puro haciendo peticiones HTTP.

Cada evento queda amarrado a su **fuente original con link**. La app no
reemplaza a la fuente: la indexa y deriva el tráfico hacia ella. Eso es lo que
mantiene el rol de "tablón de anuncios" descrito en `04_negocio_y_legal/legal_chile.md`
del proyecto.

## Cómo se usa

```bash
python3 run_diario.py                  # corrida completa
python3 run_diario.py --fuente gam     # una sola fuente, para depurar
python3 run_diario.py --probar         # muestra lo que encontraría, sin guardar
python3 run_diario.py --sin-cache -v   # ignora la caché y muestra el detalle
```

Después de cada corrida queda un informe en `informes/AAAA-MM-DD_corrida.md`
con los eventos nuevos agrupados por comuna, listos para revisar.

## Cómo dejarlo corriendo solo

```bash
bash scripts/instalar_agenda.sh
```

Queda programado a las 06:00 con launchd (el equivalente a cron en macOS). Si
el Mac está durmiendo a esa hora, la corrida se ejecuta al despertar. Para
cambiar el horario: `HORA=22 MINUTO=30 bash scripts/instalar_agenda.sh`.

Para desinstalarlo: `bash scripts/instalar_agenda.sh --quitar`.

> Un Mac apagado no corre nada. Cuando el proyecto tenga servidor o repositorio
> en GitHub, esto se mueve a GitHub Actions (gratis) y corre en la nube.

## El prototipo del mapa

```bash
cd ~/dev/loica-pipeline
python3 exportar_web.py                          # geocodifica y exporta
python3 -m http.server 8777 --directory web      # abre http://localhost:8777
```

`exportar_web.py` toma los eventos vigentes, les pone coordenadas y deja
`web/eventos.json`. `web/index.html` es la página: mapa con pines por
categoría, filtros (Gratis, Hoy, Este finde y categorías), lista lateral,
ficha de evento con link a la fuente, y los tres idiomas (es / en / pt).

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

## Los cinco tipos de fuente

| Tipo | Cuándo se usa |
|---|---|
| `wordpress` | El sitio es WordPress y tiene la API REST abierta. Prueba The Events Calendar, después los tipos de contenido propios del sitio (los descubre solo). |
| `eventon` | Calendario EventON servido por `admin-ajax.php`. |
| `rss` | El sitio publica RSS o `sitemap.rss`. |
| `html` | Hay que leer el HTML. Intenta primero JSON-LD (`schema.org/Event`) y si no, usa los selectores CSS de la configuración. |
| `api` | API oficial con permiso explícito. Hoy: Ticketmaster Discovery. |

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
4. **Guarda como borrador**. Nada se publica sin que una persona lo revise.
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

## Estructura

```
loica/
  modelo.py      Qué es un evento y cómo se identifica
  red.py         Cliente HTTP educado (robots, delays, caché)
  normalizar.py  Fechas y precios en español chileno → datos
  agrupar.py     Colapsa eventos de varios días
  almacen.py     Base SQLite y estados de curaduría
  fuentes/       Un adaptador por tipo de fuente
run_diario.py    Punto de entrada
config/          Registro de fuentes (esto es lo que se edita a diario)
datos/           Base de datos, caché y logs (no se versiona)
informes/        Un informe por corrida
```

## Pendientes conocidos

- Cultura Providencia necesita otro adaptador (su RSS no trae fechas).
- Falta la API key de Ticketmaster.
- Falta geocodificar direcciones a coordenadas para el mapa.
- La subida a Supabase todavía no está: hoy el destino es SQLite local.
