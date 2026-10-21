# Explorar fuentes con reverse-api-engineer

Muchas fuentes quedaron apagadas porque su página la arma JavaScript: el HTML
que llega no trae fechas y no hay RSS, sitemap ni API documentada. Casi
siempre hay una API detrás (un Strapi, un Next.js con su payload, un backend
propio), solo que nadie la anunció. [reverse-api-engineer](https://github.com/kalil0321/reverse-api-engineer)
abre la página en un navegador, graba el tráfico (HAR) y con Claude escribe un
cliente de esa API.

**Es una herramienta de exploración, no de la corrida.** Se usa una vez por
fuente y a mano. La corrida diaria sigue siendo Python puro sin modelos de
lenguaje: lo que se descubre acá termina como una entrada `tipo_adaptador: json`
en `config/fuentes.yaml` (o un adaptador chico), nunca como una llamada a la
herramienta.

## Instalar (una vez)

```bash
brew install uv
uv tool install "reverse-api-engineer[manual]"
uvx playwright install chromium
```

Usa la sesión de Claude Code de este Mac. Cada exploración cuesta lo que
informa al final (`total cost`): la de MMDH fueron US$4,44 con Sonnet.

## Explorar una fuente

```bash
herramientas/reverse_api/explorar_fuente.sh <id_fuente> <url> "<qué buscar>"
```

- **De a una.** Este Mac tiene 8 GB: cuatro exploraciones en paralelo se
  murieron todas (código -9) el 14-10-2026.
- Deja el resultado en `../exploracion_apis/<id_fuente>/`, **fuera del repo**:
  los HAR graban cookies y cabeceras. El `.gitignore` igual bloquea `*.har`.
- Tope de 15 minutos por defecto (`RAE_TIMEOUT_SEG`).

## Reglas (van dentro del encargo y valen para quien lo use)

1. Antes de explorar, mirar el `robots.txt` del sitio **y** el del dominio de
   la API. Si prohíbe la ruta de la API, no se usa aunque responda: Ligup
   (`ccn_nunoa_cultura`, `quinta_normal_municipio`) prohíbe `/api/` y Las Condes
   prohíbe `/wp-json/`.
2. Nada que evada controles: Passline (403 a clientes automáticos) y Centro
   Arte Alameda (desafío de Cloudflare) quedan fuera.
3. Nada con login, token de sesión ni formularios.
4. Leer el cliente generado antes de ejecutarlo.

## De la exploración a la corrida

1. Leer el `README.md` que deja la herramienta: endpoint, parámetros, campos.
2. Confirmar a mano una fecha contra la ficha pública. En MMDH la API decía
   `21:30Z` y la ficha "18:30 h": era UTC de verdad, y por eso la fuente lleva
   `zona_horaria: UTC`. Cinemark, en cambio, etiqueta con `Z` horas que ya son
   de Chile: no hay regla general, se comprueba en cada fuente.
3. Escribir la entrada en `config/fuentes.yaml` con el adaptador `json`
   (opciones útiles: `paginacion`, `plantilla_url`, `zona_horaria`,
   `prefijo_imagen`, campo `precio_texto`).
4. `python3 run_diario.py --fuente <id> --probar` y, si trae eventos de la RM
   con hora y link correctos, `activa: true`.

## Fuentes exploradas

| Fuente | Fecha | robots.txt | Resultado |
|---|---|---|---|
| `mmdh` | 14-10-2026 | permite (mmdh.cl y manager.mmdh.cl) | Strapi v4 público `manager.mmdh.cl/api/post-carteleras`. **Activa desde el 20-10-2026** (9 eventos vigentes) |
| `mim` | 20-10-2026 | mim.cl no tiene robots.txt real; el del Strapi no restringe | La herramienta encontró el Strapi Cloud (`enduring-authority-d160bd805e.strapiapp.com`) y se cortó por saldo; `/api/events` se confirmó a mano. **Activa** (2 vigentes) |
| `torneostcg` | 20-10-2026 | `Allow: /` | Sin API: los datos vienen en el payload de Next.js. Adaptador propio (`loica/fuentes/torneostcg.py`) que toma solo los destacados de la RM. **Activa** (3 regionales) |
| `maipu` | 20-10-2026 | no tiene robots.txt real | La app Vue no tiene ruta de agenda: solo noticias, trámites y licitaciones. Los panoramas irían mezclados con noticias. **Sigue apagada** |

Si la herramienta se corta por saldo ("Credit balance is too low"), lo que
alcanzó a ver queda en el log de `../exploracion_apis/<id>/`: casi siempre ya
nombra el dominio de la API, y desde ahí se sigue a mano con `curl -g`.
